# P24 — Gemini Immediate + Cross-Provider Consistency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a synchronous Gemini provider via `google-genai>=1.74.0`, and atomically normalize the existing OpenAI and Perplexity immediate providers to a single canonical surface so the codebase ships with all three providers consistent.

**Architecture:** Mirror the P23/Perplexity provider pattern (built-in modes with provider-namespaced config, side-channel stream events for `reasoning`/`citation`, error mapper with `_map_<provider>_error`, tenacity retry on `_submit_with_retry`, kind-mismatch guard via `_validate_kind_for_model`). The work is sequenced so cross-provider naming + bug-fix work lands BEFORE Gemini, which lets Gemini be written against a stable target.

**Tech Stack:** Python 3.10+, `google-genai>=1.74.0` (new dep), existing `openai` SDK, `tenacity`, `httpx` (transport-error wrap), `pytest`, `ruff`, `ty`. CI via GitHub Actions.

**Spec sources:**
- `projects/P24-gemini-immediate-sync.md` — full scope, parity matrix, provider-deltas, 17 TS/T tasks.
- `planning/p24-immediate-providers-consolidation.v1.md` — factor-dedup output classifying drift across the three providers.

**Self-pacing rule:** This plan touches 3 providers + CLI + CI + tests. Run the full pre-commit gate (`just check` + `uv run ruff format --check src/ tests/` + `uv run pytest -q` + `./thoth_test -r --skip-interactive -q`) every 2-3 commits, NOT only at the end (per `CLAUDE.md` "Periodic full-gate runs"). The plan calls out gate points explicitly.

## Plan refresh notes (post-P27 merge — 2026-05-03)

The factor-dedup pass that informed this plan ran against `perplexity.py` BEFORE P27 (Perplexity background deep-research) merged into main. Branch was fast-forwarded after the dedup pass. Material differences vs the original comparator report:

1. **`perplexity.py` is now DUAL-MODE** (immediate + background). The factor-dedup classification of "immediate-only by design" applies only to the immediate-path methods inside the file — the file itself now has a sibling background path.
2. **`_invalid_key_thotherror(provider, settings_url) -> ThothError` helper exists** at `perplexity.py:143`. P27 polish extracted this. **Plan adjustment**: in Phase 2 Task 2.2 (OpenAI auth-invalid `exit_code=2`) and Phase 4 Task 4.3 (Gemini auth-invalid handling), MOVE this helper to `src/thoth/providers/_helpers.py` and have all three providers call it, rather than each duplicating the `ThothError(...)` construction. This is the natural consolidation point — P27 did the first half; this work does the rest.
3. **`_map_perplexity_error_async`** at `perplexity.py:246` is the background-path sibling error mapper. Its docstring (line 151) explicitly says it preserves "byte-identical wording" with `_map_perplexity_error`. **Out of scope** for this plan — the consolidation is immediate-path only.
4. **`_PERPLEXITY_STATUS_TABLE`** at `perplexity.py:109` is a new module-level status table for the background path. Not touched.
5. **`list_models` adds `sonar-deep-research`** entry. The kind-mismatch guard logic in `_validate_kind_for_model` still rejects this model on `kind=immediate`; nothing in this plan changes.
6. **Line numbers in any task that says `perplexity.py:NNN-MMM` may be stale** — `_DIRECT_SDK_KEYS` was at 211-217, now at 372; `_PROVIDER_NAME` was 102, now 103. **Executors must grep for the constant or function name**, not chase the line numbers in this plan.

---

## File structure

### Files to create

| Path | Responsibility |
|---|---|
| `src/thoth/providers/gemini.py` | New `GeminiProvider` class + `_map_gemini_error` + module constants |
| `tests/test_provider_gemini.py` | Unit tests for the Gemini provider |
| `tests/extended/test_gemini_real_workflows.py` | Gated `live_api` end-to-end tests |
| `planning/p24-providers-root-namespace-investigation.v1.md` | T17 investigation report deciding ship vs punt |

### Files to modify

| Path | Why |
|---|---|
| `src/thoth/providers/openai.py` | Namespace migration (TS10/T11), `md_link_*` sanitization (T12), `exit_code=2` alignment (T14), `_DIRECT_SDK_KEYS_OPENAI` + `_PROVIDER_NAME_OPENAI` constants, optionally streaming-events wire-up after audit (T13) |
| `src/thoth/providers/perplexity.py` | Rename `_DIRECT_SDK_KEYS` → `_DIRECT_SDK_KEYS_PERPLEXITY`, `_PROVIDER_NAME` → `_PROVIDER_NAME_PERPLEXITY`; add `NotFoundError` mapping; add `unsupported parameter` regex extraction; add empty-content debug-print |
| `src/thoth/providers/__init__.py` | Register `GeminiProvider` + `PROVIDER_ENV_VARS["gemini"] = "GEMINI_API_KEY"` |
| `src/thoth/config.py` | Add 3 Gemini built-in modes to `BUILTIN_MODES` |
| `src/thoth/cli.py`, `src/thoth/cli_subcommands/_options.py`, `src/thoth/cli_subcommands/ask.py`, `src/thoth/cli_subcommands/_option_policy.py`, `src/thoth/run.py` | Thread `--api-key-gemini` through the option surface |
| `src/thoth/commands.py`, `src/thoth/interactive.py` | Replace "Gemini (not implemented)" copy with the implemented description |
| `src/thoth/help.py` | Add `[providers.gemini]` block to auth help |
| `src/thoth/errors.py` | (Possibly) update API-key resolution if a new provider needs registry knowledge |
| `tests/baselines/providers_list.json` | Regenerate snapshot after surface text changes |
| `tests/extended/conftest.py` | Add `live_gemini_env` fixture, `require_gemini_key()` helper; extend `assert_no_secret_leaked` to redact `GEMINI_API_KEY` |
| `tests/extended/test_model_kind_runtime.py` | Remove any current Gemini skip; verify auto-derivation from `BUILTIN_MODES` |
| `tests/test_openai_errors.py`, `tests/test_provider_perplexity.py`, `tests/test_provider_config.py`, `tests/test_cli_option_policy.py` | Add tests for namespace migration, NotFoundError mapping, regex extraction, sanitization, exit_code, `--api-key-gemini` |
| `.github/workflows/extended.yml`, `.github/workflows/live-api.yml` | Add `GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}` to env blocks; parse with YAML, not substring scan (P23-R10) |
| `pyproject.toml` | Add `google-genai>=1.74.0` |
| `projects/P24-gemini-immediate-sync.md`, `PROJECTS.md` | Trunk markers (`[~]` on first commit, `[x]` on closeout) |

---

## Phases at a glance

1. **Phase 1 — Cross-provider naming convention** (no behavior change): rename Perplexity constants, add OpenAI constants. **Lands before Gemini so Gemini is written against the convention.**
2. **Phase 2 — Cross-provider bug fixes**: OpenAI sanitization + `exit_code=2`; Perplexity `NotFoundError` mapping + regex extraction + empty-content debug-print.
3. **Phase 3 — OpenAI namespace migration**: `[modes.X.openai]` + backwards-compat deprecation warning for flat keys. Highest-risk phase; isolated commit.
4. **Phase 4 — Gemini implementation**: dep, skeleton, BUILTIN_MODES, request construction, error mapping, retry, stream, non-stream, kind-mismatch.
5. **Phase 5 — Gemini surface + CI**: `--api-key-gemini` plumbing, registry flip, provider description text, snapshot regen, extended/live_api coverage, workflow YAML.
6. **Phase 6 — Audits + investigations**: OpenAI Responses API streaming-events audit (T13 outcome); `[providers.X]` root-namespace investigation (T17 ship/punt decision).
7. **Phase 7 — Closeout**: Full pre-commit gate, project markers, final commit.

---

## Phase 1 — Cross-provider naming convention

Rename Perplexity's bare constants to the suffix-named convention; introduce the equivalents for OpenAI. This phase is mechanical and produces no behavior change — it's pure refactor. Land first so all subsequent phases (and Gemini) reference the consistent names.

### Task 1.1: Rename Perplexity constants

**Files:**
- Modify: `src/thoth/providers/perplexity.py`
- Test: `tests/test_provider_perplexity.py` (existing file)

- [ ] **Step 1: Add tests asserting the renamed constants exist**

Append to `tests/test_provider_perplexity.py` (top-level test functions, no class):

```python
def test_perplexity_constants_use_suffix_naming() -> None:
    """Perplexity module-level constants follow the cross-provider suffix convention."""
    from thoth.providers import perplexity as pp

    assert hasattr(pp, "_DIRECT_SDK_KEYS_PERPLEXITY"), (
        "_DIRECT_SDK_KEYS_PERPLEXITY must exist (renamed from bare _DIRECT_SDK_KEYS)"
    )
    assert hasattr(pp, "_PROVIDER_NAME_PERPLEXITY"), (
        "_PROVIDER_NAME_PERPLEXITY must exist (renamed from bare _PROVIDER_NAME)"
    )
    assert pp._PROVIDER_NAME_PERPLEXITY == "perplexity"
    assert "max_tokens" in pp._DIRECT_SDK_KEYS_PERPLEXITY
    assert "temperature" in pp._DIRECT_SDK_KEYS_PERPLEXITY


def test_perplexity_bare_constant_names_removed() -> None:
    """Bare unsuffixed names must NOT exist after the rename."""
    from thoth.providers import perplexity as pp

    assert not hasattr(pp, "_DIRECT_SDK_KEYS"), "bare _DIRECT_SDK_KEYS leaked through rename"
    assert not hasattr(pp, "_PROVIDER_NAME"), "bare _PROVIDER_NAME leaked through rename"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_provider_perplexity.py::test_perplexity_constants_use_suffix_naming tests/test_provider_perplexity.py::test_perplexity_bare_constant_names_removed -v`

Expected: FAIL — `_DIRECT_SDK_KEYS_PERPLEXITY` not found.

- [ ] **Step 3: Mechanical rename via Edit's replace_all**

Use Edit with `replace_all=true` on `src/thoth/providers/perplexity.py`:
1. `_DIRECT_SDK_KEYS` → `_DIRECT_SDK_KEYS_PERPLEXITY`
2. `_PROVIDER_NAME` → `_PROVIDER_NAME_PERPLEXITY`

Verify the rename touched the constant definitions (~lines 102, 211-217) AND every reference site in `_map_perplexity_error` (~lines 132-206).

- [ ] **Step 4: Run the new tests + the existing Perplexity test suite**

Run: `uv run pytest tests/test_provider_perplexity.py -v`
Expected: PASS for the 2 new tests + all existing Perplexity tests still pass (no behavior change).

- [ ] **Step 5: Commit**

```bash
git add src/thoth/providers/perplexity.py tests/test_provider_perplexity.py
git commit -m "$(cat <<'EOF'
refactor(perplexity): rename module constants to suffix-named convention

Renames _DIRECT_SDK_KEYS and _PROVIDER_NAME to _DIRECT_SDK_KEYS_PERPLEXITY
and _PROVIDER_NAME_PERPLEXITY for grep-uniqueness across providers. Mechanical
replace_all; no behavior change.
EOF
)"
```

### Task 1.2: Introduce OpenAI constants

**Files:**
- Modify: `src/thoth/providers/openai.py`
- Test: `tests/test_openai_errors.py` (existing file)

- [ ] **Step 1: Add tests asserting OpenAI constants exist**

Append to `tests/test_openai_errors.py`:

```python
def test_openai_constants_use_suffix_naming() -> None:
    """OpenAI module-level constants follow the cross-provider suffix convention."""
    from thoth.providers import openai as op

    assert hasattr(op, "_DIRECT_SDK_KEYS_OPENAI"), (
        "_DIRECT_SDK_KEYS_OPENAI must exist (introduced for cross-provider parity)"
    )
    assert hasattr(op, "_PROVIDER_NAME_OPENAI"), (
        "_PROVIDER_NAME_OPENAI must exist (introduced for cross-provider parity)"
    )
    assert op._PROVIDER_NAME_OPENAI == "openai"
    # The Responses API kwargs the immediate path passes:
    assert "temperature" in op._DIRECT_SDK_KEYS_OPENAI
    assert "max_tool_calls" in op._DIRECT_SDK_KEYS_OPENAI
    assert "tools" in op._DIRECT_SDK_KEYS_OPENAI
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_openai_errors.py::test_openai_constants_use_suffix_naming -v`
Expected: FAIL — constants not found.

- [ ] **Step 3: Add the constants to `openai.py`**

In `src/thoth/providers/openai.py`, near the top of the module (after imports, before `_rate_limit_error_is_quota`):

```python
_PROVIDER_NAME_OPENAI = "openai"
_DIRECT_SDK_KEYS_OPENAI: tuple[str, ...] = (
    "model",
    "input",
    "reasoning",
    "tools",
    "background",
    "temperature",
    "max_tool_calls",
)
```

Replace every inline `"openai"` literal in `_map_openai_error(...)` body (~9 occurrences at openai.py:73-142) with `_PROVIDER_NAME_OPENAI`. Use Edit with `replace_all=false` for each occurrence to be safe — there is risk of replacing string content like `"openai server error"` text, so target the `provider="openai"` kwarg and `f-string` `"openai"` literals only.

The cleanest pattern: search for each `*Error("openai", ...)` call and rewrite the first arg.

- [ ] **Step 4: Run the new test + existing OpenAI test suite**

Run: `uv run pytest tests/test_openai_errors.py -v`
Expected: PASS — all existing tests still pass + the new constant test passes.

- [ ] **Step 5: Commit**

```bash
git add src/thoth/providers/openai.py tests/test_openai_errors.py
git commit -m "$(cat <<'EOF'
refactor(openai): introduce _DIRECT_SDK_KEYS_OPENAI and _PROVIDER_NAME_OPENAI

Centralizes the SDK-native kwarg allowlist and provider-name string in module
constants for cross-provider parity. Replaces ~9 inline "openai" literals in
_map_openai_error with the constant. No behavior change.
EOF
)"
```

### Phase 1 gate

- [ ] **Run targeted check**: `just check` + `uv run pytest tests/test_provider_perplexity.py tests/test_openai_errors.py -v`
- [ ] **Verify**: 0 lint errors, 0 type errors, all tests pass.

---

## Phase 2 — Cross-provider bug fixes

Five small fixes, each test-driven. None are interdependent; commit each independently.

### Task 2.1: Backport `md_link_*` sanitization to OpenAI's Sources block (security)

**Files:**
- Modify: `src/thoth/providers/openai.py:614-622`
- Test: `tests/test_openai_errors.py`

- [ ] **Step 1: Write failing adversarial-input tests**

Append to `tests/test_openai_errors.py`:

```python
def test_openai_sources_block_escapes_html_in_title() -> None:
    """OpenAI's ## Sources block must use md_link_title to escape HTML."""
    from types import SimpleNamespace
    from thoth.providers.openai import OpenAIProvider

    provider = OpenAIProvider(api_key="dummy", config={})
    fake_response = SimpleNamespace(
        output=[
            SimpleNamespace(
                type="message",
                status="completed",
                phase="final_answer",
                content=[
                    SimpleNamespace(
                        type="output_text",
                        text="Answer body.",
                        annotations=[
                            {"url": "https://example.com", "title": "<script>alert(1)</script>"},
                        ],
                    )
                ],
            )
        ],
    )
    provider.jobs["test"] = {"response": fake_response, "background": False, "created_at": 0}

    import asyncio
    rendered = asyncio.run(provider.get_result("test"))
    assert "<script>" not in rendered, "raw HTML in title leaked into output"
    assert "&lt;script&gt;" in rendered or "\\<script\\>" in rendered, (
        "title not escaped via md_link_title"
    )


def test_openai_sources_block_blocks_javascript_scheme_in_url() -> None:
    """OpenAI's ## Sources block must use md_link_url to neutralize javascript: URLs."""
    from types import SimpleNamespace
    from thoth.providers.openai import OpenAIProvider

    provider = OpenAIProvider(api_key="dummy", config={})
    fake_response = SimpleNamespace(
        output=[
            SimpleNamespace(
                type="message",
                status="completed",
                phase="final_answer",
                content=[
                    SimpleNamespace(
                        type="output_text",
                        text="Answer.",
                        annotations=[
                            {"url": "javascript:alert(1)", "title": "Click me"},
                        ],
                    )
                ],
            )
        ],
    )
    provider.jobs["test"] = {"response": fake_response, "background": False, "created_at": 0}

    import asyncio
    rendered = asyncio.run(provider.get_result("test"))
    assert "javascript:" not in rendered, "javascript: scheme not neutralized"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_openai_errors.py::test_openai_sources_block_escapes_html_in_title tests/test_openai_errors.py::test_openai_sources_block_blocks_javascript_scheme_in_url -v`
Expected: FAIL — raw HTML/scheme passes through unsanitized.

- [ ] **Step 3: Apply sanitization to `openai.py:614-622`**

In `src/thoth/providers/openai.py`, near the top of file (after `_PROVIDER_NAME_OPENAI`):

```python
from thoth.utils import md_link_title, md_link_url
```

In the citation rendering block (`openai.py:614-622`), find the `f"- [{title}]({url})"` line and replace with:

```python
f"- [{md_link_title(title)}]({md_link_url(url)})"
```

Match Perplexity's pattern at `perplexity.py:463`. Verify the `title` variable's fallback to URL is preserved.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_openai_errors.py -v`
Expected: PASS — both new tests + all existing tests.

- [ ] **Step 5: Commit**

```bash
git add src/thoth/providers/openai.py tests/test_openai_errors.py
git commit -m "$(cat <<'EOF'
fix(openai): sanitize titles and URLs in ## Sources block

Apply md_link_title/md_link_url helpers to OpenAI's citation rendering, mirroring
Perplexity's defense against HTML and scheme injection. Closes a known gap where
hostile annotation titles or URLs could break out of the markdown link syntax.
EOF
)"
```

### Task 2.2: OpenAI auth-invalid `exit_code=2` alignment + extract `_invalid_key_thotherror` helper

**Refresh note**: P27 already extracted `_invalid_key_thotherror(provider, settings_url) -> ThothError` to `perplexity.py:143`. This task now PROMOTES it to `src/thoth/providers/_helpers.py` and has OpenAI + Gemini call it, instead of duplicating the construction. The signature gains `exit_code=2` if it doesn't already have it.

**Files:**
- Modify: `src/thoth/providers/openai.py:73-80`
- Test: `tests/test_openai_errors.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_openai_errors.py`:

```python
def test_openai_invalid_key_thotherror_has_exit_code_2() -> None:
    """OpenAI's invalid-key ThothError must set exit_code=2 to match Perplexity."""
    import openai as openai_sdk
    from thoth.providers.openai import _map_openai_error
    from thoth.errors import ThothError

    # Construct an AuthenticationError with the "incorrect api key" body trigger
    fake_exc = openai_sdk.AuthenticationError(
        message="Incorrect API key provided",
        response=None,
        body={"error": {"code": "invalid_api_key", "message": "Incorrect API key provided"}},
    )
    mapped = _map_openai_error(fake_exc, "gpt-4o", verbose=False)
    assert isinstance(mapped, ThothError)
    assert mapped.exit_code == 2, f"expected exit_code=2 (Perplexity parity), got {mapped.exit_code}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_openai_errors.py::test_openai_invalid_key_thotherror_has_exit_code_2 -v`
Expected: FAIL — current code does not set `exit_code`.

- [ ] **Step 3: Update `openai.py:73-80`**

Find the invalid-key `ThothError(...)` construction in `_map_openai_error` (around line 75-79). Add `exit_code=2` to the kwargs, mirroring `perplexity.py:142-152`'s pattern. Example:

```python
return ThothError(
    "Invalid OpenAI API key",
    hint="Verify the key at https://platform.openai.com/api-keys",
    exit_code=2,
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_openai_errors.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/thoth/providers/openai.py tests/test_openai_errors.py
git commit -m "fix(openai): align invalid-key ThothError exit_code=2 with Perplexity"
```

### Task 2.3: Perplexity `NotFoundError` mapping

**Files:**
- Modify: `src/thoth/providers/perplexity.py:132-206`
- Test: `tests/test_provider_perplexity.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_provider_perplexity.py`:

```python
def test_perplexity_not_found_error_maps_with_model_hint() -> None:
    """openai.NotFoundError must map to ProviderError with the 'models' CLI hint."""
    import openai as openai_sdk
    from thoth.providers.perplexity import _map_perplexity_error
    from thoth.errors import ProviderError

    fake_exc = openai_sdk.NotFoundError(
        message="Model 'sonar-imaginary' not found",
        response=None,
        body={"error": {"code": "model_not_found", "message": "Model 'sonar-imaginary' not found"}},
    )
    mapped = _map_perplexity_error(fake_exc, "sonar-imaginary", verbose=False)
    assert isinstance(mapped, ProviderError)
    assert mapped.provider == "perplexity"
    assert "sonar-imaginary" in str(mapped) or "not found" in str(mapped).lower()
    assert "models" in (mapped.hint or "").lower(), (
        "ProviderError hint must point users at the models CLI command"
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_provider_perplexity.py::test_perplexity_not_found_error_maps_with_model_hint -v`
Expected: FAIL — currently falls through to `APIError` generic catch.

- [ ] **Step 3: Add the branch to `_map_perplexity_error`**

In `src/thoth/providers/perplexity.py`, find `_map_perplexity_error` (~lines 132-206). After the `BadRequestError` branch and before `APITimeoutError`, insert the `NotFoundError` branch mirroring `openai.py:87-93`:

```python
if isinstance(exc, openai.NotFoundError):
    model_str = repr(model) if model else "(unknown)"
    return ProviderError(
        _PROVIDER_NAME_PERPLEXITY,
        f"Model {model_str} not found or unavailable on this provider.",
        hint="Run `thoth providers --models --provider perplexity` to list valid models.",
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_provider_perplexity.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/thoth/providers/perplexity.py tests/test_provider_perplexity.py
git commit -m "fix(perplexity): map NotFoundError to ProviderError with models CLI hint"
```

### Task 2.4: Perplexity `unsupported parameter` regex extraction

**Files:**
- Modify: `src/thoth/providers/perplexity.py` (`BadRequestError` branch in `_map_perplexity_error`)
- Test: `tests/test_provider_perplexity.py`
- Possibly create: `src/thoth/providers/_helpers.py` (if shared helper extraction is decided)

- [ ] **Step 1: Write failing test for regex extraction**

Append to `tests/test_provider_perplexity.py`:

```python
def test_perplexity_unsupported_parameter_regex_extraction() -> None:
    """BadRequestError with an offending-parameter hint surfaces the parameter name."""
    import openai as openai_sdk
    from thoth.providers.perplexity import _map_perplexity_error

    fake_exc = openai_sdk.BadRequestError(
        message="Unsupported parameter 'frequency_penalty' for sonar-pro.",
        response=None,
        body={"error": {"code": "invalid_request_error", "message": "Unsupported parameter 'frequency_penalty' for sonar-pro."}},
    )
    mapped = _map_perplexity_error(fake_exc, "sonar-pro", verbose=False)
    assert "frequency_penalty" in str(mapped), (
        "extracted parameter name must surface in the user-facing error"
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_provider_perplexity.py::test_perplexity_unsupported_parameter_regex_extraction -v`
Expected: FAIL — current Perplexity branch produces a generic "Bad request" message.

- [ ] **Step 3: Add regex extraction to the `BadRequestError` branch**

In `src/thoth/providers/perplexity.py`, find the `BadRequestError` branch in `_map_perplexity_error` (~lines 166-172). Add the same pattern OpenAI uses at `openai.py:95-113`:

```python
if isinstance(exc, openai.BadRequestError):
    import re
    msg_lower = str(exc).lower()
    param_match = re.search(r"'(\w+)'", str(exc))
    if "unsupported parameter" in msg_lower and param_match:
        param = param_match.group(1)
        return ProviderError(
            _PROVIDER_NAME_PERPLEXITY,
            f"Perplexity does not support parameter {param!r} for this model. "
            f"Remove it from the mode config or its provider namespace.",
        )
    model_hint = f" (model: {model})" if model else ""
    return ProviderError(
        _PROVIDER_NAME_PERPLEXITY,
        f"Bad request{model_hint}. Check model name and request shape.",
    )
```

- [ ] **Step 4: Helper-extraction decision**

Inspect both providers' regex usage (`openai.py:95-113` and the new Perplexity branch). If the regex pattern + the surrounding "is this an unsupported-parameter error" check are identical, extract a helper:

Create `src/thoth/providers/_helpers.py`:

```python
"""Shared helpers for provider error mapping."""

from __future__ import annotations

import re

_UNSUPPORTED_PARAM_RE = re.compile(r"'(\w+)'")


def extract_unsupported_param(message: str) -> str | None:
    """Extract the offending parameter name from a 'unsupported parameter \\'X\\'' error message.

    Returns None if no match. Both OpenAI and Perplexity use this format because they
    share the OpenAI SDK exception body shape.
    """
    if "unsupported parameter" not in message.lower():
        return None
    match = _UNSUPPORTED_PARAM_RE.search(message)
    return match.group(1) if match else None
```

Replace the inline regex in BOTH `openai.py` and `perplexity.py` with `extract_unsupported_param(str(exc))`. If shapes diverge enough that a helper would obscure semantics, document that in `planning/p24-immediate-providers-consolidation.v1.md` instead and keep inline regex.

For Gemini (Phase 4), `_map_gemini_error` will call its own equivalent pattern matching `google.genai.errors.ClientError` body shape, which differs subtly — Gemini will NOT use this helper unless the body shapes converge.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_openai_errors.py tests/test_provider_perplexity.py -v`
Expected: PASS — new test + all pre-existing OpenAI tests still pass after refactor.

- [ ] **Step 6: Commit**

```bash
git add src/thoth/providers/perplexity.py src/thoth/providers/_helpers.py src/thoth/providers/openai.py tests/test_provider_perplexity.py
git commit -m "$(cat <<'EOF'
fix(perplexity): extract offending parameter on BadRequestError

Adds the same regex extraction OpenAI does for "Unsupported parameter 'X'"
errors so users get an actionable message. If both regex sites are identical,
extract to thoth.providers._helpers.extract_unsupported_param; otherwise keep
inline.
EOF
)"
```

### Task 2.5: Perplexity empty-content debug-print

**Files:**
- Modify: `src/thoth/providers/perplexity.py` (`get_result` / `_render_answer_with_sources`)
- Test: `tests/test_provider_perplexity.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_provider_perplexity.py`:

```python
def test_perplexity_empty_content_debug_print(capsys) -> None:
    """When response.choices[0].message.content is empty and verbose=True, emit debug info."""
    from types import SimpleNamespace
    from thoth.providers.perplexity import PerplexityProvider

    provider = PerplexityProvider(api_key="dummy", config={})
    fake_response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=""))],
        search_results=[],
    )
    provider.jobs["test"] = {"response": fake_response}

    import asyncio
    asyncio.run(provider.get_result("test", verbose=True))
    captured = capsys.readouterr()
    # Debug print should fire when content is empty + verbose
    assert "empty" in captured.err.lower() or "debug" in captured.err.lower() or "no content" in captured.err.lower(), (
        "expected an empty-content debug message on stderr when verbose=True"
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_provider_perplexity.py::test_perplexity_empty_content_debug_print -v`
Expected: FAIL — Perplexity has no debug-print path.

- [ ] **Step 3: Backport the pattern from `openai.py:567-588`**

In `src/thoth/providers/perplexity.py`, modify `get_result` (or `_render_answer_with_sources`) to call a debug-print helper when `verbose=True` AND the extracted answer is empty:

```python
if verbose and not content:
    self._debug_print_empty_response(response)


def _debug_print_empty_response(self, response: Any) -> None:
    """Mirror openai.py:567-588's empty-content debug ladder."""
    import sys
    from rich.console import Console
    err_console = Console(file=sys.stderr)
    err_console.print("[yellow]Perplexity: empty content in response. Debug:[/yellow]")
    try:
        if hasattr(response, "model_dump_json"):
            err_console.print(response.model_dump_json(indent=2))
        elif hasattr(response, "__dict__"):
            err_console.print(response.__dict__)
        else:
            err_console.print(repr(response))
    except Exception:
        err_console.print(repr(response))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_provider_perplexity.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/thoth/providers/perplexity.py tests/test_provider_perplexity.py
git commit -m "feat(perplexity): emit empty-content debug ladder when verbose=True"
```

### Phase 2 gate

- [ ] **Run periodic full gate** (per CLAUDE.md "Periodic full-gate runs"):
  ```
  just check
  uv run ruff format --check src/ tests/
  uv run pytest -q
  ./thoth_test -r --skip-interactive -q
  ```
- [ ] **Verify**: 0 lint, 0 type errors, all tests pass, thoth_test green.

---

## Phase 3 — OpenAI namespace migration (highest-risk phase)

This phase migrates OpenAI from flat `self.config.get(...)` to `[modes.X.openai]` namespaced config with backwards-compat. The risk is that existing user mode TOMLs use flat keys (`temperature`, `code_interpreter`, `max_tool_calls`); the deprecation warning bridges one release cycle.

### Task 3.1: Add backwards-compat read path with deprecation

**Files:**
- Modify: `src/thoth/providers/openai.py:198-269` (`_submit_with_retry`)
- Test: `tests/test_provider_config.py` (existing) and `tests/test_openai_errors.py`

- [ ] **Step 1: Write failing tests for namespace + backwards-compat + deprecation**

Append to `tests/test_provider_config.py`:

```python
import warnings
import pytest


def test_openai_reads_namespaced_config() -> None:
    """OpenAIProvider must read [modes.X.openai].* keys."""
    from thoth.providers.openai import OpenAIProvider

    provider = OpenAIProvider(
        api_key="dummy",
        config={"openai": {"temperature": 0.42, "max_tool_calls": 5}, "kind": "immediate"},
    )
    # Trigger the request-build path; assertion via internal helper if exposed,
    # otherwise via mocking client.responses.stream(...) and asserting kwargs.
    # Implementation: provider must expose an introspectable _build_kwargs(...) method
    # OR the test mocks the SDK call and inspects kwargs.
    # See Step 3 below for the structure decision.


def test_openai_flat_config_emits_deprecation_warning() -> None:
    """Flat top-level keys (temperature without 'openai' nesting) trigger DeprecationWarning."""
    from thoth.providers.openai import OpenAIProvider

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        OpenAIProvider(
            api_key="dummy",
            config={"temperature": 0.42, "kind": "immediate"},
        )
        # Build a request to trigger the deprecation read path
        # (depends on where the read happens; adjust per implementation)

    # Find the DeprecationWarning emitted for flat keys
    dep_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert any("flat config" in str(w.message).lower() or "namespace" in str(w.message).lower()
               for w in dep_warnings), (
        "expected DeprecationWarning advising migration to [modes.X.openai] namespace"
    )


def test_openai_namespaced_overrides_flat_with_warning() -> None:
    """When both flat and namespaced keys exist, namespaced wins and a warning is emitted."""
    from thoth.providers.openai import OpenAIProvider

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        provider = OpenAIProvider(
            api_key="dummy",
            config={
                "temperature": 0.1,                  # flat
                "openai": {"temperature": 0.9},      # namespaced - should win
                "kind": "immediate",
            },
        )

    # Implementation-specific assertion: ensure the resolved temperature is 0.9
    # The exact assertion depends on whether _build_kwargs is exposed for testing.
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_provider_config.py -k "openai" -v`
Expected: FAIL — namespace not honored, no deprecation emitted.

- [ ] **Step 3: Refactor `_submit_with_retry` to read from `self.config["openai"]` namespace with backwards-compat**

In `src/thoth/providers/openai.py`, introduce a config-resolution helper near the top of the class:

```python
def _resolve_provider_config_value(
    self, key: str, default: Any = None, *, _warned: dict | None = None,
) -> Any:
    """Read a config key from `self.config["openai"][key]` first, falling back to flat `self.config[key]`.

    Emits DeprecationWarning when the flat fallback is used, advising migration
    to [modes.X.openai] namespace. Tracks warnings per-key in `_warned` to avoid
    spamming.
    """
    import warnings
    nested = self.config.get("openai", {}) or {}
    if key in nested:
        return nested[key]
    if key in self.config and key != "openai":
        if _warned is None or key not in _warned:
            warnings.warn(
                f"OpenAI provider read flat config key {key!r}; migrate to "
                f"[modes.X.openai].{key} namespace. Flat key support will be removed in a future release.",
                DeprecationWarning,
                stacklevel=3,
            )
            if _warned is not None:
                _warned[key] = True
        return self.config[key]
    return default
```

Update every `self.config.get(...)` call in `_submit_with_retry` (`openai.py:198-269`) to use `self._resolve_provider_config_value(...)`. Cover: `temperature`, `code_interpreter`, `background`, `max_tool_calls`. Leave `kind` and `model` flat — those are framework-level keys, not provider-specific.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_provider_config.py tests/test_openai_errors.py -v`
Expected: PASS — namespace resolved, deprecation warned, flat keys still work.

- [ ] **Step 5: Update existing test fixtures**

Search `tests/` for any test that constructs `OpenAIProvider(config={"temperature": ...})` flat and update to use `config={"openai": {"temperature": ...}}`. Run `grep -n 'config={"temperature"' tests/` to find sites.

- [ ] **Step 6: Run full test suite**

Run: `uv run pytest -q`
Expected: PASS — no regressions; deprecation warnings should appear in test output for tests still using flat keys (acceptable).

- [ ] **Step 7: Commit**

```bash
git add src/thoth/providers/openai.py tests/test_provider_config.py tests/test_openai_errors.py
git commit -m "$(cat <<'EOF'
refactor(openai): migrate to [modes.X.openai] namespaced config with deprecation

Reads provider-specific keys (temperature, code_interpreter, background,
max_tool_calls) from self.config["openai"][key] first, falls back to flat
self.config[key] with a DeprecationWarning. Existing user mode TOMLs continue
to work for one release cycle. Mirrors P23/Perplexity's [modes.X.perplexity]
namespace pattern.
EOF
)"
```

### Phase 3 gate

- [ ] **Run periodic full gate**:
  ```
  just check
  uv run ruff format --check src/ tests/
  uv run pytest -q
  ./thoth_test -r --skip-interactive -q
  ```

---

## Phase 4 — Gemini implementation

The biggest phase. Each task is one TDD-style increment of `src/thoth/providers/gemini.py`.

### Task 4.1: Dependency + module skeleton

**Files:**
- Modify: `pyproject.toml`
- Create: `src/thoth/providers/gemini.py`
- Create: `tests/test_provider_gemini.py`

- [ ] **Step 1: Add `google-genai` to `pyproject.toml`**

Run: `uv add 'google-genai>=1.74.0'`
This updates `pyproject.toml` and `uv.lock`.

- [ ] **Step 2: Write failing test that the module exists with constants**

Create `tests/test_provider_gemini.py`:

```python
"""Unit tests for the Gemini synchronous chat provider (P24)."""

from __future__ import annotations

import pytest


def test_gemini_module_exists() -> None:
    from thoth.providers import gemini  # noqa: F401


def test_gemini_constants_use_suffix_naming() -> None:
    from thoth.providers import gemini

    assert hasattr(gemini, "_DIRECT_SDK_KEYS_GEMINI")
    assert hasattr(gemini, "_PROVIDER_NAME_GEMINI")
    assert gemini._PROVIDER_NAME_GEMINI == "gemini"
    assert "temperature" in gemini._DIRECT_SDK_KEYS_GEMINI
    assert "thinking_budget" in gemini._DIRECT_SDK_KEYS_GEMINI


def test_gemini_provider_class_exists() -> None:
    from thoth.providers.gemini import GeminiProvider
    from thoth.providers.base import ResearchProvider

    assert issubclass(GeminiProvider, ResearchProvider)
```

- [ ] **Step 3: Create `src/thoth/providers/gemini.py` with skeleton**

```python
"""Gemini synchronous chat provider (P24).

Mirrors the P23 Perplexity provider pattern: built-in modes with a
[modes.X.gemini] namespace, side-channel stream events for reasoning and
citation, error mapper with _map_gemini_error, tenacity retry on submit.

Uses the official google-genai SDK (>=1.74.0), NOT Gemini's OpenAI-compat
endpoint, because the compat layer omits grounding metadata, thought parts,
and the thinking-budget knob.
"""

from __future__ import annotations

from typing import Any

from thoth.providers.base import ResearchProvider, StreamEvent

_PROVIDER_NAME_GEMINI = "gemini"

_DIRECT_SDK_KEYS_GEMINI: tuple[str, ...] = (
    "temperature",
    "top_p",
    "top_k",
    "max_output_tokens",
    "stop_sequences",
    "response_mime_type",
    "response_schema",
    "response_json_schema",
    "tools",
    "safety_settings",
    "thinking_budget",
    "include_thoughts",
)


class GeminiProvider(ResearchProvider):
    """Synchronous Gemini chat provider (P24)."""

    def __init__(self, api_key: str = "", config: dict[str, Any] | None = None) -> None:
        super().__init__(api_key=api_key, config=config)
        self.model = (self.config or {}).get("model") or "gemini-2.5-flash-lite"
        self.jobs: dict[str, dict[str, Any]] = {}
        # Lazy-import google-genai to avoid hard dep at module-load time
        from google import genai  # type: ignore[import-not-found]
        self.client = genai.Client(api_key=api_key)

    def is_implemented(self) -> bool:
        return True

    def implementation_status(self) -> str | None:
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_provider_gemini.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock src/thoth/providers/gemini.py tests/test_provider_gemini.py
git commit -m "feat(gemini): add google-genai dep and provider module skeleton"
```

### Task 4.2: Built-in modes + request construction

Per P24-TS01/T01 in the project file. Cover the three built-in modes (`gemini_quick`, `gemini_pro`, `gemini_reasoning`), `[modes.X.gemini]` namespace passthrough into `GenerateContentConfig`, system_instruction handling, default model fallback.

- [ ] **Step 1: Add the three built-in modes to `src/thoth/config.py:BUILTIN_MODES`**

Find the `BUILTIN_MODES` dict (~line 53) and append:

```python
"gemini_quick": {
    "provider": "gemini",
    "model": "gemini-2.5-flash-lite",
    "kind": "immediate",
    "description": "Fast Gemini 2.5 Flash-Lite with web grounding (no thinking).",
    "gemini": {
        "tools": ["google_search"],
        "thinking_budget": 0,
    },
},
"gemini_pro": {
    "provider": "gemini",
    "model": "gemini-2.5-pro",
    "kind": "immediate",
    "description": "Gemini 2.5 Pro with web grounding and dynamic thinking.",
    "gemini": {
        "tools": ["google_search"],
        "thinking_budget": -1,
    },
},
"gemini_reasoning": {
    "provider": "gemini",
    "model": "gemini-2.5-pro",
    "kind": "immediate",
    "description": "Gemini 2.5 Pro with web grounding, dynamic thinking, and surfaced thought summaries.",
    "gemini": {
        "tools": ["google_search"],
        "thinking_budget": -1,
        "include_thoughts": True,
    },
},
```

- [ ] **Step 2: Write failing tests for request construction**

Append to `tests/test_provider_gemini.py`:

```python
def test_gemini_quick_mode_constructs_expected_request() -> None:
    """gemini_quick mode produces the right model + tools + thinking_budget."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from thoth.providers.gemini import GeminiProvider
    from thoth.config import BUILTIN_MODES

    config = {**BUILTIN_MODES["gemini_quick"], "kind": "immediate"}
    with patch("google.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.aio.models.generate_content_stream = AsyncMock(return_value=iter([]))
        mock_client_cls.return_value = mock_client
        provider = GeminiProvider(api_key="dummy", config=config)
        # Trigger a stream call and capture kwargs
        # ... (depends on how stream() is structured; see Task 4.4)


def test_gemini_namespace_passthrough_for_safety_settings() -> None:
    """Keys under [modes.X.gemini].safety_settings flow into GenerateContentConfig."""
    # Same mock pattern: assert config.safety_settings == [...]
    pass  # placeholder until Task 4.4 wires the path; for now, only modes test


def test_gemini_default_model_is_flash_lite_when_unconfigured() -> None:
    from thoth.providers.gemini import GeminiProvider

    provider = GeminiProvider(api_key="dummy", config={})
    assert provider.model == "gemini-2.5-flash-lite"
```

- [ ] **Step 3: Run test to verify it fails / passes**

Run: `uv run pytest tests/test_provider_gemini.py -v`
Expected: only `test_gemini_default_model_is_flash_lite_when_unconfigured` passes; the request-construction tests are placeholders for now.

- [ ] **Step 4: Implement request-construction helpers**

In `src/thoth/providers/gemini.py`, add:

```python
def _build_messages_and_system(self, prompt: str, system_prompt: str | None) -> tuple[list[Any], str | None]:
    """Build the contents list + system_instruction for GenerateContentConfig."""
    from google.genai import types
    contents = [types.Content(role="user", parts=[types.Part(text=prompt)])]
    return contents, system_prompt or None


def _build_tools(self, tool_names: list[str]) -> list[Any]:
    """Translate ['google_search'] into [Tool(google_search=GoogleSearch())]."""
    from google.genai import types
    tools: list[Any] = []
    for name in tool_names:
        if name == "google_search":
            tools.append(types.Tool(google_search=types.GoogleSearch()))
        # Future tool names get appended here
    return tools


def _build_generate_content_config(self) -> Any:
    """Translate [modes.X.gemini].* into GenerateContentConfig kwargs."""
    from google.genai import types
    gemini_cfg = (self.config or {}).get("gemini", {}) or {}
    config_kwargs: dict[str, Any] = {}

    if "tools" in gemini_cfg:
        config_kwargs["tools"] = self._build_tools(gemini_cfg["tools"])

    thinking_budget = gemini_cfg.get("thinking_budget")
    include_thoughts = gemini_cfg.get("include_thoughts", False)
    if thinking_budget is not None or include_thoughts:
        config_kwargs["thinking_config"] = types.ThinkingConfig(
            thinking_budget=thinking_budget if thinking_budget is not None else -1,
            include_thoughts=include_thoughts,
        )

    for key in _DIRECT_SDK_KEYS_GEMINI:
        if key in {"tools", "thinking_budget", "include_thoughts"}:
            continue
        if key in gemini_cfg:
            config_kwargs[key] = gemini_cfg[key]

    return types.GenerateContentConfig(**config_kwargs) if config_kwargs else None
```

- [ ] **Step 5: Run tests + commit**

Run: `uv run pytest tests/test_provider_gemini.py -v`
Expected: PASS.

```bash
git add src/thoth/providers/gemini.py tests/test_provider_gemini.py src/thoth/config.py
git commit -m "$(cat <<'EOF'
feat(gemini): add built-in modes and request construction helpers

Adds gemini_quick / gemini_pro / gemini_reasoning to BUILTIN_MODES.
Implements _build_messages_and_system, _build_tools, _build_generate_content_config
with [modes.X.gemini] namespace translation into GenerateContentConfig.
EOF
)"
```

### Task 4.3: Error mapping + retry policy

Per P24-TS02/T02. Implements `_map_gemini_error` 12-class branch + tenacity retry.

- [ ] **Step 1: Write failing tests for each error class**

Append to `tests/test_provider_gemini.py` — 12 error-class tests + retry-count tests. Use the test shape from `tests/test_provider_perplexity.py`'s parametrized error-mapping table as the template.

```python
import pytest


@pytest.mark.parametrize("status_code,status_string,expected_error_class,expected_substr", [
    (401, "UNAUTHENTICATED", "ThothError", "key is invalid"),  # invalid-key path with exit_code=2
    (429, "RESOURCE_EXHAUSTED", "APIRateLimitError", "rate"),  # per-minute throttling
    (400, "INVALID_ARGUMENT", "ProviderError", "Bad request"),
    (404, "NOT_FOUND", "ProviderError", "not found"),
    (403, "PERMISSION_DENIED", "ProviderError", "Permission"),
    (500, "INTERNAL", "ProviderError", "server error"),
    (503, "UNAVAILABLE", "ProviderError", "server error"),
])
def test_gemini_error_mapping_table(status_code, status_string, expected_error_class, expected_substr) -> None:
    from google.genai import errors as genai_errors
    from thoth.providers.gemini import _map_gemini_error
    from thoth.errors import APIRateLimitError, APIQuotaError, APIKeyError, ProviderError, ThothError

    fake_exc = genai_errors.ClientError(code=status_code, response_json={"error": {"status": status_string, "message": "test"}}, response=None) \
        if status_code < 500 else \
        genai_errors.ServerError(code=status_code, response_json={"error": {"status": status_string, "message": "test"}}, response=None)

    mapped = _map_gemini_error(fake_exc, "gemini-2.5-flash-lite", verbose=False)
    expected_cls = {
        "ThothError": ThothError,
        "APIKeyError": APIKeyError,
        "APIRateLimitError": APIRateLimitError,
        "APIQuotaError": APIQuotaError,
        "ProviderError": ProviderError,
    }[expected_error_class]
    assert isinstance(mapped, expected_cls), f"expected {expected_cls.__name__}, got {type(mapped).__name__}"
    assert expected_substr.lower() in str(mapped).lower()


def test_gemini_quota_exhausted_per_day_maps_to_apiquotaerror() -> None:
    """429 with 'per day' or quota substring maps to APIQuotaError, not APIRateLimitError."""
    from google.genai import errors as genai_errors
    from thoth.providers.gemini import _map_gemini_error
    from thoth.errors import APIQuotaError

    fake_exc = genai_errors.ClientError(
        code=429,
        response_json={
            "error": {
                "status": "RESOURCE_EXHAUSTED",
                "message": "Quota exceeded for quota metric 'Generate content requests per day'",
                "details": [{"reason": "RATE_LIMIT_EXCEEDED"}],  # daily metric
            }
        },
        response=None,
    )
    mapped = _map_gemini_error(fake_exc, "gemini-2.5-pro", verbose=False)
    assert isinstance(mapped, APIQuotaError)


def test_gemini_invalid_key_thotherror_has_exit_code_2() -> None:
    from google.genai import errors as genai_errors
    from thoth.providers.gemini import _map_gemini_error
    from thoth.errors import ThothError

    fake_exc = genai_errors.ClientError(
        code=401,
        response_json={"error": {"status": "UNAUTHENTICATED", "message": "API key not valid"}},
        response=None,
    )
    mapped = _map_gemini_error(fake_exc, "gemini-2.5-flash-lite", verbose=False)
    assert isinstance(mapped, ThothError)
    assert mapped.exit_code == 2


def test_gemini_invalid_argument_extracts_offending_param() -> None:
    """400 INVALID_ARGUMENT with 'parameter X' extracts X via regex."""
    from google.genai import errors as genai_errors
    from thoth.providers.gemini import _map_gemini_error

    fake_exc = genai_errors.ClientError(
        code=400,
        response_json={
            "error": {
                "status": "INVALID_ARGUMENT",
                "message": "Unsupported parameter 'frequency_penalty' for gemini-2.5-pro",
            }
        },
        response=None,
    )
    mapped = _map_gemini_error(fake_exc, "gemini-2.5-pro", verbose=False)
    assert "frequency_penalty" in str(mapped)


def test_gemini_httpx_timeout_maps_to_provider_error() -> None:
    import httpx
    from thoth.providers.gemini import _map_gemini_error
    from thoth.errors import ProviderError

    fake_exc = httpx.TimeoutException("Request timed out")
    mapped = _map_gemini_error(fake_exc, "gemini-2.5-pro", verbose=False)
    assert isinstance(mapped, ProviderError)
    assert "timed out" in str(mapped).lower() or "timeout" in str(mapped).lower()


def test_gemini_httpx_connect_error_maps_to_provider_error() -> None:
    import httpx
    from thoth.providers.gemini import _map_gemini_error
    from thoth.errors import ProviderError

    fake_exc = httpx.ConnectError("Connection refused")
    mapped = _map_gemini_error(fake_exc, "gemini-2.5-pro", verbose=False)
    assert isinstance(mapped, ProviderError)


def test_gemini_retry_on_transient_succeeds_after_two_timeouts() -> None:
    """Tenacity retries httpx.TimeoutException up to 3 attempts."""
    # Mock submit to raise httpx.TimeoutException twice, then succeed
    # Assert 3 attempts total, last one returns
    pass  # implementation depends on submit() shape (Task 4.5)


def test_gemini_no_retry_on_invalid_key() -> None:
    """ThothError(invalid-key) is non-retryable."""
    pass  # similar mock pattern


def test_gemini_every_error_carries_provider_name() -> None:
    """All mapped ThothError subclasses carry provider='gemini' (the _PROVIDER_NAME_GEMINI constant)."""
    from google.genai import errors as genai_errors
    from thoth.providers.gemini import _map_gemini_error

    for code, status in [(401, "UNAUTHENTICATED"), (429, "RESOURCE_EXHAUSTED"), (400, "INVALID_ARGUMENT")]:
        fake_exc = genai_errors.ClientError(code=code, response_json={"error": {"status": status, "message": "x"}}, response=None)
        mapped = _map_gemini_error(fake_exc, "gemini-2.5-pro", verbose=False)
        assert getattr(mapped, "provider", None) == "gemini" or "gemini" in str(mapped).lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_provider_gemini.py -k error -v`
Expected: FAIL — `_map_gemini_error` does not exist.

- [ ] **Step 3: Implement `_map_gemini_error` and the retry decorator**

In `src/thoth/providers/gemini.py`, add at module level:

```python
import re

import httpx
from google.genai import errors as genai_errors  # type: ignore[import-not-found]
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from thoth.errors import (
    APIKeyError,
    APIQuotaError,
    APIRateLimitError,
    ProviderError,
    ThothError,
)

_INVALID_KEY_PHRASES_GEMINI = (
    "api key not valid",
    "api_key_invalid",
    "invalid api key",
)

_QUOTA_MARKERS_GEMINI = (
    "per day",
    "you exceeded your current quota",
    "free tier",
    "billing",
    "credit",
)


def _is_quota_exhaustion(message: str, details: list[dict[str, Any]] | None) -> bool:
    """Distinguish quota/credits exhaustion from ordinary rate-limiting on a 429."""
    msg_lower = message.lower()
    if any(marker in msg_lower for marker in _QUOTA_MARKERS_GEMINI):
        return True
    if details:
        for entry in details:
            reason = (entry.get("reason") or "").upper()
            if reason in {"FREE_TIER_LIMIT_EXCEEDED", "BILLING_DISABLED"}:
                return True
            if reason == "RATE_LIMIT_EXCEEDED":
                metric = (entry.get("quotaMetric") or entry.get("metric") or "").lower()
                if "per day" in metric or "daily" in metric:
                    return True
    return False


def _map_gemini_error(exc: Exception, model: str | None, verbose: bool = False) -> ThothError:
    """Translate google-genai SDK and httpx exceptions into ThothError subclasses."""
    # ModeKindMismatchError must propagate unmapped — caller filters before this.

    if isinstance(exc, genai_errors.ClientError):
        # Body shape varies; prefer .response_json (newer) over .body
        body = getattr(exc, "response_json", None) or getattr(exc, "body", {}) or {}
        err_obj = (body.get("error") or {}) if isinstance(body, dict) else {}
        message = err_obj.get("message") or str(exc)
        status = (err_obj.get("status") or "").upper()
        details = err_obj.get("details")
        code = exc.code if hasattr(exc, "code") else None

        if code == 401 or status == "UNAUTHENTICATED":
            if any(p in message.lower() for p in _INVALID_KEY_PHRASES_GEMINI):
                return ThothError(
                    "Gemini API key is invalid",
                    hint="Verify the key at https://aistudio.google.com/app/apikey",
                    exit_code=2,
                )
            return APIKeyError(_PROVIDER_NAME_GEMINI)

        if code == 429 or status == "RESOURCE_EXHAUSTED":
            if _is_quota_exhaustion(message, details):
                return APIQuotaError(_PROVIDER_NAME_GEMINI)
            return APIRateLimitError(_PROVIDER_NAME_GEMINI)

        if code == 404 or status == "NOT_FOUND":
            model_str = repr(model) if model else "(unknown)"
            return ProviderError(
                _PROVIDER_NAME_GEMINI,
                f"Model {model_str} not found or unavailable.",
                hint="Run `thoth providers --models --provider gemini` to list valid models.",
            )

        if code == 400 or status in {"INVALID_ARGUMENT", "FAILED_PRECONDITION", "OUT_OF_RANGE"}:
            param_match = re.search(r"'(\w+)'", message)
            if "unsupported" in message.lower() and param_match:
                param = param_match.group(1)
                return ProviderError(
                    _PROVIDER_NAME_GEMINI,
                    f"Gemini does not support parameter {param!r} for this model.",
                )
            return ProviderError(_PROVIDER_NAME_GEMINI, f"Bad request: {message}")

        if code == 403 or status == "PERMISSION_DENIED":
            return ProviderError(
                _PROVIDER_NAME_GEMINI,
                f"Permission denied: {message}",
            )

    if isinstance(exc, genai_errors.ServerError):
        return ProviderError(
            _PROVIDER_NAME_GEMINI,
            f"Gemini server error ({getattr(exc, 'code', '5xx')}). Retry shortly.",
        )

    if isinstance(exc, httpx.TimeoutException):
        return ProviderError(
            _PROVIDER_NAME_GEMINI,
            "Request timed out. Try again, or raise --timeout.",
        )

    if isinstance(exc, (httpx.ConnectError, httpx.RemoteProtocolError, httpx.RequestError)):
        return ProviderError(
            _PROVIDER_NAME_GEMINI,
            "Network connection error reaching the Gemini API.",
        )

    if isinstance(exc, genai_errors.APIError):
        return ProviderError(_PROVIDER_NAME_GEMINI, f"Gemini API error: {exc}")

    return ProviderError(_PROVIDER_NAME_GEMINI, f"Unexpected error: {exc}")


_GEMINI_RETRY_CLASSES = (
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.RemoteProtocolError,
    APIRateLimitError,
)


# Inside GeminiProvider class:
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(_GEMINI_RETRY_CLASSES),
    reraise=True,
)
async def _submit_with_retry(self, ...):
    ...
```

(The retry decorator wraps `_submit_with_retry` once it's implemented in Task 4.5.)

- [ ] **Step 4: Run error tests + commit**

Run: `uv run pytest tests/test_provider_gemini.py -k error -v`
Expected: PASS for the parametrized table + the specific quota/key/argument tests. Retry-count tests stub-passing for now.

```bash
git add src/thoth/providers/gemini.py tests/test_provider_gemini.py
git commit -m "$(cat <<'EOF'
feat(gemini): implement _map_gemini_error 12-class branch

Maps google.genai.errors.{ClientError, ServerError, APIError} and httpx
transport exceptions to Thoth error classes. Distinguishes quota exhaustion
(per-day, free-tier) from ordinary 429 rate-limiting via message + details
heuristic. Sets exit_code=2 on invalid-key. Carries provider="gemini" via
the _PROVIDER_NAME_GEMINI constant.
EOF
)"
```

### Task 4.4: `stream()` translation

Per P24-TS03/T03. Implements the chunk → StreamEvent translator with `Part.thought` reasoning detection and terminal-chunk grounding citations.

- [ ] **Step 1: Write failing stream-translation tests**

Append to `tests/test_provider_gemini.py`:

```python
import asyncio
from types import SimpleNamespace
from typing import AsyncIterator
from unittest.mock import patch


async def _consume_events(stream_iter):
    return [event async for event in stream_iter]


def _make_chunk(parts: list[dict] | None = None, grounding: dict | None = None) -> SimpleNamespace:
    """Build a fake GenerateContentResponse chunk."""
    candidate_parts = []
    for p in parts or []:
        candidate_parts.append(SimpleNamespace(text=p.get("text", ""), thought=p.get("thought", False)))
    candidate = SimpleNamespace(
        content=SimpleNamespace(parts=candidate_parts),
        grounding_metadata=SimpleNamespace(**grounding) if grounding else None,
    )
    return SimpleNamespace(candidates=[candidate], text=" ".join(p.get("text", "") for p in (parts or []) if not p.get("thought")))


def test_gemini_stream_emits_text_for_non_thought_parts() -> None:
    """A chunk with text parts (thought=False) emits StreamEvent('text', text)."""
    from thoth.providers.gemini import GeminiProvider

    fake_chunks = [
        _make_chunk(parts=[{"text": "Hello "}, {"text": "world.", "thought": False}]),
    ]

    async def fake_generator():
        for c in fake_chunks:
            yield c

    with patch("google.genai.Client") as mock_client_cls:
        mock_client = SimpleNamespace()
        mock_client.aio = SimpleNamespace()
        mock_client.aio.models = SimpleNamespace()
        mock_client.aio.models.generate_content_stream = lambda **kw: fake_generator()
        mock_client_cls.return_value = mock_client

        provider = GeminiProvider(api_key="dummy", config={"kind": "immediate"})
        events = asyncio.run(_consume_events(provider.stream("Q?", "test_mode")))

    text_events = [e for e in events if e.kind == "text"]
    assert len(text_events) == 2
    assert text_events[0].text == "Hello "
    assert text_events[1].text == "world."


def test_gemini_stream_emits_reasoning_for_thought_parts() -> None:
    """A part with thought=True emits StreamEvent('reasoning', text)."""
    from thoth.providers.gemini import GeminiProvider

    fake_chunks = [
        _make_chunk(parts=[
            {"text": "Let me think: ", "thought": True},
            {"text": "Answer is 42.", "thought": False},
        ]),
    ]

    async def fake_generator():
        for c in fake_chunks:
            yield c

    with patch("google.genai.Client") as mock_client_cls:
        mock_client = SimpleNamespace()
        mock_client.aio = SimpleNamespace()
        mock_client.aio.models = SimpleNamespace()
        mock_client.aio.models.generate_content_stream = lambda **kw: fake_generator()
        mock_client_cls.return_value = mock_client

        provider = GeminiProvider(api_key="dummy", config={"kind": "immediate"})
        events = asyncio.run(_consume_events(provider.stream("Q?", "test_mode")))

    reasoning = [e for e in events if e.kind == "reasoning"]
    text = [e for e in events if e.kind == "text"]
    assert len(reasoning) == 1
    assert reasoning[0].text == "Let me think: "
    assert len(text) == 1
    assert text[0].text == "Answer is 42."


def test_gemini_stream_emits_citations_from_terminal_grounding_chunks() -> None:
    """grounding_metadata.grounding_chunks emits StreamEvent('citation', Citation(...)) deduped."""
    from thoth.providers.gemini import GeminiProvider
    from thoth.providers.base import Citation

    grounding = {
        "grounding_chunks": [
            SimpleNamespace(web=SimpleNamespace(uri="https://vertexaisearch.cloud.google.com/grounding-api-redirect/AAA", title="example.com")),
            SimpleNamespace(web=SimpleNamespace(uri="https://vertexaisearch.cloud.google.com/grounding-api-redirect/BBB", title="other.com")),
            # duplicate URL — should dedupe
            SimpleNamespace(web=SimpleNamespace(uri="https://vertexaisearch.cloud.google.com/grounding-api-redirect/AAA", title="example.com")),
        ]
    }

    fake_chunks = [
        _make_chunk(parts=[{"text": "Per source A and B."}]),
        _make_chunk(parts=[], grounding=grounding),  # terminal chunk
    ]

    async def fake_generator():
        for c in fake_chunks:
            yield c

    with patch("google.genai.Client") as mock_client_cls:
        mock_client = SimpleNamespace()
        mock_client.aio = SimpleNamespace()
        mock_client.aio.models = SimpleNamespace()
        mock_client.aio.models.generate_content_stream = lambda **kw: fake_generator()
        mock_client_cls.return_value = mock_client

        provider = GeminiProvider(api_key="dummy", config={"kind": "immediate"})
        events = asyncio.run(_consume_events(provider.stream("Q?", "test_mode")))

    citations = [e for e in events if e.kind == "citation"]
    assert len(citations) == 2  # deduped
    assert all(isinstance(e.citation, Citation) for e in citations)
    assert citations[0].citation.url.startswith("https://vertexaisearch")


def test_gemini_stream_terminal_done_event() -> None:
    """Stream always ends with StreamEvent('done', '')."""
    from thoth.providers.gemini import GeminiProvider

    async def fake_generator():
        yield _make_chunk(parts=[{"text": "Hi."}])

    with patch("google.genai.Client") as mock_client_cls:
        mock_client = SimpleNamespace()
        mock_client.aio = SimpleNamespace()
        mock_client.aio.models = SimpleNamespace()
        mock_client.aio.models.generate_content_stream = lambda **kw: fake_generator()
        mock_client_cls.return_value = mock_client

        provider = GeminiProvider(api_key="dummy", config={"kind": "immediate"})
        events = asyncio.run(_consume_events(provider.stream("Q?", "test_mode")))

    assert events[-1].kind == "done"
    assert events[-1].text == ""


def test_gemini_stream_title_falls_back_to_netloc_when_empty() -> None:
    """Citation.title = urlparse(uri).netloc when web.title is missing/empty."""
    from urllib.parse import urlparse
    from thoth.providers.gemini import GeminiProvider

    grounding = {
        "grounding_chunks": [
            SimpleNamespace(web=SimpleNamespace(uri="https://example.com/path", title="")),
        ]
    }

    async def fake_generator():
        yield _make_chunk(parts=[], grounding=grounding)

    with patch("google.genai.Client") as mock_client_cls:
        mock_client = SimpleNamespace()
        mock_client.aio = SimpleNamespace()
        mock_client.aio.models = SimpleNamespace()
        mock_client.aio.models.generate_content_stream = lambda **kw: fake_generator()
        mock_client_cls.return_value = mock_client

        provider = GeminiProvider(api_key="dummy", config={"kind": "immediate"})
        events = asyncio.run(_consume_events(provider.stream("Q?", "test_mode")))

    citations = [e for e in events if e.kind == "citation"]
    assert citations[0].citation.title == "example.com"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_provider_gemini.py -k stream -v`
Expected: FAIL — `stream()` not implemented.

- [ ] **Step 3: Implement `stream()`**

In `src/thoth/providers/gemini.py`, add the method:

```python
from typing import AsyncIterator
from urllib.parse import urlparse

from thoth.providers.base import Citation


async def stream(
    self,
    prompt: str,
    mode: str,
    system_prompt: str | None = None,
    verbose: bool = False,
) -> AsyncIterator[StreamEvent]:
    """Yield StreamEvents translated from google-genai chunks."""
    self._validate_kind_for_model(mode)  # implemented in Task 4.6

    contents, system = self._build_messages_and_system(prompt, system_prompt)
    config = self._build_generate_content_config()

    seen_citation_urls: set[str] = set()

    try:
        kwargs = {"model": self.model, "contents": contents}
        if config is not None:
            kwargs["config"] = config
        if system:
            # system_instruction lives on config; rebuild if config is None
            if config is None:
                from google.genai import types
                kwargs["config"] = types.GenerateContentConfig(system_instruction=system)
            else:
                config.system_instruction = system

        async for chunk in await self.client.aio.models.generate_content_stream(**kwargs):
            candidate = chunk.candidates[0] if chunk.candidates else None
            if candidate is None:
                continue
            parts = getattr(candidate.content, "parts", None) if candidate.content else None
            if parts:
                for part in parts:
                    text = getattr(part, "text", "") or ""
                    if not text:
                        continue
                    if getattr(part, "thought", False):
                        yield StreamEvent(kind="reasoning", text=text)
                    else:
                        yield StreamEvent(kind="text", text=text)

            grounding = getattr(candidate, "grounding_metadata", None)
            if grounding is not None:
                grounding_chunks = getattr(grounding, "grounding_chunks", None) or []
                for gc in grounding_chunks:
                    web = getattr(gc, "web", None)
                    if web is None:
                        continue
                    url = getattr(web, "uri", None)
                    if not url or url in seen_citation_urls:
                        continue
                    seen_citation_urls.add(url)
                    title = getattr(web, "title", "") or urlparse(url).netloc
                    yield StreamEvent(kind="citation", citation=Citation(title=title, url=url))

        yield StreamEvent(kind="done", text="")

    except (genai_errors.APIError, httpx.HTTPError, Exception) as e:
        if isinstance(e, ModeKindMismatchError):  # propagate unmapped
            raise
        raise _map_gemini_error(e, self.model, verbose=verbose) from e
```

(Add `from thoth.errors import ModeKindMismatchError` import at the top.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_provider_gemini.py -k stream -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/thoth/providers/gemini.py tests/test_provider_gemini.py
git commit -m "$(cat <<'EOF'
feat(gemini): implement stream() with Part.thought reasoning + grounding citations

stream() translates google-genai chunks into StreamEvents:
- Part.thought=True parts -> StreamEvent("reasoning", text)
- Other text parts -> StreamEvent("text", text)
- Terminal-chunk grounding_metadata.grounding_chunks -> deduped citation events
- End-of-stream -> StreamEvent("done", "")

Citation title falls back to urlparse(uri).netloc when web.title is empty.
Uses Vertex redirect URLs verbatim (per Resolved Design Decision in P24).
EOF
)"
```

### Task 4.5: Non-stream (`submit` / `check_status` / `get_result`)

Per P24-TS05/T05.

- [ ] **Step 1: Write failing tests for submit/get_result**

Append to `tests/test_provider_gemini.py`:

```python
def test_gemini_submit_returns_job_id() -> None:
    """submit() runs a one-shot generate_content and stashes the response under a job_id."""
    from thoth.providers.gemini import GeminiProvider

    fake_response = SimpleNamespace(
        candidates=[SimpleNamespace(
            content=SimpleNamespace(parts=[SimpleNamespace(text="Answer.", thought=False)]),
            grounding_metadata=None,
        )],
        text="Answer.",
    )

    async def fake_generate_content(**kw):
        return fake_response

    with patch("google.genai.Client") as mock_client_cls:
        mock_client = SimpleNamespace()
        mock_client.aio = SimpleNamespace()
        mock_client.aio.models = SimpleNamespace()
        mock_client.aio.models.generate_content = fake_generate_content
        mock_client_cls.return_value = mock_client

        provider = GeminiProvider(api_key="dummy", config={"kind": "immediate"})
        job_id = asyncio.run(provider.submit("Q?", "test_mode"))

    assert job_id.startswith("gemini-")
    assert job_id in provider.jobs


def test_gemini_get_result_renders_text_reasoning_sources() -> None:
    """get_result extracts text + ## Reasoning + ## Sources with sanitization."""
    from thoth.providers.gemini import GeminiProvider

    grounding = SimpleNamespace(
        grounding_chunks=[
            SimpleNamespace(web=SimpleNamespace(uri="https://example.com", title="example.com")),
        ]
    )
    fake_response = SimpleNamespace(
        candidates=[SimpleNamespace(
            content=SimpleNamespace(parts=[
                SimpleNamespace(text="Reasoning bit. ", thought=True),
                SimpleNamespace(text="Final answer.", thought=False),
            ]),
            grounding_metadata=grounding,
        )],
        text="Final answer.",
    )

    provider = GeminiProvider(api_key="dummy", config={"kind": "immediate"})
    provider.jobs["test"] = {"response": fake_response, "created_at": 0}

    rendered = asyncio.run(provider.get_result("test"))
    assert "Final answer." in rendered
    assert "## Reasoning" in rendered
    assert "Reasoning bit." in rendered
    assert "## Sources" in rendered
    assert "[example.com](https://example.com)" in rendered


def test_gemini_get_result_sanitizes_adversarial_citation() -> None:
    """Adversarial title HTML and javascript: URLs are neutralized via md_link_*."""
    from thoth.providers.gemini import GeminiProvider

    grounding = SimpleNamespace(
        grounding_chunks=[
            SimpleNamespace(web=SimpleNamespace(uri="javascript:alert(1)", title="<script>x</script>")),
        ]
    )
    fake_response = SimpleNamespace(
        candidates=[SimpleNamespace(
            content=SimpleNamespace(parts=[SimpleNamespace(text="Body.", thought=False)]),
            grounding_metadata=grounding,
        )],
        text="Body.",
    )

    provider = GeminiProvider(api_key="dummy", config={"kind": "immediate"})
    provider.jobs["test"] = {"response": fake_response, "created_at": 0}

    rendered = asyncio.run(provider.get_result("test"))
    assert "<script>" not in rendered
    assert "javascript:" not in rendered
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_provider_gemini.py -k "submit or get_result" -v`
Expected: FAIL — methods not implemented.

- [ ] **Step 3: Implement submit / check_status / get_result**

In `src/thoth/providers/gemini.py`:

```python
import time
import uuid

from thoth.utils import md_link_title, md_link_url


async def submit(
    self,
    prompt: str,
    mode: str,
    system_prompt: str | None = None,
    verbose: bool = False,
) -> str:
    """One-shot non-stream generate_content. Stashes response under a job_id."""
    self._validate_kind_for_model(mode)

    try:
        response = await self._submit_with_retry(prompt, mode, system_prompt, verbose)
    except ModeKindMismatchError:
        raise
    except Exception as e:
        raise _map_gemini_error(e, self.model, verbose=verbose) from e

    job_id = getattr(response, "id", None) or f"gemini-{time.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
    self.jobs[job_id] = {"response": response, "created_at": time.time()}
    return job_id


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(_GEMINI_RETRY_CLASSES),
    reraise=True,
)
async def _submit_with_retry(self, prompt, mode, system_prompt, verbose):
    contents, system = self._build_messages_and_system(prompt, system_prompt)
    config = self._build_generate_content_config()
    kwargs: dict[str, Any] = {"model": self.model, "contents": contents}
    if config is not None:
        kwargs["config"] = config
    if system:
        if config is None:
            from google.genai import types
            kwargs["config"] = types.GenerateContentConfig(system_instruction=system)
        else:
            config.system_instruction = system
    return await self.client.aio.models.generate_content(**kwargs)


async def check_status(self, job_id: str) -> dict[str, Any]:
    if job_id not in self.jobs:
        return {"status": "not_found", "error": f"Unknown job_id: {job_id}"}
    return {"status": "completed", "progress": 1.0}


async def get_result(self, job_id: str, verbose: bool = False) -> str:
    if job_id not in self.jobs:
        raise ProviderError(_PROVIDER_NAME_GEMINI, f"Unknown job_id: {job_id}")

    response = self.jobs[job_id]["response"]
    candidate = response.candidates[0] if response.candidates else None
    if candidate is None or candidate.content is None:
        if verbose:
            self._debug_print_empty_response(response)
        return ""

    text_parts: list[str] = []
    thought_parts: list[str] = []
    for part in candidate.content.parts or []:
        text = getattr(part, "text", "") or ""
        if not text:
            continue
        if getattr(part, "thought", False):
            thought_parts.append(text)
        else:
            text_parts.append(text)

    answer = "".join(text_parts).strip()
    if not answer and verbose:
        self._debug_print_empty_response(response)

    sources = self._render_sources(getattr(candidate, "grounding_metadata", None))
    reasoning = "\n".join(thought_parts).strip()

    sections: list[str] = []
    if reasoning:
        sections.append(f"## Reasoning\n\n{reasoning}")
    if answer:
        sections.append(answer)
    if sources:
        sections.append(sources)
    return "\n\n".join(sections)


def _render_sources(self, grounding_metadata: Any) -> str:
    if grounding_metadata is None:
        return ""
    chunks = getattr(grounding_metadata, "grounding_chunks", None) or []
    seen: set[str] = set()
    lines: list[str] = []
    for gc in chunks:
        web = getattr(gc, "web", None)
        if web is None:
            continue
        url = getattr(web, "uri", None)
        if not url or url in seen:
            continue
        seen.add(url)
        title = getattr(web, "title", "") or urlparse(url).netloc
        lines.append(f"- [{md_link_title(title)}]({md_link_url(url)})")
    if not lines:
        return ""
    return "## Sources\n\n" + "\n".join(lines)


def _debug_print_empty_response(self, response: Any) -> None:
    """Mirror Perplexity's empty-content debug ladder (and OpenAI's pattern)."""
    import sys
    from rich.console import Console
    err_console = Console(file=sys.stderr)
    err_console.print("[yellow]Gemini: empty content in response. Debug:[/yellow]")
    try:
        if hasattr(response, "model_dump_json"):
            err_console.print(response.model_dump_json(indent=2))
        elif hasattr(response, "__dict__"):
            err_console.print(response.__dict__)
        else:
            err_console.print(repr(response))
    except Exception:
        err_console.print(repr(response))
```

- [ ] **Step 4: Run tests + commit**

Run: `uv run pytest tests/test_provider_gemini.py -k "submit or get_result" -v`
Expected: PASS.

```bash
git add src/thoth/providers/gemini.py tests/test_provider_gemini.py
git commit -m "$(cat <<'EOF'
feat(gemini): implement submit/check_status/get_result with retry

submit() does one-shot generate_content via tenacity-retried _submit_with_retry.
get_result() extracts answer text, separates thought parts into ## Reasoning,
renders ## Sources via md_link_title/md_link_url sanitization helpers.
check_status() returns completed for known job_ids (immediate path).
EOF
)"
```

### Task 4.6: Kind-mismatch guard

Per P24-TS06/T06.

- [ ] **Step 1: Write failing tests**

Append to `tests/test_provider_gemini.py`:

```python
def test_gemini_kind_mismatch_rejects_deep_research_in_immediate() -> None:
    """deep-research-pro-preview-12-2025 with kind=immediate must raise ModeKindMismatchError."""
    from thoth.providers.gemini import GeminiProvider
    from thoth.errors import ModeKindMismatchError

    provider = GeminiProvider(
        api_key="dummy",
        config={"kind": "immediate", "model": "deep-research-pro-preview-12-2025"},
    )
    with pytest.raises(ModeKindMismatchError):
        asyncio.run(provider.submit("Q?", "test_mode"))


def test_gemini_kind_mismatch_allows_regular_models() -> None:
    """gemini-2.5-pro with kind=immediate is allowed."""
    from thoth.providers.gemini import GeminiProvider

    provider = GeminiProvider(
        api_key="dummy",
        config={"kind": "immediate", "model": "gemini-2.5-pro"},
    )
    # Validation should pass (no exception)
    provider._validate_kind_for_model("test_mode")  # direct call


def test_gemini_kind_mismatch_no_http_call_before_raise() -> None:
    """ModeKindMismatchError fires BEFORE any HTTP attempt."""
    from thoth.providers.gemini import GeminiProvider
    from thoth.errors import ModeKindMismatchError
    from unittest.mock import MagicMock

    captured = {"called": False}

    async def fake_generate_content_stream(**kw):
        captured["called"] = True
        yield SimpleNamespace()

    with patch("google.genai.Client") as mock_client_cls:
        mock_client = SimpleNamespace()
        mock_client.aio = SimpleNamespace()
        mock_client.aio.models = SimpleNamespace()
        mock_client.aio.models.generate_content_stream = fake_generate_content_stream
        mock_client.aio.models.generate_content = MagicMock()
        mock_client_cls.return_value = mock_client

        provider = GeminiProvider(
            api_key="dummy",
            config={"kind": "immediate", "model": "deep-research-pro-preview-12-2025"},
        )
        with pytest.raises(ModeKindMismatchError):
            async def consume():
                async for _ in provider.stream("Q?", "test_mode"):
                    pass
            asyncio.run(consume())

    assert captured["called"] is False, "stream API was called despite kind-mismatch"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_provider_gemini.py -k kind -v`
Expected: FAIL — `_validate_kind_for_model` not implemented.

- [ ] **Step 3: Implement `_validate_kind_for_model`**

In `src/thoth/providers/gemini.py`, add to the class body:

```python
def _validate_kind_for_model(self, mode: str) -> None:
    """Mirror openai.py:160-180 / perplexity.py:253-266."""
    from thoth.errors import ModeKindMismatchError
    from thoth.config import is_background_model

    declared_kind = (self.config or {}).get("kind")
    if declared_kind == "immediate" and is_background_model(self.model):
        raise ModeKindMismatchError(
            mode_name=mode,
            model=self.model,
            declared_kind="immediate",
            required_kind="background",
        )
```

Verify `thoth.config.is_background_model` recognizes `deep-research-pro-preview-12-2025` (substring match on `"deep-research"` should already cover it; if not, update its allowlist in a separate small commit).

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_provider_gemini.py -k kind -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/thoth/providers/gemini.py tests/test_provider_gemini.py
git commit -m "feat(gemini): implement kind-mismatch guard for *-deep-research-* models"
```

### Phase 4 gate

- [ ] **Run periodic full gate**:
  ```
  just check
  uv run ruff format --check src/ tests/
  uv run pytest -q
  ./thoth_test -r --skip-interactive -q
  ```
- [ ] Verify Gemini provider unit tests pass without external API calls.

---

## Phase 5 — Gemini surface + CI

### Task 5.1: Provider registry + `--api-key-gemini` plumbing

Per P24-TS07/T07/TS08/T08.

- [ ] **Step 1: Write failing CLI + registry tests**

In `tests/test_provider_config.py` add:

```python
def test_create_provider_returns_gemini_when_provider_is_gemini() -> None:
    from thoth.providers import create_provider

    provider = create_provider("gemini", api_key="dummy", config={})
    from thoth.providers.gemini import GeminiProvider
    assert isinstance(provider, GeminiProvider)


def test_provider_env_vars_includes_gemini() -> None:
    from thoth.providers import PROVIDER_ENV_VARS
    assert PROVIDER_ENV_VARS.get("gemini") == "GEMINI_API_KEY"
```

In `tests/test_cli_option_policy.py` add:

```python
def test_api_key_gemini_accepted_by_research_commands() -> None:
    from click.testing import CliRunner
    from thoth.cli import main

    runner = CliRunner()
    # Test that --api-key-gemini ... ask "..." doesn't error on parse
    result = runner.invoke(main, ["--api-key-gemini", "dummy-key", "modes"])
    assert result.exit_code == 0 or "modes" in result.output.lower()


def test_api_key_gemini_rejected_by_non_research_subcommands() -> None:
    """Per inherited root-option policy."""
    # Adapt from existing --api-key-perplexity policy test
    pass  # implementation matches P23-R02 pattern
```

- [ ] **Step 2: Run tests to verify they fail**

Expected: FAIL — Gemini not registered, `--api-key-gemini` not present.

- [ ] **Step 3: Register Gemini in `src/thoth/providers/__init__.py`**

Add the import and the registry entries:

```python
from thoth.providers.gemini import GeminiProvider

PROVIDERS["gemini"] = GeminiProvider
PROVIDER_ENV_VARS["gemini"] = "GEMINI_API_KEY"
```

- [ ] **Step 4: Add `--api-key-gemini` to `_options.py`**

Mirror `--api-key-perplexity`'s definition exactly. The flag must be in the shared option stack used by research commands AND in the inherited root-option policy whitelist.

- [ ] **Step 5: Thread the flag through `cli.py`, `cli_subcommands/ask.py`, `run.py`, `create_provider()`**

Mirror the P23 commit's plumbing pattern (commits referenced in `projects/P23-perplexity-immediate-sync.md` task TS01/T01). The exact lines are visible in `git log --oneline -- src/thoth/cli.py src/thoth/cli_subcommands/ask.py` filtered to P23 commits.

- [ ] **Step 6: Update `src/thoth/help.py`** — add `[providers.gemini]` block to auth help (mirror the `[providers.openai]` and `[providers.perplexity]` blocks).

- [ ] **Step 7: Update provider description copy in `src/thoth/commands.py` and `src/thoth/interactive.py`** — replace any "Gemini (not implemented)" copy with the new description (e.g., "Gemini 2.5 (web-grounded synchronous search with optional thinking)").

- [ ] **Step 8: Regenerate `tests/baselines/providers_list.json`**

Run the provider-list command and capture the output:
```bash
uv run python -c "from thoth.commands import _list_providers_json; import json; print(json.dumps(_list_providers_json(), indent=2))" > tests/baselines/providers_list.json
```
(Adjust command per the actual provider-list snapshot generation pattern.)

- [ ] **Step 9: Extend `assert_no_secret_leaked` in `tests/extended/conftest.py`** to redact `GEMINI_API_KEY`.

- [ ] **Step 10: Run targeted tests + commit**

Run: `uv run pytest tests/test_provider_config.py tests/test_cli_option_policy.py tests/test_provider_gemini.py -v`
Expected: PASS.

```bash
git add src/thoth/providers/__init__.py src/thoth/cli.py src/thoth/cli_subcommands/_options.py src/thoth/cli_subcommands/ask.py src/thoth/cli_subcommands/_option_policy.py src/thoth/run.py src/thoth/help.py src/thoth/commands.py src/thoth/interactive.py tests/baselines/providers_list.json tests/extended/conftest.py tests/test_provider_config.py tests/test_cli_option_policy.py
git commit -m "$(cat <<'EOF'
feat(gemini): register provider, add --api-key-gemini CLI plumbing

Registers GeminiProvider in PROVIDERS and PROVIDER_ENV_VARS["gemini"]="GEMINI_API_KEY".
Adds --api-key-gemini to the shared option surface and root-option policy
whitelist (mirrors --api-key-perplexity from P23). Updates auth help, provider
descriptions, and the provider-list snapshot. Extends secret-redaction in
tests/extended/conftest.py to cover GEMINI_API_KEY.
EOF
)"
```

### Task 5.2: Extended + live_api coverage

Per P24-TS09/T09.

- [ ] **Step 1: Add `live_gemini_env` fixture and `require_gemini_key` helper to `tests/extended/conftest.py`**

Mirror `live_perplexity_env` exactly.

- [ ] **Step 2: Create `tests/extended/test_gemini_real_workflows.py`**

Mirror `tests/extended/test_perplexity_real_workflows.py` from P23. Cover:
- `--api-key-gemini sk-... ask "..."` with stream default
- `--provider gemini --model gemini-2.5-flash-lite` passthrough
- `--mode gemini_quick`
- `--mode gemini_reasoning` (verify `## Reasoning` block appears)
- tee `--out -,FILE`

All decorated with `@pytest.mark.live_api` and `require_gemini_key`.

- [ ] **Step 3: Update workflow YAMLs**

In `.github/workflows/extended.yml` and `.github/workflows/live-api.yml`, add to the env block (alongside `OPENAI_API_KEY` and `PERPLEXITY_API_KEY`):

```yaml
GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
```

- [ ] **Step 4: Update `tests/extended/test_model_kind_runtime.py`**

If there's an explicit Gemini skip block, remove it. The 3 new modes auto-derive into `KNOWN_MODELS` from `BUILTIN_MODES` (per P23-T09 precedent).

- [ ] **Step 5: Add CI-wiring sentinel test**

In a new file `tests/test_p24_ci_wiring.py`, parse the workflow YAMLs (NOT substring-scan, per P23-R10) and assert `GEMINI_API_KEY` is in both env blocks. Use `yaml.safe_load`.

- [ ] **Step 6: Commit**

```bash
git add tests/extended/conftest.py tests/extended/test_gemini_real_workflows.py tests/extended/test_model_kind_runtime.py .github/workflows/extended.yml .github/workflows/live-api.yml tests/test_p24_ci_wiring.py
git commit -m "$(cat <<'EOF'
ci(gemini): wire GEMINI_API_KEY into extended + live-api workflows

Adds extended/live_api Gemini coverage mirroring the P23 Perplexity pattern:
test_gemini_real_workflows.py for end-to-end CLI behavior, live_gemini_env
fixture, GEMINI_API_KEY secret in both gated workflows, YAML-parsed sentinel
test (per P23-R10).
EOF
)"
```

### Phase 5 gate

- [ ] **Run periodic full gate**:
  ```
  just check
  uv run ruff format --check src/ tests/
  uv run pytest -q
  ./thoth_test -r --skip-interactive -q
  ```

---

## Phase 6 — Audits + investigations

### Task 6.1: OpenAI Responses API streaming-events audit (T13)

Per P24-TS12/T13.

- [ ] **Step 1: Empirical audit**

Either record a live stream from `openai.AsyncOpenAI(...).responses.stream(...)` against a model that produces reasoning summaries (e.g., `o3-mini` or `gpt-4o`), OR consult the Responses API streaming-events documentation. Determine:
1. Does the stream emit a `response.reasoning_summary.delta` (or similar) event type?
2. Does the stream emit annotations as `response.output_text.annotation` (or similar) events?

Document findings in `planning/p24-openai-stream-audit.v1.md` with concrete event-type names.

- [ ] **Step 2: Branch on outcome**

**If reasoning + citation events ARE emitted during stream:**

- [ ] Step 2a: Write failing tests asserting `OpenAIProvider.stream()` emits `StreamEvent("reasoning", ...)` and `StreamEvent("citation", Citation(...))` for the documented event types.
- [ ] Step 2b: Update `openai.py:455-466`'s `stream()` event-dispatch loop to handle the new event types.
- [ ] Step 2c: Run tests + commit `feat(openai): emit reasoning + citation events during stream`.

**If they are NOT emitted (or the audit is inconclusive):**

- [ ] Step 2a: Write a test asserting `OpenAIProvider.stream()` continues to emit only `text + done` (regression lock — prevents accidentally extending the stream's event set in the future without revisiting this audit).
- [ ] Step 2b: Document the limitation in P24's `### Provider-specific deltas vs unified target surface` section.
- [ ] Step 2c: Run tests + commit `docs(openai): document Responses-API stream-event limitations as intentional`.

### Task 6.2: `[providers.X]` root-namespace investigation (T17)

Per P24-TS16/T17.

- [ ] **Step 1: Write failing tests defining the desired behavior**

In `tests/test_provider_config.py` add tests where `config["openai"]["temperature"] = 0.3` (root namespace) flows to the provider as default when no mode-level `[modes.X.openai].temperature` exists; mode-level value wins when both exist.

- [ ] **Step 2: Run tests to verify they fail**

Expected: FAIL — root-namespace passthrough not implemented.

- [ ] **Step 3: Investigation report**

Create `planning/p24-providers-root-namespace-investigation.v1.md` covering:
- Current `[providers.X]` scaffold scope (only `api_key`).
- Resolution chain: root `[providers.X]` defaults → mode-level `[modes.Y.X]` overrides.
- Risks (which keys should NOT propagate root-level — e.g., `kind`, `model`).
- Implementation sketch in `create_provider()`.
- Decision: SHIP in P24, or PUNT to a successor project?

- [ ] **Step 4: If decision is SHIP**

Implement the resolution layering in `create_provider()` (or wherever provider construction happens). Make P24-TS16 pass. Commit.

- [ ] **Step 4-alt: If decision is PUNT**

Mark `tests/test_provider_config.py`'s root-namespace tests with `@pytest.mark.skip(reason="P24-T17 deferred: see planning/p24-providers-root-namespace-investigation.v1.md")`. Mark TS16/T17 in the project file as `[-]` (decided not to do here). Add a follow-up project via `project-add` tooling. Commit.

### Phase 6 gate

- [ ] Run targeted tests for whichever T13/T17 outcomes were chosen.

---

## Phase 7 — Closeout

### Task 7.1: Documentation polish + final gate

- [ ] **Step 1: Update P24's project file**

Flip TS01–TS17 + T01–T17 checkboxes from `[ ]` to `[x]` for the items that landed. Update the trunk row in `PROJECTS.md` from `[ ]` to `[~]` (after first commit on this branch — likely already done) and to `[x]` once the full gate passes.

- [ ] **Step 2: Run the full pre-commit gate**

```
make env-check
just fix
just check
./thoth_test -r --skip-interactive -q
just test-fix
just test-lint
just test-typecheck
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run pytest -q
```

All must pass.

- [ ] **Step 3: Manually run the live Gemini test if `GEMINI_API_KEY` is set**

```bash
uv run pytest -m live_api tests/extended/test_gemini_real_workflows.py -v
```

(Or defer to weekly CI run.)

- [ ] **Step 4: Final commit and trunk flip**

```bash
git add projects/P24-gemini-immediate-sync.md PROJECTS.md
git commit -m "$(cat <<'EOF'
chore(p24): close out P24 — Gemini immediate + cross-provider consistency

All TS/T tasks complete. Trunk flipped to [x]. Full pre-commit gate green:
ruff, ty, pytest, thoth_test all pass with all three providers normalized to
the unified canonical surface.
EOF
)"
```

- [ ] **Step 5: Open PR**

```bash
git push -u origin p24-gemini-immediate-sync
gh pr create --title "feat(gemini): synchronous chat provider + cross-provider consistency (P24)" --body "$(cat <<'EOF'
## Summary
- Adds Gemini synchronous chat provider via google-genai>=1.74.0.
- Normalizes OpenAI and Perplexity to a unified canonical surface (suffix-named module constants, [modes.X.<provider>] namespace, md_link_* sanitization, exit_code=2 on auth-invalid, NotFoundError + offending-parameter regex extraction across both, empty-content debug-print on Perplexity).
- Updates extended + live_api CI workflows with GEMINI_API_KEY.
- Includes consolidation spec at planning/p24-immediate-providers-consolidation.v1.md.

## Test plan
- [ ] `just check` passes
- [ ] `uv run pytest -q` passes (full default suite)
- [ ] `./thoth_test -r --skip-interactive -q` passes
- [ ] Manual `thoth ask --mode gemini_quick "What's new in CRISPR?"` returns grounded answer with ## Sources
- [ ] Manual `thoth ask --mode gemini_reasoning "..."` shows ## Reasoning section
- [ ] Manual `thoth ask --provider gemini --model deep-research-pro-preview-12-2025 "x"` raises ModeKindMismatchError before any HTTP call
- [ ] OpenAI namespace migration: existing flat-key configs still work + emit DeprecationWarning
EOF
)"
```

---

## Self-review

**Spec coverage** — every TS/T pair in `projects/P24-gemini-immediate-sync.md` is mapped to a Phase task above:

| Project task | Plan location |
|---|---|
| TS01/T01 (built-in modes + request construction + `_DIRECT_SDK_KEYS_GEMINI` + `_PROVIDER_NAME_GEMINI`) | Phase 4 Task 4.1 + 4.2 |
| TS02/T02 (`_map_gemini_error` 12-class + retry) | Phase 4 Task 4.3 |
| TS03/T03 (stream chunk translation) | Phase 4 Task 4.4 |
| TS04/T04 (executor regression for Gemini event shapes) | Implicit — covered by Tasks 4.4, 4.5 since `_execute_immediate` is unchanged from P23 |
| TS05/T05 (`stream = false` non-stream + sanitization) | Phase 4 Task 4.5 |
| TS06/T06 (kind-mismatch guard) | Phase 4 Task 4.6 |
| TS07/T07 (`--api-key-gemini` plumbing) | Phase 5 Task 5.1 |
| TS08/T08 (provider registry surface flip + snapshot) | Phase 5 Task 5.1 |
| TS09/T09 (extended + live_api coverage) | Phase 5 Task 5.2 |
| T10 (closeout) | Phase 7 Task 7.1 |
| TS10/T11 (OpenAI namespace migration + deprecation) | Phase 3 Task 3.1; constants from Phase 1 Task 1.2 |
| TS11/T12 (OpenAI Sources sanitization) | Phase 2 Task 2.1 |
| TS12/T13 (OpenAI Responses API streaming audit) | Phase 6 Task 6.1 |
| TS13/T14 (OpenAI auth-invalid `exit_code=2`) | Phase 2 Task 2.2 |
| TS14/T15 (Perplexity rename + NotFoundError + regex extraction + helper decision) | Phase 1 Task 1.1 (rename) + Phase 2 Task 2.3 (NotFoundError) + Phase 2 Task 2.4 (regex + helper) |
| TS15/T16 (Perplexity empty-content debug) | Phase 2 Task 2.5 |
| TS16/T17 (`[providers.X]` root-namespace investigation) | Phase 6 Task 6.2 |

**Placeholder scan**: searched plan for "TBD", "TODO", "implement later", "fill in details". Two occurrences in Phase 4 Task 4.2 Step 2 (test placeholders that "depend on" Task 4.4 output) — these are intentional cross-references, not skipped work. The actual test code is in Tasks 4.4 and 4.5. Acceptable.

**Type consistency**: `_PROVIDER_NAME_<X>` and `_DIRECT_SDK_KEYS_<X>` consistent across all phases. `_map_<provider>_error(exc, model, verbose)` signature consistent. `StreamEvent` kind values (`text` / `reasoning` / `citation` / `done`) match `base.py:24-48` literal type. `Citation(title, url)` constructor matches `base.py:24` dataclass.

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-03-p24-gemini-immediate-and-cross-provider-consistency.md`. Two execution options:

**1. Subagent-Driven (recommended)** — REQUIRED SUB-SKILL: `superpowers:subagent-driven-development`. Fresh subagent per task + two-stage review between tasks; fast iteration; main context stays clean.

**2. Inline Execution** — REQUIRED SUB-SKILL: `superpowers:executing-plans`. Batch execution in this session with checkpoints; main context tracks all decisions.

**Which approach?**
