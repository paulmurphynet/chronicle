# Chronicle

**Defensibility scoring for RAG and evals.** Event-sourced evidence, claims, and defensibility; standalone scorer and .chronicle verifier. Show your work, verify it yourself.

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

## Learning and narrative

| Resource | Purpose |
|----------|---------|
| [Lessons](lessons/README.md) | Step-by-step annotated lessons that walk through the codebase (for developers). |
| [Lessons → Quizzes](lessons/quizzes/README.md) | Quizzes after each lesson to check understanding. |
| [Guidebook](guidebook/README.md) | The story of Chronicle: the problem, why it exists, how we're solving it, challenges, how you can help (for everyone). |
| [Critical areas](critical_areas/README.md) | Epistemological and practical limits: what defensibility and verification do *not* guarantee, so scores are not over-trusted (narrative + technical). |

## Docs

| Doc | Purpose |
|-----|---------|
| [Eval contract](docs/eval_contract.md) | Input/output for the defensibility scorer; how to plug into eval harnesses. |
| [Eval contract schema](docs/eval_contract_schema.json) | JSON Schema for contract input/output (machine-readable validation). |
| [Defensibility metrics schema](docs/defensibility-metrics-schema.md) | Field semantics for the scorer output. |
| [Eval and benchmarking](docs/eval-and-benchmarking.md) | How to run pipelines and report Chronicle defensibility. |
| [Verifier](docs/verifier.md) | How to verify a .chronicle file. |
| [Technical report](docs/technical-report.md) | Defensibility definition and schema (citable). |
| [Neo4j](docs/neo4j.md) | Optional graph projection for multi-run analysis and visualization. |
| [Aura graph pipeline](docs/aura-graph-pipeline.md) | Run an ever-growing Chronicle graph on Neo4j Aura (verify → import → sync). |
| [Chronicle file format](docs/chronicle-file-format.md) | What's inside a .chronicle (ZIP): manifest, DB, evidence; where claims and tensions live. |
| [Epistemology scope](docs/epistemology-scope.md) | What the project covers (and does not) regarding epistemology. |
| [AI to populate epistemology](docs/ai-to-populate-epistemology.md) | How much AI is needed to fully populate claims, support/challenge, tensions. |
| [Using Ollama locally](docs/using-ollama-locally.md) | Use local Ollama (no API key) for tension suggestion, decomposition, type inference. |
| [Migration from V1](docs/migration-from-v1.md) | What we brought from the old project, what we didn't, and why. |
| [State and plan](docs/state-and-plan.md) | What we have so far and the plan going forward. |
| [To-do](docs/to_do.md) | Single implementation to-do list (clear when batch is done and docs are updated). |
| [Testing with Ollama](docs/testing-with-ollama.md) | Use local Ollama for real LLM-backed testing (decomposer, contradiction, type inference, etc.). |
| [Verification guarantees](docs/verification-guarantees.md) | What the verifier does and does not guarantee. |

## License

AGPL-3.0. See [LICENSE](LICENSE).
