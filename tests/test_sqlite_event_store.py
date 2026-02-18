"""Tests for SqliteEventStore and replay_read_model (Phase 1 coverage)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from chronicle.core.events import Event
from chronicle.store.project import CHRONICLE_DB, create_project
from chronicle.store.session import ChronicleSession
from chronicle.store.sqlite_event_store import (
    SqliteEventStore,
    replay_read_model,
)


def _minimal_event(
    event_id: str,
    investigation_uid: str = "inv",
    subject_uid: str | None = None,
    recorded_at: str = "2024-01-01T00:00:00Z",
    idempotency_key: str | None = None,
) -> Event:
    return Event(
        event_id=event_id,
        event_type="InvestigationCreated",
        occurred_at=recorded_at,
        recorded_at=recorded_at,
        investigation_uid=investigation_uid,
        subject_uid=subject_uid or investigation_uid,
        actor_type="tool",
        actor_id="t",
        workspace="spark",
        policy_profile_id=None,
        correlation_id=None,
        causation_id=None,
        envelope_version=1,
        payload_version=1,
        payload={},
        idempotency_key=idempotency_key,
        prev_event_hash=None,
        event_hash=None,
    )


def test_event_store_append_and_read_all_no_projection(tmp_path: Path) -> None:
    """With run_projection=False, append writes to events only; read_all returns them."""
    db_path = tmp_path / CHRONICLE_DB
    tmp_path.mkdir(parents=True, exist_ok=True)
    store = SqliteEventStore(db_path, run_projection=False)
    store.append(_minimal_event("e1", recorded_at="2024-01-01T00:00:01Z"))
    store.append(_minimal_event("e2", recorded_at="2024-01-01T00:00:02Z"))
    events = store.read_all()
    store.close()
    assert len(events) == 2
    assert events[0].event_id == "e1" and events[1].event_id == "e2"


def test_event_store_read_all_with_limit(tmp_path: Path) -> None:
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        session.create_investigation("L", actor_id="t", actor_type="tool")
        events = session.store.read_all(limit=1)
    assert len(events) == 1


def test_event_store_read_all_after_event_id(tmp_path: Path) -> None:
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("After", actor_id="t", actor_type="tool")
        session.ingest_evidence(inv_uid, b"x", "text/plain", original_filename="x.txt", actor_id="t", actor_type="tool")
        events = session.store.read_all(limit=10)
        assert len(events) >= 2
        first_id = events[0].event_id
        after = session.store.read_all(after_event_id=first_id, limit=10)
    assert all(e.event_id != first_id for e in after)
    assert len(after) == len(events) - 1


def test_event_store_read_by_investigation(tmp_path: Path) -> None:
    create_project(tmp_path)
    inv_uid = None
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("ByInv", actor_id="t", actor_type="tool")
        session.ingest_evidence(inv_uid, b"y", "text/plain", original_filename="y.txt", actor_id="t", actor_type="tool")
    with ChronicleSession(tmp_path) as session:
        by_inv = session.store.read_by_investigation(inv_uid)
    assert len(by_inv) >= 2
    assert all(e.investigation_uid == inv_uid for e in by_inv)


def test_event_store_read_by_subject(tmp_path: Path) -> None:
    create_project(tmp_path)
    inv_uid = None
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("BySubj", actor_id="t", actor_type="tool")
    with ChronicleSession(tmp_path) as session:
        by_subj = session.store.read_by_subject(inv_uid, limit=5)
    assert len(by_subj) >= 1
    assert all(e.subject_uid == inv_uid for e in by_subj)


def test_event_store_get_event_by_idempotency_key_none_for_empty(tmp_path: Path) -> None:
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        ev = session.store.get_event_by_idempotency_key("")
        assert ev is None
        assert session.store.get_event_by_idempotency_key("  ") is None


def test_event_store_get_event_by_idempotency_key_returns_event(tmp_path: Path) -> None:
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        session.create_investigation("Idem", actor_id="t", actor_type="tool", idempotency_key="key-1")
        ev = session.store.get_event_by_idempotency_key("key-1")
    assert ev is not None
    assert ev.payload.get("investigation_uid") is not None


def test_event_store_close_reopens_on_next_use(tmp_path: Path) -> None:
    create_project(tmp_path)
    store = SqliteEventStore(tmp_path / CHRONICLE_DB, run_projection=True)
    store._connection()
    store.close()
    events = store.read_all(limit=1)
    assert isinstance(events, list)


def test_replay_read_model_full(tmp_path: Path) -> None:
    """replay_read_model(conn) with no bound replays all events."""
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        session.create_investigation("Replay", actor_id="t", actor_type="tool")
    db_path = tmp_path / CHRONICLE_DB
    conn = sqlite3.connect(str(db_path))
    try:
        n = replay_read_model(conn)
        assert n >= 1
    finally:
        conn.close()


def test_replay_read_model_up_to_event_id(tmp_path: Path) -> None:
    """replay_read_model(conn, up_to_event_id=X) stops after including that event."""
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("Replay2", actor_id="t", actor_type="tool")
        session.ingest_evidence(inv_uid, b"z", "text/plain", original_filename="z.txt", actor_id="t", actor_type="tool")
        events = session.store.read_all(limit=5)
        first_id = events[0].event_id
        conn = session.store._connection()
        n = replay_read_model(conn, up_to_event_id=first_id)
    assert n >= 1
    assert n <= len(events)


def test_replay_read_model_up_to_recorded_at(tmp_path: Path) -> None:
    """replay_read_model(conn, up_to_recorded_at=...) stops at events after that time."""
    create_project(tmp_path)
    rec_at = None
    with ChronicleSession(tmp_path) as session:
        session.create_investigation("Replay3", actor_id="t", actor_type="tool")
        events = session.store.read_all(limit=1)
        rec_at = events[0].recorded_at
    conn = sqlite3.connect(str(tmp_path / CHRONICLE_DB))
    try:
        n = replay_read_model(conn, up_to_recorded_at=rec_at)
        assert n >= 1
    finally:
        conn.close()


def test_event_store_get_read_model(tmp_path: Path) -> None:
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("RM", actor_id="t", actor_type="tool")
        read_model = session.store.get_read_model()
        inv = read_model.get_investigation(inv_uid)
    assert inv is not None
    assert inv.investigation_uid == inv_uid
