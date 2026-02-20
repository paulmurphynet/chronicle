"""Tests for backend config resolution and session backend entrypoint behavior."""

from __future__ import annotations

from pathlib import Path

import pytest
from chronicle.core.errors import ChronicleUserError
from chronicle.store.backend_config import (
    BACKEND_POSTGRES,
    BACKEND_SQLITE,
    resolve_event_store_config,
)
from chronicle.store.project import create_project
from chronicle.store.session import ChronicleSession


def test_resolve_event_store_config_defaults_to_sqlite(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CHRONICLE_EVENT_STORE", raising=False)
    cfg = resolve_event_store_config()
    assert cfg.backend == BACKEND_SQLITE
    assert cfg.postgres_url is None


def test_resolve_event_store_config_postgres_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHRONICLE_EVENT_STORE", "postgres")
    monkeypatch.setenv("CHRONICLE_POSTGRES_URL", "postgresql://u:p@127.0.0.1:5432/chronicle")
    cfg = resolve_event_store_config()
    assert cfg.backend == BACKEND_POSTGRES
    assert cfg.postgres_url == "postgresql://u:p@127.0.0.1:5432/chronicle"


def test_resolve_event_store_config_invalid_backend() -> None:
    with pytest.raises(ChronicleUserError, match="Unsupported CHRONICLE_EVENT_STORE value"):
        resolve_event_store_config(backend="mongo")


def test_session_postgres_backend_env_is_explicitly_guarded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    create_project(tmp_path)
    monkeypatch.setenv("CHRONICLE_EVENT_STORE", "postgres")
    monkeypatch.setenv("CHRONICLE_POSTGRES_URL", "postgresql://u:p@127.0.0.1:5432/chronicle")
    with pytest.raises(ChronicleUserError, match="CHRONICLE_EVENT_STORE=postgres"):
        ChronicleSession(tmp_path)
