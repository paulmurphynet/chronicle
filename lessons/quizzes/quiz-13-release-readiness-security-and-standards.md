# Quiz 13: Release readiness, security gates, and standards operations

Lesson: [13-release-readiness-security-and-standards.md](../13-release-readiness-security-and-standards.md)

Answer these after reading the lesson and opening the linked workflow/docs files. Try not to peek at the answer key until you've written your answers.

---

## Questions

1. Which local command is Chronicle’s release-gated quality bundle, and which two commands provide broader optional hygiene checks?

2. What are the four required CI job names used for branch-protection enforcement?

3. Which two scripts enforce vulnerability thresholds for dependency and container scans?

4. Why does `npm audit` depend on `frontend/package-lock.json`, and what install mode should CI use once the lockfile is committed?

5. What machine-readable artifact is used as evidence for branch-protection rollout verification?

6. In branch-protection rollout verification, what does `status=blocked` usually indicate?

7. Name two docs that define whitepaper/standards publication operations rather than product implementation details.

8. Where should unresolved launch blockers be tracked so they remain visible and auditable?

9. If local checks pass but CI fails, which result is source of truth for merge/release decisions?

10. Why does Chronicle separate release-gated core lint scope from optional broader lint scope?

---

## Answer key

1. `make check` is the release-gated bundle. Optional broader hygiene checks are `make lint-all` and `make format-check-all`.

2. `lint-and-test (3.11)`, `lint-and-test (3.12)`, `frontend-checks`, `postgres-event-store-smoke`.

3. `scripts/supply_chain_gate.py` (dependency scans) and `scripts/container_security_gate.py` (Trivy/container scans).

4. `npm audit` evaluates the resolved dependency tree from lockfile context; without lockfile, deterministic audit/install flow is incomplete. Once lockfile is committed, use `npm ci` in CI/release for deterministic installs.

5. `reports/branch_protection_rollout_report.json`.

6. Usually that the API could not return branch-protection details due permission/plan/visibility constraints (for example, repo settings not accessible yet).

7. Any two of:
   - `docs/whitepaper-plan.md`
   - `docs/standards-submission-package.md`
   - `docs/external-standards-review-cycle.md`

8. `docs/to_do.md` (single source of truth for pending release work).

9. CI is source of truth.

10. To keep release gates stable and trust-surface-focused while still allowing staged cleanup of non-core surfaces (`scripts/`, `tests/`) without destabilizing near-term release readiness.

---

← Previous: [quiz-12-chronicle-file-format-and-schema](quiz-12-chronicle-file-format-and-schema.md) | Index: [Quizzes](README.md) | End of quizzes
