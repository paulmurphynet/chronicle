# Verification guarantees and invariants

The **standalone verifier** (CLI `chronicle-verify` or web) checks structural integrity of a `.chronicle` file (ZIP). This doc states what is **guaranteed** and what is **not** checked.

---

## What the verifier guarantees

| Check | Guarantee |
|-------|-----------|
| **ZIP** | The file is a valid ZIP containing `manifest.json` and `chronicle.db`. |
| **Manifest** | Required keys are present (`format_version`, `investigation_uid`); `format_version` is an integer ≥ 1. |
| **Schema** | The SQLite DB has `schema_version` and the required tables (e.g. `events`, `investigation`, `claim`, `evidence_item`). |
| **Evidence hashes** | For each row in `evidence_item`, the file at `uri` inside the ZIP exists and its SHA-256 content hash equals `content_hash` in the DB. Paths are validated (no traversal outside the ZIP). |
| **Append-only ledger** (optional) | When not using `--no-invariants`, events are ordered by `recorded_at` with no reversals. |

If all checks pass, the verifier exits 0 and the package is **structurally valid**: you can trust that the manifest and DB are present, the schema is as expected, and the evidence files match the recorded hashes.

---

## What the verifier does not check

- **Truth of claims** — The verifier does not validate that any claim is factually true.
- **Semantics of events** — It does not validate that events are logically consistent (e.g. that a support link references an existing span).
- **Source independence** — It does not check whether sources are independent in the real world; independence is as modeled by the producer.
- **Policy or defensibility rules** — It does not evaluate defensibility scores or policy thresholds.
- **Reasoning briefs or submission packages** — It validates only `.chronicle` (ZIP) files, not HTML briefs or other export formats.

For the epistemological and practical limits of defensibility and verification, see [Critical areas](../critical_areas/README.md) and [Defensibility is not truth](../critical_areas/01-defensibility-is-not-truth.md).

---

## Conformance

A `.chronicle` file is **conformant** if the verifier exits 0. Producers should generate packages that pass the verifier; consumers can rely on the guarantees above when verification passes. For the verifier CLI and options, see [Verifier](verifier.md).
