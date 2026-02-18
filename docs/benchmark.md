# Defensibility benchmark

A **defensibility benchmark** uses Chronicle-formatted investigations and defensibility metrics to evaluate RAG or reasoning systems. This doc summarizes the concept and where to find scripts and data.

**Citable benchmark:** The canonical run is **`scripts/benchmark_data/run_defensibility_benchmark.py`**: fixed queries, Chronicle-backed RAG path, defensibility recorded per answer. Reproducible with one command from the repo root; output shape is documented in [Eval and benchmarking](eval-and-benchmarking.md). Papers and blogs can cite "Chronicle defensibility benchmark (run_defensibility_benchmark.py)" and the [eval contract](eval_contract.md) for the metric definition.

**Scorer default:** The default scorer links every evidence chunk as support for the single claim and does not validate that evidence actually supports the answer. For higher assurance, validate or curate evidence–claim links (e.g. human or NLI) then record; see [Eval contract](eval_contract.md#important-what-the-default-scorer-does-and-does-not-do).

**Sample / public dataset:** For validation and demos, you can generate a small set of (query, answer, evidence) investigations with schema-valid defensibility scorecards. Use `scripts/synthetic_data/generate_realistic_synthetic.py` for synthetic investigations with varied defensibility profiles, or `scripts/benchmark_data/generate_benchmark_samples.py` for fixed-query benchmark samples. A minimal Try sample is produced by `scripts/generate_sample_chronicle.py`. See [Eval contract](eval_contract.md) for the scorer input/output shape.

---

## 1. Concept

- **Dataset shape:** Investigations (or claim-centric subsets) with claims, evidence, support/challenge links, tensions, and defensibility scorecards per claim. The schema is **Chronicle-native**: any conformant `.chronicle` export is a valid benchmark instance. See [Technical report](technical-report.md) Section 4.
- **Fixed-query run:** Run a fixed set of queries through a Chronicle-backed RAG pipeline and record defensibility per answer. Script: `scripts/benchmark_data/run_defensibility_benchmark.py`. From repo root: `PYTHONPATH=. python3 scripts/benchmark_data/run_defensibility_benchmark.py` (optional `--output results.json` or `--stdout`). See [Eval and benchmarking](eval-and-benchmarking.md) for the output shape and how to reproduce.
- **Sample investigations:** Synthetic investigations with different defensibility profiles (e.g. open tension, strong, weak single source) can be generated with scripts in `scripts/synthetic_data/` or `scripts/benchmark_data/` (if present). The technical report references a sample set of 6 investigations; regenerate with the script referenced in the repo (e.g. `scripts/benchmark_data/generate_benchmark_samples.py` if it exists, or use `scripts/synthetic_data/generate_realistic_synthetic.py` for synthetic data).

### Generating the canonical sample set

From the repo root, run:

```bash
PYTHONPATH=. python3 scripts/synthetic_data/generate_realistic_synthetic.py
```

This generates synthetic investigations with varied defensibility profiles. For benchmark samples keyed to fixed queries and docs, use:

```bash
PYTHONPATH=. python3 scripts/benchmark_data/generate_benchmark_samples.py
```

(if that script exists in your checkout). Output locations and options: see each script's `--help`.

---

## 2. Export for training

To export claim–evidence–defensibility to a training-friendly format (e.g. JSONL for SFT or preference data), use the script `scripts/export_for_ml.py` (when available). Schema and use cases: [Chronicle as training data](chronicle-as-training-data.md).

---

## 3. References

| Doc | Description |
|-----|-------------|
| [Technical report](technical-report.md) | Defensibility definition, schema, use for evaluation. |
| [Eval and benchmarking](eval-and-benchmarking.md) | How to run pipelines, extract metrics, and report. |
| [Defensibility metrics schema](defensibility-metrics-schema.md) | Stable metrics fields for eval harnesses. |
