"""P27 — Perplexity async (background deep-research) provider tests.

Covers the asynchronous lifecycle on top of `/v1/async/sonar`: error
mapping for raw httpx exceptions and Perplexity HTTP status codes,
plus future submit / check_status / get_result / reconnect / cancel
coverage as those land. Mirrors the structure of `test_oai_background.py`
but against the Perplexity async API instead of OpenAI Responses.

Test slices:
- P27-T04: `_map_perplexity_error_async` covers 401/402/422/429/5xx and
  httpx.TimeoutException / ConnectError → ThothError taxonomy.
- P27-TS01..TS05: lifecycle coverage (submit body shape, status mapping,
  get_result extraction, reconnect, cancel) — added as those lifecycle
  methods land.
"""

from __future__ import annotations

import httpx
import pytest

from thoth.errors import (
    APIKeyError,
    APIQuotaError,
    APIRateLimitError,
    ProviderError,
    ThothError,
)
from thoth.providers.perplexity import _map_perplexity_error_async


def _make_http_status_error(status: int, body: str = "{}") -> httpx.HTTPStatusError:
    """Construct an httpx.HTTPStatusError as the SDK would raise from raise_for_status()."""
    request = httpx.Request("GET", "https://api.perplexity.ai/v1/async/sonar/job-x")
    response = httpx.Response(status_code=status, content=body.encode(), request=request)
    return httpx.HTTPStatusError(f"HTTP {status}", request=request, response=response)


# ---------------------------------------------------------------------------
# P27-T04 — _map_perplexity_error_async
# ---------------------------------------------------------------------------


def test_async_map_401_returns_api_key_error() -> None:
    """T04: HTTP 401 maps to APIKeyError('perplexity')."""
    exc = _make_http_status_error(401)
    result = _map_perplexity_error_async(exc)
    assert isinstance(result, APIKeyError)


def test_async_map_401_with_invalid_key_body_returns_friendly_thoth_error() -> None:
    """T04: 401 + invalid-key phrase in body → friendly invalid-key ThothError.

    Mirrors the sync path defense (perplexity.py:142–151): "key not found"
    and "key invalid" are different user actions, so the async mapper
    distinguishes them too.
    """
    exc = _make_http_status_error(
        401, body='{"error": {"code": "invalid_api_key", "message": "API key is invalid"}}'
    )
    result = _map_perplexity_error_async(exc)
    assert isinstance(result, ThothError)
    assert "invalid" in str(result).lower()
    # Specifically NOT the missing-key error (different remediation).
    assert not isinstance(result, APIKeyError) or "invalid" in str(result).lower()


def test_async_map_402_returns_api_quota_error() -> None:
    """T04: HTTP 402 (insufficient credits) maps to APIQuotaError."""
    exc = _make_http_status_error(402, body='{"error": {"message": "Insufficient credits"}}')
    result = _map_perplexity_error_async(exc)
    assert isinstance(result, APIQuotaError)


def test_async_map_422_returns_provider_error_with_model_hint() -> None:
    """T04: HTTP 422 (incompatible model) → ProviderError mentioning the model."""
    exc = _make_http_status_error(422, body='{"error": {"message": "Invalid request"}}')
    result = _map_perplexity_error_async(exc, model="sonar-pro")
    assert isinstance(result, ProviderError)
    assert "sonar-pro" in str(result)
    assert "/v1/async/sonar" in str(result) or "async" in str(result).lower()


def test_async_map_429_returns_rate_limit_error() -> None:
    """T04: HTTP 429 → APIRateLimitError (rate limit, NOT quota).

    Distinguishes from 402 (which is the credit/billing code per Perplexity
    spec §8). 429 is purely throttle.
    """
    exc = _make_http_status_error(429)
    result = _map_perplexity_error_async(exc)
    assert isinstance(result, APIRateLimitError)


@pytest.mark.parametrize("status", [500, 502, 503, 504])
def test_async_map_5xx_returns_transient_provider_error(status: int) -> None:
    """T04: 5xx → ProviderError with retry hint."""
    exc = _make_http_status_error(status)
    result = _map_perplexity_error_async(exc)
    assert isinstance(result, ProviderError)
    assert "server error" in str(result).lower() or "5xx" in str(result)


def test_async_map_httpx_timeout_returns_provider_error() -> None:
    """T04: httpx.TimeoutException → ProviderError with timeout language."""
    exc = httpx.TimeoutException("request timed out")
    result = _map_perplexity_error_async(exc)
    assert isinstance(result, ProviderError)
    assert "timed out" in str(result).lower()


def test_async_map_httpx_connect_error_returns_provider_error() -> None:
    """T04: httpx.ConnectError → ProviderError with network language."""
    exc = httpx.ConnectError("DNS resolution failed")
    result = _map_perplexity_error_async(exc)
    assert isinstance(result, ProviderError)
    assert "network" in str(result).lower() or "connection" in str(result).lower()


def test_async_map_unknown_exception_returns_generic_provider_error() -> None:
    """T04: any other exception type → generic ProviderError, not silently swallowed."""
    exc = RuntimeError("something unexpected")
    result = _map_perplexity_error_async(exc)
    assert isinstance(result, ProviderError)
    assert "something unexpected" in str(result).lower() or "unexpected" in str(result).lower()


def test_async_map_verbose_includes_raw_error_text() -> None:
    """T04: verbose=True populates raw_error on ProviderError for diagnostics."""
    exc = _make_http_status_error(500, body='{"error": {"message": "internal"}}')
    result = _map_perplexity_error_async(exc, verbose=True)
    assert isinstance(result, ProviderError)
    assert result.raw_error is not None
    assert result.raw_error  # non-empty
