# Lesson 04: Events and core

**Objectives:** You’ll understand Chronicle’s event model: what an event is, how event types are defined, and how payloads carry the data. You’ll know where the “language” of the system lives.

**Key files:**

- [chronicle/core/events.py](../chronicle/core/events.py) — event type constants and Event envelope
- [chronicle/core/payloads.py](../chronicle/core/payloads.py) — payload dataclasses per event type
- [docs/technical-report.md](../docs/technical-report.md) — defensibility and schema (Section 3)

---

## Why events matter

Chronicle is **event-sourced**: every change (evidence ingested, claim proposed, support linked, tension declared) is stored as an **event**. The read model (investigations, claims, evidence_item, evidence_link, tension tables) is **derived** by replaying these events. So the **event model** is the language of the system: if you want to understand what Chronicle can record, you look at the event types and their payloads.

## Event types

Open **`chronicle/core/events.py`**.

- **Lines 6–44:** Event type **constants** (strings). Examples: `EVENT_EVIDENCE_INGESTED`, `EVENT_CLAIM_PROPOSED`, `EVENT_SPAN_ANCHORED`, `EVENT_SUPPORT_LINKED`, `EVENT_TENSION_DECLARED`, `EVENT_CLAIM_WITHDRAWN`, etc. Every action that changes state has a corresponding event type.
- **`EVENT_TYPES`:** A frozenset of all known types so the system can validate that an event type is recognized.

The flow you’ve already seen (scorer: ingest evidence → propose claim → link support) corresponds to: **EvidenceIngested** → **ClaimProposed** → **SpanAnchored** (for each evidence chunk) → **SupportLinked** (for each span–claim pair).

## Event envelope

Events are stored with more than just a type and payload. The **Event** dataclass (in the same file) includes:

- **event_id**, **event_type** — Identity and kind.
- **occurred_at**, **recorded_at** — When it happened and when it was recorded.
- **investigation_uid**, **subject_uid** — Which investigation and which entity (e.g. claim_uid, evidence_uid) this event is about.
- **actor_type**, **actor_id** — Who did it (human, tool, system).
- **payload** — The event-specific data (e.g. claim_text, span_uid, link_type).
- **idempotency_key**, **prev_event_hash**, **event_hash** — For deduplication and chain integrity.

So when you “propose a claim,” the system appends an event with `event_type=ClaimProposed` and a payload containing `claim_uid`, `claim_text`, and related fields.

## Payloads

Open **`chronicle/core/payloads.py`**.

- Each event type has a **payload class** (dataclass) that defines the shape of its data. Examples:
  - **EvidenceIngestedPayload** — evidence_uid, content_hash, media_type, uri, optional provenance_type.
  - **ClaimProposedPayload** — claim_uid, claim_text, optional type, parent_claim_uid, etc.
  - **SupportLinked** / **ChallengeLinked** — span_uid, claim_uid, link_type, optional strength.
  - **TensionDeclaredPayload** — claim_a_uid, claim_b_uid, tension_kind, notes.
- Payloads have **to_dict** and **from_dict** (or equivalent) so they can be serialized to JSON for storage and deserialized when replaying.

You don’t need to memorize every payload; the point is: **the core package defines what can happen**. The store (next lesson) appends events and runs **projections** that update the read model from these events.

## Try it

1. In **`chronicle/core/events.py`**, count how many event types there are (length of `EVENT_TYPES` or count the constants).
2. In **`chronicle/core/payloads.py`**, find **ClaimProposedPayload** and list the fields it contains. Compare with the technical report Section 3.2 (Claim).

## Summary

- **Events** are the source of truth; each change is an event (EvidenceIngested, ClaimProposed, SupportLinked, TensionDeclared, etc.).
- **Event types** live in `chronicle/core/events.py`; **payloads** live in `chronicle/core/payloads.py`.
- The **read model** (tables like claim, evidence_item, evidence_link) is built by **projecting** these events—we’ll see that in Lesson 05.

**← Previous:** [Lesson 03: The verifier](03-the-verifier.md) | **Index:** [Lessons](README.md) | **Next →:** [Lesson 05: Store and session](05-store-and-session.md)

**Quiz:** [quizzes/quiz-04-events-and-core.md](quizzes/quiz-04-events-and-core.md)
