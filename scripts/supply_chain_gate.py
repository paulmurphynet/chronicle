#!/usr/bin/env python3
"""Evaluate supply-chain scan reports and fail on threshold breaches."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _load_json(path: Path) -> object:
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _count_pip_vulns(report: object) -> int:
    if isinstance(report, dict):
        # pip-audit has emitted both list and dict shapes across versions.
        deps = report.get("dependencies")
        if isinstance(deps, list):
            if not deps and "vulnerabilities" not in report:
                raise ValueError(
                    "pip audit report has no dependencies; audit likely did not execute"
                )
            total = 0
            for dep in deps:
                if not isinstance(dep, dict):
                    raise ValueError("pip dependency entry must be an object")
                vulns = dep.get("vulns")
                if not isinstance(vulns, list):
                    raise ValueError("pip dependency entry missing 'vulns' list")
                total += len(vulns)
            return total
        vulns = report.get("vulnerabilities")
        if isinstance(vulns, list):
            return len(vulns)
        raise ValueError("pip report missing vulnerabilities/dependencies structure")
    if isinstance(report, list):
        total = 0
        for dep in report:
            if not isinstance(dep, dict):
                raise ValueError("pip dependency entry must be an object")
            vulns = dep.get("vulns")
            if not isinstance(vulns, list):
                raise ValueError("pip dependency entry missing 'vulns' list")
            total += len(vulns)
        if not report:
            raise ValueError("pip dependency report is empty")
        return total
    raise ValueError("unsupported pip audit report format")


def _count_npm_severity(report: object, severity: str) -> int:
    if not isinstance(report, dict):
        raise ValueError("npm report must be an object")
    if isinstance(report.get("error"), dict):
        summary = report["error"].get("summary")
        raise ValueError(f"npm audit error: {summary or 'unknown'}")
    metadata = report.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("npm report missing metadata")
    vulns = metadata.get("vulnerabilities")
    if not isinstance(vulns, dict):
        raise ValueError("npm report missing metadata.vulnerabilities")
    value = vulns.get(severity)
    if isinstance(value, int):
        return value
    raise ValueError(f"npm report missing vulnerabilities.{severity}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gate supply-chain scan outputs")
    parser.add_argument("--pip-report", type=Path, required=True)
    parser.add_argument("--npm-report", type=Path, required=True)
    parser.add_argument("--max-python-vulns", type=int, default=0)
    parser.add_argument("--max-high", type=int, default=0)
    parser.add_argument("--max-critical", type=int, default=0)
    args = parser.parse_args(argv)

    pip_report = _load_json(args.pip_report)
    npm_report = _load_json(args.npm_report)

    try:
        python_vulns = _count_pip_vulns(pip_report)
        npm_high = _count_npm_severity(npm_report, "high")
        npm_critical = _count_npm_severity(npm_report, "critical")
    except ValueError as exc:
        print(f"Invalid audit report: {exc}", file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "python_vulns": python_vulns,
                "npm_high": npm_high,
                "npm_critical": npm_critical,
                "thresholds": {
                    "max_python_vulns": args.max_python_vulns,
                    "max_high": args.max_high,
                    "max_critical": args.max_critical,
                },
            },
            indent=2,
        )
    )

    failed = False
    if python_vulns > args.max_python_vulns:
        print(
            f"Python vulnerability count {python_vulns} exceeds max {args.max_python_vulns}",
            file=sys.stderr,
        )
        failed = True
    if npm_high > args.max_high:
        print(f"npm high vulnerabilities {npm_high} exceeds max {args.max_high}", file=sys.stderr)
        failed = True
    if npm_critical > args.max_critical:
        print(
            f"npm critical vulnerabilities {npm_critical} exceeds max {args.max_critical}",
            file=sys.stderr,
        )
        failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
