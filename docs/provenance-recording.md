# Provenance recording in Chronicle

Chronicle can **store** source and evidence–source links. Provenance-aware pipelines (e.g. C2PA, CR, or custom attribution) can feed us assertions and we treat them as **your modeling of provenance**—we record, we do not independently verify the assertions.

---

## What we store

- **Sources** — You can register a source (e.g. “Reuters”, “Model: gpt-4”, “Sensor XYZ”) per investigation. Sources have a type, optional alias, and optional independence notes.
- **Evidence–source links** — You can link an evidence item to a source (“this evidence was provided by this source”). We store the relationship; we do not verify that the evidence actually came from that source.
- **Evidence metadata** — At ingest time you can pass `metadata` (e.g. `provenance_type`, or custom keys like `c2pa_claim_id`). See [External IDs](external-ids.md).

So: **we record provenance assertions you give us.** We do not verify C2PA signatures, CR chains, or that a blob “really” came from a given source. That keeps Chronicle’s scope clear: structural defensibility (support/challenge, tensions, policy rules) plus your chosen provenance layer on top.

---

## Feeding C2PA / CR / custom assertions

If your pipeline produces **provenance assertions** (e.g. “this blob from this source/model”, “this claim from this C2PA assertion”):

1. **Evidence** — When you ingest evidence, pass `metadata` (and optionally `provenance_type`: e.g. `human_created` | `ai_generated` | `unknown`). You can store C2PA claim IDs or CR references in metadata so downstream tools can correlate.
2. **Source** — Register a source with `session.register_source(...)` and then link evidence to it with `session.link_evidence_to_source(inv_uid, evidence_uid, source_uid, ...)`.
3. **Claim** — Today we don’t have a dedicated “provenance assertion ID” on claims; use evidence–source links and evidence metadata to tie claims to your provenance model. See [External IDs](external-ids.md) for storing external IDs in evidence or claim notes/tags.

An **adapter** that reads C2PA/CR output and calls Chronicle’s session (register_source, ingest_evidence with metadata, link_evidence_to_source) is the intended way to “land” provenance results in Chronicle. We do not verify the assertions; we persist them so that defensibility and reasoning trails can reference your provenance model.

For a starter C2PA ingestion path, see `scripts/adapters/c2pa_to_chronicle.py` and [C2PA compatibility export](c2pa-compatibility-export.md).

---

## Summary

| Question | Answer |
|----------|--------|
| Can Chronicle store source and evidence–source links? | Yes. Register sources; link evidence to sources. |
| Do we verify C2PA/CR or that evidence “really” came from a source? | No. We record what you tell us. |
| Can I feed C2PA/CR assertions into Chronicle? | Yes—via an adapter that maps assertions to our sources and evidence–source links (and evidence metadata). |
| Where is this documented in code? | `register_source`, `link_evidence_to_source`, evidence `metadata` / `provenance_type` in the session and read model. |

Provenance-aware pipelines can land results in Chronicle and use defensibility (support, challenge, tensions) alongside that recorded provenance.
