# Using Neo4j with Chronicle (RAG/evals)

Neo4j is **optional**. The scorer and verifier do not use it. Use it when you want a **graph view** of claims, evidence, and tensions for analysis or visualization.

## When it helps in this version

| Use case | Why Neo4j |
|----------|-----------|
| **Single eval run** | One investigation = one claim + N evidence + N support links. The graph is small; Neo4j adds little. |
| **Many runs / benchmark** | After running many evals (e.g. `run_defensibility_benchmark.py` or your own harness), export or sync **all** investigations into one Neo4j graph. Then you can query: which claims share evidence? Which runs have the most support? Visualize in Neo4j Browser or Bloom. |
| **Lineage and traversal** | Queries like "all evidence that supports this claim (direct or inherited)" or "claims in tension with this one" are natural in Cypher. The read model has the data; Neo4j makes graph traversal and visualization easier. |
| **Integration with a knowledge graph** | If you already have a Neo4j knowledge graph (entities, relations), you can load Chronicle's claim–evidence–tension graph into the same DB and query defensibility alongside your KG. |

## How to use it

Before loading or syncing, run the built-in contract check to confirm sync code, CSV export, rebuild scripts, and schema docs are aligned:

```bash
PYTHONPATH=. python3 scripts/check_neo4j_contract.py
```

It exits non-zero if there is drift between:

- `chronicle/store/neo4j_sync.py`
- `chronicle/store/neo4j_export.py`
- `neo4j/rebuild/01_schema.cyp` to `04_retractions.cyp`
- `docs/neo4j-schema.md`

### Option 1: Export to CSV, then load in Neo4j

1. **Export** the read model to CSV (no Neo4j server required):

   ```bash
   chronicle neo4j-export --path /path/to/project --output /path/to/neo4j_import
   ```

   This writes CSVs: investigations, claims, evidence_items, spans, links, tensions, etc.
   - Optional observability flags:
     - `--report /path/to/export_report.json`
     - `--progress` (structured JSON progress logs to stderr)

2. **Copy** the CSVs into Neo4j's import directory (or point Neo4j at that folder).

3. **Run the Cypher scripts** in `neo4j/rebuild/` in order: `01_schema.cyp`, `02_nodes.cyp`, `03_relationships.cyp`, `04_retractions.cyp`. See [neo4j/rebuild/README.md](../neo4j/rebuild/README.md).

4. Use **queries.cyp.example** and **gds_examples.cyp** for lineage, contradiction network, and analytics.

### Option 2: Direct sync (Neo4j running)

1. **Install the extra:** `pip install -e ".[neo4j]"` (adds the `neo4j` driver).

2. **Set env:** `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` (optional: `NEO4J_DATABASE`).

3. **Sync:** `chronicle neo4j-sync --path /path/to/project`.
   - Optional hardening flags:
     - `--database <name>`
     - `--max-retries <n>`
     - `--retry-backoff-seconds <seconds>`
     - `--connection-timeout-seconds <seconds>`
   - Optional observability flags:
     - `--report /path/to/sync_report.json`
     - `--progress` (structured JSON progress logs to stderr)
   - Equivalent env vars:
     - `NEO4J_DATABASE`
     - `NEO4J_SYNC_MAX_RETRIES`
     - `NEO4J_SYNC_RETRY_BACKOFF_SECONDS`
     - `NEO4J_CONNECTION_TIMEOUT_SECONDS`

   This MERGEs the read model into the running Neo4j instance (idempotent).

## RAG/evals workflow

- Run your **scorer** or **benchmark** as usual; results are in the Chronicle project (SQLite).
- When you want a **graph view** (e.g. after 100 eval runs), run **neo4j-export** (or **neo4j-sync**) for that project (or for a project that aggregates many investigations).
- Query or visualize in Neo4j; defensibility itself stays computed in the relational store and is not recomputed in Neo4j.

## Live integration tests

Chronicle includes a live Neo4j integration suite (`tests/test_neo4j_live_integration.py`) that validates:

- End-to-end sync against a real Neo4j instance (not only static contract checks).
- Dedupe and non-dedupe mode behavior.
- Idempotent re-sync behavior and support/challenge link identity semantics.

Run locally (with a reachable Neo4j):

```bash
export CHRONICLE_RUN_NEO4J_LIVE_TESTS=1
export NEO4J_URI=bolt://127.0.0.1:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=chronicle_dev_password
CHRONICLE_EVENT_STORE=sqlite pytest tests/test_neo4j_live_integration.py -q
```

If `CHRONICLE_RUN_NEO4J_LIVE_TESTS` is unset, the suite skips by default.
You can also run `make neo4j-live-test` after setting `NEO4J_URI`, `NEO4J_USER`, and `NEO4J_PASSWORD`.

## Summary

Neo4j is a **projection** of the same read model. It does not replace the scorer or the verifier. Use it for multi-run analysis, lineage traversal, and visualization when your workflow benefits from a graph.

**Schema reference:** For node labels, relationship types, and example Cypher queries, see [Neo4j schema](neo4j-schema.md).
