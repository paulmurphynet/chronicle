# Lesson 07: Integrations and scripts

**Objectives:** You’ll know where RAG and framework integrations live, what the main scripts do (benchmark, eval harness adapter, RAG demos, transcript ingest), and how they plug into the Chronicle session.

**Key files:**

- [chronicle/integrations/](../chronicle/integrations/) — LangChain, LlamaIndex, Haystack (when present)
- [scripts/README.md](../scripts/README.md) — script layout and quick runs
- [scripts/standalone_defensibility_scorer.py](../scripts/standalone_defensibility_scorer.py) — already covered in Lesson 02
- [docs/eval-and-benchmarking.md](../docs/eval-and-benchmarking.md) — how to run pipelines and report defensibility

---

## Integrations

The **chronicle/integrations/** directory (or package) is intended to hold **handlers** or **callbacks** so that RAG frameworks (LangChain, LlamaIndex, Haystack) can write evidence and claims into Chronicle during a run. For example:

- A **LangChain** callback might create an investigation, ingest retrieved documents as evidence, and when the chain produces an answer, propose it as a claim and link the retrieved chunks as support.
- The session API is the same; the integration just wires framework events (e.g. “on_retriever_end”, “on_llm_end”) to ChronicleSession methods.

If the repo has `chronicle/integrations/langchain.py` or similar, open it and see how it uses **create_investigation**, **ingest_evidence**, **propose_claim**, **link_support**. If the directory is empty or minimal, the pattern is still: **framework event → session method**. Demos may live in **scripts/** (e.g. `langchain_rag_chronicle.py`, `cross_framework_rag_chronicle.py`).

## Scripts layout

Open **scripts/README.md**.

- **standalone_defensibility_scorer.py** — One (query, answer, evidence) in → defensibility JSON out. No framework required (Lesson 02).
- **benchmark_data/run_defensibility_benchmark.py** — Runs a fixed set of queries through a Chronicle-backed path and outputs defensibility per answer (for benchmarking).
- **eval_harness_adapter.py** — Adapts a single RAG run (e.g. LangChain) to the eval contract: run the pipeline, get the claim_uid for the answer, call **defensibility_metrics_for_claim(session, claim_uid)**, record the result.
- **generate_sample_chronicle.py** — Produces a sample .chronicle (e.g. for the verifier or frontend). Delegates to verticals (e.g. journalism).
- **ingest_transcript_csv.py** — CSV → one evidence item + one span + one claim per row; exports .chronicle. Used for transcripts (e.g. Lizzie Borden inquest).
- **suggest_tensions_with_llm.py** — Suggests tensions (heuristic or Ollama LLM) and optionally applies them to the project.
- **ingest_chronicle_to_aura.py** — Verify → import .chronicle into a graph project → sync to Neo4j (Aura pipeline).

All of these use the **session** (or the verifier, or the Neo4j sync) under the hood. They are entry points for different workflows: eval, benchmarking, sample data, transcript ingestion, tension suggestion, graph sync.

## How scripts use the session

Typical pattern:

1. Create or open a project (`create_project` or open existing path).
2. **ChronicleSession(project_path)** — get a session.
3. **session.create_investigation(...)** then **session.ingest_evidence(...)**, **session.propose_claim(...)**, **session.link_support(...)** (and optionally **session.declare_tension(...)**).
4. **session.get_defensibility_score(claim_uid)** or **session.export_investigation(inv_uid, path)** or **chronicle neo4j-sync --path project**.

So scripts are **thin orchestration**; the engine is the store and commands.

## Try it

1. List the contents of **scripts/** and **chronicle/integrations/** (if present). Match a few script names to the descriptions in **scripts/README.md**.
2. Open **scripts/ingest_transcript_csv.py** and find where it calls **session.ingest_evidence**, **session.propose_claim**, and **session.link_support**. Confirm it follows the same pattern as the scorer (without the temp project).

## Summary

- **Integrations** (chronicle/integrations/) wire RAG frameworks to ChronicleSession so that runs record evidence and claims.
- **Scripts** provide entry points: scorer, benchmark runner, eval harness adapter, sample generator, transcript ingest, tension suggestion, Aura ingest/sync.
- All rely on the same session API and event store; they differ only in input source and output (JSON, .chronicle, Neo4j).

**Quiz:** [quizzes/quiz-07-integrations-and-scripts.md](quizzes/quiz-07-integrations-and-scripts.md)
