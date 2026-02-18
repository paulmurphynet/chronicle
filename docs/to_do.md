# Implementation to-do

**Single source of truth for pending work.** All planned features, improvements, and deferred items live here. No separate implementation-plan, horizon, or onboarding checklist docs — one list, check off as you go.

**Doc updates** (guidebook, lessons, quizzes, critical areas) are done at the end after implementing new features, so docs stay in sync with the product.

---

## Current steps

1. **Test coverage — phase 1 (verify, snapshot, event store)** — Raise coverage for core I/O and verification: add tests for `chronicle/verify.py` (verifier checks on in-memory or fixture .chronicle), `chronicle/store/read_model_snapshot.py` (create + restore from temp project), and `chronicle/store/sqlite_event_store.py` (append, read_by_subject, read_by_investigation, migrations). Target: get these modules to ≥70% so overall moves toward 75%. See [coverage-core](coverage-core.md).

2. **Test coverage — phase 2 (projection, read model, commands)** — Add tests for projection handlers (e.g. SupportLinked, ClaimProposed, evidence_link with rationale), `sqlite_read_model` methods that are still uncovered (list_claims_by_type, list_*, get_defensibility_score path), and store commands used by session flow (evidence ingest/link, claims propose, defensibility). Target: projection and sqlite_read_model toward 60–70%; key commands (evidence, claims) toward 50%+.

3. **Test coverage — phase 3 (session, scorer, identity; raise fail_under)** — Cover session methods not yet hit (export/import, replay, snapshot, get_reasoning_brief), finish `scorer_contract` (URL fetch path with mock), and `chronicle/core/identity.py` branches. Then raise `fail_under` in pyproject.toml (e.g. 50% → 60% → 75%) so CI enforces the target. See [code-quality-review](code-quality-review.md).

4. **Future release** — When cutting a release: update [CHANGELOG](../../CHANGELOG.md), tag (e.g. `git tag vX.Y.Z`), push tag, optionally publish to PyPI. See [CONTRIBUTING](../../CONTRIBUTING.md#changelog-and-releases).

---

## Is 75% coverage advisable?

**Yes.** The project already targets 75% for **core** code (see [coverage-core](coverage-core.md)). Coverage is measured only on included paths; API, Neo4j, integrations, and some optional tools are omitted so the bar applies to the defensibility path (event store, read model, session, scorer, verifier). Reaching 75% again is advisable because:

- It was the previous target and keeps regressions in check.
- Core code (store, session, defensibility, verify) is the right place to invest tests.
- `fail_under` is currently 33% so CI doesn’t block; raising it stepwise (e.g. 50% → 60% → 75%) as phases 1–3 land is reasonable.

Optional or integration-heavy modules (CLI subcommands, tools/*, http_client) can stay lower or excluded; focus on getting the **included** code to 75%.

