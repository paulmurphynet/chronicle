"""Claim commands: propose, type, scope, temporalize, assert, withdraw, downgrade, promote, decompose, analyze, get_defensibility."""

import json
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from chronicle.core.errors import ChronicleUserError
from chronicle.core.events import (
    EVENT_CLAIM_ASSERTED,
    EVENT_CLAIM_DECOMPOSITION_ANALYZED,
    EVENT_CLAIM_DOWNGRADED,
    EVENT_CLAIM_PROMOTED_TO_SEF,
    EVENT_CLAIM_PROPOSED,
    EVENT_CLAIM_SCOPED,
    EVENT_CLAIM_TEMPORALIZED,
    EVENT_CLAIM_TYPED,
    EVENT_CLAIM_WITHDRAWN,
    Event,
)
from chronicle.core.payloads import (
    ActorRef,
    ClaimAssertedPayload,
    ClaimDecompositionAnalyzedPayload,
    ClaimDowngradedPayload,
    ClaimPromotedToSEFPayload,
    ClaimProposedPayload,
    ClaimScopedPayload,
    ClaimTemporalizedPayload,
    ClaimTypedPayload,
    ClaimWithdrawnPayload,
    SuggestedSplit,
)
from chronicle.core.policy import (
    PolicyProfile,
    default_policy_profile,
    require_workspace_for_command,
    validate_mes_for_sef,
)
from chronicle.core.uid import (
    generate_assertion_uid,
    generate_claim_uid,
    generate_event_id,
)
from chronicle.core.validation import MAX_CLAIM_TEXT_LENGTH
from chronicle.store.commands.attestation import apply_attestation_to_payload
from chronicle.store.protocols import EventStore, ReadModel
from chronicle.store.read_model import DefensibilityScorecard, WeakestLink
from chronicle.store.read_model.models import EvidenceTrustAssessment, LinkWithInherited

_CLAIM_TYPES = frozenset({"SAC", "SEF", "INFERENCE", "UNKNOWN", "OPEN_QUESTION"})
_ASSERTION_MODES = frozenset({"asserted", "quoted", "inferred", "hypothetical"})


def propose_claim(
    store: EventStore,
    investigation_uid: str,
    claim_text: str,
    *,
    initial_type: str | None = None,
    parent_claim_uid: str | None = None,
    actor_id: str = "default",
    actor_type: str = "human",
    workspace: str = "spark",
    idempotency_key: str | None = None,
    verification_level: str | None = None,
    attestation_ref: str | None = None,
) -> tuple[str, str]:
    """ProposeClaim command. Returns (event_id, claim_uid). Spec 1.5.1, 1.5.1a."""
    key = (idempotency_key or "").strip()
    if key:
        existing = store.get_event_by_idempotency_key(key)
        if existing:
            return (existing.event_id, existing.subject_uid)
    text = claim_text.strip() if claim_text else ""
    if not text:
        raise ChronicleUserError("claim_text must be non-empty")
    if len(text) > MAX_CLAIM_TEXT_LENGTH:
        raise ChronicleUserError(f"claim_text must be at most {MAX_CLAIM_TEXT_LENGTH} characters")
    if initial_type is not None and initial_type not in _CLAIM_TYPES:
        raise ChronicleUserError(f"initial_type must be one of {sorted(_CLAIM_TYPES)}")
    claim_uid = generate_claim_uid()
    event_id = generate_event_id()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = ClaimProposedPayload(
        claim_uid=claim_uid,
        claim_text=text,
        initial_type=initial_type,
        parent_claim_uid=parent_claim_uid,
        created_by=ActorRef(actor_type=actor_type, actor_id=actor_id),
    ).to_dict()
    apply_attestation_to_payload(
        payload,
        verification_level=verification_level,
        attestation_ref=attestation_ref,
    )
    event = Event(
        event_id=event_id,
        event_type=EVENT_CLAIM_PROPOSED,
        occurred_at=now,
        recorded_at=now,
        investigation_uid=investigation_uid,
        subject_uid=claim_uid,
        actor_type=actor_type,
        actor_id=actor_id,
        workspace=workspace,
        payload=payload,
        idempotency_key=key or None,
    )
    store.append(event)
    return event_id, claim_uid


def _require_active_claim(read_model: ReadModel, claim_uid: str) -> None:
    """Raise if claim does not exist or is not ACTIVE. Spec 1.5.1a."""
    claim = read_model.get_claim(claim_uid)
    if claim is None:
        raise ChronicleUserError(f"claim_uid must reference an existing claim: {claim_uid}")
    if claim.current_status != "ACTIVE":
        raise ChronicleUserError(f"claim must be ACTIVE (current status: {claim.current_status})")


def type_claim(
    store: EventStore,
    read_model: ReadModel,
    claim_uid: str,
    claim_type: str,
    *,
    rationale: str | None = None,
    actor_id: str = "default",
    actor_type: str = "human",
    workspace: str = "spark",
) -> str:
    """TypeClaim command. Returns event_id. Forge+ tier. Spec 1.5.1, 1.5.1a."""
    require_workspace_for_command(workspace, "type_claim")
    _require_active_claim(read_model, claim_uid)
    if claim_type not in _CLAIM_TYPES:
        raise ChronicleUserError(f"claim_type must be one of {sorted(_CLAIM_TYPES)}")
    claim = read_model.get_claim(claim_uid)
    investigation_uid = claim.investigation_uid if claim else ""
    event_id = generate_event_id()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = ClaimTypedPayload(claim_uid=claim_uid, claim_type=claim_type, rationale=rationale)
    event = Event(
        event_id=event_id,
        event_type=EVENT_CLAIM_TYPED,
        occurred_at=now,
        recorded_at=now,
        investigation_uid=investigation_uid,
        subject_uid=claim_uid,
        actor_type=actor_type,
        actor_id=actor_id,
        workspace=workspace,
        payload=payload.to_dict(),
    )
    store.append(event)
    return event_id


def scope_claim(
    store: EventStore,
    read_model: ReadModel,
    claim_uid: str,
    scope: dict[str, Any],
    *,
    actor_id: str = "default",
    actor_type: str = "human",
    workspace: str = "spark",
) -> str:
    """ScopeClaim command. Returns event_id. Forge+ tier. Spec 1.5.1, 1.5.1a."""
    require_workspace_for_command(workspace, "scope_claim")
    _require_active_claim(read_model, claim_uid)
    if not isinstance(scope, dict):
        raise ChronicleUserError("scope must be a JSON object")
    claim = read_model.get_claim(claim_uid)
    investigation_uid = claim.investigation_uid if claim else ""
    event_id = generate_event_id()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = ClaimScopedPayload(claim_uid=claim_uid, scope=scope)
    event = Event(
        event_id=event_id,
        event_type=EVENT_CLAIM_SCOPED,
        occurred_at=now,
        recorded_at=now,
        investigation_uid=investigation_uid,
        subject_uid=claim_uid,
        actor_type=actor_type,
        actor_id=actor_id,
        workspace=workspace,
        payload=payload.to_dict(),
    )
    store.append(event)
    return event_id


def temporalize_claim(
    store: EventStore,
    read_model: ReadModel,
    claim_uid: str,
    temporal: dict[str, Any],
    *,
    actor_id: str = "default",
    actor_type: str = "human",
    workspace: str = "spark",
) -> str:
    """TemporalizeClaim command. Returns event_id. Forge+ tier. Spec 1.5.1, 1.5.1a."""
    require_workspace_for_command(workspace, "temporalize_claim")
    _require_active_claim(read_model, claim_uid)
    if not isinstance(temporal, dict):
        raise ChronicleUserError("temporal must be a JSON object")
    claim = read_model.get_claim(claim_uid)
    investigation_uid = claim.investigation_uid if claim else ""
    event_id = generate_event_id()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = ClaimTemporalizedPayload(claim_uid=claim_uid, temporal=temporal)
    event = Event(
        event_id=event_id,
        event_type=EVENT_CLAIM_TEMPORALIZED,
        occurred_at=now,
        recorded_at=now,
        investigation_uid=investigation_uid,
        subject_uid=claim_uid,
        actor_type=actor_type,
        actor_id=actor_id,
        workspace=workspace,
        payload=payload.to_dict(),
    )
    store.append(event)
    return event_id


def assert_claim(
    store: EventStore,
    read_model: ReadModel,
    claim_uid: str,
    posture: str,
    *,
    confidence: float | None = None,
    justification: str | None = None,
    actor_id: str = "default",
    actor_type: str = "human",
    workspace: str = "spark",
) -> tuple[str, str]:
    """AssertClaim command. Returns (event_id, assertion_uid). Forge+ tier. Spec 1.5.1, 1.5.1a."""
    require_workspace_for_command(workspace, "assert_claim")
    if read_model.get_claim(claim_uid) is None:
        raise ChronicleUserError(f"claim_uid must reference an existing claim: {claim_uid}")
    posture = posture.strip().lower()
    if posture not in _ASSERTION_MODES:
        raise ChronicleUserError(f"posture must be one of {sorted(_ASSERTION_MODES)}")
    claim = read_model.get_claim(claim_uid)
    investigation_uid = claim.investigation_uid if claim else ""
    assertion_uid = generate_assertion_uid()
    event_id = generate_event_id()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = ClaimAssertedPayload(
        assertion_uid=assertion_uid,
        claim_uid=claim_uid,
        assertion_mode=posture,
        confidence=confidence,
        justification=justification,
    )
    event = Event(
        event_id=event_id,
        event_type=EVENT_CLAIM_ASSERTED,
        occurred_at=now,
        recorded_at=now,
        investigation_uid=investigation_uid,
        subject_uid=assertion_uid,
        actor_type=actor_type,
        actor_id=actor_id,
        workspace=workspace,
        payload=payload.to_dict(),
    )
    store.append(event)
    return event_id, assertion_uid


def withdraw_claim(
    store: EventStore,
    read_model: ReadModel,
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
    """WithdrawClaim command. Returns event_id. Forge+ tier. Spec 1.5.1, 1.5.1a."""
    require_workspace_for_command(workspace, "withdraw_claim")
    claim = read_model.get_claim(claim_uid)
    if claim is None:
        raise ChronicleUserError(f"claim_uid must reference an existing claim: {claim_uid}")
    if claim.current_status == "WITHDRAWN":
        raise ChronicleUserError("claim is already withdrawn")
    if not reason or not reason.strip():
        raise ChronicleUserError("reason must be non-empty")
    valid_withdrawal = frozenset({"retraction", "erratum", "superseded_by_new_claim", "other"})
    if withdrawal_type not in valid_withdrawal:
        raise ChronicleUserError(f"withdrawal_type must be one of {sorted(valid_withdrawal)}")
    investigation_uid = claim.investigation_uid
    event_id = generate_event_id()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = ClaimWithdrawnPayload(
        claim_uid=claim_uid,
        reason=reason.strip(),
        withdrawal_type=withdrawal_type,
        superseded_by_claim_uid=superseded_by_claim_uid,
        notes=notes,
    )
    event = Event(
        event_id=event_id,
        event_type=EVENT_CLAIM_WITHDRAWN,
        occurred_at=now,
        recorded_at=now,
        investigation_uid=investigation_uid,
        subject_uid=claim_uid,
        actor_type=actor_type,
        actor_id=actor_id,
        workspace=workspace,
        payload=payload.to_dict(),
    )
    store.append(event)
    return event_id


def downgrade_claim(
    store: EventStore,
    read_model: ReadModel,
    claim_uid: str,
    reason: str | None = None,
    *,
    to_status: str = "DOWNGRADED",
    trigger_type: str | None = None,
    trigger_uid: str | None = None,
    trigger_event_id: str | None = None,
    actor_id: str = "default",
    actor_type: str = "human",
    workspace: str = "spark",
) -> str:
    """DowngradeClaim command. Returns event_id. Forge+ tier. Spec 1.5.1, 1.5.1a."""
    require_workspace_for_command(workspace, "downgrade_claim")
    claim = read_model.get_claim(claim_uid)
    if claim is None:
        raise ChronicleUserError(f"claim_uid must reference an existing claim: {claim_uid}")
    from_status = claim.current_status
    if from_status == "WITHDRAWN":
        raise ChronicleUserError("cannot downgrade a withdrawn claim")
    if to_status not in ("DOWNGRADED",):
        raise ChronicleUserError("to_status must be DOWNGRADED")
    if from_status == to_status:
        raise ChronicleUserError(f"claim is already {to_status}")
    investigation_uid = claim.investigation_uid
    event_id = generate_event_id()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = ClaimDowngradedPayload(
        claim_uid=claim_uid,
        from_status=from_status,
        to_status=to_status,
        reason=reason,
        trigger_type=trigger_type,
        trigger_uid=trigger_uid,
        trigger_event_id=trigger_event_id,
    )
    event = Event(
        event_id=event_id,
        event_type=EVENT_CLAIM_DOWNGRADED,
        occurred_at=now,
        recorded_at=now,
        investigation_uid=investigation_uid,
        subject_uid=claim_uid,
        actor_type=actor_type,
        actor_id=actor_id,
        workspace=workspace,
        payload=payload.to_dict(),
    )
    store.append(event)
    return event_id


def promote_to_sef(
    store: EventStore,
    read_model: ReadModel,
    claim_uid: str,
    evidence_set_refs: list[str] | None = None,
    *,
    rationale: str | None = None,
    policy_profile_id: str | None = None,
    actor_id: str = "default",
    actor_type: str = "human",
    workspace: str = "vault",
    policy_profile: PolicyProfile | None = None,
) -> str:
    """PromoteToSEF command. Returns event_id. Vault tier. Spec 1.5.1, 1.5.1a. Enforces MES and evidence admissibility."""
    require_workspace_for_command(workspace, "promote_to_sef")
    _require_active_claim(read_model, claim_uid)
    profile = policy_profile if policy_profile is not None else default_policy_profile()
    support_links = read_model.get_support_for_claim(claim_uid)
    distinct_evidence_uids: set[str] = set()
    evidence_types: list[str] = []
    for link in support_links:
        span = read_model.get_evidence_span(link.span_uid)
        if span:
            distinct_evidence_uids.add(span.evidence_uid)
    for ev_uid in distinct_evidence_uids:
        ev = read_model.get_evidence_item(ev_uid)
        etype = "unknown"
        if ev and ev.metadata_json:
            try:
                meta = json.loads(ev.metadata_json)
                etype = meta.get("evidence_type") or "unknown"
            except (json.JSONDecodeError, TypeError):
                pass
        evidence_types.append(etype)
    assertions = read_model.list_assertions_for_claim(claim_uid)
    max_conf: float | None = None
    if assertions:
        confs = [a.confidence for a in assertions if a.confidence is not None]
        if confs:
            max_conf = max(confs)
    validate_mes_for_sef(
        profile,
        len(distinct_evidence_uids),
        evidence_types,
        max_conf,
    )
    # T3.3 / E2.4: no SEF from AI-only when policy sets no_sef_from_ai_only
    if (
        profile.evidence_admissibility
        and getattr(profile.evidence_admissibility, "no_sef_from_ai_only", False)
        and distinct_evidence_uids
    ):
        provenance_types = []
        for ev_uid in distinct_evidence_uids:
            ev = read_model.get_evidence_item(ev_uid)
            provenance_types.append(getattr(ev, "provenance_type", None) if ev else None)
        if all(p == "ai_generated" for p in provenance_types):
            raise ValueError(
                "PromoteToSEF: policy disallows SEF when all supporting evidence is AI-generated "
                f"(no_sef_from_ai_only); add at least one human-created or unknown-provenance evidence "
                f"(policy: {profile.profile_id})"
            )
    # Phase 7 (source-independence): require at least N sources with independence rationale when policy sets it
    mes = next((r for r in profile.mes_rules if r.target_claim_type == "SEF"), None)
    if mes is not None and getattr(mes, "min_sources_with_independence_notes", 0) > 0:
        from chronicle.store.commands.sources import get_sources_backing_claim

        sources_backing = get_sources_backing_claim(read_model, claim_uid)
        with_rationale = sum(
            1
            for s in sources_backing
            if s.get("independence_notes") and str(s.get("independence_notes", "")).strip()
        )
        if with_rationale < mes.min_sources_with_independence_notes:
            raise ValueError(
                f"Policy requires at least {mes.min_sources_with_independence_notes} source(s) "
                "with independence rationale recorded; add rationale on the Sources page. "
                f"(policy: {profile.profile_id}); {with_rationale} of {len(sources_backing)} source(s) have rationale."
            )
    claim = read_model.get_claim(claim_uid)
    investigation_uid = claim.investigation_uid if claim else ""
    event_id = generate_event_id()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = ClaimPromotedToSEFPayload(
        claim_uid=claim_uid,
        rationale=rationale,
        evidence_set_refs=evidence_set_refs or [],
        policy_profile_id=policy_profile_id,
    )
    event = Event(
        event_id=event_id,
        event_type=EVENT_CLAIM_PROMOTED_TO_SEF,
        occurred_at=now,
        recorded_at=now,
        investigation_uid=investigation_uid,
        subject_uid=claim_uid,
        actor_type=actor_type,
        actor_id=actor_id,
        workspace=workspace,
        payload=payload.to_dict(),
    )
    store.append(event)
    return event_id


def decompose_claim(
    store: EventStore,
    read_model: ReadModel,
    parent_uid: str,
    child_texts: list[str],
    *,
    actor_id: str = "default",
    actor_type: str = "human",
    workspace: str = "spark",
) -> list[tuple[str, str]]:
    """DecomposeClaim command. Emits one ClaimProposed per child with parent_claim_uid. Returns list of (event_id, claim_uid). Spec 1.5.1, 1.5.1a."""
    parent = read_model.get_claim(parent_uid)
    if parent is None:
        raise ChronicleUserError(f"parent_uid must reference an existing claim: {parent_uid}")
    if parent.current_status == "WITHDRAWN":
        raise ChronicleUserError("cannot decompose a withdrawn claim")
    if not child_texts:
        raise ChronicleUserError("child_texts must be non-empty")
    for i, t in enumerate(child_texts):
        if not t or not t.strip():
            raise ChronicleUserError(f"child_texts[{i}] must be non-empty")
    investigation_uid = parent.investigation_uid
    result: list[tuple[str, str]] = []
    for text in child_texts:
        event_id, claim_uid = propose_claim(
            store,
            investigation_uid,
            text.strip(),
            parent_claim_uid=parent_uid,
            actor_id=actor_id,
            actor_type=actor_type,
            workspace=workspace,
        )
        result.append((event_id, claim_uid))
    return result


def analyze_claim_atomicity(
    store: EventStore,
    read_model: ReadModel,
    claim_uid: str,
    *,
    is_atomic: bool = True,
    suggested_decomposition: list[dict[str, Any]] | None = None,
    overall_confidence: float = 1.0,
    analysis_rationale: str | None = None,
    tool_module_id: str = "chronicle.stub",
    tool_module_version: str = "1.0",
    tool_run_id: str | None = None,
    tool_inputs_hash: str = "",
    actor_id: str = "default",
    actor_type: str = "human",
    workspace: str = "spark",
) -> str:
    """AnalyzeClaimAtomicity stub. Emits ClaimDecompositionAnalyzed. Returns event_id. Spec 1.5.1. No AI."""
    if read_model.get_claim(claim_uid) is None:
        raise ChronicleUserError(f"claim_uid must reference an existing claim: {claim_uid}")
    claim = read_model.get_claim(claim_uid)
    investigation_uid = claim.investigation_uid if claim else ""
    splits: list[SuggestedSplit] = []
    if suggested_decomposition:
        for s in suggested_decomposition:
            splits.append(
                SuggestedSplit(
                    suggested_text=s.get("suggested_text", ""),
                    source_offset_start=s.get("source_offset_start"),
                    source_offset_end=s.get("source_offset_end"),
                    confidence=float(s.get("confidence", 0)),
                    rationale=s.get("rationale"),
                )
            )
    event_id = generate_event_id()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload_obj = ClaimDecompositionAnalyzedPayload(
        claim_uid=claim_uid,
        is_atomic=is_atomic,
        suggested_decomposition=splits,
        overall_confidence=overall_confidence,
        analysis_rationale=analysis_rationale,
        tool_module_id=tool_module_id,
        tool_module_version=tool_module_version,
        tool_run_id=tool_run_id or event_id,
        tool_inputs_hash=tool_inputs_hash,
    )
    event = Event(
        event_id=event_id,
        event_type=EVENT_CLAIM_DECOMPOSITION_ANALYZED,
        occurred_at=now,
        recorded_at=now,
        investigation_uid=investigation_uid,
        subject_uid=claim_uid,
        actor_type=actor_type,
        actor_id=actor_id,
        workspace=workspace,
        payload=payload_obj.to_dict(),
    )
    store.append(event)
    return event_id


def _parse_iso_datetime(s: str | None) -> datetime | None:
    """Parse ISO-8601 string to datetime (UTC). Returns None if invalid or None."""
    if not s or not s.strip():
        return None
    try:
        s = s.strip().replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def _compute_evidence_trust(
    read_model: ReadModel,
    policy_profile: PolicyProfile,
    support_with_inherited: list[LinkWithInherited],
) -> list[dict[str, Any]]:
    """Per supporting evidence: filtered assessments, required_gaps, warnings. Spec evidence-trust-assessments.md Phase 5."""
    evidence_uids: set[str] = set()
    for link, _ in support_with_inherited:
        span = read_model.get_evidence_span(link.span_uid)
        if span:
            evidence_uids.add(span.evidence_uid)

    has_rules = (
        bool(policy_profile.require_assessments)
        or bool(policy_profile.warn_if_below)
        or bool(policy_profile.warn_if_above)
    )
    if not has_rules:
        return []

    now = datetime.now(UTC)
    trusted = set(policy_profile.trusted_providers) if policy_profile.trusted_providers else None
    max_age_hours = policy_profile.assessment_max_age_hours
    ignore_expired = policy_profile.ignore_expired_assessments

    result_list: list[dict[str, Any]] = []
    for evidence_uid in sorted(evidence_uids):
        raw = read_model.get_latest_assessments_for_evidence(evidence_uid)
        # Filter by trusted_providers
        if trusted is not None:
            raw = [a for a in raw if a.provider_id in trusted]
        # Filter by max age
        if max_age_hours is not None:
            filtered: list[EvidenceTrustAssessment] = []
            for a in raw:
                at = _parse_iso_datetime(a.assessed_at)
                if at is not None and (now - at).total_seconds() <= max_age_hours * 3600:
                    filtered.append(a)
            raw = filtered
        # Filter by expired
        if ignore_expired:
            filtered = []
            for a in raw:
                if a.result_expires_at:
                    exp = _parse_iso_datetime(a.result_expires_at)
                    if exp is not None and now < exp:
                        filtered.append(a)
                else:
                    filtered.append(a)
            raw = filtered

        assessments_summary = [
            {
                "provider_id": a.provider_id,
                "assessment_kind": a.assessment_kind,
                "result": a.result,
                "assessed_at": a.assessed_at,
                "result_expires_at": a.result_expires_at,
            }
            for a in raw
        ]

        required_gaps: list[str] = []
        for req in policy_profile.require_assessments:
            match = any(
                a.assessment_kind == req.assessment_kind
                and (req.provider_id is None or a.provider_id == req.provider_id)
                for a in raw
            )
            if not match:
                if req.provider_id:
                    required_gaps.append(
                        f"Assessment required: {req.assessment_kind} (provider: {req.provider_id})"
                    )
                else:
                    required_gaps.append(f"Assessment required: {req.assessment_kind}")

        warnings: list[str] = []
        for w in policy_profile.warn_if_below:
            for a in raw:
                if w.assessment_kind != a.assessment_kind:
                    continue
                if w.provider_id is not None and a.provider_id != w.provider_id:
                    continue
                score = a.result.get("score") if isinstance(a.result, dict) else None
                if score is not None and isinstance(score, (int, float)):
                    if float(score) < w.threshold:
                        warnings.append(
                            f"{w.assessment_kind} score below threshold (score={score}, threshold={w.threshold})"
                        )
                    break
        for w in policy_profile.warn_if_above:
            for a in raw:
                if w.assessment_kind != a.assessment_kind:
                    continue
                if w.provider_id is not None and a.provider_id != w.provider_id:
                    continue
                score = a.result.get("score") if isinstance(a.result, dict) else None
                if score is not None and isinstance(score, (int, float)):
                    if float(score) > w.threshold:
                        warnings.append(
                            f"{w.assessment_kind} score above threshold (score={score}, threshold={w.threshold})"
                        )
                    break

        result_list.append(
            {
                "evidence_uid": evidence_uid,
                "assessments": assessments_summary,
                "required_gaps": required_gaps,
                "warnings": warnings,
            }
        )
    return result_list


def _compute_risk_signals(
    read_model: ReadModel,
    investigation_uid: str,
    support_with_inherited: list[LinkWithInherited],
    open_tensions: list[Any],
) -> list[str]:
    """Phase 6: single-origin support, bulk/single-actor ingest, high contradiction count. Spec Section 2."""
    signals: list[str] = []

    # Single-origin support: all supporting evidence from the same actor
    evidence_uids: set[str] = set()
    for link, _ in support_with_inherited:
        span = read_model.get_evidence_span(link.span_uid)
        if span:
            evidence_uids.add(span.evidence_uid)
    if evidence_uids:
        actors: set[str] = set()
        for eid in evidence_uids:
            ev = read_model.get_evidence_item(eid)
            if ev:
                actors.add(ev.ingested_by_actor_id)
        if len(actors) == 1:
            signals.append("single_origin_support")

    # Bulk/single-actor ingest: multiple evidence items in same investigation in same hour by same actor
    try:
        inv_evidence = read_model.list_evidence_by_investigation(investigation_uid)
    except Exception:
        inv_evidence = []
    # Group by (actor_id, hour(created_at))
    bucket: dict[tuple[str, str], int] = defaultdict(int)
    for ev in inv_evidence:
        at = _parse_iso_datetime(ev.created_at)
        if at:
            hour_key = at.strftime("%Y-%m-%dT%H:00:00Z")
            key = (ev.ingested_by_actor_id, hour_key)
            bucket[key] += 1
    if any(c >= 2 for c in bucket.values()):
        signals.append("bulk_single_actor_ingest")

    # High contradiction count: claim has 2+ open tensions
    if len(open_tensions) >= 2:
        signals.append("high_contradiction_count")

    return signals


def get_defensibility_score(
    read_model: ReadModel,
    claim_uid: str,
    use_strength_weighting: bool = False,
    policy_profile: PolicyProfile | None = None,
) -> DefensibilityScorecard | None:
    """GetDefensibilityScore: compute defensibility scorecard for a claim. Spec epistemic-tools 7.3.
    Returns None if claim not found or claim is WITHDRAWN (epistemology red team: do not score withdrawn claims).
    Phase B.2: when use_strength_weighting=True, weight support/challenge by link strength (default 1.0); count-based remains default."""
    claim = read_model.get_claim(claim_uid)
    if claim is None:
        return None
    if claim.current_status == "WITHDRAWN":
        return None

    support_with_inherited = read_model.get_support_for_claim_including_inherited(claim_uid)
    challenge_with_inherited = read_model.get_challenges_for_claim_including_inherited(claim_uid)
    support_count = len(support_with_inherited)
    challenge_count = len(challenge_with_inherited)

    def _weight(link: Any) -> float:
        s = getattr(link, "strength", None)
        if s is None:
            return 1.0
        return max(0.0, min(1.0, float(s)))

    if use_strength_weighting:
        support_weighted_sum = sum(_weight(link) for link, _ in support_with_inherited)
        challenge_weighted_sum = sum(_weight(link) for link, _ in challenge_with_inherited)
    else:
        support_weighted_sum = float(support_count)
        challenge_weighted_sum = float(challenge_count)

    source_uids: set[str] = set()
    for link, _inherited in support_with_inherited:
        span = read_model.get_evidence_span(link.span_uid)
        if span:
            for esl in read_model.list_evidence_source_links(span.evidence_uid):
                source_uids.add(esl.source_uid)
    independent_sources_count = len(source_uids)

    if use_strength_weighting:
        if challenge_weighted_sum > 0:
            provenance_quality = "challenged"
        elif support_weighted_sum >= 2 and independent_sources_count >= 2:
            provenance_quality = "strong"
        elif support_weighted_sum >= 1:
            provenance_quality = "medium"
        else:
            provenance_quality = "weak"
    else:
        if challenge_count > 0:
            provenance_quality = "challenged"
        elif support_count >= 2 and independent_sources_count >= 2:
            provenance_quality = "strong"
        elif support_count >= 1:
            provenance_quality = "medium"
        else:
            provenance_quality = "weak"

    tensions = read_model.get_tensions_for_claim(claim_uid)
    open_tensions = [t for t in tensions if t.status == "OPEN"]
    if not tensions:
        contradiction_status = "none"
    elif open_tensions:
        contradiction_status = "open"
    elif any(t.status == "ACK" for t in tensions):
        contradiction_status = "acknowledged"
    else:
        contradiction_status = "resolved"

    # Phase 4: per-tension details for defensibility narrative (open and addressed)
    contradiction_handling: list[dict[str, str | None]] = []
    for t in tensions:
        other_claim = t.claim_b_uid if t.claim_a_uid == claim_uid else t.claim_a_uid
        contradiction_handling.append(
            {
                "tension_uid": t.tension_uid,
                "status": t.status,
                "rationale_or_notes": t.notes,
                "other_claim_uid": other_claim,
            }
        )

    temporal_validity = (
        "set" if (claim.temporal_json and claim.temporal_json != "null") else "unset"
    )
    # Phase 5: knowability from temporal_json (known_as_of, knowable_from)
    knowability: dict[str, str | None] = {"known_as_of": None, "knowable_from": None}
    if claim.temporal_json and claim.temporal_json != "null":
        try:
            temporal = json.loads(claim.temporal_json)
            if isinstance(temporal, dict):
                for key in ("known_as_of", "knowable_from"):
                    v = temporal.get(key)
                    knowability[key] = str(v).strip() if v is not None and str(v).strip() else None
        except (TypeError, ValueError):
            pass

    attribution_posture = claim.claim_type if claim.claim_type else "UNKNOWN"

    has_inherited = any(inherited for _link, inherited in support_with_inherited)
    if claim.decomposition_status in ("atomic", "decomposition_complete") and not has_inherited:
        decomposition_precision = "high"
    elif claim.decomposition_status == "partially_decomposed" or has_inherited:
        decomposition_precision = "medium"
    else:
        decomposition_precision = "low"

    # Evidence integrity: are supporting evidence items verified? (Epistemology red team #6)
    evidence_integrity = "verified"
    for link, _ in support_with_inherited:
        span = read_model.get_evidence_span(link.span_uid)
        if span:
            ev = read_model.get_evidence_item(span.evidence_uid)
            if ev:
                if getattr(ev, "integrity_status", "UNVERIFIED") == "MISMATCH":
                    evidence_integrity = "mismatch"
                    break
                if getattr(ev, "integrity_status", "UNVERIFIED") != "VERIFIED":
                    evidence_integrity = "unverified"

    corroboration: dict[str, int | float] = {
        "support_count": support_count,
        "challenge_count": challenge_count,
        "independent_sources_count": independent_sources_count,
    }
    if use_strength_weighting:
        corroboration["support_weighted_sum"] = support_weighted_sum
        corroboration["challenge_weighted_sum"] = challenge_weighted_sum

    evidence_trust: list[dict[str, Any]] | None = None
    if policy_profile is not None:
        evidence_trust = _compute_evidence_trust(read_model, policy_profile, support_with_inherited)
        if not evidence_trust:
            evidence_trust = None  # omit when empty for backward compatibility

    risk_signals = _compute_risk_signals(
        read_model, claim.investigation_uid, support_with_inherited, open_tensions
    )
    # Phase 6 (source-independence): warn when 2+ distinct sources but none have independence rationale
    if independent_sources_count >= 2:
        with_rationale = 0
        for uid in source_uids:
            src = read_model.get_source(uid)
            if src and src.independence_notes and str(src.independence_notes).strip():
                with_rationale += 1
        if with_rationale == 0:
            risk_signals = list(risk_signals) if risk_signals else []
            risk_signals.append("sources_without_independence_rationale")

    return DefensibilityScorecard(
        claim_uid=claim_uid,
        provenance_quality=provenance_quality,
        corroboration=corroboration,
        contradiction_status=contradiction_status,
        temporal_validity=temporal_validity,
        attribution_posture=attribution_posture,
        decomposition_precision=decomposition_precision,
        contradiction_handling=contradiction_handling,
        knowability=knowability,
        evidence_integrity=evidence_integrity,
        evidence_trust=evidence_trust,
        risk_signals=risk_signals if risk_signals else None,
    )


def get_weakest_link(read_model: ReadModel, claim_uid: str) -> WeakestLink | None:
    """GetWeakestLink: single most vulnerable dimension for a claim. Spec epistemic-tools 7.4, Phase 3."""
    scorecard = get_defensibility_score(read_model, claim_uid)
    if scorecard is None:
        return None
    corr = scorecard.corroboration
    if scorecard.provenance_quality == "challenged":
        return WeakestLink(
            claim_uid,
            "corroboration",
            "Challenged by counter-evidence; add support or address challenges.",
            "add_evidence",
        )
    if scorecard.contradiction_status == "open":
        return WeakestLink(
            claim_uid,
            "contradiction",
            "Open tension with another claim; resolve or acknowledge.",
            "resolve_tension",
        )
    if scorecard.provenance_quality == "weak":
        return WeakestLink(
            claim_uid,
            "corroboration",
            "No support linked; add evidence.",
            "add_evidence",
        )
    if (corr.get("independent_sources_count", 0) or 0) < 2 and (
        corr.get("support_count", 0) or 0
    ) >= 1:
        return WeakestLink(
            claim_uid,
            "corroboration",
            "Single source; add independent evidence.",
            "add_evidence",
        )
    if scorecard.temporal_validity == "unset":
        return WeakestLink(
            claim_uid,
            "temporal",
            "No temporal context; set known_as_of or time window.",
            "temporalize",
        )
    if getattr(scorecard, "evidence_integrity", "verified") != "verified":
        return WeakestLink(
            claim_uid,
            "evidence_integrity",
            "Supporting evidence unverified or tampered; run verify or re-ingest.",
            "verify_evidence",
        )
    if scorecard.decomposition_precision == "low":
        return WeakestLink(
            claim_uid,
            "decomposition",
            "Compound or unanalyzed claim; decompose for precise evidence links.",
            "decompose",
        )
    if scorecard.attribution_posture == "UNKNOWN":
        return WeakestLink(
            claim_uid,
            "attribution",
            "Claim type not set; type as SEF, SAC, or inference.",
            "type_claim",
        )
    return WeakestLink(claim_uid, "none", "No critical weakness.", "none")
