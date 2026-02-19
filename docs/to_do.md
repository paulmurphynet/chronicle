# Implementation to-do

Single source of truth for pending implementation work.

Last refreshed: **2026-02-19**

## Review context

This backlog was refreshed from a full repository scan (code, docs, config, scripts, frontend) and local runnable checks.

- `python3 -m compileall chronicle tools scripts tests frontend/src` passed.
- `python3 scripts/check_doc_links.py docs` failed with broken links.
- Dev tools (`ruff`, `pytest`) were not available in this environment, and dependency install was blocked by network limits.

## On hold by design

Only the following are intentionally on hold unless maintainers decide otherwise.

- **CI auto-triggers**: push/PR triggers in `.github/workflows/ci.yml` remain disabled; workflow is manual (`workflow_dispatch`) only.
- **Postgres read model**: `chronicle/store/postgres_event_store.py` exists, but a Postgres read model is not implemented.

## P0: Critical correctness and contract alignment

| ID | Improvement | Why now | Primary files | Done when |
|---|---|---|---|---|
| P0-01 | Fix import merge loop to continue after duplicate events instead of stopping at first `IntegrityError`. | `with contextlib.suppress(sqlite3.IntegrityError)` currently wraps the whole loop and can silently stop import early. | `chronicle/store/export_import.py` | Duplicate events are skipped per event, non-duplicate events still import, and regression test proves mixed duplicate/new imports succeed. |
| P0-02 | Use deterministic import replay ordering aligned with append order (`rowid`) during merge import. | Current merge import orders by `recorded_at, event_id`; tied timestamps can reorder causal events. | `chronicle/store/export_import.py` | Import replay order is deterministic and causally safe; test covers tied-timestamp events. |
| P0-03 | Bring `chronicle/http_client.py` back in sync with live API routes and request model. | Client references non-existent endpoints and headers (for example `/project/init`, `/claims`, `/evidence/from-url`, GET submission package). | `chronicle/http_client.py`, `chronicle/api/app.py`, `docs/api.md` | Every client method maps to an existing endpoint or is removed/deprecated; docs and examples match code. |
| P0-04 | Add API-level error mapping consistency for `ChronicleUserError` and validation failures. | Only a subset of endpoints maps domain errors to 400/404; others can return 500s for user mistakes. | `chronicle/api/app.py` | All write/read handlers return predictable 4xx for user errors; centralized exception handler added and tested. |
| P0-05 | Repair broken documentation links in `docs/` and keep link checker green. | Current docs link checker reports broken references (Story/Lessons/policy profile links). | `docs/getting-started.md`, `docs/PROJECT_REVIEW.md`, `docs/north-star.md`, `docs/policy-profiles/README.md` | `python3 scripts/check_doc_links.py docs` returns success. |
| P0-06 | Decide and implement strategy for `scripts/check_doc_links.py` on repo-wide scans (`.`). | Current checker assumes link-without-suffix is markdown file, causing false failures for directory links. | `scripts/check_doc_links.py`, `.github/workflows/ci.yml` | Repo-wide link checks are reliable (or scoped intentionally) and CI policy is documented. |
| P0-07 | Resolve extras mismatch: code/docs reference `.[postgres]` and `.[encryption]` but pyproject does not define them. | Installation instructions are currently inconsistent and can mislead users. | `pyproject.toml`, `chronicle/store/postgres_event_store.py`, `chronicle/core/encryption.py`, `docs/POSTGRES.md` | Extras are either implemented in `pyproject.toml` or references removed/rewritten consistently. |
| P0-08 | Refresh stale review docs with current state (coverage thresholds, manual status, completed items). | Historical review docs currently include outdated thresholds and completed/planned status. | `docs/PROJECT_REVIEW.md`, `docs/code-quality-review.md` | Review docs are either updated to current state or marked archival with date and replacement doc. |

## P1: High-impact reliability and test coverage

| ID | Improvement | Why now | Primary files | Done when |
|---|---|---|---|---|
| P1-01 | Add API test suite (endpoint behavior, error mapping, export/import, identity headers). | No dedicated API tests currently protect HTTP contract. | `tests/` (new API tests), `chronicle/api/app.py` | FastAPI test suite exists and covers happy paths + negative cases for all public routes. |
| P1-02 | Add test coverage for `chronicle/http_client.py` against API test app. | Client drift happened without test protection. | `tests/` (new client tests), `chronicle/http_client.py` | Client tests fail on route mismatch and pass when in sync with API docs. |
| P1-03 | Add regression tests for import edge cases: mixed duplicate/new events, tied timestamps, malformed archive members. | Import/export path is a critical portability feature and currently under-protected for edge cases. | `tests/test_phase5_coverage.py` (or new focused test module) | New edge-case tests pass and guard against silent data loss/reordering. |
| P1-04 | Add verifier parity tests between project verifier and standalone `.chronicle` verifier. | Verification logic is duplicated across modules and can drift. | `chronicle/verify.py`, `tools/verify_chronicle/verify_chronicle.py`, `tests/` | Shared behavior matrix exists; both verifiers produce aligned pass/fail outcomes for the same fixtures. |
| P1-05 | Add frontend automated tests (unit + integration smoke). | Frontend currently has no automated tests. | `frontend/` | Basic test harness added (component rendering + core flows like Try Sample, list, export actions). |
| P1-06 | Add frontend CI checks (build + lint + tests) as manual workflow job. | Frontend quality gates are absent from CI path. | `.github/workflows/ci.yml`, `frontend/package.json` | Manual CI run executes frontend checks and publishes results/artifacts. |
| P1-07 | Add contract tests for documentation snippets (API examples and quickstart commands). | Quickstart/docs drift is already visible in links and historical docs. | `docs/`, `scripts/` (doc-test harness) | Key doc snippets are automatically validated or smoke-tested in CI/manual checks. |
| P1-08 | Increase coverage focus on high-churn large modules. | Core files are large and regression-prone (`session`, `cli`, read model/projection). | `chronicle/store/session.py`, `chronicle/cli/main.py`, `chronicle/store/read_model/*`, `tests/` | Added tests target command dispatch branches, error paths, and projection invariants. |
| P1-09 | Add offline-friendly contributor workflow docs for running tests/tooling in restricted environments. | Current setup assumes networked dependency installation. | `CONTRIBUTING.md`, `docs/troubleshooting.md` | Contributor docs include no-network guidance (`--no-build-isolation`, prebuilt env, fallback checks). |

## P2: Maintainability, performance, and developer experience

| ID | Improvement | Why now | Primary files | Done when |
|---|---|---|---|---|
| P2-01 | Refactor monolithic CLI into command modules/registry. | `chronicle/cli/main.py` is >1200 lines and hard to maintain. | `chronicle/cli/main.py`, `chronicle/cli/` (new modules) | CLI behavior unchanged, but command handlers are modular and unit-testable by domain. |
| P2-02 | Refactor `ChronicleSession` facade into composed domain mixins/modules. | `chronicle/store/session.py` is >1500 lines; interface is broad and hard to evolve safely. | `chronicle/store/session.py`, `chronicle/store/session_*` (new modules) | API-compatible session facade remains; implementation split by concerns with clearer ownership. |
| P2-03 | Reduce broad `except Exception` usage in core paths and log actionable context. | Silent suppression makes failures hard to debug and can mask data issues. | `chronicle/store/export_import.py`, `chronicle/api/app.py`, `tools/verify_chronicle/verify_chronicle.py`, integrations | Broad catches replaced with explicit exception handling where correctness matters; logs/errors are actionable. |
| P2-04 | Add structured API logging and request correlation IDs. | Debugging production failures is harder without request-scoped traces. | `chronicle/api/app.py` | Each request includes correlation/request ID in logs and error responses (where appropriate). |
| P2-05 | Add pagination/cursor strategy for high-volume list endpoints and graph payloads. | Current large default limits can create heavy responses and UI latency. | `chronicle/api/app.py`, frontend consumers | Endpoints support stable pagination, frontend consumes paged data, and docs reflect new parameters. |
| P2-06 | Optimize graph endpoint to avoid claim-by-claim N+1 link/span queries. | Current graph building loops can degrade performance with many claims/evidence items. | `chronicle/api/app.py`, read model query helpers | Graph endpoint uses batched queries and has basic performance test/benchmark. |
| P2-07 | Introduce generated typed frontend client from OpenAPI schema. | Handwritten TS API client is vulnerable to backend drift. | `frontend/src/lib/api.ts`, API OpenAPI schema tooling | Generated types/client in place (or contract tests proving parity); drift detection automated. |
| P2-08 | Split `frontend/src/pages/InvestigationDetail.tsx` into tab components/hooks. | Current ~500-line component is difficult to test and evolve. | `frontend/src/pages/InvestigationDetail.tsx`, `frontend/src/components/` | Component split by tab/domain; behavior retained; tests added for key interactions. |
| P2-09 | Add Makefile/task runner for common checks (`lint`, `typecheck`, `test`, `docs-check`). | Contributor setup is currently command-fragmented. | repo root (new `Makefile` or task config), docs | One documented command per workflow; commands used in CI/manual runs are consistent. |
| P2-10 | Unify version source between package metadata and runtime module version. | Version currently appears in multiple places. | `pyproject.toml`, `chronicle/__init__.py` | Single source of version truth with automated check or generation step. |

## P3: Productization and long-horizon backlog

| ID | Improvement | Why now | Primary files | Done when |
|---|---|---|---|---|
| P3-01 | Decide roadmap for Postgres support (event-store-only vs full read model). | Current docs and code indicate partial support and can confuse adopters. | `docs/POSTGRES.md`, `chronicle/store/postgres_event_store.py` | Clear support statement with explicit non-goals or implemented read-model milestone plan. |
| P3-02 | Add/complete encryption documentation and integration story. | `chronicle/core/encryption.py` references docs that do not exist. | `chronicle/core/encryption.py`, `docs/` (new encryption doc) | Encryption feature status and usage are documented and consistent with install extras. |
| P3-03 | Add optional extras for integration adapters (LangChain/LlamaIndex/Haystack) or document explicit install matrix. | Integration modules are optional but dependency path is not centrally managed. | `pyproject.toml`, `docs/integrating-with-chronicle.md` | Users have one clear install path per integration with tested versions. |
| P3-04 | Add release automation workflow (tag validation, build, optional publish). | Current release process is fully manual. | `.github/workflows/` (new release workflow), `CONTRIBUTING.md` | Tagged release flow is reproducible and documented; optional publish step gated. |
| P3-05 | Add supply-chain/security automation for Python and frontend deps. | No automated dependency/security checks currently run. | CI workflows, dependency config | Scheduled/manual scans exist (for example `pip-audit`, `npm audit`), with documented triage policy. |
| P3-06 | Add benchmark regression guardrails for defensibility scorer performance. | Benchmark exists, but no automated regression gates. | `scripts/benchmark_data/*`, CI/manual workflow docs | Baseline benchmark artifacts and acceptable regression thresholds are documented and enforced in manual CI runs. |
| P3-07 | Add architecture decision records (ADRs) for core irreversible choices. | Large design decisions are spread across docs and code comments. | `docs/adr/` (new) | ADR index exists with at least key decisions: event sourcing, verifier scope, API minimalism, policy profiles. |

## Done criteria for this backlog refresh

This TODO refresh is complete when:

1. New work is added here (not scattered across other docs).
2. Each new task references concrete code/docs areas.
3. P0 items are treated as blockers for reliability and API contract trust.

