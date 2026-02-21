# Example policy profiles

Shareable policy profiles for different verticals. Each JSON file can be used as a project’s active policy (`policy.json`) or as a reference profile in `policy_profiles/`. The Chronicle core loads these via `PolicyProfile.from_dict()`; see [chronicle/core/policy.py](../../chronicle/core/policy.py).

Format: `format_version: 1` (see `POLICY_FORMAT_VERSION` in policy.py). Top-level keys include `profile_id`, `display_name`, `description`, `mes_rules`, `evidence_admissibility`, `tension_rules`, `checkpoint_rules`, `tier_overrides`. Other keys are preserved in `extensions` for round-trip.

---

## Profiles

| File | Vertical | Summary |
|------|----------|--------|
| journalism.json | Investigative journalism | Two-source rule, named sources preferred, tensions block publication. Matches the default profile in code. |
| legal.json | Legal / briefs | Stricter MES and admissibility; chain-of-custody and tension resolution required for checkpoints. |
| compliance.json | Compliance / audit | Evidence admissibility and exception workflow; checkpoint requires all tensions addressed. |
| history_research.json | History / research | Source-context-heavy profile for archival and interpretation-sensitive claims with visible uncertainty. |

---

## How to use

- Activate in a project: Copy a profile to your project as `policy.json`, or use the CLI/API to set the active policy.
- Reference UI / vendors: The Reference UI (or vertical UIs) can show “blocked” / “allowed” by tier and policy; use these JSONs as templates or load them by `profile_id`.
- Compare policies: Use `get_policy_compatibility(built_under, viewing_under)` in [policy_compat.py](../../chronicle/core/policy_compat.py) to diff two profiles.
- Use role checklists: Pair policy selection with [Role-based review checklists](../role-based-review-checklists.md) for journalism/legal/compliance/history review flows.

See [Reference UI plan](../reference-ui-plan.md) and [Human-in-the-loop and attestation](../human-in-the-loop-and-attestation.md) for how policy and tiers affect the UI.
