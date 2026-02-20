"""API contract tests for docs/api.md flow, error mapping, and request identity."""

from __future__ import annotations

import sqlite3
import zipfile
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("multipart")
pytest.importorskip("httpx")
import chronicle.api.app as api_app
from chronicle.api.app import app
from chronicle.core import validation
from chronicle.core.policy import PolicyProfile, default_policy_profile, import_policy_to_project
from chronicle.store.project import CHRONICLE_DB, create_project
from chronicle.store.read_model.sqlite_read_model import SqliteReadModel
from chronicle.store.session import ChronicleSession
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
        assert defs.json().get("link_assurance_level") == "tool_generated"

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


def test_api_import_rejects_oversized_upload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Import endpoint returns 413 when upload exceeds MAX_IMPORT_BYTES."""
    project_path = tmp_path / "api-import-size"
    monkeypatch.setenv("CHRONICLE_PROJECT_PATH", str(project_path))
    monkeypatch.setattr(api_app, "MAX_IMPORT_BYTES", 32)

    with TestClient(app) as client:
        response = client.post(
            "/import",
            files={"file": ("too-big.chronicle", b"x" * 128, "application/zip")},
        )
    assert response.status_code == 413


def test_api_evidence_upload_rejects_oversized_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Evidence ingest endpoint returns 413 when upload exceeds MAX_EVIDENCE_BYTES."""
    project_path = tmp_path / "api-evidence-size"
    monkeypatch.setenv("CHRONICLE_PROJECT_PATH", str(project_path))
    monkeypatch.setattr(api_app, "MAX_EVIDENCE_BYTES", 16)

    with TestClient(app) as client:
        inv_uid, _ = _create_investigation(client)
        response = client.post(
            f"/investigations/{inv_uid}/evidence",
            files={"file": ("too-big.txt", b"x" * 64, "text/plain")},
            headers={"X-Actor-Id": "api_tester", "X-Actor-Type": "tool"},
        )
    assert response.status_code == 413


def test_api_import_returns_400_for_tampered_archive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tampered archive is rejected with a client error instead of 500."""
    source_project = tmp_path / "source-project"
    target_project = tmp_path / "target-project"
    monkeypatch.setenv("CHRONICLE_PROJECT_PATH", str(source_project))

    with TestClient(app) as client:
        inv_uid, _ = _create_investigation(client)
        _seed_claim_flow(client, inv_uid)
        export_res = client.post(f"/investigations/{inv_uid}/export")
        assert export_res.status_code == 200, export_res.text
        archive = export_res.content

        tampered_path = tmp_path / "tampered.chronicle"
        source_path = tmp_path / "source.chronicle"
        source_path.write_bytes(archive)
        with zipfile.ZipFile(source_path, "r") as zin:
            names = zin.namelist()
            blobs = {name: zin.read(name) for name in names}
        for name in list(blobs):
            if name.startswith("evidence/"):
                blobs[name] = b"tampered"
        with zipfile.ZipFile(tampered_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for name in names:
                zout.writestr(name, blobs[name])

        monkeypatch.setenv("CHRONICLE_PROJECT_PATH", str(target_project))
        imported = client.post(
            "/import",
            files={"file": ("import.chronicle", tampered_path.read_bytes(), "application/zip")},
        )
    assert imported.status_code == 400
    assert "verification failed" in imported.json()["detail"]


def _seed_project_for_archive(project_path: Path) -> tuple[str, bytes]:
    with ChronicleSession(project_path, event_store_backend="sqlite") as session:
        _, inv_uid = session.create_investigation("Archive-ready", actor_id="t", actor_type="tool")
        _, evidence_uid = session.ingest_evidence(
            inv_uid,
            b"Archive evidence",
            "text/plain",
            original_filename="archive.txt",
            actor_id="t",
            actor_type="tool",
        )
        _, span_uid = session.anchor_span(
            inv_uid,
            evidence_uid,
            "text_offset",
            {"start_char": 0, "end_char": 7},
            quote="Archive",
            actor_id="t",
            actor_type="tool",
        )
        _, claim_uid = session.propose_claim(inv_uid, "Archive claim.", actor_id="t", actor_type="tool")
        session.link_support(inv_uid, span_uid, claim_uid, actor_id="t", actor_type="tool")
        out = project_path / "archive.chronicle"
        session.export_investigation(inv_uid, out)
    return inv_uid, out.read_bytes()


def test_api_export_works_when_postgres_backend_selected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Export endpoint should stay available even when CHRONICLE_EVENT_STORE=postgres."""
    project_path = tmp_path / "api-export-postgres-mode"
    monkeypatch.setenv("CHRONICLE_PROJECT_PATH", str(project_path))
    create_project(project_path)
    inv_uid, _ = _seed_project_for_archive(project_path)
    monkeypatch.setenv("CHRONICLE_EVENT_STORE", "postgres")
    monkeypatch.setenv("CHRONICLE_POSTGRES_URL", "postgresql://u:p@127.0.0.1:5432/chronicle")

    with TestClient(app) as client:
        response = client.post(f"/investigations/{inv_uid}/export")

    assert response.status_code == 200, response.text
    assert response.content[:2] == b"PK"


def test_api_import_works_when_postgres_backend_selected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Import endpoint should stay available even when CHRONICLE_EVENT_STORE=postgres."""
    source_project = tmp_path / "api-import-source"
    target_project = tmp_path / "api-import-target"
    create_project(source_project)
    _inv_uid, archive = _seed_project_for_archive(source_project)
    monkeypatch.setenv("CHRONICLE_PROJECT_PATH", str(target_project))
    monkeypatch.setenv("CHRONICLE_EVENT_STORE", "postgres")
    monkeypatch.setenv("CHRONICLE_POSTGRES_URL", "postgresql://u:p@127.0.0.1:5432/chronicle")

    with TestClient(app) as client:
        response = client.post(
            "/import",
            files={"file": ("import.chronicle", archive, "application/zip")},
        )

    assert response.status_code == 200, response.text
    with ChronicleSession(target_project, event_store_backend="sqlite") as session:
        listed = session.read_model.list_investigations(limit=10)
    assert listed


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


def test_api_policy_compatibility_preflight(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Policy compatibility endpoint returns deltas for built-under vs viewing profile."""
    project_path = tmp_path / "api-policy-compat"
    monkeypatch.setenv("CHRONICLE_PROJECT_PATH", str(project_path))

    base = default_policy_profile().to_dict()
    base["profile_id"] = "policy_strict_test"
    base["display_name"] = "Strict test profile"
    base["mes_rules"][0]["min_independent_sources"] = 3
    strict_profile = PolicyProfile.from_dict(base)
    import_policy_to_project(project_path, strict_profile, activate=False)

    with TestClient(app) as client:
        inv_uid, _ = _create_investigation(client)
        response = client.get(
            f"/investigations/{inv_uid}/policy-compatibility",
            params={
                "viewing_profile_id": "policy_strict_test",
                "built_under_profile_id": "policy_investigative_journalism",
            },
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["investigation_uid"] == inv_uid
        assert body["built_under"] == "policy_investigative_journalism"
        assert body["viewing_under"] == "policy_strict_test"
        assert isinstance(body.get("deltas"), list)
        assert any("min_independent_sources" in d.get("rule", "") for d in body["deltas"])


def test_api_policy_sensitivity_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Policy sensitivity endpoint returns profile and pairwise comparison deltas."""
    project_path = tmp_path / "api-policy-sensitivity"
    monkeypatch.setenv("CHRONICLE_PROJECT_PATH", str(project_path))

    permissive = default_policy_profile().to_dict()
    permissive["profile_id"] = "policy_permissive_test"
    permissive["display_name"] = "Permissive test profile"
    permissive["mes_rules"][0]["min_independent_sources"] = 0
    permissive_profile = PolicyProfile.from_dict(permissive)
    import_policy_to_project(project_path, permissive_profile, activate=False)

    strict = default_policy_profile().to_dict()
    strict["profile_id"] = "policy_strict_test"
    strict["display_name"] = "Strict test profile"
    strict["mes_rules"][0]["min_independent_sources"] = 2
    strict_profile = PolicyProfile.from_dict(strict)
    import_policy_to_project(project_path, strict_profile, activate=False)

    with TestClient(app) as client:
        inv_uid, _ = _create_investigation(client)
        _seed_claim_flow(client, inv_uid)

        response = client.get(
            f"/investigations/{inv_uid}/policy-sensitivity",
            params=[
                ("profile_id", "policy_permissive_test"),
                ("profile_id", "policy_strict_test"),
                ("built_under_profile_id", "policy_permissive_test"),
                ("limit_claims", "50"),
            ],
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["investigation_uid"] == inv_uid
        assert [p["profile_id"] for p in body["selected_profiles"]] == [
            "policy_permissive_test",
            "policy_strict_test",
        ]
        assert len(body["pairwise_deltas"]) == 1
        assert body["pairwise_deltas"][0]["summary"]["changed_count"] >= 1
        assert isinstance(body.get("practical_review_implications"), list)


def test_api_reviewer_decision_ledger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reviewer decision ledger endpoint returns decisions summary and unresolved tensions."""
    project_path = tmp_path / "api-reviewer-ledger"
    monkeypatch.setenv("CHRONICLE_PROJECT_PATH", str(project_path))

    with TestClient(app) as client:
        inv_uid, _ = _create_investigation(client)

        claim_a = client.post(
            f"/investigations/{inv_uid}/claims",
            json={"text": "Claim A"},
            headers={"X-Actor-Id": "api_reviewer", "X-Actor-Type": "human"},
        )
        assert claim_a.status_code == 200, claim_a.text
        claim_a_uid = claim_a.json()["claim_uid"]

        claim_b = client.post(
            f"/investigations/{inv_uid}/claims",
            json={"text": "Claim B"},
            headers={"X-Actor-Id": "api_reviewer", "X-Actor-Type": "human"},
        )
        assert claim_b.status_code == 200, claim_b.text
        claim_b_uid = claim_b.json()["claim_uid"]

        tension = client.post(
            f"/investigations/{inv_uid}/tensions",
            json={
                "claim_a_uid": claim_a_uid,
                "claim_b_uid": claim_b_uid,
                "tension_kind": "contradiction",
            },
            headers={"X-Actor-Id": "api_reviewer", "X-Actor-Type": "human"},
        )
        assert tension.status_code == 200, tension.text

        tier = client.post(
            f"/investigations/{inv_uid}/tier",
            json={"tier": "forge", "reason": "Escalate to review"},
            headers={"X-Actor-Id": "api_reviewer", "X-Actor-Type": "human"},
        )
        assert tier.status_code == 200, tier.text

        ledger = client.get(
            f"/investigations/{inv_uid}/reviewer-decision-ledger",
            params={"limit": 200},
        )
        assert ledger.status_code == 200, ledger.text
        body = ledger.json()
        assert body["investigation_uid"] == inv_uid
        assert isinstance(body.get("decisions"), list)
        assert isinstance(body.get("unresolved_tensions"), list)
        assert any(d.get("decision_kind") == "tier_changed" for d in body["decisions"])
        assert body["summary"]["tier_changed_count"] >= 1
        assert body["summary"]["unresolved_tensions_count"] >= 1


def test_api_review_packet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unified review packet endpoint returns combined packet sections."""
    project_path = tmp_path / "api-review-packet"
    monkeypatch.setenv("CHRONICLE_PROJECT_PATH", str(project_path))

    with TestClient(app) as client:
        inv_uid, _ = _create_investigation(client)
        claim = client.post(
            f"/investigations/{inv_uid}/claims",
            json={"text": "Packet claim"},
            headers={"X-Actor-Id": "api_reviewer", "X-Actor-Type": "human"},
        )
        assert claim.status_code == 200, claim.text

        packet = client.get(
            f"/investigations/{inv_uid}/review-packet",
            params={"limit_claims": 50, "decision_limit": 100},
        )
        assert packet.status_code == 200, packet.text
        body = packet.json()
        assert body["investigation_uid"] == inv_uid
        assert "policy_compatibility" in body
        assert "policy_rationale_summary" in body
        assert "reviewer_decision_ledger" in body
        assert "audit_export_bundle" in body
