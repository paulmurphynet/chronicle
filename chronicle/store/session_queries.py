"""Read/query operations for ChronicleSession."""

from __future__ import annotations

# mypy: disable-error-code="attr-defined,no-any-return"
from datetime import (
    UTC,
    datetime,
)
from typing import Any

from chronicle.core.errors import ChronicleUserError
from chronicle.core.events import EVENT_CHAIN_OF_CUSTODY_REPORT_GENERATED
from chronicle.core.policy import (
    POLICY_FILENAME,
    load_policy_profile,
    load_policy_profile_by_id,
)
from chronicle.core.policy_compat import get_policy_compatibility as compute_policy_compatibility
from chronicle.core.validation import MAX_LIST_LIMIT
from chronicle.store.claim_embedding_store import ClaimEmbeddingStore
from chronicle.store.commands import (
    assemble_reasoning_brief,
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
    get_reviewer_decision_ledger,
    get_tension_impact,
    get_weakest_link,
)
from chronicle.store.project import CHRONICLE_DB
from chronicle.store.read_model import (
    DefensibilityScorecard,
    WeakestLink,
)


class ChronicleSessionQueryMixin:
    """Query and analytics methods mixed into ChronicleSession."""

    def get_claim_history(self, claim_uid: str, limit: int | None = None) -> list:
        """Return events for this claim in recorded_at order (GetClaimHistory). limit is capped at MAX_LIST_LIMIT."""
        effective_limit = min(limit, MAX_LIST_LIMIT) if limit is not None else None
        return list(self._store.read_by_subject(claim_uid, limit=effective_limit))

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

    def get_sources_backing_claim(self, claim_uid: str) -> list[dict[str, Any]]:
        """Return source-level backing details for a claim when supported by the read model."""
        try:
            getter = self.read_model.get_sources_backing_claim  # type: ignore[attr-defined]
        except AttributeError:
            return []
        result = getter(claim_uid)
        if isinstance(result, list):
            return result
        return []

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

    def get_reviewer_decision_ledger(
        self,
        investigation_uid: str,
        *,
        limit: int = 500,
    ) -> dict[str, Any]:
        """TE-04: Consolidated reviewer decision ledger with unresolved tensions summary."""
        if self.read_model.get_investigation(investigation_uid) is None:
            raise ChronicleUserError("Investigation not found")
        return get_reviewer_decision_ledger(
            self._store,
            self.read_model,
            investigation_uid,
            limit=limit,
        )

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
            raise ChronicleUserError("Investigation not found")
        if as_of_date is not None and as_of_event_id is not None:
            raise ChronicleUserError("At most one of as_of_date or as_of_event_id may be set")
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

    def get_policy_compatibility_preflight(
        self,
        investigation_uid: str,
        *,
        viewing_profile_id: str | None = None,
        built_under_profile_id: str | None = None,
        built_under_policy_version: str | None = None,
    ) -> dict[str, Any]:
        """Return policy compatibility preflight for an investigation.

        Compares built-under policy to viewing policy. If built-under is not provided,
        uses the latest checkpoint's built-under policy metadata when available.
        """
        if self.read_model.get_investigation(investigation_uid) is None:
            raise ChronicleUserError("Investigation not found")

        active_profile = load_policy_profile(self._path / POLICY_FILENAME)

        def _load_profile_for_compat(profile_id: str) -> Any:
            loaded = load_policy_profile_by_id(self._path, profile_id)
            if loaded is not None:
                return loaded
            if active_profile.profile_id == profile_id:
                return active_profile
            return None

        if viewing_profile_id and viewing_profile_id.strip():
            viewing_profile = _load_profile_for_compat(viewing_profile_id.strip())
            if viewing_profile is None:
                raise ChronicleUserError(f"Viewing policy profile not found: {viewing_profile_id}")
            viewing_resolution = "profile_id"
        else:
            viewing_profile = active_profile
            viewing_resolution = "active_policy"

        resolved_built_under = built_under_profile_id.strip() if built_under_profile_id else None
        resolved_built_version = built_under_policy_version.strip() if built_under_policy_version else None
        built_under_resolution = "provided"
        if not resolved_built_under:
            resolved_built_under, checkpoint_version = self.get_investigation_built_under_policy(
                investigation_uid
            )
            if not resolved_built_version:
                resolved_built_version = checkpoint_version
            built_under_resolution = "latest_checkpoint"

        result = compute_policy_compatibility(
            resolved_built_under,
            resolved_built_version,
            viewing_profile,
            load_built_under_profile=_load_profile_for_compat,
        )
        out = result.to_dict()
        out["investigation_uid"] = investigation_uid
        out["built_under_policy_id"] = resolved_built_under
        out["built_under_policy_version"] = resolved_built_version
        out["viewing_policy_id"] = viewing_profile.profile_id
        out["viewing_policy_display_name"] = viewing_profile.display_name
        out["resolution"] = {
            "built_under": built_under_resolution,
            "viewing": viewing_resolution,
        }
        return out

    def get_review_packet(
        self,
        investigation_uid: str,
        *,
        limit_claims: int = 200,
        decision_limit: int = 500,
        include_reasoning_briefs: bool = True,
        include_full_trail: bool = False,
        as_of_date: str | None = None,
        as_of_event_id: str | None = None,
        viewing_profile_id: str | None = None,
        built_under_profile_id: str | None = None,
        built_under_policy_version: str | None = None,
    ) -> dict[str, Any]:
        """TE-05: Build one review-ready packet for legal/compliance/editorial handoff."""
        inv = self.read_model.get_investigation(investigation_uid)
        if inv is None:
            raise ChronicleUserError("Investigation not found")
        if as_of_date is not None and as_of_event_id is not None:
            raise ChronicleUserError("At most one of as_of_date or as_of_event_id may be set")

        policy_compatibility = self.get_policy_compatibility_preflight(
            investigation_uid,
            viewing_profile_id=viewing_profile_id,
            built_under_profile_id=built_under_profile_id,
            built_under_policy_version=built_under_policy_version,
        )
        reviewer_decision_ledger = self.get_reviewer_decision_ledger(
            investigation_uid,
            limit=decision_limit,
        )
        audit_export_bundle = self.get_audit_export_bundle(
            investigation_uid,
            include_full_trail=include_full_trail,
            limit_claims=limit_claims,
            as_of_date=as_of_date,
            as_of_event_id=as_of_event_id,
        )

        active_profile = load_policy_profile(self._path / POLICY_FILENAME)
        viewing_id = policy_compatibility.get("viewing_under")
        viewing_profile = (
            load_policy_profile_by_id(self._path, viewing_id)
            if isinstance(viewing_id, str) and viewing_id.strip()
            else None
        )
        if viewing_profile is None:
            viewing_profile = active_profile
        profile_dict = viewing_profile.to_dict()
        policy_rationale_summary = {
            "profile_id": viewing_profile.profile_id,
            "display_name": viewing_profile.display_name,
            "description": viewing_profile.description,
            "policy_rationale": viewing_profile.policy_rationale,
            "mes_rules": [
                {
                    "target_claim_type": r.target_claim_type,
                    "min_independent_sources": r.min_independent_sources,
                    "required_evidence_types": list(r.required_evidence_types),
                    "min_confidence": r.min_confidence,
                    "min_sources_with_independence_notes": r.min_sources_with_independence_notes,
                }
                for r in viewing_profile.mes_rules
            ],
            "checkpoint_rules": profile_dict.get("checkpoint_rules"),
            "tension_rules": profile_dict.get("tension_rules"),
        }

        report_events = self._store.read_by_investigation(investigation_uid, limit=20_000)
        chain_of_custody_reports: list[dict[str, Any]] = []
        for ev in report_events:
            if ev.event_type != EVENT_CHAIN_OF_CUSTODY_REPORT_GENERATED:
                continue
            payload = ev.payload or {}
            report_uri = payload.get("report_uri")
            report_exists = False
            if isinstance(report_uri, str) and report_uri.strip():
                report_exists = (self._path / report_uri).is_file()
            chain_of_custody_reports.append(
                {
                    "event_id": ev.event_id,
                    "recorded_at": ev.recorded_at,
                    "actor_id": ev.actor_id,
                    "actor_type": ev.actor_type,
                    "report_uid": payload.get("report_uid"),
                    "scope": payload.get("scope"),
                    "scope_uid": payload.get("scope_uid"),
                    "format": payload.get("format"),
                    "generated_at": payload.get("generated_at"),
                    "content_hash": payload.get("content_hash"),
                    "report_uri": report_uri,
                    "report_exists": report_exists,
                    "items_included": payload.get("items_included") or [],
                }
            )
        chain_of_custody_reports.sort(
            key=lambda x: (x.get("generated_at") or x.get("recorded_at") or ""),
            reverse=True,
        )

        reasoning_briefs: list[dict[str, Any]] = []
        if include_reasoning_briefs:
            claims = self.read_model.list_claims_by_type(
                investigation_uid=investigation_uid,
                limit=limit_claims,
                include_withdrawn=True,
            )
            for claim in claims:
                brief = self.get_reasoning_brief(
                    claim.claim_uid,
                    limit=500,
                    as_of_date=as_of_date,
                    as_of_event_id=as_of_event_id,
                )
                if brief is None:
                    continue
                reasoning_briefs.append({"claim_uid": claim.claim_uid, "brief": brief})

        warnings: list[str] = []
        if not chain_of_custody_reports:
            warnings.append(
                "No chain-of-custody report found. Generate one for the investigation if the review workflow requires it."
            )
        unresolved_count = reviewer_decision_ledger.get("summary", {}).get("unresolved_tensions_count", 0)
        if isinstance(unresolved_count, int) and unresolved_count > 0:
            warnings.append(f"{unresolved_count} unresolved tensions remain in this review packet.")

        return {
            "investigation_uid": investigation_uid,
            "investigation_title": inv.title,
            "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "policy_compatibility": policy_compatibility,
            "policy_rationale_summary": policy_rationale_summary,
            "reviewer_decision_ledger": reviewer_decision_ledger,
            "chain_of_custody_reports": chain_of_custody_reports,
            "latest_chain_of_custody_report": chain_of_custody_reports[0]
            if chain_of_custody_reports
            else None,
            "reasoning_briefs": reasoning_briefs,
            "audit_export_bundle": audit_export_bundle,
            "warnings": warnings,
        }

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
