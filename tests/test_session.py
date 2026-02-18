"""Minimal tests for ChronicleSession: ingest evidence, propose claim, link support, get_defensibility_score."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from chronicle.store.project import create_project
from chronicle.store.session import ChronicleSession


def test_session_flow_ingest_propose_link_defensibility(tmp_path: Path) -> None:
    """Create project, investigation, ingest evidence, propose claim, link support, get defensibility score."""
    create_project(tmp_path)
    text = b"The company reported revenue of $1.2M in Q1 2024."
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation(
            "Test investigation",
            actor_id="test",
            actor_type="tool",
        )
        _, ev_uid = session.ingest_evidence(
            inv_uid,
            text,
            "text/plain",
            original_filename="doc.txt",
            actor_id="test",
            actor_type="tool",
        )
        _, span_uid = session.anchor_span(
            inv_uid,
            ev_uid,
            "text_offset",
            {"start_char": 0, "end_char": len(text.decode("utf-8"))},
            quote=text.decode("utf-8"),
            actor_id="test",
            actor_type="tool",
        )
        _, claim_uid = session.propose_claim(
            inv_uid,
            "Revenue was $1.2M.",
            actor_id="test",
            actor_type="tool",
        )
        session.link_support(
            inv_uid,
            span_uid,
            claim_uid,
            actor_id="test",
            actor_type="tool",
        )
        scorecard = session.get_defensibility_score(claim_uid)
    assert scorecard is not None
    assert scorecard.provenance_quality in ("strong", "medium", "weak", "challenged")
    assert scorecard.corroboration.get("support_count", 0) >= 1
    assert scorecard.contradiction_status in ("none", "open", "acknowledged", "resolved")


def test_session_requires_existing_project(tmp_path: Path) -> None:
    """ChronicleSession raises if project dir has no chronicle.db."""
    from chronicle.core.errors import ChronicleProjectNotFoundError

    # tmp_path exists but we never call create_project; no chronicle.db
    with pytest.raises(ChronicleProjectNotFoundError, match="Not a Chronicle project"):
        ChronicleSession(tmp_path)


def test_session_verification_level_persisted_in_payload(tmp_path: Path) -> None:
    """When verification_level (and attestation_ref) are passed, they are stored in event payload."""
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        session.create_investigation(
            "Attested run",
            actor_id="alice",
            actor_type="human",
            verification_level="verified_credential",
            attestation_ref="att-123",
        )
        events = session.store.read_all(limit=5)
    assert len(events) >= 1
    created = next((e for e in events if e.event_type == "InvestigationCreated"), events[0])
    assert created.payload.get("_verification_level") == "verified_credential"
    assert created.payload.get("_attestation_ref") == "att-123"


def test_session_multi_evidence_corroboration(tmp_path: Path) -> None:
    """Multiple evidence chunks linked as support produce higher support_count in scorecard."""
    create_project(tmp_path)
    chunk1 = b"The company reported revenue of $1.2M in Q1 2024."
    chunk2 = b"Q1 2024 revenue was $1.2 million according to the earnings release."
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation(
            "Multi-evidence test",
            actor_id="test",
            actor_type="tool",
        )
        _, ev1 = session.ingest_evidence(
            inv_uid, chunk1, "text/plain", original_filename="a.txt", actor_id="test", actor_type="tool"
        )
        _, ev2 = session.ingest_evidence(
            inv_uid, chunk2, "text/plain", original_filename="b.txt", actor_id="test", actor_type="tool"
        )
        _, span1 = session.anchor_span(
            inv_uid, ev1, "text_offset", {"start_char": 0, "end_char": len(chunk1.decode())},
            quote=chunk1.decode(), actor_id="test", actor_type="tool",
        )
        _, span2 = session.anchor_span(
            inv_uid, ev2, "text_offset", {"start_char": 0, "end_char": len(chunk2.decode())},
            quote=chunk2.decode(), actor_id="test", actor_type="tool",
        )
        _, claim_uid = session.propose_claim(
            inv_uid, "Revenue was $1.2M in Q1 2024.", actor_id="test", actor_type="tool"
        )
        session.link_support(inv_uid, span1, claim_uid, actor_id="test", actor_type="tool")
        session.link_support(inv_uid, span2, claim_uid, actor_id="test", actor_type="tool")
        scorecard = session.get_defensibility_score(claim_uid)
    assert scorecard is not None
    assert scorecard.corroboration.get("support_count", 0) >= 2
    assert scorecard.provenance_quality in ("strong", "medium", "weak", "challenged")


def test_session_defensibility_metrics_contract(tmp_path: Path) -> None:
    """defensibility_metrics_for_claim(session, claim_uid) returns eval-contract shape (claim_uid, provenance_quality, corroboration, contradiction_status)."""
    from chronicle.eval_metrics import defensibility_metrics_for_claim

    create_project(tmp_path)
    text = b"Revenue in Q1 was $1.5M."
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation(
            "Eval contract test", actor_id="test", actor_type="tool"
        )
        _, ev_uid = session.ingest_evidence(
            inv_uid, text, "text/plain", original_filename="doc.txt", actor_id="test", actor_type="tool"
        )
        _, span_uid = session.anchor_span(
            inv_uid, ev_uid, "text_offset", {"start_char": 0, "end_char": len(text.decode())},
            quote=text.decode(), actor_id="test", actor_type="tool",
        )
        _, claim_uid = session.propose_claim(
            inv_uid, "Revenue was $1.5M in Q1.", actor_id="test", actor_type="tool"
        )
        session.link_support(inv_uid, span_uid, claim_uid, actor_id="test", actor_type="tool")
        metrics = defensibility_metrics_for_claim(session, claim_uid)
    assert metrics is not None
    assert metrics.get("claim_uid") == claim_uid
    assert metrics.get("provenance_quality") in ("strong", "medium", "weak", "challenged")
    assert "corroboration" in metrics
    corr = metrics["corroboration"]
    assert "support_count" in corr
    assert "challenge_count" in corr
    assert "independent_sources_count" in corr
    assert metrics.get("contradiction_status") in ("none", "open", "acknowledged", "resolved")
