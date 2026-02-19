from __future__ import annotations

import json
import sys
from importlib import import_module
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

starter = import_module("scripts.adapters.starter_batch_to_scorer")
validator = import_module("scripts.adapters.validate_adapter_outputs")


def test_starter_run_rows_mixed_valid_and_invalid() -> None:
    lines = [
        json.dumps(
            {
                "run_id": "r1",
                "query": "What was revenue?",
                "answer": "Revenue was $1.2M.",
                "evidence": ["The company reported revenue of $1.2M in Q1 2024."],
            }
        ),
        json.dumps({"run_id": "r2", "query": "Q", "answer": "A"}),
    ]
    rows, code = starter.run_rows(
        lines,
        query_key="query",
        answer_key="answer",
        evidence_key="evidence",
        run_id_key="run_id",
    )
    assert code == 1
    assert len(rows) == 2
    assert rows[0]["ok"] is True
    assert "error" not in rows[0]["chronicle"]
    assert rows[1]["ok"] is False
    assert rows[1]["input_error"] == "missing_evidence_key:evidence"
    assert rows[1]["chronicle"]["error"] == "invalid_input"


def test_validator_accepts_success_and_error_payloads() -> None:
    success = {
        "contract_version": "1.0",
        "claim_uid": "claim_123",
        "provenance_quality": "medium",
        "corroboration": {
            "support_count": 1,
            "challenge_count": 0,
            "independent_sources_count": 1,
        },
        "contradiction_status": "none",
    }
    error = {"contract_version": "1.0", "error": "no_claim"}
    assert validator.validate_contract_payload(success) == []
    assert validator.validate_contract_payload(error) == []


def test_validator_main_detects_invalid_rows(tmp_path: Path) -> None:
    path = tmp_path / "adapter_output.jsonl"
    bad_row = {
        "chronicle": {
            "contract_version": "1.0",
            "claim_uid": "claim_123",
            "provenance_quality": "invalid",
            "corroboration": {"support_count": 1, "challenge_count": 0},
            "contradiction_status": "none",
        }
    }
    path.write_text(json.dumps(bad_row) + "\n", encoding="utf-8")
    rc = validator.main(["--input", str(path)])
    assert rc == 1
