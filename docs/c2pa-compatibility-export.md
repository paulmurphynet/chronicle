# C2PA compatibility export (S-06)

Chronicle provides a C2PA compatibility export that surfaces C2PA assertion references recorded in evidence metadata.

## API

`chronicle.store.commands.generic_export.build_c2pa_compatibility_export(read_model, investigation_uid, *, verification_enabled=False)`

## Output

The export returns:

1. `schema_version`, `schema_doc`, `investigation_uid`
2. `verification` object with explicit mode:
   - `enabled=false` -> `mode=disabled` and entries marked `not_verified`
   - `enabled=true` -> `mode=metadata_only` and status taken from recorded metadata when present
3. `evidence_assertions` array containing per-evidence C2PA reference metadata

## Recorded fields

The profile surfaces known keys when present:

- `c2pa_claim_id`
- `c2pa_assertion_id`
- `c2pa_manifest_digest`
- `c2pa_manifest_url`
- `c2pa_issuer`
- `c2pa_signer`
- `c2pa_generator`
- `c2pa_signature_algorithm`
- `c2pa_assertion_hash`
- `c2pa_validation_report_uri`
- `c2pa_verification_status`

## Important trust caveat

Chronicle records C2PA references and optional status metadata. Cryptographic verification is not performed by default in this export path.
