# Lesson 03: The .chronicle verifier

Objectives: You’ll know what a .chronicle file is, what the verifier checks, and where the verification code lives. You’ll have run the verifier.

**Key files:**

- [tools/verify_chronicle/verify_chronicle.py](../tools/verify_chronicle/verify_chronicle.py) — verifier implementation  
- [docs/verifier.md](../docs/verifier.md) — user-facing verifier doc  
- [docs/verification-guarantees.md](../docs/verification-guarantees.md) — what the verifier guarantees and does not; runtime invariants and audit  

---

## What the verifier does

A .chronicle file is a portable package (ZIP) of an investigation: manifest, schema, SQLite DB (events/read model), and evidence. The verifier checks that the package is well-formed and consistent—e.g. manifest has required keys, DB has the right tables, evidence hashes match. For a complete description of the file format and data schema (manifest keys, DB tables, evidence layout), see [Lesson 12: The .chronicle file format and data schema](12-chronicle-file-format-and-schema.md). It uses only the Python stdlib (zipfile, json, sqlite3, hashlib) so anyone can verify without installing the Chronicle package. “Verify it yourself” is a design goal.

## What gets checked

Open `tools/verify_chronicle/verify_chronicle.py`.

- Manifest (e.g. `verify_manifest`): required keys like `format_version`, `investigation_uid`; format_version must be an integer ≥ 1.
- DB schema (`verify_db_schema`): `schema_version` table and required tables (`events`, `schema_version`, `investigation`, `claim`, `evidence_item`).
- **Evidence integrity**: hashes of files in the package are checked so we can detect tampering or corruption.

The script returns a pass/fail (and details) so callers know whether the .chronicle is valid.

## How to run it

After `pip install -e .`, the CLI is:

```bash
chronicle-verify path/to/file.chronicle
```

You can also run the module directly: `python3 -m tools.verify_chronicle path/to/file.chronicle`. The entry point is in pyproject.toml (`chronicle-verify = "tools.verify_chronicle.verify_chronicle:main"`); the logic lives in `verify_chronicle.py`.

## Try it

If you have a sample .chronicle (e.g. from `scripts/generate_sample_chronicle.py`), run:

```bash
chronicle-verify path/to/sample.chronicle
```

If you don’t have one, generate it first (see [docs/verifier.md](../docs/verifier.md) or the scripts README). Read the verifier’s output: it should report pass/fail for manifest, schema, and evidence.

## Summary

- .chronicle = ZIP with manifest, schema, DB, evidence.  
- Verifier = stdlib-only checks: manifest, DB schema, evidence hashes.  
- Code: `tools/verify_chronicle/verify_chronicle.py`; CLI: `chronicle-verify`. For the full list of guarantees and what the verifier does *not* check (e.g. event semantics, truth of claims), see [docs/verification-guarantees.md](../docs/verification-guarantees.md).

← Previous: [Lesson 02: The scorer](02-the-scorer.md) | Index: [Lessons](README.md) | Next →: [Lesson 04: Events and core](04-events-and-core.md)

Quiz: [quizzes/quiz-03-the-verifier.md](quizzes/quiz-03-the-verifier.md)
