"""Contract tests for chronicle.http_client against documented API routes."""

from __future__ import annotations

from typing import Any

from chronicle.http_client import ChronicleClient, ChronicleClientError


def test_init_project_uses_health_endpoint(monkeypatch: Any) -> None:
    """init_project should validate API/project via GET /health."""
    calls: list[tuple[str, str]] = []

    def fake_request(self: ChronicleClient, method: str, path: str, **_: Any) -> dict[str, str]:
        calls.append((method, path))
        return {"status": "ok"}

    monkeypatch.setattr(ChronicleClient, "_request", fake_request)
    client = ChronicleClient("http://api", "/tmp/project")
    client.init_project()
    assert calls == [("GET", "/health")]


def test_list_investigations_unwraps_envelope(monkeypatch: Any) -> None:
    """list_investigations should return the investigations array from API envelope."""

    def fake_request(self: ChronicleClient, method: str, path: str, **_: Any) -> dict[str, Any]:
        assert method == "GET"
        assert path == "/investigations"
        return {"investigations": [{"investigation_uid": "inv_1", "title": "One"}]}

    monkeypatch.setattr(ChronicleClient, "_request", fake_request)
    client = ChronicleClient("http://api", "/tmp/project")
    invs = client.list_investigations(limit=5)
    assert len(invs) == 1
    assert invs[0]["investigation_uid"] == "inv_1"


def test_list_claims_uses_investigation_scoped_route(monkeypatch: Any) -> None:
    """list_claims should call /investigations/{uid}/claims and unwrap claims list."""
    seen: list[tuple[str, str, dict[str, Any] | None]] = []

    def fake_request(
        self: ChronicleClient,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        seen.append((method, path, params))
        return {"claims": [{"claim_uid": "claim_1"}]}

    monkeypatch.setattr(ChronicleClient, "_request", fake_request)
    client = ChronicleClient("http://api", "/tmp/project")
    claims = client.list_claims("inv/with space", include_withdrawn=False, limit=10)
    assert claims == [{"claim_uid": "claim_1"}]
    assert seen == [
        (
            "GET",
            "/investigations/inv%2Fwith%20space/claims",
            {"include_withdrawn": False, "limit": 10},
        )
    ]


def test_get_submission_package_uses_post(monkeypatch: Any) -> None:
    """get_submission_package should call POST /investigations/{uid}/submission-package."""
    seen: list[tuple[str, str, bool]] = []

    def fake_request(
        self: ChronicleClient,
        method: str,
        path: str,
        *,
        parse_json: bool = True,
        **_: Any,
    ) -> bytes:
        seen.append((method, path, parse_json))
        return b"zip-bytes"

    monkeypatch.setattr(ChronicleClient, "_request", fake_request)
    client = ChronicleClient("http://api", "/tmp/project")
    out = client.get_submission_package("inv_1")
    assert out == b"zip-bytes"
    assert seen == [("POST", "/investigations/inv_1/submission-package", False)]


def test_get_investigation_defensibility_fans_out_by_claim(monkeypatch: Any) -> None:
    """Batch defensibility should query claim defensibility and skip 404 claims."""

    def fake_request(self: ChronicleClient, method: str, path: str, **_: Any) -> Any:
        if path.startswith("/investigations/") and path.endswith("/claims"):
            return {"claims": [{"claim_uid": "c1"}, {"claim_uid": "c404"}]}
        if path == "/claims/c1/defensibility":
            return {"claim_uid": "c1", "score": 0.9}
        if path == "/claims/c404/defensibility":
            raise ChronicleClientError("not found", status=404)
        raise AssertionError(f"unexpected call: {method} {path}")

    monkeypatch.setattr(ChronicleClient, "_request", fake_request)
    client = ChronicleClient("http://api", "/tmp/project")
    out = client.get_investigation_defensibility("inv_1")
    assert out["investigation_uid"] == "inv_1"
    assert out["defensibility_by_claim"] == {"c1": {"claim_uid": "c1", "score": 0.9}}

