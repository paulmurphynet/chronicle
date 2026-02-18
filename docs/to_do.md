# Implementation to-do

**Single source of truth for pending work.** All planned features, improvements, and deferred items live here. No separate implementation-plan, horizon, or onboarding checklist docs — one list, check off as you go.

**Doc updates** (guidebook, lessons, quizzes, critical areas) are done at the end after implementing new features, so docs stay in sync with the product.

---

## Current steps

1. **Verification: checkpointing or snapshots (scale)** — For very large projects: snapshot of read model at event N plus tail events to speed up replay or recovery; verification story becomes “verify snapshot integrity and tail events, or full replay.” Update [verification-guarantees](verification-guarantees.md) when added.

2. **Aura / Neo4j: deduplication by content hash** — Evidence and claims are not deduplicated across investigations (same text in two files → two nodes). Option: merge by content hash or keep separate for lineage. Document in [aura-graph-pipeline](aura-graph-pipeline.md) if implemented.

3. **Guidebook enhancement** — Expand the guidebook (narrative, problem, approach, limits) after more features (e.g. interoperability) are in place to avoid repeated rewrites.

4. **Technical report as preprint** — Publish the technical report (e.g. arXiv) so researchers can cite the defensibility definition and schema. External; not a code change.

5. **Tagged release** — When cutting a release: update CHANGELOG, tag (e.g. v0.1.0), and optionally publish to PyPI. Process is in [CONTRIBUTING](../CONTRIBUTING.md).

6. **Optional minimal API** — If useful: tiny “run scorer as a service” (POST JSON, get defensibility) or read-only API for .chronicle inspection. Can live in this repo or a separate one.

7. **Optional depth (warrant / rationale)** — If it clearly improves evals or adoption: optional “support rationale” or “warrant” field (why this evidence supports this claim), or tighter link to NLI/entailment evals. [Epistemology scope](epistemology-scope.md) sets boundaries.
