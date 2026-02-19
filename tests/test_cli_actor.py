"""Tests for CLI actor identity (--actor-id, --actor-type, CHRONICLE_ACTOR_*)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from chronicle.cli.main import _actor_from_args, main
from chronicle.core.policy import PolicyProfile, default_policy_profile, import_policy_to_project
from chronicle.store.project import create_project
from chronicle.store.session import ChronicleSession


def test_actor_from_args_uses_args_first() -> None:
    """_actor_from_args uses args.actor_id and args.actor_type when set."""
    class Args:
        actor_id = "from_args"
        actor_type = "tool"
    args = Args()
    aid, atype = _actor_from_args(args)
    assert aid == "from_args"
    assert atype == "tool"


def test_actor_from_args_falls_back_to_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """_actor_from_args falls back to CHRONICLE_ACTOR_ID and CHRONICLE_ACTOR_TYPE."""
    class Args:
        actor_id = None
        actor_type = None
    monkeypatch.setenv("CHRONICLE_ACTOR_ID", "env_actor")
    monkeypatch.setenv("CHRONICLE_ACTOR_TYPE", "human")
    aid, atype = _actor_from_args(Args())
    assert aid == "env_actor"
    assert atype == "human"


def test_actor_from_args_default_when_empty() -> None:
    """_actor_from_args returns default/human when args and env are empty."""
    class Args:
        actor_id = None
        actor_type = None
    # Ensure env is not set for this test
    aid, atype = _actor_from_args(Args())
    assert aid == "default"
    assert atype == "human"


def test_cli_create_investigation_records_actor_id(tmp_path: Path) -> None:
    """Running create-investigation with --actor-id records that actor on the event."""
    create_project(tmp_path)
    old_argv = sys.argv
    try:
        sys.argv = [
            "chronicle",
            "--actor-id",
            "cli_curator",
            "--actor-type",
            "human",
            "create-investigation",
            "CLI actor test",
            "--path",
            str(tmp_path),
        ]
        exit_code = main()
        assert exit_code == 0
    finally:
        sys.argv = old_argv

    with ChronicleSession(tmp_path) as session:
        events = session.store.read_all(limit=10)
    created = next(
        (e for e in events if getattr(e, "event_type", None) == "InvestigationCreated"),
        None,
    )
    assert created is not None
    assert created.actor_id == "cli_curator"
    assert created.actor_type == "human"


def test_cli_policy_compat_json_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """policy compat subcommand returns machine-readable JSON when --json is set."""
    create_project(tmp_path)
    base = default_policy_profile().to_dict()
    base["profile_id"] = "policy_strict_test"
    base["display_name"] = "Strict test profile"
    base["mes_rules"][0]["min_independent_sources"] = 3
    strict_profile = PolicyProfile.from_dict(base)
    import_policy_to_project(tmp_path, strict_profile, activate=False)

    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation(
            "Policy compat test",
            actor_id="cli_tester",
            actor_type="tool",
        )

    old_argv = sys.argv
    try:
        sys.argv = [
            "chronicle",
            "policy",
            "compat",
            "--path",
            str(tmp_path),
            "--investigation",
            inv_uid,
            "--built-under-profile-id",
            "policy_investigative_journalism",
            "--viewing-profile-id",
            "policy_strict_test",
            "--json",
        ]
        exit_code = main()
        assert exit_code == 0
    finally:
        sys.argv = old_argv

    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["investigation_uid"] == inv_uid
    assert payload["built_under"] == "policy_investigative_journalism"
    assert payload["viewing_under"] == "policy_strict_test"
    assert isinstance(payload.get("deltas"), list)
