"""Full event history for an investigation. Phase 4.2: privilege logs, discovery, audit."""

from chronicle.core.events import Event
from chronicle.store.protocols import EventStore

DEFAULT_EVENT_HISTORY_LIMIT = 5000
MAX_EVENT_HISTORY_LIMIT = 20_000


def get_investigation_event_history(
    store: EventStore,
    investigation_uid: str,
    *,
    limit: int = DEFAULT_EVENT_HISTORY_LIMIT,
) -> list[dict]:
    """
    Return full event history for an investigation (who did what when).
    For privilege logs, discovery, and audit. Phase 4.2.
    Each item: event_id, event_type, occurred_at, recorded_at, investigation_uid,
    subject_uid, actor_type, actor_id, workspace, payload.
    """
    effective_limit = min(max(1, limit), MAX_EVENT_HISTORY_LIMIT)
    events = store.read_by_investigation(investigation_uid, limit=effective_limit)
    return [_event_to_export_dict(ev) for ev in events]


def _event_to_export_dict(ev: Event) -> dict:
    """Serialize event for API/export (JSON-serializable)."""
    return {
        "event_id": ev.event_id,
        "event_type": ev.event_type,
        "occurred_at": ev.occurred_at,
        "recorded_at": ev.recorded_at,
        "investigation_uid": ev.investigation_uid,
        "subject_uid": ev.subject_uid,
        "actor_type": ev.actor_type,
        "actor_id": ev.actor_id,
        "workspace": ev.workspace,
        "payload": ev.payload or {},
    }
