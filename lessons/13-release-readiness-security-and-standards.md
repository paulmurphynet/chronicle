# Lesson 13: Release readiness, security gates, and standards operations

Objectives: You will understand how Chronicle moves from “code that works” to “release that can be defended”: objective quality gates, supply-chain security checks, branch-protection rollout evidence, and standards/whitepaper review operations.

**Key files:**

- [Makefile](../Makefile) — local release-gated checks (`make check`) and optional broader hygiene checks (`lint-all`, `format-check-all`)
- [.github/workflows/ci.yml](../.github/workflows/ci.yml) — push/PR CI jobs and required checks
- [.github/workflows/release.yml](../.github/workflows/release.yml) — manual release gate workflow
- [.github/workflows/supply-chain.yml](../.github/workflows/supply-chain.yml) — dependency + container scan workflow
- [scripts/supply_chain_gate.py](../scripts/supply_chain_gate.py) — enforces pip/npm vulnerability thresholds
- [scripts/container_security_gate.py](../scripts/container_security_gate.py) — enforces Trivy report thresholds
- [scripts/check_branch_protection_rollout.py](../scripts/check_branch_protection_rollout.py) — machine-readable branch protection + CI evidence checker
- [docs/production-readiness-checklist.md](../docs/production-readiness-checklist.md) — release GO/NO-GO criteria
- [docs/security-automation.md](../docs/security-automation.md) — security scan process and triage
- [docs/ci-branch-protection.md](../docs/ci-branch-protection.md) — required branch protection checks
- [docs/branch-protection-rollout-verification.md](../docs/branch-protection-rollout-verification.md) — rollout verification process + artifact semantics
- [docs/to_do.md](../docs/to_do.md) — single source of truth for remaining launch blockers
- [docs/whitepaper-plan.md](../docs/whitepaper-plan.md) — whitepaper workflow and standards-facing publication track
- [docs/standards-submission-package.md](../docs/standards-submission-package.md) — venue-specific submission checklist
- [docs/external-standards-review-cycle.md](../docs/external-standards-review-cycle.md) — accepted/rejected deltas from external reviewers
- [docs/mcp.md](../docs/mcp.md) — MCP deployment surface and transport security notes

---

## 1. Readiness is a contract, not a feeling

Chronicle treats release readiness as an explicit contract:

- Core trust must pass: verifier, invariants, conformance.
- Backend confidence must pass: SQLite baseline and Postgres smoke/parity/onboarding.
- Operational confidence must pass: supply-chain and container thresholds.
- Governance confidence must pass: branch protection and required CI checks.

The canonical checklist is [docs/production-readiness-checklist.md](../docs/production-readiness-checklist.md). Use this file as your release decision surface, not ad-hoc judgment.

---

## 2. Local gates vs CI gates

Open [Makefile](../Makefile):

- `make check` is the local release-gated bundle:
  - `lint` + `format-check` (core surfaces)
  - `typecheck`
  - `test` (SQLite mode)
  - docs checks
  - interoperability/parity/determinism checks
- `lint-all` and `format-check-all` are intentionally separate:
  - broader repo hygiene for `scripts/` + `tests`
  - useful for cleanup work, but not currently part of release-blocking core gates

Open [ci.yml](../.github/workflows/ci.yml):

- Required jobs:
  - `lint-and-test (3.11)`
  - `lint-and-test (3.12)`
  - `frontend-checks`
  - `postgres-event-store-smoke`
- CI extends local checks with matrix/platform behavior and build-environment realism.

---

## 3. Security gating model

Chronicle uses fail-closed security gating:

1. Dependency scans (`pip-audit`, `npm audit`) produce reports.
2. `scripts/supply_chain_gate.py` enforces thresholds.
3. Trivy filesystem + image scans produce reports.
4. `scripts/container_security_gate.py` enforces thresholds.

Review [docs/security-automation.md](../docs/security-automation.md):

- `npm audit` requires a committed `frontend/package-lock.json`.
- Once lockfile exists, CI/release should use `npm ci` for deterministic installs.

This model keeps “scan succeeded but parser failed silently” from becoming a release loophole.

---

## 4. Branch protection as release evidence

Branch protection is treated as a verifiable artifact, not a screenshot process.

Open [scripts/check_branch_protection_rollout.py](../scripts/check_branch_protection_rollout.py) and [docs/branch-protection-rollout-verification.md](../docs/branch-protection-rollout-verification.md):

- Script validates:
  - branch protection exists
  - required checks include the exact CI jobs
  - critical protection settings are enabled
  - recent successful push and PR runs contain all required jobs
- Output artifact:
  - `reports/branch_protection_rollout_report.json`
- Status values:
  - `passed`, `failed`, `blocked`

Release readiness requires `passed`, not merely “looks configured.”

---

## 5. Standards and whitepaper operations

Chronicle’s standards posture is operational, not marketing:

- Standards mappings ship as explicit profiles and adapters.
- Claims about standards alignment are backed by reproducible artifacts.
- External review deltas are tracked as accepted/rejected follow-ups.

Read:

- [docs/whitepaper-plan.md](../docs/whitepaper-plan.md)
- [docs/standards-submission-package.md](../docs/standards-submission-package.md)
- [docs/external-standards-review-cycle.md](../docs/external-standards-review-cycle.md)
- [docs/to_do.md](../docs/to_do.md) (open items for public-repo-triggered review dispatch)

This is the governance layer for becoming a credible standards-facing project.

---

## 6. What remains open at launch-prep time

The current “not done yet” items are intentionally explicit in [docs/to_do.md](../docs/to_do.md). Typical examples:

- lockfile-driven deterministic frontend dependency path (`package-lock.json` + `npm ci` in workflows)
- post-public branch-protection rollout verification report with `status=passed`
- external standards-review dispatch and logged deltas

The key rule: unresolved items must stay visible in `docs/to_do.md` until objectively closed.

---

## 7. Optional integration surfaces still need operational discipline

Chronicle has optional extras (`.[api]`, `.[mcp]`, `.[neo4j]`) so teams can adopt surfaces incrementally. Optional does not mean unmanaged:

- If MCP is part of your deployment, include a local smoke check in release prep (server starts, one create/ingest/claim/link flow succeeds).
- For network MCP transports, include auth/network boundary verification in your runbook.
- Keep core trust artifacts stable regardless of integration surface: `.chronicle` verifier output and reproducible defensibility behavior remain canonical.

Release readiness decisions should explicitly say which optional surfaces are in-scope for this release.

---

## Try it

1. Run local release gates:
   - `make check`
2. Run optional broad lint sweep and inspect delta size:
   - `make lint-all`
   - `make format-check-all`
3. Run security threshold gate against existing reports:
   - `python3 scripts/supply_chain_gate.py --pip-report reports/pip-audit.json --npm-report reports/npm-audit.json --max-python-vulns 0 --max-high 0 --max-critical 0`
4. Read `docs/to_do.md` and list the currently open release blockers in one sentence each.
5. (When repo is public and token is available) run rollout verification:
   - `PYTHONPATH=. python3 scripts/check_branch_protection_rollout.py --repo owner/repo --branch main --output reports/branch_protection_rollout_report.json --stdout-json`
6. If MCP is enabled for your release target, run `chronicle-mcp --project-path /tmp/chronicle_release_mcp_smoke --transport stdio` and complete one tool-call lifecycle (create investigation → ingest evidence → propose claim → link support).

---

## Summary

- Release readiness is an objective contract across trust, backend, security, CI, and governance gates.
- `make check` and CI required jobs form the release-gated quality baseline.
- Security scans are threshold-enforced and fail-closed.
- Branch protection is validated by script and captured as a machine-readable release artifact.
- Standards and whitepaper progress are tracked as an operational review cycle with explicit deltas.
- Optional surfaces (including MCP) should be explicitly in/out of scope per release with matching smoke/runbook evidence.

---

← Previous: [Lesson 12: The .chronicle file format and data schema](12-chronicle-file-format-and-schema.md) | Index: [Lessons](README.md) | Next →: [Lesson 14: MCP agent integration](14-mcp-agent-integration.md)

Quiz: [quizzes/quiz-13-release-readiness-security-and-standards.md](quizzes/quiz-13-release-readiness-security-and-standards.md)
