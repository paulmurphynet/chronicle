# VC/Data Integrity compatibility export (S-07)

Chronicle provides a VC/Data Integrity compatibility export that surfaces attestation metadata for claims, artifacts, and checkpoints.

## API

`chronicle.store.commands.generic_export.build_vc_data_integrity_export(read_model, investigation_uid, *, verification_enabled=False)`

## Output

The export returns:

1. `schema_version`, `schema_doc`, `investigation_uid`
2. `verification` object with explicit mode:
   - `enabled=false` -> `mode=disabled` and entries marked `not_verified`
   - `enabled=true` -> `mode=metadata_only` and status derived from recorded attestation metadata
3. `attestations` object with arrays for:
   - `claims`
   - `artifacts`
   - `checkpoints`

Each subject entry includes an `attestation` object with:

- `verification_status` (`verified`, `failed`, `not_verified`, `unknown`)
- Optional `verification_level`
- Optional `attestation_ref`
- Optional `recorded_at` and `source_event_id`

## Important trust caveat

Chronicle records VC/Data Integrity references and identity-level metadata in event payloads. Cryptographic verification is not performed by default in this export path.
