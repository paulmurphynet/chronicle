"""Minimal smoke test for Chronicle Postgres event-store support."""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote_plus

from chronicle.core.events import EVENT_INVESTIGATION_CREATED, Event
from chronicle.store.postgres_event_store import PostgresEventStore


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


def _build_database_url() -> str:
    explicit = (os.environ.get("CHRONICLE_POSTGRES_URL") or "").strip()
    if explicit:
        return explicit
    host = (os.environ.get("CHRONICLE_POSTGRES_HOST") or "127.0.0.1").strip()
    port = (os.environ.get("CHRONICLE_POSTGRES_PORT") or "5432").strip()
    db = (os.environ.get("CHRONICLE_POSTGRES_DB") or "chronicle").strip()
    user = quote_plus((os.environ.get("CHRONICLE_POSTGRES_USER") or "chronicle").strip())
    password = quote_plus(
        (os.environ.get("CHRONICLE_POSTGRES_PASSWORD") or "chronicle_dev_password").strip()
    )
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Postgres event-store smoke test")
    parser.add_argument(
        "--env-file",
        default=".env.postgres.local",
        help="Optional env file to load before checks (default: .env.postgres.local)",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Override connection URL (default: CHRONICLE_POSTGRES_URL or env-derived URL)",
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Keep the inserted smoke event in DB for debugging",
    )
    args = parser.parse_args()

    _load_env_file(Path(args.env_file))
    database_url = (args.database_url or "").strip() or _build_database_url()

    try:
        import psycopg  # noqa: F401
    except ImportError:
        print("[FAIL] psycopg not installed. Run: pip install -e '.[postgres]'")
        return 2

    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    event_id = f"evt_smoke_{uuid.uuid4().hex}"
    inv_uid = f"inv_smoke_{uuid.uuid4().hex}"
    subject_uid = inv_uid
    idempotency_key = f"idem_smoke_{uuid.uuid4().hex}"

    event = Event(
        event_id=event_id,
        event_type=EVENT_INVESTIGATION_CREATED,
        occurred_at=now,
        recorded_at=now,
        investigation_uid=inv_uid,
        subject_uid=subject_uid,
        actor_type="tool",
        actor_id="postgres-smoke",
        workspace="spark",
        payload={"title": "Postgres smoke investigation"},
        idempotency_key=idempotency_key,
    )

    cleanup = not args.no_cleanup
    store: PostgresEventStore | None = None
    try:
        store = PostgresEventStore(database_url)
        store.append(event)
        by_inv = store.read_by_investigation(inv_uid, limit=10)
        if not any(e.event_id == event_id for e in by_inv):
            print("[FAIL] Inserted event was not returned by read_by_investigation")
            return 1
        by_key = store.get_event_by_idempotency_key(idempotency_key)
        if by_key is None or by_key.event_id != event_id:
            print("[FAIL] Inserted event was not returned by get_event_by_idempotency_key")
            return 1
        print("[PASS] Postgres event-store smoke test passed")
        print(f"       database_url={database_url}")
        print(f"       event_id={event_id} investigation_uid={inv_uid}")
        return 0
    except Exception as exc:
        print(f"[FAIL] Postgres smoke test failed: {exc}")
        print(f"       database_url={database_url}")
        return 1
    finally:
        if cleanup and store is not None:
            try:
                conn = store._connection()
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM events WHERE event_id = %s", (event_id,))
                conn.commit()
            except Exception:
                pass
        if store is not None:
            store.close()


if __name__ == "__main__":
    sys.exit(main())
