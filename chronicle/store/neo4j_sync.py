"""Sync Chronicle read model to Neo4j via the Neo4j driver. Optional; requires [neo4j] extra.

Spec: schemas.md 14.5, neo4j-pipeline.md 16. Order: schema, nodes, relationships, retractions.
Idempotent (MERGE). Full rebuild from read model; retractions applied per Phase 2.
Optional: dedupe by content — evidence by content_hash, claims by hash(claim_text); lineage via CONTAINS_EVIDENCE / CONTAINS_CLAIM.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
import time
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from chronicle.store.project import CHRONICLE_DB


def _claim_content_hash(claim_text: str | None) -> str:
    """Deterministic hash of claim text for deduplication."""
    text = (claim_text or "").strip()
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


BATCH_SIZE = 500
ProgressCallback = Callable[[dict[str, object]], None]

# Schema: constraints and indexes (01_schema.cyp equivalent)
_SCHEMA_STATEMENTS = [
    "CREATE CONSTRAINT investigation_uid_unique IF NOT EXISTS FOR (i:Investigation) REQUIRE i.uid IS UNIQUE",
    "CREATE CONSTRAINT source_uid_unique IF NOT EXISTS FOR (s:Source) REQUIRE s.uid IS UNIQUE",
    "CREATE CONSTRAINT claim_uid_unique IF NOT EXISTS FOR (c:Claim) REQUIRE c.uid IS UNIQUE",
    "CREATE CONSTRAINT evidence_uid_unique IF NOT EXISTS FOR (e:EvidenceItem) REQUIRE e.uid IS UNIQUE",
    "CREATE CONSTRAINT span_uid_unique IF NOT EXISTS FOR (s:EvidenceSpan) REQUIRE s.uid IS UNIQUE",
    "CREATE CONSTRAINT actor_uid_unique IF NOT EXISTS FOR (a:Actor) REQUIRE a.uid IS UNIQUE",
    "CREATE CONSTRAINT tension_uid_unique IF NOT EXISTS FOR (t:Tension) REQUIRE t.uid IS UNIQUE",
    "CREATE INDEX claim_type_idx IF NOT EXISTS FOR (c:Claim) ON (c.claim_type)",
    "CREATE INDEX claim_status_idx IF NOT EXISTS FOR (c:Claim) ON (c.current_status)",
    "CREATE INDEX tension_status_idx IF NOT EXISTS FOR (t:Tension) ON (t.status)",
    "CREATE INDEX evidence_content_hash_idx IF NOT EXISTS FOR (e:EvidenceItem) ON (e.content_hash)",
    "CREATE INDEX supports_link_uid_idx IF NOT EXISTS FOR ()-[r:SUPPORTS]-() ON (r.link_uid)",
    "CREATE INDEX challenges_link_uid_idx IF NOT EXISTS FOR ()-[r:CHALLENGES]-() ON (r.link_uid)",
    "CREATE INDEX contains_claim_uid_idx IF NOT EXISTS FOR ()-[r:CONTAINS_CLAIM]-() ON (r.claim_uid)",
    "CREATE INDEX contains_evidence_uid_idx IF NOT EXISTS FOR ()-[r:CONTAINS_EVIDENCE]-() ON (r.evidence_uid)",
]


def _iter_row_batches(
    conn: sqlite3.Connection, query: str, *, batch_size: int = BATCH_SIZE
) -> Iterator[list[dict[str, Any]]]:
    cur = conn.execute(query)
    columns = [d[0] for d in cur.description]
    while True:
        rows = cur.fetchmany(batch_size)
        if not rows:
            break
        yield [
            {c: (None if v is None else str(v)) for c, v in zip(columns, row, strict=True)}
            for row in rows
        ]


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _evidence_link_select_sql(conn: sqlite3.Connection, *, link_type: str) -> str:
    rationale_expr = _evidence_link_rationale_expr(conn)
    if link_type == "SUPPORTS":
        if rationale_expr == "coalesce(rationale, '') AS rationale":
            return (
                "SELECT span_uid, claim_uid, link_uid, source_event_id, "
                "coalesce(rationale, '') AS rationale "
                "FROM evidence_link WHERE link_type = 'SUPPORTS' ORDER BY link_uid"
            )
        if rationale_expr == "coalesce(notes, '') AS rationale":
            return (
                "SELECT span_uid, claim_uid, link_uid, source_event_id, "
                "coalesce(notes, '') AS rationale "
                "FROM evidence_link WHERE link_type = 'SUPPORTS' ORDER BY link_uid"
            )
        return (
            "SELECT span_uid, claim_uid, link_uid, source_event_id, "
            "'' AS rationale FROM evidence_link WHERE link_type = 'SUPPORTS' ORDER BY link_uid"
        )
    if link_type == "CHALLENGES":
        if rationale_expr == "coalesce(rationale, '') AS rationale":
            return (
                "SELECT span_uid, claim_uid, link_uid, source_event_id, "
                "coalesce(rationale, '') AS rationale "
                "FROM evidence_link WHERE link_type = 'CHALLENGES' ORDER BY link_uid"
            )
        if rationale_expr == "coalesce(notes, '') AS rationale":
            return (
                "SELECT span_uid, claim_uid, link_uid, source_event_id, "
                "coalesce(notes, '') AS rationale "
                "FROM evidence_link WHERE link_type = 'CHALLENGES' ORDER BY link_uid"
            )
        return (
            "SELECT span_uid, claim_uid, link_uid, source_event_id, "
            "'' AS rationale FROM evidence_link WHERE link_type = 'CHALLENGES' ORDER BY link_uid"
        )
    raise ValueError(f"Unsupported link_type: {link_type}")


def _evidence_link_select_with_claim_sql(conn: sqlite3.Connection, *, link_type: str) -> str:
    rationale_expr = _evidence_link_rationale_expr(conn)
    if rationale_expr == "coalesce(rationale, '') AS rationale":
        rationale_sql = "coalesce(el.rationale, '') AS rationale"
    elif rationale_expr == "coalesce(notes, '') AS rationale":
        rationale_sql = "coalesce(el.notes, '') AS rationale"
    else:
        rationale_sql = "'' AS rationale"
    return (
        "SELECT el.span_uid, el.claim_uid, el.link_uid, el.source_event_id, "
        f"{rationale_sql}, c.claim_text "
        "FROM evidence_link el "
        "JOIN claim c ON c.claim_uid = el.claim_uid "
        f"WHERE el.link_type = '{link_type}' "
        "ORDER BY el.link_uid"
    )


def _evidence_link_rationale_expr(conn: sqlite3.Connection) -> str:
    """Backward-compatible helper used by tests and scripts."""
    columns = _table_columns(conn, "evidence_link")
    if "rationale" in columns:
        return "coalesce(rationale, '') AS rationale"
    if "notes" in columns:
        return "coalesce(notes, '') AS rationale"
    return "'' AS rationale"


def _default_progress_sink(event: dict[str, object]) -> None:
    print(json.dumps(event, sort_keys=True), file=sys.stderr)


def _run_batched_sync_query(
    conn: sqlite3.Connection,
    session: Any,
    *,
    phase: str,
    query: str,
    cypher: str,
    progress: ProgressCallback | None = None,
    mutate_batch: Callable[[list[dict[str, Any]]], None] | None = None,
) -> dict[str, int | float]:
    rows_total = 0
    batch_count = 0
    started = time.perf_counter()
    if progress is not None:
        progress({"event": "phase_started", "phase": phase})
    for batch in _iter_row_batches(conn, query):
        batch_count += 1
        rows_total += len(batch)
        if mutate_batch is not None:
            mutate_batch(batch)
        session.run(cypher, rows=batch)
        if progress is not None:
            progress(
                {
                    "event": "batch",
                    "phase": phase,
                    "batch_index": batch_count,
                    "rows_in_batch": len(batch),
                    "rows_total": rows_total,
                }
            )
    elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
    stats: dict[str, int | float] = {
        "rows": rows_total,
        "batches": batch_count,
        "elapsed_ms": elapsed_ms,
    }
    if progress is not None:
        progress({"event": "phase_complete", "phase": phase, **stats})
    return stats


def _run_schema(
    driver: Any,
    *,
    database: str | None = None,
    progress: ProgressCallback | None = None,
) -> dict[str, int | float]:
    started = time.perf_counter()
    if progress is not None:
        progress({"event": "phase_started", "phase": "schema"})
    session_kwargs: dict[str, str] = {"database": database} if database else {}
    stmt_count = 0
    with driver.session(**session_kwargs) as session:
        for stmt in _SCHEMA_STATEMENTS:
            stmt_count += 1
            session.run(stmt)
            if progress is not None:
                progress(
                    {
                        "event": "batch",
                        "phase": "schema",
                        "batch_index": stmt_count,
                        "rows_in_batch": 1,
                        "rows_total": stmt_count,
                    }
                )
    elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
    stats: dict[str, int | float] = {
        "rows": stmt_count,
        "batches": stmt_count,
        "elapsed_ms": elapsed_ms,
    }
    if progress is not None:
        progress({"event": "phase_complete", "phase": "schema", **stats})
    return stats


def _sync_nodes(
    conn: sqlite3.Connection,
    driver: Any,
    *,
    database: str | None = None,
    dedupe_evidence_by_content_hash: bool = False,
    progress: ProgressCallback | None = None,
) -> dict[str, dict[str, int | float]]:
    session_kwargs: dict[str, str] = {"database": database} if database else {}
    stats: dict[str, dict[str, int | float]] = {}
    with driver.session(**session_kwargs) as session:
        # Investigations
        stats["investigations"] = _run_batched_sync_query(
            conn,
            session,
            phase="nodes.investigations",
            query="SELECT investigation_uid, title, description, is_archived, created_at, updated_at FROM investigation ORDER BY investigation_uid",
            progress=progress,
            cypher="""
                UNWIND $rows AS row
                MERGE (i:Investigation {uid: row.investigation_uid})
                ON CREATE SET
                  i.display_name = coalesce(CASE WHEN row.title IS NOT NULL AND row.title <> '' THEN row.title END, row.investigation_uid),
                  i.title = row.title,
                  i.description = row.description,
                  i.is_archived = (row.is_archived IN ['1', 'true', 'True']),
                  i.created_at = datetime(row.created_at),
                  i.updated_at = datetime(row.updated_at)
                ON MATCH SET
                  i.title = coalesce(CASE WHEN row.title IS NOT NULL AND row.title <> '' THEN row.title END, i.title),
                  i.description = coalesce(row.description, i.description),
                  i.is_archived = (row.is_archived IN ['1', 'true', 'True']),
                  i.updated_at = coalesce(datetime(row.updated_at), i.updated_at)
                """,
        )

        # Sources
        stats["sources"] = _run_batched_sync_query(
            conn,
            session,
            phase="nodes.sources",
            query="SELECT source_uid, investigation_uid, display_name, source_type, coalesce(alias,'') AS alias, created_at FROM source ORDER BY source_uid",
            progress=progress,
            cypher="""
                UNWIND $rows AS row
                MERGE (s:Source {uid: row.source_uid})
                ON CREATE SET
                  s.display_name = coalesce(CASE WHEN row.display_name IS NOT NULL AND row.display_name <> '' THEN row.display_name END, row.source_uid),
                  s.source_type = row.source_type,
                  s.alias = CASE WHEN row.alias <> '' THEN row.alias END,
                  s.investigation_uid = row.investigation_uid,
                  s.created_at = datetime(row.created_at)
                ON MATCH SET
                  s.display_name = coalesce(CASE WHEN row.display_name IS NOT NULL AND row.display_name <> '' THEN row.display_name END, s.display_name),
                  s.source_type = coalesce(row.source_type, s.source_type),
                  s.alias = coalesce(CASE WHEN row.alias <> '' THEN row.alias END, s.alias)
                """,
        )

        # Claims (when dedupe: one node per claim_content_hash; else one per claim_uid)
        if dedupe_evidence_by_content_hash:
            def _mutate_claims(batch: list[dict[str, Any]]) -> None:
                for row in batch:
                    row["claim_content_hash"] = _claim_content_hash(row.get("claim_text"))

            stats["claims"] = _run_batched_sync_query(
                conn,
                session,
                phase="nodes.claims",
                query="""SELECT claim_uid, investigation_uid, claim_text, claim_type, current_status,
                          decomposition_status, coalesce(parent_claim_uid,'') AS parent_claim_uid,
                          created_at, updated_at FROM claim ORDER BY claim_uid""",
                progress=progress,
                cypher="""
                    UNWIND $rows AS row
                    MERGE (c:Claim {uid: row.claim_content_hash})
                    ON CREATE SET
                      c.display_name = coalesce(CASE WHEN row.claim_text IS NOT NULL AND row.claim_text <> '' THEN row.claim_text END, row.claim_content_hash),
                      c.claim_text = row.claim_text,
                      c.claim_type = CASE WHEN row.claim_type <> '' THEN row.claim_type END,
                      c.current_status = coalesce(CASE WHEN row.current_status <> '' THEN row.current_status END, 'ACTIVE'),
                      c.decomposition_status = coalesce(CASE WHEN row.decomposition_status <> '' THEN row.decomposition_status END, 'unanalyzed'),
                      c.parent_claim_uid = CASE WHEN row.parent_claim_uid <> '' THEN row.parent_claim_uid END,
                      c.created_at = datetime(row.created_at),
                      c.updated_at = datetime(row.updated_at)
                    ON MATCH SET
                      c.claim_text = coalesce(CASE WHEN row.claim_text IS NOT NULL AND row.claim_text <> '' THEN row.claim_text END, c.claim_text),
                      c.claim_type = coalesce(CASE WHEN row.claim_type <> '' THEN row.claim_type END, c.claim_type),
                      c.current_status = coalesce(CASE WHEN row.current_status <> '' THEN row.current_status END, c.current_status),
                      c.decomposition_status = coalesce(CASE WHEN row.decomposition_status <> '' THEN row.decomposition_status END, c.decomposition_status),
                      c.parent_claim_uid = coalesce(CASE WHEN row.parent_claim_uid <> '' THEN row.parent_claim_uid END, c.parent_claim_uid),
                      c.updated_at = coalesce(datetime(row.updated_at), c.updated_at)
                    """,
                mutate_batch=_mutate_claims,
            )
        else:
            stats["claims"] = _run_batched_sync_query(
                conn,
                session,
                phase="nodes.claims",
                query="""SELECT claim_uid, investigation_uid, claim_text, claim_type, current_status,
                          decomposition_status, coalesce(parent_claim_uid,'') AS parent_claim_uid,
                          created_at, updated_at FROM claim ORDER BY claim_uid""",
                progress=progress,
                cypher="""
                    UNWIND $rows AS row
                    MERGE (c:Claim {uid: row.claim_uid})
                    ON CREATE SET
                      c.display_name = coalesce(CASE WHEN row.claim_text IS NOT NULL AND row.claim_text <> '' THEN row.claim_text END, row.claim_uid),
                      c.claim_text = row.claim_text,
                      c.claim_type = CASE WHEN row.claim_type <> '' THEN row.claim_type END,
                      c.current_status = coalesce(CASE WHEN row.current_status <> '' THEN row.current_status END, 'ACTIVE'),
                      c.decomposition_status = coalesce(CASE WHEN row.decomposition_status <> '' THEN row.decomposition_status END, 'unanalyzed'),
                      c.parent_claim_uid = CASE WHEN row.parent_claim_uid <> '' THEN row.parent_claim_uid END,
                      c.investigation_uid = row.investigation_uid,
                      c.created_at = datetime(row.created_at),
                      c.updated_at = datetime(row.updated_at)
                    ON MATCH SET
                      c.claim_text = coalesce(CASE WHEN row.claim_text IS NOT NULL AND row.claim_text <> '' THEN row.claim_text END, c.claim_text),
                      c.claim_type = coalesce(CASE WHEN row.claim_type <> '' THEN row.claim_type END, c.claim_type),
                      c.current_status = coalesce(CASE WHEN row.current_status <> '' THEN row.current_status END, c.current_status),
                      c.decomposition_status = coalesce(CASE WHEN row.decomposition_status <> '' THEN row.decomposition_status END, c.decomposition_status),
                      c.parent_claim_uid = coalesce(CASE WHEN row.parent_claim_uid <> '' THEN row.parent_claim_uid END, c.parent_claim_uid),
                      c.updated_at = coalesce(datetime(row.updated_at), c.updated_at)
                    """,
            )

        # EvidenceItem (E2.3: provenance_type; optional dedupe by content_hash)
        if dedupe_evidence_by_content_hash:
            stats["evidence_items"] = _run_batched_sync_query(
                conn,
                session,
                phase="nodes.evidence_items",
                query="""SELECT content_hash, evidence_uid, uri, media_type, created_at,
                          coalesce(provenance_type, '') AS provenance_type
                   FROM evidence_item ORDER BY content_hash, evidence_uid""",
                progress=progress,
                cypher="""
                    UNWIND $rows AS row
                    MERGE (e:EvidenceItem {uid: row.content_hash})
                    ON CREATE SET
                      e.display_name = coalesce(CASE WHEN row.uri IS NOT NULL AND row.uri <> '' THEN row.uri END, row.content_hash),
                      e.content_hash = row.content_hash,
                      e.uri = row.uri,
                      e.media_type = row.media_type,
                      e.created_at = datetime(row.created_at),
                      e.provenance_type = CASE WHEN row.provenance_type IS NOT NULL AND row.provenance_type <> '' THEN row.provenance_type ELSE null END
                    ON MATCH SET
                      e.uri = coalesce(CASE WHEN row.uri IS NOT NULL AND row.uri <> '' THEN row.uri END, e.uri),
                      e.media_type = coalesce(row.media_type, e.media_type),
                      e.provenance_type = CASE WHEN row.provenance_type IS NOT NULL AND row.provenance_type <> '' THEN row.provenance_type ELSE e.provenance_type END
                    """,
            )
            # Lineage: (Investigation)-[:CONTAINS_EVIDENCE {evidence_uid}]->(EvidenceItem)
            stats["contains_evidence"] = _run_batched_sync_query(
                conn,
                session,
                phase="nodes.contains_evidence",
                query="""SELECT investigation_uid, evidence_uid, content_hash
                   FROM evidence_item ORDER BY investigation_uid, evidence_uid""",
                progress=progress,
                cypher="""
                    UNWIND $rows AS row
                    MATCH (i:Investigation {uid: row.investigation_uid})
                    MATCH (e:EvidenceItem {uid: row.content_hash})
                    MERGE (i)-[r:CONTAINS_EVIDENCE]->(e)
                    ON CREATE SET r.evidence_uid = row.evidence_uid
                    """,
            )
        else:
            stats["evidence_items"] = _run_batched_sync_query(
                conn,
                session,
                phase="nodes.evidence_items",
                query="""SELECT evidence_uid, content_hash, uri, media_type, created_at,
                          coalesce(provenance_type, '') AS provenance_type
                   FROM evidence_item ORDER BY evidence_uid""",
                progress=progress,
                cypher="""
                    UNWIND $rows AS row
                    MERGE (e:EvidenceItem {uid: row.evidence_uid})
                    ON CREATE SET
                      e.display_name = coalesce(CASE WHEN row.uri IS NOT NULL AND row.uri <> '' THEN row.uri END, row.evidence_uid),
                      e.content_hash = row.content_hash,
                      e.uri = row.uri,
                      e.media_type = row.media_type,
                      e.created_at = datetime(row.created_at),
                      e.provenance_type = CASE WHEN row.provenance_type IS NOT NULL AND row.provenance_type <> '' THEN row.provenance_type ELSE null END
                    ON MATCH SET
                      e.uri = coalesce(CASE WHEN row.uri IS NOT NULL AND row.uri <> '' THEN row.uri END, e.uri),
                      e.media_type = coalesce(row.media_type, e.media_type),
                      e.provenance_type = CASE WHEN row.provenance_type IS NOT NULL AND row.provenance_type <> '' THEN row.provenance_type ELSE e.provenance_type END
                    """,
            )

        # EvidenceSpan
        stats["spans"] = _run_batched_sync_query(
            conn,
            session,
            phase="nodes.spans",
            query="SELECT span_uid, evidence_uid, anchor_type, anchor_json, created_at, source_event_id FROM evidence_span ORDER BY span_uid",
            progress=progress,
            cypher="""
                UNWIND $rows AS row
                MERGE (s:EvidenceSpan {uid: row.span_uid})
                ON CREATE SET
                  s.display_name = coalesce(row.span_uid, row.span_uid),
                  s.anchor_type = row.anchor_type,
                  s.anchor_json = row.anchor_json,
                  s.created_at = datetime(row.created_at)
                ON MATCH SET
                  s.anchor_type = coalesce(row.anchor_type, s.anchor_type),
                  s.anchor_json = coalesce(row.anchor_json, s.anchor_json)
                """,
        )

        # Actors
        stats["actors"] = _run_batched_sync_query(
            conn,
            session,
            phase="nodes.actors",
            query="SELECT DISTINCT actor_id AS actor_uid, actor_type, actor_id AS display_name FROM events ORDER BY actor_id",
            progress=progress,
            cypher="""
                UNWIND $rows AS row
                MERGE (a:Actor {uid: row.actor_uid})
                ON CREATE SET
                  a.display_name = coalesce(CASE WHEN row.display_name IS NOT NULL AND row.display_name <> '' THEN row.display_name END, row.actor_uid),
                  a.actor_type = row.actor_type
                ON MATCH SET
                  a.actor_type = coalesce(row.actor_type, a.actor_type)
                """,
        )

        # Tensions
        stats["tensions"] = _run_batched_sync_query(
            conn,
            session,
            phase="nodes.tensions",
            query="""SELECT tension_uid, coalesce(tension_kind,'') AS tension_kind, status, created_at
               FROM tension ORDER BY tension_uid""",
            progress=progress,
            cypher="""
                UNWIND $rows AS row
                MERGE (t:Tension {uid: row.tension_uid})
                ON CREATE SET
                  t.display_name = coalesce(row.tension_uid, row.tension_uid),
                  t.kind = CASE WHEN row.tension_kind <> '' THEN row.tension_kind END,
                  t.status = coalesce(CASE WHEN row.status <> '' THEN row.status END, 'OPEN'),
                  t.created_at = datetime(row.created_at)
                ON MATCH SET
                  t.kind = coalesce(CASE WHEN row.tension_kind <> '' THEN row.tension_kind END, t.kind),
                  t.status = coalesce(CASE WHEN row.status <> '' THEN row.status END, t.status)
                """,
        )
    return stats


def _sync_relationships(
    conn: sqlite3.Connection,
    driver: Any,
    *,
    database: str | None = None,
    dedupe_evidence_by_content_hash: bool = False,
    progress: ProgressCallback | None = None,
) -> dict[str, dict[str, int | float]]:
    session_kwargs: dict[str, str] = {"database": database} if database else {}
    stats: dict[str, dict[str, int | float]] = {}
    with driver.session(**session_kwargs) as session:
        # Span IN EvidenceItem (when dedupe: match EvidenceItem by content_hash)
        if dedupe_evidence_by_content_hash:
            stats["in"] = _run_batched_sync_query(
                conn,
                session,
                phase="relationships.in",
                query="""SELECT es.span_uid, ei.content_hash, es.source_event_id
                   FROM evidence_span es
                   JOIN evidence_item ei ON es.evidence_uid = ei.evidence_uid
                   ORDER BY es.span_uid""",
                progress=progress,
                cypher="""
                    UNWIND $rows AS row
                    MATCH (s:EvidenceSpan {uid: row.span_uid})
                    MATCH (e:EvidenceItem {uid: row.content_hash})
                    MERGE (s)-[r:IN]->(e)
                    ON CREATE SET r.source_event_id = row.source_event_id
                    """,
            )
        else:
            stats["in"] = _run_batched_sync_query(
                conn,
                session,
                phase="relationships.in",
                query="SELECT span_uid, evidence_uid, source_event_id FROM evidence_span ORDER BY span_uid",
                progress=progress,
                cypher="""
                    UNWIND $rows AS row
                    MATCH (s:EvidenceSpan {uid: row.span_uid})
                    MATCH (e:EvidenceItem {uid: row.evidence_uid})
                    MERGE (s)-[r:IN]->(e)
                    ON CREATE SET r.source_event_id = row.source_event_id
                    """,
            )

        # SUPPORTS
        if dedupe_evidence_by_content_hash:
            def _mutate_supports_claim_hash(batch: list[dict[str, Any]]) -> None:
                for row in batch:
                    row["claim_content_hash"] = _claim_content_hash(row.get("claim_text"))

            stats["supports"] = _run_batched_sync_query(
                conn,
                session,
                phase="relationships.supports",
                query=_evidence_link_select_with_claim_sql(conn, link_type="SUPPORTS"),
                progress=progress,
                cypher="""
                    UNWIND $rows AS row
                    MATCH (s:EvidenceSpan {uid: row.span_uid})
                    MATCH (c:Claim {uid: row.claim_content_hash})
                    MERGE (s)-[r:SUPPORTS {link_uid: row.link_uid}]->(c)
                    ON CREATE SET r.source_event_id = row.source_event_id, r.link_uid = row.link_uid, r.rationale = row.rationale
                    """,
                mutate_batch=_mutate_supports_claim_hash,
            )
        else:
            stats["supports"] = _run_batched_sync_query(
                conn,
                session,
                phase="relationships.supports",
                query=_evidence_link_select_sql(conn, link_type="SUPPORTS"),
                progress=progress,
                cypher="""
                    UNWIND $rows AS row
                    MATCH (s:EvidenceSpan {uid: row.span_uid})
                    MATCH (c:Claim {uid: row.claim_uid})
                    MERGE (s)-[r:SUPPORTS {link_uid: row.link_uid}]->(c)
                    ON CREATE SET r.source_event_id = row.source_event_id, r.link_uid = row.link_uid, r.rationale = row.rationale
                    """,
            )

        # CHALLENGES
        if dedupe_evidence_by_content_hash:
            def _mutate_challenges_claim_hash(batch: list[dict[str, Any]]) -> None:
                for row in batch:
                    row["claim_content_hash"] = _claim_content_hash(row.get("claim_text"))

            stats["challenges"] = _run_batched_sync_query(
                conn,
                session,
                phase="relationships.challenges",
                query=_evidence_link_select_with_claim_sql(conn, link_type="CHALLENGES"),
                progress=progress,
                cypher="""
                    UNWIND $rows AS row
                    MATCH (s:EvidenceSpan {uid: row.span_uid})
                    MATCH (c:Claim {uid: row.claim_content_hash})
                    MERGE (s)-[r:CHALLENGES {link_uid: row.link_uid}]->(c)
                    ON CREATE SET r.source_event_id = row.source_event_id, r.link_uid = row.link_uid, r.rationale = row.rationale
                    """,
                mutate_batch=_mutate_challenges_claim_hash,
            )
        else:
            stats["challenges"] = _run_batched_sync_query(
                conn,
                session,
                phase="relationships.challenges",
                query=_evidence_link_select_sql(conn, link_type="CHALLENGES"),
                progress=progress,
                cypher="""
                    UNWIND $rows AS row
                    MATCH (s:EvidenceSpan {uid: row.span_uid})
                    MATCH (c:Claim {uid: row.claim_uid})
                    MERGE (s)-[r:CHALLENGES {link_uid: row.link_uid}]->(c)
                    ON CREATE SET r.source_event_id = row.source_event_id, r.link_uid = row.link_uid, r.rationale = row.rationale
                    """,
            )

        # ASSERTS
        if dedupe_evidence_by_content_hash:
            def _mutate_asserts_claim_hash(batch: list[dict[str, Any]]) -> None:
                for row in batch:
                    row["claim_content_hash"] = _claim_content_hash(row.get("claim_text"))

            stats["asserts"] = _run_batched_sync_query(
                conn,
                session,
                phase="relationships.asserts",
                query="""SELECT ca.assertion_uid, ca.claim_uid, ca.actor_id AS actor_uid, ca.asserted_at,
                          ca.assertion_mode AS mode, ca.confidence, ca.source_event_id, c.claim_text
                   FROM claim_assertion ca
                   JOIN claim c ON c.claim_uid = ca.claim_uid
                   ORDER BY ca.assertion_uid""",
                progress=progress,
                cypher="""
                    UNWIND $rows AS row
                    MATCH (a:Actor {uid: row.actor_uid})
                    MATCH (c:Claim {uid: row.claim_content_hash})
                    MERGE (a)-[r:ASSERTS]->(c)
                    ON CREATE SET
                      r.source_event_id = row.source_event_id,
                      r.asserted_at = datetime(row.asserted_at),
                      r.mode = row.mode,
                      r.confidence = CASE WHEN row.confidence IS NOT NULL AND row.confidence <> '' THEN toFloat(row.confidence) END
                    """,
                mutate_batch=_mutate_asserts_claim_hash,
            )
        else:
            stats["asserts"] = _run_batched_sync_query(
                conn,
                session,
                phase="relationships.asserts",
                query="""SELECT assertion_uid, claim_uid, actor_id AS actor_uid, asserted_at,
                          assertion_mode AS mode, confidence, source_event_id
                   FROM claim_assertion ORDER BY assertion_uid""",
                progress=progress,
                cypher="""
                    UNWIND $rows AS row
                    MATCH (a:Actor {uid: row.actor_uid})
                    MATCH (c:Claim {uid: row.claim_uid})
                    MERGE (a)-[r:ASSERTS]->(c)
                    ON CREATE SET
                      r.source_event_id = row.source_event_id,
                      r.asserted_at = datetime(row.asserted_at),
                      r.mode = row.mode,
                      r.confidence = CASE WHEN row.confidence IS NOT NULL AND row.confidence <> '' THEN toFloat(row.confidence) END
                    """,
            )

        # Tension BETWEEN (two edges per row)
        if dedupe_evidence_by_content_hash:
            def _mutate_between_claim_hash(batch: list[dict[str, Any]]) -> None:
                for row in batch:
                    row["claim_a_content_hash"] = _claim_content_hash(row.get("claim_a_text"))
                    row["claim_b_content_hash"] = _claim_content_hash(row.get("claim_b_text"))

            stats["between"] = _run_batched_sync_query(
                conn,
                session,
                phase="relationships.between",
                query="""SELECT t.tension_uid, t.claim_a_uid, t.claim_b_uid, t.source_event_id,
                          ca.claim_text AS claim_a_text, cb.claim_text AS claim_b_text
                   FROM tension t
                   JOIN claim ca ON ca.claim_uid = t.claim_a_uid
                   JOIN claim cb ON cb.claim_uid = t.claim_b_uid
                   ORDER BY t.tension_uid""",
                progress=progress,
                cypher="""
                    UNWIND $rows AS row
                    MATCH (t:Tension {uid: row.tension_uid})
                    MATCH (c1:Claim {uid: row.claim_a_content_hash})
                    MATCH (c2:Claim {uid: row.claim_b_content_hash})
                    MERGE (t)-[r1:BETWEEN]->(c1)
                    ON CREATE SET r1.source_event_id = row.source_event_id
                    MERGE (t)-[r2:BETWEEN]->(c2)
                    ON CREATE SET r2.source_event_id = row.source_event_id
                    """,
                mutate_batch=_mutate_between_claim_hash,
            )
        else:
            stats["between"] = _run_batched_sync_query(
                conn,
                session,
                phase="relationships.between",
                query="SELECT tension_uid, claim_a_uid, claim_b_uid, source_event_id FROM tension ORDER BY tension_uid",
                progress=progress,
                cypher="""
                    UNWIND $rows AS row
                    MATCH (t:Tension {uid: row.tension_uid})
                    MATCH (c1:Claim {uid: row.claim_a_uid})
                    MATCH (c2:Claim {uid: row.claim_b_uid})
                    MERGE (t)-[r1:BETWEEN]->(c1)
                    ON CREATE SET r1.source_event_id = row.source_event_id
                    MERGE (t)-[r2:BETWEEN]->(c2)
                    ON CREATE SET r2.source_event_id = row.source_event_id
                    """,
            )

        # SUPERSEDES (when dedupe: match EvidenceItem by content_hash)
        if dedupe_evidence_by_content_hash:
            stats["supersedes"] = _run_batched_sync_query(
                conn,
                session,
                phase="relationships.supersedes",
                query="""SELECT es.new_evidence_uid, es.prior_evidence_uid, es.supersession_type,
                          coalesce(es.reason,'') AS reason, es.source_event_id,
                          en.content_hash AS new_content_hash, ep.content_hash AS prior_content_hash
                   FROM evidence_supersession es
                   JOIN evidence_item en ON es.new_evidence_uid = en.evidence_uid
                   JOIN evidence_item ep ON es.prior_evidence_uid = ep.evidence_uid
                   ORDER BY es.supersession_uid""",
                progress=progress,
                cypher="""
                    UNWIND $rows AS row
                    MATCH (eNew:EvidenceItem {uid: row.new_content_hash})
                    MATCH (ePrior:EvidenceItem {uid: row.prior_content_hash})
                    MERGE (eNew)-[r:SUPERSEDES]->(ePrior)
                    ON CREATE SET
                      r.source_event_id = row.source_event_id,
                      r.type = row.supersession_type,
                      r.reason = CASE WHEN row.reason <> '' THEN row.reason END
                    """,
            )
        else:
            stats["supersedes"] = _run_batched_sync_query(
                conn,
                session,
                phase="relationships.supersedes",
                query="""SELECT new_evidence_uid, prior_evidence_uid, supersession_type, coalesce(reason,'') AS reason, source_event_id
                   FROM evidence_supersession ORDER BY supersession_uid""",
                progress=progress,
                cypher="""
                    UNWIND $rows AS row
                    MATCH (eNew:EvidenceItem {uid: row.new_evidence_uid})
                    MATCH (ePrior:EvidenceItem {uid: row.prior_evidence_uid})
                    MERGE (eNew)-[r:SUPERSEDES]->(ePrior)
                    ON CREATE SET
                      r.source_event_id = row.source_event_id,
                      r.type = row.supersession_type,
                      r.reason = CASE WHEN row.reason <> '' THEN row.reason END
                    """,
            )

        # DECOMPOSES_TO (when dedupe: match Claim by content_hash)
        if dedupe_evidence_by_content_hash:
            def _mutate_decomposes_claim_hash(batch: list[dict[str, Any]]) -> None:
                for row in batch:
                    row["parent_content_hash"] = (
                        _claim_content_hash(row.get("parent_claim_text"))
                        if row.get("parent_claim_text") is not None
                        else row["parent_uid"]
                    )
                    row["child_content_hash"] = (
                        _claim_content_hash(row.get("child_claim_text"))
                        if row.get("child_claim_text") is not None
                        else row["child_uid"]
                    )

            stats["decomposes_to"] = _run_batched_sync_query(
                conn,
                session,
                phase="relationships.decomposes_to",
                query="""SELECT c.claim_uid AS child_uid, c.parent_claim_uid AS parent_uid, e.event_id AS source_event_id,
                          c.claim_text AS child_claim_text, p.claim_text AS parent_claim_text
                   FROM claim c
                   LEFT JOIN claim p ON p.claim_uid = c.parent_claim_uid
                   JOIN events e ON e.subject_uid = c.claim_uid AND e.event_type = 'ClaimProposed'
                   WHERE c.parent_claim_uid IS NOT NULL ORDER BY c.claim_uid""",
                progress=progress,
                cypher="""
                    UNWIND $rows AS row
                    MATCH (parent:Claim {uid: row.parent_content_hash})
                    MATCH (child:Claim {uid: row.child_content_hash})
                    MERGE (parent)-[r:DECOMPOSES_TO]->(child)
                    ON CREATE SET r.source_event_id = row.source_event_id
                    """,
                mutate_batch=_mutate_decomposes_claim_hash,
            )
        else:
            stats["decomposes_to"] = _run_batched_sync_query(
                conn,
                session,
                phase="relationships.decomposes_to",
                query="""SELECT c.claim_uid AS child_uid, c.parent_claim_uid AS parent_uid, e.event_id AS source_event_id
                   FROM claim c
                   JOIN events e ON e.subject_uid = c.claim_uid AND e.event_type = 'ClaimProposed'
                   WHERE c.parent_claim_uid IS NOT NULL ORDER BY c.claim_uid""",
                progress=progress,
                cypher="""
                    UNWIND $rows AS row
                    MATCH (parent:Claim {uid: row.parent_uid})
                    MATCH (child:Claim {uid: row.child_uid})
                    MERGE (parent)-[r:DECOMPOSES_TO]->(child)
                    ON CREATE SET r.source_event_id = row.source_event_id
                    """,
            )

        # CONTAINS (Investigation -> Claim). When dedupe: CONTAINS_CLAIM with claim_uid on rel
        if dedupe_evidence_by_content_hash:
            def _mutate_contains_claim_hash(batch: list[dict[str, Any]]) -> None:
                for row in batch:
                    row["claim_content_hash"] = _claim_content_hash(row.get("claim_text"))

            stats["contains_claim"] = _run_batched_sync_query(
                conn,
                session,
                phase="relationships.contains_claim",
                query="SELECT investigation_uid, claim_uid, claim_text FROM claim ORDER BY claim_uid",
                progress=progress,
                cypher="""
                    UNWIND $rows AS row
                    MATCH (i:Investigation {uid: row.investigation_uid})
                    MATCH (c:Claim {uid: row.claim_content_hash})
                    MERGE (i)-[r:CONTAINS_CLAIM]->(c)
                    ON CREATE SET r.claim_uid = row.claim_uid
                    """,
                mutate_batch=_mutate_contains_claim_hash,
            )
        else:
            stats["contains_claim"] = _run_batched_sync_query(
                conn,
                session,
                phase="relationships.contains_claim",
                query="SELECT investigation_uid, claim_uid FROM claim ORDER BY claim_uid",
                progress=progress,
                cypher="""
                    UNWIND $rows AS row
                    MATCH (i:Investigation {uid: row.investigation_uid})
                    MATCH (c:Claim {uid: row.claim_uid})
                    MERGE (i)-[r:CONTAINS]->(c)
                    ON CREATE SET r.source_event_id = ''
                    """,
            )

        # PROVIDED_BY (when dedupe: match EvidenceItem by content_hash)
        if dedupe_evidence_by_content_hash:
            stats["provided_by"] = _run_batched_sync_query(
                conn,
                session,
                phase="relationships.provided_by",
                query="""SELECT esl.evidence_uid, esl.source_uid, coalesce(esl.relationship,'') AS relationship,
                          esl.source_event_id, ei.content_hash
                   FROM evidence_source_link esl
                   JOIN evidence_item ei ON esl.evidence_uid = ei.evidence_uid
                   ORDER BY esl.evidence_uid, esl.source_uid""",
                progress=progress,
                cypher="""
                    UNWIND $rows AS row
                    MATCH (e:EvidenceItem {uid: row.content_hash})
                    MATCH (s:Source {uid: row.source_uid})
                    MERGE (e)-[r:PROVIDED_BY]->(s)
                    ON CREATE SET
                      r.source_event_id = row.source_event_id,
                      r.relationship = CASE WHEN row.relationship <> '' THEN row.relationship END
                    """,
            )
        else:
            stats["provided_by"] = _run_batched_sync_query(
                conn,
                session,
                phase="relationships.provided_by",
                query="SELECT evidence_uid, source_uid, coalesce(relationship,'') AS relationship, source_event_id FROM evidence_source_link ORDER BY evidence_uid, source_uid",
                progress=progress,
                cypher="""
                    UNWIND $rows AS row
                    MATCH (e:EvidenceItem {uid: row.evidence_uid})
                    MATCH (s:Source {uid: row.source_uid})
                    MERGE (e)-[r:PROVIDED_BY]->(s)
                    ON CREATE SET
                      r.source_event_id = row.source_event_id,
                      r.relationship = CASE WHEN row.relationship <> '' THEN row.relationship END
                    """,
            )
    return stats


def _sync_retractions(
    conn: sqlite3.Connection,
    driver: Any,
    *,
    database: str | None = None,
    progress: ProgressCallback | None = None,
) -> dict[str, dict[str, int | float]]:
    session_kwargs: dict[str, str] = {"database": database} if database else {}
    with driver.session(**session_kwargs) as session:
        stats = _run_batched_sync_query(
            conn,
            session,
            phase="retractions.links",
            query="""SELECT link_uid, retracted_at, coalesce(rationale, '') AS rationale
               FROM evidence_link_retraction
               ORDER BY link_uid""",
            progress=progress,
            cypher="""
                UNWIND $rows AS row
                MATCH (s:EvidenceSpan)-[r:SUPPORTS|CHALLENGES]->(c:Claim)
                WHERE r.link_uid = row.link_uid
                SET r.retracted_at = datetime(row.retracted_at),
                    r.retracted_reason = CASE WHEN row.rationale IS NOT NULL AND trim(row.rationale) <> '' THEN row.rationale END
                """,
        )
    return {"links": stats}


def sync_project_to_neo4j(
    project_dir: Path | str,
    uri: str,
    user: str,
    password: str,
    *,
    dedupe_evidence_by_content_hash: bool | None = None,
    database: str | None = None,
    max_retries: int | None = None,
    retry_backoff_seconds: float | None = None,
    connection_timeout_seconds: float | None = None,
    report_path: Path | str | None = None,
    log_progress: bool = False,
) -> None:
    """Sync a Chronicle project read model to Neo4j. Idempotent (MERGE). Full rebuild; retractions applied.

    When dedupe_evidence_by_content_hash is True (or set via NEO4J_DEDUPE_EVIDENCE_BY_CONTENT_HASH=1),
    full deduplication is enabled: one EvidenceItem per content_hash and one Claim per hash(claim_text).
    Lineage: (Investigation)-[:CONTAINS_EVIDENCE {evidence_uid}]->(EvidenceItem) and
    (Investigation)-[:CONTAINS_CLAIM {claim_uid}]->(Claim).
    """
    project_dir = Path(project_dir)
    db_path = project_dir / CHRONICLE_DB
    if not db_path.is_file():
        raise FileNotFoundError(f"Not a Chronicle project (no {CHRONICLE_DB}): {project_dir}")

    if dedupe_evidence_by_content_hash is None:
        dedupe_evidence_by_content_hash = os.environ.get(
            "NEO4J_DEDUPE_EVIDENCE_BY_CONTENT_HASH", ""
        ).strip().lower() in ("1", "true", "yes")

    if database is None:
        database = os.environ.get("NEO4J_DATABASE")
    database = (database or "").strip() or None

    if max_retries is None:
        retries_raw = os.environ.get("NEO4J_SYNC_MAX_RETRIES", "3").strip()
        try:
            max_retries = int(retries_raw)
        except ValueError as e:
            raise ValueError(
                f"NEO4J_SYNC_MAX_RETRIES must be an integer, got: {retries_raw!r}"
            ) from e
    if max_retries < 1:
        raise ValueError(f"max_retries must be >= 1, got: {max_retries}")

    if retry_backoff_seconds is None:
        backoff_raw = os.environ.get("NEO4J_SYNC_RETRY_BACKOFF_SECONDS", "1.0").strip()
        try:
            retry_backoff_seconds = float(backoff_raw)
        except ValueError as e:
            raise ValueError(
                f"NEO4J_SYNC_RETRY_BACKOFF_SECONDS must be a number, got: {backoff_raw!r}"
            ) from e
    if retry_backoff_seconds < 0:
        raise ValueError(f"retry_backoff_seconds must be >= 0, got: {retry_backoff_seconds}")

    if connection_timeout_seconds is None:
        timeout_raw = os.environ.get("NEO4J_CONNECTION_TIMEOUT_SECONDS", "15").strip()
        try:
            connection_timeout_seconds = float(timeout_raw)
        except ValueError as e:
            raise ValueError(
                f"NEO4J_CONNECTION_TIMEOUT_SECONDS must be a number, got: {timeout_raw!r}"
            ) from e
    if connection_timeout_seconds <= 0:
        raise ValueError(
            f"connection_timeout_seconds must be > 0, got: {connection_timeout_seconds}"
        )

    progress = _default_progress_sink if log_progress else None
    started_at = datetime.now(UTC).isoformat()
    started_perf = time.perf_counter()
    if progress is not None:
        progress(
            {
                "event": "sync_started",
                "kind": "neo4j_sync_report",
                "project_dir": str(project_dir),
                "uri": uri,
                "database": database or "default",
                "started_at": started_at,
                "dedupe_evidence_by_content_hash": dedupe_evidence_by_content_hash,
            }
        )

    from neo4j import GraphDatabase  # type: ignore[attr-defined]
    from neo4j.exceptions import (
        AuthError,
        ConfigurationError,
        ServiceUnavailable,
        SessionExpired,
        TransientError,
    )  # type: ignore[attr-defined]

    attempts = max(1, max_retries)
    last_error: Exception | None = None
    last_attempt = 0

    def _emit_report(
        *,
        status: str,
        attempt_used: int,
        phase_stats: dict[str, object] | None = None,
        error: str | None = None,
        event: str,
    ) -> None:
        completed_at = datetime.now(UTC).isoformat()
        elapsed_ms = round((time.perf_counter() - started_perf) * 1000.0, 3)
        report: dict[str, object] = {
            "kind": "neo4j_sync_report",
            "status": status,
            "project_dir": str(project_dir),
            "uri": uri,
            "database": database or "default",
            "dedupe_evidence_by_content_hash": dedupe_evidence_by_content_hash,
            "started_at": started_at,
            "completed_at": completed_at,
            "elapsed_ms": elapsed_ms,
            "attempts_configured": attempts,
            "attempts_used": attempt_used,
        }
        if phase_stats is not None:
            report["phase_stats"] = phase_stats
        if error is not None:
            report["error"] = error
        if report_path is not None:
            rp = Path(report_path)
            rp.parent.mkdir(parents=True, exist_ok=True)
            rp.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        if progress is not None:
            progress({"event": event, **report})

    for attempt in range(1, attempts + 1):
        last_attempt = attempt
        if progress is not None:
            progress({"event": "attempt_started", "attempt": attempt, "attempts": attempts})
        driver = GraphDatabase.driver(
            uri,
            auth=(user, password),
            connection_timeout=connection_timeout_seconds,
        )
        try:
            driver.verify_connectivity()
            conn = sqlite3.connect(str(db_path))
            try:
                schema_stats = _run_schema(driver, database=database, progress=progress)
                node_stats = _sync_nodes(
                    conn,
                    driver,
                    database=database,
                    dedupe_evidence_by_content_hash=dedupe_evidence_by_content_hash,
                    progress=progress,
                )
                relationship_stats = _sync_relationships(
                    conn,
                    driver,
                    database=database,
                    dedupe_evidence_by_content_hash=dedupe_evidence_by_content_hash,
                    progress=progress,
                )
                retraction_stats = _sync_retractions(
                    conn,
                    driver,
                    database=database,
                    progress=progress,
                )
            finally:
                conn.close()
            _emit_report(
                status="passed",
                attempt_used=attempt,
                phase_stats={
                    "schema": schema_stats,
                    "nodes": node_stats,
                    "relationships": relationship_stats,
                    "retractions": retraction_stats,
                },
                event="sync_complete",
            )
            return
        except AuthError as e:
            error = ConnectionError(
                f"Neo4j authentication failed for {uri} as user '{user}': {e}"
            )
            _emit_report(
                status="failed",
                attempt_used=attempt,
                error=str(error),
                event="sync_failed",
            )
            raise error from e
        except ConfigurationError as e:
            error = ConnectionError(
                f"Neo4j configuration error for {uri} (database={database or 'default'}): {e}"
            )
            _emit_report(
                status="failed",
                attempt_used=attempt,
                error=str(error),
                event="sync_failed",
            )
            raise error from e
        except (ServiceUnavailable, SessionExpired, TransientError) as e:
            last_error = e
            if attempt >= attempts:
                break
            sleep_seconds = retry_backoff_seconds * attempt
            if progress is not None:
                progress(
                    {
                        "event": "retry_scheduled",
                        "attempt": attempt,
                        "attempts": attempts,
                        "sleep_seconds": sleep_seconds,
                        "error": str(e),
                    }
                )
            time.sleep(sleep_seconds)
        except Exception as e:
            error = ConnectionError(
                f"Neo4j sync failed for {uri} (database={database or 'default'}): {e}"
            )
            _emit_report(
                status="failed",
                attempt_used=attempt,
                error=str(error),
                event="sync_failed",
            )
            raise error from e
        finally:
            driver.close()

    error = ConnectionError(
        f"Neo4j sync failed after {attempts} attempts for {uri} "
        f"(database={database or 'default'}). Last error: {last_error}"
    )
    _emit_report(
        status="failed",
        attempt_used=last_attempt or attempts,
        error=str(error),
        event="sync_failed",
    )
    raise error from last_error
