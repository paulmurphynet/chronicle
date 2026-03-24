"""Phase 2 coverage: projection handlers, sqlite_read_model methods, defensibility path."""

from __future__ import annotations

from pathlib import Path

import pytest
from chronicle.store.commands.claims import get_defensibility_score
from chronicle.store.project import create_project
from chronicle.store.session import ChronicleSession


def test_link_support_with_rationale_persisted(tmp_path: Path) -> None:
    """Support link with rationale is projected; read model returns it."""
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("Rationale", actor_id="t", actor_type="tool")
        _, ev_uid = session.ingest_evidence(
            inv_uid,
            b"Evidence text",
            "text/plain",
            original_filename="e.txt",
            actor_id="t",
            actor_type="tool",
        )
        _, span_uid = session.anchor_span(
            inv_uid,
            ev_uid,
            "text_offset",
            {"start_char": 0, "end_char": 12},
            quote="Evidence text",
            actor_id="t",
            actor_type="tool",
        )
        _, claim_uid = session.propose_claim(inv_uid, "The claim.", actor_id="t", actor_type="tool")
        session.link_support(
            inv_uid,
            span_uid,
            claim_uid,
            rationale="This quote backs the claim.",
            actor_id="t",
            actor_type="tool",
        )
        read_model = session.store.get_read_model()
        support = read_model.get_support_for_claim(claim_uid)
    assert len(support) == 1
    assert support[0].rationale == "This quote backs the claim."


def test_link_challenge_projection_and_defensibility_challenged(tmp_path: Path) -> None:
    """Challenge link is projected; get_defensibility_score returns provenance_quality challenged."""
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("Challenge", actor_id="t", actor_type="tool")
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
        _, claim_uid = session.propose_claim(inv_uid, "Claim.", actor_id="t", actor_type="tool")
        session.link_support(inv_uid, span_uid, claim_uid, actor_id="t", actor_type="tool")
        _, ev2 = session.ingest_evidence(
            inv_uid,
            b"Not X",
            "text/plain",
            original_filename="y.txt",
            actor_id="t",
            actor_type="tool",
        )
        _, span2 = session.anchor_span(
            inv_uid,
            ev2,
            "text_offset",
            {"start_char": 0, "end_char": 5},
            quote="Not X",
            actor_id="t",
            actor_type="tool",
        )
        session.link_challenge(inv_uid, span2, claim_uid, actor_id="t", actor_type="tool")
        scorecard = session.get_defensibility_score(claim_uid)
    assert scorecard is not None
    assert scorecard.provenance_quality == "challenged"


def test_list_claims_by_type_filter(tmp_path: Path) -> None:
    """list_claims_by_type with claim_type and investigation_uid returns only matching claims."""
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("Typed", actor_id="t", actor_type="tool")
        session.propose_claim(inv_uid, "Open claim.", actor_id="t", actor_type="tool")
        _, claim_uid_sef = session.propose_claim(
            inv_uid, "SEF claim.", initial_type="SEF", actor_id="t", actor_type="tool"
        )
        session.type_claim(claim_uid_sef, "SEF", workspace="forge")
        read_model = session.store.get_read_model()
        all_claims = read_model.list_claims_by_type(investigation_uid=inv_uid, limit=10)
        sef_claims = read_model.list_claims_by_type(
            investigation_uid=inv_uid, claim_type="SEF", limit=10
        )
    assert len(all_claims) >= 2
    assert len(sef_claims) >= 1
    assert all(c.claim_type == "SEF" for c in sef_claims)


def test_list_claims_by_type_include_withdrawn(tmp_path: Path) -> None:
    """list_claims_by_type(include_withdrawn=False) excludes WITHDRAWN claims."""
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("Withdraw", actor_id="t", actor_type="tool")
        _, claim_uid = session.propose_claim(
            inv_uid, "To withdraw.", actor_id="t", actor_type="tool"
        )
        session.withdraw_claim(
            claim_uid, "Retracting.", actor_id="t", actor_type="tool", workspace="forge"
        )
        read_model = session.store.get_read_model()
        with_withdrawn = read_model.list_claims_by_type(
            investigation_uid=inv_uid, limit=10, include_withdrawn=True
        )
        active_only = read_model.list_claims_by_type(
            investigation_uid=inv_uid, limit=10, include_withdrawn=False
        )
    assert any(c.claim_uid == claim_uid and c.current_status == "WITHDRAWN" for c in with_withdrawn)
    assert not any(c.claim_uid == claim_uid for c in active_only)


def test_list_claims_by_type_created_since(tmp_path: Path) -> None:
    """list_claims_by_type with created_since filters by created_at."""
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("Since", actor_id="t", actor_type="tool")
        _, claim_uid = session.propose_claim(inv_uid, "Claim.", actor_id="t", actor_type="tool")
        read_model = session.store.get_read_model()
        claim = read_model.get_claim(claim_uid)
        assert claim is not None
        created_at = claim.created_at
        # created_since up to claim time: should include this claim
        recent = read_model.list_claims_by_type(
            investigation_uid=inv_uid, limit=10, created_since=created_at
        )
        future = read_model.list_claims_by_type(
            investigation_uid=inv_uid, limit=10, created_since="2099-01-01T00:00:00Z"
        )
    assert any(c.claim_uid == claim_uid for c in recent)
    assert not any(c.claim_uid == claim_uid for c in future)


def test_get_defensibility_score_use_strength_weighting(tmp_path: Path) -> None:
    """get_defensibility_score with use_strength_weighting=True returns scorecard (strength-weighted path)."""
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("Strength", actor_id="t", actor_type="tool")
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
        session.link_support(
            inv_uid, span_uid, claim_uid, strength=0.8, actor_id="t", actor_type="tool"
        )
        read_model = session.store.get_read_model()
        scorecard = get_defensibility_score(read_model, claim_uid, use_strength_weighting=True)
    assert scorecard is not None
    assert scorecard.provenance_quality in ("strong", "medium", "weak", "challenged")


def test_get_defensibility_score_withdrawn_returns_none(tmp_path: Path) -> None:
    """get_defensibility_score for WITHDRAWN claim returns None."""
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("Withdrawn", actor_id="t", actor_type="tool")
        _, claim_uid = session.propose_claim(
            inv_uid, "Will withdraw.", actor_id="t", actor_type="tool"
        )
        session.withdraw_claim(
            claim_uid, "Retracting.", actor_id="t", actor_type="tool", workspace="forge"
        )
        read_model = session.store.get_read_model()
        scorecard = get_defensibility_score(read_model, claim_uid)
    assert scorecard is None


def test_type_claim_projection_updates_read_model(tmp_path: Path) -> None:
    """type_claim emits ClaimTyped; projection updates claim.claim_type."""
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("Type", actor_id="t", actor_type="tool")
        _, claim_uid = session.propose_claim(inv_uid, "Claim.", actor_id="t", actor_type="tool")
        session.type_claim(claim_uid, "SEF", workspace="forge")
        read_model = session.store.get_read_model()
        claim = read_model.get_claim(claim_uid)
    assert claim is not None
    assert claim.claim_type == "SEF"


def test_list_evidence_by_investigation(tmp_path: Path) -> None:
    """list_evidence_by_investigation returns evidence for the investigation."""
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("Ev", actor_id="t", actor_type="tool")
        session.ingest_evidence(
            inv_uid,
            b"One",
            "text/plain",
            original_filename="a.txt",
            actor_id="t",
            actor_type="tool",
        )
        session.ingest_evidence(
            inv_uid,
            b"Two",
            "text/plain",
            original_filename="b.txt",
            actor_id="t",
            actor_type="tool",
        )
        read_model = session.store.get_read_model()
        items = read_model.list_evidence_by_investigation(inv_uid)
    assert len(items) >= 2


def test_link_challenge_rejects_invalid_defeater_kind(tmp_path: Path) -> None:
    """link_challenge with defeater_kind not in (rebutting, undercutting) raises ChronicleUserError."""
    from chronicle.core.errors import ChronicleUserError

    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("Def", actor_id="t", actor_type="tool")
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
        with pytest.raises(ChronicleUserError, match="defeater_kind must be one of"):
            session.link_challenge(
                inv_uid,
                span_uid,
                claim_uid,
                defeater_kind="invalid",
                actor_id="t",
                actor_type="tool",
            )
        # Valid defeater_kind is accepted
        session.link_challenge(
            inv_uid, span_uid, claim_uid, defeater_kind="rebutting", actor_id="t", actor_type="tool"
        )


def test_declare_tension_rejects_invalid_defeater_kind(tmp_path: Path) -> None:
    """declare_tension with defeater_kind not in (rebutting, undercutting) raises ChronicleUserError."""
    from chronicle.core.errors import ChronicleUserError

    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("Ten", actor_id="t", actor_type="tool")
        _, c1 = session.propose_claim(inv_uid, "A", actor_id="t", actor_type="tool")
        _, c2 = session.propose_claim(inv_uid, "B", actor_id="t", actor_type="tool")
        session.set_tier(inv_uid, "forge", actor_id="t", actor_type="tool")
        with pytest.raises(ChronicleUserError, match="defeater_kind must be one of"):
            session.declare_tension(
                inv_uid, c1, c2, defeater_kind="invalid", actor_id="t", actor_type="tool"
            )
        session.declare_tension(
            inv_uid, c1, c2, defeater_kind="undercutting", actor_id="t", actor_type="tool"
        )
