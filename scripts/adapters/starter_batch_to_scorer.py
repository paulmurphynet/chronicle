#!/usr/bin/env python3
"""
Starter adapter: batch harness JSONL -> Chronicle scorer JSONL.

Input rows are expected to contain query/answer/evidence fields. For each row:
1) map fields to eval contract input,
2) run Chronicle standalone scorer logic in-process,
3) emit one JSON output row with original row metadata + scorer output.

Example:
  PYTHONPATH=. python3 scripts/adapters/starter_batch_to_scorer.py \
    --input runs.jsonl \
    --output scored.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from importlib import import_module
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_run_scorer = import_module("scripts.standalone_defensibility_scorer")._run_scorer


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch adapter: harness JSONL -> Chronicle scorer JSONL")
    parser.add_argument("--input", type=Path, default=None, help="Input JSONL file (default: stdin)")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSONL file (default: stdout)",
    )
    parser.add_argument("--query-key", default="query")
    parser.add_argument("--answer-key", default="answer")
    parser.add_argument("--evidence-key", default="evidence")
    parser.add_argument("--run-id-key", default="run_id")
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on first input/scoring error",
    )
    return parser.parse_args(argv)


def _load_lines(input_path: Path | None) -> list[str]:
    text = input_path.read_text(encoding="utf-8") if input_path else sys.stdin.read()
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def _format_output_row(
    *,
    row_index: int,
    run_id: str | None,
    chronicle: dict[str, Any],
    input_error: str | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "row_index": row_index,
        "run_id": run_id,
        "chronicle": chronicle,
    }
    if input_error:
        out["input_error"] = input_error
    out["ok"] = "error" not in chronicle and input_error is None
    return out


def _map_row_to_contract_input(
    obj: dict[str, Any],
    *,
    query_key: str,
    answer_key: str,
    evidence_key: str,
) -> tuple[dict[str, Any] | None, str | None]:
    if query_key not in obj:
        return None, f"missing_query_key:{query_key}"
    if answer_key not in obj:
        return None, f"missing_answer_key:{answer_key}"
    if evidence_key not in obj:
        return None, f"missing_evidence_key:{evidence_key}"
    contract_input = {
        "query": obj.get(query_key),
        "answer": obj.get(answer_key),
        "evidence": obj.get(evidence_key),
    }
    return contract_input, None


def run_rows(
    lines: list[str],
    *,
    query_key: str,
    answer_key: str,
    evidence_key: str,
    run_id_key: str,
    fail_fast: bool = False,
) -> tuple[list[dict[str, Any]], int]:
    outputs: list[dict[str, Any]] = []
    exit_code = 0

    for i, line in enumerate(lines):
        run_id: str | None = None
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            row = _format_output_row(
                row_index=i,
                run_id=None,
                chronicle={"contract_version": "1.0", "error": "invalid_input", "message": str(e)},
                input_error="invalid_json",
            )
            outputs.append(row)
            exit_code = 1
            if fail_fast:
                break
            continue

        if not isinstance(obj, dict):
            row = _format_output_row(
                row_index=i,
                run_id=None,
                chronicle={
                    "contract_version": "1.0",
                    "error": "invalid_input",
                    "message": "input row must be a JSON object",
                },
                input_error="invalid_row_shape",
            )
            outputs.append(row)
            exit_code = 1
            if fail_fast:
                break
            continue

        rid = obj.get(run_id_key)
        run_id = str(rid) if rid is not None else None
        contract_input, input_error = _map_row_to_contract_input(
            obj,
            query_key=query_key,
            answer_key=answer_key,
            evidence_key=evidence_key,
        )
        if contract_input is None:
            chronicle = {
                "contract_version": "1.0",
                "error": "invalid_input",
                "message": input_error,
            }
        else:
            chronicle = _run_scorer(json.dumps(contract_input))

        row = _format_output_row(
            row_index=i,
            run_id=run_id,
            chronicle=chronicle,
            input_error=input_error,
        )
        outputs.append(row)
        if input_error or chronicle.get("error"):
            exit_code = 1
            if fail_fast:
                break

    return outputs, exit_code


def _write_outputs(rows: list[dict[str, Any]], output_path: Path | None) -> None:
    text = "\n".join(json.dumps(r) for r in rows) + ("\n" if rows else "")
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    lines = _load_lines(args.input)
    if not lines:
        out = {
            "row_index": None,
            "run_id": None,
            "ok": False,
            "input_error": "no_input",
            "chronicle": {"contract_version": "1.0", "error": "invalid_input", "message": "empty input"},
        }
        _write_outputs([out], args.output)
        return 1

    rows, code = run_rows(
        lines,
        query_key=args.query_key,
        answer_key=args.answer_key,
        evidence_key=args.evidence_key,
        run_id_key=args.run_id_key,
        fail_fast=args.fail_fast,
    )
    _write_outputs(rows, args.output)
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
