# Implementation to-do

**Single place for implementation steps.** No separate "implementation plan" docs — we keep one list here, check items off as we go, and clear the list when the batch is done and user docs are updated.

**Guidebook:** Enhancement deferred until after more features (interoperability, etc.) to avoid repeated rewrites.

## How to use this file

1. **When starting a set of changes** — Add the steps to "Current steps" below (e.g. 10 items). Use `- [ ]` for open and `- [x]` for done.
2. **While working** — Mark items done as you complete them. Leave all items in the list so we can see what was in scope.
3. **When the batch is finished** — Confirm the features are reflected in normal user documentation (README, eval_contract, verifier, etc.). Then **empty** the "Current steps" section (delete the list or leave "— none —") so the file is clean.
4. **Next batch** — Add the next set of steps to "Current steps" and repeat.

This keeps the repo from accumulating many one-off implementation-plan docs; one file, one list, reset when done.

---

## Current steps

— none —

<!-- Batch completed: Human-in-the-loop and attestation. All 7 steps done. -->
<!-- - [x] **1. Doc: Human-in-the-loop and attestation** — Add `docs/human-in-the-loop-and-attestation.md`. Cover: why human-in-the-loop (data that can’t be fully automated; accountability); spectrum (regulated feed vs human-curated dataset); how actor_id/actor_type, human_decisions, and the identity module support it; how to do it today (CLI with actor env/flags, session, API after step 2); that attestation = we record who did it and optionally verification level (proving identity is deployment-specific); where verification_level could be stored later if needed. Link from docs/README or a “By topic” entry.
<!-- - [x] **2. API: Resolve actor from request** — In `chronicle/api/app.py`, for every write endpoint that creates investigations, evidence, claims, links, tensions, or human_decisions: resolve actor via `get_effective_actor_from_request(request)` from `chronicle.core.identity` and pass the returned `actor_id` and `actor_type` into the session call (instead of hardcoded `"api"`/`"tool"`). When IdP returns no binding, keep using headers `X-Actor-Id` / `X-Actor-Type` when present (NoneIdP already does this), else fall back to `"default"`/`"human"` or `"api"`/`"tool"` so existing clients keep working. Document in `docs/api.md` that request identity can be set via headers or auth (IdP) and is recorded on every write.
<!-- - [x] **3. CLI: Attestation identity for human operators** — Support `CHRONICLE_ACTOR_ID` and `CHRONICLE_ACTOR_TYPE` env vars (and optionally `--actor-id` / `--actor-type` on write commands) so a human running the CLI is attributed. In `chronicle/cli/main.py`: read env at startup; for commands that create investigations, evidence, claims, links, tensions, or human confirm/override, pass actor_id/actor_type from env or flags into the session. Ensure scripts that call the session (e.g. `ingest_transcript_csv.py`) document or use the same env so a human curator can set `CHRONICLE_ACTOR_ID=jane_doe` when running them.
- [x] **4. Doc: Curation workflow** — In the new human-in-the-loop doc (or a short “Human-curated ingestion” subsection), add a concrete workflow: (a) human sets identity (env or API headers); (b) run ingest/import scripts or call session/API so all writes are attributed; (c) use human_confirm / human_override where a formal sign-off is needed; (d) export .chronicle for verification and reuse. Optionally add one “curation helper” example (e.g. script that ingests a CSV with `actor_id` from env) if not already covered by existing scripts.
- [x] **5. Cross-links** — Add the human-in-the-loop doc to the README “By topic” table and to `docs/integrating-with-chronicle.md` (e.g. “Human-curated data and attestation”) and to the guidebook (e.g. “How you can help” or “Where challenges remain”) so the pattern is discoverable.
- [x] **6. Persist verification_level** — If deployments will use IdP with verification levels (e.g. verified_credential): add a way to store verification_level (and optionally attestation ref) for the actor on write—e.g. in event payload or a small attestation table—so “attested with verified credential” is queryable. Document in human-in-the-loop doc and identity/API docs.
- [x] **7. Minimal curation UI** — Add a minimal UI (e.g. single-page or small app) for “human works with a dataset to make it Chronicle-compliant”: load/map data, preview evidence/claims/links, confirm and write via API with the user’s identity. Document in human-in-the-loop doc; we can trim or simplify before v1 if needed. -->
