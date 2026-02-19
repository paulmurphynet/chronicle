# Reference workflows

This page defines practical, reproducible workflows for Chronicle users and contributors.

Each workflow is designed to be:

1. Runnable from a fresh checkout.
2. Explicit about trust limitations.
3. Reusable as a template for integrations.

## One-command runner

Run the full reference set (journalism, benchmark trust tracking, compliance report, Neo4j contract check):

```bash
PYTHONPATH=. python3 scripts/run_reference_workflows.py
```

This writes a consolidated JSON report under `reference_workflow_runs/<timestamp>/reference_workflow_report.json`.

## Workflow 1: Journalism conflict review

Goal: build a small investigation with conflicting claims, verify the artifact, and inspect tensions.

Run from repo root:

```bash
PYTHONPATH=. python3 scripts/verticals/journalism/generate_sample.py
chronicle-verify frontend/public/sample.chronicle
```

Expected outcome:

1. A deterministic `.chronicle` sample is generated.
2. Verifier passes on structure/hash checks.
3. The investigation contains claim conflict captured as a tension.

## Workflow 2: Compliance-style RAG audit output

Goal: run one RAG flow and produce an auditable report bundle.

Run from repo root:

```bash
PYTHONPATH=. python3 scripts/compliance_report_from_rag.py \
  --mode session \
  --output-dir ./compliance_run
```

Expected outcome:

1. A Chronicle investigation is created from the run.
2. Report artifacts are written with claim/evidence mappings.
3. Defensibility is available for each produced claim.

## Workflow 3: Benchmark trust tracking

Goal: track trust KPI trends over time with benchmark outputs.

Run from repo root:

```bash
PYTHONPATH=. python3 scripts/benchmark_data/run_defensibility_benchmark.py \
  --mode session \
  --output benchmark_defensibility_results.json
PYTHONPATH=. python3 scripts/benchmark_data/trust_progress_report.py \
  --results benchmark_defensibility_results.json
```

Optional baseline gate:

```bash
PYTHONPATH=. python3 scripts/benchmark_data/trust_progress_report.py \
  --results benchmark_defensibility_results.json \
  --baseline benchmark_baseline.json \
  --min-effective-unsupported-reduction 0.10
```

Expected outcome:

1. A stable benchmark result file is produced.
2. KPI summary includes effective unsupported rate and scoring reliability.
3. Thresholds can fail CI/manual checks on regressions.

## Optional extension: Neo4j projection

For workflows requiring graph analysis:

```bash
PYTHONPATH=. python3 scripts/check_neo4j_contract.py
chronicle neo4j-export --path /path/to/project --output /path/to/neo4j_import
```

Or sync directly (with Neo4j env vars set):

```bash
chronicle neo4j-sync --path /path/to/project
```

Use [Neo4j](neo4j.md) and [Aura graph pipeline](aura-graph-pipeline.md) for full setup.

## Optional extension: Adapter onboarding

For external connector development:

```bash
PYTHONPATH=. python3 scripts/adapters/starter_batch_to_scorer.py \
  --input runs.jsonl --output scored.jsonl
PYTHONPATH=. python3 scripts/adapters/validate_adapter_outputs.py \
  --input scored.jsonl
```

Use this with [Integration acceptance checklist](integration-acceptance-checklist.md) before publishing adapters.
