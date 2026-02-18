"""Evidence commands: ingest, anchor span, link support/challenge, supersede, verify, chain-of-custody report."""

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from chronicle.core.errors import ChronicleUserError
from chronicle.core.events import (
    EVENT_CHAIN_OF_CUSTODY_REPORT_GENERATED,
    EVENT_CHALLENGE_LINKED,
    EVENT_CHALLENGE_RETRACTED,
    EVENT_EVIDENCE_INGESTED,
    EVENT_EVIDENCE_INTEGRITY_VERIFIED,
    EVENT_EVIDENCE_MARKED_REVIEWED,
    EVENT_EVIDENCE_REDACTION_RECORDED,
    EVENT_EVIDENCE_SUPERSEDED,
    EVENT_EVIDENCE_TRUST_ASSESSMENT_RECORDED,
    EVENT_SPAN_ANCHORED,
    EVENT_SUPPORT_LINKED,
    EVENT_SUPPORT_RETRACTED,
    Event,
)
from chronicle.core.payloads import (
    ChainOfCustodyReportGeneratedPayload,
    EvidenceIngestedPayload,
    EvidenceIntegrityVerifiedPayload,
    EvidenceLinkPayload,
    EvidenceMarkedReviewedPayload,
    EvidenceRedactionRecordedPayload,
    EvidenceSupersededPayload,
    EvidenceTrustAssessmentRecordedPayload,
    LinkRetractedPayload,
    SpanAnchoredPayload,
)
from chronicle.core.policy import require_workspace_for_command
from chronicle.core.uid import (
    generate_event_id,
    generate_evidence_uid,
    generate_link_uid,
    generate_report_uid,
    generate_span_uid,
    generate_supersession_uid,
)
from chronicle.core.validation import MAX_EVIDENCE_BYTES
from chronicle.store.commands.attestation import apply_attestation_to_payload
from chronicle.store.protocols import EventStore, EvidenceStore, ReadModel

# MIME type: type/subtype (optional params after ;). Spec 1.5.1a.
_MIME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9+.-]*/[a-zA-Z0-9][a-zA-Z0-9+.-]*(;.*)?$")
_ANCHOR_TYPES = frozenset({"text_offset", "pdf_bbox", "timecode", "selector"})


def ingest_evidence(
    store: EventStore,
    evidence_store: EvidenceStore,
    investigation_uid: str,
    blob: bytes,
    media_type: str,
    *,
    original_filename: str = "",
    file_metadata: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    provenance_type: str | None = None,
    actor_id: str = "default",
    actor_type: str = "human",
    workspace: str = "spark",
    idempotency_key: str | None = None,
    verification_level: str | None = None,
    attestation_ref: str | None = None,
) -> tuple[str, str]:
    """IngestEvidence command. Store blob first, then emit EvidenceIngested. Returns (event_id, evidence_uid). Spec 1.5.1, 1.5.1a; evidence.md 4.2. E2.3: optional provenance_type (human_created | ai_generated | unknown)."""
    key = (idempotency_key or "").strip()
    if key:
        existing = store.get_event_by_idempotency_key(key)
        if existing:
            return (existing.event_id, existing.subject_uid)
    if not blob:
        raise ChronicleUserError("blob must be non-empty")
    if len(blob) > MAX_EVIDENCE_BYTES:
        raise ChronicleUserError(f"evidence file size must be at most {MAX_EVIDENCE_BYTES} bytes")
    media_type = media_type.strip()
    if not _MIME_PATTERN.match(media_type):
        raise ChronicleUserError(
            "media_type must be a valid MIME type (e.g. application/pdf, text/plain)"
        )
    content_hash = hashlib.sha256(blob).hexdigest()
    evidence_uid = generate_evidence_uid()
    uri = evidence_store.store(evidence_uid, blob, media_type)
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = EvidenceIngestedPayload(
        evidence_uid=evidence_uid,
        content_hash=content_hash,
        file_size_bytes=len(blob),
        original_filename=original_filename or evidence_uid,
        uri=uri,
        media_type=media_type,
        ingest_timestamp=now,
        extraction_version=None,
        file_metadata=file_metadata,
        metadata=metadata,
        provenance_type=provenance_type or "unknown",
    ).to_dict()
    apply_attestation_to_payload(
        payload,
        verification_level=verification_level,
        attestation_ref=attestation_ref,
    )
    event_id = generate_event_id()
    event = Event(
        event_id=event_id,
        event_type=EVENT_EVIDENCE_INGESTED,
        occurred_at=now,
        recorded_at=now,
        investigation_uid=investigation_uid,
        subject_uid=evidence_uid,
        actor_type=actor_type,
        actor_id=actor_id,
        workspace=workspace,
        payload=payload,
        idempotency_key=key or None,
    )
    store.append(event)
    return event_id, evidence_uid


def _validate_anchor_for_type(anchor_type: str, anchor: dict[str, Any]) -> None:
    """Validate anchor coordinates for the given anchor_type. Spec 1.5.1a, 15.1.10."""
    if anchor_type == "text_offset":
        start = anchor.get("start_char")
        end = anchor.get("end_char")
        if start is None or end is None:
            raise ChronicleUserError("text_offset anchor must have start_char and end_char")
        if not isinstance(start, int) or not isinstance(end, int):
            raise ChronicleUserError("text_offset start_char and end_char must be integers")
        if start < 0 or end < 0:
            raise ChronicleUserError("text_offset start_char and end_char must be non-negative")
        if start >= end:
            raise ChronicleUserError("text_offset start_char must be less than end_char")
    elif anchor_type == "pdf_bbox":
        page = anchor.get("page")
        bbox = anchor.get("bbox")
        if page is None:
            raise ChronicleUserError("pdf_bbox anchor must have page")
        if not isinstance(page, int) or page < 0:
            raise ChronicleUserError("pdf_bbox page must be a non-negative integer")
        if bbox is None:
            raise ChronicleUserError("pdf_bbox anchor must have bbox")
        if not isinstance(bbox, list | tuple) or len(bbox) != 4:
            raise ChronicleUserError("pdf_bbox bbox must be a list of 4 numbers [x0, y0, x1, y1]")
        if not all(isinstance(x, int | float) for x in bbox):
            raise ChronicleUserError("pdf_bbox bbox values must be numbers")
        x0, y0, x1, y1 = bbox[0], bbox[1], bbox[2], bbox[3]
        if x0 > x1 or y0 > y1:
            raise ChronicleUserError("pdf_bbox bbox must have x0 <= x1 and y0 <= y1")
    elif anchor_type == "timecode":
        start = anchor.get("start_ms")
        end = anchor.get("end_ms")
        if start is None or end is None:
            raise ChronicleUserError("timecode anchor must have start_ms and end_ms")
        if not isinstance(start, int | float) or not isinstance(end, int | float):
            raise ChronicleUserError("timecode start_ms and end_ms must be numbers")
        if start < 0 or end < 0:
            raise ChronicleUserError("timecode start_ms and end_ms must be non-negative")
        if start >= end:
            raise ChronicleUserError("timecode start_ms must be less than end_ms")
    # selector: any non-empty dict is accepted


def _validate_anchor_type_for_media(anchor_type: str, media_type: str) -> None:
    """Validate that anchor_type is appropriate for the evidence media type. Spec 1.5.1a."""
    mt = (media_type or "").strip().lower()
    if anchor_type == "text_offset":
        if not (mt.startswith("text/") or mt == "application/json" or mt == "application/xml"):
            raise ChronicleUserError(
                f"text_offset anchor is for text-like media (e.g. text/plain), not {media_type!r}"
            )
    elif anchor_type == "pdf_bbox":
        if mt != "application/pdf":
            raise ChronicleUserError(f"pdf_bbox anchor is for application/pdf, not {media_type!r}")
    elif anchor_type == "timecode" and not (mt.startswith("audio/") or mt.startswith("video/")):
        raise ChronicleUserError(f"timecode anchor is for audio or video media, not {media_type!r}")
    # selector: allowed for any media type


def anchor_span(
    store: EventStore,
    read_model: ReadModel,
    investigation_uid: str,
    evidence_uid: str,
    anchor_type: str,
    anchor: dict[str, Any],
    *,
    quote: str | None = None,
    notes: str | None = None,
    actor_id: str = "default",
    actor_type: str = "human",
    workspace: str = "spark",
    idempotency_key: str | None = None,
    verification_level: str | None = None,
    attestation_ref: str | None = None,
) -> tuple[str, str]:
    """AnchorSpan command. Returns (event_id, span_uid). Spec 1.5.1, 1.5.1a."""
    key = (idempotency_key or "").strip()
    if key:
        existing = store.get_event_by_idempotency_key(key)
        if existing:
            return (existing.event_id, existing.subject_uid)
    evidence_item = read_model.get_evidence_item(evidence_uid)
    if evidence_item is None:
        raise ChronicleUserError(
            f"evidence_uid must reference an existing evidence item: {evidence_uid}"
        )
    if anchor_type not in _ANCHOR_TYPES:
        raise ChronicleUserError(f"anchor_type must be one of {sorted(_ANCHOR_TYPES)}")
    if not isinstance(anchor, dict) or not anchor:
        raise ChronicleUserError("anchor must be a non-empty JSON object")
    _validate_anchor_for_type(anchor_type, anchor)
    _validate_anchor_type_for_media(anchor_type, evidence_item.media_type)
    span_uid = generate_span_uid()
    event_id = generate_event_id()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = SpanAnchoredPayload(
        span_uid=span_uid,
        evidence_uid=evidence_uid,
        anchor_type=anchor_type,
        anchor=anchor,
        quote=quote,
        notes=notes,
    ).to_dict()
    apply_attestation_to_payload(
        payload,
        verification_level=verification_level,
        attestation_ref=attestation_ref,
    )
    event = Event(
        event_id=event_id,
        event_type=EVENT_SPAN_ANCHORED,
        occurred_at=now,
        recorded_at=now,
        investigation_uid=investigation_uid,
        subject_uid=span_uid,
        actor_type=actor_type,
        actor_id=actor_id,
        workspace=workspace,
        payload=payload,
        idempotency_key=key or None,
    )
    store.append(event)
    return event_id, span_uid


def link_support(
    store: EventStore,
    read_model: ReadModel,
    investigation_uid: str,
    span_uid: str,
    claim_uid: str,
    *,
    strength: float | None = None,
    notes: str | None = None,
    rationale: str | None = None,
    defeater_kind: str | None = None,
    actor_id: str = "default",
    actor_type: str = "human",
    workspace: str = "spark",
    idempotency_key: str | None = None,
    verification_level: str | None = None,
    attestation_ref: str | None = None,
) -> tuple[str, str]:
    """LinkSupport command. Returns (event_id, link_uid). Spec 1.5.1, 1.5.1a."""
    key = (idempotency_key or "").strip()
    if key:
        existing = store.get_event_by_idempotency_key(key)
        if existing:
            return (existing.event_id, existing.subject_uid)
    if read_model.get_evidence_span(span_uid) is None:
        raise ChronicleUserError(f"span_uid must reference an existing span: {span_uid}")
    if read_model.get_claim(claim_uid) is None:
        raise ChronicleUserError(f"claim_uid must reference an existing claim: {claim_uid}")
    link_uid = generate_link_uid()
    event_id = generate_event_id()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = EvidenceLinkPayload(
        link_uid=link_uid, claim_uid=claim_uid, span_uid=span_uid, strength=strength, notes=notes, rationale=rationale, defeater_kind=defeater_kind
    ).to_dict()
    apply_attestation_to_payload(
        payload,
        verification_level=verification_level,
        attestation_ref=attestation_ref,
    )
    event = Event(
        event_id=event_id,
        event_type=EVENT_SUPPORT_LINKED,
        occurred_at=now,
        recorded_at=now,
        investigation_uid=investigation_uid,
        subject_uid=link_uid,
        actor_type=actor_type,
        actor_id=actor_id,
        workspace=workspace,
        payload=payload,
        idempotency_key=key or None,
    )
    store.append(event)
    return event_id, link_uid


def link_challenge(
    store: EventStore,
    read_model: ReadModel,
    investigation_uid: str,
    span_uid: str,
    claim_uid: str,
    *,
    strength: float | None = None,
    notes: str | None = None,
    rationale: str | None = None,
    defeater_kind: str | None = None,
    actor_id: str = "default",
    actor_type: str = "human",
    workspace: str = "spark",
    idempotency_key: str | None = None,
    verification_level: str | None = None,
    attestation_ref: str | None = None,
) -> tuple[str, str]:
    """LinkChallenge command. Returns (event_id, link_uid). Spec 1.5.1, 1.5.1a."""
    key = (idempotency_key or "").strip()
    if key:
        existing = store.get_event_by_idempotency_key(key)
        if existing:
            return (existing.event_id, existing.subject_uid)
    if read_model.get_evidence_span(span_uid) is None:
        raise ChronicleUserError(f"span_uid must reference an existing span: {span_uid}")
    if read_model.get_claim(claim_uid) is None:
        raise ChronicleUserError(f"claim_uid must reference an existing claim: {claim_uid}")
    link_uid = generate_link_uid()
    event_id = generate_event_id()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = EvidenceLinkPayload(
        link_uid=link_uid, claim_uid=claim_uid, span_uid=span_uid, strength=strength, notes=notes, rationale=rationale, defeater_kind=defeater_kind
    ).to_dict()
    apply_attestation_to_payload(
        payload,
        verification_level=verification_level,
        attestation_ref=attestation_ref,
    )
    event = Event(
        event_id=event_id,
        event_type=EVENT_CHALLENGE_LINKED,
        occurred_at=now,
        recorded_at=now,
        investigation_uid=investigation_uid,
        subject_uid=link_uid,
        actor_type=actor_type,
        actor_id=actor_id,
        workspace=workspace,
        payload=payload,
        idempotency_key=key or None,
    )
    store.append(event)
    return event_id, link_uid


def retract_support(
    store: EventStore,
    read_model: ReadModel,
    link_uid: str,
    *,
    rationale: str | None = None,
    actor_id: str = "default",
    actor_type: str = "human",
    workspace: str = "spark",
) -> str:
    """RetractSupport: mark a support link as retracted (Phase 3). Returns event_id. Full history preserved in ledger."""
    link = read_model.get_evidence_link(link_uid)
    if link is None:
        raise ChronicleUserError(f"link_uid must reference an existing evidence link: {link_uid}")
    if link.link_type != "SUPPORTS":
        raise ChronicleUserError(f"link_uid is a challenge link, not a support link: {link_uid}")
    claim = read_model.get_claim(link.claim_uid)
    investigation_uid = claim.investigation_uid if claim else ""
    event_id = generate_event_id()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = LinkRetractedPayload(link_uid=link_uid, rationale=rationale)
    event = Event(
        event_id=event_id,
        event_type=EVENT_SUPPORT_RETRACTED,
        occurred_at=now,
        recorded_at=now,
        investigation_uid=investigation_uid,
        subject_uid=link_uid,
        actor_type=actor_type,
        actor_id=actor_id,
        workspace=workspace,
        payload=payload.to_dict(),
    )
    store.append(event)
    return event_id


def retract_challenge(
    store: EventStore,
    read_model: ReadModel,
    link_uid: str,
    *,
    rationale: str | None = None,
    actor_id: str = "default",
    actor_type: str = "human",
    workspace: str = "spark",
) -> str:
    """RetractChallenge: mark a challenge link as retracted (Phase 3). Returns event_id. Full history preserved in ledger."""
    link = read_model.get_evidence_link(link_uid)
    if link is None:
        raise ChronicleUserError(f"link_uid must reference an existing evidence link: {link_uid}")
    if link.link_type != "CHALLENGES":
        raise ChronicleUserError(f"link_uid is a support link, not a challenge link: {link_uid}")
    claim = read_model.get_claim(link.claim_uid)
    investigation_uid = claim.investigation_uid if claim else ""
    event_id = generate_event_id()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = LinkRetractedPayload(link_uid=link_uid, rationale=rationale)
    event = Event(
        event_id=event_id,
        event_type=EVENT_CHALLENGE_RETRACTED,
        occurred_at=now,
        recorded_at=now,
        investigation_uid=investigation_uid,
        subject_uid=link_uid,
        actor_type=actor_type,
        actor_id=actor_id,
        workspace=workspace,
        payload=payload.to_dict(),
    )
    store.append(event)
    return event_id


def supersede_evidence(
    store: EventStore,
    read_model: ReadModel,
    new_evidence_uid: str,
    prior_evidence_uid: str,
    supersession_type: str,
    *,
    reason: str | None = None,
    actor_id: str = "default",
    actor_type: str = "human",
    workspace: str = "spark",
) -> tuple[str, str]:
    """SupersedeEvidence command. Returns (event_id, supersession_uid). Forge+ tier. Spec 1.5.1, 14.4.7."""
    require_workspace_for_command(workspace, "supersede_evidence")
    new_ev = read_model.get_evidence_item(new_evidence_uid)
    if new_ev is None:
        raise ChronicleUserError(
            f"new_evidence_uid must reference an existing evidence item: {new_evidence_uid}"
        )
    prior_ev = read_model.get_evidence_item(prior_evidence_uid)
    if prior_ev is None:
        raise ChronicleUserError(
            f"prior_evidence_uid must reference an existing evidence item: {prior_evidence_uid}"
        )
    if new_evidence_uid == prior_evidence_uid:
        raise ChronicleUserError("new_evidence_uid and prior_evidence_uid must differ")
    valid_type = frozenset({"correction", "enhancement", "replacement"})
    if supersession_type not in valid_type:
        raise ChronicleUserError(f"supersession_type must be one of {sorted(valid_type)}")
    investigation_uid = new_ev.investigation_uid
    supersession_uid = generate_supersession_uid()
    event_id = generate_event_id()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = EvidenceSupersededPayload(
        supersession_uid=supersession_uid,
        new_evidence_uid=new_evidence_uid,
        prior_evidence_uid=prior_evidence_uid,
        supersession_type=supersession_type,
        reason=reason,
    )
    event = Event(
        event_id=event_id,
        event_type=EVENT_EVIDENCE_SUPERSEDED,
        occurred_at=now,
        recorded_at=now,
        investigation_uid=investigation_uid,
        subject_uid=supersession_uid,
        actor_type=actor_type,
        actor_id=actor_id,
        workspace=workspace,
        payload=payload.to_dict(),
    )
    store.append(event)
    return event_id, supersession_uid


def verify_evidence_integrity(
    store: EventStore,
    read_model: ReadModel,
    evidence_store: EvidenceStore,
    *,
    investigation_uid: str | None = None,
    evidence_uid: str | None = None,
    actor_id: str = "default",
    actor_type: str = "human",
    workspace: str = "spark",
) -> list[str]:
    """VerifyEvidenceIntegrity: re-compute hash/size per file; emit EvidenceIntegrityVerified per item. Returns list of event_ids. Spec 4.3.2, 1.5.1."""
    if evidence_uid is not None:
        item = read_model.get_evidence_item(evidence_uid)
        if item is None:
            raise ChronicleUserError(
                f"evidence_uid must reference an existing evidence item: {evidence_uid}"
            )
        if investigation_uid is not None and item.investigation_uid != investigation_uid:
            raise ChronicleUserError("evidence_uid does not belong to the given investigation_uid")
        items = [item]
    elif investigation_uid is not None:
        if read_model.get_investigation(investigation_uid) is None:
            raise ChronicleUserError(
                f"investigation_uid must reference an existing investigation: {investigation_uid}"
            )
        items = read_model.list_evidence_by_investigation(investigation_uid)
    else:
        raise ChronicleUserError("either investigation_uid or evidence_uid must be provided")
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    event_ids: list[str] = []
    for item in items:
        expected_hash = item.content_hash
        expected_size = item.file_size_bytes
        actual_hash: str | None = None
        actual_size: int | None = None
        discrepancies: list[str] = []
        if not evidence_store.exists(item.uri):
            result = "MISSING"
            discrepancies.append("file not found at expected path")
        else:
            try:
                blob = evidence_store.retrieve(item.uri)
                actual_size = len(blob)
                actual_hash = hashlib.sha256(blob).hexdigest()
            except Exception as e:
                result = "MISSING"
                discrepancies.append(str(e))
                actual_hash = None
                actual_size = None
            else:
                if actual_hash != expected_hash:
                    discrepancies.append("content hash mismatch")
                if actual_size != expected_size:
                    discrepancies.append("file size mismatch")
                result = "VERIFIED" if not discrepancies else "MODIFIED"
        payload = EvidenceIntegrityVerifiedPayload(
            evidence_uid=item.evidence_uid,
            result=result,
            expected_hash=expected_hash,
            actual_hash=actual_hash,
            expected_size_bytes=expected_size,
            actual_size_bytes=actual_size,
            verified_at=now,
            discrepancies=discrepancies if discrepancies else None,
        )
        event_id = generate_event_id()
        event = Event(
            event_id=event_id,
            event_type=EVENT_EVIDENCE_INTEGRITY_VERIFIED,
            occurred_at=now,
            recorded_at=now,
            investigation_uid=item.investigation_uid,
            subject_uid=item.evidence_uid,
            actor_type=actor_type,
            actor_id=actor_id,
            workspace=workspace,
            payload=payload.to_dict(),
        )
        store.append(event)
        event_ids.append(event_id)
    return event_ids


def record_evidence_trust_assessment(
    store: EventStore,
    read_model: ReadModel,
    investigation_uid: str,
    evidence_uid: str,
    provider_id: str,
    assessment_kind: str,
    result: dict[str, Any],
    assessed_at: str,
    *,
    result_expires_at: str | None = None,
    metadata: dict[str, Any] | None = None,
    actor_id: str = "default",
    actor_type: str = "human",
    workspace: str = "spark",
) -> str:
    """RecordEvidenceTrustAssessment: append EvidenceTrustAssessmentRecorded. Returns event_id. Spec evidence-trust-assessments.md."""
    if read_model.get_investigation(investigation_uid) is None:
        raise ChronicleUserError(
            f"investigation_uid must reference an existing investigation: {investigation_uid}"
        )
    item = read_model.get_evidence_item(evidence_uid)
    if item is None:
        raise ChronicleUserError(
            f"evidence_uid must reference an existing evidence item: {evidence_uid}"
        )
    if item.investigation_uid != investigation_uid:
        raise ChronicleUserError("evidence_uid does not belong to the given investigation_uid")
    if not (provider_id and provider_id.strip()):
        raise ChronicleUserError("provider_id must be non-empty")
    if not (assessment_kind and assessment_kind.strip()):
        raise ChronicleUserError("assessment_kind must be non-empty")
    if not isinstance(result, dict):
        raise ChronicleUserError("result must be a JSON object")
    if not (assessed_at and assessed_at.strip()):
        raise ChronicleUserError("assessed_at must be non-empty (ISO-8601)")
    payload = EvidenceTrustAssessmentRecordedPayload(
        evidence_uid=evidence_uid,
        provider_id=provider_id.strip(),
        assessment_kind=assessment_kind.strip(),
        result=result,
        assessed_at=assessed_at.strip(),
        result_expires_at=(result_expires_at and result_expires_at.strip()) or None,
        metadata=metadata,
    )
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    event_id = generate_event_id()
    event = Event(
        event_id=event_id,
        event_type=EVENT_EVIDENCE_TRUST_ASSESSMENT_RECORDED,
        occurred_at=assessed_at.strip(),
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


def record_evidence_redaction(
    store: EventStore,
    read_model: ReadModel,
    evidence_uid: str,
    reason: str,
    *,
    redacted_at: str | None = None,
    actor_id: str = "default",
    actor_type: str = "human",
    workspace: str = "spark",
) -> str:
    """Record redaction on an evidence item (e.g. privilege). Phase C.1. Emits EvidenceRedactionRecorded. Returns event_id."""
    item = read_model.get_evidence_item(evidence_uid)
    if item is None:
        raise ChronicleUserError(
            f"evidence_uid must reference an existing evidence item: {evidence_uid}"
        )
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    at = redacted_at or now
    payload = EvidenceRedactionRecordedPayload(
        evidence_uid=evidence_uid,
        reason=reason.strip() or "redacted",
        redacted_at=at,
    )
    event_id = generate_event_id()
    event = Event(
        event_id=event_id,
        event_type=EVENT_EVIDENCE_REDACTION_RECORDED,
        occurred_at=now,
        recorded_at=now,
        investigation_uid=item.investigation_uid,
        subject_uid=evidence_uid,
        actor_type=actor_type,
        actor_id=actor_id,
        workspace=workspace,
        payload=payload.to_dict(),
    )
    store.append(event)
    return event_id


def mark_evidence_reviewed(
    store: EventStore,
    read_model: ReadModel,
    evidence_uid: str,
    *,
    reviewed_at: str | None = None,
    actor_id: str = "default",
    actor_type: str = "human",
    workspace: str = "spark",
) -> str:
    """Mark one evidence item as reviewed. Phase D.2. Emits EvidenceMarkedReviewed. Returns event_id."""
    item = read_model.get_evidence_item(evidence_uid)
    if item is None:
        raise ChronicleUserError(
            f"evidence_uid must reference an existing evidence item: {evidence_uid}"
        )
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    at = reviewed_at or now
    payload = EvidenceMarkedReviewedPayload(
        evidence_uid=evidence_uid,
        reviewed_at=at,
        reviewed_by_actor_id=actor_id,
    )
    event_id = generate_event_id()
    event = Event(
        event_id=event_id,
        event_type=EVENT_EVIDENCE_MARKED_REVIEWED,
        occurred_at=now,
        recorded_at=now,
        investigation_uid=item.investigation_uid,
        subject_uid=evidence_uid,
        actor_type=actor_type,
        actor_id=actor_id,
        workspace=workspace,
        payload=payload.to_dict(),
    )
    store.append(event)
    return event_id


def mark_evidence_reviewed_bulk(
    store: EventStore,
    read_model: ReadModel,
    evidence_uids: list[str],
    *,
    actor_id: str = "default",
    actor_type: str = "human",
    workspace: str = "spark",
) -> list[str]:
    """Mark multiple evidence items as reviewed. Phase D.2. Returns list of event_ids."""
    return [
        mark_evidence_reviewed(
            store, read_model, uid, actor_id=actor_id, actor_type=actor_type, workspace=workspace
        )
        for uid in evidence_uids
    ]


def generate_chain_of_custody_report(
    store: EventStore,
    read_model: ReadModel,
    scope: str,
    scope_uid: str,
    report_format: str,
    *,
    report_dir: Path,
    actor_id: str = "default",
    actor_type: str = "human",
    workspace: str = "spark",
) -> tuple[str, str]:
    """GenerateChainOfCustodyReport: build report, write file, emit event. Returns (event_id, report_uid). Forge+ tier. Spec 4.3.4, 1.5.1."""
    require_workspace_for_command(workspace, "generate_chain_of_custody_report")
    return _generate_chain_of_custody_report_impl(
        store,
        read_model,
        scope,
        scope_uid,
        report_format,
        report_dir=report_dir,
        actor_id=actor_id,
        actor_type=actor_type,
        workspace=workspace,
    )


def _build_chain_of_custody_html(report_data: dict[str, Any]) -> str:
    """Build a readable HTML document for chain-of-custody report. Printable to PDF."""
    parts = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Chain of Custody Report</title>",
        "<style>body{font-family:system-ui,sans-serif;margin:2em;max-width:900px}",
        "h1{font-size:1.4em}h2{font-size:1.1em;margin-top:1.5em}",
        ".block{background:#f5f5f5;padding:0.8em;margin:0.5em 0;border-radius:4px}",
        "table{border-collapse:collapse}td,th{padding:0.3em 0.6em;text-align:left;border:1px solid #ddd}</style></head><body>",
        "<h1>Chain of Custody Report</h1>",
        f"<p><strong>Report UID:</strong> {report_data.get('report_uid', '')}",
        f" &bull; <strong>Scope:</strong> {report_data.get('scope', '')}",
        f" &bull; <strong>Generated:</strong> {report_data.get('generated_at', '')}</p>",
    ]
    for i, item in enumerate(report_data.get("items", []), 1):
        parts.append(f"<h2>Evidence item {i}: {item.get('evidence_uid', '')}</h2>")
        parts.append("<p><strong>Identity:</strong> ")
        parts.append(
            f"{item.get('original_filename', '')} &bull; {item.get('media_type', '')} &bull; {item.get('file_size_bytes', 0)} bytes</p>"
        )
        seal = item.get("cryptographic_seal") or {}
        if seal:
            parts.append(
                f"<div class='block'><strong>Cryptographic seal:</strong> "
                f"Hash at ingestion: SHA-256 {seal.get('hash_at_ingestion', '')}<br>"
                f"Current hash: SHA-256 {seal.get('current_hash', '')}<br>"
                f"Match status: {seal.get('match_status', '')} (last verified: {item.get('last_verified_at') or '—'})</div>"
            )
        else:
            parts.append(
                f"<div class='block'><strong>Cryptographic seal:</strong> SHA-256 {item.get('content_hash', '')}<br>"
            )
            parts.append(
                f"Integrity status: {item.get('integrity_status', '')} (last verified: {item.get('last_verified_at') or '—'})</div>"
            )
        ing = item.get("ingestion_record") or {}
        if ing:
            parts.append(
                "<div class='block'><strong>Ingestion record:</strong> "
                f"Event {ing.get('event_id', '')} — By {ing.get('ingested_by_actor_id', '')} ({ing.get('actor_type', '')}) "
                f"at {ing.get('occurred_at', '')}; URI: {ing.get('uri') or '—'}; "
                f"original filename: {ing.get('original_filename') or '—'}</div>"
            )
        prov = item.get("source_provenance") or []
        if prov:
            parts.append("<div class='block'><strong>Source provenance:</strong><ul>")
            for s in prov:
                parts.append(
                    f"<li>{s.get('display_name') or s.get('source_uid')} ({s.get('source_type') or '—'}) — {s.get('relationship') or '—'}</li>"
                )
            parts.append("</ul></div>")
        vh = item.get("verification_history") or []
        if vh:
            parts.append("<div class='block'><strong>Verification history:</strong><ul>")
            for v in vh:
                exp_hash = v.get("expected_hash") or ""
                act_hash = v.get("actual_hash")
                exp_preview = f"{exp_hash[:16]}…" if len(exp_hash) > 16 else exp_hash or "—"
                act_preview = (
                    f"{act_hash[:16]}…" if act_hash and len(act_hash) > 16 else (act_hash or "—")
                )
                disc = f" — {v.get('discrepancies')}" if v.get("discrepancies") else ""
                parts.append(
                    f"<li>{v.get('recorded_at')}: {v.get('result')} — "
                    f"expected hash {exp_preview}; actual {act_preview}{disc}</li>"
                )
            parts.append("</ul></div>")
        parts.append(
            f"<p><strong>Linked claims:</strong> {', '.join(item.get('claims_linked') or []) or '—'}</p>"
        )
        events_list = item.get("events") or []
        parts.append(
            f"<p><strong>Full event history:</strong> {len(events_list)} events (chronological).</p>"
        )
        if events_list:
            parts.append("<div class='block'><ul>")
            for evt in events_list[:100]:  # cap display at 100 for readability
                parts.append(
                    f"<li>{evt.get('recorded_at')} — {evt.get('event_type')} ({evt.get('event_id', '')})</li>"
                )
            if len(events_list) > 100:
                parts.append(f"<li>… and {len(events_list) - 100} more</li>")
            parts.append("</ul></div>")
    parts.append("</body></html>")
    return "\n".join(parts)


def _generate_chain_of_custody_report_impl(
    store: EventStore,
    read_model: ReadModel,
    scope: str,
    scope_uid: str,
    report_format: str,
    *,
    report_dir: Path,
    actor_id: str = "default",
    actor_type: str = "human",
    workspace: str = "spark",
) -> tuple[str, str]:
    """Implementation of GenerateChainOfCustodyReport."""
    if scope not in ("evidence_item", "investigation"):
        raise ChronicleUserError("scope must be 'evidence_item' or 'investigation'")
    if report_format not in ("pdf", "html", "json"):
        raise ChronicleUserError("report_format must be one of pdf, html, json")
    if scope == "evidence_item":
        item = read_model.get_evidence_item(scope_uid)
        if item is None:
            raise ChronicleUserError(
                f"scope_uid must reference an existing evidence item: {scope_uid}"
            )
        investigation_uid = item.investigation_uid
        items_included = [scope_uid]
        evidence_items = [item]
    else:
        if read_model.get_investigation(scope_uid) is None:
            raise ChronicleUserError(
                f"scope_uid must reference an existing investigation: {scope_uid}"
            )
        investigation_uid = scope_uid
        evidence_items = read_model.list_evidence_by_investigation(scope_uid)
        items_included = [e.evidence_uid for e in evidence_items]
    report_uid = generate_report_uid()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    report_dir.mkdir(parents=True, exist_ok=True)
    ext = {"json": ".json", "html": ".html", "pdf": ".html"}[report_format]
    report_filename = f"{report_uid}{ext}"
    report_path = report_dir / report_filename
    report_uri = f"reports/{report_filename}"
    report_data: dict[str, Any] = {
        "report_uid": report_uid,
        "scope": scope,
        "scope_uid": scope_uid,
        "generated_at": now,
        "format": report_format,
        "items": [],
    }
    for ev in evidence_items:
        claim_uids = read_model.get_claim_uids_linked_to_evidence(ev.evidence_uid)
        events_for_evidence = store.read_by_subject(ev.evidence_uid)
        event_summaries = [
            {"event_id": e.event_id, "event_type": e.event_type, "recorded_at": e.recorded_at}
            for e in events_for_evidence
        ]
        ingestion_record: dict[str, Any] = {}
        for e in events_for_evidence:
            if e.event_type == EVENT_EVIDENCE_INGESTED:
                p = e.payload
                ingestion_record = {
                    "event_id": e.event_id,
                    "ingested_by_actor_id": e.actor_id,
                    "actor_type": e.actor_type,
                    "occurred_at": e.recorded_at,
                    "ingest_timestamp": p.get("ingest_timestamp") or e.recorded_at,
                    "uri": p.get("uri"),
                    "original_filename": p.get("original_filename"),
                    "metadata": p.get("metadata"),
                    "file_metadata": p.get("file_metadata"),
                }
                break
        source_provenance: list[dict[str, Any]] = []
        for link in read_model.list_evidence_source_links(ev.evidence_uid):
            src = read_model.get_source(link.source_uid)
            source_provenance.append(
                {
                    "source_uid": link.source_uid,
                    "display_name": src.display_name if src else None,
                    "source_type": src.source_type if src else None,
                    "relationship": link.relationship,
                }
            )
        verification_history: list[dict[str, Any]] = []
        for e in events_for_evidence:
            if e.event_type == EVENT_EVIDENCE_INTEGRITY_VERIFIED:
                p = e.payload
                verification_history.append(
                    {
                        "event_id": e.event_id,
                        "recorded_at": e.recorded_at,
                        "result": p.get("result"),
                        "expected_hash": p.get("expected_hash"),
                        "actual_hash": p.get("actual_hash"),
                        "expected_size_bytes": p.get("expected_size_bytes"),
                        "actual_size_bytes": p.get("actual_size_bytes"),
                        "verified_at": p.get("verified_at") or e.recorded_at,
                        "discrepancies": p.get("discrepancies"),
                        "notes": p.get("notes"),
                    }
                )
        latest_verification = next(
            (
                e
                for e in reversed(events_for_evidence)
                if e.event_type == EVENT_EVIDENCE_INTEGRITY_VERIFIED
            ),
            None,
        )
        if latest_verification and latest_verification.payload.get("result") == "MODIFIED":
            current_hash = latest_verification.payload.get("actual_hash") or ev.content_hash
        else:
            current_hash = ev.content_hash
        cryptographic_seal = {
            "hash_at_ingestion": ev.content_hash,
            "current_hash": current_hash,
            "match_status": ev.integrity_status,
        }
        item_entry: dict[str, Any] = {
            "evidence_uid": ev.evidence_uid,
            "original_filename": ev.original_filename,
            "media_type": ev.media_type,
            "file_size_bytes": ev.file_size_bytes,
            "content_hash": ev.content_hash,
            "cryptographic_seal": cryptographic_seal,
            "integrity_status": ev.integrity_status,
            "last_verified_at": ev.last_verified_at,
            "ingestion_record": ingestion_record,
            "source_provenance": source_provenance,
            "verification_history": verification_history,
            "claims_linked": claim_uids,
            "event_count": len(event_summaries),
            "events": event_summaries,
        }
        if getattr(ev, "redaction_reason", None):
            item_entry["redaction_reason"] = ev.redaction_reason
            item_entry["redaction_at"] = getattr(ev, "redaction_at", None)
        report_data["items"].append(item_entry)
    if report_format == "json":
        content = json.dumps(report_data, indent=2)
        report_path.write_text(content, encoding="utf-8")
    elif report_format == "html":
        content = _build_chain_of_custody_html(report_data)
        report_path.write_text(content, encoding="utf-8")
    else:
        content = _build_chain_of_custody_html(report_data)
        report_path.write_text(content, encoding="utf-8")
    content_bytes = content.encode("utf-8")
    content_hash = hashlib.sha256(content_bytes).hexdigest()
    payload = ChainOfCustodyReportGeneratedPayload(
        report_uid=report_uid,
        scope=scope,
        scope_uid=scope_uid,
        format=report_format,
        generated_at=now,
        content_hash=content_hash,
        report_uri=report_uri,
        items_included=items_included,
    )
    event_id = generate_event_id()
    subject_uid = scope_uid
    event = Event(
        event_id=event_id,
        event_type=EVENT_CHAIN_OF_CUSTODY_REPORT_GENERATED,
        occurred_at=now,
        recorded_at=now,
        investigation_uid=investigation_uid,
        subject_uid=subject_uid,
        actor_type=actor_type,
        actor_id=actor_id,
        workspace=workspace,
        payload=payload.to_dict(),
    )
    store.append(event)
    return event_id, report_uid
