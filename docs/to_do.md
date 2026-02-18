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

- [x] **1. Test coverage: session integration tests** — Add 2–3 tests under `tests/` that exercise `ChronicleSession` end-to-end: create project, create investigation, ingest evidence, propose claim, link support, then call `get_defensibility_score` and assert on scorecard shape. These complement the standalone scorer tests and protect the core defensibility path when refactoring.

- [x] **2. Test coverage: CI gate** — In `pyproject.toml`, set `[tool.coverage.report] fail_under` to a concrete value (e.g. 40 or 50). In `.github/workflows/ci.yml`, add `--cov-fail-under=33` to the pytest step so CI fails if coverage drops below the bar (33% current; raise as tests grow).

- [x] **3. Test coverage: narrow omit list** — Review `[tool.coverage.run] omit` in `pyproject.toml`. Keep excluding optional/plugin modules (api, neo4j_sync, postgres_event_store, encryption, integrations) if desired; consider removing any core command or read_model paths from omit so their coverage counts, and document in `docs/coverage-core.md` (or similar) what is in scope for the coverage target.

- [x] **4. Session module: document or split** — Either (a) add a short module docstring at the top of `chronicle/store/session.py` stating that the file is an intentional facade of thin wrappers over the command layer, so future refactors are clearly optional, or (b) split `ChronicleSession` by domain (e.g. session_investigation, session_claims, session_evidence) and compose them in one `ChronicleSession` class. Choose one approach and implement it.

- [x] **5. Scripts: first-class vs optional** — In `scripts/README.md`, ensure every script is clearly labeled as first-class (eval, verification, export, RAG demos) or optional/advanced (ai_validation, verticals, utilities). Archive or remove any script that only served an old API/UI and has no remaining dependents; document in scripts/README which scripts were archived and where.

- [x] **6. Lessons 04–07** — Either (a) add lessons 04–07 (events/core, store/session, defensibility, integrations/scripts) under `lessons/` with the same style as 00–03, or (b) update `lessons/README.md` to state that lessons 04–07 are coming later and that after lesson 03 readers should use the codebase map and technical report. Remove or update any references that assume 04–07 exist.

- [x] **7. Error surface: consistent user errors** — Ensure all user-facing validation and capacity errors (e.g. missing project, invalid input, idempotency cap) use `ChronicleUserError` or a documented subclass from `chronicle/core/errors.py`. Add a short "Errors" subsection in CONTRIBUTING or in `docs/` (e.g. in troubleshooting or a new errors.md) describing when to use which error type and how CLI/API map them to exit codes and HTTP status.

- [ ] **8. Changelog** — Add `CHANGELOG.md` at repo root with at least one entry (e.g. "0.1.0 – initial release" or current version). Document in CONTRIBUTING or README that meaningful changes should be reflected in the changelog; keep it updated as releases or notable changes happen.

- [ ] **9. Mypy and optional dependencies** — Resolve mypy issues for optional deps (neo4j, fastapi, etc.): either add stub packages (e.g. `types-*`) in dev optional-deps or add mypy overrides for those modules so `chronicle.*` can keep `ignore_missing_imports = false` without failing when optional extras are not installed. Document in CONTRIBUTING how to run mypy with optional deps if needed.

- [ ] **10. Integrations: happy path and smoke tests** — For each integration (LangChain, LlamaIndex, Haystack): (a) ensure one "happy path" is documented (e.g. in `docs/integrating-with-chronicle.md` or the integration module docstring) with a minimal runnable example; (b) if feasible, add a single smoke test per integration (e.g. import the integration module and perform a minimal call or build a minimal pipeline) so refactors don’t break them silently. Integrations can remain excluded from coverage; the goal is documentation and a basic test.
