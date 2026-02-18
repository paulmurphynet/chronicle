# Chronicle: What we have and plan going forward

## What we have so far

**Product focus:** Defensibility scoring for RAG and evals. Event-sourced evidence, claims, and defensibility; standalone scorer and .chronicle verifier. An optional minimal HTTP API lives in-repo (see [api.md](api.md); install with `.[api]`); otherwise "library + CLI + scorer + verifier + docs."

### Core deliverables

| Piece | What it does |
|-------|----------------|
| **Standalone defensibility scorer** | `scripts/standalone_defensibility_scorer.py`: JSON in (query, answer, evidence), defensibility metrics out. Implements the [eval contract](eval_contract.md). No RAG stack required. |
| **chronicle-verify** | CLI (`chronicle-verify`) to verify a .chronicle (ZIP) — manifest, schema, evidence hashes. Stdlib only; can verify without the Chronicle package. |
| **Chronicle package** | Event store, read model, defensibility computation, session API. Used by the scorer and by LangChain/LlamaIndex/Haystack integrations. Full command layer (claims, evidence, sources, tensions, reasoning brief, etc.). Optional minimal HTTP API in-repo: [api.md](api.md). |
| **Eval contract** | Stable input/output for the scorer; [eval_contract.md](eval_contract.md) and [eval_contract_schema.json](eval_contract_schema.json) for harnesses. |

### Supporting pieces

- **CLI** (`chronicle`) — Project init, neo4j-export, neo4j-sync, and other project/claim/evidence commands.
- **Neo4j** — Optional: export read model to CSV or sync to Neo4j for multi-run graph analysis; Cypher rebuild scripts in `neo4j/rebuild/`. See [Neo4j](neo4j.md).
- **Integrations** — LangChain, LlamaIndex, Haystack (optional hooks for RAG pipelines).
- **Scripts** — Benchmark runner, eval harness adapter, RAG demos, export_for_ml, ai_validation, verticals, utilities. First-class vs optional is documented in [scripts/README](../scripts/README.md).

### Docs

- **Eval and defensibility:** [Eval contract](eval_contract.md), [eval contract schema](eval_contract_schema.json), [Defensibility metrics schema](defensibility-metrics-schema.md), [Eval and benchmarking](eval-and-benchmarking.md), [Technical report](technical-report.md).
- **Verification:** [Verifier](verifier.md).
- **Context:** [Neo4j](neo4j.md), [Epistemology scope](epistemology-scope.md), [Migration from V1](migration-from-v1.md).
- **Implementation:** [To-do](to_do.md) — single list for all pending work; story, lessons, quizzes, and other doc updates are done after implementing features.
- **Testing:** [Testing with Ollama](testing-with-ollama.md) — use local Ollama for real LLM-backed testing during development.

Doc links have been updated: [Benchmark](benchmark.md), [Verification guarantees](verification-guarantees.md), [Integrating with Chronicle](integrating-with-chronicle.md), [Conformance](conformance.md), and [Chronicle as training data](chronicle-as-training-data.md) exist; technical-report and verifier no longer link to missing spec/ or stubs.

---

## What's next

All pending work (features, improvements, doc updates) lives only in [To-do](to_do.md). This doc describes **current state**; do not add future-work items here.

---

## One-line summary

**We have:** a focused RAG/evals repo with defensibility scorer, .chronicle verifier, event-sourced kernel, session API, eval contract, and supporting docs. **What's next:** see [To-do](to_do.md).
