"""OpenAI provider config → request payload tests.

Migrated from thoth_test GAP01-01…03.
"""

from __future__ import annotations

import asyncio
import types
import warnings
from pathlib import Path
from typing import Any, cast

import pytest

from thoth.providers.openai import OpenAIProvider


@pytest.fixture(autouse=True)
def _isolate_config(isolated_thoth_home: Path) -> Path:
    return isolated_thoth_home


def test_max_tool_calls_reaches_request_payload() -> None:
    """GAP01-01: max_tool_calls from provider config reaches the Responses API payload."""
    captured: dict[str, Any] = {}

    async def fake_create(*args: object, **kwargs: object) -> object:
        captured.update(kwargs)
        return types.SimpleNamespace(id="job-gap01-1")

    provider = OpenAIProvider(
        api_key="dummy",
        config={"model": "o3-deep-research", "openai": {"max_tool_calls": 80}},
    )
    provider.client = cast(
        Any, types.SimpleNamespace(responses=types.SimpleNamespace(create=fake_create))
    )
    asyncio.run(provider.submit("test prompt", mode="deep_research"))
    assert "max_tool_calls" in captured, (
        f"max_tool_calls missing from request payload: {list(captured.keys())}"
    )
    assert captured["max_tool_calls"] == 80, (
        f"expected max_tool_calls=80, got {captured['max_tool_calls']!r}"
    )


def test_code_interpreter_false_excludes_tool() -> None:
    """GAP01-02: code_interpreter=False in config excludes the tool from the request."""
    captured: dict[str, Any] = {}

    async def fake_create(*args: object, **kwargs: object) -> object:
        captured.update(kwargs)
        return types.SimpleNamespace(id="job-gap01-2")

    provider = OpenAIProvider(
        api_key="dummy",
        config={"model": "o3-deep-research", "openai": {"code_interpreter": False}},
    )
    provider.client = cast(
        Any, types.SimpleNamespace(responses=types.SimpleNamespace(create=fake_create))
    )
    asyncio.run(provider.submit("test prompt", mode="deep_research"))
    tool_types = [t.get("type") for t in captured.get("tools", [])]
    assert "code_interpreter" not in tool_types, (
        f"code_interpreter should be absent when config sets it False, got tools: {tool_types}"
    )
    assert "web_search_preview" in tool_types, (
        f"web_search_preview must still be present, got tools: {tool_types}"
    )


def test_default_config_includes_code_interpreter_and_omits_max_tool_calls() -> None:
    """GAP01-03: default config — no max_tool_calls key, code_interpreter included."""
    captured: dict[str, Any] = {}

    async def fake_create(*args: object, **kwargs: object) -> object:
        captured.update(kwargs)
        return types.SimpleNamespace(id="job-gap01-3")

    provider = OpenAIProvider(api_key="dummy", config={"model": "o3-deep-research"})
    provider.client = cast(
        Any, types.SimpleNamespace(responses=types.SimpleNamespace(create=fake_create))
    )
    asyncio.run(provider.submit("test prompt", mode="deep_research"))
    assert "max_tool_calls" not in captured, (
        f"max_tool_calls should be absent when not configured, got: {captured.get('max_tool_calls')}"
    )
    tools = captured.get("tools", [])
    code_interp_tool = next((t for t in tools if t.get("type") == "code_interpreter"), None)
    assert code_interp_tool is not None, (
        f"code_interpreter must be included by default, got tools: {[t.get('type') for t in tools]}"
    )
    assert code_interp_tool.get("container") == {"type": "auto"}, (
        f"code_interpreter tool must carry container={{type: auto}} "
        f"(OpenAI API requirement), got: {code_interp_tool}"
    )


def test_create_provider_sets_background_for_deep_research_model() -> None:
    """Regression: create_provider must set background=True when the mode
    pins a deep-research model. Previously only covered end-to-end via
    test_oai_background.py — this pins the contract at the factory."""
    from types import SimpleNamespace

    from thoth.config import ConfigManager
    from thoth.providers import create_provider

    config = cast(
        ConfigManager,
        SimpleNamespace(
            data={"providers": {"openai": {"api_key": "sk-test-deep-research-factory"}}}
        ),
    )
    mode_config: dict[str, Any] = {"model": "o3-deep-research"}

    provider = create_provider(
        "openai",
        config,
        mode_config=mode_config,
    )
    # provider.config is the mutated provider_config dict passed to the constructor;
    # background=True is set when is_background_mode(provider_config) is True.
    assert provider.config.get("background") is True


def test_create_provider_no_background_for_plain_model() -> None:
    """Inverse: a plain (non-deep-research) model does NOT get background=True."""
    from types import SimpleNamespace

    from thoth.config import ConfigManager
    from thoth.providers import create_provider

    config = cast(
        ConfigManager,
        SimpleNamespace(data={"providers": {"openai": {"api_key": "sk-test-plain-factory"}}}),
    )
    mode_config: dict[str, Any] = {"model": "o3"}

    provider = create_provider(
        "openai",
        config,
        mode_config=mode_config,
    )
    assert provider.config.get("background", False) is False


# ---------------------------------------------------------------------------
# P23-TS01 — `--model` passthrough through create_provider.
# P23-RS01 — provider-specific request settings from mode config must reach
# provider constructors, including nested Perplexity extra_body settings.
# ---------------------------------------------------------------------------


def test_create_provider_passes_perplexity_model_from_mode_config() -> None:
    """P23-TS01: mode-config model passes through to PerplexityProvider."""
    from types import SimpleNamespace

    from thoth.config import ConfigManager
    from thoth.providers import create_provider

    config = cast(
        ConfigManager,
        SimpleNamespace(data={"providers": {"perplexity": {"api_key": "pplx-test"}}}),
    )
    mode_config: dict[str, Any] = {"model": "sonar-pro", "kind": "immediate"}

    provider = create_provider("perplexity", config, mode_config=mode_config)
    assert provider.config.get("model") == "sonar-pro"


def test_create_provider_perplexity_default_model_is_sonar() -> None:
    """P23-TS01: PerplexityProvider defaults to `sonar` when no model is configured.

    Plan-pinned default; previous stub used `sonar-pro`.
    """
    from types import SimpleNamespace

    from thoth.config import ConfigManager
    from thoth.providers import create_provider
    from thoth.providers.perplexity import PerplexityProvider

    config = cast(
        ConfigManager,
        SimpleNamespace(data={"providers": {"perplexity": {"api_key": "pplx-test"}}}),
    )

    provider = create_provider("perplexity", config)
    assert isinstance(provider, PerplexityProvider)
    assert provider.model == "sonar"


def test_create_provider_perplexity_passes_arbitrary_model_string() -> None:
    """P23-TS01: no local provider/model compatibility validation.

    A model string thoth has never seen passes through unchanged; any
    invalid-model error is surfaced from the provider/API layer.
    """
    from types import SimpleNamespace

    from thoth.config import ConfigManager
    from thoth.providers import create_provider

    config = cast(
        ConfigManager,
        SimpleNamespace(data={"providers": {"perplexity": {"api_key": "pplx-test"}}}),
    )
    mode_config: dict[str, Any] = {
        "model": "future-sonar-2027-preview",
        "kind": "immediate",
    }

    provider = create_provider("perplexity", config, mode_config=mode_config)
    assert provider.config.get("model") == "future-sonar-2027-preview"


def test_create_provider_passes_perplexity_namespace_from_mode_config() -> None:
    """P23-RS01: mode_config['perplexity'] reaches PerplexityProvider.config."""
    from types import SimpleNamespace

    from thoth.config import ConfigManager
    from thoth.providers import create_provider

    config = cast(
        ConfigManager,
        SimpleNamespace(data={"providers": {"perplexity": {"api_key": "pplx-test"}}}),
    )
    mode_config: dict[str, Any] = {
        "provider": "perplexity",
        "model": "sonar",
        "kind": "immediate",
        "perplexity": {
            "web_search_options": {"search_context_size": "low"},
            "stream_mode": "full",
            "search_domain_filter": ["perplexity.ai"],
        },
    }

    provider = create_provider("perplexity", config, mode_config=mode_config)

    assert provider.config["perplexity"] == {
        "web_search_options": {"search_context_size": "low"},
        "stream_mode": "full",
        "search_domain_filter": ["perplexity.ai"],
    }


def test_create_provider_passes_openai_request_settings_from_mode_config() -> None:
    """P23-RS01: OpenAI mode request settings reach OpenAIProvider.config."""
    from types import SimpleNamespace

    from thoth.config import ConfigManager
    from thoth.providers import create_provider

    config = cast(
        ConfigManager,
        SimpleNamespace(data={"providers": {"openai": {"api_key": "sk-test"}}}),
    )
    mode_config: dict[str, Any] = {
        "provider": "openai",
        "model": "gpt-4.1-mini",
        "kind": "immediate",
        "temperature": 0.2,
        "max_tool_calls": 12,
        "system_prompt": "not provider config",
    }

    provider = create_provider("openai", config, mode_config=mode_config)

    assert provider.config["temperature"] == 0.2
    assert provider.config["max_tool_calls"] == 12
    assert "system_prompt" not in provider.config


# ---------------------------------------------------------------------------
# P24 Task 3.1 — [modes.X.openai] namespace migration with backwards-compat
# deprecation. Mirrors P23/Perplexity's [modes.X.perplexity] namespace pattern.
# ---------------------------------------------------------------------------


def test_openai_reads_namespaced_temperature() -> None:
    """OpenAIProvider reads [modes.X.openai].temperature."""
    provider = OpenAIProvider(
        api_key="dummy",
        config={"openai": {"temperature": 0.42}, "kind": "immediate"},
    )
    assert provider._resolve_provider_config_value("temperature", 0.7) == 0.42


def test_openai_reads_flat_temperature_with_deprecation_warning() -> None:
    """Flat top-level temperature still works but emits DeprecationWarning."""
    provider = OpenAIProvider(
        api_key="dummy",
        config={"temperature": 0.42, "kind": "immediate"},
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        resolved = provider._resolve_provider_config_value("temperature", 0.7)

    assert resolved == 0.42
    dep_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert any(
        "namespace" in str(w.message).lower()
        or "flat config" in str(w.message).lower()
        or "modes." in str(w.message)
        for w in dep_warnings
    ), "expected DeprecationWarning advising migration to [modes.X.openai] namespace"


def test_openai_namespaced_overrides_flat_silently() -> None:
    """When both namespaced and flat keys exist, namespaced wins. No deprecation."""
    provider = OpenAIProvider(
        api_key="dummy",
        config={
            "temperature": 0.1,
            "openai": {"temperature": 0.9},
            "kind": "immediate",
        },
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        resolved = provider._resolve_provider_config_value("temperature", 0.7)

    assert resolved == 0.9
    dep_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert not dep_warnings, "DeprecationWarning fired even though user is on the namespace path"


def test_openai_default_when_neither_present() -> None:
    """Returns the default when neither namespaced nor flat key is set."""
    provider = OpenAIProvider(api_key="dummy", config={"kind": "immediate"})
    assert provider._resolve_provider_config_value("temperature", 0.7) == 0.7
    assert provider._resolve_provider_config_value("max_tool_calls", None) is None
