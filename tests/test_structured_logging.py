from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from chronicle.core.logging import (
    ChronicleJsonFormatter,
    configure_chronicle_logging,
    to_json_safe,
)


def _snapshot_logger_state(logger: logging.Logger) -> tuple[list[logging.Handler], int, bool]:
    handlers = list(logger.handlers)
    level = logger.level
    configured = bool(getattr(logger, "_chronicle_logging_configured", False))
    return handlers, level, configured


def _restore_logger_state(
    logger: logging.Logger,
    snapshot: tuple[list[logging.Handler], int, bool],
) -> None:
    handlers, level, configured = snapshot
    logger.handlers.clear()
    for handler in handlers:
        logger.addHandler(handler)
    logger.setLevel(level)
    if configured:
        logger._chronicle_logging_configured = True  # type: ignore[attr-defined]
    elif hasattr(logger, "_chronicle_logging_configured"):
        delattr(logger, "_chronicle_logging_configured")


def test_to_json_safe_normalizes_complex_values() -> None:
    payload = {
        "path": Path("/tmp/demo"),
        "set_values": {"a", "b"},
        "time": datetime(2026, 2, 21, 4, 50, tzinfo=UTC),
        "bytes": b"abc",
    }
    converted = to_json_safe(payload)
    text = json.dumps(converted)
    assert "/tmp/demo" in text
    assert "2026-02-21T04:50:00+00:00" in text
    assert "abc" in text


def test_json_formatter_emits_rfc5424_severity_and_fields() -> None:
    formatter = ChronicleJsonFormatter()
    record = logging.LogRecord(
        name="chronicle.api",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="request_completed",
        args=(),
        exc_info=None,
    )
    record.chronicle_event = "request_completed"  # type: ignore[attr-defined]
    record.chronicle_fields = {"path": Path("/health"), "status_code": 200}  # type: ignore[attr-defined]
    line = formatter.format(record)
    parsed = json.loads(line)
    assert parsed["event"] == "request_completed"
    assert parsed["level"] == "INFO"
    assert parsed["severity"] == 6
    assert parsed["fields"]["path"] == "/health"


def test_configure_chronicle_logging_sets_level_and_handlers(monkeypatch) -> None:
    logger = logging.getLogger("chronicle")
    snap = _snapshot_logger_state(logger)
    try:
        monkeypatch.setenv("CHRONICLE_LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("CHRONICLE_LOG_FORMAT", "json")
        monkeypatch.setenv("CHRONICLE_LOG_TRANSPORTS", "stderr")
        if hasattr(logger, "_chronicle_logging_configured"):
            delattr(logger, "_chronicle_logging_configured")
        configure_chronicle_logging()
        assert logger.handlers
        assert logger.level == logging.DEBUG
    finally:
        _restore_logger_state(logger, snap)
