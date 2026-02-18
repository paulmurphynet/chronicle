# Quiz 06: Defensibility metrics

**Lesson:** [06-defensibility-metrics.md](../06-defensibility-metrics.md)

Answer these after reading the lesson and the claims/eval_metrics code. Try not to peek at the answer key until you've written your answers.

---

## Questions

1. In **get_defensibility_score**, what are the **four** possible values of **provenance_quality**?

2. When is **provenance_quality** set to **"challenged"**? (Condition in one sentence.)

3. Where does **independent_sources_count** come from? (What does the code count?)

4. What function converts a **DefensibilityScorecard** into the **stable metrics dict** that the eval contract expects?

5. Does defensibility depend on an external API or LLM? (Yes or no, and why.)

6. What is **sources_backing_claim** in the defensibility response, and what optional fields can each source include?

---

## Answer key

1. **strong**, **medium**, **weak**, **challenged**.

2. When **challenge_count > 0** (or challenge_weighted_sum > 0 if strength weighting is used)—i.e. when at least one evidence span is linked as **challenge** to the claim.

3. It counts **distinct source_uid** from **evidence_source_link** for the evidence items that back the claim via **support** links. So it's "how many distinct sources (as modeled by the user) support this claim."

4. **scorecard_to_metrics_dict(claim_uid, scorecard)** in **`chronicle/eval_metrics.py`**.

5. **No.** Defensibility is computed entirely from the **read model** (support/challenge counts, sources, tensions, claim status). No external API or LLM is called in get_defensibility_score.

6. **sources_backing_claim** is an optional list of sources that back the claim (when present in the API/export). Each entry can include **source_uid**, **display_name**, **independence_notes**, and **reliability_notes** (user-supplied; we record, we don't verify).

---

**← Previous:** [quiz-05-store-and-session](quiz-05-store-and-session.md) | **Index:** [Quizzes](README.md) | **Next →:** [quiz-07-integrations-and-scripts](quiz-07-integrations-and-scripts.md)
