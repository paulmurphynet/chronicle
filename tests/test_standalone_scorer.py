"""Minimal tests for standalone_defensibility_scorer: valid input -> metrics; invalid input -> error."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Run from repo root so scripts/ and chronicle are importable
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Import after path fix
from scripts.standalone_defensibility_scorer import _run_scorer, main


def _run(input_obj: dict) -> dict:
    return _run_scorer(json.dumps(input_obj))


def test_valid_input_returns_metrics():
    """Valid query/answer/evidence produces defensibility metrics (no error key)."""
    out = _run({
        "query": "What was revenue?",
        "answer": "Revenue was $1.2M.",
        "evidence": ["The company reported revenue of $1.2M in Q1 2024."],
    })
    assert "error" not in out
    assert out.get("contract_version") == "1.0"
    assert "claim_uid" in out
    assert out.get("provenance_quality") in ("strong", "medium", "weak", "challenged")
    assert "corroboration" in out
    assert out["corroboration"]["support_count"] >= 0
    assert out["corroboration"]["challenge_count"] >= 0
    assert out["corroboration"]["independent_sources_count"] >= 0
    assert out.get("contradiction_status") in ("none", "open", "acknowledged", "resolved")


def test_invalid_json_returns_error():
    """Invalid JSON on stdin yields invalid_input error."""
    out = _run_scorer("not json at all")
    assert out.get("error") == "invalid_input"
    assert out.get("contract_version") == "1.0"
    assert "message" in out


def test_missing_query_returns_error():
    """Missing query yields invalid_input."""
    out = _run({"answer": "Yes.", "evidence": ["A source says yes."]})
    assert out.get("error") == "invalid_input"
    assert "query" in out.get("message", "").lower()


def test_missing_answer_returns_error():
    """Missing answer yields invalid_input."""
    out = _run({"query": "Is it true?", "evidence": ["A source."]})
    assert out.get("error") == "invalid_input"
    assert "answer" in out.get("message", "").lower()


def test_missing_evidence_returns_error():
    """Missing evidence yields invalid_input."""
    out = _run({"query": "Q?", "answer": "A."})
    assert out.get("error") == "invalid_input"
    assert "evidence" in out.get("message", "").lower()


def test_evidence_not_array_returns_error():
    """Evidence that is not an array yields invalid_input."""
    out = _run({"query": "Q?", "answer": "A.", "evidence": "single string"})
    assert out.get("error") == "invalid_input"


def test_empty_evidence_returns_error():
    """Empty evidence array yields invalid_input."""
    out = _run({"query": "Q?", "answer": "A.", "evidence": []})
    assert out.get("error") == "invalid_input"
    assert "at least one" in out.get("message", "").lower() or "non-empty" in out.get("message", "").lower()


def test_evidence_objects_with_text_accepted():
    """Evidence as list of objects with 'text' is accepted."""
    out = _run({
        "query": "What happened?",
        "answer": "It happened in 2024.",
        "evidence": [{"text": "The event occurred in 2024."}],
    })
    assert "error" not in out
    assert "claim_uid" in out


def test_evidence_objects_with_url_accepted(monkeypatch):
    """Evidence as list of objects with 'url' is accepted when fetch succeeds (mocked)."""
    def mock_fetch(url: str):
        return "Fetched content from URL." if url == "https://example.com/doc.txt" else None

    monkeypatch.setattr("chronicle.scorer_contract._fetch_url", mock_fetch)
    out = _run({
        "query": "What happened?",
        "answer": "It happened.",
        "evidence": [{"url": "https://example.com/doc.txt"}],
    })
    assert "error" not in out
    assert "claim_uid" in out
    assert out["corroboration"]["support_count"] >= 1


def test_main_returns_zero_on_success(monkeypatch):
    """main() returns 0 when given valid JSON on stdin."""
    monkeypatch.setattr("sys.argv", ["standalone_defensibility_scorer.py"])
    stdin = json.dumps({
        "query": "Q?",
        "answer": "A.",
        "evidence": ["Chunk one."],
    })
    monkeypatch.setattr("sys.stdin", type("Stdin", (), {"read": lambda self, size=-1: stdin})())
    monkeypatch.setattr("sys.stdout", type("Stdout", (), {"write": lambda self, s: None})())
    exit_code = main()
    assert exit_code == 0


def test_main_returns_one_on_error(monkeypatch):
    """main() returns 1 when scorer returns error."""
    monkeypatch.setattr("sys.argv", ["standalone_defensibility_scorer.py"])
    stdin = json.dumps({"query": "Q?", "answer": "A.", "evidence": []})
    monkeypatch.setattr("sys.stdin", type("Stdin", (), {"read": lambda self, size=-1: stdin})())
    monkeypatch.setattr("sys.stdout", type("Stdout", (), {"write": lambda self, s: None})())
    exit_code = main()
    assert exit_code == 1
