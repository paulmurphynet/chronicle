# Rejected feature decisions

This log captures intentionally rejected feature directions, with rationale and tradeoffs.

## RFD-001: Treat defensibility as truth

- Status: Rejected
- Decision date: 2026-02-20
- Proposal: Expose defensibility score as a truth/confidence claim.
- Rejection rationale:
  1. Defensibility is structural and policy-relative, not a truth oracle.
  2. Would create overclaim risk in audit/public workflows.
- Tradeoff:
  - Pro: simpler public messaging.
  - Con: incorrect safety posture and misleading guarantees.
- Preferred path:
  - Keep explicit non-goal language in docs and exports.

## RFD-002: Default cryptographic verification in compatibility exports

- Status: Rejected
- Decision date: 2026-02-20
- Proposal: Mark C2PA/VC export entries as verified by default.
- Rejection rationale:
  1. Current compatibility paths are metadata-only unless verification is explicitly executed.
  2. Default verified semantics would be a false claim.
- Tradeoff:
  - Pro: cleaner integration story for some consumers.
  - Con: major trust and standards conformance risk.
- Preferred path:
  - Use explicit modes (`disabled`, `metadata_only`) and require recorded verification evidence.

## RFD-003: Replace Chronicle canonical model with standards-native storage

- Status: Rejected
- Decision date: 2026-02-20
- Proposal: Store core investigation state directly in external standards schemas.
- Rejection rationale:
  1. Would destabilize core trust artifacts (`.chronicle`, verifier, replay semantics).
  2. Would blur boundary between canonical model and interoperability adapters.
- Tradeoff:
  - Pro: fewer mapping layers.
  - Con: higher migration risk and weaker contract stability.
- Preferred path:
  - Keep Chronicle model canonical; maintain standards profiles as explicit adapters.
