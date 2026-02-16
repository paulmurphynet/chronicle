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

## What's in this repo

- **Standalone defensibility scorer** — `scripts/standalone_defensibility_scorer.py`: (query, answer, evidence) in, defensibility JSON out. No API or RAG stack required. Implements the [eval contract](docs/eval_contract.md).
- **chronicle-verify** — CLI to verify a .chronicle (ZIP) manifest, schema, and evidence hashes. Stdlib only; no Chronicle package needed for verification.
- **Chronicle package** — Event store, read model, defensibility computation, session API for ingest → claim → link support → get defensibility. Used by the scorer and by integrations.

## Docs

| Doc | Purpose |
|-----|---------|
| [Eval contract](docs/eval_contract.md) | Input/output for the defensibility scorer; how to plug into eval harnesses. |
| [Defensibility metrics schema](docs/defensibility-metrics-schema.md) | Field semantics for the scorer output. |
| [Eval and benchmarking](docs/eval-and-benchmarking.md) | How to run pipelines and report Chronicle defensibility. |
| [Verifier](docs/verifier.md) | How to verify a .chronicle file. |
| [Technical report](docs/technical-report.md) | Defensibility definition and schema (citable). |

## License

AGPL-3.0. See [LICENSE](LICENSE).
