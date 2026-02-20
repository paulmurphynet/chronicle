# Backend Migration and Versioning Policy

This policy defines how Chronicle versions event/read-model schemas across SQLite and Postgres backends.

## Versioned components

Chronicle tracks schema/component versions in `schema_version`:

1. `event_store`
2. `read_model`
3. `project_format`

Canonical constants live in `chronicle/store/schema.py`.

## Compatibility rules

1. Additive changes are preferred:
   - New nullable columns
   - New tables/indexes
   - New read-model projections that do not invalidate existing events
2. Destructive changes require a major-version migration plan:
   - Column removals or type breaks
   - Semantics that cannot be represented by replaying existing events
3. Event log compatibility is release-critical:
   - Existing events must remain replayable into current read model.

## SQLite policy

- SQLite uses DDL + additive migration helpers in `chronicle/store/schema.py`.
- Read-model rebuild from events is the default recovery path when versions drift.

## Postgres policy

- Postgres event store and read-model schema follow the same version constants and migration intent.
- Postgres read-model schema initialization and projection compatibility live in `chronicle/store/postgres_projection.py`.
- Until full query parity lands, Postgres read-model writes are treated as convergence infrastructure and validated by replay/verify paths.

## Migration process requirements

For any schema/version change:

1. Update version constant(s) if compatibility boundary changes.
2. Provide migration/rebuild path for both backends or explicitly document temporary parity gap.
3. Add/adjust tests for:
   - replay correctness
   - projection completeness
   - invariant verification
4. Update docs:
   - `docs/POSTGRES.md`
   - `docs/to_do.md`
   - release notes compatibility section

## Rollback expectations

- If migration fails, recovery path must be clear:
  - SQLite: restore DB + replay events.
  - Postgres: restore backup/snapshot + replay as needed.
- Backup/restore procedures are defined in `docs/postgres-operations-runbook.md`.
