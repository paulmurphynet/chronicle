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

run_checks = _check_module.run_checks
parse_ingest_args = _ingest_module._parse_args
sync_rationale_expr = _sync_module._evidence_link_rationale_expr
export_rationale_expr = _export_module._evidence_link_rationale_expr


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
