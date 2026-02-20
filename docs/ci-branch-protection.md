# CI Branch Protection Checklist

Use this checklist when enabling branch protection for `main`/`master`.

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
- `postgres-event-store-smoke` ensures Postgres onboarding/event-store path is not regressed.

## Verification step after setup

Open a test PR and confirm all required checks are listed as blocking checks before merge.
