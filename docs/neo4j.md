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

### Option 1: Export to CSV, then load in Neo4j

1. **Export** the read model to CSV (no Neo4j server required):

   ```bash
   chronicle neo4j-export --path /path/to/project --output /path/to/neo4j_import
   ```

   This writes CSVs: investigations, claims, evidence_items, spans, links, tensions, etc.

2. **Copy** the CSVs into Neo4j's import directory (or point Neo4j at that folder).

3. **Run the Cypher scripts** in `neo4j/rebuild/` in order: `01_schema.cyp`, `02_nodes.cyp`, `03_relationships.cyp`, `04_retractions.cyp`. See [neo4j/rebuild/README.md](../neo4j/rebuild/README.md).

4. Use **queries.cyp.example** and **gds_examples.cyp** for lineage, contradiction network, and analytics.

### Option 2: Direct sync (Neo4j running)

1. **Install the extra:** `pip install -e ".[neo4j]"` (adds the `neo4j` driver).

2. **Set env:** `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`.

3. **Sync:** `chronicle neo4j-sync --path /path/to/project`.

   This MERGEs the read model into the running Neo4j instance (idempotent).

## RAG/evals workflow

- Run your **scorer** or **benchmark** as usual; results are in the Chronicle project (SQLite).
- When you want a **graph view** (e.g. after 100 eval runs), run **neo4j-export** (or **neo4j-sync**) for that project (or for a project that aggregates many investigations).
- Query or visualize in Neo4j; defensibility itself stays computed in the relational store and is not recomputed in Neo4j.

## Summary

Neo4j is a **projection** of the same read model. It does not replace the scorer or the verifier. Use it for multi-run analysis, lineage traversal, and visualization when your workflow benefits from a graph.
