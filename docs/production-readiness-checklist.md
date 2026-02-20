# Production Readiness Checklist

This checklist defines objective pass/fail criteria before Chronicle is treated as production-ready for a release.

## 1) Core trust gates (required)

- [ ] Verifier and invariant suites pass:
  - `pytest tests/test_verify.py tests/test_verifier.py tests/test_verifier_parity.py -q`
- [ ] Conformance check passes on a freshly generated sample package:
  - `PYTHONPATH=. python3 scripts/verticals/journalism/generate_sample.py --output /tmp/release_gate_sample.chronicle`
  - `PYTHONPATH=. python3 scripts/run_conformance.py /tmp/release_gate_sample.chronicle`
- [ ] Import verification and evidence conflict protections remain covered by tests:
  - `pytest tests/test_phase5_coverage.py::test_import_investigation_blocks_merge_when_existing_evidence_differs -q`
  - `pytest tests/test_api_contract.py::test_api_import_returns_400_for_tampered_archive -q`

## 2) Backend gates (required)

- [ ] SQLite baseline tests pass:
  - `pytest -q`
- [ ] Postgres event-store smoke path passes:
  - `PYTHONPATH=. python3 scripts/postgres_doctor.py --database-url "$CHRONICLE_POSTGRES_URL"`
  - `PYTHONPATH=. python3 scripts/postgres_smoke.py --database-url "$CHRONICLE_POSTGRES_URL"`
- [ ] Backend parity gate passes (SQLite vs Postgres defensibility):
  - `PYTHONPATH=. python3 scripts/postgres_backend_parity.py --database-url "$CHRONICLE_POSTGRES_URL"`
- [ ] Timed onboarding gate passes (doctor + smoke <= 10 minutes):
  - `PYTHONPATH=. python3 scripts/postgres_onboarding_timed_check.py --database-url "$CHRONICLE_POSTGRES_URL"`
- [ ] Postgres limitation is clearly documented if read-model parity is not yet complete.

## 3) CI and branch protection gates (required)

- [ ] Required CI jobs are green on push/PR:
  - `lint-and-test (3.11)`
  - `lint-and-test (3.12)`
  - `frontend-checks`
  - `postgres-event-store-smoke`
  - Note: `postgres-event-store-smoke` includes doctor + smoke + backend parity + timed onboarding gates.
- [ ] Branch protection requires these checks before merge.
- [ ] Branch protection rollout report status is `passed`:
  - `PYTHONPATH=. python3 scripts/check_branch_protection_rollout.py --repo "$GITHUB_REPOSITORY" --branch main --output reports/branch_protection_rollout_report.json`

References:

- `docs/ci-branch-protection.md`
- `docs/branch-protection-rollout-verification.md`

## 4) Security and operational gates (required)

- [ ] Dependency scan gate passes (`pip-audit` + `npm audit` thresholds).
  - Frontend dependency audit requires committed `frontend/package-lock.json`.
- [ ] Container scan gate passes (Trivy filesystem + base image thresholds).
- [ ] Managed Postgres hardening checklist reviewed and signed off.
- [ ] Backup/restore and disaster-recovery drill steps are current and runnable.

References:

- `docs/security-automation.md`
- `docs/postgres-hardening.md`
- `docs/postgres-operations-runbook.md`

## 5) Documentation gates (required)

- [ ] Docs links check passes:
  - `python3 scripts/check_doc_links.py docs`
  - `python3 scripts/check_doc_links.py lessons`
  - `python3 scripts/check_doc_links.py story`
  - `python3 scripts/check_doc_links.py critical_areas`
- [ ] Docs currency check passes: `python3 scripts/check_docs_currency.py`
- [ ] README/docs include current support tiers and known backend limits.

## Release decision

Release is `GO` only if every required checkbox above is complete; otherwise `NO-GO`.
