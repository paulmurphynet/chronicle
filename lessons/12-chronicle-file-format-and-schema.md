# Lesson 12: The .chronicle file format and data schema

**Objectives:** You will have a complete picture of the **.chronicle** file format (ZIP layout, manifest, database, evidence) and the **data schema** (events table, read-model tables). This is the single lesson that fully covers the chronicle file format and all schema aspects so you can consume or produce .chronicle files correctly.

**Key files:**

- [docs/chronicle-file-format.md](../docs/chronicle-file-format.md) — canonical description of the .chronicle format
- [chronicle/store/schema.py](../chronicle/store/schema.py) — DDL for events and read model (EVENTS_DDL, READ_MODEL_DDL, CLAIM_DDL, EVIDENCE_SPAN_DDL, EVIDENCE_LINK_DDL, TENSION_DDL, etc.)
- [chronicle/store/schema.sql](../chronicle/store/schema.sql) — event store DDL (mirrors schema.py for event store)
- [tools/verify_chronicle/verify_chronicle.py](../tools/verify_chronicle/verify_chronicle.py) — what the verifier requires (manifest, schema_version, required tables, evidence hashes)
- [docs/consuming-chronicle.md](../docs/consuming-chronicle.md) — how to read a .chronicle from another language or tool

---

## 1. Top-level layout

A **.chronicle** file is a **ZIP** with three kinds of content:

| Path in ZIP | Role |
|-------------|------|
| **manifest.json** | Metadata and integrity: format version, investigation UID, title, exported_at, optional content_hash_manifest (evidence_uid → SHA-256). |
| **chronicle.db** | SQLite: **event store** (append-only events) and **read model** (investigation, claim, evidence_item, evidence_span, evidence_link, tension, source, etc.). |
| **evidence/** | One file per evidence **item**. Paths come from `evidence_item.uri` (e.g. `evidence/evidence_<uid>.txt`). Content is raw bytes (e.g. UTF-8 text). |

The **structure**—which claim is supported by which evidence, which claims are in tension—lives in **chronicle.db**, not in the evidence file names or contents. Evidence files are just blobs.

See **docs/chronicle-file-format.md** Section 1 for the exact layout and Section 2 for why it looks like “just sentences in separate files” (e.g. one file per transcript row).

---

## 2. Manifest (manifest.json)

Required keys (verifier rejects if missing):

- **format_version** — Integer ≥ 1. Used for compatibility.
- **investigation_uid** — Identifies the investigation in this package.

Often present: **title**, **exported_at**, **content_hash_manifest** (evidence_uid → SHA-256 hex), **redacted_evidence**, and optional policy fields (**built_under_policy_id**, etc.). The verifier checks that required keys exist and format_version is an integer ≥ 1. See **docs/chronicle-file-format.md** Section 3.

---

## 3. Database (chronicle.db): event store

Open **chronicle/store/schema.py**. The **events** table (EVENTS_DDL) stores every change as an append-only log:

- **event_id**, **event_type** — Identity and kind (e.g. EvidenceIngested, ClaimProposed, SupportLinked, TensionDeclared).
- **occurred_at**, **recorded_at** — Timestamps.
- **investigation_uid**, **subject_uid** — Which investigation and which entity (claim_uid, evidence_uid, etc.).
- **actor_type**, **actor_id** — Who did it (human, tool, system).
- **payload** — JSON: event-specific data (e.g. claim_text, span_uid, link_type).
- **idempotency_key**, **prev_event_hash**, **event_hash** — Deduplication and chain integrity.
- **workspace**, **policy_profile_id**, **correlation_id**, **causation_id**, **envelope_version**, **payload_version** — Optional/metadata.

**schema_version** table records component versions (e.g. event_store, read_model). The verifier requires **schema_version** and **events** (and read-model tables below). The **read model** is derived by projecting these events; see Lesson 05.

---

## 4. Database (chronicle.db): read model

The read model is built by **projection** (Lesson 05). Its tables are defined in **chronicle/store/schema.py**:

- **investigation** — One row per investigation (uid, title, description, created_at, …).
- **evidence_item** — One row per evidence (evidence_uid, investigation_uid, uri, content_hash, media_type, integrity_status, …). **uri** is the path inside the ZIP (e.g. `evidence/evidence_<uid>.txt`).
- **evidence_span** — Spans within evidence (span_uid, evidence_uid, anchor_type, anchor_json, …). Support/challenge links reference **spans**, not raw items.
- **claim** — One row per claim (claim_uid, investigation_uid, claim_text, current_status, claim_type, temporal_json, …).
- **evidence_link** — Links from span to claim: **link_uid**, **span_uid**, **claim_uid**, **link_type** (SUPPORT | CHALLENGE), optional strength, rationale.
- **tension** — Tensions between claims: **tension_uid**, **claim_a_uid**, **claim_b_uid**, **status** (OPEN, ACK, RESOLVED), notes.
- **source** — Source entities (optional); **evidence_source_link** links spans to sources (for independent_sources_count).
- **processed_event** — Projection checkpoint (which events have been applied).
- Other tables (claim_assertion, evidence_link_retraction, claim_decomposition, tension_suggestion, tier_history, etc.) exist for specific features; the verifier only requires that **events**, **schema_version**, **investigation**, **claim**, **evidence_item** exist. See **tools/verify_chronicle/verify_chronicle.py** (`verify_db_schema`) for the exact required set.

So: “this evidence span supports this claim” = row in **evidence_link** with link_type=SUPPORT; “these two claims are in tension” = row in **tension**. All of that is in the DB.

---

## 5. Evidence files (evidence/)

- Stored under **evidence/** inside the ZIP.
- **URI** for each item is in **evidence_item.uri** (relative path; no `..`; verifier rejects path traversal).
- **Content** is raw bytes (e.g. UTF-8 text). No structure inside the file—just the blob.
- **Integrity:** The verifier hashes each file and compares to **content_hash** in the DB (or in manifest’s content_hash_manifest). Mismatch → verification fails.

See **docs/chronicle-file-format.md** Section 5.

---

## 6. What the verifier checks (recap)

Lesson 03 covers the verifier in depth. In terms of **file format and schema**:

- **Manifest:** Required keys and format_version ≥ 1.
- **Schema:** schema_version table and required tables (events, investigation, claim, evidence_item, etc.).
- **Evidence:** Each evidence file in the ZIP exists at the path in evidence_item.uri; its SHA-256 matches content_hash. Path must not be absolute or contain `..`.

The verifier does **not** check event semantics, referential integrity, truth of claims, or source independence. See [Lesson 03](03-the-verifier.md) and [docs/verification-guarantees.md](../docs/verification-guarantees.md).

---

## 7. Relationship to export and import

- **Export** (Lesson 10): Writes one investigation to a .chronicle by selecting that investigation’s events, building a DB with only those events (and projected read model), copying evidence files, writing manifest, and zipping.
- **Import:** Reads a .chronicle ZIP, appends its events into the project’s event store, copies evidence, and lets the project’s projection update the read model.

So the **.chronicle format** is exactly what export produces and import consumes. Consuming from another language/tool: see **docs/consuming-chronicle.md** (open ZIP, read manifest, query SQLite, resolve evidence by URI).

---

## Try it

1. Generate a sample .chronicle: `PYTHONPATH=. python3 scripts/generate_sample_chronicle.py`. Unzip it and list the top level: **manifest.json**, **chronicle.db**, **evidence/**.
2. Open **chronicle.db** with `sqlite3 chronicle.db`. Run `.tables` and confirm you see **events**, **investigation**, **claim**, **evidence_item**, **evidence_span**, **evidence_link**, **tension**.
3. Run: `SELECT claim_uid, claim_text FROM claim LIMIT 3;` and `SELECT link_uid, span_uid, claim_uid, link_type FROM evidence_link LIMIT 5;`. Relate these to the structure described in this lesson.
4. Run **chronicle-verify** on the .chronicle and confirm it passes.

---

## Summary

- **.chronicle** = ZIP with **manifest.json**, **chronicle.db** (events + read model), and **evidence/** (one file per evidence item; paths in evidence_item.uri).
- **Schema:** Events table (append-only) + read-model tables (investigation, claim, evidence_item, evidence_span, evidence_link, tension, source, etc.) defined in **chronicle/store/schema.py**. Structure (support, challenge, tension) is in the DB; evidence files are raw blobs.
- **Manifest** must have format_version and investigation_uid; often includes title, exported_at, content_hash_manifest.
- **Verifier** checks manifest, required DB tables, and evidence hashes; it does not validate semantics or truth. For full format and consuming from other tools, use **docs/chronicle-file-format.md** and **docs/consuming-chronicle.md**.

---

**← Previous:** [Lesson 11: Interoperability, API, and tests](11-interoperability-api-and-tests.md) | **Index:** [Lessons](README.md) | **Next →:** [Lesson 13: Release readiness, security gates, and standards operations](13-release-readiness-security-and-standards.md)

**Quiz:** [quizzes/quiz-12-chronicle-file-format-and-schema.md](quizzes/quiz-12-chronicle-file-format-and-schema.md)
