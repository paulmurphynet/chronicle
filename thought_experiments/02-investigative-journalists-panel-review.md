# Thought experiment 02: Investigative journalists panel review (detailed)

## Setup

Imagine a newsroom workshop where Chronicle is reviewed by four senior professionals who run high-stakes investigations under publication pressure. They are asked to evaluate Chronicle as a practical "verification and publication confidence" system, not as a generic content platform.

Panelists:

1. **Mara Torres** (investigations editor)
2. **Devon Pike** (fact-check lead)
3. **Elena Rowe** (standards and ethics editor)
4. **Noah Singh** (data journalist and newsroom tooling lead)

Materials reviewed:

- `docs/reference-workflows.md`
- `docs/policy-profiles/journalism.json`
- `docs/human-in-the-loop-and-attestation.md`
- `docs/reasoning-brief.md`
- `docs/verification-guarantees.md`

---

## Mara Torres (investigations editor)

**What I think is done well**

- The claim/evidence/tension model matches editorial reality: we often publish despite unresolved ambiguity, but we need to know exactly where it is.
- Chronicle's policy profile pattern is strong for newsroom governance. We can set publication bars (MES, tension rules) without changing the core model.
- Event history helps when an editor asks: "What changed between draft one and legal review?"

**What could improve and why**

- **Review packet fragmentation.** Editors currently gather data from multiple outputs (reasoning brief, tensions, chain-of-custody status, policy context). We need one publication packet generated in one step.
- **Cross-profile handoff clarity.** A story built under journalism rules may be reviewed under legal or compliance rules. We need a default "policy compatibility preflight" so the handoff risk is explicit.

---

## Devon Pike (fact-check lead)

**What I think is done well**

- Span-level linking is exactly what fact-check teams need. "This sentence supports this claim" is a practical review unit.
- Explicit support/challenge links create better editorial discipline than flat citation lists.
- Source independence and reliability notes, even when user-recorded only, are useful context if clearly labeled.

**What could improve and why**

- **Link assurance ambiguity.** Support counts are not enough. A fact-check lead needs to know whether links were auto-created by convenience workflow or confirmed by human review.
- **Default scorer caveat visibility.** For newsroom users, caveats about default evidence-linking behavior should be surfaced in outputs, not only buried in docs.

---

## Elena Rowe (standards and ethics editor)

**What I think is done well**

- Chronicle's non-guarantee language is unusually responsible. It avoids pretending that "verified" means "true."
- Human decisions (confirm/override/dismiss) align with accountability expectations in publication ethics.
- Tensions are first-class instead of hidden in free text, which helps avoid accidental omission during review.

**What could improve and why**

- **Decision visibility.** We can record editorial choices, but the review experience still needs a single decision ledger that answers: who accepted what risk, when, and why.
- **Executive transparency without simplification risk.** We should support concise summaries for editors, but never hide unresolved tensions or weak evidence in those summaries.

---

## Noah Singh (data journalist and tooling lead)

**What I think is done well**

- API-oriented design and reproducible scripts make Chronicle viable for hybrid manual+automated newsroom pipelines.
- `.chronicle` export plus verifier gives external reviewers a way to inspect packaging integrity without the whole stack.
- Existing workflows already prove a path from ingest to defensibility to export.

**What could improve and why**

- **Machine-readable preflight.** We need compatibility deltas in JSON for CI checks and editorial workflow bots.
- **Review artifact consolidation.** A single packet with reasoning, tensions, policy delta, and decision log reduces coordination costs during deadline windows.

---

## Synthesis (moderator)

**Shared praise**

- Chronicle's explicit defensibility-not-truth boundary is editorially healthy.
- Support/challenge/tension structure is substantially better than ad hoc citation notes.
- Policy profiles are the right location for domain strictness.

**Shared improvement themes**

1. Publication and legal handoff needs first-class policy compatibility preflight.
2. Review needs one bundle, not scattered outputs.
3. Link assurance status must be visible to avoid over-trusting support counts.
4. Human decision accountability should be review-ready in one ledger.

---

## Follow-up discussion: what should be adopted now

The panel agrees that Chronicle should optimize for **reviewability** rather than automated credibility judgments.

- Accepted direction: make review artifacts denser and easier to consume.
- Rejected direction: add automated global source credibility scores.
- Rejected direction: hide unresolved tensions in "executive" views.

---

## Agreed concrete change list

| ID | Change | Type | Rationale |
|---|---|---|---|
| J-1 | Add a unified review packet generator (reasoning brief + tensions + policy delta + decision summary + chain-of-custody status). | API/CLI/report | Editorial and legal review should run from one artifact. |
| J-2 | Add policy compatibility preflight for publish/checkpoint paths (human-readable + machine-readable). | API + UI/CLI | Cross-profile handoff risk should be explicit before release. |
| J-3 | Add visible link assurance metadata and caveat text in review outputs. | Core output + docs + UI | Prevent misuse of support counts when link quality varies. |
| J-4 | Add consolidated reviewer decision ledger output. | Core query/report + surfaces | Editors need fast accountability trace: who overrode what and why. |
| J-X1 | Do not add global source credibility scoring. | Rejected | Encourages false authority and conflicts with "record, don't certify." |
| J-X2 | Do not hide unresolved tensions in concise summaries. | Rejected | Weakens transparency and increases publication risk. |

---

## Recommendation summary

| ID | Recommendation | Decision |
|----|----------------|----------|
| J-1 | Unified review packet | Adopt |
| J-2 | Policy compatibility preflight | Adopt |
| J-3 | Link assurance metadata visibility | Adopt |
| J-4 | Unified reviewer decision ledger | Adopt |
| J-X1 | Global source credibility score | Reject |
| J-X2 | Hide unresolved tensions in summaries | Reject |
