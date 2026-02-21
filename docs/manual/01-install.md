# Chapter 01: Install

Contents: Prerequisites, core install, optional API and Neo4j.

---

## Prerequisites

- **Python 3.11+**
- A virtual environment is recommended (e.g. `python3 -m venv .venv` then `source .venv/bin/activate` on Linux/macOS).

---

## Core install

From the repo root:

```bash
pip install -e .
```

This installs the `chronicle` and `chronicle-verify` commands. You can then run the [scorer](02-scorer.md) and [verifier](03-verifier.md). Verify the install with `chronicle-verify --help` or a quick scorer run (see [Scorer](02-scorer.md)).

---

## Optional: HTTP API

For the minimal HTTP API (write/read/export, POST /score):

```bash
pip install -e ".[api]"
export CHRONICLE_PROJECT_PATH=/path/to/project
uvicorn chronicle.api.app:app
```

See [API](../api.md).

---

## Optional: Neo4j

For graph sync (Neo4j / Aura):

```bash
pip install -e ".[neo4j]"
```

See [Neo4j](../neo4j.md) and [Aura graph pipeline](../aura-graph-pipeline.md).

---

**← Previous:** — (start) | Index: [Manual](README.md) | Next →: [02 — Scorer](02-scorer.md)
