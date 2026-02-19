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
- [docs/api.md](../docs/api.md) — Optional HTTP API: install, config, endpoints, request identity
- [docs/human-in-the-loop-and-attestation.md](../docs/human-in-the-loop-and-attestation.md) — Human curation, actor identity, verification level, curation UI
- [chronicle/api/app.py](../chronicle/api/app.py) — FastAPI app (write/read/export, tier, evidence/claims/tensions lists, spans, tension suggestions, submission package)
- [chronicle/core/identity.py](../chronicle/core/identity.py) — IdP abstraction, get_effective_actor_from_request
- [frontend/](../frontend/) — Reference UI (React + Vite): Try sample, investigations, evidence/claims/links, defensibility, tensions, suggestions, export, Learn guides; [frontend/README.md](../frontend/README.md), [frontend/public/guides.json](../frontend/public/guides.json)
- [tests/](../tests/) — test_standalone_scorer, test_session, test_verifier, test_attestation, test_identity, test_cli_actor
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
- **Claims:** The claim table has `notes` and `tags_json`; the API exposes them in **GET /claims/{claim_uid}** and **GET /investigations/{id}/claims** so you can correlate claim_uid with external IDs (e.g. fact_check_id) without a separate mapping.

**Provenance recording (docs/provenance-recording.md):** We can **store** source and evidence–source links. We **do not verify** C2PA, CR, or that evidence “really” came from a source. Provenance-aware pipelines can feed us assertions (e.g. “this blob from this source/model”); the **provenance adapter** (scripts/adapters/provenance_to_chronicle.py) is a template for that. Same idea for fact-checker output → Chronicle (scripts/adapters/fact_checker_to_chronicle.py).

---

## Claim–evidence–metrics and RAG evals

**Claim–evidence–metrics export (docs/claim-evidence-metrics-export.md):** Defines a stable JSON shape for “one claim + evidence refs + support/challenge counts + defensibility” so fact-checking UIs or dashboards can ingest it. Use **build_claim_evidence_metrics_export** (chronicle.store.commands.generic_export) with the read model and a defensibility getter (e.g. session.get_defensibility_score) to get the full wrapper; the doc describes the schema.

**RAG evals (docs/rag-evals-defensibility-metric.md):** One page that ties everything together for RAG pipelines: the **contract** (input/output), the **schema**, and **how to run the scorer** in your harness (stdin, CLI flags, or in-process Python). Use it as the entry point for adding Chronicle defensibility to RAG evals.

---

## Optional HTTP API

**docs/api.md** and **chronicle/api/app.py** describe and implement the minimal HTTP API. Install with **`pip install -e ".[api]"`**, set **CHRONICLE_PROJECT_PATH**, and run **uvicorn chronicle.api.app:app**. Endpoints mirror the session: create investigation, ingest evidence (JSON or multipart file), propose claim, link support/challenge, declare tension, get claim, get defensibility, get reasoning brief, export/import .chronicle. **Additional endpoints** support the Reference UI: **GET** `/investigations/{id}`, `/investigations/{id}/tier-history`, `/investigations/{id}/evidence`, `/investigations/{id}/claims`, `/investigations/{id}/tensions`, `/investigations/{id}/tension-suggestions`, **GET** `/evidence/{evidence_uid}/spans`, **POST** `/investigations/{id}/tier`, **POST** `/investigations/{id}/tension-suggestions/{suggestion_uid}/dismiss`, **POST** `/investigations/{id}/submission-package`. There is no separate “confirm” endpoint for a tension suggestion: **confirming** is done by **declaring the tension** (POST declare_tension with the same claim_a_uid and claim_b_uid); the backend then marks that suggestion as confirmed. The API also supports **tier** (POST …/tier, GET …/tier-history) for **friction tiers** (spark → forge → vault), which gate workspace actions (e.g. export, publication) per policy. Response shapes match the eval contract and defensibility schema. No auth in the minimal version; run behind your own auth or proxy in production.

Open **chronicle/api/app.py** and skim the route list and the **\_get_project_path()** logic (env, create project if missing). This is the same session API you’ve seen in lessons 05 and 07, exposed over HTTP.

### Request identity and attestation

Every **write** request records an **actor** (who did it). The API resolves the actor from:

1. **Identity Provider (IdP)** — When configured (e.g. `CHRONICLE_IDENTITY_PROVIDER=traditional`), the server can use the authenticated principal and optionally a **verification level** (e.g. `verified_credential`). See **chronicle/core/identity.py** and **get_effective_actor_from_request**.
2. **Headers** — When no IdP binding is present, the server reads **X-Actor-Id** and **X-Actor-Type** (e.g. `X-Actor-Id: jane_doe`, `X-Actor-Type: human`).
3. **Default** — If neither is set, the server uses `actor_id=default`, `actor_type=human`.

When the IdP (or headers) provide a verification level, the API stores it in the event payload as **\_verification_level** (and optionally **\_attestation_ref**). That way “attested with verified credential” is queryable. See [docs/human-in-the-loop-and-attestation.md](../docs/human-in-the-loop-and-attestation.md) and [docs/api.md#request-identity-and-attestation](../docs/api.md).

### Reference UI (frontend/)

The **Reference UI** lives in **frontend/** in this repo: a React + Vite + TypeScript app that talks only to the HTTP API (no private backend). Run it from **frontend/** with **`npm install`** then **`npm run dev`** (default http://localhost:5173). It provides: **Home** with **Try sample** (creates a minimal investigation: one evidence, one claim, one support link, then opens the investigation); **Investigations** list and **Investigation detail** (overview, tier + tier history, evidence, claims, links, defensibility, tensions, tension suggestions—confirm by declaring the tension, dismiss via the dismiss endpoint—export .chronicle and submission package); **Learn** (step-by-step guides per vertical: journalism, legal, compliance) from **frontend/public/guides.json**. See [docs/reference-ui-plan.md](../docs/reference-ui-plan.md) and [frontend/README.md](../frontend/README.md). The API can also be used with the **minimal curation UI** at **/static/curation.html** (e.g. `http://127.0.0.1:8000/static/curation.html`) for quick actor-attributed writes.

---

## Tests and CI

**tests/** contains:

- **test_standalone_scorer.py** — Valid input → metrics; invalid input (bad JSON, missing query/answer/evidence, empty evidence) → error. Also tests main() exit code.
- **test_session.py** — Full flow: create project, create_investigation, ingest_evidence, anchor_span, propose_claim, link_support, get_defensibility_score. Plus “session requires existing project” (FileNotFoundError) and verification_level/attestation_ref persisted in payload.
- **test_verifier.py** — Verify a .chronicle produced by session export (all checks pass); non-file path and wrong extension return failures.
- **test_attestation.py** — Attestation payload helper: _verification_level and _attestation_ref applied to payloads.
- **test_identity.py** — Identity module: NoneIdP, get_effective_actor_from_request (headers, default), get_identity_provider.
- **test_cli_actor.py** — CLI actor identity: _actor_from_args (args, env, default), create-investigation with --actor-id records actor on event.

Run tests: **`pytest tests/ -v`** (requires **`pip install -e ".[dev]"`**).

**CI (.github/workflows/ci.yml):** The workflow runs **ruff check** and **ruff format** on chronicle and tools, and **pytest tests/** (with coverage) on Python 3.11 and 3.12. Currently it is triggered manually via **workflow_dispatch** (Run workflow in the Actions tab); push/PR triggers can be re-enabled when desired. That keeps the scorer, session, and verifier covered and the core code style consistent.

---

## Try it

1. Read the **“Terminology for interop”** table in docs/glossary.md. Pick one row and explain it to yourself in a sentence.
2. Open **docs/external-ids.md** and find where evidence **metadata** is documented. Confirm that fact_check_id (or similar) can be stored there.
3. Open **tests/test_standalone_scorer.py** and run **pytest tests/test_standalone_scorer.py -v**. Confirm at least one “valid input” and one “invalid input” test pass.
4. (Optional) Install **`.[api]`**, set **CHRONICLE_PROJECT_PATH**, run **uvicorn chronicle.api.app:app**, and call **GET /health** and **POST /investigations** with a JSON body **{"title": "Test"}**. Add header **X-Actor-Id: your_name** on the POST and confirm the investigation is attributed to you. Run the **Reference UI** from **frontend/** (`npm run dev`) and use **Try sample** on the home page, then explore the investigation (evidence, claims, defensibility, export). Or open **/static/curation.html** for the minimal curation UI.

---

## Summary

- **Terminology (glossary)** and **external IDs** (evidence metadata) help fact-checkers and provenance tools align with Chronicle.
- **Provenance recording** and **claim–evidence–metrics** docs describe what we store and what shape we can emit; **RAG evals** doc is the entry point for adding defensibility to your harness.
- **Optional HTTP API** (chronicle/api/, install `.[api]`) exposes write/read/export over HTTP with the same shapes as the eval contract. It also exposes **tier** (set + history) for friction tiers (spark → forge → vault), **evidence/claims/tensions** lists per investigation, **evidence spans** (for linking), **tension suggestions** (list + dismiss; confirm by declaring the tension), and **submission package** (ZIP). **Request identity** is set via **X-Actor-Id** / **X-Actor-Type** (or IdP); **verification_level** can be stored in event payloads. The **Reference UI** (frontend/, React + Vite) is an API-only client: Try sample, investigations, evidence/claims/links, defensibility, tensions, suggestions (Propose–Confirm), export, and Learn guides per vertical. **Minimal curation UI** at **/static/curation.html** is also available.
- **Tests** (scorer, session, verifier, attestation, identity, CLI actor) and **CI** (ruff + pytest; currently workflow_dispatch) keep the core behavior and style stable.

**← Previous:** [Lesson 10: Export, import, and Neo4j](10-export-import-neo4j.md) | **Index:** [Lessons](README.md) | **Next →:** [Lesson 12: The .chronicle file format and data schema](12-chronicle-file-format-and-schema.md)

**Quiz:** [quizzes/quiz-11-interoperability-api-and-tests.md](quizzes/quiz-11-interoperability-api-and-tests.md)
