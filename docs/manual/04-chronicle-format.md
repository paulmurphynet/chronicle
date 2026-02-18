# Chapter 04: .chronicle format

**Contents:** What's inside a .chronicle (ZIP); manifest, DB, evidence.

---

## Top-level layout

A **.chronicle** file is a **ZIP** containing:

- **manifest.json** — Format version, investigation UID, title, exported_at, optional content_hash_manifest.
- **chronicle.db** — SQLite: event store (append-only events) and read model (investigation, claim, evidence_item, evidence_span, evidence_link, tension, etc.).
- **evidence/** — One file per evidence item; paths from `evidence_item.uri`. Raw content only; structure lives in the DB.

---

## Produce and consume

- **Produce:** Build a ZIP with manifest, DB, and evidence files; run the verifier to self-check. See [Chronicle file format](../chronicle-file-format.md) and [Implementer checklist](../implementer-checklist.md).
- **Consume:** Run `chronicle-verify`; then open the ZIP, read manifest and SQLite, resolve evidence by URI. See [Consuming .chronicle](../consuming-chronicle.md).

---

**← Previous:** [03 — Verifier](03-verifier.md) | **Index:** [Manual](README.md) | **Next →:** [05 — Integration](05-integration.md)
