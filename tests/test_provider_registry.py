"""PROVIDERS registry + create_provider factory tests.

Verifies that the R02 collapse of ProviderRegistry + legacy create_provider
into a single PROVIDERS dict + create_provider function keeps the public
contract: the factory looks up classes by name, raises on unknown names,
and resolves API keys via resolve_api_key.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from thoth import __main__ as thoth_main
from thoth.errors import ThothError
from thoth.providers import (
    PROVIDER_ENV_VARS,
    PROVIDERS,
    MockProvider,
    OpenAIProvider,
    PerplexityProvider,
    create_provider,
)


def _stub_config(providers: dict[str, dict]) -> SimpleNamespace:
    """Minimal ConfigManager shape: just .data['providers']."""
    return SimpleNamespace(data={"providers": providers})


def test_providers_dict_has_expected_keys() -> None:
    assert set(PROVIDERS) == {"openai", "perplexity", "mock"}


def test_providers_dict_maps_to_classes() -> None:
    assert PROVIDERS["openai"] is OpenAIProvider
    assert PROVIDERS["perplexity"] is PerplexityProvider
    assert PROVIDERS["mock"] is MockProvider


def test_provider_env_vars_keys_match_providers() -> None:
    assert set(PROVIDER_ENV_VARS) == set(PROVIDERS)


def test_create_provider_returns_mock_instance() -> None:
    config = _stub_config({"mock": {"api_key": "test-key"}})
    provider = create_provider("mock", config)
    assert isinstance(provider, MockProvider)
    assert provider.api_key == "test-key"


def test_create_provider_unknown_name_raises() -> None:
    config = _stub_config({})
    with pytest.raises(ThothError, match="Unknown provider"):
        create_provider("bogus", config)


def test_create_provider_rejects_invalid_mock_key() -> None:
    config = _stub_config({"mock": {"api_key": "invalid"}})
    with pytest.raises(ThothError, match="Invalid mock API key"):
        create_provider("mock", config)


def test_create_provider_is_reexported_from_main() -> None:
    assert thoth_main.create_provider is create_provider
    assert thoth_main.PROVIDERS is PROVIDERS
    assert thoth_main.MockProvider is MockProvider
