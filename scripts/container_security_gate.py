#!/usr/bin/env python3
"""Gate container vulnerability reports (Trivy JSON) by severity thresholds."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _load_report(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _count_vulns(report: dict) -> tuple[int, int]:
    high = 0
    critical = 0
    for result in report.get("Results") or []:
        vulns = result.get("Vulnerabilities") or []
        for vuln in vulns:
            sev = str(vuln.get("Severity", "")).upper()
            if sev == "HIGH":
                high += 1
            elif sev == "CRITICAL":
                critical += 1
    return high, critical


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        action="append",
        required=True,
        help="Path to one Trivy JSON report (repeat for multiple reports).",
    )
    parser.add_argument("--max-high", type=int, default=0, help="Maximum allowed HIGH findings.")
    parser.add_argument(
        "--max-critical",
        type=int,
        default=0,
        help="Maximum allowed CRITICAL findings.",
    )
    args = parser.parse_args(argv)

    total_high = 0
    total_critical = 0
    for report_path in args.report:
        path = Path(report_path)
        if not path.is_file():
            print(f"[FAIL] Missing report: {path}")
            return 1
        report = _load_report(path)
        high, critical = _count_vulns(report)
        total_high += high
        total_critical += critical
        print(f"[INFO] {path}: HIGH={high}, CRITICAL={critical}")

    print(f"[INFO] Total: HIGH={total_high}, CRITICAL={total_critical}")
    if total_high > args.max_high or total_critical > args.max_critical:
        print(
            "[FAIL] Container vulnerability gate failed: "
            f"HIGH {total_high} > {args.max_high} or CRITICAL {total_critical} > {args.max_critical}"
        )
        return 1
    print("[PASS] Container vulnerability gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
