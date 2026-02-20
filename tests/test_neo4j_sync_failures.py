from __future__ import annotations

import json
import sys
import types
from collections.abc import Callable
from pathlib import Path

import pytest
from chronicle.store.neo4j_sync import sync_project_to_neo4j
from chronicle.store.project import create_project

ExceptionMap = dict[str, type[Exception]]


def _install_fake_neo4j(
    monkeypatch: pytest.MonkeyPatch, verify_connectivity_impl: Callable[[ExceptionMap], None]
) -> dict[str, int]:
    state = {"verify_calls": 0, "driver_instances": 0}

    class FakeAuthError(Exception):
        pass

    class FakeConfigurationError(Exception):
        pass

    class FakeServiceUnavailableError(Exception):
        pass

    class FakeSessionExpiredError(Exception):
        pass

    class FakeTransientError(Exception):
        pass

    class FakeSession:
        def __enter__(self) -> FakeSession:
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

        def run(self, _query: str, **_kwargs: object) -> None:
            return None

    class FakeDriver:
        def verify_connectivity(self) -> None:
            state["verify_calls"] += 1
            verify_connectivity_impl(
                {
                    "auth": FakeAuthError,
                    "config": FakeConfigurationError,
                    "service_unavailable": FakeServiceUnavailableError,
                    "session_expired": FakeSessionExpiredError,
                    "transient": FakeTransientError,
                }
            )

        def session(self, **_kwargs: object) -> FakeSession:
            return FakeSession()

        def close(self) -> None:
            return None

    class FakeGraphDatabase:
        @staticmethod
        def driver(_uri: str, auth: tuple[str, str], connection_timeout: float) -> FakeDriver:
            assert isinstance(auth, tuple)
            assert connection_timeout > 0
            state["driver_instances"] += 1
            return FakeDriver()

    fake_neo4j = types.ModuleType("neo4j")
    fake_neo4j.GraphDatabase = FakeGraphDatabase
    fake_neo4j_exceptions = types.ModuleType("neo4j.exceptions")
    fake_neo4j_exceptions.AuthError = FakeAuthError
    fake_neo4j_exceptions.ConfigurationError = FakeConfigurationError
    fake_neo4j_exceptions.ServiceUnavailable = FakeServiceUnavailableError
    fake_neo4j_exceptions.SessionExpired = FakeSessionExpiredError
    fake_neo4j_exceptions.TransientError = FakeTransientError

    monkeypatch.setitem(sys.modules, "neo4j", fake_neo4j)
    monkeypatch.setitem(sys.modules, "neo4j.exceptions", fake_neo4j_exceptions)
    return state


def test_sync_auth_error_fails_without_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    create_project(tmp_path)
    report_path = tmp_path / "sync_auth_fail_report.json"

    def _raise_auth(errors: ExceptionMap) -> None:
        raise errors["auth"]("bad credentials")

    state = _install_fake_neo4j(monkeypatch, _raise_auth)

    with pytest.raises(ConnectionError, match="authentication failed"):
        sync_project_to_neo4j(
            tmp_path,
            "bolt://example:7687",
            "neo4j",
            "wrong-password",
            max_retries=4,
            retry_backoff_seconds=0.0,
            report_path=report_path,
        )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "failed"
    assert report["attempts_used"] == 1
    assert state["verify_calls"] == 1
    assert state["driver_instances"] == 1


def test_sync_configuration_error_includes_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    create_project(tmp_path)
    report_path = tmp_path / "sync_config_fail_report.json"

    def _raise_config_error(errors: ExceptionMap) -> None:
        raise errors["config"]("unknown database")

    _install_fake_neo4j(monkeypatch, _raise_config_error)

    with pytest.raises(ConnectionError, match="database=analytics"):
        sync_project_to_neo4j(
            tmp_path,
            "bolt://example:7687",
            "neo4j",
            "password",
            database="analytics",
            max_retries=3,
            retry_backoff_seconds=0.0,
            report_path=report_path,
        )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "failed"
    assert report["attempts_used"] == 1


def test_sync_transient_error_retries_until_exhausted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    create_project(tmp_path)
    report_path = tmp_path / "sync_retry_fail_report.json"

    def _raise_transient(errors: ExceptionMap) -> None:
        raise errors["transient"]("temporary outage")

    state = _install_fake_neo4j(monkeypatch, _raise_transient)
    monkeypatch.setattr("chronicle.store.neo4j_sync.time.sleep", lambda _s: None)

    with pytest.raises(ConnectionError, match="failed after 3 attempts"):
        sync_project_to_neo4j(
            tmp_path,
            "bolt://example:7687",
            "neo4j",
            "password",
            max_retries=3,
            retry_backoff_seconds=0.0,
            report_path=report_path,
        )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "failed"
    assert report["attempts_used"] == 3
    assert state["verify_calls"] == 3
    assert state["driver_instances"] == 3


def test_sync_reports_missing_neo4j_driver_dependency(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    create_project(tmp_path)
    fake_empty_module = types.ModuleType("neo4j")
    monkeypatch.setitem(sys.modules, "neo4j", fake_empty_module)
    monkeypatch.delitem(sys.modules, "neo4j.exceptions", raising=False)

    with pytest.raises(RuntimeError, match="Neo4j driver not installed"):
        sync_project_to_neo4j(
            tmp_path,
            "bolt://example:7687",
            "neo4j",
            "password",
        )
