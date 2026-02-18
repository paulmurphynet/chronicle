"""Event payload shapes per spec Section 15.1."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ActorRef:
    """Actor reference: actor_type, actor_id."""

    actor_type: str  # human | tool | system
    actor_id: str


@dataclass
class InvestigationCreatedPayload:
    """Payload for InvestigationCreated. Spec Section 15.1.20."""

    investigation_uid: str
    title: str
    description: str | None = None
    created_by: ActorRef | None = None
    tags: list[str] | None = None
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "investigation_uid": self.investigation_uid,
            "title": self.title,
        }
        if self.description is not None:
            d["description"] = self.description
        if self.created_by is not None:
            d["created_by"] = {
                "actor_type": self.created_by.actor_type,
                "actor_id": self.created_by.actor_id,
            }
        if self.tags is not None:
            d["tags"] = self.tags
        if self.notes is not None:
            d["notes"] = self.notes
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "InvestigationCreatedPayload":
        created_by = None
        if "created_by" in d and d["created_by"]:
            cb = d["created_by"]
            created_by = ActorRef(actor_type=cb["actor_type"], actor_id=cb["actor_id"])
        return cls(
            investigation_uid=d["investigation_uid"],
            title=d["title"],
            description=d.get("description"),
            created_by=created_by,
            tags=d.get("tags"),
            notes=d.get("notes"),
        )


@dataclass
class InvestigationArchivedPayload:
    """Payload for InvestigationArchived. Spec Section 15.1.21."""

    investigation_uid: str
    reason: str | None = None
    archived_by: ActorRef | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"investigation_uid": self.investigation_uid}
        if self.reason is not None:
            d["reason"] = self.reason
        if self.archived_by is not None:
            d["archived_by"] = {
                "actor_type": self.archived_by.actor_type,
                "actor_id": self.archived_by.actor_id,
            }
        return d


# Valid friction tiers. Innovation Implementation Plan Phase 1; spec friction-tiers.md.
VALID_TIERS = ("spark", "forge", "vault")
# Allowed transitions: Spark -> Forge -> Vault (no downgrade).
TIER_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "spark": ("forge",),
    "forge": ("vault",),
    "vault": (),  # no transition out of Vault
}


@dataclass
class TierChangedPayload:
    """Payload for TierChanged. Innovation Implementation Plan Phase 1."""

    investigation_uid: str
    from_tier: str  # spark | forge | vault
    to_tier: str
    reason: str | None = None
    changed_by: ActorRef | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "investigation_uid": self.investigation_uid,
            "from_tier": self.from_tier,
            "to_tier": self.to_tier,
        }
        if self.reason is not None:
            d["reason"] = self.reason
        if self.changed_by is not None:
            d["changed_by"] = {
                "actor_type": self.changed_by.actor_type,
                "actor_id": self.changed_by.actor_id,
            }
        return d


@dataclass
class EvidenceIngestedPayload:
    """Payload for EvidenceIngested. Spec Section 15.1.8. E2.3: optional provenance_type (human_created | ai_generated | unknown)."""

    evidence_uid: str
    content_hash: str
    file_size_bytes: int
    original_filename: str
    uri: str
    media_type: str
    ingest_timestamp: str  # ISO-8601
    extraction_version: str | None = None
    file_metadata: dict[str, Any] | None = None  # file_created_at, file_modified_at
    metadata: dict[str, Any] | None = None  # title, author, source, etc.
    provenance_type: str | None = None  # E2.3: human_created | ai_generated | unknown

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "evidence_uid": self.evidence_uid,
            "content_hash": self.content_hash,
            "file_size_bytes": self.file_size_bytes,
            "original_filename": self.original_filename,
            "uri": self.uri,
            "media_type": self.media_type,
            "ingest_timestamp": self.ingest_timestamp,
        }
        if self.extraction_version is not None:
            d["extraction_version"] = self.extraction_version
        if self.file_metadata is not None:
            d["file_metadata"] = self.file_metadata
        if self.metadata is not None:
            d["metadata"] = self.metadata
        if self.provenance_type is not None:
            d["provenance_type"] = self.provenance_type
        return d


@dataclass
class EvidenceRedactionRecordedPayload:
    """Payload for EvidenceRedactionRecorded. Phase C.1: optional redaction markers on evidence."""

    evidence_uid: str
    reason: str  # e.g. privilege, court_order
    redacted_at: str | None = None  # ISO-8601; default event recorded_at

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"evidence_uid": self.evidence_uid, "reason": self.reason}
        if self.redacted_at is not None:
            d["redacted_at"] = self.redacted_at
        return d


@dataclass
class EvidenceMarkedReviewedPayload:
    """Payload for EvidenceMarkedReviewed. Phase D.2: bulk mark as reviewed."""

    evidence_uid: str
    reviewed_at: str  # ISO-8601
    reviewed_by_actor_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"evidence_uid": self.evidence_uid, "reviewed_at": self.reviewed_at}
        if self.reviewed_by_actor_id is not None:
            d["reviewed_by_actor_id"] = self.reviewed_by_actor_id
        return d


@dataclass
class ClaimProposedPayload:
    """Payload for ClaimProposed. Spec Section 15.1.1."""

    claim_uid: str
    claim_text: str
    initial_type: str | None = None  # SAC|SEF|INFERENCE|UNKNOWN
    parent_claim_uid: str | None = None
    language: str | None = None
    created_by: ActorRef | None = None
    notes: str | None = None
    tags: list[str] | None = None
    epistemic_stance: str | None = None  # e.g. working_hypothesis | asserted_established

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"claim_uid": self.claim_uid, "claim_text": self.claim_text}
        if self.initial_type is not None:
            d["initial_type"] = self.initial_type
        if self.parent_claim_uid is not None:
            d["parent_claim_uid"] = self.parent_claim_uid
        if self.language is not None:
            d["language"] = self.language
        if self.created_by is not None:
            d["created_by"] = {
                "actor_type": self.created_by.actor_type,
                "actor_id": self.created_by.actor_id,
            }
        if self.notes is not None:
            d["notes"] = self.notes
        if self.tags is not None:
            d["tags"] = self.tags
        if self.epistemic_stance is not None:
            d["epistemic_stance"] = self.epistemic_stance
        return d


@dataclass
class ClaimTypedPayload:
    """Payload for ClaimTyped. Spec Section 15.1.2."""

    claim_uid: str
    claim_type: str  # SAC|SEF|INFERENCE|UNKNOWN
    rationale: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"claim_uid": self.claim_uid, "claim_type": self.claim_type}
        if self.rationale is not None:
            d["rationale"] = self.rationale
        return d


@dataclass
class ClaimScopedPayload:
    """Payload for ClaimScoped. Spec Section 15.1.3."""

    claim_uid: str
    scope: dict[str, Any]  # who, where, conditions, exclusions, domain

    def to_dict(self) -> dict[str, Any]:
        return {"claim_uid": self.claim_uid, "scope": self.scope}


@dataclass
class ClaimTemporalizedPayload:
    """Payload for ClaimTemporalized. Spec Section 15.1.4 (core + extended)."""

    claim_uid: str
    temporal: dict[str, Any]  # event_time, known_as_of, time_notes, knowable_from, ...

    def to_dict(self) -> dict[str, Any]:
        return {"claim_uid": self.claim_uid, "temporal": self.temporal}


@dataclass
class ClaimAssertedPayload:
    """Payload for ClaimAsserted. Spec Section 15.1.7."""

    assertion_uid: str
    claim_uid: str
    assertion_mode: str  # asserted|quoted|inferred|hypothetical
    confidence: float | None = None  # 0..1
    justification: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "assertion_uid": self.assertion_uid,
            "claim_uid": self.claim_uid,
            "assertion_mode": self.assertion_mode,
        }
        if self.confidence is not None:
            d["confidence"] = self.confidence
        if self.justification is not None:
            d["justification"] = self.justification
        return d


@dataclass
class TensionDeclaredPayload:
    """Payload for TensionDeclared. Spec Section 15.1.12."""

    tension_uid: str
    claim_a_uid: str
    claim_b_uid: str
    tension_kind: str | None = None
    defeater_kind: str | None = None  # Optional: rebutting | undercutting
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "tension_uid": self.tension_uid,
            "claim_a_uid": self.claim_a_uid,
            "claim_b_uid": self.claim_b_uid,
        }
        if self.tension_kind is not None:
            d["tension_kind"] = self.tension_kind
        if self.defeater_kind is not None:
            d["defeater_kind"] = self.defeater_kind
        if self.notes is not None:
            d["notes"] = self.notes
        return d


@dataclass
class TensionSuggestedPayload:
    """Payload for TensionSuggested. AI plan Phase 7 (Option B)."""

    suggestion_uid: str
    claim_a_uid: str
    claim_b_uid: str
    suggested_tension_kind: str
    confidence: float
    rationale: str
    tool_module_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "suggestion_uid": self.suggestion_uid,
            "claim_a_uid": self.claim_a_uid,
            "claim_b_uid": self.claim_b_uid,
            "suggested_tension_kind": self.suggested_tension_kind,
            "confidence": self.confidence,
            "rationale": self.rationale,
        }
        if self.tool_module_id is not None:
            d["tool_module_id"] = self.tool_module_id
        return d


@dataclass
class TensionSuggestionDismissedPayload:
    """Payload for TensionSuggestionDismissed. AI plan Phase 7."""

    suggestion_uid: str

    def to_dict(self) -> dict[str, Any]:
        return {"suggestion_uid": self.suggestion_uid}


# Suggestion types for SuggestionDismissed. Phase 2 Innovation Implementation Plan.
SUGGESTION_TYPE_TENSION = "tension_suggested"
SUGGESTION_TYPE_DECOMPOSITION = "decomposition_analyzed"
SUGGESTION_TYPES = (SUGGESTION_TYPE_TENSION, SUGGESTION_TYPE_DECOMPOSITION)


@dataclass
class SuggestionDismissedPayload:
    """Payload for SuggestionDismissed. Phase 2: human-over-machine in audit trail."""

    suggestion_type: str  # tension_suggested | decomposition_analyzed
    suggestion_ref: str  # suggestion_uid (tension) or analysis_uid/event_id (decomposition)
    claim_uid: str | None = None  # for decomposition_analyzed
    rationale: str | None = None
    dismissed_by: ActorRef | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "suggestion_type": self.suggestion_type,
            "suggestion_ref": self.suggestion_ref,
        }
        if self.claim_uid is not None:
            d["claim_uid"] = self.claim_uid
        if self.rationale is not None:
            d["rationale"] = self.rationale
        if self.dismissed_by is not None:
            d["dismissed_by"] = {
                "actor_type": self.dismissed_by.actor_type,
                "actor_id": self.dismissed_by.actor_id,
            }
        return d


@dataclass
class HumanOverrodePayload:
    """Payload for HumanOverrode. E3.3: human override of defensibility warning with required rationale."""

    claim_uid: str
    override_type: str  # e.g. defensibility_warning
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_uid": self.claim_uid,
            "override_type": self.override_type,
            "rationale": self.rationale,
        }


@dataclass
class HumanConfirmedPayload:
    """Payload for HumanConfirmed. E3.3: human confirm (e.g. publish despite weak) with required rationale."""

    scope: str  # claim | investigation
    scope_uid: str
    context: str  # e.g. publish_despite_weak, confirm_claim
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "scope": self.scope,
            "scope_uid": self.scope_uid,
            "context": self.context,
            "rationale": self.rationale,
        }


@dataclass
class TensionExceptionUpdatedPayload:
    """Payload for TensionExceptionUpdated. Phase 11: exception workflow (assigned_to, due_date, remediation_type)."""

    tension_uid: str
    assigned_to: str | None = None
    due_date: str | None = None
    remediation_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"tension_uid": self.tension_uid}
        if self.assigned_to is not None:
            d["assigned_to"] = self.assigned_to
        if self.due_date is not None:
            d["due_date"] = self.due_date
        if self.remediation_type is not None:
            d["remediation_type"] = self.remediation_type
        return d


@dataclass
class TensionStatusUpdatedPayload:
    """Payload for TensionStatusUpdated. Spec Section 15.1.13."""

    tension_uid: str
    from_status: str
    to_status: str
    reason: str | None = None
    escalated_to: str | None = None
    resolution_rationale: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "tension_uid": self.tension_uid,
            "from_status": self.from_status,
            "to_status": self.to_status,
        }
        if self.reason is not None:
            d["reason"] = self.reason
        if self.escalated_to is not None:
            d["escalated_to"] = self.escalated_to
        if self.resolution_rationale is not None:
            d["resolution_rationale"] = self.resolution_rationale
        return d


@dataclass
class SpanAnchoredPayload:
    """Payload for SpanAnchored. Spec Section 15.1.10."""

    span_uid: str
    evidence_uid: str
    anchor_type: str  # text_offset|pdf_bbox|timecode|selector
    anchor: dict[str, Any]  # e.g. {start_char, end_char} or {page, bbox, dpi}
    quote: str | None = None
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "span_uid": self.span_uid,
            "evidence_uid": self.evidence_uid,
            "anchor_type": self.anchor_type,
            "anchor": self.anchor,
        }
        if self.quote is not None:
            d["quote"] = self.quote
        if self.notes is not None:
            d["notes"] = self.notes
        return d


@dataclass
class EvidenceLinkPayload:
    """Payload for SupportLinked / ChallengeLinked. Spec Section 15.1.11."""

    link_uid: str
    claim_uid: str
    span_uid: str
    strength: float | None = None  # 0..1
    notes: str | None = None
    rationale: str | None = None  # Optional warrant: why this evidence supports/challenges this claim (evals, NLI)
    defeater_kind: str | None = None  # Optional: rebutting | undercutting (for challenge links)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "link_uid": self.link_uid,
            "claim_uid": self.claim_uid,
            "span_uid": self.span_uid,
        }
        if self.strength is not None:
            d["strength"] = self.strength
        if self.notes is not None:
            d["notes"] = self.notes
        if self.rationale is not None:
            d["rationale"] = self.rationale
        if self.defeater_kind is not None:
            d["defeater_kind"] = self.defeater_kind
        return d


@dataclass
class LinkRetractedPayload:
    """Payload for SupportRetracted / ChallengeRetracted. Phase 3 (Epistemology): retract a mistaken support or challenge link."""

    link_uid: str
    rationale: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"link_uid": self.link_uid}
        if self.rationale is not None:
            d["rationale"] = self.rationale
        return d


@dataclass
class ClaimWithdrawnPayload:
    """Payload for ClaimWithdrawn. Spec Section 15.1.5a."""

    claim_uid: str
    reason: str
    withdrawal_type: str  # retraction|erratum|superseded_by_new_claim|other
    superseded_by_claim_uid: str | None = None
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "claim_uid": self.claim_uid,
            "reason": self.reason,
            "withdrawal_type": self.withdrawal_type,
        }
        if self.superseded_by_claim_uid is not None:
            d["superseded_by_claim_uid"] = self.superseded_by_claim_uid
        if self.notes is not None:
            d["notes"] = self.notes
        return d


@dataclass
class ClaimDowngradedPayload:
    """Payload for ClaimDowngraded. Spec Section 15.1.5."""

    claim_uid: str
    from_status: str
    to_status: str
    reason: str | None = None
    trigger_type: str | None = None  # tension|policy|tool|manual
    trigger_uid: str | None = None
    trigger_event_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "claim_uid": self.claim_uid,
            "from_status": self.from_status,
            "to_status": self.to_status,
        }
        if self.reason is not None:
            d["reason"] = self.reason
        if self.trigger_type is not None:
            trigger: dict[str, Any] = {"trigger_type": self.trigger_type}
            if self.trigger_uid is not None:
                trigger["trigger_uid"] = self.trigger_uid
            if self.trigger_event_id is not None:
                trigger["trigger_event_id"] = self.trigger_event_id
            d["trigger"] = trigger
        return d


@dataclass
class ClaimPromotedToSEFPayload:
    """Payload for ClaimPromotedToSEF. Spec Section 15.1.6."""

    claim_uid: str
    rationale: str | None = None
    evidence_set_refs: list[str] | None = None
    policy_profile_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"claim_uid": self.claim_uid}
        if self.rationale is not None:
            d["rationale"] = self.rationale
        if self.evidence_set_refs is not None:
            d["evidence_set_refs"] = self.evidence_set_refs
        if self.policy_profile_id is not None:
            d["policy_profile_id"] = self.policy_profile_id
        return d


@dataclass
class EvidenceSupersededPayload:
    """Payload for EvidenceSuperseded. Spec Section 15.1.14."""

    supersession_uid: str
    new_evidence_uid: str
    prior_evidence_uid: str
    supersession_type: str  # correction|enhancement|replacement
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "supersession_uid": self.supersession_uid,
            "new_evidence_uid": self.new_evidence_uid,
            "prior_evidence_uid": self.prior_evidence_uid,
            "supersession_type": self.supersession_type,
        }
        if self.reason is not None:
            d["reason"] = self.reason
        return d


@dataclass(frozen=True)
class SuggestedSplit:
    """One suggested clause from ClaimDecompositionAnalyzed. Spec 15.1.19."""

    suggested_text: str
    source_offset_start: int | None = None
    source_offset_end: int | None = None
    confidence: float = 0.0
    rationale: str | None = None


@dataclass
class ClaimDecompositionAnalyzedPayload:
    """Payload for ClaimDecompositionAnalyzed. Spec Section 15.1.19."""

    claim_uid: str
    is_atomic: bool
    suggested_decomposition: list[SuggestedSplit]
    overall_confidence: float
    analysis_rationale: str | None = None
    tool_module_id: str = ""
    tool_module_version: str = ""
    tool_run_id: str = ""
    tool_inputs_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "claim_uid": self.claim_uid,
            "is_atomic": self.is_atomic,
            "suggested_decomposition": [
                {
                    "suggested_text": s.suggested_text,
                    **(
                        {}
                        if s.source_offset_start is None
                        else {"source_offset_start": s.source_offset_start}
                    ),
                    **(
                        {}
                        if s.source_offset_end is None
                        else {"source_offset_end": s.source_offset_end}
                    ),
                    "confidence": s.confidence,
                    **({} if s.rationale is None else {"rationale": s.rationale}),
                }
                for s in self.suggested_decomposition
            ],
            "overall_confidence": self.overall_confidence,
            "tool": {
                "module_id": self.tool_module_id,
                "module_version": self.tool_module_version,
                "run_id": self.tool_run_id,
                "inputs_hash": self.tool_inputs_hash,
            },
        }
        if self.analysis_rationale is not None:
            d["analysis_rationale"] = self.analysis_rationale
        return d


@dataclass
class SourceRegisteredPayload:
    """Payload for SourceRegistered. Spec Section 15.1.23.
    Phase 2 (Epistemology): independence_notes — optional rationale for treating this source as independent (e.g. different institution, different methods).
    reliability_notes: optional user-supplied reliability/authority metadata (we record, we don't verify).
    """

    source_uid: str
    investigation_uid: str
    display_name: str
    source_type: str  # person|organization|document|public_record|anonymous_tip|other
    alias: str | None = None
    encrypted_identity: str | None = None
    notes: str | None = None
    independence_notes: str | None = None
    reliability_notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "source_uid": self.source_uid,
            "investigation_uid": self.investigation_uid,
            "display_name": self.display_name,
            "source_type": self.source_type,
        }
        if self.alias is not None:
            d["alias"] = self.alias
        if self.encrypted_identity is not None:
            d["encrypted_identity"] = self.encrypted_identity
        if self.notes is not None:
            d["notes"] = self.notes
        if self.independence_notes is not None:
            d["independence_notes"] = self.independence_notes
        if self.reliability_notes is not None:
            d["reliability_notes"] = self.reliability_notes
        return d


@dataclass
class SourceIndependenceNotesRecordedPayload:
    """Payload for SourceIndependenceNotesRecorded. Phase 2 (Epistemology): record why this source is treated as independent (e.g. different institution, different methods)."""

    source_uid: str
    independence_notes: str | None  # None to clear

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"source_uid": self.source_uid}
        if self.independence_notes is not None:
            d["independence_notes"] = self.independence_notes
        return d


@dataclass
class EvidenceSourceLinkedPayload:
    """Payload for EvidenceSourceLinked. Spec Section 15.1.24."""

    evidence_uid: str
    source_uid: str
    relationship: str | None = None  # provided_by|authored_by|testified_to|other

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"evidence_uid": self.evidence_uid, "source_uid": self.source_uid}
        if self.relationship is not None:
            d["relationship"] = self.relationship
        return d


@dataclass
class EvidenceIntegrityVerifiedPayload:
    """Payload for EvidenceIntegrityVerified. Spec Section 15.1.22."""

    evidence_uid: str
    result: str  # VERIFIED|MODIFIED|MISSING
    expected_hash: str
    actual_hash: str | None = None
    expected_size_bytes: int = 0
    actual_size_bytes: int | None = None
    verified_at: str = ""
    discrepancies: list[str] | None = None
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "evidence_uid": self.evidence_uid,
            "result": self.result,
            "expected_hash": self.expected_hash,
            "expected_size_bytes": self.expected_size_bytes,
            "verified_at": self.verified_at,
        }
        if self.actual_hash is not None:
            d["actual_hash"] = self.actual_hash
        if self.actual_size_bytes is not None:
            d["actual_size_bytes"] = self.actual_size_bytes
        if self.discrepancies is not None:
            d["discrepancies"] = self.discrepancies
        if self.notes is not None:
            d["notes"] = self.notes
        return d


@dataclass
class EvidenceTrustAssessmentRecordedPayload:
    """Payload for EvidenceTrustAssessmentRecorded. Spec Section 15.1.22a; evidence-trust-assessments.md."""

    evidence_uid: str
    provider_id: str
    assessment_kind: str
    result: dict[str, Any]  # provider-specific, opaque JSON
    assessed_at: str  # ISO-8601
    result_expires_at: str | None = None  # ISO-8601 when assessment has validity window
    metadata: dict[str, Any] | None = None  # provider-specific (e.g. model version)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "evidence_uid": self.evidence_uid,
            "provider_id": self.provider_id,
            "assessment_kind": self.assessment_kind,
            "result": self.result,
            "assessed_at": self.assessed_at,
        }
        if self.result_expires_at is not None:
            d["result_expires_at"] = self.result_expires_at
        if self.metadata is not None:
            d["metadata"] = self.metadata
        return d


@dataclass
class ChainOfCustodyReportGeneratedPayload:
    """Payload for ChainOfCustodyReportGenerated. Spec Section 15.1.25."""

    report_uid: str
    scope: str  # evidence_item|investigation
    scope_uid: str
    format: str  # pdf|html|json
    generated_at: str
    content_hash: str
    report_uri: str
    items_included: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "report_uid": self.report_uid,
            "scope": self.scope,
            "scope_uid": self.scope_uid,
            "format": self.format,
            "generated_at": self.generated_at,
            "content_hash": self.content_hash,
            "report_uri": self.report_uri,
        }
        if self.items_included is not None:
            d["items_included"] = self.items_included
        return d


@dataclass
class ArtifactCreatedPayload:
    """Payload for ArtifactCreated. Spec Section 15.1.15."""

    artifact_uid: str
    artifact_type: str | None = None
    title: str | None = None
    created_by: ActorRef | None = None
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"artifact_uid": self.artifact_uid}
        if self.artifact_type is not None:
            d["artifact_type"] = self.artifact_type
        if self.title is not None:
            d["title"] = self.title
        if self.created_by is not None:
            d["created_by"] = {
                "actor_type": self.created_by.actor_type,
                "actor_id": self.created_by.actor_id,
            }
        if self.notes is not None:
            d["notes"] = self.notes
        return d


@dataclass
class CheckpointCreatedPayload:
    """Payload for CheckpointCreated. Spec Section 15.1.16. Phase 9: built_under policy. Phase A: policy_summary. E5.3: certification."""

    checkpoint_uid: str
    scope_refs: list[str]
    artifact_refs: list[str] | None = None
    reason: str | None = None
    built_under_policy_id: str | None = None
    built_under_policy_version: str | None = None
    policy_summary: str | None = None
    certifying_org_id: str | None = None  # E5.3: org that certified this checkpoint
    certified_at: str | None = None  # E5.3: ISO8601 when certified

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "checkpoint_uid": self.checkpoint_uid,
            "scope_refs": self.scope_refs,
        }
        if self.artifact_refs is not None:
            d["artifact_refs"] = self.artifact_refs
        if self.reason is not None:
            d["reason"] = self.reason
        if self.built_under_policy_id is not None:
            d["built_under_policy_id"] = self.built_under_policy_id
        if self.built_under_policy_version is not None:
            d["built_under_policy_version"] = self.built_under_policy_version
        if self.policy_summary is not None:
            d["policy_summary"] = self.policy_summary
        if self.certifying_org_id is not None:
            d["certifying_org_id"] = self.certifying_org_id
        if self.certified_at is not None:
            d["certified_at"] = self.certified_at
        return d


@dataclass
class ArtifactVersionFrozenPayload:
    """Payload for ArtifactVersionFrozen. Spec Section 15.1.17."""

    checkpoint_uid: str
    artifact_uid: str
    version_ref: str | None = None
    claim_refs: list[str] | None = None
    evidence_refs: list[str] | None = None
    tension_refs: list[str] | None = None
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "checkpoint_uid": self.checkpoint_uid,
            "artifact_uid": self.artifact_uid,
        }
        if self.version_ref is not None:
            d["version_ref"] = self.version_ref
        if self.claim_refs is not None:
            d["claim_refs"] = self.claim_refs
        if self.evidence_refs is not None:
            d["evidence_refs"] = self.evidence_refs
        if self.tension_refs is not None:
            d["tension_refs"] = self.tension_refs
        if self.reason is not None:
            d["reason"] = self.reason
        return d
