"""Policy compatibility: compare built-under vs viewing-under policy. Phase 9."""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from chronicle.core.policy import PolicyProfile


@dataclass
class PolicyDelta:
    """One rule difference between built_under and viewing_under policy."""

    rule: str
    built_under_value: Any
    viewing_under_value: Any
    note: str = ""


@dataclass
class PolicyCompatibilityResult:
    """Result of comparing built-under vs viewing-under policy. Phase 9.2.1."""

    built_under: str
    viewing_under: str
    deltas: list[PolicyDelta] = field(default_factory=list)
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "built_under": self.built_under,
            "viewing_under": self.viewing_under,
            "deltas": [
                {
                    "rule": delta.rule,
                    "built_under_value": delta.built_under_value,
                    "viewing_under_value": delta.viewing_under_value,
                    "note": delta.note,
                }
                for delta in self.deltas
            ],
        }
        if self.message:
            d["message"] = self.message
        return d


def get_policy_compatibility(
    built_under_profile_id: str | None,
    built_under_version: str | None,
    viewing_profile: PolicyProfile,
    load_built_under_profile: Callable[[str], PolicyProfile | None] | None = None,
) -> PolicyCompatibilityResult:
    """
    Compare built-under policy (by id) to viewing profile. Phase 9.2.2.
    If built_under_profile_id is None, returns empty deltas with message.
    If load_built_under_profile is provided and resolves the id, produces rule-level deltas.
    """
    viewing_id = viewing_profile.profile_id
    if not built_under_profile_id:
        return PolicyCompatibilityResult(
            built_under="",
            viewing_under=viewing_id,
            message="No built-under policy recorded (e.g. no checkpoint or pre–Phase 9 export).",
        )
    if built_under_profile_id == viewing_id:
        return PolicyCompatibilityResult(
            built_under=built_under_profile_id,
            viewing_under=viewing_id,
            message="Same policy; no differences.",
        )
    built_profile: PolicyProfile | None = None
    if load_built_under_profile:
        built_profile = load_built_under_profile(built_under_profile_id)
    deltas: list[PolicyDelta] = []
    if built_profile is not None:
        # MES rules: compare min_independent_sources per target_claim_type
        for mes in built_profile.mes_rules or []:
            viewing_mes = next(
                (
                    r
                    for r in (viewing_profile.mes_rules or [])
                    if r.target_claim_type == mes.target_claim_type
                ),
                None,
            )
            if viewing_mes is None:
                deltas.append(
                    PolicyDelta(
                        rule=f"MES {mes.target_claim_type}",
                        built_under_value=mes.min_independent_sources,
                        viewing_under_value=None,
                        note="Not present in viewing policy",
                    )
                )
            elif viewing_mes.min_independent_sources != mes.min_independent_sources:
                deltas.append(
                    PolicyDelta(
                        rule=f"MES {mes.target_claim_type} min_independent_sources",
                        built_under_value=mes.min_independent_sources,
                        viewing_under_value=viewing_mes.min_independent_sources,
                    )
                )
            # Phase 7: independence notes requirement
            mes_min_notes = getattr(mes, "min_sources_with_independence_notes", 0)
            view_min_notes = getattr(viewing_mes, "min_sources_with_independence_notes", 0)
            if mes_min_notes != view_min_notes:
                deltas.append(
                    PolicyDelta(
                        rule=f"MES {mes.target_claim_type} min_sources_with_independence_notes",
                        built_under_value=mes_min_notes,
                        viewing_under_value=view_min_notes,
                    )
                )
        # Checkpoint rules
        bc = built_profile.checkpoint_rules
        vc = viewing_profile.checkpoint_rules
        if bc and vc:
            if bc.requires_all_claims_typed != vc.requires_all_claims_typed:
                deltas.append(
                    PolicyDelta(
                        rule="checkpoint_rules.requires_all_claims_typed",
                        built_under_value=bc.requires_all_claims_typed,
                        viewing_under_value=vc.requires_all_claims_typed,
                    )
                )
            if bc.requires_all_tensions_addressed != vc.requires_all_tensions_addressed:
                deltas.append(
                    PolicyDelta(
                        rule="checkpoint_rules.requires_all_tensions_addressed",
                        built_under_value=bc.requires_all_tensions_addressed,
                        viewing_under_value=vc.requires_all_tensions_addressed,
                    )
                )
    return PolicyCompatibilityResult(
        built_under=built_under_profile_id,
        viewing_under=viewing_id,
        deltas=deltas,
        message=None
        if deltas
        else "Policies differ by id; rule-level comparison not available (built-under profile not loaded).",
    )
