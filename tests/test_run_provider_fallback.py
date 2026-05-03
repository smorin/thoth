"""Tests for P36 Layer 3 — multi-provider default fallback.

Covers two surfaces:

  1. ``available_providers(config, cli_api_keys=None)`` in
     ``thoth.providers`` — non-raising sibling of ``resolve_api_key`` that
     returns the list of providers whose keys resolve.
  2. ``_select_providers(...)`` in ``thoth.run`` — the extracted
     provider-selection helper that implements the precedence chain
     (explicit ``--provider`` > mode pin > ``general.default_provider``
     > first available > legacy ``["openai"]`` fallback).
"""

from __future__ import annotations

from typing import Any

import pytest

from thoth.config import ConfigManager


def _make_config(
    *,
    providers: dict[str, dict[str, Any]] | None = None,
    general: dict[str, Any] | None = None,
) -> ConfigManager:
    """Build a ConfigManager with only ``.data`` populated.

    ``available_providers`` and ``_select_providers`` only read
    ``config.data`` — they never call ``.load_all_layers`` or any other
    method — so we can construct an empty ``ConfigManager`` and assign
    ``.data`` directly.
    """
    cm = ConfigManager()
    cm.data = {
        "providers": providers or {},
        "general": general or {},
    }
    return cm


def _scrub_provider_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("OPENAI_API_KEY", "PERPLEXITY_API_KEY", "MOCK_API_KEY"):
        monkeypatch.delenv(var, raising=False)


# ---------------------------------------------------------------------------
# available_providers()
# ---------------------------------------------------------------------------


def test_available_providers_returns_only_those_with_resolvable_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from thoth.providers import available_providers

    _scrub_provider_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-real")
    config = _make_config()

    assert available_providers(config) == ["openai"]


def test_available_providers_returns_empty_when_no_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from thoth.providers import available_providers

    _scrub_provider_env(monkeypatch)
    config = _make_config()

    assert available_providers(config) == []


def test_available_providers_honors_dict_iteration_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from thoth.providers import available_providers

    _scrub_provider_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-real")
    monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-real")
    monkeypatch.setenv("MOCK_API_KEY", "mock-real")
    config = _make_config()

    assert available_providers(config) == ["openai", "perplexity", "mock"]


def test_available_providers_picks_up_config_file_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from thoth.providers import available_providers

    _scrub_provider_env(monkeypatch)
    config = _make_config(providers={"perplexity": {"api_key": "pplx-real"}})

    assert available_providers(config) == ["perplexity"]


def test_available_providers_picks_up_cli_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from thoth.providers import available_providers

    _scrub_provider_env(monkeypatch)
    config = _make_config()

    assert available_providers(config, cli_api_keys={"openai": "sk-cli"}) == ["openai"]


def test_available_providers_does_not_raise_on_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from thoth.providers import available_providers

    _scrub_provider_env(monkeypatch)
    config = _make_config()

    # Should return [] without raising APIKeyError.
    result = available_providers(config)
    assert result == []


# ---------------------------------------------------------------------------
# _select_providers()
# ---------------------------------------------------------------------------


def test_select_providers_picks_openai_when_only_openai_has_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from thoth.run import _select_providers

    _scrub_provider_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-real")
    config = _make_config()

    assert _select_providers(
        provider=None,
        mode="default",
        mode_config={},
        config=config,
        cli_api_keys=None,
    ) == ["openai"]


def test_select_providers_picks_perplexity_when_only_perplexity_has_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from thoth.run import _select_providers

    _scrub_provider_env(monkeypatch)
    monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-real")
    config = _make_config()

    assert _select_providers(
        provider=None,
        mode="default",
        mode_config={},
        config=config,
        cli_api_keys=None,
    ) == ["perplexity"]


def test_select_providers_respects_general_default_provider_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from thoth.run import _select_providers

    _scrub_provider_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-real")
    monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-real")
    config = _make_config(general={"default_provider": "perplexity"})

    assert _select_providers(
        provider=None,
        mode="default",
        mode_config={},
        config=config,
        cli_api_keys=None,
    ) == ["perplexity"]


def test_select_providers_general_default_ignored_if_unresolvable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from thoth.run import _select_providers

    _scrub_provider_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-real")
    config = _make_config(general={"default_provider": "perplexity"})

    # perplexity is configured as default but has no key — fall back to
    # first-available which is openai.
    assert _select_providers(
        provider=None,
        mode="default",
        mode_config={},
        config=config,
        cli_api_keys=None,
    ) == ["openai"]


def test_select_providers_zero_keys_returns_legacy_openai_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When nothing resolves, return ``["openai"]`` so create_provider
    raises L2's enhanced APIKeyError with full multi-provider enumeration.
    """
    from thoth.run import _select_providers

    _scrub_provider_env(monkeypatch)
    config = _make_config()

    assert _select_providers(
        provider=None,
        mode="default",
        mode_config={},
        config=config,
        cli_api_keys=None,
    ) == ["openai"]


def test_select_providers_explicit_provider_flag_always_wins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from thoth.run import _select_providers

    _scrub_provider_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-real")
    monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-real")
    config = _make_config(general={"default_provider": "perplexity"})

    # --provider mock wins regardless of any other config / env.
    assert _select_providers(
        provider="mock",
        mode="default",
        mode_config={},
        config=config,
        cli_api_keys=None,
    ) == ["mock"]


def test_select_providers_mode_provider_pin_wins_over_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A mode pinning a single provider wins over general.default_provider."""
    from thoth.run import _select_providers

    _scrub_provider_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-real")
    monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-real")
    config = _make_config(general={"default_provider": "openai"})

    assert _select_providers(
        provider=None,
        mode="research",
        mode_config={"provider": "perplexity"},
        config=config,
        cli_api_keys=None,
    ) == ["perplexity"]


def test_select_providers_mode_providers_list_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Modes pinning a providers list still get that list."""
    from thoth.run import _select_providers

    _scrub_provider_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-real")
    config = _make_config()

    assert _select_providers(
        provider=None,
        mode="research",
        mode_config={"providers": ["openai", "perplexity"]},
        config=config,
        cli_api_keys=None,
    ) == ["openai", "perplexity"]


def test_select_providers_thinking_mode_legacy_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The 'thinking' branch keeps the legacy ``mode_config.get('provider', 'openai')``
    behavior (existing pre-L3 contract).
    """
    from thoth.run import _select_providers

    _scrub_provider_env(monkeypatch)
    monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-real")
    config = _make_config(general={"default_provider": "perplexity"})

    # 'thinking' mode without a pinned provider falls through to "openai"
    # by historical contract; L3 doesn't change this branch.
    assert _select_providers(
        provider=None,
        mode="thinking",
        mode_config={},
        config=config,
        cli_api_keys=None,
    ) == ["openai"]


def test_select_providers_picks_up_cli_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A CLI-supplied key counts toward availability."""
    from thoth.run import _select_providers

    _scrub_provider_env(monkeypatch)
    config = _make_config()

    assert _select_providers(
        provider=None,
        mode="default",
        mode_config={},
        config=config,
        cli_api_keys={"perplexity": "pplx-cli"},
    ) == ["perplexity"]
