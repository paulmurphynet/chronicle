# Reference UI plan: same repo, best of V1

This doc captures the plan for a **Chronicle Reference UI**: a human-in-the-loop frontend that lives in this repo and consumes only the Chronicle API. It records why we use a **single repo** (no separate frontend repo) and what we intend to bring over from ChronicleV1.

---

## Strategy: same repo, clean separation

- **Core** (this repo) = Chronicle package + optional HTTP API + scorer + verifier. No first-party "product" UI in core; the API is the integration surface.
- **Reference UI** = lives in this repo under **`frontend/`**. It is the official human-facing app that demonstrates the API is complete for human-in-the-loop. Built only against the public API (and verifier).
- **Why same repo:** One place for docs (no cross-repo links going stale). Code changes that affect both API and UI can be one PR. No version matrix between "Reference UI 1.x" and "Core 0.y." Contributors get the full picture in one clone.
- **Vendors** can build their own frontends (legal, compliance, journalism, research) on the same API and .chronicle format; the Reference UI is the template.

---

## What to bring from ChronicleV1 (and improve)

| V1 idea | Bring? | Notes |
|--------|--------|------|
| **Friction tiers** (Spark → Forge → Vault) | Yes | Backend already has workspace gating. UI shows tier, tier history, and what's blocked; user advances tier when ready. |
| **Propose–Confirm** | Yes | System (or optional AI) proposes links, tensions, types; user accepts or dismisses. Generalize as "suggestions" from API so the UI stays API-only. |
| **Progressive disclosure** | Yes | Spark = minimal required fields; structure (type, scope, tensions) at Forge/Vault or at publish/checkpoint. |
| **Reading surface** | Yes, simplified | Evidence list → open/paste content → create span (select or whole-doc) → "Support claim X" / "Challenge claim Y" from lists. No raw UIDs in main flow. |
| **Writing surface** | Optional / later | Markdown + optional claim extraction; can be a later module. |
| **Full V1 surface** | Subset first | First version: Investigations, Evidence & claims & links (Reading-lite), Defensibility, Tensions, Export/Verify. Publication, Policy, Graph can be added later or left to vertical UIs. |

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

| Item | V1 had | We have | Action |
|------|--------|---------|--------|
| **Learn / Quickstart** | `learn/quickstart.md`: first investigation in ~30 min, **Try sample**, "see defensibility change in 5 min" (Reading highlight → link). | `getting-started.md`; no "Try sample" + Reading flow. | When Reference UI exists: add a **Quickstart** path (Try sample, highlight → link, defensibility update) and optional **Learn** steps. |
| **Zero-to-submission** | One path: install → create inv → add evidence → claim + link → defensibility → **export submission package** in ~30 min. | Getting-started and verifier docs; no single "zero to submission" narrative. | Add or adapt **zero-to-submission** (or fold into getting-started) so human users have one clear path to "verifiable package I can send." |
| **Reasoning brief as primary artifact** | `reasoning-brief.md`: shape, sections, "default shareable artifact for a claim," implementation options. | API and implementation exist; verifier.md mentions brief. | Add a short **Reasoning brief** doc: position as primary shareable artifact, shape, when to use vs .chronicle. |
| **When to use Chronicle** | Clarifies Chronicle vs **data lineage**, **ML pipeline provenance**; when to add Chronicle vs extend other tools. | Not present. | Add **When to use Chronicle** to prevent scope creep and guide integrators (lineage/ML tools = different; Chronicle = claims + defensibility + verification). |
| **Building with Chronicle** | One-page for **agent/RAG builders**: idempotency, actor, tool provenance, reading defensibility (endpoints). | `integrating-with-chronicle.md` (min integration, frameworks). | Add or merge **Building with Chronicle** (one-page: idempotency, actor, tool provenance, defensibility reads) for agent/RAG builders. |
| **Propose–Confirm UX philosophy** | `human-in-the-loop.md`: Propose–Confirm, progressive disclosure, **design checklist**, vocabulary (task language, not schema). | `human-in-the-loop-and-attestation.md` (identity, attestation, curation workflow). | Extend or add: **Propose–Confirm and progressive disclosure** as UX philosophy for the Reference UI (design checklist, "user's job is is this right?"). |
| **Dismissal as data** | Innovation doc: **human-over-machine** in audit trail; SuggestionDismissed recorded with optional rationale. | Backend has SuggestionDismissed, TensionSuggestionDismissed; not framed in docs. | Document **dismissal as data** (human-over-machine in audit trail) in human-in-the-loop or epistemology scope. |
| **Learn guides (in-app)** | `api/static/learn/guides.json`: structured steps per vertical (journalism, legal, …) for the Learn page. | Not present. | Reference UI: optional **Learn guides** (e.g. guides.json or API-served) per vertical for step-by-step in-app guidance. |

### API surface (for Reference UI and vendors)

| Item | V1 had | We have | Action |
|------|--------|---------|--------|
| **Tier: set + history** | `POST /investigations/{id}/tier`, `GET .../tier-history`. | Backend: `set_tier`, `list_tier_history`. API returns `current_tier` on investigation; **no set tier or tier history endpoints**. | **Expose** set investigation tier and tier history in the API so the Reference UI can drive the friction-tier flow. |
| **Tension suggestions** | List, confirm (→ declare tension), dismiss. | Backend: `list_tension_suggestions`, `dismiss_tension_suggestion`, `emit_tension_suggestions`. **Not exposed in API**. | **Expose** tension suggestions (list, confirm, dismiss) in the API for Propose–Confirm in the Reference UI. |
| **Submission package** | "Export submission package" (ZIP: reasoning_briefs/, citations, etc.). | Export .chronicle; reasoning brief per claim via API/CLI. **No single "submission package" ZIP** in API. | Consider **submission package** endpoint (ZIP with reasoning briefs, citations, optional chain-of-custody) for human handoff; document in verifier if we add it. |

### Policy and examples

| Item | V1 had | We have | Action |
|------|--------|---------|--------|
| **Example policy profiles** | `docs/spec/profiles/*.json` (journalism, legal, compliance, etc.). | Policy in core; no example shareable JSON profiles in repo. | Add **example policy profiles** (e.g. one per vertical) as JSON for reference and for vertical-specific Reference UI or vendors. |

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
