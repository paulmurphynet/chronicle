from __future__ import annotations

import json
import sys
from importlib import import_module
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

module = import_module("scripts.check_deterministic_defensibility")


def test_deterministic_defensibility_check_passes(tmp_path: Path) -> None:
    report_path = tmp_path / "deterministic_report.json"
    rc = module.main(
        [
            "--rounds",
            "3",
            "--output",
            str(report_path),
        ]
    )
    assert rc == 0
    assert report_path.is_file()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    assert report["stable"] is True
    assert len(report["normalized_runs"]) == 3


def test_deterministic_defensibility_invalid_input_fails(tmp_path: Path) -> None:
    input_path = tmp_path / "bad.json"
    input_path.write_text("[]", encoding="utf-8")
    rc = module.main(["--input", str(input_path)])
    assert rc == 1
