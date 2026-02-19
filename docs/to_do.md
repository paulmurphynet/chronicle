# Implementation To-Do

Single source of truth for pending work.

Last refreshed: **2026-02-19**

## Product stance

Chronicle should optimize for:

1. **Trust in core artifacts** (`.chronicle`, verifier, event/read-model correctness)
2. **Contract stability** (scorer contract, API/client parity, reproducible behavior)
3. **Reference surfaces as adapters** (CLI/API/UI/integrations can evolve without breaking core trust)

## On hold by design

- **CI auto-triggers**: push/PR triggers in `.github/workflows/ci.yml` remain disabled; workflow is manual (`workflow_dispatch`) only.
- **Postgres read model**: `chronicle/store/postgres_event_store.py` exists, but a Postgres read model is not implemented.

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

## Release blockers

No active release blockers at this time. Keep validating changes against:

- Core trust surfaces (`.chronicle`, verifier, event/read-model invariants)
- Contract stability (scorer schema and API/client parity)
- Documentation accuracy and explicit limitations

## Post-release high-value work

Active implementation batch from `thought_experiments/decision-register.md` (2026-02-19), prioritized:

1. **TE-01 (P1): Policy compatibility preflight surfaces (API + CLI + UI).**
   Add a machine-readable compatibility endpoint plus CLI/UI preflight before checkpoint/export/submission actions.
   Done when users can compare built-under vs viewing-under profiles and see explicit deltas in one command/page and JSON response.
2. **TE-02 (P1): Link assurance metadata in defensibility outputs.**
   Add `link_assurance_level` and caveat text to scorer/API/export outputs so auto-linked evidence is distinguishable from reviewed links.
   Done when contract/schema/docs/tests cover the fields and backward compatibility is preserved.
3. **TE-04 (P1): Unified reviewer decision ledger/report.**
   Add a consolidated report/endpoint summarizing human confirmations, overrides, suggestion dismissals, unresolved tensions, and actor/time context.
   Done when legal/compliance/editorial review can consume one artifact instead of multiple command outputs.
4. **TE-05 (P2): Unified review packet generator.**
   Produce a single review bundle combining reasoning brief, chain-of-custody report, policy compatibility summary, policy rationale summary, and decision-ledger snapshot.
   Done when an investigator can generate this packet in one API/CLI action and the packet is documented in reference workflows.
5. **TE-06 (P2): Role-based review checklists by policy profile.**
   Add policy-linked checklist templates for journalism/legal/compliance workflows in docs/UI guidance.
   Done when templates are available and linked from reference workflow docs and policy profile docs.
6. **TE-03 (P2): Multi-vertical workflow parity expansion.**
   Add research/history profile example and expand reproducible workflows for legal/compliance/history use cases.
   Done when `scripts/run_reference_workflows.py` includes these scenarios with deterministic report output and docs are updated.

## Later / research backlog

Keep this section for longer-horizon items that are intentionally deferred. Current deferred item:

- Postgres read model parity (explicitly out of scope until SQLite baseline remains stable and maintainable).
- TE-D01 temporal uncertainty extension (range/confidence fields beyond `known_as_of`) deferred until current TE batch is complete and a migration-safe schema design is approved.

## Done criteria

This file is healthy when:

1. New pending work is added here, not scattered across docs.
2. Release blockers remain focused on trust/safety/contract stability.
3. Completed items are removed from blocker sections promptly.
