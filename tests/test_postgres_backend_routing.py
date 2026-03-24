"""Routing tests for Postgres backend command paths."""

from __future__ import annotations

from pathlib import Path

import pytest
from chronicle.cli import command_handlers, project_commands
from chronicle.store.project import create_project
from chronicle.store.session import ChronicleSession
from chronicle.verify import VerifyReport


def _enable_postgres_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHRONICLE_EVENT_STORE", "postgres")
    monkeypatch.setenv("CHRONICLE_POSTGRES_URL", "postgresql://u:p@127.0.0.1:5432/chronicle")


def _seed_exportable_investigation(project_path: Path) -> tuple[str, str]:
    with ChronicleSession(project_path, event_store_backend="sqlite") as session:
        _, inv_uid = session.create_investigation("Exportable", actor_id="t", actor_type="tool")
        _, ev_uid = session.ingest_evidence(
            inv_uid,
            b"Sample evidence bytes",
            "text/plain",
            original_filename="sample.txt",
            actor_id="t",
            actor_type="tool",
        )
        _, span_uid = session.anchor_span(
            inv_uid,
            ev_uid,
            "text_offset",
            {"start_char": 0, "end_char": 6},
            quote="Sample",
            actor_id="t",
            actor_type="tool",
        )
        _, claim_uid = session.propose_claim(
            inv_uid,
            "Sample claim.",
            actor_id="t",
            actor_type="tool",
        )
        session.link_support(inv_uid, span_uid, claim_uid, actor_id="t", actor_type="tool")
    return inv_uid, claim_uid


class _FailIfSessionUsed:
    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise AssertionError(
            "ChronicleSession should not be used for archive import/export routing"
        )


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


def test_cmd_export_is_backend_independent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys
) -> None:
    create_project(tmp_path)
    inv_uid, _ = _seed_exportable_investigation(tmp_path)
    _enable_postgres_env(monkeypatch)
    monkeypatch.setattr(project_commands, "ChronicleSession", _FailIfSessionUsed)

    output = tmp_path / "out.chronicle"
    rc = project_commands.cmd_export(inv_uid, output, tmp_path)
    out = capsys.readouterr().out

    assert rc == 0
    assert output.is_file()
    assert "Exported to" in out


def test_cmd_export_minimal_is_backend_independent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys
) -> None:
    create_project(tmp_path)
    inv_uid, claim_uid = _seed_exportable_investigation(tmp_path)
    _enable_postgres_env(monkeypatch)
    monkeypatch.setattr(project_commands, "ChronicleSession", _FailIfSessionUsed)

    output = tmp_path / "minimal.chronicle"
    rc = project_commands.cmd_export_minimal(inv_uid, claim_uid, output, tmp_path)
    out = capsys.readouterr().out

    assert rc == 0
    assert output.is_file()
    assert "Exported minimal .chronicle" in out


def test_cmd_import_is_backend_independent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys
) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    create_project(source)
    create_project(target)
    inv_uid, _ = _seed_exportable_investigation(source)
    archive = tmp_path / "importable.chronicle"
    project_commands.cmd_export(inv_uid, archive, source)

    _enable_postgres_env(monkeypatch)
    monkeypatch.setattr(project_commands, "ChronicleSession", _FailIfSessionUsed)

    rc = project_commands.cmd_import(archive, target)
    out = capsys.readouterr().out

    assert rc == 0
    assert "Imported" in out
    with ChronicleSession(target, event_store_backend="sqlite") as session:
        assert session.read_model.get_investigation(inv_uid) is not None
