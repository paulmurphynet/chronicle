from __future__ import annotations

import json
import sys
from importlib import import_module
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

module = import_module("scripts.check_integration_export_contracts")


def test_check_integration_export_contracts_passes(tmp_path: Path) -> None:
    project_path = tmp_path / "source_project"
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

    report_path = output_dir / "integration_export_contract_report.json"
    assert report_path.is_file()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    assert report["checks"]["generic_json_contract_errors"] == []
    assert report["checks"]["generic_csv_contract_errors"] == []
    assert report["checks"]["markdown_contract_ok"] is True
    assert report["checks"]["signed_bundle_import_ok"] is True

    expected = [
        "generic_json",
        "generic_csv_zip",
        "reasoning_brief_markdown",
        "chronicle_export",
        "signed_bundle_zip",
    ]
    for key in expected:
        assert Path(report["artifacts"][key]).is_file()
