# Support, Compatibility, and Deprecation Policy

This document defines how Chronicle support levels, compatibility guarantees, and deprecations are communicated for public use.

## Support tiers

Chronicle is shipped in three audience tiers:

| Tier | Target user | Backend posture | Support level |
|------|-------------|-----------------|---------------|
| Lite | Individual/local evaluator | SQLite | GA |
| Team/Prod | Team workflows and service deployment | Postgres event store + SQLite read model | Beta |
| Managed Postgres | Neon/RDS/Azure/GCP operators | Postgres event store + SQLite read model | Beta |

Current scope note:

- Postgres read-model parity is not complete yet, so full Postgres-only runtime is not GA.

## Surface-level support status

| Surface | Status |
|---------|--------|
| `.chronicle` export/import + verifier (`chronicle-verify`) | GA |
| Defensibility scorer contract (`docs/eval_contract.md`) | GA |
| SQLite event store + read model | GA |
| Postgres event store append/read/idempotency path | Beta |
| Postgres read model/projector | Experimental (roadmap only) |
| API and Reference UI | Beta |
| Neo4j sync/export projection | Beta |

## Backward compatibility policy

Chronicle uses a contract-first posture:

1. `.chronicle` format:
   - Existing released `.chronicle` files must continue to verify with the matching verifier version.
   - Breaking format changes require an explicit major-version bump and release note callout.
2. Eval contract (`docs/eval_contract.md`):
   - Additive fields are allowed in minor releases.
   - Field removals/renames or semantic breaks require a major release.
3. API behavior:
   - Existing documented routes and required fields are stable within a major release line.
   - New optional fields and new routes are allowed in minor releases.

## Deprecation policy

Deprecations use a defined timeline unless a security issue requires faster action:

1. Announce: release `N` includes deprecation notice with replacement guidance.
2. Warn: release `N+1` keeps behavior but adds docs/CLI/API warnings where practical.
3. Remove: earliest release `N+2` (or at least 60 days after announcement for date-based schedules).

Each deprecation notice must include:

- `What is changing`
- `Who is affected`
- `Migration path`
- `Earliest removal release/date`

## Release-note template requirements

Every release note should include these sections:

1. `Support level changes` (GA/Beta/Experimental changes by surface)
2. `Compatibility notes` (contract and `.chronicle` implications)
3. `Deprecations` (new, ongoing, removed)
