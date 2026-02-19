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

## Release blockers

These are required before public MIT release.

| ID | Item | Why it blocks release | Primary files | Done when |
|---|---|---|---|---|
| RB-04 | Modularization pass 1 for monolithic surfaces (`cli/main.py`, `store/session.py`). | Maintainability risk is high for solo development and community contributors. | `chronicle/cli/`, `chronicle/store/` | Core command/session responsibilities are split into coherent modules with behavior preserved. |

## Post-release high-value work

| ID | Item | Why it matters | Primary files | Done when |
|---|---|---|---|---|
| PR-01 | Frontend test harness (unit + integration smoke). | Reference UI should have regression protection once adoption grows. | `frontend/` | Core UI flows are covered by automated tests. |
| PR-02 | Frontend CI checks as manual workflow job. | Keeps UI quality aligned with backend standards. | `.github/workflows/ci.yml`, `frontend/package.json` | Frontend build/lint/tests run in CI workflow. |
| PR-03 | Pagination/cursor strategy for high-volume endpoints. | Scalability and UI responsiveness. | `chronicle/api/app.py`, frontend consumers | Stable paged responses and docs for list/graph endpoints. |
| PR-04 | Optimize graph endpoint to avoid N+1 queries. | Improves performance on larger investigations. | `chronicle/api/app.py`, read-model helpers | Graph computation uses batched data access with regression benchmark. |
| PR-05 | Introduce generated typed frontend API client from OpenAPI. | Reduces manual drift between API and UI. | `frontend/src/lib/api.ts`, OpenAPI tooling | Generated client/types integrated or equivalent parity checks enforced. |

## Later / research backlog

| ID | Item | Notes |
|---|---|---|
| L-01 | Decide Postgres roadmap (event-store-only vs full read model). | Keep support statement explicit; avoid ambiguous partial support. |
| L-02 | Release automation (tag validation/build/publish gates). | Useful when release cadence increases. |
| L-03 | Supply-chain/security automation (`pip-audit`, `npm audit`, policy). | Add scheduled/manual workflows with triage guidance. |
| L-04 | Benchmark regression guardrails for defensibility scorer. | Move benchmark from informative to gated as baseline matures. |
| L-05 | ADRs for irreversible architecture choices. | Capture decisions around event sourcing, verifier scope, contract boundaries. |

## Done criteria

This file is healthy when:

1. New pending work is added here, not scattered across docs.
2. Release blockers remain focused on trust/safety/contract stability.
3. Completed items are removed from blocker sections promptly.
