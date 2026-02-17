# Generic export (JSON and CSV ZIP)

Chronicle can export a single investigation’s **read model** as generic JSON or as a ZIP of CSV files. Use this when you need to feed Chronicle data into BI tools, fact-checking pipelines, dashboards, or other systems that don’t consume the full .chronicle format.

---

## 1. JSON export

**API:** `chronicle.store.commands.generic_export.build_generic_export_json(read_model, investigation_uid)`

**Returns:** A single dict with:

| Key | Content |
|-----|---------|
| `schema_version` | Integer (currently 1). |
| `schema_doc` | URL to this doc. |
| `investigation` | One object: investigation fields (investigation_uid, title, description, created_at, etc.) as a flat dict. |
| `claims` | List of claim objects (claim_uid, investigation_uid, claim_text, current_status, claim_type, etc.). |
| `evidence` | List of evidence_item objects (evidence_uid, investigation_uid, uri, content_hash, media_type, etc.). |
| `tensions` | List of tension objects (tension_uid, claim_a_uid, claim_b_uid, status, notes, etc.). |

Field names and types follow the Chronicle read model (dataclass attribute names; values are serialized for JSON). No evidence **content** is included—only metadata. To get content, use the project’s evidence store or a .chronicle file (see [Consuming .chronicle](consuming-chronicle.md)).

**Example use:** Export from a session after opening a project:

```python
from chronicle.store.session import ChronicleSession
from chronicle.store.commands.generic_export import build_generic_export_json

with ChronicleSession(project_path) as session:
    data = build_generic_export_json(session.read_model, investigation_uid)
    # data["claims"], data["evidence"], data["tensions"] → feed to BI, dashboard, or pipeline
```

---

## 2. CSV ZIP export

**API:** `chronicle.store.commands.generic_export.build_generic_export_csv_zip(read_model, investigation_uid)`

**Returns:** Bytes of a ZIP file containing:

| File inside ZIP | Content |
|-----------------|---------|
| `investigations.csv` | One row: the investigation (columns = investigation attributes). |
| `claims.csv` | One row per claim. |
| `evidence.csv` | One row per evidence item. |
| `tensions.csv` | One row per tension. |

CSV columns are the same attribute names as in the JSON objects (e.g. claim_uid, claim_text, current_status). No evidence content—only metadata. Use for Excel, Google Sheets, or ETL into a data warehouse.

**Example use:**

```python
from chronicle.store.commands.generic_export import build_generic_export_csv_zip

with ChronicleSession(project_path) as session:
    zip_bytes = build_generic_export_csv_zip(session.read_model, investigation_uid)
    Path("export.zip").write_bytes(zip_bytes)
```

---

## 3. What’s not included

- **Evidence blobs** — Generic export does not include the raw content of evidence items. Use the project’s evidence store (by `evidence_item.uri`) or extract from a .chronicle ZIP.
- **Evidence links** — The JSON and CSV export include claims, evidence items, and tensions but not the **evidence_link** table (span → claim, SUPPORT/CHALLENGE). For link data, query the read model directly or use a .chronicle and open chronicle.db (see [Consuming .chronicle](consuming-chronicle.md)).
- **Events** — Only the read model (current state) is exported, not the event log.

For full fidelity (events, links, evidence content), use **export_investigation** to produce a .chronicle file.

---

## 4. Consumer use cases

- **BI / dashboards** — Import investigations.csv, claims.csv, evidence.csv, tensions.csv into your tool; join on investigation_uid and claim_uid. Build reports on claim counts, tension counts, etc.
- **Fact-checking pipeline** — Consume the JSON export; map claims and tensions to your workflow (e.g. “flag claims with open tensions” or “list claims with no support”).
- **Audit / compliance** — Export periodically to CSV or JSON for archival or compliance tooling.

---

## 5. Schema version

`schema_version` is currently **1**. If the shape or field set of the export changes in a breaking way, the version will be incremented and noted here. Consumers should check `schema_version` and handle unknown versions gracefully.
