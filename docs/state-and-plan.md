# Chronicle: What we have and plan going forward

## What we have so far

**Product focus:** Defensibility scoring for RAG and evals. Event-sourced evidence, claims, and defensibility; standalone scorer and .chronicle verifier. No API or frontend in this repo — "library + CLI + scorer + verifier + docs."

### Core deliverables

| Piece | What it does |
|-------|----------------|
| **Standalone defensibility scorer** | `scripts/standalone_defensibility_scorer.py`: JSON in (query, answer, evidence), defensibility metrics out. Implements the [eval contract](eval_contract.md). No RAG stack required. |
| **chronicle-verify** | CLI (`chronicle-verify`) to verify a .chronicle (ZIP) — manifest, schema, evidence hashes. Stdlib only; can verify without the Chronicle package. |
| **Chronicle package** | Event store, read model, defensibility computation, session API. Used by the scorer and by LangChain/LlamaIndex/Haystack integrations. Full command layer (claims, evidence, sources, tensions, reasoning brief, etc.); no HTTP API in this repo. |
| **Eval contract** | Stable input/output for the scorer; [eval_contract.md](eval_contract.md) and [eval_contract_schema.json](eval_contract_schema.json) for harnesses. |

### Supporting pieces

- **CLI** (`chronicle`) — Project init, neo4j-export, neo4j-sync, and other project/claim/evidence commands.
- **Neo4j** — Optional: export read model to CSV or sync to Neo4j for multi-run graph analysis; Cypher rebuild scripts in `neo4j/rebuild/`. See [Neo4j](neo4j.md).
- **Integrations** — LangChain, LlamaIndex, Haystack (optional hooks for RAG pipelines).
- **Scripts** — Benchmark runner, eval harness adapter, RAG demos, export_for_ml, ai_validation, verticals, utilities. Some are essential; others are candidates to prune (see plan below).

### Docs

- **Eval and defensibility:** [Eval contract](eval_contract.md), [eval contract schema](eval_contract_schema.json), [Defensibility metrics schema](defensibility-metrics-schema.md), [Eval and benchmarking](eval-and-benchmarking.md), [Technical report](technical-report.md).
- **Verification:** [Verifier](verifier.md).
- **Context:** [Neo4j](neo4j.md), [Epistemology scope](epistemology-scope.md), [Migration from V1](migration-from-v1.md).
- **Implementation:** [To-do](to_do.md) — single list for current implementation steps; clear when the batch is done and user docs are updated.

Some in-repo links still point to docs that were not migrated (e.g. spec/, benchmark.md, verification-guarantees.md); those are noted in the migration doc and in the plan below.

---

## Plan going forward

### Near term (stabilize and clarify)

1. **Prune scripts** — Keep: scorer, verify_chronicle, run_defensibility_benchmark, eval_harness_adapter, export_for_ml, and RAG demo scripts. Drop or archive scripts that only served the old API/UI (e.g. start_chronicle.sh; ai_validation if it depends on API). Document in README or scripts/README which scripts are first-class.
2. **Fix broken doc links** — Either add minimal in-repo versions of benchmark.md, verification-guarantees.md, integrating-with-chronicle.md (and any spec pointers) or update technical-report and other docs so they only link to existing files.
3. **Add minimal tests** — Focus on scorer and session (and optionally verifier) so we can refactor safely. No need to port the full V1 test suite.

### Medium term (as needed)

4. **Benchmark and training data** — If we want a canonical benchmark: add a small benchmark/sample set or document "generate with script X." Fix or add benchmark.md so the technical report and eval-and-benchmarking links resolve.
5. **CI** — Minimal CI (e.g. lint, scorer smoke test) without the full V1 matrix.
6. **Optional API/frontend** — If we ever want a reference API or UI, it can live in this repo or a separate one; for now we keep this repo as "library + CLI + scorer + verifier + docs."

### Out of scope here (by design)

- Full Chronicle API server and frontend (remain in V1 or a separate repo).
- Full spec doc tree (technical report + defensibility/eval docs are the source of truth).
- Product/process docs (roadmaps, verticals, deployment) unless we add a minimal set for this product.

---

## One-line summary

**We have:** a focused RAG/evals repo with defensibility scorer, .chronicle verifier, event-sourced kernel, session API, eval contract, and supporting docs. **Plan:** prune scripts, fix doc links, add minimal tests, then optionally benchmark/CI and (if ever) a separate API/UI.
