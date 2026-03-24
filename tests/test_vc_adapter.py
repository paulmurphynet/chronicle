from __future__ import annotations

from importlib import import_module
from pathlib import Path

from chronicle.store.project import create_project
from chronicle.store.session import ChronicleSession

c2_adapter = import_module("scripts.adapters.vc_to_chronicle")


def test_vc_adapter_records_claim_and_artifact_attestation(tmp_path: Path) -> None:
    create_project(tmp_path)
    payload = {
        "attestations": [
            {
                "target_type": "claim",
                "claim_text": "An attested claim",
                "claim_type": "SEF",
                "verification_level": "verified_credential",
                "attestation_ref": "urn:vc:claim-1",
            },
            {
                "target_type": "artifact",
                "title": "Attested packet",
                "artifact_type": "report",
                "verification_level": "verified_credential",
                "attestation_ref": "urn:vc:artifact-1",
            },
        ]
    }
    result = c2_adapter.run_one(payload, tmp_path)
    assert result.get("error") is None
    assert result.get("claims_created") == 1
    assert result.get("artifacts_created") == 1
    assert result.get("checkpoints_created") == 0

    inv_uid = result["investigation_uid"]
    with ChronicleSession(tmp_path) as session:
        claims = session.read_model.list_claims_by_type(investigation_uid=inv_uid, limit=10)
        artifacts = session.read_model.list_artifacts_by_investigation(inv_uid)
        events = session.get_investigation_event_history(inv_uid, limit=200)

    assert len(claims) == 1
    assert len(artifacts) == 1

    claim_event = next(
        e
        for e in events
        if e.get("subject_uid") == claims[0].claim_uid and e.get("event_type") == "ClaimProposed"
    )
    assert claim_event["payload"].get("_verification_level") == "verified_credential"
    assert claim_event["payload"].get("_attestation_ref") == "urn:vc:claim-1"

    artifact_event = next(
        e
        for e in events
        if e.get("subject_uid") == artifacts[0].artifact_uid
        and e.get("event_type") == "ArtifactCreated"
    )
    assert artifact_event["payload"].get("_verification_level") == "verified_credential"
    assert artifact_event["payload"].get("_attestation_ref") == "urn:vc:artifact-1"


def test_vc_adapter_records_checkpoint_attestation(tmp_path: Path) -> None:
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("VC checkpoint", actor_id="t", actor_type="tool")
        _, claim_uid = session.propose_claim(
            inv_uid, "Scope claim", actor_id="t", actor_type="tool"
        )

    payload = {
        "investigation_uid": inv_uid,
        "attestations": [
            {
                "target_type": "checkpoint",
                "scope_refs": [claim_uid],
                "reason": "Attested checkpoint",
                "verification_level": "claimed",
                "attestation_ref": "urn:vc:checkpoint-1",
            }
        ],
    }
    result = c2_adapter.run_one(payload, tmp_path)
    assert result.get("error") is None
    assert result.get("checkpoints_created") == 1

    with ChronicleSession(tmp_path) as session:
        checkpoints = session.read_model.list_checkpoints(inv_uid, limit=10)
        events = session.get_investigation_event_history(inv_uid, limit=200)

    assert len(checkpoints) == 1
    checkpoint_event = next(
        e
        for e in events
        if e.get("subject_uid") == checkpoints[0].checkpoint_uid
        and e.get("event_type") == "CheckpointCreated"
    )
    assert checkpoint_event["payload"].get("_verification_level") == "claimed"
    assert checkpoint_event["payload"].get("_attestation_ref") == "urn:vc:checkpoint-1"
