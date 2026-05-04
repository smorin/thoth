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


def test_gemini_built_in_modes_registered() -> None:
    """BUILTIN_MODES contains the three Gemini modes."""
    from thoth.config import BUILTIN_MODES

    assert "gemini_quick" in BUILTIN_MODES
    assert "gemini_pro" in BUILTIN_MODES
    assert "gemini_reasoning" in BUILTIN_MODES

    quick = BUILTIN_MODES["gemini_quick"]
    assert quick["provider"] == "gemini"
    assert quick["model"] == "gemini-2.5-flash-lite"
    assert quick["kind"] == "immediate"
    quick_cfg = quick.get("gemini")
    assert isinstance(quick_cfg, dict)
    assert quick_cfg.get("tools") == ["google_search"]
    assert quick_cfg.get("thinking_budget") == 0

    reasoning = BUILTIN_MODES["gemini_reasoning"]
    assert reasoning["model"] == "gemini-2.5-pro"
    reasoning_cfg = reasoning.get("gemini")
    assert isinstance(reasoning_cfg, dict)
    assert reasoning_cfg.get("thinking_budget") == -1
    assert reasoning_cfg.get("include_thoughts") is True


def test_gemini_build_messages_renders_user_prompt() -> None:
    """_build_messages_and_system creates contents=[Content(role='user', parts=[Part(text=prompt)])]."""
    from thoth.providers.gemini import GeminiProvider

    provider = GeminiProvider(api_key="dummy", config={})
    contents, system = provider._build_messages_and_system("What is 2+2?", None)
    assert len(contents) == 1
    content = contents[0]
    assert getattr(content, "role", None) == "user"
    parts = getattr(content, "parts", None) or []
    assert len(parts) == 1
    assert getattr(parts[0], "text", "") == "What is 2+2?"
    assert system is None


def test_gemini_build_messages_passes_through_system_prompt() -> None:
    """system_prompt becomes the system_instruction return value."""
    from thoth.providers.gemini import GeminiProvider

    provider = GeminiProvider(api_key="dummy", config={})
    contents, system = provider._build_messages_and_system("Q?", "You are a math tutor.")
    assert system == "You are a math tutor."


def test_gemini_build_tools_translates_google_search() -> None:
    """_build_tools(['google_search']) returns [Tool(google_search=GoogleSearch())]."""
    from google.genai import types as genai_types  # type: ignore[import-not-found]

    from thoth.providers.gemini import GeminiProvider

    provider = GeminiProvider(api_key="dummy", config={})
    tools = provider._build_tools(["google_search"])
    assert len(tools) == 1
    tool = tools[0]
    assert isinstance(tool, genai_types.Tool)
    assert tool.google_search is not None


def test_gemini_build_tools_skips_unknown_names() -> None:
    """Unknown tool names are skipped (forward-compat for future tool families)."""
    from thoth.providers.gemini import GeminiProvider

    provider = GeminiProvider(api_key="dummy", config={})
    tools = provider._build_tools(["google_search", "future_unknown_tool"])
    assert len(tools) == 1


def test_gemini_build_generate_content_config_quick_mode() -> None:
    """gemini_quick mode produces tools=[GoogleSearch()], thinking_config.thinking_budget=0."""
    from thoth.config import BUILTIN_MODES
    from thoth.providers.gemini import GeminiProvider

    config = {**BUILTIN_MODES["gemini_quick"], "kind": "immediate"}
    provider = GeminiProvider(api_key="dummy", config=config)
    gen_config = provider._build_generate_content_config()

    assert gen_config is not None
    tools = getattr(gen_config, "tools", None) or []
    assert len(tools) == 1

    thinking_config = getattr(gen_config, "thinking_config", None)
    assert thinking_config is not None
    assert thinking_config.thinking_budget == 0


def test_gemini_build_generate_content_config_reasoning_mode() -> None:
    """gemini_reasoning mode sets include_thoughts=True."""
    from thoth.config import BUILTIN_MODES
    from thoth.providers.gemini import GeminiProvider

    config = {**BUILTIN_MODES["gemini_reasoning"], "kind": "immediate"}
    provider = GeminiProvider(api_key="dummy", config=config)
    gen_config = provider._build_generate_content_config()

    thinking_config = getattr(gen_config, "thinking_config", None)
    assert thinking_config is not None
    assert thinking_config.thinking_budget == -1
    assert thinking_config.include_thoughts is True


def test_gemini_build_generate_content_config_passthrough_temperature() -> None:
    """Direct SDK key (e.g. temperature) under [modes.X.gemini] passes through to GenerateContentConfig.temperature."""
    from thoth.providers.gemini import GeminiProvider

    config = {"gemini": {"temperature": 0.42}, "kind": "immediate"}
    provider = GeminiProvider(api_key="dummy", config=config)
    gen_config = provider._build_generate_content_config()

    assert gen_config is not None
    assert gen_config.temperature == 0.42


def test_gemini_build_generate_content_config_returns_none_when_empty() -> None:
    """No [modes.X.gemini] keys -> returns None (caller falls back to no config kwarg)."""
    from thoth.providers.gemini import GeminiProvider

    provider = GeminiProvider(api_key="dummy", config={})
    gen_config = provider._build_generate_content_config()
    assert gen_config is None


def test_gemini_build_generate_content_config_include_thoughts_only_defaults_thinking_budget_to_dynamic() -> (
    None
):
    """When only include_thoughts is set (no explicit thinking_budget), helper defaults to thinking_budget=-1 ('dynamic').

    This is a deliberate policy: setting include_thoughts=True is opting INTO
    thinking-related output, so 'dynamic' (-1) is the most useful default.
    Locked by this test; change requires changing the policy and the test together.
    """
    from thoth.providers.gemini import GeminiProvider

    config = {"gemini": {"include_thoughts": True}, "kind": "immediate"}
    provider = GeminiProvider(api_key="dummy", config=config)
    gen_config = provider._build_generate_content_config()

    assert gen_config is not None
    thinking_config = getattr(gen_config, "thinking_config", None)
    assert thinking_config is not None
    assert thinking_config.thinking_budget == -1, (
        "include_thoughts=True without explicit thinking_budget must default to -1 (dynamic)"
    )
    assert thinking_config.include_thoughts is True
