# Integration export hardening

This guide defines the hardened interoperability path for four integration-facing export surfaces:

1. Generic JSON export
2. Generic CSV ZIP export
3. Reasoning brief Markdown export
4. Signed `.chronicle` archive bundles (digest-verified wrapper)

Use this as the baseline contract for adapters, API clients, and release checks.

## What was added

- Generic JSON contract validator: `validate_generic_export_json(...)`
- Generic CSV ZIP contract validator: `validate_generic_export_csv_zip(...)`
- Reasoning brief Markdown renderer: `reasoning_brief_to_markdown(...)`
- Signed bundle export/import helpers:
  - `export_signed_investigation_bundle(...)`
  - `verify_signed_investigation_bundle(...)`
  - `import_signed_investigation_bundle(...)`
- End-to-end contract harness script:
  - `scripts/check_integration_export_contracts.py`

## Signed bundle trust model

Signed bundle support is intentionally explicit:

- The bundle wraps one `.chronicle` archive plus `signature_manifest.json`.
- Integrity is enforced by SHA-256 digest matching against manifest metadata.
- If no external signature value is supplied, status is `metadata_only` (digest-verifiable, not cryptographically signed by Chronicle).
- Nested `.chronicle` integrity is still verified with the standard verifier checks before import.

So: this path is interoperable and tamper-evident by default, with optional downstream cryptographic signature integration.

## Run the contract harness

```bash
PYTHONPATH=. python3 scripts/check_integration_export_contracts.py \
  --project-path /tmp/chronicle_contract_project \
  --output-dir /tmp/chronicle_contract_out \
  --stdout-json
```

Expected output:

- `integration_export_contract_report.json`
- `generic_export.json`
- `generic_export_csv.zip`
- `reasoning_brief.md`
- `sample_investigation.chronicle`
- `sample_investigation_signed.zip`

## Contract tests

Run focused tests:

```bash
PYTHONPATH=. python3 -m pytest -q \
  tests/test_generic_export_contracts.py \
  tests/test_phase5_coverage.py \
  tests/test_integration_export_contracts.py
```

These tests are intended to catch release regressions in adapter/API-facing import/export behavior.
