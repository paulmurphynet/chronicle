from __future__ import annotations

import json
import sys
from importlib import import_module
from pathlib import Path

from chronicle.store.project import create_project
from chronicle.store.session import ChronicleSession

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

c2pa_adapter = import_module("scripts.adapters.c2pa_to_chronicle")


def test_c2pa_adapter_run_one_records_metadata(tmp_path: Path) -> None:
    create_project(tmp_path)
    payload = {
        "assertions": [
            {
                "source_display_name": "Camera A",
                "source_type": "document",
                "evidence_content": "binary-placeholder",
                "evidence_media_type": "image/jpeg",
                "evidence_filename": "frame.jpg",
                "c2pa_claim_id": "urn:uuid:claim-123",
                "c2pa_assertion_id": "assertion-123",
                "c2pa_manifest_digest": "sha256:ffff",
                "c2pa_verification_status": "verified",
            }
        ]
    }
    result = c2pa_adapter.run_one(payload, tmp_path)
    assert result.get("error") is None
    assert result.get("c2pa_assertions_recorded") == 1

    inv_uid = result["investigation_uid"]
    with ChronicleSession(tmp_path) as session:
        evidence = session.read_model.list_evidence_by_investigation(inv_uid)
    assert len(evidence) == 1
    metadata = json.loads(evidence[0].metadata_json or "{}")
    assert metadata.get("c2pa_claim_id") == "urn:uuid:claim-123"
    assert metadata.get("c2pa_assertion_id") == "assertion-123"
    assert metadata.get("c2pa_manifest_digest") == "sha256:ffff"
    assert metadata.get("c2pa_verification_status") == "verified"
    assert metadata.get("c2pa_recording_mode") == "metadata_only"


def test_c2pa_adapter_defaults_status_not_verified(tmp_path: Path) -> None:
    create_project(tmp_path)
    payload = {
        "assertions": [
            {
                "source_display_name": "Camera B",
                "source_type": "document",
                "evidence_content": "binary-placeholder",
                "evidence_media_type": "image/jpeg",
                "evidence_filename": "frame2.jpg",
                "c2pa_claim_id": "urn:uuid:claim-456",
            }
        ]
    }
    result = c2pa_adapter.run_one(payload, tmp_path)
    assert result.get("error") is None

    inv_uid = result["investigation_uid"]
    with ChronicleSession(tmp_path) as session:
        evidence = session.read_model.list_evidence_by_investigation(inv_uid)
    metadata = json.loads(evidence[0].metadata_json or "{}")
    assert metadata.get("c2pa_verification_status") == "not_verified"
