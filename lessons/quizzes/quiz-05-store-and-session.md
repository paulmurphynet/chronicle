# Quiz 05: Store and session

**Lesson:** [05-store-and-session.md](../05-store-and-session.md)

Answer these after reading the lesson and the store/session code. Try not to peek at the answer key until you've written your answers.

---

## Questions

1. What are the **three layers** (event store, projection, read model) in one sentence each?

2. Which **session method** do you call to add a support link from an evidence span to a claim?

3. Where does the **scorer** create its project and session? (Which script and roughly where?)

4. What does **handle_support_linked** in the projection do? (Which table does it write to?)

5. What does **get_defensibility_score** return? (Type or shape.)

6. What **optional** parameters can you pass when linking support, linking challenge, or declaring a tension? (Hint: warrant, defeater type, source metadata.)

---

## Answer key

1. **Event store**: Appends events to the events table (SQLite). **Projection**: Handlers run when events are appended and update the read model tables. **Read model**: Tables (investigation, claim, evidence_item, evidence_link, tension, etc.) that queries read from.

2. **session.link_support(inv_uid, span_uid, claim_uid)**.

3. In **`scripts/standalone_defensibility_scorer.py`**: it creates a **temporary directory**, calls **create_project** (or equivalent), then opens a **ChronicleSession** for that path. After building the investigation, evidence, claim, and links, it calls get_defensibility_score and serializes the result.

4. **handle_support_linked** inserts a row into the **evidence_link** table (span_uid, claim_uid, link_type=SUPPORT, etc.).

5. **get_defensibility_score** returns a **DefensibilityScorecard** (or None if claim not found or withdrawn)—a dataclass with provenance_quality, corroboration, contradiction_status, weakest_link, knowability, etc.

6. **link_support**: optional **rationale** (warrant), **strength**. **link_challenge**: optional **rationale**, **defeater_kind** (e.g. rebutting, undercutting). **declare_tension**: optional **defeater_kind**. **register_source**: optional **reliability_notes**. **propose_claim**: optional **epistemic_stance**. We record these; we don't verify them.

---

**← Previous:** [quiz-04-events-and-core](quiz-04-events-and-core.md) | **Index:** [Quizzes](README.md) | **Next →:** [quiz-06-defensibility-metrics](quiz-06-defensibility-metrics.md)
