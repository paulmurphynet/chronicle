# Quizzes

Quizzes for the [Chronicle lessons](../README.md). Do the quiz for a lesson after reading that lesson and (when suggested) running the code.

## How quizzes work

- Each quiz is a Markdown file: `quiz-NN-topic.md`.
- Questions can be short-answer, multiple choice, or “where in the code…”.
- Answers are provided in an Answer key section at the bottom of each quiz (or in a separate `quiz-NN-topic-answers.md` if you prefer to test without spoilers).
- If you get something wrong, re-read the relevant part of the lesson and the referenced code.

## Self-grading rubric

Use this quick rubric after each quiz:

- 90-100%: You can explain behavior and find the implementation quickly.
- 70-89%: You understand the flow but should re-open one or two key files.
- Below 70%: Re-read the lesson and run its “Try it” steps before continuing.

For stronger retention, answer first in your own notes, then compare with the key.

Mastery mode (recommended for maintainers/integrators):

- Answer every question with a file path and, when possible, the function or command name that proves your answer.
- Re-run one command from the lesson and include one observed output fact.
- If you miss a question, re-open code first, then update your answer from evidence.

## Cumulative review cadence

- After quizzes 04, 08, and 11, do a 10-minute cumulative review of prior wrong answers.
- After quiz 14, run a full-system pass: answer one question per lesson from memory, then verify each answer in code.

## Index

| Quiz | Lesson | Topic |
|------|--------|--------|
| [quiz-01-codebase-map.md](quiz-01-codebase-map.md) | 01 | Codebase map |
| [quiz-02-the-scorer.md](quiz-02-the-scorer.md) | 02 | The standalone defensibility scorer |
| [quiz-03-the-verifier.md](quiz-03-the-verifier.md) | 03 | The .chronicle verifier |
| [quiz-04-events-and-core.md](quiz-04-events-and-core.md) | 04 | Events and core |
| [quiz-05-store-and-session.md](quiz-05-store-and-session.md) | 05 | Store and session |
| [quiz-06-defensibility-metrics.md](quiz-06-defensibility-metrics.md) | 06 | Defensibility metrics |
| [quiz-07-integrations-and-scripts.md](quiz-07-integrations-and-scripts.md) | 07 | Integrations and scripts |
| [quiz-08-cli.md](quiz-08-cli.md) | 08 | The Chronicle CLI |
| [quiz-09-epistemic-tools.md](quiz-09-epistemic-tools.md) | 09 | Epistemic tools |
| [quiz-10-export-import-neo4j.md](quiz-10-export-import-neo4j.md) | 10 | Export, import, Neo4j |
| [quiz-11-interoperability-api-and-tests.md](quiz-11-interoperability-api-and-tests.md) | 11 | Interoperability, API, and tests |
| [quiz-12-chronicle-file-format-and-schema.md](quiz-12-chronicle-file-format-and-schema.md) | 12 | The .chronicle file format and data schema |
| [quiz-13-release-readiness-security-and-standards.md](quiz-13-release-readiness-security-and-standards.md) | 13 | Release readiness, security gates, and standards operations |
| [quiz-14-mcp-agent-integration.md](quiz-14-mcp-agent-integration.md) | 14 | MCP agent integration |

## For maintainers

- Add one quiz per lesson; name it `quiz-NN-topic.md`.
- Keep questions aligned with lesson objectives and key files.
- Prefer questions that require opening the code (e.g. “In `standalone_defensibility_scorer.py`, what happens if `evidence` is not a list?”).
