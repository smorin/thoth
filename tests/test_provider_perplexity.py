"""P23 — Perplexity provider tests.

TS02: built-in modes + request-construction shape.
TS03: error mapping + retry policy (added later).
TS04: stream() chunk translation (added later).
TS07: kind-mismatch defense (added later).
"""

from __future__ import annotations

import asyncio
import types
from typing import Any, cast

import pytest

from thoth.providers.perplexity import PerplexityProvider


def _stub_response(content: str = "Test answer", search_results=None) -> Any:
    msg = types.SimpleNamespace(content=content)
    choice = types.SimpleNamespace(message=msg)
    return types.SimpleNamespace(
        id="pplx-test-id",
        choices=[choice],
        search_results=search_results or [],
    )


def _stub_client(captured: dict[str, Any], response: Any = None) -> Any:
    """Fake AsyncOpenAI client whose chat.completions.create captures kwargs."""

    async def fake_create(**kwargs: Any) -> Any:
        captured.update(kwargs)
        return response if response is not None else _stub_response()

    return types.SimpleNamespace(
        chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=fake_create))
    )


# ---------------------------------------------------------------------------
# TS02 — built-in modes
# ---------------------------------------------------------------------------


def test_perplexity_quick_builtin_mode_present() -> None:
    """TS02: BUILTIN_MODES['perplexity_quick'] -> sonar/immediate/low/full."""
    from thoth.config import BUILTIN_MODES

    mode = BUILTIN_MODES.get("perplexity_quick")
    assert mode is not None
    assert mode["provider"] == "perplexity"
    assert mode["model"] == "sonar"
    assert mode["kind"] == "immediate"
    perp = cast(dict[str, Any], mode.get("perplexity") or {})
    assert perp.get("web_search_options", {}).get("search_context_size") == "low"
    assert perp.get("stream_mode") == "full"


def test_perplexity_pro_builtin_mode_present() -> None:
    """TS02: BUILTIN_MODES['perplexity_pro'] -> sonar-pro/immediate/high/full."""
    from thoth.config import BUILTIN_MODES

    mode = BUILTIN_MODES.get("perplexity_pro")
    assert mode is not None
    assert mode["provider"] == "perplexity"
    assert mode["model"] == "sonar-pro"
    assert mode["kind"] == "immediate"
    perp = cast(dict[str, Any], mode.get("perplexity") or {})
    assert perp.get("web_search_options", {}).get("search_context_size") == "high"
    assert perp.get("stream_mode") == "full"


def test_perplexity_reasoning_builtin_mode_present() -> None:
    """TS02: BUILTIN_MODES['perplexity_reasoning'] -> sonar-reasoning-pro/medium/concise."""
    from thoth.config import BUILTIN_MODES

    mode = BUILTIN_MODES.get("perplexity_reasoning")
    assert mode is not None
    assert mode["provider"] == "perplexity"
    assert mode["model"] == "sonar-reasoning-pro"
    assert mode["kind"] == "immediate"
    perp = cast(dict[str, Any], mode.get("perplexity") or {})
    assert perp.get("web_search_options", {}).get("search_context_size") == "medium"
    assert perp.get("stream_mode") == "concise"


def test_perplexity_deep_research_builtin_mode_present() -> None:
    """P27-TS01: BUILTIN_MODES['perplexity_deep_research'] -> sonar-deep-research/background/high.

    Locked at P27 kickoff: reasoning_effort = "high" (~$1.32/query). The mode
    targets the async API (POST /v1/async/sonar). `kind: "background"` is
    required so the runner routes to the polling lifecycle, not the immediate
    `chat.completions` path that P23's other modes use.
    """
    from thoth.config import BUILTIN_MODES

    mode = BUILTIN_MODES.get("perplexity_deep_research")
    assert mode is not None, "expected built-in mode 'perplexity_deep_research'"
    assert mode["provider"] == "perplexity"
    assert mode["model"] == "sonar-deep-research"
    assert mode["kind"] == "background"
    perp = cast(dict[str, Any], mode.get("perplexity") or {})
    assert perp.get("reasoning_effort") == "high"


# ---------------------------------------------------------------------------
# TS02 — request construction
# ---------------------------------------------------------------------------


def test_perplexity_request_messages_include_system_then_user() -> None:
    """TS02: system_prompt -> first system message; user prompt -> user message."""
    captured: dict[str, Any] = {}
    provider = PerplexityProvider(
        api_key="pplx-test", config={"model": "sonar", "kind": "immediate"}
    )
    provider.client = _stub_client(captured)
    asyncio.run(provider.submit("user prompt", mode="perplexity_quick", system_prompt="be brief"))
    assert captured["messages"] == [
        {"role": "system", "content": "be brief"},
        {"role": "user", "content": "user prompt"},
    ]


def test_perplexity_request_no_system_prompt_skips_system_message() -> None:
    """TS02: when system_prompt is None, only the user message is sent."""
    captured: dict[str, Any] = {}
    provider = PerplexityProvider(
        api_key="pplx-test", config={"model": "sonar", "kind": "immediate"}
    )
    provider.client = _stub_client(captured)
    asyncio.run(provider.submit("hello", mode="perplexity_quick"))
    assert captured["messages"] == [{"role": "user", "content": "hello"}]


def test_perplexity_request_uses_configured_model() -> None:
    """TS02: model from config is a direct SDK kwarg."""
    captured: dict[str, Any] = {}
    provider = PerplexityProvider(
        api_key="pplx-test",
        config={"model": "sonar-pro", "kind": "immediate"},
    )
    provider.client = _stub_client(captured)
    asyncio.run(provider.submit("hi", mode="perplexity_pro"))
    assert captured["model"] == "sonar-pro"


def test_perplexity_request_extra_body_uses_perplexity_namespace() -> None:
    """TS02: keys nested under config['perplexity'] flow through to extra_body."""
    captured: dict[str, Any] = {}
    config = {
        "model": "sonar",
        "kind": "immediate",
        "perplexity": {
            "web_search_options": {"search_context_size": "high"},
            "search_recency_filter": "week",
            "return_related_questions": True,
        },
    }
    provider = PerplexityProvider(api_key="pplx-test", config=config)
    provider.client = _stub_client(captured)
    asyncio.run(provider.submit("hi", mode="perplexity_quick"))
    extra_body = captured.get("extra_body", {})
    assert extra_body.get("web_search_options") == {"search_context_size": "high"}
    assert extra_body.get("search_recency_filter") == "week"
    assert extra_body.get("return_related_questions") is True


def test_perplexity_request_default_search_context_size_is_medium() -> None:
    """TS02: fallback search_context_size is 'medium' when not configured."""
    captured: dict[str, Any] = {}
    provider = PerplexityProvider(
        api_key="pplx-test", config={"model": "sonar", "kind": "immediate"}
    )
    provider.client = _stub_client(captured)
    asyncio.run(provider.submit("hi", mode="perplexity_quick"))
    extra_body = captured.get("extra_body", {})
    assert extra_body.get("web_search_options", {}).get("search_context_size") == "medium"


def test_perplexity_request_default_stream_mode_is_concise() -> None:
    """TS02: fallback stream_mode is 'concise' when not configured."""
    captured: dict[str, Any] = {}
    provider = PerplexityProvider(
        api_key="pplx-test", config={"model": "sonar", "kind": "immediate"}
    )
    provider.client = _stub_client(captured)
    asyncio.run(provider.submit("hi", mode="perplexity_quick"))
    extra_body = captured.get("extra_body", {})
    assert extra_body.get("stream_mode") == "concise"


def test_perplexity_request_passes_direct_sdk_kwargs() -> None:
    """TS02: max_tokens / temperature / top_p / stop / response_format pass directly."""
    captured: dict[str, Any] = {}
    config = {
        "model": "sonar",
        "kind": "immediate",
        "max_tokens": 512,
        "temperature": 0.4,
        "top_p": 0.9,
        "stop": ["END"],
        "response_format": {"type": "text"},
    }
    provider = PerplexityProvider(api_key="pplx-test", config=config)
    provider.client = _stub_client(captured)
    asyncio.run(provider.submit("hi", mode="perplexity_quick"))
    assert captured["max_tokens"] == 512
    assert captured["temperature"] == 0.4
    assert captured["top_p"] == 0.9
    assert captured["stop"] == ["END"]
    assert captured["response_format"] == {"type": "text"}


# ---------------------------------------------------------------------------
# TS03 — error mapping + retry policy
# ---------------------------------------------------------------------------


def _make_openai_exc(cls_name: str, status: int = 400, body: Any = None) -> BaseException:
    """Build a fake openai.* SDK exception with a real httpx.Request anchor."""
    import httpx
    import openai

    cls = getattr(openai, cls_name)
    msg = f"fake-{cls_name}"
    request = httpx.Request("POST", "https://api.perplexity.ai/chat/completions")
    if cls is openai.APITimeoutError:
        return cls(request=request)
    if cls is openai.APIConnectionError:
        return cls(message=msg, request=request)
    if cls is openai.APIError:
        return cls(message=msg, request=request, body=body)
    response = httpx.Response(status_code=status, request=request)
    return cls(message=msg, response=response, body=body)


@pytest.mark.parametrize(
    ("exc_cls", "expected_thoth"),
    [
        ("AuthenticationError", "APIKeyError"),
        ("RateLimitError", "APIRateLimitError"),
        ("BadRequestError", "ProviderError"),
        ("PermissionDeniedError", "ProviderError"),
        ("InternalServerError", "ProviderError"),
        ("APITimeoutError", "ProviderError"),
        ("APIConnectionError", "ProviderError"),
        ("APIError", "ProviderError"),
    ],
)
def test_map_perplexity_error_table(exc_cls: str, expected_thoth: str) -> None:
    """TS03: each OpenAI-SDK exception maps to the expected ThothError subclass."""
    from thoth import errors as thoth_errors
    from thoth.providers.perplexity import _map_perplexity_error

    exc = _make_openai_exc(exc_cls)
    mapped = _map_perplexity_error(exc, model="sonar")
    expected_cls = getattr(thoth_errors, expected_thoth)
    assert isinstance(mapped, expected_cls), (
        f"{exc_cls} should map to {expected_thoth}, got {type(mapped).__name__}"
    )


def test_map_perplexity_error_uses_perplexity_provider_name() -> None:
    """TS03: error message includes 'perplexity' (provider name)."""
    from thoth.providers.perplexity import _map_perplexity_error

    exc = _make_openai_exc("AuthenticationError")
    mapped = _map_perplexity_error(exc, model="sonar")
    assert "perplexity" in str(mapped).lower()


def test_map_perplexity_error_invalid_key_distinguished_from_missing() -> None:
    """TS03: AuthenticationError with 'invalid api key' body maps to ThothError with
    'invalid' message (not the misleading 'not found' message for absent keys)."""
    from thoth.errors import APIKeyError, ThothError
    from thoth.providers.perplexity import _map_perplexity_error

    exc = _make_openai_exc(
        "AuthenticationError",
        status=401,
        body={"error": {"message": "Invalid API key provided"}},
    )
    mapped = _map_perplexity_error(exc, model="sonar")
    # Must be a ThothError but NOT the missing-key APIKeyError subclass
    assert isinstance(mapped, ThothError)
    assert not isinstance(mapped, APIKeyError), (
        "A configured-but-invalid key should not report 'not found'"
    )
    assert "invalid" in mapped.message.lower()
    assert "perplexity" in mapped.message.lower()
    assert mapped.exit_code == 2


def test_map_perplexity_error_invalid_key_incorrect_phrase() -> None:
    """TS03: 'incorrect api key' phrase also triggers the invalid-key branch."""
    from thoth.errors import APIKeyError, ThothError
    from thoth.providers.perplexity import _map_perplexity_error

    exc = _make_openai_exc(
        "AuthenticationError",
        status=401,
        body={"error": {"message": "Incorrect API key provided"}},
    )
    mapped = _map_perplexity_error(exc, model="sonar")
    assert isinstance(mapped, ThothError)
    assert not isinstance(mapped, APIKeyError)
    assert mapped.exit_code == 2


def test_map_perplexity_error_absent_key_still_maps_to_api_key_error() -> None:
    """TS03: AuthenticationError with no body (absent key) still maps to APIKeyError."""
    from thoth.errors import APIKeyError
    from thoth.providers.perplexity import _map_perplexity_error

    # Default _make_openai_exc has generic message, no 'invalid api key' phrase
    exc = _make_openai_exc("AuthenticationError")
    mapped = _map_perplexity_error(exc, model="sonar")
    assert isinstance(mapped, APIKeyError)


def test_map_perplexity_error_falls_back_for_unknown_exception() -> None:
    """TS03: an unrelated exception still maps to a ProviderError (no crash)."""
    from thoth.errors import ProviderError
    from thoth.providers.perplexity import _map_perplexity_error

    mapped = _map_perplexity_error(RuntimeError("unrelated"), model="sonar")
    assert isinstance(mapped, ProviderError)


def test_map_perplexity_rate_limit_quota_message_maps_to_quota() -> None:
    """P23-RS04: quota/credit exhaustion remains APIQuotaError, distinct from rate limit."""
    from thoth.errors import APIQuotaError
    from thoth.providers.perplexity import _map_perplexity_error

    exc = _make_openai_exc(
        "RateLimitError",
        status=429,
        body={"error": {"message": "Your credits are exhausted; add billing credits."}},
    )

    mapped = _map_perplexity_error(exc, model="sonar")

    assert isinstance(mapped, APIQuotaError)


def test_perplexity_submit_retries_on_transient_then_succeeds() -> None:
    """TS03: APITimeoutError retries; eventual success returns job_id."""
    captured_calls: list[int] = []

    async def flaky_create(**kwargs: Any) -> Any:
        captured_calls.append(1)
        if len(captured_calls) < 3:
            raise _make_openai_exc("APITimeoutError")
        return _stub_response()

    provider = PerplexityProvider(
        api_key="pplx-test", config={"model": "sonar", "kind": "immediate"}
    )
    provider.client = cast(
        Any,
        types.SimpleNamespace(
            chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=flaky_create))
        ),
    )
    job_id = asyncio.run(provider.submit("hi", mode="perplexity_quick"))
    assert job_id == "pplx-test-id"
    assert len(captured_calls) == 3, "should retry twice before success"


def test_perplexity_submit_does_not_retry_authentication_error() -> None:
    """TS03: AuthenticationError is permanent — no retry."""
    captured_calls: list[int] = []

    async def fake_create(**kwargs: Any) -> Any:
        captured_calls.append(1)
        raise _make_openai_exc("AuthenticationError")

    provider = PerplexityProvider(
        api_key="pplx-test", config={"model": "sonar", "kind": "immediate"}
    )
    provider.client = cast(
        Any,
        types.SimpleNamespace(
            chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=fake_create))
        ),
    )
    from thoth.errors import APIKeyError

    with pytest.raises(APIKeyError):
        asyncio.run(provider.submit("hi", mode="perplexity_quick"))
    assert len(captured_calls) == 1, "auth error must not retry"


# ---------------------------------------------------------------------------
# TS04 — stream() chunk translation
# ---------------------------------------------------------------------------


def _delta_chunk(delta_content: str | None = None, **extra: Any) -> Any:
    delta = types.SimpleNamespace(content=delta_content)
    choice = types.SimpleNamespace(delta=delta)
    return types.SimpleNamespace(choices=[choice], **extra)


class _FakeStream:
    """Async-iterator stand-in for AsyncOpenAI's streaming response."""

    def __init__(self, chunks: list[Any]) -> None:
        self._chunks = chunks

    def __aiter__(self) -> _FakeStream:
        self._iter = iter(self._chunks)
        return self

    async def __anext__(self) -> Any:
        try:
            return next(self._iter)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


class _FailingStream:
    """Async iterator that raises after yielding any configured chunks."""

    def __init__(self, chunks: list[Any], exc: BaseException) -> None:
        self._chunks = chunks
        self._exc = exc

    def __aiter__(self) -> _FailingStream:
        self._iter = iter(self._chunks)
        return self

    async def __anext__(self) -> Any:
        try:
            return next(self._iter)
        except StopIteration:
            raise self._exc


def _stub_stream_client(chunks: list[Any], captured: dict[str, Any] | None = None) -> Any:
    captured = captured if captured is not None else {}

    async def fake_create(**kwargs: Any) -> Any:
        captured.update(kwargs)
        return _FakeStream(chunks)

    return cast(
        Any,
        types.SimpleNamespace(
            chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=fake_create))
        ),
    )


async def _drain(provider: PerplexityProvider, **kwargs: Any) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    async for ev in provider.stream(**kwargs):
        out.append((ev.kind, ev.text))
    return out


async def _drain_events(provider: PerplexityProvider, **kwargs: Any) -> list[Any]:
    out: list[Any] = []
    async for ev in provider.stream(**kwargs):
        out.append(ev)
    return out


def test_perplexity_stream_yields_text_deltas() -> None:
    """TS04: each delta.content -> StreamEvent('text', delta)."""
    chunks = [
        _delta_chunk("Hello"),
        _delta_chunk(" world"),
        _delta_chunk("!"),
    ]
    provider = PerplexityProvider(
        api_key="pplx-test", config={"model": "sonar", "kind": "immediate"}
    )
    provider.client = _stub_stream_client(chunks)
    events = asyncio.run(_drain(provider, prompt="hi", mode="perplexity_quick"))
    assert ("text", "Hello") in events
    assert ("text", " world") in events
    assert ("text", "!") in events


def test_perplexity_stream_cumulative_content_guard() -> None:
    """TS04: when the API sends cumulative content, only the new delta is emitted."""
    chunks = [
        _delta_chunk("Hello"),
        _delta_chunk("Hello world"),
        _delta_chunk("Hello world!"),
    ]
    provider = PerplexityProvider(
        api_key="pplx-test", config={"model": "sonar", "kind": "immediate"}
    )
    provider.client = _stub_stream_client(chunks)
    events = asyncio.run(_drain(provider, prompt="hi", mode="perplexity_quick"))
    text_events = [text for kind, text in events if kind == "text"]
    assert "".join(text_events) == "Hello world!"


def test_perplexity_stream_emits_terminal_done_event() -> None:
    """TS04: stream always ends with StreamEvent('done', '')."""
    chunks = [_delta_chunk("done?")]
    provider = PerplexityProvider(
        api_key="pplx-test", config={"model": "sonar", "kind": "immediate"}
    )
    provider.client = _stub_stream_client(chunks)
    events = asyncio.run(_drain(provider, prompt="hi", mode="perplexity_quick"))
    assert events[-1] == ("done", "")


def test_perplexity_stream_emits_structured_citations_from_search_results() -> None:
    """P23-RS06: final search_results emit structured citation data, not title|url."""
    final_chunk = _delta_chunk(
        None,
        search_results=[
            {"title": "T1 | pipe", "url": "https://a.example"},
            {"title": "T2", "url": "https://b.example"},
        ],
    )
    chunks = [_delta_chunk("hi"), final_chunk]
    provider = PerplexityProvider(
        api_key="pplx-test", config={"model": "sonar", "kind": "immediate"}
    )
    provider.client = _stub_stream_client(chunks)
    events = asyncio.run(_drain_events(provider, prompt="hi", mode="perplexity_quick"))
    citations = [event.citation for event in events if event.kind == "citation"]
    assert citations[0].title == "T1 | pipe"
    assert citations[0].url == "https://a.example"
    assert citations[1].title == "T2"
    assert citations[1].url == "https://b.example"


def test_perplexity_stream_extracts_think_block_as_reasoning() -> None:
    """TS04: <think>...</think> on sonar-reasoning-pro -> reasoning events; stripped from text."""
    chunks = [
        _delta_chunk("<think>internal monologue</think>"),
        _delta_chunk("answer"),
    ]
    provider = PerplexityProvider(
        api_key="pplx-test",
        config={"model": "sonar-reasoning-pro", "kind": "immediate"},
    )
    provider.client = _stub_stream_client(chunks)
    events = asyncio.run(_drain(provider, prompt="hi", mode="perplexity_reasoning"))
    reasoning_chunks = [text for kind, text in events if kind == "reasoning"]
    text_chunks = [text for kind, text in events if kind == "text"]
    assert any("internal monologue" in r for r in reasoning_chunks)
    assert "answer" in "".join(text_chunks)
    assert "<think>" not in "".join(text_chunks)


def test_perplexity_stream_extracts_think_block_split_across_chunks() -> None:
    """P23-RS05: split <think> tags are parsed statefully across chunks."""
    chunks = [
        _delta_chunk("pre <th"),
        _delta_chunk("ink>internal "),
        _delta_chunk("monologue</"),
        _delta_chunk("think> answer"),
    ]
    provider = PerplexityProvider(
        api_key="pplx-test",
        config={"model": "sonar-reasoning-pro", "kind": "immediate"},
    )
    provider.client = _stub_stream_client(chunks)

    events = asyncio.run(_drain(provider, prompt="hi", mode="perplexity_reasoning"))

    reasoning_chunks = [text for kind, text in events if kind == "reasoning"]
    text_chunks = [text for kind, text in events if kind == "text"]
    assert "".join(reasoning_chunks) == "internal monologue"
    assert "".join(text_chunks) == "pre  answer"
    assert "<think>" not in "".join(text_chunks)
    assert "</think>" not in "".join(text_chunks)


def test_perplexity_stream_tolerates_missing_think_block() -> None:
    """TS04: sonar-reasoning-pro without <think> still emits text events; no error."""
    chunks = [_delta_chunk("plain answer")]
    provider = PerplexityProvider(
        api_key="pplx-test",
        config={"model": "sonar-reasoning-pro", "kind": "immediate"},
    )
    provider.client = _stub_stream_client(chunks)
    events = asyncio.run(_drain(provider, prompt="hi", mode="perplexity_reasoning"))
    text_chunks = [text for kind, text in events if kind == "text"]
    assert "plain answer" in "".join(text_chunks)


def test_perplexity_stream_passes_stream_mode_full() -> None:
    """TS04: config['perplexity']['stream_mode'] = 'full' passes through to extra_body."""
    captured: dict[str, Any] = {}
    chunks = [_delta_chunk("hi")]

    async def fake_create(**kwargs: Any) -> Any:
        captured.update(kwargs)
        return _FakeStream(chunks)

    provider = PerplexityProvider(
        api_key="pplx-test",
        config={
            "model": "sonar",
            "kind": "immediate",
            "perplexity": {"stream_mode": "full"},
        },
    )
    provider.client = cast(
        Any,
        types.SimpleNamespace(
            chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=fake_create))
        ),
    )
    asyncio.run(_drain(provider, prompt="hi", mode="perplexity_quick"))
    assert captured["stream"] is True
    assert captured["extra_body"]["stream_mode"] == "full"


def test_perplexity_stream_passes_stream_mode_concise_default() -> None:
    """TS04: when stream_mode unset, default 'concise' propagates to extra_body."""
    captured: dict[str, Any] = {}
    chunks = [_delta_chunk("hi")]

    async def fake_create(**kwargs: Any) -> Any:
        captured.update(kwargs)
        return _FakeStream(chunks)

    provider = PerplexityProvider(
        api_key="pplx-test", config={"model": "sonar", "kind": "immediate"}
    )
    provider.client = cast(
        Any,
        types.SimpleNamespace(
            chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=fake_create))
        ),
    )
    asyncio.run(_drain(provider, prompt="hi", mode="perplexity_quick"))
    assert captured["extra_body"]["stream_mode"] == "concise"


def test_perplexity_stream_maps_iteration_errors() -> None:
    """P23-RS05: SDK errors raised mid-stream map through Perplexity taxonomy."""
    from thoth.errors import APIRateLimitError

    captured: dict[str, Any] = {}

    async def fake_create(**kwargs: Any) -> Any:
        captured.update(kwargs)
        return _FailingStream([_delta_chunk("partial")], _make_openai_exc("RateLimitError", 429))

    provider = PerplexityProvider(
        api_key="pplx-test", config={"model": "sonar", "kind": "immediate"}
    )
    provider.client = cast(
        Any,
        types.SimpleNamespace(
            chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=fake_create))
        ),
    )

    with pytest.raises(APIRateLimitError):
        asyncio.run(_drain(provider, prompt="hi", mode="perplexity_quick"))


# ---------------------------------------------------------------------------
# TS07 — kind-mismatch defense (sonar-deep-research is P27 territory)
# ---------------------------------------------------------------------------


def test_perplexity_rejects_sonar_deep_research_on_immediate() -> None:
    """TS07: model='sonar-deep-research' + kind='immediate' raises before any HTTP call."""
    from thoth.errors import ModeKindMismatchError

    captured: dict[str, Any] = {}

    async def fake_create(**kwargs: Any) -> Any:
        captured.update(kwargs)
        captured.setdefault("called", []).append(1)
        return _stub_response()

    provider = PerplexityProvider(
        api_key="pplx-test",
        config={"model": "sonar-deep-research", "kind": "immediate"},
    )
    provider.client = cast(
        Any,
        types.SimpleNamespace(
            chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=fake_create))
        ),
    )
    with pytest.raises(ModeKindMismatchError):
        asyncio.run(provider.submit("hi", mode="perplexity_deep"))
    assert "called" not in captured, "no HTTP call should have been made"


def test_perplexity_rejects_sonar_deep_research_on_stream() -> None:
    """TS07: stream() also raises before opening the HTTP request."""
    from thoth.errors import ModeKindMismatchError

    captured: dict[str, Any] = {}

    async def fake_create(**kwargs: Any) -> Any:
        captured.setdefault("called", []).append(1)
        return _FakeStream([_delta_chunk("x")])

    provider = PerplexityProvider(
        api_key="pplx-test",
        config={"model": "sonar-deep-research", "kind": "immediate"},
    )
    provider.client = cast(
        Any,
        types.SimpleNamespace(
            chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=fake_create))
        ),
    )

    async def _consume() -> None:
        async for _ in provider.stream("hi", mode="perplexity_deep"):
            pass

    with pytest.raises(ModeKindMismatchError):
        asyncio.run(_consume())
    assert "called" not in captured, "no HTTP call should have been made"


def test_perplexity_allows_plain_models_on_immediate() -> None:
    """TS07: regular Sonar models on immediate kind do NOT raise."""
    captured: dict[str, Any] = {}
    provider = PerplexityProvider(
        api_key="pplx-test", config={"model": "sonar-pro", "kind": "immediate"}
    )
    provider.client = _stub_client(captured)
    job_id = asyncio.run(provider.submit("hi", mode="perplexity_pro"))
    assert job_id  # no exception


# ---------------------------------------------------------------------------
# P27-TS06 — reverse-direction kind-mismatch defense
# ---------------------------------------------------------------------------
#
# Perplexity's `/v1/async/sonar` endpoint hard-rejects non-deep-research
# models with HTTP 422. The defense raises ModeKindMismatchError pre-HTTP
# instead, so users see a config-edit suggestion rather than a confusing
# upstream error mid-run. Mirrors P23's TS07 (immediate + DR-model) but on
# the opposite axis: background + non-DR-model.
#
# Forward-compat: any future `sonar-deep-research-*` model passes via the
# substring rule in `is_background_model()` (config.py:200), so we don't
# need a code change to support new DR models.


@pytest.mark.parametrize("bad_model", ["sonar", "sonar-pro", "sonar-reasoning-pro"])
def test_perplexity_rejects_background_on_non_deep_research(bad_model: str) -> None:
    """P27-TS06: kind='background' on a non-DR model raises before any HTTP call."""
    from thoth.errors import ModeKindMismatchError

    provider = PerplexityProvider(
        api_key="pplx-test", config={"model": bad_model, "kind": "background"}
    )
    with pytest.raises(ModeKindMismatchError):
        asyncio.run(provider.submit("hi", mode="some_misconfigured_mode"))


def test_perplexity_allows_sonar_deep_research_on_background() -> None:
    """P27-TS06: model='sonar-deep-research' + kind='background' is legal (no raise).

    The validation must let this through — it's the canonical happy path for
    the new async lifecycle.
    """
    provider = PerplexityProvider(
        api_key="pplx-test",
        config={"model": "sonar-deep-research", "kind": "background"},
    )
    # Calling the validator directly avoids tripping the (not-yet-implemented)
    # async submit path; we only assert no exception is raised here.
    provider._validate_kind_for_model("perplexity_deep_research")


# ---------------------------------------------------------------------------
# TS08 — implementation status flip + user-facing surface
# ---------------------------------------------------------------------------


def test_perplexity_is_implemented_returns_true() -> None:
    """TS08: PerplexityProvider.is_implemented() flips to True after P23 lands."""
    provider = PerplexityProvider(api_key="pplx-test")
    assert provider.is_implemented() is True


def test_perplexity_list_models_returns_supported_sync_models() -> None:
    """TS08: list_models() returns sonar / sonar-pro / sonar-reasoning-pro."""
    provider = PerplexityProvider(api_key="pplx-test")
    ids = {m["id"] for m in asyncio.run(provider.list_models())}
    assert {"sonar", "sonar-pro", "sonar-reasoning-pro"}.issubset(ids)
    # sonar-deep-research is P27's domain; it must NOT appear in P23's supported list.
    assert "sonar-deep-research" not in ids


def test_perplexity_provider_description_drops_not_implemented() -> None:
    """TS08: provider description text in commands.py + interactive.py
    no longer claims Perplexity is unimplemented after P23.

    Asserts at module-source level: the 'not implemented' marker is gone
    from the perplexity-description rows that drive `providers list` output
    and the interactive provider menu.
    """
    from pathlib import Path

    src_root = Path(__file__).resolve().parent.parent / "src" / "thoth"
    for filename in ("commands.py", "interactive.py"):
        text = (src_root / filename).read_text()
        # Find perplexity-description lines and verify none say "(not implemented)".
        for line in text.splitlines():
            if "perplexity" not in line.lower() or "Perplexity" not in line:
                continue
            if "(not implemented)" in line:
                raise AssertionError(f"stale 'not implemented' copy in {filename}: {line!r}")
