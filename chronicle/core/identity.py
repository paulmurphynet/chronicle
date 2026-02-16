"""Identity Provider (IdP) abstraction for pluggable actor binding. Epistemology Phase 5."""

import os
from dataclasses import dataclass, field
from typing import Any, Protocol

# Verification levels (spec identity-providers.md Section 2.2)
VERIFICATION_NONE = "none"
VERIFICATION_CLAIMED = "claimed"
VERIFICATION_ACCOUNT = "account"
VERIFICATION_VERIFIED_CREDENTIAL = "verified_credential"
VERIFICATION_DECENTRALIZED = "decentralized"
VERIFICATION_ZK_ATTESTED = "zk_attested"

VERIFICATION_LEVELS = (
    VERIFICATION_NONE,
    VERIFICATION_CLAIMED,
    VERIFICATION_ACCOUNT,
    VERIFICATION_VERIFIED_CREDENTIAL,
    VERIFICATION_DECENTRALIZED,
    VERIFICATION_ZK_ATTESTED,
)

# Env: which IdP adapter to use (none | traditional | gov_id | did | zk)
CHRONICLE_IDENTITY_PROVIDER_ENV = "CHRONICLE_IDENTITY_PROVIDER"
# Env: when set, API overwrites client-supplied actor with IdP principal when present
CHRONICLE_OVERRIDE_ACTOR_FROM_AUTH_ENV = "CHRONICLE_OVERRIDE_ACTOR_FROM_AUTH"


@dataclass
class PrincipalInfo:
    """Result of IdP resolve: principal to bind to actor_id, type, verification level, optional attestations."""

    principal_id: str
    actor_type: str = "human"
    verification_level: str = VERIFICATION_NONE
    attestations: dict[str, Any] = field(default_factory=dict)

    @property
    def is_bound(self) -> bool:
        """True if IdP returned a non-empty principal (server should use this, not client-supplied)."""
        return bool(self.principal_id and self.principal_id.strip())


class IdentityProvider(Protocol):
    """Protocol for Identity Provider adapters. Given a request (or session), return principal info."""

    def resolve(self, request: Any) -> PrincipalInfo:
        """Return principal and verification level for this request. Empty principal_id = no binding."""
        ...


class NoneIdP:
    """No binding. Actor is as claimed by client or default. Verification level 'none' or 'claimed'."""

    def resolve(self, request: Any) -> PrincipalInfo:
        # Optional: read X-Actor-Id / X-Actor-Type for "claimed" when no auth
        principal_id = ""
        level = VERIFICATION_NONE
        actor_type = "human"
        if hasattr(request, "headers"):
            h = getattr(request, "headers", None)
            if h and hasattr(h, "get"):
                aid = (h.get("x-actor-id") or h.get("X-Actor-Id") or "").strip()
                if aid:
                    principal_id = aid
                    level = VERIFICATION_CLAIMED
                at = (h.get("x-actor-type") or h.get("X-Actor-Type") or "human").strip()
                if at in ("human", "tool", "system"):
                    actor_type = at
        return PrincipalInfo(
            principal_id=principal_id,
            actor_type=actor_type,
            verification_level=level,
        )


class TraditionalIdP:
    """
    Traditional account: read principal from request.state (set by auth middleware).
    When CHRONICLE_OVERRIDE_ACTOR_FROM_AUTH is set and state.actor_id is present, return it.
    """

    def resolve(self, request: Any) -> PrincipalInfo:
        override = os.environ.get(CHRONICLE_OVERRIDE_ACTOR_FROM_AUTH_ENV, "").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        principal_id = ""
        actor_type = "human"
        if hasattr(request, "state"):
            state = getattr(request, "state", None)
            if state and override:
                principal_id = (getattr(state, "actor_id", None) or "").strip()
                at = (getattr(state, "actor_type", None) or "human").strip()
                if at in ("human", "tool", "system"):
                    actor_type = at
        if not principal_id and hasattr(request, "headers"):
            h = getattr(request, "headers", None)
            if h and hasattr(h, "get"):
                aid = (h.get("x-actor-id") or h.get("X-Actor-Id") or "").strip()
                if aid:
                    principal_id = aid
                    actor_type = (h.get("x-actor-type") or h.get("X-Actor-Type") or "human").strip()
                    if actor_type not in ("human", "tool", "system"):
                        actor_type = "human"
        level = VERIFICATION_ACCOUNT if principal_id else VERIFICATION_NONE
        return PrincipalInfo(
            principal_id=principal_id,
            actor_type=actor_type,
            verification_level=level,
        )


def get_identity_provider() -> IdentityProvider:
    """Return the IdP adapter selected by CHRONICLE_IDENTITY_PROVIDER (none | traditional | gov_id | did | zk)."""
    name = (os.environ.get(CHRONICLE_IDENTITY_PROVIDER_ENV) or "none").strip().lower()
    if name == "traditional":
        return TraditionalIdP()
    if name in ("gov_id", "did", "zk"):
        # Stub: not implemented; fall back to none. Document in spec; implement in later PRs.
        return NoneIdP()
    return NoneIdP()


def get_effective_actor_from_request(request: Any) -> tuple[str, str, str]:
    """
    Resolve effective (actor_id, actor_type, verification_level) for this request.
    Uses configured IdP. When IdP returns a bound principal, use it; otherwise use default or headers.
    Returns: (actor_id, actor_type, verification_level).
    """
    idp = get_identity_provider()
    info = idp.resolve(request)
    if info.is_bound:
        return (info.principal_id, info.actor_type, info.verification_level)
    # No binding: use IdP result if it had claimed from headers, else default
    if info.principal_id:
        return (info.principal_id, info.actor_type, info.verification_level)
    return ("default", "human", VERIFICATION_NONE)
