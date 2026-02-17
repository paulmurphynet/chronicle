# Critical area 04: Evidence–claim linking — how it works and its limits

**Risk:** Assuming that a **support** link means the evidence *actually* supports the claim (e.g. logically or empirically)—or that we have validated that. We record *that* a link exists; we do not model *why* it supports or verify that it does.

---

## Narrative

Defensibility depends on **support** and **challenge** links: evidence spans linked to claims. The score uses counts (support_count, challenge_count) and, when available, strength. So the system behaves as if “more support links” and “no challenge links” improve defensibility.

But we **do not**:

- Model **why** a span supports a claim (no warrant, no inference rule, no argument schema).
- Run **entailment or NLI** (natural language inference) to check that the evidence actually supports or contradicts the claim.
- Validate that the person or system that created the link was correct.

In the **standalone scorer**, we automatically link each evidence chunk as **support** for the single claim (the answer). That’s a structural default for the eval case—not a judgment that each chunk actually supports the answer. So:

- **Support** in Chronicle = “a link of type support was recorded.” It does **not** mean “we have verified that this evidence supports this claim.”
- **Challenge** = “a link of type challenge was recorded.” Same caveat.

Over-relying on link counts as if they reflected validated support/entailment is an epistemic risk. The score can look “strong” (e.g. two supports, two sources) even when the evidence doesn’t actually support the claim, if no one has added challenge links or checked the relationship.

---

## Technical

- **Where links are used for defensibility:** `chronicle/store/commands/claims.py`, `get_defensibility_score()`. It calls `get_support_for_claim_including_inherited()` and `get_challenges_for_claim_including_inherited()` and uses counts (and optional strength). No NLI or entailment check.
- **Standalone scorer:** `scripts/standalone_defensibility_scorer.py` ingests evidence, proposes the answer as one claim, then links **each** evidence chunk as support. So by construction, every chunk is treated as supporting the claim for scoring purposes. That’s a convention for the eval contract, not a guarantee that each chunk actually supports the answer.
- **Epistemology scope:** `docs/epistemology-scope.md` states we record *that* a span supports a claim (and optional strength) but we do **not** model *why* (warrant, inference rule, or argument schema).

---

## What to remember

- **Support/challenge = recorded link type, not validated entailment.** Use link counts as structural signals; do not treat them as proof that evidence actually supports or challenges the claim.
- In the scorer path, “all evidence chunks linked as support” is a **default for evals**, not a semantic guarantee. For higher assurance, evidence–claim relationships would need to be curated or validated (e.g. by humans or by a separate NLI step) and then recorded; Chronicle would still only record the links, not perform that validation itself.
- When explaining defensibility, clarify: “Support and challenge are recorded relationships; we do not verify that the evidence actually supports or contradicts the claim.”
