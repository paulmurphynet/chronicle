# Thought experiment 01: Epistemologists' conference review (detailed)

## Setup

A panel of four epistemology-focused reviewers studies Chronicle's design claims, implementation boundaries, and policy posture.

Panelists:

1. **Dr. Rowan Reed** (social epistemology: testimony and source dependence)
2. **Dr. Imani Vega** (formal epistemology: defeasibility and revision)
3. **Dr. June Kim** (virtue/applied epistemology: justification and accountability)
4. **Dr. Patrick O'Brien** (applied evaluation epistemology)

Materials reviewed:

- `docs/epistemology-scope.md`
- `critical_areas/README.md`
- `docs/verification-guarantees.md`
- `docs/policy-profiles/README.md`
- `docs/north-star.md`

---

## Dr. Rowan Reed (social epistemology)

**What I think is done well**

- Chronicle models sources, support/challenge links, and corroboration in a way that is legible to testimonial reasoning.
- Independence and reliability notes are correctly handled as recorded user assertions, not certified facts.
- The project documents non-guarantees clearly enough to reduce common misuse.

**What could improve and why**

- **Interpretation risk at score surface.** Users may over-read support counts without context about link generation quality.
- **Cross-profile source interpretation.** When work products move across domain profiles, teams need an explicit compatibility diff to interpret evidence standards correctly.

---

## Dr. Imani Vega (formal epistemology)

**What I think is done well**

- Chronicle keeps defensibility separate from truth claims.
- Tensions and event history support practical defeasibility without pretending to implement full formal belief revision.
- First-class contradiction handling is a major strength compared with systems that only tally support.

**What could improve and why**

- **Preflight for policy semantics.** Formal consistency across profiles should be visible before checkpoint/export, not discovered afterward.
- **Decision trace packaging.** The information exists, but users still need one consolidated ledger artifact for review and comparison.

---

## Dr. June Kim (virtue and accountability)

**What I think is done well**

- Human-in-the-loop events (confirm/override/dismiss) support accountable reasoning practices.
- Chronicle's model rewards explicit linkage and reasoning visibility rather than rhetorical certainty.
- The architecture boundary protects trust-critical behavior from surface churn.

**What could improve and why**

- **Accountability discoverability.** Human decisions are auditable but not yet assembled into one concise review object.
- **Workflow legibility.** Reviewers need clearer, faster answers to: who accepted what risk, under which policy, and why.

---

## Dr. Patrick O'Brien (applied evaluation epistemology)

**What I think is done well**

- Chronicle is unusually explicit about what verifier output means and does not mean.
- The system supports real-world process variation through policy profiles rather than hard-coded vertical forks.
- Current docs provide enough scope boundaries to remain credible with technical evaluators.

**What could improve and why**

- **Machine-readable policy compatibility.** This is important for practical deployment and CI-based controls.
- **Link assurance communication.** Defensibility outputs should explicitly include assurance context so dashboards cannot accidentally hide caveats.

---

## Synthesis (moderator)

**Shared praise**

- Chronicle's strongest epistemic choice is refusing to collapse defensibility into truth.
- Support/challenge/tension plus event history is a robust operational epistemology foundation.
- Policy profiles are the correct mechanism for domain specialization.

**Shared improvement themes**

1. Surface policy compatibility differences earlier in workflow.
2. Surface link assurance caveats directly in outputs.
3. Consolidate reviewer decision accountability into one ledger/report object.

---

## Follow-up discussion: scope discipline

The panel agrees Chronicle should become more expressive in review operations while preserving core boundaries.

- Rejected: adding truth probability scoring.
- Rejected: automatic acceptance of links based on support-count thresholds.
- Rejected: hiding unresolved contradictions in summary views.

---

## Agreed concrete change list

| ID | Change | Type | Rationale |
|---|---|---|---|
| EP-1 | Add policy compatibility preflight surfaces (human-readable and machine-readable). | API + UI/CLI/report | Prevents silent semantic drift across domain handoffs. |
| EP-2 | Add link assurance metadata and caveat text in defensibility outputs/exports. | Core output schema + docs + UI | Reduces false confidence from unqualified support counts. |
| EP-3 | Add unified reviewer decision ledger output across confirms/overrides/dismissals/tensions. | Core query/report + surfaces | Makes accountability easy to inspect and audit. |
| EP-4 | Add review packet composition that includes policy delta + decision ledger snapshot. | API/CLI/report | Converts fragmented review evidence into one inspectable artifact. |
| EP-X1 | Do not compute truth probability scores. | Rejected | Violates Chronicle's core boundary. |
| EP-X2 | Do not auto-accept support links by count threshold. | Rejected | Encourages over-trust and bypasses review accountability. |
| EP-X3 | Do not hide unresolved tensions in concise summaries. | Rejected | Conflicts with transparent epistemic risk reporting. |

---

## Recommendation summary

| ID | Recommendation | Decision |
|----|----------------|----------|
| EP-1 | Policy compatibility preflight surface | Adopt |
| EP-2 | Link assurance metadata in outputs | Adopt |
| EP-3 | Unified reviewer decision ledger | Adopt |
| EP-4 | Unified review packet composition | Adopt |
| EP-X1 | Truth probability scoring | Reject |
| EP-X2 | Auto-accept links by support count threshold | Reject |
| EP-X3 | Hide unresolved tensions in summaries | Reject |

---

## Round 2 rerun (2026-02-20): post-implementation reassessment

### What changed since Round 1

- Policy compatibility preflight is now available across session/API/CLI/reference surfaces.
- Link assurance fields and caveats are now included in defensibility/eval outputs.
- Reviewer decision ledger and unified review packet surfaces are implemented.
- Temporal uncertainty extension (`known_range_start`, `known_range_end`, `temporal_confidence`) is implemented.
- Multi-vertical sample/workflow parity and sample quality checks are materially improved.

### Panelist reassessment

**Dr. Rowan Reed**

- Chronicle now better protects against testimonial over-reading by exposing link-assurance posture directly in outputs.
- Remaining concern: users may still operationally over-trust "counts first, caveats second" if dashboards hide caveat text.

**Dr. Imani Vega**

- Policy preflight and decision-ledger outputs significantly improve defeasibility traceability in operational review.
- Remaining concern: no routine "same investigation under multiple policy views" summary artifact for quick comparative analysis.

**Dr. June Kim**

- Accountability discoverability improved substantially through unified decision ledger and review packet flows.
- Remaining concern: role-based review discipline exists in docs, but adoption consistency depends on workflow enforcement.

**Dr. Patrick O'Brien**

- Chronicle is now more coherent as an applied epistemic system: compatibility deltas, decision posture, and caveats are inspectable.
- Remaining concern: real-world robustness now hinges on stress-testing messy, incomplete, and conflicting artifact bundles.

### Round 1 recommendation status delta

| ID | Round 1 decision | Round 2 status | Notes |
|---|---|---|---|
| EP-1 | Adopt | Completed | Policy compatibility preflight shipped across major surfaces. |
| EP-2 | Adopt | Completed | Link assurance metadata/caveats added to output contracts and docs. |
| EP-3 | Adopt | Completed | Unified reviewer decision ledger shipped. |
| EP-4 | Adopt | Completed | Unified review packet generation shipped. |
| EP-X1 | Reject | Reaffirm reject | Boundary preserved: no truth-probability scoring. |
| EP-X2 | Reject | Reaffirm reject | Boundary preserved: no support-count auto-accept. |
| EP-X3 | Reject | Reaffirm reject | Boundary preserved: unresolved tensions remain visible. |

### New rerun recommendations

| ID | Recommendation | Decision | Why |
|---|---|---|---|
| EP-R2-1 | Add a "policy sensitivity comparison" report for same investigation across 2-3 selected profiles. | Defer | Valuable for epistemic legibility; can be layered on existing compatibility primitives. |
| EP-R2-2 | Add stress-test corpus with intentionally messy/ambiguous provenance to evaluate reviewer behavior and caveat visibility. | Defer | High value for practical trust calibration; should be staged after current workflow hardening. |
