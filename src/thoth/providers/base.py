"""Base class for research providers.

ResearchProvider defines the contract every provider implements:
submit → check_status → get_result, plus optional list_models / reconnect /
stream / cancel.

P18 added:
- `stream(prompt, mode, ...) -> AsyncIterator[StreamEvent]`: live token
  delivery for immediate-kind runs. Default raises NotImplementedError;
  subclasses opt in. The immediate execution path will fall back to
  submit + get_result if a provider doesn't implement stream.
- `cancel(job_id)`: best-effort upstream cancel for in-flight background
  jobs. Default raises NotImplementedError; the `thoth cancel` CLI catches
  and reports "upstream cancel not supported".
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Literal


@dataclass
class Citation:
    """Structured citation metadata from providers that stream sources."""

    title: str
    url: str


@dataclass
class StreamEvent:
    """One chunk emitted by `provider.stream()`.

    `kind` distinguishes text deltas from sidechannel events:
      * "text"      — main content delta; the typical case
      * "reasoning" — model reasoning summary chunk (optional, future)
      * "citation"  — annotation/citation metadata (optional, future)
      * "done"      — terminal marker; no more events follow

    Callers should treat unknown kinds as future-proof: skip what they
    don't recognize; don't error.
    """

    kind: Literal["text", "reasoning", "citation", "done"]
    text: str
    citation: Citation | None = None


class ResearchProvider:
    """Base class for research providers"""

    def __init__(self, api_key: str = "", config: dict[str, Any] | None = None):
        self.api_key = api_key
        self.config = config or {}

    async def submit(
        self, prompt: str, mode: str, system_prompt: str | None = None, verbose: bool = False
    ) -> str:
        """Submit research and return job ID"""
        raise NotImplementedError

    async def check_status(self, job_id: str) -> dict[str, Any]:
        """Check job status with progress information"""
        raise NotImplementedError

    async def get_result(self, job_id: str, verbose: bool = False) -> str:
        """Get the final result content"""
        raise NotImplementedError

    def supports_progress(self) -> bool:
        """Whether this provider supports progress reporting"""
        return False

    async def list_models(self) -> list[dict[str, Any]]:
        """List available models for this provider"""
        raise NotImplementedError

    async def list_models_cached(
        self, force_refresh: bool = False, no_cache: bool = False
    ) -> list[dict[str, Any]]:
        """List available models with caching support

        Args:
            force_refresh: If True, bypass cache and update with fresh data
            no_cache: If True, bypass cache without updating it

        Returns:
            List of model dictionaries
        """
        # Default implementation without caching - subclasses can override
        if no_cache:
            # Bypass cache completely without updating
            return await self.list_models()
        return await self.list_models()

    def is_implemented(self) -> bool:
        """Whether this provider is currently operational for research runs."""
        return True

    def implementation_status(self) -> str | None:
        """Optional user-facing implementation status string."""
        return None

    async def reconnect(self, job_id: str) -> None:
        """Reattach to an existing background job after a fresh process start.

        Subclasses that support resume override this to repopulate internal
        job state from a persisted job identifier.
        """
        raise NotImplementedError(f"{type(self).__name__} does not support resume/reconnect")

    async def stream(
        self,
        prompt: str,
        mode: str,
        system_prompt: str | None = None,
        verbose: bool = False,
    ) -> AsyncIterator[StreamEvent]:
        """Yield content chunks for immediate-mode use.

        P18: subclasses opt in by implementing this; the default raises
        NotImplementedError so the immediate-execution path can fall back
        to submit + get_result for providers that don't support streaming.

        Should yield a terminal `StreamEvent(kind="done", text="")` so
        callers can detect end-of-stream without relying on iterator
        exhaustion.
        """
        raise NotImplementedError(f"{type(self).__name__} does not support streaming")
        # Unreachable; pleases the static checkers expecting an async generator.
        if False:  # pragma: no cover
            yield StreamEvent(kind="done", text="")

    async def cancel(self, job_id: str) -> dict[str, Any]:
        """Best-effort cancel of an in-flight job. Returns final status dict.

        P18: subclasses with upstream cancel support override; otherwise the
        default raises NotImplementedError. The `thoth cancel` CLI catches
        and reports "upstream cancel not supported, local checkpoint marked
        cancelled" so the operation is at least locally cancelled.
        """
        raise NotImplementedError(f"{type(self).__name__} does not support cancel")
