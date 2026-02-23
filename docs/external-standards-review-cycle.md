# External standards review cycle tracker

Last updated: 2026-02-23

This tracker records execution state for whitepaper external review (`W-07`) and preserves the accepted/rejected feedback trail needed for revisioned publication.

## Review scope

Target communities:

1. W3C-linked JSON-LD/PROV/VC communities
2. C2PA ecosystem communities
3. Applied research/evaluation communities

Primary package reference: [Standards submission package](standards-submission-package.md)

## Current cycle status (v0.3)

Cycle revision: `v0.3`  
Package snapshot: `reports/standards_submissions/v0.3/`  
Outreach status: `prepared_pending_public_repo`

Prepared artifacts:

1. Submission bundle manifest: `reports/standards_submissions/v0.3/submission_bundle_manifest.json`
2. Venue bundle archives:
   - `reports/standards_submissions/v0.3/bundles/w3c_linked_data_v0.3.zip`
   - `reports/standards_submissions/v0.3/bundles/c2pa_ecosystem_v0.3.zip`
   - `reports/standards_submissions/v0.3/bundles/applied_research_v0.3.zip`
3. Evidence pack snapshot and manifest under `reports/standards_submissions/v0.3/evidence_pack/`
4. Dispatch tracker template: `docs/external-review-dispatch-log.template.json`

## Outreach execution checklist

Before sending:

1. Confirm public repo links resolve for `docs/whitepaper-draft.md`.
2. Confirm CI badge/check links are visible to external reviewers.
3. Confirm the bundle revision matches `docs/whitepaper-publication-metadata.json`.

When sending:

1. Send venue-specific bundle and outreach note.
2. Record each send event in the log below.
3. Set feedback window and target next revision.

When receiving feedback:

1. Add each item using the response schema.
2. Classify: `accepted`, `rejected`, or `needs_followup`.
3. Link resulting change or rationale in review logs.

## Machine-readable tracker

Maintain:

- `reports/standards_submissions/v0.3/external_review_dispatch_log.json`

Bootstrap from template if missing:

```bash
cp docs/external-review-dispatch-log.template.json \
  reports/standards_submissions/v0.3/external_review_dispatch_log.json
```

Per-venue `status` values:

- `prepared`
- `sent`
- `acknowledged`
- `feedback_received`
- `closed`

## Send log

| sent_at | venue | contact | bundle | status | note |
|---|---|---|---|---|---|
| pending | w3c_linked_data | pending-public | `w3c_linked_data_v0.3.zip` | prepared | Waiting for public repo and outbound contact list |
| pending | c2pa_ecosystem | pending-public | `c2pa_ecosystem_v0.3.zip` | prepared | Waiting for public repo and outbound contact list |
| pending | applied_research | pending-public | `applied_research_v0.3.zip` | prepared | Waiting for public repo and outbound contact list |

## Feedback response schema

Capture each response item as:

- `source_community`
- `source_link_or_contact`
- `revision_received_on`
- `feedback_summary`
- `classification` (`accepted`, `rejected`, `needs_followup`)
- `resolution_note`
- `target_revision`
