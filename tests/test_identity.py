"""Tests for identity module: NoneIdP, get_effective_actor_from_request."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from chronicle.core.identity import (
    CHRONICLE_IDENTITY_PROVIDER_ENV,
    CHRONICLE_OVERRIDE_ACTOR_FROM_AUTH_ENV,
    VERIFICATION_ACCOUNT,
    VERIFICATION_CLAIMED,
    VERIFICATION_NONE,
    get_effective_actor_from_request,
    get_identity_provider,
    NoneIdP,
    PrincipalInfo,
    TraditionalIdP,
)


def _make_request(headers: dict[str, str] | None = None, state: Any = None) -> Any:
    """Minimal request-like object with headers and optional state."""
    h = headers or {}
    class Req:
        pass
    req = Req()
    req.headers = h
    req.request_state = state
    req.state = state
    return req


def test_principal_info_is_bound() -> None:
    """PrincipalInfo.is_bound is True when principal_id is non-empty."""
    assert PrincipalInfo(principal_id="alice").is_bound is True
    assert PrincipalInfo(principal_id="  ").is_bound is False
    assert PrincipalInfo(principal_id="").is_bound is False


def test_none_idp_no_headers_returns_default() -> None:
    """NoneIdP with no headers returns empty principal and VERIFICATION_NONE."""
    req = _make_request()
    info = NoneIdP().resolve(req)
    assert info.principal_id == ""
    assert info.verification_level == VERIFICATION_NONE
    assert info.actor_type == "human"


def test_none_idp_with_x_actor_id_returns_claimed() -> None:
    """NoneIdP with X-Actor-Id returns that id and VERIFICATION_CLAIMED."""
    req = _make_request({"X-Actor-Id": "jane_doe", "X-Actor-Type": "human"})
    info = NoneIdP().resolve(req)
    assert info.principal_id == "jane_doe"
    assert info.verification_level == VERIFICATION_CLAIMED
    assert info.actor_type == "human"


def test_none_idp_lowercase_headers() -> None:
    """NoneIdP accepts lowercase x-actor-id."""
    req = _make_request({"x-actor-id": "bob", "x-actor-type": "tool"})
    info = NoneIdP().resolve(req)
    assert info.principal_id == "bob"
    assert info.actor_type == "tool"


def test_get_effective_actor_from_request_no_binding() -> None:
    """With no headers, get_effective_actor_from_request returns default, human, none."""
    req = _make_request()
    # Ensure we use NoneIdP (default)
    prev = os.environ.get("CHRONICLE_IDENTITY_PROVIDER")
    try:
        if "CHRONICLE_IDENTITY_PROVIDER" in os.environ:
            del os.environ["CHRONICLE_IDENTITY_PROVIDER"]
        actor_id, actor_type, verification_level = get_effective_actor_from_request(req)
        assert actor_id == "default"
        assert actor_type == "human"
        assert verification_level == VERIFICATION_NONE
    finally:
        if prev is not None:
            os.environ["CHRONICLE_IDENTITY_PROVIDER"] = prev
        elif "CHRONICLE_IDENTITY_PROVIDER" in os.environ:
            del os.environ["CHRONICLE_IDENTITY_PROVIDER"]


def test_get_effective_actor_from_request_with_headers() -> None:
    """With X-Actor-Id header, get_effective_actor_from_request returns claimed identity."""
    req = _make_request({"X-Actor-Id": "curator_1", "X-Actor-Type": "human"})
    prev = os.environ.get("CHRONICLE_IDENTITY_PROVIDER")
    try:
        if "CHRONICLE_IDENTITY_PROVIDER" in os.environ:
            del os.environ["CHRONICLE_IDENTITY_PROVIDER"]
        actor_id, actor_type, verification_level = get_effective_actor_from_request(req)
        assert actor_id == "curator_1"
        assert actor_type == "human"
        assert verification_level == VERIFICATION_CLAIMED
    finally:
        if prev is not None:
            os.environ["CHRONICLE_IDENTITY_PROVIDER"] = prev
        elif "CHRONICLE_IDENTITY_PROVIDER" in os.environ:
            del os.environ["CHRONICLE_IDENTITY_PROVIDER"]


def test_get_identity_provider_returns_none_idp_by_default() -> None:
    """get_identity_provider returns NoneIdP when env is unset or 'none'."""
    prev = os.environ.get(CHRONICLE_IDENTITY_PROVIDER_ENV)
    try:
        for val in (None, "none", "NONE"):
            if val is None and CHRONICLE_IDENTITY_PROVIDER_ENV in os.environ:
                del os.environ[CHRONICLE_IDENTITY_PROVIDER_ENV]
            elif val is not None:
                os.environ[CHRONICLE_IDENTITY_PROVIDER_ENV] = val
            idp = get_identity_provider()
            assert isinstance(idp, NoneIdP)
    finally:
        if prev is not None:
            os.environ[CHRONICLE_IDENTITY_PROVIDER_ENV] = prev
        elif CHRONICLE_IDENTITY_PROVIDER_ENV in os.environ:
            del os.environ[CHRONICLE_IDENTITY_PROVIDER_ENV]


def test_get_identity_provider_returns_traditional_idp() -> None:
    """get_identity_provider returns TraditionalIdP when env is 'traditional'."""
    prev = os.environ.get(CHRONICLE_IDENTITY_PROVIDER_ENV)
    try:
        os.environ[CHRONICLE_IDENTITY_PROVIDER_ENV] = "traditional"
        idp = get_identity_provider()
        assert isinstance(idp, TraditionalIdP)
    finally:
        if prev is not None:
            os.environ[CHRONICLE_IDENTITY_PROVIDER_ENV] = prev
        elif CHRONICLE_IDENTITY_PROVIDER_ENV in os.environ:
            del os.environ[CHRONICLE_IDENTITY_PROVIDER_ENV]


def test_get_identity_provider_stub_for_gov_id_did_zk() -> None:
    """get_identity_provider returns a stub IdP for gov_id, did, zk (on hold by design; resolves like NoneIdP)."""
    prev = os.environ.get(CHRONICLE_IDENTITY_PROVIDER_ENV)
    try:
        for name in ("gov_id", "did", "zk"):
            os.environ[CHRONICLE_IDENTITY_PROVIDER_ENV] = name
            idp = get_identity_provider()
            # Stub resolves like NoneIdP (e.g. reads headers or returns empty)
            info = idp.resolve(_make_request({"X-Actor-Id": "test_actor"}))
            assert info.principal_id == "test_actor" and info.verification_level == "claimed"
    finally:
        if prev is not None:
            os.environ[CHRONICLE_IDENTITY_PROVIDER_ENV] = prev
        elif CHRONICLE_IDENTITY_PROVIDER_ENV in os.environ:
            del os.environ[CHRONICLE_IDENTITY_PROVIDER_ENV]


def test_traditional_idp_with_state_override() -> None:
    """TraditionalIdP with override and request.state.actor_id returns VERIFICATION_ACCOUNT."""
    req = _make_request({"X-Actor-Id": "header_actor"}, state=None)
    # Add state with actor_id (TraditionalIdP reads getattr(state, "actor_id", None))
    class State:
        actor_id = "auth_principal"
        actor_type = "human"
    req.state = State()
    prev_override = os.environ.get(CHRONICLE_OVERRIDE_ACTOR_FROM_AUTH_ENV)
    prev_idp = os.environ.get(CHRONICLE_IDENTITY_PROVIDER_ENV)
    try:
        os.environ[CHRONICLE_OVERRIDE_ACTOR_FROM_AUTH_ENV] = "true"
        os.environ[CHRONICLE_IDENTITY_PROVIDER_ENV] = "traditional"
        info = TraditionalIdP().resolve(req)
        assert info.principal_id == "auth_principal"
        assert info.verification_level == VERIFICATION_ACCOUNT
    finally:
        if prev_override is not None:
            os.environ[CHRONICLE_OVERRIDE_ACTOR_FROM_AUTH_ENV] = prev_override
        elif CHRONICLE_OVERRIDE_ACTOR_FROM_AUTH_ENV in os.environ:
            del os.environ[CHRONICLE_OVERRIDE_ACTOR_FROM_AUTH_ENV]
        if prev_idp is not None:
            os.environ[CHRONICLE_IDENTITY_PROVIDER_ENV] = prev_idp
        elif CHRONICLE_IDENTITY_PROVIDER_ENV in os.environ:
            del os.environ[CHRONICLE_IDENTITY_PROVIDER_ENV]


def test_traditional_idp_fallback_to_headers_when_no_state() -> None:
    """TraditionalIdP with no auth-bound state treats X-Actor-Id as claimed identity."""
    req = _make_request({"X-Actor-Id": "header_actor", "X-Actor-Type": "tool"})
    req.state = None
    prev = os.environ.get(CHRONICLE_IDENTITY_PROVIDER_ENV)
    try:
        os.environ[CHRONICLE_IDENTITY_PROVIDER_ENV] = "traditional"
        info = TraditionalIdP().resolve(req)
        assert info.principal_id == "header_actor"
        assert info.actor_type == "tool"
        assert info.verification_level == VERIFICATION_CLAIMED
    finally:
        if prev is not None:
            os.environ[CHRONICLE_IDENTITY_PROVIDER_ENV] = prev
        elif CHRONICLE_IDENTITY_PROVIDER_ENV in os.environ:
            del os.environ[CHRONICLE_IDENTITY_PROVIDER_ENV]


def test_none_idp_actor_type_system() -> None:
    """NoneIdP accepts x-actor-type: system."""
    req = _make_request({"x-actor-id": "sys1", "x-actor-type": "system"})
    info = NoneIdP().resolve(req)
    assert info.principal_id == "sys1"
    assert info.actor_type == "system"
