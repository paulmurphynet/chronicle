"""SQLite implementation of EventStore. Spec Section 14.2.1, 12.5."""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from chronicle import log
from chronicle.core.events import Event
from chronicle.store.read_model import SqliteReadModel, apply_event
from chronicle.store.schema import (
    EVENT_STORE_VERSION,
    READ_MODEL_VERSION,
    init_event_store_schema,
    init_read_model_schema,
    run_read_model_ddl_only,
    truncate_read_model_tables,
)


def _row_to_event(row: tuple) -> Event:
    """Build Event from DB row (cursor.description order)."""
    return Event(
        event_id=row[0],
        event_type=row[1],
        occurred_at=row[2],
        recorded_at=row[3],
        investigation_uid=row[4],
        subject_uid=row[5],
        actor_type=row[6],
        actor_id=row[7],
        workspace=row[8],
        policy_profile_id=row[9],
        correlation_id=row[10],
        causation_id=row[11],
        envelope_version=row[12],
        payload_version=row[13],
        payload=json.loads(row[14]) if isinstance(row[14], str) else row[14],
        idempotency_key=row[15],
        prev_event_hash=row[16],
        event_hash=row[17],
    )


def _maybe_run_event_store_migrations(conn: sqlite3.Connection) -> None:
    """If event_store version is behind, run additive migrations. Spec 12.5."""
    row = conn.execute(
        "SELECT version FROM schema_version WHERE component = 'event_store'"
    ).fetchone()
    if row is None:
        return
    stored = row[0]
    if stored < 2:
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_idempotency_key ON events (idempotency_key) WHERE idempotency_key IS NOT NULL"
        )
        conn.commit()
    if stored < EVENT_STORE_VERSION:
        conn.execute(
            "INSERT OR REPLACE INTO schema_version (component, version, updated_at, notes) VALUES ('event_store', ?, ?, ?)",
            (EVENT_STORE_VERSION, datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "Migrated"),
        )
        conn.commit()


def _ensure_read_model_ready(conn: sqlite3.Connection) -> None:
    """On startup: if read_model version behind, rebuild from events. Spec 12.5, 15.3."""
    row = conn.execute(
        "SELECT version FROM schema_version WHERE component = 'read_model'"
    ).fetchone()
    if row is None:
        init_read_model_schema(conn)
        return
    stored_version = row[0]
    run_read_model_ddl_only(conn)
    if stored_version < READ_MODEL_VERSION:
        log.info(
            "Rebuilding read model from events (version %s -> %s)",
            stored_version,
            READ_MODEL_VERSION,
        )
        truncate_read_model_tables(conn)
        cur = conn.execute(
            """SELECT event_id, event_type, occurred_at, recorded_at,
                      investigation_uid, subject_uid, actor_type, actor_id, workspace,
                      policy_profile_id, correlation_id, causation_id,
                      envelope_version, payload_version, payload,
                      idempotency_key, prev_event_hash, event_hash
               FROM events ORDER BY rowid ASC"""
        )
        for r in cur.fetchall():
            event = _row_to_event(r)
            apply_event(conn, event)
        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        conn.execute(
            "INSERT OR REPLACE INTO schema_version (component, version, updated_at, notes) VALUES ('read_model', ?, ?, ?)",
            (READ_MODEL_VERSION, now, "Rebuilt from events"),
        )
        conn.commit()


class SqliteEventStore:
    """EventStore backed by SQLite. When run_projection is True, append runs projection in same transaction."""

    def __init__(self, db_path: Path | str, run_projection: bool = True) -> None:
        self._path = Path(db_path)
        self._conn: sqlite3.Connection | None = None
        self._run_projection = run_projection

    def _connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode = WAL")
            self._conn.execute("PRAGMA foreign_keys = ON")
            init_event_store_schema(self._conn)
            _maybe_run_event_store_migrations(self._conn)
            if self._run_projection:
                _ensure_read_model_ready(self._conn)
        return self._conn

    def append(self, event: Event) -> None:
        from chronicle.core.errors import ChronicleIdempotencyCapacityError
        from chronicle.core.validation import MAX_IDEMPOTENCY_KEY_EVENTS

        row = event.to_row()
        row["payload"] = json.dumps(row["payload"])
        conn = self._connection()
        if row.get("idempotency_key") and MAX_IDEMPOTENCY_KEY_EVENTS > 0:
            (count,) = conn.execute(
                "SELECT COUNT(*) FROM events WHERE idempotency_key IS NOT NULL"
            ).fetchone()
            if count >= MAX_IDEMPOTENCY_KEY_EVENTS:
                raise ChronicleIdempotencyCapacityError(
                    "Idempotency key capacity reached; increase CHRONICLE_MAX_IDEMPOTENCY_KEY_EVENTS or retry without Idempotency-Key"
                )
        conn.execute(
            """
            INSERT INTO events (
                event_id, event_type, occurred_at, recorded_at,
                investigation_uid, subject_uid, actor_type, actor_id, workspace,
                policy_profile_id, correlation_id, causation_id,
                envelope_version, payload_version, payload,
                idempotency_key, prev_event_hash, event_hash
            ) VALUES (
                :event_id, :event_type, :occurred_at, :recorded_at,
                :investigation_uid, :subject_uid, :actor_type, :actor_id, :workspace,
                :policy_profile_id, :correlation_id, :causation_id,
                :envelope_version, :payload_version, :payload,
                :idempotency_key, :prev_event_hash, :event_hash
            )
            """,
            row,
        )
        if self._run_projection:
            apply_event(conn, event)
        conn.commit()

    def _after_clause(self, conn: sqlite3.Connection, after_event_id: str) -> tuple[str, list]:
        """Return (WHERE clause, params) for events after given event_id in recorded_at, event_id order."""
        row = conn.execute(
            "SELECT recorded_at, event_id FROM events WHERE event_id = ?",
            (after_event_id,),
        ).fetchone()
        if not row:
            return "", []
        rec_at, eid = row
        return " WHERE (recorded_at > ?) OR (recorded_at = ? AND event_id > ?)", [
            rec_at,
            rec_at,
            eid,
        ]

    def read_all(
        self,
        after_event_id: str | None = None,
        limit: int | None = None,
    ) -> list[Event]:
        conn = self._connection()
        sql = """
            SELECT event_id, event_type, occurred_at, recorded_at,
                   investigation_uid, subject_uid, actor_type, actor_id, workspace,
                   policy_profile_id, correlation_id, causation_id,
                   envelope_version, payload_version, payload,
                   idempotency_key, prev_event_hash, event_hash
            FROM events
        """
        params: list = []
        if after_event_id is not None:
            clause, params = self._after_clause(conn, after_event_id)
            sql += clause
        sql += " ORDER BY recorded_at ASC, event_id ASC"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        cur = conn.execute(sql, params)
        return [_row_to_event(r) for r in cur.fetchall()]

    def read_by_investigation(
        self,
        investigation_uid: str,
        after_event_id: str | None = None,
        limit: int | None = None,
    ) -> list[Event]:
        conn = self._connection()
        sql = """
            SELECT event_id, event_type, occurred_at, recorded_at,
                   investigation_uid, subject_uid, actor_type, actor_id, workspace,
                   policy_profile_id, correlation_id, causation_id,
                   envelope_version, payload_version, payload,
                   idempotency_key, prev_event_hash, event_hash
            FROM events
            WHERE investigation_uid = ?
        """
        params: list = [investigation_uid]
        if after_event_id is not None:
            clause, extra = self._after_clause(conn, after_event_id)
            sql += " AND " + clause.removeprefix(" WHERE ")
            params.extend(extra)
        sql += " ORDER BY recorded_at ASC, event_id ASC"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        cur = conn.execute(sql, params)
        return [_row_to_event(r) for r in cur.fetchall()]

    def read_by_subject(
        self,
        subject_uid: str,
        after_event_id: str | None = None,
        limit: int | None = None,
    ) -> list[Event]:
        conn = self._connection()
        sql = """
            SELECT event_id, event_type, occurred_at, recorded_at,
                   investigation_uid, subject_uid, actor_type, actor_id, workspace,
                   policy_profile_id, correlation_id, causation_id,
                   envelope_version, payload_version, payload,
                   idempotency_key, prev_event_hash, event_hash
            FROM events
            WHERE subject_uid = ?
        """
        params: list = [subject_uid]
        if after_event_id is not None:
            clause, extra = self._after_clause(conn, after_event_id)
            sql += " AND " + clause.removeprefix(" WHERE ")
            params.extend(extra)
        sql += " ORDER BY recorded_at ASC, event_id ASC"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        cur = conn.execute(sql, params)
        return [_row_to_event(r) for r in cur.fetchall()]

    def get_event_by_idempotency_key(self, idempotency_key: str) -> Event | None:
        """Return the first event with this idempotency_key if any; else None."""
        if not idempotency_key or not idempotency_key.strip():
            return None
        conn = self._connection()
        cur = conn.execute(
            """
            SELECT event_id, event_type, occurred_at, recorded_at,
                   investigation_uid, subject_uid, actor_type, actor_id, workspace,
                   policy_profile_id, correlation_id, causation_id,
                   envelope_version, payload_version, payload,
                   idempotency_key, prev_event_hash, event_hash
            FROM events
            WHERE idempotency_key = ?
            ORDER BY recorded_at ASC, event_id ASC
            LIMIT 1
            """,
            (idempotency_key.strip(),),
        )
        row = cur.fetchone()
        return _row_to_event(row) if row else None

    def get_read_model(self) -> SqliteReadModel:
        """Return a ReadModel using the same connection (for same-transaction reads)."""
        return SqliteReadModel(self._connection())

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
