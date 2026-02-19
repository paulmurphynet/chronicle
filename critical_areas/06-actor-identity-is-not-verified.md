# Critical area 06: Actor identity is not verified

**Risk:** Assuming that **actor_id** or **verification_level** on events means Chronicle has verified who performed the action. We **record** who the writer says did it; we do **not** verify credentials or bind identity ourselves.

---

## Narrative

Every event stores **actor_id** and **actor_type** (`human` | `tool` | `system`). Optionally, events can store **verification_level** (e.g. `claimed`, `account`, `verified_credential`) and attestation references. That supports audit trails and human-in-the-loop workflows: "who did what" is recorded on each write event.

But **identity is as asserted by the writer** (or by the deployment’s auth layer). Chronicle persists the binding you give it; it does **not**:

- Verify that the actor_id corresponds to a real person or system.
- Validate credentials, tokens, or attested claims.
- Guarantee that the same actor_id across events is the same real-world entity.

When the API uses an Identity Provider (IdP) adapter, the **deployment** is responsible for resolving the request to a principal and verification level. Chronicle stores whatever the IdP (or the default NoneIdP) returns. So:

- **verification_level = "verified_credential"** means: "the deployment’s IdP reported this level." It does **not** mean "Chronicle independently verified the credential."
- **actor_id = "jane_doe"** means: "the writer (or auth) said the actor is jane_doe." We do not check that jane_doe exists or that the request actually came from her.

Over-relying on actor_id or verification_level as proof of who acted is a risk for compliance and audit. For high-assurance settings, identity binding and verification must be handled outside Chronicle (auth, IdP, verified credentials) and then fed in; Chronicle only records the result.

---

## Technical

- **Where actor is stored:** Every event payload includes `actor_id` and `actor_type`; optional `verification_level` and attestation refs when the deployment supplies them. See event schema and `chronicle.store` write paths (e.g. investigation, claim, evidence, link commands).
- **Identity module:** `chronicle/core/identity.py` defines the **IdentityProvider** protocol and adapters (e.g. `NoneIdP`, `TraditionalIdP`). `NoneIdP` uses client-supplied headers (e.g. `X-Actor-Id`) and sets verification to `claimed` or `none`; it does not verify. Other IdPs are deployment-specific; Chronicle only calls `resolve(request)` and persists the result.
- **Docs:** `docs/human-in-the-loop-and-attestation.md` states: "We **record** who did it … We do **not** verify credentials ourselves—that is a deployment concern." `docs/verification-guarantees.md` (Section 4): "That actors are who they claim to be. Actor identity in events is as asserted by the writer; binding to authenticated identities is a deployment concern."

---

## What to remember

- **Actor identity and verification_level are as asserted—not verified by Chronicle.** Use them for audit and attribution given your deployment’s trust model; do not treat them as independent proof of who acted.
- **Verification_level** reflects what your IdP (or default) reported; Chronicle does not validate credentials. For high-assurance workflows, ensure your auth and IdP are trusted and then document that in your assurance story.
- When presenting an attested chronicle, clarify: "Actor and verification level are as supplied by our deployment; Chronicle records them and does not verify identity or credentials."

---

**← [Critical areas index](README.md)** | **← Previous:** [05 — Policy and thresholds](05-policy-and-thresholds.md)
