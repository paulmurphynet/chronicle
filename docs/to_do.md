# Implementation to-do

**Single source of truth for pending work.** All planned features, improvements, and deferred items live here. No separate implementation-plan, horizon, or onboarding checklist docs — one list, check off as you go.

**Doc updates (guidebook, lessons, quizzes, critical areas, and other documentation) are done at the end** after implementing the new features below, so docs stay in sync with the product.

## How to use this file

1. **When starting a set of changes** — Pick items from "Current steps" (or add new ones). Use `- [ ]` for open and `- [x]` for done.
2. **While working** — Mark items done as you complete them. Leave completed items in the list until the batch is finished.
3. **When a batch is finished** — Update user-facing docs (README, eval_contract, verifier, etc.) as needed. Then either leave the list as-is for the next batch or empty "Current steps" to "— none —" and add the next batch.
4. **Doc pass at the end** — After implementing features, update guidebook, lessons, quizzes, critical areas, and any other docs that need to reflect the new behavior or narrative.

---

## Current steps

### Implementation and features

- [x] **Claim–evidence–metrics export helper** — Add a single API/helper (e.g. `build_claim_evidence_metrics_export`) that returns the stable JSON shape for one claim + evidence refs + defensibility, so callers don’t assemble from `build_generic_export_json` + read model + scorecards by hand. See [claim-evidence-metrics-export](claim-evidence-metrics-export.md) for the shape.

- [x] **Multi-key claim metadata** — If needed: add `metadata_json` (or equivalent) to claims so multiple external keys per claim are supported; document in [external-ids](external-ids.md). Until then, a single note or tag is enough for one external ID.

- [ ] **Verification: replay-from-N or time-range replay** — Optional extension for project verification: formal replay from event N or time-range replay. Document in [verification-guarantees](verification-guarantees.md) if added.

- [ ] **Verification: checkpointing or snapshots (scale)** — For very large projects: snapshot of read model at event N plus tail events to speed up replay or recovery; verification story becomes “verify snapshot integrity and tail events, or full replay.” Update [verification-guarantees](verification-guarantees.md) when added.

- [ ] **Aura / Neo4j: deduplication by content hash** — Evidence and claims are not deduplicated across investigations (same text in two files → two nodes). Option: merge by content hash or keep separate for lineage. Document in [aura-graph-pipeline](aura-graph-pipeline.md) if implemented.

- [x] **Ollama tests: pytest marker** — Add a marker (e.g. `@pytest.mark.ollama`) for tests that require Ollama; skip when env is unset or Ollama unreachable so CI stays fast and local runs can exercise the full stack. See [testing-with-ollama](testing-with-ollama.md).

- [x] **Prune scripts (ai_validation, verticals)** — If ai_validation or verticals assume the old API or full UI and have no remaining dependents, archive or remove them and document in [scripts/README](../scripts/README.md). Otherwise leave as optional/advanced.

- [ ] **Guidebook enhancement** — Expand the guidebook (narrative, problem, approach, limits) after more features (e.g. interoperability) are in place to avoid repeated rewrites.

- [ ] **Technical report as preprint** — Publish the technical report (e.g. arXiv) so researchers can cite the defensibility definition and schema. External; not a code change.

- [ ] **Tagged release** — When cutting a release: update CHANGELOG, tag (e.g. v0.1.0), and optionally publish to PyPI. Process is in [CONTRIBUTING](../CONTRIBUTING.md).

- [ ] **Optional minimal API** — If useful: tiny “run scorer as a service” (POST JSON, get defensibility) or read-only API for .chronicle inspection. Can live in this repo or a separate one.

- [ ] **Optional depth (warrant / rationale)** — If it clearly improves evals or adoption: optional “support rationale” or “warrant” field (why this evidence supports this claim), or tighter link to NLI/entailment evals. [Epistemology scope](epistemology-scope.md) sets boundaries.

- [x] **Eval-harness integration (RAGAS, Trulens, LangSmith)** — Document or provide a thin adapter so Chronicle defensibility can be added as a metric in popular frameworks. Goal: “add defensibility to your RAG eval in one step.” (Doc and adapter template already in [integrating-with-chronicle](integrating-with-chronicle.md); further framework-specific adapters as needed.)

- [x] **.chronicle as interchange positioning** — Clarify in docs/README that the .chronicle format is “show your work”: anyone can export and others can verify; encourage tooling that consumes .chronicle.

### Doc updates (after features)

- [x] **Update guidebook, lessons, quizzes, critical areas** — After implementing the new features above, update the guidebook, lessons (and quizzes), and critical areas so they reflect current behavior and narrative. No separate “plan” docs; keep to_do as the single list.

- [x] **Update ONBOARDING checklist** — In [ONBOARDING_AND_OPEN_SOURCE](ONBOARDING_AND_OPEN_SOURCE.md), mark completed items (e.g. README “New here?”, CONTRIBUTING, troubleshooting, glossary, getting-started, changelog, personas, example .chronicle) so the checklist matches reality, or retire the doc and keep only to_do.
