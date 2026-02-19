# ADR 0002: SQLite-first baseline; Postgres remains optional roadmap

- Status: accepted
- Date: 2026-02-19
- Related: `docs/POSTGRES.md`, `docs/to_do.md`

## Context

The project prioritizes an easy, local-first path for adopters and contributors. SQLite provides a zero-setup default and already backs the full read model and core flows. Postgres support exists for event-store scenarios but not as a complete read-model deployment.

## Decision

Release posture remains SQLite-first:

- SQLite is the default and fully supported baseline.
- Postgres event-store support is optional and explicitly partial.
- Postgres read-model parity is tracked as roadmap work, not release-blocking work.

## Consequences

- Documentation and onboarding stay simple for solo and small-team adoption.
- Reliability and correctness work focuses on one complete backend path.
- Future Postgres work must include clear support-scope language and parity tests before being promoted to baseline.

## Alternatives considered

- Make Postgres a pre-release requirement.
  - Rejected due to higher setup friction and slower quality iteration for the current contributor model.
