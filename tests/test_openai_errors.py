"""Tests for typed OpenAI SDK exception mapping in OpenAIProvider.submit.

Follows the `asyncio.run(coro)` sync-wrap pattern from tests/test_vcr_openai.py
(no pytest-asyncio dependency).
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import openai
import pytest

from thoth.__main__ import (
    APIKeyError,
    APIQuotaError,
    APIRateLimitError,
    OpenAIProvider,
    ProviderError,
    ThothError,
    _map_openai_error,
)


def _fake_sdk_error(
    exc_class: type[openai.APIError],
    *,
    message: str = "boom",
    status: int = 400,
    body: Any = None,
) -> openai.APIError:
    """Construct a fake openai SDK exception with minimal httpx.Response."""
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    if exc_class is openai.APITimeoutError:
        return exc_class(request=request)
    if exc_class is openai.APIConnectionError:
        return exc_class(message=message, request=request)
    if exc_class is openai.APIError:
        return exc_class(message=message, request=request, body=body)
    response = httpx.Response(status_code=status, request=request)
    return exc_class(message=message, response=response, body=body)  # ty: ignore[missing-argument,unknown-argument]


def _make_provider() -> OpenAIProvider:
    return OpenAIProvider(api_key="test-key", config={"model": "o3-deep-research"})


def _submit_raises(provider: OpenAIProvider, sdk_exc: BaseException) -> BaseException:
    """Invoke submit with responses.create patched to raise sdk_exc, return mapped exception."""
    with patch.object(provider.client.responses, "create", new=AsyncMock(side_effect=sdk_exc)):
        try:
            asyncio.run(provider.submit("test prompt", mode="default"))
        except BaseException as e:  # noqa: BLE001
            return e
    raise AssertionError("submit did not raise")


class TestMapOpenAIError:
    """Direct unit tests on _map_openai_error."""

    def test_authentication_error_maps_to_api_key_error(self) -> None:
        exc = _fake_sdk_error(openai.AuthenticationError, message="bad key", status=401)
        result = _map_openai_error(exc, model="o3")
        assert isinstance(result, APIKeyError)
        assert "openai API key not found" in result.message

    def test_rate_limit_error_without_quota_marker_maps_to_provider_error(self) -> None:
        exc = _fake_sdk_error(
            openai.RateLimitError, message="slow down", status=429, body={"error": {}}
        )
        result = _map_openai_error(exc, model="o3")
        assert isinstance(result, APIRateLimitError)
        assert not isinstance(result, APIQuotaError)
        assert "rate limit" in result.message.lower()

    def test_rate_limit_error_with_insufficient_quota_maps_to_api_quota_error(
        self,
    ) -> None:
        exc = _fake_sdk_error(
            openai.RateLimitError,
            message="quota",
            status=429,
            body={"error": {"code": "insufficient_quota"}},
        )
        result = _map_openai_error(exc, model="o3")
        assert isinstance(result, APIQuotaError)

    def test_rate_limit_error_with_quota_message_maps_to_api_quota_error(self) -> None:
        exc = _fake_sdk_error(
            openai.RateLimitError,
            message="quota",
            status=429,
            body={
                "error": {
                    "message": "You exceeded your current quota, please check billing.",
                    "type": "insufficient_quota",
                }
            },
        )
        result = _map_openai_error(exc, model="o3")
        assert isinstance(result, APIQuotaError)

    def test_not_found_error_maps_to_provider_error_with_model(self) -> None:
        exc = _fake_sdk_error(openai.NotFoundError, message="no such model", status=404)
        result = _map_openai_error(exc, model="o3-deep-research")
        assert isinstance(result, ProviderError)
        assert "o3-deep-research" in result.message

    def test_bad_request_temperature_keeps_guidance(self) -> None:
        exc = _fake_sdk_error(
            openai.BadRequestError,
            message="Unsupported parameter: 'temperature' for o3-deep-research",
            status=400,
        )
        result = _map_openai_error(exc, model="o3-deep-research")
        assert isinstance(result, ProviderError)
        assert "temperature" in result.message.lower()
        assert "o3-deep-research" in result.message

    def test_bad_request_generic(self) -> None:
        exc = _fake_sdk_error(openai.BadRequestError, message="bad request", status=400)
        result = _map_openai_error(exc, model="o3")
        assert isinstance(result, ProviderError)

    def test_permission_denied_maps_to_provider_error(self) -> None:
        exc = _fake_sdk_error(openai.PermissionDeniedError, message="nope", status=403)
        result = _map_openai_error(exc, model="o3")
        assert isinstance(result, ProviderError)

    def test_internal_server_error_maps_to_provider_error(self) -> None:
        exc = _fake_sdk_error(openai.InternalServerError, message="5xx", status=500)
        result = _map_openai_error(exc, model="o3")
        assert isinstance(result, ProviderError)

    def test_api_connection_error_maps_to_provider_error(self) -> None:
        exc = _fake_sdk_error(openai.APIConnectionError, message="can't connect")
        result = _map_openai_error(exc, model="o3")
        assert isinstance(result, ProviderError)
        assert "connect" in result.message.lower()

    def test_api_timeout_error_maps_to_provider_error_timeout_message(self) -> None:
        exc = _fake_sdk_error(openai.APITimeoutError)
        result = _map_openai_error(exc, model="o3")
        assert isinstance(result, ProviderError)
        assert "timed out" in result.message.lower()

    def test_unknown_exception_falls_through_to_provider_error(self) -> None:
        result = _map_openai_error(Exception("weird"), model="o3")
        assert isinstance(result, ProviderError)
        assert isinstance(result, ThothError)


class TestSubmitRaisesMappedErrors:
    """End-to-end: submit() catches typed SDK errors and raises mapped ThothError."""

    def test_authentication_error_bubbles_as_api_key_error(self) -> None:
        provider = _make_provider()
        exc = _fake_sdk_error(openai.AuthenticationError, message="bad key", status=401)
        mapped = _submit_raises(provider, exc)
        assert isinstance(mapped, APIKeyError)

    def test_timeout_retries_then_maps_to_provider_error(self) -> None:
        provider = _make_provider()
        exc = _fake_sdk_error(openai.APITimeoutError)
        mock = AsyncMock(side_effect=exc)
        with patch.object(provider.client.responses, "create", new=mock):
            with pytest.raises(ProviderError) as info:
                asyncio.run(provider.submit("p", mode="default"))
        assert "timed out" in info.value.message.lower()
        assert mock.call_count == 3, (
            f"expected tenacity to retry 3x on APITimeoutError, got {mock.call_count}"
        )


class TestVCRHappyPathDoesNotInvokeMapper:
    """VCR replay must not hit _map_openai_error on the success path."""

    def test_happy_path_does_not_call_map_openai_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from thoth import __main__ as thoth_main

        def _fail(*a, **kw):
            raise AssertionError("_map_openai_error called on happy path")

        monkeypatch.setattr(thoth_main, "_map_openai_error", _fail)

        provider = _make_provider()

        class _Resp:
            id = "resp_happy"
            status = "in_progress"

        with patch.object(provider.client.responses, "create", new=AsyncMock(return_value=_Resp())):
            job_id = asyncio.run(provider.submit("p", mode="default"))
        assert job_id == "resp_happy"


def test_openai_constants_use_suffix_naming() -> None:
    """OpenAI module-level constants follow the cross-provider suffix convention."""
    from thoth.providers import openai as op

    assert hasattr(op, "_DIRECT_SDK_KEYS_OPENAI"), (
        "_DIRECT_SDK_KEYS_OPENAI must exist (introduced for cross-provider parity)"
    )
    assert hasattr(op, "_PROVIDER_NAME_OPENAI"), (
        "_PROVIDER_NAME_OPENAI must exist (introduced for cross-provider parity)"
    )
    assert op._PROVIDER_NAME_OPENAI == "openai"
    # The Responses API kwargs the immediate path passes:
    assert "temperature" in op._DIRECT_SDK_KEYS_OPENAI
    assert "max_tool_calls" in op._DIRECT_SDK_KEYS_OPENAI
    assert "tools" in op._DIRECT_SDK_KEYS_OPENAI


def test_openai_sources_block_escapes_html_in_title() -> None:
    """OpenAI's ## Sources block must use md_link_title to escape HTML in titles."""
    from types import SimpleNamespace

    from thoth.providers.openai import OpenAIProvider

    provider = OpenAIProvider(api_key="dummy", config={})
    fake_response = SimpleNamespace(
        output=[
            SimpleNamespace(
                type="message",
                status="completed",
                phase="final_answer",
                content=[
                    SimpleNamespace(
                        type="output_text",
                        text="Answer body.",
                        annotations=[
                            {"url": "https://example.com", "title": "<script>alert(1)</script>"},
                        ],
                    )
                ],
            )
        ],
    )
    provider.jobs["test"] = {"response": fake_response, "background": False, "created_at": 0}

    rendered = asyncio.run(provider.get_result("test"))
    assert "<script>" not in rendered, (
        "raw HTML in title leaked into output (md_link_title not applied)"
    )


def test_openai_sources_block_blocks_javascript_scheme_in_url() -> None:
    """OpenAI's ## Sources block must use md_link_url to neutralize javascript: URLs."""
    from types import SimpleNamespace

    from thoth.providers.openai import OpenAIProvider

    provider = OpenAIProvider(api_key="dummy", config={})
    fake_response = SimpleNamespace(
        output=[
            SimpleNamespace(
                type="message",
                status="completed",
                phase="final_answer",
                content=[
                    SimpleNamespace(
                        type="output_text",
                        text="Answer.",
                        annotations=[
                            {"url": "javascript:alert(1)", "title": "Click me"},
                        ],
                    )
                ],
            )
        ],
    )
    provider.jobs["test"] = {"response": fake_response, "background": False, "created_at": 0}

    rendered = asyncio.run(provider.get_result("test"))
    assert "javascript:" not in rendered, (
        "javascript: scheme not neutralized (md_link_url not applied)"
    )


def test_openai_invalid_key_thotherror_has_exit_code_2() -> None:
    """OpenAI's invalid-key ThothError must set exit_code=2 to match Perplexity.

    The shared `_invalid_key_thotherror` helper sets exit_code=2 so that
    callers can distinguish 'configured but rejected' (rotate the key) from
    other ThothError exits. OpenAI previously drifted by leaving the default
    exit_code=1; this test pins the parity contract.
    """
    # 'Incorrect API key' phrase triggers the invalid-key (vs missing-key) branch.
    exc = _fake_sdk_error(
        openai.AuthenticationError,
        message="Incorrect API key provided",
        status=401,
        body={"error": {"code": "invalid_api_key", "message": "Incorrect API key provided"}},
    )
    mapped = _map_openai_error(exc, model="gpt-4o", verbose=False)
    assert isinstance(mapped, ThothError)
    assert not isinstance(mapped, APIKeyError), (
        "A configured-but-invalid key should not report 'not found'"
    )
    assert mapped.exit_code == 2, (
        f"expected exit_code=2 (Perplexity parity), got {mapped.exit_code}"
    )
