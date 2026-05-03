# P28 — Gemini Background Deep Research Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `GeminiProvider` to Thoth that mirrors the OpenAI background Deep Research surface (submit → poll → get_result → cancel/reconnect), wired into the existing provider-agnostic runtime.

**Architecture:** New `src/thoth/providers/gemini.py` module implementing `ResearchProvider` against the `google-genai>=1.55.0` SDK using the Interactions API (`agent="deep-research-pro-preview-12-2025"`, `background=True`). All polling, checkpointing, SIGINT cancel, and output-sink integration is inherited unchanged from the runtime; P28 only adds the provider class, error mapper, mode entries, CLI flag, and config defaults. Tests follow the OpenAI three-layer pattern: monkeypatched-SDK unit tests + VCR cassette replays + gated `live_api` (weekly) + gated `extended` (nightly).

**Tech Stack:** Python 3.11+, `google-genai>=1.55.0,<2`, `httpx`, `tenacity`, `pytest`, `pytest-vcr`, `rich`, existing Thoth runtime.

**Spec:** `projects/P28-gemini-background-deep-research.md` (committed in `b173538`). Read it first — every task here references concrete decisions and parity rows from that file.

---

## File structure

| Action | Path | Responsibility |
|---|---|---|
| Create | `src/thoth/providers/gemini.py` | `GeminiProvider` class + `_map_gemini_error` + agent ID constant |
| Modify | `src/thoth/providers/__init__.py` | Add `GeminiProvider` to `PROVIDERS` dict + `PROVIDER_ENV_VARS` + `__all__` |
| Modify | `src/thoth/config.py` | Add `[providers.gemini]` defaults; add 9 `gemini_*` mode entries to `KNOWN_MODELS` |
| Modify | `src/thoth/cli_subcommands/_options.py` | Add `--api-key-gemini` flag tuple |
| Create | `tests/test_gem_background.py` | Unit tests with monkeypatched `google.genai.Client` for the 6 provider methods |
| Create | `tests/test_vcr_gemini.py` | Cassette replay tests (mirrors `tests/test_vcr_openai.py` shape) |
| Create | `thoth_test_cassettes/gemini/happy-path.yaml` | Recorded happy-path cassette (created in Task 21) |
| Create | `tests/extended/test_gemini_real_workflows.py` | Live-API CLI workflow tests (`@pytest.mark.live_api`) |
| Modify | `pyproject.toml` | Add `google-genai>=1.55.0,<2` dependency |
| Modify | `.github/workflows/live-api.yml` | Add `GEMINI_API_KEY` to secrets/env block |
| Modify | `.github/workflows/extended.yml` | Add `GEMINI_API_KEY` to secrets/env block |
| Modify | `README.md` | Add Gemini cost callout + mode listing entry |

Total new code: ~600 lines provider + ~400 lines unit tests + ~200 lines VCR replay tests + ~150 lines live-API tests. Total modified lines across config/cli/init/pyproject/README: ~150.

---

## Tasks

### Task 1: Add google-genai dependency

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add dependency via uv**

```bash
cd /Users/stevemorin/c/thoth
uv add 'google-genai>=1.55.0,<2'
```

Expected: `pyproject.toml` updated with the new dependency under `[project.dependencies]`; `uv.lock` regenerated.

- [ ] **Step 2: Verify import works**

```bash
uv run python -c "from google import genai; print(genai.__version__ if hasattr(genai, '__version__') else 'imported')"
```

Expected: prints version string `1.55.0` or higher (or `imported` for the import test).

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "feat(deps): add google-genai>=1.55.0,<2 for P28 Gemini provider"
```

---

### Task 2: Stub GeminiProvider module skeleton

Lay down the file with imports and a class that can be imported without errors. No methods yet — just enough that `from thoth.providers.gemini import GeminiProvider` succeeds.

**Files:**
- Create: `src/thoth/providers/gemini.py`

- [ ] **Step 1: Create the file**

```python
"""Gemini Deep Research provider.

Mirrors the OpenAI background DR surface (submit → check_status → get_result
+ cancel + reconnect) using the google-genai SDK against the Interactions API.

See projects/P28-gemini-background-deep-research.md for the full spec, parity
matrix vs OpenAI, and provider-specific deltas (10s polling, 20-min hard
timeout, 403-on-GET handling, server-vs-user cancel disambiguation, etc.).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

import httpx
from google import genai
from google.genai import errors as genai_errors
from rich.console import Console
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from thoth.errors import APIKeyError, APIQuotaError, ProviderError, ThothError
from thoth.models import ModelCache
from thoth.providers.base import ResearchProvider

DEEP_RESEARCH_AGENT_ID = "deep-research-pro-preview-12-2025"
"""Only built-in Gemini Deep Research agent as of 2026-04 (research doc §3)."""

DEFAULT_POLL_INTERVAL_SECONDS = 10
"""Recommended poll cadence per research doc §6."""

DEFAULT_MAX_WAIT_MINUTES = 20
"""Hard polling timeout per research doc §10 stuck-in-progress workaround.
Lower than OpenAI's 30-minute default because Gemini's stuck-in-progress
bug was active and severe in March 2026."""

_console = Console()


def _map_gemini_error(
    exc: BaseException, model: str | None = None, verbose: bool = False
) -> ThothError:
    """Map a google-genai SDK exception or HTTP error to a Thoth error type.

    To be filled in by Task 4. Stub raises NotImplementedError so any
    accidental call surfaces clearly.
    """
    raise NotImplementedError("_map_gemini_error not yet implemented (Task 4)")


class GeminiProvider(ResearchProvider):
    """Gemini Deep Research via the google-genai Interactions API.

    Methods to be implemented per the parity matrix in P28's spec:
      - submit() — Task 7
      - check_status() — Task 10
      - get_result() — Task 13
      - cancel() — Task 16
      - reconnect() — Task 17
      - list_models() / list_models_cached() — Task 18
    """

    def __init__(self, api_key: str, config: dict[str, Any] | None = None):
        self.api_key = api_key
        self.config = config or {}
        self.model = self.config.get("model", DEEP_RESEARCH_AGENT_ID)
        self.poll_interval = self.config.get(
            "poll_interval", DEFAULT_POLL_INTERVAL_SECONDS
        )
        self.max_wait_minutes = self.config.get(
            "max_wait_minutes", DEFAULT_MAX_WAIT_MINUTES
        )
        self.jobs: dict[str, dict[str, Any]] = {}
        # Track local-cancel-requested state for cancel disambiguation
        # (research doc §10 "instant cancel with no output" server-side cancel
        # vs. user-initiated cancel both surface as status="cancelled").
        self._cancel_requested: dict[str, bool] = {}
        self.model_cache = ModelCache("gemini")
        self._client: genai.Client | None = None

    @property
    def client(self) -> genai.Client:
        """Lazy-instantiate the genai.Client to avoid spurious auth at import time."""
        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)
        return self._client
```

- [ ] **Step 2: Verify import succeeds**

```bash
uv run python -c "from thoth.providers.gemini import GeminiProvider, DEEP_RESEARCH_AGENT_ID; print(DEEP_RESEARCH_AGENT_ID)"
```

Expected: prints `deep-research-pro-preview-12-2025`.

- [ ] **Step 3: Run lint and typecheck**

```bash
uv run ruff check src/thoth/providers/gemini.py
uv run ruff format --check src/thoth/providers/gemini.py
uv run ty check src/thoth/providers/gemini.py
```

Expected: all three pass.

- [ ] **Step 4: Commit**

```bash
git add src/thoth/providers/gemini.py
git commit -m "feat(gemini): scaffold GeminiProvider module skeleton"
```

---

### Task 3: Register GeminiProvider in PROVIDERS dict (test-first)

The `PROVIDERS` dict in `src/thoth/providers/__init__.py` is the single source of truth for name → class dispatch. Adding `gemini` here is what makes the provider discoverable to the runtime. Test-first per CLAUDE.md TDD bias.

**Files:**
- Test: `tests/test_provider_registry.py:<existing>` (extend) OR `tests/test_gem_background.py` (new, append)
- Modify: `src/thoth/providers/__init__.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_gem_background.py` with this initial content:

```python
"""Unit tests for GeminiProvider — mirrors tests/test_oai_background.py shape.

All tests use monkeypatched google.genai.Client so they never hit the network.
See tests/test_vcr_gemini.py for cassette-replay tests, and
tests/extended/test_gemini_real_workflows.py for the gated live-API tests.
"""

from __future__ import annotations

import pytest


class TestGeminiProviderRegistration:
    """P28 parity row 4: provider registration."""

    def test_gemini_in_providers_dict(self):
        """PROVIDERS["gemini"] must point to GeminiProvider class."""
        from thoth.providers import PROVIDERS
        from thoth.providers.gemini import GeminiProvider

        assert "gemini" in PROVIDERS
        assert PROVIDERS["gemini"] is GeminiProvider

    def test_gemini_in_provider_env_vars(self):
        """PROVIDER_ENV_VARS["gemini"] must declare GEMINI_API_KEY."""
        from thoth.providers import PROVIDER_ENV_VARS

        assert PROVIDER_ENV_VARS["gemini"] == "GEMINI_API_KEY"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_gem_background.py::TestGeminiProviderRegistration -v
```

Expected: FAIL with `KeyError: 'gemini'` or assertion failure on the dict membership check.

- [ ] **Step 3: Add GeminiProvider to the registry**

In `src/thoth/providers/__init__.py`, modify two areas:

```python
# Add import alongside existing OpenAI/Perplexity imports
from thoth.providers.gemini import GeminiProvider

# Modify PROVIDERS dict — add gemini line:
PROVIDERS: dict[str, type[ResearchProvider]] = {
    "openai": OpenAIProvider,
    "perplexity": PerplexityProvider,
    "gemini": GeminiProvider,
    "mock": MockProvider,
}

# Modify PROVIDER_ENV_VARS dict — add gemini line:
PROVIDER_ENV_VARS: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "perplexity": "PERPLEXITY_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "mock": "MOCK_API_KEY",
}

# Modify __all__ — add GeminiProvider:
__all__ = [
    "PROVIDERS",
    "PROVIDER_ENV_VARS",
    "GeminiProvider",
    "MockProvider",
    "OpenAIProvider",
    "PerplexityProvider",
    "ResearchProvider",
    "_map_openai_error",
    "create_provider",
    "resolve_api_key",
]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_gem_background.py::TestGeminiProviderRegistration -v
```

Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_gem_background.py src/thoth/providers/__init__.py
git commit -m "feat(gemini): register GeminiProvider in PROVIDERS dict"
```

---

### Task 4: Error mapper — write failing tests for 8 error classes

Per spec parity row 4 + provider-specific deltas. The mapper handles google-genai SDK exception classes plus the doc §10 known bugs. Test cases enumerate each branch.

**Files:**
- Test: `tests/test_gem_background.py` (append)

- [ ] **Step 1: Append the test class**

Add to `tests/test_gem_background.py`:

```python
class TestMapGeminiError:
    """P28 parity row 4: error mapping (mirrors _map_openai_error 12-branch shape)."""

    def test_auth_error_maps_to_api_key_error(self):
        """401 / authentication failures → APIKeyError."""
        from google.genai import errors as genai_errors

        from thoth.errors import APIKeyError
        from thoth.providers.gemini import _map_gemini_error

        exc = genai_errors.ClientError(401, {"error": {"message": "invalid api key"}})
        result = _map_gemini_error(exc)
        assert isinstance(result, APIKeyError)
        assert "gemini" in str(result).lower() or "api key" in str(result).lower()

    def test_free_tier_403_maps_to_thotherror_with_pricing_url(self):
        """Free tier 403 → ThothError with pricing URL (research doc §8)."""
        from google.genai import errors as genai_errors

        from thoth.errors import ThothError
        from thoth.providers.gemini import _map_gemini_error

        exc = genai_errors.ClientError(
            403,
            {"error": {"message": "Deep Research requires paid tier"}},
        )
        result = _map_gemini_error(exc)
        assert isinstance(result, ThothError)
        # Suggestion must mention paid tier and pricing URL
        suggestion = result.suggestion or ""
        assert "paid tier" in suggestion.lower() or "tier 1" in suggestion.lower()
        assert "ai.google.dev/pricing" in suggestion or "pricing" in suggestion

    def test_rate_limit_429_maps_to_quota_or_provider_error(self):
        """429 RESOURCE_EXHAUSTED → APIQuotaError when insufficient quota, else ProviderError."""
        from google.genai import errors as genai_errors

        from thoth.errors import APIQuotaError
        from thoth.providers.gemini import _map_gemini_error

        exc = genai_errors.ClientError(
            429,
            {"error": {"status": "RESOURCE_EXHAUSTED", "message": "Resource exhausted"}},
        )
        result = _map_gemini_error(exc)
        assert isinstance(result, APIQuotaError)

    def test_invalid_argument_400_maps_to_provider_error(self):
        """400 INVALID_ARGUMENT → ProviderError with explanation."""
        from google.genai import errors as genai_errors

        from thoth.errors import ProviderError
        from thoth.providers.gemini import _map_gemini_error

        exc = genai_errors.ClientError(
            400,
            {"error": {"status": "INVALID_ARGUMENT", "message": "store=false invalid"}},
        )
        result = _map_gemini_error(exc)
        assert isinstance(result, ProviderError)

    def test_server_error_5xx_maps_to_provider_error_retryable(self):
        """500/503 → ProviderError (caller's job to retry via tenacity)."""
        from google.genai import errors as genai_errors

        from thoth.errors import ProviderError
        from thoth.providers.gemini import _map_gemini_error

        exc = genai_errors.ServerError(503, {"error": {"message": "high traffic"}})
        result = _map_gemini_error(exc)
        assert isinstance(result, ProviderError)

    def test_timeout_maps_to_provider_error(self):
        """httpx.TimeoutException → ProviderError."""
        import httpx

        from thoth.errors import ProviderError
        from thoth.providers.gemini import _map_gemini_error

        exc = httpx.TimeoutException("request timed out")
        result = _map_gemini_error(exc)
        assert isinstance(result, ProviderError)

    def test_connection_error_maps_to_provider_error(self):
        """httpx.ConnectError → ProviderError."""
        import httpx

        from thoth.errors import ProviderError
        from thoth.providers.gemini import _map_gemini_error

        exc = httpx.ConnectError("connection refused")
        result = _map_gemini_error(exc)
        assert isinstance(result, ProviderError)

    def test_unknown_exception_maps_to_provider_error(self):
        """Catch-all: any other exception → ProviderError so callers don't see raw exceptions."""
        from thoth.errors import ProviderError
        from thoth.providers.gemini import _map_gemini_error

        result = _map_gemini_error(RuntimeError("unexpected"))
        assert isinstance(result, ProviderError)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_gem_background.py::TestMapGeminiError -v
```

Expected: 8 FAIL with `NotImplementedError: _map_gemini_error not yet implemented (Task 4)`.

- [ ] **Step 3: Commit the failing tests**

```bash
git add tests/test_gem_background.py
git commit -m "test(gemini): add failing tests for _map_gemini_error 8-branch matrix"
```

---

### Task 5: Implement `_map_gemini_error`

**Files:**
- Modify: `src/thoth/providers/gemini.py:_map_gemini_error`

- [ ] **Step 1: Replace the stub with the real implementation**

In `src/thoth/providers/gemini.py`, replace the `_map_gemini_error` stub with:

```python
def _map_gemini_error(
    exc: BaseException, model: str | None = None, verbose: bool = False
) -> ThothError:
    """Map a google-genai SDK exception or HTTP error to a Thoth error type.

    Branches mirror _map_openai_error in providers/openai.py:35-126, adapted
    for google-genai's ClientError/ServerError shape and the Gemini-specific
    known bugs from research/gemini-deep-research-api.v1.md §10.
    """
    import httpx
    from google.genai import errors as genai_errors

    raw = str(exc) if verbose else None

    # google-genai ClientError carries an HTTP status code on .code
    if isinstance(exc, genai_errors.ClientError):
        code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
        body = getattr(exc, "details", None) or {}
        # Some SDK versions stash the dict on .response_json; fall back if needed.
        if not body and len(exc.args) > 1 and isinstance(exc.args[1], dict):
            body = exc.args[1]
        msg = ""
        status = ""
        if isinstance(body, dict):
            err = body.get("error") if isinstance(body.get("error"), dict) else {}
            if isinstance(err, dict):
                msg = err.get("message", "") or ""
                status = err.get("status", "") or ""

        if code == 401:
            return APIKeyError("gemini")

        if code == 403:
            # Deep Research is not available on the free tier (research doc §8).
            # Tier 1+ requires a billing account. Surface a useful suggestion.
            return ThothError(
                "Gemini Deep Research requires a paid tier",
                "Link a billing account to your Google Cloud project (Tier 1+). "
                "See https://ai.google.dev/pricing for tier requirements.",
            )

        if code == 429:
            # RESOURCE_EXHAUSTED is the rate-limit / quota-exceeded marker.
            if status == "RESOURCE_EXHAUSTED" or "quota" in msg.lower():
                return APIQuotaError("gemini")
            return ProviderError(
                "gemini",
                "Rate limit exceeded. Please wait a moment and try again.",
                raw_error=raw,
            )

        if code == 400:
            return ProviderError(
                "gemini",
                f"Invalid request: {msg or 'see Gemini API docs'}",
                raw_error=raw,
            )

        if code == 404:
            # Most likely an expired interaction (research doc §5 retention:
            # 55 days paid / 1 day free) or a deleted interaction.
            return ProviderError(
                "gemini",
                "Gemini interaction not found (it may have been deleted, or "
                "expired past the retention window: 55 days paid / 1 day free). "
                "Start a new operation.",
                raw_error=raw,
            )

        # Other 4xx: treat as provider error
        return ProviderError("gemini", msg or str(exc), raw_error=raw)

    if isinstance(exc, genai_errors.ServerError):
        # 5xx are retryable per research doc §10 503 transient errors.
        return ProviderError(
            "gemini",
            "Gemini API is experiencing issues. Try again in a moment.",
            raw_error=raw,
        )

    if isinstance(exc, httpx.TimeoutException):
        return ProviderError(
            "gemini",
            "Request timed out connecting to Gemini API. "
            "Check timeout setting in config.",
            raw_error=raw,
        )

    if isinstance(exc, httpx.ConnectError):
        return ProviderError(
            "gemini",
            "Cannot connect to Gemini API. Check internet connection.",
            raw_error=raw,
        )

    # Catchall — never let raw exceptions bubble to user
    return ProviderError("gemini", f"Gemini API error: {exc}", raw_error=raw)
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
uv run pytest tests/test_gem_background.py::TestMapGeminiError -v
```

Expected: 8 PASS.

- [ ] **Step 3: Run lint and typecheck**

```bash
uv run ruff check src/thoth/providers/gemini.py
uv run ty check src/thoth/providers/gemini.py
```

Expected: pass.

- [ ] **Step 4: Commit**

```bash
git add src/thoth/providers/gemini.py
git commit -m "feat(gemini): implement _map_gemini_error 8-branch error mapping"
```

---

### Task 6: submit() — failing test for happy path

Per spec parity row 3 + research doc §3, §6.

**Files:**
- Test: `tests/test_gem_background.py` (append)

- [ ] **Step 1: Add a test fixture for the monkeypatched client**

Append to `tests/test_gem_background.py`, just below the imports:

```python
class _FakeInteraction:
    """Stand-in for google.genai.types.Interaction during unit tests."""

    def __init__(
        self,
        id: str = "interaction-test-123",
        status: str = "in_progress",
        outputs: list | None = None,
        usage: dict | None = None,
    ):
        self.id = id
        self.status = status
        self.outputs = outputs
        self.usage = usage


class _FakeAsyncInteractions:
    """Stand-in for client.aio.interactions resource."""

    def __init__(self):
        self.create_calls: list[dict] = []
        self.get_calls: list[str] = []
        self.cancel_calls: list[str] = []
        self.next_create_response: _FakeInteraction | None = None
        self.next_get_response: _FakeInteraction | None = None
        self.next_cancel_response: _FakeInteraction | None = None

    async def create(self, **kwargs):
        self.create_calls.append(kwargs)
        return self.next_create_response or _FakeInteraction()

    async def get(self, id: str, **kwargs):
        self.get_calls.append(id)
        if self.next_get_response is None:
            raise AssertionError("Test did not configure next_get_response")
        return self.next_get_response

    async def cancel(self, id: str, **kwargs):
        self.cancel_calls.append(id)
        return self.next_cancel_response or _FakeInteraction(id=id, status="cancelled")


class _FakeAioNamespace:
    def __init__(self, interactions):
        self.interactions = interactions


class _FakeClient:
    """Stand-in for google.genai.Client."""

    def __init__(self, api_key=None):
        self._fake_interactions = _FakeAsyncInteractions()
        self.aio = _FakeAioNamespace(self._fake_interactions)


@pytest.fixture
def fake_client(monkeypatch):
    """Patch genai.Client to return a _FakeClient instance, return that instance."""
    from thoth.providers import gemini

    fake = _FakeClient(api_key="test-key")
    monkeypatch.setattr(gemini.genai, "Client", lambda **kw: fake)
    return fake


@pytest.fixture
def provider(fake_client):
    """Return a GeminiProvider wired to the fake client."""
    from thoth.providers.gemini import GeminiProvider

    p = GeminiProvider(api_key="test-key", config={})
    # Force lazy client to instantiate so fake_client is captured
    _ = p.client
    return p
```

- [ ] **Step 2: Add the failing happy-path test**

Append:

```python
class TestGeminiSubmit:
    """P28 parity row 3 + spec scope 1: submit() happy path + error cases."""

    @pytest.mark.asyncio
    async def test_submit_happy_path_returns_interaction_id(self, provider, fake_client):
        """submit() must call client.aio.interactions.create with agent + background=True
        and return the resulting interaction.id."""
        fake_client._fake_interactions.next_create_response = _FakeInteraction(
            id="interaction-abc-123", status="in_progress"
        )

        job_id = await provider.submit(
            prompt="Research quantum computing",
            mode="gemini_quick_research",
            system_prompt=None,
            verbose=False,
        )

        assert job_id == "interaction-abc-123"
        assert len(fake_client._fake_interactions.create_calls) == 1
        call = fake_client._fake_interactions.create_calls[0]
        assert call["agent"] == "deep-research-pro-preview-12-2025"
        assert call["background"] is True
        assert call["input"] == "Research quantum computing"

    @pytest.mark.asyncio
    async def test_submit_passes_system_instruction_when_set(self, provider, fake_client):
        """submit() must forward system_prompt as system_instruction kwarg."""
        fake_client._fake_interactions.next_create_response = _FakeInteraction(id="x")

        await provider.submit(
            prompt="prompt",
            mode="gemini_deep_research",
            system_prompt="You are a research analyst.",
            verbose=False,
        )

        call = fake_client._fake_interactions.create_calls[0]
        assert call.get("system_instruction") == "You are a research analyst."

    @pytest.mark.asyncio
    async def test_submit_caches_job_metadata(self, provider, fake_client):
        """Successful submit() must cache the job in self.jobs for later retrieve."""
        fake_client._fake_interactions.next_create_response = _FakeInteraction(id="cached-job")

        job_id = await provider.submit(prompt="p", mode="gemini_quick_research")

        assert job_id in provider.jobs
        assert provider.jobs[job_id]["interaction_id"] == "cached-job"
        assert "created_at" in provider.jobs[job_id]
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
uv run pytest tests/test_gem_background.py::TestGeminiSubmit -v
```

Expected: 3 FAIL with `AttributeError: 'GeminiProvider' object has no attribute 'submit'` or `NotImplementedError`.

- [ ] **Step 4: Commit failing tests**

```bash
git add tests/test_gem_background.py
git commit -m "test(gemini): add failing tests for submit() happy path"
```

---

### Task 7: submit() — implement to make tests pass

**Files:**
- Modify: `src/thoth/providers/gemini.py:GeminiProvider`

- [ ] **Step 1: Add the submit() method**

In `src/thoth/providers/gemini.py`, inside the `GeminiProvider` class, add:

```python
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        # Only retry network-level transients; let auth/quota/etc. surface immediately.
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    )
    async def submit(
        self,
        prompt: str,
        mode: str,
        system_prompt: str | None = None,
        verbose: bool = False,
    ) -> str:
        """Submit a Deep Research interaction; return the interaction ID.

        Required-True for agent interactions (research doc §3): background=True,
        store=true (defaulted by the SDK; cannot be False with background=True).
        """
        try:
            request: dict[str, Any] = {
                "agent": self.model,
                "input": prompt,
                "background": True,
            }
            if system_prompt:
                request["system_instruction"] = system_prompt

            if verbose:
                masked_key = (
                    f"{self.api_key[:8]}...{self.api_key[-4:]}"
                    if len(self.api_key) > 12
                    else "***"
                )
                _console.stderr = True
                _console.print(f"gemini API Key: {masked_key}")
                _console.print(f"Agent: {self.model}")

            interaction = await self.client.aio.interactions.create(**request)
            interaction_id = interaction.id or f"gemini-{uuid4().hex[:8]}"

            self.jobs[interaction_id] = {
                "interaction_id": interaction_id,
                "interaction": interaction,
                "created_at": datetime.now(),
            }
            self._cancel_requested[interaction_id] = False
            return interaction_id

        except (ThothError, ProviderError):
            raise
        except Exception as e:
            raise _map_gemini_error(e, model=self.model, verbose=verbose) from e
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
uv run pytest tests/test_gem_background.py::TestGeminiSubmit -v
```

Expected: 3 PASS.

- [ ] **Step 3: Commit**

```bash
git add src/thoth/providers/gemini.py
git commit -m "feat(gemini): implement submit() against client.aio.interactions.create"
```

---

### Task 8: submit() — error case tests + retry verification

**Files:**
- Test: `tests/test_gem_background.py:TestGeminiSubmit` (append cases)

- [ ] **Step 1: Add error-case tests**

Append to the `TestGeminiSubmit` class in `tests/test_gem_background.py`:

```python
    @pytest.mark.asyncio
    async def test_submit_auth_error_maps_to_api_key_error(self, provider, fake_client):
        """401 from create() must surface as APIKeyError."""
        from google.genai import errors as genai_errors

        from thoth.errors import APIKeyError

        async def raise_401(**kwargs):
            raise genai_errors.ClientError(401, {"error": {"message": "invalid"}})

        fake_client._fake_interactions.create = raise_401

        with pytest.raises(APIKeyError):
            await provider.submit(prompt="p", mode="gemini_quick_research")

    @pytest.mark.asyncio
    async def test_submit_free_tier_403_maps_to_thotherror(self, provider, fake_client):
        """403 from create() must surface as ThothError mentioning paid tier."""
        from google.genai import errors as genai_errors

        from thoth.errors import ThothError

        async def raise_403(**kwargs):
            raise genai_errors.ClientError(403, {"error": {"message": "free tier"}})

        fake_client._fake_interactions.create = raise_403

        with pytest.raises(ThothError) as exc_info:
            await provider.submit(prompt="p", mode="gemini_quick_research")
        suggestion = exc_info.value.suggestion or ""
        assert "tier" in suggestion.lower() or "pricing" in suggestion.lower()

    @pytest.mark.asyncio
    async def test_submit_rate_limit_maps_to_quota_error(self, provider, fake_client):
        """429 RESOURCE_EXHAUSTED → APIQuotaError."""
        from google.genai import errors as genai_errors

        from thoth.errors import APIQuotaError

        async def raise_429(**kwargs):
            raise genai_errors.ClientError(
                429,
                {"error": {"status": "RESOURCE_EXHAUSTED", "message": "quota"}},
            )

        fake_client._fake_interactions.create = raise_429

        with pytest.raises(APIQuotaError):
            await provider.submit(prompt="p", mode="gemini_quick_research")
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
uv run pytest tests/test_gem_background.py::TestGeminiSubmit -v
```

Expected: all 6 tests PASS (3 happy + 3 error). Tenacity retry shouldn't kick in for these error classes (they're not in the `retry_if_exception_type` list).

- [ ] **Step 3: Commit**

```bash
git add tests/test_gem_background.py
git commit -m "test(gemini): add submit() error-case tests for 401/403/429"
```

---

### Task 9: check_status() — failing tests for status enum

Per spec parity row 5 + provider-specific delta #3 (403-on-GET) + research doc §10.

**Files:**
- Test: `tests/test_gem_background.py` (append)

- [ ] **Step 1: Add the test class**

Append:

```python
class TestGeminiCheckStatus:
    """P28 parity row 5 + delta #3 (403-on-GET) + delta #4 (server cancel)."""

    @pytest.mark.asyncio
    async def test_in_progress_returns_running(self, provider, fake_client):
        provider.jobs["job-1"] = {"interaction_id": "job-1"}
        fake_client._fake_interactions.next_get_response = _FakeInteraction(
            id="job-1", status="in_progress"
        )

        result = await provider.check_status("job-1")

        assert result["status"] == "running"
        assert "progress" in result

    @pytest.mark.asyncio
    async def test_completed_returns_completed(self, provider, fake_client):
        provider.jobs["job-1"] = {"interaction_id": "job-1"}
        fake_client._fake_interactions.next_get_response = _FakeInteraction(
            id="job-1", status="completed"
        )

        result = await provider.check_status("job-1")

        assert result["status"] == "completed"
        assert result["progress"] == 1.0

    @pytest.mark.asyncio
    async def test_failed_returns_permanent_error(self, provider, fake_client):
        provider.jobs["job-1"] = {"interaction_id": "job-1"}
        fake_client._fake_interactions.next_get_response = _FakeInteraction(
            id="job-1", status="failed"
        )

        result = await provider.check_status("job-1")

        assert result["status"] == "permanent_error"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_cancelled_user_initiated_returns_cancelled(self, provider, fake_client):
        """User-initiated cancel: status=cancelled AND _cancel_requested[job]=True."""
        provider.jobs["job-1"] = {"interaction_id": "job-1"}
        provider._cancel_requested["job-1"] = True
        fake_client._fake_interactions.next_get_response = _FakeInteraction(
            id="job-1", status="cancelled"
        )

        result = await provider.check_status("job-1")

        assert result["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancelled_server_initiated_returns_permanent_error(
        self, provider, fake_client
    ):
        """Server-initiated cancel: status=cancelled AND _cancel_requested[job]=False.
        Per research doc §10 'instant cancel with no output'."""
        provider.jobs["job-1"] = {"interaction_id": "job-1"}
        provider._cancel_requested["job-1"] = False
        fake_client._fake_interactions.next_get_response = _FakeInteraction(
            id="job-1", status="cancelled"
        )

        result = await provider.check_status("job-1")

        assert result["status"] == "permanent_error"
        # Error message should hint at server-side capacity rejection
        assert "server" in result.get("error", "").lower()

    @pytest.mark.asyncio
    async def test_403_on_get_treated_as_transient(self, provider, fake_client):
        """Research doc §10 critical bug: GET /interactions/{id} returns 403 intermittently
        after a successful POST. Must be transient_error so polling retries."""
        from google.genai import errors as genai_errors

        provider.jobs["job-1"] = {"interaction_id": "job-1"}

        async def raise_403(id, **kwargs):
            raise genai_errors.ClientError(403, {"error": {"code": "permission_denied"}})

        fake_client._fake_interactions.get = raise_403

        result = await provider.check_status("job-1")

        assert result["status"] == "transient_error"

    @pytest.mark.asyncio
    async def test_unknown_job_returns_not_found(self, provider, fake_client):
        result = await provider.check_status("never-submitted")

        assert result["status"] == "not_found"
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/test_gem_background.py::TestGeminiCheckStatus -v
```

Expected: 7 FAIL with `AttributeError: ... has no attribute 'check_status'`.

- [ ] **Step 3: Commit failing tests**

```bash
git add tests/test_gem_background.py
git commit -m "test(gemini): add failing tests for check_status() status mapping"
```

---

### Task 10: check_status() — implement to make tests pass

**Files:**
- Modify: `src/thoth/providers/gemini.py:GeminiProvider`

- [ ] **Step 1: Add the check_status() method**

In `src/thoth/providers/gemini.py`, inside `GeminiProvider`, add:

```python
    async def check_status(self, job_id: str) -> dict[str, Any]:
        """Poll an in-flight Deep Research interaction.

        Returns a status dict with keys: status, progress, error (optional),
        error_class (optional). Status values per the runtime polling contract:
        running / queued / completed / cancelled / permanent_error /
        transient_error / not_found.

        Per research doc §10: GET /interactions/{id} can return 403 intermittently
        after a successful POST. We treat 403 as transient_error so the runtime's
        polling loop's max_transient_errors counter handles it.

        Per delta #4: status="cancelled" is ambiguous on Gemini — could be
        user-initiated (we flagged via _cancel_requested before calling cancel())
        or server-initiated capacity rejection (research doc §10 "instant cancel").
        Disambiguate using the local flag.
        """
        if job_id not in self.jobs:
            return {"status": "not_found", "error": "Job not found"}

        try:
            interaction = await self.client.aio.interactions.get(job_id)
            self.jobs[job_id]["interaction"] = interaction

            status = (interaction.status or "").lower()

            if status == "completed":
                return {"status": "completed", "progress": 1.0}

            if status == "in_progress":
                # No numeric progress available from Gemini; surface 0.5 as
                # placeholder consistent with how branch reference treated it.
                return {"status": "running", "progress": 0.5}

            if status == "queued":
                return {"status": "queued", "progress": 0.0}

            if status == "failed":
                return {
                    "status": "permanent_error",
                    "error": "Gemini reported the interaction failed",
                }

            if status == "cancelled":
                # Disambiguate: user vs server-initiated cancel.
                if self._cancel_requested.get(job_id, False):
                    return {"status": "cancelled", "error": "User cancelled"}
                return {
                    "status": "permanent_error",
                    "error": (
                        "Gemini server cancelled the interaction "
                        "(likely capacity / rate limit). Retry later."
                    ),
                }

            if status == "requires_action":
                # Not used by Deep Research per research doc §5; defensive.
                return {"status": "running", "progress": 0.5}

            return {"status": "running", "progress": 0.5}

        except Exception as e:
            # 403-on-GET intermittent bug (research doc §10) — surface as
            # transient_error so the runtime's max_transient_errors counter
            # handles it, instead of failing the whole operation.
            from google.genai import errors as genai_errors

            if isinstance(e, genai_errors.ClientError):
                code = getattr(e, "code", None) or getattr(e, "status_code", None)
                if code == 403:
                    return {
                        "status": "transient_error",
                        "error": "403 from interactions.get (intermittent Gemini bug)",
                        "error_class": "ClientError",
                    }
                if code in (401, 404, 400):
                    return {
                        "status": "permanent_error",
                        "error": str(e),
                        "error_class": type(e).__name__,
                    }
            if isinstance(e, genai_errors.ServerError):
                return {
                    "status": "transient_error",
                    "error": str(e),
                    "error_class": type(e).__name__,
                }
            # Unknown — treat as transient (mirrors OpenAI provider:335-344).
            return {
                "status": "transient_error",
                "error": str(e),
                "error_class": type(e).__name__,
            }
```

- [ ] **Step 2: Run tests to verify pass**

```bash
uv run pytest tests/test_gem_background.py::TestGeminiCheckStatus -v
```

Expected: 7 PASS.

- [ ] **Step 3: Commit**

```bash
git add src/thoth/providers/gemini.py
git commit -m "feat(gemini): implement check_status() with 403-quirk + cancel disambiguation"
```

---

### Task 11: get_result() — failing tests for result + citations

Per spec parity row 9 + delta #5 (empty annotations OK).

**Files:**
- Test: `tests/test_gem_background.py` (append)

- [ ] **Step 1: Add the test class**

Append:

```python
class TestGeminiGetResult:
    """P28 parity row 9 + delta #5: result extraction + citation rendering."""

    @pytest.mark.asyncio
    async def test_get_result_extracts_last_text_output(self, provider, fake_client):
        # Build a fake completed interaction with text output
        text_output = type(
            "TextOutput",
            (),
            {"type": "text", "text": "The full research report.", "annotations": []},
        )()
        completed = _FakeInteraction(
            id="job-1",
            status="completed",
            outputs=[text_output],
        )
        provider.jobs["job-1"] = {"interaction_id": "job-1", "interaction": completed}

        result = await provider.get_result("job-1")

        assert "The full research report." in result

    @pytest.mark.asyncio
    async def test_get_result_appends_sources_section_when_annotations_present(
        self, provider, fake_client
    ):
        text_output = type(
            "TextOutput",
            (),
            {
                "type": "text",
                "text": "Body text.",
                "annotations": [
                    type("A", (), {"url": "https://example.com/a"})(),
                    type("A", (), {"url": "https://example.com/b"})(),
                    type("A", (), {"url": "https://example.com/a"})(),  # dup
                ],
            },
        )()
        completed = _FakeInteraction(
            id="job-2",
            status="completed",
            outputs=[text_output],
        )
        provider.jobs["job-2"] = {"interaction_id": "job-2", "interaction": completed}

        result = await provider.get_result("job-2")

        assert "## Sources" in result
        # Deduplicated to 2 unique URLs
        assert result.count("https://example.com/a") == 1
        assert result.count("https://example.com/b") == 1

    @pytest.mark.asyncio
    async def test_get_result_no_sources_section_when_annotations_empty(
        self, provider, fake_client
    ):
        """Per delta #5: empty annotations is normal; emit text without ## Sources."""
        text_output = type(
            "TextOutput",
            (),
            {"type": "text", "text": "Body only.", "annotations": []},
        )()
        completed = _FakeInteraction(
            id="job-3",
            status="completed",
            outputs=[text_output],
        )
        provider.jobs["job-3"] = {"interaction_id": "job-3", "interaction": completed}

        result = await provider.get_result("job-3")

        assert "Body only." in result
        assert "## Sources" not in result

    @pytest.mark.asyncio
    async def test_get_result_unknown_job_raises(self, provider, fake_client):
        with pytest.raises(ValueError, match="Job .* not found"):
            await provider.get_result("never-existed")
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/test_gem_background.py::TestGeminiGetResult -v
```

Expected: 4 FAIL with `AttributeError: ... has no attribute 'get_result'`.

- [ ] **Step 3: Commit failing tests**

```bash
git add tests/test_gem_background.py
git commit -m "test(gemini): add failing tests for get_result() + citation extraction"
```

---

### Task 12: get_result() — implement to make tests pass

**Files:**
- Modify: `src/thoth/providers/gemini.py:GeminiProvider`

- [ ] **Step 1: Add get_result() method**

In `src/thoth/providers/gemini.py`, inside `GeminiProvider`, add:

```python
    async def get_result(self, job_id: str, verbose: bool = False) -> str:
        """Retrieve the final research report from a completed interaction.

        Per research doc §6: completed interactions have outputs[-1].text as
        the research report. Per research doc §10: stored result fragility
        means we should NOT re-fetch unconditionally — use the cached
        interaction object first, only fetch if it isn't completed yet.

        Per spec delta #5: annotations may be empty/absent on completed runs.
        We dedupe by URL and append a "## Sources" markdown section ONLY when
        non-empty.
        """
        if job_id not in self.jobs:
            raise ValueError(f"Job {job_id} not found")

        cached = self.jobs[job_id].get("interaction")

        # If cached isn't completed, fetch fresh.
        if cached is None or (cached.status or "").lower() != "completed":
            try:
                interaction = await self.client.aio.interactions.get(job_id)
                self.jobs[job_id]["interaction"] = interaction
            except Exception as e:
                # Per research doc §10: completed results can revert. If we
                # have a cached completed result, fall back to it.
                if cached and (cached.status or "").lower() == "completed":
                    interaction = cached
                else:
                    raise _map_gemini_error(e, model=self.model, verbose=verbose) from e
        else:
            interaction = cached

        outputs = getattr(interaction, "outputs", None) or []
        if not outputs:
            return "No research output was generated."

        # Find the last text-typed output.
        report_text = ""
        annotations: list[Any] = []
        for output in reversed(outputs):
            otype = getattr(output, "type", None)
            text = getattr(output, "text", None)
            if otype == "text" and text:
                report_text = text
                annotations = list(getattr(output, "annotations", None) or [])
                break

        if not report_text:
            # Fallback: any output with .text
            for output in outputs:
                text = getattr(output, "text", None)
                if text:
                    report_text = text
                    annotations = list(getattr(output, "annotations", None) or [])
                    break

        if not report_text:
            return "Research completed but no text content was found in outputs."

        # Citation rendering — only if non-empty after dedup.
        if annotations:
            seen_urls: set[str] = set()
            unique_sources: list[str] = []
            for ann in annotations:
                url = getattr(ann, "url", None) or (
                    ann.get("url") if isinstance(ann, dict) else None
                )
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    domain = url.split("//")[-1].split("/")[0]
                    unique_sources.append(f"- [{domain}]({url})")

            if unique_sources:
                report_text += "\n\n## Sources\n" + "\n".join(unique_sources)

        return report_text
```

- [ ] **Step 2: Run tests to verify pass**

```bash
uv run pytest tests/test_gem_background.py::TestGeminiGetResult -v
```

Expected: 4 PASS.

- [ ] **Step 3: Commit**

```bash
git add src/thoth/providers/gemini.py
git commit -m "feat(gemini): implement get_result() with citation extraction + empty-OK"
```

---

### Task 13: cancel() — failing tests for user vs server cancel

Per spec parity row 7 + delta #4.

**Files:**
- Test: `tests/test_gem_background.py` (append)

- [ ] **Step 1: Add tests**

Append:

```python
class TestGeminiCancel:
    """P28 parity row 7: cancel() honors SDK + sets local flag for disambiguation."""

    @pytest.mark.asyncio
    async def test_cancel_calls_sdk_and_sets_flag(self, provider, fake_client):
        provider.jobs["job-1"] = {"interaction_id": "job-1"}
        provider._cancel_requested["job-1"] = False
        fake_client._fake_interactions.next_cancel_response = _FakeInteraction(
            id="job-1", status="cancelled"
        )

        result = await provider.cancel("job-1")

        assert provider._cancel_requested["job-1"] is True
        assert "job-1" in fake_client._fake_interactions.cancel_calls
        assert result["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_already_completed_returns_completed(self, provider, fake_client):
        """If the interaction completed before cancel landed, surface that."""
        provider.jobs["job-1"] = {"interaction_id": "job-1"}
        fake_client._fake_interactions.next_cancel_response = _FakeInteraction(
            id="job-1", status="completed"
        )

        result = await provider.cancel("job-1")

        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_cancel_unknown_job_attempts_reconnect_then_cancel(
        self, provider, fake_client
    ):
        """If job_id isn't in self.jobs, cancel() should call reconnect first
        (mirrors OpenAI provider behavior at openai.py:368-376)."""
        fake_client._fake_interactions.next_get_response = _FakeInteraction(
            id="external-job", status="in_progress"
        )
        fake_client._fake_interactions.next_cancel_response = _FakeInteraction(
            id="external-job", status="cancelled"
        )

        result = await provider.cancel("external-job")

        assert result["status"] == "cancelled"
        assert "external-job" in provider.jobs
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/test_gem_background.py::TestGeminiCancel -v
```

Expected: 3 FAIL.

- [ ] **Step 3: Commit failing tests**

```bash
git add tests/test_gem_background.py
git commit -m "test(gemini): add failing tests for cancel() + reconnect-on-unknown"
```

---

### Task 14: cancel() and reconnect() — implement

**Files:**
- Modify: `src/thoth/providers/gemini.py:GeminiProvider`

- [ ] **Step 1: Add reconnect() and cancel() methods**

In `src/thoth/providers/gemini.py`, inside `GeminiProvider`, add:

```python
    async def reconnect(self, job_id: str) -> None:
        """Re-attach to an existing background interaction after process restart."""
        try:
            interaction = await self.client.aio.interactions.get(job_id)
            self.jobs[job_id] = {
                "interaction_id": job_id,
                "interaction": interaction,
                "created_at": datetime.now(),
            }
            self._cancel_requested.setdefault(job_id, False)
        except Exception as e:
            raise _map_gemini_error(e, model=self.model) from e

    async def cancel(self, job_id: str) -> dict[str, Any]:
        """Cancel a running interaction. Sets the _cancel_requested flag BEFORE
        the SDK call so check_status() can disambiguate user vs server cancel.
        """
        if job_id not in self.jobs:
            await self.reconnect(job_id)

        # Critical: set the flag BEFORE the cancel call. This is what
        # check_status() uses to distinguish user-initiated from
        # server-initiated cancels (research doc §10).
        self._cancel_requested[job_id] = True

        try:
            interaction = await self.client.aio.interactions.cancel(job_id)
            self.jobs[job_id]["interaction"] = interaction

            status = (interaction.status or "").lower()
            if status == "completed":
                # Job finished before our cancel landed — return completed.
                return {"status": "completed", "progress": 1.0}
            return {"status": "cancelled", "error": "User cancelled the interaction"}

        except Exception as e:
            return {
                "status": "permanent_error",
                "error": str(e),
                "error_class": type(e).__name__,
            }
```

- [ ] **Step 2: Run tests to verify pass**

```bash
uv run pytest tests/test_gem_background.py::TestGeminiCancel -v
```

Expected: 3 PASS.

- [ ] **Step 3: Commit**

```bash
git add src/thoth/providers/gemini.py
git commit -m "feat(gemini): implement cancel() + reconnect() with disambiguation flag"
```

---

### Task 15: list_models() — failing test + implement

Per parity row 3 (sub-bullet). Gemini exposes only the one DR agent currently, so this is hard-coded with a cache layer.

**Files:**
- Test: `tests/test_gem_background.py` (append)
- Modify: `src/thoth/providers/gemini.py:GeminiProvider`

- [ ] **Step 1: Add test**

Append:

```python
class TestGeminiListModels:
    """list_models() returns the deep-research agent. Gemini exposes only one."""

    @pytest.mark.asyncio
    async def test_list_models_includes_deep_research_agent(self, provider):
        models = await provider.list_models()

        ids = [m["id"] for m in models]
        assert "deep-research-pro-preview-12-2025" in ids

    @pytest.mark.asyncio
    async def test_list_models_cached_uses_cache(self, provider, monkeypatch, tmp_path):
        from thoth.models import ModelCache

        # Force the cache directory into tmp so this test is hermetic.
        cache = ModelCache("gemini")
        monkeypatch.setattr(provider, "model_cache", cache)
        # Pre-populate cache with a sentinel
        cache.save_cache([{"id": "from-cache", "owned_by": "google"}])
        # Now make the cache valid (it should be after save)
        result = await provider.list_models_cached(force_refresh=False, no_cache=False)
        assert any(m["id"] == "from-cache" for m in result)
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/test_gem_background.py::TestGeminiListModels -v
```

Expected: 2 FAIL.

- [ ] **Step 3: Implement list_models() + list_models_cached()**

Append to `GeminiProvider` in `src/thoth/providers/gemini.py`:

```python
    async def list_models(self) -> list[dict[str, Any]]:
        """Return available Gemini Deep Research agents.

        Per research doc §3: deep-research-pro-preview-12-2025 is the only
        built-in agent currently. Hardcoded; revisit if Google ships variants.
        """
        return [
            {
                "id": DEEP_RESEARCH_AGENT_ID,
                "type": "deep_research",
                "owned_by": "google",
                "created": 1733000000,  # approximate Dec 2024
            }
        ]

    async def list_models_cached(
        self, force_refresh: bool = False, no_cache: bool = False
    ) -> list[dict[str, Any]]:
        """List models with on-disk cache support."""
        if not force_refresh and not no_cache and self.model_cache.is_cache_valid():
            cached = self.model_cache.load_cache()
            if cached is not None:
                return cached

        models = await self.list_models()

        if not no_cache:
            self.model_cache.save_cache(models)

        return models
```

- [ ] **Step 4: Run tests to verify pass**

```bash
uv run pytest tests/test_gem_background.py::TestGeminiListModels -v
```

Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_gem_background.py src/thoth/providers/gemini.py
git commit -m "feat(gemini): implement list_models() + list_models_cached()"
```

---

### Task 16: Add 9 gemini_* modes to KNOWN_MODELS

Per spec parity row 2.

**Files:**
- Test: `tests/test_gem_background.py` (append)
- Modify: `src/thoth/config.py:KNOWN_MODELS`

- [ ] **Step 1: Add test asserting all 9 modes exist**

Append:

```python
class TestGeminiModes:
    """P28 parity row 2: 9 gemini_* modes mirroring OpenAI's set."""

    @pytest.mark.parametrize(
        "mode_name",
        [
            "gemini_quick_research",
            "gemini_exploration",
            "gemini_deep_dive",
            "gemini_tutorial",
            "gemini_solution",
            "gemini_prd",
            "gemini_tdd",
            "gemini_deep_research",
            "gemini_comparison",
        ],
    )
    def test_gemini_mode_exists_in_known_models(self, mode_name):
        from thoth.config import KNOWN_MODELS

        assert mode_name in KNOWN_MODELS, f"{mode_name} missing from KNOWN_MODELS"

        cfg = KNOWN_MODELS[mode_name]
        assert cfg["provider"] == "gemini"
        assert cfg["kind"] == "background"
        assert cfg["model"] == "deep-research-pro-preview-12-2025"
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/test_gem_background.py::TestGeminiModes -v
```

Expected: 9 FAIL with `AssertionError: gemini_quick_research missing from KNOWN_MODELS` etc.

- [ ] **Step 3: Add mode entries**

In `src/thoth/config.py`, find the existing `KNOWN_MODELS` dict (around line 53). Just before the closing `}`, add 9 new entries. Each mirrors the OpenAI counterpart's `system_prompt` / `description` (purpose is provider-independent), changing only `provider` and `model`:

```python
    "gemini_quick_research": {
        "provider": "gemini",
        "kind": "background",
        "model": "deep-research-pro-preview-12-2025",
        "description": "Lightweight Gemini Deep Research (~10-20 min, ~$2-3/run).",
        "system_prompt": "You are a helpful research assistant. Provide concise, well-sourced answers.",
        "auto_input": False,
    },
    "gemini_exploration": {
        "provider": "gemini",
        "kind": "background",
        "model": "deep-research-pro-preview-12-2025",
        "description": "Gemini exploration of a topic — broad-scope research.",
        "system_prompt": "Conduct broad exploratory research on the topic. Identify key dimensions, sources, and open questions.",
        "auto_input": False,
        "next": "gemini_deep_dive",
    },
    "gemini_deep_dive": {
        "provider": "gemini",
        "kind": "background",
        "model": "deep-research-pro-preview-12-2025",
        "description": "Gemini deep dive into a focused topic.",
        "system_prompt": "Produce an in-depth analysis with technical details and citations.",
        "auto_input": True,
        "previous": "gemini_exploration",
        "next": "gemini_tutorial",
    },
    "gemini_tutorial": {
        "provider": "gemini",
        "kind": "background",
        "model": "deep-research-pro-preview-12-2025",
        "description": "Gemini tutorial generation from prior research.",
        "system_prompt": "Write a step-by-step tutorial. Include examples and prerequisites.",
        "auto_input": True,
        "previous": "gemini_deep_dive",
    },
    "gemini_solution": {
        "provider": "gemini",
        "kind": "background",
        "model": "deep-research-pro-preview-12-2025",
        "description": "Gemini solution proposal for a problem.",
        "system_prompt": "Propose a concrete solution. Include trade-offs and implementation considerations.",
        "auto_input": False,
    },
    "gemini_prd": {
        "provider": "gemini",
        "kind": "background",
        "model": "deep-research-pro-preview-12-2025",
        "description": "Gemini PRD generation.",
        "system_prompt": "Produce a Product Requirements Document with goal, scope, success criteria, and out-of-scope items.",
        "auto_input": False,
    },
    "gemini_tdd": {
        "provider": "gemini",
        "kind": "background",
        "model": "deep-research-pro-preview-12-2025",
        "description": "Gemini test-driven design proposal.",
        "system_prompt": "Produce a TDD-style design: tests first, then implementation outline.",
        "auto_input": False,
    },
    "gemini_deep_research": {
        "provider": "gemini",
        "kind": "background",
        "model": "deep-research-pro-preview-12-2025",
        "description": "Comprehensive Gemini Deep Research (~20+ min, ~$4-6/run).",
        "system_prompt": "Conduct comprehensive multi-step research. Cite all claims with URLs.",
        "auto_input": True,
    },
    "gemini_comparison": {
        "provider": "gemini",
        "kind": "background",
        "model": "deep-research-pro-preview-12-2025",
        "description": "Gemini comparison-mode research.",
        "system_prompt": "Compare the topics or options provided. Use tables where appropriate.",
        "auto_input": False,
    },
```

The exact `system_prompt` text should mirror the OpenAI counterpart — open `src/thoth/config.py` and copy each prompt string from the matching `quick_research` / `exploration` / etc. mode, swapping only `provider` and `model`. The text above is approximate; use the existing prompts verbatim if they differ.

- [ ] **Step 4: Run tests to verify pass**

```bash
uv run pytest tests/test_gem_background.py::TestGeminiModes -v
```

Expected: 9 PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_gem_background.py src/thoth/config.py
git commit -m "feat(gemini): add 9 gemini_* modes to KNOWN_MODELS"
```

---

### Task 17: Add `--api-key-gemini` CLI flag

Per spec parity row 1.

**Files:**
- Modify: `src/thoth/cli_subcommands/_options.py`

- [ ] **Step 1: Add the flag tuple**

In `src/thoth/cli_subcommands/_options.py`, find the existing block:

```python
    (
        ("--api-key-openai",),
        {"help": "API key for OpenAI provider (not recommended; prefer env vars)"},
    ),
    (
        ("--api-key-perplexity",),
        {"help": "API key for Perplexity provider (not recommended; prefer env vars)"},
    ),
    (
        ("--api-key-mock",),
        {"help": "API key for Mock provider (not recommended; prefer env vars)"},
    ),
```

Add a new tuple between the perplexity and mock entries:

```python
    (
        ("--api-key-perplexity",),
        {"help": "API key for Perplexity provider (not recommended; prefer env vars)"},
    ),
    (
        ("--api-key-gemini",),
        {"help": "API key for Gemini provider (not recommended; prefer env vars)"},
    ),
    (
        ("--api-key-mock",),
        {"help": "API key for Mock provider (not recommended; prefer env vars)"},
    ),
```

- [ ] **Step 2: Verify the flag is wired through to commands**

```bash
uv run thoth ask --help 2>&1 | grep -i 'api-key-gemini'
```

Expected: line showing `--api-key-gemini TEXT` in the output.

- [ ] **Step 3: Verify resume subcommand also picks it up**

```bash
uv run thoth resume --help 2>&1 | grep -i 'api-key-gemini'
```

Expected: line showing `--api-key-gemini TEXT`. (If absent, check whether resume.py applies the same option group; it should, per the existing pattern.)

- [ ] **Step 4: Commit**

```bash
git add src/thoth/cli_subcommands/_options.py
git commit -m "feat(gemini): add --api-key-gemini CLI flag"
```

---

### Task 18: Add `[providers.gemini]` defaults to ConfigSchema

**Files:**
- Test: `tests/test_provider_config.py:<existing>` (extend)
- Modify: `src/thoth/config.py:ConfigSchema.get_defaults`

- [ ] **Step 1: Add test asserting defaults exist**

Append to `tests/test_provider_config.py` (or create a new test in `tests/test_gem_background.py` if that's cleaner):

```python
class TestGeminiConfigDefaults:
    """[providers.gemini] block must exist with default api_key placeholder."""

    def test_gemini_provider_in_default_config(self):
        from thoth.config import ConfigSchema

        defaults = ConfigSchema.get_defaults()
        assert "gemini" in defaults["providers"]
        assert defaults["providers"]["gemini"]["api_key"] == "${GEMINI_API_KEY}"

    def test_gemini_provider_has_polling_tunables(self):
        from thoth.config import ConfigSchema

        defaults = ConfigSchema.get_defaults()
        gem = defaults["providers"]["gemini"]
        assert gem.get("poll_interval") == 10
        assert gem.get("max_wait_minutes") == 20
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/test_gem_background.py::TestGeminiConfigDefaults -v
```

Expected: 2 FAIL.

- [ ] **Step 3: Add the defaults block**

In `src/thoth/config.py`, find the `providers:` block inside `ConfigSchema.get_defaults()` (around line 254):

```python
            "providers": {
                "openai": {"api_key": "${OPENAI_API_KEY}"},
                "perplexity": {"api_key": "${PERPLEXITY_API_KEY}"},
            },
```

Replace with:

```python
            "providers": {
                "openai": {"api_key": "${OPENAI_API_KEY}"},
                "perplexity": {"api_key": "${PERPLEXITY_API_KEY}"},
                "gemini": {
                    "api_key": "${GEMINI_API_KEY}",
                    "poll_interval": 10,
                    "max_wait_minutes": 20,
                },
            },
```

- [ ] **Step 4: Run tests to verify pass**

```bash
uv run pytest tests/test_gem_background.py::TestGeminiConfigDefaults -v
```

Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_gem_background.py src/thoth/config.py
git commit -m "feat(gemini): add [providers.gemini] defaults with 10s/20min polling"
```

---

### Task 19: Provider-specific polling tunables wired into runtime

The runtime's `_run_polling_loop` already reads `config["execution"]["poll_interval"]`. P28 wants per-provider override. Verify this already works OR add minimal wiring.

**Files:**
- Test: existing `tests/test_polling_interval.py` (extend) OR `tests/test_gem_background.py`
- Modify: possibly `src/thoth/run.py` (only if runtime doesn't already honor per-provider config)

- [ ] **Step 1: Check current polling config wiring**

```bash
grep -n "poll_interval\|max_wait" /Users/stevemorin/c/thoth/src/thoth/run.py | head -20
```

Read the output. If `_run_polling_loop` reads from `config["providers"][name].get("poll_interval", config["execution"]["poll_interval"])`, the per-provider override already works — proceed to step 4 (no code change). If it only reads `config["execution"]["poll_interval"]`, do step 2-3.

- [ ] **Step 2: Add the per-provider override (only if needed)**

If the runtime needs the change, find the line in `_run_polling_loop` that reads the polling interval and wrap it:

```python
# Replace:
poll_interval = config["execution"]["poll_interval"]

# With:
provider_cfg = config.get("providers", {}).get(provider_name, {})
poll_interval = provider_cfg.get(
    "poll_interval",
    config["execution"]["poll_interval"],
)
max_wait_minutes = provider_cfg.get(
    "max_wait_minutes",
    config["execution"]["max_wait"],
)
```

- [ ] **Step 3: Add a regression test**

In `tests/test_gem_background.py`, append:

```python
class TestGeminiPollingTunables:
    def test_provider_uses_gemini_poll_interval(self):
        """When provider=gemini, runtime should respect [providers.gemini] poll_interval=10."""
        from thoth.config import ConfigManager

        # Smoke test against ConfigManager — assert gemini block reads as expected.
        # Full runtime integration is covered in test_polling_interval.py / VCR tests.
        cm = ConfigManager.from_dict_overrides({})
        gem_cfg = cm.data.get("providers", {}).get("gemini", {})
        assert gem_cfg.get("poll_interval") == 10
        assert gem_cfg.get("max_wait_minutes") == 20
```

- [ ] **Step 4: Run any added tests**

```bash
uv run pytest tests/test_gem_background.py::TestGeminiPollingTunables -v
```

Expected: PASS (or skip the test if the existing runtime already covers the path with current tests).

- [ ] **Step 5: Commit**

```bash
git add src/thoth/run.py tests/test_gem_background.py
git commit -m "feat(gemini): per-provider polling tunables (10s/20min override)"
```

If only the test was added (no run.py change), use:

```bash
git add tests/test_gem_background.py
git commit -m "test(gemini): assert [providers.gemini] polling tunables resolve"
```

---

### Task 20: Run full default test suite — green gate before VCR

Before recording cassettes (which requires real API access), confirm all monkeypatched-SDK tests pass on a clean install.

- [ ] **Step 1: Run the full pytest suite**

```bash
cd /Users/stevemorin/c/thoth
uv run pytest -v 2>&1 | tail -20
```

Expected: all tests pass; new gemini tests included; no regressions in OpenAI / mock / Perplexity paths.

- [ ] **Step 2: Run lint + format + typecheck (the lefthook gate)**

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run ty check src/
```

Expected: all three pass.

- [ ] **Step 3: Run the thoth_test integration suite**

```bash
./thoth_test -r --provider mock --skip-interactive -q
```

Expected: pass (no Gemini-specific tests added there yet; mock provider should still pass).

- [ ] **Step 4: If everything passes, commit a checkpoint marker (optional)**

If the prior commits weren't full-gated, this is a good point to ensure everything's green:

```bash
git status
# Should report clean working tree
```

No new commit needed if the working tree is clean. If formatting changes were made, commit them:

```bash
git add -u
git commit -m "style(gemini): apply ruff formatting after provider implementation"
```

---

### Task 21: Record happy-path VCR cassette (manual step)

Per spec test strategy. Requires `GEMINI_API_KEY` in the environment.

**Files:**
- Create: `thoth_test_cassettes/gemini/happy-path.yaml`

⚠ **This task incurs real API cost (~$2-3 for one Deep Research call)**.

- [ ] **Step 1: Verify GEMINI_API_KEY is set**

```bash
echo "${GEMINI_API_KEY:0:8}..."
```

Expected: prints first 8 characters. If empty, get a key from https://aistudio.google.com/apikey and export it.

- [ ] **Step 2: Create a temporary recording script**

Create `/tmp/record_gemini_cassette.py`:

```python
"""One-off cassette recording. Delete after running."""
import asyncio
import os
import vcr
from thoth.providers.gemini import GeminiProvider

CASSETTE_PATH = "thoth_test_cassettes/gemini/happy-path.yaml"
PROMPT = "Briefly summarize what an LLM is in two paragraphs."


async def record():
    provider = GeminiProvider(
        api_key=os.environ["GEMINI_API_KEY"],
        config={"poll_interval": 10, "max_wait_minutes": 20},
    )
    job_id = await provider.submit(prompt=PROMPT, mode="gemini_quick_research")
    print(f"Submitted: {job_id}")

    # Poll
    while True:
        status = await provider.check_status(job_id)
        print(f"Status: {status['status']}")
        if status["status"] == "completed":
            break
        if status["status"] in ("failed", "cancelled", "permanent_error"):
            raise RuntimeError(f"Failed: {status}")
        await asyncio.sleep(provider.poll_interval)

    result = await provider.get_result(job_id)
    print(f"Result preview: {result[:200]}")
    print("Done.")


with vcr.use_cassette(
    CASSETTE_PATH,
    record_mode="all",
    match_on=["uri", "method"],
):
    asyncio.run(record())
```

- [ ] **Step 3: Run the recording**

```bash
mkdir -p thoth_test_cassettes/gemini
uv run python /tmp/record_gemini_cassette.py
```

Expected: ~10-20 min runtime. Final output: `Done.`. The file `thoth_test_cassettes/gemini/happy-path.yaml` is created.

⚠ If VCR cannot intercept the google-genai SDK's transport (Open Question #1 from the spec), this script fails or produces an empty cassette. In that case, abandon VCR for this provider and add `pytest.skip("google-genai not VCR-compatible; relies on monkeypatched-SDK tests instead")` to `tests/test_vcr_gemini.py`. The unit tests already cover the contract.

- [ ] **Step 4: Inspect the cassette to verify it captured the interactions**

```bash
head -50 thoth_test_cassettes/gemini/happy-path.yaml
wc -l thoth_test_cassettes/gemini/happy-path.yaml
```

Expected: YAML with `interactions:` block, several requests (one POST to `/interactions`, multiple GETs to `/interactions/{id}`), responses with status codes 200.

- [ ] **Step 5: Replace key with replay sentinel**

The cassette will have the real API key in headers. Sanitize by replacing it:

```bash
sed -i.bak "s|${GEMINI_API_KEY}|gemini-replay-dummy|g" thoth_test_cassettes/gemini/happy-path.yaml
rm thoth_test_cassettes/gemini/happy-path.yaml.bak
```

- [ ] **Step 6: Verify gitleaks pass**

```bash
gitleaks detect --no-git --source thoth_test_cassettes/gemini/happy-path.yaml
```

Expected: no leaks reported.

- [ ] **Step 7: Commit the cassette**

```bash
rm /tmp/record_gemini_cassette.py
git add thoth_test_cassettes/gemini/happy-path.yaml
git commit -m "test(gemini): record happy-path VCR cassette"
```

---

### Task 22: Add VCR replay tests

**Files:**
- Create: `tests/test_vcr_gemini.py`

- [ ] **Step 1: Create the file**

```python
"""VCR cassette replay tests for GeminiProvider — mirrors test_vcr_openai.py."""

from __future__ import annotations

import asyncio

from tests.conftest import CASSETTE_DIR, thoth_vcr

GEMINI_CASSETTE = str(CASSETTE_DIR / "gemini" / "happy-path.yaml")


def _run(coro):
    return asyncio.run(coro)


def _make_provider():
    from thoth.providers.gemini import GeminiProvider

    return GeminiProvider(
        api_key="gemini-replay-dummy",
        config={"poll_interval": 0.0, "max_wait_minutes": 30},
    )


class TestGeminiSubmit:
    """Replay the happy-path cassette through GeminiProvider.submit()."""

    @thoth_vcr(GEMINI_CASSETTE)
    def test_submit_returns_interaction_id(self):
        provider = _make_provider()
        job_id = _run(provider.submit(
            prompt="Briefly summarize what an LLM is in two paragraphs.",
            mode="gemini_quick_research",
        ))
        assert job_id  # Non-empty
        assert job_id in provider.jobs


class TestGeminiCheckStatus:
    @thoth_vcr(GEMINI_CASSETTE)
    def test_check_status_replay_completes(self):
        provider = _make_provider()
        job_id = _run(provider.submit(
            prompt="Briefly summarize what an LLM is in two paragraphs.",
            mode="gemini_quick_research",
        ))

        # Poll until completed (cassette has finite events)
        for _ in range(50):
            status = _run(provider.check_status(job_id))
            if status["status"] == "completed":
                break
        else:
            raise AssertionError(f"never reached completed: {status}")

        assert status["status"] == "completed"


class TestGeminiGetResult:
    @thoth_vcr(GEMINI_CASSETTE)
    def test_get_result_returns_text(self):
        provider = _make_provider()
        job_id = _run(provider.submit(
            prompt="Briefly summarize what an LLM is in two paragraphs.",
            mode="gemini_quick_research",
        ))
        for _ in range(50):
            status = _run(provider.check_status(job_id))
            if status["status"] == "completed":
                break

        result = _run(provider.get_result(job_id))
        assert isinstance(result, str)
        assert len(result) > 0
```

- [ ] **Step 2: Run the replay tests**

```bash
uv run pytest tests/test_vcr_gemini.py -v
```

Expected: 3 PASS.

If VCR was abandoned in Task 21, the tests should be `pytest.skip()`-ed and produce 3 SKIPPED.

- [ ] **Step 3: Commit**

```bash
git add tests/test_vcr_gemini.py
git commit -m "test(gemini): add VCR cassette replay tests"
```

---

### Task 23: Live-API gated tests + workflow YAML edits

Per spec test strategy, third layer.

**Files:**
- Create: `tests/extended/test_gemini_real_workflows.py`
- Modify: `.github/workflows/live-api.yml`
- Modify: `.github/workflows/extended.yml`

- [ ] **Step 1: Create the live-API test file**

```python
"""Live-API tests for Gemini Deep Research — gated by @pytest.mark.live_api.

Deselected by default. Run weekly via .github/workflows/live-api.yml or
manually with `pytest -m live_api` and GEMINI_API_KEY set.

⚠ Each test in this file costs ~$2-3 in real API spend.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

import pytest

requires_gemini_key = pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set",
)


@pytest.mark.live_api
@requires_gemini_key
class TestGeminiLiveCLIWorkflows:
    """End-to-end thoth ask --provider gemini against live API."""

    def test_ask_gemini_quick_research_writes_output(self, tmp_path):
        """Smoke test: thoth ask --mode gemini_quick_research writes a file."""
        out_dir = tmp_path / "out"
        out_dir.mkdir()

        result = subprocess.run(
            [
                "uv", "run", "thoth", "ask",
                "--mode", "gemini_quick_research",
                "--output-dir", str(out_dir),
                "--project", "test-live",
                "What are LLMs?",
            ],
            capture_output=True,
            text=True,
            timeout=1800,  # 30 min
        )

        assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"

        # File should exist matching <timestamp>_*_gemini_*.md pattern
        produced = list((out_dir / "test-live").glob("*_gemini_*.md"))
        assert produced, "no gemini output file produced"
        assert produced[0].read_text(), "output file is empty"

    def test_ask_gemini_invalid_key_surfaces_error(self):
        """A clearly invalid key must surface a useful error, not a stack trace."""
        env = os.environ.copy()
        env["GEMINI_API_KEY"] = "definitely-invalid-key-aaaaaaaaaaaa"

        result = subprocess.run(
            [
                "uv", "run", "thoth", "ask",
                "--mode", "gemini_quick_research",
                "What are LLMs?",
            ],
            capture_output=True,
            text=True,
            env=env,
            timeout=60,
        )

        assert result.returncode != 0
        # Look for our friendly error message, not a raw exception
        combined = result.stdout + result.stderr
        assert "api key" in combined.lower() or "gemini" in combined.lower()
        assert "Traceback" not in combined, "raw traceback leaked to user"
```

- [ ] **Step 2: Run locally (only if GEMINI_API_KEY is set and you accept the cost)**

```bash
uv run pytest tests/extended/test_gemini_real_workflows.py -m live_api -v
```

Expected: 2 PASS (one will take ~10-20 min for the real Deep Research call).

If you're not running locally, skip to step 3.

- [ ] **Step 3: Add `GEMINI_API_KEY` to `.github/workflows/live-api.yml`**

Open `.github/workflows/live-api.yml` and find the existing `env:` block where `OPENAI_API_KEY` is referenced from a secret. Add `GEMINI_API_KEY` alongside:

```yaml
      - name: Run live-api tests
        run: uv run pytest -m live_api -v
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
```

(Exact key name and surrounding context will follow the existing file's shape.)

- [ ] **Step 4: Add `GEMINI_API_KEY` to `.github/workflows/extended.yml` as well**

Same edit shape — add the env var for `extended.yml`'s test step. The `tests/extended/test_model_kind_runtime.py` test will iterate KNOWN_MODELS, hit the gemini_* entries, and need the API key for each model-kind drift check.

- [ ] **Step 5: Note: configure the GitHub repo secret**

Manually (not in code): add `GEMINI_API_KEY` as a repo secret at https://github.com/smorin/thoth/settings/secrets/actions. This is documented in the commit message but cannot be done from this plan.

- [ ] **Step 6: Commit**

```bash
git add tests/extended/test_gemini_real_workflows.py .github/workflows/live-api.yml .github/workflows/extended.yml
git commit -m "test(gemini): add live_api workflow tests + extended/live-api YAML wiring

Repo secret GEMINI_API_KEY must be configured at
https://github.com/smorin/thoth/settings/secrets/actions before the
nightly extended and weekly live-api workflows include Gemini coverage.
The workflows have continue-on-error: true (informational), so missing
secrets fail the job non-blocking until configured."
```

---

### Task 24: README cost callout + manual smoke test

Per spec out-of-scope item #8 and provider-specific delta #10 — surface costs in user-facing docs.

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Find the existing provider section in README**

```bash
grep -n "OpenAI\|Perplexity\|providers" /Users/stevemorin/c/thoth/README.md | head -20
```

Identify where providers are listed. Add a Gemini section near the OpenAI listing.

- [ ] **Step 2: Add Gemini section**

In `README.md`, after the OpenAI provider description (find by grep), insert:

```markdown
### Gemini Deep Research

`thoth` supports Google Gemini Deep Research as an asynchronous (background) provider via the Interactions API.

- **Default model:** `deep-research-pro-preview-12-2025` (the only built-in Deep Research agent currently available)
- **API key:** set `GEMINI_API_KEY` env var or pass `--api-key-gemini`
- **Tier requirement:** Tier 1+ paid tier — Deep Research is **not available on the free tier**
- **Cost:** approximately **$2-3 per standard task, $4-6 per complex task** (the agent autonomously determines search depth; there is no per-call cost cap)
- **Wall-clock:** typically 10-20 minutes per call; hard polling timeout 20 minutes (Gemini's stuck-in-progress bug workaround)

Available modes (mirror of the OpenAI mode set):

```bash
thoth ask --mode gemini_quick_research "What is X?"      # ~10-15 min, ~$2-3
thoth ask --mode gemini_deep_research "Comprehensive Y"  # ~20+ min, ~$4-6
# also: gemini_exploration, gemini_deep_dive, gemini_tutorial,
# gemini_solution, gemini_prd, gemini_tdd, gemini_comparison
```

Cross-provider mode chaining is supported — you can run `exploration → gemini_deep_dive → tutorial` to mix OpenAI and Gemini in a single chain.
```

- [ ] **Step 3: Run a manual smoke test (optional, requires API key)**

```bash
GEMINI_API_KEY=<your-key> uv run thoth ask --mode gemini_quick_research --project gemini-smoke "What are the three core principles of REST?"
```

Expected (after ~10-20 min): output file written under `research-outputs/gemini-smoke/<timestamp>_gemini_quick_research_gemini_*.md` containing a multi-paragraph answer with `## Sources` if annotations were returned.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs(gemini): add README cost callout + mode listing"
```

---

### Task 25: Final integration verification

Full-gate run. The committed-state should be clean and ready to PR.

- [ ] **Step 1: Run the lefthook-equivalent full gate**

```bash
cd /Users/stevemorin/c/thoth
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run ty check src/
uv run pytest -q
./thoth_test -r --skip-interactive -q
```

Expected: all 5 pass.

- [ ] **Step 2: Verify `thoth modes` lists the 9 new gemini modes**

```bash
uv run thoth modes 2>&1 | grep -i gemini
```

Expected: 9 lines, one per gemini_* mode.

- [ ] **Step 3: Verify `thoth providers --models --provider gemini` works**

```bash
uv run thoth providers --models --provider gemini
```

Expected: lists `deep-research-pro-preview-12-2025` (no API call required for hardcoded model).

- [ ] **Step 4: Verify provider error message for missing key is helpful**

```bash
GEMINI_API_KEY= uv run thoth ask --mode gemini_quick_research "test"
```

Expected: error message mentioning `GEMINI_API_KEY` env var or `--api-key-gemini`, exit code 2.

- [ ] **Step 5: Final commit (if format/lint adjustments were made)**

```bash
git status
git add -u  # only if the working tree has lint/format-related changes
git commit -m "style(gemini): final formatting pass" 2>/dev/null || echo "no changes"
```

- [ ] **Step 6: View the commit log for the P28 work**

```bash
git log --oneline origin/main..HEAD
```

Expected: ~24 commits all prefixed `feat(gemini):`, `feat(deps):`, `test(gemini):`, `docs(gemini):`, or `style(gemini):`.

P28 implementation is complete. Mark `[P28-T02]`, `[P28-T03]`, `[P28-T04]` as `[x]` in `projects/P28-gemini-background-deep-research.md`. Update PROJECTS.md trunk row glyph from `[ ]` to `[~]` (or `[x]` if all tasks are done).

---

## Acceptance criteria (mirror of P28 spec)

- [ ] `thoth ask --mode gemini_deep_research "test query"` submits and polls a Gemini Deep Research interaction end-to-end, writes the result to the project directory.
- [ ] `thoth resume <op-id>` re-attaches to a Gemini interaction after process restart.
- [ ] `thoth cancel <op-id>` calls `client.aio.interactions.cancel()` and marks the operation cancelled.
- [ ] Ctrl-C during a running Gemini operation cooperatively cancels and writes a resume hint.
- [ ] `thoth providers --models --provider gemini` lists the available Deep Research agent.
- [ ] All 9 `gemini_*` modes appear in `thoth modes` and pass the existing `tests/extended/test_model_kind_runtime.py` model-kind drift check.
- [ ] VCR cassette replay tests pass with no real API calls (or are explicitly skipped if VCR-vs-SDK incompatible — see Task 21 / Open Question #1).
- [ ] Default test suite (`uv run pytest`) green; gated `live_api` and `extended` workflows green when run manually with secrets configured.
- [ ] `_map_gemini_error` covers all 8 error classes documented in research doc §10 + standard HTTP error codes.
- [ ] Output filenames follow the existing `<timestamp>_<mode>_gemini_<slug>.md` pattern.
- [ ] All existing tests continue to pass (no regressions in OpenAI / mock / Perplexity paths).
