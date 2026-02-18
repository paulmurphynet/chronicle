# External IDs and cross-system identity

When integrating Chronicle with fact-checking systems, provenance (e.g. C2PA), or other tools, you often need to record **external identifiers** so that "this Chronicle claim" or "this evidence item" can be matched to a record in another system.

## Evidence: use `metadata`

Evidence items support a **`metadata`** dict at ingest time. Store external IDs there so you can later correlate with your fact-check DB, C2PA claim IDs, or RAG chunk IDs.

**Example (session):**

```python
session.ingest_evidence(
    inv_uid,
    blob,
    "text/plain",
    original_filename="doc.pdf",
    metadata={
        "fact_check_id": "fc-12345",
        "source_url": "https://example.com/article",
        "c2pa_assertion_id": "urn:uuid:...",
    },
    actor_id="ingest-script",
    actor_type="tool",
)
```

**Example (eval contract / scorer):** The contract accepts evidence as strings or objects with `text` (and optionally `path`). It does not pass through metadata to the store. If you need to persist external IDs for evidence in scorer runs, use the session API or an adapter that calls `ingest_evidence` with `metadata`.

- **Stored as:** `evidence_item.metadata_json` in the read model (and in the event payload). Export formats (generic export, .chronicle) can include this so consumers can join on your external IDs.
- **Query:** The read model exposes `metadata_json` per evidence item; you can parse it and filter or join on your keys (e.g. `fact_check_id`).

## Claims: notes or tags (schema ready; API to expose)

The claim table has **`notes`** and **`tags_json`** columns; the event payload supports them. The **session’s `propose_claim`** and the underlying command do **not** currently accept `notes` or `tags` parameters. So today:

- **Option A:** Keep a mapping in your system (e.g. `claim_uid` → `fact_check_id`) when you create claims from fact-check verdicts.
- **Option B:** A small change can expose `notes=` and `tags=` on `propose_claim` so you can store e.g. `notes="fact_check_id: fc-12345"` or `tags=["external:fc-12345"]` at proposal time.

If you need **multiple** external keys per claim, see [To-do](to_do.md) for planned multi-key claim metadata; until then, a single note or tag is enough for one external ID once the API exposes it.

## Summary

| Chronicle entity | Where to store external IDs |
|------------------|-----------------------------|
| **Evidence** | `metadata` at ingest → `metadata_json` in DB and exports. |
| **Claim** | Use `notes` or `tags` for a single external ref. Multi-key claim metadata is in [To-do](to_do.md) if needed. |
| **Investigation** | `tags_json` or similar if your version supports it; otherwise keep mapping in your system by `investigation_uid`. |

This lets you say "this Chronicle claim_uid corresponds to that fact-check verdict" or "this evidence_uid corresponds to that C2PA assertion" without changing Chronicle’s core schema today.
