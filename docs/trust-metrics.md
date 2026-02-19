# Trust metrics

Chronicle tracks trust progress with explicit, reproducible metrics derived from benchmark outputs.

Primary benchmark source: `scripts/benchmark_data/run_defensibility_benchmark.py`

Primary KPI tool: `scripts/benchmark_data/trust_progress_report.py`

## Why this exists

In AI systems, confidence can be high even when evidence quality is weak. Chronicle's metric posture is:

1. Measure support quality structure.
2. Make regression visible.
3. Avoid claiming "truth" from metric output alone.

## Primary KPI

`effective_unsupported_rate`

Formula:

`(unsupported_scored_claims + unscored_claims) / total_claims`

Where:

1. `unsupported_scored_claims` are rows with valid metrics but `corroboration.support_count <= 0`.
2. `unscored_claims` are rows with missing metrics or non-empty `error`.
3. `total_claims` is total benchmark rows.

Rationale:

1. Penalizes both weak support and operational failure to score.
2. Works as a single top-line KPI for release and regression checks.

## Secondary KPIs

1. `strict_unsupported_rate`: unsupported among scored claims only.
2. `unscored_rate`: operational reliability signal for evaluation runs.
3. `open_contradiction_rate`: share of scored claims with `contradiction_status = open`.
4. `trust_progress_score`: `1 - effective_unsupported_rate` (bounded summary score).

## Commands

Generate benchmark results:

```bash
PYTHONPATH=. python3 scripts/benchmark_data/run_defensibility_benchmark.py \
  --output benchmark_defensibility_results.json
```

Generate trust metrics summary:

```bash
PYTHONPATH=. python3 scripts/benchmark_data/trust_progress_report.py \
  --results benchmark_defensibility_results.json
```

Compare against a baseline and fail on insufficient improvement:

```bash
PYTHONPATH=. python3 scripts/benchmark_data/trust_progress_report.py \
  --results benchmark_defensibility_results.json \
  --baseline benchmark_baseline.json \
  --min-effective-unsupported-reduction 0.10
```

Rate-cap gate (without baseline):

```bash
PYTHONPATH=. python3 scripts/benchmark_data/trust_progress_report.py \
  --results benchmark_defensibility_results.json \
  --max-effective-unsupported-rate 0.25 \
  --max-unscored-rate 0.10
```

## Usage guidance

1. Track deltas over time; do not rely on one run.
2. Keep benchmark scenarios stable when comparing baselines.
3. Use with existing guardrails: [Benchmark](benchmark.md#3-guardrails).
4. Report limitations clearly: metric quality depends on evidence-claim linking quality.

## Non-goals

These metrics do not:

1. Prove factual truth.
2. Prove semantic entailment between evidence and claim.
3. Replace human review for high-stakes decisions.

