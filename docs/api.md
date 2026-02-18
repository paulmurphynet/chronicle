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

## Configuration

| Env | Description |
|-----|-------------|
| `CHRONICLE_PROJECT_PATH` | **Required.** Path to the Chronicle project directory. If the directory does not exist it is created; if it exists but has no `chronicle.db`, the project is initialized. |

---

## Endpoints

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
| GET | `/health` | 200 if `CHRONICLE_PROJECT_PATH` is set and project is usable; 503 otherwise. |

---

## Example flow

1. `POST /investigations` with `{"title": "My run"}` → get `investigation_uid`.
2. `POST /investigations/{id}/evidence` with `{"content": "The company reported $1.2M revenue."}` → get `evidence_uid`, `span_uid`.
3. `POST /investigations/{id}/claims` with `{"text": "Revenue was $1.2M."}` → get `claim_uid`.
4. `POST /investigations/{id}/links/support` with `{"span_uid": "...", "claim_uid": "..."}`.
5. `GET /claims/{claim_uid}/defensibility` → same shape as standalone scorer output.

See [Integrating with Chronicle](integrating-with-chronicle.md) and [RAG evals](rag-evals-defensibility-metric.md) for the session/scorer flow; the API mirrors that over HTTP.
