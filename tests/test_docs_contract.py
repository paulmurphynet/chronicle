"""Smoke tests for key docs snippets (README quick start + API /score behavior)."""

from __future__ import annotations

import pytest
from chronicle.scorer_contract import run_scorer_contract


def test_readme_quickstart_scorer_example_is_valid() -> None:
    """README quick-start payload should score without invalid_input errors."""
    payload = {
        "query": "What were Acme Corp's reported Scope 1 emissions for FY2024?",
        "answer": "Acme Corp reported Scope 1 emissions of 12,400 tCO2e for FY2024.",
        "evidence": [
            "Acme Corp Sustainability Report FY2024, p.8: Scope 1 emissions were 12,400 tCO2e.",
            "Acme Corp Annual Report 2024, Environmental section: Scope 1 totaled 12,400 tonnes CO2e.",
            "CDP submission summary (Acme Corp, 2024): Scope 1: 12.4 kt CO2e.",
        ],
    }
    out = run_scorer_contract(payload, allow_path=False)
    assert out.get("error") != "invalid_input"
    assert out.get("contract_version") == "1.0"
    assert "claim_uid" in out


def test_api_score_works_without_project_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """docs/api.md guarantee: /score works even when CHRONICLE_PROJECT_PATH is unset."""
    pytest.importorskip("fastapi")
    pytest.importorskip("multipart")
    pytest.importorskip("httpx")
    from chronicle.api.app import app
    from fastapi.testclient import TestClient

    monkeypatch.delenv("CHRONICLE_PROJECT_PATH", raising=False)
    with TestClient(app) as client:
        score = client.post(
            "/score",
            json={
                "query": "What was revenue?",
                "answer": "Revenue was $1.2M.",
                "evidence": ["The company reported revenue of $1.2M in Q1 2024."],
            },
        )
        assert score.status_code == 200, score.text

        health = client.get("/health")
        assert health.status_code == 503
