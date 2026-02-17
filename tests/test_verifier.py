"""Minimal tests for chronicle-verify on a .chronicle file."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from chronicle.store.project import create_project
from chronicle.store.session import ChronicleSession
from tools.verify_chronicle.verify_chronicle import verify_chronicle_file


def test_verify_chronicle_file_on_export(tmp_path: Path) -> None:
    """Build a minimal .chronicle via session export, then run verifier; all checks should pass."""
    create_project(tmp_path)
    text = b"Evidence chunk for verification."
    chronicle_path = tmp_path / "out.chronicle"
    with ChronicleSession(tmp_path) as session:
        _, inv_uid = session.create_investigation("Verifier test", actor_id="test", actor_type="tool")
        _, ev_uid = session.ingest_evidence(
            inv_uid, text, "text/plain", original_filename="doc.txt", actor_id="test", actor_type="tool"
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
        _, claim_uid = session.propose_claim(inv_uid, "A claim.", actor_id="test", actor_type="tool")
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
