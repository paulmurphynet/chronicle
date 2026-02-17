# Where challenges remain

We’ve made progress, but real challenges are still ahead. Being clear about them is part of our story.

---

## Adoption and visibility

The defensibility **concept** and **contract** exist, but we’re still early. Getting adoption means: eval frameworks and labs actually **using** Chronicle defensibility as a metric, papers and benchmarks **citing** it, and tooling (dashboards, harnesses) **consuming** the score and the .chronicle format. Until that happens, we’re a promising approach, not yet a standard. So the main challenge is **getting into the loop**: evals, benchmarks, and docs that make defensibility easy to add and compare.

---

## Completeness and polish

Our core is in place: scorer, verifier, event model, session API. But we still have work to do: **pruning** scripts and docs so the repo is easy to navigate, **fixing** broken doc links, **adding** minimal tests and CI so we can refactor safely, and **documenting** clearly what’s first-class (scorer, verifier, contract) and what’s optional (Neo4j, some scripts). Until that’s done, onboarding and maintenance are harder than they need to be.

---

## Scope and limits

We’re explicit about what we **don’t** do: we don’t certify “truth,” we don’t verify that sources are independent in the real world, and we don’t model deep epistemology (e.g. warrants, belief revision). The challenge is to **communicate** those limits so that users and researchers know what defensibility does and doesn’t guarantee—and so we don’t overclaim.

---

## Ecosystem and extensions

Longer term, the ecosystem could grow: hosted scorer APIs, UIs that consume .chronicle, vertical-specific policies, and tighter integration with popular eval frameworks. Each of those is a chunk of work and a design choice. The challenge is to grow in a way that keeps the **core** (contract, format, verifier) stable and understandable, so the ecosystem doesn’t fragment.

---

**Next:** [05 — How you can help](05-how-you-can-help.md)
