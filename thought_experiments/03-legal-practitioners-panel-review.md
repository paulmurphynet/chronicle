# Thought experiment 03: Legal practitioners panel review (detailed)

## Setup

A legal-domain review panel evaluates whether Chronicle supports serious legal workflows without pretending to automate legal judgment.

Panelists:

1. **Aria Bennett** (litigation associate)
2. **Marcus Hale** (e-discovery and evidence operations)
3. **Ruth Delgado** (appellate clerk)
4. **Kian Brooks** (legal ops engineer)

Materials reviewed:

- `docs/policy-profiles/legal.json`
- `docs/human-in-the-loop-and-attestation.md`
- `docs/reference-workflows.md`
- `docs/verification-guarantees.md`
- `docs/architecture-core-reference.md`

---

## Aria Bennett (litigation associate)

**What I think is done well**

- Legal policy profile design is appropriately stricter than journalism while still sharing one kernel.
- Tension handling makes contradictory claims explicit rather than hidden in narrative text.
- As-of defensibility supports timeline-sensitive legal reasoning.

**What could improve and why**

- **Role-level review handoffs.** Legal teams operate in stages (drafter, reviewer, sign-off). Chronicle should provide role-based checklist templates so review quality is repeatable.
- **Handoff delta visibility.** If a matter moves from one policy profile to another, the compatibility gap should be visible before checkpoint or export.

---

## Marcus Hale (e-discovery and evidence operations)

**What I think is done well**

- Chain-of-custody report generation and redaction tracking are practical, not theoretical.
- Event-sourced history helps explain provenance of edits and submissions.
- The model retains structure while allowing operational workflows.

**What could improve and why**

- **Audit speed.** To brief counsel quickly, we need one consolidated decision ledger: overrides, dismissals, unresolved tensions, and actor context.
- **Review packet assembly.** Chain-of-custody, reasoning brief, and policy status should be generated in one command for legal review packets.

---

## Ruth Delgado (appellate clerk)

**What I think is done well**

- Chronicle does not overclaim what verifier output means, which is crucial in legal settings.
- Explicitly modeling tensions and rationale makes argumentative weaknesses easier to inspect.
- Policy-driven gates map to procedural standards better than hard-coded product assumptions.

**What could improve and why**

- **Decision rationale consolidation.** Legal readers need to see the sequence of review decisions in one place, with concise rationale text.
- **Policy rationale discoverability.** If thresholds are strict, reviewers should quickly see why those standards were selected.

---

## Kian Brooks (legal ops engineer)

**What I think is done well**

- Core/reference separation is healthy for compliance and change management.
- API-first design means firms can automate intake/review without patching core internals.
- Existing policy profile mechanics provide a good substrate for legal operating playbooks.

**What could improve and why**

- **Operational consistency.** Teams need template checklists and standard packet outputs to reduce process variance.
- **Machine-readable review posture.** Decision ledger and policy compatibility outputs should be parseable for workflow tooling.

---

## Synthesis (moderator)

**Shared praise**

- Chronicle is credible for legal support workflows because it avoids pretending to decide legal truth.
- Chain-of-custody, redaction, event history, and policy rules are already strong foundations.

**Shared improvement themes**

1. Legal review wants one consolidated accountability artifact.
2. Role-based checklist discipline should be standardized.
3. Cross-policy handoff risk should be made explicit before critical actions.
4. Workflow outputs should be both human-readable and machine-readable.

---

## Follow-up discussion: out-of-scope boundaries

The panel explicitly rejects expanding verifier scope to legal conclusions.

- Rejected: "verifier should assert admissibility conclusions." This confuses structural verification with legal judgment.
- Rejected: "auto-resolve contradictions for filing readiness." Human legal review must remain explicit.

---

## Agreed concrete change list

| ID | Change | Type | Rationale |
|---|---|---|---|
| L-1 | Add role-based legal review checklist templates (drafter/reviewer/sign-off) aligned to policy profiles. | Docs + reference guidance | Improves consistency across teams and matters. |
| L-2 | Add unified decision ledger output for legal review (confirms/overrides/dismissals/unresolved tensions). | Core query/report + surfaces | Reduces audit friction and improves accountability traceability. |
| L-3 | Integrate policy compatibility preflight into checkpoint/export flow. | API + UI/CLI | Prevents implicit rule drift during handoff. |
| L-4 | Include policy rationale summary in review packet outputs. | Report/docs | Helps legal reviewers assess appropriateness of standards. |
| L-X1 | Do not make verifier assert legal admissibility outcomes. | Rejected | Violates verifier boundary and overclaims certainty. |
| L-X2 | Do not auto-resolve tensions for filing readiness. | Rejected | Removes required human legal judgment. |

---

## Recommendation summary

| ID | Recommendation | Decision |
|----|----------------|----------|
| L-1 | Role-based legal review checklists | Adopt |
| L-2 | Unified decision ledger | Adopt |
| L-3 | Policy compatibility preflight in legal flow | Adopt |
| L-4 | Policy rationale summary in review packet | Adopt |
| L-X1 | Verifier asserts legal admissibility conclusions | Reject |
| L-X2 | Auto-resolve tensions for filing readiness | Reject |
