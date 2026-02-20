# LLM HTTP client: Ollama (local) or OpenAI-compatible (bring your own API key). Phase 1 AI plan.
# Uses stdlib urllib; no extra dependency.

import json
import urllib.error
import urllib.request
from typing import Any

from chronicle.core.http_safety import ensure_safe_http_url
from chronicle.tools.llm_config import (
    PROVIDER_OPENAI_COMPATIBLE,
    get_llm_api_key,
    get_llm_base_url,
    get_llm_model,
    get_llm_provider,
    get_llm_timeout,
)


class LlmClientError(Exception):
    """LLM request failed (connection, timeout, or non-2xx)."""

    pass


class LlmClient:
    """Client for Ollama or OpenAI-compatible chat API. Reads config from env by default."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
        provider: str | None = None,
        api_key: str | None = None,
    ):
        self._base_url = base_url if base_url is not None else get_llm_base_url()
        self._model = model if model is not None else get_llm_model()
        self._timeout = timeout if timeout is not None else get_llm_timeout()
        self._provider = provider if provider is not None else get_llm_provider()
        self._api_key = api_key if api_key is not None else get_llm_api_key()

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        timeout: float | None = None,
    ) -> str:
        """Send prompt (and optional system message); return assistant reply text."""
        return generate(
            prompt,
            system=system,
            base_url=self._base_url,
            model=self._model,
            timeout=timeout if timeout is not None else self._timeout,
            provider=self._provider,
            api_key=self._api_key,
        )


def _ollama_request(
    url: str,
    body: dict[str, Any],
    timeout: float,
) -> str:
    """POST to Ollama /api/chat; return message.content."""
    safe_url = ensure_safe_http_url(url, block_private_hosts=False)
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        safe_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
        if resp.status != 200:
            raise LlmClientError(f"LLM API returned status {resp.status}")
        out = json.loads(resp.read().decode("utf-8"))
    msg = out.get("message")
    if not isinstance(msg, dict):
        raise LlmClientError("LLM response missing or invalid 'message'")
    content = msg.get("content")
    if content is None:
        return ""
    return str(content).strip()


def _openai_compatible_request(
    url: str,
    body: dict[str, Any],
    timeout: float,
    api_key: str | None,
) -> str:
    """POST to OpenAI-compatible /chat/completions; return choices[0].message.content."""
    safe_url = ensure_safe_http_url(url, block_private_hosts=False)
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(safe_url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
        if resp.status == 401:
            raise LlmClientError("LLM API key invalid or missing (401)")
        if resp.status != 200:
            raise LlmClientError(f"LLM API returned status {resp.status}")
        out = json.loads(resp.read().decode("utf-8"))
    choices = out.get("choices")
    if not choices or not isinstance(choices, list):
        raise LlmClientError("LLM response missing or invalid 'choices'")
    first = choices[0]
    if not isinstance(first, dict):
        raise LlmClientError("LLM response choices[0] invalid")
    msg = first.get("message")
    if not isinstance(msg, dict):
        raise LlmClientError("LLM response missing or invalid 'choices[0].message'")
    content = msg.get("content")
    if content is None:
        return ""
    return str(content).strip()


def generate(
    prompt: str,
    *,
    system: str | None = None,
    base_url: str = "http://127.0.0.1:11434",
    model: str = "qwen2.5:7b",
    timeout: float = 60.0,
    provider: str | None = None,
    api_key: str | None = None,
) -> str:
    """
    Send a single prompt to the configured LLM; return the assistant reply.
    - ollama: POST /api/chat (no auth).
    - openai_compatible: POST /chat/completions with optional Bearer API key.
    Raises LlmClientError on connection error, timeout, or non-2xx response.
    """
    effective_provider = provider if provider is not None else get_llm_provider()
    effective_key = api_key if api_key is not None else get_llm_api_key()

    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    base = base_url.rstrip("/")
    body: dict[str, Any] = {"model": model, "messages": messages}
    if effective_provider == PROVIDER_OPENAI_COMPATIBLE:
        url = f"{base}/chat/completions"
        try:
            return _openai_compatible_request(url, body, timeout, effective_key)
        except urllib.error.URLError as e:
            raise LlmClientError(f"LLM request failed: {e}") from e
        except ValueError as e:
            raise LlmClientError(f"Invalid LLM URL: {e}") from e
        except json.JSONDecodeError as e:
            raise LlmClientError(f"LLM response not valid JSON: {e}") from e
    else:
        body["stream"] = False
        url = f"{base}/api/chat"
        try:
            return _ollama_request(url, body, timeout)
        except urllib.error.URLError as e:
            raise LlmClientError(f"LLM request failed: {e}") from e
        except ValueError as e:
            raise LlmClientError(f"Invalid LLM URL: {e}") from e
        except json.JSONDecodeError as e:
            raise LlmClientError(f"LLM response not valid JSON: {e}") from e
