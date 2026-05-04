"""Gemini synchronous chat provider (P24).

Mirrors the P23 Perplexity provider pattern: built-in modes with a
[modes.X.gemini] namespace, side-channel stream events for reasoning and
citation, error mapper with _map_gemini_error, tenacity retry on submit.

Uses the official google-genai SDK (>=1.74.0), NOT Gemini's OpenAI-compat
endpoint, because the compat layer omits grounding metadata, thought parts,
and the thinking-budget knob.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import urlparse

import httpx
from google.genai import errors as genai_errors  # type: ignore[import-not-found]

from thoth.errors import (
    APIKeyError,
    APIQuotaError,
    APIRateLimitError,
    ModeKindMismatchError,
    ProviderError,
    ThothError,
)
from thoth.providers._helpers import (
    _extract_unsupported_param,
    _invalid_key_thotherror,
)
from thoth.providers.base import Citation, ResearchProvider, StreamEvent

_PROVIDER_NAME_GEMINI = "gemini"

_INVALID_KEY_PHRASES_GEMINI: tuple[str, ...] = (
    "api key not valid",
    "api_key_invalid",
    "invalid api key",
    "api key expired",
)

_QUOTA_MARKERS_GEMINI: tuple[str, ...] = (
    "per day",
    "you exceeded your current quota",
    "free tier",
    "billing",
    "credit",
)

_DIRECT_SDK_KEYS_GEMINI: tuple[str, ...] = (
    # Allowlist of [modes.X.gemini].* keys recognized by
    # _build_generate_content_config. NOTE: tools / thinking_budget /
    # include_thoughts are special-cased in the builder (translated to
    # types.Tool / types.ThinkingConfig respectively); the rest pass
    # through to GenerateContentConfig(**kwargs) directly.
    "temperature",
    "top_p",
    "top_k",
    "max_output_tokens",
    "stop_sequences",
    "response_mime_type",
    "response_schema",
    "response_json_schema",
    "tools",
    "safety_settings",
    "thinking_budget",
    "include_thoughts",
)


def _is_gemini_quota_exhaustion(message: str, details: list[dict[str, Any]] | None) -> bool:
    """Distinguish quota/credits exhaustion from ordinary rate-limiting on a 429.

    Inspect the message for known quota-exhaustion phrases AND structurally inspect
    error.details[].reason for FREE_TIER_LIMIT_EXCEEDED / BILLING_DISABLED / daily-metric markers.
    """
    msg_lower = message.lower()
    if any(marker in msg_lower for marker in _QUOTA_MARKERS_GEMINI):
        return True
    if details:
        for entry in details:
            if not isinstance(entry, dict):
                continue
            reason = (entry.get("reason") or "").upper()
            if reason in {"FREE_TIER_LIMIT_EXCEEDED", "BILLING_DISABLED"}:
                return True
            if reason == "RATE_LIMIT_EXCEEDED":
                metric = (entry.get("quotaMetric") or entry.get("metric") or "").lower()
                if "per day" in metric or "daily" in metric:
                    return True
    return False


def _map_gemini_error(exc: Exception, model: str | None, verbose: bool = False) -> ThothError:
    """Translate google-genai SDK and httpx exceptions into ThothError subclasses.

    Mirrors _map_openai_error / _map_perplexity_error's shape.
    Note: ModeKindMismatchError is propagated unmapped by the caller (provider's
    submit/stream methods); this function only handles SDK + httpx exceptions.
    """
    if isinstance(exc, genai_errors.ClientError):
        # ClientError stores response_json under .details (full body) and pre-extracts
        # .code / .status / .message. We dig into .details for the structured
        # error.details list (used by quota discrimination).
        body = getattr(exc, "details", None) or {}
        if not isinstance(body, dict):
            body = {}
        err_obj = body.get("error") or {}
        if not isinstance(err_obj, dict):
            err_obj = {}
        message = getattr(exc, "message", None) or err_obj.get("message") or str(exc) or ""
        status_raw = getattr(exc, "status", None) or err_obj.get("status") or ""
        status = status_raw.upper() if isinstance(status_raw, str) else ""
        details = err_obj.get("details")
        code = getattr(exc, "code", None)

        if code == 401 or status == "UNAUTHENTICATED":
            if any(p in message.lower() for p in _INVALID_KEY_PHRASES_GEMINI):
                return _invalid_key_thotherror(
                    "Gemini",
                    "https://aistudio.google.com/app/apikey",
                )
            return APIKeyError(_PROVIDER_NAME_GEMINI)

        if code == 429 or status == "RESOURCE_EXHAUSTED":
            if _is_gemini_quota_exhaustion(message, details if isinstance(details, list) else None):
                return APIQuotaError(_PROVIDER_NAME_GEMINI)
            return APIRateLimitError(_PROVIDER_NAME_GEMINI)

        if code == 404 or status == "NOT_FOUND":
            model_str = repr(model) if model else "(unknown)"
            return ProviderError(
                _PROVIDER_NAME_GEMINI,
                f"Model {model_str} not found or unavailable. "
                f"Run `thoth providers --models --provider gemini` to list valid models.",
            )

        if code == 400 or status in {
            "INVALID_ARGUMENT",
            "FAILED_PRECONDITION",
            "OUT_OF_RANGE",
        }:
            param = _extract_unsupported_param(message)
            if param:
                return ProviderError(
                    _PROVIDER_NAME_GEMINI,
                    f"Gemini does not support parameter {param!r} for this model. "
                    f"Remove it from the mode config or its provider namespace.",
                )
            return ProviderError(_PROVIDER_NAME_GEMINI, f"Bad request: {message}")

        if code == 403 or status == "PERMISSION_DENIED":
            return ProviderError(
                _PROVIDER_NAME_GEMINI,
                f"Permission denied: {message}",
            )

        # Other ClientError (e.g. unrecognized 4xx)
        return ProviderError(_PROVIDER_NAME_GEMINI, f"Gemini API error ({code}): {message}")

    if isinstance(exc, genai_errors.ServerError):
        code = getattr(exc, "code", "5xx")
        return ProviderError(
            _PROVIDER_NAME_GEMINI,
            f"Gemini server error ({code}). Retry shortly.",
        )

    if isinstance(exc, httpx.TimeoutException):
        return ProviderError(
            _PROVIDER_NAME_GEMINI,
            "Request timed out. Try again, or raise --timeout.",
        )

    if isinstance(exc, (httpx.ConnectError, httpx.RemoteProtocolError, httpx.RequestError)):
        return ProviderError(
            _PROVIDER_NAME_GEMINI,
            "Network connection error reaching the Gemini API.",
        )

    if isinstance(exc, genai_errors.APIError):
        return ProviderError(_PROVIDER_NAME_GEMINI, f"Gemini API error: {exc}")

    return ProviderError(_PROVIDER_NAME_GEMINI, f"Unexpected error: {exc}")


_GEMINI_RETRY_CLASSES: tuple[type[BaseException], ...] = (
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.RemoteProtocolError,
    APIRateLimitError,
)


class GeminiProvider(ResearchProvider):
    """Synchronous Gemini chat provider (P24).

    Implementation lands across Tasks 4.2-4.6 of the P24 plan:
      - 4.2: built-in modes + request construction
      - 4.3: error mapping + retry policy
      - 4.4: stream() translation (Part.thought + grounding citations)
      - 4.5: submit/check_status/get_result + retry
      - 4.6: kind-mismatch guard
    """

    def __init__(self, api_key: str = "", config: dict[str, Any] | None = None) -> None:
        super().__init__(api_key=api_key, config=config)
        self.model = (self.config or {}).get("model") or "gemini-2.5-flash-lite"
        self.jobs: dict[str, dict[str, Any]] = {}
        # Lazy-import google-genai to avoid hard dep at module-load time;
        # also lets the test suite mock the client without paying the import.
        from google import genai  # type: ignore[import-not-found]

        self.client = genai.Client(api_key=api_key)

    def is_implemented(self) -> bool:
        return True

    def implementation_status(self) -> str | None:
        return None

    def _validate_kind_for_model(self, mode: str) -> None:
        """Validate that the configured kind matches the model's capabilities.

        No-op stub. Task 4.6 will fill in the actual immediate/background
        guard. Defined here so submit/stream call sites are stable across
        the 4.4/4.5/4.6 task split.
        """
        return None

    def _build_messages_and_system(
        self, prompt: str, system_prompt: str | None
    ) -> tuple[list[Any], str | None]:
        """Build the contents list + system_instruction for GenerateContentConfig.

        Returns (contents, system_instruction). The caller composes them into
        the final request: `model=`, `contents=contents`,
        `config=GenerateContentConfig(system_instruction=system_instruction, ...)`.
        """
        from google.genai import types  # type: ignore[import-not-found]

        contents = [types.Content(role="user", parts=[types.Part(text=prompt)])]
        return contents, system_prompt or None

    def _build_tools(self, tool_names: list[str]) -> list[Any]:
        """Translate a list of tool names into a list of types.Tool instances.

        Currently supports: 'google_search' -> Tool(google_search=GoogleSearch()).
        Unknown names are silently skipped (forward-compat for future tool
        families).
        """
        from google.genai import types  # type: ignore[import-not-found]

        tools: list[Any] = []
        for name in tool_names:
            if name == "google_search":
                tools.append(types.Tool(google_search=types.GoogleSearch()))
            # Future tool names appended here.
        return tools

    def _build_generate_content_config(self) -> Any:
        """Translate [modes.X.gemini].* into a GenerateContentConfig instance.

        Returns None when no gemini-namespace keys are configured (caller will
        omit the config kwarg from the SDK call).

        Special-case keys (NOT direct passthrough):
          - tools: translated via _build_tools.
          - thinking_budget / include_thoughts: nested under
            config.thinking_config.

        All other keys in _DIRECT_SDK_KEYS_GEMINI pass through to
        GenerateContentConfig by name.
        """
        from google.genai import types  # type: ignore[import-not-found]

        gemini_cfg = (self.config or {}).get("gemini") or {}
        if not isinstance(gemini_cfg, dict) or not gemini_cfg:
            return None

        config_kwargs: dict[str, Any] = {}

        if "tools" in gemini_cfg:
            config_kwargs["tools"] = self._build_tools(gemini_cfg["tools"])

        thinking_budget = gemini_cfg.get("thinking_budget")
        include_thoughts = gemini_cfg.get("include_thoughts", False)
        if thinking_budget is not None or include_thoughts:
            # Policy: when the user opts INTO thinking-related output (either by
            # setting an explicit budget OR by enabling include_thoughts), default
            # the budget to -1 ("dynamic") rather than letting the SDK default
            # apply. Pinned by test_gemini_build_generate_content_config_include_thoughts_only_defaults_thinking_budget_to_dynamic.
            config_kwargs["thinking_config"] = types.ThinkingConfig(
                thinking_budget=thinking_budget if thinking_budget is not None else -1,
                include_thoughts=bool(include_thoughts),
            )

        # Pass through every other allowed key by name.
        for key in _DIRECT_SDK_KEYS_GEMINI:
            if key in {"tools", "thinking_budget", "include_thoughts"}:
                continue
            if key in gemini_cfg:
                config_kwargs[key] = gemini_cfg[key]

        return types.GenerateContentConfig(**config_kwargs) if config_kwargs else None

    async def stream(
        self,
        prompt: str,
        mode: str,
        system_prompt: str | None = None,
        verbose: bool = False,
    ) -> AsyncIterator[StreamEvent]:
        """Stream Gemini chunks translated to StreamEvent instances.

        Emits:
          - StreamEvent("text", part.text) for each non-thought Part.
          - StreamEvent("reasoning", part.text) for each Part where thought=True.
          - StreamEvent("citation", Citation(title, url)) for each unique
            grounding_chunks[i].web entry, deduped by URL across the stream.
          - StreamEvent("done", "") on clean stream exit.

        Mid-iteration errors map through _map_gemini_error.
        ModeKindMismatchError (raised by _validate_kind_for_model in Task 4.6)
        propagates unmapped.
        """
        self._validate_kind_for_model(mode)  # implemented by Task 4.6; no-op until then

        # Build the request kwargs
        contents, system = self._build_messages_and_system(prompt, system_prompt)
        config = self._build_generate_content_config()
        if system:
            from google.genai import types  # type: ignore[import-not-found]

            if config is None:
                config = types.GenerateContentConfig(system_instruction=system)
            else:
                config.system_instruction = system

        kwargs: dict[str, Any] = {"model": self.model, "contents": contents}
        if config is not None:
            kwargs["config"] = config

        seen_citation_urls: set[str] = set()

        try:
            stream_iter = await self.client.aio.models.generate_content_stream(**kwargs)
            async for chunk in stream_iter:
                candidates = getattr(chunk, "candidates", None) or []
                if not candidates:
                    continue
                candidate = candidates[0]
                content = getattr(candidate, "content", None)
                parts = getattr(content, "parts", None) if content else None
                if parts:
                    for part in parts:
                        text = getattr(part, "text", "") or ""
                        if not text:
                            continue
                        if getattr(part, "thought", False):
                            yield StreamEvent(kind="reasoning", text=text)
                        else:
                            yield StreamEvent(kind="text", text=text)

                grounding = getattr(candidate, "grounding_metadata", None)
                if grounding is not None:
                    grounding_chunks = getattr(grounding, "grounding_chunks", None) or []
                    for gc in grounding_chunks:
                        web = getattr(gc, "web", None)
                        if web is None:
                            continue
                        url = getattr(web, "uri", None)
                        if not url or url in seen_citation_urls:
                            continue
                        seen_citation_urls.add(url)
                        title = getattr(web, "title", "") or urlparse(url).netloc
                        yield StreamEvent(
                            kind="citation",
                            text=str(title),
                            citation=Citation(title=str(title), url=str(url)),
                        )

            yield StreamEvent(kind="done", text="")

        except ModeKindMismatchError:
            raise  # propagate unmapped (per error-mapper convention)
        except Exception as e:
            raise _map_gemini_error(e, self.model, verbose=verbose) from e
