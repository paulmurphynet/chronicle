# Identity providers (IdP)

Chronicle supports pluggable **identity providers** so the server can bind the acting identity to a request (or CLI run) and optionally store a **verification level**. This doc describes the built-in adapters and how to implement additional ones (e.g. gov_id, did, zk).

---

## Configured IdP

Set **`CHRONICLE_IDENTITY_PROVIDER`** to one of:

| Value | Behavior |
|-------|----------|
| `none` (default) | No binding. Actor from headers (X-Actor-Id, X-Actor-Type) or default. |
| `traditional` | Read principal from request.state (set by auth middleware). Use when you run behind your own auth. |
| `gov_id` | Reserved; currently resolves like `none`. Implement by adding a real adapter (see below). |
| `did` | Reserved; currently resolves like `none`. Implement by adding a real adapter (see below). |
| `zk` | Reserved; currently resolves like `none`. Implement by adding a real adapter (see below). |

When `CHRONICLE_OVERRIDE_ACTOR_FROM_AUTH` is set and the IdP returns a bound principal, the server uses that as `actor_id` and can store a verification level on each write event.

---

## Implementing a custom IdP (gov_id, did, zk)

1. **Implement the protocol** — In `chronicle.core.identity`, the IdP must implement the **IdentityProvider** protocol: a `resolve(request) -> PrincipalInfo` method. `PrincipalInfo` has `principal_id`, `actor_type`, `verification_level`, and optional `attestations`.

2. **Return a bound principal** — When the IdP can authenticate the request (e.g. verify a government ID, resolve a DID, or verify a zero-knowledge proof), return a non-empty `principal_id` and the appropriate `verification_level` (e.g. `verified_credential`, `decentralized`, `zk_attested` from the constants in `chronicle.core.identity`).

3. **Register in `get_identity_provider()`** — In `chronicle/core/identity.py`, in `get_identity_provider()`, add a branch for your provider name (e.g. `gov_id`, `did`, `zk`) and return an instance of your adapter instead of the stub.

4. **Request shape** — For the HTTP API, `request` is the FastAPI request; use `request.headers`, `request.state`, or your auth middleware’s payload. For CLI, the request object may be minimal; document how your IdP is invoked (e.g. env vars, config file).

Example skeleton for a hypothetical gov_id adapter:

```python
class GovIdIdP:
    def resolve(self, request: Any) -> PrincipalInfo:
        # e.g. read token from header, verify with gov IdP, return principal_id + verification_level
        principal_id = ""  # or from your verification
        return PrincipalInfo(
            principal_id=principal_id,
            actor_type="human",
            verification_level=VERIFICATION_VERIFIED_CREDENTIAL if principal_id else VERIFICATION_NONE,
        )
```

Then in `get_identity_provider()`: when `name == "gov_id"`, return `GovIdIdP()`.

See [Human-in-the-loop and attestation](human-in-the-loop-and-attestation.md) for how verification level is stored and used.
