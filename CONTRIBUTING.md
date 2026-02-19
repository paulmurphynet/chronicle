# Contributing to Chronicle

Thanks for your interest in contributing. This file explains how to set up a dev environment, run checks, and where to get help.

## Project notes (style and CI)

1. **CI is disabled** until the maintainer turns it on. The workflow in [.github/workflows/ci.yml](.github/workflows/ci.yml) does not run on push or pull_request; it can be run manually via "Run workflow" if needed. Do not re-enable push/PR triggers until the maintainer requests it.
2. **Do not use section symbols** (e.g. §) in this project. Use section numbers instead (e.g. "Section 5", "Section 3.2").

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
- **Releases:** Tagged releases (e.g. `v0.1.0`) allow downstream users to pin a version.

**Release checklist** (when cutting a release):

1. [ ] Update [CHANGELOG.md](CHANGELOG.md) with a new `[X.Y.Z]` section and release date.
2. [ ] Bump version in `pyproject.toml` if desired (e.g. `version = "0.1.1"`).
3. [ ] Commit the changelog and version bump.
4. [ ] Create the tag: `git tag vX.Y.Z`.
5. [ ] Push the tag: `git push origin vX.Y.Z`.
6. [ ] (Optional) Publish to PyPI if the project is set up for it: `pip install build twine && python -m build && twine upload dist/*`.

## Code style and linting

- The project uses **ruff** for linting. Run `ruff check .` and `ruff format .` from the repo root (see `pyproject.toml` for config).
- Type hints are used; run `mypy chronicle` (see **Mypy** below).

## Mypy

- Run `mypy chronicle tools` from the repo root. Core code uses strict typing (`ignore_missing_imports = false` for `chronicle.*`). Optional modules (API, Neo4j, integrations) have overrides so mypy does not require their dependencies: `chronicle.api.*`, `chronicle.store.neo4j_*`, and `chronicle.integrations.*` use `ignore_missing_imports = true`. If you add code that imports optional packages (e.g. `fastapi`, `neo4j`), either add a mypy override for that module in `pyproject.toml` or install the optional extra (e.g. `pip install -e ".[api]"`) when running mypy.

## Tests

- Tests live under `tests/` (when present). Run with `pytest` from the repo root (e.g. `pytest tests/ -v`). Requires dev deps: `pip install -e ".[dev]"`.
- **Coverage:** Scorer, session (ingest → claim → link → defensibility), verifier, identity, attestation, and core store are covered. The same coverage threshold and omit list are used locally and in CI: `fail_under = 60` for the `chronicle` package (see `pyproject.toml` and [docs/coverage-core.md](docs/coverage-core.md)). To enforce locally: `pytest tests/ --cov=chronicle --cov-report=term-missing --cov-fail-under=60`.
- **CI:** Currently disabled (workflow runs only on manual trigger). When run, CI uses the same `--cov-fail-under=60`, uploads a coverage report artifact (htmlcov/, coverage.xml), and runs the doc link check (`scripts/check_doc_links.py`). See [.github/workflows/ci.yml](.github/workflows/ci.yml) and "Project notes" above.

## Documentation

- User-facing docs are in `docs/`, the [Story](story/README.md), and [Critical areas](critical_areas/README.md). Keep them accurate when you change behavior.
- Lessons in `lessons/` walk through the codebase; update "Key files" and code references when you refactor.

## Where to ask

- Open an issue or discussion in the repository for questions, bugs, or feature ideas.
- For security-sensitive issues, contact the maintainers directly (see repository description or README).

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT).
