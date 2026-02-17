# Conformance

A **.chronicle** file is **conformant** if the standalone verifier exits 0. That is, the package is a valid ZIP with a valid manifest, schema, and evidence hashes; and (unless `--no-invariants` is used) the event log is append-only.

- **Producers** should generate `.chronicle` files that pass the verifier. See [Verifier](verifier.md) for how to run it.
- **Consumers** can rely on the [Verification guarantees](verification-guarantees.md) when verification passes.

There is no separate "conformance test suite" in this repo beyond running the verifier on a `.chronicle` file (or generating one from the session and verifying it). For what the verifier checks and does not check, see [Verification guarantees](verification-guarantees.md).
