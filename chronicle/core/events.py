"""Event envelope and event type registry. Spec Section 14.2.1."""

from dataclasses import dataclass, field
from typing import Any

# Event type strings (extend as more events are implemented)
EVENT_INVESTIGATION_CREATED = "InvestigationCreated"
EVENT_INVESTIGATION_ARCHIVED = "InvestigationArchived"
EVENT_TIER_CHANGED = "TierChanged"
EVENT_EVIDENCE_INGESTED = "EvidenceIngested"
EVENT_CLAIM_PROPOSED = "ClaimProposed"
EVENT_SPAN_ANCHORED = "SpanAnchored"
EVENT_SUPPORT_LINKED = "SupportLinked"
EVENT_SUPPORT_RETRACTED = "SupportRetracted"
EVENT_CHALLENGE_LINKED = "ChallengeLinked"
EVENT_CHALLENGE_RETRACTED = "ChallengeRetracted"
EVENT_CLAIM_TYPED = "ClaimTyped"
EVENT_CLAIM_SCOPED = "ClaimScoped"
EVENT_CLAIM_TEMPORALIZED = "ClaimTemporalized"
EVENT_CLAIM_ASSERTED = "ClaimAsserted"
EVENT_TENSION_DECLARED = "TensionDeclared"
EVENT_TENSION_SUGGESTED = "TensionSuggested"
EVENT_TENSION_SUGGESTION_DISMISSED = "TensionSuggestionDismissed"
EVENT_SUGGESTION_DISMISSED = "SuggestionDismissed"
EVENT_TENSION_STATUS_UPDATED = "TensionStatusUpdated"
EVENT_TENSION_EXCEPTION_UPDATED = "TensionExceptionUpdated"
EVENT_CLAIM_WITHDRAWN = "ClaimWithdrawn"
EVENT_CLAIM_DOWNGRADED = "ClaimDowngraded"
EVENT_CLAIM_PROMOTED_TO_SEF = "ClaimPromotedToSEF"
EVENT_CLAIM_DECOMPOSITION_ANALYZED = "ClaimDecompositionAnalyzed"
EVENT_EVIDENCE_SUPERSEDED = "EvidenceSuperseded"
EVENT_SOURCE_REGISTERED = "SourceRegistered"
EVENT_SOURCE_INDEPENDENCE_NOTES_RECORDED = "SourceIndependenceNotesRecorded"
EVENT_EVIDENCE_SOURCE_LINKED = "EvidenceSourceLinked"
EVENT_EVIDENCE_INTEGRITY_VERIFIED = "EvidenceIntegrityVerified"
EVENT_EVIDENCE_TRUST_ASSESSMENT_RECORDED = "EvidenceTrustAssessmentRecorded"
EVENT_EVIDENCE_REDACTION_RECORDED = "EvidenceRedactionRecorded"
EVENT_EVIDENCE_MARKED_REVIEWED = "EvidenceMarkedReviewed"
EVENT_CHAIN_OF_CUSTODY_REPORT_GENERATED = "ChainOfCustodyReportGenerated"
EVENT_ARTIFACT_CREATED = "ArtifactCreated"
EVENT_CHECKPOINT_CREATED = "CheckpointCreated"
EVENT_ARTIFACT_VERSION_FROZEN = "ArtifactVersionFrozen"
EVENT_HUMAN_OVERRODE = "HumanOverrode"
EVENT_HUMAN_CONFIRMED = "HumanConfirmed"

EVENT_TYPES: frozenset[str] = frozenset(
    {
        EVENT_INVESTIGATION_CREATED,
        EVENT_INVESTIGATION_ARCHIVED,
        EVENT_TIER_CHANGED,
        EVENT_EVIDENCE_INGESTED,
        EVENT_CLAIM_PROPOSED,
        EVENT_SPAN_ANCHORED,
        EVENT_SUPPORT_LINKED,
        EVENT_SUPPORT_RETRACTED,
        EVENT_CHALLENGE_LINKED,
        EVENT_CHALLENGE_RETRACTED,
        EVENT_CLAIM_TYPED,
        EVENT_CLAIM_SCOPED,
        EVENT_CLAIM_TEMPORALIZED,
        EVENT_CLAIM_ASSERTED,
        EVENT_TENSION_DECLARED,
        EVENT_TENSION_SUGGESTED,
        EVENT_TENSION_SUGGESTION_DISMISSED,
        EVENT_SUGGESTION_DISMISSED,
        EVENT_TENSION_STATUS_UPDATED,
        EVENT_TENSION_EXCEPTION_UPDATED,
        EVENT_CLAIM_WITHDRAWN,
        EVENT_CLAIM_DOWNGRADED,
        EVENT_CLAIM_PROMOTED_TO_SEF,
        EVENT_CLAIM_DECOMPOSITION_ANALYZED,
        EVENT_EVIDENCE_SUPERSEDED,
        EVENT_SOURCE_REGISTERED,
        EVENT_SOURCE_INDEPENDENCE_NOTES_RECORDED,
        EVENT_EVIDENCE_SOURCE_LINKED,
        EVENT_EVIDENCE_INTEGRITY_VERIFIED,
        EVENT_EVIDENCE_TRUST_ASSESSMENT_RECORDED,
        EVENT_EVIDENCE_REDACTION_RECORDED,
        EVENT_EVIDENCE_MARKED_REVIEWED,
        EVENT_CHAIN_OF_CUSTODY_REPORT_GENERATED,
        EVENT_ARTIFACT_CREATED,
        EVENT_CHECKPOINT_CREATED,
        EVENT_ARTIFACT_VERSION_FROZEN,
        EVENT_HUMAN_OVERRODE,
        EVENT_HUMAN_CONFIRMED,
    }
)


@dataclass
class Event:
    """Canonical event envelope. Spec Section 14.2.1."""

    event_id: str
    event_type: str
    occurred_at: str  # ISO-8601
    recorded_at: str  # ISO-8601
    investigation_uid: str
    subject_uid: str
    actor_type: str  # human | tool | system
    actor_id: str
    workspace: str  # spark | forge | vault
    policy_profile_id: str | None = None
    correlation_id: str | None = None
    causation_id: str | None = None
    envelope_version: int = 1
    payload_version: int = 1
    payload: dict[str, Any] = field(default_factory=dict)  # JSON-serializable
    idempotency_key: str | None = None
    prev_event_hash: str | None = None
    event_hash: str | None = None

    def to_row(self) -> dict[str, Any]:
        """For DB insert: keys match events table columns."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "occurred_at": self.occurred_at,
            "recorded_at": self.recorded_at,
            "investigation_uid": self.investigation_uid,
            "subject_uid": self.subject_uid,
            "actor_type": self.actor_type,
            "actor_id": self.actor_id,
            "workspace": self.workspace,
            "policy_profile_id": self.policy_profile_id,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "envelope_version": self.envelope_version,
            "payload_version": self.payload_version,
            "payload": self.payload,
            "idempotency_key": self.idempotency_key,
            "prev_event_hash": self.prev_event_hash,
            "event_hash": self.event_hash,
        }
