"""P33 provider config passthrough — provider-level, mode-level, future-provider.

Complements `tests/extended/test_provider_config_passthrough.py` (which lives
behind the `extended` marker and covers MODE-level passthrough). These tests
run in the default suite and cover:

1. Provider-level config (`[providers.openai]`, `[providers.perplexity]`)
   reaches the provider's runtime `self.config`.
2. Mode-level overrides (`[modes.x]`) are merged into provider_config via
   `_apply_mode_provider_config`.
3. The provider-namespace nested table (`[modes.x.perplexity]` or
   `[providers.perplexity.perplexity]`) deep-merges into the provider's
   `self.config[<provider_name>]` slot, which Perplexity's runtime
   forwards to `extra_body`.
4. Forward-compatibility: an unknown SDK key set inside the
   `perplexity` namespace flows through without schema rejection (the
   namespace is intentionally permissive `dict[str, Any]`).
5. Future-provider flexibility: `GeminiConfig` (placeholder) accepts
   the same ProviderConfigBase fields, ready for P28 to wire runtime.

The tests use `unittest.mock.AsyncMock` to capture request kwargs without
hitting any live API. Following the repo convention, async tests are
sync-wrapped with `asyncio.run(coro)`.

See:
  - `src/thoth/providers/__init__.py:create_provider` — provider_config
    construction
  - `src/thoth/providers/__init__.py:_apply_mode_provider_config` —
    mode-level overlay
  - `src/thoth/providers/openai.py:OpenAIProvider.submit` — config
    consumption
  - `src/thoth/providers/perplexity.py:_build_request_params /
    _build_extra_body` — config consumption
"""

from __future__ import annotations

import asyncio
import types
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

# -------------------- helpers --------------------


def _fake_config_manager(providers: dict[str, dict[str, Any]]) -> Any:
    """Build a stand-in for `ConfigManager` exposing only `data["providers"]`.

    Mirrors the helper used by `tests/extended/test_provider_config_passthrough.py`
    so the tests stay self-contained and don't pull in `ConfigManager.load_all_layers`.
    """
    return types.SimpleNamespace(data={"providers": providers})


# -------------------- OpenAI provider-level passthrough --------------------


def test_openai_provider_level_organization_reaches_runtime() -> None:
    """`[providers.openai] organization = "..."` lands in `OpenAIProvider.config`.

    `create_provider` copies `config.data['providers']['openai']` into the
    constructor, so any modeled OpenAIConfig field (including
    `organization`) reaches `self.config`.
    """
    from thoth.providers import create_provider

    cfg = _fake_config_manager(
        {"openai": {"api_key": "sk-test", "organization": "org-acme", "model": "gpt-4o-mini"}}
    )
    provider = create_provider("openai", cfg, mode_config={"kind": "immediate"})

    assert provider.config["organization"] == "org-acme"
    assert provider.config["model"] == "gpt-4o-mini"


def test_openai_provider_level_max_tool_calls_reaches_request() -> None:
    """`[providers.openai] max_tool_calls = 50` ends up in request_params."""
    from thoth.providers import create_provider

    cfg = _fake_config_manager({"openai": {"api_key": "sk-test", "max_tool_calls": 50}})
    provider = create_provider(
        "openai",
        cfg,
        mode_config={"kind": "immediate", "model": "gpt-4o-mini"},
    )

    captured: dict[str, Any] = {}

    async def fake_create(**kwargs: Any) -> Any:
        captured.update(kwargs)
        resp = MagicMock()
        resp.id = "resp_test"
        return resp

    cast(Any, provider).client = types.SimpleNamespace(
        responses=types.SimpleNamespace(create=AsyncMock(side_effect=fake_create))
    )

    asyncio.run(cast(Any, provider).submit("hi", mode="default"))

    assert captured.get("max_tool_calls") == 50


def test_openai_mode_level_overrides_provider_level() -> None:
    """Mode-level `temperature` overrides `[providers.openai] temperature`."""
    from thoth.providers import create_provider

    cfg = _fake_config_manager({"openai": {"api_key": "sk-test", "temperature": 0.1}})
    provider = create_provider(
        "openai",
        cfg,
        mode_config={"kind": "immediate", "model": "gpt-4o-mini", "temperature": 0.9},
    )

    captured: dict[str, Any] = {}

    async def fake_create(**kwargs: Any) -> Any:
        captured.update(kwargs)
        resp = MagicMock()
        resp.id = "resp_test"
        return resp

    cast(Any, provider).client = types.SimpleNamespace(
        responses=types.SimpleNamespace(create=AsyncMock(side_effect=fake_create))
    )

    asyncio.run(cast(Any, provider).submit("hi", mode="default"))

    assert captured.get("temperature") == 0.9


# -------------------- Perplexity provider-level passthrough --------------------


def test_perplexity_provider_level_top_p_reaches_request() -> None:
    """`[providers.perplexity] top_p = 0.9` flows through `_DIRECT_SDK_KEYS`."""
    from thoth.providers import create_provider

    cfg = _fake_config_manager({"perplexity": {"api_key": "pplx-test", "top_p": 0.9}})
    provider = create_provider(
        "perplexity",
        cfg,
        mode_config={"kind": "immediate", "model": "sonar"},
    )

    captured: dict[str, Any] = {}

    async def fake_create(**kwargs: Any) -> Any:
        captured.update(kwargs)
        message = types.SimpleNamespace(content="ok")
        choice = types.SimpleNamespace(message=message)
        return types.SimpleNamespace(id="resp_test", choices=[choice])

    cast(Any, provider).client = types.SimpleNamespace(
        chat=types.SimpleNamespace(
            completions=types.SimpleNamespace(create=AsyncMock(side_effect=fake_create))
        )
    )

    asyncio.run(cast(Any, provider).submit("hi", mode="default"))

    assert captured.get("top_p") == 0.9


def test_perplexity_provider_level_nested_namespace_reaches_extra_body() -> None:
    """`[providers.perplexity.perplexity.web_search_options]` content
    forwards through `_build_extra_body` into the SDK's `extra_body`.
    """
    from thoth.providers import create_provider

    cfg = _fake_config_manager(
        {
            "perplexity": {
                "api_key": "pplx-test",
                "perplexity": {
                    "stream_mode": "full",
                    "web_search_options": {"search_context_size": "high"},
                },
            }
        }
    )
    provider = create_provider(
        "perplexity",
        cfg,
        mode_config={"kind": "immediate", "model": "sonar"},
    )

    captured: dict[str, Any] = {}

    async def fake_create(**kwargs: Any) -> Any:
        captured.update(kwargs)
        message = types.SimpleNamespace(content="ok")
        choice = types.SimpleNamespace(message=message)
        return types.SimpleNamespace(id="resp_test", choices=[choice])

    cast(Any, provider).client = types.SimpleNamespace(
        chat=types.SimpleNamespace(
            completions=types.SimpleNamespace(create=AsyncMock(side_effect=fake_create))
        )
    )

    asyncio.run(cast(Any, provider).submit("hi", mode="default"))

    extra_body = captured.get("extra_body") or {}
    assert extra_body.get("stream_mode") == "full"
    assert extra_body.get("web_search_options", {}).get("search_context_size") == "high"


def test_perplexity_mode_namespace_deep_merges_with_provider_namespace() -> None:
    """Mode-level `[modes.x.perplexity]` deep-merges with provider-level
    `[providers.perplexity.perplexity]` — mode wins on key collisions.
    """
    from thoth.providers import create_provider

    cfg = _fake_config_manager(
        {
            "perplexity": {
                "api_key": "pplx-test",
                "perplexity": {
                    "stream_mode": "concise",  # overridden by mode
                    "web_search_options": {"search_context_size": "low"},  # overridden
                },
            }
        }
    )
    provider = create_provider(
        "perplexity",
        cfg,
        mode_config={
            "kind": "immediate",
            "model": "sonar",
            "perplexity": {
                "stream_mode": "full",
                "web_search_options": {"search_context_size": "high"},
            },
        },
    )

    captured: dict[str, Any] = {}

    async def fake_create(**kwargs: Any) -> Any:
        captured.update(kwargs)
        message = types.SimpleNamespace(content="ok")
        choice = types.SimpleNamespace(message=message)
        return types.SimpleNamespace(id="resp_test", choices=[choice])

    cast(Any, provider).client = types.SimpleNamespace(
        chat=types.SimpleNamespace(
            completions=types.SimpleNamespace(create=AsyncMock(side_effect=fake_create))
        )
    )

    asyncio.run(cast(Any, provider).submit("hi", mode="default"))

    extra_body = captured.get("extra_body") or {}
    # Mode-level overrides won
    assert extra_body.get("stream_mode") == "full"
    assert extra_body.get("web_search_options", {}).get("search_context_size") == "high"


# -------------------- Forward-compatibility tests --------------------


def test_perplexity_namespace_accepts_unknown_sdk_keys() -> None:
    """A new Perplexity SDK key (not modeled in our schema) under the
    `perplexity` namespace must validate and reach the runtime.

    Schema treats `perplexity: dict[str, Any]` as permissive specifically
    so SDK additions don't require schema updates.
    """
    from thoth.config_schema import ConfigSchema, PerplexityConfig

    # Schema acceptance
    PerplexityConfig(
        api_key="${PERPLEXITY_API_KEY}",
        perplexity={"future_sdk_option": True, "another_one": [1, 2, 3]},
    )

    # Validation through full UserConfigFile too
    report = ConfigSchema.validate(
        {
            "version": "2.0",
            "providers": {
                "perplexity": {
                    "api_key": "pplx-test",
                    "perplexity": {"future_sdk_option": "value"},
                }
            },
        },
        layer="user",
    )
    assert report.warnings == ()


def test_unknown_top_level_provider_field_warns() -> None:
    """A typo at the well-known provider-config tier still produces a
    warning — schema discipline is preserved for the modeled surface."""
    from thoth.config_schema import ConfigSchema

    report = ConfigSchema.validate(
        {
            "version": "2.0",
            "providers": {"openai": {"api_key": "sk-test", "bogus_field_xyz": 0.5}},
        },
        layer="user",
    )
    typo_warnings = [w for w in report.warnings if "bogus_field_xyz" in w.path]
    assert typo_warnings, f"expected typo warning; got {report.warnings}"


def test_gemini_placeholder_accepts_provider_config_base_fields() -> None:
    """Future-provider flexibility: `GeminiConfig` is a P28 placeholder
    that already accepts the full ProviderConfigBase surface. When P28
    lands, runtime hookup is the only delta — schema is ready.
    """
    from thoth.config_schema import GeminiConfig

    cfg = GeminiConfig(
        api_key="${GEMINI_API_KEY}",
        model="gemini-2.0-flash-exp",
        temperature=0.4,
        max_tokens=4000,
        timeout=30.0,
        base_url="https://generativelanguage.googleapis.com",
    )
    assert cfg.api_key == "${GEMINI_API_KEY}"
    assert cfg.model == "gemini-2.0-flash-exp"


def test_mode_provider_namespace_validates_for_each_provider() -> None:
    """`[modes.<name>.openai]`, `[modes.<name>.perplexity]`, and
    `[modes.<name>.gemini]` all pass schema validation — each is
    `dict[str, Any]` so SDK options can vary independently per provider.
    """
    from thoth.config_schema import ConfigSchema

    report = ConfigSchema.validate(
        {
            "version": "2.0",
            "modes": {
                "thinking": {
                    "openai": {"max_tool_calls": 30, "code_interpreter": False},
                    "perplexity": {"stream_mode": "full"},
                    "gemini": {"safety_settings": ["HIGH"]},
                }
            },
        },
        layer="user",
    )
    assert report.warnings == (), f"unexpected warnings: {report.warnings}"
