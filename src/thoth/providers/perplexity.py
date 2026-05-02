"""Perplexity research provider (not yet implemented)."""

from __future__ import annotations

from typing import Any

from thoth.errors import ProviderError
from thoth.providers.base import ResearchProvider


class PerplexityProvider(ResearchProvider):
    """Perplexity research implementation"""

    def __init__(self, api_key: str, config: dict[str, Any] | None = None):
        self.api_key = api_key
        self.config = config or {}
        self.model = self.config.get("model", "sonar")

    async def submit(
        self, prompt: str, mode: str, system_prompt: str | None = None, verbose: bool = False
    ) -> str:
        """Submit to Perplexity"""
        raise ProviderError(
            "perplexity",
            "Perplexity provider is not implemented yet. Use openai or mock until Perplexity support lands.",
        )

    def is_implemented(self) -> bool:
        return False

    def implementation_status(self) -> str | None:
        return "Not implemented"

    async def list_models(self) -> list[dict[str, Any]]:
        """Return hardcoded Perplexity models as specified"""
        return [
            {
                "id": "sonar-deep-research",
                "created": 1700000000,
                "owned_by": "perplexity",
            }
        ]
