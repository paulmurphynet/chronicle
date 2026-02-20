"""PostgreSQL read-model schema and projection compatibility for event replay/append."""

from __future__ import annotations

import re
import sqlite3
from datetime import UTC, datetime
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
            + " ON CONFLICT (link_uid) DO UPDATE SET "
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
