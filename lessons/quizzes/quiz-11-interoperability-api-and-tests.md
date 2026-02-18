# Quiz 11: Interoperability, API, and tests

**Lesson:** [11-interoperability-api-and-tests.md](../11-interoperability-api-and-tests.md)

Answer these after reading the lesson and the linked docs. Try not to peek at the answer key until you've written your answers.

---

## Questions

1. In **docs/glossary.md**, what Chronicle term corresponds to “evidence against” or “undermines” in other systems?

2. Where can you store an **external ID** (e.g. fact-check ID) for an **evidence item** when ingesting? (Which parameter or field?)

3. Does Chronicle **verify** C2PA or CR provenance assertions, or only **record** what you give it?

4. What is the **entry point doc** for adding “Chronicle defensibility as a standard metric” to your RAG eval harness? (One doc name.)

5. How do you run the **optional HTTP API**? (Install step, env var, and command.)

6. Which **tests** cover (a) the standalone scorer, (b) the session flow (ingest → claim → link → defensibility), (c) the verifier on a .chronicle file?

7. What does **CI** run on push/PR? (Linter and test runner.)

---

## Answer key

1. **Challenge** — “Evidence against” / “undermines” is mapped to Chronicle’s **challenge** (link type from evidence span to claim).

2. The **metadata** dict at ingest (e.g. **session.ingest_evidence(..., metadata={"fact_check_id": "..."})**). It’s stored as **metadata_json** in the read model and in exports. See docs/external-ids.md.

3. We **record** only. We do not verify C2PA/CR or that evidence actually came from the stated source. See docs/provenance-recording.md.

4. **docs/rag-evals-defensibility-metric.md** — contract, schema, and how to run the scorer in your harness.

5. **Install:** `pip install -e ".[api]"`. **Env:** Set **CHRONICLE_PROJECT_PATH** to the project directory. **Command:** `uvicorn chronicle.api.app:app` (optionally `--reload`). See docs/api.md.

6. (a) **tests/test_standalone_scorer.py** — (b) **tests/test_session.py** — (c) **tests/test_verifier.py**.

7. **Ruff** (check + format) on chronicle and tools, and **pytest tests/** on Python 3.11 and 3.12. See .github/workflows/ci.yml.
