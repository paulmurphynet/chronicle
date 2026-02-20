# RO-Crate export (S-05)

Chronicle provides a baseline RO-Crate profile to improve package interoperability for research and data workflows.

## API

`chronicle.store.commands.generic_export.build_ro_crate_export(read_model, investigation_uid, *, claim_limit=10000)`

## Output shape

The export returns JSON with:

1. `@context` including RO-Crate context and Chronicle namespace extension
2. `@graph` entries for:
   - `ro-crate-metadata.json`
   - dataset root (`./`) with `hasPart`
   - canonical Chronicle files (`chronicle.db`, `manifest.json`)
   - claims, evidence items, and tensions as crate parts

## Notes

1. This is a compatibility profile for interchange and indexing.
2. Chronicle `.chronicle` and verifier remain the canonical trust artifacts.
3. Consumers should treat Chronicle namespace fields as profile extensions.
