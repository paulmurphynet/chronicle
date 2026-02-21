# Structured logging

Chronicle now emits structured runtime logs for API request/response and unhandled exceptions.

Goals:

- JSON-safe fields (no unserializable payload crashes)
- Standard level names (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`)
- RFC 5424-aligned severity numbers in output (`severity` field)
- Configurable transports (stderr/stdout/file)

## Default behavior

By default, Chronicle configures the `chronicle` logger as:

- format: JSON
- transport: stderr
- level: INFO

Example event shape:

```json
{
  "timestamp": "2026-02-21T05:00:00+00:00",
  "logger": "chronicle.api",
  "level": "INFO",
  "severity": 6,
  "message": "request_completed",
  "event": "request_completed",
  "fields": {
    "request_id": "1d6e...",
    "method": "GET",
    "path": "/health",
    "status_code": 200,
    "duration_ms": 4.17
  }
}
```

## Environment configuration

Use these env vars to change runtime behavior:

- `CHRONICLE_LOG_LEVEL`:
  - Values: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
  - Default: `INFO`
- `CHRONICLE_LOG_FORMAT`:
  - Values: `json`, `text`
  - Default: `json`
- `CHRONICLE_LOG_TRANSPORTS`:
  - Comma-separated transports: `stderr`, `stdout`, `file`
  - Default: `stderr`
  - Example: `CHRONICLE_LOG_TRANSPORTS=stderr,file`
- `CHRONICLE_LOG_FILE`:
  - Required only when `file` transport is enabled
  - Example: `/var/log/chronicle/api.log`

## RFC 5424 severity mapping

Chronicle includes a numeric `severity` value aligned to RFC 5424 for the common Python levels:

- `DEBUG` -> `7`
- `INFO` -> `6`
- `WARNING` -> `4`
- `ERROR` -> `3`
- `CRITICAL` -> `2`

## Notes

- Chronicle logs are line-delimited JSON in `json` mode (one object per line).
- Complex fields are converted to JSON-safe values (dates, paths, bytes, containers, object payloads).
- API logs include request IDs (`X-Request-Id`) so errors can be traced across services.
