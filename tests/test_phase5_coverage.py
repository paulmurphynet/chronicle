"""Phase 5 coverage: export_import edge cases, import into fresh target, defensibility with policy."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import chronicle.store.export_import as export_import_mod
import pytest
from chronicle.store.commands.claims import get_defensibility_score
from chronicle.store.export_import import (
    export_investigation,
    export_signed_investigation_bundle,
    import_investigation,
    import_signed_investigation_bundle,
    verify_signed_investigation_bundle,
)
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
    """import_investigation blocks archive when manifest is invalid."""
    bad_chronicle = tmp_path / "bad.chronicle"
    with zipfile.ZipFile(bad_chronicle, "w") as zf:
        zf.writestr("manifest.json", json.dumps({"format_version": 1}))
    target = tmp_path / "target"
    target.mkdir()
    create_project(target)
    with pytest.raises(ValueError, match="verification failed"):
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


def test_get_defensibility_score_with_policy_mes(tmp_path: Path) -> None:
    """get_defensibility_score with policy that has MES rules returns scorecard; policy affects readiness."""
    from chronicle.core.policy import PolicyProfile

    create_project(tmp_path)
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("MES", actor_id="t", actor_type="tool")
        _, ev_uid = session.ingest_evidence(
            inv_uid, b"E", "text/plain", original_filename="e.txt", actor_id="t", actor_type="tool"
        )
        _, span_uid = session.anchor_span(
            inv_uid, ev_uid, "text_offset", {"start_char": 0, "end_char": 1}, quote="E", actor_id="t", actor_type="tool"
        )
        _, claim_uid = session.propose_claim(inv_uid, "C.", initial_type="SEF", actor_id="t", actor_type="tool")
        session.link_support(inv_uid, span_uid, claim_uid, actor_id="t", actor_type="tool")
        read_model = session.store.get_read_model()
        profile = PolicyProfile(profile_id="test", display_name="Test")
        scorecard = get_defensibility_score(read_model, claim_uid, policy_profile=profile)
    assert scorecard is not None
    assert scorecard.claim_uid == claim_uid


def test_import_investigation_merge_into_existing(tmp_path: Path) -> None:
    """import_investigation into a project that already has chronicle.db merges (append) events."""
    proj_a = tmp_path / "proj_a"
    proj_b = tmp_path / "proj_b"
    create_project(proj_a)
    create_project(proj_b)
    chronicle_file = tmp_path / "export.chronicle"
    with ChronicleSession(proj_a) as session:
        _, inv_uid = session.create_investigation("Export", actor_id="t", actor_type="tool")
        session.ingest_evidence(inv_uid, b"Content", "text/plain", original_filename="c.txt", actor_id="t", actor_type="tool")
        session.export_investigation(inv_uid, chronicle_file)
    with ChronicleSession(proj_b) as session:
        session.create_investigation("Existing", actor_id="t", actor_type="tool")
    import_investigation(chronicle_file, proj_b)
    with ChronicleSession(proj_b) as session:
        invs = session.read_model.list_investigations(limit=10)
    assert len(invs) >= 2


def test_import_investigation_merge_skips_duplicates_and_keeps_new_events(tmp_path: Path) -> None:
    """Merge import should skip duplicate events per-event and still replay new events."""
    proj_a = tmp_path / "proj_a"
    proj_b = tmp_path / "proj_b"
    create_project(proj_a)
    create_project(proj_b)
    chronicle_v1 = tmp_path / "export_v1.chronicle"
    chronicle_v2 = tmp_path / "export_v2.chronicle"

    with ChronicleSession(proj_a) as session:
        _, inv_uid = session.create_investigation("Export", actor_id="t", actor_type="tool")
        session.ingest_evidence(
            inv_uid,
            b"One",
            "text/plain",
            original_filename="one.txt",
            actor_id="t",
            actor_type="tool",
        )
        session.export_investigation(inv_uid, chronicle_v1)
        session.ingest_evidence(
            inv_uid,
            b"Two",
            "text/plain",
            original_filename="two.txt",
            actor_id="t",
            actor_type="tool",
        )
        session.export_investigation(inv_uid, chronicle_v2)

    import_investigation(chronicle_v1, proj_b)
    import_investigation(chronicle_v2, proj_b)

    with ChronicleSession(proj_b) as session:
        evidence = session.read_model.list_evidence_by_investigation(inv_uid, limit=20)
    assert len(evidence) == 2


def test_import_investigation_rejects_tampered_archive(tmp_path: Path) -> None:
    """Import blocks when evidence bytes in archive no longer match recorded content hash."""
    proj = tmp_path / "proj"
    create_project(proj)
    exported = tmp_path / "export.chronicle"
    tampered = tmp_path / "tampered.chronicle"
    with ChronicleSession(proj) as session:
        _, inv_uid = session.create_investigation("Tamper", actor_id="t", actor_type="tool")
        session.ingest_evidence(
            inv_uid,
            b"Original bytes",
            "text/plain",
            original_filename="original.txt",
            actor_id="t",
            actor_type="tool",
        )
        session.export_investigation(inv_uid, exported)

    with zipfile.ZipFile(exported, "r") as zin:
        names = zin.namelist()
        blobs = {name: zin.read(name) for name in names}
    for name in list(blobs):
        if name.startswith("evidence/"):
            blobs[name] = b"TAMPERED bytes"
    with zipfile.ZipFile(tampered, "w", zipfile.ZIP_DEFLATED) as zout:
        for name in names:
            zout.writestr(name, blobs[name])

    target = tmp_path / "target"
    target.mkdir(parents=True)
    with pytest.raises(ValueError, match="verification failed"):
        import_investigation(tampered, target)


def test_import_investigation_rejects_unexpected_archive_entries(tmp_path: Path) -> None:
    """Import should reject archives that contain files outside Chronicle contract paths."""
    proj = tmp_path / "proj"
    create_project(proj)
    exported = tmp_path / "export.chronicle"
    with_extra = tmp_path / "with-extra.chronicle"
    with ChronicleSession(proj) as session:
        _, inv_uid = session.create_investigation("Unexpected entry", actor_id="t", actor_type="tool")
        session.ingest_evidence(
            inv_uid,
            b"Bytes",
            "text/plain",
            original_filename="bytes.txt",
            actor_id="t",
            actor_type="tool",
        )
        session.export_investigation(inv_uid, exported)

    with zipfile.ZipFile(exported, "r") as zin, zipfile.ZipFile(with_extra, "w", zipfile.ZIP_DEFLATED) as zout:
        for name in zin.namelist():
            zout.writestr(name, zin.read(name))
        zout.writestr("extras/unexpected.txt", b"unexpected")

    target = tmp_path / "target"
    target.mkdir(parents=True)
    with pytest.raises(ValueError, match="unexpected archive entries"):
        import_investigation(with_extra, target)


def test_import_investigation_enforces_archive_entry_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Import should fail when archive entry count exceeds configured safety limit."""
    proj = tmp_path / "proj"
    create_project(proj)
    exported = tmp_path / "export.chronicle"
    with ChronicleSession(proj) as session:
        _, inv_uid = session.create_investigation("Archive limit", actor_id="t", actor_type="tool")
        session.ingest_evidence(
            inv_uid,
            b"Bytes",
            "text/plain",
            original_filename="bytes.txt",
            actor_id="t",
            actor_type="tool",
        )
        session.export_investigation(inv_uid, exported)

    monkeypatch.setattr(export_import_mod, "MAX_IMPORT_ARCHIVE_ENTRIES", 1)
    target = tmp_path / "target"
    target.mkdir(parents=True)
    with pytest.raises(ValueError, match="too many entries"):
        import_investigation(exported, target)


def test_import_investigation_blocks_merge_when_existing_evidence_differs(tmp_path: Path) -> None:
    """Merge import blocks if target already has same evidence path with different bytes."""
    source = tmp_path / "source"
    target = tmp_path / "target"
    exported = tmp_path / "export.chronicle"
    create_project(source)
    create_project(target)
    with ChronicleSession(source) as session:
        _, inv_uid = session.create_investigation("Conflict", actor_id="t", actor_type="tool")
        session.ingest_evidence(
            inv_uid,
            b"Canonical bytes",
            "text/plain",
            original_filename="canonical.txt",
            actor_id="t",
            actor_type="tool",
        )
        session.export_investigation(inv_uid, exported)

    import_investigation(exported, target)
    evidence_files = list((target / "evidence").glob("*"))
    assert evidence_files
    evidence_files[0].write_bytes(b"Locally modified bytes")

    with pytest.raises(ValueError, match="evidence file conflict"):
        import_investigation(exported, target)


def test_signed_bundle_export_and_import_roundtrip(tmp_path: Path) -> None:
    """Signed bundle flow should preserve importability and digest integrity checks."""
    source = tmp_path / "source"
    target = tmp_path / "target"
    create_project(source)
    create_project(target)
    signed_bundle = tmp_path / "investigation_signed.zip"

    with ChronicleSession(source) as session:
        _, inv_uid = session.create_investigation("Signed export", actor_id="t", actor_type="tool")
        session.ingest_evidence(
            inv_uid,
            b"Signed evidence bytes",
            "text/plain",
            original_filename="signed.txt",
            actor_id="t",
            actor_type="tool",
        )

    out = export_signed_investigation_bundle(source, inv_uid, signed_bundle, signer="contract-test")
    assert out.is_file()
    manifest = verify_signed_investigation_bundle(out)
    assert manifest["investigation_uid"] == inv_uid
    assert manifest["signature"]["signer"] == "contract-test"
    assert manifest["signature"]["status"] == "metadata_only"

    import_signed_investigation_bundle(out, target)
    with ChronicleSession(target) as session:
        investigations = session.read_model.list_investigations(limit=10)
    assert any(i.investigation_uid == inv_uid for i in investigations)


def test_signed_bundle_import_rejects_digest_mismatch(tmp_path: Path) -> None:
    """Signed bundle import should fail when nested archive bytes do not match declared digest."""
    source = tmp_path / "source"
    target = tmp_path / "target"
    create_project(source)
    create_project(target)
    signed_bundle = tmp_path / "investigation_signed.zip"
    tampered_bundle = tmp_path / "investigation_signed_tampered.zip"

    with ChronicleSession(source) as session:
        _, inv_uid = session.create_investigation("Signed tamper", actor_id="t", actor_type="tool")
        session.ingest_evidence(
            inv_uid,
            b"Signed evidence bytes",
            "text/plain",
            original_filename="signed.txt",
            actor_id="t",
            actor_type="tool",
        )

    export_signed_investigation_bundle(source, inv_uid, signed_bundle)
    with zipfile.ZipFile(signed_bundle, "r") as zin:
        names = zin.namelist()
        blobs = {name: zin.read(name) for name in names}
    for name in list(blobs):
        if name.endswith(".chronicle"):
            blobs[name] = blobs[name] + b"tamper"
    with zipfile.ZipFile(tampered_bundle, "w", zipfile.ZIP_DEFLATED) as zout:
        for name in names:
            zout.writestr(name, blobs[name])

    with pytest.raises(ValueError, match="digest mismatch"):
        import_signed_investigation_bundle(tampered_bundle, target)
