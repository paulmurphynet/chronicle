# Chronicle HTTP API (optional)

A **minimal HTTP API** for Chronicle: write (investigation, evidence, claim, link, tension), read (claim, defensibility, reasoning brief), export/import .chronicle. Same response shapes as the [eval contract](eval_contract.md) and [defensibility metrics schema](defensibility-metrics-schema.md).

**Install:** `pip install -e ".[api]"` (adds FastAPI, uvicorn, python-multipart).  
**Run:** Set `CHRONICLE_PROJECT_PATH` to your project directory, then:

```bash
uvicorn chronicle.api.app:app --reload
```

Default: `http://127.0.0.1:8000`. OpenAPI docs: `http://127.0.0.1:8000/docs`.

**No auth** in this minimal version; run behind your own auth or reverse proxy in production.

---

## Request identity and attestation

Every **write** request (create investigation, ingest evidence, propose claim, link support/challenge, declare tension) records an **actor** (who did it). The server resolves the actor from:

1. **Identity Provider (IdP)** — When `CHRONICLE_IDENTITY_PROVIDER` is set (e.g. `traditional`) and auth middleware sets the principal, the server uses that as `actor_id` and can store a verification level (see [Human-in-the-loop and attestation](human-in-the-loop-and-attestation.md)).
2. **Headers** — When no IdP binding is present, the server reads **X-Actor-Id** and **X-Actor-Type** (e.g. `X-Actor-Id: jane_doe`, `X-Actor-Type: human`). So a human or client can identify themselves on each request.
3. **Default** — If neither is set, the server uses `actor_id=default`, `actor_type=human`.

So: set **X-Actor-Id** (and optionally **X-Actor-Type**) on write requests so the ledger attributes them to you. When you run behind auth and configure an IdP, the server can override with the authenticated principal.

**Verification level:** When the IdP returns a verification level (e.g. `verified_credential`), the server persists it on each write event in the payload as `_verification_level` (and optionally `_attestation_ref`). This is payload-only; the event schema is unchanged. See [Human-in-the-loop and attestation](human-in-the-loop-and-attestation.md).

---

## Configuration

| Env | Description |
|-----|-------------|
| `CHRONICLE_PROJECT_PATH` | **Required for project-based endpoints.** Path to the Chronicle project directory. If the directory does not exist it is created; if it exists but has no `chronicle.db`, the project is initialized. **Not required** for `POST /score`. |

---

## Endpoints

### Standalone score (no project path)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/score` | Run defensibility scorer on `{ "query", "answer", "evidence" }`. **Does not require** `CHRONICLE_PROJECT_PATH`; uses a temporary project. Evidence: array of strings or objects with `"text"` or `"url"` (path-based evidence not accepted). Returns same shape as [eval contract](eval_contract.md) (metrics or error). |

### Write

| Method | Path | Description |
|--------|------|-------------|
| POST | `/investigations` | Create investigation. Body: `{ "title", "description?", "investigation_key?" }`. Returns `event_id`, `investigation_uid`. |
| POST | `/investigations/{id}/evidence` | Ingest evidence. JSON body: `{ "content"? \| "content_base64"?`, `media_type?`, `original_filename?` } **or** multipart form with field `file`. Returns `event_id`, `evidence_uid`, `span_uid`. |
| POST | `/investigations/{id}/claims` | Propose claim. Body: `{ "text", "initial_type?" }`. Returns `event_id`, `claim_uid`. |
| POST | `/investigations/{id}/links/support` | Link span as support. Body: `{ "span_uid", "claim_uid" }`. Returns `event_id`, `link_uid`. |
| POST | `/investigations/{id}/links/challenge` | Link span as challenge. Body: `{ "span_uid", "claim_uid" }`. |
| POST | `/investigations/{id}/tensions` | Declare tension. Body: `{ "claim_a_uid", "claim_b_uid", "tension_kind?" }`. Returns `event_id`, `tension_uid`. |

### Read

| Method | Path | Description |
|--------|------|-------------|
| GET | `/investigations` | List investigations. |
| GET | `/claims/{claim_uid}` | Get claim. |
| GET | `/claims/{claim_uid}/defensibility` | Defensibility scorecard (same shape as eval contract output). Query: `use_strength_weighting=false`. |
| GET | `/claims/{claim_uid}/reasoning-brief` | Reasoning brief (claim, defensibility, support/challenge, tensions, trail). Query: `limit?`. |

### Export / import

| Method | Path | Description |
|--------|------|-------------|
| POST | `/investigations/{id}/export` | Export investigation as .chronicle (ZIP). Returns binary attachment. |
| POST | `/import` | Import .chronicle file (multipart `file`). Merges into project. |

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | 200 if `CHRONICLE_PROJECT_PATH` is set and project is usable; 503 otherwise. When using only `POST /score`, you can leave the env unset; `/score` still works while `/health` returns 503. |

---

## Example flow

1. `POST /investigations` with `{"title": "My run"}` → get `investigation_uid`.
2. `POST /investigations/{id}/evidence` with `{"content": "The company reported $1.2M revenue."}` → get `evidence_uid`, `span_uid`.
3. `POST /investigations/{id}/claims` with `{"text": "Revenue was $1.2M."}` → get `claim_uid`.
4. `POST /investigations/{id}/links/support` with `{"span_uid": "...", "claim_uid": "..."}`.
5. `GET /claims/{claim_uid}/defensibility` → same shape as standalone scorer output.

See [Integrating with Chronicle](integrating-with-chronicle.md) and [RAG evals](rag-evals-defensibility-metric.md) for the session/scorer flow; the API mirrors that over HTTP.
