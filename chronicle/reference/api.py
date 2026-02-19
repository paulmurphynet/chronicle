"""Reference import path for the optional FastAPI app."""

from __future__ import annotations

from typing import Any


def get_app() -> Any:
    """Return the Chronicle FastAPI app.

    This import is lazy so core-only environments do not import API dependencies
    unless explicitly requested.
    """
    try:
        from chronicle.api.app import app
    except ImportError as e:
        raise ImportError(
            "Chronicle API dependencies are not installed. Install with: pip install -e '.[api]'"
        ) from e
    return app
