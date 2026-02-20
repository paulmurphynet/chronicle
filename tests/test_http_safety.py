from __future__ import annotations

import pytest
from chronicle.core.http_safety import ensure_safe_http_url


def test_ensure_safe_http_url_accepts_http_and_https() -> None:
    assert ensure_safe_http_url("https://example.com/x", block_private_hosts=False) == "https://example.com/x"
    assert ensure_safe_http_url("http://127.0.0.1:8000/health", block_private_hosts=False).startswith(
        "http://127.0.0.1:8000"
    )


def test_ensure_safe_http_url_rejects_non_http_schemes() -> None:
    with pytest.raises(ValueError):
        ensure_safe_http_url("file:///tmp/data.txt", block_private_hosts=False)


def test_ensure_safe_http_url_blocks_private_host_when_required() -> None:
    with pytest.raises(ValueError):
        ensure_safe_http_url("http://127.0.0.1/internal", block_private_hosts=True)
