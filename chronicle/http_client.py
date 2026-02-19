"""Thin HTTP client for the Chronicle API."""

from __future__ import annotations

import base64
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

    @staticmethod
    def _quote(value: str) -> str:
        return urllib.parse.quote(value, safe="")

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
        """Ensure project path is configured and reachable.

        The API auto-initializes on first project endpoint access, so there is no
        explicit /project/init route.
        """
        self._request("GET", "/health")

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
        if isinstance(out, dict):
            invs = out.get("investigations")
            if isinstance(invs, list):
                return cast(list[dict[str, Any]], invs)
        return []

    def get_investigation(self, investigation_uid: str) -> dict[str, Any]:
        """GET /investigations/{uid} — one investigation (title, description, etc.). E.5."""
        out = self._request(
            "GET", f"/investigations/{self._quote(investigation_uid)}"
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
        """GET /investigations/{uid}/claims — list claims for an investigation."""
        params: dict[str, str | int | bool | None] = {
            "include_withdrawn": include_withdrawn,
        }
        if limit is not None:
            params["limit"] = limit
        out = self._request(
            "GET",
            f"/investigations/{self._quote(investigation_uid)}/claims",
            params=params,
        )
        if isinstance(out, dict):
            claims = out.get("claims")
            if isinstance(claims, list):
                return cast(list[dict[str, Any]], claims)
        return []

    def list_evidence(self, investigation_uid: str) -> list[dict[str, Any]]:
        """GET /investigations/{uid}/evidence — list evidence items. E.5."""
        out = self._request(
            "GET",
            f"/investigations/{self._quote(investigation_uid)}/evidence",
        )
        if isinstance(out, dict):
            evidence = out.get("evidence")
            if isinstance(evidence, list):
                return cast(list[dict[str, Any]], evidence)
        return []

    def get_investigation_defensibility(
        self,
        investigation_uid: str,
        *,
        use_strength_weighting: bool = False,
    ) -> dict[str, Any]:
        """Compute batch defensibility by listing claims and fetching each scorecard."""
        claims = self.list_claims(investigation_uid, include_withdrawn=False)
        defensibility_by_claim: dict[str, Any] = {}
        for claim in claims:
            claim_uid = claim.get("claim_uid")
            if not isinstance(claim_uid, str) or not claim_uid:
                continue
            params: dict[str, str | int | bool | None] | None = None
            if use_strength_weighting:
                params = {"use_strength_weighting": True}
            try:
                score = self._request(
                    "GET",
                    f"/claims/{self._quote(claim_uid)}/defensibility",
                    params=params,
                )
            except ChronicleClientError as e:
                if e.status == 404:
                    continue
                raise
            defensibility_by_claim[claim_uid] = score
        return {
            "investigation_uid": investigation_uid,
            "defensibility_by_claim": defensibility_by_claim,
        }

    def get_investigation_graph(self, investigation_uid: str) -> dict[str, Any]:
        """GET /investigations/{uid}/graph — nodes (claims, evidence) and edges (support, challenge). E.5."""
        out = self._request(
            "GET",
            f"/investigations/{self._quote(investigation_uid)}/graph",
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
                f"/investigations/{self._quote(investigation_uid)}/claims",
                body={"text": text},
                idempotency_key=idempotency_key,
            ),
        )

    def get_defensibility(self, claim_uid: str) -> dict[str, Any] | None:
        """GET /claims/{uid}/defensibility — scorecard for a claim."""
        return cast(
            dict[str, Any] | None,
            self._request("GET", f"/claims/{self._quote(claim_uid)}/defensibility"),
        )

    def get_submission_package(
        self,
        investigation_uid: str,
        *,
        include_chain_of_custody: bool = False,
    ) -> bytes:
        """POST /investigations/{uid}/submission-package — ZIP bytes.

        include_chain_of_custody is reserved for compatibility and currently ignored
        by the API.
        """
        _ = include_chain_of_custody
        path = f"/investigations/{self._quote(investigation_uid)}/submission-package"
        return cast(bytes, self._request("POST", path, parse_json=False))

    def ingest_evidence(
        self,
        investigation_uid: str,
        content: str | bytes,
        *,
        original_filename: str = "evidence",
        media_type: str = "text/plain",
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """POST /investigations/{uid}/evidence — ingest text or binary evidence."""
        body: dict[str, Any] = {
            "original_filename": original_filename,
            "media_type": media_type,
        }
        if isinstance(content, str):
            body["content"] = content
        else:
            body["content_base64"] = base64.b64encode(content).decode("ascii")
        return cast(
            dict[str, Any],
            self._request(
                "POST",
                f"/investigations/{self._quote(investigation_uid)}/evidence",
                body=body,
                idempotency_key=idempotency_key,
            ),
        )

    def ingest_evidence_from_url(
        self,
        investigation_uid: str,
        url: str,
        *,
        title: str | None = None,
        provenance_type: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Fetch URL client-side, then ingest via /investigations/{uid}/evidence.

        The API intentionally does not provide a server-side from-url endpoint.
        """
        req = urllib.request.Request(url[:4096], method="GET")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                blob = resp.read()
                mt = resp.headers.get_content_type() or "application/octet-stream"
        except urllib.error.URLError as e:
            raise ChronicleClientError(f"URL fetch failed: {e}") from e
        filename = (title or "").strip() or Path(urllib.parse.urlparse(url).path).name or "evidence"
        body: dict[str, Any] = {
            "content_base64": base64.b64encode(blob).decode("ascii"),
            "original_filename": filename[:500],
            "media_type": mt,
        }
        if provenance_type:
            body["provenance_type"] = provenance_type
        return cast(
            dict[str, Any],
            self._request(
                "POST",
                f"/investigations/{self._quote(investigation_uid)}/evidence",
                body=body,
                idempotency_key=idempotency_key,
            ),
        )
