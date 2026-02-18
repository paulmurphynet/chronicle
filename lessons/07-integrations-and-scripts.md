# Lesson 07: Integrations and scripts

**Objectives:** You’ll know where RAG and framework integrations live, what the main scripts do (benchmark, eval harness adapter, RAG demos, transcript ingest), and how they plug into the Chronicle session.

**Key files:**

- [chronicle/integrations/](../chronicle/integrations/) — LangChain, LlamaIndex, Haystack (when present)
- [scripts/README.md](../scripts/README.md) — script layout, **first-class scripts** table, and quick runs
- [scripts/adapters/](../scripts/adapters/) — RAG→scorer example, fact-checker→Chronicle, provenance→Chronicle
- [chronicle/api/app.py](../chronicle/api/app.py) — optional HTTP API (install `.[api]`)
- [scripts/standalone_defensibility_scorer.py](../scripts/standalone_defensibility_scorer.py) — already covered in Lesson 02
- [docs/eval-and-benchmarking.md](../docs/eval-and-benchmarking.md) — how to run pipelines and report defensibility
- [docs/api.md](../docs/api.md) — HTTP API config and endpoints
- [docs/rag-evals-defensibility-metric.md](../docs/rag-evals-defensibility-metric.md) — RAG evals: contract and scorer in your harness

---

## Integrations

The **chronicle/integrations/** directory (or package) is intended to hold **handlers** or **callbacks** so that RAG frameworks (LangChain, LlamaIndex, Haystack) can write evidence and claims into Chronicle during a run. For example:

- A **LangChain** callback might create an investigation, ingest retrieved documents as evidence, and when the chain produces an answer, propose it as a claim and link the retrieved chunks as support.
- The session API is the same; the integration just wires framework events (e.g. “on_retriever_end”, “on_llm_end”) to ChronicleSession methods.

If the repo has `chronicle/integrations/langchain.py` or similar, open it and see how it uses **create_investigation**, **ingest_evidence**, **propose_claim**, **link_support**. If the directory is empty or minimal, the pattern is still: **framework event → session method**. Demos may live in **scripts/** (e.g. `langchain_rag_chronicle.py`, `cross_framework_rag_chronicle.py`).

## First-class scripts

Open **scripts/README.md** and find the **“First-class scripts”** table. These are the main entry points for pipelines and interop:

- **chronicle quickstart-rag** — One-command RAG flow (temp project, investigation, ingest, claim, link, defensibility). See [docs/rag-in-5-minutes.md](../docs/rag-in-5-minutes.md).
- **chronicle-verify** — Verify a .chronicle file (manifest, schema, evidence hashes). Stdlib only.
- **standalone_defensibility_scorer.py** — One (query, answer, evidence) in → defensibility JSON out (Lesson 02).
- **benchmark_data/run_defensibility_benchmark.py** — Fixed queries, RAG path, defensibility per answer.
- **eval_harness_adapter.py** — Adapt a RAG run to the eval contract and record defensibility.
- **export_for_ml.py** — Export investigation data for ML/training.
- **rag_path_demo.py** — Minimal RAG path (session: ingest, claim, link).
- **\*_rag_chronicle.py** — LangChain, LlamaIndex, Haystack, cross-framework demos.

Use this table when you need to plug Chronicle into an eval harness, benchmark, or export pipeline.

## Adapters (scripts/adapters/)

Open **scripts/adapters/README.md**. Adapters map **external formats** into Chronicle (or into the scorer):

- **example_rag_to_scorer.py** — Copy-paste template: read JSON (query, answer, evidence) from stdin or file, call the scorer, print metrics. Use when your RAG harness outputs the eval contract shape.
- **fact_checker_to_chronicle.py** — Fact-checker output (claim + verdict + sources) → evidence items, propose_claim, support/challenge links. Expected JSON: `claim`, `verdict`, `sources` (with snippet, stance).
- **provenance_to_chronicle.py** — Provenance assertions (“this evidence from this source”) → register_source, ingest_evidence, link_evidence_to_source. We record; we don’t verify. Requires `--path` to a project.

These are **templates**: you can copy and adjust for your fact-checking or provenance pipeline. See [docs/provenance-recording.md](../docs/provenance-recording.md) and [docs/external-ids.md](../docs/external-ids.md).

## Optional HTTP API

If you install the **`[api]`** extra (`pip install -e ".[api]"`), you get a minimal HTTP API in **chronicle/api/app.py**. Run it with:

```bash
export CHRONICLE_PROJECT_PATH=/path/to/project
uvicorn chronicle.api.app:app --reload
```

It exposes **write** (investigations, evidence, claims, links, tensions), **read** (claim, defensibility, reasoning brief), and **export/import** (.chronicle). Response shapes match the eval contract and defensibility schema. No auth in this minimal version; see [docs/api.md](../docs/api.md). Useful for fact-checking or provenance UIs that call Chronicle over HTTP.

## Other scripts (layout)

Beyond the first-class list, **scripts/README.md** also describes:

- **generate_sample_chronicle.py** — Produces a sample .chronicle (verticals, e.g. journalism).
- **ingest_transcript_csv.py** — CSV → one evidence item + one span + one claim per row; exports .chronicle.
- **suggest_tensions_with_llm.py** — Suggests tensions (heuristic or Ollama LLM), optionally applies them.
- **ingest_chronicle_to_aura.py** — Verify → import .chronicle into a graph project → sync to Neo4j (Aura pipeline).

All of these use the **session** (or the verifier, or the Neo4j sync) under the hood.

## How scripts use the session

Typical pattern:

1. Create or open a project (`create_project` or open existing path).
2. **ChronicleSession(project_path)** — get a session.
3. **session.create_investigation(...)** then **session.ingest_evidence(...)**, **session.propose_claim(...)**, **session.link_support(...)** (and optionally **session.declare_tension(...)**).
4. **session.get_defensibility_score(claim_uid)** or **session.export_investigation(inv_uid, path)** or **chronicle neo4j-sync --path project**.

So scripts are **thin orchestration**; the engine is the store and commands.

## Try it

1. Run **chronicle quickstart-rag** from the repo root (with venv activated). Confirm you see defensibility output. See [docs/rag-in-5-minutes.md](../docs/rag-in-5-minutes.md) for options (`--path`, `--text`).
2. List the contents of **scripts/** and **scripts/adapters/**. Match the first-class scripts in **scripts/README.md** to their paths.
3. Open **scripts/adapters/example_rag_to_scorer.py** and see how it reads JSON and calls the scorer logic. Run it with a one-line JSON input (query, answer, evidence) from stdin.
4. (Optional) Install **`.[api]`**, set **CHRONICLE_PROJECT_PATH**, run **uvicorn chronicle.api.app:app**, and open **http://127.0.0.1:8000/docs** to try the API.
5. Open **scripts/ingest_transcript_csv.py** and find where it calls **session.ingest_evidence**, **session.propose_claim**, and **session.link_support**. Confirm it follows the same pattern as the scorer (without the temp project).

## Summary

- **First-class scripts and CLI** (scripts/README.md, CLI): **chronicle quickstart-rag** for a one-command RAG flow; scorer, verifier, benchmark, eval harness adapter, export_for_ml, RAG demos. Use them to plug Chronicle into pipelines.
- **Adapters** (scripts/adapters/): RAG→scorer example, fact-checker→Chronicle, provenance→Chronicle. Copy-paste templates for interop.
- **Optional HTTP API** (chronicle/api/, install `.[api]`): write/read/export over HTTP; same shapes as eval contract and defensibility schema.
- **Integrations** (chronicle/integrations/) wire RAG frameworks to ChronicleSession so that runs record evidence and claims.
- All rely on the same session API and event store; they differ only in input source and output (JSON, .chronicle, Neo4j).

**← Previous:** [Lesson 06: Defensibility metrics](06-defensibility-metrics.md) | **Index:** [Lessons](README.md) | **Next →:** [Lesson 08: The CLI](08-cli.md)

**Quiz:** [quizzes/quiz-07-integrations-and-scripts.md](quizzes/quiz-07-integrations-and-scripts.md)
