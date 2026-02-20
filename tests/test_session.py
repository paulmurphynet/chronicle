"""Minimal tests for ChronicleSession: ingest evidence, propose claim, link support, get_defensibility_score."""

from __future__ import annotations

from pathlib import Path

import pytest
from chronicle.core.errors import ChronicleUserError
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


def test_claimreview_export_profile(tmp_path: Path) -> None:
    """build_claimreview_export returns schema.org ClaimReview entries with mapped ratings."""
    from chronicle.store.commands.generic_export import build_claimreview_export

    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation(
            "ClaimReview export", actor_id="test", actor_type="tool"
        )
        _, ev_support = session.ingest_evidence(
            inv_uid,
            b"Support text",
            "text/plain",
            original_filename="support.txt",
            actor_id="test",
            actor_type="tool",
        )
        _, span_support = session.anchor_span(
            inv_uid,
            ev_support,
            "text_offset",
            {"start_char": 0, "end_char": 12},
            quote="Support text",
            actor_id="test",
            actor_type="tool",
        )
        _, ev_challenge = session.ingest_evidence(
            inv_uid,
            b"Challenge text",
            "text/plain",
            original_filename="challenge.txt",
            actor_id="test",
            actor_type="tool",
        )
        _, span_challenge = session.anchor_span(
            inv_uid,
            ev_challenge,
            "text_offset",
            {"start_char": 0, "end_char": 14},
            quote="Challenge text",
            actor_id="test",
            actor_type="tool",
        )
        _, claim_uid = session.propose_claim(
            inv_uid, "A disputed claim.", actor_id="test", actor_type="tool"
        )
        session.link_support(inv_uid, span_support, claim_uid, actor_id="test", actor_type="tool")
        session.link_challenge(inv_uid, span_challenge, claim_uid, actor_id="test", actor_type="tool")

        data = build_claimreview_export(
            session.read_model,
            session.get_defensibility_score,
            inv_uid,
            publisher_name="Chronicle Test Publisher",
        )

    assert data["schema_version"] == 1
    assert data["@context"] == "https://schema.org"
    assert data["@type"] == "ItemList"
    assert len(data["itemListElement"]) == 1
    review = data["itemListElement"][0]
    assert review["@type"] == "ClaimReview"
    assert review["itemReviewed"]["identifier"] == claim_uid
    assert review["author"]["name"] == "Chronicle Test Publisher"
    assert review["reviewRating"]["ratingValue"] == 1
    assert review["reviewRating"]["alternateName"] == "Challenged"
    assert isinstance(review.get("reviewBody"), str)


def test_ro_crate_export_profile(tmp_path: Path) -> None:
    """build_ro_crate_export returns RO-Crate-shaped metadata with Chronicle parts."""
    from chronicle.store.commands.generic_export import build_ro_crate_export

    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("RO-Crate export", actor_id="test", actor_type="tool")
        _, ev_uid = session.ingest_evidence(
            inv_uid,
            b"Evidence bytes",
            "text/plain",
            original_filename="evidence.txt",
            actor_id="test",
            actor_type="tool",
        )
        _, claim_uid = session.propose_claim(
            inv_uid, "A simple claim.", actor_id="test", actor_type="tool"
        )
        data = build_ro_crate_export(session.read_model, inv_uid)

    assert data["schema_version"] == 1
    assert data["@context"][0] == "https://w3id.org/ro/crate/1.2/context"

    graph = data["@graph"]
    assert isinstance(graph, list)
    dataset = next((n for n in graph if n.get("@id") == "./"), None)
    assert dataset is not None
    assert "Dataset" in dataset.get("@type", [])
    parts = dataset.get("hasPart", [])
    assert {"@id": "chronicle.db"} in parts
    assert {"@id": "manifest.json"} in parts
    assert {"@id": f"#claim:{claim_uid}"} in parts

    evidence_node = next((n for n in graph if n.get("identifier") == ev_uid), None)
    assert evidence_node is not None
    assert evidence_node.get("@type") == "File"
    assert evidence_node.get("encodingFormat") == "text/plain"


def test_c2pa_compatibility_export_profile(tmp_path: Path) -> None:
    """build_c2pa_compatibility_export exposes C2PA references from evidence metadata."""
    from chronicle.store.commands.generic_export import build_c2pa_compatibility_export

    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("C2PA export", actor_id="test", actor_type="tool")
        _, ev_uid = session.ingest_evidence(
            inv_uid,
            b"Image bytes placeholder",
            "image/jpeg",
            original_filename="photo.jpg",
            metadata={
                "c2pa_claim_id": "urn:uuid:claim-1",
                "c2pa_assertion_id": "assertion-1",
                "c2pa_manifest_digest": "sha256:abcd",
                "c2pa_verification_status": "verified",
            },
            actor_id="test",
            actor_type="tool",
        )
        disabled = build_c2pa_compatibility_export(session.read_model, inv_uid, verification_enabled=False)
        enabled = build_c2pa_compatibility_export(session.read_model, inv_uid, verification_enabled=True)

    assert disabled["schema_version"] == 1
    assert disabled["verification"]["enabled"] is False
    assert len(disabled["evidence_assertions"]) == 1
    disabled_entry = disabled["evidence_assertions"][0]
    assert disabled_entry["evidence_uid"] == ev_uid
    assert disabled_entry["metadata"]["c2pa_verification_status"] == "not_verified"

    assert enabled["verification"]["enabled"] is True
    enabled_entry = enabled["evidence_assertions"][0]
    assert enabled_entry["metadata"]["c2pa_verification_status"] == "verified"


def test_vc_data_integrity_export_profile(tmp_path: Path) -> None:
    """build_vc_data_integrity_export exposes claim/artifact/checkpoint attestation metadata."""
    from chronicle.store.commands.generic_export import build_vc_data_integrity_export

    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation(
            "VC export",
            actor_id="test",
            actor_type="tool",
        )
        _, claim_uid = session.propose_claim(
            inv_uid,
            "Attested claim",
            initial_type="SEF",
            actor_id="test",
            actor_type="tool",
            verification_level="verified_credential",
            attestation_ref="urn:vc:claim-1",
        )
        _, artifact_uid = session.create_artifact(
            inv_uid,
            "Attested report",
            actor_id="test",
            actor_type="tool",
            workspace="forge",
            verification_level="verified_credential",
            attestation_ref="urn:vc:artifact-1",
        )
        _, checkpoint_uid = session.create_checkpoint(
            inv_uid,
            [claim_uid],
            artifact_refs=[artifact_uid],
            reason="Attested checkpoint",
            actor_id="test",
            actor_type="tool",
            workspace="vault",
            verification_level="claimed",
            attestation_ref="urn:vc:checkpoint-1",
        )
        disabled = build_vc_data_integrity_export(
            session.read_model,
            inv_uid,
            verification_enabled=False,
        )
        enabled = build_vc_data_integrity_export(
            session.read_model,
            inv_uid,
            verification_enabled=True,
        )

    assert disabled["schema_version"] == 1
    assert disabled["verification"]["enabled"] is False
    disabled_claim = next(
        x for x in disabled["attestations"]["claims"] if x["claim_uid"] == claim_uid
    )
    assert disabled_claim["attestation"]["verification_status"] == "not_verified"

    assert enabled["verification"]["enabled"] is True
    claim_entry = next(x for x in enabled["attestations"]["claims"] if x["claim_uid"] == claim_uid)
    assert claim_entry["attestation"]["verification_status"] == "verified"
    assert claim_entry["attestation"]["attestation_ref"] == "urn:vc:claim-1"

    artifact_entry = next(
        x for x in enabled["attestations"]["artifacts"] if x["artifact_uid"] == artifact_uid
    )
    assert artifact_entry["attestation"]["verification_status"] == "verified"
    assert artifact_entry["attestation"]["attestation_ref"] == "urn:vc:artifact-1"

    checkpoint_entry = next(
        x
        for x in enabled["attestations"]["checkpoints"]
        if x["checkpoint_uid"] == checkpoint_uid
    )
    assert checkpoint_entry["attestation"]["verification_status"] == "not_verified"
    assert checkpoint_entry["attestation"]["attestation_ref"] == "urn:vc:checkpoint-1"


def test_standards_jsonld_export_profile(tmp_path: Path) -> None:
    """build_standards_jsonld_export includes claims, links, tensions, and source relations."""
    from chronicle.store.commands.generic_export import (
        build_standards_jsonld_export,
        validate_standards_jsonld_export,
    )

    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("JSON-LD export", actor_id="t", actor_type="tool")
        _, ev_support = session.ingest_evidence(
            inv_uid,
            b"Primary support evidence.",
            "text/plain",
            original_filename="support.txt",
            actor_id="t",
            actor_type="tool",
        )
        _, span_support = session.anchor_span(
            inv_uid,
            ev_support,
            "text_offset",
            {"start_char": 0, "end_char": 24},
            quote="Primary support evidence.",
            actor_id="t",
            actor_type="tool",
        )
        _, ev_challenge = session.ingest_evidence(
            inv_uid,
            b"Conflicting evidence snippet.",
            "text/plain",
            original_filename="challenge.txt",
            actor_id="t",
            actor_type="tool",
        )
        _, span_challenge = session.anchor_span(
            inv_uid,
            ev_challenge,
            "text_offset",
            {"start_char": 0, "end_char": 28},
            quote="Conflicting evidence snippet.",
            actor_id="t",
            actor_type="tool",
        )
        _, claim_uid = session.propose_claim(
            inv_uid,
            "The event happened at noon.",
            actor_id="t",
            actor_type="tool",
        )
        _, other_claim_uid = session.propose_claim(
            inv_uid,
            "The event happened at midnight.",
            actor_id="t",
            actor_type="tool",
        )
        session.link_support(inv_uid, span_support, claim_uid, actor_id="t", actor_type="tool")
        session.link_challenge(inv_uid, span_challenge, claim_uid, actor_id="t", actor_type="tool")
        session.set_tier(inv_uid, "forge", actor_id="t", actor_type="tool")
        _, source_uid = session.register_source(
            inv_uid,
            "Primary Witness",
            "person",
            actor_id="t",
            actor_type="tool",
            workspace="forge",
        )
        session.link_evidence_to_source(
            ev_support,
            source_uid,
            relationship="provided_by",
            actor_id="t",
            actor_type="tool",
            workspace="forge",
        )
        session.declare_tension(
            inv_uid,
            claim_uid,
            other_claim_uid,
            actor_id="t",
            actor_type="tool",
            workspace="forge",
        )

        data = build_standards_jsonld_export(session.read_model, inv_uid)

    assert data["schema_version"] == 1
    assert data["chronicle_context_version"] == 1
    assert "prov" in data["@context"]
    assert data["@type"] == ["prov:Bundle", "chronicle:InvestigationBundle"]

    graph = data["@graph"]
    assert isinstance(graph, list)
    assert len(graph) > 0

    claim_id = f"urn:chronicle:claim:{claim_uid}"
    source_id = f"urn:chronicle:source:{source_uid}"
    support_evidence_id = f"urn:chronicle:evidence:{ev_support}"

    claim_node = next((n for n in graph if n.get("@id") == claim_id), None)
    assert claim_node is not None
    assert "chronicle:Claim" in claim_node.get("@type", [])
    assert claim_node.get("prov:wasDerivedFrom") == [{"@id": support_evidence_id}]

    support_link_nodes = [
        n
        for n in graph
        if "chronicle:EvidenceLink" in n.get("@type", [])
        and n.get("chronicle:linkType") == "SUPPORT"
    ]
    challenge_link_nodes = [
        n
        for n in graph
        if "chronicle:EvidenceLink" in n.get("@type", [])
        and n.get("chronicle:linkType") == "CHALLENGE"
    ]
    assert len(support_link_nodes) == 1
    assert len(challenge_link_nodes) == 1

    source_node = next((n for n in graph if n.get("@id") == source_id), None)
    assert source_node is not None
    assert "chronicle:Source" in source_node.get("@type", [])

    evidence_source_nodes = [
        n for n in graph if "chronicle:EvidenceSourceLink" in n.get("@type", [])
    ]
    assert len(evidence_source_nodes) == 1
    assert evidence_source_nodes[0].get("prov:agent") == {"@id": source_id}

    tension_nodes = [n for n in graph if "chronicle:Tension" in n.get("@type", [])]
    assert len(tension_nodes) == 1
    assert tension_nodes[0].get("chronicle:claimA") == {"@id": claim_id}
    assert tension_nodes[0].get("chronicle:claimB") == {
        "@id": f"urn:chronicle:claim:{other_claim_uid}"
    }
    assert validate_standards_jsonld_export(data) == []


def test_standards_jsonld_export_validator_detects_missing_reference(tmp_path: Path) -> None:
    """Validator reports missing references in PROV-required relation fields."""
    from chronicle.store.commands.generic_export import (
        build_standards_jsonld_export,
        validate_standards_jsonld_export,
    )

    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation(
            "JSON-LD validation", actor_id="t", actor_type="tool"
        )
        _, ev_uid = session.ingest_evidence(
            inv_uid,
            b"Supporting evidence.",
            "text/plain",
            original_filename="support.txt",
            actor_id="t",
            actor_type="tool",
        )
        _, span_uid = session.anchor_span(
            inv_uid,
            ev_uid,
            "text_offset",
            {"start_char": 0, "end_char": 20},
            quote="Supporting evidence.",
            actor_id="t",
            actor_type="tool",
        )
        _, claim_uid = session.propose_claim(
            inv_uid, "Claim text.", actor_id="t", actor_type="tool"
        )
        session.link_support(inv_uid, span_uid, claim_uid, actor_id="t", actor_type="tool")
        payload = build_standards_jsonld_export(session.read_model, inv_uid)

    graph = payload.get("@graph")
    assert isinstance(graph, list)
    broken_graph = [
        node
        for node in graph
        if not (isinstance(node, dict) and node.get("@id") == f"urn:chronicle:evidence:{ev_uid}")
    ]
    broken = dict(payload)
    broken["@graph"] = broken_graph

    errors = validate_standards_jsonld_export(broken)
    assert any("references missing node" in err for err in errors)


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


def test_session_policy_sensitivity_report(tmp_path: Path) -> None:
    """R2-01: session policy sensitivity report includes per-profile and pairwise claim deltas."""
    create_project(tmp_path)

    base = default_policy_profile().to_dict()
    base["profile_id"] = "policy_permissive_test"
    base["display_name"] = "Permissive test profile"
    base["mes_rules"][0]["min_independent_sources"] = 0
    permissive_profile = PolicyProfile.from_dict(base)
    import_policy_to_project(tmp_path, permissive_profile, activate=False)

    strict = default_policy_profile().to_dict()
    strict["profile_id"] = "policy_strict_test"
    strict["display_name"] = "Strict test profile"
    strict["mes_rules"][0]["min_independent_sources"] = 2
    strict_profile = PolicyProfile.from_dict(strict)
    import_policy_to_project(tmp_path, strict_profile, activate=False)

    text = b"A source reported a key timeline detail."
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation(
            "Policy sensitivity session test",
            actor_id="tester",
            actor_type="tool",
        )
        _, ev_uid = session.ingest_evidence(
            inv_uid,
            text,
            "text/plain",
            original_filename="note.txt",
            actor_id="tester",
            actor_type="tool",
        )
        _, span_uid = session.anchor_span(
            inv_uid,
            ev_uid,
            "text_offset",
            {"start_char": 0, "end_char": len(text.decode("utf-8"))},
            quote=text.decode("utf-8"),
            actor_id="tester",
            actor_type="tool",
        )
        _, claim_uid = session.propose_claim(
            inv_uid,
            "The timeline detail is accurate.",
            actor_id="tester",
            actor_type="tool",
        )
        session.link_support(
            inv_uid,
            span_uid,
            claim_uid,
            actor_id="tester",
            actor_type="tool",
        )
        report = session.get_policy_sensitivity_report(
            inv_uid,
            profile_ids=["policy_permissive_test", "policy_strict_test"],
            built_under_profile_id="policy_permissive_test",
            limit_claims=100,
        )

    assert report["investigation_uid"] == inv_uid
    assert [p["profile_id"] for p in report["selected_profiles"]] == [
        "policy_permissive_test",
        "policy_strict_test",
    ]
    assert any(c["claim_uid"] == claim_uid for c in report["claim_comparison"])
    assert len(report["pairwise_deltas"]) == 1
    pair = report["pairwise_deltas"][0]
    assert pair["summary"]["changed_count"] >= 1
    assert pair["summary"]["strong_to_weak_count"] >= 1
    assert any(
        item.get("kind") == "profile_outcome_shift"
        for item in report.get("practical_review_implications", [])
    )


def test_session_temporal_uncertainty_knowability_fields(tmp_path: Path) -> None:
    """Defensibility knowability includes temporal range and confidence when temporalized."""
    from chronicle.eval_metrics import defensibility_metrics_for_claim

    create_project(tmp_path)
    text = b"Bridge completion records vary by source."
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation(
            "Temporal uncertainty test",
            actor_id="tester",
            actor_type="tool",
        )
        _, ev_uid = session.ingest_evidence(
            inv_uid,
            text,
            "text/plain",
            original_filename="history.txt",
            actor_id="tester",
            actor_type="tool",
        )
        _, span_uid = session.anchor_span(
            inv_uid,
            ev_uid,
            "text_offset",
            {"start_char": 0, "end_char": len(text.decode("utf-8"))},
            quote=text.decode("utf-8"),
            actor_id="tester",
            actor_type="tool",
        )
        _, claim_uid = session.propose_claim(
            inv_uid,
            "Bridge was completed in the early 1860s.",
            actor_id="tester",
            actor_type="tool",
        )
        session.link_support(
            inv_uid,
            span_uid,
            claim_uid,
            actor_id="tester",
            actor_type="tool",
        )
        session.temporalize_claim(
            claim_uid,
            {
                "known_as_of": "1865-01-01",
                "known_range_start": "1862-01-01",
                "known_range_end": "1864-12-31",
                "temporal_confidence": 0.82,
                "knowable_from": "archival letter + newspaper digest",
            },
            actor_id="tester",
            actor_type="human",
            workspace="forge",
        )
        scorecard = session.get_defensibility_score(claim_uid)
        metrics = defensibility_metrics_for_claim(session, claim_uid)

    assert scorecard is not None
    knowability = scorecard.knowability
    assert knowability.get("known_as_of") == "1865-01-01"
    assert knowability.get("known_range_start") == "1862-01-01"
    assert knowability.get("known_range_end") == "1864-12-31"
    assert knowability.get("temporal_confidence") == 0.82
    assert knowability.get("knowable_from") == "archival letter + newspaper digest"
    assert metrics is not None
    assert metrics.get("knowability", {}).get("temporal_confidence") == 0.82


def test_session_temporalize_claim_rejects_invalid_uncertainty_fields(tmp_path: Path) -> None:
    """Temporalize claim validates temporal_confidence and temporal range ordering."""
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation(
            "Temporal validation test",
            actor_id="tester",
            actor_type="tool",
        )
        _, claim_uid = session.propose_claim(
            inv_uid,
            "Test claim.",
            actor_id="tester",
            actor_type="tool",
        )
        with pytest.raises(ChronicleUserError, match="temporal_confidence must be between 0 and 1"):
            session.temporalize_claim(
                claim_uid,
                {"temporal_confidence": 1.5},
                actor_id="tester",
                actor_type="human",
                workspace="forge",
            )
        with pytest.raises(ChronicleUserError, match="known_range_start must be <= known_range_end"):
            session.temporalize_claim(
                claim_uid,
                {"known_range_start": "2025-01-02", "known_range_end": "2025-01-01"},
                actor_id="tester",
                actor_type="human",
                workspace="forge",
            )


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
