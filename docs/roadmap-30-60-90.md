# 30/60/90 execution roadmap

This roadmap translates Chronicle's north star into near-term execution for an open-source release.

Start date: February 19, 2026

## Outcome we optimize for

Improve practical trust signals for AI-generated claims by reducing unsupported output and making evidence quality measurable, reproducible, and reviewable.

## North-star metric (operational)

Primary KPI: effective unsupported rate from benchmark runs.

Definition and command workflow: [Trust metrics](trust-metrics.md).

---

## First 30 days (Phase 1): measurable trust baseline

Goal: establish a metric and gate for "trust progress" that can be tracked over time.

Deliverables:

1. Standardize benchmark output as the canonical measurement input (`run_defensibility_benchmark.py`).
2. Define and document trust KPIs and failure semantics ([trust-metrics.md](trust-metrics.md)).
3. Add machine-readable summary + threshold tool:
   `scripts/benchmark_data/trust_progress_report.py`.
4. Add regression-ready checks for defensibility guardrails and trust KPIs.
5. Document the baseline workflow in benchmark docs so contributors can reproduce results.

Success criteria:

1. A contributor can run the benchmark and get a KPI report with one command.
2. The KPI report can fail with clear thresholds (rate caps and baseline regression checks).
3. The metric definition is explicit about limitations and does not overclaim truth.

---

## By 60 days (Phase 2): reference workflows and integrations

Goal: prove utility in realistic tasks and reduce adoption friction.

Deliverables:

1. Publish 2-3 end-to-end reference workflows (journalism, compliance, research/legal-lite).
2. Add notebook-first examples for ingest -> claim -> support/challenge -> defensibility -> export.
3. Add one production-oriented adapter package template for external pipelines.
4. Define a stable "integration acceptance checklist" for community connectors.
5. Ship a standards interoperability profile v0.1 (JSON-LD/PROV baseline plus staged C2PA/VC/RO-Crate/ClaimReview paths).

Success criteria:

1. New users can run a domain workflow without reading internal implementation details.
2. External contributors have a low-friction pattern for adapters and validation.
3. Workflow docs and scripts stay aligned through reproducible command paths.

---

## By 90 days (Phase 3): public trust posture and design partner readiness

Goal: be safe and credible for broader public adoption.

Deliverables:

1. Publish a formal threat model and expanded security posture docs.
2. Publish reproducibility guidance for benchmark reporting and citations.
3. Run a small design-partner loop (3-5 teams) and capture structured findings.
4. Prioritize fixes based on measured trust deltas and integration pain points.
5. Publish a standards-facing whitepaper revision with reproducible evidence pack and versioned citations.

Success criteria:

1. Public docs clearly communicate guarantees, non-guarantees, and operating limits.
2. At least one external team can reproduce Chronicle KPI outputs end-to-end.
3. Roadmap decisions are backed by metrics or user evidence, not speculative features.

---

## Scope discipline

This roadmap keeps Chronicle focused on its core role:

1. Evidence/claim structure and defensibility modeling.
2. Portable, verifiable artifacts (`.chronicle` + verifier).
3. Stable contracts for integrations and evaluation workflows.

Out of scope remains unchanged: Chronicle does not define absolute truth and does not claim semantic entailment verification by default.
