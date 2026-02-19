# Thought experiment method: panel + decision gate

## Purpose

Create a consistent way to evaluate feature ideas from different expert audiences without drifting from Chronicle's core identity.

## Panel composition (per audience)

Use four panelists with complementary perspectives:

1. Domain practitioner (daily workflow reality)
2. Reviewer/auditor (quality and accountability)
3. Methodologist/researcher (validity and assumptions)
4. Product/integration specialist (operational feasibility)

## Review rubric

Each panel reviews Chronicle on five dimensions:

1. **Core alignment**: stays within defensibility-not-truth boundary.
2. **Trust impact**: reduces misuse/overclaim risk.
3. **Workflow fit**: helps real domain decisions with less manual friction.
4. **Contract stability**: additive/backward-compatible for API/scorer/verifier.
5. **Layer placement**: correctly assigned to Core vs Policy vs Reference surfaces.

## Recommendation template

For each recommendation, capture:

- `problem`: what fails today
- `proposal`: concrete change
- `layer`: `core`, `policy-profile`, `reference-surface`, or `docs`
- `risk`: conflict with core behavior, complexity, or user over-trust
- `decision`: `adopt`, `defer`, `reject`
- `reason`: why the decision was made

## Conflict checks (mandatory)

Reject or re-scope any recommendation that:

- asks Chronicle to output truth/factuality verdicts,
- claims verified real-world source independence by default,
- hides unresolved tensions or weak evidence from reviewers,
- forks Chronicle into separate per-vertical kernels.

## Segregation rule

- **Core**: event model, policy engine, defensibility computation, `.chronicle`, verifier.
- **Policy profile**: thresholds, admissibility, checkpoint requirements.
- **Reference surfaces**: UI/CLI/API workflows, guidance, and reporting bundles.

When in doubt, keep Core minimal and move specialization to policy + reference layers.

## Completion criteria for one panel cycle

1. Panel report file exists.
2. Recommendations are listed in `decision-register.md`.
3. Any `adopt` item appears in `docs/to_do.md` with acceptance criteria.
4. Rejected items have explicit rationale.
