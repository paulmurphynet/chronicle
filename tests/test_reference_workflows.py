from __future__ import annotations

import json
import sys
from importlib import import_module
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

benchmark_module = import_module("scripts.benchmark_data.run_defensibility_benchmark")
compliance_module = import_module("scripts.compliance_report_from_rag")
runner_module = import_module("scripts.run_reference_workflows")


def test_benchmark_session_mode_writes_results(tmp_path: Path) -> None:
    output = tmp_path / "benchmark_results.json"
    rc = benchmark_module.main(["--mode", "session", "--output", str(output)])
    assert rc == 0
    assert output.is_file()
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["benchmark"] == "run_defensibility_benchmark"
    assert payload["execution_mode"] == "session"
    assert isinstance(payload["results"], list)
    assert len(payload["results"]) > 0


def test_compliance_session_mode_writes_report(tmp_path: Path) -> None:
    out_dir = tmp_path / "compliance"
    rc = compliance_module.main(["--mode", "session", "--output-dir", str(out_dir)])
    assert rc == 0
    report_path = out_dir / "report" / "audit_report.json"
    assert report_path.is_file()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert "investigation_uid" in report
    assert isinstance(report.get("claims"), list)


def test_reference_workflow_runner_with_stubbed_workflows(
    tmp_path: Path, monkeypatch
) -> None:
    def _ok(repo_root: Path, run_dir: Path) -> dict:
        return {"name": "ok", "status": "passed"}

    def _bad(repo_root: Path, run_dir: Path) -> dict:
        return {"name": "bad", "status": "failed", "error": "boom"}

    monkeypatch.setattr(runner_module, "WORKFLOW_RUNNERS", {"ok": _ok, "bad": _bad})

    out_dir = tmp_path / "runs"
    rc = runner_module.main(["--output-dir", str(out_dir)])
    assert rc == 1
    report_path = out_dir / "reference_workflow_report.json"
    assert report_path.is_file()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["summary"]["total"] == 2
    assert report["summary"]["failed"] == 1


def test_reference_workflow_runner_legal_and_history(tmp_path: Path) -> None:
    out_dir = tmp_path / "runs"
    rc = runner_module.main(["--output-dir", str(out_dir), "--only", "legal", "history"])
    assert rc == 0
    report_path = out_dir / "reference_workflow_report.json"
    assert report_path.is_file()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["summary"]["total"] == 2
    assert report["summary"]["failed"] == 0
    names = {wf["name"] for wf in report["workflows"]}
    assert names == {"legal", "history"}
