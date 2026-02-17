# Implementation to-do

**Single place for implementation steps.** No separate "implementation plan" docs — we keep one list here, check items off as we go, and clear the list when the batch is done and user docs are updated.

**Guidebook:** Enhancement deferred until after more features (interoperability, etc.) to avoid repeated rewrites.

## How to use this file

1. **When starting a set of changes** — Add the steps to "Current steps" below (e.g. 10 items). Use `- [ ]` for open and `- [x]` for done.
2. **While working** — Mark items done as you complete them. Leave all items in the list so we can see what was in scope.
3. **When the batch is finished** — Confirm the features are reflected in normal user documentation (README, eval_contract, verifier, etc.). Then **empty** the "Current steps" section (delete the list or leave "— none —") so the file is clean.
4. **Next batch** — Add the next set of steps to "Current steps" and repeat.

This keeps the repo from accumulating many one-off implementation-plan docs; one file, one list, reset when done.

---

## Current steps

### Scripts and docs

- [x] **Prune scripts** — Identify and remove or archive scripts that only served the old API/UI (e.g. `start_chronicle.sh`). Keep: scorer, verify_chronicle, run_defensibility_benchmark, eval_harness_adapter, export_for_ml, RAG demos; decide ai_validation/verticals if they depend on API.
- [x] **Document first-class scripts** — Update README or scripts/README to list which scripts are first-class (scorer, verifier, benchmark runner, eval harness adapter, export_for_ml, RAG demos) and how to run them.

### Fix broken doc links

- [x] **Verification guarantees** — Added `docs/verification-guarantees.md`; fixed verifier.md links (verification-guarantees, conformance, critical_areas).
- [x] **Benchmark doc** — Added minimal `docs/benchmark.md`; technical-report and eval-and-benchmarking now link to it and to scripts.
- [x] **Integrating with Chronicle** — Added minimal `docs/integrating-with-chronicle.md`; eval and defensibility-metrics-schema links updated.
- [x] **Technical report references** — Fixed technical-report.md: spec/ links replaced with in-report or codebase refs; benchmark, verification-guarantees, chronicle-as-training-data now resolve.
- [x] **Chronicle as training data** — Added minimal `docs/chronicle-as-training-data.md`; added `docs/conformance.md` stub.

### Tests and CI

- [x] **Tests: scorer** — Add minimal tests for `standalone_defensibility_scorer.py` (valid input → metrics; invalid input → error).
- [x] **Tests: session** — Add minimal tests for session flow (ingest evidence, propose claim, link support, get_defensibility_score).
- [x] **Tests: verifier (optional)** — Add minimal tests for chronicle-verify on a fixture .chronicle.
- [x] **CI** — Add minimal CI (e.g. ruff lint, scorer smoke test). No need for full V1 matrix.

### Interoperability and compatibility (exchange with fact-checking, provenance, RAG, graphs)

**Document and stabilize exchange surfaces**

- [x] **Eval contract versioning** — Added contract_version 1.0 to eval_contract_schema.json; eval_contract.md states breaking changes are rare and announced; "if you only do one thing: pipe JSON to the scorer" in doc.
- [x] **Consuming .chronicle** — Added docs/consuming-chronicle.md: how to open ZIP, read manifest + SQLite, resolve evidence files; linked from chronicle-file-format.md.
- [x] **Generic export doc** — Added docs/GENERIC_EXPORT.md: JSON and CSV-ZIP shapes, API usage, consumer use cases (BI, fact-checking pipeline); code already referenced this doc.

**Adapters in (others → Chronicle)**

- [x] **Fact-checker adapter** — Adapter (script or small module) that accepts a fact-checker output (e.g. claim + verdict + sources as JSON/CSV) and maps to Chronicle: evidence items, propose_claim, support/challenge, declare_tension where applicable. Document format expected and how to run.
- [x] **Provenance adapter** — Adapter that reads provenance assertions (e.g. C2PA/CR-style "this blob from this source/model") and creates Chronicle sources + evidence–source links (and optionally evidence items). Document "we record, we don't verify."
- [x] **RAG harness adapter example** — Document "your RAG harness → our scorer" as the standard path; optionally add one example adapter for a specific popular harness (copy-paste template).

**Adapters out (Chronicle → others)**

- [x] **Claim–evidence–metrics export schema** — Define and document a stable JSON schema (or thin wrapper over generic export / export_for_ml) for "one claim + evidence refs + support/challenge + defensibility" for fact-checking UIs or dashboards. Document "consumers can ingest this."
- [x] **Neo4j schema doc** — Add a short doc: node labels, relationship types, key properties for the sync output so graph RAG / graph tools can query without reverse-engineering. Optionally one or two example Cypher queries (e.g. claims in tension, evidence supporting a claim).

**API and conventions**

- [ ] **Minimal HTTP API** — Add a minimal HTTP API (e.g. FastAPI in-repo or chronicle-server): write (investigation, evidence, claim, link, tension), read (claim, defensibility, reasoning trail), export/import .chronicle. Same response shapes as eval contract and defensibility schema. Enables fact-checking/provenance UIs to call Chronicle over HTTP. *Deferred: larger follow-up; session + scorer + adapters cover most integration needs for now.*
- [x] **Terminology / glossary for interop** — Add a short "Terminology" or extend glossary: map Chronicle terms to common ones (claim ≈ statement, support/challenge ≈ evidence_for/evidence_against, tension ≈ contradiction). Help fact-checkers and argumentation tools align.
- [x] **External IDs** — Document how external IDs (e.g. fact-check ID, C2PA claim ID) can be stored (e.g. in claim or evidence metadata) so "this Chronicle claim = that external claim" is possible; implement if not already present.

**Ecosystem (longer term)**

- [x] **Claim–evidence–defensibility spec** — Publish a small, stable JSON schema or minimal spec for "one claim + evidence refs + support/challenge + defensibility" that Chronicle and others could emit/consume. Document in repo.
- [x] **Provenance recording doc** — Document "we can store source and evidence–source links; you can feed us C2PA/CR assertions and we treat them as your modeling of provenance" so provenance-aware pipelines know they can land results in Chronicle.
- [x] **RAG evals: Chronicle defensibility as standard metric** — One page: "here's the contract, schema, how to run the scorer in your harness" so Chronicle is the obvious choice for RAG + defensibility.

### When this batch is done

- [x] **Update user docs** — Ensure README, eval_contract, verifier, state-and-plan reflect any script pruning and new docs.
- [ ] **Clear this list** — Empty "Current steps" once the above are done and user docs are updated (one item remains: minimal HTTP API, deferred).

*(Mark items with `- [x]` when done. Clear the list when the batch is finished.)*
