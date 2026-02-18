# Scripts

Scripts and data used for eval pipelines, sample generation, benchmark data, scenario validation, and doc/link utilities. Run from repo root with `PYTHONPATH=.` when a script imports `chronicle` or `tools` (e.g. `PYTHONPATH=. python3 scripts/generate_sample_chronicle.py`).

---

## First-class scripts (eval, verification, export, RAG)

These are the main entry points for integrating Chronicle into pipelines: scoring, verification, benchmark, eval harness, ML export, and RAG demos. Use these when you want to score defensibility, verify a .chronicle, or run a demo.

| Script / command | Purpose | How to run |
|------------------|---------|------------|
| **chronicle-verify** | Verify a .chronicle file (manifest, schema, evidence hashes). Stdlib only. | `chronicle-verify path/to/file.chronicle` (after `pip install -e .`) or `PYTHONPATH=. python3 -m tools.verify_chronicle path/to/file.chronicle` |
| **standalone_defensibility_scorer.py** | Defensibility scorer: read JSON from stdin, write metrics to stdout. Eval contract. | `PYTHONPATH=. python3 scripts/standalone_defensibility_scorer.py < input.json` or pipe from your harness. |
| **benchmark_data/run_defensibility_benchmark.py** | Run defensibility benchmark (fixed queries, RAG, record scores). | `PYTHONPATH=. python3 scripts/benchmark_data/run_defensibility_benchmark.py` (see [benchmark](../docs/benchmark.md)). |
| **eval_harness_adapter.py** | Adapt your eval harness output to the scorer (e.g. wrap responses for contract input). | `PYTHONPATH=. python3 scripts/eval_harness_adapter.py` (see script `--help` and [eval contract](../docs/eval_contract.md)). |
| **export_for_ml.py** | Export investigation data for ML/training. | `PYTHONPATH=. python3 scripts/export_for_ml.py` with `--path`, `--investigation`, etc. |
| **rag_path_demo.py** | Minimal RAG/agent path (ChronicleSession: project, investigation, ingest, claim, link). | `PYTHONPATH=. python3 scripts/rag_path_demo.py` |
| **haystack_rag_chronicle.py**, **langchain_rag_chronicle.py**, **llamaindex_rag_chronicle.py**, **cross_framework_rag_chronicle.py** | RAG + Chronicle demos (ingest, claim, link, score). | `PYTHONPATH=. python3 scripts/<script>.py` (see [integrating-with-chronicle](../docs/integrating-with-chronicle.md)). |
| **generate_sample_chronicle.py** | Generate the default Try sample .chronicle; delegates to verticals/journalism. | `PYTHONPATH=. python3 scripts/generate_sample_chronicle.py` |
| **run_conformance.py** | Conformance test on a .chronicle file. Exit 0 = conformant. Use `--json` for CI. | `PYTHONPATH=. python3 scripts/run_conformance.py path/to/file.chronicle` |
| **claim_evidence_graph_export.py** | Export claim–evidence graph as Mermaid or Graphviz. | `PYTHONPATH=. python3 scripts/claim_evidence_graph_export.py --path <project> --investigation <uid>` |

---

## Optional / advanced

Scripts and directories for scenario validation, per-vertical samples, benchmark data generation, adapters, and one-off ingestion or analysis. Use when you need samples, synthetic data, or to map external formats into Chronicle.

| Path | Purpose |
|------|---------|
| **ai_validation/** | Scenario validation (rule-based driver). Scenarios per vertical, scorer, run_all_verticals, trace/proposal for Learn. See [ai_validation/README.md](ai_validation/README.md). |
| **verticals/** | Per-vertical sample generators (e.g. Journalism `generate_sample.py`). See [verticals/README.md](verticals/README.md). |
| **benchmark_data/** | Benchmark sample generation: `generate_benchmark_samples.py`, `generate_vertical_corpora.py`, `synthetic_training_pipeline.py`, `evals_to_preference_pair.py`. First-class entry point: `run_defensibility_benchmark.py` (listed above). |
| **adapters/** | Map external formats to Chronicle: [example_rag_to_scorer](adapters/example_rag_to_scorer.py), [fact_checker_to_chronicle](adapters/fact_checker_to_chronicle.py), [provenance_to_chronicle](adapters/provenance_to_chronicle.py). See [adapters/README.md](adapters/README.md). |
| **synthetic_data/** | Generate realistic synthetic data: `generate_realistic_synthetic.py`. |
| **suggest_tensions_with_llm.py** | Use an LLM to suggest tensions between claims (optional tooling). |
| **add_lizzie_tensions.py** | One-off: add tensions for the Lizzie Borden sample. |
| **multi_run_investigation.py** | Multi-run investigation workflow (advanced). |
| **ingest_chronicle_to_aura.py** | Ingest a .chronicle into Neo4j Aura (optional Neo4j path). |
| **ingest_transcript_csv.py** | Ingest evidence from a transcript CSV into an investigation. |
| **compliance_report_from_rag.py** | Generate a compliance-style report from a RAG + Chronicle run. |

---

## Utilities (dev / maintenance)

Scripts for repo and doc maintenance. Not needed for normal eval or integration work.

| Script | Purpose |
|--------|---------|
| **normalize_quotes_in_docs.py** | Normalize Unicode/smart quotes to ASCII in docs (see .cursor/rules). |
| **update_doc_links_after_rename.py** | Update internal doc links after renaming files. |
| **check_doc_links.py** | Check that linked docs and anchors exist. |
| **generate_agent_tools.py** | Regenerate `docs/agent-tools.json` (API operations in function-calling format for agents). |

---

## Quick runs

```bash
# Regenerate the Journalism sample (frontend/public/sample.chronicle)
PYTHONPATH=. python3 scripts/generate_sample_chronicle.py

# Run all scenario validation scenarios (9 scenarios, 7 verticals)
PYTHONPATH=. python3 scripts/ai_validation/run_all_verticals.py

# Regenerate agent tools JSON
PYTHONPATH=. python3 scripts/generate_agent_tools.py
```

---

## Archived scripts

No scripts have been archived in this repo. Scripts that only served an old API/UI (e.g. `start_chronicle.sh`) were not added here or have been removed elsewhere. If we archive scripts in the future, we will list them in this section and note where they were moved (e.g. an `archived/` directory or a tag).

---

See [CONTRIBUTING.md](../CONTRIBUTING.md) for dev setup and checks; the main [README](../README.md) and [docs](../docs/) list the full doc index.
