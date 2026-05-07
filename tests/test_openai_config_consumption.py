"""P33-TS09: OpenAI runtime-consumption regression.

The schema-only acceptance tests (TS07) prove the schema *accepts* fields
like `providers.openai.temperature`. TS09 proves those fields actually
reach `OpenAIProvider.submit` / the request builder when set in config.

If a modeled OpenAI field is NOT consumed today, P33 must either wire it
or downgrade it to schema-only and remove the runtime claim.

Async test pattern: this repo uses `asyncio.run(coro)` to sync-wrap async
tests (see `tests/test_oai_background.py`), NOT `@pytest.mark.asyncio`.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock


def test_provider_temperature_reaches_request_builder(monkeypatch) -> None:
    """`[providers.openai] temperature = 0.2` for a non-`o*` model must
    appear in the request_params passed to `client.responses.create`."""
    from thoth.providers.openai import OpenAIProvider

    captured: dict[str, Any] = {}

    async def fake_create(**kwargs):
        captured.update(kwargs)
        resp = MagicMock()
        resp.id = "resp_test"
        resp.status = "completed"
        return resp

    config = {
        "model": "gpt-4o-mini",
        "temperature": 0.2,
        "kind": "immediate",
    }
    provider = OpenAIProvider(api_key="sk-test", config=config)
    monkeypatch.setattr(
        provider.client.responses,
        "create",
        AsyncMock(side_effect=fake_create),
    )

    asyncio.run(provider.submit(prompt="hello", mode="default", system_prompt=None))

    assert "temperature" in captured, (
        f"temperature not in request_params; saw keys {list(captured.keys())}. "
        f"P33 schema models providers.openai.temperature; either wire it through "
        f"or remove the runtime claim and downgrade TS07 to schema-only."
    )
    assert captured["temperature"] == 0.2


def test_profile_overlay_system_prompt_reaches_submit(monkeypatch, tmp_path) -> None:
    """A profile-overlaid `[profiles.fast.modes.thinking] system_prompt = "..."`
    must reach `OpenAIProvider.submit`'s `system_prompt` argument."""
    from thoth.config import ConfigManager
    from thoth.providers.openai import OpenAIProvider

    cfg = tmp_path / "thoth.config.toml"
    cfg.write_text(
        "\n".join(
            [
                'version = "2.0"',
                "[general]",
                'default_profile = "fast"',
                "[profiles.fast.modes.thinking]",
                'system_prompt = "Profile-overlaid prompt"',
                'kind = "immediate"',
                'provider = "openai"',
                'model = "gpt-4o-mini"',
            ]
        )
    )

    mgr = ConfigManager(config_path=cfg)
    mgr.load_all_layers()

    mode_cfg = mgr.get_mode_config("thinking")
    assert mode_cfg.get("system_prompt") == "Profile-overlaid prompt", (
        f"profile overlay failed to reach merged mode config: {mode_cfg!r}"
    )

    captured: dict[str, Any] = {}

    async def fake_create(**kwargs):
        captured["kwargs"] = kwargs
        resp = MagicMock()
        resp.id = "resp_test"
        resp.status = "completed"
        return resp

    provider = OpenAIProvider(api_key="sk-test", config=mode_cfg)
    monkeypatch.setattr(
        provider.client.responses,
        "create",
        AsyncMock(side_effect=fake_create),
    )

    asyncio.run(
        provider.submit(
            prompt="hello",
            mode="thinking",
            system_prompt=mode_cfg.get("system_prompt"),
        )
    )

    inputs = captured["kwargs"]["input"]
    developer_msgs = [m for m in inputs if m.get("role") == "developer"]
    assert developer_msgs, "no developer message produced for system_prompt"
    text = developer_msgs[0]["content"][0]["text"]
    assert text == "Profile-overlaid prompt"
