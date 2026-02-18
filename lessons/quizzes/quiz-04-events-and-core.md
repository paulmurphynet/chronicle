# Quiz 04: Events and core

**Lesson:** [04-events-and-core.md](../04-events-and-core.md)

Answer these after reading the lesson and the core module. Try not to peek at the answer key until you've written your answers.

---

## Questions

1. Where are **event type constants** (e.g. EvidenceIngested, ClaimProposed) defined?

2. What is the **payload** of an event? Where are payload shapes defined?

3. Which **three** event types are involved in the minimal scorer flow: ingest evidence → propose answer as claim → link support?

4. Does the **read model** (claim table, evidence_link table) get updated when an event is appended? If so, how?

5. What does **event-sourced** mean in one sentence?

---

## Answer key

1. **`chronicle/core/events.py`** — constants like `EVENT_EVIDENCE_INGESTED`, `EVENT_CLAIM_PROPOSED`, etc., and the `EVENT_TYPES` frozenset.

2. The **payload** is the event-specific data (e.g. claim_uid, claim_text, span_uid). Payload shapes are defined as **dataclasses** in **`chronicle/core/payloads.py`** (e.g. ClaimProposedPayload, EvidenceIngestedPayload).

3. **EvidenceIngested** (per chunk), **SpanAnchored** (per chunk), **ClaimProposed** (the answer), **SupportLinked** (per span–claim pair). (SpanAnchored is typically created when we anchor a span for each evidence item; the scorer flow does ingest → anchor_span → propose_claim → link_support.)

4. Yes. When an event is appended, a **projection handler** runs (in `chronicle/store/read_model/projection.py`) that updates the read model tables (e.g. handle_claim_proposed updates the claim table; handle_support_linked inserts into evidence_link).

5. **Event-sourced** means all changes are stored as append-only events; state (the read model) is derived by replaying or projecting from those events, not by overwriting.

---

**← Previous:** [quiz-03-the-verifier](quiz-03-the-verifier.md) | **Index:** [Quizzes](README.md) | **Next →:** [quiz-05-store-and-session](quiz-05-store-and-session.md)
