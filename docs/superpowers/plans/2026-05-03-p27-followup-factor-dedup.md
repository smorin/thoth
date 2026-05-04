# P27 follow-up: factor-dedup fixes + helper extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply 4 bug fixes + 2 cosmetic fixes + 5 documentation comments to the OpenAI/Perplexity provider lifecycle code, and extract two small shared helpers to prevent future drift. Implements the spec at `planning/p27-followup-factor-dedup-spec.md`.

**Architecture:** Two new module-level helpers (one for the duplicated invalid-key ThothError shape, one for provider-status-enum → Thoth-status-dict translation). Existing methods are refactored to call the helpers. Bug fixes land alongside the refactors so each method gets one coherent commit. Status-enum tables are declared as module-level constants per provider.

**Tech Stack:** Python 3.11, openai SDK (compatibility mode), httpx, tenacity, pytest.

**Repo state:** Branch `p27-perplexity-background-deep-research` in worktree `/Users/stevemorin/c/thoth-worktrees/p27-perplexity-background-deep-research`. Currently 1213 pytest tests passing; 19 commits ahead of main. Pre-commit gate via lefthook (ruff + ty + bandit + gitleaks + codespell + ./thoth_test).

---

## File structure

| Path | Action | Purpose |
|---|---|---|
| `src/thoth/providers/_status.py` | **Create** | New module with `_translate_provider_status` helper. Provider-agnostic; pure data transform. |
| `src/thoth/providers/openai.py` | Modify | Add `_OPENAI_STATUS_TABLE` constant; refactor `OpenAIProvider.check_status` to use the helper. No behavior change. |
| `src/thoth/providers/perplexity.py` | Modify | Add `_PERPLEXITY_STATUS_TABLE` constant; add `_invalid_key_thotherror` helper; refactor both error mappers to use it; refactor `_poll_async_job` to use status helper + apply B1 stale-cache + B2 error_class fixes; apply A1 + A2 + A4 fixes; add 5 intentional-divergence comments. |
| `tests/test_provider_status_helper.py` | **Create** | Unit tests for `_translate_provider_status` (table lookup, unknown fallback, mutation safety). |
| `tests/test_provider_perplexity_async.py` | Modify | Add 3 new tests (A1 quota body, A2 403 branch, B1 stale-cache on HTTPStatusError). |
| `tests/test_provider_perplexity.py` | Modify | Add 1 new test (A1 sync 402 belt). Update 1 existing test if its expectation hardcoded the bare `(model: x)` formatting (A4). |

No changes to: `src/thoth/providers/base.py`, `src/thoth/run.py`, `tests/test_oai_background.py`, `tests/test_openai_errors.py` (those tests must continue passing as regression check on Task 2).

---

## Task 1: Add `_translate_provider_status` helper + tests

**Files:**
- Create: `src/thoth/providers/_status.py`
- Test: `tests/test_provider_status_helper.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_provider_status_helper.py`:

```python
"""Tests for _translate_provider_status — the shared status-enum dispatcher.

Used by both OpenAIProvider.check_status and PerplexityProvider._poll_async_job
to translate provider-specific status literals to Thoth's internal status
dict ({status, progress, error?}). Pure data transform; no I/O, no caching.
"""

from __future__ import annotations

from typing import Any

import pytest

from thoth.providers._status import _translate_provider_status


def test_table_lookup_returns_template_copy() -> None:
    """A known status returns a COPY of the template (caller may mutate freely)."""
    table = {"COMPLETED": {"status": "completed", "progress": 1.0}}
    result = _translate_provider_status("COMPLETED", table)
    assert result == {"status": "completed", "progress": 1.0}
    # Mutating the result must NOT mutate the table entry — caller fills in
    # dynamic fields (error, runtime progress) without poisoning the table.
    result["error"] = "extra"
    assert "error" not in table["COMPLETED"]


def test_unknown_status_returns_default_permanent_error() -> None:
    """An unrecognized status falls through to permanent_error with the literal in the message."""
    table = {"COMPLETED": {"status": "completed", "progress": 1.0}}
    result = _translate_provider_status("WAT", table)
    assert result == {
        "status": "permanent_error",
        "error": "Unexpected provider status: 'WAT'",
    }


def test_empty_status_string_falls_through_to_permanent_error() -> None:
    """An empty string status (defaulted from a missing key) is treated as unknown."""
    table = {"COMPLETED": {"status": "completed", "progress": 1.0}}
    result = _translate_provider_status("", table)
    assert result["status"] == "permanent_error"
    assert "''" in result["error"]


def test_explicit_unknown_template_overrides_default() -> None:
    """Caller may supply a custom unknown_template (e.g., to embed the status differently)."""
    table = {"COMPLETED": {"status": "completed", "progress": 1.0}}
    custom = {"status": "permanent_error", "error": "got status={status}"}
    result = _translate_provider_status("WAT", table, unknown_template=custom)
    assert result == {"status": "permanent_error", "error": "got status=WAT"}


def test_table_with_partial_template_returns_partial_dict() -> None:
    """Templates may omit progress (e.g., for failed states); the helper preserves shape."""
    table: dict[str, dict[str, Any]] = {
        "FAILED": {"status": "permanent_error"},
    }
    result = _translate_provider_status("FAILED", table)
    assert result == {"status": "permanent_error"}
    # Caller fills in `error` after the lookup.
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_provider_status_helper.py -v`
Expected: 5 errors collecting (`ImportError: cannot import name '_translate_provider_status' from 'thoth.providers._status'`).

- [ ] **Step 3: Create the helper module**

Create `src/thoth/providers/_status.py`:

```python
"""Shared status-enum translation for background-lifecycle providers.

Both `OpenAIProvider.check_status` and `PerplexityProvider._poll_async_job`
translate a provider-specific status literal (e.g. `"completed"`,
`"COMPLETED"`, `"in_progress"`) into Thoth's internal status dict
(`{"status": "completed", "progress": 1.0}` etc.). The dispatch shape
is identical across providers; only the table differs.

This helper is the pure-data part of that translation. It does NOT
touch self.jobs caching, exception handling, or any provider-specific
I/O — callers wrap their own error and cache logic around it.

Per the P27 factor-dedup spec; declared in its own module rather than
appended to `base.py` so the ABC doesn't grow lifecycle-specific helpers.
"""

from __future__ import annotations

from typing import Any


def _translate_provider_status(
    provider_status: str,
    status_table: dict[str, dict[str, Any]],
    *,
    unknown_template: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Translate a provider-specific status literal to Thoth's status dict.

    `status_table` maps the provider's own status enum (e.g.,
    `"COMPLETED"`, `"in_progress"`) to a Thoth status template such as
    `{"status": "completed", "progress": 1.0}`. The helper returns a
    fresh dict copy on every call so callers may mutate the result
    (e.g., to add a runtime `progress` from response.metadata or an
    `error` field from the upstream payload) without poisoning the
    table.

    Unknown statuses fall through to `unknown_template` if supplied, or
    to a default `permanent_error` carrying the unrecognized literal.
    Custom unknown_template may use `{status}` in the `error` field as
    a substitution token.
    """
    template = status_table.get(provider_status)
    if template is not None:
        return dict(template)
    if unknown_template is not None:
        result = dict(unknown_template)
        if "error" in result and isinstance(result["error"], str):
            result["error"] = result["error"].format(status=provider_status)
        return result
    return {
        "status": "permanent_error",
        "error": f"Unexpected provider status: {provider_status!r}",
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_provider_status_helper.py -v`
Expected: 5 passed.

- [ ] **Step 5: Run lint + type check**

Run: `uv run ruff check src/thoth/providers/_status.py tests/test_provider_status_helper.py`
Expected: `All checks passed!`

Run: `uv run ty check src/thoth/providers/_status.py`
Expected: `All checks passed!`

- [ ] **Step 6: Commit**

```bash
git add src/thoth/providers/_status.py tests/test_provider_status_helper.py
git commit -m "feat(p27-followup): add _translate_provider_status helper

Pure-data dispatcher shared by OpenAIProvider.check_status and
PerplexityProvider._poll_async_job. Looks up a provider's status
literal in a per-provider table and returns a fresh Thoth status
dict copy that callers may mutate to add runtime fields (progress
from metadata, error from upstream payload).

No I/O, no caching, no exception handling — those concerns stay in
the calling methods. Custom unknown_template supports {status}
substitution for callers that want a tailored error message.

5 unit tests in tests/test_provider_status_helper.py cover the
table-hit path, the default unknown fallback, the explicit-template
unknown path, mutation safety (caller mutation must not poison the
table), and partial templates (no progress field for FAILED-shaped
states).

Per P27 factor-dedup spec; placed in providers/_status.py rather
than base.py so the ABC stays free of lifecycle helpers."
```

---

## Task 2: Refactor `OpenAIProvider.check_status` to use the helper

**Files:**
- Modify: `src/thoth/providers/openai.py:271-360` (the `check_status` method)
- Existing tests must continue passing: `tests/test_oai_background.py` (no edits needed)

- [ ] **Step 1: Verify the OpenAI background test suite passes BEFORE changes**

Run: `uv run pytest tests/test_oai_background.py -q`
Expected: All tests pass (baseline).

- [ ] **Step 2: Add the status table constant**

In `src/thoth/providers/openai.py`, after the existing `import` block at the top (around line 30, before `def _rate_limit_error_is_quota` at line 36), add:

```python
from thoth.providers._status import _translate_provider_status

# Provider-status → Thoth-status template. Used by check_status; the in_progress
# template's progress is overridden at runtime from response.metadata; failed
# and incomplete templates need an `error` field filled in by the caller.
_OPENAI_STATUS_TABLE: dict[str, dict[str, Any]] = {
    "completed": {"status": "completed", "progress": 1.0},
    "in_progress": {"status": "running", "progress": 0.5},
    "failed": {"status": "permanent_error"},
    "incomplete": {"status": "permanent_error"},
    "cancelled": {"status": "cancelled", "error": "Response was cancelled"},
    "queued": {"status": "queued", "progress": 0.0},
}
```

(Note: `Any` is already imported in this file via `from typing import Any` near the top.)

- [ ] **Step 3: Refactor the if/elif chain in check_status to use the helper**

In `src/thoth/providers/openai.py`, replace the block from line 292 (`if hasattr(response, "status"):`) through line 325 (the closing `else:` block ending with `return { ..., "error": "Response object has no status attribute"}`) with:

```python
            if not hasattr(response, "status"):
                return {
                    "status": "permanent_error",
                    "error": "Response object has no status attribute",
                }

            status_str = response.status
            translated = _translate_provider_status(status_str, _OPENAI_STATUS_TABLE)

            # Per-status post-mutation: dynamic fields the table can't carry.
            if status_str == "completed":
                # Cache the completed response so stale-cache fallback below
                # and get_result() can rely on it.
                self.jobs[job_id]["response"] = response
            elif status_str == "in_progress":
                # Pull live progress from response.metadata if available; the
                # table default is 0.5.
                if hasattr(response, "metadata") and response.metadata:
                    translated["progress"] = response.metadata.get("progress", 0.5)
            elif status_str == "failed":
                error_msg = getattr(response, "error", "Unknown error")
                translated["error"] = str(error_msg)
            elif status_str == "incomplete":
                error_msg = (
                    getattr(response, "error", None)
                    or "Response was incomplete (output truncated)"
                )
                translated["error"] = str(error_msg)
            # "cancelled" and "queued" need no post-mutation; the table covers them.
            # Unknown statuses are handled by _translate_provider_status's default
            # unknown branch (permanent_error with the unrecognized literal).
            return translated
```

- [ ] **Step 4: Run the OpenAI background tests to verify zero regressions**

Run: `uv run pytest tests/test_oai_background.py -q`
Expected: same number of passes as Step 1.

- [ ] **Step 5: Run the full pytest suite for additional safety**

Run: `uv run pytest -q`
Expected: 1218+ passed (1213 baseline + 5 new helper tests from Task 1).

- [ ] **Step 6: Run lint + type check**

Run: `uv run ruff check src/thoth/providers/openai.py`
Expected: `All checks passed!`

Run: `uv run ty check src/thoth/providers/openai.py`
Expected: `All checks passed!` (or pre-existing ty diagnostic count from baseline; my changes must not increase it).

- [ ] **Step 7: Commit**

```bash
git add src/thoth/providers/openai.py
git commit -m "refactor(p27-followup): OpenAIProvider.check_status uses shared status helper

Collapses the 7-branch if/elif chain on response.status into a single
_translate_provider_status() call against the new _OPENAI_STATUS_TABLE
module-level constant. Dynamic per-status post-mutation (cache update
on completed, metadata-driven progress on in_progress, error field on
failed/incomplete) stays in the method.

No behavior change — the test suite (test_oai_background.py) covers
every status branch and continues to pass."
```

---

## Task 3: Refactor `_poll_async_job` + apply B1 stale-cache + B2 error_class fixes

**Files:**
- Modify: `src/thoth/providers/perplexity.py:644-699` (the `_poll_async_job` method)
- Test: `tests/test_provider_perplexity_async.py` (add 1 new test for B1)

- [ ] **Step 1: Add the failing test for B1 (stale-cache on HTTPStatusError)**

In `tests/test_provider_perplexity_async.py`, append after the existing `test_check_status_transient_error_with_stale_completed_cache_returns_completed` function (search for `test_check_status_transient_error_with_stale` to find it):

```python
def test_check_status_http_5xx_with_stale_completed_cache_returns_completed() -> None:
    """B1 (TS02): HTTPStatusError 5xx + cached COMPLETED → completed (stale-cache fallback).

    Mirrors test_check_status_transient_error_with_stale_completed_cache_returns_completed
    but for the HTTPStatusError branch — a 5xx blip after a previously-cached
    COMPLETED state must not regress the runner's polling loop. Per OAI-BG-07
    parity (OpenAI fires the stale-cache fallback in its transient-SDK-error
    branch; Perplexity must do the same in its HTTPStatusError 5xx branch).
    """
    provider, _ = _make_background_provider()
    _seed_background_job(provider, cached_status="COMPLETED")
    request = httpx.Request("GET", "https://api.perplexity.ai/v1/async/sonar/req-async-123")
    response = httpx.Response(status_code=503, content=b"{}", request=request)
    err = httpx.HTTPStatusError("503", request=request, response=response)
    _attach_get_response(provider, err)
    result = asyncio.run(provider.check_status("req-async-123"))
    assert result["status"] == "completed"
    assert result["progress"] == 1.0
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_provider_perplexity_async.py::test_check_status_http_5xx_with_stale_completed_cache_returns_completed -v`
Expected: FAIL with `assert 'transient_error' == 'completed'`.

- [ ] **Step 3: Add the status table constant**

In `src/thoth/providers/perplexity.py`, near the other module-level constants (after `_INVALID_KEY_PHRASES` at line 103, before `def _rate_limit_error_is_quota` at line 106), add:

```python
from thoth.providers._status import _translate_provider_status

# Provider-status → Thoth-status template for the async API. Caller fills in
# `error` for the FAILED branch from payload["error_message"]. Unknown
# statuses fall through to the helper's default permanent_error.
_PERPLEXITY_STATUS_TABLE: dict[str, dict[str, Any]] = {
    "CREATED": {"status": "queued", "progress": 0.0},
    "IN_PROGRESS": {"status": "running", "progress": 0.5},
    "COMPLETED": {"status": "completed", "progress": 1.0},
    "FAILED": {"status": "permanent_error"},
}
```

- [ ] **Step 4: Refactor `_poll_async_job` with B1 + B2 fixes**

Replace the entire `_poll_async_job` method (lines 644–699) with:

```python
    async def _poll_async_job(self, job_id: str, job_info: dict[str, Any]) -> dict[str, Any]:
        """Single poll attempt against /v1/async/sonar/{job_id} with translation.

        Stale-cache fallback fires on transient errors AND on HTTPStatusError 5xx
        (per OAI-BG-07 parity, P27 factor-dedup B1): a network or server blip
        immediately after a previously-cached COMPLETED state must not regress
        the runner's polling loop back to transient_error.
        """
        try:
            response = await self._async_http.get(f"/v1/async/sonar/{job_id}")
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return {
                    "status": "permanent_error",
                    "error": "Job expired (7-day TTL) or not found server-side",
                }
            # B1: stale-cache fallback on 5xx — a previously-cached COMPLETED
            # is authoritative even when a later poll hits a server blip.
            cached = job_info.get("response_data") or {}
            if cached.get("status") == "COMPLETED":
                return {"status": "completed", "progress": 1.0}
            return {
                "status": "transient_error",
                "error": f"HTTP {exc.response.status_code}",
                # B2: derive class name from type(exc) instead of hardcoding
                # the literal string, matching the convention used by the
                # other except branches and OpenAIProvider.check_status.
                "error_class": type(exc).__name__,
            }
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            cached = job_info.get("response_data") or {}
            if cached.get("status") == "COMPLETED":
                return {"status": "completed", "progress": 1.0}
            return {
                "status": "transient_error",
                "error": str(exc),
                "error_class": type(exc).__name__,
            }
        except Exception as exc:  # noqa: BLE001 - never silently swallow novel errors
            # Intentional: named exception branches use bare str(exc); the
            # catch-all prepends `({type(exc).__name__})` so users can
            # distinguish a known exception class from an unexpected one in
            # error logs. (P27 factor-dedup B3 — kept as intentional divergence.)
            cached = job_info.get("response_data") or {}
            if cached.get("status") == "COMPLETED":
                return {"status": "completed", "progress": 1.0}
            return {
                "status": "transient_error",
                "error": f"Unexpected error ({type(exc).__name__}): {exc}",
                "error_class": type(exc).__name__,
            }

        payload = response.json()
        status_str = payload.get("status", "")
        # Always cache the latest payload so get_result() and the stale-cache
        # fallback have an authoritative reference.
        job_info["response_data"] = payload

        translated = _translate_provider_status(status_str, _PERPLEXITY_STATUS_TABLE)
        if status_str == "FAILED":
            translated["error"] = payload.get("error_message") or "Perplexity job FAILED"
        return translated
```

- [ ] **Step 5: Run the new test to verify it passes**

Run: `uv run pytest tests/test_provider_perplexity_async.py::test_check_status_http_5xx_with_stale_completed_cache_returns_completed -v`
Expected: PASS.

- [ ] **Step 6: Run the full TS02 (check_status) test slice to verify zero regressions**

Run: `uv run pytest tests/test_provider_perplexity_async.py -k "check_status" -v`
Expected: All TS02 tests pass (existing 9 + 1 new = 10).

- [ ] **Step 7: Run the full pytest suite**

Run: `uv run pytest -q`
Expected: 1219+ passed (1218 from end of Task 2 + 1 new B1 test).

- [ ] **Step 8: Run lint + type check**

Run: `uv run ruff check src/thoth/providers/perplexity.py tests/test_provider_perplexity_async.py`
Expected: `All checks passed!`

Run: `uv run ty check src/thoth/providers/perplexity.py`
Expected: same diagnostic count as baseline.

- [ ] **Step 9: Commit**

```bash
git add src/thoth/providers/perplexity.py tests/test_provider_perplexity_async.py
git commit -m "fix(p27-followup): _poll_async_job stale-cache fallback on 5xx + error_class

Three changes in this slice:

B1: stale-cache fallback now fires in the HTTPStatusError branch when
the upstream returns 5xx and the cached status is COMPLETED, matching
the pattern OpenAIProvider.check_status uses for its transient-SDK-error
branch (per OAI-BG-07 parity). A 5xx blip after completion must not
regress the runner's polling loop.

B2: replaces the literal 'HTTPStatusError' error_class string with
type(exc).__name__, matching the convention used everywhere else in
this method and in OpenAIProvider.check_status.

Refactor: collapses the 5-branch if/elif chain on payload['status']
into a single _translate_provider_status() call against the new
_PERPLEXITY_STATUS_TABLE module-level constant. The FAILED branch
post-mutates the translated dict to fill in `error` from
payload['error_message']; everything else is table-only.

New test test_check_status_http_5xx_with_stale_completed_cache_returns_completed
proves the B1 fix; existing 9 TS02 tests + the rest of the suite
continue to pass."
```

---

## Task 4: Add `_invalid_key_thotherror` helper + refactor both 401 branches

**Files:**
- Modify: `src/thoth/providers/perplexity.py` (add helper near line 130; refactor `_map_perplexity_error` line 142–151 and `_map_perplexity_error_async` line 248–255)
- Existing tests must continue passing: `tests/test_provider_perplexity_async.py::test_async_map_401_with_invalid_key_body_returns_friendly_thoth_error` and `tests/test_provider_perplexity.py` (no edits needed; helper is internal).

- [ ] **Step 1: Verify the existing invalid-key tests pass**

Run: `uv run pytest tests/test_provider_perplexity_async.py::test_async_map_401_with_invalid_key_body_returns_friendly_thoth_error tests/test_provider_perplexity.py -k "invalid" -v`
Expected: PASS for the 401-with-invalid-key-body test (the only one specifically for this shape).

- [ ] **Step 2: Add the helper**

In `src/thoth/providers/perplexity.py`, between `_rate_limit_error_is_quota` (ends ~line 129) and `_map_perplexity_error` (starts ~line 132), add:

```python
def _invalid_key_thotherror(provider: str, settings_url: str) -> ThothError:
    """Friendly ThothError for an upstream-rejected API key.

    Distinct from APIKeyError (which signals 'no key found'); this one
    signals 'a key was supplied but the upstream rejected it'. Different
    user actions (rotate vs. set), different exit_code semantics.

    Currently called by both `_map_perplexity_error` (sync) and
    `_map_perplexity_error_async` to keep the wording byte-identical
    across the two error-mapping paths. If a third caller emerges
    (e.g., Gemini in P28), promote this helper to `thoth/errors.py`.
    """
    return ThothError(
        f"{provider} API key is invalid",
        f"Your {provider.title()} API key was rejected by the API. "
        f"Check your key at {settings_url}",
        exit_code=2,
    )
```

- [ ] **Step 3: Refactor `_map_perplexity_error` 401 branch to call the helper**

In `src/thoth/providers/perplexity.py`, replace lines 145–151 (the `if any(phrase ...)` block inside the AuthenticationError branch) with:

```python
        if any(phrase in combined for phrase in _INVALID_KEY_PHRASES):
            return _invalid_key_thotherror(
                _PROVIDER_NAME, "https://www.perplexity.ai/settings/api"
            )
```

- [ ] **Step 4: Refactor `_map_perplexity_error_async` 401-invalid branch to call the helper**

In `src/thoth/providers/perplexity.py`, replace lines 249–255 (the `if any(phrase ...)` block inside the `if status == 401:` branch) with:

```python
            if any(phrase in body_lower for phrase in _INVALID_KEY_PHRASES):
                return _invalid_key_thotherror(
                    _PROVIDER_NAME, "https://www.perplexity.ai/settings/api"
                )
```

- [ ] **Step 5: Run the affected tests to verify zero regressions**

Run: `uv run pytest tests/test_provider_perplexity_async.py::test_async_map_401_with_invalid_key_body_returns_friendly_thoth_error tests/test_provider_perplexity.py -q`
Expected: same number of passes as Step 1.

- [ ] **Step 6: Run the full pytest suite**

Run: `uv run pytest -q`
Expected: same total count as end of Task 3 (no new tests in this task; helper is purely an extraction).

- [ ] **Step 7: Run lint + type check**

Run: `uv run ruff check src/thoth/providers/perplexity.py`
Expected: `All checks passed!`

Run: `uv run ty check src/thoth/providers/perplexity.py`
Expected: same diagnostic count as baseline.

- [ ] **Step 8: Commit**

```bash
git add src/thoth/providers/perplexity.py
git commit -m "refactor(p27-followup): extract _invalid_key_thotherror helper

The byte-identical ThothError shape ('perplexity API key is invalid' +
'Check your key at https://www.perplexity.ai/settings/api', exit_code=2)
appeared in both _map_perplexity_error (sync, line 146-151) and
_map_perplexity_error_async (line 250-255). Extracted into a single
helper at module level so future remediation copy changes propagate to
both call sites.

Helper takes the provider name and settings URL as parameters so it
can be promoted to thoth/errors.py when a third caller emerges
(Gemini in P28); for now keeping it perplexity-local per the spec.

No behavior change. Existing tests pass unchanged."
```

---

## Task 5: Apply A1 (both directions) + A2 + A4 fixes with new tests

**Files:**
- Modify: `src/thoth/providers/perplexity.py` (the `_map_perplexity_error_async` body and `_map_perplexity_error` body)
- Test: `tests/test_provider_perplexity_async.py` (add 2 new tests for A1 async + A2)
- Test: `tests/test_provider_perplexity.py` (add 1 new test for A1 sync 402 belt; possibly update 1 existing test for A4 if it pinned the bare formatting)

- [ ] **Step 1: Add the failing test for A1 async (429-with-quota-body upgrades to APIQuotaError)**

In `tests/test_provider_perplexity_async.py`, append after `test_async_map_429_returns_rate_limit_error` (search the file for that name):

```python
def test_async_map_429_with_quota_body_upgrades_to_api_quota_error() -> None:
    """A1 (factor-dedup): 429 + quota markers in body → APIQuotaError, not rate-limit.

    Sync uses _rate_limit_error_is_quota body inspection to upgrade
    RateLimitError → APIQuotaError. Async should do the same when 429 carries
    quota markers in the body — otherwise the two mappers classify the same
    upstream error differently. Markers come from the same vocabulary
    (insufficient_quota, billing, credit, exhausted, no credits, etc.).
    """
    exc = _make_http_status_error(
        429,
        body='{"error": {"code": "insufficient_quota", "message": "Monthly spend limit exceeded"}}',
    )
    result = _map_perplexity_error_async(exc)
    assert isinstance(result, APIQuotaError), (
        f"expected APIQuotaError on 429-with-quota-body, got {type(result).__name__}"
    )
```

- [ ] **Step 2: Add the failing test for A2 (async 403 → ProviderError with permission hint)**

In `tests/test_provider_perplexity_async.py`, append after `test_async_map_429_with_quota_body_upgrades_to_api_quota_error`:

```python
def test_async_map_403_returns_permission_denied_provider_error() -> None:
    """A2 (factor-dedup): HTTP 403 → ProviderError with tier/model-access hint.

    Both sync mappers emit 'Permission denied (check tier / model access).' for
    PermissionDeniedError; async previously fell into the generic HTTP-{status}
    bucket with no hint. This test pins parity.
    """
    exc = _make_http_status_error(403, body='{"error": {"message": "forbidden"}}')
    result = _map_perplexity_error_async(exc)
    assert isinstance(result, ProviderError)
    msg = str(result).lower()
    assert "permission denied" in msg
    assert "tier" in msg or "model access" in msg
```

- [ ] **Step 3: Add the failing test for A1 sync (402 belt-and-suspenders via APIStatusError)**

In `tests/test_provider_perplexity.py`, after the existing `# TS06` block (or near the end of the file), append:

```python
def test_perplexity_sync_maps_402_status_code_to_api_quota_error() -> None:
    """A1 (factor-dedup) sync belt: any APIStatusError carrying status_code=402
    routes to APIQuotaError, regardless of which openai SDK subclass it is.

    Perplexity uses 402 for credit exhaustion. The openai SDK doesn't have a
    PaymentRequired exception subclass — a 402 may surface as a bare
    APIStatusError or one of its subclasses (BadRequestError etc., depending
    on SDK version). The mapper checks `getattr(exc, 'status_code', None) == 402`
    so any APIStatusError-shaped exception with that status code is upgraded
    to APIQuotaError before the generic APIError catch-all.
    """
    import httpx
    import openai

    from thoth.errors import APIQuotaError
    from thoth.providers.perplexity import _map_perplexity_error

    request = httpx.Request("POST", "https://api.perplexity.ai/chat/completions")
    response = httpx.Response(status_code=402, request=request)
    exc = openai.BadRequestError(message="402 from upstream", response=response, body=None)
    result = _map_perplexity_error(exc)
    assert isinstance(result, APIQuotaError), (
        f"expected APIQuotaError for status_code=402, got {type(result).__name__}: {result!r}"
    )
```

- [ ] **Step 4: Run all three new tests to verify they fail**

Run: `uv run pytest tests/test_provider_perplexity_async.py::test_async_map_429_with_quota_body_upgrades_to_api_quota_error tests/test_provider_perplexity_async.py::test_async_map_403_returns_permission_denied_provider_error tests/test_provider_perplexity.py::test_perplexity_sync_maps_402_status_code_to_api_quota_error -v`
Expected: 3 FAILED.

- [ ] **Step 5: Apply the A1 sync 402 belt fix**

In `src/thoth/providers/perplexity.py`, in `_map_perplexity_error`, add a new check immediately BEFORE the existing `if isinstance(exc, openai.APIError):` line (around line 195). Insert:

```python
    # A1 belt-and-suspenders: any APIStatusError with status_code == 402
    # routes to APIQuotaError. The openai SDK doesn't ship a PaymentRequired
    # exception subclass, so a 402 from Perplexity (their credit-exhaustion
    # code per docs §8) may surface here as a bare APIStatusError or one of
    # its subclasses. Checked AFTER the named openai branches so that
    # well-known classes still take their specific paths.
    if getattr(exc, "status_code", None) == 402:
        return APIQuotaError(_PROVIDER_NAME)

```

(Insert before line 195, the existing `if isinstance(exc, openai.APIError):` line. The blank line at the end is intentional to match surrounding spacing.)

- [ ] **Step 6: Apply the A1 async 429-with-quota-body fix**

In `src/thoth/providers/perplexity.py`, locate the `if status == 429:` line in `_map_perplexity_error_async` (around line 266). Replace:

```python
        if status == 429:
            return APIRateLimitError(_PROVIDER_NAME)
```

with:

```python
        if status == 429:
            # A1: upgrade to APIQuotaError when the body carries quota
            # markers (parity with _rate_limit_error_is_quota in the sync
            # path). Without this, Perplexity returning 429 + insufficient_quota
            # would be classified as a rate limit while the sync mapper would
            # call it a quota error — same upstream, different taxonomy.
            quota_markers = (
                "insufficient_quota",
                "quota",
                "billing",
                "credit",
                "credits",
                "monthly spend",
                "exhausted",
                "no credits",
                "blocked",
            )
            if any(marker in body_lower for marker in quota_markers):
                return APIQuotaError(_PROVIDER_NAME)
            return APIRateLimitError(_PROVIDER_NAME)
```

- [ ] **Step 7: Apply the A2 async 403 fix**

In `src/thoth/providers/perplexity.py`, in `_map_perplexity_error_async`, add a new branch immediately AFTER `if status == 402:` block (around line 258, before `if status == 422:` at line 259). Insert:

```python
        if status == 403:
            # A2: parity with _map_perplexity_error's PermissionDeniedError
            # handler — emit the same hint so users see the tier/model-access
            # diagnostic on both sync and async paths.
            return ProviderError(
                _PROVIDER_NAME,
                "Permission denied (check tier / model access).",
                raw_error=raw,
            )
```

- [ ] **Step 8: Apply the A4 model-hint formatting fix (sync side)**

In `src/thoth/providers/perplexity.py`, in `_map_perplexity_error`'s `BadRequestError` branch (around line 167), replace:

```python
        hint = f" (model: {model})" if model else ""
```

with:

```python
        # A4: use {model!r} for parity with _map_perplexity_error_async — repr
        # quoting is more correct for free-form upstream model strings.
        hint = f" (model: {model!r})" if model else ""
```

- [ ] **Step 9: Run the three new tests to verify they pass**

Run: `uv run pytest tests/test_provider_perplexity_async.py::test_async_map_429_with_quota_body_upgrades_to_api_quota_error tests/test_provider_perplexity_async.py::test_async_map_403_returns_permission_denied_provider_error tests/test_provider_perplexity.py::test_perplexity_sync_maps_402_status_code_to_api_quota_error -v`
Expected: 3 PASSED.

- [ ] **Step 10: Check for regressions on the existing 422 / model-hint tests**

Run: `uv run pytest tests/test_provider_perplexity_async.py::test_async_map_422_returns_provider_error_with_model_hint tests/test_provider_perplexity.py -k "request_uses_configured_model or bad_request" -v`
Expected: PASS. If the 422 test asserts `"sonar-pro"` is in the message string, it still matches because `repr("sonar-pro")` is `"'sonar-pro'"` (contains the substring `sonar-pro`). If the 422 test pinned the EXACT formatting `(model: sonar-pro)` without quotes, update it to match the new repr-quoted form.

- [ ] **Step 11: Run the full pytest suite**

Run: `uv run pytest -q`
Expected: 1222+ passed (1219 from end of Task 3 + 3 new tests).

- [ ] **Step 12: Run lint + type check**

Run: `uv run ruff check src/thoth/providers/perplexity.py tests/test_provider_perplexity.py tests/test_provider_perplexity_async.py`
Expected: `All checks passed!`

Run: `uv run ty check src/thoth/providers/perplexity.py`
Expected: same diagnostic count as baseline.

- [ ] **Step 13: Commit**

```bash
git add src/thoth/providers/perplexity.py tests/test_provider_perplexity.py tests/test_provider_perplexity_async.py
git commit -m "fix(p27-followup): A1 quota-vs-rate-limit symmetry + A2 403 + A4 model hint

Three accidental-divergence fixes between _map_perplexity_error (sync,
openai SDK) and _map_perplexity_error_async (async, raw httpx) plus a
cosmetic alignment, all surfaced by the P27 factor-dedup walk.

A1 — quota detection symmetry (both directions):
  Async: 429 with quota markers in body now upgrades to APIQuotaError,
    matching _rate_limit_error_is_quota's body-inspection in sync.
    Markers: insufficient_quota, quota, billing, credit, credits,
    monthly spend, exhausted, no credits, blocked.
  Sync belt-and-suspenders: any APIStatusError with status_code == 402
    routes to APIQuotaError before the generic APIError catch-all. The
    openai SDK doesn't ship a PaymentRequired subclass; this guards
    against a 402 surfacing as a bare APIStatusError.

A2 — async lacks 403 PermissionDenied branch:
  Adds explicit status == 403 handler emitting the same
  'Permission denied (check tier / model access).' message both sync
  mappers use; previously a 403 fell into the generic HTTP-{status}
  bucket with no hint.

A4 — model hint formatting drift:
  Unifies sync's '(model: sonar-pro)' bare to the async-style
  '(model: \\'sonar-pro\\')' (repr-quoted) — more correct for
  free-form upstream model strings.

Three new tests pin the fixes:
  - test_async_map_429_with_quota_body_upgrades_to_api_quota_error
  - test_async_map_403_returns_permission_denied_provider_error
  - test_perplexity_sync_maps_402_status_code_to_api_quota_error"
```

---

## Task 6: Add documentation comments for A3, A5, A6, B3, B4

**Files:**
- Modify: `src/thoth/providers/perplexity.py` (4 comment additions: A3, A5, A6 lives in openai.py, B3 already added in Task 3, B4 needs adding)
- Modify: `src/thoth/providers/openai.py` (1 comment addition: A6)

Note: B3 was already added during Task 3's refactor. Listing it here for completeness; no edit required if Task 3 was committed correctly.

- [ ] **Step 1: Add A3 comment in `_map_perplexity_error_async`**

In `src/thoth/providers/perplexity.py`, in `_map_perplexity_error_async`, locate the final `return ProviderError(...)` for the unknown-status fallthrough inside the HTTPStatusError branch (currently around line 274 after Task 5's edits). Add a comment immediately before it:

```python
        # A3 (P27 factor-dedup): no explicit 400 BadRequest branch — Perplexity's
        # async API documents 422 (not 400) for invalid requests, so a 400 falls
        # through to the generic HTTP-{status} bucket on purpose. Keeping it
        # explicit so future maintainers don't add a redundant 400 branch.
        return ProviderError(
            _PROVIDER_NAME,
            f"HTTP {status} from Perplexity async API: {body_text[:200]}",
            raw_error=raw,
        )
```

- [ ] **Step 2: Add A5 comment above the 401 branch in `_map_perplexity_error_async`**

In `src/thoth/providers/perplexity.py`, in `_map_perplexity_error_async`, immediately above `if status == 401:` (around line 248), add:

```python
        # A5 (P27 factor-dedup): async inspects exc.response.text only; the
        # sync mapper inspects exc.body + str(exc) because openai SDK exceptions
        # carry different surfaces. Both inspections are correct for their
        # respective contexts; do not try to unify the two.
        if status == 401:
```

- [ ] **Step 3: Add A6 comment in `_map_openai_error`**

In `src/thoth/providers/openai.py`, locate the final `return ProviderError("openai", str(exc), raw_error=raw)` after the `if isinstance(exc, openai.APIError):` branch (around line 121, the very last return in the function). Add a comment immediately before it:

```python
    # A6 (P27 factor-dedup): intentional defense-in-depth. APIError is the
    # SDK base class so this fallthrough is unreachable in practice; kept to
    # guard against non-SDK exceptions sneaking through future refactors.
    return ProviderError("openai", str(exc), raw_error=raw)
```

- [ ] **Step 4: Add B4 comment in `PerplexityProvider.check_status` dispatcher**

In `src/thoth/providers/perplexity.py`, in `check_status` (around line 639), the existing dispatcher already has the `if not job_info.get("background", False):` check. Add a comment above it:

```python
        # B4 (P27 factor-dedup): P18 non-background shortcut — kept symmetric
        # with OpenAIProvider for defense-in-depth. TODO(P19): remove both
        # shortcuts when the immediate-kind path no longer transits
        # check_status at all.
        if not job_info.get("background", False):
            # P23 immediate path — submit() already returned the full response.
            return {"status": "completed", "progress": 1.0}
```

- [ ] **Step 5: Verify B3 comment is present (added in Task 3)**

Run: `grep -n "B3 (P27 factor-dedup\|catch-all prepends" src/thoth/providers/perplexity.py`
Expected: at least one match showing the comment is present in the catch-all `Exception` branch of `_poll_async_job`. If missing (Task 3 was edited differently), add this comment above the relevant branch:

```python
        except Exception as exc:  # noqa: BLE001 - never silently swallow novel errors
            # B3 (P27 factor-dedup): named exception branches use bare str(exc);
            # this catch-all prepends `({type(exc).__name__})` so users can
            # distinguish a known exception class from an unexpected one in
            # error logs. Intentional divergence; keep.
```

- [ ] **Step 6: Run the full pytest suite to verify no regressions**

Run: `uv run pytest -q`
Expected: same total count as end of Task 5 (no new tests; comment-only change).

- [ ] **Step 7: Run lint + type check**

Run: `uv run ruff check src/thoth/providers/perplexity.py src/thoth/providers/openai.py`
Expected: `All checks passed!`

Run: `uv run ty check src/thoth/providers/perplexity.py src/thoth/providers/openai.py`
Expected: same diagnostic count as baseline.

- [ ] **Step 8: Commit**

```bash
git add src/thoth/providers/perplexity.py src/thoth/providers/openai.py
git commit -m "docs(p27-followup): document 5 intentional divergences from factor-dedup walk

Comments-only edits marking five intentional divergences identified by
the P27 factor-dedup comparator pass. Each comment names the finding
(A3/A5/A6/B3/B4) and the reason the divergence is intentional, so
future factor-dedup runs and human maintainers don't try to consolidate.

A3 — async lacks 400 BadRequest branch: Perplexity's async API
documents 422 (not 400) for invalid requests; a 400 falls through to
the generic HTTP-{status} bucket on purpose.

A5 — invalid-key body inspection surface differs (sync inspects
exc.body + str(exc); async inspects exc.response.text). Both correct
for their respective SDK contexts.

A6 — _map_openai_error has an unreachable fallthrough after the
APIError catch-all. Defense-in-depth against non-SDK exceptions.

B3 — _poll_async_job's catch-all wraps with type(exc).__name__ prefix;
named exception branches use bare str(exc). Intentional disambiguation.

B4 — both providers carry a P18 non-background shortcut as
defense-in-depth; symmetric and slated for removal at P19. TODO marker
already exists on the OpenAI side; mirroring on Perplexity for parity."
```

---

## Task 7: Run the full pre-commit gate as a final regression check

**Files:** none modified.

- [ ] **Step 1: Run ruff check (lint)**

Run: `uv run ruff check src/ tests/`
Expected: `All checks passed!`

- [ ] **Step 2: Run ruff format check**

Run: `uv run ruff format --check src/ tests/`
Expected: `158+ files already formatted`.

- [ ] **Step 3: Run ty check on src/**

Run: `uv run ty check src/`
Expected: `All checks passed!` (or same diagnostic count as the pre-Task-1 baseline).

- [ ] **Step 4: Run the full pytest suite**

Run: `uv run pytest -q`
Expected: 1222+ passed (1213 baseline + 5 helper tests + 1 B1 test + 3 A1/A2 tests = 1222), 0 failed, 29 deselected.

- [ ] **Step 5: Run thoth_test integration suite**

Run: `./thoth_test -r --skip-interactive -q`
Expected: 75+ passed, 0 failed, 12 skipped (skipped = no API keys / extended tests; expected).

- [ ] **Step 6: Confirm the git log on the branch**

Run: `git log --oneline main..HEAD | head -10`
Expected to see (in reverse order): the 6 task-by-task commits from this plan plus the 20 prior P27 commits.

- [ ] **Step 7: Final summary commit (optional — only if there's something to capture)**

If the gate passes cleanly with no last-minute fixes, no extra commit is needed — the per-task commits from Tasks 1-6 stand on their own. If a small fix was needed (e.g., a stray ty diagnostic from a missed annotation), commit it with:

```bash
git add <fix-files>
git commit -m "chore(p27-followup): clean up <specific issue> after factor-dedup fixes"
```

- [ ] **Step 8: Report the final state**

Print to console (or include in PR description):

```
P27 factor-dedup follow-up complete.
- 6 task commits on top of the prior 20 P27 commits.
- 9 new tests (5 status helper + 1 B1 + 3 A1/A2).
- 2 helpers extracted (_translate_provider_status, _invalid_key_thotherror).
- 4 bug fixes (A1 both-directions, A2, B1, plus cosmetic A4+B2).
- 5 intentional divergences documented (A3, A5, A6, B3, B4).
- Full gate: ruff + ty + pytest + thoth_test all green.
```

---

## Notes on order and parallelism

- Tasks 1, 2, 3, 4 must be done in order (Task 2 depends on Task 1's helper; Task 3 depends on Task 1's helper and locks in B3 comment; Task 4 is independent of Task 3 in principle but the spec sequencing keeps it after to minimize file conflicts).
- Tasks 5, 6 can run in either order after Tasks 1–4. Recommend Task 5 before Task 6 because Task 6 references line numbers that may shift after Task 5's edits.
- Task 7 runs last. No code changes; verification only.
- Each task is a single commit. Splitting further is not necessary — each commit is small enough to review individually.

## Spec coverage check

Each spec section maps to a task as follows:

| Spec section | Task |
|---|---|
| Helper 1: `_invalid_key_thotherror` | Task 4 |
| Helper 2: `_translate_provider_status` | Task 1 |
| Migration: openai.py status mapper | Task 2 |
| Migration: perplexity.py status mapper | Task 3 |
| Migration: perplexity.py invalid-key 401 (sync + async) | Task 4 |
| A1 (both directions) | Task 5 |
| A2 (async 403) | Task 5 |
| A4 (model hint repr-quoted) | Task 5 |
| B1 (stale-cache on 5xx) | Task 3 |
| B2 (error_class derivation) | Task 3 |
| A3, A5 (perplexity.py comments) | Task 6 |
| A6 (openai.py comment) | Task 6 |
| B3 (catch-all comment — already added in Task 3) | Task 3 (verify in Task 6) |
| B4 (P18 shortcut comment) | Task 6 |
| Risks: openai.APIError lacking status_code | Already verified during plan-writing; Task 5 uses `getattr(exc, 'status_code', None) == 402` which handles the missing-attr case. |
| Risks: B1 behavior change under 5xx-after-completed | Captured in the Task 3 commit message; informational. |
| Out of scope: richer Polling-Provider mixin / promoting helper / unifying string literals | Deferred per spec; not in this plan. |

All spec items covered.

---

**Plan complete and saved to `docs/superpowers/plans/2026-05-03-p27-followup-factor-dedup.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. Pairs well with this plan's small task count (7) and tight per-task scope.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
