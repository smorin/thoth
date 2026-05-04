"""Unit tests for the Gemini synchronous chat provider (P24)."""

from __future__ import annotations


def test_gemini_module_exists() -> None:
    """The Gemini provider module is importable."""
    from thoth.providers import gemini  # noqa: F401


def test_gemini_constants_use_suffix_naming() -> None:
    """Gemini module-level constants follow the cross-provider suffix convention."""
    from thoth.providers import gemini

    assert hasattr(gemini, "_DIRECT_SDK_KEYS_GEMINI")
    assert hasattr(gemini, "_PROVIDER_NAME_GEMINI")
    assert gemini._PROVIDER_NAME_GEMINI == "gemini"
    # Sample membership for some load-bearing keys
    assert "temperature" in gemini._DIRECT_SDK_KEYS_GEMINI
    assert "thinking_budget" in gemini._DIRECT_SDK_KEYS_GEMINI


def test_gemini_provider_class_exists_and_extends_research_provider() -> None:
    """GeminiProvider class extends ResearchProvider."""
    from thoth.providers.base import ResearchProvider
    from thoth.providers.gemini import GeminiProvider

    assert issubclass(GeminiProvider, ResearchProvider)


def test_gemini_provider_default_model_is_flash_lite() -> None:
    """GeminiProvider defaults to gemini-2.5-flash-lite when no model configured."""
    from thoth.providers.gemini import GeminiProvider

    provider = GeminiProvider(api_key="dummy", config={})
    assert provider.model == "gemini-2.5-flash-lite"


def test_gemini_provider_is_implemented() -> None:
    """is_implemented() returns True (explicit, not inherited)."""
    from thoth.providers.gemini import GeminiProvider

    provider = GeminiProvider(api_key="dummy", config={})
    assert provider.is_implemented() is True
    assert provider.implementation_status() is None


def test_gemini_built_in_modes_registered() -> None:
    """BUILTIN_MODES contains the three Gemini modes."""
    from thoth.config import BUILTIN_MODES

    assert "gemini_quick" in BUILTIN_MODES
    assert "gemini_pro" in BUILTIN_MODES
    assert "gemini_reasoning" in BUILTIN_MODES

    quick = BUILTIN_MODES["gemini_quick"]
    assert quick["provider"] == "gemini"
    assert quick["model"] == "gemini-2.5-flash-lite"
    assert quick["kind"] == "immediate"
    quick_cfg = quick.get("gemini")
    assert isinstance(quick_cfg, dict)
    assert quick_cfg.get("tools") == ["google_search"]
    assert quick_cfg.get("thinking_budget") == 0

    reasoning = BUILTIN_MODES["gemini_reasoning"]
    assert reasoning["model"] == "gemini-2.5-pro"
    reasoning_cfg = reasoning.get("gemini")
    assert isinstance(reasoning_cfg, dict)
    assert reasoning_cfg.get("thinking_budget") == -1
    assert reasoning_cfg.get("include_thoughts") is True


def test_gemini_build_messages_renders_user_prompt() -> None:
    """_build_messages_and_system creates contents=[Content(role='user', parts=[Part(text=prompt)])]."""
    from thoth.providers.gemini import GeminiProvider

    provider = GeminiProvider(api_key="dummy", config={})
    contents, system = provider._build_messages_and_system("What is 2+2?", None)
    assert len(contents) == 1
    content = contents[0]
    assert getattr(content, "role", None) == "user"
    parts = getattr(content, "parts", None) or []
    assert len(parts) == 1
    assert getattr(parts[0], "text", "") == "What is 2+2?"
    assert system is None


def test_gemini_build_messages_passes_through_system_prompt() -> None:
    """system_prompt becomes the system_instruction return value."""
    from thoth.providers.gemini import GeminiProvider

    provider = GeminiProvider(api_key="dummy", config={})
    contents, system = provider._build_messages_and_system("Q?", "You are a math tutor.")
    assert system == "You are a math tutor."


def test_gemini_build_tools_translates_google_search() -> None:
    """_build_tools(['google_search']) returns [Tool(google_search=GoogleSearch())]."""
    from google.genai import types as genai_types  # type: ignore[import-not-found]

    from thoth.providers.gemini import GeminiProvider

    provider = GeminiProvider(api_key="dummy", config={})
    tools = provider._build_tools(["google_search"])
    assert len(tools) == 1
    tool = tools[0]
    assert isinstance(tool, genai_types.Tool)
    assert tool.google_search is not None


def test_gemini_build_tools_skips_unknown_names() -> None:
    """Unknown tool names are skipped (forward-compat for future tool families)."""
    from thoth.providers.gemini import GeminiProvider

    provider = GeminiProvider(api_key="dummy", config={})
    tools = provider._build_tools(["google_search", "future_unknown_tool"])
    assert len(tools) == 1


def test_gemini_build_generate_content_config_quick_mode() -> None:
    """gemini_quick mode produces tools=[GoogleSearch()], thinking_config.thinking_budget=0."""
    from thoth.config import BUILTIN_MODES
    from thoth.providers.gemini import GeminiProvider

    config = {**BUILTIN_MODES["gemini_quick"], "kind": "immediate"}
    provider = GeminiProvider(api_key="dummy", config=config)
    gen_config = provider._build_generate_content_config()

    assert gen_config is not None
    tools = getattr(gen_config, "tools", None) or []
    assert len(tools) == 1

    thinking_config = getattr(gen_config, "thinking_config", None)
    assert thinking_config is not None
    assert thinking_config.thinking_budget == 0


def test_gemini_build_generate_content_config_reasoning_mode() -> None:
    """gemini_reasoning mode sets include_thoughts=True."""
    from thoth.config import BUILTIN_MODES
    from thoth.providers.gemini import GeminiProvider

    config = {**BUILTIN_MODES["gemini_reasoning"], "kind": "immediate"}
    provider = GeminiProvider(api_key="dummy", config=config)
    gen_config = provider._build_generate_content_config()

    thinking_config = getattr(gen_config, "thinking_config", None)
    assert thinking_config is not None
    assert thinking_config.thinking_budget == -1
    assert thinking_config.include_thoughts is True


def test_gemini_build_generate_content_config_passthrough_temperature() -> None:
    """Direct SDK key (e.g. temperature) under [modes.X.gemini] passes through to GenerateContentConfig.temperature."""
    from thoth.providers.gemini import GeminiProvider

    config = {"gemini": {"temperature": 0.42}, "kind": "immediate"}
    provider = GeminiProvider(api_key="dummy", config=config)
    gen_config = provider._build_generate_content_config()

    assert gen_config is not None
    assert gen_config.temperature == 0.42


def test_gemini_build_generate_content_config_returns_none_when_empty() -> None:
    """No [modes.X.gemini] keys -> returns None (caller falls back to no config kwarg)."""
    from thoth.providers.gemini import GeminiProvider

    provider = GeminiProvider(api_key="dummy", config={})
    gen_config = provider._build_generate_content_config()
    assert gen_config is None


def test_gemini_build_generate_content_config_include_thoughts_only_defaults_thinking_budget_to_dynamic() -> (
    None
):
    """When only include_thoughts is set (no explicit thinking_budget), helper defaults to thinking_budget=-1 ('dynamic').

    This is a deliberate policy: setting include_thoughts=True is opting INTO
    thinking-related output, so 'dynamic' (-1) is the most useful default.
    Locked by this test; change requires changing the policy and the test together.
    """
    from thoth.providers.gemini import GeminiProvider

    config = {"gemini": {"include_thoughts": True}, "kind": "immediate"}
    provider = GeminiProvider(api_key="dummy", config=config)
    gen_config = provider._build_generate_content_config()

    assert gen_config is not None
    thinking_config = getattr(gen_config, "thinking_config", None)
    assert thinking_config is not None
    assert thinking_config.thinking_budget == -1, (
        "include_thoughts=True without explicit thinking_budget must default to -1 (dynamic)"
    )
    assert thinking_config.include_thoughts is True


# ---------------------------------------------------------------------------
# Task 4.3: error mapping + retry policy
# ---------------------------------------------------------------------------

from unittest.mock import MagicMock  # noqa: E402

import pytest  # noqa: E402


def _make_gemini_client_error(code: int, status: str, message: str, details: list | None = None):
    """Construct a google.genai.errors.ClientError for testing.

    The SDK's ClientError takes (code, response_json, response). We build a
    minimal response_json dict with the error.status / error.message / error.details
    that _map_gemini_error inspects.
    """
    from google.genai import errors as genai_errors

    error_obj: dict[str, object] = {"code": code, "status": status, "message": message}
    if details is not None:
        error_obj["details"] = details
    response_json: dict[str, object] = {"error": error_obj}
    fake_response = MagicMock()
    fake_response.status_code = code
    return genai_errors.ClientError(code=code, response_json=response_json, response=fake_response)


def _make_gemini_server_error(code: int, status: str = "INTERNAL", message: str = "server error"):
    from google.genai import errors as genai_errors

    response_json = {"error": {"code": code, "status": status, "message": message}}
    fake_response = MagicMock()
    fake_response.status_code = code
    return genai_errors.ServerError(code=code, response_json=response_json, response=fake_response)


@pytest.mark.parametrize(
    "code,status,message,expected_cls,expected_substr",
    [
        # Auth-invalid (matched by phrase in message)
        (
            401,
            "UNAUTHENTICATED",
            "API key not valid. Please pass a valid API key.",
            "ThothError",
            "key is invalid",
        ),
        # Auth-missing (different phrasing)
        (401, "UNAUTHENTICATED", "Missing authentication credential.", "APIKeyError", "gemini"),
        # Rate-limit (per-minute, no quota markers)
        (
            429,
            "RESOURCE_EXHAUSTED",
            "Quota exceeded for quota metric 'Generate content requests per minute'",
            "APIRateLimitError",
            "rate",
        ),
        # Bad request (no offending param)
        (400, "INVALID_ARGUMENT", "Some bad request error", "ProviderError", "Bad request"),
        # NotFound
        (404, "NOT_FOUND", "Model not found", "ProviderError", "not found"),
        # Permission denied
        (
            403,
            "PERMISSION_DENIED",
            "API key does not have permission",
            "ProviderError",
            "Permission",
        ),
    ],
)
def test_gemini_error_mapping_table(code, status, message, expected_cls, expected_substr) -> None:
    from thoth.errors import (
        APIKeyError,
        APIQuotaError,
        APIRateLimitError,
        ProviderError,
        ThothError,
    )
    from thoth.providers.gemini import _map_gemini_error

    fake_exc = _make_gemini_client_error(code, status, message)
    mapped = _map_gemini_error(fake_exc, "gemini-2.5-flash-lite", verbose=False)
    expected = {
        "ThothError": ThothError,
        "APIKeyError": APIKeyError,
        "APIRateLimitError": APIRateLimitError,
        "APIQuotaError": APIQuotaError,
        "ProviderError": ProviderError,
    }[expected_cls]
    assert isinstance(mapped, expected), (
        f"expected {expected.__name__}, got {type(mapped).__name__}: {mapped}"
    )
    assert expected_substr.lower() in str(mapped).lower()


def test_gemini_quota_per_day_maps_to_apiquotaerror() -> None:
    """429 with 'per day' in message maps to APIQuotaError, not APIRateLimitError."""
    from thoth.errors import APIQuotaError
    from thoth.providers.gemini import _map_gemini_error

    fake_exc = _make_gemini_client_error(
        429,
        "RESOURCE_EXHAUSTED",
        "Quota exceeded for quota metric 'Generate content requests per day'",
    )
    mapped = _map_gemini_error(fake_exc, "gemini-2.5-pro", verbose=False)
    assert isinstance(mapped, APIQuotaError)


def test_gemini_quota_free_tier_maps_to_apiquotaerror() -> None:
    """429 with FREE_TIER_LIMIT_EXCEEDED reason maps to APIQuotaError."""
    from thoth.errors import APIQuotaError
    from thoth.providers.gemini import _map_gemini_error

    fake_exc = _make_gemini_client_error(
        429,
        "RESOURCE_EXHAUSTED",
        "Quota exceeded",
        details=[{"reason": "FREE_TIER_LIMIT_EXCEEDED"}],
    )
    mapped = _map_gemini_error(fake_exc, "gemini-2.5-pro", verbose=False)
    assert isinstance(mapped, APIQuotaError)


def test_gemini_invalid_key_thotherror_has_exit_code_2() -> None:
    """The shared _invalid_key_thotherror helper guarantees exit_code=2 with brand-correct casing."""
    from thoth.errors import ThothError
    from thoth.providers.gemini import _map_gemini_error

    fake_exc = _make_gemini_client_error(401, "UNAUTHENTICATED", "API key not valid")
    mapped = _map_gemini_error(fake_exc, "gemini-2.5-pro", verbose=False)
    assert isinstance(mapped, ThothError)
    assert mapped.exit_code == 2
    assert "Gemini" in str(mapped)  # capitalized brand name


def test_gemini_invalid_argument_extracts_offending_param() -> None:
    """400 INVALID_ARGUMENT with 'parameter X' extracts X via the shared helper."""
    from thoth.providers.gemini import _map_gemini_error

    fake_exc = _make_gemini_client_error(
        400,
        "INVALID_ARGUMENT",
        "Unsupported parameter 'frequency_penalty' for gemini-2.5-pro",
    )
    mapped = _map_gemini_error(fake_exc, "gemini-2.5-pro", verbose=False)
    assert "frequency_penalty" in str(mapped)


def test_gemini_server_error_5xx_maps_to_provider_error() -> None:
    from thoth.errors import ProviderError
    from thoth.providers.gemini import _map_gemini_error

    fake_exc = _make_gemini_server_error(500)
    mapped = _map_gemini_error(fake_exc, "gemini-2.5-pro", verbose=False)
    assert isinstance(mapped, ProviderError)
    assert "server error" in str(mapped).lower()


def test_gemini_httpx_timeout_maps_to_provider_error() -> None:
    import httpx

    from thoth.errors import ProviderError
    from thoth.providers.gemini import _map_gemini_error

    fake_exc = httpx.TimeoutException("Request timed out")
    mapped = _map_gemini_error(fake_exc, "gemini-2.5-pro", verbose=False)
    assert isinstance(mapped, ProviderError)
    assert "timed out" in str(mapped).lower() or "timeout" in str(mapped).lower()


def test_gemini_httpx_connect_error_maps_to_provider_error() -> None:
    import httpx

    from thoth.errors import ProviderError
    from thoth.providers.gemini import _map_gemini_error

    fake_exc = httpx.ConnectError("Connection refused")
    mapped = _map_gemini_error(fake_exc, "gemini-2.5-pro", verbose=False)
    assert isinstance(mapped, ProviderError)


def test_gemini_unknown_exception_maps_to_provider_error() -> None:
    from thoth.errors import ProviderError
    from thoth.providers.gemini import _map_gemini_error

    mapped = _map_gemini_error(RuntimeError("???"), "gemini-2.5-pro", verbose=False)
    assert isinstance(mapped, ProviderError)
    assert "Unexpected" in str(mapped) or "???" in str(mapped)


def test_gemini_retry_classes_includes_rate_limit() -> None:
    """The Gemini retry-class set includes APIRateLimitError per Google's 429 guidance."""
    import httpx

    from thoth.errors import APIRateLimitError
    from thoth.providers.gemini import _GEMINI_RETRY_CLASSES

    assert APIRateLimitError in _GEMINI_RETRY_CLASSES
    assert httpx.TimeoutException in _GEMINI_RETRY_CLASSES
    assert httpx.ConnectError in _GEMINI_RETRY_CLASSES


def test_gemini_retry_classes_excludes_quota_error() -> None:
    """APIQuotaError is NOT in the retry set (quota is permanent until reset)."""
    from thoth.errors import APIQuotaError
    from thoth.providers.gemini import _GEMINI_RETRY_CLASSES

    assert APIQuotaError not in _GEMINI_RETRY_CLASSES


# ---------------------------------------------------------------------------
# Task 4.4: stream() translation
# ---------------------------------------------------------------------------

import asyncio  # noqa: E402
from types import SimpleNamespace  # noqa: E402
from unittest.mock import patch  # noqa: E402


def _make_chunk(parts: list[dict] | None = None, grounding: dict | None = None) -> SimpleNamespace:
    """Build a fake GenerateContentResponse chunk for stream tests."""
    candidate_parts = []
    for p in parts or []:
        candidate_parts.append(
            SimpleNamespace(text=p.get("text", ""), thought=p.get("thought", False))
        )
    grounding_obj = SimpleNamespace(**grounding) if grounding else None
    candidate = SimpleNamespace(
        content=SimpleNamespace(parts=candidate_parts),
        grounding_metadata=grounding_obj,
    )
    return SimpleNamespace(
        candidates=[candidate],
        text=" ".join(p.get("text", "") for p in (parts or []) if not p.get("thought")),
    )


async def _consume_events(stream_iter):
    return [event async for event in stream_iter]


def _make_gemini_provider_with_chunks(chunks: list):
    """Construct a GeminiProvider whose client.aio.models.generate_content_stream
    yields the given fake chunks. Uses unittest.mock.patch over google.genai.Client.

    The real google-genai SDK exposes generate_content_stream as a coroutine
    function returning an AsyncIterator (i.e. `async for chunk in await
    client.aio.models.generate_content_stream(...)`). We mirror that shape
    here: the outer function is async (returns a coroutine) that resolves
    to an async generator over the fake chunks.
    """
    from thoth.providers.gemini import GeminiProvider

    async def _async_iter():
        for c in chunks:
            yield c

    async def fake_stream(**kw):
        return _async_iter()

    mock_client = SimpleNamespace()
    mock_client.aio = SimpleNamespace()
    mock_client.aio.models = SimpleNamespace()
    mock_client.aio.models.generate_content_stream = fake_stream
    mock_client.aio.models.generate_content = lambda **kw: None  # not exercised here

    with patch("google.genai.Client", return_value=mock_client):
        provider = GeminiProvider(api_key="dummy", config={"kind": "immediate"})
    return provider


def test_gemini_stream_emits_text_for_non_thought_parts() -> None:
    """A chunk with non-thought parts emits StreamEvent('text', text) per part."""
    chunks = [
        _make_chunk(
            parts=[
                {"text": "Hello "},
                {"text": "world.", "thought": False},
            ]
        ),
    ]
    provider = _make_gemini_provider_with_chunks(chunks)
    events = asyncio.run(_consume_events(provider.stream("Q?", "test_mode")))

    text_events = [e for e in events if e.kind == "text"]
    assert len(text_events) == 2
    assert text_events[0].text == "Hello "
    assert text_events[1].text == "world."


def test_gemini_stream_emits_reasoning_for_thought_parts() -> None:
    """A part with thought=True emits StreamEvent('reasoning', text)."""
    chunks = [
        _make_chunk(
            parts=[
                {"text": "Let me think: ", "thought": True},
                {"text": "Answer is 42.", "thought": False},
            ]
        ),
    ]
    provider = _make_gemini_provider_with_chunks(chunks)
    events = asyncio.run(_consume_events(provider.stream("Q?", "test_mode")))

    reasoning = [e for e in events if e.kind == "reasoning"]
    text = [e for e in events if e.kind == "text"]
    assert len(reasoning) == 1
    assert reasoning[0].text == "Let me think: "
    assert len(text) == 1
    assert text[0].text == "Answer is 42."


def test_gemini_stream_emits_citations_from_terminal_grounding_chunks() -> None:
    """grounding_metadata.grounding_chunks emit deduped StreamEvent('citation', Citation(...))."""
    grounding = {
        "grounding_chunks": [
            SimpleNamespace(
                web=SimpleNamespace(
                    uri="https://vertexaisearch.cloud.google.com/grounding-api-redirect/AAA",
                    title="example.com",
                )
            ),
            SimpleNamespace(
                web=SimpleNamespace(
                    uri="https://vertexaisearch.cloud.google.com/grounding-api-redirect/BBB",
                    title="other.com",
                )
            ),
            # duplicate URL — should dedupe
            SimpleNamespace(
                web=SimpleNamespace(
                    uri="https://vertexaisearch.cloud.google.com/grounding-api-redirect/AAA",
                    title="example.com",
                )
            ),
        ]
    }

    chunks = [
        _make_chunk(parts=[{"text": "Per source A and B."}]),
        _make_chunk(parts=[], grounding=grounding),  # terminal chunk
    ]
    provider = _make_gemini_provider_with_chunks(chunks)
    events = asyncio.run(_consume_events(provider.stream("Q?", "test_mode")))

    citations = [e for e in events if e.kind == "citation"]
    assert len(citations) == 2  # deduped
    from thoth.providers.base import Citation

    assert all(isinstance(e.citation, Citation) for e in citations)
    assert citations[0].citation.url.startswith("https://vertexaisearch")


def test_gemini_stream_terminal_done_event() -> None:
    """Stream always ends with StreamEvent('done', '')."""
    chunks = [_make_chunk(parts=[{"text": "Hi."}])]
    provider = _make_gemini_provider_with_chunks(chunks)
    events = asyncio.run(_consume_events(provider.stream("Q?", "test_mode")))

    assert events[-1].kind == "done"
    assert events[-1].text == ""


def test_gemini_stream_title_falls_back_to_netloc_when_empty() -> None:
    """Citation.title = urlparse(uri).netloc when web.title is missing/empty."""
    grounding = {
        "grounding_chunks": [
            SimpleNamespace(
                web=SimpleNamespace(
                    uri="https://example.com/path",
                    title="",
                )
            ),
        ]
    }
    chunks = [_make_chunk(parts=[], grounding=grounding)]
    provider = _make_gemini_provider_with_chunks(chunks)
    events = asyncio.run(_consume_events(provider.stream("Q?", "test_mode")))

    citations = [e for e in events if e.kind == "citation"]
    assert len(citations) == 1
    assert citations[0].citation.title == "example.com"


def test_gemini_stream_skips_empty_text_parts() -> None:
    """Empty-text parts (e.g., placeholder/empty) are skipped, not emitted."""
    chunks = [
        _make_chunk(
            parts=[
                {"text": ""},  # empty — should be skipped
                {"text": "Real text."},
            ]
        ),
    ]
    provider = _make_gemini_provider_with_chunks(chunks)
    events = asyncio.run(_consume_events(provider.stream("Q?", "test_mode")))

    text_events = [e for e in events if e.kind == "text"]
    assert len(text_events) == 1
    assert text_events[0].text == "Real text."


def test_gemini_stream_handles_chunk_without_candidates() -> None:
    """Chunks with no candidates (or empty candidates list) are tolerated, no events emitted."""
    chunks = [
        SimpleNamespace(candidates=[], text=""),  # empty candidates list
        _make_chunk(parts=[{"text": "Real."}]),
    ]
    provider = _make_gemini_provider_with_chunks(chunks)
    events = asyncio.run(_consume_events(provider.stream("Q?", "test_mode")))

    text_events = [e for e in events if e.kind == "text"]
    assert len(text_events) == 1
    assert events[-1].kind == "done"


def test_gemini_stream_skips_grounding_chunks_without_web_field() -> None:
    """grounding_chunks of type image/maps/retrievedContext (no .web) are skipped."""
    grounding = {
        "grounding_chunks": [
            # Has web — should produce a citation
            SimpleNamespace(web=SimpleNamespace(uri="https://example.com", title="example.com")),
            # No web (e.g. image variant) — should skip
            SimpleNamespace(web=None),
        ]
    }
    chunks = [_make_chunk(parts=[], grounding=grounding)]
    provider = _make_gemini_provider_with_chunks(chunks)
    events = asyncio.run(_consume_events(provider.stream("Q?", "test_mode")))

    citations = [e for e in events if e.kind == "citation"]
    assert len(citations) == 1


def test_gemini_stream_mid_iteration_error_maps_to_provider_error() -> None:
    """A ClientError raised mid-iteration is mapped via _map_gemini_error."""
    from google.genai import errors as genai_errors

    from thoth.errors import ProviderError

    fake_response = MagicMock()
    fake_response.status_code = 400

    async def _iter_raises_mid():
        yield _make_chunk(parts=[{"text": "Started"}])
        raise genai_errors.ClientError(
            code=400,
            response_json={
                "error": {"code": 400, "status": "INVALID_ARGUMENT", "message": "Bad mid-stream"}
            },
            response=fake_response,
        )

    async def fake_stream_raises_mid_iter(**kw):
        return _iter_raises_mid()

    from thoth.providers.gemini import GeminiProvider

    mock_client = SimpleNamespace()
    mock_client.aio = SimpleNamespace()
    mock_client.aio.models = SimpleNamespace()
    mock_client.aio.models.generate_content_stream = fake_stream_raises_mid_iter
    mock_client.aio.models.generate_content = lambda **kw: None

    with patch("google.genai.Client", return_value=mock_client):
        provider = GeminiProvider(api_key="dummy", config={"kind": "immediate"})
    with pytest.raises(ProviderError) as excinfo:
        asyncio.run(_consume_events(provider.stream("Q?", "test_mode")))
    assert "Bad mid-stream" in str(excinfo.value) or "bad request" in str(excinfo.value).lower()


# ---------------------------------------------------------------------------
# Task 4.5: submit / check_status / get_result + tenacity retry
# ---------------------------------------------------------------------------


def test_gemini_submit_returns_job_id_and_stashes_response() -> None:
    """submit() runs generate_content once and stashes response under a job_id starting with 'gemini-'."""
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import patch

    from thoth.providers.gemini import GeminiProvider

    fake_response = SimpleNamespace(
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(parts=[SimpleNamespace(text="Answer.", thought=False)]),
                grounding_metadata=None,
            )
        ],
        text="Answer.",
    )

    async def fake_generate_content(**kw):
        return fake_response

    mock_client = SimpleNamespace()
    mock_client.aio = SimpleNamespace()
    mock_client.aio.models = SimpleNamespace()
    mock_client.aio.models.generate_content = fake_generate_content
    mock_client.aio.models.generate_content_stream = lambda **kw: None  # not exercised

    with patch("google.genai.Client", return_value=mock_client):
        provider = GeminiProvider(api_key="dummy", config={"kind": "immediate"})
    job_id = asyncio.run(provider.submit("Q?", "test_mode"))

    assert job_id.startswith("gemini-")
    assert job_id in provider.jobs
    assert provider.jobs[job_id]["response"] is fake_response


def test_gemini_check_status_returns_completed_for_known_job() -> None:
    """check_status returns {'status': 'completed', 'progress': 1.0} for known immediate jobs."""
    import asyncio

    from thoth.providers.gemini import GeminiProvider

    provider = GeminiProvider(api_key="dummy", config={})
    provider.jobs["test-job"] = {"response": object(), "created_at": 0}
    status = asyncio.run(provider.check_status("test-job"))

    assert status["status"] == "completed"
    assert status["progress"] == 1.0


def test_gemini_check_status_returns_not_found_for_unknown_job() -> None:
    """check_status returns 'not_found' for unknown job_ids."""
    import asyncio

    from thoth.providers.gemini import GeminiProvider

    provider = GeminiProvider(api_key="dummy", config={})
    status = asyncio.run(provider.check_status("nonexistent"))

    assert status["status"] == "not_found"


def test_gemini_get_result_renders_text_only_when_no_reasoning_or_sources() -> None:
    """get_result returns just the answer text when no thoughts and no grounding."""
    import asyncio
    from types import SimpleNamespace

    from thoth.providers.gemini import GeminiProvider

    fake_response = SimpleNamespace(
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(
                    parts=[SimpleNamespace(text="Final answer.", thought=False)]
                ),
                grounding_metadata=None,
            )
        ],
        text="Final answer.",
    )
    provider = GeminiProvider(api_key="dummy", config={})
    provider.jobs["test"] = {"response": fake_response, "created_at": 0}

    rendered = asyncio.run(provider.get_result("test"))
    assert rendered == "Final answer."  # no extra sections


def test_gemini_get_result_renders_reasoning_section_when_thoughts_present() -> None:
    """Thought parts collected into a ## Reasoning section above the answer."""
    import asyncio
    from types import SimpleNamespace

    from thoth.providers.gemini import GeminiProvider

    fake_response = SimpleNamespace(
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(
                    parts=[
                        SimpleNamespace(text="Reasoning bit. ", thought=True),
                        SimpleNamespace(text="Final answer.", thought=False),
                    ]
                ),
                grounding_metadata=None,
            )
        ],
        text="Final answer.",
    )
    provider = GeminiProvider(api_key="dummy", config={})
    provider.jobs["test"] = {"response": fake_response, "created_at": 0}

    rendered = asyncio.run(provider.get_result("test"))
    assert "## Reasoning" in rendered
    assert "Reasoning bit." in rendered
    assert "Final answer." in rendered


def test_gemini_get_result_renders_sources_section_with_sanitized_links() -> None:
    """Grounding chunks become a ## Sources section using md_link_title/md_link_url."""
    import asyncio
    from types import SimpleNamespace

    from thoth.providers.gemini import GeminiProvider

    grounding = SimpleNamespace(
        grounding_chunks=[
            SimpleNamespace(web=SimpleNamespace(uri="https://example.com", title="example.com")),
        ]
    )
    fake_response = SimpleNamespace(
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(parts=[SimpleNamespace(text="Body.", thought=False)]),
                grounding_metadata=grounding,
            )
        ],
        text="Body.",
    )
    provider = GeminiProvider(api_key="dummy", config={})
    provider.jobs["test"] = {"response": fake_response, "created_at": 0}

    rendered = asyncio.run(provider.get_result("test"))
    assert "## Sources" in rendered
    assert "[example.com](https://example.com)" in rendered


def test_gemini_get_result_sanitizes_adversarial_citation() -> None:
    """Adversarial titles (HTML) and URLs (javascript:) are neutralized via md_link_*."""
    import asyncio
    from types import SimpleNamespace

    from thoth.providers.gemini import GeminiProvider

    grounding = SimpleNamespace(
        grounding_chunks=[
            SimpleNamespace(
                web=SimpleNamespace(uri="javascript:alert(1)", title="<script>x</script>")
            ),
        ]
    )
    fake_response = SimpleNamespace(
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(parts=[SimpleNamespace(text="Body.", thought=False)]),
                grounding_metadata=grounding,
            )
        ],
        text="Body.",
    )
    provider = GeminiProvider(api_key="dummy", config={})
    provider.jobs["test"] = {"response": fake_response, "created_at": 0}

    rendered = asyncio.run(provider.get_result("test"))
    assert "<script>" not in rendered
    assert "javascript:" not in rendered


def test_gemini_get_result_unknown_job_raises() -> None:
    """get_result for unknown job_id raises ProviderError."""
    import asyncio

    import pytest

    from thoth.errors import ProviderError
    from thoth.providers.gemini import GeminiProvider

    provider = GeminiProvider(api_key="dummy", config={})
    with pytest.raises(ProviderError) as excinfo:
        asyncio.run(provider.get_result("nonexistent"))
    assert "nonexistent" in str(excinfo.value) or "not found" in str(excinfo.value).lower()


def test_gemini_get_result_dedupes_sources_by_url() -> None:
    """Duplicate URLs in grounding_chunks are deduped in the Sources block."""
    import asyncio
    from types import SimpleNamespace

    from thoth.providers.gemini import GeminiProvider

    grounding = SimpleNamespace(
        grounding_chunks=[
            SimpleNamespace(web=SimpleNamespace(uri="https://a.com", title="A")),
            SimpleNamespace(web=SimpleNamespace(uri="https://a.com", title="A again")),  # dup
            SimpleNamespace(web=SimpleNamespace(uri="https://b.com", title="B")),
        ]
    )
    fake_response = SimpleNamespace(
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(parts=[SimpleNamespace(text="Body.", thought=False)]),
                grounding_metadata=grounding,
            )
        ],
        text="Body.",
    )
    provider = GeminiProvider(api_key="dummy", config={})
    provider.jobs["test"] = {"response": fake_response, "created_at": 0}

    rendered = asyncio.run(provider.get_result("test"))
    # Should have only 2 source lines (a.com once, b.com once)
    sources_block = rendered.split("## Sources")[1] if "## Sources" in rendered else ""
    a_count = sources_block.count("a.com")
    assert a_count == 1, f"expected 1 occurrence of a.com in sources, got {a_count}"


def test_gemini_get_result_empty_content_with_verbose_emits_debug(capsys) -> None:
    """verbose=True + empty content emits debug ladder to stderr."""
    import asyncio
    from types import SimpleNamespace

    from thoth.providers.gemini import GeminiProvider

    fake_response = SimpleNamespace(
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(parts=[]),  # empty
                grounding_metadata=None,
            )
        ],
        text="",
    )
    fake_response.model_dump_json = lambda **kw: '{"empty": true}'
    provider = GeminiProvider(api_key="dummy", config={})
    provider.jobs["test"] = {"response": fake_response, "created_at": 0}

    asyncio.run(provider.get_result("test", verbose=True))
    captured = capsys.readouterr()
    combined = (captured.err + captured.out).lower()
    assert "empty" in combined or "debug" in combined or "no content" in combined


def test_gemini_submit_retry_decorator_retries_transient_errors() -> None:
    """tenacity retry on httpx.TimeoutException — succeeds after 2 transient failures."""
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import patch

    import httpx

    from thoth.providers.gemini import GeminiProvider

    call_count = {"n": 0}
    fake_response = SimpleNamespace(
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(parts=[SimpleNamespace(text="OK.", thought=False)]),
                grounding_metadata=None,
            )
        ],
        text="OK.",
    )

    async def fake_generate_content(**kw):
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise httpx.TimeoutException("transient")
        return fake_response

    mock_client = SimpleNamespace()
    mock_client.aio = SimpleNamespace()
    mock_client.aio.models = SimpleNamespace()
    mock_client.aio.models.generate_content = fake_generate_content

    with patch("google.genai.Client", return_value=mock_client):
        provider = GeminiProvider(api_key="dummy", config={"kind": "immediate"})

    # Patch tenacity wait to instant for test speed
    with patch("thoth.providers.gemini.wait_exponential", return_value=lambda r: 0):
        job_id = asyncio.run(provider.submit("Q?", "test_mode"))

    assert call_count["n"] == 3  # 2 fails + 1 success
    assert job_id in provider.jobs


def test_gemini_kind_mismatch_rejects_deep_research_in_immediate_submit() -> None:
    """deep-research-pro-preview-12-2025 with kind=immediate raises ModeKindMismatchError on submit()."""
    import asyncio

    import pytest

    from thoth.errors import ModeKindMismatchError
    from thoth.providers.gemini import GeminiProvider

    mock_client = SimpleNamespace()
    mock_client.aio = SimpleNamespace()
    mock_client.aio.models = SimpleNamespace()
    mock_client.aio.models.generate_content = lambda **kw: None  # should NOT be called
    mock_client.aio.models.generate_content_stream = lambda **kw: None

    with patch("google.genai.Client", return_value=mock_client):
        provider = GeminiProvider(
            api_key="dummy",
            config={"kind": "immediate", "model": "deep-research-pro-preview-12-2025"},
        )
    with pytest.raises(ModeKindMismatchError):
        asyncio.run(provider.submit("Q?", "test_mode"))


def test_gemini_kind_mismatch_rejects_deep_research_in_immediate_stream() -> None:
    """deep-research-pro-preview-12-2025 with kind=immediate raises ModeKindMismatchError on stream() entry."""
    import asyncio

    import pytest

    from thoth.errors import ModeKindMismatchError
    from thoth.providers.gemini import GeminiProvider

    captured = {"called": False}

    async def fake_stream(**kw):
        captured["called"] = True
        if False:
            yield  # pragma: no cover

    mock_client = SimpleNamespace()
    mock_client.aio = SimpleNamespace()
    mock_client.aio.models = SimpleNamespace()
    mock_client.aio.models.generate_content_stream = fake_stream
    mock_client.aio.models.generate_content = lambda **kw: None

    with patch("google.genai.Client", return_value=mock_client):
        provider = GeminiProvider(
            api_key="dummy",
            config={"kind": "immediate", "model": "deep-research-pro-preview-12-2025"},
        )

    async def consume():
        async for _ in provider.stream("Q?", "test_mode"):
            pass

    with pytest.raises(ModeKindMismatchError):
        asyncio.run(consume())

    # CRITICAL: the SDK call MUST NOT have been made — guard fires before HTTP.
    assert captured["called"] is False, "stream API was called despite kind-mismatch"


def test_gemini_kind_mismatch_allows_regular_models() -> None:
    """gemini-2.5-pro / gemini-2.5-flash-lite with kind=immediate are allowed (validate is no-op)."""
    from thoth.providers.gemini import GeminiProvider

    for model in ("gemini-2.5-pro", "gemini-2.5-flash-lite"):
        provider = GeminiProvider(
            api_key="dummy",
            config={"kind": "immediate", "model": model},
        )
        # Direct call to the validator should not raise
        provider._validate_kind_for_model("test_mode")  # no exception


def test_gemini_kind_mismatch_allows_when_kind_is_background() -> None:
    """deep-research model with kind=background is allowed (this is P28's territory)."""
    from thoth.providers.gemini import GeminiProvider

    provider = GeminiProvider(
        api_key="dummy",
        config={"kind": "background", "model": "deep-research-pro-preview-12-2025"},
    )
    # Direct call to the validator should not raise
    provider._validate_kind_for_model("test_mode")


def test_gemini_kind_mismatch_no_kind_in_config_no_op() -> None:
    """When kind is missing from config, the guard is a no-op (silent passthrough)."""
    from thoth.providers.gemini import GeminiProvider

    provider = GeminiProvider(
        api_key="dummy",
        config={"model": "deep-research-pro-preview-12-2025"},  # no kind
    )
    # No exception (matches OpenAI/Perplexity pattern)
    provider._validate_kind_for_model("test_mode")
