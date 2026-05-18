"""Preflight error: immediate modes cannot declare multiple providers.

Doxa has two separate model spaces upstream — immediate (fast,
single-provider, streaming) and Deep Research (long-running,
background, supports multi-provider fan-out). Mixing the two via an
immediate-kind mode with `providers: [a, b, c]` is rejected at
preflight, before any provider is instantiated.
"""

from __future__ import annotations

import asyncio

import pytest

from doxa_research.config import BUILTIN_MODES, ConfigManager
from doxa_research.errors import ImmediateMultiProviderError
from doxa_research.run import run_research


def _make_test_mode(monkeypatch: pytest.MonkeyPatch, name: str, cfg: dict) -> None:
    """Inject a synthetic mode into BUILTIN_MODES for one test."""
    new_modes = {**BUILTIN_MODES, name: cfg}
    monkeypatch.setattr("doxa_research.config.BUILTIN_MODES", new_modes)


def test_immediate_with_multiple_providers_raises_at_preflight(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An immediate-kind mode with `providers: [a, b]` errors before any
    provider client is constructed.
    """
    _make_test_mode(
        monkeypatch,
        "synthetic_bad",
        {
            "providers": ["openai", "perplexity"],
            "parallel": True,
            "kind": "immediate",
            "description": "synthetic test mode — should reject at preflight",
            "openai": {"model": "o3"},
            "perplexity": {"model": "sonar"},
        },
    )

    cm = ConfigManager()
    cm.load_all_layers({})

    async def _run() -> None:
        await run_research(
            mode="synthetic_bad",
            prompt="anything",
            async_mode=False,
            project=None,
            output_dir=None,
            provider=None,
            input_file=None,
            auto=False,
            verbose=False,
        )

    with pytest.raises(ImmediateMultiProviderError) as exc_info:
        asyncio.run(_run())
    assert "synthetic_bad" in exc_info.value.message
    assert exc_info.value.exit_code == 1


def test_error_message_explains_two_model_spaces(monkeypatch: pytest.MonkeyPatch) -> None:
    """The error suggestion must make the immediate/Deep-Research split
    explicit and point users at the right alternative.
    """
    _make_test_mode(
        monkeypatch,
        "synthetic_bad_2",
        {
            "providers": ["openai", "perplexity", "gemini"],
            "parallel": True,
            "kind": "immediate",
            "description": "synthetic",
            "openai": {"model": "o3"},
            "perplexity": {"model": "sonar"},
            "gemini": {"model": "gemini-2.5-flash-lite"},
        },
    )

    cm = ConfigManager()
    cm.load_all_layers({})

    async def _run() -> None:
        await run_research(
            mode="synthetic_bad_2",
            prompt="anything",
            async_mode=False,
            project=None,
            output_dir=None,
            provider=None,
            input_file=None,
            auto=False,
            verbose=False,
        )

    with pytest.raises(ImmediateMultiProviderError) as exc_info:
        asyncio.run(_run())

    suggestion = exc_info.value.suggestion or ""
    # The two model spaces must be named.
    assert "immediate" in suggestion.lower()
    assert "deep research" in suggestion.lower() or "deep_research" in suggestion.lower()
    # The multi-provider escape hatch must be pointed out.
    assert "all_deep_research" in suggestion
    # Single-provider quick alternatives must be mentioned.
    assert "_quick" in suggestion


def test_immediate_single_provider_still_works() -> None:
    """Don't regress single-provider immediate modes — openai_quick must
    still pass preflight cleanly.
    """
    cm = ConfigManager()
    cm.load_all_layers({})
    mode = cm.get_mode_config("openai_quick")
    assert mode["kind"] == "immediate"
    # provider singular field present, no plural providers list
    assert mode["provider"] == "openai"
    # No exception expected on this shape — preflight only rejects when
    # both immediate AND providers (plural) with > 1 entries.


def test_background_multi_provider_still_works() -> None:
    """Don't regress all_deep_research — background + multi-provider is
    the intended fan-out path.
    """
    cm = ConfigManager()
    cm.load_all_layers({})
    mode = cm.get_mode_config("all_deep_research")
    assert mode["kind"] == "background"
    assert mode["providers"] == ["openai", "perplexity", "gemini"]
