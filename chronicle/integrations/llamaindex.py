"""LlamaIndex callback handler: write retrievals and synthesized answers to Chronicle.

Requires: pip install chronicle-standard llama-index-core (or llama-index).

Use with a LlamaIndex query engine or retriever by attaching the handler to the
callback manager. On RETRIEVE events, retrieved nodes are ingested as evidence;
on SYNTHESIZE end, the response is proposed as a claim and linked to that evidence.
"""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Any, cast

try:
    from llama_index.core import BaseCallbackHandler
    from llama_index.core.callbacks import CBEventType

    _LLAMA_AVAILABLE = True
except ImportError:
    BaseCallbackHandler = object  # type: ignore[misc, assignment]
    CBEventType = None  # type: ignore[assignment, misc]
    _LLAMA_AVAILABLE = False


def _node_text(node: Any) -> str:
    """Extract text from a LlamaIndex node or NodeWithScore."""
    if hasattr(node, "node"):
        node = node.node
    if hasattr(node, "get_content"):
        return node.get_content() or ""
    if hasattr(node, "text"):
        return node.text or ""
    if isinstance(node, dict):
        return node.get("text", node.get("content", "")) or ""
    return str(node)


def _response_text(payload: dict[str, Any]) -> str:
    """Extract response text from a SYNTHESIZE payload."""
    resp = payload.get("response") or payload.get("output")
    if resp is None:
        return ""
    if hasattr(resp, "response"):
        return cast(
            str, (resp.response or "") if isinstance(resp.response, str) else str(resp.response)
        )
    if hasattr(resp, "message") and hasattr(resp.message, "content"):
        return cast(str, resp.message.content or "")
    if isinstance(resp, str):
        return resp
    return str(resp)


def _get_nodes(payload: dict[str, Any]) -> list[Any]:
    """Extract list of nodes from a RETRIEVE payload."""
    nodes = payload.get("nodes") or payload.get("node_list") or payload.get("retrieved_nodes")
    if nodes is None:
        return []
    if isinstance(nodes, list):
        return nodes
    return [nodes]


def _event_matches(event_type: Any, name: str) -> bool:
    """True if event_type equals the given name (string or CBEventType enum)."""
    if event_type is None:
        return False
    if hasattr(event_type, "value"):
        return cast(bool, event_type.value == name)
    return str(event_type) == name


class ChronicleCallbackHandler(BaseCallbackHandler):  # type: ignore[misc]
    """LlamaIndex callback handler that writes retrievals and responses to Chronicle.

    On RETRIEVE (event end): ingested nodes are stored as evidence and spans.
    On SYNTHESIZE (event end): the response is proposed as a claim and linked to that evidence.

    Config:
        project_path: Chronicle project directory (must exist or be creatable; in-process only).
        investigation_uid: Use this investigation, or None to create one using investigation_title.
        investigation_title: Title when creating an investigation (default "LlamaIndex RAG").
        actor_id: Actor identifier (default "llamaindex").
        actor_type: Actor type (default "tool").
        workspace: Chronicle workspace (default "spark").
    """

    def __init__(
        self,
        project_path: Path | str,
        *,
        investigation_uid: str | None = None,
        investigation_key: str | None = None,
        investigation_title: str = "LlamaIndex RAG",
        actor_id: str = "llamaindex",
        actor_type: str = "tool",
        workspace: str = "spark",
    ) -> None:
        if not _LLAMA_AVAILABLE:
            raise ImportError(
                "Chronicle LlamaIndex integration requires llama-index-core. "
                "Install with: pip install chronicle-standard llama-index-core"
            ) from None
        super().__init__(event_starts_to_ignore=[], event_ends_to_ignore=[])
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

    def on_event_start(
        self,
        event_type: str,
        payload: dict[str, Any] | None = None,
        event_id: str = "",
        parent_id: str = "",
        **kwargs: Any,
    ) -> str:
        """On QUERY start, clear pending evidence so we associate new retrievals with this query."""
        if _event_matches(event_type, "QUERY"):
            self._pending_spans = []
        return event_id

    def start_trace(self, trace_id: str | None = None) -> None:
        """No-op for Chronicle handler."""
        pass

    def end_trace(
        self,
        trace_id: str | None = None,
        trace_map: dict[str, list[str]] | None = None,
    ) -> None:
        """No-op for Chronicle handler."""
        pass

    def on_event_end(
        self,
        event_type: Any,
        payload: dict[str, Any] | None = None,
        event_id: str = "",
        **kwargs: Any,
    ) -> None:
        """On RETRIEVE end ingest nodes as evidence; on SYNTHESIZE end propose response as claim and link support."""
        payload = payload or {}
        inv_uid = self._ensure_investigation()
        sess = self._get_session()

        if _event_matches(event_type, "RETRIEVE"):
            nodes = _get_nodes(payload)
            for i, node in enumerate(nodes):
                text = _node_text(node)
                if not text.strip():
                    continue
                blob = text.encode("utf-8")
                try:
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

        elif _event_matches(event_type, "SYNTHESIZE"):
            response_text = _response_text(payload)
            if not response_text.strip():
                return
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
