"""Policy profile and friction-tier gating. Spec policy-system.md, friction-tiers.md, index.md 1.5.1."""

import contextlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from chronicle.core.errors import ChronicleUserError

# Conventional project-level policy file (Phase 6). Active policy for the project.
POLICY_FILENAME = "policy.json"
# Directory for multiple shareable profiles (Phase 10). Files: {profile_id}.json or {profile_id}_v1.json.
POLICY_PROFILES_DIR = "policy_profiles"
# Format version for shareable profile JSON (Phase 10); enables future schema evolution.
POLICY_FORMAT_VERSION = 1

# Top-level keys in policy JSON that the core schema uses. Any other key is preserved in
# PolicyProfile.extensions for round-trip (verticals can add config without losing it). Spec: policy-system.md.
_POLICY_KNOWN_TOP_LEVEL_KEYS = frozenset(
    {
        "profile_id",
        "display_name",
        "description",
        "policy_rationale",
        "mes_rules",
        "evidence_admissibility",
        "tension_rules",
        "checkpoint_rules",
        "tier_overrides",
        "exception_workflow",
        "reference_manager_project_id",
        "reference_manager_type",
        "require_assessments",
        "warn_if_below",
        "warn_if_above",
        "trusted_providers",
        "assessment_max_age_hours",
        "ignore_expired_assessments",
        "format_version",
        "vocabulary",
        "extensions",
    }
)

# Workspace (tier) constants
WORKSPACE_SPARK = "spark"
WORKSPACE_FORGE = "forge"
WORKSPACE_VAULT = "vault"
WORKSPACES = (WORKSPACE_SPARK, WORKSPACE_FORGE, WORKSPACE_VAULT)

# Commands that require Forge or higher (rejected at Spark)
FORGE_PLUS_COMMANDS = frozenset(
    {
        "type_claim",
        "scope_claim",
        "temporalize_claim",
        "assert_claim",
        "declare_tension",
        "update_tension_status",
        "update_tension_exception",
        "supersede_evidence",
        "downgrade_claim",
        "withdraw_claim",
        "register_source",
        "link_evidence_to_source",
        "generate_chain_of_custody_report",
        "create_artifact",
    }
)

# Commands that require Vault only (rejected at Spark and Forge)
VAULT_ONLY_COMMANDS = frozenset(
    {
        "promote_to_sef",
        "create_checkpoint",
        "freeze_artifact_version",
    }
)


@dataclass
class MESRule:
    """Minimum Evidence Set rule for a target claim type (e.g. SEF)."""

    target_claim_type: str
    min_independent_sources: int
    required_evidence_types: list[str] = field(default_factory=list)
    preferred_evidence_types: list[str] = field(default_factory=list)
    disallowed_evidence_types: list[str] = field(default_factory=list)
    min_confidence: float = 0.0
    notes: str | None = None
    # Phase 7 (source-independence): require at least N sources backing the claim to have non-empty independence_notes
    min_sources_with_independence_notes: int = 0


@dataclass
class EvidenceAdmissibility:
    """Evidence admissibility for SEF promotion. T3.3: no_sef_from_ai_only (E2.4)."""

    admissible_types: list[str] = field(default_factory=list)
    inadmissible_for_sef: list[str] = field(default_factory=list)
    notes: str | None = None
    # T3.3 / E2.4: when True, SEF promotion requires at least one supporting evidence with provenance_type != ai_generated
    no_sef_from_ai_only: bool = False


@dataclass
class TensionRules:
    """Tension status rules for publication/checkpoint."""

    blocks_vault_publication: list[str] = field(default_factory=list)
    blocks_forge_export: list[str] = field(default_factory=list)
    allows_publication: list[str] = field(default_factory=list)
    requires_justification: list[str] = field(default_factory=list)
    notes: str | None = None


@dataclass
class CheckpointRules:
    """Checkpoint preconditions from policy. Phase 3: requires_tension_resolution_rationale. Epistemologists current review: warn_if_one_sided, block_checkpoint_if_one_sided."""

    requires_all_claims_typed: bool = True
    requires_all_tensions_addressed: bool = True
    requires_tension_resolution_rationale: bool = (
        False  # Phase 3: resolved/ack tensions must have non-empty notes
    )
    requires_at_least_one_sef: bool = False
    requires_chain_of_custody: bool = False
    min_decomposition_status: str | None = None  # e.g. "partially_decomposed", "compound_detected"
    # Epistemologists current review (Chen): one-sided = one source only and no challenges
    warn_if_one_sided: bool = (
        False  # when True, publication readiness includes one_sided_claim_uids and warning
    )
    block_checkpoint_if_one_sided: bool = (
        False  # when True, CreateCheckpoint fails if any scope claim is one-sided
    )
    notes: str | None = None


@dataclass
class TierOverrides:
    """Per-tier overrides (spark/forge/vault)."""

    allow_untyped_claims: bool = True
    allow_unanchored_evidence: bool = True
    require_source_registration: bool = False
    require_chain_of_custody_report: bool = False


# Evidence trust assessment policy hooks. Spec evidence-trust-assessments.md Section 4.
@dataclass
class RequireAssessmentEntry:
    """One required assessment kind (optionally from a specific provider)."""

    assessment_kind: str
    provider_id: str | None = None


@dataclass
class TrustAssessmentWarnRule:
    """Warn when latest result score is below or above threshold for an assessment kind (optional provider)."""

    assessment_kind: str
    threshold: float
    provider_id: str | None = None


@dataclass
class PolicyProfile:
    """Policy profile: MES, evidence admissibility, tension rules, checkpoint rules. Spec 6.1."""

    profile_id: str
    display_name: str = ""
    description: str = ""
    policy_rationale: str | None = None  # Optional: why thresholds were chosen (e.g. "per benchmark X")
    mes_rules: list[MESRule] = field(default_factory=list)
    evidence_admissibility: EvidenceAdmissibility | None = None
    tension_rules: TensionRules | None = None
    checkpoint_rules: CheckpointRules | None = None
    tier_overrides: dict[str, TierOverrides] = field(default_factory=dict)
    # Phase 11: when True, tensions support exception workflow fields (assigned_to, due_date, remediation_type)
    exception_workflow: bool = False
    # Phase E.3: optional link to external reference manager (Zotero/Mendeley project); metadata only, no sync
    reference_manager_project_id: str | None = None
    reference_manager_type: str | None = None  # e.g. "zotero", "mendeley"
    # Evidence trust assessments (evidence-trust-assessments.md Section 4)
    require_assessments: list[RequireAssessmentEntry] = field(default_factory=list)
    warn_if_below: list[TrustAssessmentWarnRule] = field(default_factory=list)
    warn_if_above: list[TrustAssessmentWarnRule] = field(default_factory=list)
    trusted_providers: list[str] | None = None  # if set, only these providers used for policy
    assessment_max_age_hours: float | None = (
        None  # assessments older than this ignored when evaluating
    )
    ignore_expired_assessments: bool = (
        False  # when True, result_expires_at in past => treat as missing
    )
    # Optional map: core term -> domain-specific label (e.g. defensibility -> "Report readiness"). Spec policy-system.md 6.1.6.
    vocabulary: dict[str, str] = field(default_factory=dict)
    # Vertical-specific or custom keys from profile JSON; preserved on load/save. Core ignores these for rules.
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "PolicyProfile":
        """Build profile from JSON-like dict."""
        mes_rules = []
        for r in d.get("mes_rules") or []:
            mes_rules.append(
                MESRule(
                    target_claim_type=r.get("target_claim_type", "SEF"),
                    min_independent_sources=int(r.get("min_independent_sources", 1)),
                    required_evidence_types=list(r.get("required_evidence_types") or []),
                    preferred_evidence_types=list(r.get("preferred_evidence_types") or []),
                    disallowed_evidence_types=list(r.get("disallowed_evidence_types") or []),
                    min_confidence=float(r.get("min_confidence", 0.0)),
                    notes=r.get("notes"),
                    min_sources_with_independence_notes=int(
                        r.get("min_sources_with_independence_notes", 0)
                    ),
                )
            )
        ea = d.get("evidence_admissibility")
        evidence_admissibility = None
        if ea:
            evidence_admissibility = EvidenceAdmissibility(
                admissible_types=list(ea.get("admissible_types") or []),
                inadmissible_for_sef=list(ea.get("inadmissible_for_sef") or []),
                notes=ea.get("notes"),
                no_sef_from_ai_only=bool(ea.get("no_sef_from_ai_only", False)),
            )
        tr = d.get("tension_rules")
        tension_rules = None
        if tr:
            tension_rules = TensionRules(
                blocks_vault_publication=list(tr.get("blocks_vault_publication") or []),
                blocks_forge_export=list(tr.get("blocks_forge_export") or []),
                allows_publication=list(tr.get("allows_publication") or []),
                requires_justification=list(tr.get("requires_justification") or []),
                notes=tr.get("notes"),
            )
        cr = d.get("checkpoint_rules")
        checkpoint_rules = None
        if cr:
            checkpoint_rules = CheckpointRules(
                requires_all_claims_typed=bool(cr.get("requires_all_claims_typed", True)),
                requires_all_tensions_addressed=bool(
                    cr.get("requires_all_tensions_addressed", True)
                ),
                requires_tension_resolution_rationale=bool(
                    cr.get("requires_tension_resolution_rationale", False)
                ),
                requires_at_least_one_sef=bool(cr.get("requires_at_least_one_sef", False)),
                requires_chain_of_custody=bool(cr.get("requires_chain_of_custody", False)),
                min_decomposition_status=cr.get("min_decomposition_status"),
                warn_if_one_sided=bool(cr.get("warn_if_one_sided", False)),
                block_checkpoint_if_one_sided=bool(cr.get("block_checkpoint_if_one_sided", False)),
                notes=cr.get("notes"),
            )
        tier_overrides: dict[str, TierOverrides] = {}
        for tier, to in (d.get("tier_overrides") or {}).items():
            if tier in WORKSPACES:
                tier_overrides[tier] = TierOverrides(
                    allow_untyped_claims=bool(to.get("allow_untyped_claims", True)),
                    allow_unanchored_evidence=bool(to.get("allow_unanchored_evidence", True)),
                    require_source_registration=bool(to.get("require_source_registration", False)),
                    require_chain_of_custody_report=bool(
                        to.get("require_chain_of_custody_report", False)
                    ),
                )
        require_assessments: list[RequireAssessmentEntry] = []
        for ra in d.get("require_assessments") or []:
            require_assessments.append(
                RequireAssessmentEntry(
                    assessment_kind=str(ra.get("assessment_kind", "")),
                    provider_id=ra.get("provider_id"),
                )
            )
        warn_if_below_list: list[TrustAssessmentWarnRule] = []
        for w in d.get("warn_if_below") or []:
            warn_if_below_list.append(
                TrustAssessmentWarnRule(
                    assessment_kind=str(w.get("assessment_kind", "")),
                    threshold=float(w.get("threshold", 0.0)),
                    provider_id=w.get("provider_id"),
                )
            )
        warn_if_above_list: list[TrustAssessmentWarnRule] = []
        for w in d.get("warn_if_above") or []:
            warn_if_above_list.append(
                TrustAssessmentWarnRule(
                    assessment_kind=str(w.get("assessment_kind", "")),
                    threshold=float(w.get("threshold", 0.0)),
                    provider_id=w.get("provider_id"),
                )
            )
        trusted_providers_raw = d.get("trusted_providers")
        trusted_providers: list[str] | None = (
            list(trusted_providers_raw) if isinstance(trusted_providers_raw, list) else None
        )
        assessment_max_age_raw = d.get("assessment_max_age_hours")
        assessment_max_age_hours: float | None = None
        if assessment_max_age_raw is not None:
            with contextlib.suppress(TypeError, ValueError):
                assessment_max_age_hours = float(assessment_max_age_raw)
        # Preserve unknown top-level keys in extensions for round-trip (verticals can add config).
        extensions: dict[str, Any] = dict(d.get("extensions") or {})
        for k, v in d.items():
            if k not in _POLICY_KNOWN_TOP_LEVEL_KEYS:
                extensions[k] = v
        vocab = d.get("vocabulary")
        if isinstance(vocab, dict):
            vocabulary = {str(k): str(v) for k, v in vocab.items() if isinstance(v, str)}
        else:
            vocabulary = {}
        return cls(
            profile_id=d.get("profile_id", "default"),
            display_name=d.get("display_name", ""),
            description=d.get("description", ""),
            policy_rationale=d.get("policy_rationale") or None,
            mes_rules=mes_rules,
            evidence_admissibility=evidence_admissibility,
            tension_rules=tension_rules,
            checkpoint_rules=checkpoint_rules,
            tier_overrides=tier_overrides,
            exception_workflow=bool(d.get("exception_workflow", False)),
            reference_manager_project_id=d.get("reference_manager_project_id") or None,
            reference_manager_type=d.get("reference_manager_type") or None,
            require_assessments=require_assessments,
            warn_if_below=warn_if_below_list,
            warn_if_above=warn_if_above_list,
            trusted_providers=trusted_providers,
            assessment_max_age_hours=assessment_max_age_hours,
            ignore_expired_assessments=bool(d.get("ignore_expired_assessments", False)),
            vocabulary=vocabulary,
            extensions=extensions,
        )

    def to_dict(self, include_format_version: bool = False) -> dict[str, Any]:
        """Serialize profile to JSON-serializable dict. Phase 6. Phase 10: include_format_version for export."""
        d: dict[str, Any] = {
            "profile_id": self.profile_id,
            "display_name": self.display_name,
            "description": self.description,
            "mes_rules": [
                {
                    "target_claim_type": r.target_claim_type,
                    "min_independent_sources": r.min_independent_sources,
                    "required_evidence_types": r.required_evidence_types,
                    "preferred_evidence_types": r.preferred_evidence_types,
                    "disallowed_evidence_types": r.disallowed_evidence_types,
                    "min_confidence": r.min_confidence,
                    "notes": r.notes,
                    "min_sources_with_independence_notes": r.min_sources_with_independence_notes,
                }
                for r in self.mes_rules
            ],
        }
        if self.evidence_admissibility:
            d["evidence_admissibility"] = {
                "admissible_types": self.evidence_admissibility.admissible_types,
                "inadmissible_for_sef": self.evidence_admissibility.inadmissible_for_sef,
                "notes": self.evidence_admissibility.notes,
                "no_sef_from_ai_only": self.evidence_admissibility.no_sef_from_ai_only,
            }
        if self.tension_rules:
            d["tension_rules"] = {
                "blocks_vault_publication": self.tension_rules.blocks_vault_publication,
                "blocks_forge_export": self.tension_rules.blocks_forge_export,
                "allows_publication": self.tension_rules.allows_publication,
                "requires_justification": self.tension_rules.requires_justification,
                "notes": self.tension_rules.notes,
            }
        if self.checkpoint_rules:
            d["checkpoint_rules"] = {
                "requires_all_claims_typed": self.checkpoint_rules.requires_all_claims_typed,
                "requires_all_tensions_addressed": self.checkpoint_rules.requires_all_tensions_addressed,
                "requires_tension_resolution_rationale": self.checkpoint_rules.requires_tension_resolution_rationale,
                "requires_at_least_one_sef": self.checkpoint_rules.requires_at_least_one_sef,
                "requires_chain_of_custody": self.checkpoint_rules.requires_chain_of_custody,
                "min_decomposition_status": self.checkpoint_rules.min_decomposition_status,
                "warn_if_one_sided": self.checkpoint_rules.warn_if_one_sided,
                "block_checkpoint_if_one_sided": self.checkpoint_rules.block_checkpoint_if_one_sided,
                "notes": self.checkpoint_rules.notes,
            }
        if self.tier_overrides:
            d["tier_overrides"] = {
                tier: {
                    "allow_untyped_claims": to.allow_untyped_claims,
                    "allow_unanchored_evidence": to.allow_unanchored_evidence,
                    "require_source_registration": to.require_source_registration,
                    "require_chain_of_custody_report": to.require_chain_of_custody_report,
                }
                for tier, to in self.tier_overrides.items()
            }
        if self.policy_rationale is not None:
            d["policy_rationale"] = self.policy_rationale
        if include_format_version:
            d["format_version"] = POLICY_FORMAT_VERSION
        if self.exception_workflow:
            d["exception_workflow"] = True
        if self.reference_manager_project_id is not None:
            d["reference_manager_project_id"] = self.reference_manager_project_id
        if self.reference_manager_type is not None:
            d["reference_manager_type"] = self.reference_manager_type
        if self.require_assessments:
            d["require_assessments"] = [
                {"assessment_kind": ra.assessment_kind, "provider_id": ra.provider_id}
                if ra.provider_id is not None
                else {"assessment_kind": ra.assessment_kind}
                for ra in self.require_assessments
            ]
        if self.warn_if_below:
            d["warn_if_below"] = [
                {
                    "assessment_kind": w.assessment_kind,
                    "threshold": w.threshold,
                    "provider_id": w.provider_id,
                }
                if w.provider_id is not None
                else {"assessment_kind": w.assessment_kind, "threshold": w.threshold}
                for w in self.warn_if_below
            ]
        if self.warn_if_above:
            d["warn_if_above"] = [
                {
                    "assessment_kind": w.assessment_kind,
                    "threshold": w.threshold,
                    "provider_id": w.provider_id,
                }
                if w.provider_id is not None
                else {"assessment_kind": w.assessment_kind, "threshold": w.threshold}
                for w in self.warn_if_above
            ]
        if self.trusted_providers is not None:
            d["trusted_providers"] = self.trusted_providers
        if self.assessment_max_age_hours is not None:
            d["assessment_max_age_hours"] = self.assessment_max_age_hours
        if self.ignore_expired_assessments:
            d["ignore_expired_assessments"] = True
        if self.vocabulary:
            d["vocabulary"] = self.vocabulary
        if self.extensions:
            d["extensions"] = self.extensions
        return d


def get_policy_publication_summary(profile: PolicyProfile) -> str:
    """
    Human-readable epistemic commitments: "Under this profile, we treat a claim as
    publication-ready when …". Phase 4.2 (Epistemology Implementation Plan).
    """
    parts: list[str] = []
    if profile.display_name:
        parts.append(f"Profile: {profile.display_name}.")
    parts.append("Under this profile, we treat a claim as publication-ready when:")
    bullets: list[str] = []
    for r in profile.mes_rules:
        bullet = (
            f"  • For {r.target_claim_type}: at least {r.min_independent_sources} distinct sources linked to support"
            + (f", min confidence {r.min_confidence}" if r.min_confidence else "")
        )
        if getattr(r, "min_sources_with_independence_notes", 0) > 0:
            bullet += f", at least {r.min_sources_with_independence_notes} source(s) with independence rationale recorded"
        if r.notes:
            bullet += f"; {r.notes}"
        bullets.append(bullet)
    if profile.checkpoint_rules:
        cr = profile.checkpoint_rules
        if cr.requires_all_claims_typed:
            bullets.append("  • All claims have a type (SAC/SEF/INFERENCE/UNKNOWN)")
        if cr.requires_all_tensions_addressed:
            bullets.append(
                "  • All tensions are addressed (no OPEN or DISPUTED blocking publication)"
            )
        if cr.requires_tension_resolution_rationale:
            bullets.append("  • Resolved or acknowledged tensions have a recorded rationale")
        if cr.requires_at_least_one_sef:
            bullets.append("  • At least one claim is promoted to SEF (single-source fact)")
        if cr.requires_chain_of_custody:
            bullets.append("  • Chain-of-custody requirements are met")
        if cr.min_decomposition_status:
            bullets.append(f"  • Compound claims are at least {cr.min_decomposition_status}")
    if profile.tension_rules:
        tr = profile.tension_rules
        if tr.blocks_vault_publication:
            bullets.append(
                f"  • No tension is in a blocking status for Vault: {', '.join(tr.blocks_vault_publication)}"
            )
        if tr.requires_justification:
            bullets.append(
                f"  • Tensions in {', '.join(tr.requires_justification)} have justification recorded"
            )
    if not bullets:
        bullets.append("  • (No explicit rules; check profile JSON.)")
    parts.append("\n".join(bullets))
    return "\n".join(parts)


def default_policy_profile() -> PolicyProfile:
    """Investigative journalism profile. Spec 6.1.1."""
    return PolicyProfile.from_dict(
        {
            "profile_id": "policy_investigative_journalism",
            "display_name": "Investigative Journalism Standard",
            "description": "Two-source rule, named sources preferred, tensions block publication",
            "mes_rules": [
                {
                    "target_claim_type": "SEF",
                    "min_independent_sources": 2,
                    "required_evidence_types": ["primary_document", "witness_statement"],
                    "preferred_evidence_types": ["official_record", "physical_evidence"],
                    "disallowed_evidence_types": ["anonymous_tip_alone"],
                    "min_confidence": 0.7,
                    "notes": "At least two independent sources required for established facts",
                }
            ],
            "evidence_admissibility": {
                "admissible_types": [
                    "primary_document",
                    "witness_statement",
                    "official_record",
                    "physical_evidence",
                    "expert_analysis",
                ],
                "inadmissible_for_sef": [
                    "narrator_testimony_alone",
                    "anonymous_tip_alone",
                    "social_media_unverified",
                ],
                "notes": "Anonymous tips may support SAC but never alone promote to SEF",
            },
            "tension_rules": {
                "blocks_vault_publication": ["OPEN", "DISPUTED"],
                "blocks_forge_export": [],
                "allows_publication": ["ACK", "RESOLVED", "SUPERSEDED"],
                "requires_justification": ["INTRACTABLE", "DEFERRED", "ESCALATED"],
                "notes": "Open and disputed tensions must be resolved or acknowledged before Vault publication",
            },
            "checkpoint_rules": {
                "requires_all_claims_typed": True,
                "requires_all_tensions_addressed": True,
                "requires_at_least_one_sef": False,
                "min_decomposition_status": "partially_decomposed",
                "warn_if_one_sided": False,
                "block_checkpoint_if_one_sided": False,
                "notes": "All claims must have a type, all tensions must be non-OPEN.",
            },
            "tier_overrides": {
                "spark": {"allow_untyped_claims": True, "allow_unanchored_evidence": True},
                "forge": {"allow_untyped_claims": False, "allow_unanchored_evidence": False},
                "vault": {"allow_untyped_claims": False, "allow_unanchored_evidence": False},
            },
        }
    )


def load_policy_profile(path: Path | None = None) -> PolicyProfile:
    """Load policy profile from JSON file or return default."""
    if path is not None and path.is_file():
        import json

        with open(path, encoding="utf-8") as f:
            return PolicyProfile.from_dict(json.load(f))
    return default_policy_profile()


def save_policy_profile(path: Path, profile: PolicyProfile) -> None:
    """Write policy profile to JSON file. Phase 6."""
    import json

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(profile.to_dict(), f, indent=2)


def list_policy_profiles(project_dir: Path) -> list[dict[str, Any]]:
    """List available policy profiles: policy_profiles/*.json and active policy.json. Phase 10."""
    import json

    project_dir = Path(project_dir)
    result: list[dict[str, Any]] = []
    active_path = project_dir / POLICY_FILENAME
    if active_path.is_file():
        try:
            with open(active_path, encoding="utf-8") as active_file:
                data = json.load(active_file)
            pid = data.get("profile_id", "unknown")
            result.append(
                {
                    "profile_id": pid,
                    "path": str(active_path),
                    "relative_path": POLICY_FILENAME,
                    "is_active": True,
                }
            )
        except (json.JSONDecodeError, OSError):
            pass
    profiles_dir = project_dir / POLICY_PROFILES_DIR
    if profiles_dir.is_dir():
        for f in sorted(profiles_dir.glob("*.json")):
            try:
                with open(f, encoding="utf-8") as fp:
                    data = json.load(fp)
                pid = data.get("profile_id", f.stem)
                result.append(
                    {
                        "profile_id": pid,
                        "path": str(f),
                        "relative_path": f"{POLICY_PROFILES_DIR}/{f.name}",
                        "is_active": False,
                    }
                )
            except (json.JSONDecodeError, OSError):
                continue
    return result


def _policy_profile_path_safe(project_dir: Path, candidate: Path) -> bool:
    """True if candidate path is under project_dir/policy_profiles (path traversal check)."""
    profiles_dir = (project_dir / POLICY_PROFILES_DIR).resolve()
    try:
        candidate.resolve().relative_to(profiles_dir)
        return True
    except (ValueError, OSError):
        return False


def load_policy_profile_by_id(project_dir: Path, profile_id: str) -> PolicyProfile | None:
    """Load a profile by id: active policy.json if it matches, else policy_profiles/{profile_id}.json. Phase 10."""
    project_dir = Path(project_dir)
    active_path = project_dir / POLICY_FILENAME
    if active_path.is_file():
        p = load_policy_profile(active_path)
        if p.profile_id == profile_id:
            return p
    candidates = [
        project_dir / POLICY_PROFILES_DIR / f"{profile_id}.json",
        project_dir / POLICY_PROFILES_DIR / f"{profile_id}_v1.json",
    ]
    for path in candidates:
        if path.is_file() and _policy_profile_path_safe(project_dir, path):
            return load_policy_profile(path)
    for j in (
        (project_dir / POLICY_PROFILES_DIR).glob("*.json")
        if (project_dir / POLICY_PROFILES_DIR).is_dir()
        else []
    ):
        if not _policy_profile_path_safe(project_dir, j):
            continue
        p = load_policy_profile(j)
        if p.profile_id == profile_id:
            return p
    return None


def export_policy_profile(profile: PolicyProfile, output_path: Path) -> Path:
    """Write profile to a file with format_version for sharing. Phase 10. Returns path written."""
    import json

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(profile.to_dict(include_format_version=True), f, indent=2)
    return path


def load_policy_from_file(path: Path) -> PolicyProfile:
    """Load and validate a policy from a JSON file (e.g. import). Phase 10. Raises on invalid."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Policy file not found: {path}")
    import json

    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return PolicyProfile.from_dict(data)


def import_policy_to_project(
    project_dir: Path,
    profile: PolicyProfile,
    *,
    activate: bool = False,
    overwrite: bool = True,
) -> Path:
    """Import a profile into the project: policy_profiles/{profile_id}.json; optionally set as active. Phase 10."""
    project_dir = Path(project_dir)
    profiles_dir = project_dir / POLICY_PROFILES_DIR
    profiles_dir.mkdir(parents=True, exist_ok=True)
    dest = profiles_dir / f"{profile.profile_id}.json"
    if not overwrite and dest.exists():
        raise FileExistsError(f"Profile already exists: {dest}")
    export_policy_profile(profile, dest)
    if activate:
        save_policy_profile(project_dir / POLICY_FILENAME, profile)
    return dest


def require_workspace_for_command(workspace: str, command_name: str) -> None:
    """Raise ChronicleUserError if workspace tier does not allow this command."""
    if workspace not in WORKSPACES:
        raise ChronicleUserError(f"workspace must be one of {WORKSPACES!r}, got {workspace!r}")
    if command_name in VAULT_ONLY_COMMANDS:
        if workspace != WORKSPACE_VAULT:
            raise ChronicleUserError(
                f"command {command_name!r} requires Vault workspace (got {workspace!r})"
            )
        return
    if command_name in FORGE_PLUS_COMMANDS and workspace == WORKSPACE_SPARK:
        raise ChronicleUserError(
            f"command {command_name!r} requires Forge or Vault workspace (got {workspace!r})"
        )


def validate_mes_for_sef(
    profile: PolicyProfile,
    distinct_evidence_count: int,
    evidence_types: list[str],
    max_assertion_confidence: float | None,
) -> None:
    """Raise ChronicleUserError if claim does not meet MES/admissibility for SEF."""
    mes = next((r for r in profile.mes_rules if r.target_claim_type == "SEF"), None)
    if mes is None:
        return
    if distinct_evidence_count < mes.min_independent_sources:
        raise ChronicleUserError(
            f"PromoteToSEF requires at least {mes.min_independent_sources} independent source(s) "
            f"(policy: {profile.profile_id}); got {distinct_evidence_count}"
        )
    if (
        max_assertion_confidence is not None
        and mes.min_confidence > 0
        and (max_assertion_confidence is None or max_assertion_confidence < mes.min_confidence)
    ):
        raise ChronicleUserError(
            f"PromoteToSEF requires assertion confidence >= {mes.min_confidence} "
            f"(policy: {profile.profile_id}); max confidence is {max_assertion_confidence}"
        )
    if profile.evidence_admissibility and profile.evidence_admissibility.inadmissible_for_sef:
        for et in evidence_types:
            if et in profile.evidence_admissibility.inadmissible_for_sef:
                raise ChronicleUserError(
                    f"PromoteToSEF: evidence type {et!r} is inadmissible for SEF "
                    f"(policy: {profile.profile_id})"
                )


def validate_checkpoint_scope(
    profile: PolicyProfile,
    scope_claim_uids: list[str],
    scope_tension_uids: list[str],
    claims_typed: list[bool],
    tensions_addressed: list[bool],
    investigation_has_sef: bool,
    tensions_have_rationale: list[bool] | None = None,
) -> None:
    """Raise ChronicleUserError if checkpoint scope misses policy requirements."""
    cr = profile.checkpoint_rules
    if cr is None:
        return
    if cr.requires_all_claims_typed and not all(claims_typed):
        raise ChronicleUserError(
            "CreateCheckpoint: all referenced claims must be typed (policy checkpoint_rules)"
        )
    if cr.requires_all_tensions_addressed and not all(tensions_addressed):
        raise ChronicleUserError(
            "CreateCheckpoint: all referenced tensions must be addressed / non-OPEN (policy checkpoint_rules)"
        )
    if (
        cr.requires_tension_resolution_rationale
        and tensions_have_rationale is not None
        and not all(tensions_have_rationale)
    ):
        raise ChronicleUserError(
            "CreateCheckpoint: all addressed tensions in scope must have non-empty resolution rationale (policy checkpoint_rules requires_tension_resolution_rationale)"
        )
    if cr.requires_at_least_one_sef and not investigation_has_sef:
        raise ChronicleUserError(
            "CreateCheckpoint: investigation must have at least one SEF claim (policy checkpoint_rules)"
        )


def check_publication_readiness(
    profile: PolicyProfile,
    claim_uids: list[str],
    tension_uids: list[str],
    claims_typed: list[bool],
    tensions_addressed: list[bool],
    investigation_has_sef: bool,
    one_sided_claim_uids: list[str] | None = None,
) -> dict[str, Any]:
    """Return publication-readiness checklist (no raise). Phase 3 pre-flight. All lists must align by index with claim_uids and tension_uids. Epistemologists review: one_sided_claim_uids when warn_if_one_sided or block_checkpoint_if_one_sided."""
    cr = profile.checkpoint_rules
    claims_typed_ok = not (cr and cr.requires_all_claims_typed) or all(claims_typed)
    tensions_addressed_ok = not (cr and cr.requires_all_tensions_addressed) or all(
        tensions_addressed
    )
    has_sef_ok = not (cr and cr.requires_at_least_one_sef) or investigation_has_sef
    untyped_claim_uids = [
        uid for uid, typed in zip(claim_uids, claims_typed, strict=True) if not typed
    ]
    open_tension_uids = [
        uid for uid, addr in zip(tension_uids, tensions_addressed, strict=True) if not addr
    ]
    can_create_checkpoint = claims_typed_ok and tensions_addressed_ok and has_sef_ok
    one_sided_ok = True
    one_sided_warning: str | None = None
    if cr and one_sided_claim_uids is not None:
        if cr.block_checkpoint_if_one_sided and one_sided_claim_uids:
            one_sided_ok = False
            can_create_checkpoint = False
        if (cr.warn_if_one_sided or cr.block_checkpoint_if_one_sided) and one_sided_claim_uids:
            one_sided_warning = (
                f"{len(one_sided_claim_uids)} claim(s) are one-sided (one source only, no challenges). "
                "Add evidence or record challenges, or adjust policy."
            )
    suggested_scope_refs = list(claim_uids) + list(tension_uids)
    out: dict[str, Any] = {
        "claims_typed_ok": claims_typed_ok,
        "tensions_addressed_ok": tensions_addressed_ok,
        "has_sef_ok": has_sef_ok,
        "untyped_claim_uids": untyped_claim_uids,
        "open_tension_uids": open_tension_uids,
        "can_create_checkpoint": can_create_checkpoint,
        "total_claims": len(claim_uids),
        "total_tensions": len(tension_uids),
        "suggested_scope_refs": suggested_scope_refs,
    }
    if (
        one_sided_claim_uids is not None
        and cr
        and (cr.warn_if_one_sided or cr.block_checkpoint_if_one_sided)
    ):
        out["one_sided_claim_uids"] = one_sided_claim_uids
        out["one_sided_ok"] = one_sided_ok
        if one_sided_warning:
            out["one_sided_warning"] = one_sided_warning
    return out
