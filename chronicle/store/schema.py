"""Schema initialization: event store, schema_version, read model tables.

On first init (create_project or first open of chronicle.db), all schema_version rows
(event_store, read_model, project_format) are written. Rebuild logic (Phase 11) can
therefore assume the table and version rows exist for both new and migrated projects.
"""

import sqlite3
from datetime import UTC, datetime

EVENT_STORE_VERSION = 2
READ_MODEL_VERSION = 1
PROJECT_FORMAT_VERSION = 1

EVENTS_DDL = """
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
CREATE INDEX IF NOT EXISTS idx_events_idempotency_key ON events (idempotency_key) WHERE idempotency_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS schema_version (
  component            TEXT PRIMARY KEY,
  version              INTEGER NOT NULL,
  updated_at           TEXT NOT NULL,
  notes                TEXT NULL
);
"""

READ_MODEL_DDL = """
CREATE TABLE IF NOT EXISTS investigation (
  investigation_uid    TEXT PRIMARY KEY,
  title                TEXT NOT NULL,
  description          TEXT NULL,
  created_at           TEXT NOT NULL,
  created_by_actor_id  TEXT NOT NULL,
  tags_json            TEXT NULL,
  is_archived          INTEGER NOT NULL DEFAULT 0,
  updated_at           TEXT NOT NULL,
  current_tier         TEXT NOT NULL DEFAULT 'spark',
  tier_changed_at      TEXT NULL
);

CREATE TABLE IF NOT EXISTS processed_event (
  projection_name  TEXT NOT NULL,
  event_id         TEXT NOT NULL,
  processed_at     TEXT NOT NULL,
  PRIMARY KEY (projection_name, event_id)
);

CREATE TABLE IF NOT EXISTS evidence_item (
  evidence_uid         TEXT PRIMARY KEY,
  investigation_uid    TEXT NOT NULL,
  created_at           TEXT NOT NULL,
  ingested_by_actor_id TEXT NOT NULL,
  content_hash         TEXT NOT NULL,
  file_size_bytes      INTEGER NOT NULL,
  original_filename    TEXT NOT NULL,
  uri                  TEXT NOT NULL,
  media_type           TEXT NOT NULL,
  extraction_version   TEXT NULL,
  file_metadata_json   TEXT NULL,
  metadata_json        TEXT NULL,
  integrity_status     TEXT NOT NULL DEFAULT 'UNVERIFIED',
  last_verified_at      TEXT NULL,
  updated_at           TEXT NOT NULL,
  redaction_reason     TEXT NULL,
  redaction_at         TEXT NULL,
  reviewed_at          TEXT NULL,
  reviewed_by_actor_id TEXT NULL
);
CREATE INDEX IF NOT EXISTS idx_evidence_investigation ON evidence_item (investigation_uid);
CREATE INDEX IF NOT EXISTS idx_evidence_hash ON evidence_item (content_hash);
CREATE INDEX IF NOT EXISTS idx_evidence_media ON evidence_item (media_type);
CREATE INDEX IF NOT EXISTS idx_evidence_integrity ON evidence_item (integrity_status);

CREATE TABLE IF NOT EXISTS tier_history (
  investigation_uid    TEXT NOT NULL,
  from_tier            TEXT NOT NULL,
  to_tier              TEXT NOT NULL,
  reason               TEXT NULL,
  occurred_at          TEXT NOT NULL,
  actor_id             TEXT NOT NULL,
  event_id             TEXT NOT NULL,
  PRIMARY KEY (investigation_uid, event_id)
);
CREATE INDEX IF NOT EXISTS idx_tier_history_investigation ON tier_history (investigation_uid);
"""

# claim table must exist before evidence_link (FK). Phase 3.2; needed for Phase 2.
CLAIM_DDL = """
CREATE TABLE IF NOT EXISTS claim (
  claim_uid            TEXT PRIMARY KEY,
  investigation_uid    TEXT NOT NULL,
  created_at           TEXT NOT NULL,
  created_by_actor_id  TEXT NOT NULL,
  claim_text           TEXT NOT NULL,
  claim_type           TEXT NULL,
  scope_json           TEXT NULL,
  temporal_json        TEXT NULL,
  current_status       TEXT NOT NULL DEFAULT 'ACTIVE',
  language             TEXT NULL,
  tags_json            TEXT NULL,
  notes                TEXT NULL,
  parent_claim_uid     TEXT NULL,
  decomposition_status TEXT NOT NULL DEFAULT 'unanalyzed',
  updated_at           TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_claim_investigation ON claim (investigation_uid);
CREATE INDEX IF NOT EXISTS idx_claim_type ON claim (claim_type);
CREATE INDEX IF NOT EXISTS idx_claim_parent ON claim (parent_claim_uid);
"""

# FTS5 virtual table for claim full-text search. Phase 8.
CLAIM_FTS_DDL = """
CREATE VIRTUAL TABLE IF NOT EXISTS claim_fts USING fts5(
  claim_uid UNINDEXED,
  claim_text,
  tokenize='unicode61'
);
CREATE TRIGGER IF NOT EXISTS claim_fts_insert AFTER INSERT ON claim BEGIN
  INSERT INTO claim_fts(claim_uid, claim_text) VALUES (new.claim_uid, new.claim_text);
END;
CREATE TRIGGER IF NOT EXISTS claim_fts_update AFTER UPDATE OF claim_text ON claim
  WHEN old.claim_text IS NOT new.claim_text BEGIN
  DELETE FROM claim_fts WHERE claim_uid = old.claim_uid;
  INSERT INTO claim_fts(claim_uid, claim_text) VALUES (new.claim_uid, new.claim_text);
END;
CREATE TRIGGER IF NOT EXISTS claim_fts_delete AFTER DELETE ON claim BEGIN
  DELETE FROM claim_fts WHERE claim_uid = old.claim_uid;
END;
"""

EVIDENCE_SPAN_DDL = """
CREATE TABLE IF NOT EXISTS evidence_span (
  span_uid             TEXT PRIMARY KEY,
  evidence_uid         TEXT NOT NULL REFERENCES evidence_item (evidence_uid),
  anchor_type          TEXT NOT NULL,
  anchor_json          TEXT NOT NULL,
  created_at           TEXT NOT NULL,
  created_by_actor_id  TEXT NOT NULL,
  source_event_id      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_span_evidence ON evidence_span (evidence_uid);
CREATE INDEX IF NOT EXISTS idx_span_anchor_type ON evidence_span (anchor_type);
"""

EVIDENCE_LINK_DDL = """
CREATE TABLE IF NOT EXISTS evidence_link (
  link_uid             TEXT PRIMARY KEY,
  claim_uid            TEXT NOT NULL REFERENCES claim (claim_uid),
  span_uid             TEXT NOT NULL REFERENCES evidence_span (span_uid),
  link_type            TEXT NOT NULL,
  strength             REAL NULL,
  notes                TEXT NULL,
  created_at           TEXT NOT NULL,
  created_by_actor_id  TEXT NOT NULL,
  source_event_id      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_link_claim ON evidence_link (claim_uid);
CREATE INDEX IF NOT EXISTS idx_link_span ON evidence_link (span_uid);
"""

# Phase 3 (Epistemology): retracted links are excluded from defensibility and link queries; full history in events.
EVIDENCE_LINK_RETRACTION_DDL = """
CREATE TABLE IF NOT EXISTS evidence_link_retraction (
  link_uid      TEXT PRIMARY KEY REFERENCES evidence_link (link_uid),
  retracted_at  TEXT NOT NULL,
  rationale     TEXT NULL
);
"""

CLAIM_ASSERTION_DDL = """
CREATE TABLE IF NOT EXISTS claim_assertion (
  assertion_uid        TEXT PRIMARY KEY,
  claim_uid            TEXT NOT NULL REFERENCES claim (claim_uid),
  asserted_at          TEXT NOT NULL,
  actor_type           TEXT NOT NULL,
  actor_id             TEXT NOT NULL,
  assertion_mode       TEXT NOT NULL,
  confidence           REAL NULL,
  justification        TEXT NULL,
  source_event_id      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_assertion_claim ON claim_assertion (claim_uid);
CREATE INDEX IF NOT EXISTS idx_assertion_actor ON claim_assertion (actor_id);
"""

TENSION_DDL = """
CREATE TABLE IF NOT EXISTS tension (
  tension_uid          TEXT PRIMARY KEY,
  investigation_uid    TEXT NOT NULL,
  claim_a_uid          TEXT NOT NULL REFERENCES claim (claim_uid),
  claim_b_uid          TEXT NOT NULL REFERENCES claim (claim_uid),
  tension_kind         TEXT NULL,
  status               TEXT NOT NULL DEFAULT 'OPEN',
  notes                TEXT NULL,
  created_at           TEXT NOT NULL,
  created_by_actor_id  TEXT NOT NULL,
  source_event_id      TEXT NOT NULL,
  updated_at           TEXT NOT NULL,
  assigned_to          TEXT NULL,
  due_date             TEXT NULL,
  remediation_type     TEXT NULL
);
CREATE INDEX IF NOT EXISTS idx_tension_investigation ON tension (investigation_uid);
CREATE INDEX IF NOT EXISTS idx_tension_a ON tension (claim_a_uid);
CREATE INDEX IF NOT EXISTS idx_tension_b ON tension (claim_b_uid);
CREATE INDEX IF NOT EXISTS idx_tension_status ON tension (status);
"""

# Phase 7 (AI): tension_suggestion — pending suggestions; confirm -> DeclareTension, dismiss -> TensionSuggestionDismissed
TENSION_SUGGESTION_DDL = """
CREATE TABLE IF NOT EXISTS tension_suggestion (
  suggestion_uid         TEXT PRIMARY KEY,
  investigation_uid      TEXT NOT NULL,
  claim_a_uid            TEXT NOT NULL,
  claim_b_uid            TEXT NOT NULL,
  suggested_tension_kind TEXT NOT NULL,
  confidence             REAL NOT NULL,
  rationale              TEXT NOT NULL,
  status                 TEXT NOT NULL DEFAULT 'pending',
  tool_module_id         TEXT NULL,
  created_at             TEXT NOT NULL,
  source_event_id        TEXT NOT NULL,
  updated_at             TEXT NOT NULL,
  confirmed_tension_uid  TEXT NULL,
  dismissed_at           TEXT NULL
);
CREATE INDEX IF NOT EXISTS idx_tension_suggestion_investigation ON tension_suggestion (investigation_uid);
CREATE INDEX IF NOT EXISTS idx_tension_suggestion_status ON tension_suggestion (status);
"""

# Phase 5: claim_decomposition (14.4.9), evidence_supersession (14.4.7)
CLAIM_DECOMPOSITION_DDL = """
CREATE TABLE IF NOT EXISTS claim_decomposition (
  analysis_uid         TEXT PRIMARY KEY,
  claim_uid            TEXT NOT NULL REFERENCES claim (claim_uid),
  is_atomic            INTEGER NOT NULL,
  overall_confidence   REAL NULL,
  analysis_rationale   TEXT NULL,
  suggested_splits     TEXT NOT NULL,
  analyzed_at          TEXT NOT NULL,
  analyzer_module_id   TEXT NOT NULL,
  analyzer_version     TEXT NOT NULL,
  run_id               TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_decomposition_claim ON claim_decomposition (claim_uid);
"""

EVIDENCE_SUPERSESSION_DDL = """
CREATE TABLE IF NOT EXISTS evidence_supersession (
  supersession_uid     TEXT PRIMARY KEY,
  new_evidence_uid     TEXT NOT NULL REFERENCES evidence_item (evidence_uid),
  prior_evidence_uid   TEXT NOT NULL REFERENCES evidence_item (evidence_uid),
  supersession_type    TEXT NOT NULL,
  reason               TEXT NULL,
  created_at           TEXT NOT NULL,
  created_by_actor_id  TEXT NOT NULL,
  source_event_id      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_supersession_prior ON evidence_supersession (prior_evidence_uid);
"""

# Phase 6: source (14.4.11), evidence_source_link (14.4.12)
# Phase 2 (Epistemology): independence_notes — optional rationale for treating source as independent (e.g. different institution)
SOURCE_DDL = """
CREATE TABLE IF NOT EXISTS source (
  source_uid           TEXT PRIMARY KEY,
  investigation_uid   TEXT NOT NULL,
  display_name        TEXT NOT NULL,
  source_type         TEXT NOT NULL,
  alias               TEXT NULL,
  encrypted_identity  TEXT NULL,
  notes               TEXT NULL,
  independence_notes   TEXT NULL,
  created_at          TEXT NOT NULL,
  created_by_actor_id TEXT NOT NULL,
  updated_at           TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_source_investigation ON source (investigation_uid);
"""

EVIDENCE_SOURCE_LINK_DDL = """
CREATE TABLE IF NOT EXISTS evidence_source_link (
  evidence_uid        TEXT NOT NULL REFERENCES evidence_item (evidence_uid),
  source_uid          TEXT NOT NULL REFERENCES source (source_uid),
  relationship        TEXT NULL,
  created_at          TEXT NOT NULL,
  source_event_id     TEXT NOT NULL,
  PRIMARY KEY (evidence_uid, source_uid)
);
CREATE INDEX IF NOT EXISTS idx_evidence_source_source ON evidence_source_link (source_uid);
"""

# Evidence trust assessments: pluggable provider results per evidence. Spec 14.6.3, evidence-trust-assessments.md.
EVIDENCE_TRUST_ASSESSMENT_DDL = """
CREATE TABLE IF NOT EXISTS evidence_trust_assessment (
  evidence_uid        TEXT NOT NULL REFERENCES evidence_item (evidence_uid),
  provider_id         TEXT NOT NULL,
  assessment_kind     TEXT NOT NULL,
  result              TEXT NOT NULL,
  assessed_at         TEXT NOT NULL,
  result_expires_at   TEXT NULL,
  metadata            TEXT NULL,
  source_event_id     TEXT NOT NULL,
  PRIMARY KEY (evidence_uid, provider_id, assessment_kind)
);
CREATE INDEX IF NOT EXISTS idx_evidence_trust_assessment_evidence ON evidence_trust_assessment (evidence_uid);
CREATE INDEX IF NOT EXISTS idx_evidence_trust_assessment_kind ON evidence_trust_assessment (evidence_uid, assessment_kind);
"""

# Phase 8: artifact (14.4.13), checkpoint (14.4.14), checkpoint_artifact_freeze
ARTIFACT_DDL = """
CREATE TABLE IF NOT EXISTS artifact (
  artifact_uid         TEXT PRIMARY KEY,
  investigation_uid    TEXT NOT NULL,
  artifact_type        TEXT NULL,
  title                TEXT NULL,
  created_at           TEXT NOT NULL,
  created_by_actor_id  TEXT NOT NULL,
  notes                TEXT NULL,
  updated_at           TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_artifact_investigation ON artifact (investigation_uid);
"""

CHECKPOINT_DDL = """
CREATE TABLE IF NOT EXISTS checkpoint (
  checkpoint_uid       TEXT PRIMARY KEY,
  investigation_uid   TEXT NOT NULL,
  scope_refs_json     TEXT NULL,
  artifact_refs_json  TEXT NULL,
  reason              TEXT NULL,
  created_at          TEXT NOT NULL,
  created_by_actor_id TEXT NOT NULL,
  policy_summary      TEXT NULL
);
CREATE INDEX IF NOT EXISTS idx_checkpoint_investigation ON checkpoint (investigation_uid);
"""

CHECKPOINT_ARTIFACT_FREEZE_DDL = """
CREATE TABLE IF NOT EXISTS checkpoint_artifact_freeze (
  checkpoint_uid       TEXT NOT NULL REFERENCES checkpoint (checkpoint_uid),
  artifact_uid         TEXT NOT NULL REFERENCES artifact (artifact_uid),
  claim_refs_json      TEXT NULL,
  evidence_refs_json   TEXT NULL,
  tension_refs_json   TEXT NULL,
  created_at           TEXT NOT NULL,
  source_event_id      TEXT NOT NULL,
  PRIMARY KEY (checkpoint_uid, artifact_uid)
);
CREATE INDEX IF NOT EXISTS idx_freeze_artifact ON checkpoint_artifact_freeze (artifact_uid);
"""

# Phase 2: suggestion_dismissal — record when user dismisses an AI suggestion (with optional rationale).
SUGGESTION_DISMISSAL_DDL = """
CREATE TABLE IF NOT EXISTS suggestion_dismissal (
  event_id             TEXT PRIMARY KEY,
  investigation_uid    TEXT NOT NULL,
  suggestion_type      TEXT NOT NULL,
  suggestion_ref       TEXT NOT NULL,
  claim_uid            TEXT NULL,
  rationale            TEXT NULL,
  dismissed_at         TEXT NOT NULL,
  actor_id             TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_suggestion_dismissal_investigation ON suggestion_dismissal (investigation_uid);
CREATE INDEX IF NOT EXISTS idx_suggestion_dismissal_type ON suggestion_dismissal (suggestion_type);
"""

# Optional vector projection: claim embeddings for semantic similarity. VECTOR_PROJECTION.md.
CLAIM_EMBEDDING_DDL = """
CREATE TABLE IF NOT EXISTS claim_embedding (
  claim_uid    TEXT PRIMARY KEY,
  embedding    BLOB NOT NULL,
  updated_at   TEXT NOT NULL
);
"""

PROJECTION_NAME_READ_MODEL = "read_model"

# Read model tables in reverse dependency order for truncate (FK-safe). Spec 15.3.
READ_MODEL_TABLES_TRUNCATE_ORDER = [
    "processed_event",
    "suggestion_dismissal",
    "tier_history",
    "checkpoint_artifact_freeze",
    "evidence_link_retraction",
    "evidence_link",
    "claim_assertion",
    "claim_decomposition",
    "tension_suggestion",
    "tension",
    "evidence_source_link",
    "evidence_trust_assessment",
    "evidence_supersession",
    "evidence_span",
    "claim",
    "claim_fts",
    "evidence_item",
    "source",
    "artifact",
    "checkpoint",
    "investigation",
]


def ensure_investigation_tier_columns(conn: sqlite3.Connection) -> None:
    """Add current_tier and tier_changed_at to investigation if missing (Phase 1 migration)."""
    cur = conn.execute("PRAGMA table_info(investigation)")
    columns = [row[1] for row in cur.fetchall()]
    if "current_tier" not in columns:
        conn.execute(
            "ALTER TABLE investigation ADD COLUMN current_tier TEXT NOT NULL DEFAULT 'spark'"
        )
    if "tier_changed_at" not in columns:
        conn.execute("ALTER TABLE investigation ADD COLUMN tier_changed_at TEXT NULL")
    conn.commit()


def ensure_tension_exception_columns(conn: sqlite3.Connection) -> None:
    """Phase 11: add exception workflow columns to tension if missing (migration)."""
    cur = conn.execute("PRAGMA table_info(tension)")
    columns = [row[1] for row in cur.fetchall()]
    if "assigned_to" not in columns:
        conn.execute("ALTER TABLE tension ADD COLUMN assigned_to TEXT NULL")
    if "due_date" not in columns:
        conn.execute("ALTER TABLE tension ADD COLUMN due_date TEXT NULL")
    if "remediation_type" not in columns:
        conn.execute("ALTER TABLE tension ADD COLUMN remediation_type TEXT NULL")
    conn.commit()


def ensure_source_independence_notes_column(conn: sqlite3.Connection) -> None:
    """Phase 2 (Epistemology): add independence_notes to source if missing (migration)."""
    cur = conn.execute("PRAGMA table_info(source)")
    columns = [row[1] for row in cur.fetchall()]
    if "independence_notes" not in columns:
        conn.execute("ALTER TABLE source ADD COLUMN independence_notes TEXT NULL")
    conn.commit()


def ensure_evidence_redaction_columns(conn: sqlite3.Connection) -> None:
    """Phase C.1: add redaction_reason and redaction_at to evidence_item if missing (migration)."""
    cur = conn.execute("PRAGMA table_info(evidence_item)")
    columns = [row[1] for row in cur.fetchall()]
    if "redaction_reason" not in columns:
        conn.execute("ALTER TABLE evidence_item ADD COLUMN redaction_reason TEXT NULL")
    if "redaction_at" not in columns:
        conn.execute("ALTER TABLE evidence_item ADD COLUMN redaction_at TEXT NULL")
    conn.commit()


def ensure_evidence_reviewed_columns(conn: sqlite3.Connection) -> None:
    """Phase D.2: add reviewed_at and reviewed_by_actor_id to evidence_item if missing (migration)."""
    cur = conn.execute("PRAGMA table_info(evidence_item)")
    columns = [row[1] for row in cur.fetchall()]
    if "reviewed_at" not in columns:
        conn.execute("ALTER TABLE evidence_item ADD COLUMN reviewed_at TEXT NULL")
    if "reviewed_by_actor_id" not in columns:
        conn.execute("ALTER TABLE evidence_item ADD COLUMN reviewed_by_actor_id TEXT NULL")
    conn.commit()


def ensure_evidence_provenance_column(conn: sqlite3.Connection) -> None:
    """E2.3: add provenance_type to evidence_item if missing (human_created | ai_generated | unknown)."""
    cur = conn.execute("PRAGMA table_info(evidence_item)")
    columns = [row[1] for row in cur.fetchall()]
    if "provenance_type" not in columns:
        conn.execute("ALTER TABLE evidence_item ADD COLUMN provenance_type TEXT NULL")
    conn.commit()


def ensure_checkpoint_policy_summary_column(conn: sqlite3.Connection) -> None:
    """Phase A (Verticals additive): add policy_summary to checkpoint if missing (migration)."""
    cur = conn.execute("PRAGMA table_info(checkpoint)")
    columns = [row[1] for row in cur.fetchall()]
    if "policy_summary" not in columns:
        conn.execute("ALTER TABLE checkpoint ADD COLUMN policy_summary TEXT NULL")
    conn.commit()


def ensure_checkpoint_certification_columns(conn: sqlite3.Connection) -> None:
    """E5.3: add certifying_org_id and certified_at to checkpoint if missing (epistemic credentials)."""
    cur = conn.execute("PRAGMA table_info(checkpoint)")
    columns = [row[1] for row in cur.fetchall()]
    if "certifying_org_id" not in columns:
        conn.execute("ALTER TABLE checkpoint ADD COLUMN certifying_org_id TEXT NULL")
    if "certified_at" not in columns:
        conn.execute("ALTER TABLE checkpoint ADD COLUMN certified_at TEXT NULL")
    conn.commit()


def run_read_model_ddl_only(conn: sqlite3.Connection) -> None:
    """Create read model tables if not exist. Does not write schema_version. For standalone use or before rebuild."""
    conn.executescript(READ_MODEL_DDL)
    ensure_investigation_tier_columns(conn)
    conn.executescript(CLAIM_DDL)
    conn.executescript(CLAIM_FTS_DDL)
    # Backfill FTS only when empty (e.g. existing DB upgraded to add FTS); triggers handle new claims
    if conn.execute("SELECT COUNT(*) FROM claim_fts").fetchone()[0] == 0:
        conn.execute(
            "INSERT INTO claim_fts(claim_uid, claim_text) SELECT claim_uid, claim_text FROM claim"
        )
    conn.executescript(EVIDENCE_SPAN_DDL)
    conn.executescript(EVIDENCE_LINK_DDL)
    conn.executescript(EVIDENCE_LINK_RETRACTION_DDL)
    ensure_evidence_redaction_columns(conn)
    ensure_evidence_reviewed_columns(conn)
    ensure_evidence_provenance_column(conn)
    conn.executescript(CLAIM_ASSERTION_DDL)
    conn.executescript(TENSION_DDL)
    ensure_tension_exception_columns(conn)
    conn.executescript(TENSION_SUGGESTION_DDL)
    conn.executescript(CLAIM_DECOMPOSITION_DDL)
    conn.executescript(EVIDENCE_SUPERSESSION_DDL)
    conn.executescript(SOURCE_DDL)
    ensure_source_independence_notes_column(conn)
    conn.executescript(EVIDENCE_SOURCE_LINK_DDL)
    conn.executescript(EVIDENCE_TRUST_ASSESSMENT_DDL)
    conn.executescript(ARTIFACT_DDL)
    conn.executescript(CHECKPOINT_DDL)
    ensure_checkpoint_policy_summary_column(conn)
    ensure_checkpoint_certification_columns(conn)
    conn.executescript(CHECKPOINT_ARTIFACT_FREEZE_DDL)
    conn.executescript(SUGGESTION_DISMISSAL_DDL)
    conn.executescript(CLAIM_EMBEDDING_DDL)
    conn.commit()


def init_event_store_schema(conn: sqlite3.Connection) -> None:
    """Create events table and indexes; ensure schema_version row for event_store."""
    conn.executescript(EVENTS_DDL)
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        """
        INSERT OR IGNORE INTO schema_version (component, version, updated_at, notes)
        VALUES ('event_store', ?, ?, 'Initial event store schema')
        """,
        (EVENT_STORE_VERSION, now),
    )
    conn.commit()


def truncate_read_model_tables(conn: sqlite3.Connection) -> None:
    """Delete all rows from read model tables (keep events). Order respects FKs. Spec 15.3."""
    for table in READ_MODEL_TABLES_TRUNCATE_ORDER:
        conn.execute(f"DELETE FROM {table}")
    conn.commit()


def init_read_model_schema(conn: sqlite3.Connection) -> None:
    """Create read model tables and set schema_version. Use for first-time init only."""
    run_read_model_ddl_only(conn)
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        "INSERT OR REPLACE INTO schema_version (component, version, updated_at, notes) VALUES ('read_model', ?, ?, 'Initial read model')",
        (READ_MODEL_VERSION, now),
    )
    conn.execute(
        "INSERT OR REPLACE INTO schema_version (component, version, updated_at, notes) VALUES ('project_format', ?, ?, 'Initial project format')",
        (PROJECT_FORMAT_VERSION, now),
    )
    conn.commit()
