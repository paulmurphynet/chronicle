"""Export relational read model to CSV for Neo4j rebuild. Spec 14.6.4, 16.3, 16.8."""

import csv
import sqlite3
from pathlib import Path

from chronicle.store.project import CHRONICLE_DB


def _write_csv(path: Path, headers: list[str], rows: list[tuple]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _evidence_link_rationale_expr(conn: sqlite3.Connection) -> str:
    columns = _table_columns(conn, "evidence_link")
    if "rationale" in columns:
        return "coalesce(rationale, '') AS rationale"
    if "notes" in columns:
        return "coalesce(notes, '') AS rationale"
    return "'' AS rationale"


def export_read_model_to_csv(conn: sqlite3.Connection, output_dir: Path) -> None:
    """Export read model tables to CSV files for Neo4j LOAD CSV. Spec 16.8 (SQLite)."""
    output_dir = Path(output_dir)
    cur = conn.cursor()

    cur.execute(
        "SELECT investigation_uid, title, description, is_archived, created_at, updated_at FROM investigation ORDER BY investigation_uid"
    )
    _write_csv(
        output_dir / "investigations.csv",
        ["investigation_uid", "title", "description", "is_archived", "created_at", "updated_at"],
        cur.fetchall(),
    )

    cur.execute(
        """SELECT claim_uid, investigation_uid, claim_text, claim_type, current_status,
                  decomposition_status, coalesce(parent_claim_uid,'') AS parent_claim_uid,
                  created_at, updated_at FROM claim ORDER BY claim_uid"""
    )
    _write_csv(
        output_dir / "claims.csv",
        [
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
        cur.fetchall(),
    )

    cur.execute(
        """SELECT evidence_uid, content_hash, uri, media_type, created_at,
                  coalesce(provenance_type, '') AS provenance_type
           FROM evidence_item ORDER BY evidence_uid"""
    )
    _write_csv(
        output_dir / "evidence_items.csv",
        ["evidence_uid", "content_hash", "uri", "media_type", "created_at", "provenance_type"],
        cur.fetchall(),
    )

    cur.execute(
        """SELECT span_uid, evidence_uid, anchor_type, anchor_json, created_at, source_event_id
           FROM evidence_span ORDER BY span_uid"""
    )
    _write_csv(
        output_dir / "spans.csv",
        ["span_uid", "evidence_uid", "anchor_type", "anchor_json", "created_at", "source_event_id"],
        cur.fetchall(),
    )

    cur.execute(
        "SELECT DISTINCT actor_id AS actor_uid, actor_type, actor_id AS display_name FROM events ORDER BY actor_id"
    )
    _write_csv(
        output_dir / "actors.csv",
        ["actor_uid", "actor_type", "display_name"],
        cur.fetchall(),
    )

    cur.execute(
        """SELECT assertion_uid, claim_uid, actor_id AS actor_uid, asserted_at,
                  assertion_mode AS mode, confidence, source_event_id
           FROM claim_assertion ORDER BY assertion_uid"""
    )
    _write_csv(
        output_dir / "asserts.csv",
        [
            "assertion_uid",
            "claim_uid",
            "actor_uid",
            "asserted_at",
            "mode",
            "confidence",
            "source_event_id",
        ],
        cur.fetchall(),
    )

    evidence_link_rationale_expr = _evidence_link_rationale_expr(conn)
    cur.execute(
        f"SELECT link_uid, claim_uid, span_uid, link_type, {evidence_link_rationale_expr}, "
        "created_at, source_event_id FROM evidence_link ORDER BY link_uid"
    )
    _write_csv(
        output_dir / "links.csv",
        ["link_uid", "claim_uid", "span_uid", "link_type", "rationale", "created_at", "source_event_id"],
        cur.fetchall(),
    )

    cur.execute(
        """SELECT r.link_uid, el.claim_uid, el.span_uid, el.link_type, r.retracted_at,
                  coalesce(r.rationale, '') AS rationale
           FROM evidence_link_retraction r
           JOIN evidence_link el ON el.link_uid = r.link_uid
           ORDER BY r.link_uid"""
    )
    _write_csv(
        output_dir / "link_retractions.csv",
        ["link_uid", "claim_uid", "span_uid", "link_type", "retracted_at", "rationale"],
        cur.fetchall(),
    )

    cur.execute(
        """SELECT tension_uid, claim_a_uid, claim_b_uid,
                  coalesce(tension_kind,'') AS tension_kind, status, created_at, source_event_id
           FROM tension ORDER BY tension_uid"""
    )
    _write_csv(
        output_dir / "tensions.csv",
        [
            "tension_uid",
            "claim_a_uid",
            "claim_b_uid",
            "tension_kind",
            "status",
            "created_at",
            "source_event_id",
        ],
        cur.fetchall(),
    )

    cur.execute(
        """SELECT supersession_uid, new_evidence_uid, prior_evidence_uid,
                  supersession_type, coalesce(reason,'') AS reason, created_at, source_event_id
           FROM evidence_supersession ORDER BY supersession_uid"""
    )
    _write_csv(
        output_dir / "supersession.csv",
        [
            "supersession_uid",
            "new_evidence_uid",
            "prior_evidence_uid",
            "supersession_type",
            "reason",
            "created_at",
            "source_event_id",
        ],
        cur.fetchall(),
    )

    cur.execute(
        """SELECT c.claim_uid AS child_uid, c.parent_claim_uid AS parent_uid, e.event_id AS source_event_id
           FROM claim c
           JOIN events e ON e.subject_uid = c.claim_uid AND e.event_type = 'ClaimProposed'
           WHERE c.parent_claim_uid IS NOT NULL
           ORDER BY c.claim_uid"""
    )
    _write_csv(
        output_dir / "decomposition_edges.csv",
        ["child_uid", "parent_uid", "source_event_id"],
        cur.fetchall(),
    )

    cur.execute(
        """SELECT source_uid, investigation_uid, display_name, source_type, coalesce(alias,'') AS alias, created_at
           FROM source ORDER BY source_uid"""
    )
    _write_csv(
        output_dir / "sources.csv",
        ["source_uid", "investigation_uid", "display_name", "source_type", "alias", "created_at"],
        cur.fetchall(),
    )

    cur.execute(
        """SELECT evidence_uid, source_uid, coalesce(relationship,'') AS relationship, source_event_id
           FROM evidence_source_link ORDER BY evidence_uid, source_uid"""
    )
    _write_csv(
        output_dir / "evidence_source_links.csv",
        ["evidence_uid", "source_uid", "relationship", "source_event_id"],
        cur.fetchall(),
    )


def export_project_to_neo4j_csv(project_dir: Path | str, output_dir: Path | str) -> Path:
    """Export a Chronicle project's read model to CSV files for Neo4j rebuild. Returns output_dir."""
    project_dir = Path(project_dir)
    output_dir = Path(output_dir)
    db_path = project_dir / CHRONICLE_DB
    if not db_path.is_file():
        raise FileNotFoundError(f"Not a Chronicle project (no {CHRONICLE_DB}): {project_dir}")
    conn = sqlite3.connect(str(db_path))
    try:
        export_read_model_to_csv(conn, output_dir)
    finally:
        conn.close()
    return output_dir
