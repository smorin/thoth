"""P23-TS09 sentinel: extended + live-api CI workflows expose PERPLEXITY_API_KEY.

These tests parse the workflow YAML and assert the env block names both
keys. Catches accidental removal of `PERPLEXITY_API_KEY` from the gated
collections during future workflow edits.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

WORKFLOWS = Path(__file__).resolve().parent.parent / ".github" / "workflows"


@pytest.mark.parametrize("workflow", ["extended.yml", "live-api.yml"])
def test_workflow_passes_perplexity_api_key(workflow: str) -> None:
    """TS09: nightly + weekly CI workflows pass PERPLEXITY_API_KEY env var."""
    parsed = yaml.safe_load((WORKFLOWS / workflow).read_text())
    jobs = parsed["jobs"]
    job_name = "extended" if workflow == "extended.yml" else "live_api"
    test_step = next(
        step for step in jobs[job_name]["steps"] if str(step.get("run", "")).startswith("uv run")
    )
    env = test_step.get("env") or {}

    assert "PERPLEXITY_API_KEY" in env, (
        f"{workflow} missing PERPLEXITY_API_KEY env binding — Perplexity "
        f"extended/live-api tests cannot run in CI"
    )
    assert "OPENAI_API_KEY" in env, (
        f"{workflow} should still pass OPENAI_API_KEY (unchanged from P20)"
    )


def test_perplexity_models_in_known_models_registry() -> None:
    """TS09: PerplexityProvider's sync models appear in KNOWN_MODELS.

    P27 added `sonar-deep-research` to the registry via the new
    `perplexity_deep_research` built-in mode, so the original negative guard
    has been flipped to a positive assertion.
    """
    from thoth.models import KNOWN_MODELS

    perp_ids = {m.id for m in KNOWN_MODELS if m.provider == "perplexity"}
    assert "sonar" in perp_ids
    assert "sonar-pro" in perp_ids
    assert "sonar-reasoning-pro" in perp_ids
    assert "sonar-deep-research" in perp_ids


def test_perplexity_deep_research_runtime_check_deferred_to_weekly_live_api() -> None:
    """P27: expensive non-cancellable DR is not exercised by nightly extended."""
    from tests.extended import test_model_kind_runtime as runtime
    from thoth.models import ModelSpec

    skip_reason = getattr(runtime, "_runtime_check_skip_reason", None)
    assert callable(skip_reason), (
        "test_model_kind_runtime needs an explicit skip helper so expensive "
        "Perplexity deep-research is covered by live_api, not nightly extended"
    )
    assert skip_reason(ModelSpec("sonar-deep-research", "perplexity", "background"))
    assert skip_reason(ModelSpec("sonar", "perplexity", "immediate")) is None


def test_weekly_perplexity_live_api_exercises_resume_without_cancel() -> None:
    """P27: weekly Perplexity DR coverage should test resumability, not fake cancel."""
    text = (
        Path(__file__).resolve().parent / "extended" / "test_perplexity_real_workflows.py"
    ).read_text()
    submit_test = text.split("def test_ext_pplx_bg_submit_async_persists_request_id", 1)[1]
    submit_test = submit_test.split("\ndef test_", 1)[0]

    assert '"resume", operation_id, "--async", "--json"' in submit_test
    assert '"cancel", operation_id' not in submit_test


def test_extended_skip_for_perplexity_was_removed() -> None:
    """TS09: P23 unblocked the perplexity skip in test_model_kind_runtime."""
    text = (Path(__file__).resolve().parent / "extended" / "test_model_kind_runtime.py").read_text()
    assert "perplexity provider is not yet operational" not in text, (
        "stale skip copy in test_model_kind_runtime.py; P23 should remove it"
    )
