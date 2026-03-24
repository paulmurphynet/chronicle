#!/usr/bin/env python3
"""
RAGAS batch adapter: RAGAS-style rows -> Chronicle scorer JSONL.

This adapter is a convenience layer over the Chronicle eval contract for common
RAGAS row shapes. It auto-detects fields by default:

- query: question | user_input | query | input
- answer: answer | response | output
- evidence: contexts | retrieved_contexts | evidence
- run id: run_id | id | sample_id

Input can be JSONL or a JSON array of objects.

Examples:
  PYTHONPATH=. python3 scripts/adapters/ragas_batch_to_chronicle.py \
    --input runs_ragas.jsonl --output scored.jsonl

  PYTHONPATH=. python3 scripts/adapters/ragas_batch_to_chronicle.py \
    --input runs_ragas.json --input-format json --output scored.jsonl

  PYTHONPATH=. python3 scripts/adapters/ragas_batch_to_chronicle.py \
    --input runs.jsonl --query-key payload.question --answer-key payload.answer --contexts-key payload.contexts
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

DEFAULT_QUERY_KEYS = ("question", "user_input", "query", "input")
DEFAULT_ANSWER_KEYS = ("answer", "response", "output")
DEFAULT_CONTEXT_KEYS = ("contexts", "retrieved_contexts", "evidence")
DEFAULT_RUN_ID_KEYS = ("run_id", "id", "sample_id")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RAGAS adapter: rows -> Chronicle scorer JSONL")
    parser.add_argument("--input", type=Path, default=None, help="Input file (default: stdin)")
    parser.add_argument(
        "--output", type=Path, default=None, help="Output JSONL file (default: stdout)"
    )
    parser.add_argument(
        "--input-format",
        choices=("auto", "jsonl", "json"),
        default="auto",
        help="Input format: newline-delimited JSON (jsonl), JSON array/object (json), or auto (default).",
    )
    parser.add_argument(
        "--query-key", default=None, help="Query key/path override (dot-separated supported)"
    )
    parser.add_argument(
        "--answer-key", default=None, help="Answer key/path override (dot-separated supported)"
    )
    parser.add_argument(
        "--contexts-key",
        default=None,
        help="Evidence contexts key/path override (dot-separated supported)",
    )
    parser.add_argument(
        "--run-id-key", default=None, help="Run id key/path override (dot-separated supported)"
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop after first row with input/scoring error",
    )
    return parser.parse_args(argv)


def _extract_by_path(obj: dict[str, Any], path: str) -> tuple[bool, Any]:
    current: Any = obj
    for part in path.split("."):
        if not isinstance(current, dict):
            return False, None
        if part not in current:
            return False, None
        current = current.get(part)
    return True, current


def _pick_value(obj: dict[str, Any], keys: tuple[str, ...]) -> tuple[bool, Any, str | None]:
    for key in keys:
        has_value, value = _extract_by_path(obj, key)
        if has_value:
            return True, value, key
    return False, None, None


def _normalize_evidence(value: Any) -> tuple[list[Any] | None, str | None]:
    if isinstance(value, list):
        return value, None
    if isinstance(value, tuple):
        return list(value), None
    if isinstance(value, str):
        if value.strip() == "":
            return None, "empty_evidence_string"
        return [value], None
    if isinstance(value, dict):
        return [value], None
    return None, "evidence_must_be_list_tuple_string_or_object"


def _parse_json_lines(lines: list[str]) -> tuple[list[dict[str, Any]] | None, str | None]:
    rows: list[dict[str, Any]] = []
    for idx, line in enumerate(lines):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            return None, f"invalid_jsonl_line:{idx}:{exc}"
        if not isinstance(obj, dict):
            return None, f"invalid_jsonl_row_shape:{idx}"
        rows.append(obj)
    return rows, None


def _parse_json_payload(text: str) -> tuple[list[dict[str, Any]] | None, str | None]:
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, f"invalid_json:{exc}"

    if isinstance(obj, list):
        rows: list[dict[str, Any]] = []
        for idx, row in enumerate(obj):
            if not isinstance(row, dict):
                return None, f"invalid_json_array_row_shape:{idx}"
            rows.append(row)
        return rows, None

    if isinstance(obj, dict):
        for key in ("rows", "data", "samples"):
            maybe = obj.get(key)
            if isinstance(maybe, list):
                rows = []
                for idx, row in enumerate(maybe):
                    if not isinstance(row, dict):
                        return None, f"invalid_json_object_{key}_row_shape:{idx}"
                    rows.append(row)
                return rows, None
        return None, "json_object_input_must_include_rows_data_or_samples_array"

    return None, "json_input_must_be_array_or_object_with_rows"


def _load_rows(
    input_path: Path | None, input_format: str
) -> tuple[list[dict[str, Any]] | None, str | None]:
    text = input_path.read_text(encoding="utf-8") if input_path else sys.stdin.read()
    if text.strip() == "":
        return None, "empty_input"

    if input_format == "jsonl":
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        return _parse_json_lines(lines)
    if input_format == "json":
        return _parse_json_payload(text)

    rows, err = _parse_json_payload(text)
    if rows is not None:
        return rows, None
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return _parse_json_lines(lines)


def _write_rows(rows: list[dict[str, Any]], output_path: Path | None) -> None:
    text = "\n".join(json.dumps(row) for row in rows) + ("\n" if rows else "")
    if output_path is None:
        sys.stdout.write(text)
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")


def run_rows(
    rows: list[dict[str, Any]],
    *,
    query_key: str | None = None,
    answer_key: str | None = None,
    contexts_key: str | None = None,
    run_id_key: str | None = None,
    fail_fast: bool = False,
) -> tuple[list[dict[str, Any]], int]:
    query_keys = (query_key,) if query_key else DEFAULT_QUERY_KEYS
    answer_keys = (answer_key,) if answer_key else DEFAULT_ANSWER_KEYS
    contexts_keys = (contexts_key,) if contexts_key else DEFAULT_CONTEXT_KEYS
    run_id_keys = (run_id_key,) if run_id_key else DEFAULT_RUN_ID_KEYS

    out_rows: list[dict[str, Any]] = []
    exit_code = 0

    for idx, obj in enumerate(rows):
        ok_query, query_value, query_used = _pick_value(obj, query_keys)
        ok_answer, answer_value, answer_used = _pick_value(obj, answer_keys)
        ok_evidence, evidence_value, evidence_used = _pick_value(obj, contexts_keys)

        has_run_id, run_id_value, _ = _pick_value(obj, run_id_keys)
        run_id = str(run_id_value) if has_run_id and run_id_value is not None else None

        input_error: str | None = None
        chronicle: dict[str, Any]
        mapping: dict[str, Any] = {
            "query_key": query_used,
            "answer_key": answer_used,
            "contexts_key": evidence_used,
        }

        if not ok_query:
            input_error = f"missing_query_keys:{'|'.join(query_keys)}"
        elif not ok_answer:
            input_error = f"missing_answer_keys:{'|'.join(answer_keys)}"
        elif not ok_evidence:
            input_error = f"missing_contexts_keys:{'|'.join(contexts_keys)}"

        if input_error is not None:
            chronicle = {
                "contract_version": "1.0",
                "error": "invalid_input",
                "message": input_error,
            }
        else:
            evidence_list, evidence_error = _normalize_evidence(evidence_value)
            if evidence_error is not None or evidence_list is None:
                input_error = evidence_error or "invalid_evidence"
                chronicle = {
                    "contract_version": "1.0",
                    "error": "invalid_input",
                    "message": input_error,
                }
            else:
                payload = {
                    "query": query_value,
                    "answer": answer_value,
                    "evidence": evidence_list,
                }
                chronicle = _run_scorer(json.dumps(payload))

        row_out: dict[str, Any] = {
            "row_index": idx,
            "run_id": run_id,
            "ok": input_error is None and "error" not in chronicle,
            "ragas_mapping": mapping,
            "chronicle": chronicle,
        }
        if input_error is not None:
            row_out["input_error"] = input_error

        out_rows.append(row_out)

        if input_error is not None or chronicle.get("error"):
            exit_code = 1
            if fail_fast:
                break

    return out_rows, exit_code


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    rows, load_error = _load_rows(args.input, args.input_format)
    if rows is None:
        error_row = {
            "row_index": None,
            "run_id": None,
            "ok": False,
            "input_error": "invalid_input_payload",
            "ragas_mapping": {"query_key": None, "answer_key": None, "contexts_key": None},
            "chronicle": {
                "contract_version": "1.0",
                "error": "invalid_input",
                "message": load_error or "invalid input",
            },
        }
        _write_rows([error_row], args.output)
        return 1

    out_rows, code = run_rows(
        rows,
        query_key=args.query_key,
        answer_key=args.answer_key,
        contexts_key=args.contexts_key,
        run_id_key=args.run_id_key,
        fail_fast=args.fail_fast,
    )
    _write_rows(out_rows, args.output)
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
