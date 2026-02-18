# Lesson 06: How defensibility is computed

**Objectives:** You’ll know where the defensibility scorecard is built, what inputs it uses (support/challenge counts, sources, tensions), and how the **provenance_quality** label (strong / medium / weak / challenged) is derived. You’ll see how the scorer’s output shape is produced.

**Key files:**

- [chronicle/store/commands/claims.py](../chronicle/store/commands/claims.py) — `get_defensibility_score` (and related)
- [chronicle/eval_metrics.py](../chronicle/eval_metrics.py) — `scorecard_to_metrics_dict`, `defensibility_metrics_for_claim`
- [docs/defensibility-metrics-schema.md](../docs/defensibility-metrics-schema.md) — field semantics

---

## What defensibility is (recap)

Defensibility is **not** a truth value. It’s a **structural and policy-relative** summary: given the recorded evidence, support/challenge links, tensions, and (optionally) policy rules, how well does the claim hold up? The scorecard includes: **provenance_quality** (strong | medium | weak | challenged), **corroboration** (support_count, challenge_count, independent_sources_count), **contradiction_status** (none | open | acknowledged | resolved), **weakest_link**, and optional **knowability**. See [Critical areas: Defensibility is not truth](../critical_areas/01-defensibility-is-not-truth.md).

## Where it’s computed

Open **`chronicle/store/commands/claims.py`**.

- **get_defensibility_score(read_model, claim_uid, use_strength_weighting=False, policy_profile=None)** (around line 755) is the main function. It:
  1. Loads the claim; returns None if not found or status is WITHDRAWN.
  2. Gets all **support** and **challenge** links for the claim (including inherited from parent if it’s a compound claim). Counts them and, optionally, sums their **strength** (0..1).
  3. Counts **independent_sources_count**: distinct sources (from evidence_source_link) that back the claim via supporting evidence.
  4. Sets **provenance_quality**: if any challenge → `"challenged"`; else if support_count ≥ 2 and independent_sources_count ≥ 2 → `"strong"`; else if support_count ≥ 1 → `"medium"`; else → `"weak"`. (With strength weighting, it uses weighted sums and similar thresholds.)
  5. Gets **tensions** for the claim; sets **contradiction_status** from their statuses (open → "open", etc.).
  6. Builds **knowability** from claim temporal_json (known_as_of, knowable_from), **decomposition_precision**, **evidence_integrity**, and other dimensions.
  7. Returns a **DefensibilityScorecard** (dataclass) with all these fields.

So the logic is **entirely in the read model**: no external API, no LLM. Counts and statuses drive the label.

## From scorecard to eval contract output

Open **`chronicle/eval_metrics.py`**.

- **scorecard_to_metrics_dict(claim_uid, scorecard)** — Converts a `DefensibilityScorecard` into the **stable dict** that the eval contract expects: claim_uid, provenance_quality, corroboration (support_count, challenge_count, independent_sources_count), contradiction_status, optional knowability. This is what the scorer prints as JSON.
- **defensibility_metrics_for_claim(session, claim_uid)** — Convenience: calls `session.get_defensibility_score(claim_uid)` and then `scorecard_to_metrics_dict`. Eval harnesses can use this to get the same shape without touching the scorecard directly.

The **defensibility-metrics-schema** doc defines each field so that harnesses and papers can rely on a stable shape.

## Try it

1. In **claims.py**, read the block that sets `provenance_quality` (around lines 805–812). Note the exact conditions for strong, medium, weak, challenged.
2. In **eval_metrics.py**, confirm that **scorecard_to_metrics_dict** only includes the keys listed in the defensibility-metrics-schema (no extra internal fields).

## Summary

- **get_defensibility_score** in `chronicle/store/commands/claims.py` computes the scorecard from the read model (support/challenge counts, sources, tensions, claim status).
- **provenance_quality** is derived from counts and thresholds; **contradiction_status** from tension statuses.
- **eval_metrics.py** turns the scorecard into the **stable metrics dict** for the eval contract and scorer output.

**← Previous:** [Lesson 05: Store and session](05-store-and-session.md) | **Index:** [Lessons](README.md) | **Next →:** [Lesson 07: Integrations and scripts](07-integrations-and-scripts.md)

**Quiz:** [quizzes/quiz-06-defensibility-metrics.md](quizzes/quiz-06-defensibility-metrics.md)
