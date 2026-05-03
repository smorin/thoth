"""Tests for the enhanced APIKeyError multi-channel suggestion (P35 Layer 2).

The suggestion must enumerate all three input channels (env var, CLI flag,
config-file TOML), show status of EVERY provider's env var (not just the
failing one), and offer a "switch providers" hint. The title-line
`"{provider} API key not found"` is preserved verbatim — existing tests
in tests/test_api_key_resolver.py and tests/test_error_context.py still
assert on it.
"""

from __future__ import annotations

import pytest

from thoth.errors import APIKeyError


def _isolate_env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """Point config to a clean temp dir and unset all provider env vars."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    for name in ("OPENAI_API_KEY", "PERPLEXITY_API_KEY", "MOCK_API_KEY"):
        monkeypatch.delenv(name, raising=False)


def test_apikeyerror_title_line_preserved(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression: the title line must still contain '{provider} API key not found'."""
    _isolate_env(monkeypatch, tmp_path)
    err = APIKeyError("openai")
    assert "openai API key not found" in err.message


def test_apikeyerror_suggestion_lists_env_var_channel(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Suggestion shows the env-var input channel with provider-appropriate prefix."""
    _isolate_env(monkeypatch, tmp_path)
    err = APIKeyError("openai")
    assert err.suggestion is not None
    assert "OPENAI_API_KEY=sk-" in err.suggestion


def test_apikeyerror_suggestion_lists_cli_flag_channel(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Suggestion shows the --api-key-<provider> CLI flag input channel."""
    _isolate_env(monkeypatch, tmp_path)
    err = APIKeyError("openai")
    assert err.suggestion is not None
    assert "--api-key-openai" in err.suggestion


def test_apikeyerror_suggestion_lists_config_file_channel(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Suggestion shows the config-file [providers.X] TOML syntax."""
    _isolate_env(monkeypatch, tmp_path)
    err = APIKeyError("openai")
    assert err.suggestion is not None
    assert "[providers.openai]" in err.suggestion
    assert 'api_key = "' in err.suggestion


def test_apikeyerror_status_block_lists_all_providers(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Status block enumerates ALL providers' env vars, not just the failing one.

    Patches env so OPENAI_API_KEY is unset, PERPLEXITY_API_KEY is set,
    MOCK_API_KEY is unset; raises APIKeyError("openai"); asserts the
    suggestion includes all three with the right (set)/(unset) annotations.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-test")
    monkeypatch.delenv("MOCK_API_KEY", raising=False)

    err = APIKeyError("openai")
    assert err.suggestion is not None
    assert "OPENAI_API_KEY (unset)" in err.suggestion
    assert "PERPLEXITY_API_KEY (set)" in err.suggestion
    assert "MOCK_API_KEY (unset)" in err.suggestion


def test_apikeyerror_suggests_switching_providers(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Suggestion includes a `--provider <other>` hint to switch providers."""
    _isolate_env(monkeypatch, tmp_path)
    err = APIKeyError("openai")
    assert err.suggestion is not None
    assert "--provider" in err.suggestion
    # For openai failures, the first non-failing provider in PROVIDER_ENV_VARS
    # iteration order is perplexity.
    assert "perplexity" in err.suggestion


def test_apikeyerror_legacy_config_guidance_preserved(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: format_legacy_config_guidance() output is still appended.

    Force the helper to return a sentinel string and verify it appears in
    the final suggestion body.
    """
    _isolate_env(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "thoth.config_legacy.format_legacy_config_guidance",
        lambda: "LEGACY_GUIDANCE_MARKER",
    )
    err = APIKeyError("openai")
    assert err.suggestion is not None
    assert "LEGACY_GUIDANCE_MARKER" in err.suggestion
