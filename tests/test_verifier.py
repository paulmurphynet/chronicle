"""Minimal tests for chronicle-verify on a .chronicle file."""

from __future__ import annotations

import zipfile
from pathlib import Path

import tools.verify_chronicle.verify_chronicle as verify_mod
from chronicle.store.project import create_project
from chronicle.store.session import ChronicleSession
from tools.verify_chronicle.verify_chronicle import verify_chronicle_file


def test_verify_chronicle_file_on_export(tmp_path: Path) -> None:
    """Build a minimal .chronicle via session export, then run verifier; all checks should pass."""
    create_project(tmp_path)
    text = b"Evidence chunk for verification."
    chronicle_path = tmp_path / "out.chronicle"
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation(
            "Verifier test", actor_id="test", actor_type="tool"
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
            inv_uid, "A claim.", actor_id="test", actor_type="tool"
        )
        session.link_support(inv_uid, span_uid, claim_uid, actor_id="test", actor_type="tool")
        session.export_investigation(inv_uid, chronicle_path)
    assert chronicle_path.is_file()
    results = verify_chronicle_file(chronicle_path, run_invariants=True)
    assert all(r[1] for r in results), f"Verifier failed: {results}"


def test_verify_chronicle_file_not_file() -> None:
    """Verifier on non-file path reports failure."""
    results = verify_chronicle_file(Path("/nonexistent/path.chronicle"), run_invariants=False)
    passed = [r for r in results if r[1]]
    assert len(passed) < len(results)
    assert any(r[0] == "file" and not r[1] for r in results)


def test_verify_chronicle_file_wrong_extension(tmp_path: Path) -> None:
    """Verifier on file without .chronicle extension reports failure."""
    bad = tmp_path / "not.chronicle.zip"
    bad.write_bytes(b"fake")
    results = verify_chronicle_file(bad, run_invariants=False)
    assert any(r[0] == "file" and not r[1] for r in results)


def test_verify_chronicle_file_rejects_unexpected_archive_entries(tmp_path: Path) -> None:
    """Verifier should fail when archive includes files outside manifest/db/evidence paths."""
    create_project(tmp_path)
    chronicle_path = tmp_path / "out.chronicle"
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation(
            "Verifier extra", actor_id="test", actor_type="tool"
        )
        session.ingest_evidence(
            inv_uid,
            b"Evidence",
            "text/plain",
            original_filename="doc.txt",
            actor_id="test",
            actor_type="tool",
        )
        session.export_investigation(inv_uid, chronicle_path)

    with_extra = tmp_path / "with-extra.chronicle"
    with (
        zipfile.ZipFile(chronicle_path, "r") as zin,
        zipfile.ZipFile(with_extra, "w", zipfile.ZIP_DEFLATED) as zout,
    ):
        for name in zin.namelist():
            zout.writestr(name, zin.read(name))
        zout.writestr("extras/unexpected.txt", b"unexpected")

    results = verify_chronicle_file(with_extra, run_invariants=False)
    assert any(
        name == "zip" and (not passed) and "unexpected archive entries" in detail
        for name, passed, detail in results
    )


def test_verify_chronicle_file_enforces_archive_entry_limit(tmp_path: Path, monkeypatch) -> None:
    """Verifier should fail when entry-count safety budget is exceeded."""
    create_project(tmp_path)
    chronicle_path = tmp_path / "out.chronicle"
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation(
            "Verifier limits", actor_id="test", actor_type="tool"
        )
        session.ingest_evidence(
            inv_uid,
            b"Evidence",
            "text/plain",
            original_filename="doc.txt",
            actor_id="test",
            actor_type="tool",
        )
        session.export_investigation(inv_uid, chronicle_path)

    monkeypatch.setattr(verify_mod, "MAX_IMPORT_ARCHIVE_ENTRIES", 1)
    results = verify_chronicle_file(chronicle_path, run_invariants=False)
    assert any(
        name == "zip" and (not passed) and "too many entries" in detail
        for name, passed, detail in results
    )
