"""
Convert two Chronicle eval run results into one DPO-style preference pair (M7).

Each run record must include: query, answer, and the scorer output (provenance_quality
or full defensibility metrics). The script compares defensibility and outputs
{prompt, chosen, rejected} so the higher-defensibility answer is chosen.

Input (each run): JSON with query, answer, evidence (optional), and either
- the full standalone_defensibility_scorer output (provenance_quality, corroboration, ...),
- or at least provenance_quality. If "error" is present, that run is treated as worse.

Usage (from repo root):

  # Two files (order does not matter; script picks chosen/rejected by defensibility)
  PYTHONPATH=. python3 scripts/benchmark_data/evals_to_preference_pair.py run1.json run2.json

  # Stdin: two JSON lines
  PYTHONPATH=. python3 scripts/benchmark_data/evals_to_preference_pair.py --stdin < two_runs.jsonl

  # Optional: include evidence in the prompt
  PYTHONPATH=. python3 scripts/benchmark_data/evals_to_preference_pair.py --prompt-with-evidence run1.json run2.json

Output: one JSON object to stdout: {"prompt": "...", "chosen": "...", "rejected": "..."}.
See docs/preference-pairs-from-evals.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_PROVENANCE_ORDER = ("strong", "medium", "weak", "challenged")


def _defensibility_rank(run: dict) -> tuple[int, int, int]:
    """
    Lower rank = better. Returns (provenance_rank, -support_count, challenge_count)
    so that sorting ascending gives preferred first.
    """
    if run.get("error"):
        return (999, 0, 999)
    pq = run.get("provenance_quality")
    if pq not in _PROVENANCE_ORDER:
        return (998, 0, 998)
    prov_rank = _PROVENANCE_ORDER.index(pq)
    corr = run.get("corroboration") or {}
    support = corr.get("support_count", 0)
    challenge = corr.get("challenge_count", 0)
    return (prov_rank, -support, challenge)


def _build_prompt(run: dict, with_evidence: bool) -> str:
    query = run.get("query") or ""
    if not with_evidence:
        return query
    evidence = run.get("evidence") or []
    if not evidence:
        return query
    parts = []
    for i, item in enumerate(evidence):
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, dict) and item.get("text"):
            parts.append(item["text"])
        else:
            parts.append(f"[evidence {i + 1}]")
    return "Evidence:\n" + "\n\n".join(parts) + "\n\nQuestion: " + query


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert two eval run JSONs into one DPO preference pair (chosen = higher defensibility)."
    )
    parser.add_argument("run1", nargs="?", type=Path, help="Path to first run JSON")
    parser.add_argument("run2", nargs="?", type=Path, help="Path to second run JSON")
    parser.add_argument(
        "--stdin", action="store_true", help="Read two JSON lines from stdin instead of run1/run2"
    )
    parser.add_argument(
        "--prompt-with-evidence",
        action="store_true",
        help="Include evidence in the prompt (default: prompt = query only)",
    )
    args = parser.parse_args()

    if args.stdin:
        if args.run1 or args.run2:
            print("Use either --stdin or run1 run2, not both.", file=sys.stderr)
            return 1
        lines = sys.stdin.read().strip().split("\n")
        if len(lines) < 2:
            print("Expected two JSON lines on stdin.", file=sys.stderr)
            return 1
        try:
            run1 = json.loads(lines[0])
            run2 = json.loads(lines[1])
        except json.JSONDecodeError as e:
            print(f"Invalid JSON: {e}", file=sys.stderr)
            return 1
    else:
        if not args.run1 or not args.run2:
            print("Provide two run JSON files, or use --stdin.", file=sys.stderr)
            return 1
        try:
            run1 = json.loads(args.run1.read_text(encoding="utf-8"))
            run2 = json.loads(args.run2.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"Read error: {e}", file=sys.stderr)
            return 1

    r1_rank = _defensibility_rank(run1)
    r2_rank = _defensibility_rank(run2)
    if r1_rank <= r2_rank:
        preferred, rejected = run1, run2
    else:
        preferred, rejected = run2, run1

    chosen = preferred.get("answer") or ""
    rejected_str = rejected.get("answer") or ""
    prompt = _build_prompt(preferred, args.prompt_with_evidence)

    out = {"prompt": prompt, "chosen": chosen, "rejected": rejected_str}
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
