# Quizzes

Quizzes for the [Chronicle lessons](../README.md). Do the quiz for a lesson **after** reading that lesson and (when suggested) running the code.

## How quizzes work

- Each quiz is a Markdown file: `quiz-NN-topic.md`.
- Questions can be short-answer, multiple choice, or “where in the code…”.
- Answers are provided in an **Answer key** section at the bottom of each quiz (or in a separate `quiz-NN-topic-answers.md` if you prefer to test without spoilers).
- If you get something wrong, re-read the relevant part of the lesson and the referenced code.

## Index

| Quiz | Lesson | Topic |
|------|--------|--------|
| [quiz-01-codebase-map.md](quiz-01-codebase-map.md) | 01 | Codebase map |
| [quiz-02-the-scorer.md](quiz-02-the-scorer.md) | 02 | The standalone defensibility scorer |
| [quiz-03-the-verifier.md](quiz-03-the-verifier.md) | 03 | The .chronicle verifier |
| *…* | … | … |

*(Add a row when you add a new quiz.)*

## For maintainers

- Add one quiz per lesson; name it `quiz-NN-topic.md`.
- Keep questions aligned with lesson objectives and key files.
- Prefer questions that require opening the code (e.g. “In `standalone_defensibility_scorer.py`, what happens if `evidence` is not a list?”).
