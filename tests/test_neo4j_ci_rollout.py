from __future__ import annotations

import json
import sys
from importlib import import_module
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

module = import_module("scripts.check_neo4j_ci_rollout")


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _base_runs(run_id: int, *, workflow_name: str = "CI") -> dict:
    return {
        "workflow_runs": [
            {
                "id": run_id,
                "status": "completed",
                "conclusion": "success",
                "name": workflow_name,
                "display_title": f"{workflow_name} run",
            }
        ]
    }


def _jobs(job_names: list[str]) -> dict:
    return {"jobs": [{"name": name, "conclusion": "success"} for name in job_names]}


def test_neo4j_ci_rollout_passes_with_valid_fixture(tmp_path: Path) -> None:
    required_job = module.DEFAULT_REQUIRED_JOB
    _write(tmp_path / "runs_push.json", _base_runs(101))
    _write(tmp_path / "runs_pull_request.json", _base_runs(202))
    _write(tmp_path / "jobs_101.json", _jobs(["lint-and-test (3.12)", required_job]))
    _write(tmp_path / "jobs_202.json", _jobs(["frontend-checks", required_job]))

    report = module.run_check(
        repo="chronicle-app/chronicle",
        branch="main",
        required_job=required_job,
        workflow_name=module.DEFAULT_WORKFLOW_NAME,
        runs_per_event=10,
        token=None,
        fixture_dir=tmp_path,
    )
    assert report["status"] == "passed"
    assert all(e["ok"] is True for e in report["events"])


def test_neo4j_ci_rollout_fails_when_job_missing(tmp_path: Path) -> None:
    required_job = module.DEFAULT_REQUIRED_JOB
    _write(tmp_path / "runs_push.json", _base_runs(301))
    _write(tmp_path / "runs_pull_request.json", _base_runs(302))
    _write(tmp_path / "jobs_301.json", _jobs(["lint-and-test (3.12)", required_job]))
    _write(tmp_path / "jobs_302.json", _jobs(["lint-and-test (3.12)"]))

    report = module.run_check(
        repo="chronicle-app/chronicle",
        branch="main",
        required_job=required_job,
        workflow_name=module.DEFAULT_WORKFLOW_NAME,
        runs_per_event=10,
        token=None,
        fixture_dir=tmp_path,
    )
    assert report["status"] == "failed"
    pr_event = next(e for e in report["events"] if e["event"] == "pull_request")
    assert pr_event["ok"] is False


def test_neo4j_ci_rollout_blocked_when_fixture_missing(tmp_path: Path) -> None:
    required_job = module.DEFAULT_REQUIRED_JOB
    _write(tmp_path / "runs_push.json", _base_runs(401))
    _write(tmp_path / "jobs_401.json", _jobs([required_job]))

    report = module.run_check(
        repo="chronicle-app/chronicle",
        branch="main",
        required_job=required_job,
        workflow_name=module.DEFAULT_WORKFLOW_NAME,
        runs_per_event=10,
        token=None,
        fixture_dir=tmp_path,
    )
    assert report["status"] == "blocked"
