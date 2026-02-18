# Where challenges remain

We’ve made progress, but real challenges are still ahead. Being clear about them is part of our story.

---

## What we’re not

Chronicle does **not** certify truth, verify that sources are independent in the real world, or model deep epistemology (e.g. warrants, belief revision). The defensibility score and the verifier have precise, limited meanings. **Before you rely on scores or “verified” in production or research,** read the [critical areas](../critical_areas/README.md). They spell out what defensibility and verification do and don’t guarantee—so the system isn’t over-trusted. That’s the “handle with care” layer that keeps our story honest.

---

## Adoption and visibility

The defensibility **concept** and **contract** exist, but we’re still early. Getting adoption means: eval frameworks and labs actually **using** Chronicle defensibility as a metric, papers and benchmarks **citing** it, and tooling (dashboards, harnesses) **consuming** the score and the .chronicle format. Until that happens, we’re a promising approach, not yet a standard. So the main challenge is **getting into the loop**: evals, benchmarks, and docs that make defensibility easy to add and compare.

---

## Completeness and polish: where we stand

The **core is in place** and maintained as first-class: the standalone scorer, the verifier, the event model, the session API, the eval contract, and the .chronicle format. We’ve pruned scripts and docs so the repo is navigable, fixed doc links, added tests and CI so we can refactor safely, and documented clearly what’s first-class (scorer, verifier, contract, [RAG evals](../docs/rag-evals-defensibility-metric.md), [RAG in 5 minutes](../docs/rag-in-5-minutes.md), [verification guarantees](../docs/verification-guarantees.md), [implementer checklist](../docs/implementer-checklist.md)) and what’s optional (Neo4j, HTTP API, some scripts). **What’s left** is ongoing polish: clearer onboarding for new contributors, more examples or lessons where you hit friction, and tuning docs and UX as adoption grows. So the challenge here is less “finish the foundation” and more “keep it clear and welcoming as we grow.”

---

## Scope and limits

We’re explicit about what we **don’t** do (see [critical areas](../critical_areas/README.md) and [epistemology scope](../docs/epistemology-scope.md)). The remaining challenge is **communication**: making sure users and researchers see those limits up front, so they know what defensibility does and doesn’t guarantee and we don’t overclaim.

---

## Ecosystem and extensions

Longer term, the ecosystem could grow: hosted scorer APIs, UIs that consume .chronicle, vertical-specific policies, and tighter integration with popular eval frameworks. Each of those is a chunk of work and a design choice. The challenge is to grow in a way that keeps the **core** (contract, format, verifier) stable and understandable, so the ecosystem doesn’t fragment.

---

**Next:** [05 — How you can help](05-how-you-can-help.md)
