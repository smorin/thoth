"""P18 Phase I: extended runtime contract tests.

For each model in `KNOWN_MODELS`, hit the REAL provider API and verify the
declared `kind` matches the model's actual API behavior:

  * `kind == "immediate"` → first `check_status(submit())` returns `"completed"`
    (single round-trip; no async polling required)
  * `kind == "background"` → first `check_status(submit())` returns one of
    `"running"`, `"queued"`, or `"completed"` (the latter only if the
    upstream API was very fast). For background hits, we then call
    `cancel()` as best-effort cleanup.

Gated by `@pytest.mark.extended`. Default `pytest` skips this entire
module (`addopts = "-m 'not extended and not live_api'"`); run explicitly
with `just test-extended` after exporting the required API keys.

Cost target: small prompts for all providers. Background providers with
upstream cancel stop after the kind check; providers without upstream cancel
may continue billing after the test records the live runtime behavior.
"""

from __future__ import annotations

import asyncio
import os

import pytest

from doxa_research.models import KNOWN_MODELS

# Skip the entire module unless explicit `extended` marker is selected. The
# `pytest.mark.extended` decorator ALSO does this, but the early skip avoids
# importing/instantiating providers when the user hasn't opted in.
pytestmark = pytest.mark.extended

PROVIDER_MARKS = {
    "openai": pytest.mark.provider_openai,
    "perplexity": pytest.mark.provider_perplexity,
    "gemini": pytest.mark.provider_gemini,
}


def _spec_param(spec):
    mark = PROVIDER_MARKS.get(spec.provider)
    marks = [] if mark is None else [mark]
    return pytest.param(spec, marks=marks, id=f"{spec.provider}/{spec.id}")


def _missing_keys_for(provider: str) -> list[str]:
    needs = {
        "openai": ["OPENAI_API_KEY"],
        "perplexity": ["PERPLEXITY_API_KEY"],
        "gemini": ["GEMINI_API_KEY"],
        "mock": [],
    }.get(provider, [])
    return [k for k in needs if not os.environ.get(k)]


def _runtime_check_skip_reason(spec) -> str | None:
    _ = spec
    return None


@pytest.mark.parametrize(
    "spec",
    [_spec_param(spec) for spec in KNOWN_MODELS],
)
def test_model_kind_matches_runtime_behavior(spec) -> None:
    """Submit a tiny ping; assert kind contract holds against the live API."""
    skip_reason = _runtime_check_skip_reason(spec)
    if skip_reason:
        pytest.skip(skip_reason)

    missing = _missing_keys_for(spec.provider)
    if missing:
        pytest.skip(f"{spec.provider}: required env vars missing: {missing}")

    from doxa_research.config import ConfigManager
    from doxa_research.providers import create_provider

    cm = ConfigManager()
    cm.load_all_layers({})

    mode_config = {
        "provider": spec.provider,
        "model": spec.id,
        "kind": spec.kind,
    }
    provider = create_provider(spec.provider, cm, mode_config=mode_config)

    async def _exercise() -> dict:
        job_id = await provider.submit("ping", mode="_runtime_check_")
        status = await provider.check_status(job_id)
        if spec.kind == "background" and status.get("status") in ("running", "queued"):
            # Best-effort cleanup: providers with upstream cancel stop the job;
            # providers without it report their unsupported status and continue.
            try:
                await provider.cancel(job_id)
            except NotImplementedError:
                pass
        return status

    status = asyncio.run(_exercise())

    if spec.kind == "immediate":
        assert status.get("status") == "completed", (
            f"{spec.provider}/{spec.id} declared kind='immediate' but first "
            f"check_status returned {status!r} — drift between doxa_research's "
            f"KNOWN_MODELS registry and the upstream API."
        )
    else:  # background
        assert status.get("status") in ("running", "queued", "completed"), (
            f"{spec.provider}/{spec.id} declared kind='background' but first "
            f"check_status returned {status!r}; expected running/queued/completed."
        )
