#!/usr/bin/env python3
"""Generate docs/agent-tools.json from the Chronicle API OpenAPI schema for LLM agents.

Run from repo root: PYTHONPATH=. python3 scripts/generate_agent_tools.py

Output: docs/agent-tools.json — a list of tools in OpenAI-style function-calling format
(type: "function", function: { name, description, parameters }) plus a short
note that all requests require X-Project-Path (or project_path query) and may use
Idempotency-Key and X-Actor-Id / X-Actor-Type. See docs/integrating-with-chronicle.md.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Repo root = parent of scripts/
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from chronicle.api.app import app  # noqa: E402


def _slug(path: str, method: str) -> str:
    """Return a safe identifier from path and method (e.g. post_investigations)."""
    path_part = path.strip("/").replace("/", "_").replace("{", "").replace("}", "")
    path_part = re.sub(r"[^a-zA-Z0-9_]", "_", path_part)
    path_part = re.sub(r"_+", "_", path_part).strip("_") or "root"
    return f"{method.lower()}_{path_part}"


def _openapi_params_to_schema(parameters: list[dict] | None, path: str) -> tuple[dict, list[str]]:
    """Convert OpenAPI parameters (path, query, header) to JSON Schema properties and required list."""
    if not parameters:
        return {}, []
    properties: dict = {}
    required: list[str] = []
    for p in parameters:
        if p.get("in") not in ("path", "query"):
            continue
        name = p.get("name")
        if not name:
            continue
        schema = p.get("schema") or {}
        prop: dict = {"description": p.get("description") or ""}
        if "type" in schema:
            prop["type"] = schema["type"]
        elif "$ref" in schema:
            prop["type"] = "object"
            prop["description"] = (prop["description"] or "") + " (see OpenAPI schema)"
        else:
            prop["type"] = schema.get("type", "string")
        if "enum" in schema:
            prop["enum"] = schema["enum"]
        properties[name] = prop
        if p.get("required", False):
            required.append(name)
    return {"type": "object", "properties": properties, "required": required}, required


def _get_request_body_schema(request_body: dict | None) -> dict | None:
    """Extract JSON schema from requestBody if present."""
    if not request_body:
        return None
    content = request_body.get("content") or {}
    json_media = content.get("application/json") or content.get("application/*")
    if not json_media:
        return None
    return json_media.get("schema")


def _merge_body_into_params(
    params_schema: dict, body_schema: dict | None, path: str
) -> dict:
    """Merge request body schema into params. If body has properties, add as top-level or under 'body'."""
    if not body_schema:
        return params_schema
    # Resolve simple inline schema only (no $ref)
    props = (params_schema.get("properties") or {}).copy()
    req = list(params_schema.get("required") or [])
    body_props = body_schema.get("properties")
    if body_props:
        for k, v in body_props.items():
            props[k] = {"type": v.get("type", "string"), "description": v.get("description") or ""}
        body_req = body_schema.get("required") or []
        req = list(set(req) + set(body_req))
    else:
        props["body"] = {"type": "object", "description": "Request body; see OpenAPI for shape"}
        req.append("body")
    return {"type": "object", "properties": props, "required": sorted(set(req))}


def build_tools() -> list[dict]:
    """Build list of tool definitions from app OpenAPI schema."""
    openapi = app.openapi()
    paths = openapi.get("paths") or {}
    tools: list[dict] = []
    for path, path_item in paths.items():
        for method in ("get", "post", "put", "patch", "delete"):
            op = path_item.get(method)
            if not op:
                continue
            name = op.get("operationId") or _slug(path, method)
            description = op.get("summary") or op.get("description") or f"{method.upper()} {path}"
            params_list = (path_item.get("parameters") or []) + (op.get("parameters") or [])
            params_schema, _ = _openapi_params_to_schema(params_list, path)
            body_schema = _get_request_body_schema(op.get("requestBody"))
            params_schema = _merge_body_into_params(params_schema, body_schema, path)
            if not (params_schema.get("properties")):
                params_schema = {"type": "object", "properties": {}, "required": []}
            tools.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": params_schema,
                },
            })
    return tools


def main() -> None:
    tools = build_tools()
    out_path = REPO_ROOT / "docs" / "agent-tools.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "description": (
            "Chronicle API tools for LLM agents. All requests require X-Project-Path header "
            "(or project_path query). Create endpoints accept optional Idempotency-Key; "
            "use X-Actor-Id and X-Actor-Type for actor. See docs/integrating-with-chronicle.md."
        ),
        "tools": tools,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(tools)} tools to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
