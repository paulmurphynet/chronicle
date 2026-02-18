"""Tests for CLI actor identity (--actor-id, --actor-type, CHRONICLE_ACTOR_*)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from chronicle.cli.main import _actor_from_args, main
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
