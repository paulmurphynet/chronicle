# ADR 0001: Core/Reference boundary is a release contract

- Status: accepted
- Date: 2026-02-19
- Related: `docs/architecture-core-reference.md`, `docs/to_do.md`

## Context

Chronicle's trust model depends on stable core behavior (event store, read model, verifier, defensibility contract) while CLI/API/frontend adapters can evolve faster. Mixing these concerns raises release risk and increases regression surface for contributors.

## Decision

Treat the following as release-critical core contracts:

- `.chronicle` export/import and verifier behavior
- event-store append/replay and read-model consistency
- defensibility scorer contract and API response shape

Treat CLI, API, and frontend as reference adapters that may iterate as long as they preserve these core contracts.

## Consequences

- Refactors prioritize isolating adapter code from core invariants.
- Contract and parity tests remain required for release readiness.
- Contributors can add new adapter features without modifying core trust primitives.

## Alternatives considered

- Single-layer architecture with no explicit contract boundary.
  - Rejected due to higher coupling and weaker release confidence.
