"""ChronicleSession facade composed from write/query mixins.

ChronicleSession remains the single project-scoped entry point used by CLI, API,
and integrations. Implementation details are split into focused modules:

- ``chronicle.store.session_writes``: command/write operations
- ``chronicle.store.session_queries``: read/query/analytics operations
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from chronicle.core.errors import ChronicleProjectNotFoundError, ChronicleUserError
from chronicle.core.policy import WORKSPACES
from chronicle.store.backend_config import (
    BACKEND_POSTGRES,
    EventStoreConfig,
    create_event_store,
    resolve_event_store_config,
)
from chronicle.store.evidence_store import FileSystemEvidenceStore
from chronicle.store.project import CHRONICLE_DB, project_exists
from chronicle.store.protocols import EventStore, ReadModel
from chronicle.store.session_queries import ChronicleSessionQueryMixin
from chronicle.store.session_writes import ChronicleSessionWriteMixin


class ChronicleSession(ChronicleSessionWriteMixin, ChronicleSessionQueryMixin):
    """Session for a single project: store, read model, and evidence store."""

    def __init__(
        self,
        project_dir: Path | str,
        *,
        event_store_backend: str | None = None,
        postgres_url: str | None = None,
    ) -> None:
        self._path = Path(project_dir)
        if not project_exists(self._path):
            raise ChronicleProjectNotFoundError(
                f"Not a Chronicle project (no {CHRONICLE_DB}): {self._path}"
            )
        self._event_store_config: EventStoreConfig = resolve_event_store_config(
            backend=event_store_backend,
            postgres_url=postgres_url,
        )
        try:
            self._store = create_event_store(
                self._path,
                self._event_store_config,
                run_projection=True,
            )
        except ImportError as exc:
            if self._event_store_config.backend == BACKEND_POSTGRES:
                raise ChronicleUserError(
                    "CHRONICLE_EVENT_STORE=postgres requires optional dependency psycopg. "
                    "Install with: pip install -e '.[postgres]'."
                ) from exc
            raise
        get_read_model = getattr(self._store, "get_read_model", None)
        if get_read_model is None or not callable(get_read_model):
            self._close_store()
            raise ChronicleUserError(
                "Selected event store does not expose a read model required by ChronicleSession."
            )
        try:
            maybe_read_model = get_read_model()
        except NotImplementedError as exc:
            self._close_store()
            if self._event_store_config.backend == BACKEND_POSTGRES:
                raise ChronicleUserError(
                    "CHRONICLE_EVENT_STORE=postgres is configured, but ChronicleSession currently "
                    "requires SQLite read-model parity. Use CHRONICLE_EVENT_STORE=sqlite for CLI/API/session "
                    "workflows until Postgres read-model support lands. See docs/POSTGRES.md."
                ) from exc
            raise
        if maybe_read_model is None:
            self._close_store()
            raise ChronicleUserError(
                "Selected event store returned no read model required by ChronicleSession."
            )
        self._read_model = cast(ReadModel, maybe_read_model)
        self._evidence = FileSystemEvidenceStore(self._path)

    @property
    def store(self) -> EventStore:
        return self._store

    @property
    def read_model(self) -> ReadModel:
        return self._read_model

    @property
    def evidence(self) -> FileSystemEvidenceStore:
        return self._evidence

    @property
    def project_path(self) -> Path:
        """Project directory path (for handlers that need project-level files)."""
        return self._path

    def _workspace_for_investigation(self, investigation_uid: str, workspace: str | None) -> str:
        """Resolve effective workspace: explicit value wins; otherwise use current tier."""
        if workspace is not None:
            candidate = workspace.strip().lower()
            if candidate:
                return candidate
        inv = self.read_model.get_investigation(investigation_uid)
        if inv is not None:
            tier = (inv.current_tier or "").strip().lower()
            if tier in WORKSPACES:
                return tier
        return "spark"

    def __enter__(self) -> ChronicleSession:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def close(self) -> None:
        self._close_store()

    def _close_store(self) -> None:
        close = getattr(self._store, "close", None)
        if callable(close):
            close()
