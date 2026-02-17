# Contributing to Chronicle

Thanks for your interest in contributing. This file explains how to set up a dev environment, run checks, and where to get help.

## Development setup

1. **Clone the repo** and enter the directory.

2. **Create and activate a virtual environment** (Python 3.11+):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # Linux/macOS
   # or: .venv\Scripts\activate  on Windows
   ```

3. **Install the project in editable mode:**
   ```bash
   pip install -e .
   ```
   For Neo4j-related work (sync, Aura pipeline):
   ```bash
   pip install -e ".[neo4j]"
   ```

4. **Run a quick smoke test** to confirm the scorer and verifier work:
   ```bash
   echo '{"query": "What was revenue?", "answer": "Revenue was $1.2M.", "evidence": ["The company reported revenue of $1.2M in Q1 2024."]}' \
     | PYTHONPATH=. python3 scripts/standalone_defensibility_scorer.py
   chronicle-verify path/to/any.chronicle   # or generate one with scripts/generate_sample_chronicle.py
   ```

## Code style and linting

- The project uses **ruff** for linting. Run `ruff check .` and `ruff format .` from the repo root (see `pyproject.toml` for config).
- Type hints are used; run `mypy chronicle` if mypy is configured.

## Tests

- Tests live under `tests/` (when present). Run with `pytest` from the repo root.
- The standalone scorer and verifier can be used as integration smoke tests (see Development setup above).

## Documentation

- User-facing docs are in `docs/`, the [Guidebook](guidebook/README.md), and [Critical areas](critical_areas/README.md). Keep them accurate when you change behavior.
- Lessons in `lessons/` walk through the codebase; update "Key files" and code references when you refactor.

## Where to ask

- Open an issue or discussion in the repository for questions, bugs, or feature ideas.
- For security-sensitive issues, contact the maintainers directly (see repository description or README).

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT).
