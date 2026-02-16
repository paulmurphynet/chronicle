-- Event store and schema version. Spec Section 14.2.1, 14.4.15.

CREATE TABLE IF NOT EXISTS events (
  event_id            TEXT PRIMARY KEY,
  event_type          TEXT NOT NULL,
  occurred_at         TEXT NOT NULL,
  recorded_at         TEXT NOT NULL,
  investigation_uid   TEXT NOT NULL,
  subject_uid         TEXT NOT NULL,
  actor_type          TEXT NOT NULL,
  actor_id            TEXT NOT NULL,
  workspace           TEXT NOT NULL,
  policy_profile_id   TEXT NULL,
  correlation_id      TEXT NULL,
  causation_id        TEXT NULL,
  envelope_version    INTEGER NOT NULL DEFAULT 1,
  payload_version     INTEGER NOT NULL DEFAULT 1,
  payload             TEXT NOT NULL,
  idempotency_key     TEXT NULL,
  prev_event_hash     TEXT NULL,
  event_hash          TEXT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_recorded_at ON events (recorded_at);
CREATE INDEX IF NOT EXISTS idx_events_occurred_at ON events (occurred_at);
CREATE INDEX IF NOT EXISTS idx_events_investigation ON events (investigation_uid);
CREATE INDEX IF NOT EXISTS idx_events_subject_uid ON events (subject_uid);
CREATE INDEX IF NOT EXISTS idx_events_type_time ON events (event_type, recorded_at);
CREATE INDEX IF NOT EXISTS idx_events_correlation ON events (correlation_id);
CREATE INDEX IF NOT EXISTS idx_events_investigation_type ON events (investigation_uid, event_type);

CREATE TABLE IF NOT EXISTS schema_version (
  component            TEXT PRIMARY KEY,
  version              INTEGER NOT NULL,
  updated_at           TEXT NOT NULL,
  notes                TEXT NULL
);
