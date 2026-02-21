# Quiz 02: The standalone defensibility scorer

Lesson: [02-the-scorer.md](../02-the-scorer.md)

Answer after reading the lesson and running the scorer at least once.

---

## Questions

1. What three fields must the scorer’s input JSON contain? What type is each?

2. If the user sends valid JSON but `evidence` is an empty array, what does the scorer return? (Describe the shape: key(s) and intent.)

3. In one sentence: what does `_normalize_evidence(evidence)` do?

4. What does the scorer use a temporary project for? (Why not a real project on disk?)

5. The scorer prints exactly one JSON object to stdout. What are the two possible kinds of that object (success vs failure)?

6. Does the default scorer validate that each evidence chunk actually supports the claim? What should you do for higher assurance?

---

## Answer key

1. `query` (string), `answer` (string), `evidence` (array). Evidence items can be strings or objects with `text`, `path` (file), or `url` (fetched with SSRF safeguards).

2. It returns an error object, e.g. `{"contract_version": "1.0", "error": "invalid_input", "message": "evidence must contain at least one non-empty text chunk..."}`. So: an object with `contract_version`, an `error` key (and usually a `message` key).

3. It turns the raw `evidence` list into a list of text strings: keep non-empty strings; for objects use `text` if present, read from `path` if it’s a file path, or fetch from `url` (with SSRF safeguards); skip invalid or empty items.

4. The temp project gives the scorer an isolated environment for one run: ingest evidence, propose the claim, link support, compute defensibility, then discard. No need for a real project path or cleanup; one run = one temp dir.

5. Success: a single JSON object with `contract_version: "1.0"` and defensibility metrics (e.g. `claim_uid`, `provenance_quality`, `corroboration`, `contradiction_status`, …). Failure: a single JSON object with `contract_version`, at least `error` (e.g. `invalid_input`), and usually `message`.

6. No. The default scorer links *every* evidence chunk as support without validating that evidence actually supports the claim. For higher assurance, validate or curate links (e.g. human or NLI) and then record them via the session or API; see the caveat in the eval contract and lesson.

---

← Previous: [quiz-01-codebase-map](quiz-01-codebase-map.md) | Index: [Quizzes](README.md) | Next →: [quiz-03-the-verifier](quiz-03-the-verifier.md)
