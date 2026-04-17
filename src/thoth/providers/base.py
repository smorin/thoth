"""Base class for research providers.

ResearchProvider defines the contract every provider implements:
submit → check_status → get_result, plus optional list_models / reconnect.
"""

from __future__ import annotations

from typing import Any


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
