# Implementation to-do

**Single source of truth for pending work.** All planned, future, deferred, and undone items live here. No scattered "future work" elsewhere. Doc updates (story, lessons, quizzes, critical areas) are done after implementing new features.

---

## On hold by design

Only the following are intentionally not done; no action unless the project decides otherwise.

- **CI triggers** — Push/PR triggers in [.github/workflows/ci.yml](../.github/workflows/ci.yml) are disabled. To enable, uncomment the push and pull_request triggers. CI can be run manually via "Run workflow."
- **PostgreSQL read model / migration** — The optional Postgres event store exists; the read model for Postgres is not implemented. Use SQLite for the read model. See [POSTGRES](POSTGRES.md). Do not migrate to a full Postgres backend unless the project decides otherwise.

---

## To do

*(All 12 items from the previous list have been implemented: test coverage phase 5 with new tests and fail_under raised to 60%; future release and preprint placeholders; identity-providers doc and extension points; multiple external keys documented in external-ids; user manual chapters expanded; one-line benchmark and coverage artifact/doc link check confirmed in README and CI; API and Neo4j in README verified; reference-ui-plan docs and API surface updated. Add new work below as needed.)*

1. *(No open items.)*
