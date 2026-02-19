# Human-in-the-loop and attestation

Chronicle supports **human-in-the-loop** workflows: a person can fine-tune, curate, and attest when getting data Chronicle-compliant. This doc describes why that matters, how the system supports it, and how to run it today.

---

## Why human-in-the-loop

- **Data that can't be fully automated** — Many datasets (messy formats, one-off sources, transcripts, legal records) don't yet map cleanly to Chronicle's schema without human judgment. Field mapping, which rows become claims, which links or tensions to add, and when to confirm or override require a human.
- **Accountability** — When a chronicle is used for audit, compliance, or publication, you want to know **who** curated it and, optionally, **how strongly** they were identified (claimed identity vs verified credential). Human-in-the-loop plus attestation gives you that.

We don't require a human for every write; we support **both** fully automated pipelines (actor_type=`tool`) and human-curated flows (actor_type=`human`, with optional verification level).

---

## Spectrum: regulated feed vs human-curated dataset

| Mode | Who acts | Typical use |
|------|----------|-------------|
| **Regulated feed** | Pipeline (tool) with optional human sign-off | Well-defined schema; mapping is stable; human may confirm or override at checkpoints. |
| **Human-curated dataset** | Human (or UI acting for them) as primary actor | Messy or one-off data; human maps, corrects, links, and attests; every write is attributed to them. |

Both use the same primitives: **actor_id**, **actor_type**, optional **verification_level**, and **human_decisions** (confirm/override with rationale).

---

## How the system supports it

### Actor on every event

Every event stores **actor_id** and **actor_type** (`human` | `tool` | `system`). So "who did what" is recorded on each write event. The ledger records what the writer sent (or what the server resolved from auth/headers); correctness of identity depends on your deployment's auth and IdP setup.

### Identity and verification level

The **identity module** (`chronicle.core.identity`) can bind the acting identity to a request (or CLI run) and return a **verification level**: e.g. `none`, `claimed`, `account`, `verified_credential`, `decentralized`, `zk_attested`. When the API or CLI uses this, we can store **verification_level** (and optionally an attestation ref) so that "attested with verified credential" is queryable. See [Persisting verification level](#persisting-verification-level) below.

### Propose–Confirm and progressive disclosure

The Reference UI and API are designed so the **system (or optional AI) proposes** and the **user confirms or dismisses**. Examples: tension suggestions (list → confirm by declaring the tension, or dismiss), link suggestions, type/scope suggestions. The user’s job is “is this right?”—accept or dismiss with optional rationale. **Progressive disclosure** keeps the first tier (Spark) minimal (e.g. required fields only); structure (type, scope, tensions) can be added at Forge/Vault or at publish/checkpoint. See [Reference UI plan](reference-ui-plan.md) for friction tiers and Propose–Confirm in the UI.

**Propose–Confirm design checklist (Reference UI):**

- Use **task language** in the UI (e.g. "Does this evidence support this claim?") rather than schema terms (e.g. "link_type").
- Every suggestion (tension, link, type) has a clear **confirm** and **dismiss** action; dismiss can ask for optional rationale.
- **Progressive disclosure:** Spark = minimal required fields; Forge/Vault or checkpoint = add type, scope, tensions, publication readiness.
- Show **blocked vs allowed** from policy (e.g. "Export blocked until tensions addressed") so the user knows why an action is disabled.
- Record **who** confirmed or dismissed (actor_id, actor_type) and optional rationale so the audit trail is human-over-machine explicit.

### Dismissal as data (human-over-machine in the audit trail)

When a human **dismisses** a suggestion (e.g. tension suggestion, link suggestion), that decision is recorded in the ledger: **SuggestionDismissed** or **TensionSuggestionDismissed** with optional rationale. So the audit trail shows “machine suggested X; human dismissed it (reason: …).” That supports accountability and epistemology: human-over-machine is explicit and queryable. The API exposes tension suggestions (list, confirm via `POST /tensions`, dismiss via `POST .../tension-suggestions/{id}/dismiss`). See [API](api.md) for endpoints.

### Human decision events

**record_human_confirm** and **record_human_override** record explicit human decisions (e.g. "publish despite weak defensibility") with a **required rationale** and the acting **actor_id** / **actor_type**. Use these when a human formally signs off or overrides a policy warning.

### Attestation = we record; proving identity is deployment-specific

**Attestation** here means: we **record** who did it (actor_id, actor_type) and optionally the **verification_level** (and attestation ref) when the deployment provides it. We do **not** verify credentials ourselves—that is a deployment concern (auth middleware, IdP, verified credentials). Chronicle's job is to persist the binding you give it so the ledger is auditable.

---

## How to do it today

### CLI: set your identity

Set **CHRONICLE_ACTOR_ID** and optionally **CHRONICLE_ACTOR_TYPE** so that commands that create investigations, evidence, claims, links, or tensions attribute them to you:

```bash
export CHRONICLE_ACTOR_ID="jane_doe"
export CHRONICLE_ACTOR_TYPE="human"
chronicle init /path/to/project
chronicle create-investigation --path /path/to/project --title "My curation"
```

Or pass **--actor-id** and **--actor-type** on supported write commands. Scripts that use the session (e.g. `ingest_transcript_csv.py`) will use the same env when they create a session, so running them with `CHRONICLE_ACTOR_ID` set attributes the ingest to you.

### Session API (Python)

When calling the session from your own code, pass **actor_id** and **actor_type** on every write:

```python
with ChronicleSession(project_path) as session:
    session.create_investigation("Curation run", actor_id="jane_doe", actor_type="human")
    session.propose_claim(inv_uid, "A claim.", actor_id="jane_doe", actor_type="human")
    session.record_human_confirm("claim", claim_uid, "publish", "Reviewed and approved.", actor_id="jane_doe", actor_type="human")
```

### HTTP API

When using the optional HTTP API, set **X-Actor-Id** and **X-Actor-Type** on each request so the server records you as the actor. When the deployment uses an Identity Provider (IdP), the server can resolve the actor from auth and optionally store the verification level. See [API](api.md#request-identity-and-attestation).

---

## Human-curated ingestion workflow

Concrete steps to get a dataset Chronicle-compliant with a human in the loop:

1. **Set your identity** — Env: `CHRONICLE_ACTOR_ID` and `CHRONICLE_ACTOR_TYPE` (or API headers). All subsequent writes will be attributed to you.
2. **Create project and investigation** — `chronicle init` and `chronicle create-investigation`, or API equivalents. Use a dedicated project for this curation run if you want a clean export.
3. **Ingest and map** — Run ingest scripts (e.g. `ingest_transcript_csv.py`) or call the session/API to add evidence, claims, and links. Correct and refine as needed (add links, declare tensions, type claims).
4. **Formal sign-off where needed** — For checkpoints or "publish despite weak defensibility," use **human_confirm** or **human_override** with a short rationale so the trail shows a human decision.
5. **Export and verify** — Export the investigation to a `.chronicle` file. Run `chronicle-verify` on it. Share or reuse the file; the ledger inside records who did what.

**Curation helper** — Existing scripts already support attribution: e.g. `ingest_transcript_csv.py` uses `actor_id` from the CSV speaker column for *statement* attribution; set **CHRONICLE_ACTOR_ID** for *who is running the script* (the curator). So one person can run the script with their identity set and the resulting chronicle will show them as the actor for the ingest events.

---

## Persisting verification level

When the API (or CLI) resolves identity via an Identity Provider, it can receive a **verification_level** (e.g. `verified_credential`). The API passes this into the session; the session passes it to write commands; commands store it in the event **payload** under the reserved key **`_verification_level`** (and optionally **`_attestation_ref`**). So:

- Events written with a resolved identity can carry `payload["_verification_level"]` and `payload["_attestation_ref"]`.
- Downstream tools (audit export, reasoning brief, or custom queries) can read these from the event payload to show "attested with verified credential" or link to an attestation record.

Schema and Event envelope stay unchanged; persistence is payload-only. See [Identity](api.md#request-identity-and-attestation) and `chronicle.core.identity`.

---

## Minimal curation UI

A **minimal curation UI** is provided so a human can work with a dataset in the browser: create investigations, add evidence, propose claims, and link support via the API with their identity. With the API running (`uvicorn chronicle.api.app:app`), open **/static/curation.html** (e.g. `http://127.0.0.1:8000/static/curation.html`). Set your **Actor ID** (and optionally Actor type), then create an investigation, ingest evidence (paste text), propose claims, and link span→claim as support. All writes send **X-Actor-Id** and **X-Actor-Type** so the ledger attributes them to you. We can trim or simplify this UI before v1 if needed; it is intended as a starting point for human-curated ingestion.

---

## Summary

| Question | Answer |
|----------|--------|
| Why human-in-the-loop? | Many datasets need human judgment to map and curate; accountability requires knowing who did what. |
| How is the actor recorded? | Every event has actor_id and actor_type; optional verification_level (and attestation ref) can be stored in the event payload. |
| How do I run as a human today? | Set CHRONICLE_ACTOR_ID (and CHRONICLE_ACTOR_TYPE) when using the CLI or scripts; set X-Actor-Id / X-Actor-Type when using the API; pass actor_id/actor_type when using the session in code. |
| Do we verify identity? | No. We record who you say you are (or who the IdP resolved). Proving identity is a deployment concern. |
| Where is verification level stored? | In the event payload as `_verification_level` (and optionally `_attestation_ref`) when the API/CLI provides it. |
