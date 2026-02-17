# Standalone .chronicle verifier (Phase 8)

Validates a `.chronicle` export file (ZIP) **without requiring chronicle-standard**. Recipients can run this to verify manifest, schema, and evidence hashes themselves.

## Requirements

- Python 3.10+ (stdlib only: `zipfile`, `json`, `sqlite3`, `hashlib`, `tempfile`)

## Usage

From the repository root (with or without installing the package):

```bash
PYTHONPATH=. python3 -m tools.verify_chronicle path/to/file.chronicle
```

Or after `pip install -e .`, use the entry point: `chronicle-verify path/to/file.chronicle`.

Options:

- `--no-invariants` — Skip append-only ledger check (faster; still checks manifest, schema, evidence hashes).

## What it checks

1. **ZIP** — File is a valid ZIP containing `manifest.json` and `chronicle.db`.
2. **Manifest** — Required keys: `format_version`, `investigation_uid`; `format_version` ≥ 1.
3. **Schema** — `schema_version` table and required tables exist (`events`, `investigation`, `claim`, `evidence_item`, etc.).
4. **Evidence hashes** — For each row in `evidence_item`, the file at `uri` inside the ZIP is read and its SHA-256 is compared to `content_hash`.
5. **Append-only ledger** (optional) — Events are ordered by `recorded_at` with no reversals.

## Exit codes

- `0` — All checks passed.
- `1` — One or more checks failed.
- `2` — Usage error (missing path).

## Integration with chronicle-standard CLI

When the project is installed with `pip install -e .`, the **`chronicle-verify`** command is available (see `pyproject.toml`). You can also run the module directly as above. The verifier does not import the `chronicle` package.
