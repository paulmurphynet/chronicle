# Standalone .chronicle verifier (Phase 8)

The **standalone verifier** validates a `.chronicle` export file (ZIP) so that recipients can confirm integrity and schema **without installing or running chronicle-standard**. Use it to "verify it yourself" when sharing or receiving a `.chronicle` bundle.

---

## If you receive a .chronicle file

**What it is:** A `.chronicle` file is a ZIP package of an investigation (database, evidence files, and a manifest) that you can verify without running the full Chronicle app.

**Recipient obligation:** Before relying on a submission, run the verifier on the .chronicle file (CLI or web below) to confirm structural integrity and evidence hashes.

**How to verify:**

1. **CLI (one command):** Run:
   ```bash
   chronicle-verify path/to/file.chronicle
   ```
   If you don't have Chronicle installed, from the chronicle-standard repo root you can run:
   ```bash
   python3 -m tools.verify_chronicle path/to/file.chronicle
   ```
   (Uses only Python's standard library; no install required.)
2. **Web verifier:** If the sender gave you a link (e.g. a deployed verifier page), open it in your browser and drag-and-drop the file. No install; the file is read locally and never uploaded. When the Chronicle API is running locally, the verifier is at http://localhost:8000/verifier.

**What "verified" means:** The verifier checks that the package is structurally valid (ZIP, manifest, database schema, evidence file hashes). It does *not* check that events are semantically consistent, that sources are independent, or that claims are true. For the full list of guarantees and limits, see [Verification guarantees and invariants](verification-guarantees.md). For a one-page note suitable for the court, see [Chronicle: judicial note (for the court)](legal-judicial-note.md).

**Where to get the CLI:** Install the package (`pip install chronicle-standard` when available on PyPI, or from the repo with `pip install -e .`) to get the `chronicle-verify` command. Or use the repo run above without installing.

### If you receive a submission package (ZIP)

A **submission package** is a ZIP that contains `investigation.chronicle`, a `reasoning_briefs/` folder (HTML per claim), `citations.bib`, `citations.json`, and optionally `chain-of-custody.html`. It is produced from the Publication page ("Export submission package") or via `GET /investigations/{id}/submission-package`.

**What to do:** Extract the ZIP. Then (1) **verify** the file `investigation.chronicle` as above (CLI or web verifier). (2) **Read** the reasoning briefs by opening the HTML files in `reasoning_briefs/` in your browser. (3) Use `citations.bib` or `citations.json` in your editing or fact-check workflow. See [Journal submission package](journal-submission-package.md) Section 4 (What the recipient does) for the full recipient workflow.

---

## No chronicle-standard required

The verifier uses only the Python standard library (`zipfile`, `json`, `sqlite3`, `hashlib`, `tempfile`). You do **not** need to install the chronicle-standard package or have a project directory.

## How to run

### Option 1: From repository root (no install)

```bash
python3 -m tools.verify_chronicle path/to/file.chronicle
```

Use `python` instead of `python3` if that is the command on your system.

### Option 2: After installing chronicle-standard

```bash
chronicle verify-chronicle path/to/file.chronicle
# or the dedicated entry point:
chronicle-verify path/to/file.chronicle
```

### Option 3: Static web verifier (E4)

A **drag-and-drop verifier** runs entirely in your browser. No install and no data is uploaded — the file is read locally and checked with JavaScript (JSZip, sql.js, Web Crypto API).

- **When the API is running:** Open **http://localhost:8000/verifier** (or your API base URL + `/verifier`). Drop a `.chronicle` file or click to choose one. The page runs the same checks (manifest, schema, evidence hashes, append-only ledger) and shows PASS/FAIL per check.
- **Static file:** The page is at `chronicle/api/static/verifier.html`. You can serve it from any static server (e.g. `python -m http.server` in that directory) or open the file directly in a browser; for CDN-loaded scripts to work, opening via an HTTP URL (e.g. the API's `/verifier` route) is more reliable than `file://`.

Use this when you want to verify a bundle without installing Python or chronicle-standard.

### Options (CLI only)

- **`--no-invariants`** — Skip the append-only ledger check. Use for a quicker run; manifest, schema, and evidence hashes are still checked.
- **`--summary`** — When verification passes, print a short **"What's inside"** summary (investigation UID, title, claim count, evidence count) so non-technical recipients can see what the package contains without opening the DB.
- **`--json`** — Output a single JSON object instead of human-readable lines: `{"verified": true|false, "checks": [...], "summary": {...}}` (summary only when verified). Use in CI or scripts.

**Non-technical recipients (T1.3):** The CLI prints **"Result: VERIFIED"** or **"Result: NOT VERIFIED"** at the end. With `--summary`, you get a short "What's inside" list. The **web verifier** (http://localhost:8000/verifier) shows a clear **Verified** or **Not verified** headline and, when verified, a **What's inside** section (investigation, title, claims, evidence count) so editors and reviewers can confirm the outcome without opening the database.

**Guarantees and limits:** For a precise list of what "verified" means and what the verifier does *not* check (e.g. event semantics, independence of sources, truth of claims), see [Verification guarantees and invariants](verification-guarantees.md).

## What it checks

| Check | Description |
|-------|-------------|
| **ZIP** | File is a valid ZIP and contains `manifest.json` and `chronicle.db`. |
| **Manifest** | Required keys present: `format_version`, `investigation_uid`. `format_version` must be ≥ 1. |
| **Schema** | `schema_version` table exists with expected components; required tables exist (e.g. `events`, `investigation`, `claim`, `evidence_item`). |
| **Evidence hashes** | For each row in `evidence_item`, the file at `uri` inside the ZIP is read and its SHA-256 is compared to `content_hash`. Paths are validated to prevent path traversal. |
| **Append-only ledger** (optional) | Events are ordered by `recorded_at` with no reversals. Omitted if you use `--no-invariants`. |

## Output and exit codes

- Each check is printed as `[PASS]` or `[FAIL]` with a short detail.
- **Exit 0** — All checks passed.
- **Exit 1** — One or more checks failed.
- **Exit 2** — Usage error (e.g. missing file path).

## Example

```bash
$ chronicle-verify exports/my_investigation.chronicle
  [PASS] file: (no detail)
  [PASS] zip: valid ZIP with manifest and DB
  [PASS] manifest: format_version=1, investigation_uid present
  [PASS] schema_version: versions: {'event_store': '1', 'read_model': '1'}
  [PASS] schema_tables: all required tables present
  [PASS] evidence_hashes: all 3 evidence file(s) match hash
  [PASS] append_only_ledger: 42 events in order
Verification passed.
```

## Conformance

A .chronicle is **conformant** if the verifier exits 0. See [conformance.md](conformance.md) for producer and consumer conformance criteria and the automated conformance test (golden fixture and generate-and-verify test). For what the verifier guarantees and what it does not, see [verification-guarantees.md](verification-guarantees.md).

---

## Reasoning brief and minimal slices

The **standalone verifier** (CLI and web) validates a **.chronicle file** (ZIP with manifest, `chronicle.db`, and evidence files). It accepts both **full** and **minimal** exports. It does **not** validate:

- A **reasoning brief** (the HTML or JSON artifact from `GET /claims/{claim_uid}/reasoning-brief`). The brief is a human- and court-ready summary of one claim (defensibility, evidence, tensions, trail) but is not a .chronicle and has no manifest or evidence hashes for the verifier to check. Recipients can read and trust the brief as "show your work"; they cannot run the verifier on it.

**Minimal .chronicle (one claim):** You can export a **minimal .chronicle** that contains only one claim and its linked evidence, spans, links, and tensions. Same ZIP + manifest + DB + evidence format as a full export; the DB is a subset. The **existing verifier** accepts and validates it (manifest, schema, evidence hashes, append-only ledger). To produce a minimal .chronicle:

- **CLI:** `chronicle export-minimal --investigation INVESTIGATION_UID --claim CLAIM_UID --output out.chronicle --path /project`
- **API:** `POST /investigations/{investigation_uid}/claims/{claim_uid}/export-minimal` (returns the .chronicle file)

The manifest of a minimal export includes `minimal_claim_uid` so recipients know it is a single-claim slice. Run the verifier on the file as usual: `chronicle verify-chronicle out.chronicle` or the web verifier.

**Summary:** Use the reasoning brief when you want to **hand over** "the proof" in one readable file. Use the .chronicle file (full or minimal) and verifier when you need **cryptographic and structural verification**. For a single claim, export a minimal .chronicle and verify it with the same verifier.

## Placement and dependencies

- **Location:** `tools/verify_chronicle/` in the chronicle-standard repository.
- **Dependencies:** None beyond Python 3.10+ standard library.
- **Documentation:** This file; see also `tools/verify_chronicle/README.md` and [conformance.md](conformance.md).
