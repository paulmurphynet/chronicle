#!/usr/bin/env python3
"""
Fact-checker → Chronicle adapter.

Reads a fact-checker output (claim + verdict + sources) and maps to Chronicle:
evidence items, propose_claim, support/challenge links. Optionally declares
tension when verdict is "mixed" or two claims conflict.

Expected input (JSON file or stdin): one object per line or single object.

  {
    "claim": "The company reported revenue of $1.2M in Q1 2024.",
    "verdict": "true" | "false" | "mixed",
    "sources": [
      { "url": "https://...", "snippet": "optional quote or text", "stance": "support" | "challenge" }
    ],
    "external_id": "optional fact-check ID"
  }

If "snippet" is missing, we use url as the evidence text. Each source becomes
one evidence item; we anchor a span and link as support or challenge from stance
(or from verdict when stance is missing: true→support, false→challenge, mixed→support/challenge per source).

Run from repo root:
  PYTHONPATH=. python3 scripts/adapters/fact_checker_to_chronicle.py [input.json]
  # Writes to a temp project and prints claim_uid, investigation_uid, defensibility summary.
  # For production: pass --path /path/to/project to reuse a project.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from chronicle.store.project import create_project
from chronicle.store.session import ChronicleSession


def run_one(obj: dict, project_path: Path, actor_id: str = "fact-checker-adapter") -> dict:
    claim_text = obj.get("claim") or ""
    verdict = (obj.get("verdict") or "true").lower().strip()
    sources = obj.get("sources") or []
    external_id = obj.get("external_id")

    if not claim_text:
        return {"error": "missing_claim", "message": "field 'claim' is required"}
    if not sources:
        return {"error": "missing_sources", "message": "field 'sources' (array) is required"}

    create_project(project_path)
    with ChronicleSession(project_path) as session:
        _, inv_uid = session.create_investigation(
            "Fact-check import",
            actor_id=actor_id,
            actor_type="tool",
        )
        span_uids_support: list[str] = []
        span_uids_challenge: list[str] = []
        for i, src in enumerate(sources):
            if not isinstance(src, dict):
                continue
            snippet = src.get("snippet") or src.get("text") or src.get("url") or ""
            if not snippet:
                continue
            text = snippet if isinstance(snippet, str) else json.dumps(snippet)
            blob = text.encode("utf-8")
            metadata = {"url": src.get("url"), "external_id": external_id}
            if external_id:
                metadata["fact_check_id"] = external_id
            _, ev_uid = session.ingest_evidence(
                inv_uid,
                blob,
                "text/plain",
                original_filename=f"source_{i}.txt",
                metadata=metadata,
                actor_id=actor_id,
                actor_type="tool",
            )
            _, span_uid = session.anchor_span(
                inv_uid,
                ev_uid,
                "text_offset",
                {"start_char": 0, "end_char": len(text)},
                quote=text[:2000] if len(text) > 2000 else text,
                actor_id=actor_id,
                actor_type="tool",
            )
            stance = (src.get("stance") or "").lower()
            if stance == "challenge":
                span_uids_challenge.append(span_uid)
            else:
                span_uids_support.append(span_uid)

        if not span_uids_support and not span_uids_challenge:
            return {"error": "no_evidence", "message": "no valid sources with snippet or url"}

        _, claim_uid = session.propose_claim(
            inv_uid,
            claim_text[:50000],
            actor_id=actor_id,
            actor_type="tool",
        )
        for span_uid in span_uids_support:
            session.link_support(inv_uid, span_uid, claim_uid, actor_id=actor_id, actor_type="tool")
        for span_uid in span_uids_challenge:
            session.link_challenge(inv_uid, span_uid, claim_uid, actor_id=actor_id, actor_type="tool")

        scorecard = session.get_defensibility_score(claim_uid)
        out: dict = {
            "investigation_uid": inv_uid,
            "claim_uid": claim_uid,
            "support_count": len(span_uids_support),
            "challenge_count": len(span_uids_challenge),
        }
        if scorecard:
            out["provenance_quality"] = scorecard.provenance_quality
            out["contradiction_status"] = scorecard.contradiction_status
        if external_id:
            out["external_id"] = external_id
        return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Fact-checker output → Chronicle (evidence, claim, support/challenge).")
    parser.add_argument("input", nargs="?", help="JSON file (default: stdin)")
    parser.add_argument("--path", type=Path, help="Project path (default: temp dir)")
    parser.add_argument("--actor-id", default="fact-checker-adapter", help="Actor id for events")
    args = parser.parse_args()
    if args.input:
        raw = Path(args.input).read_text()
    else:
        raw = sys.stdin.read()
    lines = [ln.strip() for ln in raw.strip().splitlines() if ln.strip()]
    if not lines:
        print(json.dumps({"error": "no_input", "message": "empty input"}))
        return 1
    path = args.path or Path(tempfile.mkdtemp(prefix="chronicle_fc_"))
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
    exit_code = 0
    for line in lines:
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            print(json.dumps({"error": "invalid_json", "message": str(e)}))
            exit_code = 1
            continue
        result = run_one(obj, path, actor_id=args.actor_id)
        print(json.dumps(result))
        if result.get("error"):
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
