"""ChronicleSession facade composed from write/query mixins.

ChronicleSession remains the single project-scoped entry point used by CLI, API,
and integrations. Implementation details are split into focused modules:

- ``chronicle.store.session_writes``: command/write operations
- ``chronicle.store.session_queries``: read/query/analytics operations
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from chronicle.core.errors import ChronicleProjectNotFoundError
from chronicle.core.policy import WORKSPACES
from chronicle.store.evidence_store import FileSystemEvidenceStore
from chronicle.store.project import CHRONICLE_DB, project_exists
from chronicle.store.protocols import EventStore, ReadModel
from chronicle.store.session_queries import ChronicleSessionQueryMixin
from chronicle.store.session_writes import ChronicleSessionWriteMixin
from chronicle.store.sqlite_event_store import SqliteEventStore


class ChronicleSession(ChronicleSessionWriteMixin, ChronicleSessionQueryMixin):
    """Session for a single project: store, read model, and evidence store."""

    def __init__(self, project_dir: Path | str) -> None:
        self._path = Path(project_dir)
        if not project_exists(self._path):
            raise ChronicleProjectNotFoundError(
                f"Not a Chronicle project (no {CHRONICLE_DB}): {self._path}"
            )
        self._store = SqliteEventStore(self._path / CHRONICLE_DB, run_projection=True)
        self._evidence = FileSystemEvidenceStore(self._path)

    @property
    def store(self) -> EventStore:
        return self._store

    @property
    def read_model(self) -> ReadModel:
        return self._store.get_read_model()

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
        self._store.close()
