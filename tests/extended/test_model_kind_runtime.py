"""P18 Phase I: extended runtime contract tests.

For each model in `KNOWN_MODELS`, hit the REAL provider API and verify the
declared `kind` matches the model's actual API behavior:

  * `kind == "immediate"` → first `check_status(submit())` returns `"completed"`
    (single round-trip; no async polling required)
  * `kind == "background"` → first `check_status(submit())` returns one of
    `"running"`, `"queued"`, or `"completed"` (the latter only if the
    upstream API was very fast). For background hits, we then `cancel()`
    to limit cost.

Gated by `@pytest.mark.extended`. Default `pytest` skips this entire
module (`addopts = "-m 'not extended'"`); run explicitly with
`uv run pytest -m extended` or `just test-extended` after exporting the
required API keys.

Cost target: <$0.10 per full run (small ping prompts; cancel before
deep-research jobs run to completion).
"""

from __future__ import annotations

import asyncio
import os

import pytest

from thoth.models import KNOWN_MODELS

# Skip the entire module unless explicit `extended` marker is selected. The
# `pytest.mark.extended` decorator ALSO does this, but the early skip avoids
# importing/instantiating providers when the user hasn't opted in.
pytestmark = pytest.mark.extended


def _missing_keys_for(provider: str) -> list[str]:
    needs = {
        "openai": ["OPENAI_API_KEY"],
        "perplexity": ["PERPLEXITY_API_KEY"],
        "mock": [],
    }.get(provider, [])
    return [k for k in needs if not os.environ.get(k)]


@pytest.mark.parametrize(
    "spec",
    KNOWN_MODELS,
    ids=lambda s: f"{s.provider}/{s.id}",
)
def test_model_kind_matches_runtime_behavior(spec) -> None:
    """Submit a tiny ping; assert kind contract holds against the live API."""
    missing = _missing_keys_for(spec.provider)
    if missing:
        pytest.skip(f"{spec.provider}: required env vars missing: {missing}")

    if spec.provider == "perplexity":
        # PerplexityProvider.submit raises NotImplementedError as of P18.
        pytest.skip("perplexity provider is not yet operational")

    from thoth.providers import create_provider
    from thoth.config import ConfigManager

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
        if (
            spec.kind == "background"
            and status.get("status") in ("running", "queued")
        ):
            # Cancel before the deep-research job actually runs to completion
            # — the test only needed to confirm submission was async.
            try:
                await provider.cancel(job_id)
            except NotImplementedError:
                pass
        return status

    status = asyncio.run(_exercise())

    if spec.kind == "immediate":
        assert status.get("status") == "completed", (
            f"{spec.provider}/{spec.id} declared kind='immediate' but first "
            f"check_status returned {status!r} — drift between thoth's "
            f"KNOWN_MODELS registry and the upstream API."
        )
    else:  # background
        assert status.get("status") in ("running", "queued", "completed"), (
            f"{spec.provider}/{spec.id} declared kind='background' but first "
            f"check_status returned {status!r}; expected running/queued/completed."
        )
