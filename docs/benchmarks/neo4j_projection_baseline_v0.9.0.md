# Neo4j Projection Baseline (v0.9.0)

Baseline artifact for Neo4j projection performance/readiness.

- Benchmark script: `scripts/benchmark_data/run_neo4j_projection_benchmark.py`
- JSON artifact: `docs/benchmarks/neo4j_projection_baseline_v0.9.0.json`
- Date: 2026-02-20

## Command

```bash
PYTHONPATH=. ./.venv/bin/python scripts/benchmark_data/run_neo4j_projection_benchmark.py \
  --output docs/benchmarks/neo4j_projection_baseline_v0.9.0.json \
  --investigations 20 \
  --claims-per-investigation 200 \
  --evidence-per-investigation 400 \
  --links-per-claim 2 \
  --max-export-elapsed-ms 1000 \
  --max-export-peak-mib 64
```

## Result snapshot

- Status: `passed`
- Row counts:
  - investigations: `20`
  - claims: `4000`
  - evidence_items: `8000`
  - links: `8000`
- Export elapsed: `231.969 ms`
- Export peak memory: `1.523 MiB`
- Threshold failures: none

## Interpretation

- Export path demonstrates bounded-memory behavior for this large synthetic fixture.
- Thresholds are now encoded in a reproducible artifact and can be raised/lowered per release policy.
