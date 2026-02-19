# Neo4j Rebuild Pipeline

Optional graph projection for lineage and contradiction networks. See [docs/neo4j.md](../../docs/neo4j.md) for when and how to use Neo4j in this project.

## Prerequisites

- Neo4j 5.x
- Chronicle project with `chronicle.db` (relational read model already populated)

## Runbook

### 0. Run contract check

From repo root, verify sync/export/docs/rebuild parity before loading:

```bash
PYTHONPATH=. python3 scripts/check_neo4j_contract.py
```

### 1. Export read model to CSV

From the project root (or any directory with a Chronicle project):

```bash
chronicle neo4j-export --path /path/to/project --output /path/to/neo4j_import
```

This writes CSV files into the output directory: `investigations.csv`, `sources.csv`, `claims.csv`, `evidence_items.csv`, `spans.csv`, `actors.csv`, `tensions.csv`, `asserts.csv`, `links.csv`, `link_retractions.csv`, `supersession.csv`, `decomposition_edges.csv`, `evidence_source_links.csv`.

### 2. Copy CSVs into Neo4j import directory

Configure Neo4j so it can load from your export directory (e.g. set `server.directories.import` or copy the CSVs into Neo4j’s default import folder). In Cypher, `LOAD CSV FROM 'file:///file.csv'` resolves relative to that import directory.

### 3. Run Cypher scripts in order

In Neo4j Browser or cypher-shell, run:

1. **01_schema.cyp** — constraints and indexes (idempotent)
2. **02_nodes.cyp** — MERGE nodes from CSVs
3. **03_relationships.cyp** — MERGE relationships from CSVs
4. **04_retractions.cyp** — set `retracted_at` / `retracted_reason` on SUPPORTS/CHALLENGES from `link_retractions.csv` (safe to run when file is empty)

For a clean rebuild, optionally clear projected data first:

```cypher
MATCH (n) WHERE n:Claim OR n:EvidenceItem OR n:EvidenceSpan OR n:Actor OR n:Tension OR n:Investigation OR n:Source
DETACH DELETE n;
```

Then run 02, 03, and 04 again.

### 4. Verify

Run example queries from **queries.cyp.example** (e.g. by investigation or claim_uid) to confirm nodes and relationships.

### 5. (Optional) One-step sync via CLI

If you have Neo4j running and the `[neo4j]` extra installed, you can sync without exporting CSVs: set `NEO4J_URI`, `NEO4J_USER`, and `NEO4J_PASSWORD`, then run `chronicle neo4j-sync --path /path/to/project`. See [docs/neo4j.md](../../docs/neo4j.md).

### 6. Run example queries

After rebuild, run the parameterized example queries in **queries.cyp.example** with your own `claim_uid` and (for investigation-scoped queries) `inv_uid` (investigation_uid).

- **Neo4j Browser:** Set parameters with the parameter panel or `:param claim_uid => 'claim_01HZX3...';` then run one query block.
- **cypher-shell:** Pass parameters with `-P "claim_uid=claim_01HZX3..."` and run the desired query.

Examples in the file: TraceLineage (support/challenge + decomposition), GetContradictionNetwork (claims in tension), PropagateDowngrade (claim + descendants), claims by investigation, evidence supporting or challenging a claim.

## Optional graph queries (14.3)

The file **queries.cyp.example** contains runnable Cypher for:

- **TraceLineage(claim_uid, depth):** traverse support/challenge and decomposition.
- **GetContradictionNetwork(claim_uid):** claims connected by tensions.
- **PropagateDowngrade(claim_uid):** read-only view of claim and descendants (actual state changes remain in the relational store and events).
- **Claims by investigation;** **evidence supporting/challenging a claim.**

For analytics (centrality, communities, path finding), see **gds_examples.cyp** (requires Neo4j Graph Data Science library).
