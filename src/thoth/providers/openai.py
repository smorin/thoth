"""OpenAI Responses API provider for Deep Research."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from uuid import uuid4

import httpx
import openai
from openai import AsyncOpenAI
from rich.console import Console
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from thoth.config import is_background_model
from thoth.errors import APIKeyError, APIQuotaError, ProviderError, ThothError
from thoth.models import ModelCache
from thoth.providers.base import ResearchProvider

_console = Console()


def _map_openai_error(
    exc: BaseException, model: str | None = None, verbose: bool = False
) -> ThothError:
    """Map an openai SDK exception to a Thoth error type.

    Ordering note: APITimeoutError is a subclass of APIConnectionError, so it is
    checked first. RateLimitError inspects body/code to route insufficient_quota
    specifically to APIQuotaError.
    """
    raw = str(exc) if verbose else None

    if isinstance(exc, openai.AuthenticationError):
        msg = str(exc).lower()
        if "incorrect api key" in msg:
            return ThothError(
                "Invalid OpenAI API key",
                "Please check your API key at https://platform.openai.com/account/api-keys",
            )
        return APIKeyError("openai")

    if isinstance(exc, openai.RateLimitError):
        body = getattr(exc, "body", None) or {}
        body_str = str(body)
        code = None
        if isinstance(body, dict):
            err = body.get("error") if isinstance(body.get("error"), dict) else None
            if isinstance(err, dict):
                code = err.get("code")
        if code == "insufficient_quota" or "insufficient_quota" in body_str:
            return APIQuotaError("openai")
        return ProviderError(
            "openai",
            "Rate limit exceeded. Please wait a moment and try again.",
            raw_error=raw,
        )

    if isinstance(exc, openai.NotFoundError):
        return ProviderError(
            "openai",
            f"Model '{model}' not found. Please check available models with "
            f"'thoth providers -- --models --provider openai'",
            raw_error=raw,
        )

    if isinstance(exc, openai.BadRequestError):
        msg = str(exc)
        msg_lower = msg.lower()
        if "unsupported parameter" in msg_lower and "temperature" in msg_lower:
            return ProviderError(
                "openai",
                f"Model '{model}' does not support temperature parameter. "
                "This is likely a response model (o3, o3-deep-research, etc.)",
                raw_error=raw,
            )
        if "unsupported parameter" in msg_lower:
            param_match = re.search(r"'(\w+)'", msg)
            param_name = param_match.group(1) if param_match else "unknown"
            return ProviderError(
                "openai",
                f"Model '{model}' does not support parameter '{param_name}'",
                raw_error=raw,
            )
        return ProviderError("openai", f"Invalid request: {msg}", raw_error=raw)

    if isinstance(exc, openai.PermissionDeniedError):
        return ProviderError("openai", "Permission denied by OpenAI API.", raw_error=raw)

    if isinstance(exc, openai.InternalServerError):
        return ProviderError(
            "openai",
            "OpenAI server error. Try again in a moment.",
            raw_error=raw,
        )

    if isinstance(exc, openai.APITimeoutError):
        return ProviderError(
            "openai",
            "Request timed out. Try increasing timeout in config.",
            raw_error=raw,
        )

    if isinstance(exc, openai.APIConnectionError):
        return ProviderError(
            "openai",
            "Failed to connect to OpenAI API. Check your internet connection.",
            raw_error=raw,
        )

    if isinstance(exc, openai.APIError):
        return ProviderError("openai", str(exc), raw_error=raw)

    return ProviderError("openai", str(exc), raw_error=raw)


class OpenAIProvider(ResearchProvider):
    """OpenAI Responses API implementation for Deep Research"""

    def __init__(self, api_key: str, config: dict[str, Any] | None = None):
        self.api_key = api_key
        self.config = config or {}
        # Model will be passed from mode configuration, default to o3
        self.model = self.config.get("model", "o3")
        self.jobs: dict[str, dict[str, Any]] = {}  # Store job information for async tracking
        self.model_cache = ModelCache("openai")  # Initialize cache for OpenAI

        # Add timeout configuration
        timeout = self.config.get("timeout", 30.0)
        self.client = AsyncOpenAI(api_key=api_key, timeout=httpx.Timeout(timeout, connect=5.0))

    async def submit(
        self, prompt: str, mode: str, system_prompt: str | None = None, verbose: bool = False
    ) -> str:
        """Submit research using OpenAI Responses API.

        Raw openai.* exceptions from the retryable inner call are mapped here to
        ThothError subclasses so callers always see a single error taxonomy.
        """
        try:
            return await self._submit_with_retry(prompt, mode, system_prompt, verbose)
        except (openai.APIError, Exception) as e:
            raise _map_openai_error(e, model=self.model, verbose=verbose) from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((openai.APITimeoutError, openai.APIConnectionError)),
        reraise=True,
    )
    async def _submit_with_retry(
        self, prompt: str, mode: str, system_prompt: str | None, verbose: bool
    ) -> str:
        """Inner retryable submit. Raises raw openai.* exceptions."""
        # Build structured input format for Responses API
        input_messages: list[dict[str, Any]] = []

        if system_prompt:
            input_messages.append(
                {
                    "role": "developer",
                    "content": [{"type": "input_text", "text": system_prompt}],
                }
            )

        input_messages.append({"role": "user", "content": [{"type": "input_text", "text": prompt}]})

        # Configure tools based on model type
        tools: list[dict[str, Any]] = []
        if is_background_model(self.model):
            tools = [{"type": "web_search_preview"}]
            if self.config.get("code_interpreter", True):
                tools.append({"type": "code_interpreter", "container": {"type": "auto"}})

        # Determine if background mode should be used
        # Background for deep-research models (via is_background_model) or explicit config
        use_background = is_background_model(self.model) or self.config.get("background", False)

        # Get configuration parameters
        temperature = self.config.get("temperature", 0.7)

        # Build request parameters
        request_params: dict[str, Any] = {
            "model": self.model,
            "input": input_messages,
            "reasoning": {"summary": "auto"},  # Enable reasoning summaries
            "tools": tools,
            "background": use_background,
        }

        # Only add temperature for models that support it
        # Response models (o3, o3-deep-research, o4-mini-deep-research) don't support temperature
        if not self.model.startswith("o"):
            request_params["temperature"] = temperature

        # Apply max_tool_calls if configured — primary lever for cost and latency control
        max_tool_calls = self.config.get("max_tool_calls")
        if max_tool_calls is not None:
            request_params["max_tool_calls"] = max_tool_calls

        # Use Responses API
        response = await self.client.responses.create(**request_params)

        # Store job information
        job_id = (
            response.id
            if hasattr(response, "id")
            else f"openai-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}"
        )
        self.jobs[job_id] = {
            "response": response,
            "background": use_background,
            "created_at": datetime.now(),
        }

        return job_id

    async def check_status(self, job_id: str) -> dict[str, Any]:
        """Check actual status of research task"""
        if job_id not in self.jobs:
            return {"status": "not_found", "error": "Job not found"}

        job_info = self.jobs[job_id]

        # If not background mode, it's already completed
        if not job_info.get("background", False):
            return {"status": "completed", "progress": 1.0}

        try:
            # Poll the Responses API for status of background job
            response = await self.client.responses.retrieve(job_id)

            if hasattr(response, "status"):
                if response.status == "completed":
                    # Update stored response with completed data
                    self.jobs[job_id]["response"] = response
                    return {"status": "completed", "progress": 1.0}
                elif response.status == "in_progress":
                    # Try to get progress from metadata
                    progress = 0.5  # Default progress
                    if hasattr(response, "metadata") and response.metadata:
                        progress = response.metadata.get("progress", 0.5)
                    return {"status": "running", "progress": progress}
                elif response.status == "failed":
                    error_msg = getattr(response, "error", "Unknown error")
                    return {"status": "permanent_error", "error": str(error_msg)}
                elif response.status == "incomplete":
                    error_msg = (
                        getattr(response, "error", None)
                        or "Response was incomplete (output truncated)"
                    )
                    return {"status": "permanent_error", "error": str(error_msg)}
                elif response.status == "cancelled":
                    return {"status": "cancelled", "error": "Response was cancelled"}
                elif response.status == "queued":
                    return {"status": "queued", "progress": 0.0}
                else:
                    return {
                        "status": "permanent_error",
                        "error": f"Unexpected API status: {response.status!r}",
                    }
            else:
                return {
                    "status": "permanent_error",
                    "error": "Response object has no status attribute",
                }
        except (
            openai.APIConnectionError,
            openai.APITimeoutError,
            openai.RateLimitError,
            openai.InternalServerError,
        ) as e:
            cached = job_info.get("response")
            if cached and getattr(cached, "status", None) == "completed":
                return {"status": "completed", "progress": 1.0}
            return {
                "status": "transient_error",
                "error": str(e),
                "error_class": type(e).__name__,
            }
        except (
            openai.AuthenticationError,
            openai.PermissionDeniedError,
            openai.BadRequestError,
            openai.NotFoundError,
        ) as e:
            return {
                "status": "permanent_error",
                "error": str(e),
                "error_class": type(e).__name__,
            }
        except Exception as e:
            # Unknown — treat as transient so we don't kill long jobs over novel errors.
            cached = job_info.get("response")
            if cached and getattr(cached, "status", None) == "completed":
                return {"status": "completed", "progress": 1.0}
            return {
                "status": "transient_error",
                "error": f"Unexpected error ({type(e).__name__}): {e}",
                "error_class": type(e).__name__,
            }

    async def reconnect(self, job_id: str) -> None:
        """Re-attach to an existing background job after a fresh process start."""
        response = await self.client.responses.retrieve(job_id)
        self.jobs[job_id] = {
            "response": response,
            "background": True,
            "created_at": datetime.now(),
        }

    async def get_result(self, job_id: str, verbose: bool = False) -> str:
        """Get the Deep Research result"""
        if job_id not in self.jobs:
            raise ValueError("Job not found")

        job_info = self.jobs[job_id]

        # If background mode, retrieve the latest response
        if job_info.get("background", False):
            try:
                response = await self.client.responses.retrieve(job_id)
                job_info["response"] = response  # Update cached response
            except Exception as e:
                # Use cached response if retrieval fails
                response = job_info.get("response")
                if not response:
                    return f"Error retrieving result: {str(e)}"
        else:
            response = job_info.get("response")

        if not response:
            return "No response available"

        # Extract content based on response structure
        content = ""
        citations: list[dict[str, str]] = []

        # Handle different response formats
        if hasattr(response, "output"):
            # Responses API format
            if isinstance(response.output, list):
                # Select the final assistant message instead of concatenating commentary.
                message_items = [
                    item for item in response.output if getattr(item, "type", None) == "message"
                ]
                target_message = (
                    next(
                        (
                            item
                            for item in reversed(message_items)
                            if getattr(item, "phase", None) == "final_answer"
                            and getattr(item, "status", None) == "completed"
                        ),
                        None,
                    )
                    or next(
                        (
                            item
                            for item in reversed(message_items)
                            if getattr(item, "status", None) == "completed"
                        ),
                        None,
                    )
                    or (message_items[-1] if message_items else None)
                )

                texts = []
                if target_message and hasattr(target_message, "content"):
                    if isinstance(target_message.content, list):
                        for content_item in target_message.content:
                            item_type = getattr(content_item, "type", None)
                            if item_type == "output_text" or (
                                item_type is None and hasattr(content_item, "text")
                            ):
                                texts.append(getattr(content_item, "text", ""))
                                for ann in getattr(content_item, "annotations", None) or []:
                                    url = getattr(ann, "url", None) or (
                                        ann.get("url") if isinstance(ann, dict) else None
                                    )
                                    title = getattr(ann, "title", None) or (
                                        ann.get("title") if isinstance(ann, dict) else url
                                    )
                                    if url:
                                        citations.append({"url": url, "title": title or url})
                    else:
                        texts.append(str(target_message.content))
                content = "\n".join(texts) if texts else ""
            elif isinstance(response.output, dict):
                content = response.output.get("content", "")
            elif isinstance(response.output, str):
                content = response.output
            elif hasattr(response.output, "content"):
                content = response.output.content
        elif hasattr(response, "choices"):
            # Chat-style response format (might be returned by responses API for non-background)
            if response.choices and len(response.choices) > 0:
                # Check if it's a message or direct content
                choice = response.choices[0]
                if hasattr(choice, "message") and hasattr(choice.message, "content"):
                    content = choice.message.content
                elif hasattr(choice, "text"):
                    content = choice.text
                elif hasattr(choice, "content"):
                    content = choice.content
        elif hasattr(response, "content"):
            content = response.content
        elif hasattr(response, "text"):
            content = response.text

        # When no content can be extracted, log debug info to console (verbose only)
        if not content and response:
            if verbose:
                try:
                    if hasattr(response, "model_dump_json"):
                        debug_info = response.model_dump_json()
                    elif hasattr(response, "__dict__"):
                        debug_info = str(
                            {
                                k: str(v)[:100]
                                for k, v in response.__dict__.items()
                                if not k.startswith("_")
                            }
                        )
                    else:
                        debug_info = repr(response)
                except Exception:
                    debug_info = f"<{type(response).__name__}>"
                _console.print(
                    f"[dim]Debug: no content found in response. Structure: {debug_info}[/dim]"
                )
            return "No content in response"

        # Extract reasoning from the new format if available
        reasoning_content = ""
        if hasattr(response, "output") and isinstance(response.output, list):
            for item in response.output:
                if hasattr(item, "type") and item.type == "reasoning":
                    if hasattr(item, "summary") and item.summary:
                        if isinstance(item.summary, list):
                            parts = []
                            for s in item.summary:
                                text_attr = getattr(s, "text", None)
                                parts.append(str(text_attr) if text_attr is not None else str(s))
                            reasoning_content = "\n".join(parts)
                        else:
                            reasoning_content = str(item.summary)
                    break

        # Include reasoning summary if available (either from new format or old format)
        if reasoning_content:
            content = f"## Reasoning Summary\n{reasoning_content}\n\n{content}"
        elif hasattr(response, "reasoning") and response.reasoning:
            if isinstance(response.reasoning, dict) and response.reasoning.get("summary"):
                reasoning_summary = response.reasoning["summary"]
                content = f"## Reasoning Summary\n{reasoning_summary}\n\n{content}"

        # Append deduplicated sources section when citations are present
        if citations:
            seen: set[str] = set()
            source_lines: list[str] = []
            for c in citations:
                if c["url"] not in seen:
                    seen.add(c["url"])
                    source_lines.append(f"- [{c['title']}]({c['url']})")
            content += "\n\n## Sources\n\n" + "\n".join(source_lines)

        return content if content else "No content in response"

    async def list_models(self) -> list[dict[str, Any]]:
        """List available models including Responses API models"""
        # Start with known Responses API models
        response_models = [
            {
                "id": "o3",
                "type": "response",
                "description": "Standard response model for general tasks",
                "created": 1719500000,  # Approximate timestamp
                "owned_by": "openai",
            },
            {
                "id": "o3-deep-research",
                "type": "deep_research",
                "description": "Full deep research model with web search and code execution",
                "created": 1719500001,
                "owned_by": "openai",
            },
            {
                "id": "o4-mini-deep-research",
                "type": "deep_research",
                "description": "Fast lightweight research model for quick answers",
                "created": 1719500002,
                "owned_by": "openai",
            },
        ]

        # Also try to fetch other models from API
        try:
            response = await self.client.models.list()
            api_models = []
            for model in response.data:
                # Include all models without filtering
                # Don't duplicate the response models we already added
                if model.id not in ["o3", "o3-deep-research", "o4-mini-deep-research"]:
                    api_models.append(
                        {
                            "id": model.id,
                            "created": model.created,
                            "owned_by": model.owned_by,
                            "type": "unknown",  # Mark type as unknown for unfiltered models
                        }
                    )
            # Combine and sort all models
            all_models = response_models + api_models
            return sorted(all_models, key=lambda x: x.get("created", 0), reverse=True)
        except Exception as e:
            raise ProviderError("openai", f"Failed to fetch models: {str(e)}")

    async def list_models_cached(
        self, force_refresh: bool = False, no_cache: bool = False
    ) -> list[dict[str, Any]]:
        """List OpenAI models with caching support

        Args:
            force_refresh: If True, bypass cache and fetch fresh data
            no_cache: If True, bypass cache without updating it

        Returns:
            List of model dictionaries from cache or API
        """
        # If no_cache is True, bypass cache without updating
        if no_cache:
            return await self.list_models()

        # Check if cache is valid
        if not force_refresh and self.model_cache.is_cache_valid():
            # Try to load from cache
            cached_models = self.model_cache.load_cache()
            if cached_models is not None:
                return cached_models

        # Fetch fresh models from API
        models = await self.list_models()

        # Save to cache (only when not using no_cache)
        self.model_cache.save_cache(models)

        return models
