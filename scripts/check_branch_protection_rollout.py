#!/usr/bin/env python3
"""Verify branch-protection rollout and required CI green status from GitHub API."""

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

DEFAULT_REQUIRED_CHECKS = [
    "lint-and-test (3.11)",
    "lint-and-test (3.12)",
    "frontend-checks",
    "postgres-event-store-smoke",
]


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _github_get_json(api_base: str, route: str, token: str | None) -> dict[str, Any]:
    url = ensure_safe_http_url(
        f"{api_base.rstrip('/')}/{route.lstrip('/')}",
        block_private_hosts=False,
    )
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "chronicle-branch-protection-check",
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


def _required_settings_report(
    protection: dict[str, Any], required_checks: list[str]
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "exists": True,
        "required_checks_present": [],
        "missing_required_checks": [],
        "settings": {
            "require_pull_request_before_merge": False,
            "require_status_checks": False,
            "require_up_to_date_branches": False,
            "include_administrators": False,
            "allow_force_pushes": True,
            "allow_deletions": True,
        },
    }
    status_checks = protection.get("required_status_checks") or {}
    contexts = status_checks.get("contexts")
    present = {str(x) for x in contexts} if isinstance(contexts, list) else set()
    out["required_checks_present"] = sorted(c for c in required_checks if c in present)
    out["missing_required_checks"] = sorted(c for c in required_checks if c not in present)

    out["settings"]["require_pull_request_before_merge"] = bool(
        protection.get("required_pull_request_reviews")
    )
    out["settings"]["require_status_checks"] = bool(protection.get("required_status_checks"))
    out["settings"]["require_up_to_date_branches"] = bool(status_checks.get("strict") is True)
    enforce_admins = protection.get("enforce_admins") or {}
    out["settings"]["include_administrators"] = bool(enforce_admins.get("enabled") is True)
    allow_force_pushes = protection.get("allow_force_pushes") or {}
    out["settings"]["allow_force_pushes"] = bool(allow_force_pushes.get("enabled") is True)
    allow_deletions = protection.get("allow_deletions") or {}
    out["settings"]["allow_deletions"] = bool(allow_deletions.get("enabled") is True)
    return out


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
    required_checks: list[str],
) -> dict[str, Any]:
    workflow_runs = runs_payload.get("workflow_runs")
    if not isinstance(workflow_runs, list):
        return {"event": event, "ok": False, "error": "workflow_runs missing from API response"}
    completed = [r for r in workflow_runs if isinstance(r, dict) and r.get("status") == "completed"]
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
        missing = sorted(check for check in required_checks if check not in success_jobs)
        checked_runs.append(
            {
                "run_id": run_id,
                "run_name": _run_name(run),
                "ok": not missing,
                "missing_required_jobs": missing,
            }
        )
    ok = any(run.get("ok") is True for run in checked_runs)
    return {
        "event": event,
        "ok": ok,
        "runs_seen": len(workflow_runs),
        "completed_runs": len(completed),
        "successful_runs": len(successful),
        "checked_runs": checked_runs,
    }


def run_check(
    *,
    repo: str,
    branch: str,
    required_checks: list[str],
    runs_per_event: int,
    token: str | None,
    api_base: str = "https://api.github.com",
    fixture_dir: Path | None = None,
) -> dict[str, Any]:
    if "/" not in repo:
        raise ValueError("--repo must be in owner/name format")
    owner, name = repo.split("/", 1)

    report: dict[str, Any] = {
        "schema_version": 1,
        "generated_at": _utc_now(),
        "repo": repo,
        "branch": branch,
        "required_checks": required_checks,
        "status": "failed",
        "branch_protection": {},
        "ci_required_jobs": {},
        "errors": [],
    }

    # Branch protection
    protection: dict[str, Any] | None = None
    try:
        if fixture_dir is not None:
            protection = _load_json(fixture_dir / "protection.json")
        else:
            protection = _github_get_json(
                api_base, f"repos/{owner}/{name}/branches/{branch}/protection", token
            )
        report["branch_protection"] = _required_settings_report(protection, required_checks)
    except FileNotFoundError:
        report["branch_protection"] = {
            "exists": False,
            "error": "fixture protection.json not found",
        }
        report["status"] = "blocked"
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 404):
            report["branch_protection"] = {
                "exists": False,
                "error": f"http_{exc.code}",
                "detail": (
                    "Branch protection endpoint unavailable (permission or plan limitation). "
                    "This is a rollout blocker until repo plan/permissions allow enforcement."
                ),
            }
            report["status"] = "blocked"
        else:
            report["errors"].append(f"branch protection API error: http_{exc.code}")
    except Exception as exc:  # pragma: no cover - defensive path
        report["errors"].append(f"branch protection error: {exc}")

    jobs_payload_by_run_id: dict[int, dict[str, Any]] = {}
    event_summaries: list[dict[str, Any]] = []

    # CI event checks
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
            summary = _summarize_event_runs(
                event=event,
                runs_payload=runs_payload,
                jobs_payload_by_run_id=jobs_payload_by_run_id,
                required_checks=required_checks,
            )
            event_summaries.append(summary)
        except FileNotFoundError:
            event_summaries.append({"event": event, "ok": False, "error": "fixture missing"})
        except Exception as exc:  # pragma: no cover - defensive path
            event_summaries.append({"event": event, "ok": False, "error": str(exc)})

    report["ci_required_jobs"] = {"events": event_summaries}

    protection_blocked = report.get("status") == "blocked"
    if report["errors"]:
        report["status"] = "failed"
        return report

    if protection_blocked:
        return report

    protection_report = report.get("branch_protection") or {}
    missing_checks = protection_report.get("missing_required_checks") or []
    settings = protection_report.get("settings") or {}
    settings_ok = (
        settings.get("require_pull_request_before_merge") is True
        and settings.get("require_status_checks") is True
        and settings.get("require_up_to_date_branches") is True
        and settings.get("include_administrators") is True
        and settings.get("allow_force_pushes") is False
        and settings.get("allow_deletions") is False
    )
    ci_ok = all(bool(item.get("ok")) for item in event_summaries) if event_summaries else False
    report["status"] = "passed" if (not missing_checks and settings_ok and ci_ok) else "failed"
    return report


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify GitHub branch-protection rollout and required CI checks."
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
        "--required-check",
        action="append",
        default=[],
        help="Required status check name (repeatable). Defaults to Chronicle required jobs.",
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
        help="Optional fixture directory for offline checks/tests (protection.json, runs_*.json, jobs_<id>.json).",
    )
    parser.add_argument("--output", type=Path, default=None, help="Optional report output path")
    parser.add_argument("--stdout-json", action="store_true", help="Print report JSON to stdout")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    required_checks = args.required_check if args.required_check else DEFAULT_REQUIRED_CHECKS
    token = os.environ.get(args.token_env, "") if args.fixture_dir is None else None
    report = run_check(
        repo=args.repo,
        branch=args.branch,
        required_checks=required_checks,
        runs_per_event=max(1, args.runs_per_event),
        token=token,
        api_base=args.api_base,
        fixture_dir=args.fixture_dir,
    )
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote branch protection rollout report: {args.output}")
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
