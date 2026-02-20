# Neo4j Projection Sync Baseline (v0.9.0)

Large-run baseline artifact for Chronicle Neo4j projection with real Neo4j connectivity.

- Benchmark script: `scripts/benchmark_data/run_neo4j_projection_benchmark.py`
- JSON artifact: `docs/benchmarks/neo4j_projection_sync_baseline_v0.9.0.json`
- Date: 2026-02-20
- Environment: local `neo4j:5` container (`bolt://127.0.0.1:7687`)

## Command

```bash
PYTHONPATH=. ./.venv/bin/python scripts/benchmark_data/run_neo4j_projection_benchmark.py \
  --output docs/benchmarks/neo4j_projection_sync_baseline_v0.9.0.json \
  --investigations 20 \
  --claims-per-investigation 200 \
  --evidence-per-investigation 400 \
  --links-per-claim 2 \
  --run-sync \
  --neo4j-uri bolt://127.0.0.1:7687 \
  --neo4j-user neo4j \
  --neo4j-password chronicle_dev_password \
  --max-export-elapsed-ms 1000 \
  --max-export-peak-mib 64 \
  --max-sync-elapsed-ms 60000 \
  --max-sync-peak-mib 256
```

## Result snapshot

- Status: `passed`
- Row counts:
  - investigations: `20`
  - claims: `4000`
  - evidence_items: `8000`
  - links: `8000`
- Export:
  - elapsed: `226.814 ms`
  - peak memory: `1.523 MiB`
- Sync (real Neo4j):
  - elapsed: `7589.511 ms`
  - peak memory: `30.351 MiB`
  - attempts used: `1`
- Threshold failures: none

## Related live validation

Live integration suite against the same local Neo4j endpoint:

```bash
CHRONICLE_EVENT_STORE=sqlite \
CHRONICLE_RUN_NEO4J_LIVE_TESTS=1 \
NEO4J_URI=bolt://127.0.0.1:7687 \
NEO4J_USER=neo4j \
NEO4J_PASSWORD=chronicle_dev_password \
./.venv/bin/pytest tests/test_neo4j_live_integration.py -q
```

Result: `2 passed`.
