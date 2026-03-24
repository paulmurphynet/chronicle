#!/usr/bin/env python3
"""Validate adapter output rows that embed Chronicle eval-contract payloads."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROVENANCE_VALUES = {"strong", "medium", "weak", "challenged"}
CONTRADICTION_VALUES = {"none", "open", "acknowledged", "resolved"}
ERROR_VALUES = {"invalid_input", "no_investigation", "no_claim", "no_defensibility_score"}


def _as_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_success(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload.get("claim_uid"), str) or not payload.get("claim_uid"):
        errors.append("missing_or_invalid_claim_uid")
    pq = payload.get("provenance_quality")
    if pq not in PROVENANCE_VALUES:
        errors.append("invalid_provenance_quality")
    corroboration = payload.get("corroboration")
    if not isinstance(corroboration, dict):
        errors.append("missing_or_invalid_corroboration")
    else:
        for field in ("support_count", "challenge_count", "independent_sources_count"):
            if not _as_int(corroboration.get(field)):
                errors.append(f"invalid_corroboration_{field}")
    cs = payload.get("contradiction_status")
    if cs not in CONTRADICTION_VALUES:
        errors.append("invalid_contradiction_status")
    return errors


def _validate_error(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    err = payload.get("error")
    if not isinstance(err, str):
        errors.append("missing_or_invalid_error")
    elif err not in ERROR_VALUES:
        errors.append("unknown_error_value")
    return errors


def validate_contract_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    version = payload.get("contract_version")
    if version is not None and version != "1.0":
        errors.append("invalid_contract_version")

    if "error" in payload:
        errors.extend(_validate_error(payload))
        return errors
    errors.extend(_validate_success(payload))
    return errors


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate adapter output rows against eval contract"
    )
    parser.add_argument("--input", type=Path, required=True, help="Adapter output JSONL file")
    parser.add_argument(
        "--wrapped-key",
        default="chronicle",
        help=(
            "Field containing Chronicle payload in each row. "
            "Use empty string to validate rows as direct Chronicle payloads."
        ),
    )
    parser.add_argument(
        "--allow-unknown-error",
        action="store_true",
        help="Allow error values outside known contract errors",
    )
    return parser.parse_args(argv)


def _load_rows(path: Path) -> list[tuple[int, dict[str, Any] | None, str | None]]:
    rows: list[tuple[int, dict[str, Any] | None, str | None]] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        ln = line.strip()
        if not ln:
            continue
        try:
            obj = json.loads(ln)
        except json.JSONDecodeError as e:
            rows.append((i, None, f"invalid_json:{e}"))
            continue
        if not isinstance(obj, dict):
            rows.append((i, None, "row_not_object"))
            continue
        rows.append((i, obj, None))
    return rows


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if not args.input.is_file():
        print(f"Input file not found: {args.input}", file=sys.stderr)
        return 1

    rows = _load_rows(args.input)
    if not rows:
        print("No rows found in input JSONL", file=sys.stderr)
        return 1

    wrapped_key = args.wrapped_key.strip()
    invalid_rows: list[dict[str, Any]] = []
    valid = 0

    for idx, row, row_error in rows:
        if row_error:
            invalid_rows.append({"row_index": idx, "errors": [row_error]})
            continue
        assert row is not None
        payload = row if not wrapped_key else row.get(wrapped_key)
        if not isinstance(payload, dict):
            invalid_rows.append(
                {"row_index": idx, "errors": [f"missing_wrapped_payload:{wrapped_key}"]}
            )
            continue
        errors = validate_contract_payload(payload)
        if args.allow_unknown_error:
            errors = [e for e in errors if e != "unknown_error_value"]
        if errors:
            invalid_rows.append({"row_index": idx, "errors": errors})
            continue
        valid += 1

    summary = {
        "input_path": str(args.input),
        "rows_total": len(rows),
        "rows_valid": valid,
        "rows_invalid": len(invalid_rows),
        "wrapped_key": wrapped_key or None,
    }
    print(json.dumps(summary, indent=2))
    if invalid_rows:
        print(json.dumps({"invalid_rows": invalid_rows[:50]}, indent=2), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
