"""LangChain callback handler: write retriever outputs and chain outputs to Chronicle.

Requires: pip install chronicle-standard langchain-core (or langchain).

Use with a LangChain RAG chain by adding the handler to the callbacks list.
On retriever end, retrieved documents are ingested as evidence; on chain end,
the chain output is proposed as a claim and linked to that evidence.
"""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Any, cast

try:
    from langchain_core.callbacks import BaseCallbackHandler
    from langchain_core.documents import Document

    _LANGCHAIN_AVAILABLE = True
except ImportError:
    BaseCallbackHandler = object  # type: ignore[misc, assignment]
    Document = None  # type: ignore[assignment, misc]
    _LANGCHAIN_AVAILABLE = False


def _doc_text(doc: Any) -> str:
    """Extract text from a LangChain Document or similar."""
    if hasattr(doc, "page_content"):
        return cast(
            str,
            (doc.page_content or "")
            if isinstance(doc.page_content, str)
            else str(doc.page_content),
        )
    if isinstance(doc, dict):
        return doc.get("page_content", doc.get("content", "")) or ""
    return str(doc)


def _output_text(outputs: dict[str, Any] | Any) -> str:
    """Extract answer text from a chain outputs dict or raw value."""
    if outputs is None:
        return ""
    if isinstance(outputs, str):
        return outputs
    if not isinstance(outputs, dict):
        if hasattr(outputs, "content"):
            return getattr(outputs, "content", "") or ""
        return str(outputs)
    if not outputs:
        return ""
    # Common keys for RAG chain output
    for key in ("answer", "result", "output", "response", "text", "content"):
        val = outputs.get(key)
        if val is not None and isinstance(val, str):
            return cast(str, val)
    # Single value
    if len(outputs) == 1:
        v = next(iter(outputs.values()))
        if isinstance(v, str):
            return v
        if hasattr(v, "content"):
            return cast(str, getattr(v, "content", "") or "")
    return str(outputs)


class ChronicleCallbackHandler(BaseCallbackHandler):  # type: ignore[misc]
    """LangChain callback handler that writes retriever and chain outputs to Chronicle.

    On retriever end: ingested documents are stored as evidence and spans.
    On chain end (root chain only): the output is proposed as a claim and linked to that evidence.

    Config:
        project_path: Chronicle project directory (must exist or be creatable; in-process only).
        investigation_uid: Use this investigation, or None to create one using investigation_title.
        investigation_title: Title when creating an investigation (default "LangChain RAG").
        actor_id: Actor identifier (default "langchain").
        actor_type: Actor type (default "tool").
        workspace: Chronicle workspace (default "spark").
    """

    def __init__(
        self,
        project_path: Path | str,
        *,
        investigation_uid: str | None = None,
        investigation_key: str | None = None,
        investigation_title: str = "LangChain RAG",
        actor_id: str = "langchain",
        actor_type: str = "tool",
        workspace: str = "spark",
    ) -> None:
        if not _LANGCHAIN_AVAILABLE:
            raise ImportError(
                "Chronicle LangChain integration requires langchain-core. "
                "Install with: pip install chronicle-standard langchain-core"
            ) from None
        super().__init__()
        self._project_path = Path(project_path)
        self._investigation_uid = investigation_uid
        self._investigation_key = (investigation_key or "").strip() or None
        self._investigation_title = investigation_title
        self._actor_id = actor_id
        self._actor_type = actor_type
        self._workspace = workspace
        self._session: Any = None
        self._pending_spans: list[tuple[str, str]] = []  # (evidence_uid, span_uid)

    def _get_session(self) -> Any:
        """Lazy init ChronicleSession (in-process)."""
        if self._session is None:
            from chronicle.store.project import create_project
            from chronicle.store.session import ChronicleSession

            if not (self._project_path / "chronicle.db").exists():
                create_project(self._project_path)
            self._session = ChronicleSession(self._project_path)
        return self._session

    def _ensure_investigation(self) -> str:
        """Ensure we have an investigation UID; create one if not set. When investigation_key is set, same key returns same investigation (get-or-create)."""
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

    def on_chain_start(
        self,
        serialized: dict[str, Any],
        inputs: dict[str, Any],
        *,
        run_id: Any = None,
        parent_run_id: Any = None,
        **kwargs: Any,
    ) -> None:
        """Clear pending evidence at the start of a root chain (new query)."""
        if parent_run_id is None:
            self._pending_spans = []

    def on_retriever_end(
        self,
        documents: Any,
        *,
        run_id: Any = None,
        parent_run_id: Any = None,
        **kwargs: Any,
    ) -> None:
        """Ingest retrieved documents as evidence and store span UIDs for linking."""
        inv_uid = self._ensure_investigation()
        sess = self._get_session()
        doc_list = documents if isinstance(documents, list) else [documents]
        for i, doc in enumerate(doc_list):
            text = _doc_text(doc)
            if not text.strip():
                continue
            try:
                blob = text.encode("utf-8")
                _, ev_uid = sess.ingest_evidence(
                    inv_uid,
                    blob,
                    "text/plain",
                    original_filename=f"retrieved_{i}.txt",
                    actor_id=self._actor_id,
                    actor_type=self._actor_type,
                    workspace=self._workspace,
                )
                _, span_uid = sess.anchor_span(
                    inv_uid,
                    ev_uid,
                    "text_offset",
                    {"start_char": 0, "end_char": len(text)},
                    quote=text[:2000] if len(text) > 2000 else text,
                    actor_id=self._actor_id,
                    actor_type=self._actor_type,
                    workspace=self._workspace,
                )
                self._pending_spans.append((ev_uid, span_uid))
            except Exception:
                continue

    def on_chain_end(
        self,
        outputs: dict[str, Any],
        *,
        run_id: Any = None,
        parent_run_id: Any = None,
        **kwargs: Any,
    ) -> None:
        """Propose chain output as claim and link pending evidence (root chain only)."""
        if parent_run_id is not None:
            return
        response_text = _output_text(outputs)
        if not response_text.strip():
            return
        inv_uid = self._ensure_investigation()
        sess = self._get_session()
        try:
            _, claim_uid = sess.propose_claim(
                inv_uid,
                response_text[:50000],
                actor_id=self._actor_id,
                actor_type=self._actor_type,
                workspace=self._workspace,
            )
            for _ev_uid, span_uid in self._pending_spans:
                with contextlib.suppress(Exception):
                    sess.link_support(
                        inv_uid,
                        span_uid,
                        claim_uid,
                        actor_id=self._actor_id,
                        actor_type=self._actor_type,
                        workspace=self._workspace,
                    )
            self._pending_spans = []
        except Exception:
            pass
