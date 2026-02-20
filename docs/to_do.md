# Implementation To-Do

Single source of truth for pending work.

Last refreshed: **2026-02-20**

## Product stance

Chronicle should optimize for:

1. **Trust in core artifacts** (`.chronicle`, verifier, event/read-model correctness)
2. **Contract stability** (scorer contract, API/client parity, reproducible behavior)
3. **Reference surfaces as adapters** (CLI/API/UI/integrations can evolve without breaking core trust)

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
- [ ] Implement Postgres read model schema + projector parity with SQLite.
- [ ] Implement replay/snapshot parity for Postgres-backed paths.
- [ ] Ensure `.chronicle` export/import semantics stay backend-independent.
- [ ] Add invariants verification parity for Postgres projects.
- [ ] Publish and enforce migration/versioning policy for both backends.

### C. CI and public repo readiness

- [x] Enable push/PR triggers in `.github/workflows/ci.yml`.
- [x] Add backend matrix jobs (SQLite + Postgres service container).
- [x] Keep docs/contract/parity checks required in CI.
- [x] Add required check list for branch protection (document exact required jobs).
- [x] Add release gate for backend parity suite + verifier/conformance.

### D. Security and operations hardening

- [x] Keep import verification and evidence conflict protections release-critical.
- [x] Add structured operational runbook for DB backup/restore and disaster recovery.
- [ ] Add dependency and container vulnerability checks to release criteria.
- [x] Add environment hardening guide for managed Postgres (TLS, least privilege, rotation).

### E. Support policy and communication

- [x] Define GA/beta/experimental support levels in README/docs.
- [x] Define backward compatibility policy for contracts and `.chronicle` format.
- [x] Add deprecation policy and timeline format.
- [x] Publish "what production-ready means" checklist with objective pass/fail criteria.

### Program release criteria (must pass together)

- [ ] Backend parity: same scenario outputs equivalent defensibility results on SQLite and Postgres.
- [ ] CI green for required jobs on push/PR with branch protection active.
- [ ] Postgres onboarding from zero to first successful smoke run in <= 10 minutes.
- [ ] Docs and troubleshooting validated by docs link/currency checks.

## On hold by design

- No active on-hold-by-design items for convergence work. Use this section only for explicit deferrals.

## Recently completed

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

## Release blockers

No active release blockers at this time. Keep validating changes against:

- Core trust surfaces (`.chronicle`, verifier, event/read-model invariants)
- Contract stability (scorer schema and API/client parity)
- Documentation accuracy and explicit limitations

## Post-release high-value work

Round 2 prioritized backlog (from thought-experiment rerun on 2026-02-20):

All Round 2 backlog items are now completed. Add new post-release items here as they are accepted.

## Later / research backlog

Keep this section for longer-horizon items that are intentionally deferred. Current deferred item:

- Postgres read model parity (explicitly out of scope until SQLite baseline remains stable and maintainable).

## Done criteria

This file is healthy when:

1. New pending work is added here, not scattered across docs.
2. Release blockers remain focused on trust/safety/contract stability.
3. Completed items are removed from blocker sections promptly.
