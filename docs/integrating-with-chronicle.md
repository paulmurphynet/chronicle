# Integrating with Chronicle

This doc describes the **minimum integration** for RAG pipelines (or other systems) that want to record evidence and claims in Chronicle and read defensibility.

---

## Minimum integration (RAG: query, answer, retrieved docs)

1. **Create a project and investigation** — Use the Chronicle session API or HTTP API: create a project directory (or use an existing one), create an investigation (e.g. one per run or per query), get `investigation_uid`.
2. **Ingest evidence** — For each retrieved document or chunk, call `session.ingest_evidence(inv_uid, content_bytes, media_type)` (and optionally `anchor_span` if you want span-level links). Record the returned `evidence_uid` and any `span_uid`.
3. **Propose the answer as a claim** — `session.propose_claim(inv_uid, answer_text, ...)`. Record `claim_uid`.
4. **Link support** — For each evidence span that supports the answer, call `session.link_support(inv_uid, span_uid, claim_uid)`.
5. **Read defensibility** — `session.get_defensibility_score(claim_uid)` or the equivalent API returns the scorecard (provenance_quality, corroboration, contradiction_status, etc.). See [Defensibility metrics schema](defensibility-metrics-schema.md).

No RAG framework is required: the [standalone defensibility scorer](eval_contract.md#3-current-implementations) (`scripts/standalone_defensibility_scorer.py`) does exactly this in-process for a single (query, answer, evidence) input and outputs the metrics JSON. **Your RAG harness → our scorer** is the standard path: see [RAG evals: defensibility metric](rag-evals-defensibility-metric.md) for the contract, schema, and a Python example; an optional copy-paste adapter template is in [scripts/adapters/example_rag_to_scorer.py](../scripts/adapters/example_rag_to_scorer.py).

**Limits of the standalone scorer:** In that path, every evidence chunk is linked as support (no entailment check); evidence is not linked to sources, so `independent_sources_count` is typically 0; and evidence can be strings or objects with `text`, `path`, or `url` (URLs fetched with SSRF safeguards). See [RAG evals §5](rag-evals-defensibility-metric.md#5-limits-of-the-standalone-scorer) and [Critical areas](../critical_areas/README.md).

---

## Happy path by framework

Each integration follows the same pattern: create project/investigation, ingest retrieved docs as evidence, propose the answer as a claim, link support, then read defensibility. Minimal runnable demos are in `scripts/`; use them as templates.

| Framework | Script | Happy path |
|-----------|--------|------------|
| **LangChain** | `scripts/langchain_rag_chronicle.py` | Install `chronicle-standard` and `langchain-core` (or `langchain`). Add `ChronicleRagCallbackHandler(project_path=..., investigation_title=...)` to your chain's `callbacks`. On retriever end, docs are ingested as evidence; on chain end, the answer is proposed as a claim and linked to that evidence. Run the script for a minimal example. |
| **LlamaIndex** | `scripts/llamaindex_rag_chronicle.py` | Install `chronicle-standard` and `llama-index-core` (or `llama-index`). Attach a Chronicle callback to the query engine's callback manager. RETRIEVE events → evidence; SYNTHESIZE end → claim + support links. Run the script for a minimal example. |
| **Haystack** | `scripts/haystack_rag_chronicle.py` | Install `chronicle-standard` and `haystack-ai`. Add `ChronicleEvidenceWriter` to your pipeline after the retriever/generator; connect documents and (optionally) claim output. Run the script for a minimal example. |
| **Cross-framework** | `scripts/cross_framework_rag_chronicle.py` | Same flow across frameworks; use when you want one demo that compares or switches. |

Integration modules live in `chronicle/integrations/` (langchain.py, llamaindex.py, haystack.py). Each module docstring describes required packages and usage.

---

## Adding defensibility to an eval harness

To add Chronicle defensibility as a **metric** in a RAG eval framework (e.g. RAGAS, Trulens, LangSmith evals, or a custom harness):

1. **Contract:** One run = one (query, answer, evidence) in → one defensibility metrics object out. See [Eval contract](eval_contract.md) and [eval_contract_schema.json](eval_contract_schema.json).
2. **Invoke the scorer:** Pipe JSON to `scripts/standalone_defensibility_scorer.py` or call `defensibility_metrics_for_claim(session, claim_uid)` after building the session (ingest → propose claim → link support). The output shape is stable (claim_uid, provenance_quality, corroboration, contradiction_status, optional knowability).
3. **Adapter:** Use [scripts/adapters/example_rag_to_scorer.py](../scripts/adapters/example_rag_to_scorer.py) as a copy-paste template: read (query, answer, evidence) from your harness (stdin or file), call the scorer, print metrics JSON. Your harness then parses the JSON and records the metric per run.

No Chronicle-specific server is required; the scorer runs in-process. For benchmarks and reporting, see [Eval and benchmarking](eval-and-benchmarking.md) and [Defensibility benchmark](benchmark.md).

**Framework-specific (RAGAS, Trulens, LangSmith):** These frameworks let you add custom metrics. Add a metric that, per run, takes (query, answer, contexts), invokes the Chronicle scorer (stdin → `standalone_defensibility_scorer.py` or in-process `defensibility_metrics_for_claim`), and records the result (e.g. `provenance_quality`, `corroboration.support_count`). Example pattern:

```python
# Pseudocode: one run → one defensibility metric
def defensibility_metric(run: Run) -> float | dict:
    payload = {"query": run.query, "answer": run.answer, "evidence": run.contexts}
    result = run_scorer(payload)  # standalone_defensibility_scorer or session path
    return result.get("provenance_quality") or result  # or map to your framework's score
```

Use [scripts/adapters/example_rag_to_scorer.py](../scripts/adapters/example_rag_to_scorer.py) as the scorer bridge; your framework then calls it per run and aggregates.

---

## Idempotency for agents and pipelines

When the same scenario (e.g. query id or scenario id) is run multiple times, you can reuse the same investigation by passing an **investigation_key** (or equivalent) so that the backend creates or looks up the investigation by that key. That way "same question, different config" can be compared in one place. Implementation details depend on your API or session wrapper; the event store supports idempotency keys for commands where applicable.

---

## Human-curated data and attestation

When a human (or tool) curates evidence and claims—e.g. transcript ingestion, manual link confirmation—you can attribute every write to an actor. Use **CLI:** set `CHRONICLE_ACTOR_ID` and optionally `CHRONICLE_ACTOR_TYPE` (or pass `--actor-id` / `--actor-type` on write commands). Use **HTTP API:** set headers `X-Actor-Id` and `X-Actor-Type` on each write request. The ledger records who did what; with an IdP you can optionally persist verification level. See [Human-in-the-loop and attestation](human-in-the-loop-and-attestation.md) for the full workflow (identity, human_confirm/human_override, export for verification).

---

## References

| Doc | Description |
|-----|-------------|
| [RAG in 5 minutes](rag-in-5-minutes.md) | One command (`chronicle quickstart-rag`) to try the flow; then scorer or session integration. |
| [HTTP API](api.md) | Optional minimal API: write/read/export over HTTP when you install `.[api]`. |
| [Eval contract](eval_contract.md) | Input/output for the scorer; plugging into eval harnesses. |
| [Eval and benchmarking](eval-and-benchmarking.md) | Running pipelines and extracting metrics. |
| [Defensibility metrics schema](defensibility-metrics-schema.md) | Scorecard fields and API. |
| [Human-in-the-loop and attestation](human-in-the-loop-and-attestation.md) | Actor identity, curation workflow, attestation. |
