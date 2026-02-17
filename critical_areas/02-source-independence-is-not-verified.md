# Critical area 02: Source independence is not verified

**Risk:** Assuming that “N independent sources” in the score means N sources that are **actually independent** in the real world (different organizations, no shared bias, etc.). We do **not** verify that.

---

## Narrative

The defensibility scorecard includes **independent_sources_count**: the number of *distinct sources* (as modeled in Chronicle) that back the claim via supporting evidence. Policy can require a minimum number of independent sources (e.g. for “System-Established Fact”). So the **number** affects whether a claim is rated strong or weak.

But **independence** in Chronicle is **as modeled by the user**. You register sources; you link evidence to sources; you can add **independence_notes** (e.g. “not independently verified”). We **do not** check that two sources are actually independent in reality—different entities, no common control, no shared incentive to align. We only count distinct source UIDs that are linked to supporting evidence. So:

- **independent_sources_count = 2** means: “Two different source entities in our model are linked to evidence that supports this claim.” It does **not** mean “Two independently verified, truly independent sources in the real world.”

Over-relying on this number as a guarantee of real-world independence is a serious epistemic risk, especially in high-stakes domains (journalism, legal, compliance).

---

## Technical

- **Where the count comes from:** `chronicle/store/commands/claims.py`, in `get_defensibility_score()`. We collect `source_uids` from support links (via evidence spans and `list_evidence_source_links`); `independent_sources_count = len(source_uids)`. So it’s “count of distinct source UIDs attached to supporting evidence”—no check of independence in fact.
- **Schema and docs:** `docs/defensibility-metrics-schema.md` states: `independent_sources_count` is “Count of distinct sources (as linked by the user) backing support; **not independently verified**.” `docs/epistemology-scope.md` states that sources are “as modeled by the user” and independence is “not independently verified.”
- **Risk signal:** When there are 2+ distinct sources but none have independence rationale, we add a risk signal `sources_without_independence_rationale` (see `claims.py` around the “Phase 6 (source-independence)” block). That warns consumers but still does not verify independence.

---

## What to remember

- **Independent_sources_count = distinct source UIDs in the model, not “verified independent in reality.”** Use it as a structural indicator; do not treat it as a guarantee of real-world independence.
- **Independence_notes** are user-supplied. They improve transparency but are not validated by us.
- When presenting the metric, clarify: “Independent sources count reflects the number of distinct sources in the model; independence in the real world is not verified by Chronicle.”
