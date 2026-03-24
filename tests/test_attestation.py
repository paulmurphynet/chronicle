"""Tests for attestation payload helper."""

from __future__ import annotations

from chronicle.store.commands.attestation import apply_attestation_to_payload


def test_apply_attestation_to_payload_adds_verification_level() -> None:
    """When verification_level is provided, it is set on the payload."""
    payload: dict = {}
    apply_attestation_to_payload(payload, verification_level="claimed")
    assert payload["_verification_level"] == "claimed"
    assert "_attestation_ref" not in payload


def test_apply_attestation_to_payload_adds_attestation_ref() -> None:
    """When attestation_ref is provided, it is set on the payload."""
    payload: dict = {}
    apply_attestation_to_payload(payload, attestation_ref="ref-456")
    assert payload["_attestation_ref"] == "ref-456"
    assert "_verification_level" not in payload


def test_apply_attestation_to_payload_both() -> None:
    """Both verification_level and attestation_ref can be set."""
    payload: dict = {"existing": "key"}
    apply_attestation_to_payload(
        payload,
        verification_level="verified_credential",
        attestation_ref="att-789",
    )
    assert payload["_verification_level"] == "verified_credential"
    assert payload["_attestation_ref"] == "att-789"
    assert payload["existing"] == "key"


def test_apply_attestation_to_payload_none_unchanged() -> None:
    """When neither is provided, payload is unchanged."""
    payload: dict = {"a": 1}
    apply_attestation_to_payload(payload)
    assert payload == {"a": 1}
