# Chapter 05: Integration

Contents: Add defensibility to your harness; session API; optional HTTP API and adapters.

---

## Add defensibility to your harness

Use the same [eval contract](../eval_contract.md): for each run, build (query, answer, evidence), call the scorer (stdin or in-process), record the metrics. See [RAG evals: defensibility metric](../rag-evals-defensibility-metric.md) and [Integration quick reference](../integration-quick-reference.md).

---

## Session API (project-based)

For workflows that keep a project (investigations, evidence, claims, links): use ChronicleSession — create_investigation, ingest_evidence, propose_claim, link_support, get_defensibility_score. The scorer uses this under the hood with a temp project. See [Integrating with Chronicle](../integrating-with-chronicle.md) and [RAG in 5 minutes](../rag-in-5-minutes.md).

---

## Optional: HTTP API and adapters

- **HTTP API** — `pip install -e ".[api]"`; POST /score for scorer-as-a-service; full project API for write/read/export. See [API](../api.md).
- **Adapters** — Example adapters in `scripts/adapters/` (RAG→scorer, fact-checker→Chronicle, provenance→Chronicle). Copy-paste templates.

Identity: For API writes, set `X-Actor-Id` and `X-Actor-Type` (or use an IdP); see [Identity providers](../identity-providers.md) and [Human-in-the-loop](../human-in-the-loop-and-attestation.md).

---

← Previous: [04 — .chronicle format](04-chronicle-format.md) | Index: [Manual](README.md) | Next →: [06 — Limits](06-limits.md)
