# Adjacent standards guidance (S-08)

This document defines Chronicle boundaries for adjacent standards that are often evaluated alongside provenance/attestation protocols.

## Position summary

Chronicle is a claim-evidence defensibility system with event-sourced auditability. It does not replace:

- data-pipeline lineage systems
- software supply-chain attestation systems

Chronicle can integrate with those systems by recording references and carrying cross-links in exports.

## OpenLineage

Use OpenLineage for pipeline/job/dataset lineage across orchestration and data platforms.

Chronicle role:

- Record resulting evidence and claims from pipeline outputs.
- Store external lineage identifiers in evidence metadata (for example run/job/dataset IDs).
- Optionally include lineage references in standards exports as compatibility metadata.

Boundary:

- Chronicle does not provide native pipeline-execution lineage semantics equivalent to OpenLineage.

## in-toto

Use in-toto for software artifact provenance and supply-chain step attestations.

Chronicle role:

- Record references to in-toto attestations for evidence or generated artifacts.
- Preserve reviewer decisions and claim defensibility trails connected to those artifacts.

Boundary:

- Chronicle does not verify supply-chain policy compliance by itself.

## SLSA

Use SLSA to set and verify software supply-chain integrity levels.

Chronicle role:

- Record SLSA-related references and review context as part of investigation evidence and checkpoint artifacts.
- Export traceable links between Chronicle claims and external supply-chain attestations.

Boundary:

- Chronicle does not issue SLSA levels and is not a replacement for SLSA verification tooling.

## Integration pattern

1. Keep external systems authoritative for their native guarantees.
2. Ingest stable identifiers and references into Chronicle metadata.
3. Use Chronicle to reason about evidence quality, challenge/support structure, tensions, and review decisions.
4. Publish combined artifacts where Chronicle defensibility and external attestations remain explicitly distinct.
