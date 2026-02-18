"""Tests for chronicle.verify: invariant verification suite (Spec 12.7.5, 15.6)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from chronicle.store.project import CHRONICLE_DB, create_project
from chronicle.store.schema import (
    init_event_store_schema,
    init_read_model_schema,
)
from chronicle.verify import (
    CheckResult,
    VerifyReport,
    verify_append_only_ledger,
    verify_db,
    verify_evidence_integrity,
    verify_project,
    verify_projection_completeness,
    verify_referential_integrity,
    verify_status_consistency,
)


def test_verify_report_add_passed_stays_true() -> None:
    r = VerifyReport(passed=True)
    r.add("a", True)
    r.add("b", True)
    assert r.passed is True
    assert len(r.results) == 2
    assert r.results[0].name == "a" and r.results[0].passed is True


def test_verify_report_add_failed_sets_passed_false() -> None:
    r = VerifyReport(passed=True)
    r.add("a", True)
    r.add("b", False, "detail")
    assert r.passed is False
    assert r.results[1].detail == "detail"


def test_verify_project_no_db(tmp_path: Path) -> None:
    report = verify_project(tmp_path)
    assert report.passed is False
    names = [c.name for c in report.results]
    assert "project_exists" in names
    assert any("no " in c.detail for c in report.results if c.name == "project_exists")


def test_verify_project_with_db_empty_store(tmp_path: Path) -> None:
    create_project(tmp_path)
    report = verify_project(tmp_path, check_evidence_files=False)
    assert report.passed is True
    names = [c.name for c in report.results]
    assert "project_exists" in names
    assert "append_only_ledger" in names
    assert "referential_integrity" in names
    assert "status_consistency" in names
    assert "projection_completeness" in names
    assert "evidence_integrity" not in names


def test_verify_project_skips_evidence_integrity_when_false(tmp_path: Path) -> None:
    create_project(tmp_path)
    report = verify_project(tmp_path, check_evidence_files=False)
    assert "evidence_integrity" not in [c.name for c in report.results]


def test_verify_db_missing_file(tmp_path: Path) -> None:
    report = verify_db(tmp_path / "nonexistent.db")
    assert report.passed is False
    assert any(c.name == "db_exists" and not c.passed for c in report.results)


def test_verify_db_existing_project(tmp_path: Path) -> None:
    create_project(tmp_path)
    db_path = tmp_path / CHRONICLE_DB
    report = verify_db(db_path)
    assert report.passed is True
    assert any(c.name == "db_exists" and c.passed for c in report.results)


def test_verify_append_only_ledger_empty(verify_conn) -> None:
    report = VerifyReport(passed=True)
    verify_append_only_ledger(verify_conn, report)
    assert report.passed is True
    assert any(c.name == "append_only_ledger" and "empty" in c.detail for c in report.results)


def test_verify_append_only_ledger_in_order(verify_conn_with_events) -> None:
    conn = verify_conn_with_events
    report = VerifyReport(passed=True)
    verify_append_only_ledger(conn, report)
    assert report.passed is True
    assert any(c.name == "append_only_ledger" and "in order" in c.detail for c in report.results)


def test_verify_append_only_ledger_reversal(verify_conn) -> None:
    conn = verify_conn
    conn.execute(
        "INSERT INTO events (event_id, event_type, occurred_at, recorded_at, investigation_uid, subject_uid, actor_type, actor_id, workspace, policy_profile_id, correlation_id, causation_id, envelope_version, payload_version, payload) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("e1", "InvestigationCreated", "2024-01-01T00:00:00Z", "2024-01-01T00:00:01Z", "i", "i", "tool", "t", "spark", None, None, None, 1, 1, "{}"),
    )
    conn.execute(
        "INSERT INTO events (event_id, event_type, occurred_at, recorded_at, investigation_uid, subject_uid, actor_type, actor_id, workspace, policy_profile_id, correlation_id, causation_id, envelope_version, payload_version, payload) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("e2", "InvestigationCreated", "2024-01-01T00:00:00Z", "2024-01-01T00:00:00Z", "i", "i", "tool", "t", "spark", None, None, None, 1, 1, "{}"),
    )
    conn.commit()
    report = VerifyReport(passed=True)
    verify_append_only_ledger(conn, report)
    assert report.passed is False
    assert any(c.name == "append_only_ledger" and "reversal" in c.detail for c in report.results)


def test_verify_referential_integrity_empty(verify_conn) -> None:
    report = VerifyReport(passed=True)
    verify_referential_integrity(verify_conn, report)
    assert report.passed is True
    assert any(c.name == "referential_integrity" for c in report.results)


def test_verify_referential_integrity_orphan_evidence_link(verify_conn) -> None:
    conn = verify_conn
    conn.execute("INSERT INTO claim (claim_uid, investigation_uid, created_at, created_by_actor_id, claim_text, current_status, updated_at) VALUES ('c1', 'i', '2024-01-01T00:00:00Z', 't', 'text', 'ACTIVE', '2024-01-01T00:00:00Z')")
    conn.execute("INSERT INTO evidence_item (evidence_uid, investigation_uid, created_at, ingested_by_actor_id, content_hash, file_size_bytes, original_filename, uri, media_type, updated_at) VALUES ('ev1', 'i', '2024-01-01T00:00:00Z', 't', 'h', 0, '', '', 'text/plain', '2024-01-01T00:00:00Z')")
    conn.execute("INSERT INTO evidence_span (span_uid, evidence_uid, anchor_type, anchor_json, created_at, created_by_actor_id, source_event_id) VALUES ('s1', 'ev1', 'text_offset', '{}', '2024-01-01T00:00:00Z', 't', 'ev-span-1')")
    conn.execute("INSERT INTO evidence_link (link_uid, claim_uid, span_uid, link_type, created_at, created_by_actor_id, source_event_id) VALUES ('l1', 'missing_claim', 's1', 'support', '2024-01-01T00:00:00Z', 't', 'ev-link-1')")
    conn.commit()
    report = VerifyReport(passed=True)
    verify_referential_integrity(conn, report)
    assert report.passed is False
    assert any(c.name == "referential_integrity" and "missing" in c.detail for c in report.results)


def test_verify_status_consistency_valid(verify_conn) -> None:
    conn = verify_conn
    conn.execute("INSERT INTO claim (claim_uid, investigation_uid, created_at, created_by_actor_id, claim_text, current_status, updated_at) VALUES ('c1', 'i', '2024-01-01T00:00:00Z', 't', 'text', 'ACTIVE', '2024-01-01T00:00:00Z')")
    conn.commit()
    report = VerifyReport(passed=True)
    verify_status_consistency(conn, report)
    assert report.passed is True


def test_verify_status_consistency_invalid_claim_status(verify_conn) -> None:
    conn = verify_conn
    conn.execute("INSERT INTO claim (claim_uid, investigation_uid, created_at, created_by_actor_id, claim_text, current_status, updated_at) VALUES ('c1', 'i', '2024-01-01T00:00:00Z', 't', 'text', 'INVALID', '2024-01-01T00:00:00Z')")
    conn.commit()
    report = VerifyReport(passed=True)
    verify_status_consistency(conn, report)
    assert report.passed is False
    assert any(c.name == "status_consistency" and "invalid" in c.detail.lower() for c in report.results)


def test_verify_projection_completeness_match(verify_conn_with_events) -> None:
    conn = verify_conn_with_events
    conn.execute("INSERT INTO processed_event (projection_name, event_id, processed_at) VALUES ('read_model', 'e1', '2024-01-01T00:00:00Z')")
    conn.commit()
    report = VerifyReport(passed=True)
    verify_projection_completeness(conn, report)
    assert report.passed is True


def test_verify_projection_completeness_mismatch(verify_conn_with_events) -> None:
    conn = verify_conn_with_events
    report = VerifyReport(passed=True)
    verify_projection_completeness(conn, report)
    assert report.passed is False
    assert any(c.name == "projection_completeness" and "events=" in c.detail for c in report.results)


def test_verify_evidence_integrity_no_items(verify_conn, tmp_path: Path) -> None:
    report = VerifyReport(passed=True)
    verify_evidence_integrity(verify_conn, tmp_path, report)
    assert report.passed is True
    assert any("no evidence" in c.detail for c in report.results if c.name == "evidence_integrity")


def test_verify_evidence_integrity_file_missing(verify_conn, tmp_path: Path) -> None:
    conn = verify_conn
    conn.execute(
        "INSERT INTO evidence_item (evidence_uid, investigation_uid, created_at, ingested_by_actor_id, content_hash, file_size_bytes, original_filename, uri, media_type, updated_at) VALUES ('ev1', 'i', '2024-01-01T00:00:00Z', 't', 'abc', 0, '', 'evidence/missing.txt', 'text/plain', '2024-01-01T00:00:00Z')"
    )
    conn.commit()
    report = VerifyReport(passed=True)
    verify_evidence_integrity(conn, tmp_path, report)
    assert report.passed is False
    assert any(c.name == "evidence_integrity" and "missing" in c.detail for c in report.results)


def test_verify_evidence_integrity_hash_mismatch(verify_conn, tmp_path: Path) -> None:
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir(exist_ok=True)
    f = evidence_dir / "ev1.txt"
    f.write_bytes(b"content")
    conn = verify_conn
    digest = "wrong_hash_not_sha256_of_content"
    conn.execute(
        "INSERT INTO evidence_item (evidence_uid, investigation_uid, created_at, ingested_by_actor_id, content_hash, file_size_bytes, original_filename, uri, media_type, updated_at) VALUES ('ev1', 'i', '2024-01-01T00:00:00Z', 't', ?, 7, '', 'evidence/ev1.txt', 'text/plain', '2024-01-01T00:00:00Z')",
        (digest,),
    )
    conn.commit()
    report = VerifyReport(passed=True)
    verify_evidence_integrity(conn, tmp_path, report)
    assert report.passed is False
    assert any(c.name == "evidence_integrity" and "mismatch" in c.detail for c in report.results)


@pytest.fixture
def verify_conn(tmp_path: Path):
    """DB with event store + read model schema, no events."""
    db_path = tmp_path / CHRONICLE_DB
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    init_event_store_schema(conn)
    init_read_model_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def verify_conn_with_events(verify_conn):
    """DB with one event in events table."""
    conn = verify_conn
    conn.execute(
        "INSERT INTO events (event_id, event_type, occurred_at, recorded_at, investigation_uid, subject_uid, actor_type, actor_id, workspace, policy_profile_id, correlation_id, causation_id, envelope_version, payload_version, payload) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("e1", "InvestigationCreated", "2024-01-01T00:00:00Z", "2024-01-01T00:00:01Z", "i", "i", "tool", "t", "spark", None, None, None, 1, 1, "{}"),
    )
    conn.commit()
    return conn
