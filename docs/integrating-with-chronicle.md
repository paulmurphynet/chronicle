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

---

## Idempotency for agents and pipelines

When the same scenario (e.g. query id or scenario id) is run multiple times, you can reuse the same investigation by passing an **investigation_key** (or equivalent) so that the backend creates or looks up the investigation by that key. That way "same question, different config" can be compared in one place. Implementation details depend on your API or session wrapper; the event store supports idempotency keys for commands where applicable.

---

## References

| Doc | Description |
|-----|-------------|
| [HTTP API](api.md) | Optional minimal API: write/read/export over HTTP when you install `.[api]`. |
| [Eval contract](eval_contract.md) | Input/output for the scorer; plugging into eval harnesses. |
| [Eval and benchmarking](eval-and-benchmarking.md) | Running pipelines and extracting metrics. |
| [Defensibility metrics schema](defensibility-metrics-schema.md) | Scorecard fields and API. |
