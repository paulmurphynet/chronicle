# Scripts

Scripts and data used for scenario validation, sample generation, benchmark data, and doc/link utilities. Run from repo root with `PYTHONPATH=.` when a script imports `chronicle` or `tools` (e.g. `PYTHONPATH=. python3 scripts/generate_sample_chronicle.py`).

## Layout

| Path | Purpose |
|------|---------|
| **ai_validation/** | Scenario validation (rule-based driver, no AI/LLM). Scenarios per vertical, scorer, run_all_verticals, trace/proposal for Learn. See [ai_validation/README.md](ai_validation/README.md). |
| **verticals/** | Per-vertical sample generators (e.g. Journalism `generate_sample.py` → `frontend/public/sample.chronicle`). See [verticals/README.md](verticals/README.md). |
| **benchmark_data/** | Benchmark sample generation (`generate_benchmark_samples.py` for docs/benchmark/sample_investigations); fixed-query defensibility run (`run_defensibility_benchmark.py` runs RAG, records defensibility per answer). |
| **claim_evidence_graph_export.py** | Export claim–evidence graph as Mermaid or Graphviz (E.3). `--path`, `--investigation`; optional `--claim`, `--format mermaid|dot`. |
| **generate_sample_chronicle.py** | Entry point to generate the default Try sample; delegates to `verticals/journalism/generate_sample.py`. |
| **generate_agent_tools.py** | Generate `docs/agent-tools.json` (API operations in function-calling format for agents). |
| **run_conformance.py** | Run conformance test on a .chronicle file (T4.4). Exit 0 = conformant. Use `--json` for CI. |
| **rag_path_demo.py** | Demo: minimal RAG/agent path (project, investigation, ingest, claim, link) using ChronicleSession. |
| **normalize_quotes_in_docs.py** | Normalize Unicode/smart quotes to ASCII in docs (see .cursor/rules). |
| **update_doc_links_after_rename.py** | Update internal doc links after renaming files. |

## First-class scripts (eval, verification, export, RAG)

These are the main entry points for integrating Chronicle into pipelines (scoring, verification, benchmark, eval harness, ML export, RAG demos). Run from repo root with `PYTHONPATH=.` when needed.

| Script / command | Purpose | How to run |
|------------------|---------|------------|
| **chronicle-verify** | Verify a .chronicle file (manifest, schema, evidence hashes). Stdlib only. | `chronicle-verify path/to/file.chronicle` (after `pip install -e .`) or `PYTHONPATH=. python3 -m tools.verify_chronicle path/to/file.chronicle` |
| **standalone_defensibility_scorer.py** | Defensibility scorer: read JSON from stdin, write metrics to stdout. Eval contract. | `PYTHONPATH=. python3 scripts/standalone_defensibility_scorer.py < input.json` or pipe from your harness. |
| **benchmark_data/run_defensibility_benchmark.py** | Run defensibility benchmark (fixed queries, RAG, record scores). | `PYTHONPATH=. python3 scripts/benchmark_data/run_defensibility_benchmark.py` (see [benchmark](docs/benchmark.md)). |
| **eval_harness_adapter.py** | Adapt your eval harness output to the scorer (e.g. wrap responses for contract input). | `PYTHONPATH=. python3 scripts/eval_harness_adapter.py` (see script `--help` and [eval contract](docs/eval_contract.md)). |
| **export_for_ml.py** | Export investigation data for ML/training (see export doc). | `PYTHONPATH=. python3 scripts/export_for_ml.py` with `--path`, `--investigation`, etc. |
| **rag_path_demo.py** | Minimal RAG/agent path (ChronicleSession: project, investigation, ingest, claim, link). | `PYTHONPATH=. python3 scripts/rag_path_demo.py` |
| **haystack_rag_chronicle.py**, **langchain_rag_chronicle.py**, **llamaindex_rag_chronicle.py**, **cross_framework_rag_chronicle.py** | RAG + Chronicle demos (ingest, claim, link, score). | `PYTHONPATH=. python3 scripts/<script>.py` (see [integrating-with-chronicle](docs/integrating-with-chronicle.md)). |

## Quick runs

```bash
# Regenerate the Journalism sample (frontend/public/sample.chronicle)
PYTHONPATH=. python3 scripts/generate_sample_chronicle.py

# Run all scenario validation scenarios (9 scenarios, 7 verticals)
PYTHONPATH=. python3 scripts/ai_validation/run_all_verticals.py

# Regenerate agent tools JSON
PYTHONPATH=. python3 scripts/generate_agent_tools.py
```

See [CONTRIBUTING.md](../CONTRIBUTING.md) for dev setup and checks; the main [README](../README.md) and [docs](docs/) list the full doc index.
