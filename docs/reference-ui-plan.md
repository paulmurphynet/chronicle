# Reference UI plan: same repo, best of V1

This doc captures the plan for a **Chronicle Reference UI**: a human-in-the-loop frontend that lives in this repo and consumes only the Chronicle API. It records why we use a **single repo** (no separate frontend repo) and what we intend to bring over from ChronicleV1.

---

## Strategy: same repo, clean separation

- **Core** (this repo) = Chronicle package + optional HTTP API + scorer + verifier. No first-party "product" UI in core; the API is the integration surface.
- **Reference UI** = lives in this repo under **`frontend/`**. It is the official human-facing app that demonstrates the API is complete for human-in-the-loop. Built only against the public API (and verifier).
- **Reference module boundary** = `chronicle/reference/*` provides reference-surface import paths (API/client) while trust-critical logic stays in core/store/verifier modules.
- **Why same repo:** One place for docs (no cross-repo links going stale). Code changes that affect both API and UI can be one PR. No version matrix between "Reference UI 1.x" and "Core 0.y." Contributors get the full picture in one clone.
- **Vendors** can build their own frontends (legal, compliance, journalism, research) on the same API and .chronicle format; the Reference UI is the template.

---

## What to bring from ChronicleV1 (and improve)

| V1 idea | Bring? | Notes |
|--------|--------|------|
| **Friction tiers** (Spark → Forge → Vault) | Yes | Backend already has workspace gating. UI shows tier, tier history, and what's blocked; user advances tier when ready. |
| **Propose–Confirm** | Yes | System (or optional AI) proposes links, tensions, types; user accepts or dismisses. Generalize as "suggestions" from API so the UI stays API-only. |
| **Progressive disclosure** | Yes | Spark = minimal required fields; structure (type, scope, tensions) at Forge/Vault or at publish/checkpoint. |
| **Reading surface** | Yes, simplified | Evidence list → open/paste content → create span (select or whole-doc) → "Support claim X" / "Challenge claim Y" from lists. No raw UIDs in main flow. **In scope and implemented:** evidence content, select text → create span + link. |
| **Writing surface** | Yes | Markdown + add as evidence, propose claim (whole or from selection). **In scope and implemented.** |
| **Full V1 surface** | First version done | Investigations, Evidence & claims & links (Reading), Defensibility, Tensions, Export/Verify. **Publication, Policy, Graph in scope and implemented:** Publication tab (readiness + submission package), Policy tab (profiles + docs link), Graph tab (nodes/edges visualization). |

**Improvements over V1:** Reference UI is an **API-only client** (no private backend coupling). Suggestions can be an explicit part of the API contract. Tier and policy behavior are documented in the API so the UI can reflect "blocked" / "allowed" without guessing.

---

## Repo layout

- **`chronicle/`** — Core package and optional API. This is the only backend.
- **`frontend/`** — Reference UI (to be added or expanded). Contains the sample `.chronicle` for demos; the app will live here when built.
- **`docs/`** — Shared documentation. API contract and Reference UI docs live here; no duplication across repos.

When the Reference UI is implemented, it will be a standard frontend stack (e.g. React/Vite) in `frontend/` that talks to the API. Until then, `frontend/` holds the plan (see [frontend/README.md](../frontend/README.md)) and any static assets (e.g. sample.chronicle).

---

## Additional items from V1 scan (to bring or adapt)

A full scan of ChronicleV1 compared to this repo identified the following. All are **appropriate to add to the migration plan** (docs, API surface, or Reference UI) so we keep the best of V1 without duplicating what we already have.

### Docs to add or adapt

| Item | V1 had | We have | Status |
|------|--------|---------|--------|
| **Learn / Quickstart** | Try sample, highlight → link, defensibility update. | [quickstart-reference-ui.md](quickstart-reference-ui.md); [getting-started.md](getting-started.md). | Done. |
| **Zero-to-submission** | One path to verifiable submission package in ~30 min. | [zero-to-submission.md](zero-to-submission.md); [getting-started.md](getting-started.md). | Done. |
| **Reasoning brief as primary artifact** | Position, shape, when to use vs .chronicle. | [reasoning-brief.md](reasoning-brief.md). | Done. |
| **When to use Chronicle** | Scope vs data lineage / ML provenance. | [when-to-use-chronicle.md](when-to-use-chronicle.md). | Done. |
| **Building with Chronicle** | Idempotency, actor, tool provenance, defensibility reads. | [integrating-with-chronicle.md](integrating-with-chronicle.md) "Building with Chronicle" section. | Done. |
| **Propose–Confirm UX philosophy** | Design checklist, vocabulary (task language, not schema). | [human-in-the-loop-and-attestation.md](human-in-the-loop-and-attestation.md) Propose–Confirm and design checklist. | Done. |
| **Dismissal as data** | Human-over-machine in audit trail; SuggestionDismissed with rationale. | [human-in-the-loop-and-attestation.md](human-in-the-loop-and-attestation.md) "Dismissal as data". | Done. |
| **Learn guides (in-app)** | guides.json per vertical for Learn page. | [frontend/public/guides.json](../frontend/public/guides.json). | Done. |

### API surface (for Reference UI and vendors)

| Item | V1 had | We have | Status |
|------|--------|---------|--------|
| **Tier: set + history** | `POST /investigations/{id}/tier`, `GET .../tier-history`. | API: `POST /investigations/{id}/tier`, `GET /investigations/{id}/tier-history`. Backend: `set_tier`, `list_tier_history`. | Done. |
| **Tension suggestions** | List, confirm (→ declare tension), dismiss. | API: `GET /investigations/{id}/tension-suggestions`, `POST .../tension-suggestions/{suggestion_uid}/dismiss`. Confirm by declaring tension (POST /tensions). | Done. |
| **Submission package** | "Export submission package" (ZIP: reasoning_briefs/, citations, etc.). | API: `POST /investigations/{id}/submission-package` returns ZIP with .chronicle, reasoning_briefs/, manifest.json. | Done. |

### Policy and examples

| Item | V1 had | We have | Action |
|------|--------|---------|--------|
| **Example policy profiles** | `docs/spec/profiles/*.json` (journalism, legal, compliance, etc.). | Policy in core; example profiles added. | **Done:** [docs/policy-profiles/](policy-profiles/README.md) — journalism, legal, compliance JSON + README for reference and vertical UIs. |

### Already aligned (no change)

- **Friction tiers (backend)** — We have workspace gating, tier in read model, tier history, TierChanged events.
- **Suggestions (backend)** — We have tension_suggestion table, emit/dismiss, SuggestionDismissed.
- **Reasoning brief (implementation)** — We have `get_reasoning_brief`, reasoning_brief_to_html, API and CLI.
- **Verification guarantees** — We have `verification-guarantees.md`.
- **Human-in-the-loop (identity)** — We have actor, attestation, verification_level in human-in-the-loop-and-attestation.

---

## Related docs

- [Human-in-the-loop and attestation](human-in-the-loop-and-attestation.md) — How the system supports human curation and attribution.
- [API](api.md) — HTTP API that the Reference UI (and any vendor UI) will use.
- [Migration from V1](migration-from-v1.md) — What was brought from ChronicleV1 and what was not; this plan extends that with "Reference UI in same repo when we add it." For a full list of V1 items to bring or adapt, see **Additional items from V1 scan** above.
