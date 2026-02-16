"""Read model dataclasses: investigation, claim, evidence, tension, etc. Spec Section 14.4."""

from dataclasses import dataclass
from typing import Any

# For get_*_including_inherited return type
LinkWithInherited = tuple["EvidenceLink", bool]


@dataclass
class Investigation:
    """One row from the investigation read model."""

    investigation_uid: str
    title: str
    description: str | None
    created_at: str
    created_by_actor_id: str
    tags_json: str | None
    is_archived: int
    updated_at: str
    current_tier: str  # spark | forge | vault. Phase 1.
    tier_changed_at: str | None  # ISO-8601 when tier was last changed. Phase 1.


@dataclass
class TierHistoryEntry:
    """One row from the tier_history read model. Phase 1."""

    investigation_uid: str
    from_tier: str
    to_tier: str
    reason: str | None
    occurred_at: str
    actor_id: str
    event_id: str


@dataclass
class EvidenceItem:
    """One row from the evidence_item read model. Spec Section 14.4.3. Phase C.1: redaction. Phase D.2: reviewed. E2.3: provenance_type."""

    evidence_uid: str
    investigation_uid: str
    created_at: str
    ingested_by_actor_id: str
    content_hash: str
    file_size_bytes: int
    original_filename: str
    uri: str
    media_type: str
    extraction_version: str | None
    file_metadata_json: str | None
    metadata_json: str | None
    integrity_status: str
    last_verified_at: str | None
    updated_at: str
    redaction_reason: str | None = None
    redaction_at: str | None = None
    reviewed_at: str | None = None
    reviewed_by_actor_id: str | None = None
    provenance_type: str | None = None  # E2.3: human_created | ai_generated | unknown


@dataclass
class Claim:
    """One row from the claim read model. Spec Section 14.4.1."""

    claim_uid: str
    investigation_uid: str
    created_at: str
    created_by_actor_id: str
    claim_text: str
    claim_type: str | None
    scope_json: str | None
    temporal_json: str | None
    current_status: str
    language: str | None
    tags_json: str | None
    notes: str | None
    parent_claim_uid: str | None
    decomposition_status: str
    updated_at: str


@dataclass
class EvidenceSpan:
    """One row from the evidence_span read model. Spec Section 14.4.4."""

    span_uid: str
    evidence_uid: str
    anchor_type: str
    anchor_json: str
    created_at: str
    created_by_actor_id: str
    source_event_id: str


@dataclass
class EvidenceLink:
    """One row from the evidence_link read model. Spec Section 14.4.5."""

    link_uid: str
    claim_uid: str
    span_uid: str
    link_type: str  # SUPPORTS|CHALLENGES
    strength: float | None
    notes: str | None
    created_at: str
    created_by_actor_id: str
    source_event_id: str


@dataclass
class ClaimAssertion:
    """One row from the claim_assertion read model. Spec Section 14.4.2."""

    assertion_uid: str
    claim_uid: str
    asserted_at: str
    actor_type: str
    actor_id: str
    assertion_mode: str
    confidence: float | None
    justification: str | None
    source_event_id: str


@dataclass
class Tension:
    """One row from the tension read model. Spec Section 14.4.6. Phase 11: exception_workflow fields optional."""

    tension_uid: str
    investigation_uid: str
    claim_a_uid: str
    claim_b_uid: str
    tension_kind: str | None
    status: str
    notes: str | None
    created_at: str
    created_by_actor_id: str
    source_event_id: str
    updated_at: str
    assigned_to: str | None = None
    due_date: str | None = None
    remediation_type: str | None = None


@dataclass
class TensionSuggestionRow:
    """One row from the tension_suggestion read model. AI plan Phase 7."""

    suggestion_uid: str
    investigation_uid: str
    claim_a_uid: str
    claim_b_uid: str
    suggested_tension_kind: str
    confidence: float
    rationale: str
    status: str  # pending | confirmed | dismissed
    tool_module_id: str | None
    created_at: str
    source_event_id: str
    updated_at: str
    confirmed_tension_uid: str | None
    dismissed_at: str | None


@dataclass
class ClaimDecomposition:
    """One row from the claim_decomposition read model. Spec Section 14.4.9."""

    analysis_uid: str
    claim_uid: str
    is_atomic: int
    overall_confidence: float | None
    analysis_rationale: str | None
    suggested_splits: str  # JSON
    analyzed_at: str
    analyzer_module_id: str
    analyzer_version: str
    run_id: str


@dataclass
class EvidenceSupersession:
    """One row from the evidence_supersession read model. Spec Section 14.4.7."""

    supersession_uid: str
    new_evidence_uid: str
    prior_evidence_uid: str
    supersession_type: str
    reason: str | None
    created_at: str
    created_by_actor_id: str
    source_event_id: str


@dataclass
class Source:
    """One row from the source read model. Spec Section 14.4.11.
    Phase 2 (Epistemology): independence_notes — optional rationale for treating this source as independent (e.g. different institution, different methods).
    """

    source_uid: str
    investigation_uid: str
    display_name: str
    source_type: str
    alias: str | None
    encrypted_identity: str | None
    notes: str | None
    independence_notes: str | None  # Phase 2: why this source is treated as independent of others
    created_at: str
    created_by_actor_id: str
    updated_at: str


@dataclass
class EvidenceSourceLink:
    """One row from the evidence_source_link read model. Spec Section 14.4.12."""

    evidence_uid: str
    source_uid: str
    relationship: str | None
    created_at: str
    source_event_id: str


@dataclass
class EvidenceTrustAssessment:
    """One row from the evidence_trust_assessment read model. Spec 14.6.3, evidence-trust-assessments.md."""

    evidence_uid: str
    provider_id: str
    assessment_kind: str
    result: dict[str, Any]
    assessed_at: str
    result_expires_at: str | None
    metadata: dict[str, Any] | None
    source_event_id: str


@dataclass
class DefensibilityScorecard:
    """Defensibility scorecard for a claim. Spec epistemic-tools 7.3, product-roadmap 9.6. Phase 4: contradiction_handling. Phase B.2: corroboration may include support_weighted_sum, challenge_weighted_sum when strength weighting used.

    Stable metrics for eval harnesses (D.1): claim_uid, provenance_quality, corroboration (support_count, challenge_count, independent_sources_count), contradiction_status, knowability. Same shape from get_defensibility_score and GET /claims/{uid}/defensibility. See docs/defensibility-metrics-schema.md."""

    claim_uid: str
    provenance_quality: str  # strong | medium | weak | challenged
    corroboration: dict[
        str, int | float
    ]  # support_count, challenge_count, independent_sources_count; optional support_weighted_sum, challenge_weighted_sum
    contradiction_status: str  # none | open | acknowledged | resolved
    temporal_validity: str  # set | unset
    attribution_posture: str  # claim_type or UNKNOWN
    decomposition_precision: str  # high | medium | low
    # Phase 4: per-tension details for "challenged and addressed" narrative
    contradiction_handling: list[
        dict[str, str | None]
    ]  # [{ tension_uid, status, rationale_or_notes, other_claim_uid }, ...]
    # Phase 5: when could we first defend this claim?
    knowability: dict[
        str, str | None
    ]  # { known_as_of: ISO8601 | null, knowable_from: "..." | null }
    # Epistemology red team #6: supporting evidence integrity (verified | unverified | mismatch)
    evidence_integrity: str = "verified"
    # Phase 5 (evidence-trust-assessments): per supporting evidence: assessments, required_gaps, warnings
    evidence_trust: list[dict[str, Any]] | None = (
        None  # [{ evidence_uid, assessments, required_gaps, warnings }, ...]
    )
    # Phase 6: risk signals for UX badges (single_origin_support, bulk_single_actor_ingest, high_contradiction_count)
    risk_signals: list[str] | None = None


@dataclass
class WeakestLink:
    """Single most vulnerable defensibility dimension for a claim. Spec epistemic-tools 7.4, Phase 3."""

    claim_uid: str
    dimension: str  # corroboration | temporal | contradiction | decomposition | attribution | none
    label: str
    action_hint: str  # add_evidence | resolve_tension | temporalize | decompose | type_claim | none


@dataclass
class Artifact:
    """One row from the artifact read model. Spec Section 14.4.13."""

    artifact_uid: str
    investigation_uid: str
    artifact_type: str | None
    title: str | None
    created_at: str
    created_by_actor_id: str
    notes: str | None
    updated_at: str


@dataclass
class Checkpoint:
    """One row from the checkpoint read model. Spec Section 14.4.14. Phase A: policy_summary. E5.3: certification."""

    checkpoint_uid: str
    investigation_uid: str
    scope_refs_json: str | None
    artifact_refs_json: str | None
    reason: str | None
    created_at: str
    created_by_actor_id: str
    policy_summary: str | None = None
    certifying_org_id: str | None = None  # E5.3: org that certified this checkpoint
    certified_at: str | None = None  # E5.3: ISO8601 when certified
