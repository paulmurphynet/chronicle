from __future__ import annotations

import json
import sys
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace

from chronicle.store.read_model.models import DefensibilityScorecard

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

parity_module = import_module("scripts.postgres_backend_parity")
onboarding_module = import_module("scripts.postgres_onboarding_timed_check")


def test_parity_normalize_scorecard_sorts_unordered_fields() -> None:
    score = DefensibilityScorecard(
        claim_uid="claim_1",
        provenance_quality="medium",
        corroboration={"support_count": 1, "challenge_count": 0, "independent_sources_count": 1},
        contradiction_status="open",
        temporal_validity="unset",
        attribution_posture="UNKNOWN",
        decomposition_precision="low",
        contradiction_handling=[
            {
                "tension_uid": "t2",
                "status": "OPEN",
                "rationale_or_notes": "b",
                "other_claim_uid": "c2",
            },
            {
                "tension_uid": "t1",
                "status": "OPEN",
                "rationale_or_notes": "a",
                "other_claim_uid": "c1",
            },
        ],
        knowability={
            "known_as_of": None,
            "known_range_start": None,
            "known_range_end": None,
            "knowable_from": None,
            "temporal_confidence": None,
        },
        risk_signals=["high_contradiction_count", "single_origin_support"],
    )
    normalized = parity_module.normalize_scorecard(score)
    assert normalized is not None
    assert [row["tension_uid"] for row in normalized["contradiction_handling"]] == ["t1", "t2"]
    assert normalized["risk_signals"] == ["high_contradiction_count", "single_origin_support"]


def test_parity_compare_scorecards_reports_mismatch() -> None:
    sqlite_scores = {"c1": {"provenance_quality": "strong"}, "c2": {"provenance_quality": "weak"}}
    postgres_scores = {"c1": {"provenance_quality": "strong"}, "c2": {"provenance_quality": "medium"}}
    mismatches = parity_module.compare_scorecards(sqlite_scores, postgres_scores)
    assert set(mismatches.keys()) == {"c2"}
    assert mismatches["c2"]["sqlite"]["provenance_quality"] == "weak"
    assert mismatches["c2"]["postgres"]["provenance_quality"] == "medium"


def test_onboarding_evaluate_report_failures() -> None:
    report = {
        "total_duration_seconds": 900,
        "max_duration_seconds": 600,
        "steps": [
            {"name": "postgres_doctor", "return_code": 0},
            {"name": "postgres_smoke", "return_code": 1},
        ],
    }
    ok, reasons = onboarding_module.evaluate_report(report)
    assert ok is False
    assert "step_failed:postgres_smoke" in reasons
    assert "duration_exceeded" in reasons


def test_onboarding_main_success_with_mocked_steps(tmp_path: Path, monkeypatch) -> None:
    output = tmp_path / "onboarding.json"

    def _ok_step(
        command: list[str],
        *,
        timeout_seconds: int,
        database_url: str,
        redacted_database_url: str,
    ) -> dict[str, object]:
        assert database_url
        assert redacted_database_url
        return {
            "command": command,
            "return_code": 0,
            "duration_seconds": 0.01,
            "stdout": "ok",
            "stderr": "",
        }

    monkeypatch.setattr(onboarding_module, "_run_step", _ok_step)
    rc = onboarding_module.main(
        [
            "--database-url",
            "postgresql://chronicle:chronicle_dev_password@127.0.0.1:5432/chronicle",
            "--output",
            str(output),
        ]
    )
    assert rc == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert len(payload["steps"]) == 2


def test_onboarding_optional_command_uses_argv_without_shell(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        captured["command"] = command
        captured["kwargs"] = kwargs
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(onboarding_module.subprocess, "run", _fake_run)
    step = onboarding_module._run_optional_command_step(
        label="bootstrap_1",
        command='echo "hello world"',
        timeout_seconds=30,
        database_url="postgresql://chronicle:password@127.0.0.1:5432/chronicle",
        redacted_database_url="postgresql://chronicle:***@127.0.0.1:5432/chronicle",
    )
    assert captured["command"] == ["echo", "hello world"]
    kwargs = captured["kwargs"]
    assert isinstance(kwargs, dict)
    assert kwargs.get("shell") is None
    assert step["return_code"] == 0
    assert step["command"] == ["echo", "hello world"]


def test_onboarding_optional_command_rejects_empty_command() -> None:
    try:
        onboarding_module._run_optional_command_step(
            label="bootstrap_1",
            command="   ",
            timeout_seconds=30,
            database_url="postgresql://chronicle:password@127.0.0.1:5432/chronicle",
            redacted_database_url="postgresql://chronicle:***@127.0.0.1:5432/chronicle",
        )
        raised = False
    except ValueError:
        raised = True
    assert raised is True
