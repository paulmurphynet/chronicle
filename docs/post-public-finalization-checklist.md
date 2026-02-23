# Post-Public Finalization Checklist

Use this checklist immediately after the repository is public and CI is enabled.

## 0. Public visibility and Actions confirmed

1. Confirm repository visibility is `Public`.
2. Confirm GitHub Actions are enabled for this repository.
3. Confirm `.github/workflows/ci.yml` triggers on both `push` and `pull_request`.

Reference: `docs/v0.9-public-launch.md`

## 1. CI required checks green on push/PR

1. Open a no-op PR (or docs-only PR) against `main`.
2. Verify required workflows/jobs pass:
   - `.github/workflows/ci.yml`
   - `.github/workflows/release.yml` (manual gate)
   - `.github/workflows/supply-chain.yml` (manual gate)
3. Confirm branch protection enforces required status checks.

## 2. Branch protection rollout verification report

Run:

```bash
PYTHONPATH=. ./.venv/bin/python scripts/check_branch_protection_rollout.py \
  --repo "$GITHUB_REPOSITORY" \
  --branch "${CHRONICLE_PROTECTED_BRANCH:-main}" \
  --output reports/branch_protection_rollout_report.json \
  --stdout-json
```

Done condition:

- `reports/branch_protection_rollout_report.json` has `status = "passed"`.

## 3. CI evidence for live Neo4j integration gate

Run:

```bash
PYTHONPATH=. ./.venv/bin/python scripts/check_neo4j_ci_rollout.py \
  --repo "$GITHUB_REPOSITORY" \
  --branch "${CHRONICLE_PROTECTED_BRANCH:-main}" \
  --output reports/neo4j_live_ci_report.json \
  --stdout-json
```

Done condition:

- `reports/neo4j_live_ci_report.json` has `status = "passed"`.

## 4. External standards review cycle dispatch (W-07)

Prepared bundles are already in:

- `reports/standards_submissions/v0.3/`

Actions:

1. Dispatch to target reviewers/venues listed in:
   - `docs/external-standards-review-cycle.md`
   - `docs/standards-submission-package.md`
2. Record each submission and response in the tracker.
3. Log accepted/rejected deltas and follow-up actions.

Machine-readable log:

- Bootstrap if missing:
  - `cp docs/external-review-dispatch-log.template.json reports/standards_submissions/v0.3/external_review_dispatch_log.json`
- Update `reports/standards_submissions/v0.3/external_review_dispatch_log.json`
  with each send/response event.

## 5. Close remaining TODO checkboxes

After items 1-4 are complete, update:

- `docs/to_do.md` remaining unchecked items.

Optional one-shot aggregate gate:

```bash
PYTHONPATH=. ./.venv/bin/python scripts/check_post_public_finalization.py \
  --output reports/post_public_finalization_report.json \
  --stdout-json
```
