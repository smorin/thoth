"""P24 sentinel: extended + live-api CI workflows expose GEMINI_API_KEY.

These tests parse the workflow YAML and assert the env block names the
key. Catches accidental removal of `GEMINI_API_KEY` from the gated
collections during future workflow edits. Mirrors `test_p23_ci_wiring.py`
(per P23-R10, substring scanning workflow YAMLs is forbidden).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

WORKFLOWS = Path(__file__).resolve().parent.parent / ".github" / "workflows"


@pytest.mark.parametrize("workflow", ["extended.yml", "live-api.yml"])
def test_workflow_passes_gemini_api_key(workflow: str) -> None:
    """P24: nightly + weekly CI workflows pass GEMINI_API_KEY env var."""
    parsed = yaml.safe_load((WORKFLOWS / workflow).read_text())
    jobs = parsed["jobs"]
    job_name = "extended" if workflow == "extended.yml" else "live_api"
    test_step = next(
        step for step in jobs[job_name]["steps"] if str(step.get("run", "")).startswith("uv run")
    )
    env = test_step.get("env") or {}

    assert "GEMINI_API_KEY" in env, (
        f"{workflow} missing GEMINI_API_KEY env binding — Gemini "
        f"extended/live-api tests cannot run in CI"
    )
    assert "OPENAI_API_KEY" in env, (
        f"{workflow} should still pass OPENAI_API_KEY (unchanged from P20)"
    )
    assert "PERPLEXITY_API_KEY" in env, (
        f"{workflow} should still pass PERPLEXITY_API_KEY (unchanged from P23)"
    )


def test_gemini_models_in_known_models_registry() -> None:
    """P24: GeminiProvider's immediate models appear in KNOWN_MODELS.

    The 3 Gemini built-in modes auto-derive into KNOWN_MODELS via
    `derive_known_models()` from BUILTIN_MODES (per P23-T09 precedent).
    """
    from thoth.config import BUILTIN_MODES
    from thoth.models import KNOWN_MODELS

    gemini_built_ins = {
        mode for mode, cfg in BUILTIN_MODES.items() if cfg.get("provider") == "gemini"
    }
    assert gemini_built_ins == {"gemini_quick", "gemini_pro", "gemini_reasoning"}

    gemini_model_ids = {m.id for m in KNOWN_MODELS if m.provider == "gemini"}
    # Two distinct model ids back the three modes (quick uses flash-lite;
    # pro and reasoning share gemini-2.5-pro).
    assert "gemini-2.5-flash-lite" in gemini_model_ids
    assert "gemini-2.5-pro" in gemini_model_ids


def test_extended_runtime_check_supports_gemini_keys() -> None:
    """P24: test_model_kind_runtime._missing_keys_for handles 'gemini'."""
    import os

    from tests.extended import test_model_kind_runtime as runtime

    # When GEMINI_API_KEY is unset, gemini provider must report it missing.
    saved = os.environ.pop("GEMINI_API_KEY", None)
    try:
        assert runtime._missing_keys_for("gemini") == ["GEMINI_API_KEY"]
    finally:
        if saved is not None:
            os.environ["GEMINI_API_KEY"] = saved
