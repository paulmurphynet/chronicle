# Chronicle Reference UI (frontend)

This directory is the home for the **Chronicle Reference UI**: the official human-in-the-loop frontend that talks only to the Chronicle HTTP API. We keep it in the **same repo** as the core so that docs and API/UI changes stay in sync and one PR can touch both when needed.

**Current state:** Full first version: **Home** (Try sample), **Investigations** list and detail (overview, tier + tier history, evidence, claims, links, defensibility, tensions, tension suggestions with confirm/dismiss, export .chronicle and submission package), **Learn** (step-by-step guides per vertical from `public/guides.json`). Static assets (e.g. `public/sample.chronicle`) live here for demos.

**Run the UI:** From this directory: `npm install` then `npm run dev`. Open http://localhost:5173. Configure the API base URL via env `VITE_API_BASE_URL` (default: use proxy `/api` → http://127.0.0.1:8000 when running dev).

**Plan:** See [Reference UI plan](../docs/reference-ui-plan.md) for:

- Why the frontend lives in this repo (no separate repo)
- What we will bring from ChronicleV1 (friction tiers, Propose–Confirm, Reading-lite) and how we'll improve it
- How the Reference UI will be an API-only client so vendors can build their own UIs on the same contract

**Running the API:** The Reference UI will require the Chronicle API to be running (e.g. `pip install -e ".[api]"`, set `CHRONICLE_PROJECT_PATH`, run `uvicorn chronicle.api.app:app`). See [API](../docs/api.md).
