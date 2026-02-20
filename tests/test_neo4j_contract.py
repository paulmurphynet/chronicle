from __future__ import annotations

import sqlite3
import sys
from importlib import import_module
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_check_module = import_module("scripts.check_neo4j_contract")
_ingest_module = import_module("scripts.ingest_chronicle_to_aura")
_sync_module = import_module("chronicle.store.neo4j_sync")
_export_module = import_module("chronicle.store.neo4j_export")
_parser_module = import_module("chronicle.cli.parser")

run_checks = _check_module.run_checks
parse_ingest_args = _ingest_module._parse_args
sync_rationale_expr = _sync_module._evidence_link_rationale_expr
export_rationale_expr = _export_module._evidence_link_rationale_expr
build_parser = _parser_module.build_parser


def _normalized_text(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_neo4j_contract_check_passes() -> None:
    errors = run_checks(REPO_ROOT)
    assert errors == []


def test_ingest_cli_parses_project_and_dedupe_flag() -> None:
    args = parse_ingest_args(
        [
            "example.chronicle",
            "--project",
            "chronicle_graph_project",
            "--dedupe-evidence-by-content-hash",
        ]
    )
    assert str(args.chronicle_file).endswith("example.chronicle")
    assert str(args.project).endswith("chronicle_graph_project")
    assert args.dedupe_evidence_by_content_hash is True


def test_ingest_cli_parses_sync_hardening_options() -> None:
    args = parse_ingest_args(
        [
            "example.chronicle",
            "--database",
            "neo4j",
            "--max-retries",
            "5",
            "--retry-backoff-seconds",
            "2.5",
            "--connection-timeout-seconds",
            "30",
            "--sync-report",
            "reports/neo4j_sync_report.json",
            "--progress",
        ]
    )
    assert args.database == "neo4j"
    assert args.max_retries == 5
    assert args.retry_backoff_seconds == 2.5
    assert args.connection_timeout_seconds == 30.0
    assert str(args.sync_report).endswith("reports/neo4j_sync_report.json")
    assert args.progress is True


def test_neo4j_sync_uses_legacy_notes_column_for_rationale() -> None:
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE evidence_link (
          link_uid TEXT PRIMARY KEY,
          claim_uid TEXT NOT NULL,
          span_uid TEXT NOT NULL,
          link_type TEXT NOT NULL,
          notes TEXT,
          source_event_id TEXT NOT NULL
        )
        """
    )
    try:
        assert sync_rationale_expr(conn) == "coalesce(notes, '') AS rationale"
    finally:
        conn.close()


def test_neo4j_export_prefers_rationale_column_when_present() -> None:
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE evidence_link (
          link_uid TEXT PRIMARY KEY,
          claim_uid TEXT NOT NULL,
          span_uid TEXT NOT NULL,
          link_type TEXT NOT NULL,
          notes TEXT,
          rationale TEXT,
          source_event_id TEXT NOT NULL
        )
        """
    )
    try:
        assert export_rationale_expr(conn) == "coalesce(rationale, '') AS rationale"
    finally:
        conn.close()


def test_neo4j_link_edges_merge_by_link_uid() -> None:
    sync_text = _normalized_text(REPO_ROOT / "chronicle/store/neo4j_sync.py")
    rels_text = _normalized_text(REPO_ROOT / "neo4j/rebuild/03_relationships.cyp")
    assert "MERGE (s)-[r:SUPPORTS {link_uid: row.link_uid}]->(c)" in sync_text
    assert "MERGE (s)-[r:CHALLENGES {link_uid: row.link_uid}]->(c)" in sync_text
    assert "MERGE (s)-[r:SUPPORTS {link_uid: row.link_uid}]->(c)" in rels_text
    assert "MERGE (s)-[r:CHALLENGES {link_uid: row.link_uid}]->(c)" in rels_text


def test_cli_parser_accepts_neo4j_observability_flags() -> None:
    parser = build_parser(lambda raw: Path(raw))
    export_args = parser.parse_args(
        [
            "neo4j-export",
            "--path",
            ".",
            "--output",
            "neo4j_import",
            "--report",
            "reports/neo4j_export_report.json",
            "--progress",
        ]
    )
    assert str(export_args.report).endswith("reports/neo4j_export_report.json")
    assert export_args.progress is True

    sync_args = parser.parse_args(
        [
            "neo4j-sync",
            "--path",
            ".",
            "--report",
            "reports/neo4j_sync_report.json",
            "--progress",
        ]
    )
    assert str(sync_args.report).endswith("reports/neo4j_sync_report.json")
    assert sync_args.progress is True
