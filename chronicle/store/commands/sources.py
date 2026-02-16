"""Source commands: register source, link evidence to source, record independence notes (Phase 2).
Phase 1 (source-independence implementation plan): get_sources_backing_claim — sources that back a claim via supporting evidence."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from chronicle.core.errors import ChronicleUserError
from chronicle.core.events import (
    EVENT_EVIDENCE_SOURCE_LINKED,
    EVENT_SOURCE_INDEPENDENCE_NOTES_RECORDED,
    EVENT_SOURCE_REGISTERED,
    Event,
)
from chronicle.core.payloads import (
    EvidenceSourceLinkedPayload,
    SourceIndependenceNotesRecordedPayload,
    SourceRegisteredPayload,
)
from chronicle.core.policy import require_workspace_for_command
from chronicle.core.uid import generate_event_id, generate_source_uid
from chronicle.store.commands.claims import get_defensibility_score
from chronicle.store.protocols import EventStore, ReadModel

_SOURCE_TYPES = frozenset(
    {"person", "organization", "document", "public_record", "anonymous_tip", "other"}
)
_EVIDENCE_SOURCE_RELATIONSHIPS = frozenset({"provided_by", "authored_by", "testified_to", "other"})


def register_source(
    store: EventStore,
    read_model: ReadModel,
    investigation_uid: str,
    display_name: str,
    source_type: str,
    *,
    alias: str | None = None,
    encrypted_identity: str | None = None,
    notes: str | None = None,
    independence_notes: str | None = None,
    actor_id: str = "default",
    actor_type: str = "human",
    workspace: str = "spark",
) -> tuple[str, str]:
    """RegisterSource command. Returns (event_id, source_uid). Forge+ tier. Spec 1.5.1."""
    require_workspace_for_command(workspace, "register_source")
    if read_model.get_investigation(investigation_uid) is None:
        raise ChronicleUserError(
            f"investigation_uid must reference an existing investigation: {investigation_uid}"
        )
    if not display_name or not display_name.strip():
        raise ChronicleUserError("display_name must be non-empty")
    if source_type not in _SOURCE_TYPES:
        raise ChronicleUserError(f"source_type must be one of {sorted(_SOURCE_TYPES)}")
    source_uid = generate_source_uid()
    event_id = generate_event_id()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = SourceRegisteredPayload(
        source_uid=source_uid,
        investigation_uid=investigation_uid,
        display_name=display_name.strip(),
        source_type=source_type,
        alias=alias,
        encrypted_identity=encrypted_identity,
        notes=notes,
        independence_notes=independence_notes,
    )
    event = Event(
        event_id=event_id,
        event_type=EVENT_SOURCE_REGISTERED,
        occurred_at=now,
        recorded_at=now,
        investigation_uid=investigation_uid,
        subject_uid=source_uid,
        actor_type=actor_type,
        actor_id=actor_id,
        workspace=workspace,
        payload=payload.to_dict(),
    )
    store.append(event)
    return event_id, source_uid


def link_evidence_to_source(
    store: EventStore,
    read_model: ReadModel,
    evidence_uid: str,
    source_uid: str,
    *,
    relationship: str | None = None,
    actor_id: str = "default",
    actor_type: str = "human",
    workspace: str = "spark",
) -> str:
    """LinkEvidenceToSource command. Returns event_id. Forge+ tier. Spec 1.5.1."""
    require_workspace_for_command(workspace, "link_evidence_to_source")
    if read_model.get_evidence_item(evidence_uid) is None:
        raise ChronicleUserError(
            f"evidence_uid must reference an existing evidence item: {evidence_uid}"
        )
    if read_model.get_source(source_uid) is None:
        raise ChronicleUserError(f"source_uid must reference an existing source: {source_uid}")
    if relationship is not None and relationship not in _EVIDENCE_SOURCE_RELATIONSHIPS:
        raise ChronicleUserError(
            f"relationship must be one of {sorted(_EVIDENCE_SOURCE_RELATIONSHIPS)}"
        )
    ev = read_model.get_evidence_item(evidence_uid)
    investigation_uid = ev.investigation_uid if ev else ""
    event_id = generate_event_id()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = EvidenceSourceLinkedPayload(
        evidence_uid=evidence_uid, source_uid=source_uid, relationship=relationship
    )
    event = Event(
        event_id=event_id,
        event_type=EVENT_EVIDENCE_SOURCE_LINKED,
        occurred_at=now,
        recorded_at=now,
        investigation_uid=investigation_uid,
        subject_uid=evidence_uid,
        actor_type=actor_type,
        actor_id=actor_id,
        workspace=workspace,
        payload=payload.to_dict(),
    )
    store.append(event)
    return event_id


def record_source_independence_notes(
    store: EventStore,
    read_model: ReadModel,
    source_uid: str,
    independence_notes: str | None,
    *,
    actor_id: str = "default",
    actor_type: str = "human",
    workspace: str = "spark",
) -> str:
    """Record or clear independence notes for a source (Phase 2 Epistemology). Returns event_id."""
    if read_model.get_source(source_uid) is None:
        raise ChronicleUserError(f"source_uid must reference an existing source: {source_uid}")
    source = read_model.get_source(source_uid)
    investigation_uid = source.investigation_uid if source else ""
    event_id = generate_event_id()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = SourceIndependenceNotesRecordedPayload(
        source_uid=source_uid,
        independence_notes=independence_notes.strip()
        if independence_notes and independence_notes.strip()
        else None,
    )
    event = Event(
        event_id=event_id,
        event_type=EVENT_SOURCE_INDEPENDENCE_NOTES_RECORDED,
        occurred_at=now,
        recorded_at=now,
        investigation_uid=investigation_uid,
        subject_uid=source_uid,
        actor_type=actor_type,
        actor_id=actor_id,
        workspace=workspace,
        payload=payload.to_dict(),
    )
    store.append(event)
    return event_id


def get_sources_backing_claim(
    read_model: ReadModel,
    claim_uid: str,
) -> list[dict[str, Any]]:
    """Return the list of sources that back this claim via supporting evidence.
    Phase 1 (source-independence implementation plan). Used by reasoning brief and defensibility API.
    Each item has source_uid, display_name, independence_notes (as recorded; not independently verified).
    Order: stable by source_uid. Returns [] if claim not found or has no support links."""
    support_with_inherited = read_model.get_support_for_claim_including_inherited(claim_uid)
    seen: dict[str, dict[str, Any]] = {}
    for _link, _inherited in support_with_inherited:
        span = read_model.get_evidence_span(_link.span_uid)
        if not span:
            continue
        for esl in read_model.list_evidence_source_links(span.evidence_uid):
            if esl.source_uid in seen:
                continue
            source = read_model.get_source(esl.source_uid)
            if source:
                seen[esl.source_uid] = {
                    "source_uid": source.source_uid,
                    "display_name": source.display_name,
                    "independence_notes": source.independence_notes,
                }
    return sorted(seen.values(), key=lambda x: x["source_uid"])


def get_source_reliability(
    read_model: ReadModel,
    source_uid: str,
    investigation_uid: str,
) -> dict[str, int]:
    """Phase 2: Return source reliability summary — evidence count, claims supported, corroborated, in tension.
    Corroborated = claim has 2+ distinct sources; in_tension = claim is in at least one tension.
    """
    source = read_model.get_source(source_uid)
    if source is None or source.investigation_uid != investigation_uid:
        return {
            "evidence_count": 0,
            "claims_supported_count": 0,
            "claims_corroborated_count": 0,
            "claims_in_tension_count": 0,
        }
    evidence_uids = read_model.list_evidence_uids_for_source(source_uid)
    claim_uids = list(
        set(read_model.list_claim_uids_with_support_from_evidence_uids(evidence_uids))
    )
    corroborated = 0
    in_tension = 0
    for c_uid in claim_uids:
        scorecard = get_defensibility_score(read_model, c_uid)
        if scorecard and (scorecard.corroboration.get("independent_sources_count") or 0) >= 2:
            corroborated += 1
        tensions = read_model.get_tensions_for_claim(c_uid)
        if tensions:
            in_tension += 1
    return {
        "evidence_count": len(evidence_uids),
        "claims_supported_count": len(claim_uids),
        "claims_corroborated_count": corroborated,
        "claims_in_tension_count": in_tension,
    }
