# Chronicle lessons

Step-by-step annotated lessons that walk through **every important area of the Chronicle codebase**. Designed for new and junior engineers: each lesson references real source code in this repo so you can read the code as you go.

## How to use these lessons

1. **Work in order.** Lessons build on each other. Start with [Lesson 00: How to use these lessons](00-how-to-use-these-lessons.md), then follow the numbered sequence.
2. **Open the code.** Every lesson points to real files and (where useful) line ranges. Open those files in your editor and read along.
3. **Run the code when possible.** Many lessons suggest commands to run (e.g. the scorer, the verifier). Run them so the behavior is concrete.
4. **Take the quiz.** After each lesson, do the matching quiz in [quizzes/](quizzes/). Quizzes check understanding and point you back to the code if something was missed.

**On GitHub:** Use the learning path table above. At the bottom of each lesson you'll see **← Previous | Index | Next →** so you can move without returning to this README.

## Learning path (lesson order)

| Lesson | Topic | Key area |
|--------|--------|----------|
| [00](00-how-to-use-these-lessons.md) | How to use these lessons | Meta |
| [01](01-codebase-map.md) | Codebase map: what lives where | Repo layout |
| [02](02-the-scorer.md) | The standalone defensibility scorer | `scripts/`, eval contract |
| [03](03-the-verifier.md) | The .chronicle verifier | `tools/verify_chronicle/` |
| [04](04-events-and-core.md) | Events and core types | `chronicle/core/` |
| [05](05-store-and-session.md) | Store, read model, and session API | `chronicle/store/` |
| [06](06-defensibility-metrics.md) | How defensibility is computed | `chronicle/eval_metrics.py`, store |
| [07](07-integrations-and-scripts.md) | Integrations and scripts | `chronicle/integrations/`, `scripts/` |
| [08](08-cli.md) | The Chronicle CLI (init, quickstart-rag, verify-chronicle, export, etc.) | `chronicle/cli/` |
| [09](09-epistemic-tools.md) | Epistemic tools (decomposer, contradiction, type inference) | `chronicle/tools/` |
| [10](10-export-import-neo4j.md) | Export, import, and Neo4j | `chronicle/store/export_import.py`, `neo4j_sync.py` |
| [11](11-interoperability-api-and-tests.md) | Interoperability, API, and tests | Terminology, external IDs, provenance, HTTP API, tests, CI |
| [12](12-chronicle-file-format-and-schema.md) | The .chronicle file format and data schema | ZIP layout, manifest, chronicle.db (events + read model), evidence/; full schema reference |

The full path from 00 to 12 covers the codebase: map, scorer, verifier, events, store/session, defensibility, integrations/scripts, CLI (including quickstart-rag and actor identity), epistemic tools, export/import/Neo4j, interop/API/tests, and the **complete .chronicle file format and data schema** (manifest, DB tables, evidence layout).

## Lesson format

Each lesson includes:

- **Objectives** — What you’ll understand by the end.
- **Key files** — Paths in this repo to open.
- **Walkthrough** — Annotated explanation with references to real code.
- **Try it** — Commands or small experiments to run.
- **Summary** — Short recap.
- **Quiz** — Link to the quiz in `lessons/quizzes/`.

## Glossary

Terms you’ll see across lessons (and in the code):

- **Defensibility** — How well a claim is supported by evidence and policy; we score it, we don’t assert “truth.”
- **Claim** — A falsifiable statement (e.g. the model’s answer); linked to evidence via support/challenge.
- **Evidence** — Immutable items (e.g. retrieved chunks); content-hashed; can have spans.
- **.chronicle** — Our portable format (ZIP) for an investigation: manifest, chronicle.db (events + read model), evidence files. Full layout and data schema: [Lesson 12](12-chronicle-file-format-and-schema.md).
- **Eval contract** — Input (query, answer, evidence) and output (defensibility metrics) for the scorer; see [docs/eval_contract.md](../docs/eval_contract.md).
- **Event-sourced** — All changes are stored as events; we don’t overwrite history.
- **quickstart-rag** — CLI command `chronicle quickstart-rag`: one-command RAG flow; see [docs/rag-in-5-minutes.md](../docs/rag-in-5-minutes.md).
- **Actor / attestation** — Every event records who did it (actor_id, actor_type); optional verification level can be stored. See [docs/human-in-the-loop-and-attestation.md](../docs/human-in-the-loop-and-attestation.md).

For more, see [Epistemology scope](../docs/epistemology-scope.md), the [Technical report](../docs/technical-report.md), and [Verification guarantees](../docs/verification-guarantees.md).

## For maintainers

- **Lessons must be kept up to date with all functionality of the app.** When you add or change features, update the relevant lesson(s) and this README. Include "Update lessons for X" in [To-do](../docs/to_do.md) when a change affects the walkthrough.
- Add new lessons in number order; update this README and the learning path table.
- Keep **Key files** and code references accurate when refactoring.
- Each lesson should have a corresponding quiz in `lessons/quizzes/` (e.g. `quiz-01-codebase-map.md`).
- Keep the **← Previous | Index | Next →** navigation at the bottom of each lesson correct when reordering or adding lessons.
