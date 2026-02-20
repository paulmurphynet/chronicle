# Chronicle → Neo4j Aura: shared justification graph

This doc describes how to run an **ever-growing knowledge graph** of Chronicle-verifiable data on Neo4j Aura: verify `.chronicle` files, import them into a single Chronicle project, and sync that project to Aura so the graph contains claims, evidence, support/challenge links, and tensions—giving graph RAG (and other consumers) both facts and **justification data**.

---

## Goal

- **Input:** People contribute `.chronicle` files (verified investigations with evidence, claims, links, tensions).
- **Output:** One Neo4j graph (e.g. on Aura) that accumulates all those investigations. The graph is not just entities and relations—it includes the **justification structure**: which evidence supports which claims, which claims are in tension, and (optionally) defensibility. So AI systems can retrieve both “what was claimed” and “why we think that” (and where it’s contested).
- **Trust:** Only **verified** `.chronicle` files are ingested (structure, schema, evidence hashes). Verification does not validate truth or independence; see [Critical areas](../critical_areas/README.md).

---

## Architecture

```
  .chronicle file
        │
        ▼
  ┌─────────────┐
  │  Verify     │  chronicle-verify (manifest, schema, evidence hashes)
  └──────┬──────┘
         │ pass
         ▼
  ┌─────────────┐
  │  Import     │  import_investigation(.chronicle, graph_project_dir)
  │             │  → one Chronicle project that accumulates investigations
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │  Sync       │  sync_project_to_neo4j(graph_project_dir, NEO4J_URI, user, password)
  │             │  → MERGE into Neo4j (idempotent)
  └──────┬──────┘
         │
         ▼
  Neo4j Aura (one graph: Investigation, Claim, EvidenceItem, EvidenceSpan, Source,
              SUPPORTS, CHALLENGES, DECOMPOSES_TO, Tension, etc.)
```

- **Single “graph project”:** One directory (e.g. `chronicle_graph_project/`) with a single `chronicle.db`. Each new `.chronicle` is **imported** into this project (merge); then we run **one** sync to Neo4j. So the Aura graph grows as more investigations are added.
- **What gets synced:** The sync pushes **every investigation in that project** to Neo4j. If the project has 10 investigations (e.g. synthetic + Lizzie), all 10 go to Aura. To have **only** certain data in Aura, use a project that contains only those investigations (e.g. a dedicated folder with one .chronicle imported), then sync that project. Clearing the Neo4j database does not change the Chronicle project—re-sync will re-push everything in the project.
- **Idempotency and safety:** Sync uses MERGE on UIDs, so re-syncing the same project is safe. Import runs verifier checks before merge; duplicate events are skipped by `event_id`; evidence file path conflicts with different bytes are blocked. In practice, still avoid re-importing the same file unless you intend to validate idempotency behavior.

---

## Credentials and environment

Use a **`.env`** file in the repo root (never commit it; it’s in `.gitignore`). Copy from `.env.example` and fill in:

| Variable | Description | Example (Aura) |
|----------|-------------|-----------------|
| `NEO4J_URI` | Neo4j connection URI | `neo4j+s://xxxxxxxx.databases.neo4j.io` |
| `NEO4J_USER` | Username (Aura usually `neo4j`) | `neo4j` |
| `NEO4J_PASSWORD` | Password from Aura console | *(from Aura)* |
| `NEO4J_DATABASE` | Optional Neo4j database name | `neo4j` |
| `CHRONICLE_GRAPH_PROJECT` | Path to the Chronicle project that accumulates investigations (optional; script default below) | `./chronicle_graph_project` |

- **Aura:** Create a free database at [Neo4j Aura](https://neo4j.com/cloud/aura/). Copy the URI (e.g. `neo4j+s://xxxx.databases.neo4j.io`), user (usually `neo4j`), and the initial password. Put them in `.env`.
- **`.env` format (required by python-dotenv):** One `KEY=value` per line, **no spaces around `=`**. If the value contains `#`, spaces, or `&`, wrap it in double quotes: `NEO4J_PASSWORD="my#pass"`. Copy from `.env.example` and only replace the value parts.
- Scripts and the CLI load `.env` when `python-dotenv` is installed (`pip install -e ".[neo4j]"`), or you can run `set -a && source .env && set +a` before commands.

---

## Runbook

### 1. One-time setup

1. Create a free Neo4j Aura database; note URI, user, password.
2. Copy `.env.example` to `.env` and set `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`. Optionally set `CHRONICLE_GRAPH_PROJECT` (default in script: `./chronicle_graph_project`). **Do not commit `.env`** (it is in `.gitignore`).
3. Install the package with Neo4j support and (optional) dotenv:
   ```bash
   pip install -e ".[neo4j]"
   pip install python-dotenv   # optional: so scripts load .env automatically
   ```
4. Validate Neo4j contract parity before first sync:
   ```bash
   PYTHONPATH=. python3 scripts/check_neo4j_contract.py
   ```
5. Create the graph project directory (if it doesn’t exist, the ingest script can create it on first import):
   ```bash
   mkdir -p chronicle_graph_project
   ```
   The first `.chronicle` import will initialize `chronicle_graph_project/chronicle.db`.

### 2. Ingest a single `.chronicle` file

From repo root:

```bash
PYTHONPATH=. python scripts/ingest_chronicle_to_aura.py path/to/file.chronicle
```

- The script will:
  1. **Verify** the file (`chronicle-verify` checks). If verification fails, exit with an error.
  2. **Import** the file into the graph project (merge into `chronicle_graph_project/` by default).
  3. **Sync** the graph project to Neo4j (using `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` from the environment or `.env`).
- To use a different project directory:
  ```bash
  CHRONICLE_GRAPH_PROJECT=/path/to/my_graph PYTHONPATH=. python scripts/ingest_chronicle_to_aura.py file.chronicle
  ```

### 3. Sync only (no new file)

If you’ve already imported and only want to push the current graph project to Aura:

```bash
chronicle neo4j-sync --path chronicle_graph_project
```

Ensure `NEO4J_URI` and `NEO4J_PASSWORD` (and optionally `NEO4J_USER`, `NEO4J_DATABASE`) are set (e.g. from `.env` or exported in the shell).

To **deduplicate by content** (one EvidenceItem per content_hash, one Claim per hash(claim_text); lineage via CONTAINS_EVIDENCE and CONTAINS_CLAIM):

```bash
chronicle neo4j-sync --path chronicle_graph_project --dedupe-evidence-by-content-hash
```

Or set `NEO4J_DEDUPE_EVIDENCE_BY_CONTENT_HASH=1` in `.env`.

For transient network hardening, you can tune sync retries/timeouts via env:

- `NEO4J_SYNC_MAX_RETRIES` (default `3`)
- `NEO4J_SYNC_RETRY_BACKOFF_SECONDS` (default `1.0`)
- `NEO4J_CONNECTION_TIMEOUT_SECONDS` (default `15`)

For run evidence and observability:

- `chronicle neo4j-sync --path chronicle_graph_project --report reports/neo4j_sync_report.json`
- Add `--progress` to stream structured JSON phase/batch progress to stderr.
- Script path equivalent:
  - `PYTHONPATH=. python scripts/ingest_chronicle_to_aura.py file.chronicle --sync-report reports/neo4j_sync_report.json --progress`

### 4. Query and analytics in Neo4j

- Use **Neo4j Browser** (Aura console) or **cypher-shell** with the same URI/user/password.
- Example queries and GDS examples: see `neo4j/rebuild/queries.cyp.example` and `neo4j/rebuild/gds_examples.cyp` (run after the first sync so the graph has data).
- For graph RAG: design retrieval so it returns subgraphs that include `(EvidenceSpan)-[:SUPPORTS|CHALLENGES]->(Claim)` and `(EvidenceSpan)-[:IN]->(EvidenceItem)`, plus optional tension context via `(Tension)-[:BETWEEN]->(Claim)`, so the model sees justification and conflict structure, not just claim text.

---

## Design choices and caveats

| Topic | Choice / caveat |
|-------|------------------|
| **One project vs many** | One “graph project” that merges all imported investigations keeps a single sync target and a single Aura graph. Each investigation keeps its own `investigation_uid` in Neo4j, so attribution is preserved. |
| **Re-import** | Re-import is safer than before: duplicate events are skipped, and conflicting evidence bytes at the same path fail fast. Prefer importing each file once, and treat conflict failures as a signal to investigate tampering or local drift. |
| **Deduplication** | Optional full deduplication: set `NEO4J_DEDUPE_EVIDENCE_BY_CONTENT_HASH=1` or use `chronicle neo4j-sync --dedupe-evidence-by-content-hash`. When enabled: one **EvidenceItem** per content_hash and one **Claim** per hash(claim_text); lineage via `(Investigation)-[:CONTAINS_EVIDENCE {evidence_uid}]->(EvidenceItem)` and `(Investigation)-[:CONTAINS_CLAIM {claim_uid}]->(Claim)`. |
| **Verification** | Only verified files should be ingested. The script runs the verifier first; do not bypass it for untrusted input. |
| **What “verified” means** | See [Critical areas: What the verifier checks](../critical_areas/03-what-the-verifier-checks.md). Verified = structure and hashes, not truth or independence. |

---

## Summary

- Put **Aura credentials** in **`.env`** (`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`); use **`.env.example`** as a template.
- **Pipeline:** Verify `.chronicle` → import into shared graph project → sync project to Neo4j. Use `scripts/ingest_chronicle_to_aura.py` for one-command ingest.
- The resulting graph is an **ever-growing, Chronicle-verifiable justification graph**: claims, evidence, support/challenge, tensions, so the AI can see both facts and why we believe them (and where they conflict).
