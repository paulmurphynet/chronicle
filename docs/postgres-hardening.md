# Managed Postgres Hardening Guide

Use this guide when running Chronicle against managed Postgres providers.

## 1) Enforce TLS

Require encrypted transport in all environments outside local development.

- Connection URL should include `sslmode=require` (or provider equivalent).
- Reject plaintext DB connections at network and parameter-group level where possible.

Example:

```bash
export CHRONICLE_POSTGRES_URL="postgresql://chronicle_app:***@db.example.com:5432/chronicle?sslmode=require"
```

## 2) Least-privilege roles

Create separate roles for runtime and operations:

1. `chronicle_app`:
   - `CONNECT`
   - `USAGE` on schema
   - `SELECT/INSERT/UPDATE/DELETE` on Chronicle tables
   - No `CREATEDB`, `CREATEROLE`, or superuser privileges
2. `chronicle_ops`:
   - Elevated rights for migrations/maintenance only
   - Not used by app runtime

## 3) Credential management and rotation

- Store DB credentials in a secret manager (not committed files).
- Rotate DB passwords/credentials on a fixed cadence (for example every 90 days) and on incident.
- Use dual-credential rotation (introduce new secret, deploy, revoke old secret).

## 4) Network controls

- Restrict inbound access to known app runners and admin networks.
- Disable broad CIDR allowlists (`0.0.0.0/0`) in production.
- Prefer private networking options from the managed provider.

## 5) Monitoring and alerting

Track and alert on:

- Failed authentication spikes
- Connection saturation
- Replication/storage health (if configured)
- Abnormal statement latency or error rates

## 6) Change safety

- Apply schema changes in staging first.
- Keep backup/restore runbook current and tested.
- Run `scripts/postgres_doctor.py` and `scripts/postgres_smoke.py` after config or credential changes.

## 7) Release sign-off checklist

Before release using managed Postgres:

1. TLS enforced
2. Least-privilege roles verified
3. Secrets rotation date within policy
4. Backup/restore drill date within policy
5. Postgres doctor/smoke checks passing
