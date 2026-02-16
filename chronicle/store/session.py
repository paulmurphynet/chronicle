"""ChronicleSession: one project path, holds EventStore + ReadModel + EvidenceStore."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from chronicle.core.policy import POLICY_FILENAME, load_policy_profile
from chronicle.core.validation import MAX_LIST_LIMIT
from chronicle.store.claim_embedding_store import ClaimEmbeddingStore
from chronicle.store.commands import (
    analyze_claim_atomicity,
    anchor_span,
    archive_investigation,
    assemble_reasoning_brief,
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
    get_accountability_chain,
    get_answer_epistemic_risk,
    get_checkpoint_diff,
    get_claim_drift,
    get_defensibility_as_of,
    get_defensibility_multi_profile,
    get_defensibility_score,
    get_evidence_impact,
    get_human_decisions_audit_trail,
    get_investigation_event_history,
    get_reasoning_trail_checkpoint,
    get_reasoning_trail_claim,
    get_tension_impact,
    get_weakest_link,
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
from chronicle.store.evidence_store import FileSystemEvidenceStore
from chronicle.store.project import CHRONICLE_DB, project_exists
from chronicle.store.protocols import EventStore, ReadModel
from chronicle.store.read_model import DefensibilityScorecard, WeakestLink
from chronicle.store.sqlite_event_store import SqliteEventStore


class ChronicleSession:
    """Session for a single project: store, read model, evidence store."""

    def __init__(self, project_dir: Path | str) -> None:
        self._path = Path(project_dir)
        if not project_exists(self._path):
            raise FileNotFoundError(f"Not a Chronicle project (no {CHRONICLE_DB}): {self._path}")
        self._store = SqliteEventStore(self._path / CHRONICLE_DB, run_projection=True)
        self._evidence = FileSystemEvidenceStore(self._path)

    @property
    def store(self) -> EventStore:
        return self._store

    @property
    def read_model(self) -> ReadModel:
        return self._store.get_read_model()

    @property
    def evidence(self) -> FileSystemEvidenceStore:
        return self._evidence

    @property
    def project_path(self) -> Path:
        """Project directory path (for API handlers that need path, e.g. policy file)."""
        return self._path

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
        )

    def archive_investigation(
        self,
        investigation_uid: str,
        *,
        reason: str | None = None,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
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
        )

    def propose_claim(
        self,
        investigation_uid: str,
        claim_text: str,
        *,
        initial_type: str | None = None,
        parent_claim_uid: str | None = None,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
        idempotency_key: str | None = None,
    ) -> tuple[str, str]:
        """Propose a claim; returns (event_id, claim_uid)."""
        return propose_claim(
            self._store,
            investigation_uid,
            claim_text,
            initial_type=initial_type,
            parent_claim_uid=parent_claim_uid,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
            idempotency_key=idempotency_key,
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
        )

    def link_support(
        self,
        investigation_uid: str,
        span_uid: str,
        claim_uid: str,
        *,
        strength: float | None = None,
        notes: str | None = None,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
        idempotency_key: str | None = None,
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
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
            idempotency_key=idempotency_key,
        )

    def link_challenge(
        self,
        investigation_uid: str,
        span_uid: str,
        claim_uid: str,
        *,
        strength: float | None = None,
        notes: str | None = None,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
        idempotency_key: str | None = None,
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
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
            idempotency_key=idempotency_key,
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

    def get_claim_history(self, claim_uid: str, limit: int | None = None) -> list:
        """Return events for this claim in recorded_at order (GetClaimHistory). limit is capped at MAX_LIST_LIMIT."""
        effective_limit = min(limit, MAX_LIST_LIMIT) if limit is not None else None
        return self._store.read_by_subject(claim_uid, limit=effective_limit)

    def get_defensibility_score(
        self,
        claim_uid: str,
        use_strength_weighting: bool = False,
    ) -> DefensibilityScorecard | None:
        """GetDefensibilityScore: defensibility scorecard for a claim. Returns None if claim not found. Phase B.2: use_strength_weighting. Phase 5: includes evidence_trust when policy has assessment rules."""
        policy_profile = load_policy_profile(self._path / POLICY_FILENAME)
        return get_defensibility_score(
            self.read_model,
            claim_uid,
            use_strength_weighting=use_strength_weighting,
            policy_profile=policy_profile,
        )

    def get_weakest_link(self, claim_uid: str) -> WeakestLink | None:
        """GetWeakestLink: single most vulnerable dimension for a claim. Returns None if claim not found."""
        return get_weakest_link(self.read_model, claim_uid)

    def get_answer_epistemic_risk(self, claim_uids: list[str]) -> dict[str, Any]:
        """Answer-level epistemic risk for a set of claims (e.g. an answer that cites them). E1.1."""
        return get_answer_epistemic_risk(self.read_model, claim_uids)

    def get_reasoning_trail_claim(self, claim_uid: str, limit: int | None = None) -> dict | None:
        """GetReasoningTrail(claim_uid): events that created or modified the claim. Phase 6. Returns None if claim not found."""
        return get_reasoning_trail_claim(self._store, self.read_model, claim_uid, limit=limit)

    def get_reasoning_brief(
        self,
        claim_uid: str,
        limit: int | None = None,
        *,
        as_of_date: str | None = None,
        as_of_event_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Assemble reasoning brief for a claim. B.2: Optional as_of_date or as_of_event_id for defensibility at a point in time."""
        return assemble_reasoning_brief(
            self._store,
            self.read_model,
            claim_uid,
            limit=limit,
            as_of_date=as_of_date,
            as_of_event_id=as_of_event_id,
        )

    def get_reasoning_trail_checkpoint(self, checkpoint_uid: str) -> dict | None:
        """GetReasoningTrail(checkpoint_uid): checkpoint snapshot and creation event. Phase 6. Returns None if checkpoint not found."""
        return get_reasoning_trail_checkpoint(self._store, self.read_model, checkpoint_uid)

    def get_accountability_chain(
        self,
        claim_uid: str,
        *,
        limit: int = 500,
    ) -> list[dict]:
        """E3.1: Accountability chain for a claim (proposer, linkers, tension declarers, evidence ingesters, dismissals)."""
        return get_accountability_chain(self._store, self.read_model, claim_uid, limit=limit)

    def get_evidence_impact(self, evidence_uid: str) -> dict:
        """E4.1: Impact if we retract or remove links from this evidence."""
        return get_evidence_impact(self.read_model, evidence_uid)

    def get_tension_impact(self, tension_uid: str) -> dict:
        """E4.1: Impact if we resolve this tension (defensibility change for claim_a and claim_b)."""
        return get_tension_impact(self.read_model, tension_uid)

    def get_defensibility_multi_profile(
        self,
        investigation_uid: str,
        profile_ids: list[str],
    ) -> dict:
        """E5.1: Defensibility under multiple policy profiles (e.g. Under legal: strong. Under journalism: weak.)."""
        return get_defensibility_multi_profile(
            self.read_model,
            self.project_path,
            investigation_uid,
            profile_ids,
        )

    def get_claim_drift(
        self,
        claim_uid: str,
        *,
        as_of_date: str | None = None,
        as_of_event_id: str | None = None,
    ) -> dict | None:
        """E4.3: Epistemic drift: has this claim's defensibility weakened since as_of?"""
        return get_claim_drift(
            self._store,
            self.read_model,
            claim_uid,
            as_of_date=as_of_date,
            as_of_event_id=as_of_event_id,
        )

    def get_human_decisions_audit_trail(
        self,
        investigation_uid: str,
        *,
        limit: int = 500,
    ) -> list[dict]:
        """E6: Audit trail of human decisions (tier changes, suggestion dismissals) for an investigation."""
        return get_human_decisions_audit_trail(self._store, investigation_uid, limit=limit)

    def get_investigation_event_history(
        self,
        investigation_uid: str,
        *,
        limit: int = 5000,
    ) -> list[dict]:
        """Full event history for an investigation (who did what when). Phase 4.2."""
        return get_investigation_event_history(self._store, investigation_uid, limit=limit)

    def get_audit_export_bundle(
        self,
        investigation_uid: str,
        *,
        include_full_trail: bool = False,
        limit_claims: int = 500,
        as_of_date: str | None = None,
        as_of_event_id: str | None = None,
    ) -> dict[str, Any]:
        """Build audit pack for an investigation. B.1. When as_of_date or as_of_event_id is set, defensibility_snapshot is at that point in time (B.2)."""
        if self.read_model.get_investigation(investigation_uid) is None:
            raise ValueError("Investigation not found")
        if as_of_date is not None and as_of_event_id is not None:
            raise ValueError("At most one of as_of_date or as_of_event_id may be set")
        rm = self.read_model
        human_decisions = self.get_human_decisions_audit_trail(investigation_uid, limit=500)
        claims = rm.list_claims_by_type(
            investigation_uid=investigation_uid, limit=limit_claims, include_withdrawn=True
        )
        accountability_by_claim = [
            {
                "claim_uid": c.claim_uid,
                "accountability_chain": self.get_accountability_chain(c.claim_uid, limit=500),
            }
            for c in claims
        ]
        evidence_items = rm.list_evidence_by_investigation(investigation_uid)
        evidence_list = [
            {
                "evidence_uid": ev.evidence_uid,
                "created_at": ev.created_at,
                "ingested_by_actor_id": ev.ingested_by_actor_id,
                "content_hash": ev.content_hash,
                "integrity_status": ev.integrity_status,
            }
            for ev in evidence_items
        ]
        claims_list = [
            {
                "claim_uid": c.claim_uid,
                "claim_text": (c.claim_text or "")[:2000],
                "created_at": c.created_at,
                "current_status": c.current_status,
                "claim_type": c.claim_type or "",
            }
            for c in claims
        ]
        links: list[dict[str, Any]] = []
        for c in claims:
            for link in rm.get_support_for_claim(c.claim_uid) + rm.get_challenges_for_claim(
                c.claim_uid
            ):
                span = rm.get_evidence_span(link.span_uid)
                links.append(
                    {
                        "claim_uid": c.claim_uid,
                        "link_type": link.link_type,
                        "span_uid": link.span_uid,
                        "evidence_uid": span.evidence_uid if span else None,
                    }
                )
        defensibility_snapshot = []
        as_of_label: str | None = None
        if as_of_date is not None or as_of_event_id is not None:
            as_of_result = self.get_defensibility_as_of(
                investigation_uid,
                as_of_date=as_of_date,
                as_of_event_id=as_of_event_id,
            )
            if as_of_result:
                as_of_label = as_of_result.get("as_of")
                by_claim = {
                    item["claim_uid"]: item.get("defensibility")
                    for item in (as_of_result.get("claims") or [])
                }
                for c in claims:
                    defn = by_claim.get(c.claim_uid)
                    defensibility_snapshot.append(
                        {
                            "claim_uid": c.claim_uid,
                            "provenance_quality": defn.get("provenance_quality") if defn else None,
                            "contradiction_status": defn.get("contradiction_status")
                            if defn
                            else None,
                            "corroboration": defn.get("corroboration") if defn else None,
                        }
                    )
            else:
                as_of_label = as_of_date or as_of_event_id
                for c in claims:
                    defensibility_snapshot.append(
                        {
                            "claim_uid": c.claim_uid,
                            "provenance_quality": None,
                            "contradiction_status": None,
                            "corroboration": None,
                        }
                    )
        else:
            for c in claims:
                sc = self.get_defensibility_score(c.claim_uid)
                defensibility_snapshot.append(
                    {
                        "claim_uid": c.claim_uid,
                        "provenance_quality": sc.provenance_quality if sc else None,
                        "contradiction_status": sc.contradiction_status if sc else None,
                        "corroboration": sc.corroboration if sc else None,
                    }
                )
        out: dict[str, Any] = {
            "investigation_uid": investigation_uid,
            "exported_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "human_decisions_audit_trail": human_decisions,
            "accountability_by_claim": accountability_by_claim,
            "evidence_list": evidence_list,
            "claims_list": claims_list,
            "links": links,
            "defensibility_snapshot": defensibility_snapshot,
        }
        if as_of_label is not None:
            out["defensibility_as_of"] = as_of_label
        if include_full_trail:
            out["full_event_history"] = self.get_investigation_event_history(
                investigation_uid, limit=20_000
            )
        return out

    def get_checkpoint_built_under_policy(
        self, checkpoint_uid: str
    ) -> tuple[str | None, str | None]:
        """Return (built_under_policy_id, built_under_policy_version) from checkpoint creation event. Phase 9."""
        events = self._store.read_by_subject(checkpoint_uid, limit=1)
        if not events:
            return (None, None)
        payload = events[0].payload or {}
        return (
            payload.get("built_under_policy_id"),
            payload.get("built_under_policy_version"),
        )

    def get_checkpoint_diff(self, checkpoint_uid_a: str, checkpoint_uid_b: str) -> dict[str, Any]:
        """Return what changed between two checkpoints (scope_refs diff). Phase A.2."""
        return get_checkpoint_diff(self.read_model, checkpoint_uid_a, checkpoint_uid_b)

    def get_investigation_built_under_policy(
        self, investigation_uid: str
    ) -> tuple[str | None, str | None]:
        """Return built_under from latest checkpoint for this investigation, or (None, None). Phase 9."""
        checkpoints = self.read_model.list_checkpoints(investigation_uid, limit=1)
        if not checkpoints:
            return (None, None)
        return self.get_checkpoint_built_under_policy(checkpoints[0].checkpoint_uid)

    def get_defensibility_as_of(
        self,
        investigation_uid: str,
        *,
        as_of_date: str | None = None,
        as_of_event_id: str | None = None,
    ) -> dict | None:
        """GetDefensibilityAsOf: defensibility snapshot at a date or event. Phase 7. Exactly one of as_of_date (ISO8601) or as_of_event_id required."""
        return get_defensibility_as_of(
            self._store,
            self.read_model,
            investigation_uid,
            as_of_date=as_of_date,
            as_of_event_id=as_of_event_id,
        )

    def get_similar_claims(self, claim_uid: str, limit: int = 10) -> list[tuple[str, float]]:
        """Return (claim_uid, similarity_score) for claims similar to this one. Optional; requires CHRONICLE_EMBEDDING_ENABLED. VECTOR_PROJECTION.md."""
        from chronicle.tools.embedding_config import is_embedding_enabled
        from chronicle.tools.embeddings import embed

        if not is_embedding_enabled():
            return []
        claim = self.read_model.get_claim(claim_uid)
        if not claim or not (claim.claim_text or "").strip():
            return []
        inv_uid = claim.investigation_uid
        candidates = [
            c.claim_uid
            for c in self.read_model.list_claims_by_type(investigation_uid=inv_uid)
            if c.claim_uid != claim_uid
        ]
        if not candidates:
            return []
        db_path = self._path / CHRONICLE_DB
        store = ClaimEmbeddingStore(db_path)
        now_iso = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        vec = store.get(claim_uid)
        if vec is None:
            vec = embed((claim.claim_text or "").strip())
            if vec:
                store.set(claim_uid, vec, now_iso)
        if vec is None:
            return []
        # Ensure each candidate has an embedding so store.similar() can score them.
        for c_uid in candidates:
            if store.get(c_uid) is not None:
                continue
            c_claim = self.read_model.get_claim(c_uid)
            if not c_claim or not (c_claim.claim_text or "").strip():
                continue
            c_vec = embed((c_claim.claim_text or "").strip())
            if c_vec:
                store.set(c_uid, c_vec, now_iso)
        return store.similar(claim_uid, candidates, limit)

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
        notes: str | None = None,
        actor_id: str = "default",
        actor_type: str = "human",
        workspace: str = "spark",
        idempotency_key: str | None = None,
    ) -> tuple[str, str]:
        """Declare a tension between two claims; returns (event_id, tension_uid)."""
        return declare_tension(
            self._store,
            self.read_model,
            investigation_uid,
            claim_a_uid,
            claim_b_uid,
            tension_kind=tension_kind,
            notes=notes,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
            idempotency_key=idempotency_key,
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
        """Stub: analyze claim atomicity and emit ClaimDecompositionAnalyzed; returns event_id."""
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
            raise ValueError(f"claim_uid must reference an existing claim: {claim_uid}")

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

    def __enter__(self) -> "ChronicleSession":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def close(self) -> None:
        self._store.close()
