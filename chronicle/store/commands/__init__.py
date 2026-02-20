"""Command handlers by domain. Re-export all public commands and MAX_EVIDENCE_BYTES for API."""

from chronicle.core.validation import MAX_EVIDENCE_BYTES
from chronicle.store.commands.accountability import get_accountability_chain
from chronicle.store.commands.artifacts_checkpoints import (
    create_artifact,
    create_checkpoint,
    freeze_artifact_version,
    get_checkpoint_diff,
)
from chronicle.store.commands.audit_trail import (
    get_human_decisions_audit_trail,
    get_reviewer_decision_ledger,
)
from chronicle.store.commands.claims import (
    analyze_claim_atomicity,
    assert_claim,
    decompose_claim,
    downgrade_claim,
    get_defensibility_score,
    get_weakest_link,
    promote_to_sef,
    propose_claim,
    scope_claim,
    temporalize_claim,
    type_claim,
    withdraw_claim,
)
from chronicle.store.commands.defensibility_as_of import get_defensibility_as_of
from chronicle.store.commands.epistemic_risk import (
    explain_defensibility_dimensions,
    explain_weakest_link,
    get_answer_epistemic_risk,
)
from chronicle.store.commands.event_history import get_investigation_event_history
from chronicle.store.commands.evidence import (
    anchor_span,
    generate_chain_of_custody_report,
    ingest_evidence,
    link_challenge,
    link_support,
    mark_evidence_reviewed,
    mark_evidence_reviewed_bulk,
    record_evidence_redaction,
    record_evidence_trust_assessment,
    retract_challenge,
    retract_support,
    supersede_evidence,
    verify_evidence_integrity,
)
from chronicle.store.commands.human_decisions import record_human_confirm, record_human_override
from chronicle.store.commands.impact import get_claim_drift, get_evidence_impact, get_tension_impact
from chronicle.store.commands.investigation import (
    archive_investigation,
    create_investigation,
    export_investigation,
    export_minimal_for_claim,
    import_investigation,
    set_tier,
)
from chronicle.store.commands.multi_profile import get_defensibility_multi_profile
from chronicle.store.commands.reasoning_brief import (
    assemble_reasoning_brief,
    reasoning_brief_to_html,
    reasoning_brief_to_markdown,
)
from chronicle.store.commands.reasoning_trail import (
    get_reasoning_trail_checkpoint,
    get_reasoning_trail_claim,
)
from chronicle.store.commands.sources import (
    get_source_reliability,
    get_sources_backing_claim,
    link_evidence_to_source,
    record_source_independence_notes,
    register_source,
)
from chronicle.store.commands.suggestions import dismiss_suggestion
from chronicle.store.commands.tensions import (
    declare_tension,
    dismiss_tension_suggestion,
    emit_tension_suggestions,
    update_tension_status,
)
from chronicle.store.commands.workflows import get_workflow_state, list_workflows

__all__ = [
    "MAX_EVIDENCE_BYTES",
    "analyze_claim_atomicity",
    "anchor_span",
    "archive_investigation",
    "assert_claim",
    "create_artifact",
    "create_checkpoint",
    "create_investigation",
    "get_defensibility_as_of",
    "get_source_reliability",
    "get_sources_backing_claim",
    "get_human_decisions_audit_trail",
    "get_reviewer_decision_ledger",
    "get_investigation_event_history",
    "declare_tension",
    "decompose_claim",
    "dismiss_suggestion",
    "dismiss_tension_suggestion",
    "downgrade_claim",
    "emit_tension_suggestions",
    "export_investigation",
    "explain_defensibility_dimensions",
    "explain_weakest_link",
    "export_minimal_for_claim",
    "freeze_artifact_version",
    "get_accountability_chain",
    "get_answer_epistemic_risk",
    "generate_chain_of_custody_report",
    "assemble_reasoning_brief",
    "get_checkpoint_diff",
    "get_claim_drift",
    "get_defensibility_multi_profile",
    "get_defensibility_score",
    "get_workflow_state",
    "list_workflows",
    "get_evidence_impact",
    "get_reasoning_trail_claim",
    "get_tension_impact",
    "get_reasoning_trail_checkpoint",
    "reasoning_brief_to_html",
    "reasoning_brief_to_markdown",
    "get_weakest_link",
    "import_investigation",
    "ingest_evidence",
    "link_challenge",
    "link_evidence_to_source",
    "link_support",
    "mark_evidence_reviewed",
    "mark_evidence_reviewed_bulk",
    "propose_claim",
    "promote_to_sef",
    "retract_challenge",
    "retract_support",
    "record_evidence_redaction",
    "record_evidence_trust_assessment",
    "record_human_confirm",
    "record_human_override",
    "record_source_independence_notes",
    "register_source",
    "scope_claim",
    "set_tier",
    "supersede_evidence",
    "temporalize_claim",
    "type_claim",
    "update_tension_status",
    "verify_evidence_integrity",
    "withdraw_claim",
]
