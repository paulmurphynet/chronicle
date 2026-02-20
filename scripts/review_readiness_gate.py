#!/usr/bin/env python3
"""One-shot review readiness gate for investigation handoff/CI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from chronicle.store.project import project_exists
from chronicle.store.session import ChronicleSession


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate investigation readiness using policy compatibility and reviewer-decision posture."
        )
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=Path("."),
        help="Chronicle project path (default: current directory).",
    )
    parser.add_argument(
        "--investigation-uid",
        required=True,
        help="Investigation UID to evaluate.",
    )
    parser.add_argument(
        "--viewing-profile-id",
        default=None,
        help="Optional viewing policy profile id for compatibility preflight.",
    )
    parser.add_argument(
        "--built-under-profile-id",
        default=None,
        help="Optional built-under policy profile id override.",
    )
    parser.add_argument(
        "--built-under-policy-version",
        default=None,
        help="Optional built-under policy version override.",
    )
    parser.add_argument(
        "--decision-limit",
        type=int,
        default=500,
        help="Maximum decision rows to scan from reviewer ledger (default: 500).",
    )
    parser.add_argument(
        "--max-unresolved-tensions",
        type=int,
        default=0,
        help="Fail when unresolved tensions exceed this count (default: 0).",
    )
    parser.add_argument(
        "--max-human-overrides",
        type=int,
        default=None,
        help="Optional maximum allowed human_overrode_count.",
    )
    parser.add_argument(
        "--allow-policy-deltas",
        action="store_true",
        help="Do not fail when built-under and viewing policy differ.",
    )
    parser.add_argument(
        "--require-built-under-policy",
        action="store_true",
        help="Fail if no built-under policy is recorded/resolved.",
    )
    parser.add_argument(
        "--require-decision-rationale",
        action="store_true",
        help="Fail when human_overrode/human_confirmed entries are missing rationale.",
    )
    parser.add_argument(
        "--require-chain-of-custody-report",
        action="store_true",
        help="Fail if no chain-of-custody report exists in review packet metadata.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional JSON report output path.",
    )
    parser.add_argument(
        "--stdout-json",
        action="store_true",
        help="Print full report JSON to stdout.",
    )
    return parser.parse_args(argv)


def _check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def _run(args: argparse.Namespace) -> dict[str, Any]:
    project_path = args.path.resolve()
    if not project_exists(project_path):
        raise FileNotFoundError(f"Not a Chronicle project (no chronicle.db): {project_path}")

    with ChronicleSession(project_path) as session:
        preflight = session.get_policy_compatibility_preflight(
            args.investigation_uid,
            viewing_profile_id=args.viewing_profile_id,
            built_under_profile_id=args.built_under_profile_id,
            built_under_policy_version=args.built_under_policy_version,
        )
        ledger = session.get_reviewer_decision_ledger(
            args.investigation_uid,
            limit=max(1, args.decision_limit),
        )
        chain_reports_count = 0
        if args.require_chain_of_custody_report:
            packet = session.get_review_packet(
                args.investigation_uid,
                include_reasoning_briefs=False,
                decision_limit=max(1, args.decision_limit),
                limit_claims=200,
                viewing_profile_id=args.viewing_profile_id,
                built_under_profile_id=args.built_under_profile_id,
                built_under_policy_version=args.built_under_policy_version,
            )
            chain_reports_count = len(packet.get("chain_of_custody_reports") or [])

    summary = ledger.get("summary") or {}
    unresolved_tensions_count = int(summary.get("unresolved_tensions_count") or 0)
    human_overrode_count = int(summary.get("human_overrode_count") or 0)
    human_confirmed_count = int(summary.get("human_confirmed_count") or 0)
    total_decisions = int(summary.get("total_decisions") or 0)

    built_under = str(preflight.get("built_under") or "")
    viewing_under = str(preflight.get("viewing_under") or "")
    deltas = preflight.get("deltas") or []
    deltas_count = len(deltas)

    rationale_missing_count = 0
    for decision in ledger.get("decisions") or []:
        kind = str(decision.get("decision_kind") or "")
        if kind not in {"human_overrode", "human_confirmed"}:
            continue
        rationale = str(decision.get("rationale") or "").strip()
        if not rationale:
            rationale_missing_count += 1

    policy_clean = (not built_under or not viewing_under or built_under == viewing_under) and (
        deltas_count == 0
    )

    checks: list[dict[str, Any]] = []
    checks.append(
        _check(
            "policy_compatibility",
            args.allow_policy_deltas or policy_clean,
            (
                f"built_under={built_under or '(none)'} "
                f"viewing_under={viewing_under or '(none)'} deltas={deltas_count}"
            ),
        )
    )
    checks.append(
        _check(
            "unresolved_tensions_threshold",
            unresolved_tensions_count <= args.max_unresolved_tensions,
            (
                f"unresolved_tensions={unresolved_tensions_count} "
                f"max_allowed={args.max_unresolved_tensions}"
            ),
        )
    )
    if args.max_human_overrides is not None:
        checks.append(
            _check(
                "human_overrides_threshold",
                human_overrode_count <= args.max_human_overrides,
                f"human_overrode_count={human_overrode_count} max_allowed={args.max_human_overrides}",
            )
        )
    if args.require_built_under_policy:
        checks.append(
            _check(
                "built_under_policy_present",
                bool(built_under.strip()),
                f"built_under={built_under or '(none)'}",
            )
        )
    if args.require_decision_rationale:
        checks.append(
            _check(
                "decision_rationale_present",
                rationale_missing_count == 0,
                f"missing_rationale_decisions={rationale_missing_count}",
            )
        )
    if args.require_chain_of_custody_report:
        checks.append(
            _check(
                "chain_of_custody_report_present",
                chain_reports_count > 0,
                f"chain_of_custody_reports={chain_reports_count}",
            )
        )

    passed = all(check["passed"] for check in checks)
    return {
        "status": "passed" if passed else "failed",
        "project_path": str(project_path),
        "investigation_uid": args.investigation_uid,
        "inputs": {
            "viewing_profile_id": args.viewing_profile_id,
            "built_under_profile_id": args.built_under_profile_id,
            "built_under_policy_version": args.built_under_policy_version,
            "decision_limit": args.decision_limit,
            "max_unresolved_tensions": args.max_unresolved_tensions,
            "max_human_overrides": args.max_human_overrides,
            "allow_policy_deltas": args.allow_policy_deltas,
            "require_built_under_policy": args.require_built_under_policy,
            "require_decision_rationale": args.require_decision_rationale,
            "require_chain_of_custody_report": args.require_chain_of_custody_report,
        },
        "metrics": {
            "policy_deltas_count": deltas_count,
            "built_under": built_under,
            "viewing_under": viewing_under,
            "unresolved_tensions_count": unresolved_tensions_count,
            "human_overrode_count": human_overrode_count,
            "human_confirmed_count": human_confirmed_count,
            "total_decisions": total_decisions,
            "missing_decision_rationale_count": rationale_missing_count,
            "chain_of_custody_reports_count": chain_reports_count,
        },
        "checks": checks,
    }


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        report = _run(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    if args.output is not None:
        out = args.output.resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote readiness gate report: {out}")

    if args.stdout_json:
        print(json.dumps(report, indent=2))
    else:
        status = report["status"].upper()
        print(f"[{status}] investigation={report['investigation_uid']}")
        for check in report["checks"]:
            mark = "PASS" if check["passed"] else "FAIL"
            print(f"  [{mark}] {check['name']}: {check['detail']}")

    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
