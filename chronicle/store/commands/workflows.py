"""Epistemic workflows: named sequences of steps with queryable state. E6.1."""

from pathlib import Path
from typing import Any

from chronicle.core.policy import (
    POLICY_FILENAME,
    check_publication_readiness,
    load_policy_profile,
)
from chronicle.core.validation import MAX_LIST_LIMIT
from chronicle.store.protocols import ReadModel

WORKFLOW_PUBLICATION_READINESS = "publication_readiness"

# Built-in workflow definitions (id -> display_name). E6.1.
WORKFLOWS: list[dict[str, str]] = [
    {"workflow_id": WORKFLOW_PUBLICATION_READINESS, "display_name": "Publication readiness"},
]


def list_workflows() -> list[dict[str, str]]:
    """Return available workflow ids and display names."""
    return list(WORKFLOWS)


def get_workflow_state(
    read_model: ReadModel,
    project_dir: Path | None,
    investigation_uid: str,
    workflow_id: str,
) -> dict[str, Any] | None:
    """Return workflow state for an investigation. Returns None if investigation or workflow not found.

    For workflow_id 'publication_readiness': steps are derived from policy checkpoint_rules
    (all claims typed, all tensions addressed, at least one SEF). Each step has step_id, label, done.
    """
    if read_model.get_investigation(investigation_uid) is None:
        return None
    if workflow_id != WORKFLOW_PUBLICATION_READINESS:
        return None

    profile = load_policy_profile((project_dir / POLICY_FILENAME) if project_dir else None)
    if profile is None:
        return None

    cr = profile.checkpoint_rules
    # Build step definitions from profile (only steps that are required)
    step_defs: list[tuple[str, str]] = []
    if cr and cr.requires_all_claims_typed:
        step_defs.append(("claims_typed", "All claims have a type"))
    if cr and cr.requires_all_tensions_addressed:
        step_defs.append(("tensions_addressed", "All tensions addressed"))
    if cr and cr.requires_at_least_one_sef:
        step_defs.append(("has_sef", "At least one single-source fact claim"))
    if not step_defs:
        # No checkpoint rules or all optional: treat as single "ready" step
        step_defs.append(("ready", "No policy requirements"))

    claims = read_model.list_claims_by_type(
        investigation_uid=investigation_uid,
        include_withdrawn=False,
        limit=MAX_LIST_LIMIT,
    )
    tensions = read_model.list_tensions(investigation_uid, limit=MAX_LIST_LIMIT)
    claim_uids = [c.claim_uid for c in claims]
    tension_uids = [t.tension_uid for t in tensions]
    claims_typed = [c.claim_type is not None and bool((c.claim_type or "").strip()) for c in claims]
    tensions_addressed = [t.status != "OPEN" for t in tensions]
    sef_claims = read_model.list_claims_by_type(
        claim_type="SEF",
        investigation_uid=investigation_uid,
        limit=1,
    )
    investigation_has_sef = len(sef_claims) > 0

    readiness = check_publication_readiness(
        profile,
        claim_uids,
        tension_uids,
        claims_typed,
        tensions_addressed,
        investigation_has_sef,
    )

    done_by_step = {
        "claims_typed": readiness.get("claims_typed_ok", False),
        "tensions_addressed": readiness.get("tensions_addressed_ok", False),
        "has_sef": readiness.get("has_sef_ok", False),
        "ready": True,
    }
    steps: list[dict[str, Any]] = []
    for step_id, label in step_defs:
        steps.append(
            {
                "step_id": step_id,
                "label": label,
                "done": done_by_step.get(step_id, False),
            }
        )
    completed = sum(1 for s in steps if s["done"])
    total = len(steps)
    return {
        "workflow_id": workflow_id,
        "display_name": "Publication readiness",
        "investigation_uid": investigation_uid,
        "steps": steps,
        "completed_count": completed,
        "total_steps": total,
        "all_done": completed == total and total > 0,
    }
