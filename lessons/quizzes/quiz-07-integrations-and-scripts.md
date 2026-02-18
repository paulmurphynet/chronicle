# Quiz 07: Integrations and scripts

**Lesson:** [07-integrations-and-scripts.md](../07-integrations-and-scripts.md)

Answer these after reading the lesson and the scripts/README. Try not to peek at the answer key until you've written your answers.

---

## Questions

1. What is the **purpose** of the **chronicle/integrations/** directory (or package)?

2. Which script **adapts a single RAG run** to the eval contract (e.g. LangChain run → defensibility metrics)?

3. Which script turns a **CSV transcript** (e.g. speaker + testimony columns) into a .chronicle with one evidence item and one claim per row?

4. Which script suggests **tensions** (heuristic or LLM) and can optionally **apply** them to the project?

5. What is the **ingest_chronicle_to_aura** script’s three-step pipeline? (In order.)

6. Where do the **adapters** (RAG→scorer, fact-checker→Chronicle, provenance→Chronicle) live, and what are they for?

7. How do you run the **optional HTTP API**? (Install extra, env var, command.)

---

## Answer key

1. To hold **handlers/callbacks** that wire RAG frameworks (LangChain, LlamaIndex, Haystack) to Chronicle—so that when a framework runs (retrieve + generate), evidence and claims are written to Chronicle via the session API.

2. **scripts/eval_harness_adapter.py** (or equivalent—adapts a RAG run to the eval contract and records defensibility per run).

3. **scripts/ingest_transcript_csv.py** — reads CSV, creates investigation, for each row: ingest evidence, anchor span, propose claim (e.g. "Speaker: text"), link_support; exports .chronicle.

4. **scripts/suggest_tensions_with_llm.py** — uses heuristic or LLM to suggest tensions; with **--apply** it declares them in the project via session.declare_tension.

5. **Verify** the .chronicle file → **Import** it into the graph project (merge events + evidence) → **Sync** the project to Neo4j (Aura). So: verify → import → sync.

6. **scripts/adapters/** — example_rag_to_scorer.py (RAG harness output → scorer), fact_checker_to_chronicle.py (fact-checker output → evidence + claim + support/challenge), provenance_to_chronicle.py (provenance assertions → sources + evidence–source links). They are **copy-paste templates** for interop with external systems.

7. **Install:** `pip install -e ".[api]"`. **Env:** Set **CHRONICLE_PROJECT_PATH** to the project directory. **Command:** `uvicorn chronicle.api.app:app` (optionally `--reload`). See docs/api.md.
