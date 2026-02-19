"""Parity tests between chronicle.verify and standalone chronicle-verify."""

from __future__ import annotations

import shutil
import sqlite3
import zipfile
from pathlib import Path

from chronicle.store.project import create_project
from chronicle.store.session import ChronicleSession
from chronicle.verify import verify_project
from tools.verify_chronicle.verify_chronicle import verify_chronicle_file


def _build_sample_chronicle(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    out = tmp_path / "sample.chronicle"
    create_project(project)
    blob = b"Evidence chunk for verifier parity."
    with ChronicleSession(project) as session:
        _, inv_uid = session.create_investigation("Verifier parity", actor_id="test", actor_type="tool")
        _, ev_uid = session.ingest_evidence(
            inv_uid,
            blob,
            "text/plain",
            original_filename="parity.txt",
            actor_id="test",
            actor_type="tool",
        )
        _, span_uid = session.anchor_span(
            inv_uid,
            ev_uid,
            "text_offset",
            {"start_char": 0, "end_char": len(blob.decode("utf-8"))},
            quote=blob.decode("utf-8"),
            actor_id="test",
            actor_type="tool",
        )
        _, claim_uid = session.propose_claim(
            inv_uid,
            "Parity claim.",
            actor_id="test",
            actor_type="tool",
        )
        session.link_support(inv_uid, span_uid, claim_uid, actor_id="test", actor_type="tool")
        session.export_investigation(inv_uid, out)
    return out


def _zip_dir(source_dir: Path, out_file: Path) -> None:
    with zipfile.ZipFile(out_file, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(source_dir.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(source_dir).as_posix())


def _extract_to_dir(chronicle_file: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(chronicle_file, "r") as zf:
        zf.extractall(out_dir)


def _tamper_evidence(chronicle_file: Path, out_file: Path) -> None:
    work = out_file.parent / "tamper-evidence-work"
    if work.exists():
        shutil.rmtree(work)
    _extract_to_dir(chronicle_file, work)
    evidence_files = [
        p
        for p in work.rglob("*")
        if p.is_file() and p.relative_to(work).as_posix().startswith("evidence/")
    ]
    assert evidence_files, "Expected at least one evidence file in sample .chronicle"
    evidence_files[0].write_bytes(b"tampered evidence content")
    _zip_dir(work, out_file)


def _tamper_append_only_ledger(chronicle_file: Path, out_file: Path) -> None:
    work = out_file.parent / "tamper-ledger-work"
    if work.exists():
        shutil.rmtree(work)
    _extract_to_dir(chronicle_file, work)
    db_path = work / "chronicle.db"
    conn = sqlite3.connect(str(db_path))
    try:
        (count,) = conn.execute("SELECT COUNT(*) FROM events").fetchone()
        assert count >= 2, "Expected at least two events to test ledger reversal"
        conn.execute("UPDATE events SET recorded_at = '2099-01-01T00:00:00Z' WHERE rowid = 1")
        conn.execute("UPDATE events SET recorded_at = '2000-01-01T00:00:00Z' WHERE rowid = 2")
        conn.commit()
    finally:
        conn.close()
    _zip_dir(work, out_file)


def test_verifier_parity_passes_on_valid_package(tmp_path: Path) -> None:
    chronicle_file = _build_sample_chronicle(tmp_path)
    standalone = verify_chronicle_file(chronicle_file, run_invariants=True)
    assert all(passed for _, passed, _ in standalone)

    unpacked = tmp_path / "unpacked-valid"
    _extract_to_dir(chronicle_file, unpacked)
    core = verify_project(unpacked)
    assert core.passed is True


def test_verifier_parity_fails_on_evidence_hash_mismatch(tmp_path: Path) -> None:
    chronicle_file = _build_sample_chronicle(tmp_path)
    tampered = tmp_path / "tampered-evidence.chronicle"
    _tamper_evidence(chronicle_file, tampered)

    standalone = verify_chronicle_file(tampered, run_invariants=True)
    assert any(name == "evidence_hashes" and not passed for name, passed, _ in standalone)

    unpacked = tmp_path / "unpacked-tampered-evidence"
    _extract_to_dir(tampered, unpacked)
    core = verify_project(unpacked)
    assert core.passed is False
    assert any(r.name == "evidence_integrity" and not r.passed for r in core.results)


def test_verifier_parity_fails_on_append_only_reversal(tmp_path: Path) -> None:
    chronicle_file = _build_sample_chronicle(tmp_path)
    tampered = tmp_path / "tampered-ledger.chronicle"
    _tamper_append_only_ledger(chronicle_file, tampered)

    standalone = verify_chronicle_file(tampered, run_invariants=True)
    assert any(name == "append_only_ledger" and not passed for name, passed, _ in standalone)

    unpacked = tmp_path / "unpacked-tampered-ledger"
    _extract_to_dir(tampered, unpacked)
    core = verify_project(unpacked)
    assert core.passed is False
    assert any(r.name == "append_only_ledger" and not r.passed for r in core.results)
