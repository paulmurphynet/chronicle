# Chronicle: Defensibility, Schema, and Use for Evaluation

**Technical report (in-repo).** This document can be cited by researchers. It defines defensibility, the core schema (evidence, claim, support/challenge, tension), and how Chronicle is used for evaluation of RAG and reasoning systems. For publication and standards-engagement workflow, see [Whitepaper plan](whitepaper-plan.md) and [Whitepaper draft](whitepaper-draft.md).

**Repository:** chronicle-standard (reference implementation). **Companion:** [Defensibility metrics schema](defensibility-metrics-schema.md), [Benchmark](benchmark.md), [Verifier](verifier.md).

---

## Abstract

Chronicle is an event-sourced epistemic layer for recording **claims** linked to **evidence**, with explicit **support and challenge** links and **tensions** (contradictions) between claims. **Defensibility** is computed per claim from this structure: it summarizes how well a claim holds up under scrutiny (corroboration, contradiction status, weakest link). This report gives a precise definition of defensibility, the core schema, and the use of Chronicle-formatted investigations and defensibility metrics for **evaluation** of retrieval-augmented generation (RAG) and reasoning systems. The same schema supports benchmarks, eval harnesses, and reproducible comparison of pipeline configurations.

---

## 1. Introduction

Systems that produce answers from evidence—RAG pipelines, fact-checking tools, investigative workflows—need to show *why* an answer holds up: which evidence supports it, what contradicts it, and whether the chain from evidence to claim is auditable. Chronicle provides a **defensibility model**: evidence and claims are stored in an append-only ledger; support and challenge links bind claims to evidence spans; tensions record explicit contradictions between claims. **Defensibility** is then computed per claim from these primitives and exposed as a scorecard (provenance quality, corroboration, contradiction status) and as a **reasoning trail** (the ordered events that built or modified the claim). This report defines the model and schema so that researchers can use Chronicle-formatted data and defensibility metrics in benchmarks and evaluations.

---

## 2. Defensibility definition

**Defensibility** is a measure of how well a **claim** holds up under scrutiny, derived from:

1. **Evidence linkage** — Which evidence (or evidence spans) support or challenge the claim. Support and challenge are first-class links; retractions are recorded as events.
2. **Corroboration** — Counts of support links, challenge links, and distinct **sources** (real-world origins of evidence, as modeled by the user) backing the claim. Policy may require a minimum number of independent sources for the claim to be promoted (e.g. to "System-Established Fact").
3. **Contradiction status** — Whether the claim is in **tension** with another claim (open, acknowledged, or resolved). Open tensions reduce defensibility; resolved tensions with recorded rationale are part of the defensibility story.
4. **Temporal and structural dimensions** — Optional: known-as-of date ("when could we first defend this claim?"), decomposition precision (atomic vs compound claim, direct vs inherited evidence links), and attribution posture (who asserted the claim and at what confidence).

Defensibility is **not** a truth value. It is a **structural and policy-relative** summary: given the recorded evidence, links, tensions, and policy rules, how strong is the case for this claim? The scorecard is computed by the system; it does not assert that the claim is true or that sources are independent in the real world.

**Provenance quality (summary label):** The primary summary is **provenance_quality**: `strong` | `medium` | `weak` | `challenged`. It aggregates the dimensions above (e.g. strong = multiple supports, no open tensions, policy thresholds met; challenged = one or more open tensions or net challenge). The full scorecard includes **corroboration** (support_count, challenge_count, independent_sources_count), **contradiction_status** (none | open | acknowledged | resolved), **weakest_link** (the single most vulnerable dimension and an action hint), and optional **knowability** and **explanations**. See [Defensibility metrics schema](defensibility-metrics-schema.md) for the stable fields used in evaluation.

---

## 3. Core schema: evidence, claim, support/challenge, tension

All state is **derived from events** (append-only). The following entities are the core of the defensibility model.

### 3.1 Evidence

- **EvidenceItem** — Immutable blob (document, snippet, or file) with a content hash. Created by `EvidenceIngested`. Identified by `evidence_uid`.
- **EvidenceSpan** — A precise segment within an evidence item (e.g. character offsets, timecode). Created by `SpanAnchored`. Support and challenge links reference **spans**, not whole items, so that "this sentence supports this claim" is explicit. Identified by `span_uid`.

Evidence is stored in the project; integrity is verified by hash (e.g. in the standalone .chronicle verifier).

### 3.2 Claim

- **Claim** — A falsifiable statement. Created by `ClaimProposed`. Has `claim_uid`, `claim_text`, optional type (e.g. SEF, SAC, inference), optional parent_claim_uid (for decomposition). Claims are never stored as "true"; they are proposed, linked to evidence, asserted or withdrawn, and may be in tension with other claims.

Compound claims (multiple propositions in one text) can be progressively **decomposed** into child claims; evidence links can be direct (to a child) or inherited (from the parent). Decomposition precision is a dimension of defensibility.

### 3.3 Support and challenge links

- **SupportLinked** / **ChallengeLinked** — Events that link an **evidence span** to a **claim** with link_type support or challenge. Optional strength (0..1). Retractions are **SupportRetracted** / **ChallengeRetracted**.

The read model maintains which spans support or challenge which claims. Corroboration (support_count, challenge_count, independent_sources_count) is derived from these links and from **source** entities linked to evidence (when used).

### 3.4 Tension

- **Tension** — An explicit record that two claims **conflict** or weaken each other. Created by `TensionDeclared` with `claim_a_uid`, `claim_b_uid`, and optional tension_kind. Status: open, acknowledged, or resolved; resolution can include rationale. Tensions are first-class: they are not "bugs" to fix but part of the defensibility story. Contradiction_status on the scorecard reflects whether the claim has open tensions.

### 3.5 Investigation and project

- **Investigation** — Top-level container for one line of inquiry (story, case, or research question). Contains claims, evidence, and tensions. Identified by `investigation_uid`.
- **Project** — Directory containing the event store, read model, and evidence files. One or more investigations live in a project. Export format: **.chronicle** (ZIP with manifest, SQLite DB, and evidence files), verifiable by a standalone verifier.

The core entities (evidence, claim, support/challenge, tension, investigation) are defined in Section 3 above. Full event and read-model schemas are maintained in the codebase (`chronicle/core/events.py`, `chronicle/core/payloads.py`, `chronicle/store/schema.py`).

---

## 4. Use for evaluation

Chronicle-formatted investigations and defensibility metrics are designed for **evaluation** of RAG and reasoning systems.

### 4.1 Benchmark dataset shape

A **defensibility benchmark** is a dataset of investigations (or claim-centric subsets) that include:

- Claims (with text, type, status)
- Evidence items and spans
- Support and challenge links (which span supports/challenges which claim)
- Tensions (pairs of claims in conflict, with status and optional rationale)
- **Defensibility scorecards** per claim (provenance_quality, corroboration, contradiction_status, weakest_link, knowability)
- **Reasoning trail** (ordered events that built or modified each claim)

The schema is **Chronicle-native**: any conformant `.chronicle` export (or event stream + read model) is a valid benchmark instance. No separate "benchmark format" is required. Synthetic investigations with different defensibility profiles can be generated with `scripts/synthetic_data/generate_realistic_synthetic.py`. See [Benchmark](benchmark.md) for the concept and script references, and [Defensibility metrics schema](defensibility-metrics-schema.md) for the stable metrics fields.

### 4.2 Evaluation targets

| Target | What Chronicle provides |
|--------|-------------------------|
| **Reasoning from evidence** | Claims with ground-truth support/challenge links; scorecards reflecting corroboration and provenance. Systems can be scored on whether they produce claims that match the evidence structure or on how well they predict defensibility. |
| **Citation faithfulness** | Evidence spans linked to claims; reasoning trail showing when and how each link was added. Evaluators can check whether a system's cited evidence actually supports the claim (e.g. NLI-style) and whether behavior aligns with the recorded trail. |
| **Contradiction handling** | Tensions with status and rationale; defensibility reflects open vs resolved tensions. Benchmarks can measure whether a system detects contradictions, proposes resolutions, or maintains consistency with the tension lifecycle. |

### 4.3 Stable metrics for eval harnesses

For RAG pipelines that write to Chronicle, the **defensibility metrics** returned by `GET /claims/{claim_uid}/defensibility` (or the session API `get_defensibility_score`) have a **stable subset** for evals:

- `claim_uid`, `provenance_quality`, `corroboration` (support_count, challenge_count, independent_sources_count), `contradiction_status`, optional `knowability`.

Eval harnesses can run a RAG pipeline with a Chronicle integration, obtain the claim_uid for the answer, and record these metrics per run for comparison across configs or models. Script: `scripts/eval_harness_adapter.py`; Python API: `chronicle.eval_metrics.defensibility_metrics_for_claim(session, claim_uid)`. For **reporting Chronicle defensibility in papers** (what to run, what to report, how to cite), see [Using Chronicle in RAG evaluation](eval-and-benchmarking.md) Section 7 and [Defensibility metrics schema](defensibility-metrics-schema.md) Section 5. For **exporting claim–evidence–defensibility to a training-friendly JSONL** (e.g. for SFT or preference data), see [Benchmark](benchmark.md) Section 2.3 (Export for training), the script `scripts/export_for_ml.py`, and [Chronicle as training data](chronicle-as-training-data.md) (exact schema, examples, use cases).

### 4.4 As-of and reproducibility

Defensibility can be queried **as of a point in time** (date or event_id), so evaluations can compare "defensibility at T1" vs "at T2" or replay the event stream for reproducibility. The .chronicle format is self-contained and verifiable (`chronicle-verify path/to/file.chronicle`) so that benchmark instances can be shared and checked without running the full Chronicle API.

---

## 5. Citation

To cite this technical report or Chronicle in research:

- **In-repo technical report (until preprint is published):** Cite the repository and this document. Example (BibTeX):

  ```bibtex
  @misc{chronicle-technical-report,
    title        = {Chronicle: Defensibility, Schema, and Use for Evaluation},
    author       = {Chronicle},
    year         = {2025},
    howpublished = {Technical report. chronicle-standard repository},
    url          = {https://github.com/chronicle-standard/chronicle-standard/blob/main/docs/technical-report.md},
    note         = {Defensibility definition, core schema, and use for RAG/reasoning evaluation.}
  }
  ```

  In prose: "Chronicle: Defensibility, Schema, and Use for Evaluation. Technical report. chronicle-standard repository. Available: [URL to this doc in the repo]."

- **Preprint / standards paper:** For publication workflow (drafting, evidence pack, review, standards outreach), see [Whitepaper plan](whitepaper-plan.md) and current [Whitepaper draft](whitepaper-draft.md). Once a preprint exists, add it here with standard citation format (e.g. arXiv ID, author, title, year). Placeholder: *When a preprint is available, insert the reference in this section.*

- **Reference implementation:** chronicle-standard (Chronicle reference implementation). https://github.com/chronicle-standard/chronicle-standard (or the canonical repo URL). For machine-readable citation, see the repository root [CITATION.cff](../CITATION.cff).

---

## References (in-repo)

| Document | Description |
|----------|-------------|
| [Defensibility metrics schema](defensibility-metrics-schema.md) | Stable metrics shape for eval harnesses; API and session usage. |
| [Benchmark](benchmark.md) | Defensibility benchmark concept; dataset shape; fixed-query run; export for training (script `export_for_ml.py`). |
| [Using Chronicle in RAG evaluation](eval-and-benchmarking.md) | How to run pipeline + extract metrics; reporting defensibility in papers (Section 7). |
| [Verification guarantees](verification-guarantees.md) | What the verifier guarantees and does not check. |
| [Verifier](verifier.md) | How to run the standalone .chronicle verifier. |
