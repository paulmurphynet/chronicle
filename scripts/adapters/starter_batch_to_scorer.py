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

Mapping profile example:
  PYTHONPATH=. python3 scripts/adapters/starter_batch_to_scorer.py \
    --profile scripts/adapters/examples/mapping_profile_nested.json \
    --input scripts/adapters/examples/harness_runs_nested.jsonl \
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
    parser = argparse.ArgumentParser(
        description="Batch adapter: harness JSONL -> Chronicle scorer JSONL"
    )
    parser.add_argument(
        "--input", type=Path, default=None, help="Input JSONL file (default: stdin)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSONL file (default: stdout)",
    )
    parser.add_argument(
        "--profile",
        type=Path,
        default=None,
        help="Optional mapping profile JSON (keys/paths and defaults)",
    )
    parser.add_argument(
        "--query-key", default=None, help="Query key/path (dot-separated supported)"
    )
    parser.add_argument(
        "--answer-key", default=None, help="Answer key/path (dot-separated supported)"
    )
    parser.add_argument(
        "--evidence-key", default=None, help="Evidence key/path (dot-separated supported)"
    )
    parser.add_argument(
        "--run-id-key", default=None, help="Run id key/path (dot-separated supported)"
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on first input/scoring error",
    )
    return parser.parse_args(argv)


def _profile_get(profile: dict[str, Any], key: str, aliases: list[str]) -> Any:
    if key in profile:
        return profile.get(key)
    for alias in aliases:
        if alias in profile:
            return profile.get(alias)
    return None


def _load_profile(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("profile must be a JSON object")
    return data


def _resolve_config(args: argparse.Namespace) -> dict[str, Any]:
    profile = _load_profile(args.profile)
    query_key = args.query_key or _profile_get(profile, "query_key", ["query_path"]) or "query"
    answer_key = args.answer_key or _profile_get(profile, "answer_key", ["answer_path"]) or "answer"
    evidence_key = (
        args.evidence_key or _profile_get(profile, "evidence_key", ["evidence_path"]) or "evidence"
    )
    run_id_key = args.run_id_key or _profile_get(profile, "run_id_key", ["run_id_path"]) or "run_id"
    # CLI flag always wins; otherwise profile can set fail_fast default.
    fail_fast = args.fail_fast or bool(profile.get("fail_fast", False))
    return {
        "query_key": str(query_key),
        "answer_key": str(answer_key),
        "evidence_key": str(evidence_key),
        "run_id_key": str(run_id_key),
        "fail_fast": fail_fast,
    }


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


def _extract_by_path(obj: dict[str, Any], path: str) -> tuple[bool, Any]:
    if path == "":
        return False, None
    current: Any = obj
    for part in path.split("."):
        if not isinstance(current, dict):
            return False, None
        if part not in current:
            return False, None
        current = current.get(part)
    return True, current


def _map_row_to_contract_input(
    obj: dict[str, Any],
    *,
    query_key: str,
    answer_key: str,
    evidence_key: str,
) -> tuple[dict[str, Any] | None, str | None]:
    has_query, query_value = _extract_by_path(obj, query_key)
    if not has_query:
        return None, f"missing_query_key:{query_key}"
    has_answer, answer_value = _extract_by_path(obj, answer_key)
    if not has_answer:
        return None, f"missing_answer_key:{answer_key}"
    has_evidence, evidence_value = _extract_by_path(obj, evidence_key)
    if not has_evidence:
        return None, f"missing_evidence_key:{evidence_key}"
    contract_input = {
        "query": query_value,
        "answer": answer_value,
        "evidence": evidence_value,
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

        has_run_id, rid = _extract_by_path(obj, run_id_key)
        if not has_run_id:
            rid = None
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
    try:
        config = _resolve_config(args)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        out = {
            "row_index": None,
            "run_id": None,
            "ok": False,
            "input_error": "invalid_profile",
            "chronicle": {"contract_version": "1.0", "error": "invalid_input", "message": str(e)},
        }
        _write_outputs([out], args.output)
        return 1

    lines = _load_lines(args.input)
    if not lines:
        out = {
            "row_index": None,
            "run_id": None,
            "ok": False,
            "input_error": "no_input",
            "chronicle": {
                "contract_version": "1.0",
                "error": "invalid_input",
                "message": "empty input",
            },
        }
        _write_outputs([out], args.output)
        return 1

    rows, code = run_rows(
        lines,
        query_key=config["query_key"],
        answer_key=config["answer_key"],
        evidence_key=config["evidence_key"],
        run_id_key=config["run_id_key"],
        fail_fast=config["fail_fast"],
    )
    _write_outputs(rows, args.output)
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
