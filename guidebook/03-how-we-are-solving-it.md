# How we’re solving it

We’re not trying to decide what’s true. We’re trying to make **how well a claim is supported** visible, scoreable, and verifiable.

---

## Evidence and claims

We treat **evidence** as first-class: immutable items (e.g. retrieved chunks or documents), often content-hashed so they can’t be changed without detection. **Claims** are the statements we care about—for example, the answer a RAG system produced. We don’t store “this is true”; we store that this claim was **proposed**, **linked** to evidence (support or challenge), and then we **compute** how defensible it is given those links and the rules you use.

---

## Defensibility score

We compute a **defensibility** result: things like strength of provenance, how many sources support the claim, whether there are open contradictions, and (optionally) temporal or knowability information. That result is a **scorecard**—a stable shape that eval harnesses and tools can consume. So “how defensible is this answer?” becomes a number and a structure, not a vague feeling.

---

## One run in, one score out

For RAG and evals, we keep the contract simple: **one (query, answer, evidence) in → one defensibility metrics object out.** No API server required. You can run our standalone scorer in a pipeline, or call the same logic from your own code. That makes it easy to add “Chronicle defensibility” as a metric alongside whatever else you already measure.

---

## .chronicle and “verify it yourself”

We also define a portable format: **.chronicle**. It’s a package (e.g. a ZIP) that contains the investigation’s manifest, schema, evidence, and claims. Anyone can **verify** it with our verifier—no need to run our full stack or trust us. So “show your work” becomes a **verifiable artifact**, not a promise. That’s how we try to close the loop: you produce a defensible record; others can check it.

---

## Event-sourced and auditable

Under the hood, we record **events**—every ingest, every claim, every link—and never erase them. So the story of how an answer was built is preserved. That supports auditing, debugging, and future extensions (e.g. “how defensible was this claim as of last Tuesday?”).

---

**Next:** [04 — Where challenges remain](04-where-challenges-remain.md)
