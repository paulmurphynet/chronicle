"""Investigation commands: create, archive, set_tier, export, import."""

from datetime import UTC, datetime
from pathlib import Path

from chronicle.core.errors import ChronicleUserError
from chronicle.core.events import (
    EVENT_INVESTIGATION_ARCHIVED,
    EVENT_INVESTIGATION_CREATED,
    EVENT_TIER_CHANGED,
    Event,
)
from chronicle.core.payloads import (
    TIER_TRANSITIONS,
    VALID_TIERS,
    ActorRef,
    InvestigationArchivedPayload,
    InvestigationCreatedPayload,
    TierChangedPayload,
)
from chronicle.core.uid import generate_event_id, generate_investigation_uid
from chronicle.core.validation import MAX_DESCRIPTION_LENGTH, MAX_TITLE_LENGTH
from chronicle.store import export_import as export_import_mod
from chronicle.store.protocols import EventStore, ReadModel


def create_investigation(
    store: EventStore,
    title: str,
    *,
    description: str | None = None,
    actor_id: str = "default",
    actor_type: str = "human",
    workspace: str = "spark",
    idempotency_key: str | None = None,
) -> tuple[str, str]:
    """CreateInvestigation command. Returns (event_id, investigation_uid). Validates title non-empty and within length limits."""
    key = (idempotency_key or "").strip()
    if key:
        existing = store.get_event_by_idempotency_key(key)
        if existing:
            return (existing.event_id, existing.investigation_uid)
    t = title.strip() if title else ""
    if not t:
        raise ChronicleUserError("title must be non-empty")
    if len(t) > MAX_TITLE_LENGTH:
        raise ChronicleUserError(f"title must be at most {MAX_TITLE_LENGTH} characters")
    if description is not None and len(description) > MAX_DESCRIPTION_LENGTH:
        raise ChronicleUserError(f"description must be at most {MAX_DESCRIPTION_LENGTH} characters")
    inv_uid = generate_investigation_uid()
    event_id = generate_event_id()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = InvestigationCreatedPayload(
        investigation_uid=inv_uid,
        title=t,
        description=description,
        created_by=ActorRef(actor_type=actor_type, actor_id=actor_id),
    )
    event = Event(
        event_id=event_id,
        event_type=EVENT_INVESTIGATION_CREATED,
        occurred_at=now,
        recorded_at=now,
        investigation_uid=inv_uid,
        subject_uid=inv_uid,
        actor_type=actor_type,
        actor_id=actor_id,
        workspace=workspace,
        payload=payload.to_dict(),
        idempotency_key=key or None,
    )
    store.append(event)
    return (event_id, inv_uid)


def set_tier(
    store: EventStore,
    read_model: ReadModel,
    investigation_uid: str,
    tier: str,
    *,
    reason: str | None = None,
    actor_id: str = "default",
    actor_type: str = "human",
    workspace: str = "spark",
) -> str:
    """SetTier(investigation_uid, tier, reason?): validate exists and transition allowed; emit TierChanged. Returns event_id. Phase 1."""
    inv = read_model.get_investigation(investigation_uid)
    if inv is None:
        raise ChronicleUserError(
            f"investigation_uid must reference an existing investigation: {investigation_uid}"
        )
    if inv.is_archived:
        raise ChronicleUserError(
            f"investigation {investigation_uid} is archived; cannot change tier"
        )
    tier_lower = tier.strip().lower()
    if tier_lower not in VALID_TIERS:
        raise ChronicleUserError(f"tier must be one of {VALID_TIERS}, got {tier!r}")
    current = (inv.current_tier or "spark").lower()
    allowed = TIER_TRANSITIONS.get(current, ())
    if tier_lower not in allowed and tier_lower != current:
        if not allowed:
            raise ChronicleUserError(
                f"investigation is already in tier {current}; no further transitions allowed"
            )
        raise ChronicleUserError(
            f"transition from {current} to {tier_lower} not allowed; allowed: {allowed}"
        )
    if tier_lower == current:
        raise ChronicleUserError(f"investigation is already in tier {current}")
    event_id = generate_event_id()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = TierChangedPayload(
        investigation_uid=investigation_uid,
        from_tier=current,
        to_tier=tier_lower,
        reason=reason,
        changed_by=ActorRef(actor_type=actor_type, actor_id=actor_id),
    )
    event = Event(
        event_id=event_id,
        event_type=EVENT_TIER_CHANGED,
        occurred_at=now,
        recorded_at=now,
        investigation_uid=investigation_uid,
        subject_uid=investigation_uid,
        actor_type=actor_type,
        actor_id=actor_id,
        workspace=tier_lower,
        payload=payload.to_dict(),
    )
    store.append(event)
    return event_id


def archive_investigation(
    store: EventStore,
    read_model: ReadModel,
    investigation_uid: str,
    *,
    reason: str | None = None,
    actor_id: str = "default",
    actor_type: str = "human",
    workspace: str = "spark",
) -> str:
    """ArchiveInvestigation(investigation_uid): validate exists; emit InvestigationArchived. Returns event_id. Spec 1.5.1."""
    inv = read_model.get_investigation(investigation_uid)
    if inv is None:
        raise ChronicleUserError(
            f"investigation_uid must reference an existing investigation: {investigation_uid}"
        )
    if inv.is_archived:
        raise ChronicleUserError(f"investigation {investigation_uid} is already archived")
    event_id = generate_event_id()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = InvestigationArchivedPayload(
        investigation_uid=investigation_uid,
        reason=reason,
        archived_by=ActorRef(actor_type=actor_type, actor_id=actor_id),
    )
    event = Event(
        event_id=event_id,
        event_type=EVENT_INVESTIGATION_ARCHIVED,
        occurred_at=now,
        recorded_at=now,
        investigation_uid=investigation_uid,
        subject_uid=investigation_uid,
        actor_type=actor_type,
        actor_id=actor_id,
        workspace=workspace,
        payload=payload.to_dict(),
    )
    store.append(event)
    return event_id


def export_investigation(
    read_model: ReadModel,
    project_dir: Path,
    investigation_uid: str,
    output_path: Path,
) -> Path:
    """ExportInvestigation(investigation_uid): read-only; build .chronicle ZIP. Spec 4.1.1, 1.5.1."""
    if read_model.get_investigation(investigation_uid) is None:
        raise ChronicleUserError(
            f"investigation_uid must reference an existing investigation: {investigation_uid}"
        )
    return export_import_mod.export_investigation(project_dir, investigation_uid, output_path)


def export_minimal_for_claim(
    read_model: ReadModel,
    project_dir: Path,
    investigation_uid: str,
    claim_uid: str,
    output_path: Path,
) -> Path:
    """Export a minimal .chronicle for one claim (claim + evidence + links + tensions) so the verifier can validate it. P2.2.2."""
    if read_model.get_claim(claim_uid) is None:
        raise ChronicleUserError(f"claim_uid must reference an existing claim: {claim_uid}")
    return export_import_mod.export_minimal_for_claim(
        project_dir, investigation_uid, claim_uid, output_path
    )


def import_investigation(chronicle_path: Path, target_dir: Path) -> None:
    """ImportInvestigation(chronicle_file): unzip; merge or fresh. Spec 4.1.1, 1.5.1."""
    export_import_mod.import_investigation(chronicle_path, target_dir)
