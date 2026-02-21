# Chronicle documentation

This folder and the repo hold all documentation. On GitHub: use the links below; each section has an index (README) and Previous | Index | Next links at the bottom of each document so you can move without returning here.

---

## Where to start

| Resource | Purpose |
|----------|---------|
| [North star](north-star.md) | Where we're headed: Chronicle's long-term direction—shared infrastructure, one model from early draft to auditable package, ecosystem. Use it to guide roadmap and scope. |
| [30/60/90 roadmap](roadmap-30-60-90.md) | Concrete near-term execution plan tied to trust outcomes and release readiness. |
| [Core vs reference architecture](architecture-core-reference.md) | Boundary between trust-critical core and replaceable reference surfaces (API/CLI/UI/integrations). |
| [Story](../story/README.md) | The Chronicle story: mission, vision, the problem, why it exists, how we're solving it, challenges, how you can help. Read in order (01 → 06). |
| [Lessons](../lessons/README.md) | Step-by-step codebase walkthrough for developers. Numbered 00–12; each lesson has ← Previous \| Index \| Next → (or End of lessons) at the bottom. Lesson 12 fully covers the .chronicle file format and data schema. |
| [Critical areas](../critical_areas/README.md) | What defensibility and verification do *not* guarantee. Read before relying on scores or "verified." Each doc links back to the index and to the next. |
| [Getting started](getting-started.md) | One page: install, scorer + verifier quick start, next steps. |
| [Integration quick reference](integration-quick-reference.md) | One page: score one run, verify .chronicle, add to harness, optional API/adapters. |

User manual: A short manual (how-to and reference) lives under [manual/](manual/README.md) with chapter stubs. Topic-based reference also lives in the files listed below and in the main [README Docs section](../README.md#docs).

---

## Key reference (quick links)

| Doc | Purpose |
|-----|---------|
| [Eval contract](eval_contract.md) | Scorer input/output; how to plug into eval harnesses. |
| [Verifier](verifier.md) | How to verify a .chronicle file (CLI and web). |
| [Verification guarantees](verification-guarantees.md) | What the verifier does and does not guarantee. |
| [Technical report](technical-report.md) | Defensibility definition and schema (citable). |
| [Glossary](glossary.md) | Terms: defensibility, claim, evidence, .chronicle, etc. |
| [Troubleshooting](troubleshooting.md) | Common issues and fixes. |
| [To-do](to_do.md) | Implementation to-do list (single source of truth for pending work). |
| [Reference UI plan](reference-ui-plan.md) | Same-repo strategy for the human-in-the-loop frontend; what to bring from V1 (tiers, Propose–Confirm, Reading-lite). |
| [Core vs reference architecture](architecture-core-reference.md) | How the project is modularized into trust-critical core and adapter/reference layers. |
| [Quickstart](quickstart.md) | First investigation in ~15 min (API or CLI). |
| [Quickstart: Reference UI](quickstart-reference-ui.md) | Try sample, highlight to link, see defensibility update (Reference UI). |
| [Zero to submission](zero-to-submission.md) | One path to a verifiable submission package in ~30 min. |
| [Reasoning brief](reasoning-brief.md) | Primary shareable artifact per claim; when to use vs .chronicle. |
| [When to use Chronicle](when-to-use-chronicle.md) | Scope vs data lineage / ML provenance. |
| [Reference workflows](reference-workflows.md) | Reproducible end-to-end workflow set (journalism, legal, history/research, compliance, benchmark trust tracking). |
| [Integration acceptance checklist](integration-acceptance-checklist.md) | Release gate for adapters/connectors: contract, safety, reproducibility, and docs minimum. |
| [MCP integration](mcp.md) | Chronicle MCP server for AI assistant tool-calling over stdio/HTTP transports. |
| [Starter packs](starter-packs.md) | Opinionated bootstrap packs (journalism, legal, audit) with policy defaults and defensibility-ready report/export artifacts. |
| [API ingestion pipeline example](api-ingestion-pipeline-example.md) | End-to-end batch input to API writes, defensibility readout, and `.chronicle` export artifact. |
| [Integration export hardening](integration-export-hardening.md) | Contract baseline for JSON/CSV/Markdown and signed `.chronicle` bundle interoperability paths with harnessed tests. |
| [Standards profile](standards-profile.md) | Chronicle interoperability profile across JSON-LD/PROV, C2PA, VC/Data Integrity, RO-Crate, and ClaimReview. |
| [Standards JSON-LD export](standards-jsonld-export.md) | JSON-LD + PROV-oriented investigation export profile (S-02 baseline). |
| [ClaimReview export](claimreview-export.md) | schema.org ClaimReview profile generated from Chronicle claim defensibility. |
| [RO-Crate export](ro-crate-export.md) | RO-Crate profile for Chronicle investigation package interoperability. |
| [C2PA compatibility export](c2pa-compatibility-export.md) | C2PA metadata compatibility export with explicit verification-mode semantics. |
| [VC/Data Integrity export](vc-data-integrity-export.md) | VC/Data Integrity compatibility export for claim/artifact/checkpoint attestations. |
| [Adjacent standards guidance](adjacent-standards-guidance.md) | Integration boundaries for OpenLineage, in-toto, and SLSA as complementary layers. |
| [Whitepaper plan](whitepaper-plan.md) | Process and quality gates for publication and standards-body engagement. |
| [Whitepaper draft](whitepaper-draft.md) | Working standards-facing whitepaper draft for iterative review. |
| [Whitepaper evidence pack](whitepaper-evidence-pack.md) | Reproducible artifact bundle (benchmark, workflow, standards exports, verifier report). |
| [Whitepaper citation metadata](whitepaper-citation.md) | Citation format and versioned publication metadata for whitepaper revisions. |
| [Whitepaper internal review log](whitepaper-internal-review-log.md) | Accepted/rejected technical edits captured per whitepaper revision. |
| [Standards submission package](standards-submission-package.md) | Submission bundle checklist and outreach notes for standards/community review. |
| [External standards review cycle tracker](external-standards-review-cycle.md) | Send log, feedback schema, and execution state for external standards review rounds. |
| [Policy profiles](policy-profiles/README.md) | Example JSON profiles (journalism, legal, compliance, history/research) for verticals. |
| [Role-based review checklists](role-based-review-checklists.md) | Role templates for journalism/legal/compliance/history review decisions using review packets and policy compatibility. |
| [Identity providers](identity-providers.md) | Configured IdP (none, traditional, gov_id, did, zk); how to implement custom IdP adapters. |
| [Neo4j](neo4j.md) | Optional graph projection and contract check command for sync/export/rebuild parity. |
| [Neo4j operations runbook](neo4j-operations-runbook.md) | Backup/restore, sync cadence, drift response, and capacity/cost guardrails for Neo4j projection operations. |
| [Neo4j query pack](neo4j-query-pack.md) | Production query set (tensions, support/challenge balance, lineage) plus indexing guidance. |
| [Neo4j projection baseline v0.9.0](benchmarks/neo4j_projection_baseline_v0.9.0.md) | Reproducible benchmark artifact with thresholded export performance and memory results. |
| [Neo4j projection sync baseline v0.9.0](benchmarks/neo4j_projection_sync_baseline_v0.9.0.md) | Large-run sync benchmark evidence against a live Neo4j instance, including thresholded sync metrics. |
| [PostgreSQL backend](POSTGRES.md) | Convergence quickstart for local/managed Postgres, doctor/smoke checks, and current backend scope. |
| [Support policy](support-policy.md) | Support tiers plus GA/Beta/Experimental status, compatibility policy, and deprecation timeline format. |
| [Production readiness checklist](production-readiness-checklist.md) | Objective pass/fail release criteria across trust, backend, CI, security, and docs. |
| [v0.9 public launch runbook](v0.9-public-launch.md) | Exact execution path for making the repo public, enabling Actions, enforcing branch protection, and producing rollout evidence. |
| [CI branch protection checklist](ci-branch-protection.md) | Exact required checks to configure in branch protection rules. |
| [Branch protection rollout verification](branch-protection-rollout-verification.md) | Scripted verification/evidence workflow for branch-protection and required CI checks. |
| [Post-public finalization checklist](post-public-finalization-checklist.md) | One pass to close post-public CI/branch-protection/Neo4j-live/standards-dispatch gating items. |
| [Postgres operations runbook](postgres-operations-runbook.md) | Backup, restore, and disaster-recovery runbook for Postgres-backed Chronicle deployments. |
| [Managed Postgres hardening](postgres-hardening.md) | TLS, least privilege, credential rotation, and network hardening for managed Postgres. |
| [Backend migration/versioning policy](backend-migration-versioning-policy.md) | Versioning/migration policy for event and read-model schemas across SQLite and Postgres. |
| [Supply-chain automation](security-automation.md) | Manual dependency scan workflow (`pip-audit`, `npm audit`) and threshold gating guidance. |
| [Trust metrics](trust-metrics.md) | KPI definitions and scripts for tracking unsupported-claim reduction over time. |
| [Structured logging](structured-logging.md) | JSON-safe logging contract, RFC 5424 severity mapping, and transport config for API/runtime logs. |
| [Notebook examples](../notebooks/README.md) | Jupyter walkthroughs for scorer and session workflows (tutorial artifacts, not a separate UI surface). |
| [Rejected feature decisions](rejected-feature-decisions.md) | Explicit log of intentionally rejected feature directions with rationale and tradeoffs. |
| [Adversarial and failure-mode examples](adversarial-failure-modes.md) | Concrete safe-failure/uncertainty-disclosure scenarios and expected Chronicle behavior. |
| [Lizzie Borden case study](case-study-lizzie-borden.md) | Why we use the inquest transcript as a trust benchmark and how to evaluate responsibly without sensational framing. |
| [Architecture decisions (ADRs)](adr/README.md) | Durable architecture decisions and rationale (core/reference, SQLite-first posture, etc.). |
| [North star](north-star.md) | Long-term direction: shared infrastructure, one model from early draft to auditable package, ecosystem; what stays in scope and what doesn't. |

---

## Topic-based reference

For the full list of docs by topic (API, Neo4j, file format, RAG evals, provenance, errors, and more), see the main repo [README — Docs](../README.md#docs). This README is the documentation index so that on GitHub you can open `docs/` and see where everything lives.

---

## Viewing on GitHub

- Story: Start at [story/README.md](../story/README.md); use the chapter table. Each chapter has ← Previous \| Index \| Next → at the bottom.
- Lessons: Start at [lessons/README.md](../lessons/README.md); use the learning path table. Each lesson has ← Previous \| Index \| Next → and a Quiz link.
- Lessons / quizzes: Each quiz has ← Previous \| Index \| Next → at the bottom (or End of quizzes for quiz-12).
- Critical areas: Start at [critical_areas/README.md](../critical_areas/README.md); use the document table. Each document has ← Index and Next → at the bottom.
- Deep links: You can link to any doc, e.g. `docs/verifier.md`, `story/03-how-we-are-solving-it.md`, or `lessons/02-the-scorer.md`. Use anchor links for sections, e.g. `eval_contract.md#2-output`.
