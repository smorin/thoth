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


def _make_openai_exc(cls_name: str, status: int = 400) -> BaseException:
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
        return cls(message=msg, request=request, body=None)
    response = httpx.Response(status_code=status, request=request)
    return cls(message=msg, response=response, body=None)


@pytest.mark.parametrize(
    ("exc_cls", "expected_thoth"),
    [
        ("AuthenticationError", "APIKeyError"),
        ("RateLimitError", "APIQuotaError"),
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


def test_map_perplexity_error_falls_back_for_unknown_exception() -> None:
    """TS03: an unrelated exception still maps to a ProviderError (no crash)."""
    from thoth.errors import ProviderError
    from thoth.providers.perplexity import _map_perplexity_error

    mapped = _map_perplexity_error(RuntimeError("unrelated"), model="sonar")
    assert isinstance(mapped, ProviderError)


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
