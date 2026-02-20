"""Project and investigation CLI command implementations."""

from __future__ import annotations

import mimetypes
import sys
from pathlib import Path

from chronicle.store import export_import as export_import_mod
from chronicle.store.project import CHRONICLE_DB, create_project, project_exists
from chronicle.store.session import ChronicleSession


def cmd_init(path: Path) -> int:
    """Initialize a directory as a Chronicle project (creates chronicle.db and schema)."""
    if (path / CHRONICLE_DB).exists():
        print(f"Already a Chronicle project: {path}", file=sys.stderr)
        return 0
    create_project(path)
    print(f"Initialized Chronicle project at {path}")
    return 0


def cmd_create_investigation(
    title: str,
    path: Path,
    description: str | None,
    *,
    actor_id: str = "default",
    actor_type: str = "human",
) -> int:
    """Create a new investigation in the project."""
    if not project_exists(path):
        print(
            f"Not a Chronicle project (no {CHRONICLE_DB}). Run: chronicle init {path}",
            file=sys.stderr,
        )
        return 1
    with ChronicleSession(path) as session:
        _event_id, investigation_uid = session.create_investigation(
            title,
            description=description or None,
            actor_id=actor_id,
            actor_type=actor_type,
        )
        print(f"Created investigation {investigation_uid}")
        return 0


def cmd_ingest_evidence(
    file_path: Path,
    investigation_uid: str,
    path: Path,
    media_type: str | None,
    *,
    actor_id: str = "default",
    actor_type: str = "human",
) -> int:
    """Ingest a file as evidence into an investigation."""
    if not project_exists(path):
        print(
            f"Not a Chronicle project (no {CHRONICLE_DB}). Run: chronicle init {path}",
            file=sys.stderr,
        )
        return 1
    if not file_path.is_file():
        print(f"Not a file: {file_path}", file=sys.stderr)
        return 1
    mt = media_type
    if not mt:
        mt, _ = mimetypes.guess_type(str(file_path))
    if not mt:
        print("Could not guess media type. Use --media-type.", file=sys.stderr)
        return 1
    blob = file_path.read_bytes()
    original_filename = file_path.name
    with ChronicleSession(path) as session:
        _event_id, evidence_uid = session.ingest_evidence(
            investigation_uid,
            blob,
            mt,
            original_filename=original_filename,
            actor_id=actor_id,
            actor_type=actor_type,
        )
        print(f"Ingested {original_filename} as {evidence_uid}")
        return 0


def cmd_set_tier(
    investigation_uid: str,
    tier: str,
    path: Path,
    reason: str | None,
    *,
    actor_id: str = "default",
    actor_type: str = "human",
) -> int:
    """Set investigation tier (spark -> forge -> vault)."""
    if not project_exists(path):
        print(
            f"Not a Chronicle project (no {CHRONICLE_DB}). Run: chronicle init {path}",
            file=sys.stderr,
        )
        return 1
    with ChronicleSession(path) as session:
        event_id = session.set_tier(
            investigation_uid,
            tier,
            reason=reason,
            actor_id=actor_id,
            actor_type=actor_type,
        )
        inv = session.read_model.get_investigation(investigation_uid)
        tier_display = inv.current_tier if inv else tier.strip().lower()
        print(f"Tier set to {tier_display} (event_id={event_id})")
        return 0


def cmd_export(investigation_uid: str, output: Path, path: Path) -> int:
    """Export investigation to .chronicle file."""
    if not project_exists(path):
        print(
            f"Not a Chronicle project (no {CHRONICLE_DB}). Run: chronicle init {path}",
            file=sys.stderr,
        )
        return 1
    out = export_import_mod.export_investigation(path, investigation_uid, output)
    print(f"Exported to {out}")
    return 0


def cmd_export_minimal(investigation_uid: str, claim_uid: str, output: Path, path: Path) -> int:
    """Export minimal .chronicle for one claim."""
    if not project_exists(path):
        print(
            f"Not a Chronicle project (no {CHRONICLE_DB}). Run: chronicle init {path}",
            file=sys.stderr,
        )
        return 1
    out = export_import_mod.export_minimal_for_claim(path, investigation_uid, claim_uid, output)
    print(f"Exported minimal .chronicle to {out}")
    return 0


def cmd_import(chronicle_file: Path, path: Path) -> int:
    """Import .chronicle file into project (extract to empty dir or merge into existing)."""
    if not chronicle_file.is_file():
        print(f"Not a file: {chronicle_file}", file=sys.stderr)
        return 1
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    export_import_mod.import_investigation(chronicle_file, path)
    print(f"Imported {chronicle_file}")
    return 0
