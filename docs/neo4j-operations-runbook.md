# Neo4j Operations Runbook

This runbook covers operational ownership for Chronicle's optional Neo4j projection surface.

Use this with:

- [Neo4j usage guide](neo4j.md)
- [Aura graph pipeline](aura-graph-pipeline.md)
- [Neo4j schema](neo4j-schema.md)
- [Support policy](support-policy.md)

## Scope and reliability posture

- Chronicle's canonical trust artifacts remain `.chronicle` + verifier.
- Neo4j is a projection for traversal, analysis, and visualization.
- If Neo4j is unavailable, scoring/verifier flows remain available from the Chronicle project database.

## Baseline preflight

Before scheduled sync windows:

1. Validate contract parity:

```bash
PYTHONPATH=. python3 scripts/check_neo4j_contract.py
```

2. Validate Chronicle source project health:
   - `chronicle.db` exists.
   - Event/read-model writes are healthy (`make test` or targeted smoke tests).
3. Validate Neo4j credentials and target DB selection:
   - `NEO4J_URI`
   - `NEO4J_USER`
   - `NEO4J_PASSWORD`
   - optional `NEO4J_DATABASE`

## Backup and restore

## Backup policy

- Source of truth: back up the Chronicle project (`chronicle.db`, `evidence/`, exported `.chronicle` artifacts) per your main backup policy.
- Neo4j projection: back up by platform policy:
  - Aura: scheduled snapshots/export policy from Aura console.
  - Self-hosted Neo4j: filesystem + transaction log backup per Neo4j guidance.
- Keep at least one matching backup checkpoint for:
  - Chronicle source project
  - Neo4j projected graph

## Restore strategy

Preferred restore path after corruption or accidental graph loss:

1. Restore Chronicle source-of-truth artifacts first.
2. Recreate or clean Neo4j target database.
3. Re-run full projection:

```bash
chronicle neo4j-sync --path /path/to/project --report reports/neo4j_sync_restore_report.json --progress
```

4. Validate expected node/edge counts and spot-check critical queries from [Neo4j query pack](neo4j-query-pack.md).

## Sync cadence and drift handling

## Cadence options

- Continuous/minute-scale: small projects, low latency requirements.
- Hourly/batch: medium projects where throughput and cost matter more than freshness.
- Daily: archival/reporting-focused graph workloads.

Use one explicit owner and one explicit cadence per environment.

## Drift detection

Drift symptoms:

- Missing expected investigations in graph.
- Query-pack aggregate counts diverge from read model trends.
- Repeated sync failures in reports.

Drift response checklist:

1. Run sync with report output and progress logs:

```bash
chronicle neo4j-sync --path /path/to/project --report reports/neo4j_sync_drift_check.json --progress
```

2. If sync repeatedly fails, inspect:
   - auth/database mismatch
   - timeout/retry settings
   - Neo4j resource pressure
3. If drift persists, perform clean rebuild from source-of-truth Chronicle project.

## Failure handling and retry posture

Recommended baseline settings:

- `--max-retries 3`
- `--retry-backoff-seconds 1.0`
- `--connection-timeout-seconds 15`

For unstable networks, raise retries/backoff gradually and record final values in deployment docs.

## Capacity and cost guardrails

## Capacity planning signals

Track these per sync run report:

- `elapsed_ms`
- per-phase row counts and batch counts
- failure rate by error class

Track these per graph:

- node count growth rate
- relationship count growth rate
- top query latency from [Neo4j query pack](neo4j-query-pack.md)

## Cost controls

- Prefer scheduled batch sync over high-frequency sync unless freshness is required.
- Use dedupe mode for high-overlap corpora where claim/evidence text repeats:
  - `--dedupe-evidence-by-content-hash`
- Keep one retention policy for archived investigations and graph snapshots.
- Re-run [projection benchmark harness](../scripts/benchmark_data/run_neo4j_projection_benchmark.py) before major workload changes to detect throughput/memory regressions.

## Release evidence expectations

For release candidates affecting Neo4j projection:

1. Save export and/or sync report artifacts.
2. Save benchmark harness output JSON with thresholds and measured values.
3. Record any changed retry/timeout/dedupe settings in release notes.

## Incident template (quick copy)

Use this structure for operational incidents:

- `Incident ID`
- `Time window (UTC)`
- `Impact` (queries degraded, sync delayed, graph unavailable)
- `Root cause`
- `Immediate mitigation`
- `Recovery steps`
- `Data correctness checks run`
- `Follow-up actions`
