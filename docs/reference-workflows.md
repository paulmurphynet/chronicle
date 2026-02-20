# Reference workflows

This page defines practical, reproducible workflows for Chronicle users and contributors.

Each workflow is designed to be:

1. Runnable from a fresh checkout.
2. Explicit about trust limitations.
3. Reusable as a template for integrations.

## One-command runner

Run the full reference set (journalism, legal, history/research, sample quality gate, readiness gate, compliance report, benchmark trust tracking, Neo4j contract check):

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

## Workflow 2: Legal conflict review

Goal: build a legal-style investigation with conflicting contractual claims and verify the artifact.

Run from repo root:

```bash
PYTHONPATH=. python3 scripts/verticals/legal/generate_sample.py
chronicle-verify frontend/public/sample_legal.chronicle
```

Expected outcome:

1. A deterministic legal `.chronicle` sample is generated.
2. Verifier passes on structure/hash checks.
3. The investigation includes a legal contradiction tension for review.

## Workflow 3: History/research conflict review

Goal: generate a history/research investigation with competing interpretations and explicit tension tracking.

Run from repo root:

```bash
PYTHONPATH=. python3 scripts/verticals/history/generate_sample.py
chronicle-verify frontend/public/sample_history.chronicle
```

Expected outcome:

1. A deterministic history/research `.chronicle` sample is generated.
2. Verifier passes on structure/hash checks.
3. The investigation preserves uncertainty via explicit competing claims and tension.

## Workflow 3b: Vertical sample quality gate

Goal: ensure sample artifacts remain realistic and complete for real-world onboarding (policy manifest, provenance, source links, supports/challenges, tensions).

Run from repo root:

```bash
PYTHONPATH=. python3 scripts/verticals/check_sample_quality.py
```

Expected outcome:

1. Every vertical generator produces a valid `.chronicle`.
2. Manifest policy IDs match the intended vertical profile.
3. Minimum quality thresholds pass (claims/evidence/sources/supports/challenges/tensions and rationale coverage).

## Workflow 4: Compliance-style RAG audit output

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

Optional one-shot review packet (TE-05) for legal/compliance/editorial handoff:

```bash
chronicle review-packet <investigation_uid> --path /path/to/project --output review_packet.json
```

Or via API:

```bash
curl "http://127.0.0.1:8000/investigations/<investigation_uid>/review-packet"
```

Role-specific review template:

```bash
# Use this after generating review packet/ledger outputs
cat docs/role-based-review-checklists.md
```

## Workflow 5: Benchmark trust tracking

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
  --input scripts/adapters/examples/harness_runs_valid.jsonl \
  --output scored.jsonl
PYTHONPATH=. python3 scripts/adapters/validate_adapter_outputs.py \
  --input scored.jsonl
PYTHONPATH=. python3 scripts/adapters/check_examples.py
```

Use this with [Integration acceptance checklist](integration-acceptance-checklist.md) before publishing adapters.

## Optional extension: Review readiness gate

For CI/compliance/editorial handoff checks on one investigation:

```bash
PYTHONPATH=. python3 scripts/review_readiness_gate.py \
  --path /path/to/project \
  --investigation-uid <investigation_uid> \
  --max-unresolved-tensions 0
```

Typical stricter options:

```bash
PYTHONPATH=. python3 scripts/review_readiness_gate.py \
  --path /path/to/project \
  --investigation-uid <investigation_uid> \
  --max-unresolved-tensions 0 \
  --require-built-under-policy \
  --require-decision-rationale \
  --require-chain-of-custody-report \
  --output readiness_gate_report.json
```

## Optional extension: Policy sensitivity comparison (R2-01)

For side-by-side review of one investigation under multiple policy profiles:

```bash
chronicle policy sensitivity \
  --path /path/to/project \
  --investigation <investigation_uid> \
  --profile-id policy_investigative_journalism \
  --profile-id policy_legal \
  --profile-id policy_compliance \
  --json
```

Interpretation guidance:

1. Start with `pairwise_deltas[].summary.changed_count` to see if profile changes materially alter claim outcomes.
2. Treat `strong_to_weak_count` as a threshold-sensitivity signal that often needs explicit reviewer rationale.
3. Treat blocked/non-blocked shifts as highest-severity handoff risk, especially before legal or compliance review.
4. Use `practical_review_implications` as a triage hint, then inspect affected `claim_uid`s before final decisions.
