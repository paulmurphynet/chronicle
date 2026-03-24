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


def test_cli_policy_sensitivity_json_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """policy sensitivity subcommand returns machine-readable JSON when --json is set."""
    create_project(tmp_path)

    base = default_policy_profile().to_dict()
    base["profile_id"] = "policy_permissive_test"
    base["display_name"] = "Permissive test profile"
    base["mes_rules"][0]["min_independent_sources"] = 0
    permissive_profile = PolicyProfile.from_dict(base)
    import_policy_to_project(tmp_path, permissive_profile, activate=False)

    strict = default_policy_profile().to_dict()
    strict["profile_id"] = "policy_strict_test"
    strict["display_name"] = "Strict test profile"
    strict["mes_rules"][0]["min_independent_sources"] = 2
    strict_profile = PolicyProfile.from_dict(strict)
    import_policy_to_project(tmp_path, strict_profile, activate=False)

    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation(
            "Policy sensitivity CLI test",
            actor_id="cli_tester",
            actor_type="tool",
        )
        _, ev_uid = session.ingest_evidence(
            inv_uid,
            b"Single-source timeline note.",
            "text/plain",
            original_filename="timeline.txt",
            actor_id="cli_tester",
            actor_type="tool",
        )
        _, span_uid = session.anchor_span(
            inv_uid,
            ev_uid,
            "text_offset",
            {"start_char": 0, "end_char": len("Single-source timeline note.")},
            quote="Single-source timeline note.",
            actor_id="cli_tester",
            actor_type="tool",
        )
        _, claim_uid = session.propose_claim(
            inv_uid,
            "Timeline note is reliable.",
            actor_id="cli_tester",
            actor_type="tool",
        )
        session.link_support(
            inv_uid,
            span_uid,
            claim_uid,
            actor_id="cli_tester",
            actor_type="tool",
        )

    old_argv = sys.argv
    try:
        sys.argv = [
            "chronicle",
            "policy",
            "sensitivity",
            "--path",
            str(tmp_path),
            "--investigation",
            inv_uid,
            "--profile-id",
            "policy_permissive_test",
            "--profile-id",
            "policy_strict_test",
            "--built-under-profile-id",
            "policy_permissive_test",
            "--json",
        ]
        exit_code = main()
        assert exit_code == 0
    finally:
        sys.argv = old_argv

    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["investigation_uid"] == inv_uid
    assert [p["profile_id"] for p in payload["selected_profiles"]] == [
        "policy_permissive_test",
        "policy_strict_test",
    ]
    assert len(payload.get("pairwise_deltas", [])) == 1
    assert payload["pairwise_deltas"][0]["summary"]["changed_count"] >= 1


def test_cli_reviewer_decision_ledger_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """reviewer-decision-ledger command returns consolidated JSON artifact."""
    create_project(tmp_path)

    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation(
            "Reviewer ledger test",
            actor_id="cli_editor",
            actor_type="human",
        )
        session.set_tier(
            inv_uid,
            "forge",
            reason="Escalated",
            actor_id="cli_editor",
            actor_type="human",
        )

    old_argv = sys.argv
    try:
        sys.argv = [
            "chronicle",
            "reviewer-decision-ledger",
            inv_uid,
            "--path",
            str(tmp_path),
            "--limit",
            "200",
        ]
        exit_code = main()
        assert exit_code == 0
    finally:
        sys.argv = old_argv

    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["investigation_uid"] == inv_uid
    assert isinstance(payload.get("decisions"), list)
    assert payload["summary"]["tier_changed_count"] >= 1


def test_cli_review_packet_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """review-packet command returns consolidated packet JSON."""
    create_project(tmp_path)

    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation(
            "Review packet CLI test",
            actor_id="cli_editor",
            actor_type="human",
        )
        session.propose_claim(
            inv_uid,
            "CLI packet claim",
            actor_id="cli_editor",
            actor_type="human",
        )

    old_argv = sys.argv
    try:
        sys.argv = [
            "chronicle",
            "review-packet",
            inv_uid,
            "--path",
            str(tmp_path),
            "--limit-claims",
            "25",
            "--decision-limit",
            "100",
            "--no-reasoning-briefs",
        ]
        exit_code = main()
        assert exit_code == 0
    finally:
        sys.argv = old_argv

    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["investigation_uid"] == inv_uid
    assert "policy_compatibility" in payload
    assert "reviewer_decision_ledger" in payload
    assert "audit_export_bundle" in payload
    assert payload["reasoning_briefs"] == []
