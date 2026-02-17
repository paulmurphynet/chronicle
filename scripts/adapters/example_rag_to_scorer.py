#!/usr/bin/env python3
"""
Example adapter: RAG harness output → Chronicle defensibility scorer.

Copy-paste template for piping your RAG run (query, answer, evidence) into the
scorer. Input: one JSON object per line or single object on stdin, same shape
as eval contract (query, answer, evidence). Output: one JSON object per line
(metrics or error). Run from repo root: PYTHONPATH=. python3 scripts/adapters/example_rag_to_scorer.py [input.json]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.standalone_defensibility_scorer import _run_scorer


def main() -> int:
    if len(sys.argv) > 1:
        text = Path(sys.argv[1]).read_text()
    else:
        text = sys.stdin.read()
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if not lines:
        print(json.dumps({"error": "no_input", "message": "empty input"}))
        return 1
    exit_code = 0
    for line in lines:
        out = _run_scorer(line)
        print(json.dumps(out))
        if out.get("error"):
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
