"""Export relational read model to CSV for Neo4j rebuild. Spec 14.6.4, 16.3, 16.8."""

import csv
import json
import sqlite3
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from chronicle.store.project import CHRONICLE_DB

FETCH_SIZE = 1000
ProgressCallback = Callable[[dict[str, object]], None]


def _write_csv(path: Path, headers: list[str], rows: list[tuple]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)


def _write_query_csv(
    conn: sqlite3.Connection,
    path: Path,
    headers: list[str],
    query: str,
    *,
    fetch_size: int = FETCH_SIZE,
    phase: str | None = None,
    progress: ProgressCallback | None = None,
) -> dict[str, int | float]:
    """Write query results to CSV in chunks to keep memory bounded."""
    path.parent.mkdir(parents=True, exist_ok=True)
    cur = conn.execute(query)
    row_count = 0
    batch_count = 0
    started = time.perf_counter()
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        while True:
            rows = cur.fetchmany(fetch_size)
            if not rows:
                break
            batch_count += 1
            row_count += len(rows)
            writer.writerows(rows)
            if progress is not None and phase is not None:
                progress(
                    {
                        "event": "batch",
                        "phase": phase,
                        "batch_index": batch_count,
                        "rows_in_batch": len(rows),
                        "rows_total": row_count,
                    }
                )
    elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
    stats: dict[str, int | float] = {
        "rows": row_count,
        "batches": batch_count,
        "elapsed_ms": elapsed_ms,
    }
    if progress is not None and phase is not None:
        progress(
            {
                "event": "phase_complete",
                "phase": phase,
                "rows": row_count,
                "batches": batch_count,
                "elapsed_ms": elapsed_ms,
            }
        )
    return stats


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _evidence_link_select_sql(conn: sqlite3.Connection) -> str:
    rationale_expr = _evidence_link_rationale_expr(conn)
    if rationale_expr == "coalesce(rationale, '') AS rationale":
        return (
            "SELECT link_uid, claim_uid, span_uid, link_type, coalesce(rationale, '') AS rationale, "
            "created_at, source_event_id FROM evidence_link ORDER BY link_uid"
        )
    if rationale_expr == "coalesce(notes, '') AS rationale":
        return (
            "SELECT link_uid, claim_uid, span_uid, link_type, coalesce(notes, '') AS rationale, "
            "created_at, source_event_id FROM evidence_link ORDER BY link_uid"
        )
    return (
        "SELECT link_uid, claim_uid, span_uid, link_type, '' AS rationale, "
        "created_at, source_event_id FROM evidence_link ORDER BY link_uid"
    )


def _evidence_link_rationale_expr(conn: sqlite3.Connection) -> str:
    columns = _table_columns(conn, "evidence_link")
    if "rationale" in columns:
        return "coalesce(rationale, '') AS rationale"
    if "notes" in columns:
        return "coalesce(notes, '') AS rationale"
    return "'' AS rationale"


def _default_progress_sink(event: dict[str, object]) -> None:
    print(json.dumps(event, sort_keys=True), file=sys.stderr)


def export_read_model_to_csv(
    conn: sqlite3.Connection,
    output_dir: Path,
    *,
    progress: ProgressCallback | None = None,
) -> dict[str, dict[str, int | float]]:
    """Export read model tables to CSV files for Neo4j LOAD CSV. Spec 16.8 (SQLite)."""
    output_dir = Path(output_dir)
    phase_stats: dict[str, dict[str, int | float]] = {}
    phase_stats["investigations"] = _write_query_csv(
        conn,
        output_dir / "investigations.csv",
        ["investigation_uid", "title", "description", "is_archived", "created_at", "updated_at"],
        "SELECT investigation_uid, title, description, is_archived, created_at, updated_at FROM investigation ORDER BY investigation_uid",
        phase="investigations",
        progress=progress,
    )

    phase_stats["claims"] = _write_query_csv(
        conn,
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
        """SELECT claim_uid, investigation_uid, claim_text, claim_type, current_status,
                  decomposition_status, coalesce(parent_claim_uid,'') AS parent_claim_uid,
                  created_at, updated_at FROM claim ORDER BY claim_uid""",
        phase="claims",
        progress=progress,
    )

    phase_stats["evidence_items"] = _write_query_csv(
        conn,
        output_dir / "evidence_items.csv",
        ["evidence_uid", "content_hash", "uri", "media_type", "created_at", "provenance_type"],
        """SELECT evidence_uid, content_hash, uri, media_type, created_at,
                  coalesce(provenance_type, '') AS provenance_type
           FROM evidence_item ORDER BY evidence_uid""",
        phase="evidence_items",
        progress=progress,
    )

    phase_stats["spans"] = _write_query_csv(
        conn,
        output_dir / "spans.csv",
        ["span_uid", "evidence_uid", "anchor_type", "anchor_json", "created_at", "source_event_id"],
        """SELECT span_uid, evidence_uid, anchor_type, anchor_json, created_at, source_event_id
           FROM evidence_span ORDER BY span_uid""",
        phase="spans",
        progress=progress,
    )

    phase_stats["actors"] = _write_query_csv(
        conn,
        output_dir / "actors.csv",
        ["actor_uid", "actor_type", "display_name"],
        "SELECT DISTINCT actor_id AS actor_uid, actor_type, actor_id AS display_name FROM events ORDER BY actor_id",
        phase="actors",
        progress=progress,
    )

    phase_stats["asserts"] = _write_query_csv(
        conn,
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
        """SELECT assertion_uid, claim_uid, actor_id AS actor_uid, asserted_at,
                  assertion_mode AS mode, confidence, source_event_id
           FROM claim_assertion ORDER BY assertion_uid""",
        phase="asserts",
        progress=progress,
    )

    phase_stats["links"] = _write_query_csv(
        conn,
        output_dir / "links.csv",
        [
            "link_uid",
            "claim_uid",
            "span_uid",
            "link_type",
            "rationale",
            "created_at",
            "source_event_id",
        ],
        _evidence_link_select_sql(conn),
        phase="links",
        progress=progress,
    )

    phase_stats["link_retractions"] = _write_query_csv(
        conn,
        output_dir / "link_retractions.csv",
        ["link_uid", "claim_uid", "span_uid", "link_type", "retracted_at", "rationale"],
        """SELECT r.link_uid, el.claim_uid, el.span_uid, el.link_type, r.retracted_at,
                  coalesce(r.rationale, '') AS rationale
           FROM evidence_link_retraction r
           JOIN evidence_link el ON el.link_uid = r.link_uid
           ORDER BY r.link_uid""",
        phase="link_retractions",
        progress=progress,
    )

    phase_stats["tensions"] = _write_query_csv(
        conn,
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
        """SELECT tension_uid, claim_a_uid, claim_b_uid,
                  coalesce(tension_kind,'') AS tension_kind, status, created_at, source_event_id
           FROM tension ORDER BY tension_uid""",
        phase="tensions",
        progress=progress,
    )

    phase_stats["supersession"] = _write_query_csv(
        conn,
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
        """SELECT supersession_uid, new_evidence_uid, prior_evidence_uid,
                  supersession_type, coalesce(reason,'') AS reason, created_at, source_event_id
           FROM evidence_supersession ORDER BY supersession_uid""",
        phase="supersession",
        progress=progress,
    )

    phase_stats["decomposition_edges"] = _write_query_csv(
        conn,
        output_dir / "decomposition_edges.csv",
        ["child_uid", "parent_uid", "source_event_id"],
        """SELECT c.claim_uid AS child_uid, c.parent_claim_uid AS parent_uid, e.event_id AS source_event_id
           FROM claim c
           JOIN events e ON e.subject_uid = c.claim_uid AND e.event_type = 'ClaimProposed'
           WHERE c.parent_claim_uid IS NOT NULL
           ORDER BY c.claim_uid""",
        phase="decomposition_edges",
        progress=progress,
    )

    phase_stats["sources"] = _write_query_csv(
        conn,
        output_dir / "sources.csv",
        ["source_uid", "investigation_uid", "display_name", "source_type", "alias", "created_at"],
        """SELECT source_uid, investigation_uid, display_name, source_type, coalesce(alias,'') AS alias, created_at
           FROM source ORDER BY source_uid""",
        phase="sources",
        progress=progress,
    )

    phase_stats["evidence_source_links"] = _write_query_csv(
        conn,
        output_dir / "evidence_source_links.csv",
        ["evidence_uid", "source_uid", "relationship", "source_event_id"],
        """SELECT evidence_uid, source_uid, coalesce(relationship,'') AS relationship, source_event_id
           FROM evidence_source_link ORDER BY evidence_uid, source_uid""",
        phase="evidence_source_links",
        progress=progress,
    )
    return phase_stats


def export_project_to_neo4j_csv(
    project_dir: Path | str,
    output_dir: Path | str,
    *,
    report_path: Path | str | None = None,
    log_progress: bool = False,
) -> Path:
    """Export a Chronicle project's read model to CSV files for Neo4j rebuild. Returns output_dir."""
    project_dir = Path(project_dir)
    output_dir = Path(output_dir)
    db_path = project_dir / CHRONICLE_DB
    if not db_path.is_file():
        raise FileNotFoundError(f"Not a Chronicle project (no {CHRONICLE_DB}): {project_dir}")
    started_at = datetime.now(UTC).isoformat()
    started_perf = time.perf_counter()
    progress = _default_progress_sink if log_progress else None
    if progress is not None:
        progress(
            {
                "event": "export_started",
                "kind": "neo4j_export_report",
                "project_dir": str(project_dir),
                "output_dir": str(output_dir),
                "started_at": started_at,
            }
        )
    phase_stats: dict[str, dict[str, int | float]]
    conn = sqlite3.connect(str(db_path))
    try:
        phase_stats = export_read_model_to_csv(conn, output_dir, progress=progress)
    finally:
        conn.close()
    elapsed_ms = round((time.perf_counter() - started_perf) * 1000.0, 3)
    completed_at = datetime.now(UTC).isoformat()
    report: dict[str, object] = {
        "kind": "neo4j_export_report",
        "status": "passed",
        "project_dir": str(project_dir),
        "output_dir": str(output_dir),
        "started_at": started_at,
        "completed_at": completed_at,
        "elapsed_ms": elapsed_ms,
        "phase_stats": phase_stats,
    }
    if report_path is not None:
        rp = Path(report_path)
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if progress is not None:
        progress({"event": "export_complete", **report})
    return output_dir
