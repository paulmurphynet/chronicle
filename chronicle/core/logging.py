"""Structured logging utilities for Chronicle runtime surfaces.

Features:
- JSON-safe serialization of log fields.
- RFC 5424-aligned severity numbers for standard Python log levels.
- Configurable transports (stderr/stdout/file) via environment.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from traceback import format_exception
from typing import Any

RFC5424_SEVERITY_BY_LEVEL: dict[str, int] = {
    "DEBUG": 7,
    "INFO": 6,
    "WARNING": 4,
    "ERROR": 3,
    "CRITICAL": 2,
}

_DEFAULT_TEXT_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def to_json_safe(value: Any) -> Any:
    """Convert arbitrary values to a JSON-serializable representation."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (datetime, date)):
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=UTC).isoformat()
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, dict):
        return {str(k): to_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [to_json_safe(v) for v in value]
    if hasattr(value, "__dict__"):
        return {
            "__class__": value.__class__.__name__,
            **{str(k): to_json_safe(v) for k, v in vars(value).items()},
        }
    return repr(value)


class ChronicleJsonFormatter(logging.Formatter):
    """Format records as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "logger": record.name,
            "level": record.levelname,
            "severity": RFC5424_SEVERITY_BY_LEVEL.get(record.levelname, 5),
            "message": message,
        }
        event_name = getattr(record, "chronicle_event", None)
        if isinstance(event_name, str) and event_name.strip():
            payload["event"] = event_name.strip()

        fields = getattr(record, "chronicle_fields", None)
        if isinstance(fields, dict) and fields:
            payload["fields"] = to_json_safe(fields)

        if record.exc_info:
            payload["exception"] = "".join(format_exception(*record.exc_info))
        return json.dumps(payload, ensure_ascii=True, separators=(",", ":"))


def _parse_level(raw_level: str | None) -> int:
    val = (raw_level or "INFO").strip().upper()
    return getattr(logging, val, logging.INFO)


def _build_handler(
    transport: str,
    formatter: logging.Formatter,
    file_path: str | None,
) -> logging.Handler:
    if transport == "stderr":
        handler: logging.Handler = logging.StreamHandler(sys.stderr)
    elif transport == "stdout":
        handler = logging.StreamHandler(sys.stdout)
    elif transport == "file":
        target = (file_path or "").strip()
        if not target:
            raise ValueError("CHRONICLE_LOG_FILE is required when transport includes 'file'")
        Path(target).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(target, encoding="utf-8")
    else:
        raise ValueError(
            "Unsupported CHRONICLE_LOG_TRANSPORTS value. Use comma-separated stderr,stdout,file."
        )
    handler.setFormatter(formatter)
    return handler


def configure_chronicle_logging() -> None:
    """Configure the `chronicle` logger once from env settings."""
    logger = logging.getLogger("chronicle")
    if getattr(logger, "_chronicle_logging_configured", False):
        return

    log_format = (os.environ.get("CHRONICLE_LOG_FORMAT") or "json").strip().lower()
    transports_raw = (os.environ.get("CHRONICLE_LOG_TRANSPORTS") or "stderr").strip()
    transports = [p.strip().lower() for p in transports_raw.split(",") if p.strip()]
    if not transports:
        transports = ["stderr"]

    file_path = os.environ.get("CHRONICLE_LOG_FILE")
    level = _parse_level(os.environ.get("CHRONICLE_LOG_LEVEL"))
    formatter: logging.Formatter
    if log_format == "json":
        formatter = ChronicleJsonFormatter()
    else:
        formatter = logging.Formatter(_DEFAULT_TEXT_FORMAT)

    logger.handlers.clear()
    for transport in transports:
        try:
            logger.addHandler(_build_handler(transport, formatter, file_path))
        except ValueError as exc:
            fallback = logging.StreamHandler(sys.stderr)
            fallback.setFormatter(logging.Formatter(_DEFAULT_TEXT_FORMAT))
            logger.addHandler(fallback)
            logger.warning("Invalid logging config: %s", exc)
            break

    logger.setLevel(level)
    logger.propagate = False
    logger._chronicle_logging_configured = True  # type: ignore[attr-defined]


def log_event(
    logger: logging.Logger,
    level: int,
    event: str,
    *,
    exc_info: Any | None = None,
    **fields: Any,
) -> None:
    """Emit a structured event with JSON-safe fields."""
    logger.log(
        level,
        event,
        extra={"chronicle_event": event, "chronicle_fields": to_json_safe(fields)},
        exc_info=exc_info,
    )
