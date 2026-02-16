"""Storage protocols. Spec Section 12.4."""

from typing import Protocol

from chronicle.core.events import Event

# Import for ReadModel return types (protocols is not imported by read_model, so no cycle)
from chronicle.store.read_model import (
    Artifact,
    Checkpoint,
    Claim,
    ClaimAssertion,
    ClaimDecomposition,
    EvidenceItem,
    EvidenceLink,
    EvidenceSourceLink,
    EvidenceSpan,
    EvidenceSupersession,
    EvidenceTrustAssessment,
    Investigation,
    LinkWithInherited,
    Source,
    Tension,
    TensionSuggestionRow,
    TierHistoryEntry,
)


class EventStore(Protocol):
    """Append-only event store."""

    def append(self, event: Event) -> None:
        """Append one event. Must be durable."""
        ...

    def get_event_by_idempotency_key(self, idempotency_key: str) -> Event | None:
        """Return the first event with this idempotency_key if any; else None. For exactly-once command delivery."""
        ...

    def read_all(
        self,
        after_event_id: str | None = None,
        limit: int | None = None,
    ) -> list[Event]:
        """Read events in recorded_at, event_id order."""
        ...

    def read_by_investigation(
        self,
        investigation_uid: str,
        after_event_id: str | None = None,
        limit: int | None = None,
    ) -> list[Event]:
        """Read events for one investigation in order."""
        ...

    def read_by_subject(
        self,
        subject_uid: str,
        after_event_id: str | None = None,
        limit: int | None = None,
    ) -> list[Event]:
        """Read events for one subject_uid (e.g. claim_uid) in recorded_at order. For GetClaimHistory."""
        ...


class ReadModel(Protocol):
    """Read model (projection) for queries. Implemented by SqliteReadModel and any future projection backend."""

    def get_investigation(self, uid: str) -> Investigation | None:
        """Return investigation by uid or None."""
        ...

    def list_investigations(
        self,
        *,
        limit: int | None = None,
        is_archived: bool | None = None,
        created_since: str | None = None,
        created_before: str | None = None,
    ) -> list[Investigation]:
        """Return investigations in created_at order. Optional filters: limit, is_archived, created_since, created_before (ISO8601). E.1 dashboard."""
        ...

    def list_tier_history(self, investigation_uid: str, limit: int = 100) -> list[TierHistoryEntry]:
        """List tier transitions for an investigation, newest first. Phase 1."""
        ...

    def get_evidence_item(self, uid: str) -> EvidenceItem | None:
        """Return evidence item by uid or None."""
        ...

    def list_evidence_by_investigation(
        self,
        investigation_uid: str,
        *,
        created_since: str | None = None,
        created_before: str | None = None,
        ingested_by_actor_id: str | None = None,
        limit: int | None = None,
    ) -> list[EvidenceItem]:
        """Return evidence items for an investigation in created_at order. Optional filters: created_since/created_before (ISO8601), ingested_by_actor_id, limit."""
        ...

    def get_claim(self, uid: str) -> Claim | None:
        """Return claim by uid or None."""
        ...

    def get_evidence_span(self, uid: str) -> EvidenceSpan | None:
        """Return evidence span by uid or None."""
        ...

    def get_evidence_link(self, link_uid: str) -> EvidenceLink | None:
        """Return evidence link by uid or None (includes retracted). Phase 3."""
        ...

    def get_support_for_claim(self, claim_uid: str) -> list[EvidenceLink]:
        """Return evidence links that support the claim."""
        ...

    def get_challenges_for_claim(self, claim_uid: str) -> list[EvidenceLink]:
        """Return evidence links that challenge the claim."""
        ...

    def list_claims_by_type(
        self,
        claim_type: str | None = None,
        investigation_uid: str | None = None,
        limit: int | None = None,
        include_withdrawn: bool = True,
        *,
        created_since: str | None = None,
        created_before: str | None = None,
        created_by_actor_id: str | None = None,
    ) -> list[Claim]:
        """List claims optionally filtered by type, investigation, time range, or actor. When include_withdrawn is False, only ACTIVE claims are returned (defensibility/UI default)."""
        ...

    def search_claims(
        self,
        investigation_uid: str,
        query: str,
        limit: int = 50,
    ) -> list[Claim]:
        """Full-text search claims in an investigation. Phase 8."""
        ...

    def list_story_package_tags(self, investigation_uid: str) -> list[str]:
        """Distinct tag values from claims' tags_json for story-package view. Phase E.1."""
        ...

    def list_claims_for_story_package(
        self, investigation_uid: str, tag: str, limit: int = 500
    ) -> list[Claim]:
        """Claims that have the given tag in tags_json. Phase E.1."""
        ...

    def list_evidence_uids_linked_to_claims(self, claim_uids: list[str]) -> list[str]:
        """Evidence UIDs linked to any of the given claims. Phase E.1."""
        ...

    def get_tension(self, tension_uid: str) -> Tension | None:
        """Return tension by uid or None."""
        ...

    def get_tensions_for_claim(self, claim_uid: str) -> list[Tension]:
        """Return tensions involving this claim (as claim_a or claim_b)."""
        ...

    def list_tensions(
        self,
        investigation_uid: str,
        *,
        status: str | None = None,
        limit: int = 500,
    ) -> list[Tension]:
        """Return tensions for an investigation; optional status filter. Phase 5."""
        ...

    def list_tensions_overdue(self, investigation_uid: str, limit: int = 500) -> list[Tension]:
        """Return tensions with due_date in the past and status not RESOLVED. Phase D.1."""
        ...

    def get_tension_suggestion(self, suggestion_uid: str) -> TensionSuggestionRow | None:
        """Return tension suggestion by uid. Phase 7."""
        ...

    def list_tension_suggestions(
        self,
        investigation_uid: str,
        *,
        status: str | None = "pending",
        limit: int = 500,
    ) -> list[TensionSuggestionRow]:
        """Return tension suggestions for an investigation. Phase 7."""
        ...

    def list_assertions_for_claim(self, claim_uid: str) -> list[ClaimAssertion]:
        """Return assertions for the claim (for MES confidence check)."""
        ...

    def get_child_claims(self, claim_uid: str) -> list[Claim]:
        """Return claims that have this claim as parent."""
        ...

    def get_parent_claim(self, claim_uid: str) -> Claim | None:
        """Return the parent claim if this claim is a child."""
        ...

    def get_inherited_links(self, claim_uid: str) -> list[EvidenceLink]:
        """Return evidence links attached to this claim's parent (inherited by this child)."""
        ...

    def get_support_for_claim_including_inherited(self, claim_uid: str) -> list[LinkWithInherited]:
        """Return support links for claim, with inherited from parent marked."""
        ...

    def get_challenges_for_claim_including_inherited(
        self, claim_uid: str
    ) -> list[LinkWithInherited]:
        """Return challenge links for claim, with inherited from parent marked."""
        ...

    def get_retracted_links_for_claim(self, claim_uid: str) -> list[dict]:
        """Return support/challenge links retracted for this claim (for reasoning brief retracted-links section)."""
        ...

    def get_latest_claim_decomposition(self, claim_uid: str) -> ClaimDecomposition | None:
        """Return latest decomposition analysis for claim by analyzed_at."""
        ...

    def get_claim_decomposition_by_analysis_uid(
        self, analysis_uid: str
    ) -> ClaimDecomposition | None:
        """Return claim decomposition by analysis_uid (event_id)."""
        ...

    def list_supersessions_for_evidence(self, evidence_uid: str) -> list[EvidenceSupersession]:
        """Return supersessions where evidence is prior or new."""
        ...

    def get_source(self, uid: str) -> Source | None:
        """Return source by uid or None."""
        ...

    def list_sources_by_investigation(self, investigation_uid: str) -> list[Source]:
        """Return sources for an investigation in created_at order."""
        ...

    def get_claim_uids_linked_to_evidence(self, evidence_uid: str) -> list[str]:
        """Return claim UIDs that have support or challenge links from spans on this evidence. For chain-of-custody reports."""
        ...

    def list_claim_uids_with_support_from_evidence_uids(
        self, evidence_uids: list[str]
    ) -> list[str]:
        """Return claim UIDs that have at least one support link from any of these evidence items (Phase 2: source reliability)."""
        ...

    def list_evidence_uids_for_source(self, source_uid: str) -> list[str]:
        """Return evidence UIDs linked to this source (Phase 2: source reliability)."""
        ...

    def list_evidence_source_links(self, evidence_uid: str) -> list[EvidenceSourceLink]:
        """Return evidence-source links for an evidence item (sources linked to this evidence). For chain-of-custody reports."""
        ...

    def list_assessments_for_evidence(self, evidence_uid: str) -> list[EvidenceTrustAssessment]:
        """Return all trust assessments for an evidence item (latest per provider_id, assessment_kind). Spec evidence-trust-assessments.md."""
        ...

    def get_latest_assessments_for_evidence(
        self, evidence_uid: str
    ) -> list[EvidenceTrustAssessment]:
        """Return latest trust assessment per (provider_id, assessment_kind) for this evidence. Spec evidence-trust-assessments.md."""
        ...

    def get_artifact(self, uid: str) -> Artifact | None:
        """Return artifact by uid or None."""
        ...

    def list_artifacts_by_investigation(self, investigation_uid: str) -> list[Artifact]:
        """Return artifacts for an investigation in created_at order."""
        ...

    def get_checkpoint(self, uid: str) -> Checkpoint | None:
        """Return checkpoint by uid or None. Spec 1.5.2."""
        ...

    def list_checkpoints(self, investigation_uid: str, limit: int = 500) -> list[Checkpoint]:
        """Return checkpoints for an investigation. Phase 5."""
        ...

    def is_artifact_frozen_at_checkpoint(self, checkpoint_uid: str, artifact_uid: str) -> bool:
        """Return True if this artifact is already frozen at this checkpoint."""
        ...

    def get_checkpoint_freeze_snapshot(self, checkpoint_uid: str) -> dict[str, list[str]]:
        """Aggregate claim_refs, evidence_refs, tension_refs from artifact freezes at this checkpoint. Phase 6."""
        ...


class EvidenceStore(Protocol):
    """Evidence file storage. Spec Section 12.4."""

    def store(self, evidence_uid: str, file_bytes: bytes, media_type: str) -> str:
        """Store bytes; return uri (relative path)."""
        ...

    def retrieve(self, uri: str) -> bytes:
        """Return file bytes for uri."""
        ...

    def exists(self, uri: str) -> bool:
        """Return True if uri exists."""
        ...

    def delete(self, uri: str) -> None:
        """Remove file. Reserved for future investigation hard-delete."""
        ...
