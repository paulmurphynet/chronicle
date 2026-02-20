"""PostgreSQL implementation of EventStore. Optional; requires pip install -e '.[postgres]'. See POSTGRES.md."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from chronicle.core.events import Event

if TYPE_CHECKING:
    from collections.abc import Sequence

try:
    import psycopg
except ImportError:
    psycopg = None  # type: ignore[assignment]

from chronicle.store.postgres_projection import (
    apply_event_to_postgres_read_model,
    init_postgres_read_model_schema,
)
from chronicle.store.schema import EVENT_STORE_VERSION

EVENTS_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS events (
    event_id            TEXT PRIMARY KEY,
    event_type          TEXT NOT NULL,
    occurred_at         TEXT NOT NULL,
    recorded_at         TEXT NOT NULL,
    investigation_uid   TEXT NOT NULL,
    subject_uid         TEXT NOT NULL,
    actor_type          TEXT NOT NULL,
    actor_id            TEXT NOT NULL,
    workspace           TEXT NOT NULL,
    policy_profile_id   TEXT,
    correlation_id      TEXT,
    causation_id        TEXT,
    envelope_version    INTEGER NOT NULL DEFAULT 1,
    payload_version     INTEGER NOT NULL DEFAULT 1,
    payload             TEXT NOT NULL,
    idempotency_key     TEXT,
    prev_event_hash     TEXT,
    event_hash          TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_recorded_at ON events (recorded_at);
CREATE INDEX IF NOT EXISTS idx_events_occurred_at ON events (occurred_at);
CREATE INDEX IF NOT EXISTS idx_events_investigation ON events (investigation_uid);
CREATE INDEX IF NOT EXISTS idx_events_subject_uid ON events (subject_uid);
CREATE INDEX IF NOT EXISTS idx_events_type_time ON events (event_type, recorded_at);
CREATE INDEX IF NOT EXISTS idx_events_correlation ON events (correlation_id);
CREATE INDEX IF NOT EXISTS idx_events_investigation_type ON events (investigation_uid, event_type);
CREATE INDEX IF NOT EXISTS idx_events_idempotency_key ON events (idempotency_key) WHERE idempotency_key IS NOT NULL;
"""

SCHEMA_VERSION_DDL = """
CREATE TABLE IF NOT EXISTS schema_version (
    component   TEXT PRIMARY KEY,
    version     INTEGER NOT NULL,
    updated_at  TEXT NOT NULL,
    notes       TEXT
);
"""


def _row_to_event(row: tuple) -> Event:
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


class PostgresEventStore:
    """EventStore backed by PostgreSQL. Requires psycopg. Can project to Postgres read-model tables."""

    def __init__(self, database_url: str, run_projection: bool = True) -> None:
        if psycopg is None:
            raise ImportError("PostgreSQL support requires pip install -e '.[postgres]' (psycopg)")
        self._url = database_url
        self._conn: psycopg.Connection | None = None
        self._run_projection = run_projection

    def _connection(self) -> psycopg.Connection:
        if self._conn is None or self._conn.closed:
            self._conn = psycopg.connect(self._url)
            with self._conn.cursor() as cur:
                cur.execute(EVENTS_TABLE_DDL)
                cur.execute(SCHEMA_VERSION_DDL)
                now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
                cur.execute(
                    """
                    INSERT INTO schema_version (component, version, updated_at, notes)
                    VALUES ('event_store', %s, %s, 'PostgreSQL event store')
                    ON CONFLICT (component) DO NOTHING
                    """,
                    (EVENT_STORE_VERSION, now),
                )
            self._conn.commit()
            if self._run_projection:
                init_postgres_read_model_schema(self._conn)
        return self._conn

    def append(self, event: Event) -> None:
        from chronicle.core.errors import ChronicleIdempotencyCapacityError
        from chronicle.core.validation import MAX_IDEMPOTENCY_KEY_EVENTS

        row = event.to_row()
        row["payload"] = json.dumps(row["payload"])
        conn = self._connection()
        if row.get("idempotency_key") and MAX_IDEMPOTENCY_KEY_EVENTS > 0:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM events WHERE idempotency_key IS NOT NULL")
                count_row = cur.fetchone()
                count = int(count_row[0]) if count_row is not None else 0
            if count >= MAX_IDEMPOTENCY_KEY_EVENTS:
                raise ChronicleIdempotencyCapacityError(
                    "Idempotency key capacity reached; increase CHRONICLE_MAX_IDEMPOTENCY_KEY_EVENTS or retry without Idempotency-Key"
                )
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO events (
                    event_id, event_type, occurred_at, recorded_at,
                    investigation_uid, subject_uid, actor_type, actor_id, workspace,
                    policy_profile_id, correlation_id, causation_id,
                    envelope_version, payload_version, payload,
                    idempotency_key, prev_event_hash, event_hash
                ) VALUES (
                    %(event_id)s, %(event_type)s, %(occurred_at)s, %(recorded_at)s,
                    %(investigation_uid)s, %(subject_uid)s, %(actor_type)s, %(actor_id)s, %(workspace)s,
                    %(policy_profile_id)s, %(correlation_id)s, %(causation_id)s,
                    %(envelope_version)s, %(payload_version)s, %(payload)s,
                    %(idempotency_key)s, %(prev_event_hash)s, %(event_hash)s
                )
                """,
                row,
            )
        if self._run_projection:
            apply_event_to_postgres_read_model(conn, event)
        conn.commit()

    def _after_clause(self, after_event_id: str) -> tuple[str, Sequence[str | None]]:
        conn = self._connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT recorded_at, event_id FROM events WHERE event_id = %s",
                (after_event_id,),
            )
            row = cur.fetchone()
        if not row:
            return "", []
        rec_at, eid = row
        return " AND ((recorded_at > %s) OR (recorded_at = %s AND event_id > %s))", [
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
        q = """
            SELECT event_id, event_type, occurred_at, recorded_at,
                   investigation_uid, subject_uid, actor_type, actor_id, workspace,
                   policy_profile_id, correlation_id, causation_id,
                   envelope_version, payload_version, payload,
                   idempotency_key, prev_event_hash, event_hash
            FROM events
        """
        params: list[str | int | None] = []
        if after_event_id is not None:
            clause, after_params = self._after_clause(after_event_id)
            q += " WHERE 1=1 " + clause
            params = list(after_params)
        q += " ORDER BY recorded_at ASC, event_id ASC"
        if limit is not None:
            q += " LIMIT %s"
            params.append(limit)
        with conn.cursor() as cur:
            cur.execute(q, params)
            rows = cur.fetchall()
        return [_row_to_event(r) for r in rows]

    def read_by_investigation(
        self,
        investigation_uid: str,
        after_event_id: str | None = None,
        limit: int | None = None,
    ) -> list[Event]:
        conn = self._connection()
        q = """
            SELECT event_id, event_type, occurred_at, recorded_at,
                   investigation_uid, subject_uid, actor_type, actor_id, workspace,
                   policy_profile_id, correlation_id, causation_id,
                   envelope_version, payload_version, payload,
                   idempotency_key, prev_event_hash, event_hash
            FROM events
            WHERE investigation_uid = %s
        """
        params: list[str | int | None] = [investigation_uid]
        if after_event_id is not None:
            clause, extra = self._after_clause(after_event_id)
            q += clause
            params.extend(extra)
        q += " ORDER BY recorded_at ASC, event_id ASC"
        if limit is not None:
            q += " LIMIT %s"
            params.append(limit)
        with conn.cursor() as cur:
            cur.execute(q, params)
            rows = cur.fetchall()
        return [_row_to_event(r) for r in rows]

    def read_by_subject(
        self,
        subject_uid: str,
        after_event_id: str | None = None,
        limit: int | None = None,
    ) -> list[Event]:
        conn = self._connection()
        q = """
            SELECT event_id, event_type, occurred_at, recorded_at,
                   investigation_uid, subject_uid, actor_type, actor_id, workspace,
                   policy_profile_id, correlation_id, causation_id,
                   envelope_version, payload_version, payload,
                   idempotency_key, prev_event_hash, event_hash
            FROM events
            WHERE subject_uid = %s
        """
        params: list[str | int | None] = [subject_uid]
        if after_event_id is not None:
            clause, extra = self._after_clause(after_event_id)
            q += clause
            params.extend(extra)
        q += " ORDER BY recorded_at ASC, event_id ASC"
        if limit is not None:
            q += " LIMIT %s"
            params.append(limit)
        with conn.cursor() as cur:
            cur.execute(q, params)
            rows = cur.fetchall()
        return [_row_to_event(r) for r in rows]

    def get_event_by_idempotency_key(self, idempotency_key: str) -> Event | None:
        """Return the first event with this idempotency_key if any; else None."""
        if not idempotency_key or not idempotency_key.strip():
            return None
        conn = self._connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT event_id, event_type, occurred_at, recorded_at,
                       investigation_uid, subject_uid, actor_type, actor_id, workspace,
                       policy_profile_id, correlation_id, causation_id,
                       envelope_version, payload_version, payload,
                       idempotency_key, prev_event_hash, event_hash
                FROM events
                WHERE idempotency_key = %s
                ORDER BY recorded_at ASC, event_id ASC
                LIMIT 1
                """,
                (idempotency_key.strip(),),
            )
            row = cur.fetchone()
        return _row_to_event(row) if row else None

    def get_read_model(self) -> None:
        """Read-model query API parity is still in progress."""
        raise NotImplementedError(
            "PostgresReadModel query API is not implemented yet. Event projection now writes read-model tables, "
            "but session/query parity is still SQLite-first. See docs/POSTGRES.md."
        )

    def close(self) -> None:
        if self._conn is not None and not self._conn.closed:
            self._conn.close()
            self._conn = None
