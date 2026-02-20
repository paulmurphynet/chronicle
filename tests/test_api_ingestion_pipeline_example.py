from __future__ import annotations

import json
import sys
from importlib import import_module
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

module = import_module("scripts.api_ingestion_pipeline_example")


def test_api_ingestion_pipeline_example_outputs_artifacts(tmp_path: Path) -> None:
    project_path = tmp_path / "project"
    output_dir = tmp_path / "out"
    rc = module.main(
        [
            "--project-path",
            str(project_path),
            "--output-dir",
            str(output_dir),
        ]
    )
    assert rc == 0

    report_path = output_dir / "api_ingestion_pipeline_report.json"
    assert report_path.is_file()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    assert report["summary"]["support_count"] >= 1
    assert report["summary"]["challenge_count"] >= 1
    assert report["summary"]["provenance_quality"] in {"strong", "medium", "weak", "challenged"}

    export_path = Path(report["artifacts"]["export_chronicle"])
    defensibility_path = Path(report["artifacts"]["defensibility"])
    review_packet_path = Path(report["artifacts"]["review_packet"])
    reasoning_path = Path(report["artifacts"]["reasoning_brief"])

    assert export_path.is_file()
    assert defensibility_path.is_file()
    assert review_packet_path.is_file()
    assert reasoning_path.is_file()


def test_api_ingestion_pipeline_falls_back_when_sockets_unavailable(
    tmp_path: Path, monkeypatch
) -> None:
    project_path = tmp_path / "project"
    output_dir = tmp_path / "out"
    monkeypatch.setattr(module, "_find_free_port", lambda: (_ for _ in ()).throw(PermissionError(1, "Operation not permitted")))
    rc = module.main(
        [
            "--project-path",
            str(project_path),
            "--output-dir",
            str(output_dir),
        ]
    )
    assert rc == 0
    report_path = output_dir / "api_ingestion_pipeline_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "passed"
