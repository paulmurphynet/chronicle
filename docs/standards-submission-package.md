# Standards submission package and outreach notes

This guide defines the package and outreach artifacts used when sharing Chronicle's standards profile with external communities.

## Package contents

Prepare a submission folder with:

1. `whitepaper-draft.md` (current revision)
2. `whitepaper-publication-metadata.json`
3. `whitepaper-citation.md`
4. `whitepaper-evidence-pack.md`
5. `evidence_pack_manifest.json` and referenced artifacts from a generated pack
6. `standards-profile.md`
7. `adjacent-standards-guidance.md`
8. `adr/0003-standards-interoperability-profile.md`
9. `external-standards-review-cycle.md`
10. `to_do.md` excerpt for standards/whitepaper status

## Build commands

From repo root:

```bash
PYTHONPATH=. python3 scripts/whitepaper/build_evidence_pack.py
```

Build venue-specific submission bundles for a whitepaper revision:

```bash
PYTHONPATH=. python3 scripts/whitepaper/build_submission_bundles.py --revision v0.3
```

Optional narrow build:

```bash
PYTHONPATH=. python3 scripts/whitepaper/build_evidence_pack.py \
  --components standards verifier \
  --output-dir whitepaper_evidence_runs/submission-pack
```

## Outreach targets and framing

### W3C-linked JSON-LD/PROV/VC communities

- Focus: mapping semantics and explicit trust boundaries.
- Include: standards profile, JSON-LD/PROV export examples, VC compatibility export examples.
- Ask for feedback on profile clarity and compatibility language.

### C2PA ecosystem discussions

- Focus: compatibility path for C2PA references without overclaiming verification.
- Include: C2PA adapter and export examples, caveats in trust model.
- Ask for feedback on staged verification integration expectations.

### Applied research / evaluation communities

- Focus: reproducibility, defensibility metrics, and verifier-backed artifacts.
- Include: evidence pack manifest, benchmark outputs, trust report, citation metadata.
- Ask for feedback on experimental reporting and reproducibility expectations.

## Outreach note template

Subject: Chronicle standards interoperability profile review request (v0.3)

1. What we are sharing:
   - Whitepaper draft revision and citation metadata
   - Reproducible evidence pack + manifest
   - Standards profile and adapter/export examples
2. What feedback we need:
   - Mapping correctness and terminology
   - Boundary clarity (semantic vs cryptographic guarantees)
   - Practical interoperability concerns for your ecosystem
3. Timeline:
   - Requested feedback window
   - Planned revision target (e.g. v0.4)

## Issue-tracking fields for responses

Record each external feedback item with:

- `source_community`
- `source_link_or_contact`
- `revision_received_on`
- `feedback_summary`
- `classification` (`accepted`, `rejected`, `needs_followup`)
- `resolution_note`
- `target_revision`

Operational tracker:

- [External standards review cycle tracker](external-standards-review-cycle.md)
