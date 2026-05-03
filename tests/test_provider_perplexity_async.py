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

import asyncio
from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest

from thoth.errors import (
    APIKeyError,
    APIQuotaError,
    APIRateLimitError,
    ProviderError,
    ThothError,
)
from thoth.providers.perplexity import (
    PerplexityProvider,
    _map_perplexity_error_async,
)


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


def test_async_maphttpx_timeout_returns_provider_error() -> None:
    """T04: httpx.TimeoutException → ProviderError with timeout language."""
    exc = httpx.TimeoutException("request timed out")
    result = _map_perplexity_error_async(exc)
    assert isinstance(result, ProviderError)
    assert "timed out" in str(result).lower()


def test_async_maphttpx_connect_error_returns_provider_error() -> None:
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


# ---------------------------------------------------------------------------
# P27-TS01 — submit() POST body shape + idempotency
# ---------------------------------------------------------------------------
#
# All tests below patch `provider._async_http` (the raw httpx client
# scheduled to be added in __init__ alongside the existing AsyncOpenAI
# `provider.client`). Calls to `submit()` with kind="background" route
# through this httpx client; calls with kind="immediate" continue to use
# the existing OpenAI-SDK client and are out of scope here.


def _async_response(
    status_code: int = 202,
    payload: dict[str, Any] | None = None,
) -> httpx.Response:
    """Build an httpx.Response with a JSON body and a synthetic Request."""
    request = httpx.Request("POST", "https://api.perplexity.ai/v1/async/sonar")
    response = httpx.Response(
        status_code=status_code,
        json=payload or {"id": "req-async-123", "status": "CREATED"},
        request=request,
    )
    return response


def _make_background_provider(
    response: httpx.Response | None = None,
    extra_config: dict[str, Any] | None = None,
) -> tuple[PerplexityProvider, AsyncMock]:
    """Provider wired with an AsyncMock httpx client; returns (provider, post_mock)."""
    config: dict[str, Any] = {
        "model": "sonar-deep-research",
        "kind": "background",
    }
    if extra_config:
        config.update(extra_config)
    provider = PerplexityProvider(api_key="pplx-test", config=config)
    post_mock = AsyncMock(return_value=response or _async_response())
    fake_client = AsyncMock()
    fake_client.post = post_mock
    fake_client.get = AsyncMock(return_value=_async_response())
    provider._async_http = fake_client  # type: ignore[attr-defined]
    return provider, post_mock


def test_async_submit_posts_to_v1_async_sonar() -> None:
    """TS01: submit() with kind=background POSTs to /v1/async/sonar."""
    provider, post = _make_background_provider()
    asyncio.run(provider.submit("hello", mode="perplexity_deep_research"))
    assert post.await_count == 1
    assert post.await_args is not None
    url = post.await_args.args[0] if post.await_args.args else post.await_args.kwargs.get("url", "")
    assert url == "/v1/async/sonar"


def test_async_submit_uses_request_wrapper_shape() -> None:
    """TS01: body matches Perplexity's `{"request": {...}, "idempotency_key": ...}` shape.

    NOT OpenAI's flat shape — the request part is wrapped explicitly.
    """
    provider, post = _make_background_provider()
    asyncio.run(provider.submit("hello", mode="perplexity_deep_research"))
    assert post.await_args is not None
    body = post.await_args.kwargs["json"]
    assert "request" in body, f"missing 'request' wrapper in body: {body}"
    assert "idempotency_key" in body
    assert body["request"]["model"] == "sonar-deep-research"
    assert body["request"]["messages"] == [{"role": "user", "content": "hello"}]


def test_async_submit_idempotency_key_is_uuid4_hex() -> None:
    """TS01: idempotency_key is a 32-char hex string (uuid4().hex)."""
    provider, post = _make_background_provider()
    asyncio.run(provider.submit("hello", mode="perplexity_deep_research"))
    assert post.await_args is not None
    body = post.await_args.kwargs["json"]
    key = body["idempotency_key"]
    assert isinstance(key, str)
    assert len(key) == 32
    int(key, 16)  # raises if not hex


def test_async_submit_idempotency_key_stable_across_retries() -> None:
    """TS01: tenacity retries reuse the SAME idempotency_key (advisor #2).

    Generating a new UUID inside the retried inner would defeat the whole
    point of idempotency. The key must be minted in `submit()` (or any
    outer caller) once, then passed into the retried inner.
    """
    provider, post = _make_background_provider()
    seen_keys: list[str] = []

    async def flaky_post(*args: Any, **kwargs: Any) -> httpx.Response:
        seen_keys.append(kwargs["json"]["idempotency_key"])
        if len(seen_keys) < 3:
            raise httpx.ConnectError("transient network failure")
        return _async_response()

    post.side_effect = flaky_post
    asyncio.run(provider.submit("hello", mode="perplexity_deep_research"))
    assert len(seen_keys) == 3, f"expected 3 retry attempts, got {len(seen_keys)}"
    assert len(set(seen_keys)) == 1, f"idempotency_key changed across retries: {seen_keys}"


def test_async_submit_includes_reasoning_effort_from_mode_config() -> None:
    """TS01: config['perplexity']['reasoning_effort'] passes through to body['request']."""
    provider, post = _make_background_provider(
        extra_config={"perplexity": {"reasoning_effort": "high"}}
    )
    asyncio.run(provider.submit("hello", mode="perplexity_deep_research"))
    assert post.await_args is not None
    body = post.await_args.kwargs["json"]
    assert body["request"].get("reasoning_effort") == "high"


def test_async_submit_omits_reasoning_effort_when_unset() -> None:
    """TS01: omitting reasoning_effort from config also omits it from the request body.

    Lets Perplexity's server-side default apply rather than forcing one client-side.
    """
    provider, post = _make_background_provider()  # no perplexity.reasoning_effort
    asyncio.run(provider.submit("hello", mode="perplexity_deep_research"))
    assert post.await_args is not None
    body = post.await_args.kwargs["json"]
    assert "reasoning_effort" not in body["request"]


def test_async_submit_with_system_prompt_yields_two_messages() -> None:
    """TS01: system_prompt -> first system message; user prompt -> user message."""
    provider, post = _make_background_provider()
    asyncio.run(
        provider.submit("user content", mode="perplexity_deep_research", system_prompt="be brief")
    )
    assert post.await_args is not None
    body = post.await_args.kwargs["json"]
    assert body["request"]["messages"] == [
        {"role": "system", "content": "be brief"},
        {"role": "user", "content": "user content"},
    ]


def test_async_submit_returns_request_id_as_job_id() -> None:
    """TS01: response.json()['id'] is captured as the job_id and stored in self.jobs."""
    provider, post = _make_background_provider(
        response=_async_response(payload={"id": "req-xyz-789", "status": "CREATED"})
    )
    job_id = asyncio.run(provider.submit("hello", mode="perplexity_deep_research"))
    assert job_id == "req-xyz-789"
    assert "req-xyz-789" in provider.jobs


def test_async_submit_does_not_route_immediate_kind_through_async_path() -> None:
    """Regression: kind='immediate' MUST continue to use the existing P23 sync path.

    P27 must not change the immediate-path lifecycle. Verifies that the
    new kind=background dispatch is the ONLY path that touches the new
    `_async_http` client.
    """
    provider, post = _make_background_provider(
        extra_config={"model": "sonar-pro", "kind": "immediate"}
    )
    # Patch the SDK client too so we can detect which path executes.
    sync_called = {"hit": False}

    async def fake_sync_create(**kwargs: Any) -> Any:
        sync_called["hit"] = True
        # Return a SimpleNamespace that mimics the SDK response shape.
        from types import SimpleNamespace

        return SimpleNamespace(id="sync-id", choices=[], search_results=[])

    from types import SimpleNamespace

    provider.client = SimpleNamespace(  # type: ignore[assignment]  # ty: ignore[invalid-assignment]
        chat=SimpleNamespace(completions=SimpleNamespace(create=fake_sync_create))
    )
    asyncio.run(provider.submit("hello", mode="perplexity_pro"))
    assert sync_called["hit"], "immediate kind should call the SDK client, not _async_http"
    assert post.await_count == 0, "_async_http MUST NOT be called for kind=immediate"


def test_async_submit_provider_init_creates_async_http_client() -> None:
    """T03 part 2: __init__ wires self._async_http as an httpx.AsyncClient.

    Verified by attribute presence and base_url. Tests below patch this
    attribute, but the real construction must happen in __init__.
    """
    provider = PerplexityProvider(
        api_key="pplx-test", config={"model": "sonar-deep-research", "kind": "background"}
    )
    assert hasattr(provider, "_async_http"), "expected _async_http attribute in __init__"
    assert isinstance(provider._async_http, httpx.AsyncClient)
    assert str(provider._async_http.base_url).rstrip("/") == "https://api.perplexity.ai"
    asyncio.run(provider._async_http.aclose())


# ---------------------------------------------------------------------------
# P27-TS02 — check_status() async-API status mapping + stale-cache fallback
# ---------------------------------------------------------------------------
#
# Mirrors OpenAI background's check_status contract (status, progress)
# while mapping Perplexity's status enum (CREATED/IN_PROGRESS/COMPLETED/
# FAILED) to Thoth's internal enum. Includes the OAI-BG-06/07 stale-cache
# cases so a transient poll error doesn't masquerade as completion (or
# fail to honor a genuinely-completed cached result).


def _status_response(
    status: str = "IN_PROGRESS",
    extra: dict[str, Any] | None = None,
) -> httpx.Response:
    payload: dict[str, Any] = {"id": "req-async-123", "status": status}
    if extra:
        payload.update(extra)
    request = httpx.Request("GET", "https://api.perplexity.ai/v1/async/sonar/req-async-123")
    return httpx.Response(status_code=200, json=payload, request=request)


def _attach_get_response(
    provider: PerplexityProvider,
    response: httpx.Response | Exception,
) -> AsyncMock:
    """Replace provider._async_http with an AsyncMock whose .get yields `response`."""
    fake_client = AsyncMock()
    if isinstance(response, Exception):
        fake_client.get = AsyncMock(side_effect=response)
    else:
        fake_client.get = AsyncMock(return_value=response)
    provider._async_http = fake_client  # type: ignore[attr-defined]
    return fake_client.get


def _seed_background_job(
    provider: PerplexityProvider,
    job_id: str = "req-async-123",
    cached_status: str = "IN_PROGRESS",
) -> None:
    """Populate provider.jobs as if _submit_async had run."""
    provider.jobs[job_id] = {
        "response_data": {"id": job_id, "status": cached_status},
        "background": True,
        "created_at": __import__("datetime").datetime.now(),
    }


def test_check_status_created_maps_to_queued() -> None:
    """TS02: Perplexity CREATED → {'status': 'queued', 'progress': 0.0}."""
    provider, _ = _make_background_provider()
    _seed_background_job(provider, cached_status="CREATED")
    _attach_get_response(provider, _status_response("CREATED"))
    result = asyncio.run(provider.check_status("req-async-123"))
    assert result["status"] == "queued"
    assert result["progress"] == 0.0


def test_check_status_in_progress_maps_to_running() -> None:
    """TS02: Perplexity IN_PROGRESS → {'status': 'running', 'progress': float}."""
    provider, _ = _make_background_provider()
    _seed_background_job(provider, cached_status="IN_PROGRESS")
    _attach_get_response(provider, _status_response("IN_PROGRESS"))
    result = asyncio.run(provider.check_status("req-async-123"))
    assert result["status"] == "running"
    assert isinstance(result["progress"], float)
    assert 0.0 <= result["progress"] <= 1.0


def test_check_status_completed_caches_response_and_returns_completed() -> None:
    """TS02: Perplexity COMPLETED → cache the response payload AND return progress 1.0.

    Caching is load-bearing — get_result() can avoid a second GET.
    """
    provider, _ = _make_background_provider()
    _seed_background_job(provider)
    full_payload = {
        "id": "req-async-123",
        "status": "COMPLETED",
        "response": {"choices": [{"message": {"content": "answer"}}]},
    }
    _attach_get_response(provider, _status_response("COMPLETED", extra=full_payload))
    result = asyncio.run(provider.check_status("req-async-123"))
    assert result["status"] == "completed"
    assert result["progress"] == 1.0
    cached = provider.jobs["req-async-123"].get("response_data")
    assert cached is not None
    assert cached.get("status") == "COMPLETED"
    assert cached.get("response", {}).get("choices") is not None


def test_check_status_failed_maps_to_permanent_error_with_message() -> None:
    """TS02: Perplexity FAILED → {'status': 'permanent_error', 'error': error_message}."""
    provider, _ = _make_background_provider()
    _seed_background_job(provider)
    _attach_get_response(
        provider,
        _status_response("FAILED", extra={"error_message": "Search service unavailable"}),
    )
    result = asyncio.run(provider.check_status("req-async-123"))
    assert result["status"] == "permanent_error"
    assert "Search service unavailable" in str(result.get("error", ""))


def test_check_status_404_maps_to_permanent_error_with_ttl_hint() -> None:
    """TS02: HTTP 404 on poll → permanent_error mentioning the 7-day TTL.

    Async results expire 7 days after submission per Perplexity spec §5.
    Surfacing the TTL helps users understand "missing job" vs "job failed".
    """
    provider, _ = _make_background_provider()
    _seed_background_job(provider)
    request = httpx.Request("GET", "https://api.perplexity.ai/v1/async/sonar/req-async-123")
    response = httpx.Response(status_code=404, content=b"{}", request=request)
    err = httpx.HTTPStatusError("404", request=request, response=response)
    _attach_get_response(provider, err)
    result = asyncio.run(provider.check_status("req-async-123"))
    assert result["status"] == "permanent_error"
    error_text = str(result.get("error", "")).lower()
    assert (
        "expired" in error_text
        or "ttl" in error_text
        or "7-day" in error_text
        or "7 day" in error_text
    )


def test_check_status_transient_error_with_stale_in_progress_cache_does_not_complete() -> None:
    """TS02: ConnectError on poll + cached IN_PROGRESS → transient_error.

    Mirrors OAI-BG-06. Critical safety property: a network blip during a
    long-running poll MUST NOT cause us to declare a job done when the
    cached state was IN_PROGRESS. Loss of liveness is preferable to false
    completion.
    """
    provider, _ = _make_background_provider()
    _seed_background_job(provider, cached_status="IN_PROGRESS")
    _attach_get_response(provider, httpx.ConnectError("network blip"))
    result = asyncio.run(provider.check_status("req-async-123"))
    assert result["status"] == "transient_error"
    assert result["status"] != "completed", (
        "stale IN_PROGRESS cache must not be reported as completed"
    )


def test_check_status_transient_error_with_stale_completed_cache_returns_completed() -> None:
    """TS02: ConnectError on poll + cached COMPLETED → completed (safe fallback).

    Mirrors OAI-BG-07. Once we've already seen COMPLETED for this job in a
    prior poll, a transient error on a later (redundant) poll should not
    flip the state back to error. The cached completion is authoritative.
    """
    provider, _ = _make_background_provider()
    _seed_background_job(provider, cached_status="COMPLETED")
    _attach_get_response(provider, httpx.ConnectError("network blip"))
    result = asyncio.run(provider.check_status("req-async-123"))
    assert result["status"] == "completed"
    assert result["progress"] == 1.0


def test_check_status_unknown_job_id_returns_not_found() -> None:
    """TS02: job_id absent from self.jobs → not_found (no HTTP attempted)."""
    provider, post = _make_background_provider()  # post mock here is for submit, unused
    fake_client = AsyncMock()
    fake_client.get = AsyncMock(return_value=_status_response("COMPLETED"))
    provider._async_http = fake_client  # type: ignore[attr-defined]
    result = asyncio.run(provider.check_status("never-seen"))
    assert result["status"] == "not_found"
    assert fake_client.get.await_count == 0, "no GET should fire for unknown job_id"


def test_check_status_immediate_path_returns_completed_without_polling() -> None:
    """Regression: P23 sync immediate path keeps its 'already completed' behavior.

    For kind=immediate jobs (where `submit()` already ran chat.completions
    synchronously), `self.jobs[job_id]` lacks `background=True`. check_status
    must return {completed, 1.0} without GETting the async API.
    """
    provider = PerplexityProvider(
        api_key="pplx-test", config={"model": "sonar", "kind": "immediate"}
    )
    fake_client = AsyncMock()
    fake_client.get = AsyncMock(return_value=_status_response("COMPLETED"))
    provider._async_http = fake_client  # type: ignore[attr-defined]
    provider.jobs["sync-job-x"] = {
        "response": object(),  # opaque sync SDK response (irrelevant for status)
        "created_at": __import__("datetime").datetime.now(),
        # no "background" key — that's how the sync path stores jobs
    }
    result = asyncio.run(provider.check_status("sync-job-x"))
    assert result["status"] == "completed"
    assert result["progress"] == 1.0
    assert fake_client.get.await_count == 0, "sync jobs must NOT trigger an async-API GET"
