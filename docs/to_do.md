# Implementation To-Do

Single source of truth for pending work.

Last refreshed: 2026-02-23

## Product stance

Chronicle should optimize for:

1. Trust in core artifacts (`.chronicle`, verifier, event/read-model correctness)
2. Contract stability (scorer contract, API/client parity, reproducible behavior)
3. Reference surfaces as adapters (CLI/API/UI/integrations can evolve without breaking core trust)

## API contract hardening batch (2026-02-23)

- [x] Fix multipart evidence ingestion path to accept FastAPI/Starlette upload objects and preserve 413 behavior for oversized files.
- [x] Fix `GET /investigations/{id}/policy-sensitivity` to treat repeated `profile_id` as query params (not request body) and honor explicit profile selection.
- [x] Align tier-gated tension behavior across API contract tests and docs (`POST /investigations/{id}/tensions` requires `forge`/`vault`).
- [ ] Close post-public release gates tracked in this file (CI green with branch protection active, branch-protection rollout `status=passed`, live Neo4j CI evidence, W-07 external standards dispatch).

## Post-public gate automation batch (2026-02-23)

- [x] Add scripted Neo4j live CI evidence checker (`scripts/check_neo4j_ci_rollout.py`) and regression tests.
- [x] Add aggregate post-public finalization gate report (`scripts/check_post_public_finalization.py`) plus Make targets and checklist docs wiring.
- [x] Add machine-readable external standards dispatch tracker template (`docs/external-review-dispatch-log.template.json`) and wire runtime log path (`reports/standards_submissions/v0.3/external_review_dispatch_log.json`) in docs/checklists.
- [ ] Execute the new post-public checks against live public repo settings and update artifacts to `status=passed`.

## Active convergence program (public + CI + Postgres)

Target: converge to a production-first architecture while keeping SQLite accessible for low-friction local use.

### A. Installability and onboarding (do not lock out users)

- [x] Define support tiers in docs and release notes:
  - Lite (SQLite, local-first)
  - Team/Prod (Postgres)
  - Cloud-managed Postgres (Neon/RDS/Azure/GCP)
- [x] Add one-command local Postgres bootstrap (`docker compose`) and healthcheck UX.
- [x] Add `.env` bootstrap path for Postgres that does not overwrite user secrets.
- [x] Add `doctor` check for Postgres connectivity + dependency readiness.
- [x] Add smoke flow for Postgres event-store append/read/idempotency-key path.
- [x] Add troubleshooting section for Docker unavailable / managed-Postgres-only environments.

### B. Backend convergence (SQLite/Postgres parity)

- [x] Introduce explicit backend factory/config wiring for event store selection (env + session entry points).
- [x] Implement Postgres read model schema + projector parity with SQLite.
- [x] Implement replay/snapshot parity for Postgres-backed paths.
- [x] Ensure `.chronicle` export/import semantics stay backend-independent.
- [x] Add invariants verification parity for Postgres projects.
- [x] Publish and enforce migration/versioning policy for both backends.

### C. CI and public repo readiness

- [x] Enable push/PR triggers in `.github/workflows/ci.yml`.
- [x] Add backend matrix jobs (SQLite + Postgres service container).
- [x] Keep docs/contract/parity checks required in CI.
- [x] Add required check list for branch protection (document exact required jobs).
- [x] Add release gate for backend parity suite + verifier/conformance.

### D. Security and operations hardening

- [x] Keep import verification and evidence conflict protections release-critical.
- [x] Add structured operational runbook for DB backup/restore and disaster recovery.
- [x] Add dependency and container vulnerability checks to release criteria.
- [x] Add environment hardening guide for managed Postgres (TLS, least privilege, rotation).

### E. Support policy and communication

- [x] Define GA/beta/experimental support levels in README/docs.
- [x] Define backward compatibility policy for contracts and `.chronicle` format.
- [x] Add deprecation policy and timeline format.
- [x] Publish "what production-ready means" checklist with objective pass/fail criteria.

### Program release criteria (must pass together)

- [x] Backend parity: same scenario outputs equivalent defensibility results on SQLite and Postgres.
- [ ] CI green for required jobs on push/PR with branch protection active.
- [x] Postgres onboarding from zero to first successful smoke run in <= 10 minutes.
- [x] Docs and troubleshooting validated by docs link/currency checks.

## Public launch readiness (v0.9.0 preflight 2026-02-20)

### Release-critical blockers

- [x] Fix core type-check failure in Postgres event store (`chronicle/store/postgres_event_store.py`, mypy tuple unpack on `fetchone()`).
- [x] Make core format gate pass (`ruff format --check chronicle tools`).
- [x] Harden `scripts/supply_chain_gate.py` to accept current `pip-audit` JSON entries that include `skip_reason` without `vulns`.
- [x] Add deterministic frontend dependency lockfile and switch CI/release frontend install steps from `npm install` to `npm ci`.
  - [x] `frontend/package-lock.json` committed (required for `npm ci` and deterministic `npm audit`).
  - [x] CI/release/supply-chain workflows switched to `npm ci`.
  - [x] Lockfile generation confirmed with elevated network access: `npm install --package-lock-only --ignore-scripts --no-audit --no-fund` (`EXIT:0`).
- [x] Resolve deterministic check invocation mismatch across local/CI/release (`scripts/check_deterministic_defensibility.py` import path expectations vs `python3 scripts/...` calls).
- [x] Align project release metadata for the intended launch version (`pyproject.toml`, `frontend/package.json`, `CHANGELOG.md`, release-tag usage).
- [ ] Re-run live branch-protection rollout verification after repo is public and record `status=passed`.

### Quality and launch-polish follow-ups

- [x] Document frontend local prerequisites for `npm run check:api-routes` (Python environment with Chronicle API deps available).
- [x] Decide and document lint scope policy (release-gated: `chronicle` + `tools`; broader `scripts/` + `tests` sweep tracked separately) and enforce consistently in local+CI commands.
- [x] Add contributor guidance for local dependency audit prerequisites (frontend lockfile + npm audit behavior).

## Neo4j best-in-class program (approved 2026-02-20)

Goal: raise Neo4j from "contract-correct optional projection" to a production-grade, scalable, and operable graph surface.

### N. Core engineering upgrades

- [x] N-01 Replace full-table `fetchall()` paths with streaming/chunked export for `neo4j-export`.
  - Move CSV export reads to cursor/`fetchmany()` loops.
  - Keep deterministic row ordering per CSV.
- [x] N-02 Replace full-table in-memory row materialization in `neo4j-sync` with streaming/chunked sync.
  - Bound memory for large investigations.
  - Keep idempotent MERGE semantics unchanged.
- [x] N-03 Harden relationship identity semantics to avoid accidental edge coalescing for multi-link cases.
  - Preserve distinct support/challenge links when same span/claim pair has multiple link_uids.
  - Add explicit regression tests for repeated span-claim links.
- [x] N-04 Add Neo4j runtime hardening controls.
  - CLI/config support for Neo4j database selection.
  - Retry/backoff and timeout controls for transient failures.
  - Clear user-facing diagnostics on connectivity/auth/db errors.
- [x] N-05 Add sync/export observability outputs.
  - Structured progress logs (table/phase, row counts, batch counts, elapsed time).
  - Optional JSON report artifact for sync/export runs (for release evidence).

### N. Quality and verification upgrades

- [x] N-06 Add live Neo4j integration tests (service-container) beyond static contract parity checks.
  - Validate end-to-end sync behavior against real Neo4j (not only fixture/text checks).
  - Include dedupe and non-dedupe mode assertions.
  - Added `tests/test_neo4j_live_integration.py` and wired CI/release service-container jobs.
  - First public CI run still required to record external `status=passed` evidence.
- [x] N-07 Add performance benchmark harness for graph projection paths.
  - Generate medium/large fixture datasets.
  - Track export/sync throughput and memory ceilings.
  - Add non-regression thresholds to release evidence.
- [x] N-08 Add cross-mode parity tests for graph semantics.
  - Validate expected equivalence/differences between rebuild CSV path and direct sync path.
  - Validate lineage semantics in dedupe mode (`CONTAINS_CLAIM`, `CONTAINS_EVIDENCE`).
- [x] N-09 Expand failure-mode tests for Neo4j operations.
  - Network interruption, partial failure, rerun-idempotency behavior.
  - Misconfiguration cases (`NEO4J_URI`, credentials, db name, driver unavailable).

### N. Docs and operations upgrades

- [x] N-10 Publish Neo4j production operations runbook.
  - Backup/restore guidance for graph data lifecycle.
  - Sync cadence strategy, drift handling, and re-sync procedures.
  - Capacity and cost guardrails for Aura/self-hosted Neo4j.
- [x] N-11 Publish query-pack and indexing guidance for common Chronicle graph workflows.
  - "Top unresolved tension clusters", "support/challenge balance", "source concentration", lineage traversals.
  - Recommend index/constraint posture per query class.
- [x] N-12 Add explicit support-level statement for Neo4j surface (GA/Beta/Experimental) in support policy.
  - Define SLA expectations and compatibility guarantees for graph schema evolution.

### Neo4j best-in-class done criteria

- [x] Large-project sync/export can run with bounded memory and deterministic results.
  - Export baseline: `docs/benchmarks/neo4j_projection_baseline_v0.9.0.json`.
  - Live sync baseline: `docs/benchmarks/neo4j_projection_sync_baseline_v0.9.0.json` (real `neo4j:5` run).
- [ ] Live Neo4j integration tests pass in CI and are part of release gating.
  - CI/release service-container jobs are wired; awaiting first public CI evidence run.
  - Local live Neo4j run is green (`tests/test_neo4j_live_integration.py`: 2 passed against local `neo4j:5`).
- [x] Performance baseline + regression thresholds are captured in release artifacts.
  - Baseline artifact: `docs/benchmarks/neo4j_projection_baseline_v0.9.0.json` (+ summary in `.md`).
- [x] Ops runbook + query pack are published and validated by docs checks.
- [x] Neo4j support level and compatibility policy are explicit in docs.

## Standards and whitepaper program (approved 2026-02-20)

Goal: make Chronicle standards-compatible without destabilizing core contracts, and produce a publication-ready standards whitepaper.

### S. Interoperability profile implementation

- [x] S-01 Define and publish Chronicle standards profile v0.1 (scope, compatibility tiers, non-goals).
  - Track canonical stance in docs and ADRs.
  - Keep `.chronicle` and verifier as canonical trust artifacts.
- [x] S-02 Implement JSON-LD export profile for investigation-level data.
  - Include claims, evidence, support/challenge links, tensions, sources.
  - Add versioned JSON-LD context and fixture tests.
- [x] S-03 Implement PROV-compatible mapping profile and validation fixtures.
  - Provide deterministic mapping rules from Chronicle entities/events.
  - Add regression tests for required PROV-aligned fields.
- [x] S-04 Add ClaimReview export adapter/profile.
  - Map Chronicle claim/review outputs to schema.org `ClaimReview`.
  - Document caveats for fields that are optional or unavailable.
- [x] S-05 Add RO-Crate export profile for package interoperability.
  - Include metadata and pointers to Chronicle artifacts.
  - Add sample crate fixtures and compatibility checks.
- [x] S-06 Add C2PA compatibility path.
  - Record/import C2PA assertion references in evidence metadata.
  - Export explicit verification semantics (`disabled` or `metadata_only`) without claiming cryptographic verification.
- [x] S-07 Add VC/Data Integrity compatibility path.
  - Define attestation envelope for claims/checkpoints/artifacts.
  - Add verification-status fields and explicit non-verified behavior (`disabled` vs `metadata_only`).
- [x] S-08 Publish adjacent standards guidance.
  - Document integration boundaries for OpenLineage, in-toto, and SLSA.
  - Explicitly state these are complementary layers, not Chronicle replacements.

### W. Whitepaper and publication track

- [x] W-01 Publish working whitepaper draft and editorial workflow.
- [x] W-02 Build a reproducible evidence pack for whitepaper claims.
  - Mapping fixtures, benchmark commands, verifier outputs, profile examples.
- [x] W-03 Add versioned citation and publication metadata for whitepaper revisions.
- [x] W-04 Run internal technical review and capture accepted/rejected edits.
- [x] W-05 Prepare standards-submission package and outreach notes for relevant communities.
- [x] W-06 Raise whitepaper draft to publication-grade structure and conformance reporting (v0.3).
- [ ] W-07 Run external standards review cycle (JSON-LD/PROV/VC, C2PA, applied research) and log accepted/rejected deltas.
  - [x] Prepared review-cycle tracker and send-ready venue bundles/snapshots (`reports/standards_submissions/v0.3/`).
  - [ ] Dispatch to external reviewers once repo is public; then record accepted/rejected/follow-up deltas.
- [x] W-08 Produce venue-specific publication bundles (formatting, submission checklists, and archive snapshots).

## On hold by design

- No active on-hold-by-design items for convergence work. Use this section only for explicit deferrals.

## Recently completed

- **Security + reliability hardening batch completed (2026-02-21)**:
  - removed process-wide environment mutation from Postgres helper scripts (`scripts/postgres_backend_parity.py`, `scripts/postgres_onboarding_timed_check.py`, `scripts/postgres_smoke.py`, `scripts/postgres_doctor.py`) to keep backend selection hermetic.
  - restricted `.chronicle` import to contract paths only (`manifest.json`, `chronicle.db`, `evidence/**`) and reject unexpected archive entries.
  - added ZIP safety budgets (entry count, total/member uncompressed bytes, suspicious compression ratio checks) and streaming ZIP member reads/writes in import/verification paths.
  - added CI guard tests for env isolation and archive hardening regressions (`tests/test_postgres_convergence_scripts.py`, `tests/test_phase5_coverage.py`, `tests/test_verifier.py`).
- **Neo4j best-in-class batch (non-CI-dependent) completed**: added projection benchmark harness and tests (`scripts/benchmark_data/run_neo4j_projection_benchmark.py`, `tests/test_neo4j_projection_benchmark.py`), cross-mode parity tests (`tests/test_neo4j_projection_parity.py`), failure-mode tests and missing-driver diagnostics (`tests/test_neo4j_sync_failures.py`, `chronicle/store/neo4j_sync.py`), and published operations/query docs (`docs/neo4j-operations-runbook.md`, `docs/neo4j-query-pack.md`) with support-policy compatibility details.
- **Neo4j live large-run evidence completed**: executed live Neo4j integration tests (`tests/test_neo4j_live_integration.py`, 2 passed) and captured thresholded sync benchmark evidence (`docs/benchmarks/neo4j_projection_sync_baseline_v0.9.0.json` + `.md`) against local `neo4j:5`.
- **Post-public closure playbook completed**: added `docs/post-public-finalization-checklist.md` to execute the remaining public/CI/external tasks in one pass.
- Merge-import correctness fixed (duplicate skip per event + `rowid` replay order), with regression tests.
- API/user-error mapping centralized for predictable 4xx/429 responses.
- HTTP client routes and response parsing aligned with current API behavior.
- Doc links fixed and link checker improved for repo-wide scans.
- Optional extras aligned (`postgres`, `encryption`) and encryption doc added.
- API request correlation IDs and structured request logs added (`X-Request-Id` in responses + error bodies).
- API contract tests added for docs flow, identity headers, error mapping, and export/import.
- Verifier parity tests added for `chronicle.verify` and standalone `chronicle-verify` on valid and tampered artifacts.
- Doc contract smoke tests added for README quick-start scorer payload and API `/score` behavior.
- Contributor workflow docs updated for `Makefile` checks and offline/no-network development.
- Quality gates now pass in this environment: `pytest`, `ruff`, `mypy`, docs link checks.
- **RB-04 completed**: `chronicle/store/session.py` and `chronicle/cli/main.py` split into coherent modules (`session_writes`, `session_queries`, `command_handlers`, `parser`, `dispatch`) with behavior preserved and tests passing.
- **PR-01 completed**: frontend test harness added (Vitest + Testing Library) with API pagination and page smoke coverage.
- **PR-02 completed**: manual CI workflow includes frontend route-parity, lint, test, and build checks.
- **PR-03 completed**: cursor pagination added for high-volume list endpoints and documented in API docs.
- **PR-04 completed**: graph endpoint switched to batched read-model access with regression test guarding against per-claim N+1 lookups.
- **PR-05 completed**: OpenAPI-derived frontend route constants and parity generation/check scripts added.
- **L-01 completed (decision)**: SQLite-first support posture documented via ADR; Postgres read model remains explicit roadmap work.
- **L-02 completed**: manual release workflow and tag/version validation script added.
- **L-03 completed**: manual supply-chain scan workflow and threshold gate script added (`pip-audit`, `npm audit`).
- **L-04 completed**: benchmark guardrail script added for defensibility regression checks.
- **L-05 completed**: ADR scaffolding and initial accepted ADRs added under `docs/adr/`.
- **Strategy execution completed (Phase 1 kickoff)**: 30/60/90 roadmap added with dated execution milestones, and trust KPI workflow documented/implemented (`docs/trust-metrics.md`, `scripts/benchmark_data/trust_progress_report.py`, tests).
- **Neo4j hardening completed**: added cross-surface parity check (`scripts/check_neo4j_contract.py`) validating sync/export/rebuild/docs alignment, fixed relationship rationale parity in rebuild Cypher, and aligned schema docs to include dedupe-mode lineage relationships.
- **Phase 2 kickoff completed (initial artifacts)**: added reproducible reference workflows and an integration acceptance checklist (`docs/reference-workflows.md`, `docs/integration-acceptance-checklist.md`).
- **Phase 2 execution tooling completed**: added `scripts/run_reference_workflows.py` (consolidated runner with JSON report), plus session-mode fallback in benchmark and compliance workflow scripts to reduce external dependency friction.
- **Quality gate integration completed**: reference workflow suite added to Makefile `check` target and manual CI workflow.
- **Integration starter tooling completed**: added adapter starter/validator (`scripts/adapters/starter_batch_to_scorer.py`, `scripts/adapters/validate_adapter_outputs.py`) with tests and docs wiring for contributor onboarding.
- **Adapter examples automation completed**: added checked-in adapter example files, `scripts/adapters/check_examples.py`, tests, and CI/Makefile gates for example+contract validation.
- **Documentation currency guard completed**: added `scripts/check_docs_currency.py` and integrated it into Makefile/CI to keep README/docs/lessons/quizzes aligned with current workflow commands.
- **Adapter mapping profiles completed**: `starter_batch_to_scorer.py` now supports JSON mapping profiles (including nested key paths), with nested examples and tests.
- **Documentation consistency sweep completed**: updated README/docs plus lessons/quizzes to reflect current benchmark, adapter, and Neo4j validation workflows.
- **TE-01 completed**: policy compatibility preflight shipped across session API (`get_policy_compatibility_preflight`), HTTP (`GET /investigations/{id}/policy-compatibility`), CLI (`chronicle policy compat`), and Reference UI policy tab; frontend route parity regenerated and regression tests added for session/CLI.
- **TE-02 completed**: added `link_assurance_level` and `link_assurance_caveat` to defensibility metrics surfaced by scorer/session/API/export (including eval contract docs/schema updates and regression tests) so auto-linked vs human-reviewed link posture is explicit.
- **TE-04 completed**: shipped a unified reviewer decision ledger/report across session/API/CLI (`get_reviewer_decision_ledger`, `GET /investigations/{id}/reviewer-decision-ledger`, `chronicle reviewer-decision-ledger`) consolidating confirmations, overrides, dismissals, tier transitions, actor/time context, and unresolved tensions in one artifact.
- **TE-05 completed**: shipped a unified review packet generator across session/API/CLI (`get_review_packet`, `GET /investigations/{id}/review-packet`, `chronicle review-packet`) combining policy compatibility, policy rationale summary, decision ledger snapshot, chain-of-custody report metadata, reasoning briefs, and audit export bundle in one action.
- **TE-06 completed**: added role-based review checklist templates (`docs/role-based-review-checklists.md`) and linked them from policy profile docs, reference workflows, and Reference UI policy guidance.
- **TE-03 completed**: expanded multi-vertical workflow parity with new legal/history deterministic sample generators and reference workflow runner coverage (`scripts/verticals/legal/generate_sample.py`, `scripts/verticals/history/generate_sample.py`, `scripts/run_reference_workflows.py`), plus a new history/research policy example profile (`docs/policy-profiles/history_research.json`).
- **TE-D01 completed (migration-safe)**: temporal uncertainty extension shipped without schema migration by standardizing extended `temporal_json` keys (`known_range_start`, `known_range_end`, `temporal_confidence`) in temporalization command validation, exposing them in defensibility/eval knowability outputs, and updating docs/schema/tests.
- **Sample data quality hardening completed**: expanded vertical generators (journalism/legal/history + new compliance) with richer provenance/challenge/tension realism, fixed journalism policy-profile pathing, added vertical sample quality gate (`scripts/verticals/check_sample_quality.py`), and integrated sample-quality workflow coverage/tests.
- **R2-04 completed**: shipped one-shot readiness gate (`scripts/review_readiness_gate.py`) and integrated it into the reference workflow runner (`scripts/run_reference_workflows.py` workflow `readiness`) with tests/docs coverage.
- **R2-01 completed**: shipped policy sensitivity comparison report across session/API/CLI (`get_policy_sensitivity_report`, `GET /investigations/{id}/policy-sensitivity`, `chronicle policy sensitivity`) with claim-level side-by-side outcomes, pairwise delta summaries, practical review implications, and interpretation guidance in reference workflows.
- **R2-02 completed**: shipped portfolio risk summary command (`scripts/portfolio_risk_summary.py`) with cross-investigation unresolved-tension totals/rates, override concentration analytics, readiness posture breakdown, deterministic risk ranking, JSON artifact output, and regression tests for unresolved/override aggregation behavior.
- **R2-03 completed**: shipped a deterministic messy-corpus stress pack (`scripts/verticals/messy/generate_sample.py`) covering partial metadata, evidence supersession, redaction, and ambiguous chronology; integrated it into sample quality checks (`scripts/verticals/check_sample_quality.py`) and reference workflow runner coverage (`scripts/run_reference_workflows.py` workflow `messy`) with tests/docs updates.
- **Postgres onboarding baseline completed**: added local bootstrap tooling (`docker-compose.postgres.yml`, `.env.postgres.example`, `make postgres-*` targets), connectivity doctor (`scripts/postgres_doctor.py`), and event-store smoke runner (`scripts/postgres_smoke.py`) with docs wiring in `docs/POSTGRES.md`.
- **CI convergence kickoff completed**: enabled CI push/PR triggers and added a Postgres service-container smoke job (`postgres_doctor.py` + `postgres_smoke.py`) in `.github/workflows/ci.yml`.
- **Support and release policy baseline completed**: added formal support/compatibility/deprecation policy (`docs/support-policy.md`) and objective production-go checklist (`docs/production-readiness-checklist.md`), then linked both from README/docs index.
- **Branch protection and Postgres ops docs completed**: added required-check configuration guide (`docs/ci-branch-protection.md`), Postgres backup/restore DR runbook (`docs/postgres-operations-runbook.md`), and managed Postgres hardening guidance (`docs/postgres-hardening.md`).
- **Release-gate hardening completed**: expanded manual release workflow to include docs/parity gates, verifier+conformance checks, Postgres doctor/smoke checks, and dependency vulnerability threshold enforcement.
- **B1 completed (backend wiring)**: added explicit backend config/factory wiring (`chronicle/store/backend_config.py`) and session entrypoint integration (`chronicle/store/session.py`) so `CHRONICLE_EVENT_STORE` is parsed/validated consistently, with fail-fast user guidance for current Postgres read-model limitation.
- **B2 completed (schema + projector parity)**: added Postgres read-model schema initializer and SQLite-to-Postgres projection SQL compatibility layer (`chronicle/store/postgres_projection.py`), then wired `PostgresEventStore` append flow to project events into Postgres read-model tables.
- **B3 completed (replay/snapshot parity)**: added Postgres replay and snapshot helpers (`replay_postgres_read_model_from_url`, `create_postgres_read_model_snapshot_from_url`, `restore_postgres_read_model_snapshot_from_url`) and routed CLI `replay`/`snapshot` commands through Postgres mode when configured.
- **B4 completed (backend-independent archive semantics)**: decoupled `.chronicle` import/export paths from session backend selection so CLI/API archive operations remain available under `CHRONICLE_EVENT_STORE=postgres`, with routing regression tests.
- **B5 completed (verify parity)**: added Postgres invariant verification entrypoint (`verify_postgres_url`) and wired CLI `chronicle verify` to use Postgres checks under `CHRONICLE_EVENT_STORE=postgres`.
- **B6 completed (migration/versioning policy)**: added backend migration and versioning policy doc (`docs/backend-migration-versioning-policy.md`) and linked it in README/docs index for release/process enforcement.
- **Release-criteria automation expanded**: added deterministic backend parity gate (`scripts/postgres_backend_parity.py`) and timed onboarding gate (`scripts/postgres_onboarding_timed_check.py`), then wired both into CI/release Postgres jobs with JSON artifacts.
- **Local Postgres convergence validation completed**: confirmed `make postgres-parity` and `make postgres-onboarding-check` pass against local Docker Postgres after smoke payload parity fix.
- **Security release criteria expanded**: added Trivy-based container vulnerability gating (`scripts/container_security_gate.py`) and wired supply-chain/release workflows to enforce container HIGH/CRITICAL thresholds alongside dependency scans.
- **Postgres image security baseline completed**: switched local/CI/release Postgres baseline to a pinned Bitnami Postgres digest (`bitnami/postgresql@sha256:9a4d4d644f36fa01715066c769e0c480a4bdd528f6b4880fa8e32d9fd715ec8a`) after validating Chronicle doctor/smoke compatibility and verifying Trivy HIGH/CRITICAL clean image scans.
- **Docs release-criteria check completed**: reran docs link and docs currency gates (`scripts/check_doc_links.py`, `scripts/check_docs_currency.py`) and confirmed pass.
- **Branch-protection rollout automation completed**: added GitHub API verifier script (`scripts/check_branch_protection_rollout.py`), fixture-based regression tests (`tests/test_branch_protection_rollout.py`), make target (`branch-protection-rollout-check`), and release-evidence doc path (`docs/branch-protection-rollout-verification.md`).

## Release blockers

Active release blocker:

- CI branch-protection rollout still pending final external verification (`reports/branch_protection_rollout_report.json` must report `status=passed` against live repo settings).
- GitHub plan constraint: private-repo branch protection unavailable on current tier; unblock by upgrading to Pro/Team/Enterprise or switching to public before final release sign-off.

Continue validating changes against:

- Core trust surfaces (`.chronicle`, verifier, event/read-model invariants)
- Contract stability (scorer schema and API/client parity)
- Documentation accuracy and explicit limitations

## Immediate next sprint (tomorrow)

Priority implementation items accepted on 2026-02-20 for immediate execution:

- [x] Start standards profile implementation with JSON-LD + PROV export MVP.
  - Add a first `build_standards_jsonld_export(...)` path in export commands.
  - Include fixture tests for one investigation containing support/challenge/tension/source cases.
- [x] Prepare whitepaper v0.2 from the working draft with concrete Chronicle examples.
  - Add one end-to-end example appendix based on an existing deterministic sample.
  - Add explicit guarantees/non-guarantees matrix tied to verifier and scorecard docs.
- [x] Ship opinionated starter packs (Journalism, Legal, Audit) to reduce first-project ambiguity and improve adoption.
  - Add template bootstrap commands/fixtures for each pack.
  - Include schema defaults, policy profile defaults, and report/export examples per pack.
  - Add docs walkthroughs and acceptance tests proving each starter pack reaches a defensible report from a clean workspace.
- [x] Publish trust artifacts focused on defensibility and failure handling (not marketing collateral).
  - Add an explicit "rejected feature decisions" log with rationale and tradeoffs.
  - Add adversarial/failure-mode examples that show uncertainty disclosure and safe failure behavior.
  - Add reproducibility checks for deterministic scenarios (`same input -> same defensibility outcome`) in CI/release gates.
- [x] Prioritize integration hooks for real-world workflow interoperability.
  - Hardened import/export paths for CSV, Markdown, JSON, and signed `.chronicle` archive bundles via validators, markdown renderer, signed-bundle helpers, and docs: `chronicle/store/commands/generic_export.py`, `chronicle/store/commands/reasoning_brief.py`, `chronicle/store/export_import.py`, `docs/integration-export-hardening.md`.
  - Added one end-to-end API ingestion example pipeline (batch input -> Chronicle -> defensibility artifact output): `scripts/api_ingestion_pipeline_example.py`, `docs/api-ingestion-pipeline-example.md`, `tests/test_api_ingestion_pipeline_example.py`.
  - Added integration contract tests and harnesses to stabilize adapter/API-facing import/export behavior across releases: `scripts/check_integration_export_contracts.py`, `tests/test_integration_export_contracts.py`, `tests/test_generic_export_contracts.py`, `tests/test_phase5_coverage.py`.

## Later / research backlog

Keep this section for longer-horizon items that are intentionally deferred. Current deferred item:

- Postgres read model parity (explicitly out of scope until SQLite baseline remains stable and maintainable).
- Frontend lint-toolchain advisory follow-up: `eslint` currently depends on `ajv@6` (Trivy medium `CVE-2025-69873`) with no compatible upstream fix in current stable ESLint line; track upstream remediation before re-enabling strict MEDIUM=0 container policy.

## Done criteria

This file is healthy when:

1. New pending work is added here, not scattered across docs.
2. Release blockers remain focused on trust/safety/contract stability.
3. Completed items are removed from blocker sections promptly.
