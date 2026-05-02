# P36: Uniform `--help` + Useful API-Key Errors Implementation Plan

**References**
- **Project:** [projects/P36-help-uniform-errors.md](../../../projects/P36-help-uniform-errors.md) — P36 project file (scope, tasks, verification — canonical)
- **Trunk:** [PROJECTS.md](../../../PROJECTS.md)
- **Code:**
  - `src/thoth/help.py:109-137` (ThothGroup.invoke, the dispatch fix surface)
  - `src/thoth/errors.py:45-64` (APIKeyError, the message surface)
  - `src/thoth/providers/__init__.py:25-65` (PROVIDERS, PROVIDER_ENV_VARS, resolve_api_key)
  - `src/thoth/run.py:272-294` (provider-selection fallback)

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `--help` work uniformly across the CLI (regardless of whether the command is registered), and replace the misleading "openai API key not found" error that surfaces for unknown commands with a clear "unknown command" error + did-you-mean suggestion. Additionally, when the runner does need a provider key, surface a useful error that enumerates all input channels and shows status of every provider's keys, and pick any-provider-with-key as the default rather than hardcoding "openai."

**Architecture:** Three orthogonal layers, each its own subagent-driven cycle:

- **Layer 1** — Dispatch fix in `ThothGroup.invoke`. Short-circuit `--help`/`-h` before the bare-prompt fallback; reject single-token unrecognized commands with a structured "unknown command" error including a fuzzy + curated suggestion plus the full top-level command listing.
- **Layer 2** — `APIKeyError` message enhancement. Enumerate all three input channels (env var, `--api-key-*` CLI flag, config file syntax). Show every provider's env-var status, not just the failing one. Preserve the title-line substring `"{provider} API key not found"` so existing assertions stay green.
- **Layer 3** — Multi-provider default fallback in `run.py`. Add `available_providers(config) -> list[str]` helper that returns providers with resolvable keys (no exception). When no `--provider` is specified and no mode-specific provider is set, pick from available providers, honoring `general.default_provider` if set. Only fall back to "openai" + Layer 2's enhanced error when zero providers have keys.

**Tech Stack:** Python 3.11+, Click, pytest. Reuses existing `format_config_context` helper, `PROVIDER_ENV_VARS` registry, `resolve_api_key` resolver.

**Source of truth:** The P36 section of `projects/P36-help-uniform-errors.md`. If this plan and the project file disagree, the project file wins.

---

## Context

Running `uv run thoth profiles --help` currently fails with:

```
Error: openai API key not found
Suggestion: Set OPENAI_API_KEY (or edit /Users/stevemorin/.config/thoth/thoth.config.toml)
  Config file: /Users/stevemorin/.config/thoth/thoth.config.toml  (exists)
  Env checked: OPENAI_API_KEY (unset)
```

Three layered bugs cause this:

1. **`profiles` is not a top-level command** (it's `config profiles`). `ThothGroup.invoke` (`src/thoth/help.py:109-137`) has three dispatch paths: registered subcommand → builtin mode → bare-prompt fallback. The bare-prompt fallback greedily accepts ANY unrecognized first-arg, including obvious typos.

2. **`--help` is not in the bare-prompt parser's flag table** (`src/thoth/cli.py:250-266`), so `--help` flows through as a positional and becomes part of the "research prompt."

3. **The default provider is hardcoded to "openai"** at `src/thoth/run.py:280`. The bare-prompt fallback then tries to instantiate the OpenAI provider, which fails on the missing `OPENAI_API_KEY` even though the user has other providers configured.

The user-visible result: a help command for an unknown subcommand emits a misleading API-key error instead of "unknown command" or the help text. This violates the principle of least surprise (`bash: foo: command not found` ≫ `Error: openai API key not found`).

A diagnostic finding worth flagging: `tests/baselines/unknown_command.json` literally pins the current broken behavior — its `stdout` field contains the API-key error for an unknown command. The test infrastructure already covers this dispatch surface; it just snapshot-tested the symptom rather than fixing the cause.

---

## Pre-flight (already complete)

- [x] **P0.1**: Worktree created at `/Users/stevemorin/c/thoth-worktrees/help-uniform-errors` on branch `help-uniform-errors`, branched from `origin/main` at `582853b` (P12 squash-merge).
- [x] **P0.2**: Baseline gate green from worktree:
  - `just check`: ruff + ty all pass
  - `uv run pytest -q`: 980 passed, 16 deselected
  - `./thoth_test -r --skip-interactive -q`: 76 passed, 0 failed, 10 skipped
- [ ] **P0.3**: Commit project file + plan reference (this commit also flips trunk glyph `[?]`/missing → `[~]` and Status line).

---

## Layer 1 — Uniform help dispatch (must-have)

### Goal

Any invocation containing `--help` or `-h` shows help (top-level, command-specific, or "unknown command + suggestions"), never falls through to the research runner. Single-token unrecognized commands fail with a structured "unknown command" error followed by a fuzzy/curated suggestion and the full command list.

### Files to modify

| File | Change |
|---|---|
| `src/thoth/help.py:109-137` (`ThothGroup.invoke`) | Add a `--help`/`-h` short-circuit ahead of the existing 3-path dispatch. Add an unknown-command branch for single-token cases that look like command identifiers. |
| `src/thoth/help.py` (new helpers) | `_KNOWN_SUBPATHS: dict[str, str]`, `_suggest_command(typed, registered) -> str | None`, `_format_unknown_command_error(typed, registered, run_commands, admin_commands) -> str`. |
| `src/thoth/cli.py:250-266` | Add `--help` and `-h` to the `flag_options` dict so the bare-prompt parser recognizes them and routes to help. (Belt-and-suspenders — Layer 1's invoke-level fix should catch them earlier, but this prevents regression if dispatch changes.) |

### Dispatch rule (replaces current Path 3)

```text
if "--help" in args or "-h" in args:
    if args[0] in self.commands:           → standard Click dispatch (Click handles --help)
    elif args[0] in BUILTIN_MODES:         → mode help (existing path)
    else:                                  → emit "unknown command" error
                                             + fuzzy/curated "did you mean..." line
                                             + full command list
                                             exit 2
else:
    if args[0] in self.commands:           → standard dispatch (Path 1, unchanged)
    elif args[0] in BUILTIN_MODES:         → mode positional dispatch (Path 2, unchanged)
    elif (len(args) == 1
          and re.match(r"^[a-z][a-z0-9_-]*$", args[0])
          and not args[0].startswith("-")): → emit "unknown command" error (same format)
                                             exit 2
    else:                                  → bare-prompt fallback (Path 3, unchanged)
```

**Key heuristic** (per user's input): a "single token that looks like a command name" is a typo, not a research prompt. Multi-token strings, quoted prompts, and option-only invocations preserve the existing bare-prompt behavior.

### Error message format

For `thoth profiles --help`:

```text
Error: unknown command 'profiles'

Did you mean 'thoth config profiles'?

Available top-level commands:
  Run research:
    ask              Run a research mode against your prompt
    default          Default research mode
    clarification    Ask clarifying questions before research
    deep_research    Background deep-research mode
    ...
  Manage thoth:
    config           Read/write configuration
    init             Bootstrap a config file
    list             List recent research runs
    modes            Inspect or edit research modes
    providers        List configured providers
    status           Show in-flight background runs
    ...

Run `thoth --help` for the full command list and options.
```

Fuzzy-match seed list: registered top-level subcommands + a hand-curated `_KNOWN_SUBPATHS` dict for common nested paths (`profiles → thoth config profiles`, etc.) so the suggestion can name the right path even when the user typed only the leaf.

### `_KNOWN_SUBPATHS` initial entries

```python
_KNOWN_SUBPATHS: dict[str, str] = {
    "profiles": "thoth config profiles",
    "profile": "thoth config profiles",
    "set": "thoth config set",
    "get": "thoth config get",
    "unset": "thoth config unset",
    # P12 mode operations (also accepted at top level via `thoth modes`)
    "add": "thoth modes add",
    "remove": "thoth modes remove",
    "rename": "thoth modes rename",
    "copy": "thoth modes copy",
}
```

### Tests to add (Layer 1)

In `tests/test_cli_help.py` (or a new `tests/test_unknown_command.py`):

- `test_help_works_for_unknown_command` — `thoth profiles --help` → exit 2, stdout contains `unknown command 'profiles'`, `Did you mean 'thoth config profiles'`, `Available top-level commands:`.
- `test_help_works_for_registered_command` — `thoth modes --help` → exit 0 with the standard click help (regression preservation).
- `test_help_works_for_builtin_mode` — `thoth default --help` → mode help (existing behavior preserved).
- `test_unknown_single_token_no_help_flag` — `thoth profiles` → exit 2 with the same "unknown command" error (the bare-prompt fallback should NOT swallow this).
- `test_bare_prompt_multi_token_still_works` — `thoth quantum gravity` → bare-prompt fallback (unchanged).
- `test_quoted_prompt_still_works` — `thoth "what is X"` → bare-prompt fallback (quoted strings have spaces, don't match the command-name regex).
- `test_help_flag_short_form` — `thoth profiles -h` → same path as `--help`.

### Tests to update (Layer 1)

- `tests/baselines/unknown_command.json` — regenerate. Currently pins the broken behavior (its `stdout` is the API-key error). New baseline captures the "unknown command" error.
- `tests/test_p16_thothgroup.py::test_invoke_routes_bare_prompt` — currently asserts "single unknown first-word → bare-prompt routing." Reframe: assert single-token unknown → "unknown command" error; multi-token unknown → bare-prompt.

---

## Layer 2 — Enhanced APIKeyError message (high-value)

### Goal

When key validation fails legitimately, the error enumerates ALL input channels and shows multi-provider status, not just the single env var that was checked.

### Files to modify

| File | Change |
|---|---|
| `src/thoth/errors.py:45-64` (`APIKeyError`) | Expand the suggestion to mention env var, CLI flag, AND config file with concrete TOML syntax. Show every provider's env-var status, not just the failing one. |
| `src/thoth/errors.py:20-32` (`format_config_context`) | Extend to optionally emit the multi-provider env-var status block, OR add a new helper alongside it. (Caller-side decision in implementation.) |
| `src/thoth/providers/__init__.py:32-36` (`PROVIDER_ENV_VARS`) | Add a sibling `PROVIDER_CLI_FLAGS: dict[str, str]` mapping provider → CLI flag name (`"openai" → "--api-key-openai"`, etc.) for use by the error formatter. |

### Updated error message format

```text
Error: openai API key not found

Provide an OpenAI API key via one of:
  1. Environment variable: export OPENAI_API_KEY=sk-...
  2. CLI flag:              thoth --api-key-openai sk-... <command>
  3. Config file:           Add to /Users/stevemorin/.config/thoth/thoth.config.toml:
                              [providers.openai]
                              api_key = "sk-..."

Or switch providers with --provider perplexity (or another) and supply that
provider's key via the same channels.

Status of currently-checked sources:
  Config file: /Users/stevemorin/.config/thoth/thoth.config.toml  (exists)
  Env vars:    OPENAI_API_KEY (unset)  PERPLEXITY_API_KEY (unset)  MOCK_API_KEY (set)
```

The substring `"openai API key not found"` (the title line) is **preserved verbatim** so existing assertions in `tests/test_api_key_resolver.py:42`, `tests/test_openai_errors.py:65`, `tests/test_config_filename.py:255`, `tests/test_error_context.py:44,61` all stay green.

### Tests to add (Layer 2)

In `tests/test_api_key_resolver.py` (extend) or `tests/test_error_context.py` (extend):

- `test_apikeyerror_message_lists_all_input_channels` — assert env var, CLI flag, AND config-file syntax all appear in the suggestion.
- `test_apikeyerror_shows_all_provider_envvar_status` — assert OPENAI/PERPLEXITY/MOCK status all appear in the multi-provider status block, not just the failing one.
- `test_apikeyerror_legacy_guidance_still_appended` — preserve the existing legacy-config-file guidance behavior (regression).

---

## Layer 3 — Multi-provider default fallback

### Goal

When `--provider` is not specified and the active mode doesn't pin a provider, the runner picks any provider that has a resolvable key. Errors only when ZERO providers have keys.

### Files to modify

| File | Change |
|---|---|
| `src/thoth/providers/__init__.py` (new helper) | Add `available_providers(config, cli_api_keys=None) -> list[str]` that returns providers with resolvable keys (consults CLI args, env, config — does NOT raise on missing keys). Order matches `PROVIDERS` dict iteration (stable). |
| `src/thoth/run.py:272-294` | Replace the hardcoded `providers_to_use = ["openai"]` fallback with `available_providers(...)` lookup. Preference order: `general.default_provider` if set + resolvable → first available in `PROVIDERS` dict order → "openai" (when zero available, to trigger Layer 2's enhanced error). |

### `available_providers` helper

```python
def available_providers(
    config: ConfigManager,
    cli_api_keys: dict[str, str | None] | None = None,
) -> list[str]:
    """Return list of provider names that have a resolvable API key.

    Checks CLI-supplied keys, env vars, and the loaded config. Does NOT
    raise on missing keys (unlike resolve_api_key); use when dispatch
    logic needs to discover available providers before calling
    create_provider.

    Order matches PROVIDERS dict iteration so callers get a stable order
    (currently: openai, perplexity, mock).
    """
    cli_api_keys = cli_api_keys or {}
    available = []
    for name in PROVIDERS:
        cli_key = cli_api_keys.get(f"api_key_{name}")
        provider_config = config.data.get("providers", {}).get(name, {})
        try:
            resolve_api_key(name, cli_key, provider_config)
            available.append(name)
        except APIKeyError:
            continue
    return available
```

### Updated `run.py` fallback logic

Replace the existing block at `run.py:272-294`:

```python
if provider:
    providers_to_use = [provider]
elif mode == "thinking" or "provider" in mode_config:
    providers_to_use = [mode_config.get("provider", "openai")]
elif "providers" in mode_config:
    providers_to_use = mode_config.get("providers", ["openai"])
else:
    # NEW: Multi-provider default — pick any with a resolvable key.
    available = available_providers(config, cli_api_keys=ctx_api_keys)
    if not available:
        # No keys anywhere — let create_provider("openai", ...) raise the
        # enhanced APIKeyError with full enumeration (Layer 2's job).
        providers_to_use = ["openai"]
    else:
        # Prefer general.default_provider if set + resolvable.
        default = config.data.get("general", {}).get("default_provider")
        if default in available:
            providers_to_use = [default]
        else:
            # First available in PROVIDERS dict iteration order.
            providers_to_use = [available[0]]
```

### Tests to add (Layer 3)

In `tests/test_run_provider_fallback.py` (new file):

- `test_default_provider_picks_openai_when_available` — `OPENAI_API_KEY` set, no `--provider`: openai used.
- `test_default_provider_picks_perplexity_when_only_one_with_key` — only `PERPLEXITY_API_KEY` set: perplexity used.
- `test_default_provider_respects_general_default_provider_config` — `general.default_provider = "perplexity"` + key set: perplexity used even if openai also has a key.
- `test_no_keys_raises_apikeyerror_with_enhanced_message` — no provider keys: error raised, message includes Layer 2's full enumeration.
- `test_explicit_provider_flag_overrides_fallback` — `--provider mock` always wins regardless of which keys are set.

### Behavior change scope

| Scenario | Current behavior | New behavior |
|---|---|---|
| `OPENAI_API_KEY` set, no `--provider` | Uses openai ✓ | Uses openai (unchanged) |
| Only `PERPLEXITY_API_KEY` set, no `--provider` | Errors on missing OpenAI key | Auto-uses perplexity |
| Only `MOCK_API_KEY` set | Errors on missing OpenAI key | Auto-uses mock |
| OpenAI + Perplexity both set, `general.default_provider = "perplexity"` | Uses openai (config ignored for fallback) | Uses perplexity (config honored) |
| OpenAI + Perplexity both set, no `general.default_provider` | Uses openai ✓ | Uses openai (still — preserves preference) |
| No keys anywhere | Errors on missing OpenAI | Errors with Layer 2's enhanced message |
| `--provider perplexity` explicit | Uses perplexity ✓ | Uses perplexity (unchanged) |

The behavioral change is **strictly additive**: cases where openai works today continue to work; cases that fail today (only-non-openai keys) now succeed. No existing successful invocation changes behavior.

---

## Verification (acceptance criteria)

After all three layers land:

```bash
# Layer 1: unknown command + --help
unset OPENAI_API_KEY
uv run thoth profiles --help              # → "unknown command 'profiles', did you mean 'thoth config profiles'?" + full list, exit 2
uv run thoth profiles                     # → same error, exit 2 (no longer falls into research)
uv run thoth profiel --help               # → typo: "did you mean 'thoth profiles'" via fuzzy match
uv run thoth modes --help                 # → standard click help (regression check)
uv run thoth quantum gravity              # → bare-prompt fallback (existing behavior)

# Layer 2: enhanced APIKeyError
uv run thoth ask "test"                   # → multi-line error with env/flag/config syntax + multi-provider status

# Layer 3: multi-provider default
unset OPENAI_API_KEY
export PERPLEXITY_API_KEY=pplx-...
uv run thoth ask "test"                   # → uses perplexity automatically (was: openai-not-found error)

# Full gate
just check && uv run pytest -q && ./thoth_test -r --skip-interactive -q
```

### Acceptance criteria

- [ ] All `--help` invocations work without API keys (regardless of command name validity).
- [ ] Unknown single-token commands emit "unknown command" + did-you-mean + command list.
- [ ] Multi-token strings still route to bare-prompt research (`test_bare_prompt_*` regressions stay green).
- [ ] APIKeyError suggestion lists env var + CLI flag + config syntax.
- [ ] APIKeyError shows status of ALL provider env vars in one block.
- [ ] Runner picks any-provider-with-key when no `--provider` is given.
- [ ] `general.default_provider` config key honored when its provider has a key.
- [ ] No regressions in registered-subcommand or builtin-mode dispatch.
- [ ] Full pytest suite green; thoth_test green; lefthook gate green.

---

## Test-suite impact estimate

**Existing tests that need updates** (~5-7 tests, all inverting bug-pinning behavior):

| File / Test | What changes |
|---|---|
| `tests/baselines/unknown_command.json` | Regenerate with new "unknown command" error output. |
| `tests/test_p16_thothgroup.py::test_invoke_routes_bare_prompt` | Reframe: assert single-token unknown → "unknown command" error; multi-token unknown → bare-prompt. |
| `tests/test_p16_dispatch_parity.py` (parity baselines) | Possibly regenerate `unknown_command` baseline; other parity cases unchanged. |
| `tests/test_config_profile_cli_integration.py::test_profile_default_mode_used_for_bare_prompt` | Verify behavior — should still pass IF it uses a multi-token prompt. |

**Existing tests that should pass UNCHANGED** (Layer 2 preserves the title-line substring):

- `tests/test_api_key_resolver.py:42` — `"openai API key not found" in info.value.message` ✓
- `tests/test_openai_errors.py:65` — same substring check ✓
- `tests/test_config_filename.py:255` — same substring check ✓
- `tests/test_error_context.py:44, 61` — APIKeyError instantiation, doesn't pin the suggestion text ✓

**New tests added** (~15 across the 3 layers):

- L1: ~7 tests in `tests/test_cli_help.py` (or `tests/test_unknown_command.py`)
- L2: ~3 tests in `tests/test_api_key_resolver.py` (or `tests/test_error_context.py`)
- L3: ~5 tests in `tests/test_run_provider_fallback.py` (new)

**Net impact:** ~5-7 modified, ~15 added, **no deletions**. The modified ones are inverting tests that pin current broken behavior — exactly what we want.

---

## Suggested commit sequence

1. `chore(p36): start P36 — flip glyph and Status to [~]` — project-tracking flip.
2. `feat(help): route --help and unknown commands before bare-prompt fallback (L1)` — invoke change + helpers + tests.
3. `feat(errors): enumerate all key-input channels in APIKeyError (L2)` — error message + tests.
4. `feat(run): pick any-provider-with-key as default fallback (L3)` — run.py + `available_providers` helper + tests.
5. `feat(p36): close P36 — uniform help + useful API-key errors` — final glyph flip.

Each commit goes through the full lefthook gate. No `--no-verify`.

---

## Files reference

| File | Purpose |
|---|---|
| `src/thoth/help.py:109-137` | `ThothGroup.invoke` — main dispatch (Layer 1) |
| `src/thoth/help.py:139-160` | `format_commands` — command-list rendering (reused by Layer 1's error) |
| `src/thoth/cli.py:250-266` | `_extract_fallback_options` flag/value tables (Layer 1 belt-and-suspenders) |
| `src/thoth/errors.py:20-32` | `format_config_context` (Layer 2) |
| `src/thoth/errors.py:45-64` | `APIKeyError` class (Layer 2) |
| `src/thoth/providers/__init__.py:25-36` | `PROVIDERS`, `PROVIDER_ENV_VARS` registries (Layer 2/3) |
| `src/thoth/providers/__init__.py:39-65` | `resolve_api_key` (Layer 2 caller; new `available_providers` sits alongside) |
| `src/thoth/run.py:272-294` | Provider-selection fallback (Layer 3) |
| `tests/test_cli_help.py` | Existing CLI help tests (Layer 1 extends) |
| `tests/test_api_key_resolver.py` | Existing resolver tests (Layer 2 extends) |
| `tests/test_run_provider_fallback.py` (NEW) | Layer 3 tests |
