"""Sync Chronicle read model to Neo4j via the Neo4j driver. Optional; requires [neo4j] extra.

Spec: schemas.md 14.5, neo4j-pipeline.md 16. Order: schema, nodes, relationships, retractions.
Idempotent (MERGE). Full rebuild from read model; retractions applied per Phase 2.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from chronicle.store.project import CHRONICLE_DB

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
    "CREATE INDEX tension_status_idx IF NOT EXISTS FOR (t:Tension) ON (t.status)",
]


def _fetch_rows(conn: sqlite3.Connection, query: str) -> list[dict[str, Any]]:
    cur = conn.execute(query)
    columns = [d[0] for d in cur.description]
    return [
        {c: (None if v is None else str(v)) for c, v in zip(columns, row, strict=True)}
        for row in cur.fetchall()
    ]


def _batched(rows: list[dict[str, Any]], size: int):
    for i in range(0, len(rows), size):
        yield rows[i : i + size]


def _run_schema(driver: Any) -> None:
    with driver.session() as session:
        for stmt in _SCHEMA_STATEMENTS:
            session.run(stmt)


def _sync_nodes(conn: sqlite3.Connection, driver: Any) -> None:
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

        # Claims
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

        # EvidenceItem (E2.3: provenance_type for human_created | ai_generated | unknown)
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


def _sync_relationships(conn: sqlite3.Connection, driver: Any) -> None:
    with driver.session() as session:
        # Span IN EvidenceItem
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
            "SELECT span_uid, claim_uid, link_uid, source_event_id, rationale FROM evidence_link WHERE link_type = 'SUPPORTS' ORDER BY link_uid",
        )
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
            "SELECT span_uid, claim_uid, link_uid, source_event_id, rationale FROM evidence_link WHERE link_type = 'CHALLENGES' ORDER BY link_uid",
        )
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
        for batch in _batched(rows, BATCH_SIZE):
            session.run(
                """
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
                rows=batch,
            )

        # Tension BETWEEN (two edges per row)
        rows = _fetch_rows(
            conn,
            "SELECT tension_uid, claim_a_uid, claim_b_uid, source_event_id FROM tension ORDER BY tension_uid",
        )
        for batch in _batched(rows, BATCH_SIZE):
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

        # SUPERSEDES
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

        # DECOMPOSES_TO
        rows = _fetch_rows(
            conn,
            """SELECT c.claim_uid AS child_uid, c.parent_claim_uid AS parent_uid, e.event_id AS source_event_id
               FROM claim c
               JOIN events e ON e.subject_uid = c.claim_uid AND e.event_type = 'ClaimProposed'
               WHERE c.parent_claim_uid IS NOT NULL ORDER BY c.claim_uid""",
        )
        for batch in _batched(rows, BATCH_SIZE):
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

        # CONTAINS (Investigation -> Claim)
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

        # PROVIDED_BY
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
        """SELECT r.link_uid, el.claim_uid, el.span_uid, el.link_type, r.retracted_at,
                  coalesce(r.rationale, '') AS rationale
           FROM evidence_link_retraction r
           JOIN evidence_link el ON el.link_uid = r.link_uid
           ORDER BY r.link_uid""",
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
) -> None:
    """Sync a Chronicle project read model to Neo4j. Idempotent (MERGE). Full rebuild; retractions applied."""
    project_dir = Path(project_dir)
    db_path = project_dir / CHRONICLE_DB
    if not db_path.is_file():
        raise FileNotFoundError(f"Not a Chronicle project (no {CHRONICLE_DB}): {project_dir}")

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
            _sync_nodes(conn, driver)
            _sync_relationships(conn, driver)
            _sync_retractions(conn, driver)
        finally:
            conn.close()
    finally:
        driver.close()
