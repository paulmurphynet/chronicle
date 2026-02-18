# Lessons, Quizzes, and Story — Completeness Review

**Implementation status:** The changes in Sections 1–4 below were implemented (lessons 01, 05, 06, 11; quizzes 01, 11; story ch 03). Optional Lesson 13 (Reference UI) was not added.

This document summarizes what needs to be **added or updated** in the lessons, quizzes, and story so they stay complete and aligned with the project’s code. It was produced by reviewing the repo structure, lesson content, quiz questions/answers, story chapters, and the implemented code (API, store, frontend, docs).

---

## 1. Lessons — What to Add or Update

### 1.1 Lesson 01 (Codebase map)

- **Clarify verifier location:** The table says `scripts/` includes “scorer, verifier (CLI)”. The **verifier** implementation lives in **`tools/verify_chronicle/`**; the **CLI** `chronicle-verify` is installed with the package and implemented there. Either move “verifier” to a separate row for `tools/` or rephrase to: “Scorer and other scripts in `scripts/`; verifier in `tools/verify_chronicle/` (CLI: `chronicle-verify`).”
- **Optional:** Add **`frontend/`** to the top-level layout table (Reference UI: React + Vite, API-only client) with one line so new contributors see it on the map. Lesson 11 already covers it in depth.

### 1.2 Lesson 02 (The scorer)

- **Line numbers:** The lesson says “around lines 98–122” and “124–185”. If the scorer file is refactored, update these or use “in `_run_scorer`” / “in the block that creates the temp project and session” instead of fixed line ranges.
- No other gaps; content matches the code.

### 1.3 Lesson 03 (The verifier)

- No changes required; key files and behavior match `tools/verify_chronicle/` and docs.

### 1.4 Lesson 04 (Events and core)

- **Try it:** “Compare with the technical report Section 3.2 (Claim)” — confirm that the technical report still has Section 3.2 and that payload fields align. If the report was renumbered, update the reference.
- No other gaps.

### 1.5 Lesson 05 (Store and session)

- **Line numbers:** The lesson says “Read **session.py** around **ingest_evidence** and **propose_claim** (e.g. lines 200–280).” In the current code, `ingest_evidence` starts ~190 and `propose_claim` ~226. Update to “around lines 190–250” or “in the `ingest_evidence` and `propose_claim` methods” so it stays valid after small edits.
- **Optional:** Mention **tension suggestions** and **tier** briefly: the session also has `emit_tension_suggestions`, `dismiss_tension_suggestion`, and tier (e.g. `set_tier`, tier history) for the Reference UI and workspace gating. A single sentence plus “see Lesson 11 and docs/api.md” is enough so the session description matches the API surface.

### 1.6 Lesson 06 (Defensibility metrics)

- **Line number:** The lesson says “**get_defensibility_score** (around line 755)”. The function is at **line 769** in `chronicle/store/commands/claims.py`. Update to “around line 769” or “in `get_defensibility_score`”.
- **Line numbers:** “the block that sets `provenance_quality` (around lines 805–812)” — verify these line numbers in the current file and adjust if needed.
- No other gaps.

### 1.7 Lesson 07 (Integrations and scripts)

- **Script list:** Lesson and scripts/README list `generate_sample_chronicle.py` and verticals. Ensure any new first-class scripts in scripts/README are mentioned if they’re part of the “scripts you’ll see” scope.
- No other gaps.

### 1.8 Lesson 08 (CLI)

- **Tier:** The lesson already mentions “set-tier” and actor identity. Optional: one sentence that **tiers** (spark → forge → vault) gate workspace actions (e.g. export, publication) per policy; details in docs/human-in-the-loop-and-attestation.md and docs/api.md.
- No other gaps.

### 1.9 Lesson 09 (Epistemic tools)

- No changes required if the tools (decomposer, contradiction, type inference) are still in `chronicle/tools/` and match the descriptions.

### 1.10 Lesson 10 (Export, import, Neo4j)

- No changes required; content matches export/import and Neo4j code.

### 1.11 Lesson 11 (Interoperability, API, and tests)

- **Tension suggestion “confirm”:** The lesson says “tension suggestions with confirm/dismiss”. In the API there is **POST …/tension-suggestions/{id}/dismiss**; there is **no** separate “confirm” endpoint. **Confirm** is done by **declaring a tension** (POST declare_tension with the same claim_a_uid / claim_b_uid); the projection then marks the matching suggestion as confirmed. Add one sentence: “Confirming a suggestion is done by declaring the tension (same claim pair); the backend then marks that suggestion as confirmed.”
- **CI trigger:** The lesson says “On push/PR to main (or master), we run ruff and pytest.” If CI is currently **only** `workflow_dispatch` (as in some project notes), either update the lesson to say “CI can be run via workflow_dispatch; push/PR triggers are re-enabled when ready” or re-enable push/PR and keep the lesson as-is.
- **Friction tiers:** Optional: add one sentence that the API supports **tier** (POST …/tier, GET …/tier-history) for spark/forge/vault and that the Reference UI uses this for the friction-tier flow. This ties the lesson to the real UI behavior.

### 1.12 Lesson 12 (Chronicle file format and schema)

- **Try it:** The lesson says “`PYTHONPATH=. python3 scripts/generate_sample_chronicle.py`”. The script exists and writes a path (or default); the lesson is correct. If the script ever changes its output path or name, update the Try it step.
- No other gaps; schema and verifier requirements match the code.

### 1.13 Missing lesson (optional)

- **Reference UI / frontend:** There is **no** dedicated lesson for the **frontend** (React, pages, API client, guides.json). Lesson 11 already covers “Reference UI” and key files (frontend/, frontend/README.md, guides.json). For “lessons cover every important area,” consider adding **Lesson 13: The Reference UI** (short): structure of `frontend/`, main pages (Home, Investigations, InvestigationDetail, Learn), how it calls the API, where guides and sample.chronicle live. This is optional and can be a single-page lesson with a link to docs/reference-ui-plan.md.

---

## 2. Quizzes — What to Add or Update

### 2.1 Quiz 01 (Codebase map)

- **Q1:** Answer key correctly says scorer = `scripts/standalone_defensibility_scorer.py` and verifier = `chronicle-verify` (tools/verify_chronicle). No change.
- **Optional:** Add one question: “Where does the Reference UI (human-in-the-loop frontend) live?” Answer: **frontend/** (React + Vite, API-only). This reinforces the codebase map for new contributors.

### 2.2 Quizzes 02–10

- No changes required; questions and answers align with the lessons and code.

### 2.3 Quiz 11 (Interoperability, API, and tests)

- **Q10:** Answer correctly describes Reference UI and “Try sample”. No change.
- **Optional:** Add a question: “How do you **confirm** a tension suggestion in the API (turn it into a real tension)?” Answer: **By declaring a tension** (POST declare_tension with the same claim_a_uid and claim_b_uid); the backend marks the matching suggestion as confirmed. There is no separate “confirm” endpoint.
- **Optional:** If you add a sentence about CI being workflow_dispatch-only, add or adjust a question so the answer key matches the actual CI behavior.

### 2.4 Quiz 12 (Chronicle file format and schema)

- No changes required.

### 2.5 Lesson 00

- By design there is **no quiz** for Lesson 00 (meta). No change.

---

## 3. Story — What to Add or Update

### 3.1 Chapter 01 (The problem)

- No changes needed; content is product-agnostic and matches the mission.

### 3.2 Chapter 02 (Why this problem exists)

- No changes needed.

### 3.3 Chapter 03 (How we’re solving it)

- **Friction tiers:** The story does not explain **spark → forge → vault** or workspace gating. Consider adding one short paragraph or bullet: “Investigations can move through **friction tiers** (e.g. Spark → Forge → Vault); each tier can require more structure (e.g. typed claims, resolved tensions) before export or publication. The Reference UI and API support setting tier and viewing tier history so teams can enforce ‘show your work’ step by step.” This matches docs/reference-ui-plan.md and the API (POST …/tier, GET …/tier-history).
- **Tension suggestions:** You already mention “tension suggestions” and “Propose–Confirm”. Optional: one phrase that users **confirm** by declaring the tension (same claim pair), and **dismiss** via the dismiss endpoint, so the story matches the API and UI.
- Rest of the chapter (evidence, claims, score, .chronicle, verifier, ecosystem, Reference UI, curation UI) is aligned.

### 3.4 Chapter 04 (Where challenges remain)

- **Completeness:** The list of “first-class” and “optional” items is accurate. If you add a Reference UI lesson (Lesson 13), you could add a line under “what’s left” or “polish”: “A short lesson on the Reference UI (frontend) is optional for full codebase coverage.”
- No other changes required.

### 3.5 Chapter 05 (How you can help)

- No changes needed.

### 3.6 Chapter 06 (Epistemology tables)

- No changes needed; the “what we implement” and “what we don’t” tables match the code and docs (verifier, defensibility, rationale, defeater_kind, etc.).

---

## 4. Summary Checklist

Use this list to track updates. Items are ordered by impact (accuracy first, then completeness, then optional polish).

| Area | Action | Priority |
|------|--------|----------|
| **Lesson 01** | Clarify that verifier lives in `tools/verify_chronicle/`, not in `scripts/`. Optionally add `frontend/` to the layout table. | High |
| **Lesson 05** | Update line numbers for `ingest_evidence` / `propose_claim` (e.g. “around 190–250” or “in the … methods”). Optionally mention session methods for tension suggestions and tier. | Medium |
| **Lesson 06** | Update line number for `get_defensibility_score` to ~769 and verify `provenance_quality` block line numbers in claims.py. | Medium |
| **Lesson 11** | Add one sentence: confirming a tension suggestion = declare_tension (no separate confirm endpoint). Optionally mention tier endpoints and friction tiers; align CI description with actual triggers (workflow_dispatch vs push/PR). | High |
| **Quiz 11** | Optionally add a question/answer: how do you confirm a tension suggestion? (By declaring the tension.) | Low |
| **Quiz 01** | Optionally add a question: where does the Reference UI live? (frontend/.) | Low |
| **Story Ch 03** | Add a short mention of **friction tiers** (spark → forge → vault) and optional phrase that confirm = declare tension, dismiss = dismiss endpoint. | Medium |
| **Optional** | Add **Lesson 13: The Reference UI** (frontend structure, main pages, API usage, guides) and reference it in lessons/README and story if you want “every important area” to include the frontend. | Low |

---

## 5. Doc and Code References Checked

- **Docs:** verification-guarantees.md, consuming-chronicle.md, integrating-with-chronicle.md, api.md, reference-ui-plan.md, human-in-the-loop-and-attestation.md, policy-profiles (tier_overrides), eval_contract.md, defensibility-metrics-schema.md — all referenced in lessons/story exist and names are correct.
- **Scripts:** generate_sample_chronicle.py exists; lessons 03, 10, 12 and docs reference it correctly.
- **API:** Tier (POST/GET), tension-suggestions (list + dismiss), submission-package, declare_tension — all present; “confirm” for suggestions is via declare_tension, not a separate endpoint.
- **Frontend:** InvestigationDetail confirms suggestions via `api.declareTension(...)` and dismiss via the dismiss endpoint; tiers and export/submission package are used.

No broken internal links or missing files were found in the reviewed lessons, quizzes, or story chapters. The main gaps are: (1) clarifying verifier location and tension-suggestion “confirm” behavior, (2) updating a few line numbers, and (3) adding friction tiers and optional Reference UI coverage in the story and (optionally) in a new lesson.
