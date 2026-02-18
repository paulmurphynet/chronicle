# Lesson 05: Store, read model, and session API

**Objectives:** You’ll understand how events are stored, how the read model is updated (projection), and how the **session API** gives you a single entry point to create investigations, ingest evidence, propose claims, and link support. You’ll see how the scorer’s flow maps onto session methods.

**Key files:**

- [chronicle/store/session.py](../chronicle/store/session.py) — ChronicleSession and its methods
- [chronicle/store/read_model/projection.py](../chronicle/store/read_model/projection.py) — event → read model handlers
- [chronicle/store/sqlite_event_store.py](../chronicle/store/sqlite_event_store.py) — appends events and runs projection

---

## Three layers

1. **Event store** — Appends events to an `events` table (SQLite). Each row is one event (event_id, event_type, payload JSON, etc.).
2. **Projection** — When an event is appended, a **handler** runs and updates the read model. For example, `ClaimProposed` → insert or update a row in the `claim` table; `SupportLinked` → insert a row in `evidence_link`. Handlers live in **`chronicle/store/read_model/projection.py`** (e.g. `handle_claim_proposed`, `handle_support_linked`).
3. **Read model** — SQLite tables: `investigation`, `claim`, `evidence_item`, `evidence_span`, `evidence_link`, `tension`, etc. Queries (get claim, list supports, get defensibility) read from these tables, not from the raw event stream.

So: **write path** = session method → command → append event → run projection. **Read path** = session/read_model query → read from tables.

## Session API

Open **`chronicle/store/session.py`**.

- **ChronicleSession** is the main API. You construct it with a **project directory** (must already contain `chronicle.db`; create it with `chronicle init` or `create_project` from code).
- **create_investigation(title, ...)** — Appends `InvestigationCreated`; returns `(event_id, investigation_uid)`.
- **ingest_evidence(inv_uid, content_bytes, media_type, ...)** — Writes the blob to the evidence store, appends `EvidenceIngested`; returns `(event_id, evidence_uid)`.
- **anchor_span(inv_uid, evidence_uid, anchor_type, anchor_value, quote=...)** — Appends `SpanAnchored`; returns `(event_id, span_uid)`.
- **propose_claim(inv_uid, claim_text, ...)** — Appends `ClaimProposed`; returns `(event_id, claim_uid)`. Optional **epistemic_stance** (e.g. working_hypothesis, asserted_established).
- **link_support(inv_uid, span_uid, claim_uid, rationale=..., strength=...)** — Appends `SupportLinked`. Optional **rationale** (warrant: why this evidence supports this claim). Same pattern for **link_challenge** (optional rationale, **defeater_kind** e.g. rebutting/undercutting) and **declare_tension** (optional **defeater_kind**). **register_source** accepts optional **reliability_notes** (user-supplied; we record, we don't verify).
- **get_defensibility_score(claim_uid)** — Reads from the read model (via the claims command) and returns a **DefensibilityScorecard**. We’ll see how that’s computed in Lesson 06.

The session also supports **tension suggestions** (emit_tension_suggestions, dismiss_tension_suggestion) and **tier** (set_tier, tier history) for the Reference UI and workspace gating; see Lesson 11 and [docs/api.md](../docs/api.md).

The **scorer** (Lesson 02) does exactly this: create project → open session → create investigation → for each evidence chunk: ingest_evidence, anchor_span → propose_claim (answer) → link_support for each span → get_defensibility_score → serialize to JSON.

## Projection in one example

Open **`chronicle/store/read_model/projection.py`**.

- **EVENT_HANDLERS** — A registry mapping event_type string → function(conn, event). When an event is appended, the store looks up the handler and calls it with the DB connection and the event.
- **handle_claim_proposed** — Inserts or updates the `claim` table with claim_uid, investigation_uid, claim_text, status, etc., from the event payload.
- **handle_support_linked** — Inserts into `evidence_link` (span_uid, claim_uid, link_type=SUPPORT). So after the event is stored, the read model immediately reflects the new link.

You don’t need to read every handler; the point is: **one event type → one (or more) table updates**. The read model is always a function of the event log.

## Try it

1. Read **session.py** in the **ingest_evidence** and **propose_claim** methods (around lines 190–250). See how they call the command and return the UIDs.
2. In **projection.py**, find **handle_evidence_ingested** and **handle_support_linked**. See what tables they write to.

## Summary

- **Event store** appends events; **projection** updates the read model (investigation, claim, evidence_item, evidence_span, evidence_link, tension).
- **ChronicleSession** is the main API: create_investigation, ingest_evidence, anchor_span, propose_claim, link_support, get_defensibility_score, plus tension suggestions, tier, and more.
- The scorer is a thin script over the session; all real work is in the store and commands.

**← Previous:** [Lesson 04: Events and core](04-events-and-core.md) | **Index:** [Lessons](README.md) | **Next →:** [Lesson 06: Defensibility metrics](06-defensibility-metrics.md)

**Quiz:** [quizzes/quiz-05-store-and-session.md](quizzes/quiz-05-store-and-session.md)
