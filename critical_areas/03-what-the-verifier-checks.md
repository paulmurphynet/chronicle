# Critical area 03: What the verifier does and does not check

**Risk:** Assuming that a **“verified”** .chronicle file means the *content* is correct, trustworthy, or that claims are true or well-supported in reality. “Verified” has a narrow, technical meaning.

---

## Narrative

The verifier exists so that recipients can **“verify it yourself”** without running the full Chronicle stack. It checks that the .chronicle package (ZIP) is **structurally valid**: manifest present and valid, database schema and required tables present, evidence file hashes consistent. So you can be confident that the package was produced by a compliant implementation and wasn’t corrupted or tampered with in a way that breaks the structure or hashes.

The verifier does **not** check:

- Whether any **claim is true** or factually correct.
- Whether **sources are independent** in the real world.
- Whether **support/challenge links** are correct (e.g. that the evidence actually supports or challenges the claim).
- Whether **events are semantically consistent** (e.g. that event payloads refer to prior events that existed, or that UIDs in events refer to existing entities).
- **Referential integrity** (e.g. that every SupportLinked references an existing claim and span). The Chronicle runtime enforces that when writing; the standalone verifier does not re-check it on the exported package.
- Whether **actor identity** is correct (who performed an action); see [06 — Actor identity is not verified](06-actor-identity-is-not-verified.md).

Optionally, with the default options, the verifier also checks that the **events** table has non-decreasing `recorded_at` (append-only ledger). That is still structural—it does not validate event meaning or referential integrity.

So “verified” means: **integrity, schema, and hashes** (and optionally append-only events). It does **not** mean: content is correct, reliable, or epistemically sound. Over-relying on “verified” as a content guarantee is a critical risk.

---

## Technical

- **Implementation:** `tools/verify_chronicle/verify_chronicle.py`. Functions include `verify_manifest()` (required keys, format_version), `verify_db_schema()` (schema_version, required tables such as events, investigation, claim, evidence_item), and evidence-hash checks. By default, the verifier also checks append-only ordering of `events` (non-decreasing `recorded_at`). No code path validates claim truth, source independence, link semantics, referential integrity, or actor identity.
- **User-facing doc:** `docs/verifier.md` states that the verifier checks “structurally valid (ZIP, manifest, database schema, evidence file hashes)” and does *not* check “event semantics, independence of sources, truth of claims,” and points to [verification guarantees](../docs/verification-guarantees.md). For a full list of what is and is not guaranteed, see [Verification guarantees](../docs/verification-guarantees.md) (Sections 1–2).

---

## What to remember

- **Verified = structural integrity and evidence hashes, not content correctness.** Use verification to trust that the package is well-formed and unaltered; do not use it to infer that claims are true or that evidence actually supports them.
- When sharing or receiving a .chronicle, communicate clearly: “Verified means the package structure and hashes check out; it does not mean we’ve validated the truth or the support relationships of the claims inside.”
---

**← [Critical areas index](README.md)** | **Next →:** [04 — Evidence–claim linking](04-evidence-claim-linking.md)