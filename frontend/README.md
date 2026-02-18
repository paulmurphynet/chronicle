# Chronicle Reference UI (frontend)

This directory is the home for the **Chronicle Reference UI**: the official human-in-the-loop frontend that talks only to the Chronicle HTTP API. We keep it in the **same repo** as the core so that docs and API/UI changes stay in sync and one PR can touch both when needed.

**Current state:** This folder holds static assets used by the project (e.g. `public/sample.chronicle` for demos and sample loading). The full Reference UI app (e.g. React/Vite) will be added here when we implement it.

**Plan:** See [Reference UI plan](../docs/reference-ui-plan.md) for:

- Why the frontend lives in this repo (no separate repo)
- What we will bring from ChronicleV1 (friction tiers, Propose–Confirm, Reading-lite) and how we'll improve it
- How the Reference UI will be an API-only client so vendors can build their own UIs on the same contract

**Running the API:** The Reference UI will require the Chronicle API to be running (e.g. `pip install -e ".[api]"`, set `CHRONICLE_PROJECT_PATH`, run `uvicorn chronicle.api.app:app`). See [API](../docs/api.md).
