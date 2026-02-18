# Troubleshooting

Common issues when running Chronicle for the first time or in a new environment.

---

## `chronicle: command not found` or `chronicle-verify: command not found`

**Cause:** The project isn’t installed in the current environment, or the virtual environment isn’t activated.

**Fix:**

1. Activate the project’s venv, then run the command again:
   ```bash
   source .venv/bin/activate   # Linux/macOS
   chronicle neo4j-sync --path .
   chronicle-verify path/to/file.chronicle
   ```
2. Or run without activating by using the venv’s binaries:
   ```bash
   ./.venv/bin/chronicle neo4j-sync --path .
   ./.venv/bin/chronicle-verify path/to/file.chronicle
   ```
3. Or run the verifier as a module (no install):
   ```bash
   PYTHONPATH=. python3 -m tools.verify_chronicle path/to/file.chronicle
   ```

---

## `NEO4J_URI is not set`

**Cause:** You’re running `chronicle neo4j-sync` but Neo4j credentials aren’t in the environment.

**Fix:**

- Create a `.env` file in the repo root (see [Aura graph pipeline](aura-graph-pipeline.md)) with:
  - `NEO4J_URI` (e.g. `neo4j+s://xxxx.databases.neo4j.io`)
  - `NEO4J_PASSWORD`
  - Optionally `NEO4J_USER` (default `neo4j`)
- Or export them in the shell before running: `export NEO4J_URI=... NEO4J_PASSWORD=...`
- Use **no spaces around `=`** in `.env`; quote values that contain `#` or spaces.

---

## Scorer: invalid JSON or "missing query/answer/evidence"

**Cause:** The scorer expects a single JSON object on stdin with `query`, `answer`, and `evidence` (array of strings or objects with `text`).

**Fix:**

- Send valid JSON, e.g.:
  ```bash
  echo '{"query": "What was revenue?", "answer": "Revenue was $1.2M.", "evidence": ["The company reported revenue of $1.2M in Q1 2024."]}' \
    | PYTHONPATH=. python3 scripts/standalone_defensibility_scorer.py
  ```
- On Windows, use a file or a JSON-friendly shell so quotes and escaping are correct. See [Eval contract](eval_contract.md).

---

## Verifier: "Not a .chronicle" or "missing manifest.json"

**Cause:** The file isn’t a valid .chronicle (ZIP with `manifest.json` and `chronicle.db` inside).

**Fix:**

- Use a file produced by Chronicle (e.g. export from a project or from `scripts/generate_sample_chronicle.py`). See [Chronicle file format](chronicle-file-format.md) and [Verifier](verifier.md).

---

## `ModuleNotFoundError: No module named 'chronicle'` when running a script

**Cause:** The script imports `chronicle` or `tools` but the repo root isn’t on `PYTHONPATH`.

**Fix:**

- Run from the repo root with `PYTHONPATH=.`:
  ```bash
  PYTHONPATH=. python3 scripts/ingest_transcript_csv.py ...
  ```
- Or install the project first: `pip install -e .` and run the script with the same Python that has the package.

---

## CLI shows "Error: ..." and exits with code 1

**Cause:** The command hit a user-fixable condition (e.g. not a Chronicle project, investigation not found, validation failure). The CLI prints the message and exits 1 without a traceback.

**Fix:**

- Read the message (e.g. "Not a Chronicle project (no chronicle.db): ..." → run from a project dir or run `chronicle init` first). For the full list of error types and how they are used, see [Errors](errors.md).

---

## Python version errors

**Cause:** Chronicle requires Python 3.11+.

**Fix:**

- Use Python 3.11 or newer: `python3 --version`. Create the venv with that interpreter: `python3.11 -m venv .venv` (or your 3.11+ path).
