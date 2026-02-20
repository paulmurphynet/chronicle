from __future__ import annotations

import json
import sys
from importlib import import_module
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_module = import_module("scripts.benchmark_data.run_neo4j_projection_benchmark")
main = _module.main


def test_benchmark_export_passes_for_small_seed(tmp_path: Path) -> None:
    out = tmp_path / "neo4j_projection_benchmark.json"
    code = main(
        [
            "--output",
            str(out),
            "--investigations",
            "1",
            "--claims-per-investigation",
            "3",
            "--evidence-per-investigation",
            "4",
            "--links-per-claim",
            "2",
        ]
    )
    assert code == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["status"] == "passed"
    assert payload["export"]["status"] == "passed"
    assert payload["row_counts"]["claims"] == 3
    assert payload["row_counts"]["evidence_items"] == 4
    assert payload["row_counts"]["links"] == 6
    assert payload["sync"]["status"] == "skipped"


def test_benchmark_threshold_failure_returns_nonzero(tmp_path: Path) -> None:
    out = tmp_path / "neo4j_projection_benchmark_fail.json"
    code = main(
        [
            "--output",
            str(out),
            "--investigations",
            "1",
            "--claims-per-investigation",
            "2",
            "--evidence-per-investigation",
            "2",
            "--links-per-claim",
            "1",
            "--max-export-elapsed-ms",
            "0.0",
        ]
    )
    assert code == 2
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["status"] == "failed"
    failures = payload["threshold_failures"]
    assert failures
    assert "export.elapsed_ms exceeded threshold" in failures[0]
