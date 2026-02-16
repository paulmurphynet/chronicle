"""
Thin HTTP client for the Chronicle API (T5.3). E.5: dashboard helpers.

Use this when your pipeline or script runs in a separate process and talks to
Chronicle over HTTP. For in-process use (same Python process), use
ChronicleSession from chronicle.store.session instead.

Requires only the Python standard library. All requests use X-Project-Path;
optional X-Actor-Id, X-Actor-Type, Idempotency-Key for writes.

Example (pipeline):

    from chronicle.http_client import ChronicleClient

    client = ChronicleClient("http://localhost:8000", "/path/to/project")
    client.init_project()
    inv = client.create_investigation("My investigation")
    ev = client.ingest_evidence_from_url(inv["investigation_uid"], "https://example.com/doc.pdf")
    claim = client.propose_claim(inv["investigation_uid"], "The document states X.")
    # ... anchor span, link support (see API docs) ...
    scorecard = client.get_defensibility(claim["claim_uid"])
    zip_bytes = client.get_submission_package(inv["investigation_uid"])

Example (dashboard: list investigations, load summary, graph):

    invs = client.list_investigations(limit=20, is_archived=False)
    inv = client.get_investigation(invs[0]["investigation_uid"])
    claims = client.list_claims(inv["investigation_uid"])
    def_batch = client.get_investigation_defensibility(inv["investigation_uid"])
    graph = client.get_investigation_graph(inv["investigation_uid"])
"""

from __future__ import annotations

import contextlib
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, cast


class ChronicleClientError(Exception):
    """Raised when the API returns an error status or invalid response."""

    def __init__(self, message: str, status: int | None = None, body: Any = None):
        super().__init__(message)
        self.status = status
        self.body = body


class ChronicleClient:
    """Thin HTTP client for Chronicle API. T5.3."""

    def __init__(
        self,
        base_url: str,
        project_path: str | Path,
        *,
        actor_id: str = "default",
        actor_type: str = "human",
    ):
        self.base_url = base_url.rstrip("/")
        self.project_path = str(project_path).strip()
        self.actor_id = actor_id
        self.actor_type = actor_type

    def _headers(self, idempotency_key: str | None = None) -> dict[str, str]:
        h: dict[str, str] = {
            "X-Project-Path": self.project_path,
            "X-Actor-Id": self.actor_id,
            "X-Actor-Type": self.actor_type,
            "Content-Type": "application/json",
        }
        if idempotency_key:
            h["Idempotency-Key"] = idempotency_key.strip()
        return h

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        parse_json: bool = True,
        params: dict[str, str | int | bool | None] | None = None,
    ) -> Any:
        if params:
            q = "&".join(
                f"{k}={urllib.parse.quote(str(v), safe='')}"
                for k, v in params.items()
                if v is not None
            )
            path = f"{path}?{q}" if q else path
        url = f"{self.base_url}{path}"
        data = None
        headers = self._headers(idempotency_key)
        if body is not None:
            data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as e:
            try:
                detail = e.read().decode("utf-8")
                with contextlib.suppress(json.JSONDecodeError):
                    detail = json.loads(detail)
            except Exception:
                detail = None
            raise ChronicleClientError(
                f"API error: {e.code} {e.reason}", status=e.code, body=detail
            ) from e
        if not raw and method != "DELETE":
            return None
        if parse_json:
            return json.loads(raw.decode("utf-8"))
        return raw

    def init_project(self) -> None:
        """POST /project/init — ensure project exists."""
        self._request("POST", "/project/init", body={"project_path": self.project_path})

    def list_investigations(
        self,
        *,
        limit: int | None = None,
        is_archived: bool | None = None,
        created_since: str | None = None,
        created_before: str | None = None,
    ) -> list[dict[str, Any]]:
        """GET /investigations — list investigations. E.1/E.5: optional filters for dashboard."""
        params: dict[str, str | int | bool | None] = {}
        if limit is not None:
            params["limit"] = limit
        if is_archived is not None:
            params["is_archived"] = is_archived
        if created_since is not None:
            params["created_since"] = created_since
        if created_before is not None:
            params["created_before"] = created_before
        out = self._request("GET", "/investigations", params=params or None)
        return cast(list[dict[str, Any]], out) if isinstance(out, list) else []

    def get_investigation(self, investigation_uid: str) -> dict[str, Any]:
        """GET /investigations/{uid} — one investigation (title, description, etc.). E.5."""
        out = self._request(
            "GET", f"/investigations/{urllib.parse.quote(investigation_uid, safe='')}"
        )
        if not out:
            raise ChronicleClientError("Investigation not found", status=404, body=out)
        return cast(dict[str, Any], out)

    def list_claims(
        self,
        investigation_uid: str,
        *,
        include_withdrawn: bool = False,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """GET /claims?investigation_uid= — list claims for an investigation. E.5."""
        params: dict[str, str | int | bool | None] = {
            "investigation_uid": investigation_uid,
            "include_withdrawn": include_withdrawn,
        }
        if limit is not None:
            params["limit"] = limit
        out = self._request("GET", "/claims", params=params)
        return cast(list[dict[str, Any]], out) if isinstance(out, list) else []

    def list_evidence(self, investigation_uid: str) -> list[dict[str, Any]]:
        """GET /investigations/{uid}/evidence — list evidence items. E.5."""
        out = self._request(
            "GET",
            f"/investigations/{urllib.parse.quote(investigation_uid, safe='')}/evidence",
        )
        return cast(list[dict[str, Any]], out) if isinstance(out, list) else []

    def get_investigation_defensibility(
        self,
        investigation_uid: str,
        *,
        use_strength_weighting: bool = False,
    ) -> dict[str, Any]:
        """GET /investigations/{uid}/defensibility — batch defensibility for all claims. E.5."""
        params: dict[str, str | int | bool | None] = {}
        if use_strength_weighting:
            params["use_strength_weighting"] = True
        out = self._request(
            "GET",
            f"/investigations/{urllib.parse.quote(investigation_uid, safe='')}/defensibility",
            params=params or None,
        )
        return cast(dict[str, Any], out)

    def get_investigation_graph(self, investigation_uid: str) -> dict[str, Any]:
        """GET /investigations/{uid}/graph — nodes (claims, evidence) and edges (support, challenge). E.5."""
        out = self._request(
            "GET",
            f"/investigations/{urllib.parse.quote(investigation_uid, safe='')}/graph",
        )
        if not isinstance(out, dict):
            return {"nodes": [], "edges": []}
        return cast(dict[str, Any], {"nodes": out.get("nodes", []), "edges": out.get("edges", [])})

    def create_investigation(
        self,
        title: str,
        *,
        description: str | None = None,
        idempotency_key: str | None = None,
        investigation_key: str | None = None,
    ) -> dict[str, Any]:
        """POST /investigations — create investigation. Returns { investigation_uid, event_id }. Pass investigation_key for get-or-create (same key returns same investigation)."""
        body: dict[str, Any] = {"title": title}
        if description is not None:
            body["description"] = description
        if investigation_key is not None and (k := investigation_key.strip()):
            body["investigation_key"] = k
        return cast(
            dict[str, Any],
            self._request("POST", "/investigations", body=body, idempotency_key=idempotency_key),
        )

    def propose_claim(
        self,
        investigation_uid: str,
        text: str,
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """POST /investigations/{id}/claims — propose claim. Returns { claim_uid, event_id }."""
        return cast(
            dict[str, Any],
            self._request(
                "POST",
                f"/investigations/{investigation_uid}/claims",
                body={"text": text},
                idempotency_key=idempotency_key,
            ),
        )

    def get_defensibility(self, claim_uid: str) -> dict[str, Any] | None:
        """GET /claims/{uid}/defensibility — scorecard for a claim."""
        return cast(
            dict[str, Any] | None,
            self._request("GET", f"/claims/{claim_uid}/defensibility"),
        )

    def get_submission_package(
        self,
        investigation_uid: str,
        *,
        include_chain_of_custody: bool = False,
    ) -> bytes:
        """GET /investigations/{uid}/submission-package — ZIP bytes."""
        path = f"/investigations/{investigation_uid}/submission-package?include_chain_of_custody={str(include_chain_of_custody).lower()}"
        return cast(bytes, self._request("GET", path, parse_json=False))

    def ingest_evidence_from_url(
        self,
        investigation_uid: str,
        url: str,
        *,
        title: str | None = None,
        provenance_type: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """POST /investigations/{id}/evidence/from-url — fetch URL and ingest as evidence."""
        body: dict[str, Any] = {"url": url[:4096]}
        if title is not None:
            body["title"] = title[:500]
        if provenance_type is not None:
            body["provenance_type"] = provenance_type
        return cast(
            dict[str, Any],
            self._request(
                "POST",
                f"/investigations/{investigation_uid}/evidence/from-url",
                body=body,
                idempotency_key=idempotency_key,
            ),
        )
