# Adversarial and failure-mode examples

This document shows how Chronicle should fail safely or disclose uncertainty under adversarial or ambiguous conditions.

## AF-001: Conflicting evidence on the same event

- Scenario:
  - One evidence source supports claim A.
  - Another source challenges claim A for the same date/time.
- Expected Chronicle behavior:
  1. Record both links.
  2. Represent contradiction explicitly as tension.
  3. Reflect challenge posture in defensibility output.
- Safe outcome:
  - Do not collapse to a truth claim.
  - Preserve unresolved contradiction in outputs/reports.

## AF-002: Provenance assertion with no cryptographic verification

- Scenario:
  - C2PA or VC reference metadata is provided, but verification is not executed.
- Expected Chronicle behavior:
  1. Preserve references in compatibility exports.
  2. Mark verification mode explicitly (`disabled` or `metadata_only`).
- Safe outcome:
  - Do not claim authenticity as verified.

## AF-003: Source-independence overstatement risk

- Scenario:
  - Multiple linked sources might not be truly independent in the real world.
- Expected Chronicle behavior:
  1. Report independent source counts as modeled, not as independently verified fact.
  2. Keep `independence_notes` and caveat language explicit.
- Safe outcome:
  - Preserve analyst-entered rationale without overclaiming verification.

## AF-004: Non-deterministic scoring risk under identical inputs

- Scenario:
  - Same scorer input produces unstable defensibility outputs across repeated runs.
- Expected Chronicle behavior:
  1. Run deterministic reproducibility gate:
     - `PYTHONPATH=. python3 scripts/check_deterministic_defensibility.py --rounds 3`
  2. Fail CI/release gate when normalized outputs differ.
- Safe outcome:
  - Prevent silent non-determinism from shipping.

## AF-005: Partial package integrity compromise

- Scenario:
  - `.chronicle` archive contains altered evidence bytes or manifest/schema mismatch.
- Expected Chronicle behavior:
  1. Verifier fails package checks.
  2. Import path blocks non-conformant archives.
- Safe outcome:
  - Reject invalid artifacts instead of attempting silent recovery.

## Practical review checklist

When evaluating a pipeline or release candidate:

1. Run `.chronicle` verification on produced artifacts.
2. Check tensions and contradiction posture in review packet.
3. Verify compatibility export modes are explicit and non-overclaiming.
4. Run deterministic defensibility check before release.
