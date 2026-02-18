# Lesson 10: Export, import, and Neo4j

**Objectives:** You’ll understand how an investigation is **exported** to a .chronicle file (ZIP with manifest, DB, evidence), how **import** merges a .chronicle into a project, and how the **Neo4j sync** pushes the read model to a graph (e.g. Aura) for visualization and graph RAG.

**Key files:**

- [chronicle/store/export_import.py](../chronicle/store/export_import.py) — export_investigation, import_investigation
- [chronicle/store/neo4j_sync.py](../chronicle/store/neo4j_sync.py) — sync_project_to_neo4j
- [docs/chronicle-file-format.md](../docs/chronicle-file-format.md) — what’s inside a .chronicle
- [docs/consuming-chronicle.md](../docs/consuming-chronicle.md) — how to read a .chronicle from another language or tool (ZIP, manifest, SQLite, evidence)
- [docs/GENERIC_EXPORT.md](../docs/GENERIC_EXPORT.md) — export investigation as JSON or CSV ZIP (no evidence blobs) for BI/dashboards
- [docs/neo4j-schema.md](../docs/neo4j-schema.md) — node labels, relationship types, and example Cypher for the sync output
- [docs/aura-graph-pipeline.md](../docs/aura-graph-pipeline.md) — verify → import → sync runbook

---

## Export: investigation → .chronicle

Open **chronicle/store/export_import.py**.

- **export_investigation(project_dir, investigation_uid, output_path)** (around line 63):
  1. Loads the project’s event store and read model.
  2. Selects all **events** for that investigation from the event store.
  3. Builds a **new** SQLite DB containing only those events and runs the **projection** so the new DB has the read model for that investigation only.
  4. Copies **evidence files** referenced by the read model into a temp directory under **evidence/** (paths from evidence_item.uri).
  5. Writes **manifest.json** (format_version, investigation_uid, title, exported_at, optional content_hash_manifest, redacted_evidence).
  6. Zips the temp dir (chronicle.db, manifest.json, evidence/) into **output_path** (.chronicle file).

So a .chronicle is a **self-contained snapshot** of one investigation: you can send it to someone and they can verify it (manifest, schema, evidence hashes) without your project or API.

## Import: .chronicle → project

- **import_investigation(project_dir, chronicle_path)** (around line 453):
  1. Opens the .chronicle ZIP, reads **manifest.json**, gets investigation_uid.
  2. Extracts **chronicle.db** and reads the **events** from it (or replays them).
  3. **Appends** those events into the **project’s** event store (with idempotency so duplicate import doesn’t double events when possible).
  4. Copies **evidence** files from the ZIP into the project’s evidence store.
  5. The project’s **projection** runs on the new events, so the read model now includes the imported investigation.

So import is **merge**: the project accumulates investigations. Script **ingest_chronicle_to_aura.py** does verify → import into a “graph project” → sync to Neo4j.

## Neo4j sync

Open **chronicle/store/neo4j_sync.py**.

- **sync_project_to_neo4j(project_dir, uri, user, password, ...)** (or equivalent):
  1. Opens the project’s read model (from its chronicle.db).
  2. Reads **all** investigations, claims, evidence items, evidence spans, evidence links, tensions, sources (if any).
  3. Pushes them to Neo4j using **MERGE** (by UID) so the graph has nodes for Investigation, Claim, EvidenceItem, EvidenceSpan, Tension, etc., and relationships: CONTAINS, SUPPORTS, CHALLENGES, BETWEEN (tension), etc.

So the **same** data you have in SQLite (read model) is mirrored in Neo4j for graph queries, visualization (e.g. Aura Browser), or graph RAG. Sync is **idempotent**: re-syncing the same project updates the graph to match the project.

**Graph schema reference:** **docs/neo4j-schema.md** documents node labels (Investigation, Claim, EvidenceItem, EvidenceSpan, Tension, etc.), relationship types (CONTAINS, SUPPORTS, CHALLENGES, BETWEEN, …), and example Cypher queries (e.g. claims in tension, evidence supporting a claim). Use it when building graph RAG or custom queries without reverse-engineering the sync output.

## .chronicle file format (recap)

From **docs/chronicle-file-format.md**:

- **manifest.json** — format_version, investigation_uid, title, exported_at, optional content_hash_manifest.
- **chronicle.db** — SQLite with events table and read model tables (investigation, claim, evidence_item, evidence_span, evidence_link, tension, …).
- **evidence/** — One file per evidence item; path in evidence_item.uri. Content is the raw blob (e.g. text). The **structure** (who said what, support, tensions) is in the DB, not in the filenames.

**Consuming without the Chronicle package:** If you need to read a .chronicle from another language or tool (e.g. fact-checking UI, dashboard), see **docs/consuming-chronicle.md**: open the ZIP, read manifest and chronicle.db, resolve evidence by URI. The verifier (`chronicle-verify`) can still validate the file.

**Generic export:** For BI or dashboards you may not need the full .chronicle. **docs/GENERIC_EXPORT.md** describes exporting an investigation as **JSON** or **CSV ZIP** (claims, evidence metadata, tensions; no evidence blobs). Use the session and **build_generic_export_json** or **build_generic_export_csv_zip** from the store commands. For fact-checking UIs and dashboards, **build_claim_evidence_metrics_export** returns the stable claim+evidence refs+defensibility shape; see [claim-evidence-metrics-export](../docs/claim-evidence-metrics-export.md).

## Try it

1. Generate a sample .chronicle: **PYTHONPATH=. python3 scripts/generate_sample_chronicle.py** (or use an existing one). Run **chronicle-verify path/to/file.chronicle** and confirm it passes.
2. Unzip the .chronicle and list its contents: **manifest.json**, **chronicle.db**, **evidence/**.
3. If you have Neo4j (or Aura) credentials, run **chronicle neo4j-sync --path /path/to/project** and inspect the graph in Neo4j Browser (nodes and relationships).

## Summary

- **Export** writes one investigation to a .chronicle (ZIP: manifest, DB subset, evidence files). **Import** merges a .chronicle into a project by appending its events and copying evidence.
- **Neo4j sync** pushes the project’s read model to Neo4j so you can query or visualize the graph (claims, evidence, support, tensions).
- The **verifier** checks .chronicle files; the **Aura pipeline** (verify → import → sync) is the full runbook for getting Chronicle data into a shared graph.

**Quiz:** [quizzes/quiz-10-export-import-neo4j.md](quizzes/quiz-10-export-import-neo4j.md)
