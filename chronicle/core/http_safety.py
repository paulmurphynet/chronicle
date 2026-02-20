"""HTTP URL validation helpers used by networked client/tooling code."""

from __future__ import annotations

from urllib.parse import urlparse

from chronicle.core.ssrf import is_ssrf_unsafe_host

_ALLOWED_SCHEMES = frozenset({"http", "https"})


def ensure_safe_http_url(url: str, *, block_private_hosts: bool) -> str:
    """Validate URL scheme/host constraints and return a normalized URL string."""
    raw = (url or "").strip()
    parsed = urlparse(raw)
    scheme = parsed.scheme.lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise ValueError("URL scheme must be http or https")
    if not parsed.netloc:
        raise ValueError("URL must include host")
    host = (parsed.hostname or "").strip()
    if not host:
        raise ValueError("URL must include host")
    if block_private_hosts and is_ssrf_unsafe_host(host):
        raise ValueError("URL host is not allowed")
    return parsed.geturl()
