# Chapter 02: Scorer

**Contents:** Score one (query, answer, evidence) run; eval contract; stdin and CLI.

---

## One run in, metrics out

The standalone defensibility scorer takes one JSON object (query, answer, evidence) and prints one JSON object (defensibility metrics or error). No project or API required.

```bash
echo '{"query": "What was revenue?", "answer": "Revenue was $1.2M.", "evidence": ["The company reported revenue of $1.2M in Q1 2024."]}' \
  | PYTHONPATH=. python3 scripts/standalone_defensibility_scorer.py
```

---

## Contract and schema

- **Input:** `query` (string), `answer` (string), `evidence` (array of strings or objects with `text`/`path`/`url`).
- **Output:** `contract_version`, `claim_uid`, `provenance_quality`, `corroboration`, `contradiction_status`, and more. See [Eval contract](../eval_contract.md) and [Defensibility metrics schema](../defensibility-metrics-schema.md).

---

## CLI flags

You can pass `--query`, `--answer`, and `--evidence` instead of stdin. See [Eval contract](../eval_contract.md#3-current-implementations).

---

**← Previous:** [01 — Install](01-install.md) | **Index:** [Manual](README.md) | **Next →:** [03 — Verifier](03-verifier.md)
