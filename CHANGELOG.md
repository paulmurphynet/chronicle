# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) for the public API and eval contract.

---

## [0.2.0] — 2025-02-17

### Added

- **POST /score** — Optional API endpoint for scorer-as-a-service: same eval contract (query, answer, evidence) in, defensibility JSON out; no `CHRONICLE_PROJECT_PATH` required. See [docs/api.md](docs/api.md).
- **Scorer contract in package** — `chronicle.scorer_contract.run_scorer_contract()`: single entry point for (query, answer, evidence) → defensibility; used by the standalone script and by POST /score.
- **Optional rationale (warrant) on links** — Support and challenge links accept an optional `rationale` (why this evidence supports/challenges this claim). Session, API, reasoning brief, and Neo4j export include it; see [epistemology scope](docs/epistemology-scope.md).
- **Neo4j full deduplication** — With `--dedupe-evidence-by-content-hash` or `NEO4J_DEDUPE_EVIDENCE_BY_CONTENT_HASH=1`: one EvidenceItem per content hash, one Claim per hash(claim text); lineage via CONTAINS_EVIDENCE and CONTAINS_CLAIM. See [aura-graph-pipeline](docs/aura-graph-pipeline.md).
- **Replay from event or time** — `replay_read_model(store, up_to_event_id=...)` / `up_to_time=...` and CLI `chronicle replay --up-to-event` / `--up-to-time` for point-in-time read model.
- **Read model snapshot create/restore** — `chronicle.store.read_model_snapshot`: `create_read_model_snapshot`, `restore_from_snapshot`; CLI `chronicle snapshot create` / `chronicle snapshot restore`.
- **Claim–evidence–metrics export** — `build_claim_evidence_metrics_export()` in `chronicle.store.commands.generic_export` for fact-checking UIs and dashboards; see [claim-evidence-metrics-export](docs/claim-evidence-metrics-export.md).
- **Technical report citation** — [CITATION.cff](CITATION.cff) and citation section in [technical report Section 5](docs/technical-report.md#5-citation); README links to citation.

### Changed

- **Guidebook** — Expanded with interoperability at a glance (POST /score, .chronicle interchange, optional rationale, Neo4j deduplication), limits (rationale vs full warrants, optional graph deduplication), and how-to-help (POST /score, Neo4j dedupe).
- **Standalone scorer** — Refactored to use `chronicle.scorer_contract.run_scorer_contract()`; URL fetch and evidence normalization live in the package.

### Fixed

- **external-ids.md** — Removed stale reference to multi-key claim metadata in to_do; clarified “not yet supported.”

---

## [0.1.0] — initial release

- **Standalone defensibility scorer** — `scripts/standalone_defensibility_scorer.py`: (query, answer, evidence) in, defensibility JSON out. Implements the [eval contract](docs/eval_contract.md).
- **chronicle-verify** — CLI to verify a .chronicle (ZIP) manifest, schema, and evidence hashes. Stdlib only.
- **Chronicle package** — Event store, read model, defensibility computation, session API. Optional HTTP API (`.[api]`), Neo4j sync (`.[neo4j]`).
- **Integrations** — LangChain, LlamaIndex, Haystack (optional callbacks/components).
- **Docs** — Eval contract, verifier, technical report, guidebook, critical areas, lessons 00–11, troubleshooting, errors.

[0.2.0]: https://github.com/chronicle-standard/chronicle-standard/releases/tag/v0.2.0
[0.1.0]: https://github.com/chronicle-standard/chronicle-standard/releases/tag/v0.1.0
