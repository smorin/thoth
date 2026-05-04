"""Gemini synchronous chat provider (P24).

Mirrors the P23 Perplexity provider pattern: built-in modes with a
[modes.X.gemini] namespace, side-channel stream events for reasoning and
citation, error mapper with _map_gemini_error, tenacity retry on submit.

Uses the official google-genai SDK (>=1.74.0), NOT Gemini's OpenAI-compat
endpoint, because the compat layer omits grounding metadata, thought parts,
and the thinking-budget knob.
"""

from __future__ import annotations

from typing import Any

from thoth.providers.base import ResearchProvider

_PROVIDER_NAME_GEMINI = "gemini"

_DIRECT_SDK_KEYS_GEMINI: tuple[str, ...] = (
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
