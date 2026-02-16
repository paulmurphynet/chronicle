"""Answer-level epistemic risk and natural-language explanations. E1."""

from __future__ import annotations

from typing import Any

from chronicle.store.commands.claims import get_defensibility_score
from chronicle.store.protocols import ReadModel
from chronicle.store.read_model import DefensibilityScorecard, WeakestLink


def get_answer_epistemic_risk(
    read_model: ReadModel,
    claim_uids: list[str],
) -> dict[str, Any]:
    """Compute aggregate epistemic risk for a set of claims (e.g. an answer that cites them). E1.1.

    Returns risk_level (low | medium | high), risk_score (0.0-1.0), summary (human-readable),
    and per_claim_risk (list of { claim_uid, provenance_quality, contradiction_status, risk_contribution }).
    Claims not found or withdrawn are skipped. Empty claim_uids yields low risk.
    """
    if not claim_uids:
        return {
            "risk_level": "low",
            "risk_score": 0.0,
            "summary": "No claims referenced.",
            "per_claim_risk": [],
        }

    per_claim: list[dict[str, Any]] = []
    weak_count = 0
    challenged_count = 0
    open_tension_count = 0
    strong_count = 0
    medium_count = 0

    for uid in claim_uids:
        scorecard = get_defensibility_score(read_model, uid)
        if scorecard is None:
            continue
        contrib = "none"
        if scorecard.provenance_quality == "challenged":
            challenged_count += 1
            contrib = "challenged"
        elif scorecard.provenance_quality == "weak":
            weak_count += 1
            contrib = "weak"
        if scorecard.contradiction_status == "open":
            open_tension_count += 1
            if contrib == "none":
                contrib = "open_tension"
        if scorecard.provenance_quality == "strong":
            strong_count += 1
        elif scorecard.provenance_quality == "medium":
            medium_count += 1

        per_claim.append(
            {
                "claim_uid": uid,
                "provenance_quality": scorecard.provenance_quality,
                "contradiction_status": scorecard.contradiction_status,
                "risk_contribution": contrib,
            }
        )

    # Risk level: any challenged or open tension -> high; any weak -> medium; else low
    if challenged_count > 0 or open_tension_count > 0:
        risk_level = "high"
        risk_score = 0.85
    elif weak_count > 0:
        risk_level = "medium"
        risk_score = 0.5 + 0.1 * min(weak_count, 3)
    else:
        risk_level = "low"
        risk_score = 0.15 if (strong_count + medium_count) > 0 else 0.0

    risk_score = min(1.0, risk_score)

    # Summary sentence
    parts = []
    if challenged_count:
        parts.append(f"{challenged_count} challenged")
    if open_tension_count:
        parts.append(f"{open_tension_count} open tension(s)")
    if weak_count:
        parts.append(f"{weak_count} weak")
    if strong_count:
        parts.append(f"{strong_count} strong")
    if medium_count:
        parts.append(f"{medium_count} medium")
    summary = "; ".join(parts) if parts else "No defensibility data for referenced claims."

    return {
        "risk_level": risk_level,
        "risk_score": round(risk_score, 2),
        "summary": summary,
        "per_claim_risk": per_claim,
    }


# --- Natural-language explanations (E1.3) ---

_WEAKEST_LINK_EXPLANATIONS: dict[str, str] = {
    "add_evidence": "This claim needs more support. Add or link supporting evidence (e.g. from Reading, or link evidence to this claim in Writing). Your policy may require two independent sources for established facts.",
    "resolve_tension": "This claim has an open tension with another claim. Resolve or acknowledge the tension (Tensions page or tension API) before relying on this claim.",
    "temporalize": "Temporal context is not set for this claim. Set known_as_of or a time window so readers know when the claim was defensible.",
    "decompose": "This claim could be decomposed into sub-claims for more precise evidence links. Consider decomposing for stronger defensibility.",
    "type_claim": "Set a claim type (e.g. single-source fact, inference) so defensibility rules apply correctly.",
    "verify_evidence": "Supporting evidence has not been verified or has a hash mismatch. Verify or re-ingest evidence (Reading).",
    "none": "No critical weakness; this claim meets current defensibility thresholds.",
}


def explain_weakest_link(weakest: WeakestLink | None) -> str | None:
    """Return a one- or two-sentence explanation for the weakest link. E1.3."""
    if weakest is None:
        return None
    return _WEAKEST_LINK_EXPLANATIONS.get(
        weakest.action_hint,
        weakest.label,
    )


def explain_defensibility_dimensions(scorecard: DefensibilityScorecard | None) -> dict[str, str]:
    """Return a short explanation per dimension that needs attention. E1.3."""
    if scorecard is None:
        return {}
    out: dict[str, str] = {}
    corr = scorecard.corroboration or {}
    support_count = corr.get("support_count", 0) or 0
    independent = corr.get("independent_sources_count", 0) or 0

    if scorecard.provenance_quality == "challenged":
        out["corroboration"] = (
            "This claim is challenged by counter-evidence. Add support or address the challenges before relying on it."
        )
    elif scorecard.provenance_quality == "weak":
        out["corroboration"] = (
            "This claim has no support linked. Add evidence that supports the claim."
        )
    elif independent < 2 and support_count >= 1:
        out["corroboration"] = (
            "This claim has only one source. Your policy typically requires two independent sources for established facts. Add evidence from a second source."
        )

    if scorecard.contradiction_status == "open":
        out["contradiction"] = (
            "This claim has an open tension with another claim. Resolve or acknowledge the tension before publication or reliance."
        )

    if scorecard.temporal_validity == "unset":
        out["temporal"] = (
            "Temporal context is not set. Set known_as_of or a time window so readers know when the claim was defensible."
        )

    if getattr(scorecard, "evidence_integrity", "verified") != "verified":
        out["evidence_integrity"] = (
            "Supporting evidence is unverified or has a hash mismatch. Verify or re-ingest evidence."
        )

    if scorecard.decomposition_precision == "low":
        out["decomposition"] = (
            "Consider decomposing this claim into sub-claims for more precise evidence links."
        )

    if scorecard.attribution_posture == "UNKNOWN":
        out["attribution"] = (
            "Set a claim type (e.g. single-source fact, inference) so defensibility rules apply correctly."
        )

    # Phase 5: trust assessment gaps (evidence-trust-assessments.md)
    evidence_trust = getattr(scorecard, "evidence_trust", None)
    if evidence_trust:
        gaps: list[str] = []
        for item in evidence_trust:
            for g in item.get("required_gaps") or []:
                gaps.append(f"Evidence {item.get('evidence_uid', '')}: {g}")
        if gaps:
            out["trust_assessments"] = (
                " ".join(gaps) + ". Configure or run an assessment provider, or adjust policy."
            )

    return out
