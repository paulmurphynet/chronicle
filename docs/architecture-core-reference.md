# Core vs Reference architecture

Chronicle is split conceptually into two layers:

1. **Core (trust boundary)**: event model, policy, validation, event store/read model, defensibility scoring, `.chronicle` export/import, and verification.
2. **Reference (adapter boundary)**: CLI UX, HTTP API, frontend, and integration adapters.

This split keeps the trust-critical logic stable while allowing user interfaces and adapters to evolve faster.

---

## Why this matters

- **Safety and ethics**: users should trust that scores and verification are reproducible, even if UI/API wrappers change.
- **Open-source adoption**: contributors can build domain-specific surfaces without changing the core trust model.
- **Solo-dev sustainability**: most regressions come from boundary drift; this architecture makes drift visible and testable.

---

## Current module map

### Core

- `chronicle/core/*`
- `chronicle/store/*` (event store, read model, projection, session facade)
- `chronicle/eval_metrics.py`
- `chronicle/verify.py`
- `tools/verify_chronicle/*`

### Reference

- `chronicle/api/app.py`
- `chronicle/http_client.py`
- `chronicle/reference/*` (stable reference import paths)
- `chronicle/cli/*`
- `frontend/*`
- `chronicle/integrations/*`

---

## Practical rules

1. Core behavior changes require regression tests.
2. Reference layers should consume stable core contracts, not bypass them.
3. API/client/frontend parity is enforced through tests.
4. `.chronicle` compatibility and verifier behavior are treated as release-critical.

---

## Migration direction

Near term:

- Continue extracting monolithic modules (`chronicle/cli/main.py`, `chronicle/store/session.py`) into domain files while preserving public interfaces.
- Keep backward-compatible import paths (`chronicle.http_client`, `chronicle.api.app`).

Longer term:

- Consider publishing core and reference as separate install extras once boundaries are stable.

See also: [Reference UI plan](reference-ui-plan.md), [To-do](to_do.md), [Verification guarantees](verification-guarantees.md).
