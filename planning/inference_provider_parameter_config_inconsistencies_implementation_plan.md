# Inference Provider Parameter Config Inconsistencies Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the accepted global provider-parameter consistency contract from `inference_provider_parameter_config_matrix.md` and `inference_provider_parameter_config_inconsistencies.md`.

**Architecture:** Add one shared provider-parameter normalization layer between config/mode resolution and provider adapters. `create_provider()` should build a normalized structure once, then OpenAI, Perplexity, and Gemini adapters should translate that structure into their SDK request shapes without rediscovering layer semantics.

**Tech Stack:** Python, pytest, Pydantic config schema, existing Doxa Research provider adapters, `ConfigManager`, `create_provider()`.

---

## Source Of Truth

- Desired state: `planning/inference_provider_parameter_config_matrix.md`
- Backlog IDs: `planning/inference_provider_parameter_config_inconsistencies.md`
- Current punt/tracker: `projects/P24-gemini-immediate-sync.md` (`P24-T26`)
- Main routing point: `src/doxa_research/providers/__init__.py`
- Mode overlay: `src/doxa_research/config.py::ConfigManager.get_mode_config`
- Provider adapters:
  - `src/doxa_research/providers/openai.py`
  - `src/doxa_research/providers/perplexity.py`
  - `src/doxa_research/providers/gemini.py`

## Scope

This plan covers the global consistency bundle:

- `P24-T26` - recognized-field registry docs.
- `GAP-001` - provider defaults normalization, including `[providers.defaults]`.
- `GAP-002` - fixed L6/L8 mode common parameter set.
- `GAP-003` - shared normalized provider parameter object.
- `INC-001` - flat mode common params consumed unevenly.
- `INC-002` - root provider defaults behave differently by provider.
- `INC-003` - provider namespace unknown-key policy diverges.
- `INC-004` - built-in mode overrides are shallow.
- `INC-011` - Perplexity sync/async `response_format` mismatch.

This plan intentionally does not finish every parameter-family gap (`GAP-008` through `GAP-017`) except where needed to prove the global normalizer works. Those rows become follow-up tasks after the shared path is in place.

## Target Layer Contract

Precedence is lowest to highest:

1. L0 provider implementation defaults.
2. L1 built-in mode defaults.
3. L2 `[providers.defaults]`.
4. L3 `[providers.NAME]`.
5. L4 `[profiles.PROFILE.providers.defaults]`.
6. L5 `[profiles.PROFILE.providers.NAME]`.
7. L6 `[modes.MODE]` fixed common params.
8. L7 `[modes.MODE.PROVIDER]`.
9. L8 `[profiles.PROFILE.modes.MODE]` fixed common params.
10. L9 `[profiles.PROFILE.modes.MODE.PROVIDER]`.
11. L10 runtime overrides.
12. L11 clarification config stays outside this bundle; `GAP-007` tracks reuse of provider normalization for clarification model calls.

## Checkpoints

- [x] **Checkpoint 1:** Contract and registry documented (`P24-T26`).
- [x] **Checkpoint 2:** Failing normalization tests exist for L2-L10 precedence. Checkpoint 2/3 cover the current normalizer input surface, including `timeout_override`; model and provider API-key runtime overrides are wired through `create_provider()` in Checkpoint 4.
- [x] **Checkpoint 3:** Shared normalized provider parameter object exists and tests pass without adapter rewrites.
- [x] **Checkpoint 4:** `create_provider()` uses the normalizer for OpenAI, Perplexity, and Gemini.
- [x] **Checkpoint 5:** Built-in/user/profile mode overlays deep-merge provider namespaces.
- [x] **Checkpoint 6:** Provider adapters consume normalized request/provider sections consistently.
- [x] **Checkpoint 7:** Unknown-key and extension-bag policy is enforced consistently.
- [x] **Checkpoint 8:** Docs, skipped tests, and migration notes are aligned.
- [x] **Checkpoint 9:** Targeted tests, lint/type checks, and final gate pass.

---

## Checkpoint Verification Log

- [x] **Checkpoint 1:** Documentation consistency verified with `rg` and `git diff --check`.
- [x] **Checkpoint 2:** Red-state pytest failure was expected because `doxa-research.providers.parameter_config` did not exist; `doxa_test` still passed, preserving core functionality.
- [x] **Checkpoint 3:** `uv run pytest tests/test_provider_parameter_normalization.py -q` passed (`6 passed`); `uv run pytest -m extended -q` passed (`3 passed, 17 skipped, 1433 deselected`); `./doxa_test -r --skip-interactive -q` passed (`75 passed, 12 skipped`); `uv run pytest -q` passed (`1401 passed, 4 skipped, 48 deselected`).
- [x] **Checkpoint 4 focused:** Initial red tests failed for the expected reasons (`[providers.defaults]` missing, OpenAI root defaults warning, Perplexity `extra_body` bridge missing). After wiring, focused tests passed (`12 passed, 30 deselected`) and targeted provider suites passed (`62 passed`).
- [x] **Checkpoint 4:** `uv run pytest -m extended -q` passed (`3 passed, 17 skipped, 1441 deselected`); `./doxa_test -r --skip-interactive -q` passed (`75 passed, 12 skipped`); `uv run pytest -q` passed (`1413 passed, 48 deselected`).
- [x] **Checkpoint 5 focused:** Deep-merge test failed for the expected reason, then passed after replacing shallow `mode_config.update()` overlays; focused mode suite passed (`35 passed`).
- [x] **Checkpoint 5:** `uv run pytest -m extended -q` passed (`3 passed, 17 skipped, 1442 deselected`); `./doxa_test -r --skip-interactive -q` passed (`75 passed, 12 skipped`); `uv run pytest -q` passed (`1414 passed, 48 deselected`).
- [x] **Checkpoint 6 focused:** Perplexity sync/async response-format and `extra_body` tests already passed; Gemini timeout failed for the expected reason, then passed after wiring `HttpOptions(timeout=...)`; adapter suite passed (`148 passed`) and normalization/passthrough suite passed (`21 passed`).
- [x] **Checkpoint 6:** `uv run pytest -m extended -q` passed (`3 passed, 17 skipped, 1445 deselected`); `./doxa_test -r --skip-interactive -q` passed (`75 passed, 12 skipped`); `uv run pytest -q` passed (`1417 passed, 48 deselected`).
- [x] **Checkpoint 7 focused:** Unknown root/default/provider-namespace tests failed for the expected reason, then passed after strict normalizer validation; normalizer suite passed (`16 passed`) and P33/extra-body compatibility passed (`11 passed`).
- [x] **Checkpoint 7:** `uv run pytest -m extended -q` passed (`3 passed, 17 skipped, 1450 deselected`); `./doxa_test -r --skip-interactive -q` passed (`75 passed, 12 skipped`); first `uv run pytest -q` failure was expected because `test_root_providers_namespace_unknown_keys_passed_through_or_filtered` still asserted the old placeholder contract, then the test was updated to assert strict rejection and `uv run pytest -q` passed (`1422 passed, 48 deselected`).
- [x] **Checkpoint 8 focused:** Docs/statuses/migration notes were aligned with the implementation, `P24-T26` was marked complete, stale P33 passthrough wording was updated, `git diff --check` passed, focused provider config/normalizer tests passed (`58 passed`), and ruff check/format-check passed for touched Python files.
- [x] **Checkpoint 8:** `uv run pytest -m extended -q` passed (`3 passed, 17 skipped, 1450 deselected`); `./doxa_test -r --skip-interactive -q` passed (`75 passed, 12 skipped`); `uv run pytest -q` passed (`1422 passed, 48 deselected`).
- [x] **Checkpoint 9 focused:** Targeted provider normalization/provider suites passed (`187 passed`); `just check`, `make env-check`, `just fix`, final `just check`, full `./doxa_test -r`, `just test-fix`, `just test-lint`, and `just test-typecheck` all passed. Full `./doxa_test -r` reported `91 passed, 13 skipped`; skips were expected because live OpenAI/Perplexity API keys were not set.
- [x] **Checkpoint 9:** `uv run pytest -m extended -q` passed (`3 passed, 17 skipped, 1450 deselected`); `./doxa_test -r --skip-interactive -q` passed (`75 passed, 12 skipped`); `uv run pytest -q` passed (`1422 passed, 48 deselected`).

---

## Task 1: Document Recognized Field Registry

**Backlog IDs:** `P24-T26`, `INC-002`, `DEC-007`

**Files:**
- Modify: `planning/inference_provider_parameter_config_matrix.md`
- Modify: `planning/inference_provider_parameter_config_inconsistencies.md`
- Modify: `projects/P24-gemini-immediate-sync.md`

- [x] **Step 1: Add the registry section to the matrix**

Add a section named `Recognized Field Registry` after the configuration layers. Include one table per scope:

```markdown
### All-Provider Defaults

Allowed in `[providers.defaults]` and `[profiles.NAME.providers.defaults]`.

| Internal key | Category | Providers | Provider key path | Normalized section | Notes |
|---|---|---|---|---|---|
| `timeout` | client | OpenAI, Perplexity, Gemini | client timeout | `client.timeout` | Shared client/runtime control. |
| `temperature` | common request | OpenAI, Perplexity, Gemini | provider-specific request key | `common_request.temperature` | Adapter omits for unsupported OpenAI reasoning models. |
| `top_p` | common request | OpenAI, Perplexity, Gemini | provider-specific request key | `common_request.top_p` | Supported where provider accepts it. |
| `max_output_tokens` | common request | OpenAI, Perplexity, Gemini | OpenAI/Gemini `max_output_tokens`, Perplexity `max_tokens` | `common_request.max_output_tokens` | Canonical internal token-budget key. |
```

Add a second table for `[providers.NAME]` / `[profiles.NAME.providers.PROVIDER]` that adds provider auth/client and provider-native fields.

- [x] **Step 2: Add references back to inconsistency IDs**

Update `INC-002`, `INC-008`, and `DEC-007` references to point to the new matrix section.

- [x] **Step 3: Mark `P24-T26` as complete only after runtime plan exists**

Do not mark `P24-T26` complete until this plan has implementation checkpoints and test coverage for the registry. Leave the checkbox open until Task 8.

- [x] **Step 4: Verify markdown consistency**

Run:

```bash
rg -n 'providers.defaults|Recognized Field Registry|INC-002|DEC-007' planning/inference_provider_parameter_config_matrix.md planning/inference_provider_parameter_config_inconsistencies.md projects/P24-gemini-immediate-sync.md
git diff --check -- planning/inference_provider_parameter_config_matrix.md planning/inference_provider_parameter_config_inconsistencies.md projects/P24-gemini-immediate-sync.md
```

Expected: references exist, and `git diff --check` prints no output.

---

## Task 2: Add Normalizer Unit Tests First

**Backlog IDs:** `GAP-001`, `GAP-002`, `GAP-003`, `INC-001`, `INC-002`

**Files:**
- Create: `tests/test_provider_parameter_normalization.py`
- Create: `src/doxa_research/providers/parameter_config.py`

- [x] **Step 1: Write failing tests for layer precedence**

Create `tests/test_provider_parameter_normalization.py` with tests shaped like:

```python
from types import SimpleNamespace
from typing import Any, cast

import pytest

from doxa-research.config import ConfigManager
from doxa-research.providers.parameter_config import build_provider_runtime_config


def _config(data: dict[str, Any]) -> ConfigManager:
    return cast(ConfigManager, SimpleNamespace(data=data))


def test_provider_defaults_precedence_l2_to_l5() -> None:
    config = _config(
        {
            "providers": {
                "defaults": {"timeout": 30, "temperature": 0.2, "kind": "background"},
                "gemini": {"api_key": "AIza-test", "temperature": 0.4, "kind": "immediate"},
            },
            "profiles": {
                "work": {
                    "providers": {
                        "defaults": {"timeout": 45},
                        "gemini": {"temperature": 0.6, "kind": "background"},
                    }
                }
            },
        }
    )

    runtime = build_provider_runtime_config(
        provider_name="gemini",
        config=config,
        active_profile="work",
        mode_name=None,
        mode_config=None,
        timeout_override=None,
    )

    assert runtime.auth["api_key"] == "AIza-test"
    assert runtime.client["timeout"] == 45
    assert runtime.common_request["temperature"] == 0.6
    assert runtime.routing["kind"] == "background"
```

```python
def test_mode_common_and_provider_namespace_precedence_l6_to_l9() -> None:
    config = _config(
        {
            "providers": {
                "defaults": {"temperature": 0.1},
                "perplexity": {"api_key": "pplx-test"},
            },
            "profiles": {
                "work": {
                    "modes": {
                        "focused": {
                            "top_p": 0.8,
                            "kind": "immediate",
                            "temperature": 0.4,
                            "perplexity": {
                                "kind": "background",
                                "temperature": 0.7,
                                "response_format": {"type": "json_schema"},
                            },
                        }
                    }
                }
            },
        }
    )
    mode_config = {
        "provider": "perplexity",
        "model": "sonar",
        "kind": "immediate",
        "temperature": 0.3,
        "perplexity": {
            "temperature": 0.5,
            "kind": "immediate",
            "response_format": {"type": "json_object"},
        },
    }

    runtime = build_provider_runtime_config(
        provider_name="perplexity",
        config=config,
        active_profile="work",
        mode_name="focused",
        mode_config=mode_config,
        timeout_override=None,
    )

    assert runtime.common_request["temperature"] == 0.7
    assert runtime.common_request["top_p"] == 0.8
    assert runtime.common_request["response_format"] == {"type": "json_schema"}
    assert runtime.routing["kind"] == "background"
    assert runtime.provider_request == {}
```

```python
def test_runtime_timeout_override_wins_over_config_layers() -> None:
    config = _config(
        {
            "providers": {
                "defaults": {"timeout": 30},
                "openai": {"api_key": "sk-test", "timeout": 45},
            }
        }
    )

    runtime = build_provider_runtime_config(
        provider_name="openai",
        config=config,
        active_profile=None,
        mode_name=None,
        mode_config=None,
        timeout_override=60,
    )

    assert runtime.client["timeout"] == 60
```

- [x] **Step 2: Run tests and verify they fail because the normalizer does not exist**

Run:

```bash
uv run pytest tests/test_provider_parameter_normalization.py -q
```

Expected: fail with `ModuleNotFoundError: No module named 'doxa-research.providers.parameter_config'`.

---

## Task 3: Implement Shared Runtime Config Object

**Backlog IDs:** `GAP-003`

**Files:**
- Create: `src/doxa_research/providers/parameter_config.py`
- Modify: `src/doxa_research/providers/__init__.py`
- Test: `tests/test_provider_parameter_normalization.py`

- [x] **Step 1: Create the normalized dataclasses and field registry**

Create `src/doxa_research/providers/parameter_config.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


ALL_PROVIDER_COMMON_REQUEST_KEYS: frozenset[str] = frozenset(
    {
        "model",
        "temperature",
        "top_p",
        "max_output_tokens",
        "response_format",
        "system_prompt",
    }
)

MODE_COMMON_REQUEST_KEYS: frozenset[str] = frozenset(
    {
        "model",
        "temperature",
        "top_p",
        "max_output_tokens",
        "stop_sequences",
        "response_format",
        "system_prompt",
    }
)
PROVIDER_COMMON_REQUEST_KEYS: frozenset[str] = MODE_COMMON_REQUEST_KEYS

CLIENT_KEYS: frozenset[str] = frozenset({"timeout", "base_url", "organization"})
ALL_PROVIDER_CLIENT_KEYS: frozenset[str] = frozenset({"timeout"})
AUTH_KEYS: frozenset[str] = frozenset({"api_key"})
ROUTING_KEYS: frozenset[str] = frozenset({"kind"})
NO_KEYS: frozenset[str] = frozenset()
PROVIDER_NATIVE_REQUEST_KEYS: frozenset[str] = frozenset(
    {
        "background",
        "code_interpreter",
        "frequency_penalty",
        "include_thoughts",
        "max_tokens",
        "max_tool_calls",
        "n",
        "presence_penalty",
        "reasoning",
        "reasoning_effort",
        "reasoning_summary",
        "response_json_schema",
        "response_mime_type",
        "response_schema",
        "safety_settings",
        "search_context_size",
        "search_domain_filter",
        "seed",
        "stop",
        "stream_mode",
        "thinking_budget",
        "tools",
        "top_k",
        "web_search",
        "web_search_options",
    }
)
FRAMEWORK_KEYS: frozenset[str] = frozenset(
    {
        "provider",
        "providers",
        "description",
        "previous",
        "next",
        "auto_input",
        "parallel",
        "stream",
    }
)


@dataclass(slots=True)
class ProviderRuntimeConfig:
    provider_name: str
    auth: dict[str, Any] = field(default_factory=dict)
    client: dict[str, Any] = field(default_factory=dict)
    routing: dict[str, Any] = field(default_factory=dict)
    framework: dict[str, Any] = field(default_factory=dict)
    common_request: dict[str, Any] = field(default_factory=dict)
    provider_request: dict[str, Any] = field(default_factory=dict)
    extension_bags: dict[str, dict[str, Any]] = field(default_factory=dict)
    sources: dict[str, str] = field(default_factory=dict)

    def to_legacy_config(self) -> dict[str, Any]:
        config: dict[str, Any] = {}
        config.update(self.auth)
        config.update(self.client)
        config.update(self.routing)
        config.update(self.framework)
        config.update(self.common_request)
        provider_namespace = dict(self.provider_request)
        provider_extensions = self.extension_bags.get(self.provider_name)
        if provider_extensions:
            provider_namespace.update(provider_extensions)
        if provider_namespace:
            config[self.provider_name] = provider_namespace
        return config
```

- [x] **Step 2: Implement deterministic merge helpers**

Add helpers in the same file:

```python
def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = _deep_merge(existing, value)
        else:
            merged[key] = value
    return merged


def _merge_layer(target: dict[str, Any], layer: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(layer, dict):
        return target
    return _deep_merge(target, layer)
```

- [x] **Step 3: Implement `build_provider_runtime_config()` minimally**

The function must accept:

```python
def build_provider_runtime_config(
    *,
    provider_name: str,
    config: Any,
    active_profile: str | None,
    mode_name: str | None,
    mode_config: dict[str, Any] | None,
    timeout_override: float | None,
) -> ProviderRuntimeConfig:
```

It should:

1. Read `config.data["providers"]["defaults"]`.
2. Read `config.data["providers"][provider_name]`.
3. If `active_profile` is set, read profile-scoped provider defaults and provider config.
4. Apply fixed common mode keys and routing keys such as `kind` from `mode_config`; do not promote mode-generic auth/client/unknown keys.
5. Apply provider namespace fields from `mode_config[provider_name]`; common request keys stay in `common_request`, recognized provider-native fields go to `provider_request`, `extra_body` goes to `extension_bags`, and routing keys such as `kind` go to `routing`.
6. If `active_profile` and `mode_name` are set, apply profile mode generic and profile mode provider namespace from `config.data["profiles"][active_profile]["modes"][mode_name]`, including routing keys.
7. Apply `timeout_override` last; other L10 runtime overrides are handled when `create_provider()` passes model/API-key inputs through the normalizer.
8. Split merged keys into `auth`, `client`, `routing`, `framework`, `common_request`, and `provider_request`.

- [x] **Step 4: Run the normalizer tests**

Run:

```bash
uv run pytest tests/test_provider_parameter_normalization.py -q
```

Expected: all tests in this file pass.

---

## Task 4: Wire `create_provider()` Through The Normalizer

**Backlog IDs:** `GAP-001`, `GAP-002`, `INC-001`, `INC-002`

**Files:**
- Modify: `src/doxa_research/providers/__init__.py`
- Test: `tests/test_provider_config.py`
- Test: `tests/test_provider_parameter_normalization.py`

- [x] **Step 1: Replace skipped root-provider tests with active tests**

In `tests/test_provider_config.py`, unskip or duplicate the existing P24-T17 desired tests and extend them for `[providers.defaults]`:

```python
def test_providers_defaults_temperature_flows_to_openai_without_deprecation() -> None:
    from types import SimpleNamespace

    from doxa-research.config import ConfigManager
    from doxa-research.providers import create_provider

    config = cast(
        ConfigManager,
        SimpleNamespace(
            data={
                "providers": {
                    "defaults": {"temperature": 0.3},
                    "openai": {"api_key": "sk-test"},
                }
            }
        ),
    )

    provider = create_provider("openai", config)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        resolved = cast(OpenAIProvider, provider)._resolve_provider_config_value("temperature", 0.7)

    assert resolved == 0.3
    assert not [w for w in caught if issubclass(w.category, DeprecationWarning)]
```

Add equivalent constructor assertions for Perplexity and Gemini.

- [x] **Step 2: Add a through-path extension-bag compatibility test**

In `tests/test_provider_parameter_normalization.py`, add:

```python
def test_perplexity_extra_body_survives_runtime_to_legacy_request_shapes() -> None:
    from doxa-research.providers.parameter_config import build_provider_runtime_config
    from doxa-research.providers.perplexity import PerplexityProvider

    config = _config(
        {
            "providers": {
                "perplexity": {"api_key": "pplx-test"},
            }
        }
    )
    runtime = build_provider_runtime_config(
        provider_name="perplexity",
        config=config,
        active_profile=None,
        mode_name="focused",
        mode_config={
            "provider": "perplexity",
            "model": "sonar",
            "kind": "immediate",
            "perplexity": {"extra_body": {"new_vendor_flag": True}},
        },
        timeout_override=None,
    )

    provider = PerplexityProvider(
        api_key=runtime.auth["api_key"],
        config=runtime.to_legacy_config(),
    )
    sync_params = provider._build_request_params("prompt", None)
    async_body = provider._build_async_request_body("prompt", None, "idem-test")

    assert sync_params["extra_body"]["new_vendor_flag"] is True
    assert async_body["request"]["extra_body"]["new_vendor_flag"] is True
```

Add the L9 profile-scoped sibling:

```python
def test_profile_perplexity_extra_body_survives_runtime_to_legacy_request_shapes() -> None:
    from doxa-research.providers.parameter_config import build_provider_runtime_config
    from doxa-research.providers.perplexity import PerplexityProvider

    config = _config(
        {
            "providers": {
                "perplexity": {"api_key": "pplx-test"},
            },
            "profiles": {
                "work": {
                    "modes": {
                        "focused": {
                            "perplexity": {"extra_body": {"profile_vendor_flag": True}},
                        }
                    }
                }
            },
        }
    )
    runtime = build_provider_runtime_config(
        provider_name="perplexity",
        config=config,
        active_profile="work",
        mode_name="focused",
        mode_config={
            "provider": "perplexity",
            "model": "sonar",
            "kind": "immediate",
        },
        timeout_override=None,
    )

    provider = PerplexityProvider(
        api_key=runtime.auth["api_key"],
        config=runtime.to_legacy_config(),
    )
    sync_params = provider._build_request_params("prompt", None)
    async_body = provider._build_async_request_body("prompt", None, "idem-test")

    assert sync_params["extra_body"]["profile_vendor_flag"] is True
    assert async_body["request"]["extra_body"]["profile_vendor_flag"] is True
```

Together, these tests prove L7 and L9 extension bags survive the normalizer, compatibility bridge, and both Perplexity request builders.

- [x] **Step 3: Run the tests and verify they fail on current behavior**

Run:

```bash
uv run pytest tests/test_provider_parameter_normalization.py tests/test_provider_config.py -k 'providers_defaults or root_providers_namespace or extra_body_survives' -q
```

Expected: tests fail because `[providers.defaults]` is not merged and current OpenAI flat fallback emits a misleading warning.

- [x] **Step 4: Update `create_provider()` to call the normalizer**

In `src/doxa_research/providers/__init__.py`:

1. Import `build_provider_runtime_config`.
2. Build `runtime_config` before API key resolution.
3. Resolve API key against `runtime_config.auth`.
4. Convert to legacy config with `runtime_config.to_legacy_config()` for the first commit; the compatibility output must preserve extension bags by merging them into the selected provider namespace.
5. Keep mock provider on its existing path unless mock support is explicitly added.

- [x] **Step 5: Run focused tests**

Run:

```bash
uv run pytest tests/test_provider_parameter_normalization.py tests/test_provider_config.py -k 'providers_defaults or root_providers_namespace or mode_level_openai_temperature or extra_body_survives' -q
```

Expected: focused tests pass.

---

## Task 5: Deep-Merge Built-In Mode Overrides

**Backlog IDs:** `INC-004`, `DEC-006`

**Files:**
- Modify: `src/doxa_research/config.py`
- Test: `tests/test_provider_parameter_normalization.py` or `tests/test_config_modes.py`

- [x] **Step 1: Write failing deep-merge test**

Add:

```python
def test_builtin_mode_provider_namespace_user_override_deep_merges() -> None:
    from types import SimpleNamespace

    from doxa-research.config import ConfigManager

    manager = ConfigManager.__new__(ConfigManager)
    manager.data = {
        "modes": {
            "gemini_quick": {
                "gemini": {"temperature": 0.2},
            }
        }
    }

    mode = manager.get_mode_config("gemini_quick")

    assert mode["gemini"]["temperature"] == 0.2
    assert mode["gemini"]["tools"] == ["google_search"]
    assert mode["gemini"]["thinking_budget"] == 0
```

- [x] **Step 2: Run and verify failure**

Run:

```bash
uv run pytest tests/test_provider_parameter_normalization.py::test_builtin_mode_provider_namespace_user_override_deep_merges -q
```

Expected: fail because `mode_config.update(user_mode)` replaces the nested `gemini` table.

- [x] **Step 3: Replace shallow mode overlay with deep merge**

In `src/doxa_research/config.py::get_mode_config()`, replace both `mode_config.update(user_mode)` calls with `self._deep_merge(mode_config, user_mode)`.

- [x] **Step 4: Run focused tests**

Run:

```bash
uv run pytest tests/test_provider_parameter_normalization.py::test_builtin_mode_provider_namespace_user_override_deep_merges tests/test_mode_aliases.py tests/test_modes_cmd.py -q
```

Expected: pass.

---

## Task 6: Switch Adapters To Normalized Request Sections

**Backlog IDs:** `GAP-003`, `INC-001`, `INC-011`, `INC-010`

**Files:**
- Modify: `src/doxa_research/providers/openai.py`
- Modify: `src/doxa_research/providers/perplexity.py`
- Modify: `src/doxa_research/providers/gemini.py`
- Test: `tests/test_provider_config.py`
- Test: `tests/test_provider_perplexity.py`
- Test: `tests/test_provider_gemini.py`

- [x] **Step 1: Add adapter tests for common request fields**

Add focused tests proving the same normalized common value reaches each provider:

```python
def test_common_temperature_reaches_gemini_generate_content_config() -> None:
    provider = GeminiProvider(api_key="AIza-test", config={"gemini": {"temperature": 0.2}})
    cfg = provider._build_generate_content_config()
    assert cfg.temperature == 0.2
```

```python
def test_perplexity_response_format_reaches_sync_and_async_request_shapes() -> None:
    provider = PerplexityProvider(
        api_key="pplx-test",
        config={"perplexity": {"response_format": {"type": "json_object"}}},
    )

    sync_params = provider._build_request_params("prompt", None)
    async_body = provider._build_async_request_body("prompt", None, "idem-test")

    assert sync_params["response_format"] == {"type": "json_object"}
    assert async_body["request"]["response_format"] == {"type": "json_object"}
```

```python
def test_perplexity_extra_body_reaches_sync_extra_body_and_async_request() -> None:
    provider = PerplexityProvider(
        api_key="pplx-test",
        config={"perplexity": {"extra_body": {"new_vendor_flag": True}}},
    )

    sync_params = provider._build_request_params("prompt", None)
    async_body = provider._build_async_request_body("prompt", None, "idem-test")

    assert sync_params["extra_body"]["new_vendor_flag"] is True
    assert async_body["request"]["extra_body"]["new_vendor_flag"] is True
```

The helper exists today as `_build_async_request_body(prompt, system_prompt, idempotency_key)`.

- [x] **Step 2: Run and verify current failures**

Run:

```bash
uv run pytest tests/test_provider_perplexity.py -k 'response_format and async' -q
uv run pytest tests/test_provider_gemini.py -k 'temperature' -q
```

Expected: at least the async Perplexity assertion fails until normalized request routing is implemented.

- [x] **Step 3: Update OpenAI adapter**

In `src/doxa_research/providers/openai.py`:

1. Keep `_resolve_provider_config_value()` only as a backward-compatible read path for legacy flat config.
2. Prefer `self.config["openai"]` provider request values and normalized common request values already copied there by `create_provider()`.
3. Map internal `system_prompt` to top-level `instructions` in request params when moving fully to normalized request construction.

- [x] **Step 4: Update Perplexity adapter**

In `src/doxa_research/providers/perplexity.py`:

1. Make sync and async request builders both read provider request keys from `self.config["perplexity"]`.
2. Stop relying on flat root fallback for direct SDK keys after the normalizer has moved defaults into the provider namespace.
3. Preserve `extra_body` for explicit extension fields and merge it into the final Perplexity extras without dropping known direct SDK keys.

- [x] **Step 5: Update Gemini adapter**

In `src/doxa_research/providers/gemini.py`:

1. Ensure normalized common request fields are available under `self.config["gemini"]`.
2. Keep `_DIRECT_SDK_KEYS_GEMINI` as the allowlist for typed SDK config.
3. Add missing direct keys only in parameter-family follow-up tasks unless required for this global bundle.

- [x] **Step 6: Run adapter tests**

Run:

```bash
uv run pytest tests/test_provider_config.py tests/test_provider_perplexity.py tests/test_provider_gemini.py -q
```

Expected: pass.

---

## Task 7: Implement Unknown-Key And Extension-Bag Policy

**Backlog IDs:** `INC-003`, `DEC-004`

**Files:**
- Modify: `src/doxa_research/providers/parameter_config.py`
- Modify: `src/doxa_research/config_schema.py`
- Test: `tests/test_provider_parameter_normalization.py`

- [x] **Step 1: Write failing tests for extension bags**

Add:

```python
def test_unknown_root_provider_key_is_rejected() -> None:
    config = _config(
        {
            "providers": {
                "perplexity": {
                    "api_key": "pplx-test",
                    "definitely_not_real": "x",
                }
            }
        }
    )

    with pytest.raises(ValueError, match="definitely_not_real"):
        build_provider_runtime_config(
            provider_name="perplexity",
            config=config,
            active_profile=None,
            mode_name=None,
            mode_config=None,
            timeout_override=None,
        )
```

Add positive tests that L7 and L9 `extra_body` reach `runtime.extension_bags["perplexity"]`:

```python
def test_mode_provider_namespace_extra_body_is_allowed() -> None:
    config = _config(
        {
            "providers": {
                "perplexity": {"api_key": "pplx-test"},
            }
        }
    )

    runtime = build_provider_runtime_config(
        provider_name="perplexity",
        config=config,
        active_profile=None,
        mode_name="focused",
        mode_config={
            "provider": "perplexity",
            "model": "sonar",
            "kind": "immediate",
            "perplexity": {"extra_body": {"new_vendor_flag": True}},
        },
        timeout_override=None,
    )

    assert runtime.extension_bags["perplexity"]["extra_body"] == {"new_vendor_flag": True}
```

```python
def test_profile_mode_provider_namespace_extra_body_is_allowed() -> None:
    config = _config(
        {
            "providers": {
                "perplexity": {"api_key": "pplx-test"},
            },
            "profiles": {
                "work": {
                    "modes": {
                        "focused": {
                            "perplexity": {"extra_body": {"profile_vendor_flag": True}},
                        }
                    }
                }
            },
        }
    )

    runtime = build_provider_runtime_config(
        provider_name="perplexity",
        config=config,
        active_profile="work",
        mode_name="focused",
        mode_config={
            "provider": "perplexity",
            "model": "sonar",
            "kind": "immediate",
        },
        timeout_override=None,
    )

    assert runtime.extension_bags["perplexity"]["extra_body"] == {"profile_vendor_flag": True}
```

- [x] **Step 2: Run and verify failure**

Run:

```bash
uv run pytest tests/test_provider_parameter_normalization.py -k 'unknown_root_provider_key or extra_body' -q
```

Expected: fail until validation policy exists.

- [x] **Step 3: Implement validation**

In `src/doxa_research/providers/parameter_config.py`:

1. Reject unknown keys in `[providers.defaults]`.
2. Reject unknown top-level keys in `[providers.NAME]` unless the key is a recognized auth/client/common/provider-native key.
3. Permit documented extension bags such as `perplexity.extra_body` only in L7/L9 provider namespaces.
4. Preserve provider-native namespace dictionaries for explicit provider keys.

- [x] **Step 4: Run validation tests**

Run:

```bash
uv run pytest tests/test_provider_parameter_normalization.py -q
```

Expected: pass.

---

## Task 8: Align Docs, Skipped Tests, And Migration Notes

**Backlog IDs:** `INC-008`, `P24-T26`

**Files:**
- Modify: `planning/inference_provider_parameter_config_matrix.md`
- Modify: `planning/inference_provider_parameter_config_inconsistencies.md`
- Modify: `projects/P24-gemini-immediate-sync.md`
- Modify: `tests/test_provider_config.py`

- [x] **Step 1: Remove stale skipped tests or convert them to active tests**

In `tests/test_provider_config.py`, remove `@pytest.mark.skip` from the P24-T17 tests that are now implemented, or delete duplicate skipped versions if new active tests supersede them.

- [x] **Step 2: Update inconsistency statuses**

Update entries according to actual implementation:

- `GAP-001`: `resolved` only after L2-L5 provider defaults work across all three providers.
- `GAP-002`: `resolved` only after L6/L8 common params are fixed and arbitrary passthrough has warning/error behavior.
- `GAP-003`: `resolved` only after adapters consume the normalized object or a compatibility wrapper backed by it.
- `INC-001`, `INC-002`, `INC-003`, `INC-004`, `INC-011`: `resolved` only after tests prove the inconsistency is gone.

- [x] **Step 3: Update migration notes**

Add concrete migration notes for:

- Flat arbitrary mode keys outside the fixed common set.
- Root provider default behavior becoming consistent.
- Unknown provider namespace keys moving to extension bags.

- [x] **Step 4: Mark P24-T26 complete**

Only after the registry, code, and tests are aligned, change:

```markdown
- [ ] [P24-T26] ...
```

to:

```markdown
- [x] [P24-T26] ...
```

- [x] **Step 5: Verify docs**

Run:

```bash
rg -n 'GAP-001|GAP-002|GAP-003|INC-001|INC-002|INC-003|INC-004|INC-011|P24-T26' planning/inference_provider_parameter_config_inconsistencies.md projects/P24-gemini-immediate-sync.md
git diff --check -- planning/inference_provider_parameter_config_matrix.md planning/inference_provider_parameter_config_inconsistencies.md projects/P24-gemini-immediate-sync.md tests/test_provider_config.py
```

Expected: statuses and references are coherent, and `git diff --check` prints no output.

---

## Task 9: Final Verification

**Backlog IDs:** all in scope

**Files:**
- Verify all changed files.

- [x] **Step 1: Run targeted provider normalization tests**

Run:

```bash
uv run pytest tests/test_provider_parameter_normalization.py tests/test_provider_config.py tests/test_provider_perplexity.py tests/test_provider_gemini.py tests/test_openai_errors.py -q
```

Expected: pass.

- [x] **Step 2: Run lint/type check for main executable**

Run:

```bash
just check
```

Expected: pass.

- [x] **Step 3: Run test suite**

Run:

```bash
./doxa_test -r --skip-interactive -q
```

Expected: pass.

- [x] **Step 4: Run final project gate before commit**

Run the repository-required final gate:

```bash
make env-check
just fix
just check
./doxa_test -r
just test-fix
just test-lint
just test-typecheck
```

Expected: all commands pass.

- [ ] **Step 5: Commit (deferred until explicitly requested)**

Commit after the full gate passes:

```bash
git add src/doxa_research/providers/parameter_config.py src/doxa_research/providers/__init__.py src/doxa_research/providers/openai.py src/doxa_research/providers/perplexity.py src/doxa_research/providers/gemini.py src/doxa_research/config.py src/doxa_research/config_schema.py tests/test_provider_parameter_normalization.py tests/test_provider_config.py tests/test_provider_perplexity.py tests/test_provider_gemini.py planning/inference_provider_parameter_config_matrix.md planning/inference_provider_parameter_config_inconsistencies.md projects/P24-gemini-immediate-sync.md
git commit -m "Normalize provider parameter configuration layers"
```

Expected: commit hooks pass.

---

## Rollback Boundaries

- If Task 3 becomes too large, keep `ProviderRuntimeConfig.to_legacy_config()` as the adapter compatibility boundary and defer direct adapter consumption to a second commit.
- If unknown-key validation creates too many schema conflicts, ship extension-bag support first and leave strict rejection as an accepted follow-up under `INC-003`.
- If Gemini timeout or reasoning-effort SDK details block progress, leave those provider-specific parameter-family gaps open; they are not required for the global consistency bundle.

## Definition Of Done

- [x] `[providers.defaults]` and `[profiles.NAME.providers.defaults]` are real normalized layers.
- [x] `[providers.NAME]` and profile provider blocks override all-provider defaults.
- [x] L6/L8 are a fixed common parameter set, not arbitrary passthrough.
- [x] L7/L9 provider namespaces override common/default values.
- [x] Runtime overrides retain highest precedence.
- [x] OpenAI, Perplexity, and Gemini receive equivalent normalized request values.
- [x] Perplexity sync and async request paths agree on `response_format`.
- [x] Built-in mode overrides deep-merge nested provider namespaces.
- [x] Unknown-key policy is documented and enforced consistently.
- [x] Matrix, inconsistency sidecar, tests, and P24 tracker agree.
