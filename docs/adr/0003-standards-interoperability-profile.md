# ADR 0003: Layered standards interoperability profile

- Status: accepted
- Date: 2026-02-20
- Related: `docs/standards-profile.md`, `docs/whitepaper-plan.md`, `docs/to_do.md`

## Context

Chronicle needs explicit interoperability posture so adopters can integrate with established provenance, attestation, and fact-checking ecosystems without forcing Chronicle's internal model to mirror any single external standard.

## Decision

Adopt a layered profile:

1. JSON-LD + PROV family as the semantic baseline.
2. C2PA for media/content cryptographic provenance compatibility.
3. VC Data Model 2.0 + VC Data Integrity 1.0 for signed attestations (with DID Core optional by deployment).
4. RO-Crate profile for research/data package interoperability.
5. schema.org ClaimReview export profile for fact-checking ecosystem compatibility.

Chronicle's canonical representation remains `.chronicle` + event/read model. Standards outputs are compatibility profiles and adapters.

## Consequences

- Implementation work is staged as export/import/profile tasks rather than full internal model replacement.
- Chronicle can interoperate with multiple ecosystems while preserving trust-critical core contracts.
- Conformance language must distinguish semantic compatibility from cryptographic verification.

## Alternatives considered

- Adopt only JSON-LD/PROV-O and defer all other standards.
  - Rejected due to missing cryptographic and publication interoperability needs.
- Replace Chronicle core schema with external ontology-first storage.
  - Rejected due to high migration risk and loss of current contract stability.
