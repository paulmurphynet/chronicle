# RAG evals: Chronicle defensibility as a standard metric

Use **Chronicle defensibility** in your RAG eval harness as a standard metric: one (query, answer, evidence) in → one defensibility score out. No API server required; pipe JSON to the scorer and read JSON back.

---

## 1. Contract and schema

- **Input:** One JSON object: `query` (string), `answer` (string), `evidence` (array of strings or objects with `text`/`path`). See [Eval contract](eval_contract.md).
- **Output:** One JSON object: defensibility metrics (`claim_uid`, `provenance_quality`, `corroboration`, `contradiction_status`, optional `knowability`) or an error object with `error` and `message`.
- **Machine-readable:** [eval_contract_schema.json](eval_contract_schema.json) — validate input with `$defs/Input`, output with `$defs/OutputSuccess` or `$defs/OutputError`.
- **Field semantics:** [Defensibility metrics schema](defensibility-metrics-schema.md).

**Contract version:** 1.0. Breaking changes will be rare and announced.

---

## 2. How to run the scorer in your harness

**From repo (no install):**

```bash
# One JSON object per line or single object on stdin
echo '{"query": "What was revenue?", "answer": "Revenue was $1.2M.", "evidence": ["The company reported revenue of $1.2M in Q1 2024."]}' \
  | PYTHONPATH=. python3 scripts/standalone_defensibility_scorer.py
```

**After install:** `pip install -e .` (or `chronicle-standard` when on PyPI). Then:

```bash
echo '{"query": "...", "answer": "...", "evidence": ["..."]}' | standalone_defensibility_scorer.py
# or use the entry point if exposed
```

**From Python (in-process):**

```python
import json
from scripts.standalone_defensibility_scorer import _run_scorer

input_obj = {"query": "What was revenue?", "answer": "Revenue was $1.2M.", "evidence": ["The company reported revenue of $1.2M in Q1 2024."]}
out = _run_scorer(json.dumps(input_obj))
if "error" in out:
    raise RuntimeError(out.get("message", out["error"]))
# out has claim_uid, provenance_quality, corroboration, contradiction_status
```

Or run the script via subprocess and parse stdout. Exit code 0 = success (metrics), 1 = error (check for `"error"` in the output).

**CLI flags (alternative to stdin):**

```bash
python3 scripts/standalone_defensibility_scorer.py \
  --query "What was revenue?" \
  --answer "Revenue was $1.2M." \
  --evidence '["The company reported revenue of $1.2M in Q1 2024."]'
```

---

## 3. Integrating with your RAG pipeline

1. For each (query, model answer, retrieved chunks): build one contract input object.
2. Pipe it to the scorer (or call the scorer function in-process).
3. Parse the output: if `error` is present, treat as failed eval or invalid input; otherwise use `provenance_quality`, `corroboration`, `contradiction_status` as your defensibility metrics.
4. Aggregate across runs (e.g. % strong, average support_count) as you do for other RAG metrics.

**Adapter:** If your harness speaks a different format (e.g. a custom JSON per run), add a thin adapter that maps your format → contract input, runs the scorer, and maps output → your format. See [Integrating with Chronicle](integrating-with-chronicle.md) and [Eval and benchmarking](eval-and-benchmarking.md).

---

## 4. Why Chronicle for RAG + defensibility

- **Single responsibility** — Defensibility only: support/challenge, tensions, policy-relative score. No truth certification.
- **Portable** — Stdlib + SQLite; no API server needed for the scorer.
- **Stable contract** — Versioned 1.0; same shape from session, API, or standalone script.
- **Eval-native** — Designed for “one run in, one metrics out” so harnesses can add defensibility alongside accuracy, latency, etc.

Use this page as the entry point for “Chronicle defensibility as the standard metric” in RAG evals.
