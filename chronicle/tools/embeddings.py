# Optional embedding API: embed(text) -> list[float] for semantic search. See VECTOR_PROJECTION.md.

import json
import urllib.error
import urllib.request
from typing import Any

from chronicle.core.http_safety import ensure_safe_http_url
from chronicle.tools.embedding_config import (
    get_embedding_api_key,
    get_embedding_base_url,
    get_embedding_model,
    get_embedding_provider,
    is_embedding_enabled,
)


def embed(text: str) -> list[float] | None:
    """Compute embedding for text. Returns None if disabled, misconfigured, or on failure."""
    if not text or not is_embedding_enabled():
        return None
    provider = get_embedding_provider()
    base_url = get_embedding_base_url()
    model = get_embedding_model()
    api_key = get_embedding_api_key()
    timeout = 30.0
    try:
        if provider == "ollama":
            return _embed_ollama(base_url, model, text, timeout)
        return _embed_openai_compatible(base_url, model, text, api_key, timeout)
    except Exception:
        return None


def _embed_ollama(base_url: str, model: str, text: str, timeout: float) -> list[float] | None:
    try:
        url = ensure_safe_http_url(f"{base_url.rstrip('/')}/api/embeddings", block_private_hosts=False)
        body = json.dumps({"model": model, "input": text}).encode("utf-8")
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
            data: Any = json.loads(resp.read().decode())
        emb = data.get("embeddings")
        if isinstance(emb, list) and len(emb) > 0 and isinstance(emb[0], list):
            return [float(x) for x in emb[0]]
        return None
    except (urllib.error.URLError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None


def _embed_openai_compatible(
    base_url: str, model: str, text: str, api_key: str | None, timeout: float
) -> list[float] | None:
    if not api_key:
        return None
    try:
        url = ensure_safe_http_url(f"{base_url.rstrip('/')}/embeddings", block_private_hosts=False)
        body = json.dumps({"model": model, "input": text}).encode("utf-8")
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {api_key}")
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
            data = json.loads(resp.read().decode())
        items = data.get("data")
        if isinstance(items, list) and len(items) > 0:
            emb = items[0].get("embedding") if isinstance(items[0], dict) else None
            if isinstance(emb, list):
                return [float(x) for x in emb]
        return None
    except (urllib.error.URLError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None
