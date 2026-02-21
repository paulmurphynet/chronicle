# Lesson 14: MCP agent integration

Objectives: You’ll understand Chronicle’s MCP server architecture, how tool calls map to the session/event model, what transports are available, and how to run/validate an agent integration safely.

**Key files:**

- [chronicle/mcp/server.py](../chronicle/mcp/server.py) — MCP server bootstrap, tool registration, transport options
- [chronicle/mcp/service.py](../chronicle/mcp/service.py) — thin service layer from MCP tools to Chronicle session operations
- [tests/test_mcp_service.py](../tests/test_mcp_service.py) — end-to-end MCP service behavior tests
- [docs/mcp.md](../docs/mcp.md) — install, run, client config, security notes
- [pyproject.toml](../pyproject.toml) — `chronicle-mcp` entry point and optional dependency extra `.[mcp]`

---

## Why MCP exists in Chronicle

Chronicle already exposes three integration surfaces:

1. In-process Python/session API
2. Optional HTTP API (`.[api]`)
3. Scripts/adapters/CLI orchestration

MCP adds a fourth: tool-calling for AI assistants. Instead of writing custom glue code for each assistant, Chronicle can expose a stable set of tools that assistants call directly.

---

## Server architecture

Open [chronicle/mcp/server.py](../chronicle/mcp/server.py).

The pattern is:

1. Parse runtime args (`--project-path`, `--transport`, `--host`, `--port`, `--name`)
2. Build `ChronicleMcpService(project_path)`
3. Create `FastMCP(...)`
4. Register tool functions on the server
5. `server.run(transport=...)`

Important implementation details:

- `mcp` import is lazy; if the optional extra is missing, Chronicle raises a clear runtime error telling you to install `chronicle-standard[mcp]`.
- Project path is resolved from CLI arg or `CHRONICLE_PROJECT_PATH`.
- Transport defaults to `stdio`, with `sse` and `streamable-http` also supported.

---

## Tool surface and Chronicle mapping

MCP tools are thin wrappers over the same domain operations you already learned in lessons 05/07/11:

- `chronicle_create_investigation`
- `chronicle_list_investigations`
- `chronicle_ingest_evidence_text` (auto-anchors full text span)
- `chronicle_propose_claim`
- `chronicle_list_claims`
- `chronicle_link_support`
- `chronicle_link_challenge`
- `chronicle_get_defensibility`
- `chronicle_get_reasoning_brief`
- `chronicle_export_investigation`

This means MCP is not a separate data model; it is another adapter over the same event-sourced core.

---

## Service layer behavior

Open [chronicle/mcp/service.py](../chronicle/mcp/service.py).

The service layer handles:

- Project auto-initialization if the directory does not exist yet
- Input validation (for example empty evidence text rejection)
- Command/session orchestration and return-shape normalization

Design goal: keep protocol concerns in `server.py` and Chronicle behavior in `service.py`.

---

## Testing strategy

Open [tests/test_mcp_service.py](../tests/test_mcp_service.py).

The test suite validates:

- end-to-end flow: investigation → evidence/span → claim → support link → defensibility/brief → export
- error handling (empty text rejected)

Notice this tests service behavior without requiring a full MCP client runtime. Protocol transport behavior is intentionally kept minimal and tested by runtime smoke checks.

---

## Running Chronicle MCP

Install optional dependency:

```bash
pip install -e ".[mcp]"
```

Run local stdio server (assistant integration default):

```bash
chronicle-mcp --project-path /tmp/chronicle_mcp_project
```

Run HTTP transport:

```bash
chronicle-mcp --project-path /tmp/chronicle_mcp_project --transport streamable-http --host 127.0.0.1 --port 8000
```

For client wiring, use [docs/mcp.md](../docs/mcp.md).

---

## Security and deployment boundaries

MCP is a tool-execution boundary, so apply least privilege:

- Prefer local `stdio` where possible.
- For network transports (`sse`, `streamable-http`), run behind your normal auth/network controls.
- Treat MCP clients as actors with write capability: creating investigations, proposing claims, linking evidence.
- Keep Chronicle verification posture unchanged: MCP records events; defensibility is structural and does not claim legal truth.

---

## Try it

1. Install `.[mcp]` and run `chronicle-mcp --project-path /tmp/chronicle_mcp_lesson --transport stdio`.
2. From an MCP-capable client, call `chronicle_create_investigation`, then `chronicle_ingest_evidence_text`, then `chronicle_propose_claim`.
3. Call `chronicle_link_support` and `chronicle_get_defensibility`; confirm support count reflects your link.
4. Export with `chronicle_export_investigation` to `/tmp/chronicle_mcp_lesson/export.chronicle`, then run `chronicle-verify /tmp/chronicle_mcp_lesson/export.chronicle`.
5. Run `pytest tests/test_mcp_service.py -v` and inspect what is asserted about lifecycle and validation.

---

## Summary

- Chronicle MCP is a protocol adapter over the same session/event model used by CLI/API/scripts.
- `server.py` handles MCP protocol/transport wiring; `service.py` handles Chronicle operations and validation.
- Tool calls cover investigation creation, evidence/claim lifecycle, linking, scoring, reasoning brief, and export.
- `stdio` is the default integration path; HTTP transports are available with standard deployment controls.
- `tests/test_mcp_service.py` gives a concrete behavior contract for MCP-facing operations.

---

← Previous: [Lesson 13: Release readiness, security gates, and standards operations](13-release-readiness-security-and-standards.md) | Index: [Lessons](README.md) | End of lessons

Quiz: [quizzes/quiz-14-mcp-agent-integration.md](quizzes/quiz-14-mcp-agent-integration.md)
