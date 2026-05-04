# Consolidation: provider error mappers + status mappers (P27 follow-up)

**Goal:** Apply the bug-shaped and cosmetic fixes surfaced by the
factor-dedup walk over P27's provider lifecycle code, and extract two
small shared helpers that prevent future drift. Net effect: closer
behavioral parity between OpenAI and Perplexity background lifecycles
without forcing a unified abstraction over genuinely different input
shapes.

This spec is ready to hand to `superpowers:writing-plans` for an
executable plan.

---

## Implementations consolidated / patched

| File | Implementation | Change |
|---|---|---|
| `src/thoth/providers/openai.py` | `_map_openai_error` | Patched — A6 documented as intentional |
| `src/thoth/providers/perplexity.py` | `_map_perplexity_error` (sync) | Patched — A1 belt-and-suspenders, calls new shared helper |
| `src/thoth/providers/perplexity.py` | `_map_perplexity_error_async` | Patched — A1 + A2 + A4 fixes, calls new shared helper |
| `src/thoth/providers/openai.py` | `OpenAIProvider.check_status` | Refactored to call new shared status-table helper |
| `src/thoth/providers/perplexity.py` | `_poll_async_job` | Patched — B1 stale-cache fallback + B2 error_class, refactored to call shared helper |

Two new module-level helpers:
- `_invalid_key_thotherror(provider, settings_url)` (in `perplexity.py` initially; could promote to `errors.py` if a third caller emerges)
- `_translate_provider_status(provider_status, status_table)` (new module — likely `src/thoth/providers/_status.py` or appended to `base.py`)

---

## Unified design

### Helper 1 — `_invalid_key_thotherror(provider, settings_url)`

```python
def _invalid_key_thotherror(provider: str, settings_url: str) -> ThothError:
    """Friendly ThothError for an upstream-rejected API key.

    Distinct from APIKeyError (which signals 'no key found'); this one
    signals 'a key was supplied but the upstream rejected it'. Different
    user actions (rotate vs. set), different exit_code semantics.
    """
    return ThothError(
        f"{provider} API key is invalid",
        f"Your {provider.title()} API key was rejected by the API. "
        f"Check your key at {settings_url}",
        exit_code=2,
    )
```

**Edge-case strategy:** the helper takes the provider name and the
settings-page URL as parameters. The "API key is invalid" / "Check your
key at <url>" wording is the canonical shape; both Perplexity mappers
call the same helper.

**Migration:**
- `_map_perplexity_error` line 145–151: replace inline `ThothError(...)`
  construction with `_invalid_key_thotherror("perplexity", "https://www.perplexity.ai/settings/api")`.
- `_map_perplexity_error_async` 401-with-invalid-body branch: same
  replacement.
- OpenAI's `_map_openai_error` 401-incorrect-key branch is similar in
  spirit but uses different wording (`"Invalid OpenAI API key"`) — leave
  as-is for now; promoting it would be a behavior change in error text.
  Document with a `# intentional: OpenAI uses distinct wording for parity
  with platform.openai.com support docs` comment.

### Helper 2 — `_translate_provider_status(provider_status, status_table)`

```python
def _translate_provider_status(
    provider_status: str,
    status_table: dict[str, dict[str, Any]],
    *,
    unknown_template: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Translate a provider-specific status literal to Thoth's status dict.

    `status_table` maps the provider's own status enum (e.g.,
    'COMPLETED', 'in_progress') to a Thoth status template
    ({"status": "completed", "progress": 1.0}). Unknown statuses fall
    through to `unknown_template`, defaulting to a permanent_error with
    the unrecognized literal in the message.

    The helper does NOT touch self.jobs caching, exception handling, or
    any provider-specific I/O. Callers wrap their own error/cache logic
    around it.
    """
    template = status_table.get(provider_status)
    if template is not None:
        return dict(template)  # caller may mutate
    if unknown_template is not None:
        return dict(unknown_template) | {
            "error": unknown_template.get("error", "").format(status=provider_status)
            if "error" in unknown_template
            else f"Unexpected provider status: {provider_status!r}",
        }
    return {
        "status": "permanent_error",
        "error": f"Unexpected provider status: {provider_status!r}",
    }
```

**Status tables (per provider, declared at module level):**

```python
# openai.py
_OPENAI_STATUS_TABLE: dict[str, dict[str, Any]] = {
    "completed":   {"status": "completed", "progress": 1.0},
    "in_progress": {"status": "running",   "progress": 0.5},  # caller overrides progress from response.metadata
    "failed":      {"status": "permanent_error"},  # caller fills in `error`
    "incomplete":  {"status": "permanent_error"},  # caller fills in `error`
    "cancelled":   {"status": "cancelled", "error": "Response was cancelled"},
    "queued":      {"status": "queued",    "progress": 0.0},
}

# perplexity.py
_PERPLEXITY_STATUS_TABLE: dict[str, dict[str, Any]] = {
    "CREATED":     {"status": "queued",    "progress": 0.0},
    "IN_PROGRESS": {"status": "running",   "progress": 0.5},
    "COMPLETED":   {"status": "completed", "progress": 1.0},
    "FAILED":      {"status": "permanent_error"},  # caller fills in `error`
}
```

**Edge-case strategy:**
- The helper is pure: no I/O, no caching, no exception swallowing.
- Caller fills in dynamic fields (`error` from upstream, runtime
  `progress` from metadata) by mutating the returned dict.
- Unknown statuses fall through to a permanent_error with the literal
  surfaced — both providers already do this.

**Migration:**
- `OpenAIProvider.check_status` lines 277–304 (the if/elif chain on
  `response.status`): collapse to a `_translate_provider_status(...)`
  call, then post-mutate for in_progress progress and failed/incomplete
  error fields.
- `PerplexityProvider._poll_async_job` lines after `payload = response.json()`:
  same collapse, with the FAILED branch post-mutating `error` from
  `payload.get("error_message")`.

---

## Accidental divergences fixed

### A1 — Quota detection symmetry (FIX BOTH DIRECTIONS, accepted)

- `_map_perplexity_error_async` 429 branch: add body inspection mirroring
  the existing `_rate_limit_error_is_quota` helper. If body contains
  quota markers (`insufficient_quota`, `quota`, `billing`, `credit`,
  `credits`, `monthly spend`, `exhausted`, `no credits`, `blocked`),
  return `APIQuotaError` instead of `APIRateLimitError`.
- `_map_perplexity_error` (sync): also add a 402-equivalent guard for
  the case where the openai SDK ever surfaces a 402 as something other
  than `RateLimitError`. Since the sync path doesn't see raw status
  codes, this means: in the catch-all `APIError` branch, inspect
  `getattr(exc, "status_code", None) == 402` and return `APIQuotaError`
  if matched. Belt-and-suspenders per user direction.

**Test:** add 1 case to `tests/test_provider_perplexity_async.py`:
`test_async_map_429_with_quota_body_upgrades_to_quota_error`. Add 1 case
to `tests/test_openai_errors.py` (or perplexity sync equivalent) for the
402-as-APIError sync path.

### A2 — Async 403 branch (ACCEPTED)

`_map_perplexity_error_async`: add explicit `status == 403` branch
returning `ProviderError(_PROVIDER_NAME, "Permission denied (check tier
/ model access).", raw_error=raw)` matching sync wording.

**Test:** add 1 case to `tests/test_provider_perplexity_async.py`:
`test_async_map_403_returns_permission_denied_provider_error`.

### A4 — Model hint formatting (ACCEPT BOTH cosmetics)

Unify on `f" (model: {model!r})"` (repr-quoted) — async's existing form
is the more correct default for free-form model strings. Patch
`_map_perplexity_error` 422-equivalent branch to match.

**Test:** existing tests already check the message contains the model
name. Update `_map_perplexity_error` test expectation if it asserts the
exact literal.

### B1 — Stale-cache fallback on HTTPStatusError (ACCEPT, recommended scope)

`_poll_async_job`: in the `except httpx.HTTPStatusError` branch, after
the 404 special case, add a stale-cache check before the generic
transient_error return:

```python
except httpx.HTTPStatusError as exc:
    if exc.response.status_code == 404:
        return {"status": "permanent_error", "error": "Job expired (7-day TTL) or not found server-side"}
    cached = job_info.get("response_data") or {}
    if cached.get("status") == "COMPLETED":
        return {"status": "completed", "progress": 1.0}
    return {
        "status": "transient_error",
        "error": f"HTTP {exc.response.status_code}",
        "error_class": type(exc).__name__,  # also fixes B2
    }
```

**Test:** add 1 case mirroring
`test_check_status_transient_error_with_stale_completed_cache_returns_completed`
but raising HTTPStatusError(500) instead of ConnectError.

### B2 — error_class derivation (ACCEPT BOTH cosmetics)

Already folded into B1's edit: replace the literal `"HTTPStatusError"`
with `type(exc).__name__`.

---

## Intentional divergences preserved (DOCUMENT ALL FIVE)

Add brief comments at each site so future factor-dedup runs (and human
maintainers) don't try to consolidate.

### A3 — Async lacks 400 BadRequest branch

`_map_perplexity_error_async`, before the unknown-status fallthrough:

```python
# Intentional: Perplexity's async API documents 422 (not 400) for
# invalid requests. A 400 would be unusual; falls through to the
# generic HTTP-{status} bucket on purpose.
```

### A5 — Invalid-key body inspection surface

Above the 401 branch in `_map_perplexity_error_async`:

```python
# Intentional: async inspects exc.response.text only; the sync mapper
# inspects exc.body + str(exc) because openai SDK exceptions carry
# different surfaces. Both are correct for their respective contexts.
```

### A6 — Unreachable APIError fallthrough in _map_openai_error

After the `if isinstance(exc, openai.APIError)` branch:

```python
# Intentional defense-in-depth: APIError is the SDK base class so this
# fallthrough is unreachable in practice. Kept to guard against
# non-SDK exceptions sneaking through future refactors.
```

### B3 — Catch-all wraps with type prefix

In `_poll_async_job`'s catch-all `Exception` branch:

```python
# Intentional: named exception branches use bare str(exc); the catch-all
# prepends `({type(exc).__name__})` so users can distinguish a known
# exception class from an unexpected one in error logs.
```

### B4 — P18 non-background shortcut

Already has a TODO marker in OpenAI; mirror it in Perplexity's
`check_status` dispatcher:

```python
# P18 non-background shortcut: kept symmetric with OpenAIProvider for
# defense-in-depth. TODO(P19): remove both shortcuts when the
# immediate-kind path no longer transits check_status at all.
```

---

## Risks

- **A1's belt-and-suspenders sync 402 check** assumes the openai SDK's
  `APIError` carries a `status_code` attribute. Verify with
  `dir(openai.APIError)` before committing the patch; if absent, fall
  back to inspecting `getattr(exc, "response", None).status_code` or
  drop the sync direction (async-only fix is fine).
- **B1 changes a behavior** under network blip + 5xx scenarios: a
  Perplexity background run that previously failed with `transient_error`
  on a 5xx-after-completed will now succeed with `completed`. This is
  the intended fix, but a runner whose retry policy was tuned around
  the old behavior could see a measurable change in completion rates
  (a positive change, but still a change).
- **Helper extraction (`_translate_provider_status`)** introduces a new
  module-level dependency. If misused (e.g., caller forgets to mutate
  the returned dict for in_progress progress), the runner could report
  hardcoded `0.5` when actual progress is available. Mitigation: add a
  unit test per provider that the in_progress branch produces
  metadata-driven progress when supplied.
- **The `_invalid_key_thotherror` helper** lives in `perplexity.py`
  initially. If a third caller emerges later (Gemini in P28?), it
  should be promoted to `errors.py`. Note this in the helper docstring.

---

## Suggested sequencing

1. **Add `_translate_provider_status` helper** (new module or appended
   to `base.py`). Add unit tests for the helper itself (table lookup,
   unknown-status fallback, mutation safety).
2. **Refactor OpenAIProvider.check_status** to use the helper. Run the
   full OpenAI test suite (`tests/test_oai_background.py`,
   `tests/test_openai_errors.py`) — should be zero regressions.
3. **Refactor _poll_async_job** to use the helper. Apply B1 stale-cache
   fix and B2 error_class fix in the same edit. Run TS02 tests.
4. **Add `_invalid_key_thotherror` helper** in `perplexity.py`. Refactor
   both `_map_perplexity_error` and `_map_perplexity_error_async` 401
   branches to call it. Run T04 tests.
5. **Apply A1 (both directions), A2, A4** in `_map_perplexity_error_async`
   plus the sync 402 belt. Add the 3 new test cases.
6. **Apply documentation comments** for A3, A5, A6, B3, B4. Pure
   comments — no test changes.
7. **Run full pre-commit gate** (lefthook = ruff + ty + bandit + gitleaks
   + codespell + ./thoth_test). Verify 1213+ pytest tests still pass.

Each step is a separate commit. Suggested commit-message conventions
match P27's existing style (`refactor(p27-followup): ...`,
`fix(p27-followup): ...`, `docs(p27-followup): ...`).

---

## Out of scope (deferred)

- **A richer Polling-Provider mixin / protocol** (Q5 option C).
  Belongs in P29 (architecture review of background providers) once
  Gemini's P28 background provider lands and a third concrete
  implementation reveals the right abstraction shape.
- **Promoting `_invalid_key_thotherror` to `errors.py`.** Wait for the
  third caller (Gemini) before committing to the API.
- **Unifying the timeout / connect-error string literals** between the
  three mappers. Currently byte-identical by coincidence; could become
  a shared constants block, but the savings are <10 lines and the drift
  risk is low.
