"""Record human override and confirm events with required rationale. E3.3."""

from datetime import UTC, datetime

from chronicle.core.errors import ChronicleUserError
from chronicle.core.events import EVENT_HUMAN_CONFIRMED, EVENT_HUMAN_OVERRODE, Event
from chronicle.core.payloads import HumanConfirmedPayload, HumanOverrodePayload
from chronicle.core.uid import generate_event_id
from chronicle.store.protocols import EventStore, ReadModel


def record_human_override(
    store: EventStore,
    read_model: ReadModel,
    claim_uid: str,
    override_type: str,
    rationale: str,
    *,
    actor_id: str = "default",
    actor_type: str = "human",
) -> str:
    """E3.3: Record HumanOverrode (e.g. override defensibility warning). rationale is required. Returns event_id."""
    if not (rationale and rationale.strip()):
        raise ChronicleUserError("rationale is required for human override")
    claim = read_model.get_claim(claim_uid)
    if claim is None:
        raise ChronicleUserError("Claim not found")
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = HumanOverrodePayload(
        claim_uid=claim_uid,
        override_type=(override_type or "defensibility_warning").strip(),
        rationale=rationale.strip(),
    )
    event_id = generate_event_id()
    event = Event(
        event_id=event_id,
        event_type=EVENT_HUMAN_OVERRODE,
        occurred_at=now,
        recorded_at=now,
        investigation_uid=claim.investigation_uid,
        subject_uid=claim_uid,
        actor_type=actor_type,
        actor_id=actor_id,
        workspace="spark",
        payload=payload.to_dict(),
    )
    store.append(event)
    return event_id


def record_human_confirm(
    store: EventStore,
    read_model: ReadModel,
    scope: str,
    scope_uid: str,
    context: str,
    rationale: str,
    *,
    actor_id: str = "default",
    actor_type: str = "human",
) -> str:
    """E3.3: Record HumanConfirmed (e.g. publish despite weak defensibility). rationale is required. Returns event_id."""
    if not (rationale and rationale.strip()):
        raise ChronicleUserError("rationale is required for human confirm")
    if scope not in ("claim", "investigation"):
        raise ChronicleUserError("scope must be 'claim' or 'investigation'")
    if scope == "claim":
        claim = read_model.get_claim(scope_uid)
        if claim is None:
            raise ChronicleUserError("Claim not found")
        investigation_uid = claim.investigation_uid
    else:
        inv = read_model.get_investigation(scope_uid)
        if inv is None:
            raise ChronicleUserError("Investigation not found")
        investigation_uid = scope_uid
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = HumanConfirmedPayload(
        scope=scope,
        scope_uid=scope_uid,
        context=(context or "publish_despite_weak").strip(),
        rationale=rationale.strip(),
    )
    event_id = generate_event_id()
    event = Event(
        event_id=event_id,
        event_type=EVENT_HUMAN_CONFIRMED,
        occurred_at=now,
        recorded_at=now,
        investigation_uid=investigation_uid,
        subject_uid=scope_uid,
        actor_type=actor_type,
        actor_id=actor_id,
        workspace="spark",
        payload=payload.to_dict(),
    )
    store.append(event)
    return event_id
