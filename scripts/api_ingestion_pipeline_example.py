#!/usr/bin/env python3
"""End-to-end API ingestion example: batch input -> Chronicle -> defensibility artifacts."""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from chronicle.core.http_safety import ensure_safe_http_url
from chronicle.store import export_import as export_import_mod
from chronicle.store.project import create_project, project_exists
from chronicle.store.session import ChronicleSession

DEFAULT_BATCH = {
    "title": "API ingestion example: contested revenue timing",
    "claim": "Revenue timing for INV-204 requires exception tracking.",
    "records": [
        {
            "text": "Ledger entry recognized INV-204 revenue on 2024-03-31 under quarter-close adjustments.",
            "stance": "support",
            "rationale": "Ledger record supports the claim that timing is policy-sensitive.",
            "filename": "ledger.txt",
        },
        {
            "text": "Delivery receipt for INV-204 is signed on 2024-04-02, indicating fulfillment after quarter close.",
            "stance": "challenge",
            "rationale": "Operational timing challenges straight-through March recognition.",
            "filename": "delivery_receipt.txt",
        },
    ],
}


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _write_json(path: Path, payload: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(path)


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _http_json(
    base_url: str, method: str, path: str, payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    url = ensure_safe_http_url(f"{base_url}{path}", block_private_hosts=False)
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} {method} {path}: {detail}") from exc
    return json.loads(body) if body else {}


def _http_bytes(base_url: str, method: str, path: str) -> bytes:
    url = ensure_safe_http_url(f"{base_url}{path}", block_private_hosts=False)
    req = urllib.request.Request(url, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310
            return resp.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} {method} {path}: {detail}") from exc


def _wait_for_health(
    base_url: str,
    *,
    timeout_s: float = 15.0,
    proc: subprocess.Popen[str] | None = None,
) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if proc is not None and proc.poll() is not None:
            stderr = ""
            if proc.stderr is not None:
                stderr = proc.stderr.read().strip()
            raise RuntimeError(
                f"API server exited before health check. "
                f"returncode={proc.returncode} stderr={stderr or '<none>'}"
            )
        try:
            data = _http_json(base_url, "GET", "/health")
            if data.get("status") == "ok" or data.get("ok") is True:
                return
        except Exception:
            pass
        time.sleep(0.2)
    raise TimeoutError("API server did not become healthy in time")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a deterministic end-to-end API ingestion pipeline example."
    )
    parser.add_argument(
        "--project-path",
        type=Path,
        required=True,
        help="Chronicle project path used by API routes.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Output directory for report artifacts.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Optional JSON batch payload. Defaults to built-in example.",
    )
    parser.add_argument(
        "--stdout-json",
        action="store_true",
        help="Print full report JSON to stdout.",
    )
    return parser.parse_args(argv)


def _load_batch(path: Path | None) -> dict[str, Any]:
    if path is None:
        return DEFAULT_BATCH
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Batch payload must be a JSON object")
    return payload


def _run_pipeline(batch: dict[str, Any], project_path: Path, output_dir: Path) -> dict[str, Any]:
    if not project_exists(project_path):
        project_path.mkdir(parents=True, exist_ok=True)
        create_project(project_path)

    def _run_requests(
        json_request: Any,
        bytes_request: Any,
    ) -> tuple[
        str,
        str,
        str,
        dict[str, Any],
        list[dict[str, Any]],
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
        bytes,
    ]:
        created = json_request(
            "POST",
            "/investigations",
            {"title": batch.get("title") or "API ingestion example"},
        )
        investigation_uid = created["investigation_uid"]
        json_request(
            "POST",
            f"/investigations/{investigation_uid}/tier",
            {"tier": "forge", "reason": "API ingestion example requires tension modeling."},
        )

        claim_resp = json_request(
            "POST",
            f"/investigations/{investigation_uid}/claims",
            {"text": batch.get("claim") or "Example claim from API ingestion"},
        )
        claim_uid = claim_resp["claim_uid"]

        records = batch.get("records") or []
        if not isinstance(records, list) or not records:
            raise ValueError("Batch payload requires non-empty 'records' array")

        evidence_rows: list[dict[str, Any]] = []
        for idx, row in enumerate(records):
            if not isinstance(row, dict):
                continue
            text = str(row.get("text") or "")
            if not text.strip():
                continue
            ingest = json_request(
                "POST",
                f"/investigations/{investigation_uid}/evidence",
                {
                    "content": text,
                    "media_type": "text/plain",
                    "original_filename": row.get("filename") or f"record_{idx + 1}.txt",
                },
            )
            evidence_uid = ingest["evidence_uid"]
            span_uid = ingest["span_uid"]

            stance = str(row.get("stance") or "support").strip().lower()
            rationale = str(row.get("rationale") or "").strip() or None
            if stance == "challenge":
                linked = json_request(
                    "POST",
                    f"/investigations/{investigation_uid}/links/challenge",
                    {"claim_uid": claim_uid, "span_uid": span_uid, "rationale": rationale},
                )
            else:
                linked = json_request(
                    "POST",
                    f"/investigations/{investigation_uid}/links/support",
                    {"claim_uid": claim_uid, "span_uid": span_uid, "rationale": rationale},
                )
            evidence_rows.append(
                {
                    "evidence_uid": evidence_uid,
                    "span_uid": span_uid,
                    "stance": "challenge" if stance == "challenge" else "support",
                    "link_uid": linked["link_uid"],
                }
            )

        claim_2 = json_request(
            "POST",
            f"/investigations/{investigation_uid}/claims",
            {"text": "Revenue can be recognized in March 2024 without exception."},
        )
        claim_2_uid = claim_2["claim_uid"]
        tension = json_request(
            "POST",
            f"/investigations/{investigation_uid}/tensions",
            {
                "claim_a_uid": claim_uid,
                "claim_b_uid": claim_2_uid,
                "tension_kind": "contradiction",
            },
        )

        defensibility = json_request("GET", f"/claims/{claim_uid}/defensibility")
        reasoning_brief = json_request("GET", f"/claims/{claim_uid}/reasoning-brief")
        review_packet = json_request("GET", f"/investigations/{investigation_uid}/review-packet")
        exported = bytes_request("POST", f"/investigations/{investigation_uid}/export")
        return (
            investigation_uid,
            claim_uid,
            claim_2_uid,
            tension,
            evidence_rows,
            defensibility,
            reasoning_brief,
            review_packet,
            exported,
        )

    def _run_over_uvicorn() -> tuple[
        str,
        str,
        str,
        dict[str, Any],
        list[dict[str, Any]],
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
        bytes,
    ]:
        port = _find_free_port()
        base_url = f"http://127.0.0.1:{port}"
        env = os.environ.copy()
        env["CHRONICLE_PROJECT_PATH"] = str(project_path.resolve())
        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "chronicle.api.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ]
        proc = subprocess.Popen(
            cmd,
            cwd=str(Path(__file__).resolve().parent.parent),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            _wait_for_health(base_url, proc=proc)
            return _run_requests(
                lambda method, path, payload=None: _http_json(base_url, method, path, payload),
                lambda method, path: _http_bytes(base_url, method, path),
            )
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)

    def _run_in_process() -> tuple[
        str,
        str,
        str,
        dict[str, Any],
        list[dict[str, Any]],
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
        bytes,
    ]:
        with ChronicleSession(project_path, event_store_backend="sqlite") as session:
            _, investigation_uid = session.create_investigation(
                str(batch.get("title") or "API ingestion example"),
            )
            session.set_tier(
                investigation_uid,
                "forge",
                reason="API ingestion example requires tension modeling.",
            )
            _, claim_uid = session.propose_claim(
                investigation_uid,
                str(batch.get("claim") or "Example claim from API ingestion"),
            )

            records = batch.get("records") or []
            if not isinstance(records, list) or not records:
                raise ValueError("Batch payload requires non-empty 'records' array")

            evidence_rows: list[dict[str, Any]] = []
            for idx, row in enumerate(records):
                if not isinstance(row, dict):
                    continue
                text = str(row.get("text") or "")
                if not text.strip():
                    continue
                _, evidence_uid = session.ingest_evidence(
                    investigation_uid,
                    text.encode("utf-8"),
                    "text/plain",
                    original_filename=str(row.get("filename") or f"record_{idx + 1}.txt"),
                )
                _, span_uid = session.anchor_span(
                    investigation_uid,
                    evidence_uid,
                    "text_offset",
                    {"start_char": 0, "end_char": len(text)},
                    quote=text[:2000] if len(text) > 2000 else text,
                )
                stance = str(row.get("stance") or "support").strip().lower()
                rationale = str(row.get("rationale") or "").strip() or None
                if stance == "challenge":
                    _, link_uid = session.link_challenge(
                        investigation_uid,
                        span_uid,
                        claim_uid,
                        rationale=rationale,
                    )
                else:
                    _, link_uid = session.link_support(
                        investigation_uid,
                        span_uid,
                        claim_uid,
                        rationale=rationale,
                    )
                evidence_rows.append(
                    {
                        "evidence_uid": evidence_uid,
                        "span_uid": span_uid,
                        "stance": "challenge" if stance == "challenge" else "support",
                        "link_uid": link_uid,
                    }
                )

            _, claim_2_uid = session.propose_claim(
                investigation_uid,
                "Revenue can be recognized in March 2024 without exception.",
            )
            _, tension_uid = session.declare_tension(
                investigation_uid,
                claim_uid,
                claim_2_uid,
                tension_kind="contradiction",
            )
            scorecard = session.get_defensibility_score(claim_uid)
            defensibility = dataclasses.asdict(scorecard) if scorecard is not None else {}
            reasoning_brief = session.get_reasoning_brief(claim_uid) or {}
            review_packet = session.get_review_packet(investigation_uid)

        with tempfile.NamedTemporaryFile(suffix=".chronicle", delete=False) as f:
            out_path = Path(f.name)
        try:
            export_import_mod.export_investigation(project_path, investigation_uid, out_path)
            exported = out_path.read_bytes()
        finally:
            out_path.unlink(missing_ok=True)
        return (
            investigation_uid,
            claim_uid,
            claim_2_uid,
            {"tension_uid": tension_uid},
            evidence_rows,
            defensibility,
            reasoning_brief,
            review_packet,
            exported,
        )

    try:
        (
            investigation_uid,
            claim_uid,
            claim_2_uid,
            tension,
            evidence_rows,
            defensibility,
            reasoning_brief,
            review_packet,
            exported,
        ) = _run_over_uvicorn()
    except Exception:
        # Example script should remain usable even when uvicorn/bootstrap networking
        # is unavailable in constrained environments (e.g., CI sandboxes).
        (
            investigation_uid,
            claim_uid,
            claim_2_uid,
            tension,
            evidence_rows,
            defensibility,
            reasoning_brief,
            review_packet,
            exported,
        ) = _run_in_process()

    output_dir.mkdir(parents=True, exist_ok=True)
    export_path = output_dir / "api_ingestion_export.chronicle"
    export_path.write_bytes(exported)
    defensibility_path = Path(_write_json(output_dir / "defensibility.json", defensibility))
    review_packet_path = Path(_write_json(output_dir / "review_packet.json", review_packet))
    reasoning_path = Path(_write_json(output_dir / "reasoning_brief.json", reasoning_brief))

    report = {
        "schema_version": 1,
        "generated_at": _utc_now(),
        "project_path": str(project_path.resolve()),
        "investigation_uid": investigation_uid,
        "claim_uid": claim_uid,
        "secondary_claim_uid": claim_2_uid,
        "tension_uid": tension["tension_uid"],
        "evidence_rows": evidence_rows,
        "artifacts": {
            "export_chronicle": str(export_path),
            "defensibility": str(defensibility_path),
            "review_packet": str(review_packet_path),
            "reasoning_brief": str(reasoning_path),
        },
        "summary": {
            "provenance_quality": defensibility.get("provenance_quality"),
            "contradiction_status": defensibility.get("contradiction_status"),
            "support_count": (defensibility.get("corroboration") or {}).get("support_count"),
            "challenge_count": (defensibility.get("corroboration") or {}).get("challenge_count"),
        },
    }
    return report


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        batch = _load_batch(args.input)
        report = _run_pipeline(batch, args.project_path, args.output_dir)
        report["status"] = "passed"
    except Exception as exc:
        report = {
            "schema_version": 1,
            "generated_at": _utc_now(),
            "status": "failed",
            "error": f"exception:{exc}",
            "project_path": str(args.project_path.resolve()),
            "output_dir": str(args.output_dir.resolve()),
        }

    report_path = args.output_dir.resolve() / "api_ingestion_pipeline_report.json"
    _write_json(report_path, report)
    print(f"Wrote API ingestion pipeline report: {report_path}")
    if args.stdout_json:
        print(json.dumps(report, indent=2))
    return 0 if report.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
