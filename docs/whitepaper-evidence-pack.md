# Whitepaper evidence pack

This document defines the reproducible evidence bundle used for whitepaper claims and standards-facing review.

## Goal

Produce a single, reproducible artifact set containing:

1. Benchmark outputs and trust summary
2. Reproducible workflow report
3. Standards profile export examples (JSON-LD/PROV, ClaimReview, RO-Crate, C2PA, VC/Data Integrity)
4. Verifier output over a generated `.chronicle` artifact
5. One machine-readable manifest with command traces

## Build command

From repo root:

```bash
PYTHONPATH=. python3 scripts/whitepaper/build_evidence_pack.py
```

By default this writes to:

- `whitepaper_evidence_runs/<timestamp>/`

Manifest path:

- `whitepaper_evidence_runs/<timestamp>/evidence_pack_manifest.json`

## Optional component selection

Build only specific components:

```bash
PYTHONPATH=. python3 scripts/whitepaper/build_evidence_pack.py \
  --components standards verifier \
  --output-dir whitepaper_evidence_runs/manual-pack
```

Available components:

- `benchmark`
- `workflows`
- `standards`
- `verifier`

## Artifact layout

The generated pack includes:

- `benchmark/benchmark_defensibility_results.json`
- `benchmark/trust_progress_report.json`
- `reference_workflows/reference_workflow_report.json`
- `standards_profiles/standards_jsonld_export.json`
- `standards_profiles/claimreview_export.json`
- `standards_profiles/ro_crate_export.json`
- `standards_profiles/c2pa_export_disabled.json`
- `standards_profiles/c2pa_export_metadata_only.json`
- `standards_profiles/vc_export_disabled.json`
- `standards_profiles/vc_export_metadata_only.json`
- `standards_profiles/sample_investigation.chronicle`
- `verifier/verification_report.json`
- `evidence_pack_manifest.json`

## Trust boundary reminder

Compatibility exports represent Chronicle-recorded metadata and mappings. They do not claim cryptographic verification unless verification is explicitly executed and recorded.
