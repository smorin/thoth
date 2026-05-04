"""Unit tests for the Gemini synchronous chat provider (P24)."""

from __future__ import annotations


def test_gemini_module_exists() -> None:
    """The Gemini provider module is importable."""
    from thoth.providers import gemini  # noqa: F401


def test_gemini_constants_use_suffix_naming() -> None:
    """Gemini module-level constants follow the cross-provider suffix convention."""
    from thoth.providers import gemini

    assert hasattr(gemini, "_DIRECT_SDK_KEYS_GEMINI")
    assert hasattr(gemini, "_PROVIDER_NAME_GEMINI")
    assert gemini._PROVIDER_NAME_GEMINI == "gemini"
    # Sample membership for some load-bearing keys
    assert "temperature" in gemini._DIRECT_SDK_KEYS_GEMINI
    assert "thinking_budget" in gemini._DIRECT_SDK_KEYS_GEMINI


def test_gemini_provider_class_exists_and_extends_research_provider() -> None:
    """GeminiProvider class extends ResearchProvider."""
    from thoth.providers.base import ResearchProvider
    from thoth.providers.gemini import GeminiProvider

    assert issubclass(GeminiProvider, ResearchProvider)


def test_gemini_provider_default_model_is_flash_lite() -> None:
    """GeminiProvider defaults to gemini-2.5-flash-lite when no model configured."""
    from thoth.providers.gemini import GeminiProvider

    provider = GeminiProvider(api_key="dummy", config={})
    assert provider.model == "gemini-2.5-flash-lite"


def test_gemini_provider_is_implemented() -> None:
    """is_implemented() returns True (explicit, not inherited)."""
    from thoth.providers.gemini import GeminiProvider

    provider = GeminiProvider(api_key="dummy", config={})
    assert provider.is_implemented() is True
    assert provider.implementation_status() is None
