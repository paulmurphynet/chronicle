"""
Eval contract runner: (query, answer, evidence) dict in -> defensibility metrics dict out.

Used by the standalone script and by the optional POST /score API. No project path required;
runs in a temporary project. Implements docs/eval_contract.md.
"""

from __future__ import annotations

import json
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from chronicle.eval_metrics import defensibility_metrics_for_claim
from chronicle.store.project import create_project
from chronicle.store.session import ChronicleSession

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


def _normalize_evidence(evidence: list, *, allow_path: bool = True) -> list[str]:
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
            elif allow_path and "path" in item:
                path = Path(item["path"])
                if path.is_file():
                    chunks.append(path.read_text(encoding="utf-8", errors="replace").strip())
            elif "url" in item and isinstance(item["url"], str) and item["url"].strip():
                fetched = _fetch_url(item["url"].strip())
                if fetched:
                    chunks.append(fetched)
    return chunks


def run_scorer_contract(
    data: dict,
    *,
    allow_path: bool = True,
) -> dict:
    """Run the eval contract: (query, answer, evidence) -> defensibility metrics or error dict.

    Input: dict with keys "query" (str), "answer" (str), "evidence" (list of strings or
    objects with "text", "path", or "url"). Output: dict with contract_version, claim_uid,
    provenance_quality, corroboration, contradiction_status, etc., or error/message.

    When allow_path is False (e.g. from HTTP API), evidence items with "path" are skipped.
    """
    query = data.get("query")
    answer = data.get("answer")
    evidence = data.get("evidence")

    if not isinstance(query, str):
        return {"contract_version": "1.0", "error": "invalid_input", "message": "query must be a string"}
    if not isinstance(answer, str):
        return {"contract_version": "1.0", "error": "invalid_input", "message": "answer must be a string"}
    if not isinstance(evidence, list):
        return {"contract_version": "1.0", "error": "invalid_input", "message": "evidence must be an array"}

    chunks = _normalize_evidence(evidence, allow_path=allow_path)
    if not chunks:
        return {
            "contract_version": "1.0",
            "error": "invalid_input",
            "message": "evidence must contain at least one non-empty text chunk (string or object with \"text\", \"path\", or \"url\")",
        }

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
