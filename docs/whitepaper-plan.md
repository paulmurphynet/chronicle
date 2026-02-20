# Whitepaper and standards submission plan

Last updated: **2026-02-20**

This plan defines how Chronicle should produce a publication-quality whitepaper and engage standards bodies responsibly.

## Goals

1. Publish a credible, citable whitepaper describing Chronicle's model, guarantees, and limits.
2. Provide a standards-facing interoperability profile with concrete mappings and conformance language.
3. Create an evidence-backed package suitable for standards discussions and external review.

## Deliverables

1. **Position whitepaper draft** (problem, model, standards mappings, trust boundaries, threat model).
2. **Interoperability annex** (JSON-LD context, PROV mapping rules, ClaimReview/RO-Crate/C2PA/VC profile details).
3. **Conformance evidence pack** (verifier results, reproducible workflows, example artifacts, mapping test fixtures).
4. **Submission package** for standards/community review (PDF/Markdown draft, references, reproducibility instructions).

Implementation reference: [Whitepaper evidence pack](whitepaper-evidence-pack.md), [Whitepaper citation and publication metadata](whitepaper-citation.md), [Whitepaper internal review log](whitepaper-internal-review-log.md), [Standards submission package](standards-submission-package.md), and `scripts/whitepaper/build_evidence_pack.py`.

## Recommended process

### Phase 1: authoring baseline

1. Freeze terminology and guarantees using existing docs (`technical-report`, `verification-guarantees`, `critical_areas`).
2. Draft whitepaper v0.1 using the template in `docs/whitepaper-draft.md`.
3. Add explicit non-goals and limitations to avoid overclaiming.

### Phase 2: technical evidence

1. Add interoperability examples for each adopted standard profile.
2. Run reproducibility checks on all examples and archive outputs.
3. Record known gaps and implementation status by profile.

### Phase 3: review and publication readiness

1. Internal review pass (core maintainers + integration contributors).
2. External peer-review pass (friendly design partners / researchers).
3. Produce citable release (tagged document revision + changelog entry + citation update).

### Phase 4: standards engagement

1. Share the profile and whitepaper with relevant groups.
2. Collect issue-driven feedback and track accepted/rejected changes.
3. Publish periodic profile revisions with versioned compatibility notes.

## Suggested target venues and communities

Use a parallel outreach strategy; do not block on a single venue:

1. W3C-linked communities for JSON-LD/PROV/VC related discussion.
2. C2PA ecosystem channels for content provenance compatibility review.
3. Research and applied-AI venues where reproducible provenance and defensibility evaluation matter.

## Publication quality gate

Whitepaper submission should require:

1. Every claim about Chronicle guarantees links to a verifiable source doc or test.
2. Every standards mapping has at least one executable example.
3. Limitations are explicit (semantic provenance vs cryptographic verification vs truth claims).
4. Versioning/citation metadata is present (date, revision, canonical repo path, citation format).

## Ownership model

- **Editor:** coordinates narrative coherence and publication timeline.
- **Technical owners:** maintain mapping correctness per standard profile.
- **Verification owner:** validates reproducibility artifacts and conformance evidence.
- **Release owner:** manages versioned publication and citation updates.

Track concrete implementation and publication tasks in [Implementation To-Do](to_do.md).
