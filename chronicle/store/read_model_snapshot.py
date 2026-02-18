"""Read-model snapshot at event N for scale: create snapshot, restore from snapshot + tail replay.

For very large projects, create a snapshot of the read model at event N; recovery or catch-up
is then "restore snapshot and replay tail events" instead of full replay from zero.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from chronicle.core.events import Event
from chronicle.store.project import CHRONICLE_DB
from chronicle.store.read_model import apply_event
from chronicle.store.schema import (
    READ_MODEL_TABLES_TRUNCATE_ORDER,
    run_read_model_ddl_only,
    truncate_read_model_tables,
)


SNAPSHOT_META_DDL = """
CREATE TABLE IF NOT EXISTS snapshot_meta (
  as_of_event_id    TEXT PRIMARY KEY,
  as_of_event_rowid INTEGER NOT NULL,
  recorded_at       TEXT NOT NULL
);
"""

# Copy order: parent tables before child (reverse of truncate order).
_INSERT_ORDER = list(reversed(READ_MODEL_TABLES_TRUNCATE_ORDER))

_EVENT_COLUMNS = (
    "event_id, event_type, occurred_at, recorded_at, investigation_uid, subject_uid, "
    "actor_type, actor_id, workspace, policy_profile_id, correlation_id, causation_id, "
    "envelope_version, payload_version, payload, idempotency_key, prev_event_hash, event_hash"
)


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


def create_read_model_snapshot(
    project_dir: Path | str,
    at_event_id: str,
    output_path: Path | str,
) -> int:
    """Create a snapshot of the read model as of event at_event_id in a separate SQLite file.

    Reads events from the project DB up to and including at_event_id, replays them into
    output_path, and writes snapshot_meta (as_of_event_id, as_of_event_rowid, recorded_at).
    The project DB is only read; it is not modified.

    Returns the number of events replayed into the snapshot.
    """
    project_dir = Path(project_dir)
    output_path = Path(output_path)
    db_path = project_dir / CHRONICLE_DB
    if not db_path.is_file():
        raise FileNotFoundError(f"Not a Chronicle project (no {CHRONICLE_DB}): {project_dir}")

    main_conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        row = main_conn.execute(
            "SELECT rowid, recorded_at FROM events WHERE event_id = ?", (at_event_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"Event not found: {at_event_id!r}")
        target_rowid, recorded_at = row[0], row[1]

        output_path.parent.mkdir(parents=True, exist_ok=True)
        snap_conn = sqlite3.connect(str(output_path))
        try:
            run_read_model_ddl_only(snap_conn)
            snap_conn.executescript(SNAPSHOT_META_DDL)
            query = f"SELECT {_EVENT_COLUMNS} FROM events ORDER BY rowid ASC"
            cur = main_conn.execute(query)
            applied = 0
            for row in cur.fetchall():
                event = _row_to_event(row)
                apply_event(snap_conn, event)
                applied += 1
                if event.event_id == at_event_id:
                    break
            snap_conn.execute(
                "INSERT OR REPLACE INTO snapshot_meta (as_of_event_id, as_of_event_rowid, recorded_at) VALUES (?, ?, ?)",
                (at_event_id, target_rowid, recorded_at),
            )
            snap_conn.commit()
            return applied
        finally:
            snap_conn.close()
    finally:
        main_conn.close()


def restore_from_snapshot(
    project_dir: Path | str,
    snapshot_path: Path | str,
) -> int:
    """Restore the project read model from a snapshot file, then replay tail events.

    Truncates the project read model, copies all read model tables from the snapshot DB
    into the project DB, then replays events with rowid > snapshot's as_of_event_rowid.
    Returns the number of tail events applied.
    """
    project_dir = Path(project_dir)
    snapshot_path = Path(snapshot_path)
    if not snapshot_path.is_file():
        raise FileNotFoundError(f"Snapshot file not found: {snapshot_path}")
    db_path = project_dir / CHRONICLE_DB
    if not db_path.is_file():
        raise FileNotFoundError(f"Not a Chronicle project (no {CHRONICLE_DB}): {project_dir}")

    main_conn = sqlite3.connect(str(db_path))
    try:
        snap_conn = sqlite3.connect(f"file:{snapshot_path}?mode=ro", uri=True)
        try:
            row = snap_conn.execute(
                "SELECT as_of_event_id, as_of_event_rowid, recorded_at FROM snapshot_meta LIMIT 1"
            ).fetchone()
            if row is None:
                raise ValueError("Snapshot has no snapshot_meta row")
            as_of_event_id, as_of_event_rowid, _ = row
        finally:
            snap_conn.close()

        truncate_read_model_tables(main_conn)
        main_conn.execute("ATTACH DATABASE ? AS snap", (str(snapshot_path),))
        try:
            for table in _INSERT_ORDER:
                try:
                    main_conn.execute(f"INSERT INTO {table} SELECT * FROM snap.{table}")
                except sqlite3.OperationalError:
                    pass
            main_conn.commit()
        finally:
            main_conn.execute("DETACH DATABASE snap")

        # Replay tail: events with rowid > as_of_event_rowid
        query = f"SELECT rowid, {_EVENT_COLUMNS} FROM events WHERE rowid > ? ORDER BY rowid ASC"
        cur = main_conn.execute(query, (as_of_event_rowid,))
        tail_count = 0
        for row in cur.fetchall():
            rowid, *event_row = row
            event = _row_to_event(tuple(event_row))
            apply_event(main_conn, event)
            tail_count += 1
        main_conn.commit()
        return tail_count
    finally:
        main_conn.close()
