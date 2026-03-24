"""Phase 4 coverage: session get_defensibility_as_of, export_minimal_for_claim, reasoning trail, accountability, audit bundle."""

from __future__ import annotations

from pathlib import Path

import pytest
from chronicle.core.errors import ChronicleUserError
from chronicle.store.project import create_project
from chronicle.store.session import ChronicleSession


def test_session_get_defensibility_as_of_by_event_id(tmp_path: Path) -> None:
    """get_defensibility_as_of with as_of_event_id returns snapshot at that event."""
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("AsOf", actor_id="t", actor_type="tool")
        _, ev_uid = session.ingest_evidence(
            inv_uid, b"E", "text/plain", original_filename="e.txt", actor_id="t", actor_type="tool"
        )
        _, span_uid = session.anchor_span(
            inv_uid,
            ev_uid,
            "text_offset",
            {"start_char": 0, "end_char": 1},
            quote="E",
            actor_id="t",
            actor_type="tool",
        )
        _, claim_uid = session.propose_claim(inv_uid, "Claim.", actor_id="t", actor_type="tool")
        events = session.store.read_all(limit=10)
        first_event_id = events[0].event_id
        session.link_support(inv_uid, span_uid, claim_uid, actor_id="t", actor_type="tool")

        result = session.get_defensibility_as_of(inv_uid, as_of_event_id=first_event_id)
    assert result is not None
    assert result["investigation_uid"] == inv_uid
    assert result["as_of"] == first_event_id
    assert "claims" in result
    # At first event we only had InvestigationCreated; claim may not exist yet in ephemeral replay
    assert isinstance(result["claims"], list)


def test_session_get_defensibility_as_of_by_date(tmp_path: Path) -> None:
    """get_defensibility_as_of with as_of_date returns snapshot at that time."""
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("AsOfDate", actor_id="t", actor_type="tool")
        session.propose_claim(inv_uid, "C.", actor_id="t", actor_type="tool")
        claims = session.store.get_read_model().list_claims_by_type(
            investigation_uid=inv_uid, limit=1
        )
        assert claims
        created_at = claims[0].created_at

        result = session.get_defensibility_as_of(inv_uid, as_of_date=created_at)
    assert result is not None
    assert result["investigation_uid"] == inv_uid
    assert result["as_of"] == created_at
    assert "claims" in result


def test_session_get_defensibility_as_of_requires_exactly_one(tmp_path: Path) -> None:
    """get_defensibility_as_of raises when both or neither as_of_date and as_of_event_id are set."""
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("AsOf", actor_id="t", actor_type="tool")
        with pytest.raises(ChronicleUserError, match="Exactly one"):
            session.get_defensibility_as_of(inv_uid)
        with pytest.raises(ChronicleUserError, match="Exactly one|At most one"):
            session.get_defensibility_as_of(
                inv_uid, as_of_date="2024-01-01T00:00:00Z", as_of_event_id="e1"
            )


def test_session_export_minimal_for_claim(tmp_path: Path) -> None:
    """export_minimal_for_claim writes a .chronicle file for one claim."""
    create_project(tmp_path)
    out = tmp_path / "minimal.chronicle"
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("Min", actor_id="t", actor_type="tool")
        _, ev_uid = session.ingest_evidence(
            inv_uid, b"X", "text/plain", original_filename="x.txt", actor_id="t", actor_type="tool"
        )
        _, span_uid = session.anchor_span(
            inv_uid,
            ev_uid,
            "text_offset",
            {"start_char": 0, "end_char": 1},
            quote="X",
            actor_id="t",
            actor_type="tool",
        )
        _, claim_uid = session.propose_claim(inv_uid, "Answer.", actor_id="t", actor_type="tool")
        session.link_support(inv_uid, span_uid, claim_uid, actor_id="t", actor_type="tool")
        path = session.export_minimal_for_claim(inv_uid, claim_uid, out)
    assert path.is_file()
    assert path.suffix == ".chronicle"


def test_session_get_reasoning_trail_claim(tmp_path: Path) -> None:
    """get_reasoning_trail_claim returns events that affected the claim."""
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("Trail", actor_id="t", actor_type="tool")
        _, claim_uid = session.propose_claim(inv_uid, "C.", actor_id="t", actor_type="tool")
        trail = session.get_reasoning_trail_claim(claim_uid)
    assert trail is not None
    assert trail["claim_uid"] == claim_uid
    assert "events" in trail
    assert len(trail["events"]) >= 1


def test_session_get_reasoning_trail_claim_nonexistent(tmp_path: Path) -> None:
    """get_reasoning_trail_claim returns None for unknown claim."""
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        trail = session.get_reasoning_trail_claim("nonexistent-claim-uid")
    assert trail is None


def test_session_get_accountability_chain(tmp_path: Path) -> None:
    """get_accountability_chain returns roles (proposer, linkers, etc.) for a claim."""
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("Account", actor_id="t", actor_type="tool")
        _, ev_uid = session.ingest_evidence(
            inv_uid, b"E", "text/plain", original_filename="e.txt", actor_id="t", actor_type="tool"
        )
        _, span_uid = session.anchor_span(
            inv_uid,
            ev_uid,
            "text_offset",
            {"start_char": 0, "end_char": 1},
            quote="E",
            actor_id="t",
            actor_type="tool",
        )
        _, claim_uid = session.propose_claim(inv_uid, "Claim.", actor_id="t", actor_type="tool")
        session.link_support(inv_uid, span_uid, claim_uid, actor_id="t", actor_type="tool")
        chain = session.get_accountability_chain(claim_uid, limit=50)
    assert isinstance(chain, list)
    assert len(chain) >= 1
    assert any(e.get("role") for e in chain)


def test_session_get_audit_export_bundle(tmp_path: Path) -> None:
    """get_audit_export_bundle returns investigation audit pack with claims and defensibility_snapshot."""
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("Audit", actor_id="t", actor_type="tool")
        session.propose_claim(inv_uid, "C.", actor_id="t", actor_type="tool")
        bundle = session.get_audit_export_bundle(inv_uid, limit_claims=10)
    assert bundle["investigation_uid"] == inv_uid
    assert "claims_list" in bundle
    assert "defensibility_snapshot" in bundle
    assert "accountability_by_claim" in bundle
    assert "evidence_list" in bundle
    assert "human_decisions_audit_trail" in bundle
    assert "exported_at" in bundle


def test_session_get_audit_export_bundle_with_as_of_event_id(tmp_path: Path) -> None:
    """get_audit_export_bundle with as_of_event_id sets defensibility_snapshot at that point."""
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("AuditAsOf", actor_id="t", actor_type="tool")
        events = session.store.read_all(limit=5)
        first_id = events[0].event_id
        session.propose_claim(inv_uid, "C.", actor_id="t", actor_type="tool")
        bundle = session.get_audit_export_bundle(inv_uid, as_of_event_id=first_id, limit_claims=10)
    assert bundle["investigation_uid"] == inv_uid
    assert bundle.get("defensibility_as_of") == first_id
    assert "defensibility_snapshot" in bundle


def test_session_get_audit_export_bundle_investigation_not_found(tmp_path: Path) -> None:
    """get_audit_export_bundle raises when investigation does not exist."""
    create_project(tmp_path)
    with (
        ChronicleSession(tmp_path) as session,
        pytest.raises(ChronicleUserError, match="Investigation not found"),
    ):
        session.get_audit_export_bundle("nonexistent-inv-uid")


def test_session_get_reasoning_brief_with_as_of_date(tmp_path: Path) -> None:
    """get_reasoning_brief with as_of_date uses defensibility at that point in time."""
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("BriefAsOf", actor_id="t", actor_type="tool")
        _, ev_uid = session.ingest_evidence(
            inv_uid, b"E", "text/plain", original_filename="e.txt", actor_id="t", actor_type="tool"
        )
        _, span_uid = session.anchor_span(
            inv_uid,
            ev_uid,
            "text_offset",
            {"start_char": 0, "end_char": 1},
            quote="E",
            actor_id="t",
            actor_type="tool",
        )
        _, claim_uid = session.propose_claim(inv_uid, "C.", actor_id="t", actor_type="tool")
        session.link_support(inv_uid, span_uid, claim_uid, actor_id="t", actor_type="tool")
        rm = session.store.get_read_model()
        claim = rm.get_claim(claim_uid)
        assert claim is not None
        brief = session.get_reasoning_brief(claim_uid, as_of_date=claim.created_at)
    assert brief is not None
    assert brief.get("claim_uid") == claim_uid


def test_session_get_human_decisions_audit_trail(tmp_path: Path) -> None:
    """get_human_decisions_audit_trail returns list (tier changes, dismissals)."""
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("Decisions", actor_id="t", actor_type="tool")
        trail = session.get_human_decisions_audit_trail(inv_uid, limit=100)
    assert isinstance(trail, list)


def test_session_get_reviewer_decision_ledger(tmp_path: Path) -> None:
    """get_reviewer_decision_ledger returns consolidated decisions plus unresolved tensions."""
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("Ledger", actor_id="editor", actor_type="human")
        _, claim_a_uid = session.propose_claim(
            inv_uid,
            "Claim A.",
            actor_id="editor",
            actor_type="human",
        )
        _, claim_b_uid = session.propose_claim(
            inv_uid,
            "Claim B.",
            actor_id="editor",
            actor_type="human",
        )
        session.record_human_override(
            claim_a_uid,
            "defensibility_warning",
            "Reviewed by senior editor.",
            actor_id="editor",
            actor_type="human",
        )
        session.record_human_confirm(
            "claim",
            claim_a_uid,
            "editorial_review",
            "Confirmed after review.",
            actor_id="editor",
            actor_type="human",
        )
        session.set_tier(
            inv_uid,
            "forge",
            actor_id="editor",
            actor_type="human",
        )
        _, tension_uid = session.declare_tension(
            inv_uid,
            claim_a_uid,
            claim_b_uid,
            tension_kind="contradiction",
            notes="Potential conflict under review.",
            actor_id="editor",
            actor_type="human",
            workspace="forge",
        )

        ledger = session.get_reviewer_decision_ledger(inv_uid, limit=200)

    assert ledger["investigation_uid"] == inv_uid
    assert "generated_at" in ledger
    assert isinstance(ledger["decisions"], list)
    assert isinstance(ledger["unresolved_tensions"], list)
    assert any(d.get("decision_kind") == "human_overrode" for d in ledger["decisions"])
    assert any(d.get("decision_kind") == "human_confirmed" for d in ledger["decisions"])
    assert any(d.get("decision_kind") == "tier_changed" for d in ledger["decisions"])
    assert any(t.get("tension_uid") == tension_uid for t in ledger["unresolved_tensions"])

    summary = ledger["summary"]
    assert summary["total_decisions"] >= 3
    assert summary["tier_changed_count"] >= 1
    assert summary["human_overrode_count"] >= 1
    assert summary["human_confirmed_count"] >= 1
    assert summary["unresolved_tensions_count"] >= 1


def test_session_get_review_packet(tmp_path: Path) -> None:
    """get_review_packet returns one artifact with policy, decisions, reasoning, and audit sections."""
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("ReviewPacket", actor_id="t", actor_type="tool")
        _, claim_uid = session.propose_claim(
            inv_uid, "Packet claim", actor_id="t", actor_type="tool"
        )
        session.set_tier(inv_uid, "forge", actor_id="t", actor_type="human")

        packet = session.get_review_packet(
            inv_uid,
            limit_claims=50,
            decision_limit=100,
            include_reasoning_briefs=True,
        )

    assert packet["investigation_uid"] == inv_uid
    assert packet["investigation_title"] == "ReviewPacket"
    assert "generated_at" in packet
    assert packet["policy_compatibility"]["investigation_uid"] == inv_uid
    assert packet["reviewer_decision_ledger"]["investigation_uid"] == inv_uid
    assert packet["audit_export_bundle"]["investigation_uid"] == inv_uid
    assert isinstance(packet["reasoning_briefs"], list)
    assert any(r.get("claim_uid") == claim_uid for r in packet["reasoning_briefs"])
    assert isinstance(packet["chain_of_custody_reports"], list)
    assert isinstance(packet["warnings"], list)


def test_session_get_investigation_event_history(tmp_path: Path) -> None:
    """get_investigation_event_history returns events for the investigation."""
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("History", actor_id="t", actor_type="tool")
        session.propose_claim(inv_uid, "C.", actor_id="t", actor_type="tool")
        history = session.get_investigation_event_history(inv_uid, limit=50)
    assert isinstance(history, list)
    assert len(history) >= 2


def test_session_get_audit_export_bundle_include_full_trail(tmp_path: Path) -> None:
    """get_audit_export_bundle with include_full_trail=True includes full_event_history."""
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("FullTrail", actor_id="t", actor_type="tool")
        session.propose_claim(inv_uid, "C.", actor_id="t", actor_type="tool")
        bundle = session.get_audit_export_bundle(inv_uid, include_full_trail=True, limit_claims=10)
    assert "full_event_history" in bundle
    assert isinstance(bundle["full_event_history"], list)


def test_session_get_defensibility_as_of_event_id_not_found(tmp_path: Path) -> None:
    """get_defensibility_as_of raises when as_of_event_id is not in the investigation stream."""
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("AsOfErr", actor_id="t", actor_type="tool")
        session.propose_claim(inv_uid, "C.", actor_id="t", actor_type="tool")
        with pytest.raises(
            ChronicleUserError, match="as_of_event_id .* not found in investigation stream"
        ):
            session.get_defensibility_as_of(inv_uid, as_of_event_id="nonexistent-event-id")


def test_session_get_reasoning_brief_with_as_of_event_id(tmp_path: Path) -> None:
    """get_reasoning_brief with as_of_event_id uses defensibility at that event."""
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("BriefEvent", actor_id="t", actor_type="tool")
        _, ev_uid = session.ingest_evidence(
            inv_uid, b"E", "text/plain", original_filename="e.txt", actor_id="t", actor_type="tool"
        )
        _, span_uid = session.anchor_span(
            inv_uid,
            ev_uid,
            "text_offset",
            {"start_char": 0, "end_char": 1},
            quote="E",
            actor_id="t",
            actor_type="tool",
        )
        _, claim_uid = session.propose_claim(inv_uid, "C.", actor_id="t", actor_type="tool")
        session.link_support(inv_uid, span_uid, claim_uid, actor_id="t", actor_type="tool")
        events = session.store.read_by_investigation(inv_uid, limit=20)
        event_ids = [e.event_id for e in events]
        assert len(event_ids) >= 1
        brief = session.get_reasoning_brief(claim_uid, as_of_event_id=event_ids[-1])
    assert brief is not None
    assert brief.get("claim_uid") == claim_uid


def test_session_get_reasoning_brief_with_tension(tmp_path: Path) -> None:
    """get_reasoning_brief includes tensions and claim_set_consistency when claim has a tension."""
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("Tension", actor_id="t", actor_type="tool")
        _, claim_a = session.propose_claim(inv_uid, "Claim A.", actor_id="t", actor_type="tool")
        _, claim_b = session.propose_claim(inv_uid, "Claim B.", actor_id="t", actor_type="tool")
        session.declare_tension(
            inv_uid,
            claim_a,
            claim_b,
            tension_kind="contradiction",
            notes="Test",
            actor_id="t",
            actor_type="tool",
            workspace="forge",
        )
        brief = session.get_reasoning_brief(claim_a)
    assert brief is not None
    assert brief.get("claim_uid") == claim_a
    assert "tensions" in brief
    assert len(brief["tensions"]) >= 1
    assert "claim_set_consistency" in brief
    assert brief["claim_set_consistency"]["total"] >= 1
