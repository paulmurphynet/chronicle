from __future__ import annotations

import json
import sys
from importlib import import_module
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

ragas_adapter = import_module("scripts.adapters.ragas_batch_to_chronicle")


def test_ragas_adapter_auto_maps_common_keys() -> None:
    rows = [
        {
            "run_id": "r1",
            "question": "What was revenue?",
            "answer": "Revenue was $1.2M.",
            "contexts": ["The company reported revenue of $1.2M in Q1 2024."],
        }
    ]
    out_rows, code = ragas_adapter.run_rows(rows)
    assert code == 0
    assert len(out_rows) == 1
    assert out_rows[0]["run_id"] == "r1"
    assert out_rows[0]["ok"] is True
    assert out_rows[0]["ragas_mapping"]["query_key"] == "question"
    assert out_rows[0]["ragas_mapping"]["answer_key"] == "answer"
    assert out_rows[0]["ragas_mapping"]["contexts_key"] == "contexts"
    assert "error" not in out_rows[0]["chronicle"]


def test_ragas_adapter_accepts_retrieved_contexts_and_string_evidence() -> None:
    rows = [
        {
            "id": "s-1",
            "user_input": "Where was he?",
            "response": "He was in the kitchen.",
            "retrieved_contexts": "Witness said he was in the kitchen.",
        }
    ]
    out_rows, code = ragas_adapter.run_rows(rows)
    assert code == 0
    assert out_rows[0]["run_id"] == "s-1"
    assert out_rows[0]["ok"] is True
    assert out_rows[0]["ragas_mapping"]["contexts_key"] == "retrieved_contexts"
    assert "error" not in out_rows[0]["chronicle"]


def test_ragas_adapter_reports_missing_contexts() -> None:
    rows = [
        {
            "question": "Q",
            "answer": "A",
        }
    ]
    out_rows, code = ragas_adapter.run_rows(rows)
    assert code == 1
    assert out_rows[0]["ok"] is False
    assert out_rows[0]["chronicle"]["error"] == "invalid_input"
    assert out_rows[0]["input_error"].startswith("missing_contexts_keys:")


def test_ragas_adapter_main_supports_json_array_input(tmp_path: Path) -> None:
    input_path = tmp_path / "ragas_runs.json"
    output_path = tmp_path / "scored.jsonl"
    input_rows = [
        {
            "sample_id": "arr-1",
            "question": "What happened?",
            "answer": "A service outage occurred.",
            "contexts": ["Status page shows a service outage at 08:10 UTC."],
        }
    ]
    input_path.write_text(json.dumps(input_rows), encoding="utf-8")
    rc = ragas_adapter.main(
        [
            "--input",
            str(input_path),
            "--input-format",
            "json",
            "--output",
            str(output_path),
        ]
    )
    assert rc == 0
    lines = [ln for ln in output_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["run_id"] == "arr-1"
    assert row["ok"] is True
    assert "error" not in row["chronicle"]
