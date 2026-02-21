# Lesson 10: Export, import, and Neo4j

Objectives: You’ll understand how an investigation is exported to a .chronicle file (ZIP with manifest, DB, evidence), how import merges a .chronicle into a project, how signed bundle wrapping works for `.chronicle` handoff, and how Neo4j export/sync project the read model to a graph (e.g. Aura) with observability, hardening controls, and live integration validation.

**Key files:**

- [chronicle/store/export_import.py](../chronicle/store/export_import.py) — export_investigation, import_investigation
- [chronicle/store/neo4j_export.py](../chronicle/store/neo4j_export.py) — export_project_to_neo4j_csv (streaming CSV export + report/progress)
- [chronicle/store/neo4j_sync.py](../chronicle/store/neo4j_sync.py) — sync_project_to_neo4j
- [docs/chronicle-file-format.md](../docs/chronicle-file-format.md) — what’s inside a .chronicle
- [docs/consuming-chronicle.md](../docs/consuming-chronicle.md) — how to read a .chronicle from another language or tool (ZIP, manifest, SQLite, evidence)
- [docs/GENERIC_EXPORT.md](../docs/GENERIC_EXPORT.md) — export investigation as JSON or CSV ZIP (no evidence blobs) for BI/dashboards
- [docs/integration-export-hardening.md](../docs/integration-export-hardening.md) — contract hardening for JSON/CSV/Markdown/signed-bundle import-export paths
- [docs/neo4j-schema.md](../docs/neo4j-schema.md) — node labels, relationship types, and example Cypher for the sync output
- [docs/neo4j.md](../docs/neo4j.md) — Neo4j usage guide, observability flags, and live test workflow
- [docs/aura-graph-pipeline.md](../docs/aura-graph-pipeline.md) — verify → import → sync runbook
- [docs/neo4j-operations-runbook.md](../docs/neo4j-operations-runbook.md) — production operations posture (backup/restore, drift handling, capacity/cost guardrails)
- [docs/neo4j-query-pack.md](../docs/neo4j-query-pack.md) — operational Cypher query set + index guidance
- [scripts/benchmark_data/run_neo4j_projection_benchmark.py](../scripts/benchmark_data/run_neo4j_projection_benchmark.py) — projection benchmark harness with threshold gates
- [tests/test_neo4j_live_integration.py](../tests/test_neo4j_live_integration.py) — live Neo4j integration assertions (dedupe and non-dedupe)

---

## Export: investigation → .chronicle

Open chronicle/store/export_import.py.

- **export_investigation(project_dir, investigation_uid, output_path)**:
  1. Loads the project’s event store and read model.
  2. Selects all events for that investigation from the event store.
  3. Builds a new SQLite DB containing only those events and runs the projection so the new DB has the read model for that investigation only.
  4. Copies evidence files referenced by the read model into a temp directory under evidence/ (paths from evidence_item.uri).
  5. Writes manifest.json (format_version, investigation_uid, title, exported_at, optional content_hash_manifest, redacted_evidence).
  6. Zips the temp dir (chronicle.db, manifest.json, evidence/) into output_path (.chronicle file).

So a .chronicle is a self-contained snapshot of one investigation: you can send it to someone and they can verify it (manifest, schema, evidence hashes) without your project or API.

## Import: .chronicle → project

- **import_investigation(chronicle_path, target_dir)**:
  1. Opens the .chronicle ZIP, reads manifest.json, gets investigation_uid.
  2. Extracts chronicle.db and reads the events from it (or replays them).
  3. Appends those events into the project’s event store (with idempotency so duplicate import doesn’t double events when possible).
  4. Copies evidence files from the ZIP into the project’s evidence store.
  5. The project’s projection runs on the new events, so the read model now includes the imported investigation.

So import is merge: the project accumulates investigations. Script ingest_chronicle_to_aura.py does verify → import into a “graph project” → sync to Neo4j.

## Signed bundle wrapper for `.chronicle` handoff

The export/import module also supports a digest-verified signed bundle wrapper for `.chronicle` archives:

- **export_signed_investigation_bundle(...)** — wraps one `.chronicle` archive in a ZIP bundle with `signature_manifest.json` and archive SHA-256.
- **verify_signed_investigation_bundle(...)** — verifies bundle structure, digest integrity, and nested `.chronicle` verifier checks.
- **import_signed_investigation_bundle(...)** — verifies then imports the nested `.chronicle` into a target project.

By default this is metadata-oriented (`signature.status = metadata_only`) unless an external signature value is supplied. See [integration export hardening](../docs/integration-export-hardening.md).

## Neo4j export and sync

Open chronicle/store/neo4j_export.py and chronicle/store/neo4j_sync.py.

- **export_project_to_neo4j_csv(project_dir, output_dir, ...)**:
  1. Streams read-model rows in chunks (bounded memory).
  2. Writes deterministic CSVs for rebuild scripts.
  3. Can emit structured progress events and an optional JSON report artifact.

- **sync_project_to_neo4j(project_dir, uri, user, password, ...)**:
  1. Opens the project’s read model (from its chronicle.db).
  2. Runs schema, nodes, relationships, and retractions phases against Neo4j.
  3. Uses MERGE semantics for idempotent re-sync behavior.
  4. Supports dedupe mode (claim/evidence content-hash identity + lineage edges).
  5. Supports hardening controls (`--database`, retries/backoff, connection timeout).
  6. Can emit structured progress events and an optional JSON report artifact.

So the same data in SQLite (read model) is mirrored in Neo4j for graph queries, visualization (e.g. Aura Browser), or graph RAG. Sync is idempotent: re-syncing the same project updates the graph to match the project.

Before running export/import/sync in production workflows, run:

```bash
PYTHONPATH=. python3 scripts/check_neo4j_contract.py
```

This checks parity across sync code, CSV export, rebuild Cypher files, and schema docs so drift is caught early.

For throughput/memory baselines and threshold gating, run:

```bash
PYTHONPATH=. python3 scripts/benchmark_data/run_neo4j_projection_benchmark.py --output reports/neo4j_projection_benchmark.json
```

For runtime validation against a real Neo4j instance, run the live integration suite:

```bash
export CHRONICLE_RUN_NEO4J_LIVE_TESTS=1
export NEO4J_URI=bolt://127.0.0.1:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=chronicle_dev_password
CHRONICLE_EVENT_STORE=sqlite pytest tests/test_neo4j_live_integration.py -q
```

Graph schema reference: docs/neo4j-schema.md documents node labels (Investigation, Claim, EvidenceItem, EvidenceSpan, Tension, etc.), relationship types (CONTAINS, SUPPORTS, CHALLENGES, BETWEEN, …), and example Cypher queries (e.g. claims in tension, evidence supporting a claim). Use it when building graph RAG or custom queries without reverse-engineering the sync output.

## .chronicle file format (recap)

For full coverage of the .chronicle format and data schema (manifest, all DB tables, evidence integrity), see [Lesson 12: The .chronicle file format and data schema](12-chronicle-file-format-and-schema.md). From docs/chronicle-file-format.md:

- **manifest.json** — format_version, investigation_uid, title, exported_at, optional content_hash_manifest.
- **chronicle.db** — SQLite with events table and read model tables (investigation, claim, evidence_item, evidence_span, evidence_link, tension, …).
- **evidence/** — One file per evidence item; path in evidence_item.uri. Content is the raw blob (e.g. text). The structure (who said what, support, tensions) is in the DB, not in the filenames.

Consuming without the Chronicle package: If you need to read a .chronicle from another language or tool (e.g. fact-checking UI, dashboard), see docs/consuming-chronicle.md: open the ZIP, read manifest and chronicle.db, resolve evidence by URI. The verifier (`chronicle-verify`) can still validate the file.

Generic export: For BI or dashboards you may not need the full .chronicle. docs/GENERIC_EXPORT.md describes exporting an investigation as JSON or CSV ZIP (claims, evidence metadata, tensions; no evidence blobs). Use the session and build_generic_export_json or build_generic_export_csv_zip from the store commands. Contract validators validate_generic_export_json and validate_generic_export_csv_zip are available for adapter/API release checks. For fact-checking UIs and dashboards, build_claim_evidence_metrics_export returns the stable claim+evidence refs+defensibility shape; see [claim-evidence-metrics-export](../docs/claim-evidence-metrics-export.md).

## Try it

1. Generate a sample .chronicle: PYTHONPATH=. python3 scripts/generate_sample_chronicle.py (or use an existing one). Run chronicle-verify path/to/file.chronicle and confirm it passes.
2. Unzip the .chronicle and list its contents: manifest.json, chronicle.db, evidence/.
3. Run `PYTHONPATH=. python3 scripts/check_integration_export_contracts.py --project-path /tmp/chronicle_lesson10_contract_project --output-dir /tmp/chronicle_lesson10_contract_out` and inspect JSON/CSV/Markdown/`.chronicle`/signed-bundle outputs.
4. If you have Neo4j credentials, run:
   - `chronicle neo4j-export --path /path/to/project --output /tmp/neo4j_import --report /tmp/neo4j_export_report.json --progress`
   - `chronicle neo4j-sync --path /path/to/project --report /tmp/neo4j_sync_report.json --progress`
   - `PYTHONPATH=. python3 scripts/benchmark_data/run_neo4j_projection_benchmark.py --run-sync --neo4j-uri "$NEO4J_URI" --neo4j-password "$NEO4J_PASSWORD" --output /tmp/neo4j_projection_benchmark.json`
   Then inspect the graph and report artifacts.

## Summary

- Export writes one investigation to a .chronicle (ZIP: manifest, DB subset, evidence files). Import merges a .chronicle into a project by appending its events and copying evidence.
- Signed bundle helpers can wrap `.chronicle` exports in a digest-verified bundle for interoperability handoff while preserving the canonical verifier path.
- Neo4j export/sync project the read model to Neo4j with chunked processing, idempotent semantics, observability outputs, and retry/timeout controls.
- The verifier checks .chronicle files; the Aura pipeline (verify → import → sync) is the full runbook for getting Chronicle data into a shared graph.
- The Neo4j operations runbook and query pack define production ops posture and recurring analytical checks.

← Previous: [Lesson 09: Epistemic tools](09-epistemic-tools.md) | Index: [Lessons](README.md) | Next →: [Lesson 11: Interoperability, API, and tests](11-interoperability-api-and-tests.md)

Quiz: [quizzes/quiz-10-export-import-neo4j.md](quizzes/quiz-10-export-import-neo4j.md)
