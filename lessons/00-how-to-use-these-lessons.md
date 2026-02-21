# Lesson 00: How to use these lessons

Objectives: You’ll know how to navigate the lesson system, what to do before and after each lesson, and where to find the quizzes.

Key files: This file; [lessons/README.md](README.md).

---

## Why these lessons exist

Chronicle is a codebase with a clear purpose: defensibility scoring for RAG and evals. The lessons take you through every important part of the repo so that, by the end, you understand how it all fits together—not just one script or one module.

## How each lesson is structured

1. **Objectives** — What you should understand after reading and trying the lesson.
2. **Key files** — Real paths in this repo. Open them and read along.
3. **Walkthrough** — Explanation that points to specific code (files and, when useful, line numbers).
4. **Try it** — Commands or small tasks to run so the ideas become concrete.
5. **Summary** — Short recap.
6. **Quiz** — A link to the quiz in `lessons/quizzes/`. Do the quiz before moving on.

## How to study effectively

- One lesson at a time. Don’t skip; later lessons assume you’ve seen the earlier ones.
- Open the code. When a lesson says “see `chronicle/store/session.py`,” open that file and look at the relevant section.
- Run commands. When a lesson says “run the scorer” or “run the verifier,” do it. Use the same inputs as in the examples.
- Take the quiz. If you get something wrong, re-read that part of the lesson and the code it references.
- Use checkpoints. After every 2-3 lessons, run `make check` so your understanding is tied to the current working system.

## Where the quizzes live

All quizzes are in the [quizzes](quizzes/) subfolder. Naming:

- Lesson 01 → [quizzes/quiz-01-codebase-map.md](quizzes/quiz-01-codebase-map.md)
- Lesson 02 → `quiz-02-the-scorer.md`
- and so on.

Each quiz has questions (and, in the same file or a separate key, answers) so you can check your understanding.

## What “100% of the codebase” means

We don’t mean every single line. We mean every important area: the scorer, the verifier, the event model, the store, the session API, defensibility computation, integrations, API/MCP surfaces, and the main scripts. After the full lesson set, you’ll have seen and understood the role of each major part.

## Next step

Go to [Lesson 01: Codebase map](01-codebase-map.md). It gives you a map of the whole repo so you know where everything lives.

After Lesson 01, you can follow track recommendations in [lessons/README.md](README.md) (fast onboarding, integrator path, or trust/release path).

---

Summary: Use the lessons in order, open the key files, run the suggested commands, and take each quiz. Start with Lesson 01.

Quiz: N/A (this is the meta-lesson).

Next →: [Lesson 01: Codebase map](01-codebase-map.md) | Index: [Lessons](README.md)
