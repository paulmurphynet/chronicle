"""Event-to-read-model projection: handlers and apply_event. Spec 14.6.3."""

import json
import sqlite3
from collections.abc import Callable

from chronicle.core.events import (
    EVENT_ARTIFACT_CREATED,
    EVENT_ARTIFACT_VERSION_FROZEN,
    EVENT_CHAIN_OF_CUSTODY_REPORT_GENERATED,
    EVENT_CHALLENGE_LINKED,
    EVENT_CHALLENGE_RETRACTED,
    EVENT_CHECKPOINT_CREATED,
    EVENT_CLAIM_ASSERTED,
    EVENT_CLAIM_DECOMPOSITION_ANALYZED,
    EVENT_CLAIM_DOWNGRADED,
    EVENT_CLAIM_PROMOTED_TO_SEF,
    EVENT_CLAIM_PROPOSED,
    EVENT_CLAIM_SCOPED,
    EVENT_CLAIM_TEMPORALIZED,
    EVENT_CLAIM_TYPED,
    EVENT_CLAIM_WITHDRAWN,
    EVENT_EVIDENCE_INGESTED,
    EVENT_EVIDENCE_INTEGRITY_VERIFIED,
    EVENT_EVIDENCE_MARKED_REVIEWED,
    EVENT_EVIDENCE_REDACTION_RECORDED,
    EVENT_EVIDENCE_SOURCE_LINKED,
    EVENT_EVIDENCE_SUPERSEDED,
    EVENT_EVIDENCE_TRUST_ASSESSMENT_RECORDED,
    EVENT_INVESTIGATION_ARCHIVED,
    EVENT_INVESTIGATION_CREATED,
    EVENT_SOURCE_INDEPENDENCE_NOTES_RECORDED,
    EVENT_SOURCE_REGISTERED,
    EVENT_SPAN_ANCHORED,
    EVENT_SUGGESTION_DISMISSED,
    EVENT_SUPPORT_LINKED,
    EVENT_SUPPORT_RETRACTED,
    EVENT_TENSION_DECLARED,
    EVENT_TENSION_EXCEPTION_UPDATED,
    EVENT_TENSION_STATUS_UPDATED,
    EVENT_TENSION_SUGGESTED,
    EVENT_TENSION_SUGGESTION_DISMISSED,
    EVENT_TIER_CHANGED,
    Event,
)
from chronicle.store.schema import PROJECTION_NAME_READ_MODEL

# Registry: event_type -> (conn, event) -> None. Add new event types here instead of extending apply_event.
EventProjectionHandler = Callable[[sqlite3.Connection, Event], None]
EVENT_HANDLERS: dict[str, EventProjectionHandler] = {}


def handle_investigation_created(conn: sqlite3.Connection, event: Event) -> None:
    """Projection handler: InvestigationCreated -> upsert investigation."""
    payload = event.payload
    inv_uid = payload["investigation_uid"]
    title = payload["title"]
    description = payload.get("description")
    created_by = payload.get("created_by") or {}
    created_by_actor_id = created_by.get("actor_id", event.actor_id)
    tags = payload.get("tags")
    tags_json = json.dumps(tags) if tags is not None else None
    now = event.recorded_at
    conn.execute(
        """
        INSERT INTO investigation (
            investigation_uid, title, description, created_at, created_by_actor_id,
            tags_json, is_archived, updated_at, current_tier, tier_changed_at
        ) VALUES (?, ?, ?, ?, ?, ?, 0, ?, 'spark', NULL)
        ON CONFLICT(investigation_uid) DO UPDATE SET
            title = excluded.title,
            description = excluded.description,
            updated_at = excluded.updated_at,
            tags_json = excluded.tags_json
        """,
        (inv_uid, title, description, now, created_by_actor_id, tags_json, now),
    )
    conn.execute(
        "INSERT OR IGNORE INTO processed_event (projection_name, event_id, processed_at) VALUES (?, ?, ?)",
        (PROJECTION_NAME_READ_MODEL, event.event_id, now),
    )


def handle_investigation_archived(conn: sqlite3.Connection, event: Event) -> None:
    """Projection: InvestigationArchived -> set investigation.is_archived = 1. Spec 14.6.3."""
    payload = event.payload
    inv_uid = payload["investigation_uid"]
    now = event.recorded_at
    conn.execute(
        "UPDATE investigation SET is_archived = 1, updated_at = ? WHERE investigation_uid = ?",
        (now, inv_uid),
    )
    conn.execute(
        "INSERT OR IGNORE INTO processed_event (projection_name, event_id, processed_at) VALUES (?, ?, ?)",
        (PROJECTION_NAME_READ_MODEL, event.event_id, now),
    )


def handle_tier_changed(conn: sqlite3.Connection, event: Event) -> None:
    """Projection: TierChanged -> update investigation current_tier, tier_changed_at; append tier_history. Phase 1."""
    payload = event.payload
    inv_uid = payload["investigation_uid"]
    from_tier = payload["from_tier"]
    to_tier = payload["to_tier"]
    reason = payload.get("reason")
    changed_by = payload.get("changed_by") or {}
    actor_id = changed_by.get("actor_id", event.actor_id)
    now = event.recorded_at
    conn.execute(
        "UPDATE investigation SET current_tier = ?, tier_changed_at = ?, updated_at = ? WHERE investigation_uid = ?",
        (to_tier, now, now, inv_uid),
    )
    conn.execute(
        """INSERT INTO tier_history (investigation_uid, from_tier, to_tier, reason, occurred_at, actor_id, event_id)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (inv_uid, from_tier, to_tier, reason, now, actor_id, event.event_id),
    )
    conn.execute(
        "INSERT OR IGNORE INTO processed_event (projection_name, event_id, processed_at) VALUES (?, ?, ?)",
        (PROJECTION_NAME_READ_MODEL, event.event_id, now),
    )


def handle_evidence_ingested(conn: sqlite3.Connection, event: Event) -> None:
    """Projection handler: EvidenceIngested -> upsert evidence_item. Spec 14.6.3."""
    payload = event.payload
    evidence_uid = payload["evidence_uid"]
    investigation_uid = event.investigation_uid
    created_at = payload.get("ingest_timestamp", event.recorded_at)
    ingested_by_actor_id = event.actor_id
    content_hash = payload["content_hash"]
    file_size_bytes = payload["file_size_bytes"]
    original_filename = payload["original_filename"]
    uri = payload["uri"]
    media_type = payload["media_type"]
    extraction_version = payload.get("extraction_version")
    file_metadata = payload.get("file_metadata")
    file_metadata_json = json.dumps(file_metadata) if file_metadata is not None else None
    metadata = payload.get("metadata")
    metadata_json = json.dumps(metadata) if metadata is not None else None
    provenance_type = payload.get("provenance_type") or "unknown"  # E2.3
    integrity_status = "UNVERIFIED"
    last_verified_at = None
    conn.execute(
        """
        INSERT INTO evidence_item (
            evidence_uid, investigation_uid, created_at, ingested_by_actor_id,
            content_hash, file_size_bytes, original_filename, uri, media_type,
            extraction_version, file_metadata_json, metadata_json,
            provenance_type, integrity_status, last_verified_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(evidence_uid) DO UPDATE SET
            content_hash = excluded.content_hash,
            file_size_bytes = excluded.file_size_bytes,
            original_filename = excluded.original_filename,
            uri = excluded.uri,
            media_type = excluded.media_type,
            extraction_version = excluded.extraction_version,
            file_metadata_json = excluded.file_metadata_json,
            metadata_json = excluded.metadata_json,
            provenance_type = excluded.provenance_type,
            updated_at = excluded.updated_at
        """,
        (
            evidence_uid,
            investigation_uid,
            created_at,
            ingested_by_actor_id,
            content_hash,
            file_size_bytes,
            original_filename,
            uri,
            media_type,
            extraction_version,
            file_metadata_json,
            metadata_json,
            provenance_type,
            integrity_status,
            last_verified_at,
            created_at,
        ),
    )
    conn.execute(
        "INSERT OR IGNORE INTO processed_event (projection_name, event_id, processed_at) VALUES (?, ?, ?)",
        (PROJECTION_NAME_READ_MODEL, event.event_id, created_at),
    )


def handle_claim_proposed(conn: sqlite3.Connection, event: Event) -> None:
    """Projection handler: ClaimProposed -> upsert claim. Spec 14.6.3."""
    payload = event.payload
    claim_uid = payload["claim_uid"]
    investigation_uid = event.investigation_uid
    created_at = event.recorded_at
    created_by = payload.get("created_by") or {}
    created_by_actor_id = created_by.get("actor_id", event.actor_id)
    claim_text = payload["claim_text"]
    claim_type = payload.get("initial_type")
    scope_json = None
    temporal_json = None
    current_status = "ACTIVE"
    language = payload.get("language")
    tags = payload.get("tags")
    tags_json = json.dumps(tags) if tags is not None else None
    notes = payload.get("notes")
    parent_claim_uid = payload.get("parent_claim_uid")
    decomposition_status = "unanalyzed"
    conn.execute(
        """
        INSERT INTO claim (
            claim_uid, investigation_uid, created_at, created_by_actor_id, claim_text,
            claim_type, scope_json, temporal_json, current_status, language, tags_json, notes,
            parent_claim_uid, decomposition_status, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(claim_uid) DO UPDATE SET
            claim_text = excluded.claim_text,
            claim_type = excluded.claim_type,
            notes = excluded.notes,
            tags_json = excluded.tags_json,
            updated_at = excluded.updated_at
        """,
        (
            claim_uid,
            investigation_uid,
            created_at,
            created_by_actor_id,
            claim_text,
            claim_type,
            scope_json,
            temporal_json,
            current_status,
            language,
            tags_json,
            notes,
            parent_claim_uid,
            decomposition_status,
            created_at,
        ),
    )
    if parent_claim_uid:
        conn.execute(
            "UPDATE claim SET decomposition_status = ?, updated_at = ? WHERE claim_uid = ?",
            ("partially_decomposed", created_at, parent_claim_uid),
        )
    conn.execute(
        "INSERT OR IGNORE INTO processed_event (projection_name, event_id, processed_at) VALUES (?, ?, ?)",
        (PROJECTION_NAME_READ_MODEL, event.event_id, created_at),
    )


def handle_span_anchored(conn: sqlite3.Connection, event: Event) -> None:
    """Projection handler: SpanAnchored -> insert evidence_span. Spec 14.6.3."""
    payload = event.payload
    span_uid = payload["span_uid"]
    evidence_uid = payload["evidence_uid"]
    anchor_type = payload["anchor_type"]
    anchor_json = json.dumps(payload["anchor"])
    created_at = event.recorded_at
    created_by_actor_id = event.actor_id
    source_event_id = event.event_id
    conn.execute(
        """
        INSERT INTO evidence_span (span_uid, evidence_uid, anchor_type, anchor_json, created_at, created_by_actor_id, source_event_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            span_uid,
            evidence_uid,
            anchor_type,
            anchor_json,
            created_at,
            created_by_actor_id,
            source_event_id,
        ),
    )
    conn.execute(
        "INSERT OR IGNORE INTO processed_event (projection_name, event_id, processed_at) VALUES (?, ?, ?)",
        (PROJECTION_NAME_READ_MODEL, event.event_id, created_at),
    )


def _handle_evidence_link(conn: sqlite3.Connection, event: Event, link_type: str) -> None:
    """Shared: SupportLinked or ChallengeLinked -> insert evidence_link."""
    payload = event.payload
    link_uid = payload["link_uid"]
    claim_uid = payload["claim_uid"]
    span_uid = payload["span_uid"]
    strength = payload.get("strength")
    notes = payload.get("notes")
    rationale = payload.get("rationale")
    created_at = event.recorded_at
    created_by_actor_id = event.actor_id
    source_event_id = event.event_id
    conn.execute(
        """
        INSERT INTO evidence_link (link_uid, claim_uid, span_uid, link_type, strength, notes, rationale, created_at, created_by_actor_id, source_event_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            link_uid,
            claim_uid,
            span_uid,
            link_type,
            strength,
            notes,
            rationale,
            created_at,
            created_by_actor_id,
            source_event_id,
        ),
    )
    conn.execute(
        "INSERT OR IGNORE INTO processed_event (projection_name, event_id, processed_at) VALUES (?, ?, ?)",
        (PROJECTION_NAME_READ_MODEL, event.event_id, created_at),
    )


def handle_support_linked(conn: sqlite3.Connection, event: Event) -> None:
    _handle_evidence_link(conn, event, "SUPPORTS")


def handle_challenge_linked(conn: sqlite3.Connection, event: Event) -> None:
    _handle_evidence_link(conn, event, "CHALLENGES")


def _handle_link_retracted(conn: sqlite3.Connection, event: Event) -> None:
    """Shared: SupportRetracted or ChallengeRetracted -> insert evidence_link_retraction. Phase 3."""
    payload = event.payload
    link_uid = payload["link_uid"]
    rationale = payload.get("rationale")
    retracted_at = event.recorded_at
    conn.execute(
        "INSERT OR REPLACE INTO evidence_link_retraction (link_uid, retracted_at, rationale) VALUES (?, ?, ?)",
        (link_uid, retracted_at, rationale),
    )
    conn.execute(
        "INSERT OR IGNORE INTO processed_event (projection_name, event_id, processed_at) VALUES (?, ?, ?)",
        (PROJECTION_NAME_READ_MODEL, event.event_id, retracted_at),
    )


def handle_support_retracted(conn: sqlite3.Connection, event: Event) -> None:
    _handle_link_retracted(conn, event)


def handle_challenge_retracted(conn: sqlite3.Connection, event: Event) -> None:
    _handle_link_retracted(conn, event)


def handle_claim_typed(conn: sqlite3.Connection, event: Event) -> None:
    """Projection: ClaimTyped -> update claim.claim_type, updated_at. Spec 14.6.3."""
    payload = event.payload
    claim_uid = payload["claim_uid"]
    claim_type = payload["claim_type"]
    now = event.recorded_at
    conn.execute(
        "UPDATE claim SET claim_type = ?, updated_at = ? WHERE claim_uid = ?",
        (claim_type, now, claim_uid),
    )
    conn.execute(
        "INSERT OR IGNORE INTO processed_event (projection_name, event_id, processed_at) VALUES (?, ?, ?)",
        (PROJECTION_NAME_READ_MODEL, event.event_id, now),
    )


def handle_claim_scoped(conn: sqlite3.Connection, event: Event) -> None:
    """Projection: ClaimScoped -> update claim.scope_json, updated_at. Spec 14.6.3."""
    payload = event.payload
    claim_uid = payload["claim_uid"]
    scope_json = json.dumps(payload["scope"])
    now = event.recorded_at
    conn.execute(
        "UPDATE claim SET scope_json = ?, updated_at = ? WHERE claim_uid = ?",
        (scope_json, now, claim_uid),
    )
    conn.execute(
        "INSERT OR IGNORE INTO processed_event (projection_name, event_id, processed_at) VALUES (?, ?, ?)",
        (PROJECTION_NAME_READ_MODEL, event.event_id, now),
    )


def handle_claim_temporalized(conn: sqlite3.Connection, event: Event) -> None:
    """Projection: ClaimTemporalized -> update claim.temporal_json, updated_at. Spec 14.6.3."""
    payload = event.payload
    claim_uid = payload["claim_uid"]
    temporal_json = json.dumps(payload["temporal"])
    now = event.recorded_at
    conn.execute(
        "UPDATE claim SET temporal_json = ?, updated_at = ? WHERE claim_uid = ?",
        (temporal_json, now, claim_uid),
    )
    conn.execute(
        "INSERT OR IGNORE INTO processed_event (projection_name, event_id, processed_at) VALUES (?, ?, ?)",
        (PROJECTION_NAME_READ_MODEL, event.event_id, now),
    )


def handle_claim_asserted(conn: sqlite3.Connection, event: Event) -> None:
    """Projection: ClaimAsserted -> insert claim_assertion. Spec 14.6.3."""
    payload = event.payload
    assertion_uid = payload["assertion_uid"]
    claim_uid = payload["claim_uid"]
    asserted_at = event.recorded_at
    actor_type = event.actor_type
    actor_id = event.actor_id
    assertion_mode = payload["assertion_mode"]
    confidence = payload.get("confidence")
    justification = payload.get("justification")
    source_event_id = event.event_id
    conn.execute(
        """
        INSERT INTO claim_assertion (assertion_uid, claim_uid, asserted_at, actor_type, actor_id, assertion_mode, confidence, justification, source_event_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            assertion_uid,
            claim_uid,
            asserted_at,
            actor_type,
            actor_id,
            assertion_mode,
            confidence,
            justification,
            source_event_id,
        ),
    )
    conn.execute(
        "INSERT OR IGNORE INTO processed_event (projection_name, event_id, processed_at) VALUES (?, ?, ?)",
        (PROJECTION_NAME_READ_MODEL, event.event_id, asserted_at),
    )


def handle_tension_declared(conn: sqlite3.Connection, event: Event) -> None:
    """Projection: TensionDeclared -> insert tension; mark matching tension_suggestion confirmed. Spec 14.6.3; Phase 7."""
    payload = event.payload
    tension_uid = payload["tension_uid"]
    investigation_uid = event.investigation_uid
    claim_a_uid = payload["claim_a_uid"]
    claim_b_uid = payload["claim_b_uid"]
    tension_kind = payload.get("tension_kind")
    status = "OPEN"
    notes = payload.get("notes")
    created_at = event.recorded_at
    created_by_actor_id = event.actor_id
    source_event_id = event.event_id
    conn.execute(
        """
        INSERT INTO tension (tension_uid, investigation_uid, claim_a_uid, claim_b_uid, tension_kind, status, notes, created_at, created_by_actor_id, source_event_id, updated_at, assigned_to, due_date, remediation_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL)
        """,
        (
            tension_uid,
            investigation_uid,
            claim_a_uid,
            claim_b_uid,
            tension_kind,
            status,
            notes,
            created_at,
            created_by_actor_id,
            source_event_id,
            created_at,
        ),
    )
    # Phase 7: mark any pending suggestion for this pair as confirmed
    conn.execute(
        """UPDATE tension_suggestion SET status = 'confirmed', confirmed_tension_uid = ?, updated_at = ?
           WHERE investigation_uid = ? AND claim_a_uid = ? AND claim_b_uid = ? AND status = 'pending'""",
        (tension_uid, created_at, investigation_uid, claim_a_uid, claim_b_uid),
    )
    conn.execute(
        "INSERT OR IGNORE INTO processed_event (projection_name, event_id, processed_at) VALUES (?, ?, ?)",
        (PROJECTION_NAME_READ_MODEL, event.event_id, created_at),
    )


def handle_tension_suggested(conn: sqlite3.Connection, event: Event) -> None:
    """Projection: TensionSuggested -> insert tension_suggestion. Phase 7."""
    payload = event.payload
    suggestion_uid = payload["suggestion_uid"]
    investigation_uid = event.investigation_uid
    claim_a_uid = payload["claim_a_uid"]
    claim_b_uid = payload["claim_b_uid"]
    suggested_tension_kind = payload["suggested_tension_kind"]
    confidence = float(payload["confidence"])
    rationale = payload["rationale"]
    tool_module_id = payload.get("tool_module_id")
    now = event.recorded_at
    conn.execute(
        """INSERT INTO tension_suggestion (
             suggestion_uid, investigation_uid, claim_a_uid, claim_b_uid,
             suggested_tension_kind, confidence, rationale, status, tool_module_id,
             created_at, source_event_id, updated_at, confirmed_tension_uid, dismissed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, NULL, NULL)""",
        (
            suggestion_uid,
            investigation_uid,
            claim_a_uid,
            claim_b_uid,
            suggested_tension_kind,
            confidence,
            rationale,
            tool_module_id,
            now,
            event.event_id,
            now,
        ),
    )
    conn.execute(
        "INSERT OR IGNORE INTO processed_event (projection_name, event_id, processed_at) VALUES (?, ?, ?)",
        (PROJECTION_NAME_READ_MODEL, event.event_id, now),
    )


def handle_tension_suggestion_dismissed(conn: sqlite3.Connection, event: Event) -> None:
    """Projection: TensionSuggestionDismissed -> update tension_suggestion to dismissed. Phase 7."""
    payload = event.payload
    suggestion_uid = payload["suggestion_uid"]
    now = event.recorded_at
    conn.execute(
        "UPDATE tension_suggestion SET status = 'dismissed', dismissed_at = ?, updated_at = ? WHERE suggestion_uid = ?",
        (now, now, suggestion_uid),
    )
    conn.execute(
        "INSERT OR IGNORE INTO processed_event (projection_name, event_id, processed_at) VALUES (?, ?, ?)",
        (PROJECTION_NAME_READ_MODEL, event.event_id, now),
    )


def handle_suggestion_dismissed(conn: sqlite3.Connection, event: Event) -> None:
    """Projection: SuggestionDismissed -> update tension_suggestion if type=tension_suggested; insert suggestion_dismissal. Phase 2."""
    payload = event.payload
    suggestion_type = payload["suggestion_type"]
    suggestion_ref = payload["suggestion_ref"]
    claim_uid = payload.get("claim_uid")
    rationale = payload.get("rationale")
    dismissed_by = payload.get("dismissed_by") or {}
    actor_id = dismissed_by.get("actor_id", event.actor_id)
    now = event.recorded_at
    investigation_uid = event.investigation_uid
    if suggestion_type == "tension_suggested":
        conn.execute(
            "UPDATE tension_suggestion SET status = 'dismissed', dismissed_at = ?, updated_at = ? WHERE suggestion_uid = ?",
            (now, now, suggestion_ref),
        )
    conn.execute(
        """INSERT INTO suggestion_dismissal (event_id, investigation_uid, suggestion_type, suggestion_ref, claim_uid, rationale, dismissed_at, actor_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            event.event_id,
            investigation_uid,
            suggestion_type,
            suggestion_ref,
            claim_uid,
            rationale,
            now,
            actor_id,
        ),
    )
    conn.execute(
        "INSERT OR IGNORE INTO processed_event (projection_name, event_id, processed_at) VALUES (?, ?, ?)",
        (PROJECTION_NAME_READ_MODEL, event.event_id, now),
    )


def handle_tension_status_updated(conn: sqlite3.Connection, event: Event) -> None:
    """Projection: TensionStatusUpdated -> update tension.status, updated_at; optional notes from reason. Spec 14.6.3."""
    payload = event.payload
    tension_uid = payload["tension_uid"]
    to_status = payload["to_status"]
    reason = payload.get("reason") or payload.get("resolution_rationale")
    now = event.recorded_at
    if reason is not None:
        conn.execute(
            "UPDATE tension SET status = ?, notes = ?, updated_at = ? WHERE tension_uid = ?",
            (to_status, reason, now, tension_uid),
        )
    else:
        conn.execute(
            "UPDATE tension SET status = ?, updated_at = ? WHERE tension_uid = ?",
            (to_status, now, tension_uid),
        )
    conn.execute(
        "INSERT OR IGNORE INTO processed_event (projection_name, event_id, processed_at) VALUES (?, ?, ?)",
        (PROJECTION_NAME_READ_MODEL, event.event_id, now),
    )


def handle_tension_exception_updated(conn: sqlite3.Connection, event: Event) -> None:
    """Projection: TensionExceptionUpdated -> update tension assigned_to, due_date, remediation_type. Phase 11."""
    payload = event.payload
    tension_uid = payload["tension_uid"]
    now = event.recorded_at
    updates: list[str] = ["updated_at = ?"]
    args: list[object] = [now]
    if "assigned_to" in payload:
        updates.append("assigned_to = ?")
        args.append(payload["assigned_to"])
    if "due_date" in payload:
        updates.append("due_date = ?")
        args.append(payload["due_date"])
    if "remediation_type" in payload:
        updates.append("remediation_type = ?")
        args.append(payload["remediation_type"])
    args.append(tension_uid)
    conn.execute(
        f"UPDATE tension SET {', '.join(updates)} WHERE tension_uid = ?",
        tuple(args),
    )
    conn.execute(
        "INSERT OR IGNORE INTO processed_event (projection_name, event_id, processed_at) VALUES (?, ?, ?)",
        (PROJECTION_NAME_READ_MODEL, event.event_id, now),
    )


def handle_claim_withdrawn(conn: sqlite3.Connection, event: Event) -> None:
    """Projection: ClaimWithdrawn -> set claim.current_status = WITHDRAWN. Spec 14.6.3."""
    payload = event.payload
    claim_uid = payload["claim_uid"]
    now = event.recorded_at
    conn.execute(
        "UPDATE claim SET current_status = ?, updated_at = ? WHERE claim_uid = ?",
        ("WITHDRAWN", now, claim_uid),
    )
    conn.execute(
        "INSERT OR IGNORE INTO processed_event (projection_name, event_id, processed_at) VALUES (?, ?, ?)",
        (PROJECTION_NAME_READ_MODEL, event.event_id, now),
    )


def handle_claim_downgraded(conn: sqlite3.Connection, event: Event) -> None:
    """Projection: ClaimDowngraded -> set claim.current_status = to_status. Spec 14.6.3."""
    payload = event.payload
    claim_uid = payload["claim_uid"]
    to_status = payload["to_status"]
    now = event.recorded_at
    conn.execute(
        "UPDATE claim SET current_status = ?, updated_at = ? WHERE claim_uid = ?",
        (to_status, now, claim_uid),
    )
    conn.execute(
        "INSERT OR IGNORE INTO processed_event (projection_name, event_id, processed_at) VALUES (?, ?, ?)",
        (PROJECTION_NAME_READ_MODEL, event.event_id, now),
    )


def handle_claim_promoted_to_sef(conn: sqlite3.Connection, event: Event) -> None:
    """Projection: ClaimPromotedToSEF -> set claim.claim_type = SEF. Spec 14.6.3."""
    payload = event.payload
    claim_uid = payload["claim_uid"]
    now = event.recorded_at
    conn.execute(
        "UPDATE claim SET claim_type = ?, updated_at = ? WHERE claim_uid = ?",
        ("SEF", now, claim_uid),
    )
    conn.execute(
        "INSERT OR IGNORE INTO processed_event (projection_name, event_id, processed_at) VALUES (?, ?, ?)",
        (PROJECTION_NAME_READ_MODEL, event.event_id, now),
    )


def handle_claim_decomposition_analyzed(conn: sqlite3.Connection, event: Event) -> None:
    """Projection: ClaimDecompositionAnalyzed -> insert claim_decomposition; update claim.decomposition_status. Spec 14.6.3."""
    payload = event.payload
    claim_uid = payload["claim_uid"]
    is_atomic = payload["is_atomic"]
    suggested = payload.get("suggested_decomposition", [])
    suggested_splits = json.dumps(
        [
            {
                "suggested_text": s.get("suggested_text", ""),
                "source_offset_start": s.get("source_offset_start"),
                "source_offset_end": s.get("source_offset_end"),
                "confidence": s.get("confidence", 0),
                "rationale": s.get("rationale"),
            }
            for s in suggested
        ]
    )
    overall_confidence = payload.get("overall_confidence")
    analysis_rationale = payload.get("analysis_rationale")
    tool = payload.get("tool") or {}
    analyzed_at = event.recorded_at
    analysis_uid = event.event_id
    conn.execute(
        """
        INSERT INTO claim_decomposition (
            analysis_uid, claim_uid, is_atomic, overall_confidence, analysis_rationale,
            suggested_splits, analyzed_at, analyzer_module_id, analyzer_version, run_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            analysis_uid,
            claim_uid,
            1 if is_atomic else 0,
            overall_confidence,
            analysis_rationale,
            suggested_splits,
            analyzed_at,
            tool.get("module_id", ""),
            tool.get("module_version", ""),
            tool.get("run_id", ""),
        ),
    )
    row = conn.execute(
        "SELECT decomposition_status FROM claim WHERE claim_uid = ?", (claim_uid,)
    ).fetchone()
    if row:
        current = row[0]
        if current == "unanalyzed":
            new_status = "atomic" if is_atomic else "compound_detected"
            conn.execute(
                "UPDATE claim SET decomposition_status = ?, updated_at = ? WHERE claim_uid = ?",
                (new_status, analyzed_at, claim_uid),
            )
    conn.execute(
        "INSERT OR IGNORE INTO processed_event (projection_name, event_id, processed_at) VALUES (?, ?, ?)",
        (PROJECTION_NAME_READ_MODEL, event.event_id, analyzed_at),
    )


def handle_evidence_superseded(conn: sqlite3.Connection, event: Event) -> None:
    """Projection: EvidenceSuperseded -> insert evidence_supersession. Spec 14.6.3."""
    payload = event.payload
    supersession_uid = payload["supersession_uid"]
    new_evidence_uid = payload["new_evidence_uid"]
    prior_evidence_uid = payload["prior_evidence_uid"]
    supersession_type = payload["supersession_type"]
    reason = payload.get("reason")
    created_at = event.recorded_at
    created_by_actor_id = event.actor_id
    source_event_id = event.event_id
    conn.execute(
        """
        INSERT INTO evidence_supersession (
            supersession_uid, new_evidence_uid, prior_evidence_uid, supersession_type,
            reason, created_at, created_by_actor_id, source_event_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            supersession_uid,
            new_evidence_uid,
            prior_evidence_uid,
            supersession_type,
            reason,
            created_at,
            created_by_actor_id,
            source_event_id,
        ),
    )
    conn.execute(
        "INSERT OR IGNORE INTO processed_event (projection_name, event_id, processed_at) VALUES (?, ?, ?)",
        (PROJECTION_NAME_READ_MODEL, event.event_id, created_at),
    )


def handle_source_registered(conn: sqlite3.Connection, event: Event) -> None:
    """Projection: SourceRegistered -> upsert source. Spec 14.6.3. Phase 2: independence_notes."""
    payload = event.payload
    source_uid = payload["source_uid"]
    investigation_uid = payload["investigation_uid"]
    display_name = payload["display_name"]
    source_type = payload["source_type"]
    alias = payload.get("alias")
    encrypted_identity = payload.get("encrypted_identity")
    notes = payload.get("notes")
    independence_notes = payload.get("independence_notes")
    created_at = event.recorded_at
    created_by_actor_id = event.actor_id
    conn.execute(
        """
        INSERT INTO source (
            source_uid, investigation_uid, display_name, source_type, alias,
            encrypted_identity, notes, independence_notes, created_at, created_by_actor_id, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_uid) DO UPDATE SET
            display_name = excluded.display_name,
            source_type = excluded.source_type,
            alias = excluded.alias,
            encrypted_identity = excluded.encrypted_identity,
            notes = excluded.notes,
            independence_notes = excluded.independence_notes,
            updated_at = excluded.updated_at
        """,
        (
            source_uid,
            investigation_uid,
            display_name,
            source_type,
            alias,
            encrypted_identity,
            notes,
            independence_notes,
            created_at,
            created_by_actor_id,
            created_at,
        ),
    )
    conn.execute(
        "INSERT OR IGNORE INTO processed_event (projection_name, event_id, processed_at) VALUES (?, ?, ?)",
        (PROJECTION_NAME_READ_MODEL, event.event_id, created_at),
    )


def handle_source_independence_notes_recorded(conn: sqlite3.Connection, event: Event) -> None:
    """Projection: SourceIndependenceNotesRecorded -> update source.independence_notes. Phase 2 (Epistemology)."""
    payload = event.payload
    source_uid = payload["source_uid"]
    independence_notes = payload.get("independence_notes")
    updated_at = event.recorded_at
    conn.execute(
        "UPDATE source SET independence_notes = ?, updated_at = ? WHERE source_uid = ?",
        (independence_notes, updated_at, source_uid),
    )
    conn.execute(
        "INSERT OR IGNORE INTO processed_event (projection_name, event_id, processed_at) VALUES (?, ?, ?)",
        (PROJECTION_NAME_READ_MODEL, event.event_id, updated_at),
    )


def handle_evidence_source_linked(conn: sqlite3.Connection, event: Event) -> None:
    """Projection: EvidenceSourceLinked -> insert evidence_source_link. Spec 14.6.3."""
    payload = event.payload
    evidence_uid = payload["evidence_uid"]
    source_uid = payload["source_uid"]
    relationship = payload.get("relationship")
    created_at = event.recorded_at
    source_event_id = event.event_id
    conn.execute(
        """
        INSERT INTO evidence_source_link (evidence_uid, source_uid, relationship, created_at, source_event_id)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(evidence_uid, source_uid) DO UPDATE SET relationship = excluded.relationship, source_event_id = excluded.source_event_id
        """,
        (evidence_uid, source_uid, relationship, created_at, source_event_id),
    )
    conn.execute(
        "INSERT OR IGNORE INTO processed_event (projection_name, event_id, processed_at) VALUES (?, ?, ?)",
        (PROJECTION_NAME_READ_MODEL, event.event_id, created_at),
    )


def handle_evidence_integrity_verified(conn: sqlite3.Connection, event: Event) -> None:
    """Projection: EvidenceIntegrityVerified -> update evidence_item.integrity_status, last_verified_at. Spec 14.6.3."""
    payload = event.payload
    evidence_uid = payload["evidence_uid"]
    result = payload["result"]  # VERIFIED|MODIFIED|MISSING
    verified_at = payload.get("verified_at", event.recorded_at)
    conn.execute(
        "UPDATE evidence_item SET integrity_status = ?, last_verified_at = ?, updated_at = ? WHERE evidence_uid = ?",
        (result, verified_at, verified_at, evidence_uid),
    )
    conn.execute(
        "INSERT OR IGNORE INTO processed_event (projection_name, event_id, processed_at) VALUES (?, ?, ?)",
        (PROJECTION_NAME_READ_MODEL, event.event_id, verified_at),
    )


def handle_evidence_trust_assessment_recorded(conn: sqlite3.Connection, event: Event) -> None:
    """Projection: EvidenceTrustAssessmentRecorded -> upsert evidence_trust_assessment. Spec 14.6.3, evidence-trust-assessments.md."""
    payload = event.payload
    evidence_uid = payload["evidence_uid"]
    provider_id = payload["provider_id"]
    assessment_kind = payload["assessment_kind"]
    result_json = json.dumps(payload["result"])
    assessed_at = payload["assessed_at"]
    result_expires_at = payload.get("result_expires_at")
    metadata_json = json.dumps(payload["metadata"]) if payload.get("metadata") is not None else None
    source_event_id = event.event_id
    conn.execute(
        """
        INSERT INTO evidence_trust_assessment (
            evidence_uid, provider_id, assessment_kind, result, assessed_at,
            result_expires_at, metadata, source_event_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(evidence_uid, provider_id, assessment_kind) DO UPDATE SET
            result = excluded.result,
            assessed_at = excluded.assessed_at,
            result_expires_at = excluded.result_expires_at,
            metadata = excluded.metadata,
            source_event_id = excluded.source_event_id
        """,
        (
            evidence_uid,
            provider_id,
            assessment_kind,
            result_json,
            assessed_at,
            result_expires_at,
            metadata_json,
            source_event_id,
        ),
    )
    conn.execute(
        "INSERT OR IGNORE INTO processed_event (projection_name, event_id, processed_at) VALUES (?, ?, ?)",
        (PROJECTION_NAME_READ_MODEL, event.event_id, event.recorded_at),
    )


def handle_evidence_redaction_recorded(conn: sqlite3.Connection, event: Event) -> None:
    """Projection: EvidenceRedactionRecorded -> update evidence_item.redaction_reason, redaction_at. Phase C.1."""
    payload = event.payload
    evidence_uid = payload["evidence_uid"]
    reason = payload.get("reason") or ""
    redacted_at = payload.get("redacted_at") or event.recorded_at
    conn.execute(
        "UPDATE evidence_item SET redaction_reason = ?, redaction_at = ?, updated_at = ? WHERE evidence_uid = ?",
        (reason, redacted_at, redacted_at, evidence_uid),
    )
    conn.execute(
        "INSERT OR IGNORE INTO processed_event (projection_name, event_id, processed_at) VALUES (?, ?, ?)",
        (PROJECTION_NAME_READ_MODEL, event.event_id, redacted_at),
    )


def handle_evidence_marked_reviewed(conn: sqlite3.Connection, event: Event) -> None:
    """Projection: EvidenceMarkedReviewed -> update evidence_item.reviewed_at, reviewed_by_actor_id. Phase D.2."""
    payload = event.payload
    evidence_uid = payload["evidence_uid"]
    reviewed_at = payload.get("reviewed_at") or event.recorded_at
    reviewed_by = payload.get("reviewed_by_actor_id") or event.actor_id
    conn.execute(
        "UPDATE evidence_item SET reviewed_at = ?, reviewed_by_actor_id = ?, updated_at = ? WHERE evidence_uid = ?",
        (reviewed_at, reviewed_by, reviewed_at, evidence_uid),
    )
    conn.execute(
        "INSERT OR IGNORE INTO processed_event (projection_name, event_id, processed_at) VALUES (?, ?, ?)",
        (PROJECTION_NAME_READ_MODEL, event.event_id, reviewed_at),
    )


def handle_chain_of_custody_report_generated(conn: sqlite3.Connection, event: Event) -> None:
    """Projection: ChainOfCustodyReportGenerated -> recorded in event history only; mark processed."""
    conn.execute(
        "INSERT OR IGNORE INTO processed_event (projection_name, event_id, processed_at) VALUES (?, ?, ?)",
        (PROJECTION_NAME_READ_MODEL, event.event_id, event.recorded_at),
    )


def handle_artifact_created(conn: sqlite3.Connection, event: Event) -> None:
    """Projection: ArtifactCreated -> insert artifact. Spec 14.6.3."""
    payload = event.payload
    artifact_uid = payload["artifact_uid"]
    investigation_uid = event.investigation_uid
    artifact_type = payload.get("artifact_type")
    title = payload.get("title")
    created_by = payload.get("created_by") or {}
    created_by_actor_id = created_by.get("actor_id", event.actor_id)
    notes = payload.get("notes")
    created_at = event.recorded_at
    conn.execute(
        """
        INSERT INTO artifact (
            artifact_uid, investigation_uid, artifact_type, title,
            created_at, created_by_actor_id, notes, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            artifact_uid,
            investigation_uid,
            artifact_type,
            title,
            created_at,
            created_by_actor_id,
            notes,
            created_at,
        ),
    )
    conn.execute(
        "INSERT OR IGNORE INTO processed_event (projection_name, event_id, processed_at) VALUES (?, ?, ?)",
        (PROJECTION_NAME_READ_MODEL, event.event_id, created_at),
    )


def handle_checkpoint_created(conn: sqlite3.Connection, event: Event) -> None:
    """Projection: CheckpointCreated -> insert checkpoint. Spec 14.6.3. Phase A: policy_summary. E5.3: certification."""
    payload = event.payload
    checkpoint_uid = payload["checkpoint_uid"]
    investigation_uid = event.investigation_uid
    scope_refs = payload.get("scope_refs") or []
    artifact_refs = payload.get("artifact_refs") or []
    reason = payload.get("reason")
    policy_summary = payload.get("policy_summary")
    certifying_org_id = payload.get("certifying_org_id")
    certified_at = payload.get("certified_at")
    created_at = event.recorded_at
    created_by_actor_id = event.actor_id
    scope_refs_json = json.dumps(scope_refs) if scope_refs else None
    artifact_refs_json = json.dumps(artifact_refs) if artifact_refs else None
    conn.execute(
        """
        INSERT INTO checkpoint (
            checkpoint_uid, investigation_uid, scope_refs_json, artifact_refs_json,
            reason, created_at, created_by_actor_id, policy_summary,
            certifying_org_id, certified_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            checkpoint_uid,
            investigation_uid,
            scope_refs_json,
            artifact_refs_json,
            reason,
            created_at,
            created_by_actor_id,
            policy_summary,
            certifying_org_id,
            certified_at,
        ),
    )
    conn.execute(
        "INSERT OR IGNORE INTO processed_event (projection_name, event_id, processed_at) VALUES (?, ?, ?)",
        (PROJECTION_NAME_READ_MODEL, event.event_id, created_at),
    )


def handle_artifact_version_frozen(conn: sqlite3.Connection, event: Event) -> None:
    """Projection: ArtifactVersionFrozen -> insert checkpoint_artifact_freeze. Spec 14.6.3."""
    payload = event.payload
    checkpoint_uid = payload["checkpoint_uid"]
    artifact_uid = payload["artifact_uid"]
    claim_refs = payload.get("claim_refs")
    evidence_refs = payload.get("evidence_refs")
    tension_refs = payload.get("tension_refs")
    created_at = event.recorded_at
    source_event_id = event.event_id
    claim_refs_json = json.dumps(claim_refs) if claim_refs else None
    evidence_refs_json = json.dumps(evidence_refs) if evidence_refs else None
    tension_refs_json = json.dumps(tension_refs) if tension_refs else None
    conn.execute(
        """
        INSERT OR IGNORE INTO checkpoint_artifact_freeze (
            checkpoint_uid, artifact_uid, claim_refs_json, evidence_refs_json, tension_refs_json,
            created_at, source_event_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            checkpoint_uid,
            artifact_uid,
            claim_refs_json,
            evidence_refs_json,
            tension_refs_json,
            created_at,
            source_event_id,
        ),
    )
    conn.execute(
        "INSERT OR IGNORE INTO processed_event (projection_name, event_id, processed_at) VALUES (?, ?, ?)",
        (PROJECTION_NAME_READ_MODEL, event.event_id, created_at),
    )


# Register handlers so apply_event can dispatch without a long if-chain. Add new event types here.
EVENT_HANDLERS[EVENT_INVESTIGATION_CREATED] = handle_investigation_created
EVENT_HANDLERS[EVENT_INVESTIGATION_ARCHIVED] = handle_investigation_archived
EVENT_HANDLERS[EVENT_TIER_CHANGED] = handle_tier_changed
EVENT_HANDLERS[EVENT_EVIDENCE_INGESTED] = handle_evidence_ingested
EVENT_HANDLERS[EVENT_CLAIM_PROPOSED] = handle_claim_proposed
EVENT_HANDLERS[EVENT_SPAN_ANCHORED] = handle_span_anchored
EVENT_HANDLERS[EVENT_SUPPORT_LINKED] = handle_support_linked
EVENT_HANDLERS[EVENT_SUPPORT_RETRACTED] = handle_support_retracted
EVENT_HANDLERS[EVENT_CHALLENGE_LINKED] = handle_challenge_linked
EVENT_HANDLERS[EVENT_CHALLENGE_RETRACTED] = handle_challenge_retracted
EVENT_HANDLERS[EVENT_CLAIM_TYPED] = handle_claim_typed
EVENT_HANDLERS[EVENT_CLAIM_SCOPED] = handle_claim_scoped
EVENT_HANDLERS[EVENT_CLAIM_TEMPORALIZED] = handle_claim_temporalized
EVENT_HANDLERS[EVENT_CLAIM_ASSERTED] = handle_claim_asserted
EVENT_HANDLERS[EVENT_TENSION_DECLARED] = handle_tension_declared
EVENT_HANDLERS[EVENT_TENSION_SUGGESTED] = handle_tension_suggested
EVENT_HANDLERS[EVENT_TENSION_SUGGESTION_DISMISSED] = handle_tension_suggestion_dismissed
EVENT_HANDLERS[EVENT_SUGGESTION_DISMISSED] = handle_suggestion_dismissed
EVENT_HANDLERS[EVENT_TENSION_STATUS_UPDATED] = handle_tension_status_updated
EVENT_HANDLERS[EVENT_TENSION_EXCEPTION_UPDATED] = handle_tension_exception_updated
EVENT_HANDLERS[EVENT_CLAIM_WITHDRAWN] = handle_claim_withdrawn
EVENT_HANDLERS[EVENT_CLAIM_DOWNGRADED] = handle_claim_downgraded
EVENT_HANDLERS[EVENT_CLAIM_PROMOTED_TO_SEF] = handle_claim_promoted_to_sef
EVENT_HANDLERS[EVENT_CLAIM_DECOMPOSITION_ANALYZED] = handle_claim_decomposition_analyzed
EVENT_HANDLERS[EVENT_EVIDENCE_SUPERSEDED] = handle_evidence_superseded
EVENT_HANDLERS[EVENT_SOURCE_REGISTERED] = handle_source_registered
EVENT_HANDLERS[EVENT_SOURCE_INDEPENDENCE_NOTES_RECORDED] = handle_source_independence_notes_recorded
EVENT_HANDLERS[EVENT_EVIDENCE_SOURCE_LINKED] = handle_evidence_source_linked
EVENT_HANDLERS[EVENT_EVIDENCE_INTEGRITY_VERIFIED] = handle_evidence_integrity_verified
EVENT_HANDLERS[EVENT_EVIDENCE_TRUST_ASSESSMENT_RECORDED] = handle_evidence_trust_assessment_recorded
EVENT_HANDLERS[EVENT_EVIDENCE_REDACTION_RECORDED] = handle_evidence_redaction_recorded
EVENT_HANDLERS[EVENT_EVIDENCE_MARKED_REVIEWED] = handle_evidence_marked_reviewed
EVENT_HANDLERS[EVENT_CHAIN_OF_CUSTODY_REPORT_GENERATED] = handle_chain_of_custody_report_generated
EVENT_HANDLERS[EVENT_ARTIFACT_CREATED] = handle_artifact_created
EVENT_HANDLERS[EVENT_CHECKPOINT_CREATED] = handle_checkpoint_created
EVENT_HANDLERS[EVENT_ARTIFACT_VERSION_FROZEN] = handle_artifact_version_frozen


def apply_event(conn: sqlite3.Connection, event: Event) -> None:
    """Dispatch event to the correct projection handler. Uses EVENT_HANDLERS registry."""
    handler = EVENT_HANDLERS.get(event.event_type)
    if handler is not None:
        handler(conn, event)
