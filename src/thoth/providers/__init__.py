"""Provider registry and factory.

PROVIDERS is the single source of truth for name → class dispatch.
create_provider() handles API-key resolution plus provider-specific
config tweaks (mock validation, timeout override, mode-driven model,
is_background_mode derivation).
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from thoth.config import mode_kind
from thoth.errors import APIKeyError, ThothError
from thoth.providers.base import ResearchProvider
from thoth.providers.mock import MockProvider
from thoth.providers.openai import OpenAIProvider, _map_openai_error
from thoth.providers.perplexity import PerplexityProvider
from thoth.utils import _is_placeholder

if TYPE_CHECKING:
    from thoth.config import ConfigManager


PROVIDERS: dict[str, type[ResearchProvider]] = {
    "openai": OpenAIProvider,
    "perplexity": PerplexityProvider,
    "mock": MockProvider,
}

PROVIDER_ENV_VARS: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "perplexity": "PERPLEXITY_API_KEY",
    "mock": "MOCK_API_KEY",
}

PROVIDER_CLI_FLAGS: dict[str, str] = {
    "openai": "--api-key-openai",
    "perplexity": "--api-key-perplexity",
    "mock": "--api-key-mock",
}

_MODE_METADATA_KEYS: frozenset[str] = frozenset(
    {
        "provider",
        "providers",
        "model",
        "kind",
        "system_prompt",
        "description",
        "previous",
        "next",
        "auto_input",
        "parallel",
        "stream",
    }
)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = _deep_merge(existing, value)
        else:
            merged[key] = value
    return merged


def _apply_mode_provider_config(
    provider_name: str,
    provider_config: dict[str, Any],
    mode_config: dict[str, Any] | None,
) -> None:
    """Thread mode-level request settings into provider constructor config."""
    if not mode_config or provider_name not in ("openai", "perplexity"):
        return

    provider_names = set(PROVIDERS)
    for key, value in mode_config.items():
        if key in _MODE_METADATA_KEYS or key in provider_names:
            continue
        provider_config[key] = value

    provider_namespace = mode_config.get(provider_name)
    if isinstance(provider_namespace, dict):
        existing = provider_config.get(provider_name)
        base = existing if isinstance(existing, dict) else {}
        provider_config[provider_name] = _deep_merge(base, provider_namespace)


def resolve_api_key(
    provider_name: str,
    cli_api_key: str | None,
    provider_config: dict[str, Any],
    env_var_name: str | None = None,
) -> str:
    """Resolve a provider API key with precedence: CLI > env > config.

    Empty strings and unresolved `${VAR}` placeholders are treated as missing
    at every tier, so an empty --api-key flag falls through to the env var.
    Raises APIKeyError if nothing resolves.
    """
    env_name = env_var_name or PROVIDER_ENV_VARS.get(provider_name)

    if cli_api_key and not _is_placeholder(cli_api_key):
        return cli_api_key

    if env_name:
        env_val = os.getenv(env_name, "")
        if env_val and not _is_placeholder(env_val):
            return env_val

    cfg_val = provider_config.get("api_key", "") or ""
    if cfg_val and not _is_placeholder(cfg_val):
        return cfg_val

    raise APIKeyError(provider_name)


def available_providers(
    config: ConfigManager,
    cli_api_keys: dict[str, str | None] | None = None,
) -> list[str]:
    """Return list of provider names that have a resolvable API key.

    Checks CLI-supplied keys, env vars, and the loaded config (in
    ``resolve_api_key`` precedence order). Does NOT raise on missing keys;
    for dispatch logic that needs to discover what's available before
    calling ``create_provider``.

    Order matches ``PROVIDERS`` dict iteration so callers get a stable
    order (openai, perplexity, mock).
    """
    cli_api_keys = cli_api_keys or {}
    available: list[str] = []
    for name in PROVIDERS:
        cli_key = cli_api_keys.get(name)
        provider_config = config.data.get("providers", {}).get(name, {})
        try:
            resolve_api_key(name, cli_key, provider_config)
            available.append(name)
        except APIKeyError:
            continue
    return available


def create_provider(
    provider_name: str,
    config: ConfigManager,
    cli_api_key: str | None = None,
    timeout_override: float | None = None,
    mode_config: dict[str, Any] | None = None,
) -> ResearchProvider:
    """Create a provider instance with proper configuration and error handling.

    Replaces the old ProviderRegistry.create + create_provider duplication.
    Dispatch happens through the PROVIDERS registry dict; per-provider config
    shaping (timeout override, mode-driven model, is_background_mode-derived background)
    is applied before instantiation.
    """
    if provider_name not in PROVIDERS:
        raise ThothError(
            f"Unknown provider: {provider_name}",
            f"Valid providers are: {', '.join(sorted(PROVIDERS))}",
        )

    provider_config = config.data["providers"].get(provider_name, {}).copy()

    if provider_name == "mock":
        mock_api_key = resolve_api_key("mock", cli_api_key, provider_config)
        # Special validation for testing: reject "invalid" as API key
        if mock_api_key == "invalid":
            raise ThothError(
                "Invalid mock API key format",
                "Mock API key should not be 'invalid'",
            )
        return MockProvider(name=provider_name, delay=0.1, api_key=mock_api_key)

    api_key = resolve_api_key(provider_name, cli_api_key, provider_config)

    # Apply timeout override if provided
    if timeout_override is not None and provider_name in ("openai", "perplexity"):
        provider_config["timeout"] = timeout_override

    # Apply model from mode configuration if specified.
    # P23: extended from openai-only to perplexity. Generic passthrough; the
    # provider/API surfaces validation, not this factory.
    if mode_config and "model" in mode_config and provider_name in ("openai", "perplexity"):
        provider_config["model"] = mode_config["model"]

    _apply_mode_provider_config(provider_name, provider_config, mode_config)

    # Thread the mode's declared `kind` into provider_config so the OpenAI
    # provider's runtime validator (`_validate_kind_for_model`) can detect
    # mismatches before any HTTP call. P18.
    if mode_config and "kind" in mode_config:
        provider_config["kind"] = mode_config["kind"]

    # Apply background mode for deep research models. P18: resolution path
    # uses `mode_kind` (declared `kind` first; substring fallback for legacy).
    if provider_name == "openai" and mode_kind(provider_config) == "background":
        provider_config["background"] = True

    cls = PROVIDERS[provider_name]
    return cls(api_key=api_key, config=provider_config)


__all__ = [
    "PROVIDERS",
    "PROVIDER_CLI_FLAGS",
    "PROVIDER_ENV_VARS",
    "MockProvider",
    "OpenAIProvider",
    "PerplexityProvider",
    "ResearchProvider",
    "_map_openai_error",
    "available_providers",
    "create_provider",
    "resolve_api_key",
]
