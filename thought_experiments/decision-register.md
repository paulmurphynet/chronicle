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

## Round 2 status refresh (2026-02-20 rerun)

| ID | Recommendation | Status |
|----|----------------|------------------|
| TE-R2-04 | One-shot readiness gate command/report composing compatibility, decision posture, and unresolved-risk thresholds. | **Completed** (`scripts/review_readiness_gate.py` + reference workflow runner integration); profile-specific preset guidance remains optional enhancement. |
| TE-R2-01 | Policy sensitivity comparison report across multiple selected profiles for same investigation. | **Completed** (`get_policy_sensitivity_report`, API `/policy-sensitivity`, CLI `policy sensitivity`) with pairwise deltas and practical implication summaries. |
| TE-R2-03 | Portfolio-level cross-investigation summaries (unresolved tensions, override concentration, readiness posture). | **Completed** (`scripts/portfolio_risk_summary.py`) with deterministic ranking + aggregate concentration/readiness analytics. |
| TE-R2-02 | Messy real-world stress corpus (partial metadata, supersession, redactions, conflicting/ambiguous chronology). | **Completed** (`scripts/verticals/messy/generate_sample.py`) with sample-quality and reference-workflow integration. |

## Round 3 pre-public rerun status refresh (2026-02-20)

Panel source: `07-pre-publication-launch-readiness-panel-review.md`.

### Deferred Round 2 recommendations: current status

| ID | Previous status | Current status | Notes |
|----|-----------------|----------------|-------|
| EP-R2-1 | Defer | **Completed** | Policy sensitivity comparison shipped (`R2-01`). |
| EP-R2-2 | Defer | **Completed** | Messy/noisy corpus shipped (`R2-03`). |
| J-R2-2 | Defer | **Completed** | Portfolio-level analytics shipped (`R2-02`). |
| C-R2-1 | Defer | **Completed** | Readiness gate shipped (`R2-04`). |
| C-R2-2 | Defer | **Completed** | Cross-investigation exception analytics shipped (`R2-02`). |
| L-R2-2 | Defer | **Completed** | General readiness gate now covers required artifact posture checks (`R2-04`). |
| H-R2-1 | Defer | **Completed** | History-relevant messy archive corpus shipped (`R2-03`). |
| R-R2-1 | Defer | **Completed** | Pipeline readiness command/report shipped (`R2-04`). |
| R-R2-2 | Defer | **Completed** | Large/noisy stress sample capability shipped via messy corpus (`R2-03`). |
| J-R2-1 | Defer | **Still deferred** | Editorial deadline-priority packet view. |
| L-R2-1 | Defer | **Still deferred** | Legal-stage packet presets. |
| H-R2-2 | Defer | **Still deferred** | Chronology comparison artifact for review packets. |

### New Round 3 recommendations

| ID | Recommendation | Layer | Decision | To-do linkage |
|----|----------------|-------|----------|---------------|
| P-1 | Complete frontend lockfile + `npm ci` migration in CI/release workflows. | CI/release ops | Adopt | `docs/to_do.md` public launch blockers (`frontend/package-lock.json`, `npm ci`) |
| P-2 | Execute first public CI + branch-protection rollout verification and archive evidence report. | CI/governance evidence | Adopt | `docs/to_do.md` branch-protection/public CI blockers |
| P-3 | Keep Neo4j support level explicit as Beta until N-07..N-12 are complete and evidenced. | Support policy/docs | Adopt | `docs/support-policy.md`; `docs/to_do.md` N-07..N-12 |
| P-4 | Complete Neo4j N-07/N-08/N-09 (performance, parity, failure-mode testing). | Neo4j engineering | Defer | `docs/to_do.md` N-07..N-09 |
| P-5 | Complete Neo4j N-10/N-11/N-12 (ops runbook, query pack, compatibility policy details). | Neo4j docs/operations | Defer | `docs/to_do.md` N-10..N-12 |
| P-X1 | Block public launch until all Neo4j best-in-class items are complete. | Strategy | Reject | Rejected in Round 3 as over-constraining vs trust-critical launch gates |

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
