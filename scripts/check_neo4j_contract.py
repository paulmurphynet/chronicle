#!/usr/bin/env python3
"""Validate Neo4j sync/export/docs/rebuild contract consistency."""

from __future__ import annotations

import argparse
import csv
import re
import tempfile
from pathlib import Path

from chronicle.store.neo4j_export import export_project_to_neo4j_csv
from chronicle.store.neo4j_sync import _SCHEMA_STATEMENTS
from chronicle.store.project import create_project

EXPECTED_EXPORT_HEADERS: dict[str, list[str]] = {
    "actors.csv": ["actor_uid", "actor_type", "display_name"],
    "asserts.csv": [
        "assertion_uid",
        "claim_uid",
        "actor_uid",
        "asserted_at",
        "mode",
        "confidence",
        "source_event_id",
    ],
    "claims.csv": [
        "claim_uid",
        "investigation_uid",
        "claim_text",
        "claim_type",
        "current_status",
        "decomposition_status",
        "parent_claim_uid",
        "created_at",
        "updated_at",
    ],
    "decomposition_edges.csv": ["child_uid", "parent_uid", "source_event_id"],
    "evidence_items.csv": [
        "evidence_uid",
        "content_hash",
        "uri",
        "media_type",
        "created_at",
        "provenance_type",
    ],
    "evidence_source_links.csv": ["evidence_uid", "source_uid", "relationship", "source_event_id"],
    "investigations.csv": [
        "investigation_uid",
        "title",
        "description",
        "is_archived",
        "created_at",
        "updated_at",
    ],
    "link_retractions.csv": [
        "link_uid",
        "claim_uid",
        "span_uid",
        "link_type",
        "retracted_at",
        "rationale",
    ],
    "links.csv": [
        "link_uid",
        "claim_uid",
        "span_uid",
        "link_type",
        "rationale",
        "created_at",
        "source_event_id",
    ],
    "sources.csv": [
        "source_uid",
        "investigation_uid",
        "display_name",
        "source_type",
        "alias",
        "created_at",
    ],
    "spans.csv": [
        "span_uid",
        "evidence_uid",
        "anchor_type",
        "anchor_json",
        "created_at",
        "source_event_id",
    ],
    "supersession.csv": [
        "supersession_uid",
        "new_evidence_uid",
        "prior_evidence_uid",
        "supersession_type",
        "reason",
        "created_at",
        "source_event_id",
    ],
    "tensions.csv": [
        "tension_uid",
        "claim_a_uid",
        "claim_b_uid",
        "tension_kind",
        "status",
        "created_at",
        "source_event_id",
    ],
}

DEDUPE_ONLY_RELATIONSHIPS = {"CONTAINS_CLAIM", "CONTAINS_EVIDENCE"}


def _normalize_cypher_statement(statement: str) -> str:
    return " ".join(statement.split())


def _read_cypher_statements(path: Path) -> list[str]:
    lines: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("//"):
            continue
        line = raw
        if "//" in line:
            line = line.split("//", 1)[0]
        if line.strip():
            lines.append(line)
    joined = "\n".join(lines)
    out: list[str] = []
    for part in joined.split(";"):
        norm = _normalize_cypher_statement(part.strip())
        if norm:
            out.append(norm)
    return out


def _read_export_headers(output_dir: Path) -> dict[str, list[str]]:
    headers: dict[str, list[str]] = {}
    for path in sorted(output_dir.glob("*.csv")):
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            first_row = next(reader, [])
        headers[path.name] = [h.strip() for h in first_row]
    return headers


def _extract_csv_refs(*cypher_paths: Path) -> set[str]:
    refs: set[str] = set()
    pattern = re.compile(r"file:///([^']+\.csv)")
    for path in cypher_paths:
        refs.update(pattern.findall(path.read_text(encoding="utf-8")))
    return refs


def _extract_labels_from_text(text: str) -> set[str]:
    return set(re.findall(r":([A-Za-z][A-Za-z0-9_]*)\s*\{uid:", text))


def _extract_relationships_from_text(text: str) -> set[str]:
    return set(re.findall(r"\[[A-Za-z0-9_]+:?([A-Z_]+)\]", text))


def _extract_markdown_table_values(md_text: str, heading: str) -> set[str]:
    marker = f"## {heading}"
    start = md_text.find(marker)
    if start < 0:
        return set()
    remainder = md_text[start + len(marker) :]
    next_heading = remainder.find("\n## ")
    section = remainder if next_heading < 0 else remainder[:next_heading]
    return set(re.findall(r"\|\s+\*\*([A-Za-z_]+)\*\*", section))


def run_checks(repo_root: Path) -> list[str]:
    errors: list[str] = []

    schema_path = repo_root / "neo4j/rebuild/01_schema.cyp"
    nodes_path = repo_root / "neo4j/rebuild/02_nodes.cyp"
    rels_path = repo_root / "neo4j/rebuild/03_relationships.cyp"
    retract_path = repo_root / "neo4j/rebuild/04_retractions.cyp"
    docs_schema_path = repo_root / "docs/neo4j-schema.md"
    sync_path = repo_root / "chronicle/store/neo4j_sync.py"

    schema_sync = {_normalize_cypher_statement(s) for s in _SCHEMA_STATEMENTS}
    schema_cyp = set(_read_cypher_statements(schema_path))
    if schema_sync != schema_cyp:
        only_sync = sorted(schema_sync - schema_cyp)
        only_cyp = sorted(schema_cyp - schema_sync)
        if only_sync:
            errors.append(f"Schema statements missing in 01_schema.cyp: {only_sync}")
        if only_cyp:
            errors.append(f"Schema statements present only in 01_schema.cyp: {only_cyp}")

    with tempfile.TemporaryDirectory(prefix="chronicle_neo4j_contract_") as tmp:
        tmp_path = Path(tmp)
        project = tmp_path / "project"
        output = tmp_path / "csv"
        create_project(project)
        export_project_to_neo4j_csv(project, output)
        headers = _read_export_headers(output)

    expected_files = set(EXPECTED_EXPORT_HEADERS.keys())
    actual_files = set(headers.keys())
    if actual_files != expected_files:
        missing = sorted(expected_files - actual_files)
        extra = sorted(actual_files - expected_files)
        if missing:
            errors.append(f"Missing exported CSV files: {missing}")
        if extra:
            errors.append(f"Unexpected exported CSV files: {extra}")

    for filename, expected_header in EXPECTED_EXPORT_HEADERS.items():
        actual_header = headers.get(filename)
        if actual_header != expected_header:
            errors.append(
                f"CSV header mismatch for {filename}: expected {expected_header}, got {actual_header}"
            )

    cypher_refs = _extract_csv_refs(nodes_path, rels_path, retract_path)
    if cypher_refs != expected_files:
        missing_refs = sorted(expected_files - cypher_refs)
        extra_refs = sorted(cypher_refs - expected_files)
        if missing_refs:
            errors.append(
                f"CSV files exported but not referenced by rebuild Cypher: {missing_refs}"
            )
        if extra_refs:
            errors.append(f"CSV files referenced by rebuild Cypher but not exported: {extra_refs}")

    sync_text = sync_path.read_text(encoding="utf-8")
    rebuild_text = (
        nodes_path.read_text(encoding="utf-8") + "\n" + rels_path.read_text(encoding="utf-8")
    )
    docs_text = docs_schema_path.read_text(encoding="utf-8")

    sync_labels = _extract_labels_from_text(sync_text)
    rebuild_labels = _extract_labels_from_text(rebuild_text)
    docs_labels = _extract_markdown_table_values(docs_text, "Node labels")

    if sync_labels != rebuild_labels:
        errors.append(
            f"Node label mismatch between sync and rebuild scripts: sync={sorted(sync_labels)}, rebuild={sorted(rebuild_labels)}"
        )
    if docs_labels != sync_labels:
        errors.append(
            f"Node label mismatch between docs and sync: docs={sorted(docs_labels)}, sync={sorted(sync_labels)}"
        )

    sync_rels = _extract_relationships_from_text(sync_text)
    rebuild_rels = _extract_relationships_from_text(
        rels_path.read_text(encoding="utf-8") + "\n" + retract_path.read_text(encoding="utf-8")
    )
    docs_rels = _extract_markdown_table_values(docs_text, "Relationship types")

    if not rebuild_rels.issubset(sync_rels):
        errors.append(
            f"Relationship mismatch: rebuild has relationships not present in sync: {sorted(rebuild_rels - sync_rels)}"
        )
    if not DEDUPE_ONLY_RELATIONSHIPS.issubset(sync_rels - rebuild_rels):
        errors.append(
            "Expected dedupe-only relationships (CONTAINS_CLAIM, CONTAINS_EVIDENCE) are not isolated to sync-only mode"
        )
    if not sync_rels.issubset(docs_rels):
        errors.append(
            f"Relationship docs missing sync relationships: {sorted(sync_rels - docs_rels)}"
        )

    rels_text = rels_path.read_text(encoding="utf-8")
    if rels_text.count("r.rationale") < 2:
        errors.append(
            "03_relationships.cyp should set r.rationale for both SUPPORTS and CHALLENGES edges"
        )

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check Neo4j schema/integration contract consistency"
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Repository root (default: parent of scripts/)",
    )
    args = parser.parse_args(argv)
    repo_root = args.repo_root.resolve()

    errors = run_checks(repo_root)
    if errors:
        print("Neo4j contract check failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Neo4j contract check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
