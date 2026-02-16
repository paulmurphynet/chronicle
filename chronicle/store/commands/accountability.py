"""Accountability chain for a claim: who proposed, linked evidence, declared tensions, etc. E3.1."""

from typing import Any

from chronicle.core.events import (
    EVENT_CHALLENGE_LINKED,
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
    EVENT_SUGGESTION_DISMISSED,
    EVENT_SUPPORT_LINKED,
    EVENT_TENSION_DECLARED,
    EVENT_TENSION_SUGGESTION_DISMISSED,
    Event,
)
from chronicle.store.protocols import EventStore, ReadModel

# Event types that have subject_uid == claim_uid
_CLAIM_SUBJECT_EVENTS = frozenset(
    {
        EVENT_CLAIM_PROPOSED,
        EVENT_CLAIM_TYPED,
        EVENT_CLAIM_SCOPED,
        EVENT_CLAIM_TEMPORALIZED,
        EVENT_CLAIM_ASSERTED,
        EVENT_CLAIM_WITHDRAWN,
        EVENT_CLAIM_DOWNGRADED,
        EVENT_CLAIM_PROMOTED_TO_SEF,
        EVENT_CLAIM_DECOMPOSITION_ANALYZED,
    }
)

# Map event_type -> short role label for accountability chain
_ROLE_BY_EVENT: dict[str, str] = {
    EVENT_CLAIM_PROPOSED: "proposer",
    EVENT_CLAIM_TYPED: "claim_typed",
    EVENT_CLAIM_SCOPED: "claim_scoped",
    EVENT_CLAIM_TEMPORALIZED: "claim_temporalized",
    EVENT_CLAIM_ASSERTED: "claim_asserted",
    EVENT_CLAIM_WITHDRAWN: "claim_withdrawn",
    EVENT_CLAIM_DOWNGRADED: "claim_downgraded",
    EVENT_CLAIM_PROMOTED_TO_SEF: "claim_promoted_to_sef",
    EVENT_CLAIM_DECOMPOSITION_ANALYZED: "decomposition_analyzed",
    EVENT_SUPPORT_LINKED: "support_linked",
    EVENT_CHALLENGE_LINKED: "challenge_linked",
    EVENT_TENSION_DECLARED: "tension_declared",
    EVENT_EVIDENCE_INGESTED: "evidence_ingested",
    EVENT_SUGGESTION_DISMISSED: "suggestion_dismissed",
    EVENT_TENSION_SUGGESTION_DISMISSED: "tension_suggestion_dismissed",
}

DEFAULT_ACCOUNTABILITY_LIMIT = 500
MAX_ACCOUNTABILITY_LIMIT = 2000


def get_accountability_chain(
    store: EventStore,
    read_model: ReadModel,
    claim_uid: str,
    *,
    limit: int = DEFAULT_ACCOUNTABILITY_LIMIT,
) -> list[dict[str, Any]]:
    """
    Return the chain of responsibility for a claim: proposer, support/challenge linkers,
    tension declarers, evidence ingesters (for evidence linked to this claim), suggestion dismissals.
    E3.1. Each item: role, event_type, event_id, occurred_at, actor_id, actor_type, optional detail.
    """
    claim = read_model.get_claim(claim_uid)
    if claim is None:
        return []

    investigation_uid = claim.investigation_uid
    effective_limit = min(max(1, limit), MAX_ACCOUNTABILITY_LIMIT)
    events = store.read_by_investigation(investigation_uid, limit=effective_limit * 3)

    # Evidence UIDs that are linked to this claim (via support or challenge)
    evidence_uids_linked = set(read_model.list_evidence_uids_linked_to_claims([claim_uid]))

    result: list[dict[str, Any]] = []

    for ev in events:
        role = _ROLE_BY_EVENT.get(ev.event_type)
        if role is None:
            continue

        if ev.event_type in _CLAIM_SUBJECT_EVENTS:
            if ev.subject_uid != claim_uid:
                continue
            result.append(_entry(ev, role, None))
            continue

        if ev.event_type in (EVENT_SUPPORT_LINKED, EVENT_CHALLENGE_LINKED):
            payload = ev.payload or {}
            if payload.get("claim_uid") != claim_uid:
                continue
            result.append(
                _entry(ev, role, {"link_uid": ev.subject_uid, "span_uid": payload.get("span_uid")})
            )
            continue

        if ev.event_type == EVENT_TENSION_DECLARED:
            payload = ev.payload or {}
            if payload.get("claim_a_uid") != claim_uid and payload.get("claim_b_uid") != claim_uid:
                continue
            result.append(_entry(ev, role, {"tension_uid": ev.subject_uid}))
            continue

        if ev.event_type == EVENT_EVIDENCE_INGESTED:
            if ev.subject_uid not in evidence_uids_linked:
                continue
            result.append(_entry(ev, role, {"evidence_uid": ev.subject_uid}))
            continue

        if ev.event_type == EVENT_SUGGESTION_DISMISSED:
            payload = ev.payload or {}
            if payload.get("claim_uid") != claim_uid:
                continue
            result.append(_entry(ev, role, {"suggestion_ref": payload.get("suggestion_ref")}))
            continue

        if ev.event_type == EVENT_TENSION_SUGGESTION_DISMISSED:
            payload = ev.payload or {}
            suggestion_uid = payload.get("suggestion_uid")
            if not suggestion_uid:
                continue
            row = read_model.get_tension_suggestion(suggestion_uid)
            if not row or (row.claim_a_uid != claim_uid and row.claim_b_uid != claim_uid):
                continue
            result.append(_entry(ev, role, {"suggestion_uid": suggestion_uid}))
        if len(result) >= effective_limit:
            break
    result.sort(key=lambda x: (x["occurred_at"], x["event_id"]))
    return result[:effective_limit]


def _entry(ev: Event, role: str, detail: dict[str, Any] | None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "role": role,
        "event_type": ev.event_type,
        "event_id": ev.event_id,
        "occurred_at": ev.occurred_at,
        "actor_id": ev.actor_id,
        "actor_type": ev.actor_type,
    }
    if detail:
        out["detail"] = detail
    return out
