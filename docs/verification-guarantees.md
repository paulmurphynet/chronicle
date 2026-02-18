# Verification guarantees and invariants

One place for implementers and auditors to see what "verified" means and what is out of scope. The **standalone verifier** (CLI `chronicle-verify` or web) checks a `.chronicle` file (ZIP). The **Chronicle runtime** (this project: event store + read model) maintains stronger invariants on a live project. This doc states both.

**Companion:** [Verifier](verifier.md) (how to run), [Conformance](conformance.md), [Chronicle file format](chronicle-file-format.md).

---

## 1. What the standalone verifier guarantees

When you run `chronicle-verify path/to/file.chronicle` (or the web verifier) and it exits 0, the following are **guaranteed**:

| Check | Guarantee |
|-------|-----------|
| **ZIP** | The file is a valid ZIP archive containing `manifest.json` and `chronicle.db`. |
| **Manifest** | Required keys `format_version` and `investigation_uid` are present. `format_version` is an integer ≥ 1. |
| **Schema** | The database has a `schema_version` table with at least one row for component `event_store` or `read_model`. The required tables exist: `events`, `schema_version`, `investigation`, `claim`, `evidence_item`. |
| **Evidence hashes** | For every row in `evidence_item`, the ZIP contains a member at the path given by `uri`; the path is not absolute and does not contain `..` (path traversal is rejected); the SHA-256 hash (hex) of the file content equals `content_hash`. |
| **Append-only ledger** (optional) | If you do **not** use `--no-invariants`, the verifier also checks that the `events` table, when ordered by insertion order (`rowid`), has non-decreasing `recorded_at` values (no timestamp reversals). |

If all checks pass, the package is **structurally valid**: you can trust that the manifest and DB are present, the schema is as expected, and the evidence files match the recorded hashes. A conformant .chronicle is one that passes all of the above (see [conformance.md](conformance.md)).

---

## 2. What the standalone verifier does NOT verify

The verifier is **structural and integrity-only**. It does **not** verify:

- **Semantics of events.** It does not check that event payloads are meaningful or consistent with each other (e.g. that a `SupportRetracted` or `ChallengeRetracted` event refers to a prior link that existed, or that UIDs in events refer to existing entities in the read model). A .chronicle could pass the verifier and still contain logically inconsistent or malformed events.
- **Referential integrity.** Referential integrity (e.g. every `SupportLinked` references an existing claim and span) is enforced by the Chronicle runtime when writing events; the standalone verifier does not re-check it on the exported DB. The full invariant suite (Section 3) does.
- **Independence of sources.** "Distinct sources" in the read model are as recorded by the producer. The verifier does not and cannot verify that two source entities represent actually independent real-world actors.
- **Truth of claims.** The verifier does not assess whether any claim is true, well-supported, or defensible. It only checks that the package is well-formed and that evidence file content matches recorded hashes.
- **Correctness of the read model.** The verifier does not verify that the read model (claim, evidence_item, etc.) was correctly derived from the event stream. It only checks that required tables exist.
- **Policy or defensibility rules** — It does not evaluate defensibility scores or policy thresholds.
- **Reasoning briefs or submission packages** — It validates only `.chronicle` (ZIP) files, not HTML briefs or other export formats.

**Summary:** "Verified" means **the package is structurally valid and evidence files match their hashes**. It does not mean "the events are semantically consistent" or "the claims are true" or "sources are independent."

For the epistemological and practical limits of defensibility and verification, see [Critical areas](../critical_areas/README.md) and [Defensibility is not truth](../critical_areas/01-defensibility-is-not-truth.md).

---

## 3. System invariants (Chronicle runtime)

When running Chronicle on a project (event store + read model), the system maintains the following. These are **not** all checked by the standalone .chronicle verifier; they are enforced by the runtime and by the **invariant verification suite** (`chronicle verify --path /project`).

**Non-negotiable invariants:**

- **Events are append-only.** No deletion or rewriting of events.
- **Projections are disposable.** The read model can be rebuilt from the event stream.
- **Claims are not truth.** The system does not store "truth"; it stores evidence, claims, links, and tensions and computes defensibility.
- **Contradictions are explicit.** Tensions are first-class and recorded.
- **Corrections do not erase history.** Retractions and supersessions add events; they do not remove prior events.
- **Rebuilds are normal.** Truncating and rebuilding the read model from the event stream is a supported operation and produces the same state as incremental projection.

**Invariant verification suite:** The `chronicle verify --path /project` command (and the test suite) checks, on a **project database**, append-only ledger, referential integrity (events reference existing UIDs), status consistency, projection completeness, checkpoint consistency, and evidence integrity on disk. The **standalone .chronicle verifier** does not run this full suite; it only checks what is listed in Section 1 above (and optionally append-only on the exported events table).

**As-of consistency:** Queries (e.g. defensibility as of a date or event) are defined over the event stream and read model; the system guarantees that as-of results are consistent with replaying events up to that point. The standalone verifier does not evaluate as-of semantics.

---

## 4. What the system does NOT guarantee

Neither the verifier nor the Chronicle runtime guarantees:

- **That any claim is true.** Defensibility is computed from recorded support, challenge, and policy; it is not a proof of truth.
- **That sources are independent.** Distinct sources are as you have modeled them; not independently verified.
- **That actors are who they claim to be.** Actor identity in events is as asserted by the writer; binding to authenticated identities is a deployment concern.
- **That the reasoning brief or defensibility score is complete.** They reflect the current state of the ledger and read model; they do not include information that was never recorded.

---

## 5. Replay and audit

**Replay semantics:** The read model is **derived** from the event log. **Full replay from event zero** is the normative semantics: given the same event stream, the read model is deterministic. The runtime supports truncating the read model and rebuilding it from the event stream (see Section 3, "Rebuilds are normal").

**Audit today:**

- **Project database:** Run `chronicle verify --path /project` to execute the full invariant suite (append-only ledger, referential integrity, status consistency, projection completeness, checkpoint consistency, evidence integrity on disk). The project is audited as a whole. Event history is available via the CLI for inspection; for a formal replay-from-N or time-range replay, that is a possible future extension.
- **.chronicle file:** Run the standalone verifier (CLI or web) as in Section 1. The verifier checks the exported snapshot (structure, hashes, optional append-only); it does not run the full invariant suite.

**Future (scale):** For very large projects, **checkpointing or snapshots** (e.g. snapshot of read model at event N plus tail events) may be added to speed up replay or recovery. When we add checkpointing, the verification story will be: **verify snapshot integrity and tail events, or verify full replay**; this doc will be updated accordingly. Today there is no snapshot path, only full replay.

---

## 6. Summary table

| Question | Answer |
|----------|--------|
| What does "verifier passed" mean for a .chronicle? | ZIP valid; manifest and schema present and valid; evidence files in ZIP match content_hash; optional: events table append-only. |
| Does the verifier check that events make sense? | No. Only structure and hashes. |
| Does the verifier check that claims are true or sources independent? | No. |
| What guarantees does the Chronicle runtime give? | Append-only events; projections derivable from events; no silent deletion; as-of consistency; see Section 3. |
| Where do I run the full invariant suite? | On a project: `chronicle verify --path /project`. Not on a .chronicle file. |

---

## Conformance

A `.chronicle` file is **conformant** if the verifier exits 0. Producers should generate packages that pass the verifier; consumers can rely on the guarantees above when verification passes. For the verifier CLI and options, see [Verifier](verifier.md).
