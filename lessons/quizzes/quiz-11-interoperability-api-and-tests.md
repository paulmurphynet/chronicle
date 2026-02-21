# Quiz 11: Interoperability, API, and tests

Lesson: [11-interoperability-api-and-tests.md](../11-interoperability-api-and-tests.md)

Answer these after reading the lesson and the linked docs. Try not to peek at the answer key until you've written your answers.

---

## Questions

1. In docs/glossary.md, what Chronicle term corresponds to “evidence against” or “undermines” in other systems?

2. Where can you store an external ID (e.g. fact-check ID) for an evidence item when ingesting? (Which parameter or field?)

3. Does Chronicle verify C2PA or CR provenance assertions, or only record what you give it?

4. What is the entry point doc for adding Chronicle defensibility to your RAG eval harness? (One doc name.)

5. How do you run the optional HTTP API? (Install step, env var, and command.)

6. Which tests cover (a) the standalone scorer, (b) the session flow (ingest → claim → link → defensibility), (c) the verifier on a .chronicle file?

7. What does CI run, and what are the current triggers/events?

8. How does the API record who made a write request (e.g. who created an investigation)? What headers can a client send?

9. Where is the minimal curation UI served when the API is running? What does it let you do?

10. What is the Reference UI and where does it live? What does Try sample do?

11. How do you confirm a tension suggestion in the API (turn it into a real tension)? Is there a separate “confirm” endpoint?

12. Which script generates a machine-readable report for branch-protection rollout and required CI job evidence?

---

## Answer key

1. **Challenge** — “Evidence against” / “undermines” is mapped to Chronicle’s challenge (link type from evidence span to claim).

2. The metadata dict at ingest (e.g. session.ingest_evidence(..., metadata={"fact_check_id": "..."})). It’s stored as metadata_json in the read model and in exports. See docs/external-ids.md.

3. We record only. We do not verify C2PA/CR or that evidence actually came from the stated source. See docs/provenance-recording.md.

4. **docs/rag-evals-defensibility-metric.md** — contract, schema, and how to run the scorer in your harness.

5. Install: `pip install -e ".[api]"`. Env: Set CHRONICLE_PROJECT_PATH to the project directory. Command: `uvicorn chronicle.api.app:app` (optionally `--reload`). See docs/api.md.

6. (a) tests/test_standalone_scorer.py — (b) tests/test_session.py — (c) tests/test_verifier.py. Also test_attestation.py (payload helper), test_identity.py (identity module), test_cli_actor.py (CLI actor identity).

7. CI runs on push, pull_request, and workflow_dispatch. It includes core lint/tests/docs/parity checks, frontend route/lint/test/build checks, and Postgres doctor/smoke/parity/onboarding checks.

8. The API resolves the actor from an Identity Provider (IdP) when configured, or from request headers: X-Actor-Id and X-Actor-Type. Clients can send those headers so the ledger records them as the actor. Default is `actor_id=default`, `actor_type=human`. See docs/api.md and chronicle/core/identity.py.

9. /static/curation.html (e.g. http://127.0.0.1:8000/static/curation.html). It lets you set your Actor ID, create investigations, ingest evidence (paste text), propose claims, and link support—all writes are attributed to you via X-Actor-Id. See docs/human-in-the-loop-and-attestation.md.

10. The Reference UI is the official human-in-the-loop frontend that talks only to the Chronicle HTTP API; it lives in frontend/ in this repo (React + Vite + TypeScript). Try sample creates a minimal investigation (one evidence, one claim, one support link) via the API and opens it so you can see defensibility and export. See frontend/README.md and docs/reference-ui-plan.md.

11. You confirm by declaring the tension: POST declare_tension with the same claim_a_uid and claim_b_uid. The backend then marks the matching suggestion as confirmed. There is no separate “confirm” endpoint; dismiss is the only dedicated tension-suggestion endpoint (POST …/tension-suggestions/{id}/dismiss).

12. `scripts/check_branch_protection_rollout.py`.

---

← Previous: [quiz-10-export-import-neo4j](quiz-10-export-import-neo4j.md) | Index: [Quizzes](README.md) | Next →: [quiz-12-chronicle-file-format-and-schema](quiz-12-chronicle-file-format-and-schema.md)
