"""API contract tests for docs/api.md flow, error mapping, and request identity."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("multipart")
pytest.importorskip("httpx")
from chronicle.api.app import app
from chronicle.core import validation
from chronicle.store.project import CHRONICLE_DB
from chronicle.store.read_model.sqlite_read_model import SqliteReadModel
from fastapi.testclient import TestClient


def _create_investigation(client: TestClient, *, key: str | None = None) -> tuple[str, str]:
    body: dict[str, str] = {"title": "API contract investigation"}
    if key:
        body["investigation_key"] = key
    r = client.post(
        "/investigations",
        json=body,
        headers={"X-Actor-Id": "api_tester", "X-Actor-Type": "tool"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    return data["investigation_uid"], data["event_id"]


def _seed_claim_flow(client: TestClient, investigation_uid: str) -> tuple[str, str]:
    evidence = client.post(
        f"/investigations/{investigation_uid}/evidence",
        json={
            "content": "Acme reported revenue of $1.2M in Q1 2024.",
            "media_type": "text/plain",
            "original_filename": "rev.txt",
        },
        headers={"X-Actor-Id": "api_tester", "X-Actor-Type": "tool"},
    )
    assert evidence.status_code == 200, evidence.text
    span_uid = evidence.json()["span_uid"]

    claim = client.post(
        f"/investigations/{investigation_uid}/claims",
        json={"text": "Revenue was $1.2M in Q1 2024."},
        headers={"X-Actor-Id": "api_tester", "X-Actor-Type": "tool"},
    )
    assert claim.status_code == 200, claim.text
    claim_uid = claim.json()["claim_uid"]

    link = client.post(
        f"/investigations/{investigation_uid}/links/support",
        json={"span_uid": span_uid, "claim_uid": claim_uid},
        headers={"X-Actor-Id": "api_tester", "X-Actor-Type": "tool"},
    )
    assert link.status_code == 200, link.text
    return span_uid, claim_uid


def test_api_example_flow_and_identity_headers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Covers docs/api.md example flow and verifies write actor identity persistence."""
    project_path = tmp_path / "api-project"
    monkeypatch.setenv("CHRONICLE_PROJECT_PATH", str(project_path))

    with TestClient(app) as client:
        create = client.post(
            "/investigations",
            json={"title": "My run"},
            headers={
                "X-Actor-Id": "jane_doe",
                "X-Actor-Type": "tool",
                "X-Request-Id": "req-doc-flow",
            },
        )
        assert create.status_code == 200, create.text
        assert create.headers.get("X-Request-Id") == "req-doc-flow"
        investigation_uid = create.json()["investigation_uid"]
        event_id = create.json()["event_id"]

        _, claim_uid = _seed_claim_flow(client, investigation_uid)

        defs = client.get(f"/claims/{claim_uid}/defensibility")
        assert defs.status_code == 200, defs.text
        assert defs.json()["claim_uid"] == claim_uid

        listed = client.get("/investigations", params={"limit": 10, "is_archived": False})
        assert listed.status_code == 200
        assert any(i["investigation_uid"] == investigation_uid for i in listed.json()["investigations"])

    db_path = project_path / CHRONICLE_DB
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute(
            "SELECT actor_id, actor_type FROM events WHERE event_id = ?",
            (event_id,),
        ).fetchone()
    finally:
        conn.close()
    assert row == ("jane_doe", "tool")


def test_api_export_import_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Covers export/import endpoints with a real .chronicle package."""
    source_project = tmp_path / "source-project"
    target_project = tmp_path / "target-project"
    monkeypatch.setenv("CHRONICLE_PROJECT_PATH", str(source_project))

    with TestClient(app) as client:
        inv_uid, _ = _create_investigation(client)
        _seed_claim_flow(client, inv_uid)

        export_res = client.post(f"/investigations/{inv_uid}/export")
        assert export_res.status_code == 200, export_res.text
        archive = export_res.content
        assert archive[:2] == b"PK"

        monkeypatch.setenv("CHRONICLE_PROJECT_PATH", str(target_project))
        imported = client.post(
            "/import",
            files={"file": ("import.chronicle", archive, "application/zip")},
        )
        assert imported.status_code == 200, imported.text
        assert imported.json()["status"] == "ok"

        listed = client.get("/investigations")
        assert listed.status_code == 200, listed.text
        assert len(listed.json()["investigations"]) >= 1


def test_api_error_mapping_and_request_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensures error mapping and request_id surfaces on 400/404/429 responses."""
    project_path = tmp_path / "api-errors"
    monkeypatch.setenv("CHRONICLE_PROJECT_PATH", str(project_path))

    with TestClient(app) as client:
        inv_uid, _ = _create_investigation(client, key="idem-key-1")

        bad_tier = client.post(
            f"/investigations/{inv_uid}/tier",
            json={"tier": "not-a-tier"},
            headers={"X-Request-Id": "req-bad-tier"},
        )
        assert bad_tier.status_code == 400
        assert bad_tier.headers.get("X-Request-Id") == "req-bad-tier"
        assert bad_tier.json()["request_id"] == "req-bad-tier"

        missing = client.get("/investigations/inv_missing", headers={"X-Request-Id": "req-missing"})
        assert missing.status_code == 404
        assert missing.headers.get("X-Request-Id") == "req-missing"
        assert missing.json()["request_id"] == "req-missing"

        monkeypatch.setattr(validation, "MAX_IDEMPOTENCY_KEY_EVENTS", 1)
        cap = client.post(
            "/investigations",
            json={"title": "Second", "investigation_key": "idem-key-2"},
            headers={"X-Request-Id": "req-cap"},
        )
        assert cap.status_code == 429
        assert "Idempotency key capacity reached" in cap.json()["detail"]
        assert cap.headers.get("X-Request-Id") == "req-cap"
        assert cap.json()["request_id"] == "req-cap"


def test_api_cursor_pagination_for_claims_and_graph(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Claims and graph endpoints should support cursor pagination."""
    project_path = tmp_path / "api-pagination"
    monkeypatch.setenv("CHRONICLE_PROJECT_PATH", str(project_path))

    with TestClient(app) as client:
        inv_uid, _ = _create_investigation(client)

        created_claims: list[str] = []
        for i in range(3):
            evidence = client.post(
                f"/investigations/{inv_uid}/evidence",
                json={
                    "content": f"Evidence paragraph {i}.",
                    "media_type": "text/plain",
                    "original_filename": f"ev_{i}.txt",
                },
                headers={"X-Actor-Id": "api_tester", "X-Actor-Type": "tool"},
            )
            assert evidence.status_code == 200, evidence.text
            span_uid = evidence.json()["span_uid"]

            claim = client.post(
                f"/investigations/{inv_uid}/claims",
                json={"text": f"Claim {i}"},
                headers={"X-Actor-Id": "api_tester", "X-Actor-Type": "tool"},
            )
            assert claim.status_code == 200, claim.text
            claim_uid = claim.json()["claim_uid"]
            created_claims.append(claim_uid)

            linked = client.post(
                f"/investigations/{inv_uid}/links/support",
                json={"span_uid": span_uid, "claim_uid": claim_uid},
                headers={"X-Actor-Id": "api_tester", "X-Actor-Type": "tool"},
            )
            assert linked.status_code == 200, linked.text

        page_1 = client.get(
            f"/investigations/{inv_uid}/claims",
            params={"limit": 2},
        )
        assert page_1.status_code == 200, page_1.text
        body_1 = page_1.json()
        assert len(body_1["claims"]) == 2
        assert body_1["page"]["has_more"] is True
        cursor = body_1["page"]["next_cursor"]
        assert isinstance(cursor, str) and cursor

        page_2 = client.get(
            f"/investigations/{inv_uid}/claims",
            params={"limit": 2, "cursor": cursor},
        )
        assert page_2.status_code == 200, page_2.text
        body_2 = page_2.json()
        assert len(body_2["claims"]) == 1
        assert body_2["page"]["has_more"] is False

        paged_claim_uids = [c["claim_uid"] for c in body_1["claims"] + body_2["claims"]]
        assert set(paged_claim_uids) == set(created_claims)

        graph_1 = client.get(
            f"/investigations/{inv_uid}/graph",
            params={"edge_limit": 2},
        )
        assert graph_1.status_code == 200, graph_1.text
        g1 = graph_1.json()
        assert len(g1["edges"]) == 2
        assert g1["edges_page"]["has_more"] is True
        edge_cursor = g1["edges_page"]["next_cursor"]
        assert isinstance(edge_cursor, str) and edge_cursor

        graph_2 = client.get(
            f"/investigations/{inv_uid}/graph",
            params={"edge_limit": 2, "edge_cursor": edge_cursor},
        )
        assert graph_2.status_code == 200, graph_2.text
        g2 = graph_2.json()
        assert len(g2["edges"]) == 1
        assert g2["edges_page"]["has_more"] is False


def test_graph_endpoint_avoids_per_claim_link_queries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Graph endpoint should not call per-claim link/span lookups (N+1 regression guard)."""
    project_path = tmp_path / "api-graph-batch"
    monkeypatch.setenv("CHRONICLE_PROJECT_PATH", str(project_path))

    with TestClient(app) as client:
        inv_uid, _ = _create_investigation(client)
        _seed_claim_flow(client, inv_uid)

        def _fail(*_: object, **__: object) -> list[object]:
            raise AssertionError("N+1 method should not be called by /graph")

        monkeypatch.setattr(SqliteReadModel, "get_support_for_claim", _fail)
        monkeypatch.setattr(SqliteReadModel, "get_challenges_for_claim", _fail)
        monkeypatch.setattr(SqliteReadModel, "get_evidence_span", _fail)

        graph = client.get(f"/investigations/{inv_uid}/graph")
        assert graph.status_code == 200, graph.text
        payload = graph.json()
        assert len(payload["edges"]) >= 1
