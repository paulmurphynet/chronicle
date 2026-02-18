# Implementation to-do

**Single source of truth for pending work.** All planned features, improvements, and deferred items live here. No separate implementation-plan, horizon, or onboarding checklist docs — one list, check off as you go.

**Doc updates** (guidebook, lessons, quizzes, critical areas) are done at the end after implementing new features, so docs stay in sync with the product.

---

## Current steps

1. ~~**Test coverage — phase 1 (verify, snapshot, event store)**~~ — **Done.** Tests added for `chronicle/verify.py`, `chronicle/store/read_model_snapshot.py`, and `chronicle/store/sqlite_event_store.py` (see `tests/test_verify.py`, `tests/test_read_model_snapshot.py`, `tests/test_sqlite_event_store.py`). Coverage for these modules is now ~80–98%.

2. ~~**Test coverage — phase 2 (projection, read model, commands)**~~ — **Done.** Tests added in `tests/test_projection_read_model_commands.py`: support/challenge link with rationale, list_claims_by_type (filter, include_withdrawn, created_since), get_defensibility_score (strength weighting, withdrawn returns None), type_claim and withdraw_claim projection, list_evidence_by_investigation.

3. ~~**Test coverage — phase 3 (session, scorer, identity; raise fail_under)**~~ — **Done.** Session: export/import and get_reasoning_brief covered in `tests/test_phase3_session_scorer_identity.py`. Scorer: URL fetch path tested with mocked `_fetch_url`. Identity: TraditionalIdP (state override, fallback to headers), get_identity_provider (traditional, gov_id/did/zk stub), NoneIdP actor_type=system in `tests/test_identity.py`. `fail_under` raised to 40% in pyproject.toml (current coverage ~42%); further raises (50% → 60% → 75%) as more tests land.

4. **Future release** — When cutting a release: update [CHANGELOG](../../CHANGELOG.md), tag (e.g. `git tag vX.Y.Z`), push tag, optionally publish to PyPI. See [CONTRIBUTING](../../CONTRIBUTING.md#changelog-and-releases).

---

## Is 75% coverage advisable?

**Yes.** The project already targets 75% for **core** code (see [coverage-core](coverage-core.md)). Coverage is measured only on included paths; API, Neo4j, integrations, and some optional tools are omitted so the bar applies to the defensibility path (event store, read model, session, scorer, verifier). Reaching 75% again is advisable because:

- It was the previous target and keeps regressions in check.
- Core code (store, session, defensibility, verify) is the right place to invest tests.
- `fail_under` is currently 33% so CI doesn’t block; raising it stepwise (e.g. 50% → 60% → 75%) as phases 1–3 land is reasonable.

Optional or integration-heavy modules (CLI subcommands, tools/*, http_client) can stay lower or excluded; focus on getting the **included** code to 75%.

