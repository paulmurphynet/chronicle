# Lesson 11: Interoperability, API, and tests

**Objectives:** You’ll know how Chronicle fits into the wider ecosystem: terminology for interop, external IDs, provenance recording, claim–evidence export shapes, the optional HTTP API, and how tests and CI keep the codebase stable.

**Key files:**

- [docs/glossary.md](../docs/glossary.md) — “Terminology for interop” (claim≈statement, support/challenge≈evidence for/against)
- [docs/verification-guarantees.md](../docs/verification-guarantees.md) — What the verifier and runtime guarantee; what they do not
- [docs/implementer-checklist.md](../docs/implementer-checklist.md) — Produce/consume .chronicle checklist
- [docs/rag-in-5-minutes.md](../docs/rag-in-5-minutes.md) — One-command RAG path (`chronicle quickstart-rag`) and next steps
- [docs/external-ids.md](../docs/external-ids.md) — Storing fact-check IDs, C2PA claim IDs in evidence metadata
- [docs/provenance-recording.md](../docs/provenance-recording.md) — We record source and evidence–source links; we don’t verify
- [docs/claim-evidence-metrics-export.md](../docs/claim-evidence-metrics-export.md) — Stable JSON shape for one claim + evidence refs + defensibility
- [docs/rag-evals-defensibility-metric.md](../docs/rag-evals-defensibility-metric.md) — RAG evals: contract, schema, running the scorer in your harness
- [docs/api.md](../docs/api.md) — Optional HTTP API: install, config, endpoints
- [chronicle/api/app.py](../chronicle/api/app.py) — FastAPI app (write/read/export)
- [tests/](../tests/) — test_standalone_scorer, test_session, test_verifier
- [.github/workflows/ci.yml](../.github/workflows/ci.yml) — CI: ruff + pytest

---

## Terminology for interop

Open **docs/glossary.md** and scroll to **“Terminology for interop”**. Chronicle uses specific terms; when you integrate with fact-checking tools, argumentation frameworks, or provenance systems, this table maps our vocabulary to common equivalents:

- **Claim** ≈ statement, assertion, verdict  
- **Support** ≈ evidence for, backs  
- **Challenge** ≈ evidence against, undermines  
- **Tension** ≈ contradiction (between two claims)  
- **Evidence (item)** ≈ source, document, chunk  
- **Defensibility** ≈ structural score given evidence and policy (not “truth”)

Export formats and adapters use Chronicle’s names; your adapter can map to local schemas using this table.

---

## External IDs and provenance

**External IDs (docs/external-ids.md):** When you need to correlate Chronicle entities with external systems (e.g. “this Chronicle claim = that fact-check verdict”):

- **Evidence:** Use the **metadata** dict at ingest. Store `fact_check_id`, `c2pa_assertion_id`, or similar. It’s persisted as `metadata_json` in the read model and in exports.
- **Claims:** The claim table has `notes` and `tags_json`; the API may expose them in a later release. Until then, keep a mapping (claim_uid → external_id) in your system or use a single note/tag convention.

**Provenance recording (docs/provenance-recording.md):** We can **store** source and evidence–source links. We **do not verify** C2PA, CR, or that evidence “really” came from a source. Provenance-aware pipelines can feed us assertions (e.g. “this blob from this source/model”); the **provenance adapter** (scripts/adapters/provenance_to_chronicle.py) is a template for that. Same idea for fact-checker output → Chronicle (scripts/adapters/fact_checker_to_chronicle.py).

---

## Claim–evidence–metrics and RAG evals

**Claim–evidence–metrics export (docs/claim-evidence-metrics-export.md):** Defines a stable JSON shape for “one claim + evidence refs + support/challenge counts + defensibility” so fact-checking UIs or dashboards can ingest it. You can build this from the generic export plus evidence_link and get_defensibility_score; the doc describes the schema and wrapper format.

**RAG evals (docs/rag-evals-defensibility-metric.md):** One page that ties everything together for RAG pipelines: the **contract** (input/output), the **schema**, and **how to run the scorer** in your harness (stdin, CLI flags, or in-process Python). Use it as the entry point for “Chronicle defensibility as a standard metric” in RAG evals.

---

## Optional HTTP API

**docs/api.md** and **chronicle/api/app.py** describe and implement the minimal HTTP API. Install with **`pip install -e ".[api]"`**, set **CHRONICLE_PROJECT_PATH**, and run **uvicorn chronicle.api.app:app**. Endpoints mirror the session: create investigation, ingest evidence (JSON or multipart file), propose claim, link support/challenge, declare tension, get claim, get defensibility, get reasoning brief, export/import .chronicle. Response shapes match the eval contract and defensibility schema. No auth in the minimal version; run behind your own auth or proxy in production.

Open **chronicle/api/app.py** and skim the route list and the **\_get_project_path()** logic (env, create project if missing). This is the same session API you’ve seen in lessons 05 and 07, exposed over HTTP.

---

## Tests and CI

**tests/** contains:

- **test_standalone_scorer.py** — Valid input → metrics; invalid input (bad JSON, missing query/answer/evidence, empty evidence) → error. Also tests main() exit code.
- **test_session.py** — Full flow: create project, create_investigation, ingest_evidence, anchor_span, propose_claim, link_support, get_defensibility_score. Plus “session requires existing project” (FileNotFoundError).
- **test_verifier.py** — Verify a .chronicle produced by session export (all checks pass); non-file path and wrong extension return failures.

Run tests: **`pytest tests/ -v`** (requires **`pip install -e ".[dev]"`**).

**CI (.github/workflows/ci.yml):** On push/PR to main (or master), we run **ruff check** and **ruff format** on chronicle and tools, and **pytest tests/** (with coverage) on Python 3.11 and 3.12. That keeps the scorer, session, and verifier covered and the core code style consistent.

---

## Try it

1. Read the **“Terminology for interop”** table in docs/glossary.md. Pick one row and explain it to yourself in a sentence.
2. Open **docs/external-ids.md** and find where evidence **metadata** is documented. Confirm that fact_check_id (or similar) can be stored there.
3. Open **tests/test_standalone_scorer.py** and run **pytest tests/test_standalone_scorer.py -v**. Confirm at least one “valid input” and one “invalid input” test pass.
4. (Optional) Install **`.[api]`**, set **CHRONICLE_PROJECT_PATH**, run **uvicorn chronicle.api.app:app**, and call **GET /health** and **POST /investigations** with a JSON body **{"title": "Test"}**.

---

## Summary

- **Terminology (glossary)** and **external IDs** (evidence metadata) help fact-checkers and provenance tools align with Chronicle.
- **Provenance recording** and **claim–evidence–metrics** docs describe what we store and what shape we can emit; **RAG evals** doc is the entry point for adding defensibility to your harness.
- **Optional HTTP API** (chronicle/api/, install `.[api]`) exposes write/read/export over HTTP with the same shapes as the eval contract.
- **Tests** (scorer, session, verifier) and **CI** (ruff + pytest) keep the core behavior and style stable.

**Quiz:** [quizzes/quiz-11-interoperability-api-and-tests.md](quizzes/quiz-11-interoperability-api-and-tests.md)
