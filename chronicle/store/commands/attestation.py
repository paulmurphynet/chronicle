"""Helpers for attestation metadata on event payloads (payload-only; no schema change)."""


def apply_attestation_to_payload(
    payload: dict,
    *,
    verification_level: str | None = None,
    attestation_ref: str | None = None,
) -> None:
    """Set _verification_level and/or _attestation_ref on payload when provided. Mutates payload in place."""
    if verification_level:
        payload["_verification_level"] = verification_level
    if attestation_ref:
        payload["_attestation_ref"] = attestation_ref
