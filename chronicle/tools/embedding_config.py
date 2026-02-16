# Embedding config: optional semantic search. Read from env.
# See docs/VECTOR_PROJECTION.md.

import os
from urllib.parse import urlparse

from chronicle.core.ssrf import is_ssrf_unsafe_host

_DEFAULT_BASE_URL = "http://127.0.0.1:11434"
_DEFAULT_MODEL_OLLAMA = "nomic-embed-text"
_DEFAULT_MODEL_OPENAI = "text-embedding-3-small"
_ALLOWED_SCHEMES = ("http", "https")


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def is_embedding_enabled() -> bool:
    """True if CHRONICLE_EMBEDDING_ENABLED is set. Default False."""
    return _env_bool("CHRONICLE_EMBEDDING_ENABLED", False)


def get_embedding_provider() -> str:
    """'ollama' or 'openai_compatible'. Default ollama."""
    raw = os.environ.get("CHRONICLE_EMBEDDING_PROVIDER", "ollama").strip().lower()
    if raw in ("ollama", "openai_compatible"):
        return raw
    return "ollama"


def get_embedding_api_key() -> str | None:
    """API key for openai_compatible. None if unset."""
    raw = os.environ.get("CHRONICLE_EMBEDDING_API_KEY", "").strip()
    return raw or None


def get_embedding_base_url() -> str:
    """Base URL for embeddings. SSRF-safe."""
    provider = get_embedding_provider()
    default = _DEFAULT_BASE_URL if provider == "ollama" else "https://api.openai.com/v1"
    url = os.environ.get("CHRONICLE_EMBEDDING_BASE_URL", default).strip().rstrip("/") or default
    try:
        parsed = urlparse(url)
        if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
            return default
        host = (parsed.hostname or parsed.netloc.split(":")[0] or "").strip()
        if is_ssrf_unsafe_host(host):
            return default
        return f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        return default


def get_embedding_model() -> str:
    """Model name for embeddings."""
    provider = get_embedding_provider()
    default = _DEFAULT_MODEL_OLLAMA if provider == "ollama" else _DEFAULT_MODEL_OPENAI
    return os.environ.get("CHRONICLE_EMBEDDING_MODEL", default).strip() or default
