# Quickstart: first investigation in ~15 minutes

Get from zero to a verified record of a claim and its evidence using the Chronicle API or CLI. When the [Reference UI](reference-ui-plan.md) is available, you can do the same flow in the browser with a Try sample path (load a sample investigation, highlight → link, see defensibility update).

---

## Option A: API (recommended for automation)

Prerequisites: Python 3.11+, `pip install -e ".[api]"`, set `CHRONICLE_PROJECT_PATH` to a directory (e.g. `./my_project`), run `uvicorn chronicle.api.app:app --reload`.

1. **Create an investigation**
   ```http
   POST /investigations
   {"title": "Quickstart run", "description": "First investigation"}
   ```
   → Save `investigation_uid`.

2. **Add evidence**
   ```http
   POST /investigations/{id}/evidence
   Content-Type: application/json
   {"content": "The company reported revenue of $1.2M in Q1 2024."}
   ```
   → Save `evidence_uid` and `span_uid`.

3. **Propose a claim**
   ```http
   POST /investigations/{id}/claims
   {"text": "Revenue was $1.2M in Q1 2024."}
   ```
   → Save `claim_uid`.

4. **Link evidence as support**
   ```http
   POST /investigations/{id}/links/support
   {"span_uid": "<span_uid>", "claim_uid": "<claim_uid>"}
   ```

5. **Check defensibility**
   ```http
   GET /claims/{claim_uid}/defensibility
   ```
   → You get the same metrics shape as the [eval contract](eval_contract.md).

6. **Export and verify**
   - `POST /investigations/{id}/export` → download `{id}.chronicle`.
   - Run `chronicle-verify path/to/file.chronicle` (or use the web verifier at `/verifier`).

See [API](api.md) for all endpoints and [Zero to submission](zero-to-submission.md) for the full path to a submission package.

---

## Option B: CLI

From the repo root with a project directory:

```bash
export CHRONICLE_PROJECT_PATH=./my_project   # or set in env
chronicle project init                       # if directory is new
chronicle investigation create "Quickstart" --description "First investigation"
# Use the returned investigation_uid in the next commands.
chronicle evidence add <inv_uid> --content "The company reported revenue of $1.2M in Q1 2024."
chronicle claim propose <inv_uid> --text "Revenue was $1.2M in Q1 2024."
chronicle link support <inv_uid> --span-uid <span_uid> --claim-uid <claim_uid>
chronicle defensibility <claim_uid>
chronicle export <inv_uid> --output ./quickstart.chronicle
chronicle-verify ./quickstart.chronicle
```

See [Getting started](getting-started.md) and [Verifier](verifier.md) for details.

---

## Try sample (no typing)

To verify a .chronicle file without building one yourself:

```bash
PYTHONPATH=. python3 scripts/generate_sample_chronicle.py
chronicle-verify path/to/generated.chronicle
```

Or open the web verifier at http://localhost:8000/verifier (with the API running) and drag-and-drop a `.chronicle` file. No data is uploaded; verification runs in the browser.

---

## Next steps

- **Zero to submission** — [Zero to submission](zero-to-submission.md): one path to an exportable submission package in ~30 minutes.
- **Reasoning brief** — [Reasoning brief](reasoning-brief.md): the shareable artifact per claim (defensibility, support/challenge, trail).
- **When to use Chronicle** — [When to use Chronicle](when-to-use-chronicle.md): scope and how it differs from data lineage or ML provenance.
