"""
Suggest tensions in a Chronicle investigation using heuristic and/or local LLM (Ollama).

Use this to populate tensions "for free" with Ollama (qwen2.5:7b or any model).

  export CHRONICLE_LLM_ENABLED=1
  PYTHONPATH=. python scripts/suggest_tensions_with_llm.py --path /path/to/project --method heuristic
  PYTHONPATH=. python scripts/suggest_tensions_with_llm.py --path /path/to/project --method llm --max-claims 500 --max-pairs 50
  PYTHONPATH=. python scripts/suggest_tensions_with_llm.py --path /path/to/project --method heuristic --apply

See docs/using-ollama-locally.md.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Suggest tensions (heuristic and/or Ollama LLM) and optionally apply them."
    )
    parser.add_argument(
        "--path",
        "-p",
        required=True,
        help="Chronicle project directory (must contain chronicle.db)",
    )
    parser.add_argument(
        "--investigation-uid",
        default="",
        help="Investigation UID; if not set, use first investigation or --title",
    )
    parser.add_argument(
        "--title",
        default="",
        help="Investigation title to match (ignored if --investigation-uid set)",
    )
    parser.add_argument(
        "--method",
        choices=("heuristic", "llm"),
        default="heuristic",
        help="heuristic = rule-based only (no API). llm = use Ollama (set CHRONICLE_LLM_ENABLED=1)",
    )
    parser.add_argument(
        "--max-claims",
        type=int,
        default=2000,
        help="Max claims to load (default 2000). Lower for faster LLM; heuristic can use more.",
    )
    parser.add_argument(
        "--max-pairs",
        type=int,
        default=50,
        help="Max claim pairs to send to LLM when --method llm (default 50)",
    )
    parser.add_argument(
        "--output",
        choices=("text", "json"),
        default="text",
        help="Output format for suggestions (default text)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Declare each suggested tension in the project (writes to DB)",
    )
    args = parser.parse_args()

    project_path = Path(args.path)
    if not project_path.is_absolute():
        project_path = (REPO_ROOT / project_path).resolve()
    if not (project_path / "chronicle.db").is_file():
        print(f"Error: not a Chronicle project (no chronicle.db): {project_path}", file=sys.stderr)
        return 1

    from chronicle.store.session import ChronicleSession

    with ChronicleSession(project_path) as session:
        investigations = session.read_model.list_investigations()
        if not investigations:
            print("Error: no investigations in project.", file=sys.stderr)
            return 1
        inv = None
        if (args.investigation_uid or "").strip():
            for i in investigations:
                if i.investigation_uid == args.investigation_uid.strip():
                    inv = i
                    break
        else:
            title_match = (args.title or "").strip()
            if title_match:
                for i in investigations:
                    if (i.title or "").strip() == title_match or title_match.lower() in (
                        i.title or ""
                    ).lower():
                        inv = i
                        break
            if inv is None:
                inv = investigations[0]
        if inv is None:
            print("Error: no matching investigation.", file=sys.stderr)
            return 1
        inv_uid = inv.investigation_uid
        print(f"Investigation: {inv.title!r} ({inv_uid})", file=sys.stderr)

        claims = session.read_model.list_claims_by_type(
            investigation_uid=inv_uid, limit=args.max_claims, include_withdrawn=False
        )
        claim_list = [(c.claim_uid, c.claim_text or "") for c in claims]
        if len(claim_list) >= args.max_claims and args.max_claims < 50_000:
            print(f"Using first {args.max_claims} claims (--max-claims).", file=sys.stderr)
        if not claim_list:
            print("Error: no claims in investigation.", file=sys.stderr)
            return 1

        from chronicle.tools.contradiction import suggest_tensions_heuristic, suggest_tensions_llm
        from chronicle.tools.llm_client import LlmClient, LlmClientError

        suggestions = []
        if args.method == "heuristic":
            suggestions = suggest_tensions_heuristic(claim_list)
        else:
            os.environ.setdefault("CHRONICLE_LLM_ENABLED", "1")
            try:
                client = LlmClient()
                suggestions = suggest_tensions_llm(
                    claim_list,
                    client,
                    max_pairs=args.max_pairs,
                    batch_size=8,
                )
            except LlmClientError as e:
                print(f"LLM failed ({e}); falling back to heuristic.", file=sys.stderr)
                suggestions = suggest_tensions_heuristic(claim_list)

        if args.output == "json":
            out = [
                {
                    "claim_a_uid": s.claim_a_uid,
                    "claim_b_uid": s.claim_b_uid,
                    "tension_kind": s.suggested_tension_kind,
                    "confidence": s.confidence,
                    "rationale": s.rationale,
                }
                for s in suggestions
            ]
            print(json.dumps(out, indent=2))
        else:
            for s in suggestions:
                print(
                    f"  {s.claim_a_uid} <-> {s.claim_b_uid}  kind={s.suggested_tension_kind} conf={s.confidence:.2f}"
                )
                print(f"    {s.rationale}")

        if args.apply and suggestions:
            applied = 0
            for s in suggestions:
                try:
                    session.declare_tension(
                        inv_uid,
                        s.claim_a_uid,
                        s.claim_b_uid,
                        tension_kind=s.suggested_tension_kind,
                        notes=s.rationale,
                        workspace="forge",
                    )
                    applied += 1
                except Exception as e:
                    print(f"Skip tension {s.claim_a_uid}–{s.claim_b_uid}: {e}", file=sys.stderr)
            print(f"Applied {applied} tensions.", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
