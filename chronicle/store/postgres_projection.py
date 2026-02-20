"""PostgreSQL read-model schema and projection compatibility for event replay/append."""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from chronicle.core.events import Event
from chronicle.store import schema
from chronicle.store.read_model.projection import apply_event

try:
    import psycopg
except ImportError:
    psycopg = None  # type: ignore[assignment]

_INSERT_OR_IGNORE_RE = re.compile(r"^\s*INSERT\s+OR\s+IGNORE\s+INTO\s+", re.IGNORECASE)
_INSERT_OR_REPLACE_RETRACTION_RE = re.compile(
    r"^\s*INSERT\s+OR\s+REPLACE\s+INTO\s+evidence_link_retraction\b",
    re.IGNORECASE,
)
_EVENT_COLUMNS = (
    "event_id, event_type, occurred_at, recorded_at, investigation_uid, subject_uid, "
    "actor_type, actor_id, workspace, policy_profile_id, correlation_id, causation_id, "
    "envelope_version, payload_version, payload, idempotency_key, prev_event_hash, event_hash"
)
_POSTGRES_TRUNCATE_ORDER = [t for t in schema.READ_MODEL_TABLES_TRUNCATE_ORDER if t != "claim_fts"]
_POSTGRES_INSERT_ORDER = list(reversed(_POSTGRES_TRUNCATE_ORDER))
_POSTGRES_TABLES = frozenset(_POSTGRES_TRUNCATE_ORDER)
_SELECT_EVENTS_ORDERED_SQL = (
    "SELECT event_id, event_type, occurred_at, recorded_at, investigation_uid, subject_uid, "
    "actor_type, actor_id, workspace, policy_profile_id, correlation_id, causation_id, "
    "envelope_version, payload_version, payload, idempotency_key, prev_event_hash, event_hash "
    "FROM events ORDER BY recorded_at ASC, event_id ASC"
)
_SELECT_TAIL_EVENTS_SQL = (
    "SELECT event_id, event_type, occurred_at, recorded_at, investigation_uid, subject_uid, "
    "actor_type, actor_id, workspace, policy_profile_id, correlation_id, causation_id, "
    "envelope_version, payload_version, payload, idempotency_key, prev_event_hash, event_hash "
    "FROM events WHERE (recorded_at > %s) OR (recorded_at = %s AND event_id > %s) "
    "ORDER BY recorded_at ASC, event_id ASC"
)
_SQL_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _quote_ident(name: str, *, allowed: set[str] | frozenset[str] | None = None) -> str:
    if allowed is not None and name not in allowed:
        raise ValueError(f"Unsupported SQL identifier: {name!r}")
    if not _SQL_IDENT_RE.fullmatch(name):
        raise ValueError(f"Invalid SQL identifier: {name!r}")
    return '"' + name.replace('"', '""') + '"'


def _split_sql_statements(sql: str) -> list[str]:
    """Split a SQL script into statements using semicolons outside quotes/comments."""
    out: list[str] = []
    buf: list[str] = []
    in_single = False
    in_double = False
    in_line_comment = False
    in_block_comment = False
    i = 0
    while i < len(sql):
        ch = sql[i]
        nxt = sql[i + 1] if i + 1 < len(sql) else ""
        if in_line_comment:
            buf.append(ch)
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue
        if in_block_comment:
            buf.append(ch)
            if ch == "*" and nxt == "/":
                buf.append(nxt)
                i += 2
                in_block_comment = False
                continue
            i += 1
            continue
        if not in_single and not in_double:
            if ch == "-" and nxt == "-":
                buf.append(ch)
                buf.append(nxt)
                i += 2
                in_line_comment = True
                continue
            if ch == "/" and nxt == "*":
                buf.append(ch)
                buf.append(nxt)
                i += 2
                in_block_comment = True
                continue
        if ch == "'" and not in_double:
            in_single = not in_single
            buf.append(ch)
            i += 1
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
            buf.append(ch)
            i += 1
            continue
        if ch == ";" and not in_single and not in_double:
            stmt = "".join(buf).strip()
            if stmt:
                out.append(stmt)
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    tail = "".join(buf).strip()
    if tail:
        out.append(tail)
    return out


def _convert_qmark_to_pyformat(sql: str) -> str:
    """Convert SQLite qmark placeholders to PostgreSQL pyformat placeholders."""
    out: list[str] = []
    in_single = False
    in_double = False
    in_line_comment = False
    in_block_comment = False
    i = 0
    while i < len(sql):
        ch = sql[i]
        nxt = sql[i + 1] if i + 1 < len(sql) else ""
        if in_line_comment:
            out.append(ch)
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue
        if in_block_comment:
            out.append(ch)
            if ch == "*" and nxt == "/":
                out.append(nxt)
                i += 2
                in_block_comment = False
                continue
            i += 1
            continue
        if not in_single and not in_double:
            if ch == "-" and nxt == "-":
                out.append(ch)
                out.append(nxt)
                i += 2
                in_line_comment = True
                continue
            if ch == "/" and nxt == "*":
                out.append(ch)
                out.append(nxt)
                i += 2
                in_block_comment = True
                continue
        if ch == "'" and not in_double:
            in_single = not in_single
            out.append(ch)
            i += 1
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
            out.append(ch)
            i += 1
            continue
        if ch == "?" and not in_single and not in_double:
            out.append("%s")
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _append_on_conflict_do_nothing(sql: str) -> str:
    stripped = sql.rstrip()
    if stripped.endswith(";"):
        stripped = stripped[:-1].rstrip()
    return f"{stripped} ON CONFLICT DO NOTHING"


def translate_sqlite_to_postgres_sql(sql_text: str) -> str:
    """Translate SQLite-leaning projection SQL to PostgreSQL-safe SQL."""
    sql = sql_text.strip()
    if not sql:
        return sql
    sql = sql.replace("date('now')", "CURRENT_DATE").replace('date("now")', "CURRENT_DATE")

    if _INSERT_OR_REPLACE_RETRACTION_RE.match(sql):
        sql = _INSERT_OR_REPLACE_RETRACTION_RE.sub(
            "INSERT INTO evidence_link_retraction ",
            sql,
            count=1,
        )
        sql = _append_on_conflict_do_nothing(sql)
        sql = (
            sql[: -len(" ON CONFLICT DO NOTHING")]
            + " ON CONFLICT (link_uid) DO UPDATE SET "  # nosec B608
            + "retracted_at = EXCLUDED.retracted_at, rationale = EXCLUDED.rationale"
        )

    if _INSERT_OR_IGNORE_RE.match(sql):
        sql = _INSERT_OR_IGNORE_RE.sub("INSERT INTO ", sql, count=1)
        if " ON CONFLICT " not in sql.upper():
            sql = _append_on_conflict_do_nothing(sql)

    return _convert_qmark_to_pyformat(sql)


class _CompatCursor:
    """Minimal cursor wrapper exposing sqlite-like fetch APIs."""

    def __init__(self, cursor: Any) -> None:
        self._cursor = cursor

    def fetchone(self) -> tuple[Any, ...] | None:
        row = self._cursor.fetchone()
        if row is None:
            return None
        return tuple(row)

    def fetchall(self) -> list[tuple[Any, ...]]:
        return [tuple(r) for r in self._cursor.fetchall()]


class PostgresProjectionCompatConnection:
    """Adapter exposing sqlite-like execute() for projection handlers."""

    def __init__(self, connection: Any) -> None:
        self._conn = connection

    def execute(
        self, sql_text: str, params: tuple[Any, ...] | list[Any] | None = None
    ) -> _CompatCursor:
        sql = translate_sqlite_to_postgres_sql(sql_text)
        cur = self._conn.cursor()
        if params is None:
            cur.execute(sql)
        else:
            cur.execute(sql, list(params))
        return _CompatCursor(cur)


def _normalized_read_model_ddl_blocks() -> list[str]:
    """Return schema DDL blocks normalized for PostgreSQL."""
    blocks = [
        schema.READ_MODEL_DDL,
        schema.CLAIM_DDL,
        schema.EVIDENCE_SPAN_DDL,
        schema.EVIDENCE_LINK_DDL,
        schema.EVIDENCE_LINK_RETRACTION_DDL,
        schema.CLAIM_ASSERTION_DDL,
        schema.TENSION_DDL,
        schema.TENSION_SUGGESTION_DDL,
        schema.CLAIM_DECOMPOSITION_DDL,
        schema.EVIDENCE_SUPERSESSION_DDL,
        schema.SOURCE_DDL,
        schema.EVIDENCE_SOURCE_LINK_DDL,
        schema.EVIDENCE_TRUST_ASSESSMENT_DDL,
        schema.ARTIFACT_DDL,
        schema.CHECKPOINT_DDL,
        schema.CHECKPOINT_ARTIFACT_FREEZE_DDL,
        schema.SUGGESTION_DISMISSAL_DDL,
        schema.CLAIM_EMBEDDING_DDL.replace("BLOB", "BYTEA"),
    ]
    return blocks


def _row_to_event(row: tuple[Any, ...]) -> Event:
    payload = row[14]
    if isinstance(payload, str):
        parsed_payload: Any = json.loads(payload)
    else:
        parsed_payload = payload
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
        payload=parsed_payload,
        idempotency_key=row[15],
        prev_event_hash=row[16],
        event_hash=row[17],
    )


def init_postgres_read_model_schema(connection: Any) -> None:
    """Create Postgres read-model tables/indexes and schema_version rows."""
    cur = connection.cursor()
    for block in _normalized_read_model_ddl_blocks():
        for stmt in _split_sql_statements(block):
            cur.execute(stmt)

    # Additive columns that SQLite gets via PRAGMA-based migrations.
    cur.execute("ALTER TABLE evidence_item ADD COLUMN IF NOT EXISTS provenance_type TEXT NULL")
    cur.execute("ALTER TABLE checkpoint ADD COLUMN IF NOT EXISTS certifying_org_id TEXT NULL")
    cur.execute("ALTER TABLE checkpoint ADD COLUMN IF NOT EXISTS certified_at TEXT NULL")

    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    cur.execute(
        """
        INSERT INTO schema_version (component, version, updated_at, notes)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (component) DO UPDATE SET
          version = EXCLUDED.version,
          updated_at = EXCLUDED.updated_at,
          notes = EXCLUDED.notes
        """,
        ("read_model", schema.READ_MODEL_VERSION, now, "PostgreSQL read model"),
    )
    cur.execute(
        """
        INSERT INTO schema_version (component, version, updated_at, notes)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (component) DO UPDATE SET
          version = EXCLUDED.version,
          updated_at = EXCLUDED.updated_at,
          notes = EXCLUDED.notes
        """,
        ("project_format", schema.PROJECT_FORMAT_VERSION, now, "PostgreSQL project format"),
    )
    connection.commit()


def apply_event_to_postgres_read_model(connection: Any, event: Event) -> None:
    """Apply one Chronicle event to Postgres read-model tables via SQLite-compatible handlers."""
    compat_conn = PostgresProjectionCompatConnection(connection)
    apply_event(cast(sqlite3.Connection, compat_conn), event)


def replay_postgres_read_model(
    connection: Any,
    *,
    up_to_event_id: str | None = None,
    up_to_recorded_at: str | None = None,
    commit: bool = True,
) -> int:
    """Rebuild Postgres read model from events (optionally up to an event/time)."""
    init_postgres_read_model_schema(connection)
    cur = connection.cursor()
    for table in _POSTGRES_TRUNCATE_ORDER:
        cur.execute(f"DELETE FROM {_quote_ident(table, allowed=_POSTGRES_TABLES)}")  # nosec B608

    events_cur = connection.cursor()
    events_cur.execute(_SELECT_EVENTS_ORDERED_SQL)
    rows = events_cur.fetchall()
    applied = 0
    found_target = up_to_event_id is None
    for row in rows:
        event = _row_to_event(tuple(row))
        if up_to_recorded_at is not None and event.recorded_at > up_to_recorded_at:
            break
        apply_event_to_postgres_read_model(connection, event)
        applied += 1
        if up_to_event_id is not None and event.event_id == up_to_event_id:
            found_target = True
            break
    if up_to_event_id is not None and not found_target:
        raise ValueError(f"Event not found: {up_to_event_id!r}")
    if commit:
        connection.commit()
    return applied


def replay_postgres_read_model_from_url(
    database_url: str,
    *,
    up_to_event_id: str | None = None,
    up_to_recorded_at: str | None = None,
) -> int:
    """Connect to Postgres and rebuild read model from events."""
    if psycopg is None:
        raise ImportError("PostgreSQL support requires pip install -e '.[postgres]' (psycopg)")
    conn = psycopg.connect(database_url)
    try:
        return replay_postgres_read_model(
            conn,
            up_to_event_id=up_to_event_id,
            up_to_recorded_at=up_to_recorded_at,
            commit=True,
        )
    finally:
        conn.close()


def _dump_table_rows(connection: Any, table: str) -> list[dict[str, Any]]:
    cur = connection.cursor()
    cur.execute(f"SELECT * FROM {_quote_ident(table, allowed=_POSTGRES_TABLES)}")  # nosec B608
    names = [c.name if hasattr(c, "name") else c[0] for c in (cur.description or [])]
    return [dict(zip(names, tuple(row), strict=False)) for row in cur.fetchall()]


def create_postgres_read_model_snapshot_from_url(
    database_url: str,
    at_event_id: str,
    output_path: Path | str,
) -> int:
    """Create JSON snapshot of Postgres read-model tables as-of an event."""
    if psycopg is None:
        raise ImportError("PostgreSQL support requires pip install -e '.[postgres]' (psycopg)")
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    conn = psycopg.connect(database_url)
    try:
        init_postgres_read_model_schema(conn)
        cur = conn.cursor()
        cur.execute("SELECT recorded_at FROM events WHERE event_id = %s", (at_event_id,))
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"Event not found: {at_event_id!r}")
        (recorded_at,) = row
        try:
            applied = replay_postgres_read_model(conn, up_to_event_id=at_event_id, commit=False)
            tables = {table: _dump_table_rows(conn, table) for table in _POSTGRES_INSERT_ORDER}
            payload = {
                "snapshot_format": 1,
                "as_of_event_id": at_event_id,
                "as_of_recorded_at": recorded_at,
                "tables": tables,
            }
            output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            return applied
        finally:
            conn.rollback()
    finally:
        conn.close()


def _truncate_postgres_read_model(connection: Any) -> None:
    cur = connection.cursor()
    for table in _POSTGRES_TRUNCATE_ORDER:
        cur.execute(f"DELETE FROM {_quote_ident(table, allowed=_POSTGRES_TABLES)}")  # nosec B608


def _restore_table_rows(connection: Any, table: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    table_sql = _quote_ident(table, allowed=_POSTGRES_TABLES)
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"Snapshot rows must be objects for table {table!r}")
    columns = list(rows[0].keys())
    if not columns:
        return
    cur = connection.cursor()
    cur.execute(f"SELECT * FROM {table_sql} LIMIT 0")  # nosec B608
    allowed_columns = {c.name if hasattr(c, "name") else c[0] for c in (cur.description or [])}
    if not all(isinstance(col, str) and col in allowed_columns for col in columns):
        raise ValueError(f"Snapshot contains unsupported columns for table {table!r}")
    cols_sql = ", ".join(_quote_ident(col) for col in columns)
    placeholders = ", ".join("%s" for _ in columns)
    sql = f"INSERT INTO {table_sql} ({cols_sql}) VALUES ({placeholders})"  # nosec B608
    for row in rows:
        cur.execute(sql, [row.get(col) for col in columns])


def restore_postgres_read_model_snapshot_from_url(
    database_url: str,
    snapshot_path: Path | str,
) -> int:
    """Restore Postgres read-model tables from JSON snapshot and replay tail events."""
    if psycopg is None:
        raise ImportError("PostgreSQL support requires pip install -e '.[postgres]' (psycopg)")
    path = Path(snapshot_path)
    if not path.is_file():
        raise FileNotFoundError(f"Snapshot file not found: {path}")
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(snapshot, dict):
        raise ValueError("Invalid snapshot format")
    as_of_event_id = snapshot.get("as_of_event_id")
    as_of_recorded_at = snapshot.get("as_of_recorded_at")
    tables = snapshot.get("tables")
    if not as_of_event_id or not as_of_recorded_at or not isinstance(tables, dict):
        raise ValueError("Snapshot missing required fields")

    conn = psycopg.connect(database_url)
    try:
        init_postgres_read_model_schema(conn)
        _truncate_postgres_read_model(conn)
        for table in _POSTGRES_INSERT_ORDER:
            raw_rows = tables.get(table) or []
            if not isinstance(raw_rows, list):
                raise ValueError(f"Snapshot table payload invalid for {table}")
            _restore_table_rows(conn, table, raw_rows)

        cur = conn.cursor()
        cur.execute(_SELECT_TAIL_EVENTS_SQL, (as_of_recorded_at, as_of_recorded_at, as_of_event_id))
        tail_count = 0
        for row in cur.fetchall():
            apply_event_to_postgres_read_model(conn, _row_to_event(tuple(row)))
            tail_count += 1
        conn.commit()
        return tail_count
    finally:
        conn.close()
