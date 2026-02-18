"""Phase 5 coverage: export_import edge cases, import into fresh target, defensibility with policy."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from chronicle.store.commands.claims import get_defensibility_score
from chronicle.store.export_import import export_investigation, import_investigation
from chronicle.store.project import create_project
from chronicle.store.session import ChronicleSession


def test_export_investigation_nonexistent_investigation_raises(tmp_path: Path) -> None:
    """export_investigation raises when the investigation has no events."""
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        session.create_investigation("Only one", actor_id="t", actor_type="tool")
    out = tmp_path / "out.chronicle"
    with pytest.raises(ValueError, match="No events found"):
        export_investigation(tmp_path, "nonexistent-inv-uid", out)


def test_import_investigation_fresh_target(tmp_path: Path) -> None:
    """import_investigation into empty dir (no chronicle.db) does fresh extract."""
    proj_a = tmp_path / "proj_a"
    fresh = tmp_path / "fresh"
    create_project(proj_a)
    chronicle_file = tmp_path / "export.chronicle"

    with ChronicleSession(proj_a) as session:
        _, inv_uid = session.create_investigation("Fresh import", actor_id="t", actor_type="tool")
        session.ingest_evidence(
            inv_uid, b"X", "text/plain", original_filename="x.txt", actor_id="t", actor_type="tool"
        )
        session.export_investigation(inv_uid, chronicle_file)

    fresh.mkdir(parents=True)
    assert not (fresh / "chronicle.db").exists()
    import_investigation(chronicle_file, fresh)
    assert (fresh / "chronicle.db").is_file()
    assert (fresh / "manifest.json").is_file()


def test_import_investigation_invalid_manifest_missing_uid(tmp_path: Path) -> None:
    """import_investigation raises when manifest lacks investigation_uid."""
    bad_chronicle = tmp_path / "bad.chronicle"
    with zipfile.ZipFile(bad_chronicle, "w") as zf:
        zf.writestr("manifest.json", json.dumps({"format_version": 1}))
    target = tmp_path / "target"
    target.mkdir()
    create_project(target)
    with pytest.raises(ValueError, match="missing investigation_uid"):
        import_investigation(bad_chronicle, target)


def test_get_defensibility_score_with_policy_profile_none(tmp_path: Path) -> None:
    """get_defensibility_score with policy_profile=None still returns scorecard (same as no policy)."""
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("P", actor_id="t", actor_type="tool")
        _, ev_uid = session.ingest_evidence(
            inv_uid, b"E", "text/plain", original_filename="e.txt", actor_id="t", actor_type="tool"
        )
        _, span_uid = session.anchor_span(
            inv_uid, ev_uid, "text_offset", {"start_char": 0, "end_char": 1}, quote="E", actor_id="t", actor_type="tool"
        )
        _, claim_uid = session.propose_claim(inv_uid, "C.", actor_id="t", actor_type="tool")
        session.link_support(inv_uid, span_uid, claim_uid, actor_id="t", actor_type="tool")

        read_model = session.store.get_read_model()
        scorecard = get_defensibility_score(read_model, claim_uid, policy_profile=None)
    assert scorecard is not None
    assert scorecard.provenance_quality in ("strong", "medium", "weak", "challenged")


def test_export_investigation_output_suffix_normalized(tmp_path: Path) -> None:
    """export_investigation adds .chronicle suffix if output_path has different extension."""
    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("Suffix", actor_id="t", actor_type="tool")
        out = tmp_path / "out.zip"
        result = session.export_investigation(inv_uid, out)
    assert result.suffix == ".chronicle"
    assert result.name == "out.chronicle"
    assert result.is_file()
