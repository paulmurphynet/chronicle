#!/usr/bin/env python3
"""Summarize benchmark trust metrics and optional improvement vs a baseline."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

PROVENANCE_LABELS = ("strong", "medium", "weak", "challenged")


def _read_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ValueError(f"Results file not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Results payload must be a JSON object")

    rows = payload.get("results")
    if not isinstance(rows, list) or not rows:
        raise ValueError("Results payload missing non-empty 'results' list")

    normalized: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            normalized.append(row)
    if not normalized:
        raise ValueError("Results payload has no valid result rows")
    return normalized


def _is_success_row(row: dict[str, Any]) -> bool:
    metrics = row.get("metrics")
    error = row.get("error")
    return isinstance(metrics, dict) and error in (None, "")


def _support_count(metrics: dict[str, Any]) -> float:
    corroboration = metrics.get("corroboration")
    if isinstance(corroboration, dict):
        raw = corroboration.get("support_count")
        if isinstance(raw, (int, float)):
            return float(raw)
    return 0.0


def _round4(value: float) -> float:
    return round(value, 4)


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    scored = 0
    unscored = 0
    unsupported = 0
    support_sum = 0.0
    open_contradictions = 0
    provenance_counts = dict.fromkeys(PROVENANCE_LABELS, 0)

    for row in rows:
        if not _is_success_row(row):
            unscored += 1
            continue

        metrics = row["metrics"]
        assert isinstance(metrics, dict)
        scored += 1

        support = _support_count(metrics)
        support_sum += support
        if support <= 0:
            unsupported += 1

        provenance = metrics.get("provenance_quality")
        if provenance in provenance_counts:
            provenance_counts[str(provenance)] += 1

        if metrics.get("contradiction_status") == "open":
            open_contradictions += 1

    avg_support = support_sum / scored if scored else 0.0
    strict_unsupported_rate = unsupported / scored if scored else 1.0
    unscored_rate = unscored / total if total else 1.0
    effective_unsupported_rate = (unsupported + unscored) / total if total else 1.0
    open_contradiction_rate = open_contradictions / scored if scored else 0.0

    provenance_distribution = {
        label: _round4((count / scored) if scored else 0.0)
        for label, count in provenance_counts.items()
    }

    return {
        "counts": {
            "total_claims": total,
            "scored_claims": scored,
            "unscored_claims": unscored,
            "unsupported_scored_claims": unsupported,
            "open_contradictions": open_contradictions,
        },
        "rates": {
            "strict_unsupported_rate": _round4(strict_unsupported_rate),
            "unscored_rate": _round4(unscored_rate),
            "effective_unsupported_rate": _round4(effective_unsupported_rate),
            "open_contradiction_rate": _round4(open_contradiction_rate),
            "trust_progress_score": _round4(max(0.0, 1.0 - effective_unsupported_rate)),
        },
        "averages": {
            "support_count": _round4(avg_support),
        },
        "provenance_distribution": provenance_distribution,
    }


def compare_effective_unsupported(
    current_summary: dict[str, Any],
    baseline_summary: dict[str, Any],
) -> dict[str, Any]:
    current_rate = float(current_summary["rates"]["effective_unsupported_rate"])
    baseline_rate = float(baseline_summary["rates"]["effective_unsupported_rate"])
    absolute_change = current_rate - baseline_rate

    if baseline_rate > 0:
        relative_reduction = (baseline_rate - current_rate) / baseline_rate
    else:
        relative_reduction = 0.0 if current_rate <= 0 else -1.0

    return {
        "baseline_effective_unsupported_rate": _round4(baseline_rate),
        "current_effective_unsupported_rate": _round4(current_rate),
        "absolute_change": _round4(absolute_change),
        "relative_reduction": _round4(relative_reduction),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize benchmark trust metrics and compare current "
            "effective unsupported rate against a baseline."
        )
    )
    parser.add_argument(
        "--results",
        type=Path,
        default=Path("benchmark_defensibility_results.json"),
        help="Current benchmark results JSON",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help="Optional baseline benchmark results JSON for change comparison",
    )
    parser.add_argument("--max-effective-unsupported-rate", type=float, default=None)
    parser.add_argument("--max-unscored-rate", type=float, default=None)
    parser.add_argument("--min-effective-unsupported-reduction", type=float, default=None)
    args = parser.parse_args(argv)

    try:
        current_rows = _read_rows(args.results)
        current_summary = summarize_rows(current_rows)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    baseline_summary: dict[str, Any] | None = None
    comparison: dict[str, Any] | None = None
    if args.baseline is not None:
        try:
            baseline_rows = _read_rows(args.baseline)
            baseline_summary = summarize_rows(baseline_rows)
            comparison = compare_effective_unsupported(current_summary, baseline_summary)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
    elif args.min_effective_unsupported_reduction is not None:
        print(
            "--min-effective-unsupported-reduction requires --baseline",
            file=sys.stderr,
        )
        return 1

    payload: dict[str, Any] = {
        "results_path": str(args.results),
        "summary": current_summary,
    }
    if args.baseline is not None:
        payload["baseline_path"] = str(args.baseline)
    if baseline_summary is not None:
        payload["baseline_summary"] = baseline_summary
    if comparison is not None:
        payload["comparison"] = comparison
    payload["thresholds"] = {
        "max_effective_unsupported_rate": args.max_effective_unsupported_rate,
        "max_unscored_rate": args.max_unscored_rate,
        "min_effective_unsupported_reduction": args.min_effective_unsupported_reduction,
    }

    print(json.dumps(payload, indent=2))

    failed = False
    effective_rate = float(current_summary["rates"]["effective_unsupported_rate"])
    unscored_rate = float(current_summary["rates"]["unscored_rate"])

    if (
        args.max_effective_unsupported_rate is not None
        and effective_rate > args.max_effective_unsupported_rate
    ):
        print(
            "Threshold failed: "
            f"effective_unsupported_rate={effective_rate:.4f} > "
            f"{args.max_effective_unsupported_rate:.4f}",
            file=sys.stderr,
        )
        failed = True

    if args.max_unscored_rate is not None and unscored_rate > args.max_unscored_rate:
        print(
            f"Threshold failed: unscored_rate={unscored_rate:.4f} > {args.max_unscored_rate:.4f}",
            file=sys.stderr,
        )
        failed = True

    if args.min_effective_unsupported_reduction is not None:
        assert comparison is not None
        reduction = float(comparison["relative_reduction"])
        if reduction < args.min_effective_unsupported_reduction:
            print(
                "Threshold failed: "
                f"relative_reduction={reduction:.4f} < "
                f"{args.min_effective_unsupported_reduction:.4f}",
                file=sys.stderr,
            )
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
