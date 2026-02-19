# Implementation to-do

**Single source of truth for pending work.** All planned features, improvements, and deferred items live here. No separate implementation-plan, horizon, or onboarding checklist docs — one list, check off as you go.

**Doc updates** (story, lessons, quizzes, critical areas) are done at the end after implementing new features, so docs stay in sync with the product.

**Review-driven improvements:** All items from [PROJECT_REVIEW](PROJECT_REVIEW.md) were implemented (CI aligned to 50%, coverage artifact, doc link check, integration quick reference, user manual skeleton, benchmark one-liner, release checklist, optional API/Neo4j in README). See PROJECT_REVIEW "Completion status" table.

---

## On hold by design

The following are **intentionally** not implemented or not enabled; no action required unless the project decides otherwise.

- **CI triggers** — Push/PR triggers in [.github/workflows/ci.yml](../.github/workflows/ci.yml) are disabled. CI can be run manually via "Run workflow." To enable on push/PR, uncomment the `push` and `pull_request` triggers.
- **PostgreSQL read model** — The optional Postgres event store exists; the **read model** for Postgres is not implemented. Use SQLite for the read model. See [POSTGRES](POSTGRES.md). Migration to a full Postgres backend is on hold by design.
- **Identity providers (gov_id, did, zk)** — Configurable IdP names exist but resolve via a stub (same behavior as none). Real integrations with government ID, decentralized identity, or zero-knowledge providers are on hold by design.

---

## Current steps

1. ~~**Test coverage — phase 1 (verify, snapshot, event store)**~~ — **Done.** Tests added for `chronicle/verify.py`, `chronicle/store/read_model_snapshot.py`, and `chronicle/store/sqlite_event_store.py` (see `tests/test_verify.py`, `tests/test_read_model_snapshot.py`, `tests/test_sqlite_event_store.py`). Coverage for these modules is now ~80–98%.

2. ~~**Test coverage — phase 2 (projection, read model, commands)**~~ — **Done.** Tests added in `tests/test_projection_read_model_commands.py`: support/challenge link with rationale, list_claims_by_type (filter, include_withdrawn, created_since), get_defensibility_score (strength weighting, withdrawn returns None), type_claim and withdraw_claim projection, list_evidence_by_investigation.

3. ~~**Test coverage — phase 3 (session, scorer, identity; raise fail_under)**~~ — **Done.** Session: export/import and get_reasoning_brief covered in `tests/test_phase3_session_scorer_identity.py`. Scorer: URL fetch path tested with mocked `_fetch_url`. Identity: TraditionalIdP (state override, fallback to headers), get_identity_provider (traditional, gov_id/did/zk stub), NoneIdP actor_type=system in `tests/test_identity.py`. `fail_under` raised to 40% in pyproject.toml (current coverage ~42%); further raises (50% → 60% → 75%) as more tests land.

4. ~~**Test coverage — phase 4 (toward 50%; raise fail_under)**~~ — **Done.** Tests in `tests/test_phase4_session_audit_trail.py`: get_defensibility_as_of (by event_id, by date, validation, event_id not found), export_minimal_for_claim, get_reasoning_trail_claim, get_accountability_chain, get_audit_export_bundle (basic, as_of_event_id, investigation not found, include_full_trail), get_reasoning_brief (as_of_date, as_of_event_id, with tension), get_human_decisions_audit_trail, get_investigation_event_history. Optional LLM/tools modules added to coverage omit so core bar is meaningful. `fail_under` raised to 50%.

5. **Test coverage — phase 5 (toward 75%; raise fail_under stepwise)** — Add tests for remaining hot paths (e.g. export_import edge cases, CLI subcommands that use session, policy application in get_defensibility_score). Raise `fail_under` to 60% when coverage allows, then to 75%. See [coverage-core](coverage-core.md). Phase 5 tests added in `tests/test_phase5_coverage.py`; raise fail_under when suite is green.

6. **Future release** — When cutting a release: update [CHANGELOG](../../CHANGELOG.md), tag (e.g. `git tag vX.Y.Z`), push tag, optionally publish to PyPI. See [CONTRIBUTING](../../CONTRIBUTING.md#changelog-and-releases) (release checklist). When a preprint (e.g. arXiv) or publication exists, add its ID and citation to [technical-report](technical-report.md).

---

## Epistemology-optimal configuration (from thought experiment 01)

Agreed list of changes from the [epistemologists’ conference review](../../thought_experiments/01-epistemologists-conference-review.md) to bring Chronicle to the target epistemology configuration. See story [06 — Epistemology: what we implement and what we don’t](../../story/06-epistemology-scope-tables.md) for the full tables.

7. ~~**Scorer / eval caveat (docs)**~~ — **Done.** Prominent note added in eval contract, benchmark, and RAG evals defensibility metric.

8. ~~**Surface independence_notes (data + docs)**~~ — **Done.** sources_backing_claim (with independence_notes and reliability_notes) in GET /claims/{uid}/defensibility and in claim–evidence–metrics export.

9. ~~**Optional warrant / link rationale (schema + API)**~~ — **Done.** Rationale in schema and API; documented in epistemology-scope and critical areas.

10. ~~**Optional defeater type (schema + API)**~~ — **Done.** Optional defeater_kind on evidence_link and tension (schema, API, session).

11. ~~**Optional source reliability / authority metadata (schema + API)**~~ — **Done.** Optional reliability_notes on source; documented in epistemology-scope and critical area 02.

12. ~~**Optional policy rationale (schema + config)**~~ — **Done.** Optional policy_rationale on PolicyProfile; documented in epistemology-scope and critical area 05.

13. ~~**Optional epistemic stance on claims (schema + API)**~~ — **Done.** Optional epistemic_stance on claim (schema, API, session); documented in epistemology-scope.

14. ~~**Epistemology-scope and critical areas (docs)**~~ — **Done.** epistemology-scope and critical areas 02, 04, 05 updated with new optional fields and "recorded, not verified" wording.

---

## Is 75% coverage advisable?

**Yes.** The project already targets 75% for **core** code (see [coverage-core](coverage-core.md)). Coverage is measured only on included paths; API, Neo4j, integrations, and some optional tools are omitted so the bar applies to the defensibility path (event store, read model, session, scorer, verifier). Reaching 75% again is advisable because:

- It was the previous target and keeps regressions in check.
- Core code (store, session, defensibility, verify) is the right place to invest tests.
- `fail_under` is 50% (CI and pyproject aligned); raising it stepwise (60% → 75%) as phase 5 tests land is reasonable. CI triggers remain disabled until the maintainer enables them; when run, CI uses --cov-fail-under=50 and uploads coverage artifacts; doc link check runs. See [PROJECT_REVIEW](PROJECT_REVIEW.md) completion status.

Optional or integration-heavy modules (CLI subcommands, tools/*, http_client) can stay lower or excluded; focus on getting the **included** code to 75%.

