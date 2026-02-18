# How fully does Chronicle cover epistemology?

Chronicle is described as an "epistemic layer" and implements a **defensibility** model over claims, evidence, and tensions. This doc states what we cover, what we do not, and where the boundaries are.

---

## What we cover (and how)

| Area | Coverage |
|------|----------|
| **Evidence** | First-class: immutable evidence items and spans; content-hashed; support/challenge links reference **spans** so "this sentence supports this claim" is explicit. |
| **Claims** | Treated as **falsifiable statements**; never stored as "true"; proposed, linked to evidence, asserted or withdrawn; optional decomposition (compound into atomic sub-claims). |
| **Support and challenge** | First-class link types (support / challenge) from evidence span to claim; optional strength; retractions recorded as events. |
| **Corroboration** | Derived from links: support_count, challenge_count, **independent_sources_count** (distinct sources backing the claim via supporting evidence). Policy can require a minimum number of independent sources (e.g. for "System-Established Fact"). |
| **Sources** | Real-world origins of evidence: register source, link evidence to source, record **independence_notes** (user-supplied; "not independently verified" is stated in UI and docs). Used for corroboration and policy (e.g. min sources with independence rationale). |
| **Contradiction / tension** | Explicit **tensions** between two claims (conflict or weakening); status: open, acknowledged, resolved; resolution can include rationale. Tensions are first-class; defensibility reflects open vs resolved. |
| **Defensibility** | **Structural and policy-relative**: how well the claim holds up given recorded evidence, links, tensions, and policy rules. **Not** a truth value. Scorecard: provenance_quality, corroboration, contradiction_status, weakest_link, optional knowability. |
| **Temporal** | Optional known_as_of ("when could we first defend this claim?"); as-of queries for defensibility at a point in time; full event history (event-sourced). |
| **Attribution and trail** | Who asserted the claim; optional confidence; **reasoning trail** (ordered events that built or modified the claim). |
| **Explicit limits** | Docs and UI state: defensibility does not assert truth; sources are "as modeled by the user"; independence is "not independently verified"; verifier does not check truth or source independence. |

So we cover: **evidence–claim linkage**, **support/challenge/corroboration**, **source modeling and independence notes**, **contradiction (tensions)**, **structural defensibility**, **temporal and attribution posture**, and **clear disclaimers** that we are not certifying truth or real-world source independence.

---

## What we do not cover (or only lightly)

| Area | Gap or limit |
|------|--------------|
| **Justification / warrant** | We record *that* a span supports a claim (and optional strength). We support an optional **rationale** (warrant) on each support/challenge link: short text for *why* this evidence supports or challenges this claim (e.g. for NLI/entailment evals). We do not model full Toulmin backing or argument schemas. |
| **Belief revision** | Retractions and tensions give a form of revision. We do not implement formal belief-revision semantics (e.g. AGM) or priority orderings over evidence. |
| **Knowledge vs belief** | Claim types (e.g. SEF, SAC, inference) and status (asserted/withdrawn) give a rough distinction. We do not model "known" vs "believed" vs "accepted" in a fine-grained epistemic sense. |
| **Defeater types** | Challenges and tensions make claims defeasible in practice. We do not distinguish rebutting vs undercutting defeaters in the schema or scorecard. |
| **Epistemic justification theory** | No commitment to foundationalism, coherentism, or reliabilism. The model is structural and policy-driven (counts, thresholds, open tensions). |
| **Source reliability / authority** | We have source registration and independence_notes; `get_source_reliability` exists (evidence count, claims supported, corroborated, in tension). We do not store or compute a general "reliability" or "authority" score; independence is user-recorded. |
| **Documented epistemology** | The technical report and eval docs define defensibility and schema operationally. They do not frame the design in philosophical epistemology terms or cite epistemic literature. |

---

## Summary

We cover **evidence, claims, support/challenge (with optional link rationale), sources (with independence notes), tensions, and a structural defensibility score** with clear boundaries: defensibility is not truth; source independence is as modeled, not verified. We do **not** cover full Toulmin warrants/argument schemas, formal belief revision, fine-grained knowledge/belief, defeater taxonomy, or justification theory. The project is **operationally epistemic** (good for RAG evals, show-your-work, and policy-driven scoring) rather than a full epistemological framework.

For the precise defensibility definition and schema, see [Technical report](technical-report.md) and [Defensibility metrics schema](defensibility-metrics-schema.md).
