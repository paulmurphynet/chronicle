"""Multi-profile defensibility: same investigation under multiple policy profiles. E5.1."""

from pathlib import Path
from typing import Any

from chronicle.core.policy import load_policy_profile_by_id
from chronicle.store.commands.claims import get_defensibility_score
from chronicle.store.commands.policy_impact import _mes_rule_for_claim_type
from chronicle.store.protocols import ReadModel


def get_defensibility_multi_profile(
    read_model: ReadModel,
    project_dir: Path,
    investigation_uid: str,
    profile_ids: list[str],
) -> dict[str, Any]:
    """
    E5.1: Return defensibility view under multiple policy profiles (e.g. "Under legal: strong. Under journalism: weak.").
    For each profile: display_name, and per claim: structural defensibility, meets_mes under this profile,
    blocking_tension_uids for this claim, and summary (strong | weak | blocked).
    """
    if read_model.get_investigation(investigation_uid) is None:
        return {
            "investigation_uid": investigation_uid,
            "message": "Investigation not found",
            "profiles": [],
        }

    claims = read_model.list_claims_by_type(
        investigation_uid=investigation_uid,
        limit=500,
        include_withdrawn=False,
    )
    tensions = read_model.list_tensions(investigation_uid, limit=500)
    claim_uid_to_tensions: dict[str, list[Any]] = {}
    for t in tensions:
        for uid in (t.claim_a_uid, t.claim_b_uid):
            claim_uid_to_tensions.setdefault(uid, []).append(t)

    profiles_out: list[dict[str, Any]] = []
    for profile_id in profile_ids:
        profile = load_policy_profile_by_id(project_dir, profile_id)
        if profile is None:
            profiles_out.append(
                {
                    "profile_id": profile_id,
                    "display_name": "",
                    "message": f"Profile {profile_id} not found",
                    "claims": [],
                }
            )
            continue
        blocks = (profile.tension_rules and profile.tension_rules.blocks_vault_publication) or []
        claims_out: list[dict[str, Any]] = []
        for c in claims:
            scorecard = get_defensibility_score(read_model, c.claim_uid)
            if scorecard is None:
                continue
            min_indep, min_support = _mes_rule_for_claim_type(profile, c.claim_type)
            corr = scorecard.corroboration or {}
            indep = corr.get("independent_sources_count", 0) or 0
            support = corr.get("support_count", 0) or 0
            meets_mes = indep >= min_indep and support >= min_support
            claim_tensions = claim_uid_to_tensions.get(c.claim_uid) or []
            blocking = [t.tension_uid for t in claim_tensions if t.status in blocks]
            if blocking:
                summary = "blocked"
            elif meets_mes:
                summary = "strong"
            else:
                summary = "weak"
            claims_out.append(
                {
                    "claim_uid": c.claim_uid,
                    "provenance_quality": scorecard.provenance_quality,
                    "contradiction_status": scorecard.contradiction_status,
                    "meets_mes": meets_mes,
                    "blocking_tension_uids": blocking,
                    "summary_under_profile": summary,
                }
            )
        profiles_out.append(
            {
                "profile_id": profile_id,
                "display_name": profile.display_name or profile_id,
                "claims": claims_out,
            }
        )

    return {
        "investigation_uid": investigation_uid,
        "profiles": profiles_out,
    }
