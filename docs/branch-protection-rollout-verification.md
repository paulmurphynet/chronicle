# Branch Protection Rollout Verification

Use this procedure to verify the remaining release blocker:

- Branch protection is configured on the protected branch.
- Required CI checks are enforced and have recent green evidence for both `push` and `pull_request`.

## Script

Run:

```bash
export GITHUB_REPOSITORY=owner/repo
export GITHUB_TOKEN=... # token with repo admin/read permissions
PYTHONPATH=. python3 scripts/check_branch_protection_rollout.py \
  --repo "$GITHUB_REPOSITORY" \
  --branch main \
  --output reports/branch_protection_rollout_report.json \
  --stdout-json
```

Exit codes:

- `0`: passed
- `1`: failed (configuration or CI evidence mismatch)
- `2`: blocked (branch-protection API unavailable due permission/plan constraints)

## What the script validates

1. Branch protection endpoint exists for the branch.
2. Required status checks include:
   - `lint-and-test (3.11)`
   - `lint-and-test (3.12)`
   - `frontend-checks`
   - `postgres-event-store-smoke`
3. Protection settings:
   - PR required before merge
   - status checks required
   - branch up-to-date required
   - administrators included
   - force pushes disabled
   - deletions disabled
4. Recent successful workflow runs for both events:
   - `push`
   - `pull_request`
5. At least one successful run per event where all required jobs concluded `success`.

## Evidence artifact

Store and reference:

- `reports/branch_protection_rollout_report.json`

This file is the release-evidence artifact for the CI/branch-protection gate in `docs/production-readiness-checklist.md`.

## If status is `blocked`

`blocked` means the API could not provide protection details (commonly permission or plan limitation on private repos). In that case:

1. Upgrade to a plan that supports private-repo branch protection (Pro/Team/Enterprise) or switch visibility to public.
2. Re-run the script and attach the new report.
3. Keep the release blocker open until script status is `passed`.
