from __future__ import annotations

from pathlib import Path

import pytest
from chronicle.core.errors import ChronicleUserError
from chronicle.mcp.service import ChronicleMcpService


def test_mcp_service_end_to_end(tmp_path: Path) -> None:
    service = ChronicleMcpService(tmp_path / "project")

    created = service.create_investigation(title="MCP Investigation")
    investigation_uid = created["investigation_uid"]
    assert investigation_uid

    investigations = service.list_investigations(limit=10)
    assert investigations["count"] >= 1
    assert any(row["investigation_uid"] == investigation_uid for row in investigations["items"])

    ingested = service.ingest_evidence_text(
        investigation_uid=investigation_uid,
        text="Quarter-close adjustments changed recognition timing for INV-204.",
        original_filename="ledger.txt",
    )
    span_uid = ingested["span_uid"]
    assert span_uid

    claim = service.propose_claim(
        investigation_uid=investigation_uid,
        claim_text="Revenue timing for INV-204 requires exception tracking.",
    )
    claim_uid = claim["claim_uid"]
    assert claim_uid

    claims = service.list_claims(investigation_uid=investigation_uid)
    assert claims["count"] >= 1
    assert any(row["claim_uid"] == claim_uid for row in claims["items"])

    linked = service.link_support(
        investigation_uid=investigation_uid,
        span_uid=span_uid,
        claim_uid=claim_uid,
        rationale="Ledger entry supports policy-sensitive timing.",
    )
    assert linked["link_uid"]

    score = service.get_defensibility(claim_uid=claim_uid)
    assert score is not None
    assert (score["corroboration"] or {}).get("support_count", 0) >= 1

    brief = service.get_reasoning_brief(claim_uid=claim_uid)
    assert brief is not None
    assert brief.get("claim_uid") == claim_uid

    exported = service.export_investigation(
        investigation_uid=investigation_uid,
        output_path="exports/mcp_test.chronicle",
    )
    export_path = Path(exported["output_path"])
    assert export_path.is_file()
    assert export_path.suffix == ".chronicle"
    assert exported["size_bytes"] > 0


def test_mcp_service_rejects_empty_text(tmp_path: Path) -> None:
    service = ChronicleMcpService(tmp_path / "project")
    created = service.create_investigation(title="MCP Empty Text")

    with pytest.raises(ChronicleUserError):
        service.ingest_evidence_text(
            investigation_uid=created["investigation_uid"],
            text="   ",
        )
