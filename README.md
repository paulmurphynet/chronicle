# Chronicle

In the age of AI, generating answers is easy; deciding what to trust is hard. Systems can sound confident even when evidence is weak, missing, or contradictory. Chronicle does not try to define truth. Instead, it provides tools to examine and judge the quality of supporting evidence: link claims to evidence, surface support and challenge structure, score defensibility (provenance, corroboration, contradictions), and package the result in a portable **.chronicle** file that others can verify.

## New here?

Chronicle answers: *How well is this answer supported by evidence?* It’s for RAG evaluation, audits, fact-checking, and anyone who needs a portable, verifiable record of claims and their evidence.

**Prerequisites:** Python 3.11+; we recommend a virtual environment (e.g. `python3 -m venv .venv` then `source .venv/bin/activate` on Linux/macOS). Install the project with `pip install -e .` so the `chronicle` and `chronicle-verify` commands work.

**Two paths:**

- **I want to understand the project** — Read the [Story](story/README.md) (mission, vision, problem, approach, limits), then the [Lessons](lessons/README.md) (codebase walkthrough). Before relying on scores or verification, read [Critical areas](critical_areas/README.md) (what defensibility and “verified” do *not* guarantee).
- **I want to see where we're headed** — Read the [North star](docs/north-star.md) (long-term direction) and the [30/60/90 roadmap](docs/roadmap-30-60-90.md) (concrete near-term execution).
- **I want to run the scorer or verifier** — Use the [Quick start](#quick-start) below, or the full [Getting started](docs/getting-started.md) page. For common issues (e.g. `chronicle: command not found`), see [Troubleshooting](docs/troubleshooting.md).

**Concepts:** [Glossary](docs/glossary.md) defines defensibility, claim, evidence, .chronicle, and related terms.

**Personas:** **Researchers / evaluators** → [Eval contract](docs/eval_contract.md), scorer, [Technical report](docs/technical-report.md). **Engineers integrating** → [Integrating with Chronicle](docs/integrating-with-chronicle.md), session API, [RAG in 5 minutes](docs/rag-in-5-minutes.md). **Contributors** → [CONTRIBUTING](CONTRIBUTING.md), [Lessons](lessons/README.md).

## Quick start

**1. Install and run the defensibility scorer**

The scorer takes one (query, answer, evidence) run and returns a defensibility scorecard. No API or database required—ideal for pipelines and eval harnesses.

```bash
pip install -e .
```

Save a run as JSON (e.g. `run.json`). Example: a RAG answer about a company's emissions, with multiple retrieved chunks as evidence:

```json
{
  "query": "What were Acme Corp's reported Scope 1 emissions for FY2024?",
  "answer": "Acme Corp reported Scope 1 emissions of 12,400 tCO2e for FY2024.",
  "evidence": [
    "Acme Corp Sustainability Report FY2024, p.8: 'Scope 1 (direct) emissions for the reporting period were 12,400 tCO2e, unchanged from the prior year.'",
    "Acme Corp Annual Report 2024, Environmental section: 'Our direct operational footprint (Scope 1) totaled 12,400 tonnes CO2 equivalent.'",
    "CDP submission summary (Acme Corp, 2024): 'Scope 1: 12.4 kt CO2e.'"
  ]
}
```

Pipe it into the scorer:

```bash
PYTHONPATH=. python3 scripts/standalone_defensibility_scorer.py < run.json
```

You get one JSON object back: defensibility metrics for that claim. Example shape:

```json
{
  "contract_version": "1.0",
  "claim_uid": "claim_...",
  "provenance_quality": "strong",
  "corroboration": {
    "support_count": 3,
    "challenge_count": 0,
    "independent_sources_count": 1
  },
  "contradiction_status": "none"
}
```

Here, three evidence chunks support the same claim, so provenance is **strong**. In the default scorer path, evidence is not linked to separate sources, so `independent_sources_count` is derived from the single run; for multi-source corroboration, use the session or API to register sources and link evidence. See [Eval contract](docs/eval_contract.md) and [Defensibility metrics schema](docs/defensibility-metrics-schema.md).

**2. Verify a .chronicle file**

Export an investigation to a .chronicle package (ZIP); anyone can verify it without running your stack:

```bash
chronicle-verify path/to/file.chronicle
```

Use a venv (`source .venv/bin/activate`) or run `./.venv/bin/chronicle-verify` from the repo root. See [Verifier](docs/verifier.md) and [Verification guarantees](docs/verification-guarantees.md).

**3. Run the defensibility benchmark**

Fixed queries, recorded defensibility scores: `PYTHONPATH=. python3 scripts/benchmark_data/run_defensibility_benchmark.py --mode session`. See [Benchmark](docs/benchmark.md).

## What's in this repo

- **Standalone defensibility scorer** — `scripts/standalone_defensibility_scorer.py`: (query, answer, evidence) in, defensibility JSON out. No API or RAG stack required. Implements the [eval contract](docs/eval_contract.md).
- **chronicle-verify** — CLI to verify a .chronicle (ZIP) manifest, schema, and evidence hashes. Stdlib only; no Chronicle package needed for verification.
- **Chronicle package** — Event store, read model, defensibility computation, session API for ingest → claim → link support → get defensibility. Used by the scorer and by integrations.
- **Optional:** HTTP API (`pip install -e ".[api]"`) and Neo4j sync (`.[neo4j]`) for project-based and graph workflows; see [API](docs/api.md) and [Neo4j](docs/neo4j.md).
- **Frontend** — The [Reference UI](frontend/README.md) (human-in-the-loop) lives in `frontend/` in this repo. It will consume only the API; see [Reference UI plan](docs/reference-ui-plan.md) for the same-repo strategy and what we'll bring from V1.

The **.chronicle** format is “show your work”: export your investigation and anyone can verify it with `chronicle-verify`. We encourage tooling that consumes .chronicle (dashboards, fact-checking UIs, or other pipelines); see [Consuming .chronicle](docs/consuming-chronicle.md) and [Claim–evidence–metrics export](docs/claim-evidence-metrics-export.md).

## Learning and narrative

| Resource | Purpose |
|----------|---------|
| [Lessons](lessons/README.md) | Step-by-step annotated lessons that walk through the codebase (for developers). |
| [Lessons → Quizzes](lessons/quizzes/README.md) | Quizzes after each lesson to check understanding. |
| [Story](story/README.md) | The Chronicle story: mission, vision, the problem, why it exists, how we're solving it, challenges, how you can help (for everyone). |
| [Critical areas](critical_areas/README.md) | Epistemological and practical limits: what defensibility and verification do *not* guarantee, so scores are not over-trusted (narrative + technical). |

## Docs

**Essential:** [Eval contract](docs/eval_contract.md) (scorer I/O), [Verifier](docs/verifier.md) (.chronicle verification), [Technical report](docs/technical-report.md) (defensibility definition), [Story](story/README.md) (narrative), [Critical areas](critical_areas/README.md) (limits), [Troubleshooting](docs/troubleshooting.md) (common issues), [Glossary](docs/glossary.md) (terms). **Releases:** [CHANGELOG](CHANGELOG.md) and tagged versions for pinning. **Citation:** [Technical report Section 5 (Citation)](docs/technical-report.md#5-citation) and [CITATION.cff](CITATION.cff).

**By topic:**

| Doc | Purpose |
|-----|---------|
| [Eval contract](docs/eval_contract.md) | Input/output for the defensibility scorer; how to plug into eval harnesses. |
| [Eval contract schema](docs/eval_contract_schema.json) | JSON Schema for contract input/output (machine-readable validation). |
| [Defensibility metrics schema](docs/defensibility-metrics-schema.md) | Field semantics for the scorer output. |
| [Eval and benchmarking](docs/eval-and-benchmarking.md) | How to run pipelines and report Chronicle defensibility. |
| [Trust metrics](docs/trust-metrics.md) | North-star KPI definitions and baseline comparison workflow for benchmark outputs. |
| [Rejected feature decisions](docs/rejected-feature-decisions.md) | Intentional "no" decisions with rationale/tradeoffs to preserve trust boundaries. |
| [Adversarial and failure-mode examples](docs/adversarial-failure-modes.md) | Safe-failure scenarios and uncertainty-disclosure expectations for defensibility workflows. |
| [HTTP API](docs/api.md) | Optional minimal API: `pip install -e ".[api]"`, set `CHRONICLE_PROJECT_PATH`, run uvicorn. Write/read/export/import. |
| [RAG evals: defensibility metric](docs/rag-evals-defensibility-metric.md) | Contract, schema, and how to run the scorer in your RAG harness as a defensibility metric. |
| [Verifier](docs/verifier.md) | How to verify a .chronicle file. |
| [Errors](docs/errors.md) | Error types (ChronicleUserError, etc.); when to use which; how CLI/API map to exit codes and HTTP status. |
| [Technical report](docs/technical-report.md) | Defensibility definition and schema (citable). |
| [Neo4j](docs/neo4j.md) | Optional graph projection for multi-run analysis and visualization, with a parity check across sync/export/rebuild/docs. |
| [Neo4j operations runbook](docs/neo4j-operations-runbook.md) | Backup/restore, sync cadence, drift handling, and capacity/cost guardrails for Neo4j projection operations. |
| [Neo4j query pack](docs/neo4j-query-pack.md) | Operational Cypher query set (tension triage, support/challenge balance, source concentration, lineage) and indexing guidance. |
| [Neo4j projection baseline v0.9.0](docs/benchmarks/neo4j_projection_baseline_v0.9.0.md) | Thresholded benchmark evidence for export-path throughput and memory at launch scale. |
| [Neo4j projection sync baseline v0.9.0](docs/benchmarks/neo4j_projection_sync_baseline_v0.9.0.md) | Thresholded large-run sync benchmark evidence against a live Neo4j instance. |
| [PostgreSQL backend](docs/POSTGRES.md) | Postgres convergence track: local bootstrap (`make postgres-up`), doctor/smoke checks, and current scope. |
| [Support policy](docs/support-policy.md) | Support tiers (Lite/Team/Managed), GA/Beta/Experimental status, compatibility guarantees, and deprecation timeline policy. |
| [Production readiness checklist](docs/production-readiness-checklist.md) | Objective go/no-go criteria for trust gates, backend checks, CI branch protection, security, and docs. |
| [CI branch protection checklist](docs/ci-branch-protection.md) | Exact required CI checks to enforce before merge on protected branches. |
| [Branch protection rollout verification](docs/branch-protection-rollout-verification.md) | API-driven verification workflow and evidence artifact for final CI/branch-protection release gating. |
| [Post-public finalization checklist](docs/post-public-finalization-checklist.md) | One pass to close post-public CI/branch-protection/Neo4j-live/standards-dispatch gating items. |
| [Neo4j schema](docs/neo4j-schema.md) | Node labels, relationship types, and example Cypher for the sync output. |
| [Aura graph pipeline](docs/aura-graph-pipeline.md) | Run an ever-growing Chronicle graph on Neo4j Aura (verify → import → sync). |
| [Chronicle file format](docs/chronicle-file-format.md) | What's inside a .chronicle (ZIP): manifest, DB, evidence; where claims and tensions live. |
| [Consuming .chronicle](docs/consuming-chronicle.md) | How to read a .chronicle without the Chronicle package (ZIP + SQLite + evidence). |
| [Generic export](docs/GENERIC_EXPORT.md) | Export investigation as JSON or CSV ZIP for BI, dashboards, fact-checking pipelines. |
| [Claim–evidence–metrics export](docs/claim-evidence-metrics-export.md) | Stable JSON shape for one claim + evidence refs + defensibility (fact-checking UIs, dashboards). |
| [ClaimReview export](docs/claimreview-export.md) | schema.org ClaimReview interoperability profile mapped from Chronicle defensibility. |
| [RO-Crate export](docs/ro-crate-export.md) | RO-Crate interoperability profile for Chronicle investigations and package metadata. |
| [C2PA compatibility export](docs/c2pa-compatibility-export.md) | C2PA reference export from evidence metadata with explicit verification-mode semantics. |
| [VC/Data Integrity export](docs/vc-data-integrity-export.md) | VC/Data Integrity attestation export for claims, artifacts, and checkpoints with explicit verification-mode semantics. |
| [Adjacent standards guidance](docs/adjacent-standards-guidance.md) | Chronicle boundaries and integration guidance for OpenLineage, in-toto, and SLSA. |
| [External IDs](docs/external-ids.md) | How to store fact-check IDs, C2PA claim IDs, etc. in evidence metadata (and claim notes/tags when exposed). |
| [Provenance recording](docs/provenance-recording.md) | Store source and evidence–source links; feed C2PA/CR assertions (we record, we don’t verify). |
| [Epistemology scope](docs/epistemology-scope.md) | What the project covers (and does not) regarding epistemology. |
| [AI to populate epistemology](docs/ai-to-populate-epistemology.md) | How much AI is needed to fully populate claims, support/challenge, tensions. |
| [Using Ollama locally](docs/using-ollama-locally.md) | Use local Ollama (no API key) for tension suggestion, decomposition, type inference. |
| [Lizzie Borden case study](docs/case-study-lizzie-borden.md) | Rationale for using the inquest transcript as a trust benchmark (sworn-testimony scope, noisy web-training-data contrast, and neutral evaluation protocol). |
| [State and plan](docs/state-and-plan.md) | What we have so far and the plan going forward. |
| [30/60/90 roadmap](docs/roadmap-30-60-90.md) | Time-bound execution plan from trust baseline to design-partner readiness. |
| [To-do](docs/to_do.md) | Single implementation to-do list (clear when batch is done and docs are updated). |
| [Standards profile](docs/standards-profile.md) | Chronicle interoperability profile across JSON-LD/PROV, C2PA, VC/Data Integrity, RO-Crate, and ClaimReview. |
| [Standards JSON-LD export](docs/standards-jsonld-export.md) | JSON-LD + PROV-oriented export profile for investigations (claims/evidence/links/tensions/sources). |
| [Whitepaper plan](docs/whitepaper-plan.md) | Publication workflow and standards-submission process for Chronicle. |
| [Whitepaper draft](docs/whitepaper-draft.md) | Working draft for standards-facing publication and external review. |
| [Whitepaper evidence pack](docs/whitepaper-evidence-pack.md) | Reproducible evidence bundle for whitepaper claims and standards-review discussions. |
| [Whitepaper citation metadata](docs/whitepaper-citation.md) | Versioned citation and publication metadata for whitepaper revisions. |
| [Whitepaper internal review log](docs/whitepaper-internal-review-log.md) | Accepted/rejected technical review outcomes per whitepaper revision. |
| [Standards submission package](docs/standards-submission-package.md) | Checklist and outreach notes for standards-body/community submissions. |
| [Core vs reference architecture](docs/architecture-core-reference.md) | How trust-critical core differs from API/CLI/UI reference surfaces and why that boundary matters. |
| [Testing with Ollama](docs/testing-with-ollama.md) | Use local Ollama for real LLM-backed testing (decomposer, contradiction, type inference, etc.). |
| [Verification guarantees](docs/verification-guarantees.md) | What the verifier does and does not guarantee; runtime invariants and audit. |
| [Implementer checklist](docs/implementer-checklist.md) | Produce or consume a .chronicle: checklist and pointers. |
| [Integration quick reference](docs/integration-quick-reference.md) | One page: score one run, verify .chronicle, add to harness, optional API/adapters. |
| [Reference workflows](docs/reference-workflows.md) | Reproducible, end-to-end workflow set for journalism, compliance-style audit, and benchmark trust tracking. |
| [Integration acceptance checklist](docs/integration-acceptance-checklist.md) | Release checklist for adapters and connectors (contract, trust posture, reproducibility). |
| [Starter packs](docs/starter-packs.md) | Opinionated project bootstrap packs (journalism, legal, audit) with policy defaults and defensibility-ready artifacts. |
| [API ingestion pipeline example](docs/api-ingestion-pipeline-example.md) | End-to-end API pipeline example: batch input to Chronicle writes, defensibility output, and export artifact. |
| [Integration export hardening](docs/integration-export-hardening.md) | Hardened contract for JSON/CSV/Markdown exports and signed `.chronicle` bundle import/export with release-test harness. |
| [Postgres operations runbook](docs/postgres-operations-runbook.md) | Backup, restore, and disaster-recovery procedure for Chronicle deployments using Postgres. |
| [Managed Postgres hardening](docs/postgres-hardening.md) | TLS, least-privilege, credential rotation, and network/monitoring hardening guidance. |
| [Backend migration/versioning policy](docs/backend-migration-versioning-policy.md) | Versioning and migration expectations for event/read-model schemas across SQLite and Postgres. |
| [User manual](docs/manual/README.md) | Short how-to manual (install, scorer, verifier, format, integration, limits). |
| [RAG in 5 minutes](docs/rag-in-5-minutes.md) | One command (`chronicle quickstart-rag`) to see defensibility; next steps to scorer and integration. |
| [Human-in-the-loop and attestation](docs/human-in-the-loop-and-attestation.md) | Human-curated data, actor identity (CLI env, API headers), attestation and verification level; curation workflow. |
| [Reference UI plan](docs/reference-ui-plan.md) | Same-repo strategy for the Reference UI; what to bring from V1 (friction tiers, Propose–Confirm, Reading-lite). |
| [Onboarding and open-source checklist](docs/ONBOARDING_AND_OPEN_SOURCE.md) | Plan for making the repo ready for colleagues and public release. |
| [Getting started](docs/getting-started.md) | One page: what Chronicle is, install, scorer + verifier quick start, next steps. |

## License

MIT. See [LICENSE](LICENSE).
