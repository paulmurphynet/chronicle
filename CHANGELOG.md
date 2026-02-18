# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) for the public API and eval contract.

---

## [0.1.0] — initial release

- **Standalone defensibility scorer** — `scripts/standalone_defensibility_scorer.py`: (query, answer, evidence) in, defensibility JSON out. Implements the [eval contract](docs/eval_contract.md).
- **chronicle-verify** — CLI to verify a .chronicle (ZIP) manifest, schema, and evidence hashes. Stdlib only.
- **Chronicle package** — Event store, read model, defensibility computation, session API. Optional HTTP API (`.[api]`), Neo4j sync (`.[neo4j]`).
- **Integrations** — LangChain, LlamaIndex, Haystack (optional callbacks/components).
- **Docs** — Eval contract, verifier, technical report, guidebook, critical areas, lessons 00–11, troubleshooting, errors.

[0.1.0]: https://github.com/chronicle-standard/chronicle-standard/releases/tag/v0.1.0
