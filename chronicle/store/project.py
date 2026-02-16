"""Project layout and initialization. Spec Section 4.1."""

from pathlib import Path

from chronicle.store.evidence_store import EVIDENCE_DIR
from chronicle.store.sqlite_event_store import SqliteEventStore

CHRONICLE_DB = "chronicle.db"


def create_project(project_dir: Path | str) -> None:
    """Create project directory with chronicle.db and evidence/. Leaves schema_version populated (event_store, read_model, project_format) so rebuild logic has a single path for new and migrated projects."""
    root = Path(project_dir)
    root.mkdir(parents=True, exist_ok=True)
    (root / EVIDENCE_DIR).mkdir(exist_ok=True)
    db_path = root / CHRONICLE_DB
    if db_path.exists():
        return  # Idempotent: already initialized
    store = SqliteEventStore(db_path, run_projection=True)
    store._connection()
    store.close()


def project_exists(project_dir: Path | str) -> bool:
    """Return True if project_dir contains chronicle.db."""
    return (Path(project_dir) / CHRONICLE_DB).is_file()
