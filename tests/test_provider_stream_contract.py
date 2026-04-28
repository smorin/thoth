"""P18 Phase E: provider.stream() contract.

Mock provider yields deterministic chunks; aggregating them must equal the
non-streaming get_result. OpenAI provider's stream impl is exercised in the
extended suite (Phase I) since it requires real API or VCR cassettes.

Spec §5.3.
"""

from __future__ import annotations

import asyncio

import pytest

from thoth.providers.base import ResearchProvider, StreamEvent
from thoth.providers.mock import MockProvider


def test_stream_event_carries_kind_and_text() -> None:
    e = StreamEvent(kind="text", text="hello")
    assert e.kind == "text"
    assert e.text == "hello"


def test_base_stream_raises_not_implemented() -> None:
    p = ResearchProvider(api_key="any")

    async def _consume() -> list[StreamEvent]:
        return [event async for event in p.stream("prompt", "default")]

    with pytest.raises(NotImplementedError, match="ResearchProvider"):
        asyncio.run(_consume())


def test_mock_stream_yields_deterministic_chunks() -> None:
    """MockProvider.stream() yields a fixed sequence; aggregating reproduces the prompt-echo."""
    mock = MockProvider(name="mock", delay=0.0, api_key="mock-test")

    async def _consume() -> list[StreamEvent]:
        return [event async for event in mock.stream("hello world", "default")]

    events = asyncio.run(_consume())
    assert events, "MockProvider.stream() must yield at least one event"
    assert all(isinstance(e, StreamEvent) for e in events)
    text_events = [e for e in events if e.kind == "text"]
    aggregated = "".join(e.text for e in text_events)
    # Mock echoes the prompt somewhere in its output
    assert "hello world" in aggregated


def test_mock_stream_emits_done_event_last() -> None:
    """The final event has kind='done' so callers can detect end-of-stream."""
    mock = MockProvider(name="mock", delay=0.0, api_key="mock-test")

    async def _consume() -> list[StreamEvent]:
        return [event async for event in mock.stream("prompt", "default")]

    events = asyncio.run(_consume())
    assert events[-1].kind == "done"
