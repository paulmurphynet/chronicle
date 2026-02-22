# Quiz 07: Integrations and scripts

Lesson: [07-integrations-and-scripts.md](../07-integrations-and-scripts.md)

Answer these after reading the lesson and the scripts/README. Try not to peek at the answer key until you've written your answers.

---

## Questions

1. What is the purpose of the chronicle/integrations/ directory (or package)?

2. Which script adapts a single RAG run to the eval contract (e.g. LangChain run → defensibility metrics)?

3. Which script turns a CSV transcript (e.g. speaker + testimony columns) into a .chronicle with one evidence item and one claim per row?

4. Which script suggests tensions (heuristic or LLM) and can optionally apply them to the project?

5. What is the ingest_chronicle_to_aura script’s three-step pipeline? (In order.)

6. Where do the adapters (RAG→scorer, fact-checker→Chronicle, provenance→Chronicle) live, and what are they for?

7. How do you run the optional HTTP API? (Install extra, env var, command.)

8. Which adapter scripts are intended for production onboarding when your harness rows are JSONL and may use nested fields?

9. For the Lizzie inquest transcript benchmark, what is the correct project framing and one explicit non-goal?

10. Which script validates the hardened interoperability export/import contract across JSON, CSV ZIP, Markdown reasoning brief, `.chronicle`, and signed bundle flows?

11. Which command starts Chronicle’s MCP server, and what optional dependency extra must be installed first?

12. You have RAGAS-style rows with keys `question`, `answer`, and `contexts`. Which Chronicle adapter is the direct batch path?

---

## Answer key

1. To hold handlers/callbacks that wire RAG frameworks (LangChain, LlamaIndex, Haystack) to Chronicle—so that when a framework runs (retrieve + generate), evidence and claims are written to Chronicle via the session API.

2. scripts/eval_harness_adapter.py (or equivalent—adapts a RAG run to the eval contract and records defensibility per run).

3. **scripts/ingest_transcript_csv.py** — reads CSV, creates investigation, for each row: ingest evidence, anchor span, propose claim (e.g. "Speaker: text"), link_support; exports .chronicle.

4. **scripts/suggest_tensions_with_llm.py** — uses heuristic or LLM to suggest tensions; with --apply it declares them in the project via session.declare_tension.

5. Verify the .chronicle file → Import it into the graph project (merge events + evidence) → Sync the project to Neo4j (Aura). So: verify → import → sync.

6. **scripts/adapters/** — example_rag_to_scorer.py (RAG harness output → scorer), fact_checker_to_chronicle.py (fact-checker output → evidence + claim + support/challenge), provenance_to_chronicle.py (provenance assertions → sources + evidence–source links). They are copy-paste templates for interop with external systems.

7. Install: `pip install -e ".[api]"`. Env: Set CHRONICLE_PROJECT_PATH to the project directory. Command: `uvicorn chronicle.api.app:app` (optionally `--reload`). See docs/api.md.

8. Use `scripts/adapters/starter_batch_to_scorer.py` (supports mapping profiles for nested paths) and `scripts/adapters/validate_adapter_outputs.py`. You can validate shipped examples with `scripts/adapters/check_examples.py`.

9. Frame it as an evidence-quality and trust-evaluation benchmark (claim-evidence linkage, support/challenge, temporal consistency), grounded in a bounded transcript corpus. An explicit non-goal is sensational retelling or claiming Chronicle establishes legal truth.

10. `scripts/check_integration_export_contracts.py`.

11. Command: `chronicle-mcp --project-path /path/to/project` (or with transport flags). Install extra: `pip install -e ".[mcp]"` (or package install with `[mcp]`).

12. `scripts/adapters/ragas_batch_to_chronicle.py`.

---

← Previous: [quiz-06-defensibility-metrics](quiz-06-defensibility-metrics.md) | Index: [Quizzes](README.md) | Next →: [quiz-08-cli](quiz-08-cli.md)
