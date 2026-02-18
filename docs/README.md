# Chronicle documentation

This folder and the repo hold all documentation. **On GitHub:** use the links below; each section has an index (README) and **Previous | Index | Next** links at the bottom of each document so you can move without returning here.

---

## Where to start

| Resource | Purpose |
|----------|---------|
| [**Story**](../story/README.md) | The Chronicle story: mission, vision, the problem, why it exists, how we're solving it, challenges, how you can help. Read in order (01 → 05). |
| [**Lessons**](../lessons/README.md) | Step-by-step codebase walkthrough for developers. Numbered 00–11; each lesson has **← Previous \| Index \| Next →** at the bottom. |
| [**Critical areas**](../critical_areas/README.md) | What defensibility and verification do *not* guarantee. Read before relying on scores or "verified." Each doc links back to the index and to the next. |
| [**Getting started**](getting-started.md) | One page: install, scorer + verifier quick start, next steps. |

**User manual:** A single user manual (how-to and reference) is planned under `manual/`. Until then, topic-based reference lives in the files listed below and in the main [README Docs section](../README.md#docs).

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

---

## Topic-based reference

For the full list of docs by topic (API, Neo4j, file format, RAG evals, provenance, errors, and more), see the main repo [README — Docs](../README.md#docs). This README is the **documentation index** so that on GitHub you can open `docs/` and see where everything lives.

---

## Viewing on GitHub

- **Story:** Start at [story/README.md](../story/README.md); use the chapter table. Each chapter has **← Previous \| Index \| Next →** at the bottom.
- **Lessons:** Start at [lessons/README.md](../lessons/README.md); use the learning path table. Each lesson has **← Previous \| Index \| Next →** and a **Quiz** link.
- **Critical areas:** Start at [critical_areas/README.md](../critical_areas/README.md); use the document table. Each document has **← Index** and **Next →** at the bottom.
- **Deep links:** You can link to any doc, e.g. `docs/verifier.md`, `story/03-how-we-are-solving-it.md`, or `lessons/02-the-scorer.md`. Use anchor links for sections, e.g. `eval_contract.md#2-output`.
