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
| **start_chronicle.sh** | Convenience script to start the API (and optionally frontend). |

## Quick runs

```bash
# Regenerate the Journalism sample (frontend/public/sample.chronicle)
PYTHONPATH=. python3 scripts/generate_sample_chronicle.py

# Run all scenario validation scenarios (9 scenarios, 7 verticals)
PYTHONPATH=. python3 scripts/ai_validation/run_all_verticals.py

# Regenerate agent tools JSON
PYTHONPATH=. python3 scripts/generate_agent_tools.py
```

See [CONTRIBUTING.md](../CONTRIBUTING.md) for tests and checks; [docs/README.md](../docs/README.md) for the full doc index.
