# Quickstart: Reference UI (Try sample, highlight to link, defensibility update)

This path is for users who run the **Reference UI** (frontend) and want to see defensibility change in a few minutes.

---

## Prerequisites

- Chronicle API running (e.g. `pip install -e ".[api]"`, set `CHRONICLE_PROJECT_PATH`, run `uvicorn chronicle.api.app:app`).
- Reference UI running from `frontend/` (e.g. `npm install` then `npm run dev`; open http://localhost:5173).

---

## Quick path

1. **Try sample** — In the Reference UI, use "Try sample" or "Load sample" (e.g. Journalism sample) so an investigation opens with evidence and claims.
2. **Open evidence** — Open an evidence item and view its content.
3. **Highlight to link** — Select text in the evidence (highlight a span). Create a span from the selection, then use "Support claim X" or "Challenge claim Y" to link that span to a claim.
4. **See defensibility update** — The defensibility scorecard for the claim updates (e.g. support count, provenance strength). Check the claim's defensibility view or reasoning brief.

This demonstrates: evidence, claims, support/challenge links, and defensibility in one flow. For a full path to a verifiable package, see [Zero to submission](zero-to-submission.md). For API-only or CLI use, see [Getting started](getting-started.md) and [Quickstart](quickstart.md).
