# Core test coverage

Coverage is measured over the **chronicle** package with certain paths omitted (API, Neo4j, integrations, optional tools). See `pyproject.toml` → `[tool.coverage.run]` for `omit`.

**Target:** 75% statement coverage for the included (core) code. We raise `fail_under` as coverage improves so CI keeps the bar meaningful.

**Current:** `fail_under` is set to 33%. CI runs `pytest tests/ ... --cov-fail-under=33` so the build fails if coverage drops below that. We raise the value as the test suite grows (target 75%). The suite focuses on session flow (including multi-evidence and eval-contract metrics), standalone scorer, verifier, attestation, identity, and CLI actor.

**Running coverage:**

```bash
pip install -e ".[dev]"
pytest tests/ --cov=chronicle --cov-report=term-missing
```

To enforce the same minimum locally:

```bash
pytest tests/ --cov=chronicle --cov-report=term-missing --cov-fail-under=33
```

## What is omitted and why

The following paths are excluded from coverage so that the **core** defensibility path (event store, read model, session, commands, scorer, verifier) is what we measure. Optional or integration-heavy code is omitted; cover it with integration or optional test runs when needed.

| Omitted path | Reason |
|--------------|--------|
| `chronicle/__init__.py` | Package init only. |
| `*/tests/*` | Test code. |
| `chronicle/api/*` | Optional HTTP API; separate deployment. |
| `chronicle/store/neo4j_sync.py`, `chronicle/store/neo4j_export.py` | Optional Neo4j; requires Neo4j. |
| `chronicle/core/encryption.py` | Optional encryption. |
| `chronicle/store/postgres_event_store.py` | Optional Postgres backend. |
| `chronicle/tools/embeddings.py`, `chronicle/tools/embedding_config.py` | Optional embedding tools. |
| `chronicle/integrations/*` | LangChain, LlamaIndex, Haystack; optional and framework-specific. |

Included in coverage: `chronicle/core` (except encryption), `chronicle/store` (except api, neo4j, postgres), `chronicle/eval_metrics.py`, `chronicle/verify.py`, CLI, and the rest of the package used by the session and scorer.
