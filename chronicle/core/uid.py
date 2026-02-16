"""UID generation. Prefix registry per spec Section 16.1.3."""

import uuid

# Prefixes (semantic hints only; do not infer type solely from prefix)
PREFIX_INVESTIGATION = "inv_"
PREFIX_CLAIM = "claim_"
PREFIX_EVIDENCE = "evidence_"
PREFIX_SPAN = "span_"
PREFIX_TENSION = "tension_"
PREFIX_SUGGESTION = "suggestion_"
PREFIX_ASSERTION = "assertion_"
PREFIX_LINK = "link_"
PREFIX_SOURCE = "src_"
PREFIX_ARTIFACT = "artifact_"
PREFIX_CHECKPOINT = "checkpoint_"
PREFIX_ACTOR = "actor_"
PREFIX_SUPERSESSION = "supersession_"
PREFIX_REPORT = "report_"


def generate_ulid() -> str:
    """Generate a unique, URL-safe id (UUID4 hex). Replace with real ULID later if desired."""
    return uuid.uuid4().hex


def generate_investigation_uid() -> str:
    """Generate investigation UID: inv_<ulid>."""
    return PREFIX_INVESTIGATION + generate_ulid()


def generate_event_id() -> str:
    """Generate event ID (ULID recommended in spec; we use same as ulid for now)."""
    return generate_ulid()


def generate_evidence_uid() -> str:
    """Generate evidence UID: evidence_<ulid>. Spec Section 16.1.3."""
    return PREFIX_EVIDENCE + generate_ulid()


def generate_claim_uid() -> str:
    """Generate claim UID: claim_<ulid>. Spec Section 16.1.3."""
    return PREFIX_CLAIM + generate_ulid()


def generate_span_uid() -> str:
    """Generate span UID: span_<ulid>. Spec Section 16.1.3."""
    return PREFIX_SPAN + generate_ulid()


def generate_link_uid() -> str:
    """Generate link UID: link_<ulid>. Spec Section 16.1.3."""
    return PREFIX_LINK + generate_ulid()


def generate_assertion_uid() -> str:
    """Generate assertion UID: assertion_<ulid>. Spec Section 16.1.3."""
    return PREFIX_ASSERTION + generate_ulid()


def generate_tension_uid() -> str:
    """Generate tension UID: tension_<ulid>. Spec Section 16.1.3."""
    return PREFIX_TENSION + generate_ulid()


def generate_suggestion_uid() -> str:
    """Generate tension suggestion UID for TensionSuggested. AI plan Phase 7."""
    return PREFIX_SUGGESTION + generate_ulid()


def generate_supersession_uid() -> str:
    """Generate supersession UID for EvidenceSuperseded. Spec 14.4.7."""
    return PREFIX_SUPERSESSION + generate_ulid()


def generate_source_uid() -> str:
    """Generate source UID: src_<ulid>. Spec Section 16.1.3."""
    return PREFIX_SOURCE + generate_ulid()


def generate_report_uid() -> str:
    """Generate report UID for chain-of-custody reports. Spec 15.1.25."""
    return PREFIX_REPORT + generate_ulid()


def generate_artifact_uid() -> str:
    """Generate artifact UID: artifact_<ulid>. Spec Section 16.1.3."""
    return PREFIX_ARTIFACT + generate_ulid()


def generate_checkpoint_uid() -> str:
    """Generate checkpoint UID: checkpoint_<ulid>. Spec Section 16.1.3."""
    return PREFIX_CHECKPOINT + generate_ulid()
