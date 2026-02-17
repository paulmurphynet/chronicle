# Critical area 01: Defensibility is not truth

**Risk:** Treating a “strong” or “medium” defensibility score as meaning the claim is **true** or **reliable in the real world**. That is not what the score means.

---

## Narrative

Chronicle computes **defensibility**: how well a claim holds up *given the evidence and links that were recorded* and *given the policy rules you use* (e.g. how many supports, how many independent sources). We aggregate that into a label: `strong`, `medium`, `weak`, or `challenged`.

We **never** assert that a claim is true. We don’t have access to the world; we only have the events and the read model. So:

- **Strong** means: given what’s in the system (supports, sources, tensions), the structural and policy conditions for “strong” are met. It does **not** mean “this claim is factually correct.”
- **Weak** or **challenged** means: structurally, support is lacking or there are open challenges/tensions. It does **not** mean “this claim is false.”

Defensibility is **structural and policy-relative**. Truth is a different question—one we do not answer. Over-relying on the score as a proxy for truth is the main epistemological risk.

---

## Technical

- **Where the label is computed:** `chronicle/store/commands/claims.py`, in `get_defensibility_score()`. The logic (roughly): if there are any challenge links → `challenged`; else if support count ≥ 2 and independent_sources_count ≥ 2 → `strong`; else if support count ≥ 1 → `medium`; else → `weak`. Open tensions can also affect `contradiction_status`. So **provenance_quality** is derived only from **counts and statuses** in the read model, not from any external fact-check.
- **Where it’s exposed:** `chronicle/eval_metrics.py` turns the scorecard into the stable metrics dict (e.g. for the scorer and eval contract). The scorer in `scripts/standalone_defensibility_scorer.py` returns that shape to stdout. The schema and field semantics are in `docs/defensibility-metrics-schema.md` and `docs/technical-report.md`; both state that defensibility is not a truth value.

---

## What to remember

- **Defensibility = structure + policy, not truth.** Use the score to see how well the *recorded* evidence and *recorded* links support the claim—not to decide whether the claim is correct in the world.
- **Document this** when you present scores (e.g. in dashboards or reports): e.g. “Defensibility reflects support structure and policy; it does not certify factual correctness.”
