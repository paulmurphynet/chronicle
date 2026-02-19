"""Tests for SSRF mitigation (scorer URL fetch and core.ssrf)."""

from __future__ import annotations

import socket
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from chronicle.core.ssrf import is_ssrf_unsafe_host  # noqa: E402


def test_ssrf_blocks_loopback() -> None:
    """Loopback hostnames are considered unsafe."""
    assert is_ssrf_unsafe_host("localhost") is True
    assert is_ssrf_unsafe_host("127.0.0.1") is True
    assert is_ssrf_unsafe_host("::1") is True


def test_ssrf_blocks_private() -> None:
    """Private RFC1918 addresses are considered unsafe."""
    assert is_ssrf_unsafe_host("192.168.1.1") is True
    assert is_ssrf_unsafe_host("10.0.0.1") is True
    assert is_ssrf_unsafe_host("172.16.0.1") is True


def test_ssrf_blocks_metadata() -> None:
    """Cloud metadata IP is considered unsafe."""
    assert is_ssrf_unsafe_host("169.254.169.254") is True


def test_ssrf_blocks_empty() -> None:
    """Empty or missing host is unsafe."""
    assert is_ssrf_unsafe_host("") is True
    assert is_ssrf_unsafe_host("   ") is True


def test_ssrf_allows_public_hostname() -> None:
    """Public hostnames that resolve to public IPs are not unsafe."""

    def fake_getaddrinfo(_host: str, _port: object, _family: int) -> list[tuple]:
        return [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                6,
                "",
                ("93.184.216.34", 0),
            )
        ]

    orig = socket.getaddrinfo
    socket.getaddrinfo = fake_getaddrinfo  # type: ignore[assignment]
    try:
        assert is_ssrf_unsafe_host("example.com") is False
    finally:
        socket.getaddrinfo = orig  # type: ignore[assignment]
