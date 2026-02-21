# Quiz 14: MCP agent integration

Lesson: [14-mcp-agent-integration.md](../14-mcp-agent-integration.md)

Answer these after reading the lesson and opening the linked MCP files. Try not to peek at the answer key until you've written your answers.

---

## Questions

1. Where is the `chronicle-mcp` command entry point declared, and which Python function does it call?

2. In `chronicle/mcp/server.py`, which three transport choices are accepted by `--transport`?

3. What happens if the `mcp` dependency is not installed and the server starts?

4. Which MCP tool ingests evidence text and also returns a `span_uid`? Why is returning `span_uid` useful for follow-up tool calls?

5. Which layer should own Chronicle operation semantics (`create_investigation`, `link_support`, etc.): `server.py` or `service.py`? Why?

6. Name the two MCP tools used to create positive and negative evidence links against a claim.

7. In the current design, does MCP introduce a new Chronicle data model, or does it adapt existing session/event operations?

8. Which test file covers end-to-end MCP service behavior, and what is one failure case it explicitly checks?

9. What is the recommended default transport for desktop/agent integrations, and what extra controls should you add for network transports?

10. Write the command to run Chronicle MCP on `127.0.0.1:8000` using `streamable-http` for project path `/tmp/chronicle_project`.

---

## Answer key

1. In [pyproject.toml](../../pyproject.toml): `chronicle-mcp = "chronicle.mcp.server:main"`. It calls `chronicle.mcp.server.main`.

2. `stdio`, `sse`, `streamable-http`.

3. Chronicle raises a runtime error with install guidance, indicating MCP support requires optional dependency `mcp` (install `chronicle-standard[mcp]`).

4. `chronicle_ingest_evidence_text`. Returning `span_uid` allows immediate link operations (`chronicle_link_support` / `chronicle_link_challenge`) without separate span lookup.

5. `service.py` should own Chronicle operation semantics; `server.py` should remain protocol/transport wiring. This keeps protocol adapter logic thin and domain behavior testable.

6. `chronicle_link_support` and `chronicle_link_challenge`.

7. It adapts existing session/event operations; MCP is an integration protocol surface, not a new data model.

8. `tests/test_mcp_service.py`. One explicit failure case: empty evidence text is rejected.

9. `stdio` is the recommended default. For `sse`/`streamable-http`, run behind normal auth/network controls.

10. `chronicle-mcp --project-path /tmp/chronicle_project --transport streamable-http --host 127.0.0.1 --port 8000`

---

← Previous: [quiz-13-release-readiness-security-and-standards](quiz-13-release-readiness-security-and-standards.md) | Index: [Quizzes](README.md) | End of quizzes
