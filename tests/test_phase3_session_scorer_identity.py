"""Phase 3 coverage: session export/import, get_reasoning_brief, scorer URL path, identity branches."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from chronicle.scorer_contract import run_scorer_contract
from chronicle.store.project import create_project
from chronicle.store.session import ChronicleSession

# ---- Session: export, import, get_reasoning_brief ----


def test_session_export_then_import_investigation(tmp_path: Path) -> None:
    """Export investigation to .chronicle; import into another project; data is present."""
    proj_a = tmp_path / "proj_a"
    proj_b = tmp_path / "proj_b"
    create_project(proj_a)
    create_project(proj_b)
    chronicle_file = tmp_path / "export.chronicle"

    with ChronicleSession(proj_a) as session:
        _, inv_uid = session.create_investigation("Export me", actor_id="t", actor_type="tool")
        session.ingest_evidence(
            inv_uid,
            b"Evidence",
            "text/plain",
            original_filename="e.txt",
            actor_id="t",
            actor_type="tool",
        )
        out = session.export_investigation(inv_uid, chronicle_file)
    assert out.is_file()
    assert out.suffix == ".chronicle"

    with ChronicleSession(proj_b) as session:
        session.import_investigation(chronicle_file)
        invs = session.store.get_read_model().list_investigations()
    imported = [i for i in invs if i.title == "Export me"]
    assert len(imported) >= 1


def test_session_get_reasoning_brief(tmp_path: Path) -> None:
    """get_reasoning_brief returns claim, defensibility, support/challenge, tensions."""
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("Brief", actor_id="t", actor_type="tool")
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
        brief = session.get_reasoning_brief(claim_uid)
    assert brief is not None
    assert "claim" in brief
    assert "defensibility" in brief
    assert brief.get("claim_uid") == claim_uid


def test_session_get_reasoning_brief_nonexistent_claim(tmp_path: Path) -> None:
    """get_reasoning_brief returns None for unknown claim_uid."""
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        brief = session.get_reasoning_brief("nonexistent-claim-uid")
    assert brief is None


# ---- Scorer contract: evidence with URL (mocked fetch) ----


def test_scorer_contract_evidence_url_fetch_mocked() -> None:
    """Evidence item with 'url' uses _fetch_url; mock returns content so contract succeeds."""
    with patch("chronicle.scorer_contract._fetch_url", return_value="Fetched content from URL."):
        result = run_scorer_contract(
            {
                "query": "Q?",
                "answer": "A.",
                "evidence": [{"url": "http://example.com/doc.txt"}],
            },
            allow_path=False,
        )
    assert "error" not in result or result.get("error") != "invalid_input"
    assert result.get("contract_version") == "1.0"
    assert "provenance_quality" in result or "claim_uid" in result


def test_scorer_contract_evidence_url_fetch_returns_none() -> None:
    """When _fetch_url returns None (unsafe/failed), no chunk from URL; contract can still succeed if another chunk exists."""
    with patch("chronicle.scorer_contract._fetch_url", return_value=None):
        result = run_scorer_contract(
            {
                "query": "Q?",
                "answer": "A.",
                "evidence": ["Inline text.", {"url": "http://unsafe/local"}],
            },
            allow_path=False,
        )
    assert result.get("contract_version") == "1.0"
    assert "provenance_quality" in result or "claim_uid" in result
