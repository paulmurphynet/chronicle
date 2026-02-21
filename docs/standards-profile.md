# Chronicle standards profile

Last updated: 2026-02-20

This document defines Chronicle's standards posture so integrations remain compatible with existing ecosystems while Chronicle's own model matures.

## Decision summary

Chronicle adopts a layered standards strategy:

1. Semantic interoperability baseline: JSON-LD 1.1 + PROV family (PROV-O / PROV-DM concepts)
2. Cryptographic provenance compatibility (media/content): C2PA
3. Cryptographic attestation compatibility (identity/claims): W3C VC Data Model 2.0 + VC Data Integrity 1.0 (DID Core optional by deployment)
4. Research/data-packaging interoperability: RO-Crate 1.2 profile
5. Fact-checking ecosystem compatibility: schema.org ClaimReview mapping

Chronicle remains the canonical internal model and storage format (`.chronicle`, event/read model, verifier). Standards mappings are interoperability profiles, not replacements for core data structures.

## Why this profile

- JSON-LD + PROV-O are the most stable base for linked-data provenance semantics.
- C2PA and VC/Data Integrity cover trust needs that semantic models alone do not cover (signatures, issuer assertions, verification).
- RO-Crate and ClaimReview reduce integration friction with research and fact-checking workflows.
- OpenLineage, in-toto, and SLSA are important adjacent ecosystems, but they solve different primary problems (data/software lineage and supply-chain assurance).

## Normative scope (what Chronicle commits to)

### Tier 1: required interoperability targets

- JSON-LD export profile for investigations, claims, evidence, links, tensions, and source relations.
- PROV-compatible representation of Chronicle provenance concepts:
  - Evidence as entities
  - Sources/actors as agents
  - Ingest/link/assert actions as activities or qualified relations
  - Claim evidence relationships modeled with explicit relation typing
- Versioned context policy for JSON-LD so clients can pin behavior.

### Tier 2: required compatibility adapters

- C2PA adapter path for recording and exporting C2PA assertion references now; verification integration path staged as optional capability.
- VC/Data Integrity adapter path for attestations over Chronicle artifacts/claims/checkpoints.
- ClaimReview export profile for fact-checking distribution compatibility.

### Tier 3: planned packaging and ecosystem profiles

- RO-Crate export profile for investigation package interchange.
- Clear mapping guidance for adjacent ecosystems (OpenLineage, in-toto, SLSA) as complementary, non-replacing layers.

## Chronicle-to-standards mapping (initial model)

| Chronicle concept | JSON-LD / PROV-oriented mapping |
|-------------------|---------------------------------|
| Investigation | `prov:Bundle` (plus Chronicle profile type) |
| Evidence item | `prov:Entity` |
| Evidence span | `prov:Entity` with linkage to evidence item (specialized segment) |
| Claim | `prov:Entity` with Chronicle claim typing |
| Support/challenge link | qualified derivation/influence pattern with explicit `chronicle:linkType` |
| Source | `prov:Agent` |
| Evidence-source link | attribution/provision relation to source agent |
| Tension | Chronicle profile relation (with PROV-compatible influence semantics where appropriate) |
| Event log entry | provenance activity record (Chronicle event envelope remains canonical) |

Chronicle-specific fields that have no direct PROV term stay namespaced under the Chronicle JSON-LD context.

## Non-goals and boundaries

- Chronicle does not claim that PROV semantics alone prove authenticity.
- Chronicle does not claim C2PA/VC verification unless verification has actually been executed and recorded.
- Chronicle does not replace data pipeline lineage systems (OpenLineage) or software supply-chain attestation systems (in-toto/SLSA).

## Implementation and governance

- Backlog and sequencing: [Implementation To-Do](to_do.md)
- Architecture decision: [ADR 0003](adr/0003-standards-interoperability-profile.md)
- JSON-LD export profile details: [Standards JSON-LD export](standards-jsonld-export.md)
- ClaimReview profile details: [ClaimReview export](claimreview-export.md)
- RO-Crate profile details: [RO-Crate export](ro-crate-export.md)
- C2PA compatibility export details: [C2PA compatibility export](c2pa-compatibility-export.md)
- VC/Data Integrity export details: [VC/Data Integrity export](vc-data-integrity-export.md)
- Adjacent standards boundaries: [Adjacent standards guidance](adjacent-standards-guidance.md)
- Publication process: [Whitepaper and standards submission plan](whitepaper-plan.md)
