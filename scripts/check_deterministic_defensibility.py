#!/usr/bin/env python3
"""Check deterministic defensibility outputs for identical scorer inputs."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from importlib import import_module
from pathlib import Path
from typing import Any

# Allow direct invocation from repo root without requiring PYTHONPATH.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

run_scorer = import_module("scripts.standalone_defensibility_scorer")._run_scorer

DEFAULT_INPUT = {
    "query": "What happened to invoice INV-204 recognition timing?",
    "answer": "The timing remains disputed and needs exception tracking.",
    "evidence": [
        "Ledger entry recognized INV-204 revenue on 2024-03-31.",
        "Delivery receipt is signed 2024-04-02, indicating later fulfillment.",
    ],
}


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _normalize(output: dict[str, Any]) -> dict[str, Any]:
    """Normalize scorer output by removing non-deterministic identifiers."""
    clone = dict(output)
    clone.pop("claim_uid", None)
    return clone


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ensure same scorer input yields the same defensibility metrics."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Optional JSON input file (defaults to built-in deterministic payload).",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=3,
        help="Number of repeated scorer runs (default: 3).",
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


def _load_input(path: Path | None) -> dict[str, Any]:
    if path is None:
        return DEFAULT_INPUT
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Input payload must be a JSON object")
    return payload


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        payload = _load_input(args.input)
    except Exception as exc:
        report = {
            "check": "deterministic_defensibility",
            "generated_at": _utc_now(),
            "status": "failed",
            "error": f"invalid_input:{exc}",
            "rounds_requested": int(args.rounds),
            "runs": [],
        }
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
            print(f"Wrote deterministic check report: {args.output}")
        if args.stdout_json:
            print(json.dumps(report, indent=2))
        return 1

    rounds = max(2, int(args.rounds))
    payload_json = json.dumps(payload)

    normalized_runs: list[dict[str, Any]] = []
    raw_runs: list[dict[str, Any]] = []
    mismatch_at: int | None = None
    baseline: dict[str, Any] | None = None
    error: str | None = None

    for idx in range(rounds):
        output = run_scorer(payload_json)
        if output.get("error"):
            error = f"scorer_error_round_{idx + 1}:{output.get('error')}"
            raw_runs.append(output)
            break
        normalized = _normalize(output)
        raw_runs.append(output)
        normalized_runs.append(normalized)
        if baseline is None:
            baseline = normalized
            continue
        if normalized != baseline and mismatch_at is None:
            mismatch_at = idx + 1

    stable = error is None and mismatch_at is None
    status = "passed" if stable else "failed"
    report: dict[str, Any] = {
        "check": "deterministic_defensibility",
        "generated_at": _utc_now(),
        "status": status,
        "rounds_requested": rounds,
        "stable": stable,
        "mismatch_round": mismatch_at,
        "error": error,
        "input": payload,
        "normalized_runs": normalized_runs,
        "runs": raw_runs,
    }

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote deterministic check report: {args.output}")
    if args.stdout_json:
        print(json.dumps(report, indent=2))
    return 0 if stable else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
