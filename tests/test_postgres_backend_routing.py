"""Routing tests for Postgres backend command paths."""

from __future__ import annotations

from pathlib import Path

import pytest
from chronicle.cli import command_handlers
from chronicle.store.project import create_project
from chronicle.verify import VerifyReport


def _enable_postgres_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHRONICLE_EVENT_STORE", "postgres")
    monkeypatch.setenv("CHRONICLE_POSTGRES_URL", "postgresql://u:p@127.0.0.1:5432/chronicle")


def test_cmd_replay_routes_to_postgres(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys
) -> None:
    create_project(tmp_path)
    _enable_postgres_env(monkeypatch)

    import chronicle.store.postgres_projection as pg_projection

    monkeypatch.setattr(
        pg_projection,
        "replay_postgres_read_model_from_url",
        lambda database_url, **_: 7,
    )
    rc = command_handlers.cmd_replay(tmp_path, None, None)
    out = capsys.readouterr().out
    assert rc == 0
    assert "Replayed 7 events into Postgres read model" in out


def test_cmd_snapshot_create_routes_to_postgres(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys
) -> None:
    create_project(tmp_path)
    _enable_postgres_env(monkeypatch)

    import chronicle.store.postgres_projection as pg_projection

    monkeypatch.setattr(
        pg_projection,
        "create_postgres_read_model_snapshot_from_url",
        lambda database_url, at_event, output: 3,
    )
    rc = command_handlers.cmd_snapshot_create(tmp_path, "event_123", tmp_path / "snap.json")
    out = capsys.readouterr().out
    assert rc == 0
    assert "Created Postgres snapshot" in out


def test_cmd_snapshot_restore_routes_to_postgres(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys
) -> None:
    create_project(tmp_path)
    _enable_postgres_env(monkeypatch)

    import chronicle.store.postgres_projection as pg_projection

    monkeypatch.setattr(
        pg_projection,
        "restore_postgres_read_model_snapshot_from_url",
        lambda database_url, snapshot_path: 2,
    )
    rc = command_handlers.cmd_snapshot_restore(tmp_path, tmp_path / "snap.json")
    out = capsys.readouterr().out
    assert rc == 0
    assert "Restored Postgres read model" in out


def test_cmd_verify_routes_to_postgres(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys
) -> None:
    create_project(tmp_path)
    _enable_postgres_env(monkeypatch)

    import chronicle.verify as verify_mod

    fake = VerifyReport(passed=True)
    fake.add("postgres_connect", True, "connected")
    fake.add("projection_completeness", True, "all good")
    monkeypatch.setattr(verify_mod, "verify_postgres_url", lambda database_url, **_: fake)

    rc = command_handlers.cmd_verify(tmp_path, skip_evidence=True)
    out = capsys.readouterr().out
    assert rc == 0
    assert "[PASS] postgres_connect" in out
    assert "All checks passed." in out
