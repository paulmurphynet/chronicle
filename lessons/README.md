# Chronicle lessons

Step-by-step annotated lessons that walk through **100% of the Chronicle codebase**. Designed for new and junior engineers: each lesson references real source code in this repo so you can read the code as you go.

## How to use these lessons

1. **Work in order.** Lessons build on each other. Start with [Lesson 00: How to use these lessons](00-how-to-use-these-lessons.md), then follow the numbered sequence.
2. **Open the code.** Every lesson points to real files and (where useful) line ranges. Open those files in your editor and read along.
3. **Run the code when possible.** Many lessons suggest commands to run (e.g. the scorer, the verifier). Run them so the behavior is concrete.
4. **Take the quiz.** After each lesson, do the matching quiz in [quizzes/](quizzes/). Quizzes check understanding and point you back to the code if something was missed.

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

The full path from 00 to 11 covers the codebase: map, scorer, verifier, events, store/session, defensibility, integrations/scripts, CLI (including quickstart-rag), epistemic tools, export/import/Neo4j, and interop/API/tests.

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
- **.chronicle** — Our portable format (ZIP) for an investigation: manifest, schema, evidence, claims.
- **Eval contract** — Input (query, answer, evidence) and output (defensibility metrics) for the scorer; see [docs/eval_contract.md](../docs/eval_contract.md).
- **Event-sourced** — All changes are stored as events; we don’t overwrite history.
- **quickstart-rag** — CLI command `chronicle quickstart-rag`: one-command RAG flow; see [docs/rag-in-5-minutes.md](../docs/rag-in-5-minutes.md).

For more, see [Epistemology scope](../docs/epistemology-scope.md), the [Technical report](../docs/technical-report.md), and [Verification guarantees](../docs/verification-guarantees.md).

## For maintainers

- Add new lessons in number order; update this README and the learning path table.
- Keep **Key files** and code references accurate when refactoring.
- Each lesson should have a corresponding quiz in `lessons/quizzes/` (e.g. `quiz-01-codebase-map.md`).
