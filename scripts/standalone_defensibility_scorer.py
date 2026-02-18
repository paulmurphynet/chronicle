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
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

# Max bytes to fetch per URL (avoid memory exhaustion)
_URL_FETCH_MAX_BYTES = 5 * 1024 * 1024


def _fetch_url(url: str) -> str | None:
    """Fetch URL and return decoded text, or None if unsafe/failed. Uses SSRF safeguards."""
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return None
    if parsed.scheme not in ("http", "https"):
        return None
    host = parsed.hostname or parsed.netloc.split(":")[0]
    from chronicle.core.ssrf import is_ssrf_unsafe_host

    if is_ssrf_unsafe_host(host):
        return None

    class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            p = urlparse(newurl)
            h = p.hostname or (p.netloc.split(":")[0] if p.netloc else "")
            if h and is_ssrf_unsafe_host(h):
                raise ValueError("Redirect to disallowed host")
            return urllib.request.HTTPRedirectHandler.redirect_request(
                self, req, fp, code, msg, headers, newurl
            )

    opener = urllib.request.build_opener(_SafeRedirectHandler)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Chronicle-Scorer/1.0"})
        with opener.open(req, timeout=30) as resp:
            raw = resp.read(_URL_FETCH_MAX_BYTES + 1)
            if len(raw) > _URL_FETCH_MAX_BYTES:
                return None
            return raw.decode("utf-8", errors="replace").strip()
    except Exception:
        return None


def _normalize_evidence(evidence: list) -> list[str]:
    """Extract text chunks from evidence list (strings or objects with text/path/url)."""
    chunks: list[str] = []
    for item in evidence:
        if isinstance(item, str):
            if item.strip():
                chunks.append(item)
        elif isinstance(item, dict):
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                chunks.append(text)
            elif "path" in item:
                path = Path(item["path"])
                if path.is_file():
                    chunks.append(path.read_text(encoding="utf-8", errors="replace").strip())
            elif "url" in item and isinstance(item["url"], str) and item["url"].strip():
                fetched = _fetch_url(item["url"].strip())
                if fetched:
                    chunks.append(fetched)
        # else skip non-string, non-dict
    return chunks


def _run_scorer(stdin_input: str) -> dict:
    """Run the scorer logic; returns output dict (metrics or error)."""
    try:
        data = json.loads(stdin_input)
    except json.JSONDecodeError as e:
        return {"contract_version": "1.0", "error": "invalid_input", "message": str(e)}

    query = data.get("query")
    answer = data.get("answer")
    evidence = data.get("evidence")

    if not isinstance(query, str):
        return {"contract_version": "1.0", "error": "invalid_input", "message": "query must be a string"}
    if not isinstance(answer, str):
        return {"contract_version": "1.0", "error": "invalid_input", "message": "answer must be a string"}
    if not isinstance(evidence, list):
        return {"contract_version": "1.0", "error": "invalid_input", "message": "evidence must be an array"}

    chunks = _normalize_evidence(evidence)
    if not chunks:
        return {
            "contract_version": "1.0",
            "error": "invalid_input",
            "message": "evidence must contain at least one non-empty text chunk (string or object with \"text\", \"path\", or \"url\")",
        }

    from chronicle.eval_metrics import defensibility_metrics_for_claim
    from chronicle.store.project import create_project
    from chronicle.store.session import ChronicleSession

    with tempfile.TemporaryDirectory(prefix="chronicle_scorer_") as tmp:
        path = Path(tmp)
        create_project(path)

        with ChronicleSession(path) as session:
            _, inv_uid = session.create_investigation(
                "Standalone defensibility scorer run",
                actor_id="standalone-scorer",
                actor_type="tool",
            )

            span_uids: list[str] = []
            for i, text in enumerate(chunks):
                blob = text.encode("utf-8")
                _, ev_uid = session.ingest_evidence(
                    inv_uid,
                    blob,
                    "text/plain",
                    original_filename=f"chunk_{i}.txt",
                    actor_id="standalone-scorer",
                    actor_type="tool",
                )
                _, span_uid = session.anchor_span(
                    inv_uid,
                    ev_uid,
                    "text_offset",
                    {"start_char": 0, "end_char": len(text)},
                    quote=text[:2000] if len(text) > 2000 else text,
                    actor_id="standalone-scorer",
                    actor_type="tool",
                )
                span_uids.append(span_uid)

            _, claim_uid = session.propose_claim(
                inv_uid,
                answer[:50000],
                actor_id="standalone-scorer",
                actor_type="tool",
            )

            for span_uid in span_uids:
                session.link_support(
                    inv_uid,
                    span_uid,
                    claim_uid,
                    actor_id="standalone-scorer",
                    actor_type="tool",
                )

            metrics = defensibility_metrics_for_claim(session, claim_uid)
            if metrics is None:
                return {
                    "contract_version": "1.0",
                    "claim_uid": claim_uid,
                    "error": "no_defensibility_score",
                    "investigation_uid": inv_uid,
                }
            return {"contract_version": "1.0", **metrics}


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
