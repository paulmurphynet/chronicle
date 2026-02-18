"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import os
import urllib.error
import urllib.request

import pytest


def _ollama_available() -> bool:
    """True if CHRONICLE_LLM_ENABLED is set and Ollama is reachable."""
    if not os.environ.get("CHRONICLE_LLM_ENABLED", "").strip().lower() in ("true", "1", "yes"):
        return False
    base = os.environ.get("CHRONICLE_LLM_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    try:
        req = urllib.request.Request(f"{base}/api/tags", method="GET")
        urllib.request.urlopen(req, timeout=2)
        return True
    except (OSError, urllib.error.URLError, TimeoutError):
        return False


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Skip tests marked 'ollama' when Ollama is not available."""
    if item.get_closest_marker("ollama") and not _ollama_available():
        pytest.skip(
            "Ollama not available (set CHRONICLE_LLM_ENABLED=true and ensure Ollama is running). "
            "See docs/testing-with-ollama.md."
        )
