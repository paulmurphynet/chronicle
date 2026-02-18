"""
Standalone defensibility scorer: (query, answer, evidence) in -> defensibility JSON out (M2).

Accepts input either as one JSON object on stdin or via CLI flags (--query, --answer,
--evidence). Creates a temp project, ingests evidence, proposes the answer as a claim,
links each evidence chunk as support, and prints the defensibility metrics JSON to stdout.
No API server or RAG stack required. Implements the [eval contract](docs/eval_contract.md).

Usage (from repo root):

  # Stdin (one JSON object):
  echo '{"query": "What was revenue?", "answer": "Revenue was $1.2M.", "evidence": ["The company reported revenue of $1.2M in Q1 2024."]}' \\
    | PYTHONPATH=. python3 scripts/standalone_defensibility_scorer.py

  # CLI flags (--evidence is a JSON array string):
  PYTHONPATH=. python3 scripts/standalone_defensibility_scorer.py \\
    --query "What was revenue?" --answer "Revenue was $1.2M." \\
    --evidence '["The company reported revenue of $1.2M in Q1 2024."]'

  # JSON file on stdin:
  PYTHONPATH=. python3 scripts/standalone_defensibility_scorer.py < input.json

Output: one JSON object (metrics or error). See docs/eval_contract.md.
"""

from __future__ import annotations

import argparse
import json
import sys

from chronicle.scorer_contract import run_scorer_contract


def _run_scorer(stdin_input: str) -> dict:
    """Run the scorer logic; returns output dict (metrics or error)."""
    try:
        data = json.loads(stdin_input)
    except json.JSONDecodeError as e:
        return {"contract_version": "1.0", "error": "invalid_input", "message": str(e)}
    return run_scorer_contract(data, allow_path=True)


def _build_input_from_args(args: argparse.Namespace) -> tuple[bool, str | dict]:
    """Build input from CLI args. Returns (True, json_string) or (False, error_dict)."""
    if args.query is None and args.answer is None and args.evidence is None:
        return (False, {"error": "no_input", "message": "no input"})  # signal: use stdin
    if args.query is None or args.answer is None or args.evidence is None:
        return (
            False,
            {
                "error": "invalid_input",
                "message": "when using CLI flags, all of --query, --answer, and --evidence are required",
            },
        )
    try:
        evidence_parsed = json.loads(args.evidence)
    except json.JSONDecodeError as e:
        return (False, {"error": "invalid_input", "message": f"--evidence must be a JSON array: {e}"})
    if not isinstance(evidence_parsed, list):
        return (False, {"error": "invalid_input", "message": "--evidence must be a JSON array"})
    return (True, json.dumps({"query": args.query, "answer": args.answer, "evidence": evidence_parsed}))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Standalone defensibility scorer: (query, answer, evidence) -> defensibility JSON. Input via stdin or --query/--answer/--evidence."
    )
    parser.add_argument("--query", type=str, help="User question or prompt")
    parser.add_argument("--answer", type=str, help="Model answer (claim text)")
    parser.add_argument("--evidence", type=str, help='JSON array of evidence chunks, e.g. \'["chunk1", "chunk2"]\'')
    args = parser.parse_args()

    use_args, payload = _build_input_from_args(args)

    if use_args:
        input_str = payload
    else:
        if payload.get("error") != "no_input":
            print(json.dumps(payload))
            return 1
        stdin_input = sys.stdin.read()
        if not stdin_input.strip():
            out = {
                "contract_version": "1.0",
                "error": "invalid_input",
                "message": "empty stdin; send one JSON object with query, answer, evidence or use --query, --answer, --evidence",
            }
            print(json.dumps(out))
            return 1
        input_str = stdin_input

    out = _run_scorer(input_str)
    print(json.dumps(out))
    return 1 if out.get("error") else 0


if __name__ == "__main__":
    raise SystemExit(main())
