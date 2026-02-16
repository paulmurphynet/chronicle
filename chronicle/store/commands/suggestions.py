"""Unified suggestion dismissal: record when user dismisses an AI suggestion with optional rationale. Phase 2."""

from datetime import UTC, datetime

from chronicle.core.errors import ChronicleUserError
from chronicle.core.events import EVENT_SUGGESTION_DISMISSED, Event
from chronicle.core.payloads import (
    SUGGESTION_TYPE_DECOMPOSITION,
    SUGGESTION_TYPE_TENSION,
    SUGGESTION_TYPES,
    ActorRef,
    SuggestionDismissedPayload,
)
from chronicle.core.uid import generate_event_id
from chronicle.store.protocols import EventStore, ReadModel


def dismiss_suggestion(
    store: EventStore,
    read_model: ReadModel,
    investigation_uid: str,
    suggestion_type: str,
    suggestion_ref: str,
    *,
    rationale: str | None = None,
    claim_uid: str | None = None,
    actor_id: str = "default",
    actor_type: str = "human",
    workspace: str = "spark",
) -> str:
    """Emit SuggestionDismissed. Validates ref exists; records dismissal with optional rationale. Phase 2."""
    suggestion_type = suggestion_type.strip().lower()
    if suggestion_type not in SUGGESTION_TYPES:
        raise ChronicleUserError(
            f"suggestion_type must be one of {SUGGESTION_TYPES}, got {suggestion_type!r}"
        )
    if suggestion_type == SUGGESTION_TYPE_TENSION:
        row = read_model.get_tension_suggestion(suggestion_ref)
        if row is None:
            raise ChronicleUserError(
                f"suggestion_ref must reference an existing tension suggestion: {suggestion_ref}"
            )
        if row.status != "pending":
            raise ChronicleUserError(f"tension suggestion is not pending (status={row.status})")
        if row.investigation_uid != investigation_uid:
            raise ChronicleUserError("tension suggestion does not belong to this investigation")
        effective_inv = row.investigation_uid
        effective_claim_uid = None
    else:
        assert suggestion_type == SUGGESTION_TYPE_DECOMPOSITION
        analysis = read_model.get_claim_decomposition_by_analysis_uid(suggestion_ref)
        if analysis is None:
            raise ChronicleUserError(
                f"suggestion_ref must reference an existing decomposition analysis: {suggestion_ref}"
            )
        if claim_uid is not None and analysis.claim_uid != claim_uid:
            raise ChronicleUserError(
                f"decomposition analysis is for claim {analysis.claim_uid}, not {claim_uid}"
            )
        claim = read_model.get_claim(analysis.claim_uid)
        if claim is None:
            raise ChronicleUserError("claim for decomposition analysis not found")
        effective_inv = claim.investigation_uid
        effective_claim_uid = analysis.claim_uid
        if effective_inv != investigation_uid:
            raise ChronicleUserError(
                "decomposition suggestion does not belong to this investigation"
            )

    event_id = generate_event_id()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = SuggestionDismissedPayload(
        suggestion_type=suggestion_type,
        suggestion_ref=suggestion_ref,
        claim_uid=effective_claim_uid,
        rationale=rationale,
        dismissed_by=ActorRef(actor_type=actor_type, actor_id=actor_id),
    )
    event = Event(
        event_id=event_id,
        event_type=EVENT_SUGGESTION_DISMISSED,
        occurred_at=now,
        recorded_at=now,
        investigation_uid=effective_inv,
        subject_uid=suggestion_ref,
        actor_type=actor_type,
        actor_id=actor_id,
        workspace=workspace,
        payload=payload.to_dict(),
    )
    store.append(event)
    return event_id
