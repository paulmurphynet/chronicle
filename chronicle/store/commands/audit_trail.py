"""Audit trail of human decisions: dismissals, tier transitions. E6. Phase 4: dismissals in brief."""

from datetime import UTC, datetime

from chronicle.core.events import (
    EVENT_HUMAN_CONFIRMED,
    EVENT_HUMAN_OVERRODE,
    EVENT_SUGGESTION_DISMISSED,
    EVENT_TENSION_SUGGESTION_DISMISSED,
    EVENT_TIER_CHANGED,
)
from chronicle.store.protocols import EventStore, ReadModel

# Event types that represent explicit human decisions (overrides, tier changes). E3.3: HumanOverrode, HumanConfirmed.
HUMAN_DECISION_EVENT_TYPES = frozenset(
    {
        EVENT_TIER_CHANGED,
        EVENT_SUGGESTION_DISMISSED,
        EVENT_TENSION_SUGGESTION_DISMISSED,
        EVENT_HUMAN_OVERRODE,
        EVENT_HUMAN_CONFIRMED,
    }
)

DEFAULT_AUDIT_TRAIL_LIMIT = 500
DEFAULT_DISMISSALS_FOR_BRIEF_LIMIT = 50
UNRESOLVED_TENSION_STATUSES = frozenset({"OPEN", "DISPUTED"})


def get_dismissals_relevant_to_claim(
    store: EventStore,
    read_model: ReadModel,
    investigation_uid: str,
    claim_uid: str,
    *,
    limit: int = DEFAULT_DISMISSALS_FOR_BRIEF_LIMIT,
) -> list[dict]:
    """
    Return SuggestionDismissed and TensionSuggestionDismissed events that reference the given claim.
    For reasoning brief optional section "Suggestions considered and dismissed". Phase 4.1.
    Each item: event_type, suggestion_type (for SuggestionDismissed), suggestion_ref, rationale, recorded_at, dismissed_by (optional).
    """
    events = store.read_by_investigation(investigation_uid, limit=min(limit * 5, 2000))
    result: list[dict] = []
    for ev in events:
        if ev.event_type == EVENT_SUGGESTION_DISMISSED:
            payload = ev.payload or {}
            if payload.get("claim_uid") != claim_uid:
                continue
            result.append(
                {
                    "event_type": ev.event_type,
                    "suggestion_type": payload.get("suggestion_type", "decomposition_analyzed"),
                    "suggestion_ref": payload.get("suggestion_ref", ""),
                    "rationale": payload.get("rationale"),
                    "recorded_at": ev.recorded_at,
                    "dismissed_by": payload.get("dismissed_by"),
                }
            )
        elif ev.event_type == EVENT_TENSION_SUGGESTION_DISMISSED:
            payload = ev.payload or {}
            suggestion_uid = payload.get("suggestion_uid")
            if not suggestion_uid:
                continue
            row = read_model.get_tension_suggestion(suggestion_uid)
            if not row or (row.claim_a_uid != claim_uid and row.claim_b_uid != claim_uid):
                continue
            result.append(
                {
                    "event_type": ev.event_type,
                    "suggestion_type": "tension_suggested",
                    "suggestion_ref": suggestion_uid,
                    "rationale": None,
                    "recorded_at": ev.recorded_at,
                    "dismissed_by": None,
                }
            )
        if len(result) >= limit:
            break
    result.sort(key=lambda x: x["recorded_at"], reverse=True)
    return result


def get_human_decisions_audit_trail(
    store: EventStore,
    investigation_uid: str,
    *,
    limit: int = DEFAULT_AUDIT_TRAIL_LIMIT,
) -> list[dict]:
    """
    Return events that represent human decisions (tier changes, suggestion dismissals) for an investigation.
    E6. Each item: event_id, event_type, subject_uid, payload, recorded_at.
    """
    # Read more events so we can return up to `limit` human-decision events
    events = store.read_by_investigation(investigation_uid, limit=min(limit * 10, 10_000))
    result: list[dict] = []
    for ev in events:
        if ev.event_type not in HUMAN_DECISION_EVENT_TYPES:
            continue
        result.append(
            {
                "event_id": ev.event_id,
                "event_type": ev.event_type,
                "subject_uid": ev.subject_uid,
                "payload": ev.payload or {},
                "recorded_at": ev.recorded_at,
            }
        )
        if len(result) >= limit:
            break
    return result


def get_reviewer_decision_ledger(
    store: EventStore,
    read_model: ReadModel,
    investigation_uid: str,
    *,
    limit: int = DEFAULT_AUDIT_TRAIL_LIMIT,
) -> dict:
    """Return consolidated reviewer decision ledger for one investigation.

    Includes normalized decision entries plus unresolved tensions for pre-checkpoint/pre-export review.
    """
    events = store.read_by_investigation(investigation_uid, limit=min(limit * 10, 10_000))
    decisions: list[dict] = []

    summary = {
        "total_decisions": 0,
        "tier_changed_count": 0,
        "suggestion_dismissed_count": 0,
        "tension_suggestion_dismissed_count": 0,
        "human_overrode_count": 0,
        "human_confirmed_count": 0,
    }

    def _decision_kind(event_type: str) -> str:
        return {
            EVENT_TIER_CHANGED: "tier_changed",
            EVENT_SUGGESTION_DISMISSED: "suggestion_dismissed",
            EVENT_TENSION_SUGGESTION_DISMISSED: "tension_suggestion_dismissed",
            EVENT_HUMAN_OVERRODE: "human_overrode",
            EVENT_HUMAN_CONFIRMED: "human_confirmed",
        }.get(event_type, "decision")

    for ev in events:
        if ev.event_type not in HUMAN_DECISION_EVENT_TYPES:
            continue
        payload = ev.payload or {}
        kind = _decision_kind(ev.event_type)
        target_uid = (
            payload.get("target_uid")
            or payload.get("suggestion_ref")
            or payload.get("suggestion_uid")
            or ev.subject_uid
        )
        rationale = payload.get("rationale") or payload.get("justification")
        decisions.append(
            {
                "event_id": ev.event_id,
                "event_type": ev.event_type,
                "decision_kind": kind,
                "subject_uid": ev.subject_uid,
                "target_uid": target_uid,
                "actor_id": ev.actor_id,
                "actor_type": ev.actor_type,
                "recorded_at": ev.recorded_at,
                "rationale": rationale,
                "payload": payload,
            }
        )
        summary["total_decisions"] += 1
        if kind == "tier_changed":
            summary["tier_changed_count"] += 1
        elif kind == "suggestion_dismissed":
            summary["suggestion_dismissed_count"] += 1
        elif kind == "tension_suggestion_dismissed":
            summary["tension_suggestion_dismissed_count"] += 1
        elif kind == "human_overrode":
            summary["human_overrode_count"] += 1
        elif kind == "human_confirmed":
            summary["human_confirmed_count"] += 1

        if len(decisions) >= limit:
            break

    unresolved = [
        {
            "tension_uid": t.tension_uid,
            "claim_a_uid": t.claim_a_uid,
            "claim_b_uid": t.claim_b_uid,
            "tension_kind": t.tension_kind,
            "status": t.status,
            "notes": t.notes,
            "updated_at": t.updated_at,
        }
        for t in read_model.list_tensions(investigation_uid, limit=5000)
        if t.status in UNRESOLVED_TENSION_STATUSES
    ]
    summary["unresolved_tensions_count"] = len(unresolved)

    return {
        "investigation_uid": investigation_uid,
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": summary,
        "decisions": decisions,
        "unresolved_tensions": unresolved,
    }
