# Zero to submission: one path to a verifiable package

One narrative path: install → create investigation → add evidence → claim + link → defensibility → export submission package in about 30 minutes. Use this when you want a single “how do I get to something I can send?” guide.

---

## Goal

Produce a submission package (ZIP) that you can hand off to someone else. It contains:

- The investigation as a `.chronicle` file (verifiable with `chronicle-verify`).
- Reasoning briefs (one HTML per claim): claim, defensibility, support/challenge, tensions, trail.
- A manifest listing the investigation and claim UIDs.

Recipients can verify the .chronicle and read the reasoning briefs without running Chronicle.

---

## Path (API or CLI)

### 1. Install and run

- API: `pip install -e ".[api]"`, set `CHRONICLE_PROJECT_PATH`, run `uvicorn chronicle.api.app:app --reload`.
- CLI only: `pip install -e .`, set `CHRONICLE_PROJECT_PATH`, use `chronicle` and `chronicle-verify` commands.

See [Getting started](getting-started.md) and [API](api.md).

### 2. Create an investigation

- API: `POST /investigations` with `{"title": "...", "description": "..."}` → `investigation_uid`.
- CLI: `chronicle investigation create "Title" --description "..."`.

### 3. Add evidence

- API: `POST /investigations/{id}/evidence` with JSON `{"content": "..."}` or multipart file → `evidence_uid`, `span_uid`.
- CLI: `chronicle evidence add <inv_uid> --content "..."` or `--file path`.

Add as many evidence items as you need; record `span_uid`s for linking.

### 4. Propose claims and link support/challenge

- API: `POST /investigations/{id}/claims` → `claim_uid`. Then `POST .../links/support` and/or `.../links/challenge` with `span_uid` and `claim_uid`.
- CLI: `chronicle claim propose ...`, `chronicle link support ...` / `chronicle link challenge ...`.

Optionally declare tensions between claims (`POST .../tensions` or CLI).

### 5. Check defensibility

- API: `GET /claims/{claim_uid}/defensibility`.
- CLI: `chronicle defensibility <claim_uid>`.

Same shape as the [eval contract](eval_contract.md) and [defensibility metrics schema](defensibility-metrics-schema.md).

### 6. Export submission package

- API: `POST /investigations/{id}/submission-package` → download `{id}-submission.zip`.
- CLI: Use the API for the submission package, or export only the .chronicle: `chronicle export <inv_uid> --output file.chronicle`.

The submission ZIP contains:

- `{investigation_uid}.chronicle` — full investigation export (verify with `chronicle-verify`).
- `reasoning_briefs/{claim_uid}.html` — one HTML reasoning brief per claim.
- `manifest.json` — investigation_uid, title, claim_uids, generated_at.

### 7. Verify before sending

Run `chronicle-verify path/to/file.chronicle` on the `.chronicle` file inside the ZIP (or verify the .chronicle from a plain export). See [Verifier](verifier.md) and [Verification guarantees](verification-guarantees.md).

---

## Summary

| Step | Outcome |
|------|--------|
| Install + run | API or CLI ready |
| Create investigation | investigation_uid |
| Add evidence | evidence_uid, span_uid(s) |
| Propose claim(s) + link | claim_uid(s), support/challenge links |
| Defensibility | Scorecard per claim |
| Export submission package | ZIP: .chronicle + reasoning_briefs/ + manifest |
| Verify | chronicle-verify on the .chronicle |

For a shorter “first run” without the full submission package, see [Quickstart](quickstart.md). For the reasoning brief as the primary shareable artifact, see [Reasoning brief](reasoning-brief.md).
