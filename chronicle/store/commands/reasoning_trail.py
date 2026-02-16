"""Reasoning trail export: GetReasoningTrail(claim_uid) and GetReasoningTrail(checkpoint_uid). Phase 6."""

import html
import json
from typing import Any

from chronicle.core.validation import MAX_LIST_LIMIT
from chronicle.store.protocols import EventStore, ReadModel


def _event_affects_claim(event: Any, claim_uid: str) -> bool:
    """True if this event is part of the claim's reasoning trail."""
    if event.subject_uid == claim_uid:
        return True
    payload = event.payload or {}
    if payload.get("claim_uid") == claim_uid:
        return True
    return payload.get("claim_a_uid") == claim_uid or payload.get("claim_b_uid") == claim_uid


def get_reasoning_trail_claim(
    store: EventStore,
    read_model: ReadModel,
    claim_uid: str,
    limit: int | None = None,
) -> dict[str, Any] | None:
    """GetReasoningTrail(claim_uid): ordered events that created or modified the claim, plus linked evidence/tensions. Phase 6."""
    claim = read_model.get_claim(claim_uid)
    if claim is None:
        return None
    effective_limit = min(limit, MAX_LIST_LIMIT) if limit is not None else MAX_LIST_LIMIT
    events = store.read_by_investigation(claim.investigation_uid, limit=effective_limit * 2)
    trail = [e for e in events if _event_affects_claim(e, claim_uid)]
    trail.sort(key=lambda e: (e.occurred_at, e.event_id))
    trail = trail[:effective_limit]
    return {
        "claim_uid": claim_uid,
        "investigation_uid": claim.investigation_uid,
        "events": [e.to_row() for e in trail],
    }


def get_reasoning_trail_checkpoint(
    store: EventStore,
    read_model: ReadModel,
    checkpoint_uid: str,
) -> dict[str, Any] | None:
    """GetReasoningTrail(checkpoint_uid): checkpoint snapshot and the event that created it. Phase 6."""
    checkpoint = read_model.get_checkpoint(checkpoint_uid)
    if checkpoint is None:
        return None
    creation_events = store.read_by_subject(checkpoint_uid, limit=1)
    snapshot = read_model.get_checkpoint_freeze_snapshot(checkpoint_uid)
    scope_refs = json.loads(checkpoint.scope_refs_json) if checkpoint.scope_refs_json else []
    artifact_refs = (
        json.loads(checkpoint.artifact_refs_json) if checkpoint.artifact_refs_json else []
    )
    return {
        "checkpoint_uid": checkpoint.checkpoint_uid,
        "investigation_uid": checkpoint.investigation_uid,
        "reason": checkpoint.reason,
        "created_at": checkpoint.created_at,
        "created_by_actor_id": checkpoint.created_by_actor_id,
        "scope_refs": scope_refs,
        "artifact_refs": artifact_refs,
        "snapshot": snapshot,
        "events": [e.to_row() for e in creation_events],
    }


def reasoning_trail_claim_to_html(trail: dict[str, Any]) -> str:
    """Render claim reasoning trail as HTML narrative. Phase 6."""
    lines = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Reasoning trail</title></head><body>",
        "<h1>Reasoning trail: " + html.escape(trail.get("claim_uid", "")) + "</h1>",
        "<p>Investigation: " + html.escape(trail.get("investigation_uid", "")) + "</p>",
        "<h2>Events</h2><ol>",
    ]
    for ev in trail.get("events", []):
        et = ev.get("event_type", "")
        occ = ev.get("occurred_at", "")
        payload = ev.get("payload") or {}
        if et == "ClaimProposed":
            text = (payload.get("claim_text") or "")[:200]
            lines.append(f"<li><strong>Claim proposed</strong> ({occ}). {html.escape(text)}…</li>")
        elif et == "SupportLinked":
            lines.append(f"<li><strong>Support linked</strong> ({occ}). Span → claim.</li>")
        elif et == "ChallengeLinked":
            lines.append(f"<li><strong>Challenge linked</strong> ({occ}). Span → claim.</li>")
        elif et == "ClaimTyped":
            lines.append(
                f"<li><strong>Claim typed</strong> ({occ}). Type: {html.escape(str(payload.get('claim_type', '')))}.</li>"
            )
        elif et == "ClaimTemporalized":
            lines.append(f"<li><strong>Claim temporalized</strong> ({occ}).</li>")
        elif et == "ClaimAsserted":
            lines.append(f"<li><strong>Claim asserted</strong> ({occ}).</li>")
        elif et == "TensionDeclared":
            lines.append(f"<li><strong>Tension declared</strong> ({occ}). With another claim.</li>")
        elif et == "TensionStatusUpdated":
            lines.append(f"<li><strong>Tension status updated</strong> ({occ}).</li>")
        else:
            lines.append(f"<li><strong>{html.escape(et)}</strong> ({occ}).</li>")
    lines.append("</ol></body></html>")
    return "\n".join(lines)


def reasoning_trail_checkpoint_to_html(trail: dict[str, Any]) -> str:
    """Render checkpoint reasoning trail as HTML. Phase 6."""
    lines = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Checkpoint trail</title></head><body>",
        "<h1>Checkpoint: " + html.escape(trail.get("checkpoint_uid", "")) + "</h1>",
        "<p>Created: " + html.escape(trail.get("created_at", "")) + "</p>",
        "<p>Reason: " + html.escape(trail.get("reason") or "") + "</p>",
        "<h2>Snapshot</h2><ul>",
        "<li>Claims: " + str(len(trail.get("snapshot", {}).get("claim_refs", []))) + "</li>",
        "<li>Evidence: " + str(len(trail.get("snapshot", {}).get("evidence_refs", []))) + "</li>",
        "<li>Tensions: " + str(len(trail.get("snapshot", {}).get("tension_refs", []))) + "</li>",
        "</ul></body></html>",
    ]
    return "\n".join(lines)
