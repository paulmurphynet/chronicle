"""
Minimal HTTP API for Chronicle. Requires [api] extra: pip install -e ".[api]".

Set CHRONICLE_PROJECT_PATH to the project directory (must exist and contain chronicle.db,
or the path will be created and initialized on first write). No auth in this minimal version;
run behind your own auth/proxy in production.

Run: uvicorn chronicle.api.app:app --reload
"""

from __future__ import annotations

import base64
import os
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from chronicle.store.project import create_project, project_exists
from chronicle.store.session import ChronicleSession

# Project path from env; None if not set
PROJECT_PATH_ENV = "CHRONICLE_PROJECT_PATH"


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


class LinkBody(BaseModel):
    span_uid: str
    claim_uid: str


class DeclareTensionBody(BaseModel):
    claim_a_uid: str
    claim_b_uid: str
    tension_kind: str = "contradiction"


app = FastAPI(
    title="Chronicle API",
    description="Minimal HTTP API for evidence, claims, defensibility, and export/import. Same shapes as eval contract and defensibility schema.",
    version="0.1.0",
)

# Static files (e.g. web verifier)
_STATIC_DIR = Path(__file__).resolve().parent / "static"
if _STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


@app.get("/verifier")
def verifier_page() -> FileResponse:
    """Serve the drag-and-drop .chronicle verifier page. No data is uploaded; verification runs in the browser."""
    path = _STATIC_DIR / "verifier.html"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Verifier page not found")
    return FileResponse(path, media_type="text/html")


# ----- Investigations -----


@app.post("/investigations")
def create_investigation(body: CreateInvestigationBody) -> dict[str, Any]:
    """Create an investigation. Returns event_id, investigation_uid."""
    path = _get_project_path()
    with ChronicleSession(path) as session:
        event_id, inv_uid = session.create_investigation(
            body.title,
            description=body.description,
            investigation_key=body.investigation_key,
            actor_id="api",
            actor_type="tool",
        )
        return {"event_id": event_id, "investigation_uid": inv_uid}


@app.get("/investigations")
def list_investigations() -> dict[str, Any]:
    """List investigations (uid, title, etc.)."""
    path = _get_project_path()
    with ChronicleSession(path) as session:
        invs = session.read_model.list_investigations()
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
    path = _get_project_path()
    with ChronicleSession(path) as session:
        if session.read_model.get_investigation(investigation_uid) is None:
            raise HTTPException(status_code=404, detail="Investigation not found")
        event_id, ev_uid = session.ingest_evidence(
            investigation_uid,
            blob,
            media_type,
            original_filename=original_filename or "evidence",
            actor_id="api",
            actor_type="tool",
        )
        text = blob.decode("utf-8", errors="replace")
        _, span_uid = session.anchor_span(
            investigation_uid,
            ev_uid,
            "text_offset",
            {"start_char": 0, "end_char": len(text)},
            quote=text[:2000] if len(text) > 2000 else text,
            actor_id="api",
            actor_type="tool",
        )
        return {"event_id": event_id, "evidence_uid": ev_uid, "span_uid": span_uid}


# ----- Claims -----


@app.post("/investigations/{investigation_uid}/claims")
def propose_claim(investigation_uid: str, body: ProposeClaimBody) -> dict[str, Any]:
    """Propose a claim. Returns event_id, claim_uid."""
    path = _get_project_path()
    with ChronicleSession(path) as session:
        if session.read_model.get_investigation(investigation_uid) is None:
            raise HTTPException(status_code=404, detail="Investigation not found")
        event_id, claim_uid = session.propose_claim(
            investigation_uid,
            body.text,
            initial_type=body.initial_type,
            actor_id="api",
            actor_type="tool",
        )
        return {"event_id": event_id, "claim_uid": claim_uid}


# ----- Links -----


@app.post("/investigations/{investigation_uid}/links/support")
def link_support(investigation_uid: str, body: LinkBody) -> dict[str, Any]:
    """Link a span as supporting a claim. Returns event_id, link_uid."""
    path = _get_project_path()
    with ChronicleSession(path) as session:
        if session.read_model.get_investigation(investigation_uid) is None:
            raise HTTPException(status_code=404, detail="Investigation not found")
        event_id, link_uid = session.link_support(
            investigation_uid,
            body.span_uid,
            body.claim_uid,
            actor_id="api",
            actor_type="tool",
        )
        return {"event_id": event_id, "link_uid": link_uid}


@app.post("/investigations/{investigation_uid}/links/challenge")
def link_challenge(investigation_uid: str, body: LinkBody) -> dict[str, Any]:
    """Link a span as challenging a claim. Returns event_id, link_uid."""
    path = _get_project_path()
    with ChronicleSession(path) as session:
        if session.read_model.get_investigation(investigation_uid) is None:
            raise HTTPException(status_code=404, detail="Investigation not found")
        event_id, link_uid = session.link_challenge(
            investigation_uid,
            body.span_uid,
            body.claim_uid,
            actor_id="api",
            actor_type="tool",
        )
        return {"event_id": event_id, "link_uid": link_uid}


# ----- Tensions -----


@app.post("/investigations/{investigation_uid}/tensions")
def declare_tension(investigation_uid: str, body: DeclareTensionBody) -> dict[str, Any]:
    """Declare a tension between two claims. Returns event_id, tension_uid."""
    path = _get_project_path()
    with ChronicleSession(path) as session:
        if session.read_model.get_investigation(investigation_uid) is None:
            raise HTTPException(status_code=404, detail="Investigation not found")
        event_id, tension_uid = session.declare_tension(
            investigation_uid,
            body.claim_a_uid,
            body.claim_b_uid,
            tension_kind=body.tension_kind,
            actor_id="api",
            actor_type="tool",
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
        return {
            "claim_uid": claim.claim_uid,
            "investigation_uid": claim.investigation_uid,
            "claim_text": claim.claim_text,
            "claim_type": claim.claim_type,
            "current_status": claim.current_status,
            "created_at": claim.created_at,
            "updated_at": claim.updated_at,
        }


@app.get("/claims/{claim_uid}/defensibility")
def get_defensibility(
    claim_uid: str,
    use_strength_weighting: bool = False,
) -> dict[str, Any]:
    """Get defensibility scorecard for a claim. Same shape as eval contract / defensibility schema. 404 if claim not found."""
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
        return asdict(scorecard)


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


@app.post("/import")
async def import_chronicle(file: UploadFile = File(...)) -> dict[str, Any]:
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
        raise HTTPException(status_code=503, detail=str(e))
