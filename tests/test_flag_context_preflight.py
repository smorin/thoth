"""Preflight: flags must be used in the right context.

Standardization #4: stop silently ignoring flags passed in the wrong
context. Three checks at preflight:

  1. --out      on background-kind mode → error
  2. --append   on background-kind mode → error
  3. --combined on single-provider mode → error

The principle (same as ImmediateMultiProviderError in aa7d070): every
flag means one thing and refuses to be silently ignored.
"""

from __future__ import annotations

import asyncio

import pytest

from doxa_research.errors import (
    BackgroundFlagError,
    CombinedNeedsMultiProviderError,
)
from doxa_research.run import run_research


def _call(
    *,
    mode: str = "default",
    out_specs: tuple[str, ...] = (),
    append: bool = False,
    combined: bool = False,
) -> None:
    """Invoke run_research with the minimum surface this test file exercises."""
    asyncio.run(
        run_research(
            mode=mode,
            prompt="ping",
            async_mode=False,
            project=None,
            output_dir=None,
            provider=None,
            input_file=None,
            auto=False,
            verbose=False,
            out_specs=out_specs,
            append=append,
            combined=combined,
        )
    )


# ---------------------------------------------------------------------------
# --out on background-kind mode
# ---------------------------------------------------------------------------


def test_out_on_background_mode_raises() -> None:
    """--out PATH is for immediate streaming; rejecting on background avoids
    silent no-op and steers users to --output-dir."""
    with pytest.raises(BackgroundFlagError) as exc_info:
        _call(mode="deep_research", out_specs=("file.md",))
    assert exc_info.value.flag_name == "--out"
    assert "deep_research" in exc_info.value.message
    assert exc_info.value.exit_code == 1


def test_out_on_immediate_mode_does_not_raise_preflight(monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression: --out PATH on immediate stays past preflight.

    Monkeypatch `create_provider` to a stub so we don't hit a real
    provider — the only thing this test cares about is that the preflight
    check doesn't reject the combination.
    """
    from unittest.mock import MagicMock

    monkeypatch.setattr(
        "doxa_research.run.create_provider",
        lambda *a, **kw: MagicMock(model="stub", api_key="stub", config={}),
    )
    # Stop dispatch after preflight — any later RuntimeError is fine as long
    # as it's not BackgroundFlagError.
    try:
        _call(mode="default", out_specs=("file.md",))
    except BackgroundFlagError:
        pytest.fail("--out on immediate mode must not raise BackgroundFlagError")
    except Exception:
        pass  # any other failure past preflight is out of scope


# ---------------------------------------------------------------------------
# --append on background-kind mode
# ---------------------------------------------------------------------------


def test_append_on_background_mode_raises() -> None:
    """--append is for --out file sinks; rejecting on background prevents
    silent ignore and clarifies the flag's actual scope."""
    with pytest.raises(BackgroundFlagError) as exc_info:
        _call(mode="deep_research", append=True)
    assert exc_info.value.flag_name == "--append"


# ---------------------------------------------------------------------------
# --combined on single-provider mode
# ---------------------------------------------------------------------------


def test_combined_on_single_provider_mode_raises() -> None:
    """--combined synthesizes a unified report from multiple per-provider
    outputs; single-provider runs have nothing to combine."""
    # The 'default' mode is single-provider (openai). --combined here makes
    # no sense.
    with pytest.raises(CombinedNeedsMultiProviderError) as exc_info:
        _call(mode="default", combined=True)
    assert "default" in exc_info.value.message
    assert exc_info.value.exit_code == 1


def test_combined_on_multi_provider_background_passes_preflight(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression: --combined on all_deep_research stays past preflight.

    Monkeypatch the provider factory so we don't hit live APIs; the test
    only needs to verify that preflight doesn't reject the combination.
    """
    from unittest.mock import MagicMock

    monkeypatch.setattr(
        "doxa_research.run.create_provider",
        lambda *a, **kw: MagicMock(model="stub", api_key="stub", config={}),
    )
    try:
        _call(mode="all_deep_research", combined=True)
    except CombinedNeedsMultiProviderError:
        pytest.fail("--combined on multi-provider background must not raise")
    except Exception:
        pass  # downstream provider-submit errors past preflight are unrelated


# ---------------------------------------------------------------------------
# Error message contents
# ---------------------------------------------------------------------------


def test_background_flag_error_explains_alternative() -> None:
    """The BackgroundFlagError suggestion must point users at the right flag
    (--output-dir / --project)."""
    with pytest.raises(BackgroundFlagError) as exc_info:
        _call(mode="deep_research", out_specs=("file.md",))
    suggestion = exc_info.value.suggestion or ""
    assert "--output-dir" in suggestion or "--project" in suggestion


def test_combined_error_explains_multi_provider_modes() -> None:
    """The CombinedNeedsMultiProviderError suggestion must point users at
    all_deep_research (the canonical multi-provider built-in)."""
    with pytest.raises(CombinedNeedsMultiProviderError) as exc_info:
        _call(mode="default", combined=True)
    suggestion = exc_info.value.suggestion or ""
    assert "all_deep_research" in suggestion
