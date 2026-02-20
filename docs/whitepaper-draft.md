# Chronicle standards whitepaper draft (working)

Status: **working draft (v0.2)**  
Last updated: **2026-02-20**  
Citation and revision metadata: [Whitepaper citation and publication metadata](whitepaper-citation.md)

## Title

Chronicle: A Defensibility-Centered Provenance Model with Standards-Compatible Interoperability

## Abstract

Chronicle is an event-sourced system for recording claims, evidence, support/challenge links, and tensions, then computing defensibility metrics for review and evaluation workflows. This draft presents a standards-compatible interoperability profile that preserves Chronicle's trust-critical core while mapping to JSON-LD/PROV semantics and staged compatibility layers for C2PA, VC Data Integrity, RO-Crate, and ClaimReview. The paper also provides a reproducible evidence-pack workflow and explicit guarantee boundaries to prevent overclaiming.

## 1. Problem statement

AI-assisted workflows can generate plausible outputs that are weakly supported, difficult to audit, and hard to compare across systems. Teams need artifacts that answer:

1. What evidence supports or challenges each claim?
2. Which contradictions remain unresolved?
3. Which guarantees are structural integrity checks versus policy-relative quality metrics versus cryptographic verification?

## 2. Chronicle model summary

Chronicle centers on:

1. Immutable event history
2. Evidence and span anchoring
3. Claim lifecycle and typed support/challenge links
4. Tension lifecycle for contradiction handling
5. Defensibility scorecards and reasoning trails

Chronicle remains the canonical internal model; standards mappings are interoperability profiles layered on top.

## 3. Standards interoperability profile

### 3.1 Semantic baseline

- JSON-LD 1.1 serialization profile
- PROV-compatible mapping for entities, agents, activities, and qualified relations

### 3.2 Cryptographic compatibility layers

- C2PA adapter path for media/content provenance assertions
- VC Data Model 2.0 + VC Data Integrity 1.0 for signed attestation compatibility

### 3.3 Packaging and publication interoperability

- RO-Crate profile for portable research/data packages
- schema.org ClaimReview export profile for fact-checking ecosystems

### 3.4 Adjacent standards boundaries

OpenLineage, in-toto, and SLSA are treated as complementary ecosystems rather than Chronicle replacements. See [Adjacent standards guidance](adjacent-standards-guidance.md).

## 4. End-to-end reproducible example (deterministic)

This revision includes a concrete reproducible flow based on the whitepaper evidence pack tooling.

Run from repo root:

```bash
PYTHONPATH=. python3 scripts/whitepaper/build_evidence_pack.py \
  --components standards verifier \
  --output-dir whitepaper_evidence_runs/v0_2_example
```

Expected outputs include:

1. `standards_profiles/standards_jsonld_export.json`
2. `standards_profiles/claimreview_export.json`
3. `standards_profiles/ro_crate_export.json`
4. `standards_profiles/c2pa_export_metadata_only.json`
5. `standards_profiles/vc_export_metadata_only.json`
6. `standards_profiles/sample_investigation.chronicle`
7. `verifier/verification_report.json`
8. `evidence_pack_manifest.json`

This deterministic example demonstrates one investigation containing support, challenge, source linkage, tension modeling, C2PA metadata references, VC attestation metadata, and verifier-backed package integrity.

## 5. Guarantees and non-guarantees matrix

| Area | Chronicle guarantees | Chronicle does not guarantee | Primary source |
|------|----------------------|------------------------------|----------------|
| `.chronicle` package verification | Structural ZIP/manifest/schema checks; evidence hash integrity; optional append-only timestamp monotonicity checks. | Event semantic correctness, claim truth, source independence verification. | [Verification guarantees](verification-guarantees.md) |
| Runtime invariants | Append-only event history, replayable read model, consistency checks via runtime verification commands. | That user-recorded provenance assertions are externally true. | [Verification guarantees](verification-guarantees.md) |
| Defensibility scorecards | Stable metrics shape for claim-level defensibility (`provenance_quality`, corroboration, contradiction status, optional knowability/link assurance). | Truth judgments or entailment proof of support/challenge links. | [Defensibility metrics schema](defensibility-metrics-schema.md) |
| C2PA compatibility export | Explicit verification modes (`disabled`, `metadata_only`) and normalized status semantics. | Cryptographic C2PA verification by default. | [C2PA compatibility export](c2pa-compatibility-export.md) |
| VC/Data Integrity compatibility export | Explicit verification modes (`disabled`, `metadata_only`) and attestation metadata projection for claims/artifacts/checkpoints. | Cryptographic VC/Data Integrity verification by default. | [VC/Data Integrity export](vc-data-integrity-export.md) |
| Standards mapping posture | JSON-LD/PROV/RO-Crate/ClaimReview/C2PA/VC interoperability profiles with versioned docs and tests. | Replacement of Chronicle canonical model with external schema-first storage. | [Standards profile](standards-profile.md) |

## 6. Security and threat considerations

This profile addresses:

1. Tampering and package integrity checks (`.chronicle` verifier and evidence hashes)
2. Provenance assertion spoofing risk (recorded-vs-verified boundary is explicit)
3. Evidence/source trust boundaries (modeled links are auditable but not self-authenticating)
4. Replay and reproducibility safeguards (event log + deterministic tooling + manifested evidence pack)

## 7. Evaluation methodology

Evaluation and reporting are grounded in reproducible commands:

1. Deterministic benchmark scenarios (`scripts/benchmark_data/run_defensibility_benchmark.py`)
2. Trust metric reporting (`scripts/benchmark_data/trust_progress_report.py`)
3. Standards profile examples via whitepaper evidence pack (`scripts/whitepaper/build_evidence_pack.py`)

This yields a repeatable artifact chain from benchmark rows to defensibility metrics to export compatibility examples and verifier outputs.

## 8. Standardization path

Versioned progression:

1. Publish and revise the whitepaper draft with explicit citations and metadata.
2. Run internal and external review loops; log accepted/rejected changes.
3. Share submission package artifacts with relevant communities using the outreach template.

Operational references:

- [Whitepaper plan](whitepaper-plan.md)
- [Whitepaper internal review log](whitepaper-internal-review-log.md)
- [Standards submission package](standards-submission-package.md)

## 9. Conclusion

Chronicle can remain model-first and verifiability-first while interoperating with established provenance and attestation standards through explicit, testable profile layers. The key requirement is explicit separation between structural integrity guarantees, policy-relative defensibility metrics, and cryptographic verification claims.

## Appendix A: reproducibility commands

```bash
# Build full whitepaper evidence pack
PYTHONPATH=. python3 scripts/whitepaper/build_evidence_pack.py

# Build standards + verifier subset used in this revision
PYTHONPATH=. python3 scripts/whitepaper/build_evidence_pack.py \
  --components standards verifier \
  --output-dir whitepaper_evidence_runs/v0_2_example

# Re-run docs integrity checks before publication update
PYTHONPATH=. python3 scripts/check_doc_links.py .
PYTHONPATH=. python3 scripts/check_docs_currency.py
```

## Appendix B: artifacts to attach before public release

1. Profile mapping examples (JSON-LD/PROV)
2. C2PA/VC adapter examples
3. RO-Crate and ClaimReview export fixtures
4. Reproducibility command list and expected outputs (see [Whitepaper evidence pack](whitepaper-evidence-pack.md))
