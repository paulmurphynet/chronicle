# Whitepaper internal review log

This document captures internal technical review outcomes for Chronicle's standards whitepaper revisions.

## Review round: v0.1

- Date: 2026-02-20
- Revision under review: `docs/whitepaper-draft.md` (v0.1)
- Evidence bundle: `docs/whitepaper-evidence-pack.md`
- Metadata source: `docs/whitepaper-publication-metadata.json`

### Accepted edits

1. Added reproducible evidence-pack builder and manifest (`scripts/whitepaper/build_evidence_pack.py`).
2. Added standards profile export examples (JSON-LD, ClaimReview, RO-Crate, C2PA, VC/Data Integrity) to the evidence pack.
3. Added verifier report generation for a pack-contained `.chronicle` sample.
4. Added machine-readable publication/citation metadata for revisioned whitepaper releases.
5. Added explicit documentation links from plan and draft to evidence-pack and citation metadata.

### Rejected edits

1. Rejected claiming default cryptographic verification in C2PA/VC compatibility exports.
   - Rationale: current path is metadata-only unless explicit verification is executed and recorded.
2. Rejected replacing Chronicle's canonical model with external standards schema.
   - Rationale: standards mappings are interoperability profiles; Chronicle event/read model remains canonical.

### Open follow-ups

1. Collect external reviewer feedback for v0.2 and map accepted/rejected deltas.
2. Add publication venue-specific formatting once target venue is selected.

## Review round: v0.2

- Date: 2026-02-20
- Revision under review: `docs/whitepaper-draft.md` (v0.2)
- Evidence bundle: `docs/whitepaper-evidence-pack.md`
- Metadata source: `docs/whitepaper-publication-metadata.json`

### Accepted edits

1. Added deterministic end-to-end reproducibility appendix with concrete command path and generated artifact set.
2. Added explicit guarantees/non-guarantees matrix tied to verifier and defensibility schema docs.
3. Updated citation metadata and publication records to `v0.2`.

### Rejected edits

1. Rejected broadening guarantee language beyond current verifier/runtime scope.
   - Rationale: guarantees must remain strictly aligned to implemented checks and docs.

### Open follow-ups

1. Run external review pass and collect accepted/rejected edits for v0.3 planning.
2. Add venue-specific formatting package once target publication venue is selected.
