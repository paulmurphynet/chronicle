# Thought experiments

This folder contains structured thought experiments used to pressure-test Chronicle against real audiences and use cases.

The goal is not to brainstorm features endlessly. The goal is to decide what improves Chronicle's core mission, what belongs in policy/UI layers, and what should be explicitly rejected.

## Method (better than ad-hoc prompting)

We use a repeatable panel workflow instead of one-off essays:

1. Pick one audience/use case.
2. Simulate a 4-expert panel with different roles inside that audience.
3. Capture strengths, gaps, and risks.
4. Run each recommendation through a conflict screen:
- Does it violate Chronicle's core boundary (defensibility, not truth)?
- Does it belong in Core, Policy profile, or Reference surface?
- Is it additive and backward-compatible?
5. Record a decision (`adopt`, `defer`, `reject`) with rationale.
6. For `adopt`, add an implementation item to `docs/to_do.md` with clear acceptance criteria.

See `00-panel-method.md` for the full rubric.

## Standard depth and format

Each panel file should follow a detailed structure (same depth standard):

1. Setup and panel composition
2. Panelist-by-panelist assessments (`what is strong`, `what should improve`, `why`)
3. Moderator synthesis (shared praise, shared gaps)
4. Conflict checks and out-of-scope boundaries
5. Agreed concrete change list
6. Recommendation summary table (`adopt`, `defer`, `reject`)

## Current panel set

| # | Panel | Focus |
|---|-------|-------|
| [00](00-panel-method.md) | Panel method | Rubric, conflict checks, and decision rules |
| [01](01-epistemologists-conference-review.md) | Epistemologists | Scope integrity, defensibility semantics, policy boundaries |
| [02](02-investigative-journalists-panel-review.md) | Investigative journalists | Editorial workflow, publication risk, explainability |
| [03](03-legal-practitioners-panel-review.md) | Legal practitioners | Admissibility, chain-of-custody, defensibility under scrutiny |
| [04](04-historians-archivists-panel-review.md) | Historians and archivists | Temporal reasoning, source provenance, uncertainty reporting |
| [05](05-compliance-audit-panel-review.md) | Compliance and audit leads | Controls, exceptions, review accountability |
| [06](06-rag-evaluation-engineers-panel-review.md) | RAG/eval engineers | Contract clarity, metric reliability, pipeline adoption |
| [Decision register](decision-register.md) | Cross-panel decisions | Adopt/defer/reject log with reasons and TODO linkage |

## What changed in this batch

- Replaced the previous single-panel format with a multi-audience review cycle.
- Added a decision register to document accepted and rejected ideas.
- Linked adopted recommendations to concrete implementation planning in `docs/to_do.md`.

## Operating rule

A recommendation is only accepted if it strengthens Chronicle's trust posture without turning Chronicle into a truth engine, a global credibility oracle, or separate per-vertical products.
