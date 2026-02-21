# Chronicle error types

This doc describes the error hierarchy in `chronicle/core/errors.py` and how the CLI and API map them to exit codes and HTTP status. Use it when adding validation or capacity checks so user-facing failures are consistent.

## Hierarchy

| Class | Use when |
|-------|----------|
| ChronicleError | Base for all Chronicle errors. Don’t raise it directly. |
| ChronicleUserError | User-fixable conditions: validation (empty title, invalid type, missing entity), policy rules (e.g. “policy disallows SEF when all evidence is AI-generated”), or “not found” for a referenced entity. Not a bug in the code. |
| ChronicleProjectNotFoundError | The project path does not contain a Chronicle project (e.g. no `chronicle.db`). Subclass of ChronicleUserError so it can be mapped to 404 by the API. |
| ChronicleIdempotencyCapacityError | The idempotency-key event cap is reached (env `CHRONICLE_MAX_IDEMPOTENCY_KEY_EVENTS`). API should return 429 Too Many Requests. |

## When to use which

- Validation or “not found” in commands/session → Raise ChronicleUserError (or ChronicleProjectNotFoundError only for “not a Chronicle project”).
- Idempotency cap reached → Raise ChronicleIdempotencyCapacityError.
- Bugs, programming errors, unexpected failures → Raise a standard exception (e.g. ValueError, KeyError) or a custom non-user error; the CLI will not catch them and the process may exit with a traceback (or pytest will see them).

Avoid raising bare ValueError or FileNotFoundError for user-fixable conditions; use ChronicleUserError (or ChronicleProjectNotFoundError) so the CLI and API can treat them uniformly.

## CLI mapping

The CLI (`chronicle/cli/main.py`) catches user errors via `_USER_ERRORS`:

- ChronicleUserError (and its subclasses, including ChronicleProjectNotFoundError)
- ValueError, FileNotFoundError, OSError, sqlite3.Error (for compatibility with code that still raises these)

On catch: the CLI prints `Error: <message>` to stderr and exits with code 1. It does not print a traceback.

Any other exception propagates (e.g. for pytest or debug).

## API mapping

The optional HTTP API (`chronicle/api/app.py`) usually checks conditions before calling the session and raises fastapi.HTTPException (404, 400, etc.) directly. If you add API endpoints that call session or commands and do not pre-check:

- ChronicleProjectNotFoundError → map to 404 Not Found (e.g. “Project not found”).
- ChronicleUserError (validation, “investigation not found”, “claim not found”, etc.) → map to 400 Bad Request with `detail=str(e)`, or 404 if the message indicates a missing resource.
- ChronicleIdempotencyCapacityError → map to 429 Too Many Requests.
- Oversize request payloads (evidence ingest or `.chronicle` import) → map to 413 Payload Too Large.

API responses also include a request correlation id:

- Header: `X-Request-Id`
- Error JSON: `{ "detail": ..., "request_id": "..." }`

Clients can pass `X-Request-Id` on request to preserve their own trace id across logs and responses.

## See also

- [Troubleshooting](troubleshooting.md) — common user-facing errors and fixes.
- `chronicle/core/errors.py` — the definitions.
