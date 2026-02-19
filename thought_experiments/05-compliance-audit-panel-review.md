# Thought experiment 05: Compliance and audit panel review (detailed)

## Setup

A governance panel evaluates Chronicle for internal controls, audit evidence, and exception handling workflows.

Panelists:

1. **Priya Nanda** (internal audit director)
2. **Owen Carr** (compliance manager)
3. **Talia Grant** (risk analyst)
4. **Ben Ortiz** (controls automation engineer)

Materials reviewed:

- `docs/policy-profiles/compliance.json`
- `docs/reference-workflows.md`
- `docs/human-in-the-loop-and-attestation.md`
- `docs/trust-metrics.md`
- `docs/verification-guarantees.md`

---

## Priya Nanda (internal audit director)

**What I think is done well**

- Chronicle's event history and explicit non-guarantees support audit defensibility.
- Policy-driven checkpoint rules are aligned with control frameworks.
- Human override with rationale is a practical mechanism for controlled exceptions.

**What could improve and why**

- **Exception visibility.** Auditors need one place that summarizes overrides, dismissals, unresolved tensions, and rationale quality.
- **Packet consistency.** Review artifacts should be generated consistently for each audit cycle, not assembled ad hoc.

---

## Owen Carr (compliance manager)

**What I think is done well**

- Policy profiles let teams adapt requirements by domain without changing trust-critical internals.
- Chronicle captures enough structure to support repeatable review.
- Documentation is clear about what verification does not guarantee.

**What could improve and why**

- **Cross-policy preflight.** Compliance reviews often apply stricter criteria than earlier draft workflows. We need compatibility deltas surfaced before sign-off.
- **Checklist consistency.** Teams need profile-linked review checklists to reduce reviewer variance.

---

## Talia Grant (risk analyst)

**What I think is done well**

- Tensions and weakest-link concepts support risk-oriented review.
- Benchmark/trust tooling gives a foundation for trend monitoring.
- Chronicle's structure supports "show me why this passed" questions.

**What could improve and why**

- **Risk posture readability.** Decision outputs should make unresolved contradictions and exception concentration obvious.
- **No silent closure.** Auto-closing tensions based on time would hide risk rather than manage it.

---

## Ben Ortiz (controls automation engineer)

**What I think is done well**

- API-first plus deterministic scripts are suitable for compliance automation.
- Existing workflow runner is a good base for integration gates.
- Separation between core semantics and surface-level workflow logic supports maintainability.

**What could improve and why**

- **Machine-readable decision and compatibility outputs.** Needed for automated gates in CI and control pipelines.
- **Vertical parity.** Compliance onboarding is stronger when legal/history/compliance examples are all equally reproducible.

---

## Synthesis (moderator)

**Shared praise**

- Chronicle has strong raw ingredients for governance workflows: policy rules, event history, and explicit decision recording.

**Shared improvement themes**

1. Consolidate decisions/exceptions into one audit-ready artifact.
2. Surface policy compatibility deltas before critical checkpoints.
3. Expand reproducible workflows across intended verticals.
4. Never hide unresolved tensions by automation shortcuts.

---

## Follow-up discussion: what to reject decisively

Rejected recommendation: automatically close unresolved tensions after a timeout.

Reason: this creates procedural cleanliness without epistemic resolution and undermines audit integrity.

---

## Agreed concrete change list

| ID | Change | Type | Rationale |
|---|---|---|---|
| C-1 | Add unified reviewer decision ledger/report including unresolved tension summary. | Core query/report + surfaces | Gives audit teams a single accountability artifact. |
| C-2 | Add compatibility preflight output before compliance checkpoint/export. | API + UI/CLI | Makes stricter-review deltas explicit and reviewable. |
| C-3 | Expand multi-vertical workflow parity coverage and acceptance checks. | Scripts/docs/tests | Reduces onboarding friction for governance adopters. |
| C-4 | Add policy-linked role checklists to compliance workflow docs/UI guidance. | Docs/reference guidance | Increases review consistency across teams. |
| C-X1 | Do not auto-close tensions after timeout. | Rejected | Hides unresolved risk; conflicts with audit transparency. |

---

## Recommendation summary

| ID | Recommendation | Decision |
|----|----------------|----------|
| C-1 | Unified decision ledger + unresolved tension summary | Adopt |
| C-2 | Policy compatibility preflight in compliance path | Adopt |
| C-3 | Multi-vertical workflow parity expansion | Adopt |
| C-4 | Compliance role-based checklist templates | Adopt |
| C-X1 | Auto-close tensions after timeout | Reject |
