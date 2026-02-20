# PostgreSQL backend (convergence track)

Chronicle includes a PostgreSQL **event-store** implementation today and is actively converging toward broader backend parity.

Current scope:

- PostgreSQL event-store append/read is available via `chronicle/store/postgres_event_store.py`.
- PostgreSQL event append now also projects into Postgres read-model tables (schema + projector parity path).
- SQLite remains the complete baseline path for read model + projections.
- Postgres read-model parity is tracked in the main convergence program in [to_do](to_do.md#active-convergence-program-public--ci--postgres).

## Quick start (local Postgres in minutes)

Prerequisites:

- Docker with `docker compose`
- Python env with optional Postgres deps: `pip install -e ".[postgres]"`

From repo root:

```bash
make postgres-env
make postgres-up
make postgres-doctor
make postgres-smoke
```

What these do:

- `make postgres-env` creates `.env.postgres.local` from `.env.postgres.example` (if missing).
- `make postgres-up` starts Postgres via `docker-compose.postgres.yml`.
- `make postgres-doctor` verifies dependency + connectivity.
- `make postgres-smoke` performs a minimal Chronicle event-store append/read/idempotency-key smoke test.

Stop local Postgres:

```bash
make postgres-down
```

## Managed Postgres (Neon/RDS/etc.)

You can skip Docker and point tools to a managed DB:

1. Set `CHRONICLE_POSTGRES_URL` in environment (or in your env file).
2. Run:

```bash
PYTHONPATH=. python3 scripts/postgres_doctor.py --database-url "$CHRONICLE_POSTGRES_URL"
PYTHONPATH=. python3 scripts/postgres_smoke.py --database-url "$CHRONICLE_POSTGRES_URL"
```

## Environment variables

See `.env.postgres.example`:

- `CHRONICLE_EVENT_STORE`
- `CHRONICLE_POSTGRES_URL`
- `CHRONICLE_POSTGRES_HOST`
- `CHRONICLE_POSTGRES_PORT`
- `CHRONICLE_POSTGRES_DB`
- `CHRONICLE_POSTGRES_USER`
- `CHRONICLE_POSTGRES_PASSWORD`

Backend wiring behavior (current):

- `ChronicleSession` now resolves event-store backend from `CHRONICLE_EVENT_STORE` (or explicit constructor args).
- `sqlite` is the default and remains the only full session/API/CLI path.
- `postgres` selection is parsed and validated.
- Postgres read-model tables are projected, but query-surface parity remains in progress; session/API guardrails remain SQLite-first for now.

## Important limitation (current)

Postgres read model is not yet parity-complete. Query surfaces for claims/defensibility/tensions remain SQLite-first in the current runtime path even though Postgres read-model projection tables are now written.

## Replay and snapshot (Postgres mode)

When `CHRONICLE_EVENT_STORE=postgres` is set, CLI replay/snapshot commands route to Postgres backend helpers:

- `chronicle replay --path /path/to/project`
- `chronicle snapshot create --path /path/to/project --at-event <event_id> --output postgres_snapshot.json`
- `chronicle snapshot restore --path /path/to/project --snapshot postgres_snapshot.json`

Postgres snapshots currently use a JSON read-model snapshot format for restore + tail replay workflows.

`chronicle verify --path /path/to/project` also supports Postgres mode in this configuration and runs invariant checks directly against the configured Postgres database URL.

Archive import/export behavior is backend-independent: `.chronicle` CLI/API archive operations continue to use the canonical archive pipeline and do not require `ChronicleSession` query-surface parity.

## Backend parity and onboarding gates

Use these scripts for convergence/release criteria:

```bash
PYTHONPATH=. python3 scripts/postgres_backend_parity.py --database-url "$CHRONICLE_POSTGRES_URL"
PYTHONPATH=. python3 scripts/postgres_onboarding_timed_check.py --database-url "$CHRONICLE_POSTGRES_URL"
```

- `postgres_backend_parity.py` seeds a deterministic SQLite scenario, replays the same event stream into Postgres, and compares canonical defensibility scorecards claim-by-claim.
- `postgres_onboarding_timed_check.py` runs doctor + smoke and fails if required steps fail or total elapsed time exceeds 10 minutes (configurable).

The active implementation plan and release criteria live in [to_do](to_do.md#active-convergence-program-public--ci--postgres).

Operational references:

- Backup/restore + disaster recovery: [Postgres operations runbook](postgres-operations-runbook.md)
- Managed environment security posture: [Managed Postgres hardening](postgres-hardening.md)
