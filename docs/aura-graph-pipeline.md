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
- **Idempotency:** Sync uses MERGE on UIDs, so re-syncing the same project is safe. Re-importing the same `.chronicle` (same investigation_uid) would replay the same events; the event store may dedupe by idempotency_key or event_id depending on implementation—in practice, avoid re-importing the same file unless you’ve cleared that investigation.

---

## Credentials and environment

Use a **`.env`** file in the repo root (never commit it; it’s in `.gitignore`). Copy from `.env.example` and fill in:

| Variable | Description | Example (Aura) |
|----------|-------------|-----------------|
| `NEO4J_URI` | Neo4j connection URI | `neo4j+s://xxxxxxxx.databases.neo4j.io` |
| `NEO4J_USER` | Username (Aura usually `neo4j`) | `neo4j` |
| `NEO4J_PASSWORD` | Password from Aura console | *(from Aura)* |
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
4. Create the graph project directory (if it doesn’t exist, the ingest script can create it on first import):
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

Ensure `NEO4J_URI` and `NEO4J_PASSWORD` (and optionally `NEO4J_USER`) are set (e.g. from `.env` or exported in the shell).

### 4. Query and analytics in Neo4j

- Use **Neo4j Browser** (Aura console) or **cypher-shell** with the same URI/user/password.
- Example queries and GDS examples: see `neo4j/rebuild/queries.cyp.example` and `neo4j/rebuild/gds_examples.cyp` (run after the first sync so the graph has data).
- For graph RAG: design retrieval so it returns subgraphs that include `(Claim)-[:SUPPORTS|CHALLENGES]-(EvidenceSpan)-[:FROM]-(EvidenceItem)` and optionally `(Claim)-[:IN_TENSION]-(Claim)`, so the model sees justification and tensions, not just claim text.

---

## Design choices and caveats

| Topic | Choice / caveat |
|-------|------------------|
| **One project vs many** | One “graph project” that merges all imported investigations keeps a single sync target and a single Aura graph. Each investigation keeps its own `investigation_uid` in Neo4j, so attribution is preserved. |
| **Re-import** | Re-importing the same `.chronicle` (same investigation_uid) can lead to duplicate events or conflicts depending on idempotency. Prefer importing each file once. |
| **Deduplication** | Evidence/claims are not deduplicated across investigations (e.g. same text in two files → two nodes). Optional merge by content hash is in [To-do](to_do.md). |
| **Verification** | Only verified files should be ingested. The script runs the verifier first; do not bypass it for untrusted input. |
| **What “verified” means** | See [Critical areas: What the verifier checks](../critical_areas/03-what-the-verifier-checks.md). Verified = structure and hashes, not truth or independence. |

---

## Summary

- Put **Aura credentials** in **`.env`** (`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`); use **`.env.example`** as a template.
- **Pipeline:** Verify `.chronicle` → import into shared graph project → sync project to Neo4j. Use `scripts/ingest_chronicle_to_aura.py` for one-command ingest.
- The resulting graph is an **ever-growing, Chronicle-verifiable justification graph**: claims, evidence, support/challenge, tensions, so the AI can see both facts and why we believe them (and where they conflict).
