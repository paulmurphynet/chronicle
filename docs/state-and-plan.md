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
- **Testing:** [Testing with Ollama](testing-with-ollama.md) — use local Ollama for real LLM-backed testing during development.

Doc links have been updated: [Benchmark](benchmark.md), [Verification guarantees](verification-guarantees.md), [Integrating with Chronicle](integrating-with-chronicle.md), [Conformance](conformance.md), and [Chronicle as training data](chronicle-as-training-data.md) exist; technical-report and verifier no longer link to missing spec/ or stubs.

---

## Plan going forward

### Near term (stabilize and clarify)

1. **Prune scripts** — Keep: scorer, verify_chronicle, run_defensibility_benchmark, eval_harness_adapter, export_for_ml, and RAG demo scripts. Drop or archive scripts that only served the old API/UI (e.g. start_chronicle.sh; ai_validation if it depends on API). Document in README or scripts/README which scripts are first-class.
2. **Fix broken doc links** — Done: benchmark.md, verification-guarantees.md, integrating-with-chronicle.md, conformance.md, chronicle-as-training-data.md added; technical-report and verifier updated to link only to existing docs.
3. **Add minimal tests** — Focus on scorer and session (and optionally verifier) so we can refactor safely. No need to port the full V1 test suite.

### Medium term (as needed)

4. **Benchmark and training data** — benchmark.md added with concept and script refs. For a canonical sample set, document "generate with script X" (e.g. synthetic_data or benchmark_data scripts) as needed.
5. **CI** — Minimal CI (e.g. lint, scorer smoke test) without the full V1 matrix.
6. **Optional API/frontend** — If we ever want a reference API or UI, it can live in this repo or a separate one; for now we keep this repo as "library + CLI + scorer + verifier + docs."

### Out of scope here (by design)

- Full Chronicle API server and frontend (remain in V1 or a separate repo).
- Full spec doc tree (technical report + defensibility/eval docs are the source of truth).
- Product/process docs (roadmaps, verticals, deployment) unless we add a minimal set for this product.

---

## Horizon: after the to-do list

Once the current to-do (prune scripts, fix links, minimal tests, CI) is done and the list is cleared, these are the directions that can make Chronicle **the very best it can be** — in adoption, quality, and differentiation. None are mandatory; they’re a menu to pick from.

**Adoption and visibility**

- **Eval-harness integration** — Document or provide a thin adapter so Chronicle defensibility can be added as a metric in popular frameworks (e.g. RAGAS, Trulens, LangSmith evals, or custom harnesses). Goal: “add defensibility to your RAG eval in one step.”
- **Citable benchmark** — A small, public benchmark (fixed queries + expected shape, or a generated set) that papers and blogs can cite. Reproducible with a single script; optional leaderboard or “baseline” numbers.
- **Technical report as preprint** — Publish the technical report (e.g. arXiv) so researchers can cite the defensibility definition and schema. Strengthens “Chronicle” as a standard for evidence-based answer quality.

**Quality and trust**

- **Stable contract and CI** — Keep the eval contract stable; CI that runs scorer + verifier (and optional Ollama integration tests) on every change. Tagged releases so downstream users can pin a version.
- **Small public dataset** — Optional: a few dozen (query, answer, evidence) examples with reference defensibility or at least schema-valid scorecards, for validation and demos.

**Differentiation**

- **One clear story** — “Chronicle: the defensibility score for RAG.” Docs and README lead with that; eval contract and technical report are the single source of truth. No competing narratives.
- **Optional depth** — If we want to go further epistemically: optional “support rationale” or “warrant” field (why this evidence supports this claim), or a tighter link to NLI/entailment evals. Only if it clearly improves evals or adoption; [epistemology scope](epistemology-scope.md) already sets boundaries.

**Ecosystem**

- **Polish integrations** — LangChain, LlamaIndex, Haystack: ensure one “happy path” each is documented and tested; drop or archive the rest so the repo doesn’t carry dead code.
- **.chronicle as interchange** — Position the .chronicle format as “show your work”: anyone can export (query, answer, evidence, defensibility) and others can verify. Encourages tooling and integrations that consume .chronicle.
- **Optional minimal API** — If useful for demos or hosted evals: a tiny “run scorer as a service” (POST JSON, get defensibility) or a read-only API for .chronicle inspection. Can live in this repo or a separate one; not required for “best.”

**Summary**

Best = **adopted** (harnesses, papers, benchmark), **trusted** (stable contract, CI, tests), and **clearly differentiated** (defensibility for RAG, one story). The horizon above is a set of levers; we can choose a few and do them well rather than trying to do everything.

---

## One-line summary

**We have:** a focused RAG/evals repo with defensibility scorer, .chronicle verifier, event-sourced kernel, session API, eval contract, and supporting docs. **Plan:** prune scripts, fix doc links, add minimal tests, then optionally benchmark/CI and (if ever) a separate API/UI.
