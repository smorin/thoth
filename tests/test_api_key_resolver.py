"""Tests for resolve_api_key() — unified CLI > env > config precedence."""

from __future__ import annotations

import pytest

from thoth.__main__ import (
    PROVIDER_ENV_VARS,
    APIKeyError,
    resolve_api_key,
)


def test_cli_beats_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "env-key")
    result = resolve_api_key(
        "openai",
        cli_api_key="cli-key",
        provider_config={"api_key": "cfg-key"},
    )
    assert result == "cli-key"


def test_env_beats_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "env-key")
    result = resolve_api_key(
        "openai",
        cli_api_key=None,
        provider_config={"api_key": "cfg-key"},
    )
    assert result == "env-key"


def test_missing_everywhere_raises_api_key_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(APIKeyError) as info:
        resolve_api_key(
            "openai",
            cli_api_key=None,
            provider_config={},
        )
    assert "openai API key not found" in info.value.message


def test_unresolved_placeholder_treated_as_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(APIKeyError):
        resolve_api_key(
            "openai",
            cli_api_key=None,
            provider_config={"api_key": "${OPENAI_API_KEY}"},
        )


def test_empty_cli_falls_through_to_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "env-key")
    result = resolve_api_key(
        "openai",
        cli_api_key="",
        provider_config={"api_key": "cfg-key"},
    )
    assert result == "env-key"


def test_provider_env_vars_covers_known_providers() -> None:
    assert PROVIDER_ENV_VARS["openai"] == "OPENAI_API_KEY"
    assert PROVIDER_ENV_VARS["perplexity"] == "PERPLEXITY_API_KEY"
    assert PROVIDER_ENV_VARS["mock"] == "MOCK_API_KEY"


def test_explicit_env_var_name_overrides_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CUSTOM_KEY", "custom-value")
    result = resolve_api_key(
        "openai",
        cli_api_key=None,
        provider_config={},
        env_var_name="CUSTOM_KEY",
    )
    assert result == "custom-value"
