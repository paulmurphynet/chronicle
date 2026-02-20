# CI Branch Protection Checklist

Use this checklist when enabling branch protection for `main`/`master`.

## Private repo support

You can enforce this checklist while the repository is still private.

As of **February 20, 2026**, GitHub docs state:

- Protected branches are available for private repositories on GitHub Pro, Team, and Enterprise plans.
- GitHub Actions can run on private repositories.
- GitHub Free private repositories may not expose branch-protection enforcement controls.

If branch protection settings are unavailable in your private repo UI, verify plan eligibility first.

## Required status checks

Mark these as required in GitHub branch protection:

1. `lint-and-test (3.11)`
2. `lint-and-test (3.12)`
3. `frontend-checks`
4. `postgres-event-store-smoke`

These map to jobs defined in `.github/workflows/ci.yml`.

## Branch protection settings

Recommended minimum settings:

1. Require a pull request before merging.
2. Require status checks to pass before merging.
3. Require branches to be up to date before merging.
4. Include administrators.
5. Restrict force pushes and deletions.

## Why these checks are required

- `lint-and-test` covers Python quality gates, docs checks, and workflow parity checks.
- `frontend-checks` keeps Reference UI route/contract parity and build health.
- `postgres-event-store-smoke` now includes doctor, smoke, backend parity, and timed onboarding gates, so Postgres convergence regressions block merges.

## Verification step after setup

Open a test PR and confirm all required checks are listed as blocking checks before merge.

Recommended validation sequence:

1. Push a non-trivial test PR.
2. Confirm all required checks complete successfully.
3. Confirm merge is blocked when any required check fails.
4. Confirm direct pushes to the protected branch are blocked (if configured).
