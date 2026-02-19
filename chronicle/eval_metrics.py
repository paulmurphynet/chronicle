"""
Eval harness adapter: stable defensibility metrics for a claim (D.2).

RAG eval frameworks can use this to record defensibility per run. The output
dict matches docs/defensibility-metrics-schema.md so harnesses can compare
runs by claim_uid and metrics.
"""

from __future__ import annotations

from typing import Any, Protocol

from chronicle.store.read_model import DefensibilityScorecard


def _stable_corroboration(corroboration: dict[str, int | float]) -> dict[str, int | float]:
    """Return only the stable corroboration keys for eval metrics."""
    stable_keys = (
        "support_count",
        "challenge_count",
        "independent_sources_count",
        "support_weighted_sum",
        "challenge_weighted_sum",
    )
    return {k: v for k, v in corroboration.items() if k in stable_keys}


def _stable_knowability(knowability: dict[str, str | None]) -> dict[str, str | None]:
    """Return only known_as_of and knowable_from."""
    return {
        "known_as_of": knowability.get("known_as_of"),
        "knowable_from": knowability.get("knowable_from"),
    }


def scorecard_to_metrics_dict(
    claim_uid: str,
    scorecard: DefensibilityScorecard,
) -> dict[str, Any]:
    """Build the stable eval-metrics dict from a DefensibilityScorecard.

    Output shape matches docs/defensibility-metrics-schema.md (claim_uid,
    provenance_quality, corroboration, contradiction_status, knowability).
    """
    out: dict[str, Any] = {
        "claim_uid": claim_uid,
        "provenance_quality": scorecard.provenance_quality,
        "corroboration": _stable_corroboration(scorecard.corroboration),
        "contradiction_status": scorecard.contradiction_status,
        "link_assurance_level": getattr(scorecard, "link_assurance_level", "unknown"),
    }
    caveat = getattr(scorecard, "link_assurance_caveat", None)
    if isinstance(caveat, str) and caveat.strip():
        out["link_assurance_caveat"] = caveat.strip()
    if scorecard.knowability:
        out["knowability"] = _stable_knowability(scorecard.knowability)
    return out


class SessionLike(Protocol):
    """Protocol for a session that can return a defensibility scorecard."""

    def get_defensibility_score(
        self,
        claim_uid: str,
        use_strength_weighting: bool = False,
    ) -> DefensibilityScorecard | None: ...


def defensibility_metrics_for_claim(
    session: SessionLike,
    claim_uid: str,
    *,
    use_strength_weighting: bool = False,
) -> dict[str, Any] | None:
    """Fetch defensibility for a claim and return the stable metrics dict.

    Returns None if the claim has no scorecard. Otherwise returns a single
    JSON-serializable dict with claim_uid and metrics (provenance_quality,
    corroboration, contradiction_status, optional knowability). Eval
    harnesses can use this as the hook to record defensibility per run.
    """
    scorecard = session.get_defensibility_score(
        claim_uid,
        use_strength_weighting=use_strength_weighting,
    )
    if scorecard is None:
        return None
    return scorecard_to_metrics_dict(claim_uid, scorecard)
