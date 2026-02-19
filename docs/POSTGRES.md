# PostgreSQL backend (optional, read model on hold)

Chronicle supports an optional **PostgreSQL event store** for appending and reading events. Install with `pip install -e ".[postgres]"` and set `CHRONICLE_EVENT_STORE=postgres` plus connection env vars (see `.env.example`).

**Read model:** A PostgreSQL-backed read model is **not implemented** and is **on hold by design**. The Postgres event store can persist events, but projectors and queries (claims, defensibility, tensions, etc.) use the **SQLite** read model. To use Chronicle with Postgres for events only, point `CHRONICLE_PROJECT_PATH` at a directory that contains (or will contain) the SQLite project DB for the read model; the event store can be configured separately for Postgres if desired in a custom setup.

For the canonical to-do and on-hold items, see [to_do](to_do.md#on-hold-by-design).
