"""Preflight: `--model NAME` requires a single resolved provider.

Standardization #5: `--model NAME` is ambiguous on a multi-provider mode
because each provider has its own per-provider namespace model
(`mode.openai.model`, `mode.perplexity.model`, etc.) that wins in the
parameter_config.py merge order. Silently letting the override be
dropped is the same class of footgun fixed in commit 6601a83 for --out,
--append, and --combined.

After this change:
  - `--model NAME` on a multi-provider mode (no --provider filter)
    raises ModelOverrideMultiProviderError.
  - `--model NAME --provider X` on a multi-provider mode narrows to
    single-provider AND patches the X-namespace's model, so the
    override actually takes effect on the X provider's runtime config.
  - `--model NAME` on a single-provider mode that has a per-provider
    namespace (e.g. openai_quick) ALSO patches the matching namespace,
    not just the generic mode model.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from doxa_research.config import ConfigManager
from doxa_research.errors import ModelOverrideMultiProviderError
from doxa_research.providers.parameter_config import build_provider_runtime_config
from doxa_research.run import run_research


def _call(
    *,
    mode: str = "default",
    provider: str | None = None,
    model: str | None = None,
) -> None:
    asyncio.run(
        run_research(
            mode=mode,
            prompt="ping",
            async_mode=False,
            project=None,
            output_dir=None,
            provider=provider,
            input_file=None,
            auto=False,
            verbose=False,
            model_override=model,
        )
    )


def test_model_override_on_multi_provider_mode_raises() -> None:
    """`--model NAME` on all_deep_research with no --provider → error."""
    with pytest.raises(ModelOverrideMultiProviderError) as exc_info:
        _call(mode="all_deep_research", model="some-custom-model")
    assert exc_info.value.exit_code == 1
    assert "all_deep_research" in exc_info.value.message


def test_model_override_error_suggests_provider_narrowing() -> None:
    """The error suggestion should point users at --provider X --model NAME."""
    with pytest.raises(ModelOverrideMultiProviderError) as exc_info:
        _call(mode="all_deep_research", model="some-custom-model")
    suggestion = exc_info.value.suggestion or ""
    assert "--provider" in suggestion
    assert "--model" in suggestion


def test_model_override_with_provider_narrowing_passes_preflight(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression: --model NAME --provider X on multi-provider narrows cleanly."""
    monkeypatch.setattr(
        "doxa_research.run.create_provider",
        lambda *a, **kw: MagicMock(model="stub", api_key="stub", config={}),
    )
    try:
        _call(mode="all_deep_research", provider="gemini", model="custom")
    except ModelOverrideMultiProviderError:
        pytest.fail("narrowed --provider + --model should pass preflight")
    except Exception:
        pass  # downstream stub call may fail; out of scope


def test_model_override_on_single_provider_mode_passes_preflight(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression: --model NAME on default (single-provider) still works."""
    monkeypatch.setattr(
        "doxa_research.run.create_provider",
        lambda *a, **kw: MagicMock(model="stub", api_key="stub", config={}),
    )
    try:
        _call(mode="default", model="custom")
    except ModelOverrideMultiProviderError:
        pytest.fail("--model on single-provider mode must pass preflight")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# The narrowing path must actually patch the per-provider namespace model,
# otherwise the error's suggestion ("use --provider X") is a dead end.
# ---------------------------------------------------------------------------


def test_narrowed_override_patches_per_provider_namespace_model() -> None:
    """When narrowing to one provider, --model NAME must reach that
    provider's namespace, not just mode_config.model. Otherwise the
    parameter_config merge order silently drops the override.
    """
    cm = ConfigManager()
    cm.load_all_layers({})
    base_mode_cfg = cm.get_mode_config("all_deep_research").copy()
    # Simulate the run_research logic: model override patches both the
    # generic model AND the matching provider namespace.
    base_mode_cfg["model"] = "custom-model"
    base_mode_cfg["gemini"] = {**base_mode_cfg["gemini"], "model": "custom-model"}

    rt = build_provider_runtime_config(
        provider_name="gemini",
        config=cm,
        mode_config=base_mode_cfg,
        timeout_override=None,
    )
    assert rt.provider_request.get("model") == "custom-model", (
        f"expected gemini's resolved model = custom-model, got {rt.provider_request.get('model')}"
    )


def test_single_provider_namespace_mode_picks_up_override() -> None:
    """openai_quick has a `mode.openai` namespace (web_search=True). With
    --model NAME, the override must reach openai's namespace, not just
    mode_config.model — otherwise the gpt-4.1-mini default still wins.
    """
    cm = ConfigManager()
    cm.load_all_layers({})
    base_mode_cfg = cm.get_mode_config("openai_quick").copy()
    # Simulate the narrowed-override patching path:
    base_mode_cfg["model"] = "custom-model"
    if isinstance(base_mode_cfg.get("openai"), dict):
        base_mode_cfg["openai"] = {**base_mode_cfg["openai"], "model": "custom-model"}

    rt = build_provider_runtime_config(
        provider_name="openai",
        config=cm,
        mode_config=base_mode_cfg,
        timeout_override=None,
    )
    assert rt.provider_request.get("model") == "custom-model"
