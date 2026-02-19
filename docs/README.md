# Chronicle documentation

This folder and the repo hold all documentation. **On GitHub:** use the links below; each section has an index (README) and **Previous | Index | Next** links at the bottom of each document so you can move without returning here.

---

## Where to start

| Resource | Purpose |
|----------|---------|
| [**North star**](north-star.md) | **Where we're headed:** Chronicle's long-term direction—shared infrastructure, one model from early draft to auditable package, ecosystem. Use it to guide roadmap and scope. |
| [**Core vs reference architecture**](architecture-core-reference.md) | Boundary between trust-critical core and replaceable reference surfaces (API/CLI/UI/integrations). |
| [**Story**](../story/README.md) | The Chronicle story: mission, vision, the problem, why it exists, how we're solving it, challenges, how you can help. Read in order (01 → 06). |
| [**Lessons**](../lessons/README.md) | Step-by-step codebase walkthrough for developers. Numbered 00–12; each lesson has **← Previous \| Index \| Next →** (or End of lessons) at the bottom. Lesson 12 fully covers the .chronicle file format and data schema. |
| [**Critical areas**](../critical_areas/README.md) | What defensibility and verification do *not* guarantee. Read before relying on scores or "verified." Each doc links back to the index and to the next. |
| [**Getting started**](getting-started.md) | One page: install, scorer + verifier quick start, next steps. |
| [**Integration quick reference**](integration-quick-reference.md) | One page: score one run, verify .chronicle, add to harness, optional API/adapters. |

**User manual:** A short manual (how-to and reference) lives under [manual/](manual/README.md) with chapter stubs. Topic-based reference also lives in the files listed below and in the main [README Docs section](../README.md#docs).

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
| [Policy profiles](policy-profiles/README.md) | Example JSON profiles (journalism, legal, compliance) for verticals. |
| [Identity providers](identity-providers.md) | Configured IdP (none, traditional, gov_id, did, zk); how to implement custom IdP adapters. |
| [Supply-chain automation](security-automation.md) | Manual dependency scan workflow (`pip-audit`, `npm audit`) and threshold gating guidance. |
| [Architecture decisions (ADRs)](adr/README.md) | Durable architecture decisions and rationale (core/reference, SQLite-first posture, etc.). |
| [North star](north-star.md) | Long-term direction: shared infrastructure, one model from early draft to auditable package, ecosystem; what stays in scope and what doesn't. |

---

## Topic-based reference

For the full list of docs by topic (API, Neo4j, file format, RAG evals, provenance, errors, and more), see the main repo [README — Docs](../README.md#docs). This README is the **documentation index** so that on GitHub you can open `docs/` and see where everything lives.

---

## Viewing on GitHub

- **Story:** Start at [story/README.md](../story/README.md); use the chapter table. Each chapter has **← Previous \| Index \| Next →** at the bottom.
- **Lessons:** Start at [lessons/README.md](../lessons/README.md); use the learning path table. Each lesson has **← Previous \| Index \| Next →** and a **Quiz** link.
- **Lessons / quizzes:** Each quiz has **← Previous \| Index \| Next →** at the bottom (or End of quizzes for quiz-12).
- **Critical areas:** Start at [critical_areas/README.md](../critical_areas/README.md); use the document table. Each document has **← Index** and **Next →** at the bottom.
- **Deep links:** You can link to any doc, e.g. `docs/verifier.md`, `story/03-how-we-are-solving-it.md`, or `lessons/02-the-scorer.md`. Use anchor links for sections, e.g. `eval_contract.md#2-output`.
