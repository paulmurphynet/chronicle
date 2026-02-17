# Quiz 01: Codebase map

**Lesson:** [01-codebase-map.md](../01-codebase-map.md)

Answer these after reading the lesson and looking at the repo layout. Try not to peek at the answer key until you’ve written your answers.

---

## Questions

1. What are the **two main entry points** a user runs for scoring and verification? (Give the script/tool path or name for each.)

2. Where does the **defensibility metrics** structure (the shape of the scorer output) get defined? (Name the doc or file.)

3. Which folder contains the **event model** and core types (payloads, UIDs, validation)?

4. What is the **eval contract**? (One sentence.)

5. Where do the **RAG integration hooks** (e.g. LangChain, LlamaIndex) live in the repo?

---

## Answer key

1. **Scorer:** `scripts/standalone_defensibility_scorer.py`. **Verifier:** `chronicle-verify` CLI (implementation in `tools/verify_chronicle/`).

2. The defensibility metrics shape is defined in **`docs/defensibility-metrics-schema.md`** and used by the scorer to match the eval contract; the code that builds it is in **`chronicle/eval_metrics.py`**.

3. **`chronicle/core/`** — events, payloads, UIDs, validation, policy.

4. The **eval contract** is the agreed input (query, answer, evidence) and output (defensibility metrics or error) for the defensibility scorer so that eval harnesses can plug in without depending on implementation details. Defined in `docs/eval_contract.md`.

5. **`chronicle/integrations/`** — e.g. LangChain, LlamaIndex, Haystack.
