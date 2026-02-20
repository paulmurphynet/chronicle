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

readiness_module = import_module("scripts.review_readiness_gate")


def _build_project_with_open_tension(project_dir: Path) -> str:
    create_project(project_dir)
    with ChronicleSession(project_dir) as session:
        _, inv_uid = session.create_investigation("Readiness test", actor_id="t", actor_type="tool")
        _, c1_uid = session.propose_claim(inv_uid, "Claim A", actor_id="t", actor_type="tool")
        _, c2_uid = session.propose_claim(inv_uid, "Claim B", actor_id="t", actor_type="tool")
        session.declare_tension(
            inv_uid,
            c1_uid,
            c2_uid,
            workspace="forge",
            actor_id="t",
            actor_type="tool",
        )
    return inv_uid


def test_review_readiness_gate_passes_with_relaxed_tension_threshold(tmp_path: Path) -> None:
    inv_uid = _build_project_with_open_tension(tmp_path)
    report_path = tmp_path / "readiness.json"
    rc = readiness_module.main(
        [
            "--path",
            str(tmp_path),
            "--investigation-uid",
            inv_uid,
            "--max-unresolved-tensions",
            "1",
            "--output",
            str(report_path),
        ]
    )
    assert rc == 0
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["status"] == "passed"
    assert payload["metrics"]["unresolved_tensions_count"] == 1


def test_review_readiness_gate_fails_default_unresolved_threshold(tmp_path: Path) -> None:
    inv_uid = _build_project_with_open_tension(tmp_path)
    report_path = tmp_path / "readiness_fail.json"
    rc = readiness_module.main(
        [
            "--path",
            str(tmp_path),
            "--investigation-uid",
            inv_uid,
            "--output",
            str(report_path),
        ]
    )
    assert rc == 1
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["status"] == "failed"
    checks = {c["name"]: c for c in payload["checks"]}
    assert checks["unresolved_tensions_threshold"]["passed"] is False


def test_review_readiness_gate_fails_on_policy_mismatch(tmp_path: Path) -> None:
    inv_uid = _build_project_with_open_tension(tmp_path)
    report_path = tmp_path / "readiness_policy_fail.json"
    rc = readiness_module.main(
        [
            "--path",
            str(tmp_path),
            "--investigation-uid",
            inv_uid,
            "--max-unresolved-tensions",
            "1",
            "--built-under-profile-id",
            "policy_legal",
            "--viewing-profile-id",
            "policy_investigative_journalism",
            "--output",
            str(report_path),
        ]
    )
    assert rc == 1
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    checks = {c["name"]: c for c in payload["checks"]}
    assert checks["policy_compatibility"]["passed"] is False
