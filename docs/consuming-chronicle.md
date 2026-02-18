# Consuming a .chronicle file without the Chronicle Python package

This doc describes how to **read** a `.chronicle` file (ZIP) and extract investigations, claims, evidence, and links **without** installing the Chronicle Python package. Use this when you're building a downstream tool (e.g. fact-checking UI, dashboard, or converter) that only needs to consume the data.

---

## 1. What’s in the ZIP

A `.chronicle` file is a ZIP containing:

| Entry | Description |
|-------|-------------|
| **manifest.json** | JSON: `format_version`, `investigation_uid`, `title`, `exported_at`, optional `content_hash_manifest` (evidence_uid → SHA-256 hex). |
| **chronicle.db** | SQLite 3 database: event log + read model tables. |
| **evidence/** | Directory of files; each file is one evidence item’s raw content. Path = `evidence_item.uri` in the DB. |

See [Chronicle file format](chronicle-file-format.md) for the full layout and semantics.

---

## 2. Steps to consume (any language)

1. **Open the ZIP** — Use your language’s ZIP library (e.g. Python `zipfile`, Node `adm-zip`, Java `ZipInputStream`). Do not rely on unzipping to disk if you want to avoid path traversal; read entries by name.
2. **Read manifest.json** — Parse JSON. You get `investigation_uid`, `title`, and optionally `content_hash_manifest`. Validate `format_version` ≥ 1 if you care about compatibility.
3. **Open chronicle.db** — Either extract it to a temp file and open with SQLite, or (in some runtimes) open from the ZIP stream if your SQLite driver supports it. Enable foreign keys if you use them: `PRAGMA foreign_keys = ON;`.
4. **Query the read model** — The DB has tables such as:
   - **investigation** — `investigation_uid`, `title`, `description`, etc.
   - **claim** — `claim_uid`, `investigation_uid`, `claim_text`, `current_status`, etc.
   - **evidence_item** — `evidence_uid`, `investigation_uid`, `uri`, `content_hash`, etc.
   - **evidence_span** — `span_uid`, `evidence_uid`, anchor fields, etc.
   - **evidence_link** — `link_uid`, `span_uid`, `claim_uid`, `link_type` (SUPPORT or CHALLENGE).
   - **tension** — `tension_uid`, `claim_a_uid`, `claim_b_uid`, `status`, `notes`, etc.
5. **Resolve evidence content** — For each `evidence_item`, the `uri` (e.g. `evidence/evidence_abc123.txt`) is the path inside the ZIP. Read that entry from the ZIP to get the raw bytes. Decode as UTF-8 if the content is text. Optionally verify against `content_hash` (SHA-256 of the bytes) if you need integrity.

---

## 3. Example: list claims and their support counts (pseudocode)

```
open zip from path
manifest = json.parse(zip.read("manifest.json"))
db = sqlite.open(zip.read("chronicle.db"))  # or extract to temp file

claims = db.query("SELECT claim_uid, claim_text FROM claim WHERE investigation_uid = ?", manifest.investigation_uid)
for claim in claims:
  links = db.query("SELECT link_type FROM evidence_link WHERE claim_uid = ?", claim.claim_uid)
  support_count = count(links where link_type = 'SUPPORT')
  challenge_count = count(links where link_type = 'CHALLENGE')
  print claim.claim_uid, claim.claim_text, support_count, challenge_count
```

---

## 4. Schema details (read model)

Table and column names follow the Chronicle read model. Key tables:

- **claim** — `claim_uid` (PK), `investigation_uid`, `claim_text`, `current_status`, `claim_type`, `decomposition_status`, `temporal_json`, etc.
- **evidence_item** — `evidence_uid` (PK), `investigation_uid`, `uri`, `content_hash`, `media_type`, etc.
- **evidence_span** — `span_uid` (PK), `evidence_uid`, `anchor_type`, `anchor_start`, `anchor_end`, `quote`, etc.
- **evidence_link** — `link_uid` (PK), `span_uid`, `claim_uid`, `link_type` (SUPPORT | CHALLENGE), optional `strength`, optional `rationale` (warrant: why this evidence supports/challenges this claim). Check for **evidence_link_retraction** table: if a link_uid appears there, treat as retracted.
- **tension** — `tension_uid` (PK), `claim_a_uid`, `claim_b_uid`, `status` (OPEN, ACK, RESOLVED), `tension_kind`, `notes`.

For full schema (column list and types), inspect the DB with `sqlite3 chronicle.db ".schema"` after extracting, or see the Chronicle source: `chronicle/store/schema.py` (read model section).

---

## 5. Integrity (optional)

- **Manifest** — `content_hash_manifest` maps evidence_uid to SHA-256 (hex) of the file at `evidence_item.uri`. After reading each evidence file from the ZIP, hash the bytes and compare to the manifest (or to `evidence_item.content_hash` in the DB).
- **Verifier** — To validate the whole package (manifest, DB schema, evidence hashes, append-only ledger), use the official verifier: `chronicle-verify path/to/file.chronicle`. See [Verifier](verifier.md). This doc is for **consuming** the content; verification is a separate step.

---

## 6. Summary

You can consume a .chronicle with any stack: open the ZIP, read **manifest.json**, open **chronicle.db** with SQLite, query the read model tables, and read evidence files from the ZIP by **uri**. No Chronicle Python package required. For full format and schema details, see [Chronicle file format](chronicle-file-format.md).
