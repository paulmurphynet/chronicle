# Core test coverage

Coverage is measured over the **chronicle** package with certain paths omitted (API, Neo4j, integrations, optional tools). See `pyproject.toml` → `[tool.coverage.run]` for `omit`.

**Target:** 75% statement coverage for the included (core) code. We raise `fail_under` as coverage improves so CI keeps the bar meaningful.

**Current:** The suite focuses on session flow, standalone scorer, verifier, attestation, identity, and CLI actor. Additional tests for store commands, read model, and projection will raise the total toward 75%.

**Running coverage:**

```bash
pip install -e ".[dev]"
pytest tests/ --cov=chronicle --cov-report=term-missing
```

**Excluded from coverage:** `chronicle/api/*`, Neo4j sync/export, postgres store, embeddings, integrations. These are optional or integration-heavy; cover them with integration tests when needed.
