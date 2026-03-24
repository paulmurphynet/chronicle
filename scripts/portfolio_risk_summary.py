#!/usr/bin/env python3
"""Project-level portfolio risk summary across investigations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from chronicle.store.project import project_exists
from chronicle.store.session import ChronicleSession


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _round4(value: float) -> float:
    return round(value, 4)


def _portfolio_posture(
    *,
    unresolved_tensions_count: int,
    human_overrode_count: int,
    policy_deltas_count: int,
    policy_has_message: bool,
) -> str:
    if unresolved_tensions_count > 0:
        return "blocked"
    if human_overrode_count > 0 or policy_deltas_count > 0:
        return "review_required"
    if policy_has_message:
        return "insufficient_policy_context"
    return "ready"


def _risk_score(
    *,
    unresolved_tensions_count: int,
    human_overrode_count: int,
    policy_deltas_count: int,
    policy_has_message: bool,
) -> int:
    score = 0
    score += unresolved_tensions_count * 5
    score += human_overrode_count * 3
    score += policy_deltas_count
    if policy_has_message:
        score += 1
    return score


def build_portfolio_risk_summary(
    project_path: Path,
    *,
    decision_limit: int = 500,
    include_archived: bool = False,
    viewing_profile_id: str | None = None,
    built_under_profile_id: str | None = None,
    built_under_policy_version: str | None = None,
) -> dict[str, Any]:
    resolved_project_path = project_path.resolve()
    if not project_exists(resolved_project_path):
        raise FileNotFoundError(
            f"Not a Chronicle project (no chronicle.db): {resolved_project_path}"
        )

    inv_rows: list[dict[str, Any]] = []
    with ChronicleSession(resolved_project_path) as session:
        investigations = session.read_model.list_investigations()
        investigations_sorted = sorted(
            investigations,
            key=lambda inv: (inv.created_at or "", inv.investigation_uid),
        )
        for inv in investigations_sorted:
            if not include_archived and bool(inv.is_archived):
                continue

            ledger = session.get_reviewer_decision_ledger(
                inv.investigation_uid,
                limit=max(1, decision_limit),
            )
            preflight = session.get_policy_compatibility_preflight(
                inv.investigation_uid,
                viewing_profile_id=viewing_profile_id,
                built_under_profile_id=built_under_profile_id,
                built_under_policy_version=built_under_policy_version,
            )

            summary = ledger.get("summary") or {}
            unresolved_tensions_count = _safe_int(summary.get("unresolved_tensions_count"))
            human_overrode_count = _safe_int(summary.get("human_overrode_count"))
            human_confirmed_count = _safe_int(summary.get("human_confirmed_count"))
            total_decisions = _safe_int(summary.get("total_decisions"))
            policy_deltas_count = len(preflight.get("deltas") or [])
            policy_has_message = bool(str(preflight.get("message") or "").strip())
            posture = _portfolio_posture(
                unresolved_tensions_count=unresolved_tensions_count,
                human_overrode_count=human_overrode_count,
                policy_deltas_count=policy_deltas_count,
                policy_has_message=policy_has_message,
            )
            score = _risk_score(
                unresolved_tensions_count=unresolved_tensions_count,
                human_overrode_count=human_overrode_count,
                policy_deltas_count=policy_deltas_count,
                policy_has_message=policy_has_message,
            )
            override_rate = _round4(
                (human_overrode_count / total_decisions) if total_decisions > 0 else 0.0
            )

            inv_rows.append(
                {
                    "investigation_uid": inv.investigation_uid,
                    "title": inv.title,
                    "created_at": inv.created_at,
                    "is_archived": bool(inv.is_archived),
                    "current_tier": inv.current_tier,
                    "metrics": {
                        "unresolved_tensions_count": unresolved_tensions_count,
                        "human_overrode_count": human_overrode_count,
                        "human_confirmed_count": human_confirmed_count,
                        "total_decisions": total_decisions,
                        "override_rate": override_rate,
                        "policy_deltas_count": policy_deltas_count,
                    },
                    "policy": {
                        "built_under": preflight.get("built_under"),
                        "viewing_under": preflight.get("viewing_under"),
                        "message": preflight.get("message"),
                    },
                    "readiness_posture": posture,
                    "risk_score": score,
                }
            )

    ranked = sorted(
        inv_rows,
        key=lambda row: (
            -_safe_int(row.get("risk_score")),
            -_safe_int((row.get("metrics") or {}).get("unresolved_tensions_count")),
            -_safe_int((row.get("metrics") or {}).get("human_overrode_count")),
            str(row.get("created_at") or ""),
            str(row.get("investigation_uid") or ""),
        ),
    )
    for idx, row in enumerate(ranked, start=1):
        row["risk_rank"] = idx

    total_investigations = len(ranked)
    total_unresolved = sum(
        _safe_int((row.get("metrics") or {}).get("unresolved_tensions_count")) for row in ranked
    )
    total_overrides = sum(
        _safe_int((row.get("metrics") or {}).get("human_overrode_count")) for row in ranked
    )
    investigations_with_unresolved = sum(
        1
        for row in ranked
        if _safe_int((row.get("metrics") or {}).get("unresolved_tensions_count")) > 0
    )
    investigations_with_overrides = sum(
        1 for row in ranked if _safe_int((row.get("metrics") or {}).get("human_overrode_count")) > 0
    )
    readiness_counts = {
        "ready": 0,
        "review_required": 0,
        "blocked": 0,
        "insufficient_policy_context": 0,
    }
    for row in ranked:
        posture = str(row.get("readiness_posture") or "")
        if posture in readiness_counts:
            readiness_counts[posture] += 1

    top_override_row = max(
        ranked,
        key=lambda row: (
            _safe_int((row.get("metrics") or {}).get("human_overrode_count")),
            str(row.get("investigation_uid") or ""),
        ),
        default=None,
    )
    top_override_count = (
        _safe_int((top_override_row.get("metrics") or {}).get("human_overrode_count"))
        if top_override_row is not None
        else 0
    )
    top_override_uid = (
        str(top_override_row.get("investigation_uid")) if top_override_row is not None else None
    )
    top_share = (top_override_count / total_overrides) if total_overrides > 0 else 0.0
    hhi = 0.0
    if total_overrides > 0:
        for row in ranked:
            share = (
                _safe_int((row.get("metrics") or {}).get("human_overrode_count")) / total_overrides
            )
            hhi += share * share

    aggregate = {
        "total_investigations": total_investigations,
        "total_unresolved_tensions": total_unresolved,
        "investigations_with_unresolved_tensions": investigations_with_unresolved,
        "unresolved_tension_rate": _round4(
            (investigations_with_unresolved / total_investigations)
            if total_investigations > 0
            else 0.0
        ),
        "total_human_overrides": total_overrides,
        "investigations_with_human_overrides": investigations_with_overrides,
        "human_override_rate": _round4(
            (investigations_with_overrides / total_investigations)
            if total_investigations > 0
            else 0.0
        ),
        "override_concentration": {
            "top_investigation_uid": top_override_uid,
            "top_investigation_override_count": top_override_count,
            "top_investigation_share": _round4(top_share),
            "hhi": _round4(hhi),
        },
        "readiness_posture_counts": readiness_counts,
        "average_risk_score": _round4(
            (sum(_safe_float(row.get("risk_score")) for row in ranked) / total_investigations)
            if total_investigations > 0
            else 0.0
        ),
    }

    return {
        "project_path": str(resolved_project_path),
        "inputs": {
            "decision_limit": decision_limit,
            "include_archived": include_archived,
            "viewing_profile_id": viewing_profile_id,
            "built_under_profile_id": built_under_profile_id,
            "built_under_policy_version": built_under_policy_version,
        },
        "aggregate": aggregate,
        "investigations": ranked,
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize portfolio-level risk posture across investigations "
            "(unresolved tensions, override concentration, readiness posture)."
        )
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=Path("."),
        help="Chronicle project path (default: current directory).",
    )
    parser.add_argument(
        "--decision-limit",
        type=int,
        default=500,
        help="Maximum decision rows per investigation to scan (default: 500).",
    )
    parser.add_argument(
        "--include-archived",
        action="store_true",
        help="Include archived investigations.",
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
        "--output",
        type=Path,
        default=None,
        help="Optional JSON output path.",
    )
    parser.add_argument(
        "--stdout-json",
        action="store_true",
        help="Print full report JSON to stdout.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        report = build_portfolio_risk_summary(
            args.path,
            decision_limit=max(1, args.decision_limit),
            include_archived=bool(args.include_archived),
            viewing_profile_id=args.viewing_profile_id,
            built_under_profile_id=args.built_under_profile_id,
            built_under_policy_version=args.built_under_policy_version,
        )
    except (FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Portfolio risk summary failed: {e}", file=sys.stderr)
        return 1

    out_json = json.dumps(report, indent=2)
    if args.output is not None:
        out = args.output.resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(out_json, encoding="utf-8")
        print(f"Wrote portfolio risk summary: {out}")
    if args.stdout_json:
        print(out_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
