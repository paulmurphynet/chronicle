# Using Chronicle in RAG evaluation

> **Purpose:** Explain how to use Chronicle as the **provenance backend** for RAG evaluation: run your pipeline with a Chronicle handler or writer, extract defensibility metrics for each answer, and compare runs or configs. No full benchmark required; this doc focuses on the pattern and interfaces.

**Companion:** [Eval contract (input/output)](eval_contract.md), [Defensibility metrics schema](defensibility-metrics-schema.md), [Benchmark](benchmark.md), [Trust metrics](trust-metrics.md), [Integrating with Chronicle](integrating-with-chronicle.md).

---

## 1. Why use Chronicle for RAG evals

RAG evaluation often measures retrieval quality, answer correctness, or citation faithfulness. Chronicle adds **defensibility** as an additional metric: provenance quality, corroboration (support/challenge counts, independent sources), contradiction status, and optional knowability. For the minimal **input/output contract** (query, answer, evidence in; metrics or error out) that eval frameworks can depend on, see [Eval contract](eval_contract.md). By running your RAG pipeline with Chronicle attached, every answer becomes a **claim** linked to **evidence** in the ledger; you then read the **defensibility scorecard** for that claim and use it in your eval harness.

Benefits:

- **Same backend as production** — The same handler or API you use in production records evidence and claims; evals just read the resulting metrics.
- **Stable metrics shape** — The defensibility output (claim_uid, provenance_quality, corroboration, contradiction_status, knowability) is documented and stable so you can compare across runs and configs. See [Defensibility metrics schema](defensibility-metrics-schema.md).
- **Compare configs** — Run the same (or different) queries with different retrievers, models, or prompts; record defensibility per run and compare.

---

## 2. Run the pipeline with a Chronicle integration

Attach a Chronicle **handler** or **writer** to your RAG pipeline so that retrieval and generation are recorded as evidence and claims.

1. **Choose an integration** — Use the handler for your framework so that documents and the final answer are written to Chronicle:
   - **LangChain, LlamaIndex, Haystack:** Demo scripts (e.g. `scripts/langchain_rag_chronicle.py`, `scripts/cross_framework_rag_chronicle.py`) and integration docs when present in the repo.
   - **Custom:** Use the session API or HTTP API to create an investigation, ingest evidence, propose a claim, and link support/challenge. See [Integrating with Chronicle](integrating-with-chronicle.md).

2. **One investigation per eval run (or per query)** — By default, each run creates a new investigation. For evals you can:
   - **One investigation per run** — Keep default; each run has one investigation and one (or more) claims. Simple and isolated.
   - **Stable key per scenario** — Use `investigation_key` (e.g. query id or scenario id) so that multiple runs with the same key reuse the same investigation. See [Integrating with Chronicle](integrating-with-chronicle.md#idempotency-for-agents-and-pipelines).

3. **Run the pipeline** — Execute your RAG chain with the handler in the callbacks (or equivalent). After the run, the handler holds the session and investigation UID; you can list claims and read defensibility.

---

## 3. Extract defensibility metrics

After each RAG run, get the **claim UID** for the answer (e.g. the last claim in the investigation) and the **defensibility scorecard**. The scorecard is available as a stable **metrics dict** suitable for eval harnesses.

**Option A: Standalone defensibility scorer (no RAG stack)**

Send one JSON object to stdin with `query`, `answer`, and `evidence` (list of strings or `{text}` objects). The script creates a temp project, ingests evidence, proposes the answer as a claim, links support, and prints the defensibility metrics JSON to stdout. No API server or framework required. From repo root:

```bash
echo '{"query": "What was revenue?", "answer": "Revenue was $1.2M.", "evidence": ["The company reported revenue of $1.2M in Q1 2024."]}' \
  | PYTHONPATH=. python3 scripts/standalone_defensibility_scorer.py
```

Exit code 0 on success, 1 on error. See [Eval contract](eval_contract.md) for input/output shape.

**Option B: Eval harness adapter script**

Run the provided script that runs one LangChain RAG flow and prints a single JSON object to stdout with `claim_uid` and metrics (provenance_quality, corroboration, contradiction_status, optional knowability):

```bash
PYTHONPATH=. python3 scripts/eval_harness_adapter.py
```

Your harness can run this script (or a variant that runs your own pipeline) and parse the JSON. On success you get one line of JSON; on missing investigation or claim you get an object with `error` and optional `claim_uid` / `investigation_uid`. See [Eval harness adapter](defensibility-metrics-schema.md#5-eval-harness-adapter-script-and-python-api).

**Option C: Python API inside your harness**

If your eval framework is in Python, call Chronicle directly after each run:

1. From the handler, get the session and investigation UID (e.g. `handler._get_session()`, `handler._investigation_uid`).
2. List claims for the investigation (e.g. `session.read_model.list_claims_by_type(investigation_uid=..., limit=...)`) and take the claim UID you care about (e.g. the last claim for the answer).
3. Call `chronicle.eval_metrics.defensibility_metrics_for_claim(session, claim_uid)`. It returns a dict with `claim_uid`, `provenance_quality`, `corroboration`, `contradiction_status`, and optionally `knowability`—or `None` if the claim has no scorecard.

Example pattern:

```python
from chronicle.eval_metrics import defensibility_metrics_for_claim

# After your RAG run, with session and claim_uid from the handler:
metrics = defensibility_metrics_for_claim(session, claim_uid)
if metrics:
    # Record for this run: metrics["provenance_quality"], metrics["corroboration"], etc.
    eval_results.append({"run_id": run_id, "claim_uid": claim_uid, "metrics": metrics})
```

**Option D: HTTP API**

If your pipeline uses the Chronicle HTTP API, after proposing the claim and linking support you have a `claim_uid`. Call `GET /claims/{claim_uid}/defensibility`. The response includes the same stable fields; use the subset in [Defensibility metrics schema](defensibility-metrics-schema.md) (claim_uid, provenance_quality, corroboration, contradiction_status, knowability) for evals.

---

## 4. Compare across configs

- **Same query, different configs** — Run the same question with e.g. different retrievers or models, each with Chronicle attached. Record defensibility metrics per run (e.g. in a table or JSON array). Compare `provenance_quality`, `corroboration.support_count`, `corroboration.challenge_count`, and `contradiction_status` across configs.
- **Fixed set of queries** — For a small benchmark, run a fixed set of queries through your Chronicle-backed RAG pipeline and save one metrics object per (query_id, config_id). You can then aggregate (e.g. average provenance_quality, count of "strong" claims) or feed into existing eval tooling that expects a metrics dict per run.
- **Stable investigation key** — To compare two frameworks (e.g. LangChain vs LlamaIndex) on the same question in one investigation, use the same `investigation_key`; both runs append to the same investigation and you get multiple claims. See `scripts/cross_framework_rag_chronicle.py`.

---

## 5. Fixed-query benchmark run

A **fixed set of queries** can be run through the same Chronicle-backed benchmark pipeline and defensibility recorded per answer. The script `scripts/benchmark_data/run_defensibility_benchmark.py` runs three queries, writes one investigation per query, and outputs a JSON file (or stdout) with `query_id`, `query`, `claim_uid`, and `metrics` for each. **How to reproduce:** From repo root, `PYTHONPATH=. python3 scripts/benchmark_data/run_defensibility_benchmark.py --mode session` (optional `--mode langchain`, `--output results.json`, or `--stdout`). See [Benchmark](benchmark.md) Section 1.3 for the full description and output shape.

---

## 6. Summary

| Step | What to do |
|------|------------|
| Run pipeline | **No pipeline:** use `scripts/standalone_defensibility_scorer.py` (stdin JSON). Or attach Chronicle handler (LangChain, LlamaIndex, Haystack) or use session/API; one investigation per run or per key. |
| Get claim | From handler: session + investigation UID, then list claims and take the claim UID for the answer. (Standalone scorer returns metrics directly.) |
| Get metrics | **Standalone:** `scripts/standalone_defensibility_scorer.py` (stdin JSON, stdout metrics). Script: `scripts/eval_harness_adapter.py` (stdout JSON). Python: `defensibility_metrics_for_claim(session, claim_uid)`. API: `GET /claims/{claim_uid}/defensibility`. |
| Compare | Record metrics per (run, config); compare provenance_quality, corroboration, contradiction_status across configs. |

For the canonical metrics fields and examples, see [Defensibility metrics schema](defensibility-metrics-schema.md). For benchmark datasets and the fixed-query defensibility run, see [Benchmark](benchmark.md).

---

## 7. Reporting Chronicle defensibility in papers

To use **Chronicle defensibility** as a reported measure in research papers (e.g. RAG evaluation, citation faithfulness, or defensible reasoning):

1. **Run your RAG pipeline with Chronicle** — Use the [standalone defensibility scorer](eval_contract.md#3-current-implementations) (`scripts/standalone_defensibility_scorer.py`) when you have (query, answer, evidence) and want metrics without a RAG stack; the [eval harness adapter](defensibility-metrics-schema.md#5-eval-harness-adapter-script-and-python-api) (`scripts/eval_harness_adapter.py`) for a single built-in RAG run; or [run_defensibility_benchmark](benchmark.md#13-fixed-query-defensibility-benchmark-rag-run) (`scripts/benchmark_data/run_defensibility_benchmark.py`) for a fixed set of queries. For custom pipelines, attach a Chronicle handler (LangChain, LlamaIndex, Haystack) or use the [minimum integration](integrating-with-chronicle.md#minimum-integration-rag-pipeline-query-answer-retrieved-docs); then call `defensibility_metrics_for_claim(session, claim_uid)` or `GET /claims/{claim_uid}/defensibility`.

2. **Record the metrics per answer** — The stable fields for reporting are: **provenance_quality** (strong | medium | weak | challenged), **corroboration** (support_count, challenge_count, independent_sources_count), **contradiction_status** (none | open | acknowledged | resolved), and optionally **knowability**. Same shape from the script stdout, Python API, or HTTP API. See [Defensibility metrics schema](defensibility-metrics-schema.md).

3. **Report in your results** — You can report e.g. "Chronicle defensibility (provenance_quality) per query," "mean support_count across runs," or "fraction of claims with contradiction_status = none." For reproducibility, state which script or integration you used (eval_harness_adapter, run_defensibility_benchmark, or custom) and the metrics subset you report.

4. **Cite** — Cite the [Technical report](technical-report.md) for the defensibility definition and schema, and this document or the [Benchmark](benchmark.md) for the eval harness and benchmark run. Example: "We report Chronicle defensibility (provenance_quality, corroboration) using the eval harness adapter (chronicle-standard); see technical report (defensibility definition, schema, use for evaluation)."

**Scripts at a glance:**

| Script | Purpose | Output |
|--------|---------|--------|
| `scripts/standalone_defensibility_scorer.py` | (query, answer, evidence) on stdin or `--query`/`--answer`/`--evidence`; no RAG stack; optional Docker | One JSON object (claim_uid + metrics or error) to stdout; exit 0/1 |
| `scripts/eval_harness_adapter.py` | One RAG run; hook for eval frameworks | One JSON object (claim_uid + metrics) to stdout |
| `scripts/benchmark_data/run_defensibility_benchmark.py` | Fixed queries; defensibility per answer | JSON file or stdout: `results[]` with query_id, claim_uid, metrics |
| `scripts/compliance_report_from_rag.py` | One RAG run; audit report (evidence, claim, brief, audit export) | Writes report dir + audit_report.json; for compliance/audit use cases |
