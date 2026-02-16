"""Haystack component: write pipeline documents to Chronicle as evidence (and optionally as a claim with support).

Requires: pip install chronicle-standard haystack-ai.

Add ChronicleEvidenceWriter to your pipeline after a retriever or generator; connect
documents (and optionally claim_text from a generator). Documents are ingested as
evidence; if claim_text is provided, it is proposed as a claim and linked to that evidence.
"""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Any, cast

try:
    from haystack import component
    from haystack.dataclasses import Document

    _HAYSTACK_AVAILABLE = True
except ImportError:
    component = None  # type: ignore[assignment]
    Document = None  # type: ignore[assignment, misc]
    _HAYSTACK_AVAILABLE = False


def _document_text(doc: Any) -> str:
    """Extract text from a Haystack Document (content or blob)."""
    if hasattr(doc, "content") and doc.content is not None and isinstance(doc.content, str):
        return cast(str, doc.content)
    if hasattr(doc, "blob") and doc.blob is not None:
        blob = doc.blob
        if hasattr(blob, "data"):
            data = blob.data
            if isinstance(data, bytes):
                return cast(str, data.decode("utf-8", errors="replace"))
        return str(blob)
    if isinstance(doc, dict):
        return doc.get("content", doc.get("text", "")) or ""
    return str(doc)


def _create_component_class() -> type:
    """Build the component class only when Haystack is available."""

    @component
    class ChronicleEvidenceWriter:
        """Haystack component: write documents to Chronicle as evidence; optionally propose claim and link support.

        Inputs:
            documents: List of Haystack Documents to ingest as evidence.
            claim_text: Optional. If set, proposed as a claim and all evidence from this batch is linked as support.

        Outputs:
            documents: The same documents (pass-through) so the pipeline can continue.

        Config (constructor):
            project_path: Chronicle project directory (must exist or be creatable). In-process only.
            investigation_uid: Use this investigation, or None to create one using investigation_title.
            investigation_title: Title when creating an investigation (default "Haystack RAG").
            actor_id: Actor identifier (default "haystack").
            actor_type: Actor type (default "tool").
            workspace: Chronicle workspace (default "spark").
        """

        @component.output_types(documents=list)
        def run(
            self,
            documents: list,
            claim_text: str | None = None,
        ) -> dict[str, list]:
            if not _HAYSTACK_AVAILABLE:
                raise ImportError(
                    "Chronicle Haystack integration requires haystack-ai. "
                    "Install with: pip install chronicle-standard haystack-ai"
                ) from None
            doc_list = list(documents) if documents else []
            if not doc_list:
                return {"documents": doc_list}

            session = self._get_session()
            inv_uid = self._ensure_investigation()
            pending_spans: list[tuple[str, str]] = []

            for i, doc in enumerate(doc_list):
                text = _document_text(doc)
                if not text.strip():
                    continue
                try:
                    blob = text.encode("utf-8")
                    _, ev_uid = session.ingest_evidence(
                        inv_uid,
                        blob,
                        "text/plain",
                        original_filename=f"haystack_doc_{i}.txt",
                        actor_id=self._actor_id,
                        actor_type=self._actor_type,
                        workspace=self._workspace,
                    )
                    _, span_uid = session.anchor_span(
                        inv_uid,
                        ev_uid,
                        "text_offset",
                        {"start_char": 0, "end_char": len(text)},
                        quote=text[:2000] if len(text) > 2000 else text,
                        actor_id=self._actor_id,
                        actor_type=self._actor_type,
                        workspace=self._workspace,
                    )
                    pending_spans.append((ev_uid, span_uid))
                except Exception:
                    continue

            if claim_text and claim_text.strip() and pending_spans:
                with contextlib.suppress(Exception):
                    _, claim_uid = session.propose_claim(
                        inv_uid,
                        claim_text[:50000],
                        actor_id=self._actor_id,
                        actor_type=self._actor_type,
                        workspace=self._workspace,
                    )
                    for _ev_uid, span_uid in pending_spans:
                        with contextlib.suppress(Exception):
                            session.link_support(
                                inv_uid,
                                span_uid,
                                claim_uid,
                                actor_id=self._actor_id,
                                actor_type=self._actor_type,
                                workspace=self._workspace,
                            )

            return {"documents": doc_list}

        def __init__(
            self,
            project_path: Path | str,
            *,
            investigation_uid: str | None = None,
            investigation_key: str | None = None,
            investigation_title: str = "Haystack RAG",
            actor_id: str = "haystack",
            actor_type: str = "tool",
            workspace: str = "spark",
        ) -> None:
            if not _HAYSTACK_AVAILABLE:
                raise ImportError(
                    "Chronicle Haystack integration requires haystack-ai. "
                    "Install with: pip install chronicle-standard haystack-ai"
                ) from None
            self._project_path = Path(project_path)
            self._investigation_uid = investigation_uid
            self._investigation_key = (investigation_key or "").strip() or None
            self._investigation_title = investigation_title
            self._actor_id = actor_id
            self._actor_type = actor_type
            self._workspace = workspace
            self._session: Any = None

        def _get_session(self) -> Any:
            from chronicle.store.project import create_project
            from chronicle.store.session import ChronicleSession

            if self._session is None:
                if not (self._project_path / "chronicle.db").exists():
                    create_project(self._project_path)
                self._session = ChronicleSession(self._project_path)
            return self._session

        def _ensure_investigation(self) -> str:
            """When investigation_key is set, same key returns same investigation (get-or-create)."""
            if self._investigation_uid:
                return self._investigation_uid
            sess = self._get_session()
            _, inv_uid = sess.create_investigation(
                self._investigation_title,
                actor_id=self._actor_id,
                actor_type=self._actor_type,
                workspace=self._workspace,
                investigation_key=self._investigation_key,
            )
            self._investigation_uid = inv_uid
            return cast(str, inv_uid)

    return ChronicleEvidenceWriter


ChronicleEvidenceWriter = _create_component_class() if _HAYSTACK_AVAILABLE else None  # type: ignore[assignment]
