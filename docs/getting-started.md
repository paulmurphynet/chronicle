# Getting started with Chronicle

One page: what Chronicle is, how to install it, and how to run the scorer and verifier. After this, go to the [Story](story/README.md) for the story or [Lessons](lessons/README.md) for the codebase walkthrough.

---

## What Chronicle is

Chronicle answers: **How well is this answer supported by evidence?** It’s for RAG evaluation, audits, and anyone who needs a portable, verifiable record of claims and their evidence. We don’t assert “truth”—we score **defensibility** (support, challenges, sources, tensions) and provide a **.chronicle** format and **verifier** so others can check “show your work” without running our full stack.

---

## Prerequisites

- **Python 3.11+**
- A virtual environment is recommended (e.g. `python3 -m venv .venv` then `source .venv/bin/activate` on Linux/macOS).

---

## Install

From the repo root:

```bash
pip install -e .
```

This installs the `chronicle` and `chronicle-verify` commands. If you use a venv, activate it first so the commands are on your PATH.

---

## Quick start: scorer and verifier

**1. Score one (query, answer, evidence) run**

```bash
echo '{"query": "What was revenue?", "answer": "Revenue was $1.2M.", "evidence": ["The company reported revenue of $1.2M in Q1 2024."]}' \
  | PYTHONPATH=. python3 scripts/standalone_defensibility_scorer.py
```

You get one JSON object with defensibility metrics (or an error). See [Eval contract](eval_contract.md).

**2. Verify a .chronicle file**

```bash
chronicle-verify path/to/file.chronicle
```

To get a sample .chronicle to verify: `PYTHONPATH=. python3 scripts/generate_sample_chronicle.py`, then verify the file it creates. See [Verifier](verifier.md).

**3. Run the defensibility benchmark** (reproducible: fixed queries, RAG run, record scores):

```bash
PYTHONPATH=. python3 scripts/benchmark_data/run_defensibility_benchmark.py
```

See [Benchmark](benchmark.md) for options and sample generation.

---

## Next steps

- **Understand the project** — Read the [Story](story/README.md) (mission, vision, problem, approach, limits), then [Lessons](lessons/README.md) (codebase walkthrough). Before relying on scores or verification, read [Critical areas](../critical_areas/README.md).
- **Run the scorer in your pipeline** — [Eval contract](eval_contract.md), [RAG evals: defensibility metric](rag-evals-defensibility-metric.md), [Integrating with Chronicle](integrating-with-chronicle.md).
- **Contribute** — [CONTRIBUTING](../CONTRIBUTING.md), [Lessons](lessons/README.md).
