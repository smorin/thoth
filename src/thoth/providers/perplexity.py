"""Perplexity Sonar provider — synchronous immediate-path implementation.

Uses the OpenAI Python SDK in compatibility mode against
`https://api.perplexity.ai`. Per-request Perplexity-specific options live
under the `perplexity` mode-config namespace and are forwarded via
`extra_body` (any other shape raises TypeError per the SDK).
"""

from __future__ import annotations

import re
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any
from uuid import uuid4

import httpx
import openai
from openai import AsyncOpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from thoth.errors import (
    APIKeyError,
    APIQuotaError,
    ProviderError,
    ThothError,
)
from thoth.providers.base import ResearchProvider, StreamEvent

_THINK_PATTERN = re.compile(r"<think>(.*?)</think>", re.DOTALL)


def _split_think_segments(text: str) -> list[tuple[str, str]]:
    """Split text on `<think>...</think>` tags.

    Returns a list of ('reasoning', body) and ('text', body) tuples in
    document order. Handles tags that fully open-and-close within `text`;
    open tags without a matching close are treated as text (defensive —
    the model can drop the closing tag mid-stream per community report).
    """
    segments: list[tuple[str, str]] = []
    pos = 0
    for m in _THINK_PATTERN.finditer(text):
        if m.start() > pos:
            segments.append(("text", text[pos : m.start()]))
        segments.append(("reasoning", m.group(1)))
        pos = m.end()
    if pos < len(text):
        segments.append(("text", text[pos:]))
    return segments


_PROVIDER_NAME = "perplexity"


def _map_perplexity_error(
    exc: BaseException, model: str | None = None, verbose: bool = False
) -> ThothError:
    """Map an openai-SDK exception (or other) raised against Perplexity to a ThothError.

    Mirrors `_map_openai_error` shape but uses provider name "perplexity" and
    keeps the suggestion text Perplexity-specific.
    """
    raw = str(exc) if verbose else None

    if isinstance(exc, openai.AuthenticationError):
        return APIKeyError(_PROVIDER_NAME)

    if isinstance(exc, openai.RateLimitError):
        return APIQuotaError(_PROVIDER_NAME)

    if isinstance(exc, openai.PermissionDeniedError):
        return ProviderError(
            _PROVIDER_NAME,
            "Permission denied (check tier / model access).",
            raw_error=raw,
        )

    if isinstance(exc, openai.BadRequestError):
        hint = f" (model: {model})" if model else ""
        return ProviderError(
            _PROVIDER_NAME,
            f"Bad request{hint}. Check model name and request shape.",
            raw_error=raw,
        )

    if isinstance(exc, openai.APITimeoutError):
        return ProviderError(
            _PROVIDER_NAME,
            "Request timed out. Try again, or raise --timeout.",
            raw_error=raw,
        )

    if isinstance(exc, openai.APIConnectionError):
        return ProviderError(
            _PROVIDER_NAME,
            "Network connection error reaching api.perplexity.ai.",
            raw_error=raw,
        )

    if isinstance(exc, openai.InternalServerError):
        return ProviderError(
            _PROVIDER_NAME,
            "Perplexity server error (5xx). Retry shortly.",
            raw_error=raw,
        )

    if isinstance(exc, openai.APIError):
        return ProviderError(
            _PROVIDER_NAME,
            f"Perplexity API error: {exc}",
            raw_error=raw,
        )

    return ProviderError(
        _PROVIDER_NAME,
        f"Unexpected error: {exc}",
        raw_error=raw,
    )


PERPLEXITY_BASE_URL = "https://api.perplexity.ai"

_DIRECT_SDK_KEYS: tuple[str, ...] = (
    "max_tokens",
    "temperature",
    "top_p",
    "stop",
    "response_format",
)


class PerplexityProvider(ResearchProvider):
    """Perplexity research implementation (synchronous Sonar)."""

    def __init__(self, api_key: str, config: dict[str, Any] | None = None):
        self.api_key = api_key
        self.config = config or {}
        self.model = self.config.get("model", "sonar")
        self.jobs: dict[str, dict[str, Any]] = {}

        timeout = self.config.get("timeout", 30.0)
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=PERPLEXITY_BASE_URL,
            timeout=httpx.Timeout(timeout, connect=5.0),
        )

    def is_implemented(self) -> bool:
        return False

    def implementation_status(self) -> str | None:
        return "Not implemented"

    async def list_models(self) -> list[dict[str, Any]]:
        return [
            {"id": "sonar", "created": 1700000000, "owned_by": "perplexity"},
            {"id": "sonar-pro", "created": 1700000000, "owned_by": "perplexity"},
            {
                "id": "sonar-reasoning-pro",
                "created": 1700000000,
                "owned_by": "perplexity",
            },
        ]

    def _build_messages(self, prompt: str, system_prompt: str | None) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _build_extra_body(self) -> dict[str, Any]:
        """Forward `config['perplexity'].*` keys through to extra_body.

        Defaults applied when not configured:
        - web_search_options.search_context_size = "medium"
        - stream_mode = "concise"
        """
        perplexity_cfg: dict[str, Any] = dict(self.config.get("perplexity") or {})

        web_search_options = dict(perplexity_cfg.pop("web_search_options", {}) or {})
        web_search_options.setdefault("search_context_size", "medium")

        stream_mode = perplexity_cfg.pop("stream_mode", None) or "concise"

        extra_body: dict[str, Any] = {
            "web_search_options": web_search_options,
            "stream_mode": stream_mode,
        }
        extra_body.update(perplexity_cfg)
        return extra_body

    def _build_request_params(self, prompt: str, system_prompt: str | None) -> dict[str, Any]:
        params: dict[str, Any] = {
            "model": self.model,
            "messages": self._build_messages(prompt, system_prompt),
            "extra_body": self._build_extra_body(),
        }
        for key in _DIRECT_SDK_KEYS:
            if key in self.config:
                params[key] = self.config[key]
        return params

    async def submit(
        self,
        prompt: str,
        mode: str,
        system_prompt: str | None = None,
        verbose: bool = False,
    ) -> str:
        """One-shot synchronous chat completion.

        Wraps the inner retryable call to map any openai.* exception to a
        ThothError before reaching the caller.
        """
        try:
            response = await self._submit_with_retry(prompt, system_prompt)
        except (openai.APIError, Exception) as exc:
            raise _map_perplexity_error(exc, model=self.model, verbose=verbose) from exc

        job_id = (
            getattr(response, "id", None)
            or f"perplexity-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}"
        )
        self.jobs[job_id] = {"response": response, "created_at": datetime.now()}
        return job_id

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((openai.APITimeoutError, openai.APIConnectionError)),
        reraise=True,
    )
    async def _submit_with_retry(self, prompt: str, system_prompt: str | None) -> Any:
        params = self._build_request_params(prompt, system_prompt)
        return await self.client.chat.completions.create(**params)

    async def stream(
        self,
        prompt: str,
        mode: str,
        system_prompt: str | None = None,
        verbose: bool = False,
    ) -> AsyncIterator[StreamEvent]:
        """Translate Perplexity's streaming chunks into StreamEvent."""
        params = self._build_request_params(prompt, system_prompt)
        params["stream"] = True

        try:
            stream = await self.client.chat.completions.create(**params)
        except (openai.APIError, Exception) as exc:
            raise _map_perplexity_error(exc, model=self.model, verbose=verbose) from exc

        accumulated = ""
        is_reasoning_model = "reasoning" in self.model
        last_search_results: list[Any] = []

        async for chunk in stream:
            sr = getattr(chunk, "search_results", None)
            if sr:
                last_search_results = list(sr)

            choices = getattr(chunk, "choices", None) or []
            if not choices:
                continue
            delta = getattr(choices[0], "delta", None)
            if delta is None:
                continue
            content = getattr(delta, "content", None)
            if not content:
                continue

            # Cumulative-content guard: if `content` starts with what we've
            # already seen, the API is sending cumulative state per chunk;
            # peel off only the new tail.
            if accumulated and content.startswith(accumulated):
                new_text = content[len(accumulated) :]
                accumulated = content
            else:
                new_text = content
                accumulated += content

            if not new_text:
                continue

            if is_reasoning_model:
                for kind, body in _split_think_segments(new_text):
                    if not body:
                        continue
                    if kind == "reasoning":
                        yield StreamEvent(kind="reasoning", text=body)
                    else:
                        yield StreamEvent(kind="text", text=body)
            else:
                yield StreamEvent(kind="text", text=new_text)

        seen_urls: set[str] = set()
        for entry in last_search_results:
            url = _entry_get(entry, "url") or ""
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            title = _entry_get(entry, "title") or url
            yield StreamEvent(kind="citation", text=f"{title}|{url}")

        yield StreamEvent(kind="done", text="")

    async def check_status(self, job_id: str) -> dict[str, Any]:
        if job_id not in self.jobs:
            return {"status": "not_found", "error": "Job not found"}
        return {"status": "completed", "progress": 1.0}

    async def get_result(self, job_id: str, verbose: bool = False) -> str:
        if job_id not in self.jobs:
            raise ProviderError("perplexity", f"Unknown job_id: {job_id}")
        response = self.jobs[job_id]["response"]
        return _render_answer_with_sources(response)


def _render_answer_with_sources(response: Any) -> str:
    """Extract content + append a deduped `## Sources` block from search_results."""
    choices = getattr(response, "choices", None) or []
    content = ""
    if choices:
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", "") or ""

    search_results = getattr(response, "search_results", None) or []
    seen_urls: set[str] = set()
    sources: list[str] = []
    for entry in search_results:
        url = _entry_get(entry, "url") or ""
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        title = _entry_get(entry, "title") or url
        sources.append(f"- [{title}]({url})")

    if not sources:
        return content
    return f"{content}\n\n## Sources\n\n" + "\n".join(sources)


def _entry_get(entry: Any, key: str) -> Any:
    if isinstance(entry, dict):
        return entry.get(key)
    return getattr(entry, key, None)
