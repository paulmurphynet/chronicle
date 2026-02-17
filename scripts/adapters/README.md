# Adapters (examples and templates)

Minimal adapters that map external formats or harnesses to Chronicle (scorer, session, or export).

| Script | Purpose |
|--------|---------|
| **example_rag_to_scorer.py** | Copy-paste template: read JSON (query, answer, evidence) from stdin or file, call the defensibility scorer, print metrics JSON. Use when your RAG harness outputs the same shape as the [eval contract](../docs/eval_contract.md). |
| **fact_checker_to_chronicle.py** | Fact-checker output → Chronicle: claim + verdict + sources (JSON) → evidence items, propose_claim, support/challenge links. Expected format: `claim`, `verdict` (true/false/mixed), `sources` (array with snippet, stance). See script docstring. |
| **provenance_to_chronicle.py** | Provenance assertions → Chronicle: register sources, ingest evidence, link_evidence_to_source. We record; we do not verify. Expected format: `assertions` array with source_display_name, evidence_content, etc. See [Provenance recording](../docs/provenance-recording.md). Requires `--path` to an existing project. |

**Standard path:** Your RAG harness → contract input (query, answer, evidence) → scorer → defensibility metrics. See [RAG evals: defensibility metric](../docs/rag-evals-defensibility-metric.md).
