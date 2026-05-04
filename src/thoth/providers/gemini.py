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
