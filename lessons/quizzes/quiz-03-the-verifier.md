# Quiz 03: The .chronicle verifier

**Lesson:** [03-the-verifier.md](../03-the-verifier.md)

---

## Questions

1. What is a **.chronicle** file (format and contents)?

2. Why does the verifier use **only the Python stdlib**?

3. Name **two** things the verifier checks (e.g. manifest, schema, evidence).

4. How do you run the verifier from the command line (after installing the package)?

5. Where is the verifier implementation located in the repo?

---

## Answer key

1. A **.chronicle** file is a **ZIP package** containing: a **manifest** (e.g. format_version, investigation_uid), **schema** info, a **SQLite DB** (events and read model), and **evidence** (files). It’s the portable format for an investigation.

2. So that **anyone can verify** without installing the Chronicle package—recipients can “verify it yourself” with just Python. No dependency on our full stack.

3. **Manifest** (required keys, format_version); **DB schema** (schema_version, required tables); **evidence integrity** (hashes). (Any two of these is fine.)

4. **`chronicle-verify path/to/file.chronicle`** (after `pip install -e .`).

5. **`tools/verify_chronicle/verify_chronicle.py`** (and the package entry point that calls it).

---

**← Previous:** [quiz-02-the-scorer](quiz-02-the-scorer.md) | **Index:** [Quizzes](README.md) | **Next →:** [quiz-04-events-and-core](quiz-04-events-and-core.md)
