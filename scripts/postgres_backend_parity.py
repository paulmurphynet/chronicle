"""Backend parity gate: compare defensibility outputs between SQLite and Postgres.

This script builds a deterministic scenario in a temporary SQLite Chronicle project,
replays the same event stream into Postgres, then computes defensibility scorecards
for the same claim UIDs on both backends and compares canonicalized outputs.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sqlite3
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from chronicle.store.backend_config import build_postgres_url
from chronicle.store.commands.claims import get_defensibility_score
from chronicle.store.postgres_event_store import PostgresEventStore
from chronicle.store.project import CHRONICLE_DB, create_project
from chronicle.store.read_model.sqlite_read_model import SqliteReadModel
from chronicle.store.schema import init_event_store_schema, run_read_model_ddl_only
from chronicle.store.session import ChronicleSession
from chronicle.store.sqlite_event_store import _row_to_event

EVENT_COLUMNS = (
    "event_id, event_type, occurred_at, recorded_at, investigation_uid, subject_uid, "
    "actor_type, actor_id, workspace, policy_profile_id, correlation_id, causation_id, "
    "envelope_version, payload_version, payload, idempotency_key, prev_event_hash, event_hash"
)

READ_MODEL_TABLES_FOR_SCORECARD = (
    "investigation",
    "tier_history",
    "claim",
    "evidence_item",
    "source",
    "evidence_span",
    "evidence_link",
    "evidence_link_retraction",
    "evidence_source_link",
    "tension",
)


def _load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _resolve_database_url(explicit: str | None) -> str:
    if explicit and explicit.strip():
        return explicit.strip()
    return build_postgres_url()


def _redact_database_url(database_url: str) -> str:
    if "@" not in database_url or "://" not in database_url:
        return database_url
    scheme, rest = database_url.split("://", 1)
    if "@" not in rest:
        return database_url
    creds, host = rest.split("@", 1)
    if ":" not in creds:
        return f"{scheme}://***@{host}"
    user = creds.split(":", 1)[0]
    return f"{scheme}://{user}:***@{host}"


def _build_sqlite_scenario(project_dir: Path) -> dict[str, Any]:
    create_project(project_dir)
    with ChronicleSession(project_dir, event_store_backend="sqlite") as session:
        _, investigation_uid = session.create_investigation(
            "Backend parity deterministic scenario",
            actor_id="parity_human",
            actor_type="human",
        )
        _, source_a = session.register_source(
            investigation_uid,
            "Filing source A",
            "document",
            independence_notes="Independent corporate filing",
            actor_id="parity_human",
            actor_type="human",
        )
        _, source_b = session.register_source(
            investigation_uid,
            "Audit source B",
            "document",
            independence_notes="Independent auditor memo",
            actor_id="parity_human",
            actor_type="human",
        )

        _, evidence_a = session.ingest_evidence(
            investigation_uid,
            b"Revenue ledger indicates March recognition for INV-204.",
            "text/plain",
            original_filename="ledger_march.txt",
            actor_id="parity_human",
            actor_type="human",
        )
        _, evidence_b = session.ingest_evidence(
            investigation_uid,
            b"Auditor memo corroborates March recognition controls.",
            "text/plain",
            original_filename="auditor_memo.txt",
            actor_id="parity_human",
            actor_type="human",
        )
        _, evidence_c = session.ingest_evidence(
            investigation_uid,
            b"Counterstatement claims April recognition.",
            "text/plain",
            original_filename="counter_claim.txt",
            actor_id="parity_tool",
            actor_type="tool",
        )
        session.link_evidence_to_source(
            evidence_a,
            source_a,
            relationship="provided_by",
            actor_id="parity_human",
            actor_type="human",
        )
        session.link_evidence_to_source(
            evidence_b,
            source_b,
            relationship="provided_by",
            actor_id="parity_human",
            actor_type="human",
        )
        session.link_evidence_to_source(
            evidence_c,
            source_a,
            relationship="provided_by",
            actor_id="parity_tool",
            actor_type="tool",
        )

        _, span_a = session.anchor_span(
            investigation_uid,
            evidence_a,
            "text_offset",
            {"start_char": 0, "end_char": 18},
            quote="March recognition",
            actor_id="parity_human",
            actor_type="human",
        )
        _, span_b = session.anchor_span(
            investigation_uid,
            evidence_b,
            "text_offset",
            {"start_char": 0, "end_char": 20},
            quote="corroborates March",
            actor_id="parity_human",
            actor_type="human",
        )
        _, span_c = session.anchor_span(
            investigation_uid,
            evidence_c,
            "text_offset",
            {"start_char": 0, "end_char": 12},
            quote="April claim",
            actor_id="parity_tool",
            actor_type="tool",
        )

        _, claim_primary = session.propose_claim(
            investigation_uid,
            "INV-204 revenue was recognized in March 2024.",
            initial_type="SAC",
            actor_id="parity_human",
            actor_type="human",
        )
        _, claim_counter = session.propose_claim(
            investigation_uid,
            "INV-204 revenue should be recognized in April 2024.",
            initial_type="INFERENCE",
            actor_id="parity_human",
            actor_type="human",
        )

        session.link_support(
            investigation_uid,
            span_a,
            claim_primary,
            rationale="Ledger entry supports March timing.",
            actor_id="parity_human",
            actor_type="human",
        )
        session.link_support(
            investigation_uid,
            span_b,
            claim_primary,
            rationale="Independent audit corroborates March timing.",
            actor_id="parity_human",
            actor_type="human",
        )
        session.link_challenge(
            investigation_uid,
            span_c,
            claim_primary,
            rationale="Counterstatement challenges March timing.",
            actor_id="parity_tool",
            actor_type="tool",
        )
        session.declare_tension(
            investigation_uid,
            claim_primary,
            claim_counter,
            tension_kind="contradiction",
            notes="Competing period recognition claims remain open.",
            actor_id="parity_human",
            actor_type="human",
        )
        session.verify_evidence_integrity(
            investigation_uid=investigation_uid,
            actor_id="parity_human",
            actor_type="human",
        )

        claim_uids = [claim_primary, claim_counter]
        sqlite_scores: dict[str, dict[str, Any] | None] = {}
        for claim_uid in claim_uids:
            score = session.get_defensibility_score(claim_uid)
            sqlite_scores[claim_uid] = normalize_scorecard(score)

    return {
        "investigation_uid": investigation_uid,
        "claim_uids": claim_uids,
        "sqlite_scores": sqlite_scores,
    }


def _read_events_for_investigation(project_dir: Path, investigation_uid: str) -> list[Any]:
    conn = sqlite3.connect(str(project_dir / CHRONICLE_DB))
    try:
        rows = conn.execute(
            f"SELECT {EVENT_COLUMNS} FROM events WHERE investigation_uid = ? ORDER BY rowid ASC",
            (investigation_uid,),
        ).fetchall()
        return [_row_to_event(tuple(row)) for row in rows]
    finally:
        conn.close()


def _insert_sqlite_rows(conn: sqlite3.Connection, table: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    columns = list(rows[0].keys())
    placeholders = ", ".join("?" for _ in columns)
    sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
    conn.executemany(sql, [tuple(row.get(col) for col in columns) for row in rows])


def _fetch_postgres_rows(
    pg_conn: Any, table: str, *, investigation_uid: str
) -> list[dict[str, Any]]:
    cur = pg_conn.cursor()
    if table in {"investigation", "tier_history", "claim", "evidence_item", "source", "tension"}:
        cur.execute(f"SELECT * FROM {table} WHERE investigation_uid = %s", (investigation_uid,))
    elif table == "events":
        cur.execute(
            f"SELECT {EVENT_COLUMNS} FROM events WHERE investigation_uid = %s ORDER BY recorded_at ASC, event_id ASC",
            (investigation_uid,),
        )
    elif table == "evidence_span":
        cur.execute(
            """
            SELECT es.*
            FROM evidence_span es
            JOIN evidence_item ei ON ei.evidence_uid = es.evidence_uid
            WHERE ei.investigation_uid = %s
            """,
            (investigation_uid,),
        )
    elif table == "evidence_link":
        cur.execute(
            """
            SELECT el.*
            FROM evidence_link el
            JOIN claim c ON c.claim_uid = el.claim_uid
            WHERE c.investigation_uid = %s
            """,
            (investigation_uid,),
        )
    elif table == "evidence_link_retraction":
        cur.execute(
            """
            SELECT elr.*
            FROM evidence_link_retraction elr
            JOIN evidence_link el ON el.link_uid = elr.link_uid
            JOIN claim c ON c.claim_uid = el.claim_uid
            WHERE c.investigation_uid = %s
            """,
            (investigation_uid,),
        )
    elif table == "evidence_source_link":
        cur.execute(
            """
            SELECT esl.*
            FROM evidence_source_link esl
            JOIN evidence_item ei ON ei.evidence_uid = esl.evidence_uid
            WHERE ei.investigation_uid = %s
            """,
            (investigation_uid,),
        )
    else:
        raise ValueError(f"Unsupported table for parity extraction: {table}")

    names = [c.name if hasattr(c, "name") else c[0] for c in (cur.description or [])]
    return [dict(zip(names, tuple(row), strict=False)) for row in cur.fetchall()]


def _build_sqlite_shadow_from_postgres(pg_conn: Any, investigation_uid: str) -> sqlite3.Connection:
    shadow = sqlite3.connect(":memory:")
    shadow.execute("PRAGMA foreign_keys = OFF")
    init_event_store_schema(shadow)
    run_read_model_ddl_only(shadow)

    event_rows = _fetch_postgres_rows(pg_conn, "events", investigation_uid=investigation_uid)
    _insert_sqlite_rows(shadow, "events", event_rows)

    for table in READ_MODEL_TABLES_FOR_SCORECARD:
        rows = _fetch_postgres_rows(pg_conn, table, investigation_uid=investigation_uid)
        _insert_sqlite_rows(shadow, table, rows)

    shadow.commit()
    shadow.execute("PRAGMA foreign_keys = ON")
    return shadow


def normalize_scorecard(score: Any) -> dict[str, Any] | None:
    """Canonicalize scorecard output for cross-backend equality checks."""
    if score is None:
        return None
    payload = dataclasses.asdict(score)
    contradiction = payload.get("contradiction_handling") or []
    if isinstance(contradiction, list):
        payload["contradiction_handling"] = sorted(
            contradiction,
            key=lambda row: (
                str(row.get("tension_uid", "")),
                str(row.get("other_claim_uid", "")),
            ),
        )
    risk = payload.get("risk_signals")
    if isinstance(risk, list):
        payload["risk_signals"] = sorted(str(x) for x in risk)
    return payload


def compare_scorecards(
    sqlite_scores: dict[str, dict[str, Any] | None],
    postgres_scores: dict[str, dict[str, Any] | None],
) -> dict[str, dict[str, Any]]:
    """Return claim_uid -> {sqlite, postgres} for non-matching scorecards."""
    mismatches: dict[str, dict[str, Any]] = {}
    for claim_uid in sorted(set(sqlite_scores) | set(postgres_scores)):
        sqlite_row = sqlite_scores.get(claim_uid)
        postgres_row = postgres_scores.get(claim_uid)
        if sqlite_row != postgres_row:
            mismatches[claim_uid] = {"sqlite": sqlite_row, "postgres": postgres_row}
    return mismatches


def _cleanup_scenario_events(database_url: str, investigation_uid: str) -> None:
    """Delete inserted scenario events and rebuild Postgres read model."""
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError(
            "Cleanup requested, but psycopg is unavailable. Install with: pip install -e '.[postgres]'."
        ) from exc

    from chronicle.store.postgres_projection import replay_postgres_read_model

    conn = psycopg.connect(database_url)
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM events WHERE investigation_uid = %s", (investigation_uid,))
        conn.commit()
        replay_postgres_read_model(conn, commit=True)
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare deterministic defensibility outputs between SQLite and Postgres."
    )
    parser.add_argument(
        "--env-file",
        default=".env.postgres.local",
        help="Optional env file to load before checks (default: .env.postgres.local)",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Override Postgres URL (default: CHRONICLE_POSTGRES_URL or env-derived URL)",
    )
    parser.add_argument(
        "--output",
        default="reports/postgres_backend_parity.json",
        help="Output report path (default: reports/postgres_backend_parity.json)",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Delete parity scenario events after comparison and replay Postgres read model.",
    )
    args = parser.parse_args(argv)

    _load_env_file(Path(args.env_file))
    database_url = _resolve_database_url(args.database_url)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    started_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    report: dict[str, Any] = {
        "started_at": started_at,
        "database_url": _redact_database_url(database_url),
        "ok": False,
        "mismatches": {},
    }

    try:
        with tempfile.TemporaryDirectory(prefix="chronicle_parity_") as tmp:
            tmp_path = Path(tmp)
            sqlite_project = tmp_path / "sqlite_project"
            scenario = _build_sqlite_scenario(sqlite_project)
            investigation_uid = str(scenario["investigation_uid"])
            claim_uids = [str(c) for c in scenario["claim_uids"]]
            sqlite_scores = dict(scenario["sqlite_scores"])
            events = _read_events_for_investigation(sqlite_project, investigation_uid)

            pg_store = PostgresEventStore(database_url, run_projection=True)
            try:
                for event in events:
                    pg_store.append(event)
                pg_conn = pg_store._connection()
                shadow_conn = _build_sqlite_shadow_from_postgres(pg_conn, investigation_uid)
                try:
                    postgres_read_model = SqliteReadModel(shadow_conn)
                    postgres_scores: dict[str, dict[str, Any] | None] = {}
                    for claim_uid in claim_uids:
                        score = get_defensibility_score(postgres_read_model, claim_uid)
                        postgres_scores[claim_uid] = normalize_scorecard(score)
                finally:
                    shadow_conn.close()
            finally:
                pg_store.close()

            mismatches = compare_scorecards(sqlite_scores, postgres_scores)
            report["scenario"] = {
                "investigation_uid": investigation_uid,
                "claim_uids": claim_uids,
                "event_count": len(events),
            }
            report["sqlite_scores"] = sqlite_scores
            report["postgres_scores"] = postgres_scores
            report["mismatches"] = mismatches
            report["ok"] = len(mismatches) == 0
            report["ended_at"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

            if args.cleanup:
                _cleanup_scenario_events(database_url, investigation_uid)
                report["cleanup"] = "completed"
    except ImportError as exc:
        report["error"] = str(exc)
        report["ended_at"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(
            "[FAIL] PostgreSQL support requires optional dependency psycopg. "
            "Install with: pip install -e '.[postgres]'."
        )
        return 2
    except Exception as exc:
        report["error"] = str(exc)
        report["ended_at"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"[FAIL] Backend parity check failed: {exc}")
        print(f"       report={output_path}")
        return 1

    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if report["ok"]:
        print("[PASS] Backend parity check passed (SQLite vs Postgres defensibility)")
        print(f"       claims={len(report['scenario']['claim_uids'])} events={report['scenario']['event_count']}")
        print(f"       report={output_path}")
        return 0

    print("[FAIL] Backend parity mismatch detected")
    print(f"       mismatched_claims={len(report['mismatches'])}")
    print(f"       report={output_path}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
