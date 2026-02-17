# Lesson 01: Codebase map

**Objectives:** You’ll know where the main parts of Chronicle live: scorer, verifier, core package, store, integrations, and docs.

**Key files:**

- [README.md](../README.md) — repo overview and quick start  
- [chronicle/](../chronicle/) — main Python package  
- [scripts/standalone_defensibility_scorer.py](../scripts/standalone_defensibility_scorer.py) — the scorer entry point  
- [tools/verify_chronicle/](../tools/verify_chronicle/) — the verifier  
- [docs/](../docs/) — contracts, schemas, and technical docs  

---

## What Chronicle does in one sentence

Chronicle takes a **query**, an **answer**, and **evidence** (e.g. retrieved chunks), and produces **defensibility metrics** so you can see how well the answer is supported—and it can package that into a **.chronicle** file that anyone can **verify** without running our full stack.

## Top-level layout

Open the repo root and look at the main folders:

| Path | What it is |
|------|------------|
| **`chronicle/`** | The main Python package: events, store, session, defensibility, integrations. This is the “engine.” |
| **`scripts/`** | Runnable scripts: the **standalone defensibility scorer**, benchmark runner, RAG demos, utilities. |
| **`tools/`** | Standalone tooling. The important one is **`verify_chronicle/`** — the .chronicle verifier (stdlib only). |
| **`docs/`** | Eval contract, technical report, verifier doc, Neo4j, migration, plan, to-do. |
| **`neo4j/`** | Optional: Cypher scripts to rebuild a graph from Chronicle data (for analysis/visualization). |
| **`lessons/`** | These lessons. **`lessons/quizzes/`** holds the quizzes. |
| **`guidebook/`** | The narrative guide (problem, solution, how to help)—for everyone, not only engineers. |

The **entry points** you’ll use most are:

1. **Scorer:** `scripts/standalone_defensibility_scorer.py` (or call the same logic from your own code).  
2. **Verifier:** `chronicle-verify` CLI (installed with the package), implemented in `tools/verify_chronicle/`.

## Inside `chronicle/` (the package)

This is the core. High-level structure:

| Path | Role |
|------|------|
| **`chronicle/core/`** | Event model, payloads, UIDs, validation, policy. The “language” of what we record. |
| **`chronicle/store/`** | Event store, read model (projection, models, sqlite_read_model), session API, commands (claims, evidence, defensibility, etc.). |
| **`chronicle/store/commands/`** | Command handlers: investigation, evidence, claims, tensions, defensibility, export, and more. |
| **`chronicle/eval_metrics.py`** | Builds the **defensibility metrics** structure (the shape the scorer returns). |
| **`chronicle/integrations/`** | LangChain, LlamaIndex, Haystack hooks so RAG pipelines can use Chronicle. |
| **`chronicle/tools/`** | Epistemic tools: decomposer, contradiction detection, type/scope inference, embeddings (optional LLM). |
| **`chronicle/cli/`** | CLI: project init, neo4j-export, neo4j-sync, and other project/claim/evidence commands. |
| **`chronicle/verify.py`** | Project invariant suite (run via `chronicle verify`). |
| **`tools/verify_chronicle/`** | Standalone .chronicle file verifier (run via `chronicle-verify` or `chronicle verify-chronicle`). |

When you run the **standalone scorer**, it uses: `create_project`, session, ingest evidence, propose claim, link support, then **get defensibility** and serialize it to the eval contract shape. All of that lives under `chronicle/`.

## Scripts you’ll see in lessons

- **`standalone_defensibility_scorer.py`** — The main scorer: JSON in (query, answer, evidence) → defensibility JSON out. Implements the [eval contract](../docs/eval_contract.md).  
- **`run_defensibility_benchmark.py`** (in `scripts/benchmark_data/`) — Runs the scorer over many cases for benchmarking.  
- **`eval_harness_adapter.py`** — Adapts a single RAG run to the eval contract (LangChain + Chronicle).  
- **`*_rag_chronicle.py`** — Demos: LangChain, LlamaIndex, Haystack, cross-framework.

## Docs that define behavior

- **`docs/eval_contract.md`** — Input/output for the scorer; what harnesses rely on.  
- **`docs/eval_contract_schema.json`** — JSON Schema for that contract.  
- **`docs/defensibility-metrics-schema.md`** — Meaning of each field in the scorer output.  
- **`docs/verifier.md`** — What the verifier checks and how to use it.  
- **`docs/technical-report.md`** — Defensibility definition and schema (citable).

## Try it

1. From repo root, list the package:  
   `ls chronicle/`  
   You should see `core/`, `store/`, `cli/`, `integrations/`, `tools/`, `eval_metrics.py`, `verify.py`, etc.

2. List the scorer and verifier:  
   `ls scripts/standalone_defensibility_scorer.py tools/verify_chronicle/`

3. Skim the repo [README.md](../README.md) and the “What’s in this repo” and “Docs” sections so the map above matches what you see.

## Summary

- **Scorer:** `scripts/standalone_defensibility_scorer.py`; **verifier:** `tools/verify_chronicle/` (and `chronicle-verify` CLI).  
- **Engine:** `chronicle/` — core (events), store (session, commands), eval_metrics, integrations, tools, CLI.  
- **Contracts and semantics:** `docs/eval_contract.md`, defensibility-metrics-schema, technical-report, verifier.

**Quiz:** [quizzes/quiz-01-codebase-map.md](quizzes/quiz-01-codebase-map.md)
