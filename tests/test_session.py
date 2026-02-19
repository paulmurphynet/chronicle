"""Minimal tests for ChronicleSession: ingest evidence, propose claim, link support, get_defensibility_score."""

from __future__ import annotations

from pathlib import Path

import pytest
from chronicle.core.policy import PolicyProfile, default_policy_profile, import_policy_to_project
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
    assert scorecard.link_assurance_level == "tool_generated"


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
    assert metrics.get("link_assurance_level") == "tool_generated"
    assert isinstance(metrics.get("link_assurance_caveat"), str)


def test_claim_evidence_metrics_export(tmp_path: Path) -> None:
    """build_claim_evidence_metrics_export returns stable JSON shape (claim + evidence refs + defensibility)."""
    from chronicle.store.commands.generic_export import build_claim_evidence_metrics_export

    create_project(tmp_path)
    text = b"The company reported revenue of $1.2M in Q1 2024."
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation(
            "Export test", actor_id="test", actor_type="tool"
        )
        _, ev_uid = session.ingest_evidence(
            inv_uid, text, "text/plain", original_filename="doc.txt", actor_id="test", actor_type="tool"
        )
        _, span_uid = session.anchor_span(
            inv_uid, ev_uid, "text_offset", {"start_char": 0, "end_char": len(text.decode())},
            quote=text.decode(), actor_id="test", actor_type="tool",
        )
        _, claim_uid = session.propose_claim(
            inv_uid, "Revenue was $1.2M in Q1 2024.", actor_id="test", actor_type="tool"
        )
        session.link_support(inv_uid, span_uid, claim_uid, actor_id="test", actor_type="tool")
        data = build_claim_evidence_metrics_export(
            session.read_model,
            session.get_defensibility_score,
            inv_uid,
        )
    assert data["schema_version"] == 1
    assert data["investigation_uid"] == inv_uid
    assert len(data["claims"]) == 1
    claim = data["claims"][0]
    assert claim["claim_uid"] == claim_uid
    assert "Revenue" in claim["claim_text"]
    assert claim["support_count"] == 1
    assert claim["challenge_count"] == 0
    assert len(claim["evidence_refs"]) == 1
    ref = claim["evidence_refs"][0]
    assert ref["evidence_uid"] == ev_uid
    assert ref.get("span_uid") == span_uid
    assert ref["link_type"] == "SUPPORT"
    assert "defensibility" in claim
    assert claim["defensibility"].get("provenance_quality") in ("strong", "medium", "weak", "challenged")
    assert claim["defensibility"].get("link_assurance_level") == "tool_generated"


def test_session_policy_compatibility_preflight(tmp_path: Path) -> None:
    """Session can compare built-under and viewing policy profiles for one investigation."""
    create_project(tmp_path)
    base = default_policy_profile().to_dict()
    base["profile_id"] = "policy_strict_test"
    base["display_name"] = "Strict test profile"
    base["mes_rules"][0]["min_independent_sources"] = 3
    strict_profile = PolicyProfile.from_dict(base)
    import_policy_to_project(tmp_path, strict_profile, activate=False)

    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation(
            "Policy preflight session test",
            actor_id="tester",
            actor_type="tool",
        )
        result = session.get_policy_compatibility_preflight(
            inv_uid,
            viewing_profile_id="policy_strict_test",
            built_under_profile_id="policy_investigative_journalism",
        )

    assert result["investigation_uid"] == inv_uid
    assert result["built_under"] == "policy_investigative_journalism"
    assert result["viewing_under"] == "policy_strict_test"
    assert isinstance(result.get("deltas"), list)
    assert any("min_independent_sources" in d.get("rule", "") for d in result["deltas"])


def test_session_link_assurance_human_reviewed(tmp_path: Path) -> None:
    """Human-created links should surface human_reviewed assurance level."""
    create_project(tmp_path)
    text = b"Claim support text."
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation(
            "Human assurance test",
            actor_id="alice",
            actor_type="human",
        )
        _, ev_uid = session.ingest_evidence(
            inv_uid,
            text,
            "text/plain",
            original_filename="doc.txt",
            actor_id="alice",
            actor_type="human",
        )
        _, span_uid = session.anchor_span(
            inv_uid,
            ev_uid,
            "text_offset",
            {"start_char": 0, "end_char": len(text.decode("utf-8"))},
            quote=text.decode("utf-8"),
            actor_id="alice",
            actor_type="human",
        )
        _, claim_uid = session.propose_claim(
            inv_uid,
            "Supported claim.",
            actor_id="alice",
            actor_type="human",
        )
        session.link_support(
            inv_uid,
            span_uid,
            claim_uid,
            actor_id="alice",
            actor_type="human",
        )
        scorecard = session.get_defensibility_score(claim_uid)
    assert scorecard is not None
    assert scorecard.link_assurance_level == "human_reviewed"
    assert isinstance(scorecard.link_assurance_caveat, str)
