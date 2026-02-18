# Chronicle

**Defensibility scoring for RAG and evals.** Event-sourced evidence, claims, and defensibility; standalone scorer and .chronicle verifier. Show your work, verify it yourself.

## New here?

Chronicle answers: *How well is this answer supported by evidence?* It’s for RAG evaluation, audits, and anyone who needs a portable, verifiable record of claims and their evidence.

**Prerequisites:** Python 3.11+; we recommend a virtual environment (e.g. `python3 -m venv .venv` then `source .venv/bin/activate` on Linux/macOS). Install the project with `pip install -e .` so the `chronicle` and `chronicle-verify` commands work.

**Two paths:**

- **I want to understand the project** — Read the [Guidebook](guidebook/README.md) (the story: problem, approach, limits), then the [Lessons](lessons/README.md) (codebase walkthrough). Before relying on scores or verification, read [Critical areas](critical_areas/README.md) (what defensibility and “verified” do *not* guarantee).
- **I want to run the scorer or verifier** — Use the [Quick start](#quick-start) below, or the full [Getting started](docs/getting-started.md) page. For common issues (e.g. `chronicle: command not found`), see [Troubleshooting](docs/troubleshooting.md).

**Concepts:** [Glossary](docs/glossary.md) defines defensibility, claim, evidence, .chronicle, and related terms.

**Personas:** **Researchers / evaluators** → [Eval contract](docs/eval_contract.md), scorer, [Technical report](docs/technical-report.md). **Engineers integrating** → [Integrating with Chronicle](docs/integrating-with-chronicle.md), session API, [RAG in 5 minutes](docs/rag-in-5-minutes.md). **Contributors** → [CONTRIBUTING](CONTRIBUTING.md), [Lessons](lessons/README.md).

## Quick start

**Score one (query, answer, evidence) run:**

```bash
pip install -e .
echo '{"query": "What was revenue?", "answer": "Revenue was $1.2M.", "evidence": ["The company reported revenue of $1.2M in Q1 2024."]}' \
  | PYTHONPATH=. python3 scripts/standalone_defensibility_scorer.py
```

Output: one JSON object with defensibility metrics (or error). See [Eval contract](docs/eval_contract.md).

**Verify a .chronicle file:**

```bash
chronicle-verify path/to/file.chronicle
```

(Activate the project venv first: `source .venv/bin/activate`, or run with `./.venv/bin/chronicle-verify` from the repo root.)

## What's in this repo

- **Standalone defensibility scorer** — `scripts/standalone_defensibility_scorer.py`: (query, answer, evidence) in, defensibility JSON out. No API or RAG stack required. Implements the [eval contract](docs/eval_contract.md).
- **chronicle-verify** — CLI to verify a .chronicle (ZIP) manifest, schema, and evidence hashes. Stdlib only; no Chronicle package needed for verification.
- **Chronicle package** — Event store, read model, defensibility computation, session API for ingest → claim → link support → get defensibility. Used by the scorer and by integrations.

The **.chronicle** format is “show your work”: export your investigation and anyone can verify it with `chronicle-verify`. We encourage tooling that consumes .chronicle (dashboards, fact-checking UIs, or other pipelines); see [Consuming .chronicle](docs/consuming-chronicle.md) and [Claim–evidence–metrics export](docs/claim-evidence-metrics-export.md).

## Learning and narrative

| Resource | Purpose |
|----------|---------|
| [Lessons](lessons/README.md) | Step-by-step annotated lessons that walk through the codebase (for developers). |
| [Lessons → Quizzes](lessons/quizzes/README.md) | Quizzes after each lesson to check understanding. |
| [Guidebook](guidebook/README.md) | The story of Chronicle: the problem, why it exists, how we're solving it, challenges, how you can help (for everyone). |
| [Critical areas](critical_areas/README.md) | Epistemological and practical limits: what defensibility and verification do *not* guarantee, so scores are not over-trusted (narrative + technical). |

## Docs

**Essential:** [Eval contract](docs/eval_contract.md) (scorer I/O), [Verifier](docs/verifier.md) (.chronicle verification), [Technical report](docs/technical-report.md) (defensibility definition), [Guidebook](guidebook/README.md) (narrative), [Critical areas](critical_areas/README.md) (limits), [Troubleshooting](docs/troubleshooting.md) (common issues), [Glossary](docs/glossary.md) (terms). **Releases:** [CHANGELOG](CHANGELOG.md) and tagged versions for pinning. **Citation:** [Technical report Section 5 (Citation)](docs/technical-report.md#5-citation) and [CITATION.cff](CITATION.cff).

**By topic:**

| Doc | Purpose |
|-----|---------|
| [Eval contract](docs/eval_contract.md) | Input/output for the defensibility scorer; how to plug into eval harnesses. |
| [Eval contract schema](docs/eval_contract_schema.json) | JSON Schema for contract input/output (machine-readable validation). |
| [Defensibility metrics schema](docs/defensibility-metrics-schema.md) | Field semantics for the scorer output. |
| [Eval and benchmarking](docs/eval-and-benchmarking.md) | How to run pipelines and report Chronicle defensibility. |
| [HTTP API](docs/api.md) | Optional minimal API: `pip install -e ".[api]"`, set `CHRONICLE_PROJECT_PATH`, run uvicorn. Write/read/export/import. |
| [RAG evals: defensibility metric](docs/rag-evals-defensibility-metric.md) | Contract, schema, and how to run the scorer in your RAG harness (standard metric). |
| [Verifier](docs/verifier.md) | How to verify a .chronicle file. |
| [Errors](docs/errors.md) | Error types (ChronicleUserError, etc.); when to use which; how CLI/API map to exit codes and HTTP status. |
| [Technical report](docs/technical-report.md) | Defensibility definition and schema (citable). |
| [Neo4j](docs/neo4j.md) | Optional graph projection for multi-run analysis and visualization. |
| [Neo4j schema](docs/neo4j-schema.md) | Node labels, relationship types, and example Cypher for the sync output. |
| [Aura graph pipeline](docs/aura-graph-pipeline.md) | Run an ever-growing Chronicle graph on Neo4j Aura (verify → import → sync). |
| [Chronicle file format](docs/chronicle-file-format.md) | What's inside a .chronicle (ZIP): manifest, DB, evidence; where claims and tensions live. |
| [Consuming .chronicle](docs/consuming-chronicle.md) | How to read a .chronicle without the Chronicle package (ZIP + SQLite + evidence). |
| [Generic export](docs/GENERIC_EXPORT.md) | Export investigation as JSON or CSV ZIP for BI, dashboards, fact-checking pipelines. |
| [Claim–evidence–metrics export](docs/claim-evidence-metrics-export.md) | Stable JSON shape for one claim + evidence refs + defensibility (fact-checking UIs, dashboards). |
| [External IDs](docs/external-ids.md) | How to store fact-check IDs, C2PA claim IDs, etc. in evidence metadata (and claim notes/tags when exposed). |
| [Provenance recording](docs/provenance-recording.md) | Store source and evidence–source links; feed C2PA/CR assertions (we record, we don’t verify). |
| [Epistemology scope](docs/epistemology-scope.md) | What the project covers (and does not) regarding epistemology. |
| [AI to populate epistemology](docs/ai-to-populate-epistemology.md) | How much AI is needed to fully populate claims, support/challenge, tensions. |
| [Using Ollama locally](docs/using-ollama-locally.md) | Use local Ollama (no API key) for tension suggestion, decomposition, type inference. |
| [Migration from V1](docs/migration-from-v1.md) | What we brought from the old project, what we didn't, and why. |
| [State and plan](docs/state-and-plan.md) | What we have so far and the plan going forward. |
| [To-do](docs/to_do.md) | Single implementation to-do list (clear when batch is done and docs are updated). |
| [Testing with Ollama](docs/testing-with-ollama.md) | Use local Ollama for real LLM-backed testing (decomposer, contradiction, type inference, etc.). |
| [Verification guarantees](docs/verification-guarantees.md) | What the verifier does and does not guarantee; runtime invariants and audit. |
| [Implementer checklist](docs/implementer-checklist.md) | Produce or consume a .chronicle: checklist and pointers. |
| [RAG in 5 minutes](docs/rag-in-5-minutes.md) | One command (`chronicle quickstart-rag`) to see defensibility; next steps to scorer and integration. |
| [Human-in-the-loop and attestation](docs/human-in-the-loop-and-attestation.md) | Human-curated data, actor identity (CLI env, API headers), attestation and verification level; curation workflow. |
| [Onboarding and open-source checklist](docs/ONBOARDING_AND_OPEN_SOURCE.md) | Plan for making the repo ready for colleagues and public release. |
| [Getting started](docs/getting-started.md) | One page: what Chronicle is, install, scorer + verifier quick start, next steps. |

## License

MIT. See [LICENSE](LICENSE).
