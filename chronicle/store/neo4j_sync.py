"""Sync Chronicle read model to Neo4j via the Neo4j driver. Optional; requires [neo4j] extra.

Spec: schemas.md 14.5, neo4j-pipeline.md 16. Order: schema, nodes, relationships, retractions.
Idempotent (MERGE). Full rebuild from read model; retractions applied per Phase 2.
Optional: dedupe by content — evidence by content_hash, claims by hash(claim_text); lineage via CONTAINS_EVIDENCE / CONTAINS_CLAIM.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
from pathlib import Path
from typing import Any

from chronicle.store.project import CHRONICLE_DB


def _claim_content_hash(claim_text: str | None) -> str:
    """Deterministic hash of claim text for deduplication."""
    text = (claim_text or "").strip()
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


BATCH_SIZE = 500

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


def _fetch_rows(conn: sqlite3.Connection, query: str) -> list[dict[str, Any]]:
    cur = conn.execute(query)
    columns = [d[0] for d in cur.description]
    return [
        {c: (None if v is None else str(v)) for c, v in zip(columns, row, strict=True)}
        for row in cur.fetchall()
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


def _evidence_link_rationale_expr(conn: sqlite3.Connection) -> str:
    """Backward-compatible helper used by tests and scripts."""
    columns = _table_columns(conn, "evidence_link")
    if "rationale" in columns:
        return "coalesce(rationale, '') AS rationale"
    if "notes" in columns:
        return "coalesce(notes, '') AS rationale"
    return "'' AS rationale"


def _batched(rows: list[dict[str, Any]], size: int):
    for i in range(0, len(rows), size):
        yield rows[i : i + size]


def _run_schema(driver: Any) -> None:
    with driver.session() as session:
        for stmt in _SCHEMA_STATEMENTS:
            session.run(stmt)


def _sync_nodes(
    conn: sqlite3.Connection,
    driver: Any,
    *,
    dedupe_evidence_by_content_hash: bool = False,
) -> None:
    with driver.session() as session:
        # Investigations
        rows = _fetch_rows(
            conn,
            "SELECT investigation_uid, title, description, is_archived, created_at, updated_at FROM investigation ORDER BY investigation_uid",
        )
        for batch in _batched(rows, BATCH_SIZE):
            session.run(
                """
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
                rows=batch,
            )

        # Sources
        rows = _fetch_rows(
            conn,
            "SELECT source_uid, investigation_uid, display_name, source_type, coalesce(alias,'') AS alias, created_at FROM source ORDER BY source_uid",
        )
        for batch in _batched(rows, BATCH_SIZE):
            session.run(
                """
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
                rows=batch,
            )

        # Claims (when dedupe: one node per claim_content_hash; else one per claim_uid)
        if dedupe_evidence_by_content_hash:
            rows = _fetch_rows(
                conn,
                """SELECT claim_uid, investigation_uid, claim_text, claim_type, current_status,
                          decomposition_status, coalesce(parent_claim_uid,'') AS parent_claim_uid,
                          created_at, updated_at FROM claim ORDER BY claim_uid""",
            )
            for r in rows:
                r["claim_content_hash"] = _claim_content_hash(r.get("claim_text"))
            for batch in _batched(rows, BATCH_SIZE):
                session.run(
                    """
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
                    rows=batch,
                )
        else:
            rows = _fetch_rows(
                conn,
                """SELECT claim_uid, investigation_uid, claim_text, claim_type, current_status,
                          decomposition_status, coalesce(parent_claim_uid,'') AS parent_claim_uid,
                          created_at, updated_at FROM claim ORDER BY claim_uid""",
            )
            for batch in _batched(rows, BATCH_SIZE):
                session.run(
                    """
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
                    rows=batch,
                )

        # EvidenceItem (E2.3: provenance_type; optional dedupe by content_hash)
        if dedupe_evidence_by_content_hash:
            rows = _fetch_rows(
                conn,
                """SELECT content_hash, evidence_uid, uri, media_type, created_at,
                          coalesce(provenance_type, '') AS provenance_type
                   FROM evidence_item ORDER BY content_hash, evidence_uid""",
            )
            for batch in _batched(rows, BATCH_SIZE):
                session.run(
                    """
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
                    rows=batch,
                )
            # Lineage: (Investigation)-[:CONTAINS_EVIDENCE {evidence_uid}]->(EvidenceItem)
            rows = _fetch_rows(
                conn,
                """SELECT investigation_uid, evidence_uid, content_hash
                   FROM evidence_item ORDER BY investigation_uid, evidence_uid""",
            )
            for batch in _batched(rows, BATCH_SIZE):
                session.run(
                    """
                    UNWIND $rows AS row
                    MATCH (i:Investigation {uid: row.investigation_uid})
                    MATCH (e:EvidenceItem {uid: row.content_hash})
                    MERGE (i)-[r:CONTAINS_EVIDENCE]->(e)
                    ON CREATE SET r.evidence_uid = row.evidence_uid
                    """,
                    rows=batch,
                )
        else:
            rows = _fetch_rows(
                conn,
                """SELECT evidence_uid, content_hash, uri, media_type, created_at,
                          coalesce(provenance_type, '') AS provenance_type
                   FROM evidence_item ORDER BY evidence_uid""",
            )
            for batch in _batched(rows, BATCH_SIZE):
                session.run(
                    """
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
                    rows=batch,
                )

        # EvidenceSpan
        rows = _fetch_rows(
            conn,
            "SELECT span_uid, evidence_uid, anchor_type, anchor_json, created_at, source_event_id FROM evidence_span ORDER BY span_uid",
        )
        for batch in _batched(rows, BATCH_SIZE):
            session.run(
                """
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
                rows=batch,
            )

        # Actors
        rows = _fetch_rows(
            conn,
            "SELECT DISTINCT actor_id AS actor_uid, actor_type, actor_id AS display_name FROM events ORDER BY actor_id",
        )
        for batch in _batched(rows, BATCH_SIZE):
            session.run(
                """
                UNWIND $rows AS row
                MERGE (a:Actor {uid: row.actor_uid})
                ON CREATE SET
                  a.display_name = coalesce(CASE WHEN row.display_name IS NOT NULL AND row.display_name <> '' THEN row.display_name END, row.actor_uid),
                  a.actor_type = row.actor_type
                ON MATCH SET
                  a.actor_type = coalesce(row.actor_type, a.actor_type)
                """,
                rows=batch,
            )

        # Tensions
        rows = _fetch_rows(
            conn,
            """SELECT tension_uid, coalesce(tension_kind,'') AS tension_kind, status, created_at
               FROM tension ORDER BY tension_uid""",
        )
        for batch in _batched(rows, BATCH_SIZE):
            session.run(
                """
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
                rows=batch,
            )


def _sync_relationships(
    conn: sqlite3.Connection,
    driver: Any,
    *,
    dedupe_evidence_by_content_hash: bool = False,
) -> None:
    # When dedupe: resolve claim_uid -> claim_content_hash for relationship MATCHes
    claim_uid_to_content_hash: dict[str, str] = {}
    if dedupe_evidence_by_content_hash:
        for r in _fetch_rows(conn, "SELECT claim_uid, claim_text FROM claim"):
            claim_uid_to_content_hash[r["claim_uid"]] = _claim_content_hash(r.get("claim_text"))

    with driver.session() as session:
        # Span IN EvidenceItem (when dedupe: match EvidenceItem by content_hash)
        if dedupe_evidence_by_content_hash:
            rows = _fetch_rows(
                conn,
                """SELECT es.span_uid, ei.content_hash, es.source_event_id
                   FROM evidence_span es
                   JOIN evidence_item ei ON es.evidence_uid = ei.evidence_uid
                   ORDER BY es.span_uid""",
            )
            for batch in _batched(rows, BATCH_SIZE):
                session.run(
                    """
                    UNWIND $rows AS row
                    MATCH (s:EvidenceSpan {uid: row.span_uid})
                    MATCH (e:EvidenceItem {uid: row.content_hash})
                    MERGE (s)-[r:IN]->(e)
                    ON CREATE SET r.source_event_id = row.source_event_id
                    """,
                    rows=batch,
                )
        else:
            rows = _fetch_rows(
                conn,
                "SELECT span_uid, evidence_uid, source_event_id FROM evidence_span ORDER BY span_uid",
            )
            for batch in _batched(rows, BATCH_SIZE):
                session.run(
                    """
                    UNWIND $rows AS row
                    MATCH (s:EvidenceSpan {uid: row.span_uid})
                    MATCH (e:EvidenceItem {uid: row.evidence_uid})
                    MERGE (s)-[r:IN]->(e)
                    ON CREATE SET r.source_event_id = row.source_event_id
                    """,
                    rows=batch,
                )

        # SUPPORTS
        rows = _fetch_rows(
            conn,
            _evidence_link_select_sql(conn, link_type="SUPPORTS"),
        )
        if dedupe_evidence_by_content_hash:
            for r in rows:
                r["claim_content_hash"] = claim_uid_to_content_hash.get(
                    r["claim_uid"], r["claim_uid"]
                )
            for batch in _batched(rows, BATCH_SIZE):
                session.run(
                    """
                    UNWIND $rows AS row
                    MATCH (s:EvidenceSpan {uid: row.span_uid})
                    MATCH (c:Claim {uid: row.claim_content_hash})
                    MERGE (s)-[r:SUPPORTS]->(c)
                    ON CREATE SET r.source_event_id = row.source_event_id, r.link_uid = row.link_uid, r.rationale = row.rationale
                    """,
                    rows=batch,
                )
        else:
            for batch in _batched(rows, BATCH_SIZE):
                session.run(
                    """
                    UNWIND $rows AS row
                    MATCH (s:EvidenceSpan {uid: row.span_uid})
                    MATCH (c:Claim {uid: row.claim_uid})
                    MERGE (s)-[r:SUPPORTS]->(c)
                    ON CREATE SET r.source_event_id = row.source_event_id, r.link_uid = row.link_uid, r.rationale = row.rationale
                    """,
                    rows=batch,
                )

        # CHALLENGES
        rows = _fetch_rows(
            conn,
            _evidence_link_select_sql(conn, link_type="CHALLENGES"),
        )
        if dedupe_evidence_by_content_hash:
            for r in rows:
                r["claim_content_hash"] = claim_uid_to_content_hash.get(
                    r["claim_uid"], r["claim_uid"]
                )
            for batch in _batched(rows, BATCH_SIZE):
                session.run(
                    """
                    UNWIND $rows AS row
                    MATCH (s:EvidenceSpan {uid: row.span_uid})
                    MATCH (c:Claim {uid: row.claim_content_hash})
                    MERGE (s)-[r:CHALLENGES]->(c)
                    ON CREATE SET r.source_event_id = row.source_event_id, r.link_uid = row.link_uid, r.rationale = row.rationale
                    """,
                    rows=batch,
                )
        else:
            for batch in _batched(rows, BATCH_SIZE):
                session.run(
                    """
                    UNWIND $rows AS row
                    MATCH (s:EvidenceSpan {uid: row.span_uid})
                    MATCH (c:Claim {uid: row.claim_uid})
                    MERGE (s)-[r:CHALLENGES]->(c)
                    ON CREATE SET r.source_event_id = row.source_event_id, r.link_uid = row.link_uid, r.rationale = row.rationale
                    """,
                    rows=batch,
                )

        # ASSERTS
        rows = _fetch_rows(
            conn,
            """SELECT assertion_uid, claim_uid, actor_id AS actor_uid, asserted_at,
                      assertion_mode AS mode, confidence, source_event_id
               FROM claim_assertion ORDER BY assertion_uid""",
        )
        if dedupe_evidence_by_content_hash:
            for r in rows:
                r["claim_content_hash"] = claim_uid_to_content_hash.get(
                    r["claim_uid"], r["claim_uid"]
                )
        for batch in _batched(rows, BATCH_SIZE):
            claim_key = "claim_content_hash" if dedupe_evidence_by_content_hash else "claim_uid"
            session.run(
                f"""
                UNWIND $rows AS row
                MATCH (a:Actor {{uid: row.actor_uid}})
                MATCH (c:Claim {{uid: row.{claim_key}}})
                MERGE (a)-[r:ASSERTS]->(c)
                ON CREATE SET
                  r.source_event_id = row.source_event_id,
                  r.asserted_at = datetime(row.asserted_at),
                  r.mode = row.mode,
                  r.confidence = CASE WHEN row.confidence IS NOT NULL AND row.confidence <> '' THEN toFloat(row.confidence) END
                """,
                rows=batch,
            )

        # Tension BETWEEN (two edges per row)
        rows = _fetch_rows(
            conn,
            "SELECT tension_uid, claim_a_uid, claim_b_uid, source_event_id FROM tension ORDER BY tension_uid",
        )
        if dedupe_evidence_by_content_hash:
            for r in rows:
                r["claim_a_content_hash"] = claim_uid_to_content_hash.get(
                    r["claim_a_uid"], r["claim_a_uid"]
                )
                r["claim_b_content_hash"] = claim_uid_to_content_hash.get(
                    r["claim_b_uid"], r["claim_b_uid"]
                )
        for batch in _batched(rows, BATCH_SIZE):
            if dedupe_evidence_by_content_hash:
                session.run(
                    """
                    UNWIND $rows AS row
                    MATCH (t:Tension {uid: row.tension_uid})
                    MATCH (c1:Claim {uid: row.claim_a_content_hash})
                    MATCH (c2:Claim {uid: row.claim_b_content_hash})
                    MERGE (t)-[r1:BETWEEN]->(c1)
                    ON CREATE SET r1.source_event_id = row.source_event_id
                    MERGE (t)-[r2:BETWEEN]->(c2)
                    ON CREATE SET r2.source_event_id = row.source_event_id
                    """,
                    rows=batch,
                )
            else:
                session.run(
                    """
                    UNWIND $rows AS row
                    MATCH (t:Tension {uid: row.tension_uid})
                    MATCH (c1:Claim {uid: row.claim_a_uid})
                    MATCH (c2:Claim {uid: row.claim_b_uid})
                    MERGE (t)-[r1:BETWEEN]->(c1)
                    ON CREATE SET r1.source_event_id = row.source_event_id
                    MERGE (t)-[r2:BETWEEN]->(c2)
                    ON CREATE SET r2.source_event_id = row.source_event_id
                    """,
                    rows=batch,
                )

        # SUPERSEDES (when dedupe: match EvidenceItem by content_hash)
        if dedupe_evidence_by_content_hash:
            rows = _fetch_rows(
                conn,
                """SELECT es.new_evidence_uid, es.prior_evidence_uid, es.supersession_type,
                          coalesce(es.reason,'') AS reason, es.source_event_id,
                          en.content_hash AS new_content_hash, ep.content_hash AS prior_content_hash
                   FROM evidence_supersession es
                   JOIN evidence_item en ON es.new_evidence_uid = en.evidence_uid
                   JOIN evidence_item ep ON es.prior_evidence_uid = ep.evidence_uid
                   ORDER BY es.supersession_uid""",
            )
            for batch in _batched(rows, BATCH_SIZE):
                session.run(
                    """
                    UNWIND $rows AS row
                    MATCH (eNew:EvidenceItem {uid: row.new_content_hash})
                    MATCH (ePrior:EvidenceItem {uid: row.prior_content_hash})
                    MERGE (eNew)-[r:SUPERSEDES]->(ePrior)
                    ON CREATE SET
                      r.source_event_id = row.source_event_id,
                      r.type = row.supersession_type,
                      r.reason = CASE WHEN row.reason <> '' THEN row.reason END
                    """,
                    rows=batch,
                )
        else:
            rows = _fetch_rows(
                conn,
                """SELECT new_evidence_uid, prior_evidence_uid, supersession_type, coalesce(reason,'') AS reason, source_event_id
                   FROM evidence_supersession ORDER BY supersession_uid""",
            )
            for batch in _batched(rows, BATCH_SIZE):
                session.run(
                    """
                    UNWIND $rows AS row
                    MATCH (eNew:EvidenceItem {uid: row.new_evidence_uid})
                    MATCH (ePrior:EvidenceItem {uid: row.prior_evidence_uid})
                    MERGE (eNew)-[r:SUPERSEDES]->(ePrior)
                    ON CREATE SET
                      r.source_event_id = row.source_event_id,
                      r.type = row.supersession_type,
                      r.reason = CASE WHEN row.reason <> '' THEN row.reason END
                    """,
                    rows=batch,
                )

        # DECOMPOSES_TO (when dedupe: match Claim by content_hash)
        rows = _fetch_rows(
            conn,
            """SELECT c.claim_uid AS child_uid, c.parent_claim_uid AS parent_uid, e.event_id AS source_event_id
               FROM claim c
               JOIN events e ON e.subject_uid = c.claim_uid AND e.event_type = 'ClaimProposed'
               WHERE c.parent_claim_uid IS NOT NULL ORDER BY c.claim_uid""",
        )
        if dedupe_evidence_by_content_hash:
            for r in rows:
                r["parent_content_hash"] = claim_uid_to_content_hash.get(
                    r["parent_uid"], r["parent_uid"]
                )
                r["child_content_hash"] = claim_uid_to_content_hash.get(
                    r["child_uid"], r["child_uid"]
                )
        for batch in _batched(rows, BATCH_SIZE):
            if dedupe_evidence_by_content_hash:
                session.run(
                    """
                    UNWIND $rows AS row
                    MATCH (parent:Claim {uid: row.parent_content_hash})
                    MATCH (child:Claim {uid: row.child_content_hash})
                    MERGE (parent)-[r:DECOMPOSES_TO]->(child)
                    ON CREATE SET r.source_event_id = row.source_event_id
                    """,
                    rows=batch,
                )
            else:
                session.run(
                    """
                    UNWIND $rows AS row
                    MATCH (parent:Claim {uid: row.parent_uid})
                    MATCH (child:Claim {uid: row.child_uid})
                    MERGE (parent)-[r:DECOMPOSES_TO]->(child)
                    ON CREATE SET r.source_event_id = row.source_event_id
                    """,
                    rows=batch,
                )

        # CONTAINS (Investigation -> Claim). When dedupe: CONTAINS_CLAIM with claim_uid on rel
        if dedupe_evidence_by_content_hash:
            rows = _fetch_rows(
                conn,
                "SELECT investigation_uid, claim_uid, claim_text FROM claim ORDER BY claim_uid",
            )
            for r in rows:
                r["claim_content_hash"] = _claim_content_hash(r.get("claim_text"))
            for batch in _batched(rows, BATCH_SIZE):
                session.run(
                    """
                    UNWIND $rows AS row
                    MATCH (i:Investigation {uid: row.investigation_uid})
                    MATCH (c:Claim {uid: row.claim_content_hash})
                    MERGE (i)-[r:CONTAINS_CLAIM]->(c)
                    ON CREATE SET r.claim_uid = row.claim_uid
                    """,
                    rows=batch,
                )
        else:
            rows = _fetch_rows(
                conn,
                "SELECT investigation_uid, claim_uid FROM claim ORDER BY claim_uid",
            )
            for batch in _batched(rows, BATCH_SIZE):
                session.run(
                    """
                    UNWIND $rows AS row
                    MATCH (i:Investigation {uid: row.investigation_uid})
                    MATCH (c:Claim {uid: row.claim_uid})
                    MERGE (i)-[r:CONTAINS]->(c)
                    ON CREATE SET r.source_event_id = ''
                    """,
                    rows=batch,
                )

        # PROVIDED_BY (when dedupe: match EvidenceItem by content_hash)
        if dedupe_evidence_by_content_hash:
            rows = _fetch_rows(
                conn,
                """SELECT esl.evidence_uid, esl.source_uid, coalesce(esl.relationship,'') AS relationship,
                          esl.source_event_id, ei.content_hash
                   FROM evidence_source_link esl
                   JOIN evidence_item ei ON esl.evidence_uid = ei.evidence_uid
                   ORDER BY esl.evidence_uid, esl.source_uid""",
            )
            for batch in _batched(rows, BATCH_SIZE):
                session.run(
                    """
                    UNWIND $rows AS row
                    MATCH (e:EvidenceItem {uid: row.content_hash})
                    MATCH (s:Source {uid: row.source_uid})
                    MERGE (e)-[r:PROVIDED_BY]->(s)
                    ON CREATE SET
                      r.source_event_id = row.source_event_id,
                      r.relationship = CASE WHEN row.relationship <> '' THEN row.relationship END
                    """,
                    rows=batch,
                )
        else:
            rows = _fetch_rows(
                conn,
                "SELECT evidence_uid, source_uid, coalesce(relationship,'') AS relationship, source_event_id FROM evidence_source_link ORDER BY evidence_uid, source_uid",
            )
            for batch in _batched(rows, BATCH_SIZE):
                session.run(
                    """
                    UNWIND $rows AS row
                    MATCH (e:EvidenceItem {uid: row.evidence_uid})
                    MATCH (s:Source {uid: row.source_uid})
                    MERGE (e)-[r:PROVIDED_BY]->(s)
                    ON CREATE SET
                      r.source_event_id = row.source_event_id,
                      r.relationship = CASE WHEN row.relationship <> '' THEN row.relationship END
                    """,
                    rows=batch,
                )


def _sync_retractions(conn: sqlite3.Connection, driver: Any) -> None:
    rows = _fetch_rows(
        conn,
        """SELECT link_uid, retracted_at, coalesce(rationale, '') AS rationale
           FROM evidence_link_retraction
           ORDER BY link_uid""",
    )
    if not rows:
        return
    with driver.session() as session:
        for batch in _batched(rows, BATCH_SIZE):
            session.run(
                """
                UNWIND $rows AS row
                MATCH (s:EvidenceSpan)-[r:SUPPORTS|CHALLENGES]->(c:Claim)
                WHERE r.link_uid = row.link_uid
                SET r.retracted_at = datetime(row.retracted_at),
                    r.retracted_reason = CASE WHEN row.rationale IS NOT NULL AND trim(row.rationale) <> '' THEN row.rationale END
                """,
                rows=batch,
            )


def sync_project_to_neo4j(
    project_dir: Path | str,
    uri: str,
    user: str,
    password: str,
    *,
    dedupe_evidence_by_content_hash: bool | None = None,
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

    from neo4j import GraphDatabase  # type: ignore[attr-defined]

    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        driver.verify_connectivity()
    except Exception as e:
        driver.close()
        raise ConnectionError(f"Cannot connect to Neo4j at {uri}: {e}") from e

    try:
        conn = sqlite3.connect(str(db_path))
        try:
            _run_schema(driver)
            _sync_nodes(
                conn, driver, dedupe_evidence_by_content_hash=dedupe_evidence_by_content_hash
            )
            _sync_relationships(
                conn, driver, dedupe_evidence_by_content_hash=dedupe_evidence_by_content_hash
            )
            _sync_retractions(conn, driver)
        finally:
            conn.close()
    finally:
        driver.close()
