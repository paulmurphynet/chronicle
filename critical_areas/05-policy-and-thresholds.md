# Critical area 05: Policy and thresholds

**Risk:** Treating policy rules and thresholds (e.g. “strong = at least 2 supports and 2 independent sources”) as **domain-validated** or **scientifically grounded**. They are **configurable** and **structural**; we do not validate that they match any particular domain standard or empirical outcome.

---

## Narrative

Defensibility is **policy-relative**. The same claim can be “strong” under one policy (e.g. minimal thresholds) and “weak” under another (e.g. stricter source or support requirements). Policy profiles encode rules like minimum support count, minimum independent sources, and how tensions affect the score.

Those rules are **chosen** by the deployer or the organization—not derived from a universal standard or from empirical validation in a given domain. So:

- The thresholds in the **default** logic (e.g. 2 supports + 2 independent sources → strong) are **design choices** for the reference implementation, not a result of “this is what journalism (or legal, or compliance) requires.”
- A policy profile might say “for SEF we require 2 independent sources.” That reflects what someone encoded; we don’t check that this matches any official or evidence-based standard.

Over-relying on the score as if it were backed by domain-validated or scientifically validated policy is a risk. The score is only as good as the policy and the data; neither is validated by Chronicle for fitness to a particular domain.

---

## Technical

- **Where thresholds appear:** `chronicle/store/commands/claims.py`, `get_defensibility_score()`. The provenance_quality logic uses fixed conditions: e.g. support_count ≥ 2 and independent_sources_count ≥ 2 for “strong.” Policy can influence the score via `policy_profile` (e.g. evidence_trust, risk_signals); the core strong/medium/weak/challenged logic is in this file.
- **Policy and compatibility:** `chronicle/core/policy.py` and `chronicle/core/policy_compat.py` define and apply policy; the read model and commands can take an optional policy profile. Thresholds and rules are defined in policy structures, not by external validation.
- **Docs:** `docs/epistemology-scope.md` states that defensibility is “structural and policy-driven (counts, thresholds, open tensions)” and that we have “no commitment to foundationalism, coherentism, or reliabilism.”

---

## What to remember

- **Policy and thresholds are configurable and structural—not empirically or domain-validated by us.** Use them to enforce consistency and to reflect organizational choices; do not present them as if they were validated for a given domain (e.g. “journalism standard”) unless you have done that validation yourself.
- When documenting or deploying a policy, state clearly that it reflects your (or your org’s) choices and that Chronicle does not certify that it meets any external standard.
- For domain-specific assurance, policy would need to be validated against domain requirements outside Chronicle; Chronicle only applies whatever policy is configured.


---
**← [Critical areas index](README.md)**