"""
Minimal HTTP API for Chronicle. Requires [api] extra: pip install -e ".[api]".

Set CHRONICLE_PROJECT_PATH to the project directory (must exist and contain chronicle.db,
or the path will be created and initialized on first write). No auth in this minimal version;
run behind your own auth/proxy in production.

Run: uvicorn chronicle.api.app:app --reload
"""

from __future__ import annotations

import base64
import binascii
import io
import json
import logging
import os
import tempfile
import time
import uuid
import zipfile
from collections.abc import Awaitable, Callable
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from chronicle.core.errors import (
    ChronicleIdempotencyCapacityError,
    ChronicleProjectNotFoundError,
    ChronicleUserError,
)
from chronicle.core.identity import get_effective_actor_from_request
from chronicle.core.validation import MAX_EVIDENCE_BYTES, MAX_IMPORT_BYTES, MAX_LIST_LIMIT
from chronicle.scorer_contract import run_scorer_contract
from chronicle.store import export_import as export_import_mod
from chronicle.store.commands.reasoning_brief import reasoning_brief_to_html
from chronicle.store.project import create_project, project_exists
from chronicle.store.session import ChronicleSession

# Project path from env; None if not set
PROJECT_PATH_ENV = "CHRONICLE_PROJECT_PATH"
REQUEST_ID_HEADER = "X-Request-Id"
log = logging.getLogger("chronicle.api")


def _get_actor(request: Request) -> tuple[str, str, str]:
    """Resolve (actor_id, actor_type, verification_level) from request (IdP or X-Actor-Id / X-Actor-Type). Fallback: default, human, none."""
    actor_id, actor_type, verification_level = get_effective_actor_from_request(request)
    if not actor_id or not actor_id.strip():
        actor_id = "default"
    if actor_type not in ("human", "tool", "system"):
        actor_type = "human"
    return (actor_id, actor_type, verification_level or "none")


def _get_project_path() -> Path:
    raw = os.environ.get(PROJECT_PATH_ENV)
    if not raw or not raw.strip():
        raise HTTPException(
            status_code=503,
            detail=f"Set {PROJECT_PATH_ENV} to the Chronicle project directory to use the API.",
        )
    path = Path(raw.strip()).resolve()
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
    if not project_exists(path):
        create_project(path)
    return path


class CreateInvestigationBody(BaseModel):
    title: str
    description: str | None = None
    investigation_key: str | None = None


class ProposeClaimBody(BaseModel):
    text: str
    initial_type: str | None = None
    epistemic_stance: str | None = None  # e.g. working_hypothesis | asserted_established


class LinkBody(BaseModel):
    span_uid: str
    claim_uid: str
    rationale: str | None = (
        None  # Optional: why this evidence supports/challenges this claim (warrant)
    )
    defeater_kind: str | None = None  # Optional: rebutting | undercutting (for challenge links)


class DeclareTensionBody(BaseModel):
    claim_a_uid: str
    claim_b_uid: str
    tension_kind: str = "contradiction"
    defeater_kind: str | None = None  # Optional: rebutting | undercutting


class SetTierBody(BaseModel):
    tier: str  # spark | forge | vault
    reason: str | None = None


class ScoreBody(BaseModel):
    """Eval contract: query, answer, evidence. Same shape as docs/eval_contract.md."""

    query: str
    answer: str
    evidence: list[dict[str, Any] | str]


app = FastAPI(
    title="Chronicle API",
    description="Minimal HTTP API for evidence, claims, defensibility, and export/import. Same shapes as eval contract and defensibility schema.",
    version="0.1.0",
)

# Static files (e.g. web verifier)
_STATIC_DIR = Path(__file__).resolve().parent / "static"
if _STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


def _request_id_for(request: Request) -> str:
    rid = getattr(request.state, "request_id", None)
    if isinstance(rid, str) and rid.strip():
        return rid.strip()
    return "unknown"


def _error_content(request: Request, detail: Any) -> dict[str, Any]:
    return {"detail": detail, "request_id": _request_id_for(request)}


def _clamp_limit(limit: int | None, default: int) -> int:
    if limit is None:
        return min(default, MAX_LIST_LIMIT)
    return max(1, min(limit, MAX_LIST_LIMIT))


def _content_length_exceeds(request: Request, max_bytes: int) -> bool:
    """Best-effort early reject when Content-Length exceeds configured limit."""
    raw = (request.headers.get("content-length") or "").strip()
    if not raw:
        return False
    try:
        return int(raw) > max_bytes
    except ValueError:
        return False


def _max_json_payload_bytes(max_blob_bytes: int) -> int:
    """Allow base64+JSON overhead while still bounding in-memory body size."""
    return int(max_blob_bytes * 4 / 3) + 16 * 1024


async def _read_upload_file_limited(file: UploadFile, max_bytes: int) -> bytes:
    """Read UploadFile in chunks and abort if payload exceeds max_bytes."""
    buf = bytearray()
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        buf.extend(chunk)
        if len(buf) > max_bytes:
            raise HTTPException(
                status_code=413, detail=f"File exceeds max size ({max_bytes} bytes)"
            )
    return bytes(buf)


async def _write_upload_file_limited(file: UploadFile, max_bytes: int) -> Path:
    """Stream UploadFile to temp file and abort if payload exceeds max_bytes."""
    total = 0
    with tempfile.NamedTemporaryFile(suffix=".chronicle", delete=False) as f:
        temp_path = Path(f.name)
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                temp_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"File exceeds max size ({max_bytes} bytes)",
                )
            f.write(chunk)
    return temp_path


def _encode_cursor(created_at: str, uid: str) -> str:
    raw = json.dumps({"created_at": created_at, "uid": uid}, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_cursor(cursor: str | None) -> tuple[str, str] | None:
    if cursor is None:
        return None
    token = cursor.strip()
    if not token:
        return None
    padding = "=" * ((4 - len(token) % 4) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode((token + padding).encode("ascii")))
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid cursor") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid cursor payload")
    created_at = payload.get("created_at")
    uid = payload.get("uid")
    if not isinstance(created_at, str) or not isinstance(uid, str) or not created_at or not uid:
        raise HTTPException(status_code=400, detail="Invalid cursor payload")
    return (created_at, uid)


def _page_meta(*, limit: int, has_more: bool, next_cursor: str | None) -> dict[str, Any]:
    return {"limit": limit, "has_more": has_more, "next_cursor": next_cursor}


@app.middleware("http")
async def request_context_and_logging(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request_id = (request.headers.get("x-request-id") or "").strip() or str(uuid.uuid4())
    request.state.request_id = request_id[:128]
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)
        log.exception(
            json.dumps(
                {
                    "event": "request_failed",
                    "request_id": _request_id_for(request),
                    "method": request.method,
                    "path": request.url.path,
                    "client_ip": request.client.host if request.client else None,
                    "duration_ms": elapsed_ms,
                }
            )
        )
        raise
    elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)
    response.headers[REQUEST_ID_HEADER] = _request_id_for(request)
    log.info(
        json.dumps(
            {
                "event": "request_completed",
                "request_id": _request_id_for(request),
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "client_ip": request.client.host if request.client else None,
                "duration_ms": elapsed_ms,
            }
        )
    )
    return response


@app.exception_handler(ChronicleIdempotencyCapacityError)
def handle_idempotency_capacity_error(
    request: Request, exc: ChronicleIdempotencyCapacityError
) -> JSONResponse:
    """Map idempotency-capacity user errors to HTTP 429."""
    return JSONResponse(status_code=429, content=_error_content(request, str(exc)))


@app.exception_handler(ChronicleProjectNotFoundError)
def handle_project_not_found(request: Request, exc: ChronicleProjectNotFoundError) -> JSONResponse:
    """Map project-not-found user errors to HTTP 404."""
    return JSONResponse(status_code=404, content=_error_content(request, str(exc)))


@app.exception_handler(ChronicleUserError)
def handle_user_error(request: Request, exc: ChronicleUserError) -> JSONResponse:
    """Map all Chronicle user errors to HTTP 400 by default."""
    return JSONResponse(status_code=400, content=_error_content(request, str(exc)))


@app.exception_handler(HTTPException)
def handle_http_error(request: Request, exc: HTTPException) -> JSONResponse:
    """Ensure FastAPI HTTP errors include request_id for traceability."""
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_content(request, exc.detail),
        headers=exc.headers,
    )


@app.exception_handler(Exception)
def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """Return a generic 500 with request_id while logging traceback server-side."""
    log.exception(
        "Unhandled Chronicle API exception request_id=%s", _request_id_for(request), exc_info=exc
    )
    return JSONResponse(status_code=500, content=_error_content(request, "Internal server error"))


@app.get("/verifier")
def verifier_page() -> FileResponse:
    """Serve the drag-and-drop .chronicle verifier page. No data is uploaded; verification runs in the browser."""
    path = _STATIC_DIR / "verifier.html"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Verifier page not found")
    return FileResponse(path, media_type="text/html")


# ----- Standalone score (no project path required) -----


@app.post("/score")
def score_defensibility(body: ScoreBody) -> dict[str, Any]:
    """Run defensibility scorer on (query, answer, evidence). No CHRONICLE_PROJECT_PATH required.

    Body: { "query", "answer", "evidence" } (evidence: array of strings or objects with
    "text" or "url"). Path-based evidence is not accepted. Returns same shape as eval contract.
    """
    result = run_scorer_contract(body.model_dump(), allow_path=False)
    if result.get("error") == "invalid_input":
        raise HTTPException(status_code=400, detail=result)
    return result


# ----- Investigations -----


@app.post("/investigations")
def create_investigation(request: Request, body: CreateInvestigationBody) -> dict[str, Any]:
    """Create an investigation. Returns event_id, investigation_uid."""
    actor_id, actor_type, verification_level = _get_actor(request)
    path = _get_project_path()
    with ChronicleSession(path) as session:
        event_id, inv_uid = session.create_investigation(
            body.title,
            description=body.description,
            investigation_key=body.investigation_key,
            actor_id=actor_id,
            actor_type=actor_type,
            verification_level=verification_level,
        )
        return {"event_id": event_id, "investigation_uid": inv_uid}


@app.get("/investigations")
def list_investigations(
    limit: int | None = None,
    cursor: str | None = None,
    is_archived: bool | None = None,
    created_since: str | None = None,
    created_before: str | None = None,
) -> dict[str, Any]:
    """List investigations (uid, title, etc.)."""
    effective_limit = _clamp_limit(limit, default=MAX_LIST_LIMIT)
    decoded_cursor = _decode_cursor(cursor)
    path = _get_project_path()
    with ChronicleSession(path) as session:
        invs = session.read_model.list_investigations_page(
            limit=effective_limit + 1,
            after_created_at=decoded_cursor[0] if decoded_cursor else None,
            after_investigation_uid=decoded_cursor[1] if decoded_cursor else None,
            is_archived=is_archived,
            created_since=created_since,
            created_before=created_before,
        )
        has_more = len(invs) > effective_limit
        page_items = invs[:effective_limit]
        next_cursor = (
            _encode_cursor(page_items[-1].created_at, page_items[-1].investigation_uid)
            if has_more and page_items
            else None
        )
        return {
            "investigations": [
                {
                    "investigation_uid": i.investigation_uid,
                    "title": i.title,
                    "description": i.description,
                    "is_archived": bool(i.is_archived),
                    "current_tier": i.current_tier,
                }
                for i in page_items
            ],
            "page": _page_meta(
                limit=effective_limit,
                has_more=has_more,
                next_cursor=next_cursor,
            ),
        }


@app.get("/investigations/{investigation_uid}")
def get_investigation(investigation_uid: str) -> dict[str, Any]:
    """Get a single investigation by uid. 404 if not found."""
    path = _get_project_path()
    with ChronicleSession(path) as session:
        inv = session.read_model.get_investigation(investigation_uid)
        if inv is None:
            raise HTTPException(status_code=404, detail="Investigation not found")
        return {
            "investigation_uid": inv.investigation_uid,
            "title": inv.title,
            "description": inv.description,
            "is_archived": bool(inv.is_archived),
            "current_tier": inv.current_tier,
            "tier_changed_at": getattr(inv, "tier_changed_at", None),
            "created_at": inv.created_at,
            "updated_at": getattr(inv, "updated_at", None),
        }


@app.get("/investigations/{investigation_uid}/policy-compatibility")
def get_policy_compatibility_preflight(
    investigation_uid: str,
    viewing_profile_id: str | None = None,
    built_under_profile_id: str | None = None,
    built_under_policy_version: str | None = None,
) -> dict[str, Any]:
    """Compare built-under policy vs viewing policy for an investigation."""
    path = _get_project_path()
    try:
        with ChronicleSession(path) as session:
            if session.read_model.get_investigation(investigation_uid) is None:
                raise HTTPException(status_code=404, detail="Investigation not found")
            return session.get_policy_compatibility_preflight(
                investigation_uid,
                viewing_profile_id=viewing_profile_id,
                built_under_profile_id=built_under_profile_id,
                built_under_policy_version=built_under_policy_version,
            )
    except ChronicleUserError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/investigations/{investigation_uid}/policy-sensitivity")
def get_policy_sensitivity_report(
    investigation_uid: str,
    profile_id: list[str] | None = None,
    built_under_profile_id: str | None = None,
    built_under_policy_version: str | None = None,
    limit_claims: int = 200,
) -> dict[str, Any]:
    """R2-01: Compare one investigation across selected policy profiles."""
    effective_claim_limit = _clamp_limit(limit_claims, default=200)
    path = _get_project_path()
    try:
        with ChronicleSession(path) as session:
            if session.read_model.get_investigation(investigation_uid) is None:
                raise HTTPException(status_code=404, detail="Investigation not found")
            return session.get_policy_sensitivity_report(
                investigation_uid,
                profile_ids=profile_id,
                built_under_profile_id=built_under_profile_id,
                built_under_policy_version=built_under_policy_version,
                limit_claims=effective_claim_limit,
            )
    except ChronicleUserError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/investigations/{investigation_uid}/reviewer-decision-ledger")
def get_reviewer_decision_ledger(
    investigation_uid: str,
    limit: int = 500,
) -> dict[str, Any]:
    """TE-04: Consolidated reviewer decision ledger and unresolved tensions snapshot."""
    effective_limit = _clamp_limit(limit, default=500)
    path = _get_project_path()
    try:
        with ChronicleSession(path) as session:
            if session.read_model.get_investigation(investigation_uid) is None:
                raise HTTPException(status_code=404, detail="Investigation not found")
            return session.get_reviewer_decision_ledger(investigation_uid, limit=effective_limit)
    except ChronicleUserError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/investigations/{investigation_uid}/review-packet")
def get_review_packet(
    investigation_uid: str,
    limit_claims: int = 200,
    decision_limit: int = 500,
    include_reasoning_briefs: bool = True,
    include_full_trail: bool = False,
    as_of_date: str | None = None,
    as_of_event_id: str | None = None,
    viewing_profile_id: str | None = None,
    built_under_profile_id: str | None = None,
    built_under_policy_version: str | None = None,
) -> dict[str, Any]:
    """TE-05: Build a unified review packet for legal/compliance/editorial handoff."""
    effective_claim_limit = _clamp_limit(limit_claims, default=200)
    effective_decision_limit = _clamp_limit(decision_limit, default=500)
    path = _get_project_path()
    try:
        with ChronicleSession(path) as session:
            if session.read_model.get_investigation(investigation_uid) is None:
                raise HTTPException(status_code=404, detail="Investigation not found")
            return session.get_review_packet(
                investigation_uid,
                limit_claims=effective_claim_limit,
                decision_limit=effective_decision_limit,
                include_reasoning_briefs=include_reasoning_briefs,
                include_full_trail=include_full_trail,
                as_of_date=as_of_date,
                as_of_event_id=as_of_event_id,
                viewing_profile_id=viewing_profile_id,
                built_under_profile_id=built_under_profile_id,
                built_under_policy_version=built_under_policy_version,
            )
    except ChronicleUserError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/investigations/{investigation_uid}/tier")
def set_investigation_tier(
    request: Request, investigation_uid: str, body: SetTierBody
) -> dict[str, Any]:
    """Set investigation tier (spark → forge → vault). Returns event_id. 400 if transition not allowed."""
    actor_id, actor_type, verification_level = _get_actor(request)
    path = _get_project_path()
    try:
        with ChronicleSession(path) as session:
            if session.read_model.get_investigation(investigation_uid) is None:
                raise HTTPException(status_code=404, detail="Investigation not found")
            event_id = session.set_tier(
                investigation_uid,
                body.tier.strip().lower(),
                reason=body.reason,
                actor_id=actor_id,
                actor_type=actor_type,
                verification_level=verification_level,
            )
            return {"event_id": event_id}
    except ChronicleUserError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/investigations/{investigation_uid}/tier-history")
def get_tier_history(
    investigation_uid: str,
    limit: int = 100,
) -> dict[str, Any]:
    """List tier transitions for an investigation, newest first."""
    path = _get_project_path()
    with ChronicleSession(path) as session:
        if session.read_model.get_investigation(investigation_uid) is None:
            raise HTTPException(status_code=404, detail="Investigation not found")
        entries = session.read_model.list_tier_history(investigation_uid, limit=limit)
        return {
            "tier_history": [
                {
                    "from_tier": e.from_tier,
                    "to_tier": e.to_tier,
                    "reason": e.reason,
                    "occurred_at": e.occurred_at,
                    "actor_id": e.actor_id,
                    "event_id": e.event_id,
                }
                for e in entries
            ]
        }


@app.get("/investigations/{investigation_uid}/tension-suggestions")
def list_tension_suggestions(
    investigation_uid: str,
    status: str | None = "pending",  # pending | confirmed | dismissed | None for all
    limit: int = 500,
    cursor: str | None = None,
) -> dict[str, Any]:
    """List tension suggestions for an investigation. Default status=pending for Propose–Confirm UI."""
    effective_limit = _clamp_limit(limit, default=500)
    decoded_cursor = _decode_cursor(cursor)
    path = _get_project_path()
    with ChronicleSession(path) as session:
        if session.read_model.get_investigation(investigation_uid) is None:
            raise HTTPException(status_code=404, detail="Investigation not found")
        suggestions = session.read_model.list_tension_suggestions_page(
            investigation_uid,
            status=status,
            limit=effective_limit + 1,
            after_created_at=decoded_cursor[0] if decoded_cursor else None,
            after_suggestion_uid=decoded_cursor[1] if decoded_cursor else None,
        )
        has_more = len(suggestions) > effective_limit
        page_items = suggestions[:effective_limit]
        next_cursor = (
            _encode_cursor(page_items[-1].created_at, page_items[-1].suggestion_uid)
            if has_more and page_items
            else None
        )
        return {
            "tension_suggestions": [
                {
                    "suggestion_uid": s.suggestion_uid,
                    "investigation_uid": s.investigation_uid,
                    "claim_a_uid": s.claim_a_uid,
                    "claim_b_uid": s.claim_b_uid,
                    "suggested_tension_kind": s.suggested_tension_kind,
                    "confidence": s.confidence,
                    "rationale": s.rationale,
                    "status": s.status,
                    "tool_module_id": s.tool_module_id,
                    "created_at": s.created_at,
                    "source_event_id": s.source_event_id,
                    "updated_at": s.updated_at,
                    "confirmed_tension_uid": s.confirmed_tension_uid,
                    "dismissed_at": s.dismissed_at,
                }
                for s in page_items
            ],
            "page": _page_meta(
                limit=effective_limit,
                has_more=has_more,
                next_cursor=next_cursor,
            ),
        }


@app.post("/investigations/{investigation_uid}/tension-suggestions/{suggestion_uid}/dismiss")
def dismiss_tension_suggestion(
    request: Request, investigation_uid: str, suggestion_uid: str
) -> dict[str, Any]:
    """Dismiss a tension suggestion. Returns event_id. 400 if suggestion not pending."""
    actor_id, actor_type, _ = _get_actor(request)
    path = _get_project_path()
    try:
        with ChronicleSession(path) as session:
            if session.read_model.get_investigation(investigation_uid) is None:
                raise HTTPException(status_code=404, detail="Investigation not found")
            event_id = session.dismiss_tension_suggestion(
                suggestion_uid,
                actor_id=actor_id,
                actor_type=actor_type,
            )
            return {"event_id": event_id}
    except ChronicleUserError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/investigations/{investigation_uid}/evidence")
def list_investigation_evidence(
    investigation_uid: str, limit: int = 2000, cursor: str | None = None
) -> dict[str, Any]:
    """List evidence items for an investigation. For Reference UI and vendors."""
    effective_limit = _clamp_limit(limit, default=2000)
    decoded_cursor = _decode_cursor(cursor)
    path = _get_project_path()
    with ChronicleSession(path) as session:
        if session.read_model.get_investigation(investigation_uid) is None:
            raise HTTPException(status_code=404, detail="Investigation not found")
        items = session.read_model.list_evidence_by_investigation_page(
            investigation_uid,
            limit=effective_limit + 1,
            after_created_at=decoded_cursor[0] if decoded_cursor else None,
            after_evidence_uid=decoded_cursor[1] if decoded_cursor else None,
        )
        has_more = len(items) > effective_limit
        page_items = items[:effective_limit]
        next_cursor = (
            _encode_cursor(page_items[-1].created_at, page_items[-1].evidence_uid)
            if has_more and page_items
            else None
        )
        return {
            "evidence": [
                {
                    "evidence_uid": e.evidence_uid,
                    "investigation_uid": e.investigation_uid,
                    "created_at": e.created_at,
                    "ingested_by_actor_id": e.ingested_by_actor_id,
                    "original_filename": e.original_filename,
                    "media_type": e.media_type,
                    "file_size_bytes": e.file_size_bytes,
                    "content_hash": e.content_hash,
                }
                for e in page_items
            ],
            "page": _page_meta(
                limit=effective_limit,
                has_more=has_more,
                next_cursor=next_cursor,
            ),
        }


@app.get("/investigations/{investigation_uid}/claims")
def list_investigation_claims(
    investigation_uid: str,
    include_withdrawn: bool = True,
    limit: int = 2000,
    cursor: str | None = None,
) -> dict[str, Any]:
    """List claims for an investigation. For Reference UI and vendors."""
    effective_limit = _clamp_limit(limit, default=2000)
    decoded_cursor = _decode_cursor(cursor)
    path = _get_project_path()
    with ChronicleSession(path) as session:
        if session.read_model.get_investigation(investigation_uid) is None:
            raise HTTPException(status_code=404, detail="Investigation not found")
        claims = session.read_model.list_claims_page(
            investigation_uid,
            include_withdrawn=include_withdrawn,
            limit=effective_limit + 1,
            before_updated_at=decoded_cursor[0] if decoded_cursor else None,
            before_claim_uid=decoded_cursor[1] if decoded_cursor else None,
        )
        has_more = len(claims) > effective_limit
        page_items = claims[:effective_limit]
        next_cursor = (
            _encode_cursor(page_items[-1].updated_at, page_items[-1].claim_uid)
            if has_more and page_items
            else None
        )
        return {
            "claims": [
                {
                    "claim_uid": c.claim_uid,
                    "investigation_uid": c.investigation_uid,
                    "claim_text": c.claim_text,
                    "claim_type": c.claim_type,
                    "current_status": c.current_status,
                    "created_at": c.created_at,
                    "updated_at": c.updated_at,
                    "notes": getattr(c, "notes", None),
                    "tags_json": getattr(c, "tags_json", None),
                    "epistemic_stance": getattr(c, "epistemic_stance", None),
                }
                for c in page_items
            ],
            "page": _page_meta(
                limit=effective_limit,
                has_more=has_more,
                next_cursor=next_cursor,
            ),
        }


@app.get("/investigations/{investigation_uid}/tensions")
def list_investigation_tensions(
    investigation_uid: str,
    status: str | None = None,
    limit: int = 500,
    cursor: str | None = None,
) -> dict[str, Any]:
    """List tensions for an investigation. For Reference UI and vendors."""
    effective_limit = _clamp_limit(limit, default=500)
    decoded_cursor = _decode_cursor(cursor)
    path = _get_project_path()
    with ChronicleSession(path) as session:
        if session.read_model.get_investigation(investigation_uid) is None:
            raise HTTPException(status_code=404, detail="Investigation not found")
        tensions = session.read_model.list_tensions_page(
            investigation_uid,
            status=status,
            limit=effective_limit + 1,
            before_created_at=decoded_cursor[0] if decoded_cursor else None,
            before_tension_uid=decoded_cursor[1] if decoded_cursor else None,
        )
        has_more = len(tensions) > effective_limit
        page_items = tensions[:effective_limit]
        next_cursor = (
            _encode_cursor(page_items[-1].created_at, page_items[-1].tension_uid)
            if has_more and page_items
            else None
        )
        return {
            "tensions": [
                {
                    "tension_uid": t.tension_uid,
                    "investigation_uid": t.investigation_uid,
                    "claim_a_uid": t.claim_a_uid,
                    "claim_b_uid": t.claim_b_uid,
                    "tension_kind": t.tension_kind,
                    "status": t.status,
                    "notes": t.notes,
                    "created_at": t.created_at,
                    "defeater_kind": getattr(t, "defeater_kind", None),
                }
                for t in page_items
            ],
            "page": _page_meta(
                limit=effective_limit,
                has_more=has_more,
                next_cursor=next_cursor,
            ),
        }


@app.get("/investigations/{investigation_uid}/graph")
def get_investigation_graph(
    investigation_uid: str,
    node_limit: int = 2000,
    edge_limit: int = 2000,
    edge_cursor: str | None = None,
) -> dict[str, Any]:
    """Return graph nodes and a paged edge list for visualization."""
    effective_node_limit = _clamp_limit(node_limit, default=2000)
    effective_edge_limit = _clamp_limit(edge_limit, default=2000)
    decoded_cursor = _decode_cursor(edge_cursor)
    path = _get_project_path()
    with ChronicleSession(path) as session:
        if session.read_model.get_investigation(investigation_uid) is None:
            raise HTTPException(status_code=404, detail="Investigation not found")
        claims = session.read_model.list_claims_by_type(
            investigation_uid=investigation_uid,
            limit=effective_node_limit,
        )
        evidence_items = session.read_model.list_evidence_by_investigation(
            investigation_uid,
            limit=effective_node_limit,
        )
        links = session.read_model.list_graph_links(
            investigation_uid,
            limit=effective_edge_limit + 1,
            after_created_at=decoded_cursor[0] if decoded_cursor else None,
            after_link_uid=decoded_cursor[1] if decoded_cursor else None,
        )
        has_more_edges = len(links) > effective_edge_limit
        page_links = links[:effective_edge_limit]
        next_edge_cursor = (
            _encode_cursor(page_links[-1].created_at, page_links[-1].link_uid)
            if has_more_edges and page_links
            else None
        )
        nodes: list[dict[str, Any]] = []
        for c in claims:
            nodes.append({"id": c.claim_uid, "type": "claim", "label": (c.claim_text or "")[:80]})
        for e in evidence_items:
            nodes.append(
                {
                    "id": e.evidence_uid,
                    "type": "evidence",
                    "label": e.original_filename or e.evidence_uid,
                }
            )
        edges: list[dict[str, Any]] = []
        for link in page_links:
            edges.append(
                {
                    "from": link.evidence_uid,
                    "to": link.claim_uid,
                    "link_type": "support" if link.link_type == "SUPPORTS" else "challenge",
                    "link_uid": link.link_uid,
                }
            )
        return {
            "nodes": nodes,
            "edges": edges,
            "edges_page": _page_meta(
                limit=effective_edge_limit,
                has_more=has_more_edges,
                next_cursor=next_edge_cursor,
            ),
        }


@app.get("/evidence/{evidence_uid}/spans")
def list_evidence_spans(evidence_uid: str, limit: int = 500) -> dict[str, Any]:
    """List spans for an evidence item (for linking support/challenge in UI)."""
    path = _get_project_path()
    with ChronicleSession(path) as session:
        item = session.read_model.get_evidence_item(evidence_uid)
        if item is None:
            raise HTTPException(status_code=404, detail="Evidence not found")
        spans = session.read_model.list_spans_for_evidence(evidence_uid, limit=limit)
        return {
            "spans": [
                {
                    "span_uid": s.span_uid,
                    "evidence_uid": s.evidence_uid,
                    "anchor_type": s.anchor_type,
                    "created_at": s.created_at,
                }
                for s in spans
            ]
        }


@app.get("/evidence/{evidence_uid}/content")
def get_evidence_content(evidence_uid: str) -> Response:
    """Return evidence file content. For text/* returns text/plain; else binary. 404 if not found."""
    path = _get_project_path()
    with ChronicleSession(path) as session:
        item = session.read_model.get_evidence_item(evidence_uid)
        if item is None:
            raise HTTPException(status_code=404, detail="Evidence not found")
        if not session.evidence.exists(item.uri):
            raise HTTPException(status_code=404, detail="Evidence file not found")
        blob = session.evidence.retrieve(item.uri)
        mt = (item.media_type or "application/octet-stream").split(";")[0].strip()
        if mt.startswith("text/"):
            return Response(
                content=blob.decode("utf-8", errors="replace"),
                media_type="text/plain; charset=utf-8",
            )
        return Response(
            content=blob,
            media_type=mt,
            headers={
                "Content-Disposition": f'inline; filename="{item.original_filename or evidence_uid}"'
            },
        )


class AnchorSpanBody(BaseModel):
    """Create a text_offset span (e.g. from selection)."""

    evidence_uid: str
    start_char: int
    end_char: int
    quote: str | None = None


# ----- Evidence -----


@app.post("/investigations/{investigation_uid}/evidence")
async def ingest_evidence(request: Request, investigation_uid: str) -> dict[str, Any]:
    """
    Ingest evidence. Send JSON body with content or content_base64, OR multipart form with file.
    Returns event_id, evidence_uid, span_uid (full-content span for linking).
    """
    blob = None
    original_filename = "evidence"
    media_type = "text/plain"
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        max_json_bytes = _max_json_payload_bytes(MAX_EVIDENCE_BYTES)
        if _content_length_exceeds(request, max_json_bytes):
            raise HTTPException(
                status_code=413,
                detail=f"Request body exceeds max size ({max_json_bytes} bytes)",
            )
        try:
            raw = await request.body()
            if len(raw) > max_json_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=f"Request body exceeds max size ({max_json_bytes} bytes)",
                )
            body = json.loads(raw)
            if not isinstance(body, dict):
                body = {}
        except json.JSONDecodeError:
            body = {}
        except UnicodeDecodeError:
            body = {}
        if body.get("content_base64"):
            try:
                blob = base64.b64decode(body["content_base64"], validate=True)
            except (ValueError, binascii.Error) as exc:
                raise HTTPException(
                    status_code=400, detail="Invalid content_base64 payload"
                ) from exc
        elif body.get("content") is not None:
            blob = (body["content"] or "").encode("utf-8")
        original_filename = body.get("original_filename") or "evidence"
        media_type = body.get("media_type") or "text/plain"
    elif "multipart/form-data" in content_type:
        if _content_length_exceeds(request, MAX_EVIDENCE_BYTES + (1024 * 1024)):
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds max size ({MAX_EVIDENCE_BYTES} bytes)",
            )
        form = await request.form()
        file = form.get("file")
        if file and isinstance(file, UploadFile) and file.filename:
            blob = await _read_upload_file_limited(file, MAX_EVIDENCE_BYTES)
            original_filename = file.filename
            media_type = file.content_type or "application/octet-stream"
    if blob is None:
        raise HTTPException(
            status_code=400,
            detail="Provide JSON body with content or content_base64, or multipart file",
        )
    if len(blob) > MAX_EVIDENCE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds max size ({MAX_EVIDENCE_BYTES} bytes)",
        )
    actor_id, actor_type, verification_level = _get_actor(request)
    path = _get_project_path()
    with ChronicleSession(path) as session:
        if session.read_model.get_investigation(investigation_uid) is None:
            raise HTTPException(status_code=404, detail="Investigation not found")
        event_id, ev_uid = session.ingest_evidence(
            investigation_uid,
            blob,
            media_type,
            original_filename=original_filename or "evidence",
            actor_id=actor_id,
            actor_type=actor_type,
            verification_level=verification_level,
        )
        text = blob.decode("utf-8", errors="replace")
        _, span_uid = session.anchor_span(
            investigation_uid,
            ev_uid,
            "text_offset",
            {"start_char": 0, "end_char": len(text)},
            quote=text[:2000] if len(text) > 2000 else text,
            actor_id=actor_id,
            actor_type=actor_type,
            verification_level=verification_level,
        )
        return {"event_id": event_id, "evidence_uid": ev_uid, "span_uid": span_uid}


@app.post("/investigations/{investigation_uid}/spans")
def create_span(request: Request, investigation_uid: str, body: AnchorSpanBody) -> dict[str, Any]:
    """Create a text_offset span (e.g. from selection in Reading UI). Returns event_id, span_uid."""
    actor_id, actor_type, verification_level = _get_actor(request)
    path = _get_project_path()
    try:
        with ChronicleSession(path) as session:
            if session.read_model.get_investigation(investigation_uid) is None:
                raise HTTPException(status_code=404, detail="Investigation not found")
            item = session.read_model.get_evidence_item(body.evidence_uid)
            if item is None or item.investigation_uid != investigation_uid:
                raise HTTPException(
                    status_code=404, detail="Evidence not found in this investigation"
                )
            event_id, span_uid = session.anchor_span(
                investigation_uid,
                body.evidence_uid,
                "text_offset",
                {"start_char": body.start_char, "end_char": body.end_char},
                quote=body.quote,
                actor_id=actor_id,
                actor_type=actor_type,
                verification_level=verification_level,
            )
            return {"event_id": event_id, "span_uid": span_uid}
    except ChronicleUserError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/investigations/{investigation_uid}/claims")
def propose_claim(
    request: Request, investigation_uid: str, body: ProposeClaimBody
) -> dict[str, Any]:
    """Propose a claim. Returns event_id, claim_uid."""
    actor_id, actor_type, verification_level = _get_actor(request)
    path = _get_project_path()
    with ChronicleSession(path) as session:
        if session.read_model.get_investigation(investigation_uid) is None:
            raise HTTPException(status_code=404, detail="Investigation not found")
        event_id, claim_uid = session.propose_claim(
            investigation_uid,
            body.text,
            initial_type=body.initial_type,
            epistemic_stance=body.epistemic_stance,
            actor_id=actor_id,
            actor_type=actor_type,
            verification_level=verification_level,
        )
        return {"event_id": event_id, "claim_uid": claim_uid}


# ----- Links -----


@app.post("/investigations/{investigation_uid}/links/support")
def link_support(request: Request, investigation_uid: str, body: LinkBody) -> dict[str, Any]:
    """Link a span as supporting a claim. Returns event_id, link_uid."""
    actor_id, actor_type, verification_level = _get_actor(request)
    path = _get_project_path()
    with ChronicleSession(path) as session:
        if session.read_model.get_investigation(investigation_uid) is None:
            raise HTTPException(status_code=404, detail="Investigation not found")
        event_id, link_uid = session.link_support(
            investigation_uid,
            body.span_uid,
            body.claim_uid,
            rationale=body.rationale,
            defeater_kind=body.defeater_kind,
            actor_id=actor_id,
            actor_type=actor_type,
            verification_level=verification_level,
        )
        return {"event_id": event_id, "link_uid": link_uid}


@app.post("/investigations/{investigation_uid}/links/challenge")
def link_challenge(request: Request, investigation_uid: str, body: LinkBody) -> dict[str, Any]:
    """Link a span as challenging a claim. Returns event_id, link_uid."""
    actor_id, actor_type, verification_level = _get_actor(request)
    path = _get_project_path()
    with ChronicleSession(path) as session:
        if session.read_model.get_investigation(investigation_uid) is None:
            raise HTTPException(status_code=404, detail="Investigation not found")
        event_id, link_uid = session.link_challenge(
            investigation_uid,
            body.span_uid,
            body.claim_uid,
            rationale=body.rationale,
            defeater_kind=body.defeater_kind,
            actor_id=actor_id,
            actor_type=actor_type,
            verification_level=verification_level,
        )
        return {"event_id": event_id, "link_uid": link_uid}


# ----- Tensions -----


@app.post("/investigations/{investigation_uid}/tensions")
def declare_tension(
    request: Request, investigation_uid: str, body: DeclareTensionBody
) -> dict[str, Any]:
    """Declare a tension between two claims. Returns event_id, tension_uid."""
    actor_id, actor_type, verification_level = _get_actor(request)
    path = _get_project_path()
    with ChronicleSession(path) as session:
        if session.read_model.get_investigation(investigation_uid) is None:
            raise HTTPException(status_code=404, detail="Investigation not found")
        event_id, tension_uid = session.declare_tension(
            investigation_uid,
            body.claim_a_uid,
            body.claim_b_uid,
            tension_kind=body.tension_kind,
            defeater_kind=body.defeater_kind,
            actor_id=actor_id,
            actor_type=actor_type,
            verification_level=verification_level,
        )
        return {"event_id": event_id, "tension_uid": tension_uid}


# ----- Read: claim, defensibility, reasoning brief -----


@app.get("/claims/{claim_uid}")
def get_claim(claim_uid: str) -> dict[str, Any]:
    """Get claim by uid. 404 if not found."""
    path = _get_project_path()
    with ChronicleSession(path) as session:
        claim = session.read_model.get_claim(claim_uid)
        if claim is None:
            raise HTTPException(status_code=404, detail="Claim not found")
        out: dict[str, Any] = {
            "claim_uid": claim.claim_uid,
            "investigation_uid": claim.investigation_uid,
            "claim_text": claim.claim_text,
            "claim_type": claim.claim_type,
            "current_status": claim.current_status,
            "created_at": claim.created_at,
            "updated_at": claim.updated_at,
            "notes": getattr(claim, "notes", None),
            "tags_json": getattr(claim, "tags_json", None),
        }
        if getattr(claim, "epistemic_stance", None) is not None:
            out["epistemic_stance"] = claim.epistemic_stance
        return out


@app.get("/claims/{claim_uid}/defensibility")
def get_defensibility(
    claim_uid: str,
    use_strength_weighting: bool = False,
) -> dict[str, Any]:
    """Get defensibility scorecard for a claim. Same shape as eval contract / defensibility schema.
    Includes sources_backing_claim (with independence_notes when present) so evaluators can interpret N independent sources. 404 if claim not found."""
    path = _get_project_path()
    with ChronicleSession(path) as session:
        claim = session.read_model.get_claim(claim_uid)
        if claim is None:
            raise HTTPException(status_code=404, detail="Claim not found")
        scorecard = session.get_defensibility_score(
            claim_uid, use_strength_weighting=use_strength_weighting
        )
        if scorecard is None:
            raise HTTPException(status_code=404, detail="Defensibility not available")
        out = asdict(scorecard)
        sources_backing = session.get_sources_backing_claim(claim_uid)
        if sources_backing:
            out["sources_backing_claim"] = sources_backing
        return out


@app.get("/claims/{claim_uid}/reasoning-brief")
def get_reasoning_brief(
    claim_uid: str,
    limit: int | None = None,
) -> dict[str, Any]:
    """Get reasoning brief (claim, defensibility, support/challenge, tensions, trail). 404 if claim not found."""
    path = _get_project_path()
    with ChronicleSession(path) as session:
        brief = session.get_reasoning_brief(claim_uid, limit=limit)
        if brief is None:
            raise HTTPException(status_code=404, detail="Claim not found")
        return brief


# ----- Export / Import -----


@app.post("/investigations/{investigation_uid}/export")
def export_investigation(investigation_uid: str) -> Response:
    """Export investigation as .chronicle (ZIP). Returns binary attachment."""
    path = _get_project_path()
    with tempfile.NamedTemporaryFile(suffix=".chronicle", delete=False) as f:
        out_path = Path(f.name)
    try:
        try:
            export_import_mod.export_investigation(path, investigation_uid, out_path)
        except ValueError as exc:
            if "No events found for investigation" in str(exc):
                raise HTTPException(status_code=404, detail="Investigation not found") from exc
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        body = out_path.read_bytes()
        return Response(
            content=body,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{investigation_uid}.chronicle"'
            },
        )
    finally:
        out_path.unlink(missing_ok=True)


@app.post("/investigations/{investigation_uid}/submission-package")
def export_submission_package(investigation_uid: str) -> Response:
    """Export a submission package: ZIP containing .chronicle, reasoning_briefs/ (HTML per claim), and manifest.json.
    For human handoff and verification. 404 if investigation not found."""
    path = _get_project_path()
    with ChronicleSession(path) as session:
        inv = session.read_model.get_investigation(investigation_uid)
        if inv is None:
            raise HTTPException(status_code=404, detail="Investigation not found")
        with tempfile.NamedTemporaryFile(suffix=".chronicle", delete=False) as f:
            chronicle_path = Path(f.name)
        try:
            session.export_investigation(investigation_uid, chronicle_path)
            chronicle_bytes = chronicle_path.read_bytes()
        finally:
            chronicle_path.unlink(missing_ok=True)

        claims = session.read_model.list_claims_by_type(
            investigation_uid=investigation_uid, limit=10_000
        )
        generated_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        manifest = {
            "investigation_uid": investigation_uid,
            "title": inv.title,
            "claim_uids": [c.claim_uid for c in claims],
            "generated_at": generated_at,
        }

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(f"{investigation_uid}.chronicle", chronicle_bytes)
            zf.writestr(
                "manifest.json",
                json.dumps(manifest, indent=2),
            )
            for c in claims:
                brief = session.get_reasoning_brief(c.claim_uid)
                if brief:
                    html = reasoning_brief_to_html(brief)
                    zf.writestr(
                        f"reasoning_briefs/{c.claim_uid}.html",
                        html.encode("utf-8"),
                    )

        buf.seek(0)
        return Response(
            content=buf.getvalue(),
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{investigation_uid}-submission.zip"'
            },
        )


@app.post("/import")
async def import_chronicle(request: Request, file: Annotated[UploadFile, File()]) -> dict[str, Any]:
    """Import a .chronicle file into the project. Accepts multipart file upload."""
    if not file.filename or not file.filename.endswith(".chronicle"):
        raise HTTPException(status_code=400, detail="File must have .chronicle extension")
    if _content_length_exceeds(request, MAX_IMPORT_BYTES + (1024 * 1024)):
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds max size ({MAX_IMPORT_BYTES} bytes)",
        )
    path = _get_project_path()
    chronicle_path = await _write_upload_file_limited(file, MAX_IMPORT_BYTES)
    try:
        try:
            export_import_mod.import_investigation(chronicle_path, path)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"status": "ok", "message": "Import completed"}
    finally:
        chronicle_path.unlink(missing_ok=True)


@app.get("/health")
def health() -> dict[str, str]:
    """Health check. Returns 503 if CHRONICLE_PROJECT_PATH is not set."""
    try:
        p = _get_project_path()
        return {"status": "ok", "project_path": str(p)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
