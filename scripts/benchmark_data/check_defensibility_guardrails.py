#!/usr/bin/env python3
"""Evaluate benchmark output against configurable guardrails."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Check defensibility benchmark guardrails")
    parser.add_argument(
        "--results",
        type=Path,
        default=Path("benchmark_defensibility_results.json"),
        help="Benchmark results JSON from run_defensibility_benchmark.py",
    )
    parser.add_argument("--min-success-rate", type=float, default=1.0)
    parser.add_argument("--min-average-support", type=float, default=1.0)
    parser.add_argument("--max-open-contradiction-rate", type=float, default=1.0)
    args = parser.parse_args()

    if not args.results.is_file():
        print(f"Results file not found: {args.results}", file=sys.stderr)
        return 1

    payload = json.loads(args.results.read_text(encoding="utf-8"))
    rows = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(rows, list) or not rows:
        print("Benchmark results payload missing non-empty 'results' list", file=sys.stderr)
        return 1

    total = len(rows)
    successful = 0
    support_sum = 0.0
    support_count = 0
    open_contradictions = 0

    for row in rows:
        if not isinstance(row, dict):
            continue
        metrics = row.get("metrics")
        error = row.get("error")
        if isinstance(metrics, dict) and error in (None, ""):
            successful += 1
            corroboration = metrics.get("corroboration")
            if isinstance(corroboration, dict):
                support_raw = corroboration.get("support_count")
                if isinstance(support_raw, (int, float)):
                    support_sum += float(support_raw)
                    support_count += 1
            if metrics.get("contradiction_status") == "open":
                open_contradictions += 1

    success_rate = successful / total if total else 0.0
    avg_support = support_sum / support_count if support_count else 0.0
    open_contradiction_rate = open_contradictions / successful if successful else 0.0

    summary = {
        "total": total,
        "successful": successful,
        "success_rate": round(success_rate, 4),
        "average_support_count": round(avg_support, 4),
        "open_contradiction_rate": round(open_contradiction_rate, 4),
        "thresholds": {
            "min_success_rate": args.min_success_rate,
            "min_average_support": args.min_average_support,
            "max_open_contradiction_rate": args.max_open_contradiction_rate,
        },
    }
    print(json.dumps(summary, indent=2))

    failed = False
    if success_rate < args.min_success_rate:
        print(
            f"Guardrail failed: success_rate={success_rate:.4f} < {args.min_success_rate:.4f}",
            file=sys.stderr,
        )
        failed = True
    if avg_support < args.min_average_support:
        print(
            f"Guardrail failed: average_support_count={avg_support:.4f} < {args.min_average_support:.4f}",
            file=sys.stderr,
        )
        failed = True
    if open_contradiction_rate > args.max_open_contradiction_rate:
        print(
            "Guardrail failed: "
            f"open_contradiction_rate={open_contradiction_rate:.4f} > {args.max_open_contradiction_rate:.4f}",
            file=sys.stderr,
        )
        failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
