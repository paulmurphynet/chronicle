# PostgreSQL backend (convergence track)

Chronicle includes a PostgreSQL **event-store** implementation today and is actively converging toward broader backend parity.

Current scope:

- PostgreSQL event-store append/read is available via `chronicle/store/postgres_event_store.py`.
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

## Important limitation (current)

Postgres read model is not yet parity-complete. Queries and projections for claims/defensibility/tensions remain SQLite-first in the current runtime path.

The active implementation plan and release criteria live in [to_do](to_do.md#active-convergence-program-public--ci--postgres).

Operational references:

- Backup/restore + disaster recovery: [Postgres operations runbook](postgres-operations-runbook.md)
- Managed environment security posture: [Managed Postgres hardening](postgres-hardening.md)
