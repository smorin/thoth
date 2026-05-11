# P24 Task 6.2: `[providers.X]` root-namespace passthrough investigation

**Date**: 2026-05-03
**Owner**: P24 plan (closeout phase)
**Outcome**: **PUNT** — defer to a focused follow-up project.

## Question

Should `[providers.X]` carry default settings (e.g. `[providers.openai].temperature = 0.3`) that flow through to the provider when no mode-level override is set?

Currently `[providers.X]` is documented (in `render_auth_help`) only as carrying `api_key`. After P24 Task 3.1's OpenAI namespace migration, mode-level config can use `[modes.X.openai].temperature` etc. The next conceptual step would be to ALSO allow `[providers.openai].temperature` as a global default that any mode-level value overrides.

## Current state — survey findings

### `create_provider` (`src/thoth/providers/__init__.py:154-216`)

The factory copies the *entire* `[providers.<name>]` table verbatim:

```python
provider_config = config.data["providers"].get(provider_name, {}).copy()
```

It then layers mode-level config on top via `_apply_mode_provider_config` and a few targeted overrides (`model`, `kind`, `timeout`, `background`). **There is no schema-level filter on which keys are allowed under `[providers.X]` — anything the user puts there is copied through unchanged.**

### `OpenAIProvider._resolve_provider_config_value` (`src/thoth/providers/openai.py:195-230`)

The OpenAI provider's per-call resolver chain is:

1. `self.config["openai"][key]` — the `[modes.X.openai]` namespace (preferred).
2. `self.config[key]` — flat top-level (deprecated; emits `DeprecationWarning` unless `key in _FRAMEWORK_FLAT_KEYS_OPENAI`).
3. `default`.

`_FRAMEWORK_FLAT_KEYS_OPENAI = {"openai", "kind", "model", "timeout", "background"}` — `temperature`, `max_tool_calls`, `code_interpreter`, etc. are NOT in this set.

### Schema (`src/thoth/config.py`)

`ConfigSchema.get_defaults()["providers"]` declares only `api_key` for each provider. `_validate_config` checks that the `providers` top-level key exists but does **not** validate the keys *inside* each provider's table. Unknown keys pass through silently.

### `render_auth_help` (`src/thoth/help.py:335-352`)

Documents `[providers.openai]`, `[providers.perplexity]`, and `[providers.gemini]` as carrying *only* `api_key`. No mention of other defaults.

### Empirical behavior today (verified)

```python
config.data = {"providers": {"openai": {"api_key": "sk-test", "temperature": 0.3}}}
provider = create_provider("openai", config)
# provider.config == {"api_key": "sk-test", "temperature": 0.3}
provider._resolve_provider_config_value("temperature", 0.7)
# → 0.3, AND emits DeprecationWarning telling user to migrate to
#   [modes.X.openai].temperature
```

So the feature **already half-works** for OpenAI: the value flows through correctly via the flat-top-level fallback, but the resolver fires a misleading `DeprecationWarning` advising the user to move the value to a mode-level key — wrong advice when the user *intentionally* wants a global default.

For Perplexity/Gemini, the situation is similar: `create_provider` copies any keys verbatim into `provider_config`, and each provider's own config-reading code (analogous to `_resolve_provider_config_value`) decides how to interpret them.

## Implementation cost (if SHIP)

A clean SHIP is **not** ~30 lines in `create_provider`. The work spans:

1. **Layering helper in `create_provider`**: layer `config.data["providers"][name]` UNDER `mode_config[name]` so root-level values become defaults (~15 lines).
2. **Resolver awareness across providers**: `_resolve_provider_config_value` (and Perplexity/Gemini equivalents) needs to know that a value sourced from the `[providers.X]` root must NOT trigger the `[modes.X.<name>]` migration `DeprecationWarning`. Today the resolver can't distinguish "value originated from root-providers" from "value originated from mode-level flat key" because both end up flat on `self.config`. This requires either:
   - Threading the source layer (`"root_providers"` vs `"mode_flat"`) through the merged dict, OR
   - Stuffing root-providers values into `self.config["openai"][key]` *before* mode merge, so they become indistinguishable from namespaced values.
3. **Schema design call**: must `[providers.openai].temperature` mean "flat default" or "feed into the `openai` namespace"? Both are defensible; they have different override semantics with `[modes.X.openai]`.
4. **Unknown-key policy**: pass-through (current), ignore, or validate? All three providers need to agree.
5. **Help text + docs update**: `render_auth_help` and any user docs need to advertise the new defaults pattern.
6. **Symmetric tests** for OpenAI / Perplexity / Gemini, plus negative tests that the `DeprecationWarning` does NOT fire on the root-providers path.

## Risks

**Of SHIP-now**:
- The half-baked existing behavior (works for OpenAI, fires misleading warning) is itself evidence that this needs design, not just code. Shipping without a schema decision risks cementing whichever interpretation the implementation picks.
- P24 is at task 18 of 19; adding this scope risks closeout slip.
- Cross-provider symmetry needs explicit verification — Perplexity and Gemini have their own resolver patterns (or lack thereof) that may diverge from OpenAI's.

**Of PUNT**:
- The misleading `DeprecationWarning` for OpenAI users who already put `temperature` under `[providers.openai]` continues to mislead. This is a documentation issue today (`render_auth_help` doesn't advertise root-level defaults), so few users are likely affected, but it's a latent bug.
- A user who reads "migrate to `[modes.X.openai]`" and complies will *lose* their global default in any other mode.

## Decision

**PUNT.** Reasoning:

- P24 closeout is imminent (this is the last task before Phase 7).
- The clean SHIP is not mechanical — it requires schema decisions (key meaning, unknown-key policy) plus changes that span all three providers' resolver patterns plus the deprecation-warning logic.
- The existing half-baked behavior is itself an argument for a focused follow-up: a SHIP that doesn't fix the deprecation-warning incoherence would be no better than today. A SHIP that *does* fix it touches three providers and the schema.
- A focused follow-up project can audit the existing schema, decide which keys can SAFELY have a root-level default vs which should require mode-scope (e.g. `kind`, `model`, `system_prompt` arguably should NOT have global defaults), and ship symmetric behavior across providers.

## Follow-up

Recommended successor project (not auto-created here — owner can register via `project-add` when ready):

> **P##: `[providers.X]` root-namespace defaults + deprecation-warning fix**
>
> 1. Decide schema: which keys are allowed under `[providers.X]`, and do they layer as flat defaults or feed into the `[providers.X.<provider>]` namespace? Document in `render_auth_help` and project-level docs.
> 2. Implement layering in `create_provider` so `config.data["providers"][name]` becomes a default under `mode_config`.
> 3. Update each provider's resolver (OpenAI's `_resolve_provider_config_value`, plus Perplexity/Gemini equivalents) so values sourced from the root-providers tier do NOT emit the `[modes.X.<name>]` migration `DeprecationWarning`.
> 4. Make the four skipped P24-T17 aspirational tests pass (`tests/test_provider_config.py::test_root_providers_namespace_*` and `::test_mode_level_openai_temperature_overrides_root_providers_default`).
> 5. Add symmetric coverage for Perplexity + Gemini.
> 6. Update `render_auth_help` to document the new defaults pattern.

## Files in this task

- `planning/p24-providers-root-namespace-investigation.v1.md` (this document, NEW)
- `tests/test_provider_config.py` — adds four `@pytest.mark.skip(...)` tests with real assertion bodies that pin the desired contract for the successor project.
- `projects/P24-gemini-immediate-sync.md` — flips P24-TS16 and P24-T17 to `[-]` (decided not to do here) with a one-liner pointing here.

No production code changes (`src/thoth/providers/__init__.py`, `src/thoth/config.py`, `src/thoth/providers/openai.py` untouched).
