#!/usr/bin/env python3
"""Benchmark Chronicle Neo4j projection paths (CSV export and optional direct sync)."""

from __future__ import annotations

import argparse
import json
import sqlite3
import tempfile
import time
import tracemalloc
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from chronicle.store.neo4j_export import export_project_to_neo4j_csv
from chronicle.store.neo4j_sync import sync_project_to_neo4j
from chronicle.store.project import CHRONICLE_DB, create_project
from chronicle.store.session import ChronicleSession

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUTPUT = REPO_ROOT / "reports" / "neo4j_projection_benchmark.json"


@dataclass(frozen=True)
class SeedConfig:
    investigations: int
    claims_per_investigation: int
    evidence_per_investigation: int
    links_per_claim: int


@dataclass(frozen=True)
class ThresholdConfig:
    max_export_elapsed_ms: float | None
    max_export_peak_mib: float | None
    max_sync_elapsed_ms: float | None
    max_sync_peak_mib: float | None


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Benchmark Neo4j projection paths. By default this seeds a temporary Chronicle "
            "project, runs CSV export, and writes a JSON report. Optional direct sync can also run."
        )
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Benchmark report path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--project-path",
        type=Path,
        default=None,
        help="Use an existing Chronicle project path instead of generating a temporary benchmark project.",
    )
    parser.add_argument(
        "--csv-output-dir",
        type=Path,
        default=None,
        help="Directory for exported Neo4j CSV files (default: temp dir).",
    )
    parser.add_argument(
        "--investigations",
        type=int,
        default=8,
        help="Seeded investigations when --project-path is not provided (default: 8).",
    )
    parser.add_argument(
        "--claims-per-investigation",
        type=int,
        default=60,
        help="Seeded claims per investigation for generated benchmark projects (default: 60).",
    )
    parser.add_argument(
        "--evidence-per-investigation",
        type=int,
        default=120,
        help="Seeded evidence items per investigation for generated benchmark projects (default: 120).",
    )
    parser.add_argument(
        "--links-per-claim",
        type=int,
        default=2,
        help="Support/challenge links created per claim for generated benchmark projects (default: 2).",
    )
    parser.add_argument(
        "--run-sync",
        action="store_true",
        help="Also run direct Neo4j sync benchmark after CSV export.",
    )
    parser.add_argument("--neo4j-uri", default="", help="Neo4j URI (required when --run-sync).")
    parser.add_argument(
        "--neo4j-user",
        default="neo4j",
        help="Neo4j user (default: neo4j, used when --run-sync).",
    )
    parser.add_argument(
        "--neo4j-password",
        default="",
        help="Neo4j password (required when --run-sync).",
    )
    parser.add_argument(
        "--neo4j-database",
        default="",
        help="Optional Neo4j database name for sync benchmark.",
    )
    parser.add_argument(
        "--dedupe-evidence-by-content-hash",
        action="store_true",
        help="Enable dedupe mode for sync benchmark.",
    )
    parser.add_argument(
        "--sync-max-retries",
        type=int,
        default=3,
        help="Retry attempts for sync benchmark (default: 3).",
    )
    parser.add_argument(
        "--sync-retry-backoff-seconds",
        type=float,
        default=1.0,
        help="Retry backoff seconds for sync benchmark (default: 1.0).",
    )
    parser.add_argument(
        "--sync-connection-timeout-seconds",
        type=float,
        default=15.0,
        help="Connection timeout for sync benchmark (default: 15.0).",
    )
    parser.add_argument(
        "--max-export-elapsed-ms",
        type=float,
        default=None,
        help="Optional threshold: fail if export elapsed_ms exceeds this value.",
    )
    parser.add_argument(
        "--max-export-peak-mib",
        type=float,
        default=None,
        help="Optional threshold: fail if export peak memory (MiB) exceeds this value.",
    )
    parser.add_argument(
        "--max-sync-elapsed-ms",
        type=float,
        default=None,
        help="Optional threshold: fail if sync elapsed_ms exceeds this value.",
    )
    parser.add_argument(
        "--max-sync-peak-mib",
        type=float,
        default=None,
        help="Optional threshold: fail if sync peak memory (MiB) exceeds this value.",
    )
    return parser.parse_args(argv)


def _validate_seed_config(config: SeedConfig) -> None:
    if config.investigations < 1:
        raise ValueError("--investigations must be >= 1")
    if config.claims_per_investigation < 1:
        raise ValueError("--claims-per-investigation must be >= 1")
    if config.evidence_per_investigation < 1:
        raise ValueError("--evidence-per-investigation must be >= 1")
    if config.links_per_claim < 1:
        raise ValueError("--links-per-claim must be >= 1")


def _seed_project(project_path: Path, config: SeedConfig) -> None:
    create_project(project_path)
    with ChronicleSession(project_path) as session:
        for inv_idx in range(config.investigations):
            _, inv_uid = session.create_investigation(
                f"Neo4j benchmark investigation {inv_idx:03d}",
                actor_id="neo4j-benchmark",
                actor_type="tool",
            )
            span_uids: list[str] = []
            for ev_idx in range(config.evidence_per_investigation):
                body = (
                    f"benchmark_inv={inv_idx};evidence={ev_idx};"
                    f"group={ev_idx % 10};signal={(ev_idx * 17) % 97}"
                )
                _, evidence_uid = session.ingest_evidence(
                    inv_uid,
                    body.encode("utf-8"),
                    "text/plain",
                    original_filename=f"bench_{inv_idx:03d}_{ev_idx:05d}.txt",
                    actor_id="neo4j-benchmark",
                    actor_type="tool",
                )
                _, span_uid = session.anchor_span(
                    inv_uid,
                    evidence_uid,
                    "text_offset",
                    {"start_char": 0, "end_char": min(len(body), 64)},
                    quote=body[:64],
                    actor_id="neo4j-benchmark",
                    actor_type="tool",
                )
                span_uids.append(span_uid)

            for claim_idx in range(config.claims_per_investigation):
                _, claim_uid = session.propose_claim(
                    inv_uid,
                    (
                        f"Benchmark claim {claim_idx:04d} for investigation {inv_idx:03d}. "
                        f"Topic bucket {(claim_idx + inv_idx) % 12}."
                    ),
                    actor_id="neo4j-benchmark",
                    actor_type="tool",
                )
                for link_offset in range(config.links_per_claim):
                    span_uid = span_uids[(claim_idx + link_offset) % len(span_uids)]
                    if link_offset % 2 == 0:
                        session.link_support(
                            inv_uid,
                            span_uid,
                            claim_uid,
                            actor_id="neo4j-benchmark",
                            actor_type="tool",
                        )
                    else:
                        session.link_challenge(
                            inv_uid,
                            span_uid,
                            claim_uid,
                            actor_id="neo4j-benchmark",
                            actor_type="tool",
                        )


def _read_row_counts(project_path: Path) -> dict[str, int]:
    db_path = project_path / CHRONICLE_DB
    conn = sqlite3.connect(str(db_path))
    try:
        queries = {
            "investigations": "SELECT count(*) FROM investigation",
            "claims": "SELECT count(*) FROM claim",
            "evidence_items": "SELECT count(*) FROM evidence_item",
            "spans": "SELECT count(*) FROM evidence_span",
            "links": "SELECT count(*) FROM evidence_link",
            "tensions": "SELECT count(*) FROM tension",
        }
        return {name: int(conn.execute(sql).fetchone()[0]) for name, sql in queries.items()}
    finally:
        conn.close()


def _read_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _run_with_measurement(fn: Any) -> tuple[Any, float, int]:
    tracemalloc.start()
    started = time.perf_counter()
    try:
        result = fn()
    finally:
        elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
        _, peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    return result, elapsed_ms, int(peak_bytes)


def _validate_threshold(
    failures: list[str],
    *,
    metric_name: str,
    measured: float,
    threshold: float | None,
) -> None:
    if threshold is None:
        return
    if measured > threshold:
        failures.append(
            f"{metric_name} exceeded threshold: measured={measured:.3f}, threshold={threshold:.3f}"
        )


def _serialize_path(path: Path | None) -> str | None:
    return str(path) if path is not None else None


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    seed_config = SeedConfig(
        investigations=args.investigations,
        claims_per_investigation=args.claims_per_investigation,
        evidence_per_investigation=args.evidence_per_investigation,
        links_per_claim=args.links_per_claim,
    )
    thresholds = ThresholdConfig(
        max_export_elapsed_ms=args.max_export_elapsed_ms,
        max_export_peak_mib=args.max_export_peak_mib,
        max_sync_elapsed_ms=args.max_sync_elapsed_ms,
        max_sync_peak_mib=args.max_sync_peak_mib,
    )

    generated_project_dir: tempfile.TemporaryDirectory[str] | None = None
    generated_csv_dir: tempfile.TemporaryDirectory[str] | None = None
    try:
        if args.project_path is None:
            _validate_seed_config(seed_config)
            generated_project_dir = tempfile.TemporaryDirectory(
                prefix="chronicle_neo4j_bench_project_"
            )
            project_path = Path(generated_project_dir.name)
            _seed_project(project_path, seed_config)
            seeded_project = True
        else:
            project_path = args.project_path.resolve()
            if not (project_path / CHRONICLE_DB).is_file():
                print(
                    json.dumps(
                        {
                            "error": "invalid_project",
                            "message": f"Not a Chronicle project (missing {CHRONICLE_DB}): {project_path}",
                        }
                    )
                )
                return 1
            seeded_project = False

        if args.csv_output_dir is None:
            generated_csv_dir = tempfile.TemporaryDirectory(prefix="chronicle_neo4j_bench_csv_")
            csv_output_dir = Path(generated_csv_dir.name)
        else:
            csv_output_dir = args.csv_output_dir.resolve()
            csv_output_dir.mkdir(parents=True, exist_ok=True)

        export_report_path = csv_output_dir / "neo4j_export_report.json"
        _, export_elapsed_ms, export_peak_bytes = _run_with_measurement(
            lambda: export_project_to_neo4j_csv(
                project_path,
                csv_output_dir,
                report_path=export_report_path,
            )
        )

        payload: dict[str, Any] = {
            "kind": "neo4j_projection_benchmark",
            "generated_at": datetime.now(UTC).isoformat(),
            "project_path": str(project_path),
            "seeded_project": seeded_project,
            "seed_config": {
                "investigations": seed_config.investigations,
                "claims_per_investigation": seed_config.claims_per_investigation,
                "evidence_per_investigation": seed_config.evidence_per_investigation,
                "links_per_claim": seed_config.links_per_claim,
            }
            if seeded_project
            else None,
            "row_counts": _read_row_counts(project_path),
            "export": {
                "status": "passed",
                "csv_output_dir": str(csv_output_dir),
                "report_path": str(export_report_path),
                "elapsed_ms": export_elapsed_ms,
                "peak_memory_bytes": export_peak_bytes,
                "peak_memory_mib": round(export_peak_bytes / (1024 * 1024), 3),
                "report": _read_json_if_exists(export_report_path),
            },
            "sync": {
                "status": "skipped",
                "reason": "sync_not_requested",
            },
            "thresholds": {
                "max_export_elapsed_ms": thresholds.max_export_elapsed_ms,
                "max_export_peak_mib": thresholds.max_export_peak_mib,
                "max_sync_elapsed_ms": thresholds.max_sync_elapsed_ms,
                "max_sync_peak_mib": thresholds.max_sync_peak_mib,
            },
            "threshold_failures": [],
            "status": "passed",
        }

        threshold_failures: list[str] = payload["threshold_failures"]
        _validate_threshold(
            threshold_failures,
            metric_name="export.elapsed_ms",
            measured=export_elapsed_ms,
            threshold=thresholds.max_export_elapsed_ms,
        )
        _validate_threshold(
            threshold_failures,
            metric_name="export.peak_memory_mib",
            measured=payload["export"]["peak_memory_mib"],
            threshold=thresholds.max_export_peak_mib,
        )

        if args.run_sync:
            if not args.neo4j_uri.strip() or not args.neo4j_password:
                payload["sync"] = {
                    "status": "failed",
                    "reason": "missing_credentials",
                    "required": ["--neo4j-uri", "--neo4j-password"],
                }
                payload["status"] = "failed"
            else:
                sync_report_path = csv_output_dir / "neo4j_sync_report.json"
                try:
                    _, sync_elapsed_ms, sync_peak_bytes = _run_with_measurement(
                        lambda: sync_project_to_neo4j(
                            project_path,
                            args.neo4j_uri,
                            args.neo4j_user,
                            args.neo4j_password,
                            dedupe_evidence_by_content_hash=args.dedupe_evidence_by_content_hash,
                            database=(args.neo4j_database or "").strip() or None,
                            max_retries=args.sync_max_retries,
                            retry_backoff_seconds=args.sync_retry_backoff_seconds,
                            connection_timeout_seconds=args.sync_connection_timeout_seconds,
                            report_path=sync_report_path,
                            log_progress=False,
                        )
                    )
                    payload["sync"] = {
                        "status": "passed",
                        "report_path": str(sync_report_path),
                        "elapsed_ms": sync_elapsed_ms,
                        "peak_memory_bytes": sync_peak_bytes,
                        "peak_memory_mib": round(sync_peak_bytes / (1024 * 1024), 3),
                        "report": _read_json_if_exists(sync_report_path),
                        "dedupe_evidence_by_content_hash": bool(
                            args.dedupe_evidence_by_content_hash
                        ),
                        "database": (args.neo4j_database or "").strip() or "default",
                    }
                    _validate_threshold(
                        threshold_failures,
                        metric_name="sync.elapsed_ms",
                        measured=sync_elapsed_ms,
                        threshold=thresholds.max_sync_elapsed_ms,
                    )
                    _validate_threshold(
                        threshold_failures,
                        metric_name="sync.peak_memory_mib",
                        measured=payload["sync"]["peak_memory_mib"],
                        threshold=thresholds.max_sync_peak_mib,
                    )
                except Exception as e:
                    payload["sync"] = {
                        "status": "failed",
                        "report_path": _serialize_path(sync_report_path),
                        "error": str(e),
                    }
                    payload["status"] = "failed"

        if threshold_failures and payload["status"] != "failed":
            payload["status"] = "failed"

        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2))

        if payload["status"] != "passed":
            return 2 if threshold_failures else 1
        return 0
    finally:
        if generated_csv_dir is not None:
            generated_csv_dir.cleanup()
        if generated_project_dir is not None:
            generated_project_dir.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
