"""Quick Postgres readiness check for Chronicle convergence work."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import quote_plus


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
    parser = argparse.ArgumentParser(
        description="Check Postgres connectivity/readiness for Chronicle"
    )
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
        "--json",
        action="store_true",
        help="Print machine-readable JSON output",
    )
    args = parser.parse_args()

    _load_env_file(Path(args.env_file))
    database_url = (args.database_url or "").strip() or _build_database_url()

    try:
        import psycopg
    except ImportError:
        detail = "psycopg not installed. Run: pip install -e '.[postgres]'"
        if args.json:
            print(json.dumps({"ok": False, "error": detail}))
        else:
            print(f"[FAIL] {detail}")
        return 2

    try:
        with psycopg.connect(database_url, connect_timeout=5) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT version(), current_database(), current_user, "
                "to_regclass('public.events') IS NOT NULL, "
                "to_regclass('public.schema_version') IS NOT NULL"
            )
            row = cur.fetchone()
    except Exception as exc:
        if args.json:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "database_url": database_url,
                        "error": str(exc),
                    }
                )
            )
        else:
            print(f"[FAIL] Could not connect to Postgres: {exc}")
            print(f"       URL: {database_url}")
        return 1

    assert row is not None
    version, database, user, has_events, has_schema_version = row
    result = {
        "ok": True,
        "database_url": database_url,
        "database": database,
        "user": user,
        "postgres_version": version,
        "has_events_table": bool(has_events),
        "has_schema_version_table": bool(has_schema_version),
    }
    if args.json:
        print(json.dumps(result))
    else:
        print("[PASS] Postgres is reachable")
        print(f"       database={database} user={user}")
        print(
            f"       has_events_table={bool(has_events)} has_schema_version_table={bool(has_schema_version)}"
        )
        if not has_events or not has_schema_version:
            print(
                "       note: run scripts/postgres_smoke.py once to initialize Chronicle event-store tables"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
