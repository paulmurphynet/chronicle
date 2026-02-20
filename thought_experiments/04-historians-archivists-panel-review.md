# Thought experiment 04: Historians and archivists panel review (detailed)

## Setup

A history-focused panel evaluates Chronicle for evidence-heavy historical inquiry where chronology, provenance, and interpretation uncertainty matter.

Panelists:

1. **Dr. Lila Morant** (modern historian)
2. **Evan Price** (archivist)
3. **Dr. Sora Whitman** (oral history specialist)
4. **Nadia Cole** (digital humanities researcher)

Materials reviewed:

- `docs/epistemology-scope.md`
- `docs/defensibility-metrics-schema.md`
- `docs/reference-workflows.md`
- `docs/policy-profiles/README.md`
- `docs/reasoning-brief.md`

---

## Dr. Lila Morant (modern historian)

**What I think is done well**

- Chronicle's support/challenge/tension structure mirrors contested historical interpretation better than linear note systems.
- Explicit claim/evidence links make historiographic arguments auditable.
- The defensibility-not-truth boundary is appropriate for historical method.

**What could improve and why**

- **Temporal uncertainty representation.** Historical claims often rely on approximate windows (circa, before/after bounds), not precise dates. Current `known_as_of` support is useful but narrow.
- **Interpretive context surfacing.** Reasoning outputs should better show why a date or chronology judgment is uncertain.

---

## Evan Price (archivist)

**What I think is done well**

- Provenance-aware structures and event history fit archival expectations.
- Redaction and chain-of-custody concepts are useful for restricted archival material.
- Portable `.chronicle` artifacts support preservation and downstream verification workflows.

**What could improve and why**

- **Profile coverage gap.** There is no dedicated research/history policy profile example, which slows onboarding for historians.
- **Workflow guidance gap.** Reference workflows currently emphasize journalism/compliance patterns more than historical research practice.

---

## Dr. Sora Whitman (oral history specialist)

**What I think is done well**

- Chronicle can model conflicting testimony without forcing premature convergence.
- Human decision events provide useful context when interpretation choices are made.
- Source notes can capture caveats when independence or reliability is uncertain.

**What could improve and why**

- **Uncertainty communication.** Oral-history claims often require narrative uncertainty markers that should appear in review summaries.
- **Authority caution.** Any attempt to auto-rank sources by institution would be methodologically weak and potentially biased.

---

## Nadia Cole (digital humanities researcher)

**What I think is done well**

- API and export surfaces support reproducible humanities workflows.
- Chronicle structures can bridge human interpretation and computational analysis.
- Policy profiles are a good strategy for adapting standards across domains without forking core.

**What could improve and why**

- **Research workflow parity.** Add deterministic example workflows and datasets for research/history similar to other verticals.
- **Machine-readable temporal caveats.** Where uncertainty exists, downstream tools should be able to detect that state programmatically.

---

## Synthesis (moderator)

**Shared praise**

- Chronicle is a good fit for contested-claim historical work because it preserves structure, disagreement, and auditability.
- The non-truth framing is a strength, not a weakness, for this domain.

**Shared improvement themes**

1. Add research/history policy and workflow examples now.
2. Expand temporal uncertainty modeling carefully, with schema discipline.
3. Keep uncertainty explicit; do not hide it behind authority heuristics.

---

## Follow-up discussion: sequencing and risk

The panel recommends a two-step sequence:

1. **Adopt now**: add history profile and workflow parity.
2. **Defer with design brief**: temporal uncertainty schema expansion, to avoid destabilizing current contracts.

Rejected direction: institution-based automatic authority scoring.

---

## Agreed concrete change list

| ID | Change | Type | Rationale |
|---|---|---|---|
| H-1 | Add `research_history` policy profile example with clear rationale and constraints. | Policy profile/docs | Reduces onboarding friction for historical/research users. |
| H-2 | Add reproducible research/history reference workflow and include it in workflow runner/report. | Scripts/docs/tests | Establishes parity with other supported verticals. |
| H-3 | Design temporal uncertainty extension (ranges/qualifiers/notes) for reasoning outputs. | Core schema/reporting | Better reflects historical method where dates are approximate. |
| H-X1 | Do not auto-rank source authority by institution. | Rejected | High bias risk and inconsistent with Chronicle scope. |

---

## Recommendation summary

| ID | Recommendation | Decision |
|----|----------------|----------|
| H-1 | Research/history policy profile example | Adopt |
| H-2 | Research/history workflow parity | Adopt |
| H-3 | Temporal uncertainty reporting expansion | Defer |
| H-X1 | Auto-rank source authority by institution | Reject |

---

## Round 2 rerun (2026-02-20): history/archives reassessment after implementation

### What changed since Round 1

- History/research policy profile example is now in place.
- Deterministic history workflow parity has been added to reference workflow tooling.
- Temporal uncertainty extension is now implemented with `known_range_start`, `known_range_end`, and `temporal_confidence`.
- Sample datasets now include richer provenance, challenge links, and uncertainty-supporting rationale text.

### Panelist reassessment

**Dr. Lila Morant**

- Temporal range/confidence support is a meaningful upgrade for historical claims with approximate chronology.
- Remaining concern: uncertainty is captured, but cross-claim chronology comparison is still mostly manual.

**Evan Price**

- Research profile and workflow parity materially improve onboarding for archival users.
- Remaining concern: large archival collections still need "messy corpus" examples with redactions, supersession, and partial metadata.

**Dr. Sora Whitman**

- Competing testimony modeling remains strong and now has better uncertainty representation.
- Remaining concern: oral-history caveat language quality varies by operator; stronger authoring guidance would help consistency.

**Nadia Cole**

- Machine-readable uncertainty fields improve downstream computational analysis.
- Remaining concern: profile-sensitivity studies across the same historical dataset are still not a first-class workflow artifact.

### Round 1 recommendation status delta

| ID | Round 1 decision | Round 2 status | Notes |
|---|---|---|---|
| H-1 | Adopt | Completed | Research/history policy profile added. |
| H-2 | Adopt | Completed | Workflow parity and runner coverage added. |
| H-3 | Defer | Completed | Temporal uncertainty extension shipped migration-safe. |
| H-X1 | Reject | Reaffirm reject | No institution-based authority auto-ranking. |

### New rerun recommendations

| ID | Recommendation | Decision | Why |
|---|---|---|---|
| H-R2-1 | Add history-focused "messy archive" sample set (partial dates, redactions, supersessions, conflicting editions). | Defer | High realism value for scholarly practice; should be staged as reference data work. |
| H-R2-2 | Add chronology comparison artifact (claim timelines + uncertainty windows) for review packets. | Defer | Strong fit for historians; additive reference/report surface. |
