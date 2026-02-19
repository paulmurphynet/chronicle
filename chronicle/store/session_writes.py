"""Write/command operations for ChronicleSession."""

from __future__ import annotations

# mypy: disable-error-code="attr-defined"
from pathlib import Path
from typing import Any

from chronicle.core.errors import ChronicleUserError
from chronicle.core.policy import (
    POLICY_FILENAME,
    load_policy_profile,
)
from chronicle.store.commands import (
    analyze_claim_atomicity,
    anchor_span,
    archive_investigation,
    assert_claim,
    create_artifact,
    create_checkpoint,
    create_investigation,
    declare_tension,
    decompose_claim,
    dismiss_suggestion,
    dismiss_tension_suggestion,
    downgrade_claim,
    emit_tension_suggestions,
    export_investigation,
    export_minimal_for_claim,
    freeze_artifact_version,
    generate_chain_of_custody_report,
    import_investigation,
    ingest_evidence,
    link_challenge,
    link_evidence_to_source,
    link_support,
    mark_evidence_reviewed,
    mark_evidence_reviewed_bulk,
    promote_to_sef,
    propose_claim,
    record_evidence_redaction,
    record_evidence_trust_assessment,
    record_human_confirm,
    record_human_override,
    record_source_independence_notes,
    register_source,
    retract_challenge,
    retract_support,
    scope_claim,
    set_tier,
    supersede_evidence,
    temporalize_claim,
    type_claim,
    update_tension_status,
    verify_evidence_integrity,
    withdraw_claim,
)


class ChronicleSessionWriteMixin:
    """Command/write methods mixed into ChronicleSession."""

    def create_investigation(
        self,
        title: str,
        *,
        description: str | None = None,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
        idempotency_key: str | None = None,
        investigation_key: str | None = None,
        verification_level: str | None = None,
        attestation_ref: str | None = None,
    ) -> tuple[str, str]:
        """Create investigation; returns (event_id, investigation_uid). When idempotency_key or investigation_key is set, repeated calls with the same key return the same investigation_uid (get-or-create)."""
        key = (idempotency_key or investigation_key or "").strip() or None
        return create_investigation(
            self._store,
            title,
            description=description,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
            idempotency_key=key,
            verification_level=verification_level,
            attestation_ref=attestation_ref,
        )

    def archive_investigation(
        self,
        investigation_uid: str,
        *,
        reason: str | None = None,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
        verification_level: str | None = None,
        attestation_ref: str | None = None,
    ) -> str:
        """Archive investigation; returns event_id."""
        return archive_investigation(
            self._store,
            self.read_model,
            investigation_uid,
            reason=reason,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
            verification_level=verification_level,
            attestation_ref=attestation_ref,
        )

    def set_tier(
        self,
        investigation_uid: str,
        tier: str,
        *,
        reason: str | None = None,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
        verification_level: str | None = None,
        attestation_ref: str | None = None,
    ) -> str:
        """Set investigation tier (Spark -> Forge -> Vault). Returns event_id. Phase 1."""
        return set_tier(
            self._store,
            self.read_model,
            investigation_uid,
            tier,
            reason=reason,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
            verification_level=verification_level,
            attestation_ref=attestation_ref,
        )

    def ingest_evidence(
        self,
        investigation_uid: str,
        blob: bytes,
        media_type: str,
        *,
        original_filename: str = "",
        file_metadata: dict | None = None,
        metadata: dict | None = None,
        provenance_type: str | None = None,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
        idempotency_key: str | None = None,
        verification_level: str | None = None,
        attestation_ref: str | None = None,
    ) -> tuple[str, str]:
        """Ingest evidence; returns (event_id, evidence_uid). E2.3: optional provenance_type."""
        return ingest_evidence(
            self._store,
            self._evidence,
            investigation_uid,
            blob,
            media_type,
            original_filename=original_filename,
            file_metadata=file_metadata,
            metadata=metadata,
            provenance_type=provenance_type,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
            idempotency_key=idempotency_key,
            verification_level=verification_level,
            attestation_ref=attestation_ref,
        )

    def propose_claim(
        self,
        investigation_uid: str,
        claim_text: str,
        *,
        initial_type: str | None = None,
        parent_claim_uid: str | None = None,
        notes: str | None = None,
        tags: list[str] | None = None,
        epistemic_stance: str | None = None,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
        idempotency_key: str | None = None,
        verification_level: str | None = None,
        attestation_ref: str | None = None,
    ) -> tuple[str, str]:
        """Propose a claim; returns (event_id, claim_uid)."""
        return propose_claim(
            self._store,
            investigation_uid,
            claim_text,
            initial_type=initial_type,
            parent_claim_uid=parent_claim_uid,
            notes=notes,
            tags=tags,
            epistemic_stance=epistemic_stance,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
            idempotency_key=idempotency_key,
            verification_level=verification_level,
            attestation_ref=attestation_ref,
        )

    def anchor_span(
        self,
        investigation_uid: str,
        evidence_uid: str,
        anchor_type: str,
        anchor: dict[str, Any],
        *,
        quote: str | None = None,
        notes: str | None = None,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
        idempotency_key: str | None = None,
        verification_level: str | None = None,
        attestation_ref: str | None = None,
    ) -> tuple[str, str]:
        """Anchor a span in evidence; returns (event_id, span_uid)."""
        return anchor_span(
            self._store,
            self.read_model,
            investigation_uid,
            evidence_uid,
            anchor_type,
            anchor,
            quote=quote,
            notes=notes,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
            idempotency_key=idempotency_key,
            verification_level=verification_level,
            attestation_ref=attestation_ref,
        )

    def link_support(
        self,
        investigation_uid: str,
        span_uid: str,
        claim_uid: str,
        *,
        strength: float | None = None,
        notes: str | None = None,
        rationale: str | None = None,
        defeater_kind: str | None = None,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
        idempotency_key: str | None = None,
        verification_level: str | None = None,
        attestation_ref: str | None = None,
    ) -> tuple[str, str]:
        """Link a span as supporting a claim; returns (event_id, link_uid)."""
        return link_support(
            self._store,
            self.read_model,
            investigation_uid,
            span_uid,
            claim_uid,
            strength=strength,
            notes=notes,
            rationale=rationale,
            defeater_kind=defeater_kind,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
            idempotency_key=idempotency_key,
            verification_level=verification_level,
            attestation_ref=attestation_ref,
        )

    def link_challenge(
        self,
        investigation_uid: str,
        span_uid: str,
        claim_uid: str,
        *,
        strength: float | None = None,
        notes: str | None = None,
        rationale: str | None = None,
        defeater_kind: str | None = None,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
        idempotency_key: str | None = None,
        verification_level: str | None = None,
        attestation_ref: str | None = None,
    ) -> tuple[str, str]:
        """Link a span as challenging a claim; returns (event_id, link_uid)."""
        return link_challenge(
            self._store,
            self.read_model,
            investigation_uid,
            span_uid,
            claim_uid,
            strength=strength,
            notes=notes,
            rationale=rationale,
            defeater_kind=defeater_kind,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
            idempotency_key=idempotency_key,
            verification_level=verification_level,
            attestation_ref=attestation_ref,
        )

    def retract_support(
        self,
        link_uid: str,
        *,
        rationale: str | None = None,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
    ) -> str:
        """Retract a support link (Phase 3). Returns event_id."""
        return retract_support(
            self._store,
            self.read_model,
            link_uid,
            rationale=rationale,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
        )

    def retract_challenge(
        self,
        link_uid: str,
        *,
        rationale: str | None = None,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
    ) -> str:
        """Retract a challenge link (Phase 3). Returns event_id."""
        return retract_challenge(
            self._store,
            self.read_model,
            link_uid,
            rationale=rationale,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
        )

    def type_claim(
        self,
        claim_uid: str,
        claim_type: str,
        *,
        rationale: str | None = None,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
    ) -> str:
        """Type a claim (SAC|SEF|INFERENCE|UNKNOWN); returns event_id."""
        return type_claim(
            self._store,
            self.read_model,
            claim_uid,
            claim_type,
            rationale=rationale,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
        )

    def scope_claim(
        self,
        claim_uid: str,
        scope: dict[str, Any],
        *,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
    ) -> str:
        """Set scope for a claim; returns event_id."""
        return scope_claim(
            self._store,
            self.read_model,
            claim_uid,
            scope,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
        )

    def temporalize_claim(
        self,
        claim_uid: str,
        temporal: dict[str, Any],
        *,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
    ) -> str:
        """Set temporal context for a claim; returns event_id."""
        return temporalize_claim(
            self._store,
            self.read_model,
            claim_uid,
            temporal,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
        )

    def assert_claim(
        self,
        claim_uid: str,
        posture: str,
        *,
        confidence: float | None = None,
        justification: str | None = None,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
    ) -> tuple[str, str]:
        """Assert a claim (posture: asserted|quoted|inferred|hypothetical); returns (event_id, assertion_uid)."""
        return assert_claim(
            self._store,
            self.read_model,
            claim_uid,
            posture,
            confidence=confidence,
            justification=justification,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
        )

    def declare_tension(
        self,
        investigation_uid: str,
        claim_a_uid: str,
        claim_b_uid: str,
        *,
        tension_kind: str | None = None,
        defeater_kind: str | None = None,
        notes: str | None = None,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str | None = None,
        idempotency_key: str | None = None,
        verification_level: str | None = None,
        attestation_ref: str | None = None,
    ) -> tuple[str, str]:
        """Declare a tension between two claims; returns (event_id, tension_uid)."""
        resolved_workspace = self._workspace_for_investigation(investigation_uid, workspace)
        return declare_tension(
            self._store,
            self.read_model,
            investigation_uid,
            claim_a_uid,
            claim_b_uid,
            tension_kind=tension_kind,
            defeater_kind=defeater_kind,
            notes=notes,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=resolved_workspace,
            idempotency_key=idempotency_key,
            verification_level=verification_level,
            attestation_ref=attestation_ref,
        )

    def emit_tension_suggestions(
        self,
        investigation_uid: str,
        suggestions: list[Any],
        *,
        tool_module_id: str | None = None,
        actor_id: str = "default",
        actor_type: str = "tool",
        workspace: str = "spark",
    ) -> list[str]:
        """Emit TensionSuggested events for each suggestion. Phase 7. Returns list of event_ids."""
        return emit_tension_suggestions(
            self._store,
            investigation_uid,
            suggestions,
            tool_module_id=tool_module_id,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
        )

    def dismiss_tension_suggestion(
        self,
        suggestion_uid: str,
        *,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
    ) -> str:
        """Dismiss a tension suggestion. Phase 7. Returns event_id."""
        return dismiss_tension_suggestion(
            self._store,
            self.read_model,
            suggestion_uid,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
        )

    def dismiss_suggestion(
        self,
        investigation_uid: str,
        suggestion_type: str,
        suggestion_ref: str,
        *,
        rationale: str | None = None,
        claim_uid: str | None = None,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
    ) -> str:
        """Dismiss an AI suggestion (tension or decomposition) with optional rationale. Phase 2. Returns event_id."""
        return dismiss_suggestion(
            self._store,
            self.read_model,
            investigation_uid,
            suggestion_type,
            suggestion_ref,
            rationale=rationale,
            claim_uid=claim_uid,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
        )

    def update_tension_status(
        self,
        tension_uid: str,
        to_status: str,
        *,
        reason: str | None = None,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
    ) -> str:
        """Update tension status; returns event_id. Valid transitions per event-model 2.2."""
        return update_tension_status(
            self._store,
            self.read_model,
            tension_uid,
            to_status,
            reason=reason,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
        )

    def update_tension_exception(
        self,
        tension_uid: str,
        *,
        assigned_to: str | None = None,
        due_date: str | None = None,
        remediation_type: str | None = None,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
    ) -> str:
        """Update tension exception workflow fields (Phase 11). Call only when profile has exception_workflow. Returns event_id."""
        from chronicle.store.commands.tensions import (
            update_tension_exception as cmd_update_tension_exception,
        )

        return cmd_update_tension_exception(
            self._store,
            self.read_model,
            tension_uid,
            assigned_to=assigned_to,
            due_date=due_date,
            remediation_type=remediation_type,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
        )

    def withdraw_claim(
        self,
        claim_uid: str,
        reason: str,
        *,
        withdrawal_type: str = "retraction",
        superseded_by_claim_uid: str | None = None,
        notes: str | None = None,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
    ) -> str:
        """Withdraw a claim; returns event_id."""
        return withdraw_claim(
            self._store,
            self.read_model,
            claim_uid,
            reason,
            withdrawal_type=withdrawal_type,
            superseded_by_claim_uid=superseded_by_claim_uid,
            notes=notes,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
        )

    def downgrade_claim(
        self,
        claim_uid: str,
        reason: str | None = None,
        *,
        to_status: str = "DOWNGRADED",
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
    ) -> str:
        """Downgrade a claim; returns event_id."""
        return downgrade_claim(
            self._store,
            self.read_model,
            claim_uid,
            reason,
            to_status=to_status,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
        )

    def promote_to_sef(
        self,
        claim_uid: str,
        evidence_set_refs: list[str] | None = None,
        *,
        rationale: str | None = None,
        policy_profile_id: str | None = None,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "vault",
    ) -> str:
        """Promote claim to SEF; returns event_id."""
        return promote_to_sef(
            self._store,
            self.read_model,
            claim_uid,
            evidence_set_refs=evidence_set_refs,
            rationale=rationale,
            policy_profile_id=policy_profile_id,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
            policy_profile=load_policy_profile(self._path / POLICY_FILENAME),
        )

    def decompose_claim(
        self,
        parent_uid: str,
        child_texts: list[str],
        *,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
    ) -> list[tuple[str, str]]:
        """Decompose a claim into children; returns list of (event_id, claim_uid)."""
        return decompose_claim(
            self._store,
            self.read_model,
            parent_uid,
            child_texts,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
        )

    def analyze_claim_atomicity(
        self,
        claim_uid: str,
        *,
        is_atomic: bool = True,
        suggested_decomposition: list[dict] | None = None,
        overall_confidence: float = 1.0,
        analysis_rationale: str | None = None,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
    ) -> str:
        """Record a decomposition analysis (supplied or from heuristic/LLM). For AI/heuristic-driven analysis use analyze_claim_atomicity_with_heuristic instead. Returns event_id."""
        return analyze_claim_atomicity(
            self._store,
            self.read_model,
            claim_uid,
            is_atomic=is_atomic,
            suggested_decomposition=suggested_decomposition,
            overall_confidence=overall_confidence,
            analysis_rationale=analysis_rationale,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
        )

    def analyze_claim_atomicity_with_heuristic(
        self,
        claim_uid: str,
        *,
        use_llm: bool | None = None,
        actor_id: str = "default",
        actor_type: str = "tool",
        workspace: str = "spark",
    ) -> str:
        """Run decomposer (LLM if enabled, else heuristic) and emit ClaimDecompositionAnalyzed. Returns event_id.
        use_llm: None = use config; True = prefer LLM when enabled; False = heuristic only. Phase 9."""
        from chronicle.tools.decomposer import (
            analyze_claim_atomicity_heuristic,
            analyze_claim_atomicity_llm,
        )
        from chronicle.tools.llm_client import LlmClient, LlmClientError
        from chronicle.tools.llm_config import is_llm_enabled

        claim = self.read_model.get_claim(claim_uid)
        if claim is None:
            raise ChronicleUserError(f"claim_uid must reference an existing claim: {claim_uid}")

        result = None
        tool_module_id = "chronicle.tools.decomposer.heuristic"
        try_llm = (use_llm is True) or (use_llm is None and is_llm_enabled())
        if try_llm:
            try:
                client = LlmClient()
                result = analyze_claim_atomicity_llm(claim.claim_text or "", client)
                if result is not None:
                    tool_module_id = "chronicle.tools.decomposer.ollama"
            except LlmClientError:
                pass
        if result is None:
            result = analyze_claim_atomicity_heuristic(claim.claim_text or "")

        return analyze_claim_atomicity(
            self._store,
            self.read_model,
            claim_uid,
            is_atomic=result.is_atomic,
            suggested_decomposition=result.suggested_splits,
            overall_confidence=result.overall_confidence,
            analysis_rationale=result.analysis_rationale,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
            tool_module_id=tool_module_id,
            tool_module_version="1.0",
        )

    def supersede_evidence(
        self,
        new_evidence_uid: str,
        prior_evidence_uid: str,
        supersession_type: str,
        *,
        reason: str | None = None,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
    ) -> tuple[str, str]:
        """Record evidence supersession; returns (event_id, supersession_uid)."""
        return supersede_evidence(
            self._store,
            self.read_model,
            new_evidence_uid,
            prior_evidence_uid,
            supersession_type,
            reason=reason,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
        )

    def register_source(
        self,
        investigation_uid: str,
        display_name: str,
        source_type: str,
        *,
        alias: str | None = None,
        encrypted_identity: str | None = None,
        notes: str | None = None,
        independence_notes: str | None = None,
        reliability_notes: str | None = None,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
    ) -> tuple[str, str]:
        """Register a source; returns (event_id, source_uid). Phase 2: independence_notes optional."""
        return register_source(
            self._store,
            self.read_model,
            investigation_uid,
            display_name,
            source_type,
            alias=alias,
            encrypted_identity=encrypted_identity,
            notes=notes,
            independence_notes=independence_notes,
            reliability_notes=reliability_notes,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
        )

    def link_evidence_to_source(
        self,
        evidence_uid: str,
        source_uid: str,
        *,
        relationship: str | None = None,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
    ) -> str:
        """Link evidence to a source; returns event_id."""
        return link_evidence_to_source(
            self._store,
            self.read_model,
            evidence_uid,
            source_uid,
            relationship=relationship,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
        )

    def record_source_independence_notes(
        self,
        source_uid: str,
        independence_notes: str | None,
        *,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
    ) -> str:
        """Record or clear independence notes for a source (Phase 2). Returns event_id."""
        return record_source_independence_notes(
            self._store,
            self.read_model,
            source_uid,
            independence_notes,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
        )

    def verify_evidence_integrity(
        self,
        *,
        investigation_uid: str | None = None,
        evidence_uid: str | None = None,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
    ) -> list[str]:
        """Verify evidence file integrity; returns list of event_ids."""
        return verify_evidence_integrity(
            self._store,
            self.read_model,
            self._evidence,
            investigation_uid=investigation_uid,
            evidence_uid=evidence_uid,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
        )

    def record_evidence_redaction(
        self,
        evidence_uid: str,
        reason: str,
        *,
        redacted_at: str | None = None,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
    ) -> str:
        """Record redaction on an evidence item (e.g. privilege). Phase C.1. Returns event_id."""
        return record_evidence_redaction(
            self._store,
            self.read_model,
            evidence_uid,
            reason,
            redacted_at=redacted_at,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
        )

    def record_evidence_trust_assessment(
        self,
        investigation_uid: str,
        evidence_uid: str,
        provider_id: str,
        assessment_kind: str,
        result: dict[str, Any],
        assessed_at: str,
        *,
        result_expires_at: str | None = None,
        metadata: dict[str, Any] | None = None,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
    ) -> str:
        """Record a trust assessment for an evidence item. Spec evidence-trust-assessments.md. Returns event_id."""
        return record_evidence_trust_assessment(
            self._store,
            self.read_model,
            investigation_uid,
            evidence_uid,
            provider_id,
            assessment_kind,
            result,
            assessed_at,
            result_expires_at=result_expires_at,
            metadata=metadata,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
        )

    def record_human_override(
        self,
        claim_uid: str,
        override_type: str,
        rationale: str,
        *,
        actor_id: str = "default",
        actor_type: str = "human",
    ) -> str:
        """E3.3: Record HumanOverrode (e.g. override defensibility warning). rationale required. Returns event_id."""
        return record_human_override(
            self._store,
            self.read_model,
            claim_uid,
            override_type,
            rationale,
            actor_id=actor_id,
            actor_type=actor_type,
        )

    def record_human_confirm(
        self,
        scope: str,
        scope_uid: str,
        context: str,
        rationale: str,
        *,
        actor_id: str = "default",
        actor_type: str = "human",
    ) -> str:
        """E3.3: Record HumanConfirmed (e.g. publish despite weak). rationale required. Returns event_id."""
        return record_human_confirm(
            self._store,
            self.read_model,
            scope,
            scope_uid,
            context,
            rationale,
            actor_id=actor_id,
            actor_type=actor_type,
        )

    def mark_evidence_reviewed(
        self,
        evidence_uid: str,
        *,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
    ) -> str:
        """Mark one evidence item as reviewed. Phase D.2. Returns event_id."""
        return mark_evidence_reviewed(
            self._store,
            self.read_model,
            evidence_uid,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
        )

    def mark_evidence_reviewed_bulk(
        self,
        evidence_uids: list[str],
        *,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
    ) -> list[str]:
        """Mark multiple evidence items as reviewed. Phase D.2. Returns list of event_ids."""
        return mark_evidence_reviewed_bulk(
            self._store,
            self.read_model,
            evidence_uids,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
        )

    def generate_chain_of_custody_report(
        self,
        scope: str,
        scope_uid: str,
        report_format: str,
        *,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
    ) -> tuple[str, str]:
        """Generate chain-of-custody report; returns (event_id, report_uid). Report written to project reports/ dir."""
        report_dir = self._path / "reports"
        return generate_chain_of_custody_report(
            self._store,
            self.read_model,
            scope,
            scope_uid,
            report_format,
            report_dir=report_dir,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
        )

    def create_artifact(
        self,
        investigation_uid: str,
        title: str,
        *,
        artifact_type: str | None = None,
        notes: str | None = None,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
    ) -> tuple[str, str]:
        """Create artifact; returns (event_id, artifact_uid)."""
        return create_artifact(
            self._store,
            self.read_model,
            investigation_uid,
            title,
            artifact_type=artifact_type,
            notes=notes,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
        )

    def create_checkpoint(
        self,
        investigation_uid: str,
        scope_refs: list[str],
        *,
        artifact_refs: list[str] | None = None,
        reason: str | None = None,
        certifying_org_id: str | None = None,
        certified_at: str | None = None,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
    ) -> tuple[str, str]:
        """Create checkpoint; returns (event_id, checkpoint_uid). E5.3: optional certifying_org_id, certified_at."""
        return create_checkpoint(
            self._store,
            self.read_model,
            investigation_uid,
            scope_refs,
            artifact_refs=artifact_refs,
            reason=reason,
            certifying_org_id=certifying_org_id,
            certified_at=certified_at,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
            policy_profile=load_policy_profile(self._path / POLICY_FILENAME),
        )

    def freeze_artifact_version(
        self,
        checkpoint_uid: str,
        artifact_uid: str,
        *,
        claim_refs: list[str] | None = None,
        evidence_refs: list[str] | None = None,
        tension_refs: list[str] | None = None,
        reason: str | None = None,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
    ) -> str:
        """Freeze artifact version at checkpoint; returns event_id."""
        return freeze_artifact_version(
            self._store,
            self.read_model,
            checkpoint_uid,
            artifact_uid,
            claim_refs=claim_refs,
            evidence_refs=evidence_refs,
            tension_refs=tension_refs,
            reason=reason,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
        )

    def export_investigation(self, investigation_uid: str, output_path: Path | str) -> Path:
        """Export investigation to .chronicle file; returns path to written file."""
        return export_investigation(
            self.read_model,
            self._path,
            investigation_uid,
            Path(output_path),
        )

    def export_minimal_for_claim(
        self, investigation_uid: str, claim_uid: str, output_path: Path | str
    ) -> Path:
        """Export a minimal .chronicle for one claim (and its evidence/links/tensions) for verification. P2.2.2."""
        return export_minimal_for_claim(
            self.read_model,
            self._path,
            investigation_uid,
            claim_uid,
            Path(output_path),
        )

    def import_investigation(self, chronicle_path: Path | str) -> None:
        """Import .chronicle file into this project (merge or fresh)."""
        import_investigation(Path(chronicle_path), self._path)
