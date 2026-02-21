# What we brought from ChronicleV1 (and what we didn't)

This document is a historical migration snapshot from the initial ChronicleV1 import. It explains what was brought first, what was deferred, and why.

Current repo state has evolved since then (including API/frontend/tests/docs additions). For current architecture and status, see [Docs index](README.md), [Core vs reference architecture](architecture-core-reference.md), and [To-do](to_do.md).

---

## Brought over (initial migration phase)

### Chronicle package (`chronicle/`) — initial migration excluded `api/`

| Area | What | Why |
|------|------|-----|
| core/ | events, payloads, uid, errors, validation, identity, encryption, policy, policy_compat, ssrf | Needed for event model, commands, and session. |
| store/ | session, schema, sqlite/postgres event stores, read_model (projection, models, sqlite_read_model), commands/*, evidence_store, claim_embedding_store, export_import, project, protocols | Full read model and command layer; defensibility and scorecard live here. Session API is how the scorer and integrations run. |
| store/neo4j_export.py, neo4j_sync.py | CSV export and direct Neo4j sync | Optional graph projection; useful for multi-run analysis (see [Neo4j](neo4j.md)). Kept as optional, no default dependency. |
| cli/main.py | CLI including neo4j-export, neo4j-sync, project/claim/evidence commands | Needed for project init, neo4j export/sync, and any local use; scorer does not require it. |
| eval_metrics.py | Defensibility metrics for claim (stable shape for evals) | Core to the eval contract and harness. |
| integrations/ | LangChain, LlamaIndex, Haystack | Optional RAG hooks; evals and demos can use them. |
| tools/ | decomposer, type_scope_inference, contradiction, embeddings, evidence_temporal, llm_client/config, embedding_config | Used by session/evidence/claims flows (e.g. type inference, contradiction detection); scorer path can stay minimal but package stays coherent. |
| http_client.py, verify.py | HTTP client for API; verify for .chronicle checks | Client useful when someone runs an API elsewhere; verifier is standalone and critical. |

Historical note: `chronicle/api/` was intentionally deferred in the initial migration to keep first import scope small. API support now exists in this repo.

---

## Not brought at initial migration time (and why)

| Category | What | Why |
|----------|------|-----|
| API and server | `chronicle/api/` (app, routers, deps, schemas, static) | Deferred in first migration phase to keep scope tight. |
| Frontend | `frontend/` (full UI) | Deferred in first migration phase. |
| Tests | `tests/` | Migration note from first pass; test coverage has since been expanded in this repo. |
| Spec docs | `docs/spec/` (index, schemas, core-entities, epistemic-tools, etc.) | Large spec surface; not needed to run scorer or verifier. Technical report and defensibility/eval docs are the source of truth here. Some in-repo links still point to spec — we can fix those to point to technical-report or remove. |
| Most of docs/ | ~85 other docs (roadmap, vision, deployment, security reviews, verticals, learn, integration-story, etc.) | Only eval- and defensibility-critical docs were brought: eval_contract, eval_contract_schema.json, defensibility-metrics-schema, eval-and-benchmarking, technical-report, verifier. Keeps the repo readable and avoids outdated product/process docs. |
| Benchmark sample data | `benchmark/`, `docs/benchmark.md` | Sample investigations and benchmark doc not copied. Scripts reference them; we can add a minimal benchmark/samples or point to "generate with script" only. |
| CI / dev tooling | `.github/`, `.pre-commit-config.yaml`, coverage/mypy/ruff config for api | New repo can add minimal CI (e.g. lint, scorer smoke test) without the full V1 matrix. |
| Other | CHANGELOG, CONTRIBUTING (V1-specific), logo, .env.example, uv.lock | Changelog/contributing can be rewritten for this repo; logo/env/lock are optional. |

---

## Scripts and tools

| Brought | Not brought | Why |
|---------|-------------|-----|
| scripts/standalone_defensibility_scorer.py | — | Core: (query, answer, evidence) in, defensibility JSON out. |
| scripts/benchmark_data/ (e.g. run_defensibility_benchmark, generate_benchmark_samples, export_for_ml, evals_to_preference_pair, etc.) | — | Supports benchmark and training-data export; some assume API or full project (we may prune or document assumptions). |
| scripts/eval_harness_adapter.py | — | Single RAG run + metrics out; depends on LangChain + Chronicle integration. |
| **scripts/*_rag_chronicle.py** (langchain, llamaindex, haystack, cross_framework) | — | Demo integrations; optional. |
| scripts/ai_validation/, scripts/verticals/ | — | Brought as-is; first-class vs optional is in [scripts/README](../scripts/README.md). Pruning is in [To-do](to_do.md) if needed. |
| scripts/ (normalize_quotes_in_docs, check_doc_links, generate_sample_chronicle, etc.) | — | Utility and demos; keep or prune by use. |
| tools/verify_chronicle/ | — | Standalone verifier; required. |

So: we brought all scripts from V1. Some are directly relevant (scorer, benchmark runner, eval harness adapter, verify_chronicle); others are demos or utilities. Pruning scripts to "only what we need" is a good next pass (see below).

---

## Docs in this repo (initial migration snapshot)

- eval_contract.md, eval_contract_schema.json — Contract for scorer and harnesses.
- **defensibility-metrics-schema.md** — Stable metrics shape.
- **eval-and-benchmarking.md** — How to run pipelines and report.
- **technical-report.md** — Defensibility definition, schema, evaluation.
- **verifier.md** — How to verify a .chronicle file.
- **neo4j.md** — Optional Neo4j use (added in new repo).
- **epistemology-scope.md** — What we cover epistemically (added in new repo).

At migration time, some of these linked to missing docs. Those link gaps were later addressed in the current repo.

---

## Neo4j

- Brought: `chronicle/store/neo4j_export.py`, `neo4j_sync.py`, CLI commands `neo4j-export` and `neo4j-sync`, and the neo4j/rebuild/ Cypher scripts (from V1).
- Why: Optional graph view for multi-run analysis and lineage; documented in [Neo4j](neo4j.md). Not required for scorer or verifier.

---

## Historical summary (initial migration)

| We had in first migration pass | Deferred in first migration pass |
|---------|----------------------------|
| Full event-sourced kernel (core + store) | API, frontend, full spec docs |
| Scorer, verifier, session API, eval_metrics | Broader test/CI/doc surface |
| Eval-focused docs + neo4j + epistemology scope | Some benchmark/docs pieces |
| All V1 scripts (some to prune) | — |

## Current status (brief)

- API, frontend, and expanded tests are now present in this repository.
- Documentation coverage is broader than the initial migration snapshot.
- Use this file as historical context for migration decisions, not as current feature inventory.

**Historical suggested next steps (from migration period)**

1. **Prune scripts** — Keep scorer, verify_chronicle, run_defensibility_benchmark, eval_harness_adapter, export_for_ml, and RAG demo scripts; drop or archive scripts that only serve the old API/UI (e.g. start_chronicle.sh, or ai_validation if it depends on API).
2. **Fix broken doc links** — Either add minimal in-repo versions of benchmark.md, verification-guarantees.md, integrating-with-chronicle.md (and spec pointers) or change technical-report and other docs to reference only existing files.
3. **Add minimal tests** — For scorer and session (and optionally verifier) so we can refactor safely.
4. **Reference UI in same repo** — When we add a human-in-the-loop UI, it will live in this repo under `frontend/` (same repo, no separate frontend repo). See [Reference UI plan](reference-ui-plan.md) for what we will bring from V1 (friction tiers, Propose–Confirm, Reading-lite) and why we keep one repo.

5. **Full V1 scan and migration plan** — A complete scan of ChronicleV1 was done to find anything V1 did better that we should add here. The consolidated list (docs to add or adapt, API surface to expose, policy examples) lives in [Reference UI plan — Additional items from V1 scan](reference-ui-plan.md#additional-items-from-v1-scan-to-bring-or-adapt). Summary: Docs — Quickstart/Learn flow, zero-to-submission path, reasoning brief as primary artifact, when-to-use-Chronicle, building-with-Chronicle one-pager, Propose–Confirm UX philosophy, dismissal-as-data, optional Learn guides. API — Expose set tier + tier history, tension suggestions (list/confirm/dismiss), optional submission package. Policy — Example policy profile JSONs per vertical. Backend already has tier, tier history, suggestions, and reasoning brief; the gap is mainly API exposure and docs/onboarding.
