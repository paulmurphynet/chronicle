# Thought experiment 06: RAG/evaluation engineers panel review (detailed)

## Setup

A technical panel evaluates Chronicle as an evaluation and governance primitive inside RAG and agent pipelines.

Panelists:

1. **Iris Cho** (LLM evaluation engineer)
2. **Daniel Kerr** (MLOps lead)
3. **Mina Patel** (applied research scientist)
4. **Leo Voss** (platform API engineer)

Materials reviewed:

- `docs/eval_contract.md`
- `docs/defensibility-metrics-schema.md`
- `docs/eval-and-benchmarking.md`
- `docs/reference-workflows.md`
- `docs/integration-acceptance-checklist.md`

---

## Iris Cho (LLM evaluation engineer)

**What I think is done well**

- Chronicle adds a useful trust-structure signal to standard quality metrics.
- Eval contract is straightforward enough to integrate quickly.
- The model encourages explicit claim/evidence structure rather than opaque scalar scoring.

**What could improve and why**

- **Link quality observability.** Evaluators need output fields that distinguish weakly assured linking from human-validated linking.
- **Caveat proximity.** Default-linking caveats should appear in metrics outputs and dashboards, not only in docs.

---

## Daniel Kerr (MLOps lead)

**What I think is done well**

- Standalone scorer and script-based workflows fit CI pipelines.
- Deterministic artifacts and reports support reproducibility goals.
- Chronicle's architecture boundary helps keep trust logic stable under rapid surface iteration.

**What could improve and why**

- **Machine-readable preflight.** We need JSON compatibility outputs to gate deployments when policy assumptions diverge.
- **Machine-readable decision posture.** Pipelines should detect unresolved human decisions/exceptions without scraping text artifacts.

---

## Mina Patel (applied research scientist)

**What I think is done well**

- Defensibility decomposition (corroboration, contradiction status, weakest link) supports diagnosis better than one opaque score.
- Chronicle's caution around truth claims improves scientific honesty in evaluation reporting.
- Source-level context fields are useful for nuanced analysis when interpreted correctly.

**What could improve and why**

- **Over-aggregation pressure.** Teams will try to compress results into one "trust score." Chronicle should resist this by design and documentation.
- **Vertical eval parity.** Research teams need comparable workflows across journalism/legal/compliance/history to test policy sensitivity.

---

## Leo Voss (platform API engineer)

**What I think is done well**

- API-first orientation and stable contracts make Chronicle a practical platform component.
- Existing adapters and validation scripts provide strong integration scaffolding.
- Export/verifier architecture is suitable for ecosystem interoperability.

**What could improve and why**

- **Endpoint coverage gap.** Compatibility and decision-ledger APIs should be first-class rather than inferred through multiple calls.
- **Unified packet output for partner handoffs.** Integrators want one artifact they can attach to model evaluation reports.

---

## Synthesis (moderator)

**Shared praise**

- Chronicle already solves the hard part: explicit, portable trust structure.
- Contracts and scripts are strong enough for practical integration.

**Shared improvement themes**

1. Add link assurance metadata and caveats in output contracts.
2. Add machine-readable compatibility and reviewer decision surfaces.
3. Expand cross-vertical deterministic workflows for better comparative evaluation.
4. Preserve multi-component scorecards; avoid collapsing into one scalar.

---

## Follow-up discussion: guardrails against misuse

The panel agrees that Chronicle should actively prevent common evaluation misinterpretations.

- Rejecting single-score collapse is part of preserving actionable diagnostics.
- Surfacing link assurance and decision posture is part of preventing false confidence.

---

## Agreed concrete change list

| ID | Change | Type | Rationale |
|---|---|---|---|
| R-1 | Add `link_assurance_level` and caveat fields to scorer/API/export outputs. | Core output schema + docs | Prevents over-trust in support counts by exposing link quality context. |
| R-2 | Add machine-readable policy compatibility preflight surfaces. | API/CLI/report | Enables CI gating when built-under and viewing-under assumptions diverge. |
| R-3 | Add machine-readable reviewer decision ledger surfaces. | Core query/report + API/CLI | Enables automated compliance/review gating in pipelines. |
| R-4 | Expand deterministic multi-vertical workflow coverage in runner outputs. | Scripts/docs/tests | Improves confidence in cross-domain integration behavior. |
| R-X1 | Do not collapse scorecards into one aggregate trust score. | Rejected | Removes diagnostic value and encourages false precision. |

---

## Recommendation summary

| ID | Recommendation | Decision |
|----|----------------|----------|
| R-1 | Link assurance metadata and caveats | Adopt |
| R-2 | Machine-readable policy compatibility preflight | Adopt |
| R-3 | Machine-readable reviewer decision ledger | Adopt |
| R-4 | Multi-vertical deterministic workflow parity | Adopt |
| R-X1 | Single aggregate trust score replacing components | Reject |

---

## Round 2 rerun (2026-02-20): RAG/eval reassessment after implementation

### What changed since Round 1

- Link assurance level/caveat fields are now included in output schemas and surfaced across scorer/session/API/export paths.
- Compatibility preflight and reviewer decision ledger are now machine-readable and available across surfaces.
- Multi-vertical deterministic workflow coverage is significantly improved.
- Sample-data quality hardening added richer, more realistic vertical artifacts and a quality-check script.

### Panelist reassessment

**Iris Cho**

- Output observability improved; link assurance and caveats now support better evaluator interpretation.
- Remaining concern: many teams still need guardrails in dashboards to prevent caveat fields from being dropped.

**Daniel Kerr**

- Machine-readable compatibility and decision posture are now usable for CI gating.
- Remaining concern: pipeline adoption would improve with a prebuilt gate command that fails on missing required review artifacts.

**Mina Patel**

- Multi-component scorecards remain intact and diagnostic quality is preserved.
- Remaining concern: cross-profile sensitivity analysis still takes multiple manual steps.

**Leo Voss**

- API/read-model/report surfaces are much more complete for integration handoffs.
- Remaining concern: partner teams need stronger examples for large, noisy, and partially missing evidence contexts.

### Round 1 recommendation status delta

| ID | Round 1 decision | Round 2 status | Notes |
|---|---|---|---|
| R-1 | Adopt | Completed | Link assurance metadata/caveats shipped. |
| R-2 | Adopt | Completed | Policy compatibility preflight shipped. |
| R-3 | Adopt | Completed | Reviewer decision ledger shipped. |
| R-4 | Adopt | Completed | Multi-vertical workflow parity expanded. |
| R-X1 | Reject | Reaffirm reject | No single aggregate trust score collapse. |

### New rerun recommendations

| ID | Recommendation | Decision | Why |
|---|---|---|---|
| R-R2-1 | Add one command to evaluate "pipeline readiness" (compatibility, decision posture, unresolved-risk thresholds). | Defer | High practical value for MLOps gates; composes existing primitives. |
| R-R2-2 | Add large/noisy benchmark sample pack for stress-testing caveat and uncertainty handling at scale. | Defer | Needed for production confidence, but should be staged after current quality gates mature. |
