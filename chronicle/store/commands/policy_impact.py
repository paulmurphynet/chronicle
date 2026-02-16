"""Policy impact: what would change if we switched to another profile. E2.1."""

from pathlib import Path
from typing import Any

from chronicle.core.policy import (
    PolicyProfile,
    load_policy_profile_by_id,
)
from chronicle.store.commands.claims import get_defensibility_score
from chronicle.store.protocols import ReadModel


def _mes_rule_for_claim_type(profile: PolicyProfile, claim_type: str | None) -> tuple[int, int]:
    """Return (min_independent_sources, effective_min_support) for the claim type. Default 1, 1."""
    ct = (claim_type or "SEF").strip() or "SEF"
    for r in profile.mes_rules:
        if r.target_claim_type == ct:
            return (r.min_independent_sources, max(r.min_independent_sources, 1))
    return (1, 1)


def get_policy_impact(
    read_model: ReadModel,
    project_dir: Path,
    investigation_uid: str,
    profile_id: str,
) -> dict[str, Any]:
    """Compute impact of switching to another policy profile. E2.1.

    Returns: profile_id, display_name, claims_would_drop (count), affected_claim_uids,
    tensions_would_block (count), blocking_tension_uids, message.
    """
    target = load_policy_profile_by_id(project_dir, profile_id)
    if target is None:
        return {
            "profile_id": profile_id,
            "display_name": "",
            "message": f"Profile {profile_id} not found in project.",
            "claims_would_drop": 0,
            "affected_claim_uids": [],
            "tensions_would_block": 0,
            "blocking_tension_uids": [],
        }

    if read_model.get_investigation(investigation_uid) is None:
        raise ValueError("Investigation not found")

    claims = read_model.list_claims_by_type(
        investigation_uid=investigation_uid,
        limit=500,
        include_withdrawn=False,
    )
    affected_claim_uids: list[str] = []
    for c in claims:
        scorecard = get_defensibility_score(read_model, c.claim_uid)
        if scorecard is None:
            continue
        min_indep, min_support = _mes_rule_for_claim_type(target, c.claim_type)
        corr = scorecard.corroboration or {}
        indep = corr.get("independent_sources_count", 0) or 0
        support = corr.get("support_count", 0) or 0
        if min_indep > indep or min_support > support:
            affected_claim_uids.append(c.claim_uid)

    tensions = read_model.list_tensions(investigation_uid, limit=500)
    blocks = (target.tension_rules and target.tension_rules.blocks_vault_publication) or []
    blocking_tension_uids = [t.tension_uid for t in tensions if t.status in blocks]

    message = (
        f"Under profile '{target.display_name or profile_id}': "
        f"{len(affected_claim_uids)} claim(s) would not meet MES; "
        f"{len(blocking_tension_uids)} tension(s) would block vault publication."
    )
    return {
        "profile_id": profile_id,
        "display_name": target.display_name or profile_id,
        "message": message,
        "claims_would_drop": len(affected_claim_uids),
        "affected_claim_uids": affected_claim_uids,
        "tensions_would_block": len(blocking_tension_uids),
        "blocking_tension_uids": blocking_tension_uids,
    }
