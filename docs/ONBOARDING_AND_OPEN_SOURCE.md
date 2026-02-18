# Onboarding and open-source readiness

This doc is a checklist and plan for making Chronicle easy for newcomers (colleague handoff and public open source). Use it to prioritize work; items are ordered by impact for "know nothing" readers.

---

## High impact (do first)

### 1. **Single entry point: "Start here"**

- **README:** Add a **"New here?"** or **"First time?"** block at the top that says:
  - Prerequisites (Python 3.11+, optional venv).
  - One sentence: "Chronicle scores how well answers are supported by evidence; it’s for RAG evals and audits."
  - Two paths: **"I want to understand the project"** → Guidebook then Lessons. **"I want to run the scorer"** → Quick start.
- **Prerequisites section:** Explicit: Python 3.11+, `pip install -e .`, and "use a venv" so `chronicle` and `chronicle-verify` work. Mention that `chronicle` requires the venv (or `./.venv/bin/chronicle`) so "command not found" is avoided.

### 2. **CONTRIBUTING.md**

- scripts/README and common OSS expectations reference it; it’s missing.
- Include: how to set up dev environment (clone, venv, `pip install -e ".[dev]"` or `.[neo4j]` if needed), how to run tests (when they exist), how to run the verifier/scorer as a smoke test, code style (ruff), and where to ask (e.g. GitHub Discussions or a stated contact). Keeps colleague and future contributors from guessing.

### 3. **Troubleshooting / FAQ**

- Add a short **docs/troubleshooting.md** (or a section in README) for:
  - `chronicle: command not found` → activate venv or use `./.venv/bin/chronicle`.
  - `chronicle-verify: command not found` → same; or `PYTHONPATH=. python3 -m tools.verify_chronicle`.
  - `NEO4J_URI is not set` → .env or export for Neo4j sync.
  - Scorer input format (JSON with query, answer, evidence).
- Reduces support load and builds trust.

### 4. **Fix broken references**

- **scripts/README.md:** Replace link to `CONTRIBUTING.md` and `docs/README.md` with existing targets (e.g. README, docs in repo root, or CONTRIBUTING once added). Avoid 404s on first click.

### 5. **Glossary in one place**

- lessons/README has a good glossary; **docs/glossary.md** (or **README § Glossary**) gives "concepts first" readers a single place for: defensibility, claim, evidence, span, support/challenge, tension, .chronicle, eval contract, event-sourced. Link from README "New here?" so new people can decode jargon before diving into docs.

---

## Medium impact (before or soon after open source)

### 6. **Lessons 04–11** ✓

- The full learning path is in place: lessons 00–11 (and matching quizzes) exist under `lessons/`. 04 = events/core, 05 = store/session, 06 = defensibility, 07 = integrations/scripts; 08 = CLI, 09 = epistemic tools, 10 = export/import/Neo4j, 11 = interop/API/tests. No “coming soon” placeholder; readers can work through the full sequence.

### 7. **Doc grouping for newcomers**

- README’s doc table is long. Add a short **"Essential docs"** (eval contract, verifier, technical report, guidebook, critical areas) and **"More"** or **"By topic"** (Neo4j, Aura, Ollama, file format, epistemology, etc.) so new readers know what to read first vs later.

### 8. **One "Getting started" doc**

- **docs/getting-started.md:** One page: what Chronicle is, prerequisites, quick start (scorer + verifier), then "Next: read the [Guidebook](guidebook/README.md) or run through [Lessons](lessons/README.md)." Link from README so there’s a single detailed onboarding page.

### 9. **Critical areas up front**

- README (or getting-started) should say: "Before using scores or verification in production, read [Critical areas](critical_areas/README.md): they explain what defensibility and 'verified' do *not* guarantee." So newcomers don’t over-trust the system.

### 10. **Version and changelog**

- For open source: a **CHANGELOG.md** (or "Releases" in README) and clear version in pyproject.toml help users know what they’re looking at. Can start minimal (e.g. "0.1.0 – initial open source release").

---

## Lower priority (polish)

- **Code comments:** Ensure key modules (e.g. session, defensibility, verifier) have a short module docstring and that public APIs are clear for first-time readers.
- **Example .chronicle:** Document where to get a sample (e.g. `scripts/generate_sample_chronicle.py`) and link from verifier doc so "verify a file" has a ready example.
- **Personas in README:** Short bullets: "Researchers / evaluators" → eval contract, scorer, technical report; "Engineers integrating" → integrating-with-chronicle, session API; "Contributors" → CONTRIBUTING, lessons.

---

## Summary

| Priority | Action |
|----------|--------|
| High | README: "New here?", prerequisites, two paths (understand vs run). |
| High | Add CONTRIBUTING.md (setup, tests, style, where to ask). |
| High | Add troubleshooting (command not found, NEO4J_URI, scorer input). |
| High | Fix scripts/README links; add glossary (docs/glossary.md or README). |
| Medium | Done: lessons 04–11 exist; learning path complete. Group README docs (essential vs more). |
| Medium | Add getting-started.md; surface critical areas in README/getting-started. |
| Medium | Changelog/version note for open source. |

Doing the high-impact items first will make the repo much more welcoming for your colleague and for future open-source users.
