"""SSRF mitigation: block private/link-local/loopback/metadata hosts.

Used by:
- chronicle.api.helpers.fetch_url() — validates initial URL and each redirect target for from-url evidence ingest.
- chronicle.tools.llm_config.get_llm_base_url() — rejects CHRONICLE_LLM_BASE_URL if host is unsafe.

Keep this module the single source of truth for SSRF host checks so both call sites stay consistent.
"""

import ipaddress
import socket


def is_ssrf_unsafe_host(host: str) -> bool:
    """True if host resolves to a private/link-local/loopback/metadata address. SSRF mitigation."""
    if not host or host.strip() == "":
        return True
    try:
        for _, _, _, _, sockaddr in socket.getaddrinfo(host, None, socket.AF_UNSPEC):
            addr = sockaddr[0]
            try:
                ip = ipaddress.ip_address(addr)
            except ValueError:
                continue
            if ip.is_loopback or ip.is_private or ip.is_link_local:
                return True
            if addr == "169.254.169.254":
                return True
        return False
    except (OSError, socket.gaierror):
        return True
