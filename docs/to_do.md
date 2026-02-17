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

- [x] **Verification guarantees** — Added `docs/verification-guarantees.md`; fixed verifier.md links (verification-guarantees, conformance, critical_areas).
- [x] **Benchmark doc** — Added minimal `docs/benchmark.md`; technical-report and eval-and-benchmarking now link to it and to scripts.
- [x] **Integrating with Chronicle** — Added minimal `docs/integrating-with-chronicle.md`; eval and defensibility-metrics-schema links updated.
- [x] **Technical report references** — Fixed technical-report.md: spec/ links replaced with in-report or codebase refs; benchmark, verification-guarantees, chronicle-as-training-data now resolve.
- [x] **Chronicle as training data** — Added minimal `docs/chronicle-as-training-data.md`; added `docs/conformance.md` stub.

### Tests and CI

- [ ] **Tests: scorer** — Add minimal tests for `standalone_defensibility_scorer.py` (valid input → metrics; invalid input → error).
- [ ] **Tests: session** — Add minimal tests for session flow (ingest evidence, propose claim, link support, get_defensibility_score).
- [ ] **Tests: verifier (optional)** — Add minimal tests for chronicle-verify on a fixture .chronicle.
- [ ] **CI** — Add minimal CI (e.g. ruff lint, scorer smoke test). No need for full V1 matrix.

### When this batch is done

- [ ] **Update user docs** — Ensure README, eval_contract, verifier, state-and-plan reflect any script pruning and new docs.
- [ ] **Clear this list** — Empty "Current steps" once the above are done and user docs are updated.

*(Mark items with `- [x]` when done. Clear the list when the batch is finished.)*
