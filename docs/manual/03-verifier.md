# Chapter 03: Verifier

**Contents:** Verify a .chronicle file; what is and is not guaranteed.

---

## Run the verifier

```bash
chronicle-verify path/to/file.chronicle
```

Exit 0 = the package is structurally valid (manifest, schema, evidence hashes). Stdlib only; no Chronicle package needed for verification.

---

## What the verifier checks

- **Manifest** — Required keys (`format_version`, `investigation_uid`).
- **Schema** — Required tables in the SQLite DB.
- **Evidence hashes** — Each evidence file in the ZIP matches its recorded content hash.

---

## What it does not check

The verifier does **not** check that claims are true, that sources are independent, or that evidence actually supports the claim. See [Verification guarantees](../verification-guarantees.md) and [Critical areas](../../critical_areas/README.md).

---

**← Previous:** [02 — Scorer](02-scorer.md) | **Index:** [Manual](README.md) | **Next →:** [04 — .chronicle format](04-chronicle-format.md)
