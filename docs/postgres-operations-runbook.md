# Postgres Operations Runbook

This runbook covers backup, restore, and disaster-recovery operations for Chronicle deployments that use Postgres.

## Scope

- Event-store backend in Postgres (`events`, `schema_version`)
- Chronicle application state that depends on this DB
- Managed providers (Neon/RDS/Azure/GCP) and self-managed Postgres

## Backup policy

Minimum baseline:

1. Daily full backup (`pg_dump` custom format)
2. Retention window: at least 14 days
3. Backup integrity hash recorded (`sha256sum`)
4. Quarterly restore drill into a non-production environment

Example backup command:

```bash
pg_dump "$CHRONICLE_POSTGRES_URL" --format=custom --no-owner --file /backups/chronicle_$(date +%F).dump
sha256sum /backups/chronicle_$(date +%F).dump > /backups/chronicle_$(date +%F).dump.sha256
```

## Restore procedure

1. Create target database (or empty recovery DB).
2. Restore from the selected backup:

```bash
createdb chronicle_restore_candidate
pg_restore --clean --if-exists --no-owner --dbname postgresql://USER:PASS@HOST:5432/chronicle_restore_candidate /backups/chronicle_YYYY-MM-DD.dump
```

3. Run Chronicle health checks against restored DB:

```bash
PYTHONPATH=. python3 scripts/postgres_doctor.py --database-url "postgresql://USER:PASS@HOST:5432/chronicle_restore_candidate"
PYTHONPATH=. python3 scripts/postgres_smoke.py --database-url "postgresql://USER:PASS@HOST:5432/chronicle_restore_candidate"
```

4. Validate expected investigation/event counts before cutover.
5. Cut over application only after validation is complete.

## Disaster recovery playbook

Trigger examples:

- Primary DB corruption
- Accidental destructive write
- Provider-region outage

Immediate actions:

1. Freeze write traffic to Chronicle.
2. Select recovery point (latest consistent backup or provider snapshot).
3. Restore to a recovery DB.
4. Run doctor/smoke checks.
5. Re-enable traffic after data validation and incident sign-off.

Post-incident:

1. Document root cause and timeline.
2. Record data-loss window (RPO) and recovery duration (RTO).
3. Update this runbook and alerts to reduce repeat risk.

## SQLite fallback note

If a deployment still uses SQLite for local workflows, back up `chronicle.db` and `evidence/` together with matching timestamps to preserve consistency.
