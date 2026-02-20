# Role-Based Review Checklists

Role-specific review templates for Chronicle investigations.

Use these with:

- `chronicle review-packet <investigation_uid> --path <project>`
- `chronicle reviewer-decision-ledger <investigation_uid> --path <project>`
- `chronicle policy compat --investigation <investigation_uid> --path <project> --json`

Goal: make decisions explicit and consistent across policy profiles and review teams.

## How to use this page

1. Pick the checklist that matches your active or viewing policy profile.
2. Run the review packet first, then walk the checklist in order.
3. Record outcomes as Chronicle decisions (confirm, override, dismiss, tension updates).
4. For every failed check, either remediate or record rationale for defer/exception.

## Profile-to-checklist mapping

| Policy profile | Primary checklist |
|---|---|
| `policy_investigative_journalism` | Journalism / Editorial review |
| `policy_legal` | Legal review |
| `policy_compliance` | Compliance / Audit review |
| `policy_history_research` | History / Research review |

## Journalism / Editorial Review

Use when publication risk is the main decision driver.

1. Confirm the review packet contains all publication-bound claims.
2. Verify policy compatibility deltas are empty or explicitly accepted.
3. Check unresolved tensions count:
   - `0` for publication-ready runs, or
   - non-zero only with documented editorial rationale.
4. For every high-impact claim, confirm at least two independent sources or document why not.
5. Validate that support/challenge links with `tool_generated` assurance are human-reviewed before release.
6. Confirm suggestion dismissals have rationale (no silent dismissals).
7. Confirm tier progression is justified (`spark -> forge -> vault`) in decision ledger entries.
8. Export submission package only after unresolved publication blockers are addressed.

## Legal Review

Use for briefs, discovery, filings, and dispute-support workflows.

1. Verify policy profile and version are correct for legal review.
2. Confirm chain-of-custody report exists and `report_exists=true` in review packet metadata.
3. For each claim relied on in legal argument:
   - verify source/evidence traceability,
   - verify no unresolved contradiction affecting the claim.
4. Confirm every override/confirmation has a clear legal rationale in the decision ledger.
5. Review tension statuses and ensure unresolved items are either remediated or flagged as legal exceptions.
6. Confirm any AI-only or weak-evidence posture is documented and not treated as SEF without support.
7. Ensure checkpoint/export decisions include actor identity and timestamped accountability.

## Compliance / Audit Review

Use for control validation, audit readiness, and internal assurance.

1. Confirm policy compatibility check was run for the viewing profile.
2. Validate reviewer decision summary counts are consistent with expected process activity.
3. Confirm exception-like outcomes (deferred/intractable/escalated tensions) include rationale.
4. Verify evidence inventory completeness in the audit export bundle.
5. Check chain-of-custody metadata presence for scopes requiring stronger provenance.
6. Confirm defensibility dimensions are reviewed claim-by-claim, not collapsed into one score.
7. Record final audit disposition:
   - pass,
   - pass with exceptions,
   - fail/remediate.

## History / Research Review

Use for archival, historiography, and evidence-uncertainty-heavy workflows.

1. Confirm claim wording distinguishes evidence-backed assertion from interpretation.
2. Validate provenance context is recorded for archival sources (origin, date, notes).
3. Check for temporal ambiguity and competing interpretations in tensions.
4. Ensure unresolved tensions are not hidden; they should remain visible in packet outputs.
5. Confirm policy rationale aligns with research standards (citation quality, source independence expectations).
6. For claims with limited evidence, require explicit caveat language in reviewer decisions.
7. Capture accepted uncertainty in confirmation/override rationale instead of forcing false certainty.

## Review outcomes template

Record one of:

- `approved`: no blockers remain.
- `approved_with_exceptions`: accepted risk with rationale.
- `remediation_required`: unresolved blockers must be fixed.
- `deferred`: out of current scope, reviewed and documented.

For each non-`approved` outcome, include:

1. blocking items,
2. assigned owner,
3. target date,
4. re-review trigger.
