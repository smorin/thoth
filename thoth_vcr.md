# VCR Cassette Integration for Thoth

## What's available

The sibling repo `deepresearch_replay` records real OpenAI Deep Research API
traffic through Hoverfly, sanitizes the captures, and exports them as VCR.py
cassettes. Cassettes live at:

```
thoth_test_cassettes/
└── openai/
    └── happy-path.yaml   # 57 interactions, full polling lifecycle
```

The happy-path cassette covers:
- `POST /v1/responses` — submit a deep research job (status: `queued`)
- 55 `GET /v1/responses/{id}` polls — transition through `in_progress`
- Final `GET` — status: `completed`, full output with text + annotations

All API keys and auth headers are redacted. Response bodies are plain UTF-8
(gzip decoded at export time). Pair order is preserved — VCR replays repeated
URIs in recorded order, which reproduces the polling sequence without runtime
state logic.

Gemini and Perplexity cassettes will land when `deepresearch_replay` P03/P04
complete.

## Re-exporting cassettes

From the `deepresearch_replay` checkout:

```bash
just export-vcr                          # all providers
just export-vcr-one openai happy-path    # single cassette
VCR_EXPORT_DIR=/custom/path just export-vcr  # override target
```

Default output: `../thoth/thoth_test_cassettes/<provider>/<scenario>.yaml`.

## Dependencies

Add `vcrpy` to the dev dependency group:

```bash
uv add --dev 'vcrpy>=8.1.1'
```

This pulls in `pyyaml` and `wrapt` transitively. No other deps needed — vcrpy
intercepts `httpx` natively since v7.

## Integration

Two approaches, depending on whether thoth stays with the custom `thoth_test`
runner or adds pytest alongside it.

### Option A: Fixture tests inside `thoth_test`

Add `vcrpy` to the inline script dependencies at the top of `thoth_test`:

```python
# /// script
# dependencies = [
#   ...
#   "vcrpy>=8.1.1",
# ]
# ///
```

Then add fixture-type test cases that use `vcr.VCR` directly:

```python
import vcr

CASSETTE_DIR = Path(__file__).parent / "thoth_test_cassettes"


def _vcr_openai_submit() -> None:
    """Fixture test: submit via cassette, get a job ID back."""
    from thoth.__main__ import OpenAIProvider

    cassette_path = CASSETTE_DIR / "openai" / "happy-path.yaml"
    my_vcr = vcr.VCR(record_mode="none", cassette_library_dir=str(CASSETTE_DIR))

    with my_vcr.use_cassette(str(cassette_path)):
        provider = OpenAIProvider(api_key="sk-replay-dummy")
        job_id = asyncio.run(provider.submit(
            prompt="What are the three most significant recent breakthroughs"
                   " in solid-state battery technology?",
            mode="deep-research",
        ))
        assert job_id.startswith("resp_"), f"unexpected job_id: {job_id}"
```

Register it in the test list alongside existing fixture tests:

```python
TestCase(
    name="VCR-OAI-SUBMIT",
    description="OpenAI submit replays from VCR cassette",
    command="fixture",
    test_type="fixture",
    setup_func=_vcr_openai_submit,
    expected_exit_code=0,
    tags=["VCR", "VCR-OAI"],
),
```

**Pros:** Consistent with how thoth tests work today. No new test runner.
**Cons:** `thoth_test` is already ~3600 lines. vcrpy's httpx interception
relies on patching at the transport layer, which may interact with the
`AsyncOpenAI` client's internal httpx usage in ways that need debugging.

### Option B: Separate pytest test file (recommended)

Create `tests/test_vcr_openai.py` using pytest + vcrpy:

```python
"""VCR cassette replay tests for OpenAI provider."""

from __future__ import annotations

import asyncio
from pathlib import Path

import vcr

CASSETTE_DIR = Path(__file__).resolve().parent.parent / "thoth_test_cassettes"


def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


class TestOpenAISubmit:
    """Replay the happy-path cassette through OpenAIProvider.submit()."""

    CASSETTE = str(CASSETTE_DIR / "openai" / "happy-path.yaml")

    @vcr.use_cassette(CASSETTE, record_mode="none")
    def test_submit_returns_response_id(self):
        from thoth.__main__ import OpenAIProvider

        provider = OpenAIProvider(api_key="sk-replay-dummy")
        job_id = _run(provider.submit(
            prompt=(
                "What are the three most significant recent breakthroughs"
                " in solid-state battery technology?"
            ),
            mode="deep-research",
        ))
        assert job_id.startswith("resp_")

    @vcr.use_cassette(CASSETTE, record_mode="none")
    def test_submit_status_is_queued(self):
        from thoth.__main__ import OpenAIProvider

        provider = OpenAIProvider(api_key="sk-replay-dummy")
        job_id = _run(provider.submit(
            prompt=(
                "What are the three most significant recent breakthroughs"
                " in solid-state battery technology?"
            ),
            mode="deep-research",
        ))
        status = _run(provider.check_status(job_id))
        assert status["status"] in ("queued", "in_progress")


class TestOpenAIPolling:
    """Replay the full polling sequence to completion."""

    CASSETTE = str(CASSETTE_DIR / "openai" / "happy-path.yaml")

    @vcr.use_cassette(CASSETTE, record_mode="none")
    def test_poll_to_completed(self):
        from thoth.__main__ import OpenAIProvider

        provider = OpenAIProvider(api_key="sk-replay-dummy")
        job_id = _run(provider.submit(
            prompt=(
                "What are the three most significant recent breakthroughs"
                " in solid-state battery technology?"
            ),
            mode="deep-research",
        ))

        # Poll until completed — cassette has 55 in_progress + 1 completed
        for _ in range(60):
            info = _run(provider.check_status(job_id))
            if info["status"] == "completed":
                break
        assert info["status"] == "completed"

    @vcr.use_cassette(CASSETTE, record_mode="none")
    def test_get_result_returns_text(self):
        from thoth.__main__ import OpenAIProvider

        provider = OpenAIProvider(api_key="sk-replay-dummy")
        job_id = _run(provider.submit(
            prompt=(
                "What are the three most significant recent breakthroughs"
                " in solid-state battery technology?"
            ),
            mode="deep-research",
        ))

        for _ in range(60):
            info = _run(provider.check_status(job_id))
            if info["status"] == "completed":
                break

        result = _run(provider.get_result(job_id))
        assert len(result) > 100, "expected substantial research output"
```

Run with:

```bash
uv run pytest tests/test_vcr_openai.py -v
```

Add a justfile recipe:

```just
# Run VCR cassette replay tests.
test-vcr:
    uv run pytest tests/test_vcr_openai.py -v
```

**Pros:** Clean separation. pytest + vcrpy is the standard pattern. Easy to
add per-provider test files as cassettes land. Doesn't bloat `thoth_test`.
**Cons:** Introduces pytest as a second test runner alongside `thoth_test`.

## Notes

- **`record_mode="none"`** is critical — it tells vcrpy to never make real
  HTTP requests. If the cassette doesn't cover a request, the test fails
  instead of hitting the live API.
- **Async caveat:** `OpenAIProvider` uses `AsyncOpenAI`. vcrpy patches httpx
  at the transport level and works with both sync and async clients, but the
  test harness needs `asyncio.run()` to drive the coroutines.
- **Request matching:** vcrpy defaults to matching on URI + method + body.
  The cassette bodies are JSON strings, so matching works out of the box for
  the Responses API. If matching issues arise, configure a custom
  `match_on=["uri", "method"]` on the VCR instance.
- **Retry decorator:** `OpenAIProvider.submit()` uses `@retry` from tenacity
  (3 attempts on timeout/connection errors). Under VCR replay there are no
  real network errors, so retries won't fire. This is fine — the cassette
  tests verify the happy path, not retry logic.
- **Polling delay:** `check_status()` may include `await asyncio.sleep()`
  between polls in production. Under VCR this sleep still executes but the
  HTTP call returns instantly from the cassette, so the test runs fast.
