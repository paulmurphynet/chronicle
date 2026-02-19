# Quiz 01: Codebase map

**Lesson:** [01-codebase-map.md](../01-codebase-map.md)

Answer these after reading the lesson and looking at the repo layout. Try not to peek at the answer key until you’ve written your answers.

---

## Questions

1. What are the **two main entry points** a user runs for scoring and verification? (Give the script/tool path or name for each.)

2. Where does the **defensibility metrics** structure (the shape of the scorer output) get defined? (Name the doc or file.)

3. Which folder contains the **event model** and core types (payloads, UIDs, validation)?

4. What is the **eval contract**? (One sentence.)

5. Where do the **RAG integration hooks** (e.g. LangChain, LlamaIndex) live in the repo?

6. Where do **pytest tests** for the scorer, session, and verifier live? What does **CI** run when the workflow is triggered?

7. Where is the **optional HTTP API** implemented, and how do you install it?

8. Where does **actor identity** and **verification level** (for human-in-the-loop and attestation) live in the codebase? Which doc describes the full workflow?

9. Where does the **Reference UI** (human-in-the-loop frontend) live in the repo?

---

## Answer key

1. **Scorer:** `scripts/standalone_defensibility_scorer.py`. **Verifier:** `chronicle-verify` CLI (implementation in `tools/verify_chronicle/`).

2. The defensibility metrics shape is defined in **`docs/defensibility-metrics-schema.md`** and used by the scorer to match the eval contract; the code that builds it is in **`chronicle/eval_metrics.py`**.

3. **`chronicle/core/`** — events, payloads, UIDs, validation, policy.

4. The **eval contract** is the agreed input (query, answer, evidence) and output (defensibility metrics or error) for the defensibility scorer so that eval harnesses can plug in without depending on implementation details. Defined in `docs/eval_contract.md`.

5. **`chronicle/integrations/`** — e.g. LangChain, LlamaIndex, Haystack.

6. **`tests/`** — e.g. test_standalone_scorer.py, test_session.py, test_verifier.py. **CI** (`.github/workflows/ci.yml`) runs **ruff** (check + format) on chronicle and tools, and **pytest tests/** on Python 3.11 and 3.12 when the workflow is run (currently manual `workflow_dispatch`).

7. **`chronicle/api/app.py`** (FastAPI app). Install with **`pip install -e ".[api]"`**; then set `CHRONICLE_PROJECT_PATH` and run `uvicorn chronicle.api.app:app`. See docs/api.md.

8. **`chronicle/core/identity.py`** — IdP abstraction, get_effective_actor_from_request; **`chronicle/store/commands/attestation.py`** — payload helpers for _verification_level / _attestation_ref. The full workflow (CLI env, API headers, curation UI) is in **docs/human-in-the-loop-and-attestation.md**.

9. **`frontend/`** — React + Vite + TypeScript app; API-only client for Try sample, investigations, evidence/claims/links, defensibility, export, Learn guides. See frontend/README.md.

---

**Index:** [Quizzes](README.md) | **Next →:** [quiz-02-the-scorer](quiz-02-the-scorer.md)
