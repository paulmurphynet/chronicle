#!/usr/bin/env python3
"""Verify CI evidence for the live Neo4j integration gate via GitHub Actions API."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from chronicle.core.http_safety import ensure_safe_http_url

DEFAULT_REQUIRED_JOB = "neo4j-live-integration"
DEFAULT_WORKFLOW_NAME = "CI"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _github_get_json(api_base: str, route: str, token: str | None) -> dict[str, Any]:
    url = ensure_safe_http_url(
        f"{api_base.rstrip('/')}/{route.lstrip('/')}",
        block_private_hosts=False,
    )
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "chronicle-neo4j-ci-check",
    }
    if token and token.strip():
        headers["Authorization"] = f"Bearer {token.strip()}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310
        raw = resp.read().decode("utf-8")
    payload = json.loads(raw) if raw else {}
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object from {route}")
    return payload


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Fixture must be a JSON object: {path}")
    return payload


def _run_name(run: dict[str, Any]) -> str:
    for key in ("display_title", "name", "workflow_name"):
        value = run.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return str(run.get("id") or "unknown-run")


def _summarize_event_runs(
    *,
    event: str,
    runs_payload: dict[str, Any],
    jobs_payload_by_run_id: dict[int, dict[str, Any]],
    required_job: str,
    workflow_name: str | None,
) -> dict[str, Any]:
    workflow_runs = runs_payload.get("workflow_runs")
    if not isinstance(workflow_runs, list):
        return {"event": event, "ok": False, "error": "workflow_runs missing from API response"}

    runs = [r for r in workflow_runs if isinstance(r, dict)]
    if workflow_name and workflow_name.strip():
        target = workflow_name.strip()
        runs = [r for r in runs if str(r.get("name") or "").strip() == target]

    completed = [r for r in runs if r.get("status") == "completed"]
    successful = [r for r in completed if r.get("conclusion") == "success"]
    checked_runs: list[dict[str, Any]] = []

    for run in successful:
        run_id = run.get("id")
        if not isinstance(run_id, int):
            continue
        jobs_payload = jobs_payload_by_run_id.get(run_id, {})
        jobs = jobs_payload.get("jobs")
        if not isinstance(jobs, list):
            checked_runs.append(
                {
                    "run_id": run_id,
                    "run_name": _run_name(run),
                    "ok": False,
                    "error": "jobs payload missing",
                }
            )
            continue
        success_jobs = {
            str(job.get("name"))
            for job in jobs
            if isinstance(job, dict) and job.get("conclusion") == "success"
        }
        checked_runs.append(
            {
                "run_id": run_id,
                "run_name": _run_name(run),
                "ok": required_job in success_jobs,
                "missing_required_job": required_job not in success_jobs,
            }
        )

    return {
        "event": event,
        "ok": any(run.get("ok") is True for run in checked_runs),
        "runs_seen": len(workflow_runs),
        "runs_after_workflow_filter": len(runs),
        "completed_runs": len(completed),
        "successful_runs": len(successful),
        "checked_runs": checked_runs,
    }


def run_check(
    *,
    repo: str,
    branch: str,
    required_job: str,
    workflow_name: str | None,
    runs_per_event: int,
    token: str | None,
    api_base: str = "https://api.github.com",
    fixture_dir: Path | None = None,
) -> dict[str, Any]:
    if "/" not in repo:
        raise ValueError("--repo must be in owner/name format")
    owner, name = repo.split("/", 1)
    required_job = required_job.strip()
    if not required_job:
        raise ValueError("--required-job must be non-empty")

    report: dict[str, Any] = {
        "schema_version": 1,
        "generated_at": _utc_now(),
        "repo": repo,
        "branch": branch,
        "required_job": required_job,
        "workflow_name": workflow_name,
        "status": "failed",
        "events": [],
        "errors": [],
    }

    jobs_payload_by_run_id: dict[int, dict[str, Any]] = {}
    event_summaries: list[dict[str, Any]] = []
    blocked = False

    for event in ("push", "pull_request"):
        try:
            if fixture_dir is not None:
                runs_payload = _load_json(fixture_dir / f"runs_{event}.json")
            else:
                query = urllib.parse.urlencode(
                    {"branch": branch, "event": event, "per_page": runs_per_event}
                )
                runs_payload = _github_get_json(
                    api_base, f"repos/{owner}/{name}/actions/runs?{query}", token
                )
            runs = runs_payload.get("workflow_runs")
            if isinstance(runs, list):
                for run in runs:
                    run_id = run.get("id") if isinstance(run, dict) else None
                    if not isinstance(run_id, int):
                        continue
                    if fixture_dir is not None:
                        jobs_path = fixture_dir / f"jobs_{run_id}.json"
                        if jobs_path.is_file():
                            jobs_payload_by_run_id[run_id] = _load_json(jobs_path)
                        else:
                            jobs_payload_by_run_id[run_id] = {}
                    else:
                        jobs_payload_by_run_id[run_id] = _github_get_json(
                            api_base, f"repos/{owner}/{name}/actions/runs/{run_id}/jobs", token
                        )

            event_summaries.append(
                _summarize_event_runs(
                    event=event,
                    runs_payload=runs_payload,
                    jobs_payload_by_run_id=jobs_payload_by_run_id,
                    required_job=required_job,
                    workflow_name=workflow_name,
                )
            )
        except FileNotFoundError:
            blocked = True
            event_summaries.append({"event": event, "ok": False, "error": "fixture missing"})
        except urllib.error.HTTPError as exc:
            if exc.code in (403, 404):
                blocked = True
                event_summaries.append(
                    {
                        "event": event,
                        "ok": False,
                        "error": f"http_{exc.code}",
                        "detail": "GitHub Actions API unavailable for this repository/token scope.",
                    }
                )
            else:
                event_summaries.append({"event": event, "ok": False, "error": f"http_{exc.code}"})
                report["errors"].append(f"actions API error ({event}): http_{exc.code}")
        except Exception as exc:  # pragma: no cover - defensive path
            event_summaries.append({"event": event, "ok": False, "error": str(exc)})
            report["errors"].append(f"actions error ({event}): {exc}")

    report["events"] = event_summaries
    if report["errors"]:
        report["status"] = "failed"
        return report
    if blocked:
        report["status"] = "blocked"
        return report
    report["status"] = (
        "passed" if all(bool(item.get("ok")) for item in event_summaries) else "failed"
    )
    return report


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify push/pull_request CI evidence for the Neo4j live integration job via GitHub API."
        )
    )
    parser.add_argument(
        "--repo",
        default=os.environ.get("GITHUB_REPOSITORY", ""),
        help="GitHub repo in owner/name format (default: $GITHUB_REPOSITORY)",
    )
    parser.add_argument(
        "--branch",
        default=os.environ.get("GITHUB_REF_NAME", "main"),
        help="Branch to verify (default: $GITHUB_REF_NAME or main)",
    )
    parser.add_argument(
        "--required-job",
        default=DEFAULT_REQUIRED_JOB,
        help=f"Required successful job name (default: {DEFAULT_REQUIRED_JOB})",
    )
    parser.add_argument(
        "--workflow-name",
        default=DEFAULT_WORKFLOW_NAME,
        help=f"Workflow name filter for runs (default: {DEFAULT_WORKFLOW_NAME})",
    )
    parser.add_argument(
        "--runs-per-event",
        type=int,
        default=20,
        help="How many recent runs to inspect per event (push/pull_request).",
    )
    parser.add_argument(
        "--token-env",
        default="GITHUB_TOKEN",
        help="Environment variable for GitHub API token (default: GITHUB_TOKEN).",
    )
    parser.add_argument(
        "--api-base",
        default="https://api.github.com",
        help="GitHub API base URL (default: https://api.github.com).",
    )
    parser.add_argument(
        "--fixture-dir",
        type=Path,
        default=None,
        help="Optional fixture directory for offline checks/tests (runs_*.json, jobs_<id>.json).",
    )
    parser.add_argument("--output", type=Path, default=None, help="Optional report output path")
    parser.add_argument("--stdout-json", action="store_true", help="Print report JSON to stdout")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    token = os.environ.get(args.token_env, "") if args.fixture_dir is None else None
    workflow_name = args.workflow_name.strip() if isinstance(args.workflow_name, str) else ""
    report = run_check(
        repo=args.repo,
        branch=args.branch,
        required_job=args.required_job,
        workflow_name=workflow_name or None,
        runs_per_event=max(1, args.runs_per_event),
        token=token,
        api_base=args.api_base,
        fixture_dir=args.fixture_dir,
    )
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote Neo4j CI rollout report: {args.output}")
    if args.stdout_json:
        print(json.dumps(report, indent=2))
    status = report.get("status")
    if status == "passed":
        return 0
    if status == "blocked":
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
