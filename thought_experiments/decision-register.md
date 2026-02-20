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

## Adopt now status refresh (2026-02-20)

All initial `TE-01` through `TE-06` recommendations are now implemented (see `docs/to_do.md` completed section).

## Defer (historical)

| ID | Recommendation | Reason for defer |
|----|----------------|------------------|
| TE-D01 | Temporal uncertainty extension (range/confidence fields beyond `known_as_of`). | **Completed on 2026-02-19** (migration-safe implementation). |

## Defer (Round 2 rerun: 2026-02-20)

| ID | Recommendation | Reason for defer |
|----|----------------|------------------|
| TE-R2-01 | Policy sensitivity comparison report across multiple selected profiles for same investigation. | High-value additive artifact; current compatibility primitives exist but report composition is not yet first-class. |
| TE-R2-02 | Messy real-world stress corpus (partial metadata, supersession, redactions, conflicting/ambiguous chronology). | Valuable for operational trust calibration; should follow current sample-quality hardening rollout. |
| TE-R2-03 | Portfolio-level cross-investigation summaries (unresolved tensions, override concentration, readiness posture). | Needed for larger-team operations; best staged as reference analytics layer. |
| TE-R2-04 | One-shot readiness gate command/report composing compatibility, decision posture, and unresolved-risk thresholds. | Useful for CI/compliance gating; requires policy/default design work to avoid over-prescriptive behavior. |

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
