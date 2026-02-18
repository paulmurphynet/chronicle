"""Tests for read_model_snapshot: create snapshot at event N, restore from snapshot + tail replay."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from chronicle.store.project import CHRONICLE_DB, create_project
from chronicle.store.read_model_snapshot import (
    SNAPSHOT_META_DDL,
    create_read_model_snapshot,
    restore_from_snapshot,
)
from chronicle.store.schema import run_read_model_ddl_only
from chronicle.store.session import ChronicleSession


def test_create_read_model_snapshot_not_a_project(tmp_path: Path) -> None:
    """create_read_model_snapshot raises when directory has no chronicle.db."""
    out = tmp_path / "snap.db"
    with pytest.raises(FileNotFoundError, match="Not a Chronicle project"):
        create_read_model_snapshot(tmp_path, "e1", out)


def test_create_read_model_snapshot_event_not_found(tmp_path: Path) -> None:
    """create_read_model_snapshot raises when at_event_id does not exist."""
    create_project(tmp_path)
    out = tmp_path / "snap.db"
    with pytest.raises(ValueError, match="Event not found"):
        create_read_model_snapshot(tmp_path, "nonexistent-event-id", out)


def test_create_read_model_snapshot_happy(tmp_path: Path) -> None:
    """Create project with two events (via session), snapshot at first event; snapshot file has read model + meta."""
    create_project(tmp_path)
    first_event_id = None
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("Snap test", actor_id="t", actor_type="tool")
        session.ingest_evidence(
            inv_uid, b"chunk", "text/plain", original_filename="a.txt", actor_id="t", actor_type="tool"
        )
        events = session.store.read_all(limit=5)
        e1 = next(e for e in events if e.event_type == "InvestigationCreated")
        first_event_id = e1.event_id

    out = tmp_path / "snapshot.db"
    n = create_read_model_snapshot(tmp_path, first_event_id, out)
    assert n >= 1
    assert out.is_file()

    conn = sqlite3.connect(str(out))
    row = conn.execute("SELECT as_of_event_id, as_of_event_rowid, recorded_at FROM snapshot_meta LIMIT 1").fetchone()
    conn.close()
    assert row is not None
    assert row[0] == first_event_id
    assert row[1] >= 1


def test_create_read_model_snapshot_at_second_event(tmp_path: Path) -> None:
    """Snapshot at second event replays two events."""
    create_project(tmp_path)
    second_event_id = None
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("Snap two", actor_id="t", actor_type="tool")
        session.ingest_evidence(inv_uid, b"x", "text/plain", original_filename="x.txt", actor_id="t", actor_type="tool")
        events = session.store.read_all(limit=5)
        ingested = next(e for e in events if e.event_type == "EvidenceIngested")
        second_event_id = ingested.event_id

    out = tmp_path / "snap2.db"
    n = create_read_model_snapshot(tmp_path, second_event_id, out)
    assert n >= 2
    assert out.is_file()


def test_restore_from_snapshot_file_not_found(tmp_path: Path) -> None:
    """restore_from_snapshot raises when snapshot path is not a file."""
    create_project(tmp_path)
    with pytest.raises(FileNotFoundError, match="Snapshot file not found"):
        restore_from_snapshot(tmp_path, tmp_path / "missing.db")


def test_restore_from_snapshot_not_a_project(tmp_path: Path) -> None:
    """restore_from_snapshot raises when project_dir has no chronicle.db."""
    snap = tmp_path / "snap.db"
    snap.write_bytes(b"not a real db")
    with pytest.raises(FileNotFoundError, match="Not a Chronicle project"):
        restore_from_snapshot(tmp_path, snap)


def test_restore_from_snapshot_no_meta(tmp_path: Path) -> None:
    """restore_from_snapshot raises when snapshot has no snapshot_meta row."""
    create_project(tmp_path)
    bad_snap = tmp_path / "bad_snap.db"
    conn = sqlite3.connect(str(bad_snap))
    run_read_model_ddl_only(conn)
    conn.executescript(SNAPSHOT_META_DDL)
    conn.commit()
    conn.close()
    with pytest.raises(ValueError, match="Snapshot has no snapshot_meta row"):
        restore_from_snapshot(tmp_path, bad_snap)


def test_restore_from_snapshot_tail_replay(tmp_path: Path) -> None:
    """Create snapshot at first event, then add more events; restore replays tail."""
    create_project(tmp_path)
    first_event_id = None
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("Tail test", actor_id="t", actor_type="tool")
        events = session.store.read_all(limit=5)
        first_event_id = next(e for e in events if e.event_type == "InvestigationCreated").event_id
        session.ingest_evidence(inv_uid, b"more", "text/plain", original_filename="b.txt", actor_id="t", actor_type="tool")

    snap_path = tmp_path / "snap.db"
    create_read_model_snapshot(tmp_path, first_event_id, snap_path)

    tail = restore_from_snapshot(tmp_path, snap_path)
    assert tail >= 1

    with ChronicleSession(tmp_path) as session:
        events = session.store.read_all(limit=10)
    assert len(events) >= 2
