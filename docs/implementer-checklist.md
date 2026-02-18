# Implementer checklist

For anyone building a **producer** (tool that creates .chronicle files) or **consumer** (viewer, validator, or converter). For RAG pipelines and session integration, see [Integrating with Chronicle](integrating-with-chronicle.md).

---

## Checklist

| Goal | Step | Reference |
|------|------|-----------|
| **Produce** a valid .chronicle | Build a ZIP with `manifest.json`, `chronicle.db`, and `evidence/`; satisfy producer conformance. | [Chronicle file format](chronicle-file-format.md); [Conformance](conformance.md) |
| **Consume** or verify a .chronicle | Run the reference verifier or implement the same checks (manifest, schema, evidence hashes). | [Verifier](verifier.md); [Verification guarantees](verification-guarantees.md) |
| **Build on .chronicle** (graph, export, or other tools) | Use the read model or a conformant .chronicle as input; optional Neo4j export/sync. | [Neo4j](neo4j.md); [Consuming .chronicle](consuming-chronicle.md) |

**Producing (high-level):** (1) Create a ZIP with `manifest.json`, `chronicle.db`, and optional `evidence/` directory. (2) Populate the manifest with required keys (`format_version`, `investigation_uid`). (3) Build the SQLite database with `schema_version` and required tables (`events`, `investigation`, `claim`, `evidence_item`). (4) For each evidence row, add the file at the path given by `uri` and ensure its SHA-256 equals `content_hash`. (5) Run the verifier on the output to self-check: `chronicle-verify path/to/file.chronicle`.

**Consuming:** Run `chronicle-verify path/to/file.chronicle`. If it exits 0, the package is structurally valid; see [Verification guarantees](verification-guarantees.md) for what is and is not guaranteed.
