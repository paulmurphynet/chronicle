"""Tension commands: declare, emit suggestions, dismiss suggestion, update status."""

from datetime import UTC, datetime
from typing import Any

from chronicle.core.errors import ChronicleUserError
from chronicle.core.events import (
    EVENT_TENSION_DECLARED,
    EVENT_TENSION_EXCEPTION_UPDATED,
    EVENT_TENSION_STATUS_UPDATED,
    EVENT_TENSION_SUGGESTED,
    EVENT_TENSION_SUGGESTION_DISMISSED,
    Event,
)
from chronicle.core.payloads import (
    TensionDeclaredPayload,
    TensionExceptionUpdatedPayload,
    TensionStatusUpdatedPayload,
    TensionSuggestedPayload,
    TensionSuggestionDismissedPayload,
)
from chronicle.core.policy import require_workspace_for_command
from chronicle.core.uid import generate_event_id, generate_suggestion_uid, generate_tension_uid
from chronicle.store.commands.attestation import apply_attestation_to_payload
from chronicle.store.protocols import EventStore, ReadModel

_TENSION_STATUSES = frozenset(
    {"OPEN", "DISPUTED", "ACK", "DEFERRED", "ESCALATED", "RESOLVED", "INTRACTABLE", "SUPERSEDED"}
)
_TENSION_TRANSITIONS: frozenset[tuple[str, str]] = frozenset(
    {
        ("OPEN", "DISPUTED"),
        ("OPEN", "ACK"),
        ("OPEN", "DEFERRED"),
        ("OPEN", "RESOLVED"),
        ("OPEN", "INTRACTABLE"),
        ("DISPUTED", "ACK"),
        ("DISPUTED", "RESOLVED"),
        ("DISPUTED", "INTRACTABLE"),
        ("DISPUTED", "ESCALATED"),
        ("ACK", "RESOLVED"),
        ("ACK", "INTRACTABLE"),
        ("ACK", "DISPUTED"),
        ("DEFERRED", "OPEN"),
        ("DEFERRED", "DISPUTED"),
        ("DEFERRED", "RESOLVED"),
        ("ESCALATED", "RESOLVED"),
        ("ESCALATED", "INTRACTABLE"),
    }
)


def declare_tension(
    store: EventStore,
    read_model: ReadModel,
    investigation_uid: str,
    claim_a_uid: str,
    claim_b_uid: str,
    *,
    tension_kind: str | None = None,
    notes: str | None = None,
    actor_id: str = "default",
    actor_type: str = "human",
    workspace: str = "spark",
    idempotency_key: str | None = None,
    verification_level: str | None = None,
    attestation_ref: str | None = None,
) -> tuple[str, str]:
    """DeclareTension command. Returns (event_id, tension_uid). Forge+ tier. Spec 1.5.1, 1.5.1a."""
    key = (idempotency_key or "").strip()
    if key:
        existing = store.get_event_by_idempotency_key(key)
        if existing:
            return (existing.event_id, existing.subject_uid)
    require_workspace_for_command(workspace, "declare_tension")
    if read_model.get_claim(claim_a_uid) is None:
        raise ChronicleUserError(f"claim_a_uid must reference an existing claim: {claim_a_uid}")
    if read_model.get_claim(claim_b_uid) is None:
        raise ChronicleUserError(f"claim_b_uid must reference an existing claim: {claim_b_uid}")
    if claim_a_uid == claim_b_uid:
        raise ChronicleUserError("claim_a and claim_b must differ")
    pair = frozenset({claim_a_uid, claim_b_uid})
    for t in read_model.get_tensions_for_claim(claim_a_uid):
        if t.status == "OPEN" and frozenset({t.claim_a_uid, t.claim_b_uid}) == pair:
            raise ChronicleUserError(
                "a tension between these two claims already exists in OPEN status"
            )
    tension_uid = generate_tension_uid()
    event_id = generate_event_id()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = TensionDeclaredPayload(
        tension_uid=tension_uid,
        claim_a_uid=claim_a_uid,
        claim_b_uid=claim_b_uid,
        tension_kind=tension_kind,
        notes=notes,
    ).to_dict()
    apply_attestation_to_payload(
        payload,
        verification_level=verification_level,
        attestation_ref=attestation_ref,
    )
    event = Event(
        event_id=event_id,
        event_type=EVENT_TENSION_DECLARED,
        occurred_at=now,
        recorded_at=now,
        investigation_uid=investigation_uid,
        subject_uid=tension_uid,
        actor_type=actor_type,
        actor_id=actor_id,
        workspace=workspace,
        payload=payload,
        idempotency_key=key or None,
    )
    store.append(event)
    return event_id, tension_uid


def emit_tension_suggestions(
    store: EventStore,
    investigation_uid: str,
    suggestions: list[Any],
    *,
    tool_module_id: str | None = None,
    actor_id: str = "default",
    actor_type: str = "tool",
    workspace: str = "spark",
) -> list[str]:
    """Emit one TensionSuggested event per suggestion. Phase 7. Returns list of event_ids."""
    event_ids: list[str] = []
    for s in suggestions:
        suggestion_uid = generate_suggestion_uid()
        event_id = generate_event_id()
        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        payload = TensionSuggestedPayload(
            suggestion_uid=suggestion_uid,
            claim_a_uid=s.claim_a_uid,
            claim_b_uid=s.claim_b_uid,
            suggested_tension_kind=s.suggested_tension_kind,
            confidence=s.confidence,
            rationale=s.rationale,
            tool_module_id=tool_module_id,
        )
        event = Event(
            event_id=event_id,
            event_type=EVENT_TENSION_SUGGESTED,
            occurred_at=now,
            recorded_at=now,
            investigation_uid=investigation_uid,
            subject_uid=suggestion_uid,
            actor_type=actor_type,
            actor_id=actor_id,
            workspace=workspace,
            payload=payload.to_dict(),
        )
        store.append(event)
        event_ids.append(event_id)
    return event_ids


def dismiss_tension_suggestion(
    store: EventStore,
    read_model: ReadModel,
    suggestion_uid: str,
    *,
    actor_id: str = "default",
    actor_type: str = "human",
    workspace: str = "spark",
) -> str:
    """Emit TensionSuggestionDismissed. Phase 7. Returns event_id."""
    row = read_model.get_tension_suggestion(suggestion_uid)
    if row is None:
        raise ChronicleUserError(
            f"suggestion_uid must reference an existing tension suggestion: {suggestion_uid}"
        )
    if row.status != "pending":
        raise ChronicleUserError(f"tension suggestion is not pending (status={row.status})")
    event_id = generate_event_id()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = TensionSuggestionDismissedPayload(suggestion_uid=suggestion_uid)
    event = Event(
        event_id=event_id,
        event_type=EVENT_TENSION_SUGGESTION_DISMISSED,
        occurred_at=now,
        recorded_at=now,
        investigation_uid=row.investigation_uid,
        subject_uid=suggestion_uid,
        actor_type=actor_type,
        actor_id=actor_id,
        workspace=workspace,
        payload=payload.to_dict(),
    )
    store.append(event)
    return event_id


def update_tension_status(
    store: EventStore,
    read_model: ReadModel,
    tension_uid: str,
    to_status: str,
    *,
    reason: str | None = None,
    actor_id: str = "default",
    actor_type: str = "human",
    workspace: str = "spark",
) -> str:
    """UpdateTensionStatus command. Returns event_id. Forge+ tier. Spec 1.5.1, 1.5.1a."""
    require_workspace_for_command(workspace, "update_tension_status")
    tension = read_model.get_tension(tension_uid)
    if tension is None:
        raise ChronicleUserError(f"tension_uid must reference an existing tension: {tension_uid}")
    to_status = to_status.strip().upper()
    if to_status not in _TENSION_STATUSES:
        raise ChronicleUserError(f"status must be one of {sorted(_TENSION_STATUSES)}")
    from_status = tension.status
    if (from_status, to_status) not in _TENSION_TRANSITIONS:
        raise ChronicleUserError(
            f"invalid transition from {from_status} to {to_status} (terminal states: RESOLVED, INTRACTABLE, SUPERSEDED)"
        )
    event_id = generate_event_id()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = TensionStatusUpdatedPayload(
        tension_uid=tension_uid, from_status=from_status, to_status=to_status, reason=reason
    )
    event = Event(
        event_id=event_id,
        event_type=EVENT_TENSION_STATUS_UPDATED,
        occurred_at=now,
        recorded_at=now,
        investigation_uid=tension.investigation_uid,
        subject_uid=tension_uid,
        actor_type=actor_type,
        actor_id=actor_id,
        workspace=workspace,
        payload=payload.to_dict(),
    )
    store.append(event)
    return event_id


def update_tension_exception(
    store: EventStore,
    read_model: ReadModel,
    tension_uid: str,
    *,
    assigned_to: str | None = None,
    due_date: str | None = None,
    remediation_type: str | None = None,
    actor_id: str = "default",
    actor_type: str = "human",
    workspace: str = "spark",
) -> str:
    """Update tension exception workflow fields. Phase 11. Call only when profile has exception_workflow. Returns event_id."""
    require_workspace_for_command(workspace, "update_tension_exception")
    tension = read_model.get_tension(tension_uid)
    if tension is None:
        raise ChronicleUserError(f"tension_uid must reference an existing tension: {tension_uid}")
    if assigned_to is None and due_date is None and remediation_type is None:
        raise ChronicleUserError(
            "At least one of assigned_to, due_date, remediation_type must be provided"
        )
    event_id = generate_event_id()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = TensionExceptionUpdatedPayload(
        tension_uid=tension_uid,
        assigned_to=assigned_to,
        due_date=due_date,
        remediation_type=remediation_type,
    )
    event = Event(
        event_id=event_id,
        event_type=EVENT_TENSION_EXCEPTION_UPDATED,
        occurred_at=now,
        recorded_at=now,
        investigation_uid=tension.investigation_uid,
        subject_uid=tension_uid,
        actor_type=actor_type,
        actor_id=actor_id,
        workspace=workspace,
        payload=payload.to_dict(),
    )
    store.append(event)
    return event_id
