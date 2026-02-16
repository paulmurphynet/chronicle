# Implementation to-do

**Single place for implementation steps.** No separate "implementation plan" docs — we keep one list here, check items off as we go, and clear the list when the batch is done and user docs are updated.

## How to use this file

1. **When starting a set of changes** — Add the steps to "Current steps" below (e.g. 10 items). Use `- [ ]` for open and `- [x]` for done.
2. **While working** — Mark items done as you complete them. Leave all items in the list so we can see what was in scope.
3. **When the batch is finished** — Confirm the features are reflected in normal user documentation (README, eval_contract, verifier, etc.). Then **empty** the "Current steps" section (delete the list or leave "— none —") so the file is clean.
4. **Next batch** — Add the next set of steps to "Current steps" and repeat.

This keeps the repo from accumulating many one-off implementation-plan docs; one file, one list, reset when done.

---

## Current steps

### Scripts and docs

- [ ] **Prune scripts** — Identify and remove or archive scripts that only served the old API/UI (e.g. `start_chronicle.sh`). Keep: scorer, verify_chronicle, run_defensibility_benchmark, eval_harness_adapter, export_for_ml, RAG demos; decide ai_validation/verticals if they depend on API.
- [ ] **Document first-class scripts** — Update README or scripts/README to list which scripts are first-class (scorer, verifier, benchmark runner, eval harness adapter, export_for_ml, RAG demos) and how to run them.

### Fix broken doc links

- [ ] **Verification guarantees** — Add `docs/verification-guarantees.md` (minimal: what the verifier checks and does not check) or fold that content into verifier.md; fix verifier.md links that point to verification-guarantees.md, legal-judicial-note.md, conformance.md (either add stubs or remove/rewrite links).
- [ ] **Benchmark doc** — Add minimal `docs/benchmark.md` (benchmark concept, fixed-query run, export for training, script refs) so technical-report and eval-and-benchmarking links to Benchmark and benchmark/sample_investigations resolve; or rewrite those links to eval-and-benchmarking + scripts only.
- [ ] **Integrating with Chronicle** — Add minimal `docs/integrating-with-chronicle.md` (minimum integration, investigation_key idempotency) or rewrite links in eval_contract.md, eval-and-benchmarking.md, defensibility-metrics-schema.md to existing docs (e.g. eval-and-benchmarking, scripts).
- [ ] **Technical report references** — Fix technical-report.md links: spec/index, spec/schemas, spec/core-entities, spec/epistemic-tools (point to technical-report sections or add a short "Schema" section); benchmark.md, verification-guarantees.md, chronicle-as-training-data.md (resolve via new docs or rewrite).
- [ ] **Chronicle as training data** — Add minimal `docs/chronicle-as-training-data.md` (export schema, export_for_ml) or remove/rewrite the technical-report and eval references to it.

### Tests and CI

- [ ] **Tests: scorer** — Add minimal tests for `standalone_defensibility_scorer.py` (valid input → metrics; invalid input → error).
- [ ] **Tests: session** — Add minimal tests for session flow (ingest evidence, propose claim, link support, get_defensibility_score).
- [ ] **Tests: verifier (optional)** — Add minimal tests for chronicle-verify on a fixture .chronicle.
- [ ] **CI** — Add minimal CI (e.g. ruff lint, scorer smoke test). No need for full V1 matrix.

### When this batch is done

- [ ] **Update user docs** — Ensure README, eval_contract, verifier, state-and-plan reflect any script pruning and new docs.
- [ ] **Clear this list** — Empty "Current steps" once the above are done and user docs are updated.

*(Mark items with `- [x]` when done. Clear the list when the batch is finished.)*
