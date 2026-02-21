# Quiz 12: The .chronicle file format and data schema

Lesson: [12-chronicle-file-format-and-schema.md](../12-chronicle-file-format-and-schema.md)

Answer these after reading the lesson and the chronicle-file-format doc and schema. Try not to peek at the answer key until you've written your answers.

---

## Questions

1. What are the three top-level contents of a .chronicle ZIP, and what is each used for?

2. Where is the structure (which evidence supports which claim, which claims are in tension) stored—in the evidence files or in the database? Explain in one sentence.

3. Which manifest keys are required (verifier rejects if missing)?

4. Name four read-model tables in chronicle.db and what they represent (one phrase each).

5. Where is the DDL for the events table and read-model tables defined in the repo?

6. What does the verifier check about evidence files (path and content)?

---

## Answer key

1. **manifest.json** — metadata and integrity (format_version, investigation_uid, title, exported_at, optional content_hash_manifest). chronicle.db — SQLite with event store (append-only events) and read model (investigation, claim, evidence_item, evidence_span, evidence_link, tension, etc.). evidence/ — one file per evidence item; paths from evidence_item.uri; content is raw blobs.

2. The structure is stored in the database (chronicle.db). Evidence files are raw content only; support/challenge links and tensions are in the evidence_link and tension tables.

3. format_version (integer ≥ 1) and investigation_uid.

4. Examples: investigation — one row per investigation; claim — one row per claim (claim_text, status, …); evidence_item — one row per evidence (uri, content_hash, …); evidence_span — spans within evidence; evidence_link — span-to-claim links (SUPPORT/CHALLENGE); tension — links between two claims (claim_a_uid, claim_b_uid, status). (Any four with correct role is fine.)

5. **chronicle/store/schema.py** — EVENTS_DDL, READ_MODEL_DDL, CLAIM_DDL, EVIDENCE_SPAN_DDL, EVIDENCE_LINK_DDL, TENSION_DDL, etc. (schema.sql mirrors the event store DDL.)

6. The verifier checks that each evidence file exists at the path given by evidence_item.uri (relative, no `..`), and that the SHA-256 hash of the file content equals the content_hash in the DB (or manifest). Path traversal is rejected; mismatch fails verification.

---

← Previous: [quiz-11-interoperability-api-and-tests](quiz-11-interoperability-api-and-tests.md) | Index: [Quizzes](README.md) | Next →: [quiz-13-release-readiness-security-and-standards](quiz-13-release-readiness-security-and-standards.md)
