# Integration quick reference

One page for evaluators and engineers: how to score a run, verify a .chronicle, add defensibility to your harness, and (optionally) use the session API or HTTP API. For full detail, follow the linked docs.

---

## 1. Score one run (no project)

**Input:** One JSON object: `query`, `answer`, `evidence` (array).  
**Output:** One JSON object: defensibility metrics or error.

```bash
echo '{"query": "What was revenue?", "answer": "Revenue was $1.2M.", "evidence": ["The company reported revenue of $1.2M in Q1 2024."]}' \
  | PYTHONPATH=. python3 scripts/standalone_defensibility_scorer.py
```

- **Contract and schema:** [Eval contract](eval_contract.md), [Defensibility metrics schema](defensibility-metrics-schema.md), [eval_contract_schema.json](eval_contract_schema.json).
- **In-process:** Call `_run_scorer(json.dumps(input_obj))` from `scripts/standalone_defensibility_scorer` or run the script via subprocess and parse stdout.

---

## 2. Verify a .chronicle file

```bash
chronicle-verify path/to/file.chronicle
```

Exit 0 = structurally valid (manifest, schema, evidence hashes). See [Verifier](verifier.md) and [Verification guarantees](verification-guarantees.md) for what is and is not guaranteed.

---

## 3. Add defensibility to your harness

- Use the **same contract** as above: one (query, answer, evidence) in → one metrics object out.
- In your eval loop: for each run, build the input JSON, call the scorer (stdin or in-process), record `provenance_quality`, `corroboration`, `contradiction_status`, etc.
- **RAG evals (full guide):** [RAG evals: defensibility metric](rag-evals-defensibility-metric.md) — contract, schema, and how to run the scorer in your RAG harness.
- **Frameworks:** RAGAS, Trulens, LangSmith (and custom harnesses) can add a custom metric that invokes the scorer; see [Integrating with Chronicle](integrating-with-chronicle.md).

---

## 4. Optional: session API, HTTP API, adapters

- **Session API** — For project-based workflows: create project, investigation, ingest evidence, propose claim, link support, get defensibility. Used by the scorer under the hood. See [Integrating with Chronicle](integrating-with-chronicle.md) and [RAG in 5 minutes](rag-in-5-minutes.md).
- **HTTP API** — `pip install -e ".[api]"`, set `CHRONICLE_PROJECT_PATH`, run `uvicorn chronicle.api.app:app`. **POST /score** gives scorer-as-a-service (no project path; same contract). See [API](api.md).
- **Adapters** — Example adapters in `scripts/adapters/`: RAG→scorer, fact-checker→Chronicle, provenance→Chronicle. Copy-paste templates for interop.

---

## Where to go next

| Goal | Doc |
|------|-----|
| First run in 5 minutes | [RAG in 5 minutes](rag-in-5-minutes.md) |
| Eval contract and schema | [Eval contract](eval_contract.md), [Defensibility metrics schema](defensibility-metrics-schema.md) |
| Harness integration | [RAG evals: defensibility metric](rag-evals-defensibility-metric.md), [Integrating with Chronicle](integrating-with-chronicle.md) |
| Produce/consume .chronicle | [Implementer checklist](implementer-checklist.md), [Chronicle file format](chronicle-file-format.md) |
| Limits (what we don't guarantee) | [Critical areas](../critical_areas/README.md) |
