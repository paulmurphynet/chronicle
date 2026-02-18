# Lesson 02: The standalone defensibility scorer

**Objectives:** You’ll understand how the scorer gets its input, how it uses the Chronicle session under the hood, and what it outputs. You’ll have run it yourself.

**Key files:**

- [scripts/standalone_defensibility_scorer.py](../scripts/standalone_defensibility_scorer.py) — scorer implementation  
- [docs/eval_contract.md](../docs/eval_contract.md) — input/output contract  

---

## What the scorer does

The scorer is the main “product” surface for evals: **one (query, answer, evidence) in → one defensibility metrics JSON out.** No API or RAG stack required. It implements the [eval contract](../docs/eval_contract.md) so eval harnesses can plug in without depending on our internals.

High-level flow:

1. Parse input (stdin or CLI flags): `query`, `answer`, `evidence` (list of strings or objects with `text`/`path`).  
2. Create a temporary project and session.  
3. Ingest each evidence chunk, propose the answer as a claim, link each chunk as support.  
4. Compute defensibility and serialize it to the contract output shape.  
5. Print one JSON object to stdout (metrics or error).

**Important:** The default scorer links *every* evidence chunk as **support** for the single claim. It does **not** validate that evidence actually supports the claim. For higher assurance (e.g. human-curated or NLI-validated links), record links via the session or API after validation; see the caveat in [eval contract](../docs/eval_contract.md) and [benchmark](../docs/benchmark.md).

## Key code: input and validation

Open **`scripts/standalone_defensibility_scorer.py`**.

- **`_run_scorer(stdin_input)`** (around lines 98–122): parses JSON, validates `query` (string), `answer` (string), `evidence` (array). If invalid, it returns an error object with `contract_version: "1.0"` and e.g. `{"error": "invalid_input", "message": "..."}`.
- **`_normalize_evidence(evidence)`** (around lines 75–96): turns the evidence list into a list of text chunks. Strings are used as-is (if non-empty); objects can have `text`, `path` (file read from disk), or `url` (fetched with SSRF safeguards). This matches the contract’s evidence formats.

So: **input** is exactly the eval contract input; **validation** happens before any Chronicle code runs.

## Key code: temp project and session

- **Around lines 124–185:** The script creates a temporary directory and calls `create_project(path)` (from `chronicle.store.project`), then opens a **ChronicleSession** for that project. The session is the API you use to ingest evidence, propose claims, link support, and get defensibility.
- Evidence is ingested (one chunk per item, with `anchor_span` per chunk); then the **answer** is proposed as a single claim; then each evidence span is linked as **support** for that claim. All of that goes through the session (event-sourced under the hood).
- Defensibility is read via **`defensibility_metrics_for_claim(session, claim_uid)`** and merged into the output with **`contract_version: "1.0"`**.

We’ll go deeper into the session in Lesson 05; for now it’s enough to know that the scorer is a thin script that: creates project + session → ingest → anchor spans → propose claim → link support → get defensibility → print JSON.

## Key code: output shape

After the session has run, the script gets the defensibility result and converts it to the **eval contract output** shape (claim_uid, provenance_quality, corroboration, contradiction_status, optional knowability, etc.). That shape is defined in [docs/defensibility-metrics-schema.md](../docs/defensibility-metrics-schema.md) and in the contract. The script prints one JSON object to stdout—either that metrics object (with `contract_version: "1.0"`) or an error object.

## Try it

From repo root (with `pip install -e .` and venv activated if you use one):

```bash
echo '{"query": "What was revenue?", "answer": "Revenue was $1.2M.", "evidence": ["The company reported revenue of $1.2M in Q1 2024."]}' \
  | PYTHONPATH=. python3 scripts/standalone_defensibility_scorer.py
```

You should see one JSON object with `claim_uid`, `provenance_quality`, `corroboration`, `contradiction_status`, etc. If you pass invalid JSON or missing fields, you’ll get an `error` object instead.

## Summary

- The scorer reads **query**, **answer**, and **evidence** (contract input), validates and normalizes evidence, then uses a **temporary project and session** to ingest evidence, propose the answer as a claim, link support, and compute defensibility.  
- Output is **one JSON object** per run: either the defensibility metrics (contract success) or an error object.  
- The implementation is in `scripts/standalone_defensibility_scorer.py`; the contract is in `docs/eval_contract.md`.

**← Previous:** [Lesson 01: Codebase map](01-codebase-map.md) | **Index:** [Lessons](README.md) | **Next →:** [Lesson 03: The verifier](03-the-verifier.md)

**Quiz:** [quizzes/quiz-02-the-scorer.md](quizzes/quiz-02-the-scorer.md)
