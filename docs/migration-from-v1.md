# What we brought from ChronicleV1 (and what we didn't)

This doc lists what was brought into the RAG/evals Chronicle repo from the old project (ChronicleV1), what was left behind, and why. Goal: **only what we need for a focused RAG/evals story** — scorer, verifier, defensibility model, and eval story — without pulling in product surface that doesn't serve that focus.

---

## Brought over

### Chronicle package (`chronicle/`) — **except** `api/`

| Area | What | Why |
|------|------|-----|
| **core/** | events, payloads, uid, errors, validation, identity, encryption, policy, policy_compat, ssrf | Needed for event model, commands, and session. |
| **store/** | session, schema, sqlite/postgres event stores, read_model (projection, models, sqlite_read_model), commands/*, evidence_store, claim_embedding_store, export_import, project, protocols | Full read model and command layer; defensibility and scorecard live here. Session API is how the scorer and integrations run. |
| **store/neo4j_export.py, neo4j_sync.py** | CSV export and direct Neo4j sync | Optional graph projection; useful for multi-run analysis (see [Neo4j](neo4j.md)). Kept as optional, no default dependency. |
| **cli/main.py** | CLI including neo4j-export, neo4j-sync, project/claim/evidence commands | Needed for project init, neo4j export/sync, and any local use; scorer does not require it. |
| **eval_metrics.py** | Defensibility metrics for claim (stable shape for evals) | Core to the eval contract and harness. |
| **integrations/** | LangChain, LlamaIndex, Haystack | Optional RAG hooks; evals and demos can use them. |
| **tools/** | decomposer, type_scope_inference, contradiction, embeddings, evidence_temporal, llm_client/config, embedding_config | Used by session/evidence/claims flows (e.g. type inference, contradiction detection); scorer path can stay minimal but package stays coherent. |
| **http_client.py, verify.py** | HTTP client for API; verify for .chronicle checks | Client useful when someone runs an API elsewhere; verifier is standalone and critical. |

**Not brought: `chronicle/api/`** — Routers, FastAPI app, deps, webhook, Neo4j client, tension cache, static (verifier.html, learn guides). The RAG/evals product is scorer + verifier + session API; a separate API/frontend can live in this repo or another (see [To-do](to_do.md)). Leaving it out keeps this repo focused and dependency-light.

---

## Not brought (and why)

| Category | What | Why |
|----------|------|-----|
| **API and server** | `chronicle/api/` (app, routers, deps, schemas, static) | Out of scope for this focus: no HTTP server, no auth, no web UI. Integrations use session API or scorer stdin/stdout. |
| **Frontend** | `frontend/` (full UI) | Out of scope. Eval users need scorer output and .chronicle verification, not the full app UI. |
| **Tests** | `tests/` | Not copied to avoid carrying suite that targets API/frontend. A focused test set (scorer, session, verifier) exists in this repo. |
| **Spec docs** | `docs/spec/` (index, schemas, core-entities, epistemic-tools, etc.) | Large spec surface; not needed to run scorer or verifier. Technical report and defensibility/eval docs are the source of truth here. Some in-repo links still point to spec — we can fix those to point to technical-report or remove. |
| **Most of docs/** | ~85 other docs (roadmap, vision, deployment, security reviews, verticals, learn, integration-story, etc.) | Only eval- and defensibility-critical docs were brought: eval_contract, eval_contract_schema.json, defensibility-metrics-schema, eval-and-benchmarking, technical-report, verifier. Keeps the repo readable and avoids outdated product/process docs. |
| **Benchmark sample data** | `benchmark/`, `docs/benchmark.md` | Sample investigations and benchmark doc not copied. Scripts reference them; we can add a minimal benchmark/samples or point to "generate with script" only. |
| **CI / dev tooling** | `.github/`, `.pre-commit-config.yaml`, coverage/mypy/ruff config for api | New repo can add minimal CI (e.g. lint, scorer smoke test) without the full V1 matrix. |
| **Other** | CHANGELOG, CONTRIBUTING (V1-specific), logo, .env.example, uv.lock | Changelog/contributing can be rewritten for this repo; logo/env/lock are optional. |

---

## Scripts and tools

| Brought | Not brought | Why |
|---------|-------------|-----|
| **scripts/standalone_defensibility_scorer.py** | — | Core: (query, answer, evidence) in, defensibility JSON out. |
| **scripts/benchmark_data/** (e.g. run_defensibility_benchmark, generate_benchmark_samples, export_for_ml, evals_to_preference_pair, etc.) | — | Supports benchmark and training-data export; some assume API or full project (we may prune or document assumptions). |
| **scripts/eval_harness_adapter.py** | — | Single RAG run + metrics out; depends on LangChain + Chronicle integration. |
| **scripts/*_rag_chronicle.py** (langchain, llamaindex, haystack, cross_framework) | — | Demo integrations; optional. |
| **scripts/ai_validation/, scripts/verticals/** | — | Brought as-is; first-class vs optional is in [scripts/README](../scripts/README.md). Pruning is in [To-do](to_do.md) if needed. |
| **scripts/** (normalize_quotes_in_docs, check_doc_links, generate_sample_chronicle, etc.) | — | Utility and demos; keep or prune by use. |
| **tools/verify_chronicle/** | — | Standalone verifier; required. |

So: we brought **all scripts** from V1. Some are directly relevant (scorer, benchmark runner, eval harness adapter, verify_chronicle); others are demos or utilities. Pruning scripts to "only what we need" is a good next pass (see below).

---

## Docs in this repo (after migration)

- **eval_contract.md**, **eval_contract_schema.json** — Contract for scorer and harnesses.
- **defensibility-metrics-schema.md** — Stable metrics shape.
- **eval-and-benchmarking.md** — How to run pipelines and report.
- **technical-report.md** — Defensibility definition, schema, evaluation.
- **verifier.md** — How to verify a .chronicle file.
- **neo4j.md** — Optional Neo4j use (added in new repo).
- **epistemology-scope.md** — What we cover epistemically (added in new repo).

Some of these still **link to missing docs** (e.g. `spec/index.md`, `benchmark.md`, `verification-guarantees.md`, `integrating-with-chronicle.md`, `chronicle-as-training-data.md`). Options: (1) copy over only the minimal sections we need into this repo, or (2) remove or rewrite the links so they don't point at missing files.

---

## Neo4j

- **Brought:** `chronicle/store/neo4j_export.py`, `neo4j_sync.py`, CLI commands `neo4j-export` and `neo4j-sync`, and the **neo4j/rebuild/** Cypher scripts (from V1).
- **Why:** Optional graph view for multi-run analysis and lineage; documented in [Neo4j](neo4j.md). Not required for scorer or verifier.

---

## Summary

| We have | We don't have (by choice) |
|---------|----------------------------|
| Full event-sourced kernel (core + store, no API) | API, frontend, full spec docs |
| Scorer, verifier, session API, eval_metrics | Tests, CI, most product/process docs |
| Eval-focused docs + neo4j + epistemology scope | Benchmark sample data, verification-guarantees, integrating-with-chronicle (as files) |
| All V1 scripts (some to prune) | — |

**Suggested next steps**

1. **Prune scripts** — Keep scorer, verify_chronicle, run_defensibility_benchmark, eval_harness_adapter, export_for_ml, and RAG demo scripts; drop or archive scripts that only serve the old API/UI (e.g. start_chronicle.sh, or ai_validation if it depends on API).
2. **Fix broken doc links** — Either add minimal in-repo versions of benchmark.md, verification-guarantees.md, integrating-with-chronicle.md (and spec pointers) or change technical-report and other docs to reference only existing files.
3. **Add minimal tests** — For scorer and session (and optionally verifier) so we can refactor safely.
4. **Leave API/frontend in V1** — Until we decide to host a reference API or UI, keep this repo "library + CLI + scorer + verifier + docs."
