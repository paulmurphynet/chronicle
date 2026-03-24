"""Smoke tests for optional integrations: import module and ensure public API exists.

These tests do not require LangChain, LlamaIndex, or Haystack to be installed.
When the framework is missing, the integration module still imports and exposes
the handler/component as None or a stub. When the framework is present, the
real class is available. We only assert that the module imports and the
expected attribute exists (type may be None or a class).
"""

from __future__ import annotations


def test_langchain_integration_imports_and_exposes_handler() -> None:
    """chronicle.integrations.langchain can be imported and exposes ChronicleCallbackHandler."""
    import chronicle.integrations.langchain as m

    assert hasattr(m, "ChronicleCallbackHandler")


def test_llamaindex_integration_imports_and_exposes_handler() -> None:
    """chronicle.integrations.llamaindex can be imported and exposes ChronicleCallbackHandler."""
    import chronicle.integrations.llamaindex as m

    assert hasattr(m, "ChronicleCallbackHandler")


def test_haystack_integration_imports_and_exposes_component() -> None:
    """chronicle.integrations.haystack can be imported and exposes ChronicleEvidenceWriter."""
    import chronicle.integrations.haystack as m

    assert hasattr(m, "ChronicleEvidenceWriter")
