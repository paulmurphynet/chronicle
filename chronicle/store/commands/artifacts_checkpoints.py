"""Artifact and checkpoint commands: create artifact, create checkpoint, freeze artifact version."""

import json
from datetime import UTC, datetime
from typing import Any

from chronicle.core.errors import ChronicleUserError
from chronicle.core.events import (
    EVENT_ARTIFACT_CREATED,
    EVENT_ARTIFACT_VERSION_FROZEN,
    EVENT_CHECKPOINT_CREATED,
    Event,
)
from chronicle.core.payloads import (
    ActorRef,
    ArtifactCreatedPayload,
    ArtifactVersionFrozenPayload,
    CheckpointCreatedPayload,
)
from chronicle.core.policy import (
    PolicyProfile,
    default_policy_profile,
    get_policy_publication_summary,
    require_workspace_for_command,
    validate_checkpoint_scope,
)
from chronicle.core.uid import generate_artifact_uid, generate_checkpoint_uid, generate_event_id
from chronicle.store.protocols import EventStore, ReadModel


def create_artifact(
    store: EventStore,
    read_model: ReadModel,
    investigation_uid: str,
    title: str,
    *,
    artifact_type: str | None = None,
    notes: str | None = None,
    actor_id: str = "default",
    actor_type: str = "human",
    workspace: str = "spark",
) -> tuple[str, str]:
    """CreateArtifact(type, title): title non-empty; emit ArtifactCreated. Returns (event_id, artifact_uid). Forge+ tier. Spec 1.5.1, 1.5.1a."""
    require_workspace_for_command(workspace, "create_artifact")
    if not title or not title.strip():
        raise ChronicleUserError("title must be non-empty")
    if read_model.get_investigation(investigation_uid) is None:
        raise ChronicleUserError(
            f"investigation_uid must reference an existing investigation: {investigation_uid}"
        )
    artifact_uid = generate_artifact_uid()
    event_id = generate_event_id()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = ArtifactCreatedPayload(
        artifact_uid=artifact_uid,
        artifact_type=artifact_type,
        title=title.strip(),
        created_by=ActorRef(actor_type=actor_type, actor_id=actor_id),
        notes=notes,
    )
    event = Event(
        event_id=event_id,
        event_type=EVENT_ARTIFACT_CREATED,
        occurred_at=now,
        recorded_at=now,
        investigation_uid=investigation_uid,
        subject_uid=artifact_uid,
        actor_type=actor_type,
        actor_id=actor_id,
        workspace=workspace,
        payload=payload.to_dict(),
    )
    store.append(event)
    return event_id, artifact_uid


def create_checkpoint(
    store: EventStore,
    read_model: ReadModel,
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
    policy_profile: PolicyProfile | None = None,
) -> tuple[str, str]:
    """CreateCheckpoint(scope_refs): validate scope_refs exist; enforce checkpoint_rules. Returns (event_id, checkpoint_uid). Spec 1.5.1, 1.5.1a."""
    require_workspace_for_command(workspace, "create_checkpoint")
    if read_model.get_investigation(investigation_uid) is None:
        raise ChronicleUserError(
            f"investigation_uid must reference an existing investigation: {investigation_uid}"
        )
    for ref in scope_refs:
        if not ref or not ref.strip():
            raise ChronicleUserError("scope_refs must not contain empty strings")
        if read_model.get_claim(ref) is None and read_model.get_tension(ref) is None:
            raise ChronicleUserError(
                f"scope_ref {ref!r} must reference an existing claim or tension"
            )
    profile = policy_profile if policy_profile is not None else default_policy_profile()
    scope_claim_uids: list[str] = []
    scope_tension_uids: list[str] = []
    claims_typed: list[bool] = []
    tensions_addressed: list[bool] = []
    tensions_have_rationale: list[bool] = []
    for ref in scope_refs:
        claim = read_model.get_claim(ref)
        tension = read_model.get_tension(ref)
        if claim is not None:
            scope_claim_uids.append(ref)
            claims_typed.append(claim.claim_type is not None and bool(claim.claim_type.strip()))
        elif tension is not None:
            scope_tension_uids.append(ref)
            addressed = tension.status != "OPEN"
            tensions_addressed.append(addressed)
            # Phase 3: for addressed tensions, rationale (notes) required when policy enables it
            tensions_have_rationale.append(
                bool(tension.notes and tension.notes.strip()) if addressed else True
            )
    sef_claims = read_model.list_claims_by_type(
        claim_type="SEF", investigation_uid=investigation_uid, limit=1
    )
    validate_checkpoint_scope(
        profile,
        scope_claim_uids,
        scope_tension_uids,
        claims_typed,
        tensions_addressed,
        len(sef_claims) >= 1,
        tensions_have_rationale=tensions_have_rationale if scope_tension_uids else None,
    )
    # Phase 7 (source-independence): SEF claims in scope must meet MES min_sources_with_independence_notes
    mes_sef = next((r for r in profile.mes_rules if r.target_claim_type == "SEF"), None)
    if (
        mes_sef is not None
        and getattr(mes_sef, "min_sources_with_independence_notes", 0) > 0
        and scope_claim_uids
    ):
        from chronicle.store.commands.sources import get_sources_backing_claim

        min_notes = mes_sef.min_sources_with_independence_notes
        for claim_uid in scope_claim_uids:
            claim = read_model.get_claim(claim_uid)
            if claim is None or claim.claim_type != "SEF":
                continue
            sources_backing = get_sources_backing_claim(read_model, claim_uid)
            with_rationale = sum(
                1
                for s in sources_backing
                if s.get("independence_notes") and str(s.get("independence_notes", "")).strip()
            )
            if with_rationale < min_notes:
                raise ChronicleUserError(
                    f"CreateCheckpoint: policy requires at least {min_notes} source(s) "
                    "with independence rationale for SEF claims in scope; "
                    f"claim {claim_uid!r} has {with_rationale}. Add rationale on the Sources page."
                )
    # Epistemologists current review (Chen): block checkpoint if policy requires and any scope claim is one-sided
    cr = profile.checkpoint_rules
    if cr and getattr(cr, "block_checkpoint_if_one_sided", False) and scope_claim_uids:
        from chronicle.store.commands.claims import get_defensibility_score
        from chronicle.store.commands.sources import get_sources_backing_claim

        one_sided: list[str] = []
        for claim_uid in scope_claim_uids:
            sources_backing = get_sources_backing_claim(read_model, claim_uid)
            scorecard = get_defensibility_score(read_model, claim_uid, policy_profile=profile)
            if scorecard is None:
                continue
            challenge_count = scorecard.corroboration.get("challenge_count", 0) or 0
            if len(sources_backing) == 1 and challenge_count == 0:
                one_sided.append(claim_uid)
        if one_sided:
            raise ChronicleUserError(
                "CreateCheckpoint: policy blocks checkpoint when any scope claim is one-sided "
                "(one source only, no challenges). One-sided claim(s): "
                + ", ".join(one_sided[:5])
                + ("..." if len(one_sided) > 5 else "")
                + ". Add evidence or record challenges, or use a profile that does not block."
            )
    if artifact_refs is not None:
        for ref in artifact_refs:
            if read_model.get_artifact(ref) is None:
                raise ChronicleUserError(
                    f"artifact_ref {ref!r} must reference an existing artifact"
                )
    checkpoint_uid = generate_checkpoint_uid()
    event_id = generate_event_id()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    # Phase 9: record policy under which checkpoint was created
    built_under_version: str | None = None
    try:
        import hashlib
        import json

        built_under_version = hashlib.sha256(
            json.dumps(profile.to_dict(), sort_keys=True).encode()
        ).hexdigest()[:16]
    except Exception:
        pass
    policy_summary = get_policy_publication_summary(profile)
    payload = CheckpointCreatedPayload(
        checkpoint_uid=checkpoint_uid,
        scope_refs=scope_refs,
        artifact_refs=artifact_refs,
        reason=reason,
        built_under_policy_id=profile.profile_id,
        built_under_policy_version=built_under_version,
        policy_summary=policy_summary,
        certifying_org_id=certifying_org_id,
        certified_at=certified_at,
    )
    event = Event(
        event_id=event_id,
        event_type=EVENT_CHECKPOINT_CREATED,
        occurred_at=now,
        recorded_at=now,
        investigation_uid=investigation_uid,
        subject_uid=checkpoint_uid,
        actor_type=actor_type,
        actor_id=actor_id,
        workspace=workspace,
        payload=payload.to_dict(),
    )
    store.append(event)
    return event_id, checkpoint_uid


def freeze_artifact_version(
    store: EventStore,
    read_model: ReadModel,
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
    """FreezeArtifactVersion(checkpoint_uid, artifact_uid): validate both exist; no duplicate freeze; emit ArtifactVersionFrozen. Returns event_id. Spec 1.5.1, 1.5.1a. Vault tier."""
    require_workspace_for_command(workspace, "freeze_artifact_version")
    checkpoint = read_model.get_checkpoint(checkpoint_uid)
    if checkpoint is None:
        raise ChronicleUserError(
            f"checkpoint_uid must reference an existing checkpoint: {checkpoint_uid}"
        )
    artifact = read_model.get_artifact(artifact_uid)
    if artifact is None:
        raise ChronicleUserError(
            f"artifact_uid must reference an existing artifact: {artifact_uid}"
        )
    if artifact.investigation_uid != checkpoint.investigation_uid:
        raise ChronicleUserError("checkpoint and artifact must belong to the same investigation")
    if read_model.is_artifact_frozen_at_checkpoint(checkpoint_uid, artifact_uid):
        raise ChronicleUserError(
            f"artifact {artifact_uid} is already frozen at checkpoint {checkpoint_uid}"
        )
    event_id = generate_event_id()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = ArtifactVersionFrozenPayload(
        checkpoint_uid=checkpoint_uid,
        artifact_uid=artifact_uid,
        claim_refs=claim_refs or [],
        evidence_refs=evidence_refs or [],
        tension_refs=tension_refs or [],
        reason=reason,
    )
    event = Event(
        event_id=event_id,
        event_type=EVENT_ARTIFACT_VERSION_FROZEN,
        occurred_at=now,
        recorded_at=now,
        investigation_uid=checkpoint.investigation_uid,
        subject_uid=checkpoint_uid,
        actor_type=actor_type,
        actor_id=actor_id,
        workspace=workspace,
        payload=payload.to_dict(),
    )
    store.append(event)
    return event_id


def get_checkpoint_diff(
    read_model: ReadModel,
    checkpoint_uid_a: str,
    checkpoint_uid_b: str,
) -> dict[str, Any]:
    """Return what changed between two checkpoints (scope_refs diff). Phase A.2.
    Keys: scope_refs_added, scope_refs_removed, claims_added, claims_removed,
    tensions_added, tensions_removed, claims_removed_now_withdrawn.
    Raises ChronicleUserError if either checkpoint is missing or from a different investigation.
    """
    from chronicle.core.errors import ChronicleUserError

    cp_a = read_model.get_checkpoint(checkpoint_uid_a)
    cp_b = read_model.get_checkpoint(checkpoint_uid_b)
    if cp_a is None:
        raise ChronicleUserError(f"Checkpoint not found: {checkpoint_uid_a}")
    if cp_b is None:
        raise ChronicleUserError(f"Checkpoint not found: {checkpoint_uid_b}")
    if cp_a.investigation_uid != cp_b.investigation_uid:
        raise ChronicleUserError("Checkpoints must belong to the same investigation to diff")
    refs_a = set(json.loads(cp_a.scope_refs_json) if cp_a.scope_refs_json else [])
    refs_b = set(json.loads(cp_b.scope_refs_json) if cp_b.scope_refs_json else [])
    added = sorted(refs_b - refs_a)
    removed = sorted(refs_a - refs_b)
    claims_added = [r for r in added if read_model.get_claim(r) is not None]
    claims_removed = [r for r in removed if read_model.get_claim(r) is not None]
    tensions_added = [r for r in added if read_model.get_tension(r) is not None]
    tensions_removed = [r for r in removed if read_model.get_tension(r) is not None]
    claims_removed_now_withdrawn = [
        r
        for r in claims_removed
        if (c := read_model.get_claim(r)) and getattr(c, "current_status", None) == "WITHDRAWN"
    ]
    return {
        "checkpoint_uid_a": checkpoint_uid_a,
        "checkpoint_uid_b": checkpoint_uid_b,
        "investigation_uid": cp_a.investigation_uid,
        "scope_refs_added": added,
        "scope_refs_removed": removed,
        "claims_added": claims_added,
        "claims_removed": claims_removed,
        "tensions_added": tensions_added,
        "tensions_removed": tensions_removed,
        "claims_removed_now_withdrawn": claims_removed_now_withdrawn,
    }
