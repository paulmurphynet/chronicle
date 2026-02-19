# Thought experiment decision register

Cross-panel decision log for this batch. Use this as the source of truth for what was accepted, deferred, or rejected and why.

## Adopt now

| ID | Recommendation | Layer | Why accepted | To-do link |
|----|----------------|-------|--------------|------------|
| TE-01 | Add policy compatibility preflight surfaces (API + CLI + UI) for built-under vs viewing-under profiles. | API + reference surfaces | Directly supports north-star cross-domain workflows and reduces handoff errors. | `docs/to_do.md` |
| TE-02 | Add `link_assurance_level` (and caveats) to defensibility outputs and exports. | Core output + docs + surfaces | Prevents over-trust from treating auto-linked evidence as equivalent to reviewed links. | `docs/to_do.md` |
| TE-03 | Expand reference workflows and policy examples to include research/history and stronger legal/compliance parity. | Policy + scripts/docs/tests | Improves adoption across intended target audiences without touching core semantics. | `docs/to_do.md` |
| TE-04 | Add unified reviewer decision ledger/report (confirmations, overrides, dismissals, unresolved tensions). | Core query/report + surfaces | Makes accountability practical for legal/compliance/editorial review. | `docs/to_do.md` |
| TE-05 | Add unified review packet generator (reasoning brief + chain-of-custody + policy compatibility + policy rationale summary + decision summary). | Reference reporting | Converts scattered artifacts into one review-ready bundle suitable for editor/legal/compliance review. | `docs/to_do.md` |
| TE-06 | Add role-based review checklist templates per policy profile. | Docs + reference UI guidance | Improves consistency for multi-role review teams with minimal risk. | `docs/to_do.md` |

## Defer

| ID | Recommendation | Reason for defer |
|----|----------------|------------------|
| TE-D01 | Temporal uncertainty extension (range/confidence fields beyond `known_as_of`). | Valuable for historical use cases, but needs careful schema design and migration plan; schedule after current adopted batch. |

## Reject

| ID | Recommendation | Reason rejected |
|----|----------------|-----------------|
| TE-X01 | Add truth/factuality probability output per claim. | Violates Chronicle core identity (defensibility is not truth). |
| TE-X02 | Global automated source credibility ranking. | High bias risk and overclaim; Chronicle records source context rather than certifying authority. |
| TE-X03 | Hide unresolved tensions in executive views. | Weakens auditability and can mislead reviewers. |
| TE-X04 | Make verifier assert domain conclusions (legal admissibility/editorial correctness). | Verifier is structural/integrity-only by design; domain conclusions belong to policy/human review. |
| TE-X05 | Replace scorecard with one aggregate trust number. | Loses interpretability and masks failure modes. |

## Notes on feature segregation

- Keep trust-critical semantics in Core.
- Push domain variation into policy profiles.
- Keep workflow convenience in API/CLI/UI layers.
- If a feature changes verifier guarantees, treat as release-critical and require explicit documentation updates.
