"""
Minimal HTTP API for Chronicle. Requires [api] extra: pip install -e ".[api]".

Set CHRONICLE_PROJECT_PATH to the project directory (must exist and contain chronicle.db,
or the path will be created and initialized on first write). No auth in this minimal version;
run behind your own auth/proxy in production.

Run: uvicorn chronicle.api.app:app --reload
"""

from __future__ import annotations

import base64
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
from chronicle.scorer_contract import run_scorer_contract
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
    rationale: str | None = None  # Optional: why this evidence supports/challenges this claim (warrant)
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
def handle_project_not_found(
    request: Request, exc: ChronicleProjectNotFoundError
) -> JSONResponse:
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
    log.exception("Unhandled Chronicle API exception request_id=%s", _request_id_for(request), exc_info=exc)
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
    is_archived: bool | None = None,
    created_since: str | None = None,
    created_before: str | None = None,
) -> dict[str, Any]:
    """List investigations (uid, title, etc.)."""
    path = _get_project_path()
    with ChronicleSession(path) as session:
        invs = session.read_model.list_investigations(
            limit=limit,
            is_archived=is_archived,
            created_since=created_since,
            created_before=created_before,
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
                for i in invs
            ]
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
) -> dict[str, Any]:
    """List tension suggestions for an investigation. Default status=pending for Propose–Confirm UI."""
    path = _get_project_path()
    with ChronicleSession(path) as session:
        if session.read_model.get_investigation(investigation_uid) is None:
            raise HTTPException(status_code=404, detail="Investigation not found")
        suggestions = session.read_model.list_tension_suggestions(
            investigation_uid, status=status, limit=limit
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
                for s in suggestions
            ]
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
def list_investigation_evidence(investigation_uid: str, limit: int = 2000) -> dict[str, Any]:
    """List evidence items for an investigation. For Reference UI and vendors."""
    path = _get_project_path()
    with ChronicleSession(path) as session:
        if session.read_model.get_investigation(investigation_uid) is None:
            raise HTTPException(status_code=404, detail="Investigation not found")
        items = session.read_model.list_evidence_by_investigation(
            investigation_uid, limit=limit
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
                for e in items
            ]
        }


@app.get("/investigations/{investigation_uid}/claims")
def list_investigation_claims(
    investigation_uid: str, include_withdrawn: bool = True, limit: int = 2000
) -> dict[str, Any]:
    """List claims for an investigation. For Reference UI and vendors."""
    path = _get_project_path()
    with ChronicleSession(path) as session:
        if session.read_model.get_investigation(investigation_uid) is None:
            raise HTTPException(status_code=404, detail="Investigation not found")
        claims = session.read_model.list_claims_by_type(
            investigation_uid=investigation_uid,
            include_withdrawn=include_withdrawn,
            limit=limit,
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
                for c in claims
            ]
        }


@app.get("/investigations/{investigation_uid}/tensions")
def list_investigation_tensions(
    investigation_uid: str, status: str | None = None, limit: int = 500
) -> dict[str, Any]:
    """List tensions for an investigation. For Reference UI and vendors."""
    path = _get_project_path()
    with ChronicleSession(path) as session:
        if session.read_model.get_investigation(investigation_uid) is None:
            raise HTTPException(status_code=404, detail="Investigation not found")
        tensions = session.read_model.list_tensions(
            investigation_uid, status=status, limit=limit
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
                for t in tensions
            ]
        }


@app.get("/investigations/{investigation_uid}/graph")
def get_investigation_graph(investigation_uid: str) -> dict[str, Any]:
    """Return nodes (claims, evidence) and edges (support/challenge) for graph visualization."""
    path = _get_project_path()
    with ChronicleSession(path) as session:
        if session.read_model.get_investigation(investigation_uid) is None:
            raise HTTPException(status_code=404, detail="Investigation not found")
        claims = session.read_model.list_claims_by_type(
            investigation_uid=investigation_uid, limit=2000
        )
        evidence_items = session.read_model.list_evidence_by_investigation(
            investigation_uid, limit=2000
        )
        nodes: list[dict[str, Any]] = []
        for c in claims:
            nodes.append(
                {"id": c.claim_uid, "type": "claim", "label": (c.claim_text or "")[:80]}
            )
        for e in evidence_items:
            nodes.append(
                {
                    "id": e.evidence_uid,
                    "type": "evidence",
                    "label": e.original_filename or e.evidence_uid,
                }
            )
        edges: list[dict[str, Any]] = []
        for c in claims:
            for link in session.read_model.get_support_for_claim(c.claim_uid):
                span = session.read_model.get_evidence_span(link.span_uid)
                if span:
                    edges.append(
                        {
                            "from": span.evidence_uid,
                            "to": c.claim_uid,
                            "link_type": "support",
                            "link_uid": link.link_uid,
                        }
                    )
            for link in session.read_model.get_challenges_for_claim(c.claim_uid):
                span = session.read_model.get_evidence_span(link.span_uid)
                if span:
                    edges.append(
                        {
                            "from": span.evidence_uid,
                            "to": c.claim_uid,
                            "link_type": "challenge",
                            "link_uid": link.link_uid,
                        }
                    )
        return {"nodes": nodes, "edges": edges}


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
            headers={"Content-Disposition": f'inline; filename="{item.original_filename or evidence_uid}"'},
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
        try:
            body = await request.json()
        except Exception:
            body = {}
        if body.get("content_base64"):
            blob = base64.b64decode(body["content_base64"])
        elif body.get("content") is not None:
            blob = (body["content"] or "").encode("utf-8")
        original_filename = body.get("original_filename") or "evidence"
        media_type = body.get("media_type") or "text/plain"
    elif "multipart/form-data" in content_type:
        form = await request.form()
        file = form.get("file")
        if file and isinstance(file, UploadFile) and file.filename:
            blob = await file.read()
            original_filename = file.filename
            media_type = file.content_type or "application/octet-stream"
    if blob is None:
        raise HTTPException(
            status_code=400,
            detail="Provide JSON body with content or content_base64, or multipart file",
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
def create_span(
    request: Request, investigation_uid: str, body: AnchorSpanBody
) -> dict[str, Any]:
    """Create a text_offset span (e.g. from selection in Reading UI). Returns event_id, span_uid."""
    actor_id, actor_type, verification_level = _get_actor(request)
    path = _get_project_path()
    try:
        with ChronicleSession(path) as session:
            if session.read_model.get_investigation(investigation_uid) is None:
                raise HTTPException(status_code=404, detail="Investigation not found")
            item = session.read_model.get_evidence_item(body.evidence_uid)
            if item is None or item.investigation_uid != investigation_uid:
                raise HTTPException(status_code=404, detail="Evidence not found in this investigation")
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
    with ChronicleSession(path) as session:
        if session.read_model.get_investigation(investigation_uid) is None:
            raise HTTPException(status_code=404, detail="Investigation not found")
        with tempfile.NamedTemporaryFile(suffix=".chronicle", delete=False) as f:
            out_path = Path(f.name)
        try:
            session.export_investigation(investigation_uid, out_path)
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
async def import_chronicle(file: Annotated[UploadFile, File()]) -> dict[str, Any]:
    """Import a .chronicle file into the project. Accepts multipart file upload."""
    if not file.filename or not file.filename.endswith(".chronicle"):
        raise HTTPException(status_code=400, detail="File must have .chronicle extension")
    path = _get_project_path()
    content = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".chronicle", delete=False) as f:
        f.write(content)
        chronicle_path = Path(f.name)
    try:
        with ChronicleSession(path) as session:
            session.import_investigation(chronicle_path)
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
