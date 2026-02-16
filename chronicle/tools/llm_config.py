# LLM config: Ollama (local) or OpenAI-compatible (bring your own API key). Read from env; no HTTP here.
# See docs/AI_IMPLEMENTATION_PLAN.md Phase 1.

import os
from urllib.parse import urlparse

from chronicle.core.ssrf import is_ssrf_unsafe_host

_DEFAULT_BASE_URL = "http://127.0.0.1:11434"
_DEFAULT_MODEL = "qwen2.5:7b"
_DEFAULT_TIMEOUT = 60.0
_ALLOWED_LLM_SCHEMES = ("http", "https")

# Provider: ollama = local Ollama (no key); openai_compatible = hosted APIs (Bearer key).
PROVIDER_OLLAMA = "ollama"
PROVIDER_OPENAI_COMPATIBLE = "openai_compatible"
_VALID_PROVIDERS = frozenset({PROVIDER_OLLAMA, PROVIDER_OPENAI_COMPATIBLE})


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def is_llm_enabled() -> bool:
    """True if CHRONICLE_LLM_ENABLED is set to a truthy value (e.g. true, 1). Default False."""
    return _env_bool("CHRONICLE_LLM_ENABLED", False)


def get_llm_provider() -> str:
    """Provider: 'ollama' (local, no key) or 'openai_compatible' (hosted, use CHRONICLE_LLM_API_KEY). Default ollama."""
    raw = os.environ.get("CHRONICLE_LLM_PROVIDER", PROVIDER_OLLAMA).strip().lower()
    if raw in _VALID_PROVIDERS:
        return raw
    return PROVIDER_OLLAMA


def get_llm_api_key() -> str | None:
    """API key for openai_compatible provider. None if unset or empty. Not used for ollama."""
    raw = os.environ.get("CHRONICLE_LLM_API_KEY", "").strip()
    return raw or None


def get_llm_base_url() -> str:
    """Ollama or OpenAI-compatible API base URL (no trailing slash). Default http://127.0.0.1:11434.
    Only http and https are allowed; private/metadata hosts rejected (SSRF mitigation)."""
    url = os.environ.get("CHRONICLE_LLM_BASE_URL", _DEFAULT_BASE_URL).strip()
    url = url.rstrip("/") or _DEFAULT_BASE_URL
    try:
        parsed = urlparse(url)
        if parsed.scheme.lower() not in _ALLOWED_LLM_SCHEMES:
            return _DEFAULT_BASE_URL
        if not parsed.netloc:
            return _DEFAULT_BASE_URL
        host = (parsed.hostname or parsed.netloc.split(":")[0] or "").strip()
        if is_ssrf_unsafe_host(host):
            return _DEFAULT_BASE_URL
        return f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        return _DEFAULT_BASE_URL


def get_llm_model() -> str:
    """Model name (e.g. qwen2.5:7b for Ollama, gpt-4o-mini for OpenAI). Default qwen2.5:7b."""
    return os.environ.get("CHRONICLE_LLM_MODEL", _DEFAULT_MODEL).strip() or _DEFAULT_MODEL


def get_llm_timeout() -> float:
    """Request timeout in seconds. Default 60."""
    raw = os.environ.get("CHRONICLE_LLM_TIMEOUT_SECONDS", "").strip()
    if not raw:
        return _DEFAULT_TIMEOUT
    try:
        return max(1.0, float(raw))
    except ValueError:
        return _DEFAULT_TIMEOUT
