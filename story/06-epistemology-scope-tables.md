# Epistemology: what we implement and what we don’t

This chapter is the **canonical reference** for Chronicle’s epistemic scope. Two tables spell out: (1) what we implement—and why it fits our purposes—and (2) what we do *not* implement—and why we don’t. They align with [Epistemology scope](../docs/epistemology-scope.md) and with the [thought experiment](../thought_experiments/01-epistemologists-conference-review.md) in which four epistemologists reviewed the project. All items in the first table are implemented; the [to-do list](../docs/to_do.md) tracks completed epistemology-optimal items (e.g. defeater_kind, reliability_notes, epistemic_stance, policy_rationale).

---

## What Chronicle implements (and why)

Epistemic options and features we implement (or will implement), and the reason each is in scope for RAG evals, show-your-work, and policy-driven scoring.

| Feature / option | What we implement | Why (for our purposes) |
|------------------|-------------------|-------------------------|
| **Evidence** | First-class immutable evidence items and spans; content-hashed; links reference spans. | Enables “this sentence supports this claim”; integrity via hash; verifiable in .chronicle. |
| **Claims** | Falsifiable statements; proposed, linked, asserted or withdrawn; never stored as “true.” | Keeps defensibility structural; avoids truth claims; fits evals and audits. |
| **Support and challenge** | First-class link types span→claim; optional strength; retractions as events. | Core of defensibility: what supports or challenges a claim is explicit and auditable. |
| **Corroboration** | support_count, challenge_count, independent_sources_count from links and sources. | Policy can require min sources; matches testimonial intuition (multiple independent backings). |
| **Sources** | Register source; link evidence to source; independence_notes (user-supplied). | Models real-world origins for corroboration; independence “as modeled,” documented. |
| **Tensions** | First-class tensions between claims (conflict/weakening); status open/acknowledged/resolved; optional resolution rationale. | Contradictions explicit; defensibility reflects open vs resolved; defeasibility without full belief revision. |
| **Defensibility** | Structural, policy-relative scorecard (provenance_quality, corroboration, contradiction_status, weakest_link, etc.). | Single summary for “how well does this claim hold up?” for evals and dashboards; not truth. |
| **Temporal** | known_as_of; as-of defensibility queries; full event history. | Reproducibility; “defensibility at T”; audit trail. |
| **Attribution and trail** | Who asserted; optional confidence; reasoning trail (events that built/modified the claim). | Accountability; agent-centred interpretation; audit. |
| **Link rationale / warrant** | Optional rationale (or warrant) on support/challenge links—first-class and stable. | “Why this evidence supports this claim” for justification-sensitive workflows; as asserted, not verified. |
| **Defeater type** | Optional defeater_kind (e.g. rebutting vs undercutting) on challenge links and tensions; we record, we don't verify. | Richer explanation of why defensibility changed; aligns with formal epistemology; optional. |
| **Source reliability metadata** | Optional reliability_notes on sources (user-supplied); we record, we don't verify. | Distinguish strong vs weak sources in structure; we record, we don’t verify. |
| **Policy rationale** | Optional policy_rationale on policy profiles; we record, we don't validate. | Evaluators can assess whether the bar is appropriate; applied epistemology. |
| **Epistemic stance** | Optional epistemic_stance on claims (e.g. working hypothesis vs asserted). | Domains that need “we believe but don’t claim to know” without a full theory of knowledge. |
| **Verifier and .chronicle** | Standalone verifier (structure, schema, evidence hashes); portable format. | “Show your work” is checkable by anyone; no overclaim (verified = well-formed, not true). |
| **Explicit limits** | Critical areas; epistemology-scope; verification-guarantees. | Prevents over-trust; defensibility ≠ truth; independence/support “as modeled,” not verified. |

---

## What we do not implement (and why not)

Epistemic concepts or theories that exist in the literature or in practice but that Chronicle does *not* attempt to implement, and the reason they are out of scope for our purposes.

| Area of epistemology | What we do not implement | Why not (for our purposes) |
|----------------------|---------------------------|----------------------------|
| **Truth and factuality** | We do not assert that any claim is true or false. | Our job is structural defensibility and verifiable “show your work,” not access to the world or fact-checking. Truth is a different question; asserting it would require semantics and verification we don’t have and don’t promise. |
| **Full Toulmin / argument schemas** | We do not model full argument structure (claim, data, warrant, backing, qualifier) or argument schemas. | We support optional warrant/rationale on links; full Toulmin would complicate the schema and the UI for limited gain in RAG evals and portable verification. Operational defensibility doesn’t require it. |
| **Formal belief revision (e.g. AGM)** | We do not implement AGM-style revision or priority orderings over evidence/sources. | Retractions and tensions give a practical form of revision; full AGM would require a commitment to a specific revision policy and ordering. Out of scope for a portable, policy-agnostic eval and verification tool. |
| **Fine-grained knowledge vs belief** | We do not model “known” vs “believed” vs “accepted” in a fine-grained epistemic sense. | We allow optional epistemic stance (e.g. working hypothesis vs asserted); we do not commit to a theory of knowledge or justification. That keeps the system usable across domains without philosophical baggage. |
| **Justification theory** | We do not commit to foundationalism, coherentism, or reliabilism. | Defensibility is structural and policy-driven (counts, thresholds, tensions). Picking a justification theory would constrain use cases and would not add value for RAG evals and show-your-work. |
| **Defeater semantics** | We do not *compute* or validate defeater correctness (rebutting vs undercutting). We may *record* defeater type optionally. | We record structure; we don’t verify that a link is correctly classified as rebutting or undercutting. Implementing semantics would require a formal model of content we don’t have. |
| **Source independence (verified)** | We do not verify that two sources are actually independent in the real world. | We record independence as modeled by the user; verification would require external knowledge and would break our “record, don’t verify” boundary. |
| **Source reliability (computed)** | We do not compute or verify a general “reliability” or “authority” score. | We may record user-supplied reliability metadata; we do not validate it. Computing reliability would require a theory of evidence and authority we don’t adopt. |
| **Entailment / NLI** | We do not run natural-language inference or entailment checks to validate that evidence supports or challenges a claim. | We record links; validating entailment would be a separate service and would blur the line between “structure” and “content correctness.” Critical area 04 states this clearly. |
| **Verifier: semantics or truth** | The verifier does not check event semantics, referential consistency, truth of claims, or independence. | Verification is structural and integrity-only (ZIP, manifest, schema, hashes). Semantic or factual verification would be a different product and would require definitions we don’t impose. |
| **Actor identity (verified)** | We do not verify that actor_id or verification_level correspond to real identities or credentials. | We record who the writer says acted; identity binding is a deployment concern. Documented in critical area 06. |
| **Policy validity** | We do not validate that thresholds or policy rules are empirically or scientifically grounded for a domain. | Policy is configurable; we allow optional rationale so evaluators can assess it. We don’t certify that a policy is “correct” for a given domain. |
| **Documented epistemology (literature)** | The technical report and docs define defensibility operationally; we do not frame the design in philosophical epistemology terms or cite epistemic literature. | The project is operationally epistemic—focused on RAG evals, show-your-work, and verification—not a contribution to philosophical epistemology. The thought experiment and this chapter are the exception for reflection. |

---

**← Previous:** [05 — How you can help](05-how-you-can-help.md) | **Index:** [Story](README.md) | **End of story**
