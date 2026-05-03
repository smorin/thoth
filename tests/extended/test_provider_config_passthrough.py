"""Extended contract guards for mode-level provider request passthrough.

These do not hit live APIs; they live with the extended provider tests because
the contract guards provider-specific request variables that can drift against
real providers.
"""

from __future__ import annotations

import asyncio
import types
from typing import Any, cast

import pytest

pytestmark = pytest.mark.extended


def test_ext_oai_mode_request_settings_reach_request_payload() -> None:
    """P23-RS07: OpenAI mode-level request settings reach Responses API kwargs."""
    from thoth.config import ConfigManager
    from thoth.providers import create_provider

    config = cast(
        ConfigManager,
        types.SimpleNamespace(data={"providers": {"openai": {"api_key": "sk-test"}}}),
    )
    mode_config: dict[str, Any] = {
        "provider": "openai",
        "model": "gpt-4.1-mini",
        "kind": "immediate",
        "temperature": 0.2,
    }
    provider = create_provider("openai", config, mode_config=mode_config)
    provider_any = cast(Any, provider)
    captured: dict[str, Any] = {}

    async def fake_create(**kwargs: Any) -> Any:
        captured.update(kwargs)
        return types.SimpleNamespace(id="resp-openai-passthrough")

    provider_any.client = cast(
        Any,
        types.SimpleNamespace(responses=types.SimpleNamespace(create=fake_create)),
    )

    asyncio.run(provider_any.submit("hi", mode="openai_passthrough"))

    assert captured["model"] == "gpt-4.1-mini"
    assert captured["temperature"] == 0.2


def test_ext_pplx_mode_provider_namespace_reaches_extra_body() -> None:
    """P23-RS07: Perplexity nested mode namespace reaches extra_body."""
    from thoth.config import ConfigManager
    from thoth.providers import create_provider

    config = cast(
        ConfigManager,
        types.SimpleNamespace(data={"providers": {"perplexity": {"api_key": "pplx-test"}}}),
    )
    mode_config: dict[str, Any] = {
        "provider": "perplexity",
        "model": "sonar",
        "kind": "immediate",
        "perplexity": {
            "stream_mode": "full",
            "web_search_options": {"search_context_size": "low"},
        },
    }
    provider = create_provider("perplexity", config, mode_config=mode_config)
    provider_any = cast(Any, provider)
    captured: dict[str, Any] = {}

    async def fake_create(**kwargs: Any) -> Any:
        captured.update(kwargs)
        message = types.SimpleNamespace(content="pplx ok")
        choice = types.SimpleNamespace(message=message)
        return types.SimpleNamespace(id="resp-pplx-passthrough", choices=[choice])

    provider_any.client = cast(
        Any,
        types.SimpleNamespace(
            chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=fake_create))
        ),
    )

    asyncio.run(provider_any.submit("hi", mode="pplx_passthrough"))

    assert captured["model"] == "sonar"
    assert captured["extra_body"]["stream_mode"] == "full"
    assert captured["extra_body"]["web_search_options"]["search_context_size"] == "low"
