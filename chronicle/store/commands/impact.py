"""Impact analysis (E4.1) and epistemic drift (E4.3)."""

from typing import Any

from chronicle.store.commands.claims import get_defensibility_score
from chronicle.store.commands.defensibility_as_of import get_defensibility_as_of
from chronicle.store.protocols import EventStore, ReadModel

# Order: better -> worse for provenance_quality and contradiction_status
_PROVENANCE_ORDER = ("strong", "medium", "weak", "challenged")
_CONTRADICTION_ORDER = ("resolved", "acknowledged", "none", "open")


def get_evidence_impact(read_model: ReadModel, evidence_uid: str) -> dict[str, Any]:
    """
    E4.1: If we retract (or remove links from) this evidence, which claims are affected
    and how does their defensibility change? Returns affected_claim_uids and per-claim
    detail: supports_from_this_evidence, challenges_from_this_evidence, current_defensibility.
    """
    if read_model.get_evidence_item(evidence_uid) is None:
        return {
            "evidence_uid": evidence_uid,
            "message": "Evidence not found",
            "affected_claim_uids": [],
            "affected_claims": [],
        }

    claim_uids = read_model.get_claim_uids_linked_to_evidence(evidence_uid)
    affected_claims: list[dict[str, Any]] = []

    for claim_uid in claim_uids:
        claim = read_model.get_claim(claim_uid)
        if claim is None or claim.current_status == "WITHDRAWN":
            continue
        supports_from_ev = 0
        challenges_from_ev = 0
        for link in read_model.get_support_for_claim(claim_uid):
            span = read_model.get_evidence_span(link.span_uid)
            if span and span.evidence_uid == evidence_uid:
                supports_from_ev += 1
        for link in read_model.get_challenges_for_claim(claim_uid):
            span = read_model.get_evidence_span(link.span_uid)
            if span and span.evidence_uid == evidence_uid:
                challenges_from_ev += 1
        if supports_from_ev == 0 and challenges_from_ev == 0:
            continue
        scorecard = get_defensibility_score(read_model, claim_uid)
        current_defensibility: dict[str, Any] = {}
        if scorecard:
            current_defensibility = {
                "provenance_quality": scorecard.provenance_quality,
                "contradiction_status": scorecard.contradiction_status,
            }
        affected_claims.append(
            {
                "claim_uid": claim_uid,
                "supports_from_this_evidence": supports_from_ev,
                "challenges_from_this_evidence": challenges_from_ev,
                "current_defensibility": current_defensibility,
            }
        )

    message = (
        f"Retracting or removing links from this evidence would affect {len(affected_claims)} claim(s); "
        "each would lose the support/challenge links listed."
    )
    return {
        "evidence_uid": evidence_uid,
        "message": message,
        "affected_claim_uids": [c["claim_uid"] for c in affected_claims],
        "affected_claims": affected_claims,
    }


def get_tension_impact(read_model: ReadModel, tension_uid: str) -> dict[str, Any]:
    """
    E4.1: If we resolve this tension, how does defensibility change for claim_a and claim_b?
    Returns claim_a_uid, claim_b_uid, current status, current defensibility for both claims,
    and a summary message.
    """
    tension = read_model.get_tension(tension_uid)
    if tension is None:
        return {
            "tension_uid": tension_uid,
            "message": "Tension not found",
            "claim_a_uid": None,
            "claim_b_uid": None,
            "current_status": None,
            "claim_a_defensibility": {},
            "claim_b_defensibility": {},
        }

    sc_a = get_defensibility_score(read_model, tension.claim_a_uid)
    sc_b = get_defensibility_score(read_model, tension.claim_b_uid)
    claim_a_defensibility: dict[str, Any] = {}
    claim_b_defensibility: dict[str, Any] = {}
    if sc_a:
        claim_a_defensibility = {
            "provenance_quality": sc_a.provenance_quality,
            "contradiction_status": sc_a.contradiction_status,
        }
    if sc_b:
        claim_b_defensibility = {
            "provenance_quality": sc_b.provenance_quality,
            "contradiction_status": sc_b.contradiction_status,
        }

    if tension.status == "OPEN":
        message = (
            "Resolving this tension (status OPEN -> RESOLVED/ACK) would remove one open "
            "contradiction for both claims; defensibility (contradiction_status) may improve for both."
        )
    else:
        message = (
            f"Tension status is {tension.status}; resolving or updating it may still change "
            "how defensibility is computed for the two claims."
        )

    return {
        "tension_uid": tension_uid,
        "message": message,
        "claim_a_uid": tension.claim_a_uid,
        "claim_b_uid": tension.claim_b_uid,
        "current_status": tension.status,
        "claim_a_defensibility": claim_a_defensibility,
        "claim_b_defensibility": claim_b_defensibility,
    }


def _quality_rank(q: str, order: tuple[str, ...]) -> int:
    """Lower rank = better. Unknown values sort last."""
    try:
        return order.index(q) if q in order else len(order)
    except (TypeError, ValueError):
        return len(order)


def get_claim_drift(
    store: EventStore,
    read_model: ReadModel,
    claim_uid: str,
    *,
    as_of_date: str | None = None,
    as_of_event_id: str | None = None,
) -> dict[str, Any] | None:
    """
    E4.3: Detect if this claim's defensibility has weakened since a point in time (as_of_date or as_of_event_id).
    Returns claim_uid, as_of_defensibility, current_defensibility, drifted (bool), message.
    None if claim not found or as_of not set correctly.
    """
    claim = read_model.get_claim(claim_uid)
    if claim is None:
        return None
    if (as_of_date is None) == (as_of_event_id is None):
        return None
    investigation_uid = claim.investigation_uid
    as_of_result = get_defensibility_as_of(
        store,
        read_model,
        investigation_uid,
        as_of_date=as_of_date,
        as_of_event_id=as_of_event_id,
    )
    if not as_of_result:
        return None
    as_of_label = as_of_result["as_of"]
    as_of_claims = as_of_result.get("claims") or []
    as_of_defensibility: dict[str, Any] = {}
    for c in as_of_claims:
        if c.get("claim_uid") == claim_uid:
            as_of_defensibility = c.get("defensibility") or {}
            break
    if not as_of_defensibility:
        return {
            "claim_uid": claim_uid,
            "as_of": as_of_label,
            "as_of_defensibility": {},
            "current_defensibility": {},
            "drifted": False,
            "message": "Claim did not exist or had no defensibility at as_of point.",
        }

    scorecard = get_defensibility_score(read_model, claim_uid)
    current_defensibility: dict[str, Any] = {}
    if scorecard:
        current_defensibility = {
            "provenance_quality": scorecard.provenance_quality,
            "contradiction_status": scorecard.contradiction_status,
        }

    pq_as_of = as_of_defensibility.get("provenance_quality") or ""
    pq_cur = current_defensibility.get("provenance_quality") or ""
    co_as_of = as_of_defensibility.get("contradiction_status") or ""
    co_cur = current_defensibility.get("contradiction_status") or ""

    # Drift = current is worse than as_of (higher rank = worse)
    rank_pq_as_of = _quality_rank(pq_as_of, _PROVENANCE_ORDER)
    rank_pq_cur = _quality_rank(pq_cur, _PROVENANCE_ORDER)
    rank_co_as_of = _quality_rank(co_as_of, _CONTRADICTION_ORDER)
    rank_co_cur = _quality_rank(co_cur, _CONTRADICTION_ORDER)
    drifted = (rank_pq_cur > rank_pq_as_of) or (rank_co_cur > rank_co_as_of)

    if drifted:
        message = (
            f"Defensibility has weakened since {as_of_label}: "
            f"provenance_quality {pq_as_of} -> {pq_cur}, "
            f"contradiction_status {co_as_of} -> {co_cur}. Review recommended."
        )
    else:
        message = f"No significant drift since {as_of_label}; defensibility unchanged or improved."

    return {
        "claim_uid": claim_uid,
        "as_of": as_of_label,
        "as_of_defensibility": as_of_defensibility,
        "current_defensibility": current_defensibility,
        "drifted": drifted,
        "message": message,
    }
