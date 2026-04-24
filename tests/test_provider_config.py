"""OpenAI provider config → request payload tests.

Migrated from thoth_test GAP01-01…03.
"""

from __future__ import annotations

import asyncio
import types
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
        api_key="dummy", config={"model": "o3-deep-research", "max_tool_calls": 80}
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
        api_key="dummy", config={"model": "o3-deep-research", "code_interpreter": False}
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
    tool_types = [t.get("type") for t in tools]
    assert "code_interpreter" in tool_types, (
        f"code_interpreter must be included by default, got tools: {tool_types}"
    )
    code_interp_tool = next(t for t in tools if t.get("type") == "code_interpreter")
    assert code_interp_tool.get("container") == {"type": "auto"}, (
        f"code_interpreter tool must carry container={{type: auto}} "
        f"(OpenAI API requirement), got: {code_interp_tool}"
    )
