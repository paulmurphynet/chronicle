from __future__ import annotations

import json
import sys
from importlib import import_module
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

module = import_module("scripts.check_branch_protection_rollout")


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _base_protection(required_checks: list[str]) -> dict:
    return {
        "required_status_checks": {
            "strict": True,
            "contexts": required_checks,
        },
        "required_pull_request_reviews": {"enabled": True},
        "enforce_admins": {"enabled": True},
        "allow_force_pushes": {"enabled": False},
        "allow_deletions": {"enabled": False},
    }


def _base_runs(run_id: int) -> dict:
    return {
        "workflow_runs": [
            {
                "id": run_id,
                "status": "completed",
                "conclusion": "success",
                "name": "CI",
                "display_title": "CI run",
            }
        ]
    }


def _jobs(required_checks: list[str]) -> dict:
    return {"jobs": [{"name": name, "conclusion": "success"} for name in required_checks]}


def test_branch_protection_rollout_passes_with_valid_fixture(tmp_path: Path) -> None:
    required = module.DEFAULT_REQUIRED_CHECKS
    _write(tmp_path / "protection.json", _base_protection(required))
    _write(tmp_path / "runs_push.json", _base_runs(101))
    _write(tmp_path / "runs_pull_request.json", _base_runs(202))
    _write(tmp_path / "jobs_101.json", _jobs(required))
    _write(tmp_path / "jobs_202.json", _jobs(required))

    report = module.run_check(
        repo="chronicle-app/chronicle",
        branch="main",
        required_checks=required,
        runs_per_event=10,
        token=None,
        fixture_dir=tmp_path,
    )
    assert report["status"] == "passed"
    assert report["branch_protection"]["missing_required_checks"] == []
    assert all(e["ok"] is True for e in report["ci_required_jobs"]["events"])


def test_branch_protection_rollout_fails_when_required_check_missing(tmp_path: Path) -> None:
    required = module.DEFAULT_REQUIRED_CHECKS
    protection = _base_protection(required)
    protection["required_status_checks"]["contexts"] = required[:-1]
    _write(tmp_path / "protection.json", protection)
    _write(tmp_path / "runs_push.json", _base_runs(301))
    _write(tmp_path / "runs_pull_request.json", _base_runs(302))
    _write(tmp_path / "jobs_301.json", _jobs(required))
    _write(tmp_path / "jobs_302.json", _jobs(required))

    report = module.run_check(
        repo="chronicle-app/chronicle",
        branch="main",
        required_checks=required,
        runs_per_event=10,
        token=None,
        fixture_dir=tmp_path,
    )
    assert report["status"] == "failed"
    assert report["branch_protection"]["missing_required_checks"] == [required[-1]]


def test_branch_protection_rollout_blocked_when_protection_fixture_missing(tmp_path: Path) -> None:
    required = module.DEFAULT_REQUIRED_CHECKS
    _write(tmp_path / "runs_push.json", _base_runs(401))
    _write(tmp_path / "runs_pull_request.json", _base_runs(402))
    _write(tmp_path / "jobs_401.json", _jobs(required))
    _write(tmp_path / "jobs_402.json", _jobs(required))

    report = module.run_check(
        repo="chronicle-app/chronicle",
        branch="main",
        required_checks=required,
        runs_per_event=10,
        token=None,
        fixture_dir=tmp_path,
    )
    assert report["status"] == "blocked"
    assert report["branch_protection"]["exists"] is False
