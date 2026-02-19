# How fully does Chronicle cover epistemology?

Chronicle is described as an "epistemic layer" and implements a **defensibility** model over claims, evidence, and tensions. This doc states what we cover, what we do not, and where the boundaries are.

---

## What we cover (and how)

| Area | Coverage |
|------|----------|
| **Evidence** | First-class: immutable evidence items and spans; content-hashed; support/challenge links reference **spans** so "this sentence supports this claim" is explicit. |
| **Claims** | Treated as **falsifiable statements**; never stored as "true"; proposed, linked to evidence, asserted or withdrawn; optional **epistemic_stance** (e.g. working_hypothesis | asserted_established); optional decomposition (compound into atomic sub-claims). |
| **Support and challenge** | First-class link types (support / challenge) from evidence span to claim; optional strength; optional **rationale** (warrant) per link—*why* this evidence supports/challenges this claim (as asserted, not verified); retractions recorded as events. Optional **defeater_kind** (rebutting | undercutting) on challenge links. |
| **Corroboration** | Derived from links: support_count, challenge_count, **independent_sources_count** (distinct sources backing the claim via supporting evidence). Policy can require a minimum number of independent sources (e.g. for "System-Established Fact"). |
| **Sources** | Real-world origins of evidence: register source, link evidence to source, record **independence_notes** (user-supplied; "not independently verified" is stated in UI and docs) and optional **reliability_notes** (user-supplied; we record, we do not verify). Used for corroboration and policy (e.g. min sources with independence rationale). |
| **Contradiction / tension** | Explicit **tensions** between two claims (conflict or weakening); status: open, acknowledged, resolved; resolution can include rationale. Optional **defeater_kind** (rebutting | undercutting) on tensions. Tensions are first-class; defensibility reflects open vs resolved. |
| **Defensibility** | **Structural and policy-relative**: how well the claim holds up given recorded evidence, links, tensions, and policy rules. **Not** a truth value. Scorecard: provenance_quality, corroboration, contradiction_status, weakest_link, optional knowability. Policy profiles may include optional **policy_rationale** (why thresholds were chosen); we record, we do not validate. |
| **Temporal** | Optional known_as_of ("when could we first defend this claim?"); as-of queries for defensibility at a point in time; full event history (event-sourced). |
| **Attribution and trail** | Who asserted the claim; optional confidence; **reasoning trail** (ordered events that built or modified the claim). |
| **Explicit limits** | Docs and UI state: defensibility does not assert truth; sources are "as modeled by the user"; independence is "not independently verified"; verifier does not check truth or source independence. |

So we cover: **evidence–claim linkage**, **support/challenge/corroboration**, **source modeling and independence notes**, **contradiction (tensions)**, **structural defensibility**, **temporal and attribution posture**, and **clear disclaimers** that we are not certifying truth or real-world source independence.

---

## What we do not cover (or only lightly)

| Area | Gap or limit |
|------|--------------|
| **Justification / warrant** | We support an optional **rationale** (warrant) on each support/challenge link: short text for *why* this evidence supports or challenges this claim (e.g. for NLI/entailment evals). We **record** it; we do **not** verify that the rationale is correct. We do not model full Toulmin backing or argument schemas. |
| **Belief revision** | Retractions and tensions give a form of revision. We do not implement formal belief-revision semantics (e.g. AGM) or priority orderings over evidence. |
| **Knowledge vs belief** | We allow optional **epistemic_stance** on claims (e.g. working_hypothesis vs asserted_established). We do not model "known" vs "believed" vs "accepted" in a fine-grained epistemic sense or commit to a theory of knowledge. |
| **Defeater types** | We **record** optional **defeater_kind** (rebutting | undercutting) on challenge links and tensions. When supplied, we **validate** that the value is one of `rebutting` or `undercutting`; we do **not** compute or validate that a link is correctly classified (defeater semantics are not implemented). |
| **Epistemic justification theory** | No commitment to foundationalism, coherentism, or reliabilism. The model is structural and policy-driven (counts, thresholds, open tensions). |
| **Source reliability / authority** | We allow optional **reliability_notes** on sources (user-supplied). We **record** them; we do **not** verify or compute a general "reliability" or "authority" score. `get_source_reliability` returns evidence/claim counts only. |
| **Documented epistemology** | The technical report and eval docs define defensibility and schema operationally. They do not frame the design in philosophical epistemology terms or cite epistemic literature. |

---

## Summary

We cover **evidence, claims, support/challenge (with optional link rationale and defeater_kind), sources (with independence_notes and optional reliability_notes), tensions (with optional defeater_kind), optional epistemic_stance on claims, optional policy_rationale on policy profiles, and a structural defensibility score** with clear boundaries: defensibility is not truth; source independence and reliability are as modeled, not verified; rationale, defeater_kind, and policy_rationale are **recorded, not verified**. We do **not** cover full Toulmin warrants/argument schemas, formal belief revision, fine-grained knowledge/belief, or justification theory. The project is **operationally epistemic** (good for RAG evals, show-your-work, and policy-driven scoring) rather than a full epistemological framework.

For the precise defensibility definition and schema, see [Technical report](technical-report.md) and [Defensibility metrics schema](defensibility-metrics-schema.md).
