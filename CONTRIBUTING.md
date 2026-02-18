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
   For the optional HTTP API:
   ```bash
   pip install -e ".[api]"
   export CHRONICLE_PROJECT_PATH=/path/to/project
   uvicorn chronicle.api.app:app --reload
   ```
   See [docs/api.md](docs/api.md). For Neo4j-related work (sync, Aura pipeline):
   ```bash
   pip install -e ".[neo4j]"
   ```

4. **Run a quick smoke test** to confirm the scorer and verifier work:
   ```bash
   echo '{"query": "What was revenue?", "answer": "Revenue was $1.2M.", "evidence": ["The company reported revenue of $1.2M in Q1 2024."]}' \
     | PYTHONPATH=. python3 scripts/standalone_defensibility_scorer.py
   chronicle-verify path/to/any.chronicle   # or generate one with scripts/generate_sample_chronicle.py
   ```

## Errors (user-facing)

- User-fixable failures (validation, missing project, missing entity, policy rules) should raise **ChronicleUserError** or **ChronicleProjectNotFoundError** from `chronicle.core.errors`. The CLI catches these and exits 1 with a clean message; the API can map them to 400/404/429. See [docs/errors.md](docs/errors.md) for the full hierarchy, when to use which type, and how CLI/API map them.

## Changelog and releases

- **Changelog:** Meaningful user-facing changes (new features, contract changes, breaking changes) should be reflected in [CHANGELOG.md](CHANGELOG.md). Add a new `[X.Y.Z]` section with a short list of changes; link the version to the release tag when the release is cut.
- **Releases:** Tagged releases (e.g. `v0.1.0`) allow downstream users to pin a version. When cutting a release:
  1. Update [CHANGELOG.md](CHANGELOG.md) with a new `[X.Y.Z]` section and release date.
  2. Commit the changelog (and any version bumps), then create the tag: `git tag vX.Y.Z`.
  3. Push the tag: `git push origin vX.Y.Z`.
  4. (Optional) Publish to PyPI if the project is set up for it.

## Code style and linting

- The project uses **ruff** for linting. Run `ruff check .` and `ruff format .` from the repo root (see `pyproject.toml` for config).
- Type hints are used; run `mypy chronicle` (see **Mypy** below).

## Mypy

- Run `mypy chronicle tools` from the repo root. Core code uses strict typing (`ignore_missing_imports = false` for `chronicle.*`). Optional modules (API, Neo4j, integrations) have overrides so mypy does not require their dependencies: `chronicle.api.*`, `chronicle.store.neo4j_*`, and `chronicle.integrations.*` use `ignore_missing_imports = true`. If you add code that imports optional packages (e.g. `fastapi`, `neo4j`), either add a mypy override for that module in `pyproject.toml` or install the optional extra (e.g. `pip install -e ".[api]"`) when running mypy.

## Tests

- Tests live under `tests/` (when present). Run with `pytest` from the repo root (e.g. `pytest tests/ -v`). Requires dev deps: `pip install -e ".[dev]"`.
- Coverage: scorer (valid/invalid input), session (ingest → claim → link → defensibility), verifier (on a .chronicle export). The standalone scorer and verifier can also be used as integration smoke tests (see Development setup above).
- **CI:** GitHub Actions runs ruff (chronicle, tools) and pytest on push/PR. See [.github/workflows/ci.yml](.github/workflows/ci.yml).

## Documentation

- User-facing docs are in `docs/`, the [Guidebook](guidebook/README.md), and [Critical areas](critical_areas/README.md). Keep them accurate when you change behavior.
- Lessons in `lessons/` walk through the codebase; update "Key files" and code references when you refactor.

## Where to ask

- Open an issue or discussion in the repository for questions, bugs, or feature ideas.
- For security-sensitive issues, contact the maintainers directly (see repository description or README).

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT).
