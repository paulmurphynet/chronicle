# Adapters (examples and templates)

Minimal adapters that map external formats or harnesses to Chronicle (scorer, session, or export).

| Script | Purpose |
|--------|---------|
| **example_rag_to_scorer.py** | Copy-paste template: read JSON (query, answer, evidence) from stdin or file, call the defensibility scorer, print metrics JSON. Use when your RAG harness outputs the same shape as the [eval contract](../../docs/eval_contract.md). |
| **starter_batch_to_scorer.py** | Production-ready starter: read harness JSONL rows, map fields/paths to eval contract, run scorer, emit one JSONL output row per run with `chronicle` payload. Supports nested-path mapping via `--profile`. |
| **ragas_batch_to_chronicle.py** | RAGAS-first batch adapter: auto-maps common RAGAS keys (`question`, `answer`, `contexts` / `retrieved_contexts`) to Chronicle eval contract and emits scored JSONL rows with mapping metadata. |
| **validate_adapter_outputs.py** | Validate adapter output rows against eval contract success/error shapes (defaults to `chronicle` wrapper key). |
| **fact_checker_to_chronicle.py** | Fact-checker output → Chronicle: claim + verdict + sources (JSON) → evidence items, propose_claim, support/challenge links. Expected format: `claim`, `verdict` (true/false/mixed), `sources` (array with snippet, stance). See script docstring. |
| **provenance_to_chronicle.py** | Provenance assertions → Chronicle: register sources, ingest evidence, link_evidence_to_source. We record; we do not verify. Expected format: `assertions` array with source_display_name, evidence_content, etc. See [Provenance recording](../../docs/provenance-recording.md). Requires `--path` to an existing project. |
| **c2pa_to_chronicle.py** | C2PA assertions → Chronicle metadata and source links. Records C2PA references (`c2pa_claim_id`, `c2pa_assertion_id`, etc.) with explicit status semantics; does not perform cryptographic verification by default. See [C2PA compatibility export](../../docs/c2pa-compatibility-export.md). |
| **vc_to_chronicle.py** | VC/Data Integrity attestations → Chronicle claim/artifact/checkpoint writes with payload attestation metadata (`_verification_level`, `_attestation_ref`). Exposes status via [VC/Data Integrity compatibility export](../../docs/vc-data-integrity-export.md). |

**Standard path:** Your RAG harness → contract input (query, answer, evidence) → scorer → defensibility metrics. See [RAG evals: defensibility metric](../../docs/rag-evals-defensibility-metric.md).

### Starter commands

```bash
# Score harness rows (JSONL) with default keys: query, answer, evidence
PYTHONPATH=. python3 scripts/adapters/starter_batch_to_scorer.py \
  --input runs.jsonl \
  --output scored.jsonl

# Validate adapter outputs
PYTHONPATH=. python3 scripts/adapters/validate_adapter_outputs.py \
  --input scored.jsonl
```

Use a mapping profile (nested key paths):

```bash
PYTHONPATH=. python3 scripts/adapters/starter_batch_to_scorer.py \
  --profile scripts/adapters/examples/mapping_profile_nested.json \
  --input scripts/adapters/examples/harness_runs_nested.jsonl \
  --output scored_nested.jsonl

# RAGAS-like rows (JSONL or JSON array)
PYTHONPATH=. python3 scripts/adapters/ragas_batch_to_chronicle.py \
  --input runs_ragas.jsonl \
  --output scored_ragas.jsonl
```

### Included examples

Checked-in examples live under `scripts/adapters/examples/`:

- `harness_runs_valid.jsonl` (input rows for starter adapter)
- `scored_runs_example.jsonl` (example output rows with success and contract-valid error payload)

Validate examples and starter flow end-to-end:

```bash
PYTHONPATH=. python3 scripts/adapters/check_examples.py
```
