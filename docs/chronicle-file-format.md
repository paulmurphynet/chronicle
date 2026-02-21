# The .chronicle file format

A .chronicle file is a ZIP that contains three kinds of content. What you see when you unzip (e.g. lots of small text files under `evidence/`) is only the evidence blobs. The structure—who said what, which evidence supports which claim, tensions—lives in the database and the manifest.

---

## 1. Top-level layout

```
file.chronicle (ZIP)
├── manifest.json          # Required: format version, investigation id, title, hashes
├── chronicle.db           # SQLite: event log + read model (claims, evidence, links, tensions)
└── evidence/              # One file per evidence item (raw content only)
    ├── evidence_<uid>.txt
    ├── evidence_<uid>.txt
    └── ...
```

- **manifest.json** — Metadata and integrity: `format_version`, `investigation_uid`, `title`, `exported_at`, optional policy info, and a content_hash_manifest (evidence_uid → SHA-256 of the file). The verifier checks that each evidence file in the ZIP matches its hash in the manifest or in the DB.
- **chronicle.db** — The actual structure. It has an event store (append-only log of what happened) and a read model (tables built from those events): investigations, claims, evidence items, spans, links (support/challenge), tensions, sources, etc. So “this claim is supported by this evidence span” and “these two claims are in tension” are in the DB, not in the evidence file names or contents.
- **evidence/** — One file per evidence item. The path is stored in `evidence_item.uri` (e.g. `evidence/evidence_0eacc56c424a40e0adc8b3f5abe98f2c.txt`). The file is just the raw content (e.g. one line of testimony). So for a transcript ingest you get many small text files—that’s expected. The meaning (that this file is evidence for *this* claim, and that claim is in tension with *that* one) is in the database.

---

## 2. Why it looks like “just sentences in separate files”

For the Lizzie Borden transcript ingest we create one evidence item per CSV row. Each item’s content is stored as one file under `evidence/` (with a generated name, often based on content hash or UID). So when you unzip you see:

- Many small `.txt` files, each containing one sentence (one row of testimony).

That’s only the evidence layer. The rest is in chronicle.db:

- **claim** — One row per claim; `claim_text` is e.g. `"Lizzie Borden: I think in my room up stairs."`; `claim_uid` identifies it.
- **evidence_item** — One row per evidence file; `evidence_uid`, `uri` (path inside the ZIP), `content_hash`, `investigation_uid`.
- **evidence_span** — Spans within evidence (for the transcript, we created one span per evidence item, covering the whole content).
- **evidence_link** — Links from span to claim with type SUPPORT or CHALLENGE; this is the “this evidence supports this claim” relationship.
- **tension** — Rows linking two claims (claim_a_uid, claim_b_uid, status, …).

So the format is: ZIP + manifest + DB + evidence files. The evidence files are just blobs; the schema (claims, links, tensions) is in the database.

---

## 3. Manifest (manifest.json)

Required keys:

| Key | Description |
|-----|-------------|
| `format_version` | Integer ≥ 1. Verifier rejects older versions. |
| `investigation_uid` | Identifies the investigation. |

Often present: `title`, `exported_at`, `content_hash_manifest` (evidence_uid → SHA-256 hex), `redacted_evidence`, and optional policy fields (`built_under_policy_id`, etc.).

---

## 4. Database (chronicle.db)

SQLite with at least:

- **events** — Append-only event log (EvidenceIngested, ClaimProposed, SupportLinked, TensionDeclared, etc.). The source of truth; the read model is derived from it.
- **schema_version** — Versions for event_store and read_model.
- **investigation** — One row per investigation (uid, title, …).
- **claim** — One row per claim (claim_uid, investigation_uid, claim_text, current_status, …).
- **evidence_item** — One row per evidence (evidence_uid, investigation_uid, uri, content_hash, …).
- **evidence_span** — Spans within evidence (span_uid, evidence_uid, anchor type, start/end, …).
- **evidence_link** — Links from span to claim (link_uid, span_uid, claim_uid, link_type: SUPPORT | CHALLENGE).
- **tension** — Tensions between claims (tension_uid, claim_a_uid, claim_b_uid, status, …).

Other tables (source, actor, etc.) may exist depending on the schema version. The verifier only requires that certain tables exist; it does not validate semantics.

---

## 5. Evidence files (evidence/*)

- Stored under the evidence/ prefix inside the ZIP.
- URI for each evidence item is in `evidence_item.uri` (e.g. `evidence/evidence_<id>.txt`).
- Content is the raw bytes (e.g. UTF-8 text). No structure inside the file—just the blob.
- **Integrity**: verifier hashes each file and compares to `content_hash` in the DB (or manifest).

So: the .chronicle format is ZIP + manifest + SQLite + evidence blobs. The “contains” / support / tension relationships are in the database, not in the evidence file names or contents. If you want to inspect or query structure, open chronicle.db (e.g. with sqlite3 or a DB browser) and look at the claim, evidence_link, and tension tables.

Consuming without the Chronicle package: To read a .chronicle from another language or tool (e.g. fact-checking UI, dashboard), see [Consuming .chronicle](consuming-chronicle.md) for step-by-step instructions (open ZIP, read manifest, query SQLite, resolve evidence files).
