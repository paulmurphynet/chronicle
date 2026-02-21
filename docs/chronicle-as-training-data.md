# Chronicle as training data

Chronicle investigations (claims, evidence, support/challenge links, defensibility) can be exported to a training-friendly format (e.g. JSONL) for SFT, preference learning, or other ML use cases.

---

## Export script and schema

- Script: `scripts/export_for_ml.py` (when available in the repo). Run from repo root with `PYTHONPATH=. python3 scripts/export_for_ml.py --path /project --output claims.jsonl` (or similar; see script `--help` for options).
- Shape: Typically one line per claim (or per claim–evidence pair), with claim text, evidence snippets, support/challenge labels, and defensibility fields (provenance_quality, corroboration, contradiction_status). Exact schema is defined by the script output and documented in the script or in this doc when the script is present.
- Use cases: Training models to predict defensibility, to cite evidence, or to prefer well-supported over poorly supported claims; building preference datasets from Chronicle-verified runs.

---

## References

| Doc | Description |
|-----|-------------|
| [Technical report](technical-report.md) | Defensibility and schema. |
| [Benchmark](benchmark.md) | Benchmark concept and export for training (Section 2). |
| [Eval and benchmarking](eval-and-benchmarking.md) | Reporting and pipelines. |
