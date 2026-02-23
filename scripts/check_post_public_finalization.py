#!/usr/bin/env python3
"""Aggregate post-public finalization evidence into one machine-readable report."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REQUIRED_VENUES = (
    "w3c_linked_data",
    "c2pa_ecosystem",
    "applied_research",
)
SENT_OR_BETTER = frozenset(("sent", "acknowledged", "feedback_received", "closed"))


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def _check_branch_protection(report: dict[str, Any]) -> dict[str, Any]:
    status = str(report.get("status") or "").strip().lower()
    passed = status == "passed"
    return {
        "name": "branch_protection_rollout",
        "status": "passed" if passed else ("blocked" if status == "blocked" else "failed"),
        "passed": passed,
        "detail": f"status={status or 'missing'}",
    }


def _check_neo4j_ci(report: dict[str, Any]) -> dict[str, Any]:
    status = str(report.get("status") or "").strip().lower()
    events = report.get("events")
    event_ok = (
        isinstance(events, list)
        and all(isinstance(item, dict) and bool(item.get("ok")) for item in events)
        and len(events) >= 2
    )
    passed = status == "passed" and event_ok
    return {
        "name": "neo4j_live_ci_rollout",
        "status": "passed" if passed else ("blocked" if status == "blocked" else "failed"),
        "passed": passed,
        "detail": f"status={status or 'missing'} event_ok={event_ok}",
    }


def _check_standards_dispatch(
    log: dict[str, Any], required_venues: tuple[str, ...]
) -> dict[str, Any]:
    venues_raw = log.get("venues")
    if not isinstance(venues_raw, list):
        return {
            "name": "external_standards_dispatch",
            "status": "blocked",
            "passed": False,
            "detail": "venues list missing",
            "missing_venues": list(required_venues),
            "pending_venues": [],
        }

    venue_map: dict[str, dict[str, Any]] = {}
    for item in venues_raw:
        if not isinstance(item, dict):
            continue
        venue = str(item.get("venue") or "").strip()
        if venue:
            venue_map[venue] = item

    missing: list[str] = []
    pending: list[str] = []
    for venue in required_venues:
        item = venue_map.get(venue)
        if item is None:
            missing.append(venue)
            continue
        status = str(item.get("status") or "").strip().lower()
        sent_at = str(item.get("sent_at") or "").strip().lower()
        if status not in SENT_OR_BETTER or not sent_at or sent_at == "pending":
            pending.append(venue)

    passed = not missing and not pending
    check_status = "passed" if passed else ("blocked" if missing else "failed")
    return {
        "name": "external_standards_dispatch",
        "status": check_status,
        "passed": passed,
        "detail": (
            f"required={len(required_venues)} missing={len(missing)} pending={len(pending)} "
            f"outreach_status={str(log.get('outreach_status') or '') or 'missing'}"
        ),
        "missing_venues": missing,
        "pending_venues": pending,
    }


def run_check(
    *,
    branch_protection_report: dict[str, Any],
    neo4j_ci_report: dict[str, Any],
    standards_dispatch_log: dict[str, Any],
    required_venues: tuple[str, ...],
) -> dict[str, Any]:
    checks = [
        _check_branch_protection(branch_protection_report),
        _check_neo4j_ci(neo4j_ci_report),
        _check_standards_dispatch(standards_dispatch_log, required_venues),
    ]
    if any(check["status"] == "blocked" for check in checks):
        status = "blocked"
    elif all(check["passed"] for check in checks):
        status = "passed"
    else:
        status = "failed"
    return {
        "schema_version": 1,
        "generated_at": _utc_now(),
        "status": status,
        "checks": checks,
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aggregate post-public finalization evidence into one report."
    )
    parser.add_argument(
        "--branch-protection-report",
        type=Path,
        default=Path("reports/branch_protection_rollout_report.json"),
        help="Path to branch protection rollout report JSON.",
    )
    parser.add_argument(
        "--neo4j-ci-report",
        type=Path,
        default=Path("reports/neo4j_live_ci_report.json"),
        help="Path to Neo4j live CI rollout report JSON.",
    )
    parser.add_argument(
        "--standards-dispatch-log",
        type=Path,
        default=Path("reports/standards_submissions/v0.3/external_review_dispatch_log.json"),
        help="Path to external standards dispatch log JSON.",
    )
    parser.add_argument(
        "--required-venue",
        action="append",
        default=[],
        help="Required standards venue key (repeatable). Defaults to Chronicle W-07 venues.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/post_public_finalization_report.json"),
        help="Output path for aggregate report JSON.",
    )
    parser.add_argument("--stdout-json", action="store_true", help="Print report JSON to stdout")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    required_venues = tuple(args.required_venue) if args.required_venue else REQUIRED_VENUES
    try:
        branch_report = _load_json(args.branch_protection_report)
        neo4j_report = _load_json(args.neo4j_ci_report)
        standards_log = _load_json(args.standards_dispatch_log)
    except FileNotFoundError as exc:
        print(f"Missing required artifact: {exc}")
        return 2
    except ValueError as exc:
        print(f"Invalid artifact JSON: {exc}")
        return 2

    report = run_check(
        branch_protection_report=branch_report,
        neo4j_ci_report=neo4j_report,
        standards_dispatch_log=standards_log,
        required_venues=required_venues,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote post-public finalization report: {args.output}")
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
