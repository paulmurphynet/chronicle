"""Service layer for Chronicle MCP tools."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from chronicle.core.errors import ChronicleUserError
from chronicle.store.project import create_project, project_exists
from chronicle.store.session import ChronicleSession


class ChronicleMcpService:
    """Project-scoped operations exposed by the MCP server."""

    def __init__(self, project_path: Path | str) -> None:
        self._project_path = Path(project_path).resolve()
        self._ensure_project_exists()

    def _ensure_project_exists(self) -> None:
        if not self._project_path.exists():
            self._project_path.mkdir(parents=True, exist_ok=True)
        if not project_exists(self._project_path):
            create_project(self._project_path)

    def create_investigation(
        self,
        *,
        title: str,
        description: str | None = None,
        investigation_key: str | None = None,
        actor_id: str = "mcp",
        actor_type: str = "tool",
    ) -> dict[str, str]:
        with ChronicleSession(self._project_path) as session:
            event_id, investigation_uid = session.create_investigation(
                title,
                description=description,
                investigation_key=investigation_key,
                actor_id=actor_id,
                actor_type=actor_type,
                workspace="spark",
            )
        return {"event_id": event_id, "investigation_uid": investigation_uid}

    def list_investigations(
        self,
        *,
        limit: int = 20,
        is_archived: bool | None = None,
    ) -> dict[str, Any]:
        with ChronicleSession(self._project_path) as session:
            rows = session.read_model.list_investigations(
                limit=max(1, min(limit, 200)),
                is_archived=is_archived,
            )
        return {"items": [asdict(row) for row in rows], "count": len(rows)}

    def ingest_evidence_text(
        self,
        *,
        investigation_uid: str,
        text: str,
        original_filename: str = "evidence.txt",
        media_type: str = "text/plain",
        provenance_type: str | None = None,
        actor_id: str = "mcp",
        actor_type: str = "tool",
    ) -> dict[str, str]:
        body = text.strip()
        if not body:
            raise ChronicleUserError("text must be non-empty")
        with ChronicleSession(self._project_path) as session:
            ingest_event_id, evidence_uid = session.ingest_evidence(
                investigation_uid,
                body.encode("utf-8"),
                media_type,
                original_filename=original_filename,
                provenance_type=provenance_type,
                actor_id=actor_id,
                actor_type=actor_type,
                workspace="spark",
            )
            anchor_event_id, span_uid = session.anchor_span(
                investigation_uid,
                evidence_uid,
                "text_offset",
                {"start_char": 0, "end_char": len(body)},
                quote=body[:2000],
                actor_id=actor_id,
                actor_type=actor_type,
                workspace="spark",
            )
        return {
            "ingest_event_id": ingest_event_id,
            "anchor_event_id": anchor_event_id,
            "evidence_uid": evidence_uid,
            "span_uid": span_uid,
        }

    def propose_claim(
        self,
        *,
        investigation_uid: str,
        claim_text: str,
        initial_type: str | None = None,
        actor_id: str = "mcp",
        actor_type: str = "tool",
    ) -> dict[str, str]:
        with ChronicleSession(self._project_path) as session:
            event_id, claim_uid = session.propose_claim(
                investigation_uid,
                claim_text,
                initial_type=initial_type,
                actor_id=actor_id,
                actor_type=actor_type,
                workspace="spark",
            )
        return {"event_id": event_id, "claim_uid": claim_uid}

    def list_claims(
        self,
        *,
        investigation_uid: str,
        include_withdrawn: bool = True,
        limit: int = 50,
    ) -> dict[str, Any]:
        with ChronicleSession(self._project_path) as session:
            rows = session.read_model.list_claims_by_type(
                investigation_uid=investigation_uid,
                include_withdrawn=include_withdrawn,
                limit=max(1, min(limit, 500)),
            )
        return {"items": [asdict(row) for row in rows], "count": len(rows)}

    def link_support(
        self,
        *,
        investigation_uid: str,
        span_uid: str,
        claim_uid: str,
        rationale: str | None = None,
        actor_id: str = "mcp",
        actor_type: str = "tool",
    ) -> dict[str, str]:
        with ChronicleSession(self._project_path) as session:
            event_id, link_uid = session.link_support(
                investigation_uid,
                span_uid,
                claim_uid,
                rationale=rationale,
                actor_id=actor_id,
                actor_type=actor_type,
                workspace="spark",
            )
        return {"event_id": event_id, "link_uid": link_uid}

    def link_challenge(
        self,
        *,
        investigation_uid: str,
        span_uid: str,
        claim_uid: str,
        rationale: str | None = None,
        defeater_kind: str | None = None,
        actor_id: str = "mcp",
        actor_type: str = "tool",
    ) -> dict[str, str]:
        with ChronicleSession(self._project_path) as session:
            event_id, link_uid = session.link_challenge(
                investigation_uid,
                span_uid,
                claim_uid,
                rationale=rationale,
                defeater_kind=defeater_kind,
                actor_id=actor_id,
                actor_type=actor_type,
                workspace="spark",
            )
        return {"event_id": event_id, "link_uid": link_uid}

    def get_defensibility(self, *, claim_uid: str) -> dict[str, Any] | None:
        with ChronicleSession(self._project_path) as session:
            scorecard = session.get_defensibility_score(claim_uid)
        if scorecard is None:
            return None
        return asdict(scorecard)

    def get_reasoning_brief(
        self,
        *,
        claim_uid: str,
        limit: int = 200,
    ) -> dict[str, Any] | None:
        with ChronicleSession(self._project_path) as session:
            return session.get_reasoning_brief(claim_uid, limit=max(1, min(limit, 5000)))

    def export_investigation(
        self,
        *,
        investigation_uid: str,
        output_path: str,
    ) -> dict[str, Any]:
        target = Path(output_path)
        if not target.is_absolute():
            target = self._project_path / target
        target = target.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        with ChronicleSession(self._project_path) as session:
            session.export_investigation(investigation_uid, target)
        return {"output_path": str(target), "size_bytes": target.stat().st_size}
