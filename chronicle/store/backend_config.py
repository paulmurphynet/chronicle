"""Event-store backend configuration and factory helpers."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus

from chronicle.core.errors import ChronicleUserError
from chronicle.store.postgres_event_store import PostgresEventStore
from chronicle.store.project import CHRONICLE_DB
from chronicle.store.protocols import EventStore
from chronicle.store.sqlite_event_store import SqliteEventStore

BACKEND_SQLITE = "sqlite"
BACKEND_POSTGRES = "postgres"


@dataclass(frozen=True)
class EventStoreConfig:
    """Resolved event-store configuration."""

    backend: str
    postgres_url: str | None = None


def _normalize_backend(value: str | None) -> str:
    raw = (value or "").strip().lower() or BACKEND_SQLITE
    if raw not in {BACKEND_SQLITE, BACKEND_POSTGRES}:
        raise ChronicleUserError(
            f"Unsupported CHRONICLE_EVENT_STORE value: {value!r}. "
            f"Supported values: {BACKEND_SQLITE}, {BACKEND_POSTGRES}."
        )
    return raw


def build_postgres_url(
    *,
    explicit_url: str | None = None,
    env: Mapping[str, str] | None = None,
) -> str:
    """Build Postgres URL from explicit URL or CHRONICLE_POSTGRES_* environment vars."""
    if explicit_url is not None and explicit_url.strip():
        return explicit_url.strip()
    env_source: Mapping[str, str] = env if env is not None else os.environ
    env_url = (env_source.get("CHRONICLE_POSTGRES_URL") or "").strip()
    if env_url:
        return env_url
    host = (env_source.get("CHRONICLE_POSTGRES_HOST") or "127.0.0.1").strip()
    port = (env_source.get("CHRONICLE_POSTGRES_PORT") or "5432").strip()
    db = (env_source.get("CHRONICLE_POSTGRES_DB") or "chronicle").strip()
    user = quote_plus((env_source.get("CHRONICLE_POSTGRES_USER") or "chronicle").strip())
    password = quote_plus(
        (env_source.get("CHRONICLE_POSTGRES_PASSWORD") or "chronicle_dev_password").strip()
    )
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def resolve_event_store_config(
    *,
    backend: str | None = None,
    postgres_url: str | None = None,
) -> EventStoreConfig:
    """Resolve event-store backend from explicit args or environment."""
    selected = _normalize_backend(backend or os.environ.get("CHRONICLE_EVENT_STORE"))
    if selected == BACKEND_POSTGRES:
        return EventStoreConfig(
            backend=selected, postgres_url=build_postgres_url(explicit_url=postgres_url)
        )
    return EventStoreConfig(backend=BACKEND_SQLITE, postgres_url=None)


def create_event_store(
    project_dir: Path,
    config: EventStoreConfig,
    *,
    run_projection: bool = True,
) -> EventStore:
    """Instantiate event-store implementation for the resolved backend."""
    if config.backend == BACKEND_POSTGRES:
        if not config.postgres_url:
            raise ChronicleUserError(
                "CHRONICLE_POSTGRES_URL is required when CHRONICLE_EVENT_STORE=postgres."
            )
        return PostgresEventStore(config.postgres_url, run_projection=run_projection)
    return SqliteEventStore(project_dir / CHRONICLE_DB, run_projection=run_projection)
