# P33 — Schema-Driven Config Defaults Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Drive every default config value — `thoth init`'s starter document, `ConfigSchema.get_defaults()`, and the per-provider configuration surface — from a single Pydantic v2 schema. Eliminate duplication between runtime defaults and the init template, and gain typechecker + warn-only diagnostic coverage for every key the project ships.

**Architecture:** A new `src/thoth/config_schema.py` module owns the typed schema (`ThothConfig` for runtime defaults; `ConfigOverlay`/`ProfileConfig`/`ModeConfig`/`UserConfigFile` for user-supplied shapes; `ProviderConfigBase` + per-provider subclasses for forward-looking provider fields). A new `src/thoth/_starter_data.py` holds the 6 starter profiles as seed data. The existing `src/thoth/commands.py:_build_starter_*()` writers become thin wrappers that walk the schema for in-starter fields and read structural prose from a writer-owned `WRITER_COMMENTS` table. Validation is **advisory, not enforced**: warn-only at runtime via `ConfigManager.validation_reports`, strict-mode in tests, with an `[experimental]` carve-out and a `--no-validate` CLI flag threaded as loader metadata.

**Tech Stack:** Python 3.11+, `pydantic>=2.12.5,<3` (already a transitive dep, promoted to direct), `tomlkit>=0.13`, `click>=8.3.3`, `pytest>=8.0`, existing thoth runtime.

**Spec:** `projects/P33-schema-driven-config-defaults.md` (committed in `824a757` + `3053942`). Read it first — every task here references concrete decisions and TS/T IDs from that file.

---

## File structure

| Action | Path | Responsibility |
|---|---|---|
| Modify | `pyproject.toml` | Add `pydantic>=2.12.5,<3` to `[project.dependencies]` |
| Create | `src/thoth/config_schema.py` | Pydantic models, `StarterField`, `make_partial`, `ConfigSchema` façade, `ValidationReport`/`ValidationWarning`, `_ROOT_SCHEMA`, `_no_validate` module global |
| Create | `src/thoth/_starter_data.py` | `STARTER_PROFILES` seed list (6 profiles, content frozen verbatim from today's `_build_starter_profiles()`) |
| Modify | `src/thoth/config.py:221-280` | `ConfigSchema.get_defaults()` body becomes `_ROOT_SCHEMA.model_dump(mode="python")` — signature unchanged |
| Modify | `src/thoth/config.py:283-371` | Add `ConfigManager.validation_reports: dict[str, ValidationReport]`; replace `_validate_config()` with per-layer warn-only validation; honor `_no_validate` |
| Modify | `src/thoth/commands.py:70-159` | Refactor `_build_starter_profiles()` and `_build_starter_document()` to use schema metadata + writer-owned `WRITER_COMMENTS` table, sourcing profile content from `STARTER_PROFILES` |
| Modify | `src/thoth/cli.py` | Add `--no-validate` global flag mirroring `--config`/`_apply_config_path()` pattern; thread as `config_schema._no_validate = True` |
| Create | `tests/test_p33_pydantic_dep.py` | TS00 — pyproject + uv.lock dependency metadata |
| Create | `tests/test_config_schema.py` | TS01 (smoke), TS02 (coverage), TS03 (partial regression), TS07 (provider fields), TS08 (mode/profile prompt surface) |
| Create | `tests/test_config_validate.py` | TS05 (warn-only `prompy_prefix`), TS06 (`[experimental]` carve-out) |
| Create | `tests/test_config_starter_round_trip.py` | TS04 (parsed-dict equality + strict validation + substring assertions) |
| Create | `tests/test_openai_config_consumption.py` | TS09 (provider temperature reaches request builder; profile mode `system_prompt` reaches `OpenAIProvider.submit`) |

Total new code: ~600 lines schema + ~150 lines seed data + ~100 lines starter-writer rewrite + ~700 lines tests. Total modified lines across config/cli: ~80.

---

## Tasks

### Task 1: Promote Pydantic to a direct dependency (P33-T00, TS00)

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/test_p33_pydantic_dep.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_p33_pydantic_dep.py`:

```python
"""P33-TS00: Dependency metadata test.

Pydantic must be a *direct* dependency, not only transitively pulled in by
openai. Schema-driven config relies on it; declaring it directly makes the
contract explicit and survives a future openai dep change.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"


def test_pydantic_declared_in_pyproject() -> None:
    data = tomllib.loads(PYPROJECT.read_text())
    deps = data["project"]["dependencies"]
    matches = [d for d in deps if d.lower().startswith("pydantic")]
    assert matches, (
        f"Expected a direct 'pydantic' entry in [project.dependencies]; "
        f"found only: {deps}"
    )
    spec = matches[0].lower().replace(" ", "")
    assert ">=2.12.5" in spec and "<3" in spec, (
        f"Expected pydantic>=2.12.5,<3 (got {matches[0]!r}); "
        f"P33 locks Pydantic v2.x, not v3."
    )


def test_pydantic_resolves_to_v2() -> None:
    import pydantic

    major = int(pydantic.VERSION.split(".")[0])
    assert major == 2, (
        f"Resolved Pydantic major version is {pydantic.VERSION}; "
        f"P33 requires v2.x."
    )
    assert sys.version_info >= (3, 11)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/stevemorin/c/thoth-worktrees/p33-schema-driven-config-defaults
uv run pytest tests/test_p33_pydantic_dep.py -v
```

Expected: `test_pydantic_declared_in_pyproject` FAILS — pydantic is currently only transitive. `test_pydantic_resolves_to_v2` may already pass (resolved transitively).

- [ ] **Step 3: Add the dependency via `uv add`**

```bash
uv add 'pydantic>=2.12.5,<3'
```

Expected: `pyproject.toml` `[project.dependencies]` gains `"pydantic>=2.12.5,<3"`; `uv.lock` updated (resolved version unchanged because Pydantic was already transitively present).

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_p33_pydantic_dep.py -v
```

Expected: PASS for both tests.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock tests/test_p33_pydantic_dep.py
git commit -m "feat(deps): promote pydantic to a direct dependency (P33-T00, TS00)"
```

---

### Task 2: Define `ThothConfig` and per-section sub-models (P33-T01, TS01 + TS02 default-paths)

This is the largest single task. It establishes the schema module and the `ThothConfig` model whose `model_dump()` reproduces today's `ConfigSchema.get_defaults()` byte-for-byte.

**Files:**
- Create: `src/thoth/config_schema.py`
- Create: `tests/test_config_schema.py`

- [ ] **Step 1: Write TS01 (smoke) and TS02 default-paths**

Create `tests/test_config_schema.py`:

```python
"""P33 schema tests.

Covers TS01 (smoke), TS02 (coverage), TS03 (partial regression),
TS07 (provider fields), TS08 (mode/profile prompt surface).

Strict-mode validation uses ConfigSchema.validate(..., strict=True).
"""

from __future__ import annotations

from typing import Any

import pytest


def _walk_leaves(d: dict[str, Any], prefix: tuple[str, ...] = ()) -> list[tuple[str, ...]]:
    """Yield every leaf path through a nested dict.

    A "leaf" is a path whose value is NOT a dict. Empty dicts (e.g.
    `modes = {}`) are considered leaves themselves.
    """
    out: list[tuple[str, ...]] = []
    for key, value in d.items():
        path = prefix + (key,)
        if isinstance(value, dict) and value:
            out.extend(_walk_leaves(value, path))
        else:
            out.append(path)
    return out


# ---------- TS01: smoke ----------

def test_thoth_config_constructs_with_no_overrides() -> None:
    from thoth.config_schema import ThothConfig

    cfg = ThothConfig()
    assert cfg.version == "2.0"


def test_get_defaults_equals_root_schema_dump() -> None:
    from thoth.config import ConfigSchema
    from thoth.config_schema import _ROOT_SCHEMA

    assert ConfigSchema.get_defaults() == _ROOT_SCHEMA.model_dump(mode="python")


# ---------- TS02: coverage (default paths only at this stage) ----------

def test_every_default_path_resolves_to_a_field() -> None:
    """Every leaf path in get_defaults() must resolve to a ThothConfig field.

    This is the test that catches the `prompy_prefix` typo class.
    """
    from thoth.config import ConfigSchema
    from thoth.config_schema import ThothConfig, resolve_path

    defaults = ConfigSchema.get_defaults()
    for path in _walk_leaves(defaults):
        # `resolve_path` returns a (model, field_name) tuple or raises
        # KeyError if the path doesn't reach a declared field.
        resolve_path(ThothConfig, path)
```

- [ ] **Step 2: Create `src/thoth/config_schema.py` skeleton**

Create the file with imports and section docstrings only (so subsequent steps add code in known locations):

```python
"""P33: schema for thoth.config.toml.

Single source of truth for runtime defaults, init starter content, and
warn-only diagnostic validation.

Three layers cooperate (P33):
  1. Schema (this module): types, defaults, per-field metadata, validation.
  2. Seed data (`_starter_data.py`): example profiles shown by `thoth init`.
  3. Writer (`commands.py`): tomlkit emitter; reads schema metadata for inline
     comments and the in-starter set.

Validation is advisory — extra fields produce warnings via the existing
config-warning channel but never raise. See P33's "Locked decision 4".
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any, Literal, get_args, get_origin

from pydantic import BaseModel, ConfigDict, Field, ValidationError, create_model

# Imported lazily where needed to avoid a top-level circular dep with
# `thoth.paths`.

# ---------------------------------------------------------------------------
# Module globals (set by the CLI `--no-validate` flag; mirrors the
# `_config_path` pattern in src/thoth/config.py:49).
# ---------------------------------------------------------------------------

_no_validate: bool = False


# ---------------------------------------------------------------------------
# Field-level helper: StarterField
# ---------------------------------------------------------------------------


def StarterField(default: Any = ..., *, default_factory: Any = None, **kwargs: Any) -> Any:
    """Pydantic Field that ships in the `thoth init` starter document.

    Forces an explicit `in_starter=True` flag in `json_schema_extra` so the
    starter writer (P33-T05) can iterate fields and emit only the in-starter
    set. Adding a new field forces an explicit decision: `StarterField(...)`
    ships in init; plain `Field(...)` does not.
    """
    extra = dict(kwargs.pop("json_schema_extra", {}) or {})
    extra["in_starter"] = True
    if default_factory is not None:
        return Field(default_factory=default_factory, json_schema_extra=extra, **kwargs)
    return Field(default, json_schema_extra=extra, **kwargs)


# ---------------------------------------------------------------------------
# Per-section sub-models — runtime defaults
# ---------------------------------------------------------------------------

# (Filled in next step.)


# ---------------------------------------------------------------------------
# Provider configs — forward-looking surface
# ---------------------------------------------------------------------------

# (Filled in Task 4.)


# ---------------------------------------------------------------------------
# Top-level model
# ---------------------------------------------------------------------------

# (Filled in next step.)


# ---------------------------------------------------------------------------
# Overlay / partial / user-file shapes
# ---------------------------------------------------------------------------

# (Filled in Task 3.)


# ---------------------------------------------------------------------------
# Validation report types
# ---------------------------------------------------------------------------

# (Filled in Task 5.)


# ---------------------------------------------------------------------------
# Path resolution helper (used by TS02)
# ---------------------------------------------------------------------------


def resolve_path(model: type[BaseModel], path: tuple[str, ...]) -> tuple[type[BaseModel], str]:
    """Walk a leaf path through nested BaseModel fields.

    Returns the (containing model, leaf field name) pair, or raises
    KeyError if the path does not resolve to a declared field. Used by
    TS02 to assert that every key in `get_defaults()` corresponds to a
    schema field.

    For `dict[str, X]`-typed fields (e.g. `modes`), the path is consumed
    one extra step: the dict key itself is treated as a wildcard, and
    resolution continues against the value type if it is a BaseModel.
    """
    if not path:
        raise KeyError("empty path")

    head, *rest = path
    fields = model.model_fields
    if head not in fields:
        raise KeyError(f"{model.__name__} has no field {head!r}")

    finfo = fields[head]
    annot = finfo.annotation

    if not rest:
        return model, head

    # Recurse into nested BaseModel
    if isinstance(annot, type) and issubclass(annot, BaseModel):
        return resolve_path(annot, tuple(rest))

    # Handle dict[str, X] — consume one extra key as wildcard
    origin = get_origin(annot)
    if origin is dict:
        args = get_args(annot)
        if len(args) == 2:
            value_type = args[1]
            if isinstance(value_type, type) and issubclass(value_type, BaseModel):
                # path was [head, dict_key, ...]; consume dict_key, recurse
                if len(rest) >= 2:
                    return resolve_path(value_type, tuple(rest[1:]))
                # path stops at the dict-keyed level (e.g. modes.thinking with
                # no further fields) — accept as resolved
                return model, head

    # Scalar / non-model annotation — leaf must be at this level
    raise KeyError(
        f"path {path!r} continues past leaf {head!r} (type {annot!r})",
    )


# ---------------------------------------------------------------------------
# Public façade: ConfigSchema
# ---------------------------------------------------------------------------

# (Filled in Task 5; for now define a placeholder so the module imports.)


# ---------------------------------------------------------------------------
# Singleton root model — set at module-import time
# ---------------------------------------------------------------------------

_ROOT_SCHEMA: "ThothConfig | None" = None  # set at end of this module
```

- [ ] **Step 3: Add per-section sub-models with default values byte-identical to `get_defaults()`**

In `src/thoth/config_schema.py`, replace the `# Per-section sub-models — runtime defaults` placeholder block with:

```python
class GeneralConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    default_project: str = StarterField("")
    default_mode: str = StarterField("default")


class PathsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_output_dir: str = StarterField("./research-outputs")
    checkpoint_dir: str = StarterField(
        default_factory=lambda: _checkpoint_dir_default(),
    )


def _checkpoint_dir_default() -> str:
    # Imported here to avoid top-of-module circular imports with thoth.paths.
    from thoth.paths import user_checkpoints_dir

    return str(user_checkpoints_dir())


class ExecutionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    poll_interval: int = StarterField(30)
    max_wait: int = StarterField(30)
    parallel_providers: bool = StarterField(True)
    retry_attempts: int = StarterField(3)
    # Advanced fields — Field(...), NOT StarterField — deliberately omitted
    # from `thoth init` per the P33 starter-subset contract.
    max_transient_errors: int = Field(5)
    auto_input: bool = StarterField(True)
    prompt_max_bytes: int = Field(1024 * 1024)
    cancel_upstream_on_interrupt: bool = Field(True)


class OutputConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    combine_reports: bool = StarterField(False)
    format: Literal["markdown", "json"] = StarterField("markdown")
    include_metadata: bool = StarterField(True)
    timestamp_format: str = StarterField("%Y-%m-%d_%H%M%S")


class ClarificationCLIConfig(BaseModel):
    """Settings for the CLI clarification flow (`thoth ask --clarify`).

    NOT shipped in `thoth init` (no StarterField anywhere). The defaults
    match today's `get_defaults()['clarification']['cli']` byte-for-byte.
    """

    model_config = ConfigDict(extra="forbid")
    provider: str = Field("openai")
    model: str = Field("gpt-4o-mini")
    temperature: float = Field(0.7)
    max_tokens: int = Field(500)
    system_prompt: str = Field(
        """I don't want you to follow the above question and instructions; I want you to tell me the ways this is unclear, point out any ambiguities or anything you don't understand. Follow that by asking questions to help clarify the ambiguous points. Once there are no more unclear, ambiguous or not understood portions, help me draft a clear version of the question/instruction."""
    )
    retry_attempts: int = Field(3)
    retry_delay: float = Field(2.0)


class ClarificationInteractiveConfig(BaseModel):
    """Settings for the interactive clarification flow.

    Same not-in-starter rule as `ClarificationCLIConfig`.
    """

    model_config = ConfigDict(extra="forbid")
    provider: str = Field("openai")
    model: str = Field("gpt-4o-mini")
    temperature: float = Field(0.7)
    max_tokens: int = Field(800)
    system_prompt: str = Field(
        """I don't want you to follow the above question and instructions; I want you to tell me the ways this is unclear, point out any ambiguities or anything you don't understand. Follow that by asking questions to help clarify the ambiguous points. Once there are no more unclear, ambiguous or not understood portions, help me draft a clear version of the question/instruction."""
    )
    retry_attempts: int = Field(3)
    retry_delay: float = Field(2.0)
    input_height: int = Field(6)
    max_input_height: int = Field(15)


class ClarificationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cli: ClarificationCLIConfig = Field(default_factory=ClarificationCLIConfig)
    interactive: ClarificationInteractiveConfig = Field(default_factory=ClarificationInteractiveConfig)


class ModeConfig(BaseModel):
    """Schema for `[modes.<name>]` and profile-overlaid mode tables.

    Every field is optional — modes are user-extensible and the runtime
    merges with BUILTIN_MODES (out of P33 scope). Includes the prompt-bearing
    and mode-control fields the runtime supports today.
    """

    model_config = ConfigDict(extra="forbid")
    provider: str | None = None
    model: str | None = None
    kind: Literal["immediate", "background"] | None = None
    system_prompt: str | None = None
    prompt_prefix: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    providers: list[str] | None = None
    parallel: bool | None = None
    previous: str | None = None
    next: str | None = None
    auto_input: bool | None = None
    description: str | None = None
```

- [ ] **Step 4: Add the top-level `ThothConfig` model and singleton wiring**

In `src/thoth/config_schema.py`, replace the `# Top-level model` and `# Singleton root model` placeholders:

```python
# At the end of the "Top-level model" section:

class ThothConfig(BaseModel):
    """Runtime defaults — what `ConfigSchema.get_defaults()` emits.

    Every field present here corresponds to a key in the historical
    `get_defaults()` dict. Adding a new key here adds a new default; it
    does not automatically appear in the `thoth init` starter doc unless
    declared with `StarterField(...)`.
    """

    model_config = ConfigDict(extra="forbid")
    version: str = "2.0"
    general: GeneralConfig = Field(default_factory=GeneralConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    # `providers` is filled in Task 4 — for now use a placeholder dict.
    providers: dict[str, dict[str, Any]] = Field(
        default_factory=lambda: {
            "openai": {"api_key": "${OPENAI_API_KEY}"},
            "perplexity": {"api_key": "${PERPLEXITY_API_KEY}"},
        }
    )
    clarification: ClarificationConfig = Field(default_factory=ClarificationConfig)
    modes: dict[str, ModeConfig] = Field(default_factory=dict)
```

And at the bottom of the file, replace the singleton placeholder:

```python
# Built once at import time. Tests assert this dump equals get_defaults().
_ROOT_SCHEMA = ThothConfig()
```

- [ ] **Step 5: Run TS01 to verify the smoke and dump-equality tests pass**

```bash
uv run pytest tests/test_config_schema.py::test_thoth_config_constructs_with_no_overrides tests/test_config_schema.py::test_get_defaults_equals_root_schema_dump -v
```

Expected: smoke test PASSES. The `test_get_defaults_equals_root_schema_dump` test FAILS — `get_defaults()` still returns the legacy hand-coded dict, which differs from `_ROOT_SCHEMA.model_dump()` only on the `providers` shape (legacy returns `{"openai": {"api_key": ...}}`, schema returns the same shape). If they actually match byte-identically already, the test passes — that's even better. Either way, do not modify `get_defaults()` body yet — that is Task 6.

If the test fails, capture the diff for Task 6 by running:

```bash
uv run python -c "
from thoth.config import ConfigSchema
from thoth.config_schema import _ROOT_SCHEMA
import json
legacy = ConfigSchema.get_defaults()
new = _ROOT_SCHEMA.model_dump(mode='python')
print('LEGACY KEYS:', sorted(legacy.keys()))
print('NEW KEYS:   ', sorted(new.keys()))
for k in sorted(set(legacy) | set(new)):
    if legacy.get(k) != new.get(k):
        print(f'DIFF at {k!r}:')
        print(f'  legacy: {legacy.get(k)}')
        print(f'  new:    {new.get(k)}')
"
```

Use the diff output to adjust default values in `config_schema.py` until the structure matches except for the `providers` block (which Task 4 finalizes). The dump-equality test only needs to pass after Task 6.

- [ ] **Step 6: Run TS02 default-paths to verify schema coverage**

```bash
uv run pytest tests/test_config_schema.py::test_every_default_path_resolves_to_a_field -v
```

Expected: PASS — every leaf path in today's `get_defaults()` resolves to a declared field.

If a path fails to resolve, the schema is missing a field. Add the field with the appropriate `StarterField` or `Field` until the test passes.

- [ ] **Step 7: Commit**

```bash
git add src/thoth/config_schema.py tests/test_config_schema.py
git commit -m "feat(config): introduce config_schema.py with ThothConfig models (P33-T01, TS01/TS02)"
```

---

### Task 3: Add `make_partial`, `ConfigOverlay`, `ProfileConfig`, `UserConfigFile` (P33-T02, TS03 + TS02 overlay-paths + TS08)

This task adds the auto-derived partial helper, the user-only overlay shape (which permits P21 fields like `general.default_profile`), and the document-level `UserConfigFile` schema.

**Files:**
- Modify: `src/thoth/config_schema.py`
- Modify: `tests/test_config_schema.py`

- [ ] **Step 1: Write TS03 (partial regression) and TS08 (mode/profile prompt surface)**

Append to `tests/test_config_schema.py`:

```python
# ---------- TS03: make_partial regression ----------


def test_make_partial_keeps_field_set() -> None:
    """make_partial(ThothConfig) must produce a model with the same field
    set as ThothConfig, all marked optional with `None` defaults."""
    from thoth.config_schema import PartialThothConfig, ThothConfig

    src_fields = set(ThothConfig.model_fields.keys())
    partial_fields = set(PartialThothConfig.model_fields.keys())
    assert src_fields == partial_fields, (
        f"PartialThothConfig field set drifted from ThothConfig: "
        f"missing {src_fields - partial_fields}, extra {partial_fields - src_fields}"
    )

    for name, finfo in PartialThothConfig.model_fields.items():
        # Each field must have a `None` default, signalling "unset = ok"
        assert finfo.default is None or finfo.default_factory is not None, (
            f"PartialThothConfig.{name} should default to None or a factory; "
            f"got {finfo.default!r}"
        )


def test_make_partial_constructs_empty() -> None:
    from thoth.config_schema import PartialThothConfig

    PartialThothConfig()  # must not raise


# ---------- TS02: overlay-path coverage ----------


def test_user_only_overlay_paths_resolve() -> None:
    """Valid P21 user-only fields must resolve through ConfigOverlay /
    ProfileConfig, even though they are NOT part of get_defaults()."""
    from thoth.config_schema import ConfigOverlay, ProfileConfig, resolve_path

    # general.default_profile and general.prompt_prefix are P21 user-only
    # overlay fields — not emitted by get_defaults() but valid in user TOML.
    resolve_path(ConfigOverlay, ("general", "default_profile"))
    resolve_path(ConfigOverlay, ("general", "prompt_prefix"))

    # modes.<name>.system_prompt and modes.<name>.prompt_prefix
    resolve_path(ConfigOverlay, ("modes", "thinking", "system_prompt"))
    resolve_path(ConfigOverlay, ("modes", "thinking", "prompt_prefix"))

    # Profile-root prompt_prefix
    resolve_path(ProfileConfig, ("prompt_prefix",))


# ---------- TS08: mode/profile prompt surface validates ----------


def test_mode_table_with_prompts_validates() -> None:
    from thoth.config_schema import ModeConfig

    ModeConfig(system_prompt="Be precise", prompt_prefix="Cite sources")


def test_profile_with_root_and_nested_prompts_validates() -> None:
    from thoth.config_schema import ProfileConfig

    profile = ProfileConfig(
        prompt_prefix="Be thorough",
        modes={"thinking": {"system_prompt": "Step by step"}},
    )
    assert profile.prompt_prefix == "Be thorough"
    assert profile.modes is not None and "thinking" in profile.modes


def test_user_file_with_full_p21_shape_validates() -> None:
    from thoth.config_schema import UserConfigFile

    doc = {
        "general": {
            "default_project": "daily-notes",
            "default_profile": "fast",
            "prompt_prefix": "Cite sources",
        },
        "modes": {"thinking": {"system_prompt": "Be careful"}},
        "profiles": {
            "fast": {
                "prompt_prefix": "Be quick",
                "modes": {"thinking": {"system_prompt": "Profile prompt"}},
            }
        },
    }
    UserConfigFile.model_validate(doc)


def test_typo_at_each_overlay_level_raises_in_strict() -> None:
    from pydantic import ValidationError

    from thoth.config_schema import ProfileConfig, UserConfigFile

    # Top-level [general] typo
    with pytest.raises(ValidationError):
        UserConfigFile.model_validate({"general": {"prompy_prefix": "x"}})

    # Profile-root typo
    with pytest.raises(ValidationError):
        ProfileConfig.model_validate({"prompy_prefix": "x"})

    # Profile.modes.<x> typo
    with pytest.raises(ValidationError):
        UserConfigFile.model_validate(
            {"profiles": {"fast": {"modes": {"thinking": {"system_prompy": "x"}}}}}
        )
```

- [ ] **Step 2: Run the new tests to verify they fail**

```bash
uv run pytest tests/test_config_schema.py -v -k "make_partial or overlay_paths_resolve or with_prompts_validates or with_root_and_nested or with_full_p21 or typo_at_each"
```

Expected: import errors / FAILS — `PartialThothConfig`, `ConfigOverlay`, `ProfileConfig`, `UserConfigFile` don't exist yet.

- [ ] **Step 3: Add `make_partial` helper**

In `src/thoth/config_schema.py`, in the "Overlay / partial / user-file shapes" section, add:

```python
def make_partial(model: type[BaseModel], *, suffix: str = "Partial") -> type[BaseModel]:
    """Return a new BaseModel subclass with every field made optional.

    Recursively partials nested BaseModel-typed fields. `dict[str, BaseModel]`
    fields are kept as-is — their value type is already optional-shaped (e.g.
    `ModeConfig` has every field optional).

    The returned model has `model_config = ConfigDict(extra="forbid")` so
    it still catches typos in keys it knows about.
    """
    new_fields: dict[str, tuple[Any, Any]] = {}
    for name, finfo in model.model_fields.items():
        annotation = finfo.annotation

        # If the field type is itself a BaseModel, recurse.
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            sub_partial = make_partial(annotation, suffix=suffix)
            new_fields[name] = (sub_partial | None, None)
            continue

        # Otherwise wrap whatever it was in Optional with None default.
        new_fields[name] = (annotation | None, None)

    return create_model(
        f"{model.__name__}{suffix}",
        __config__=ConfigDict(extra="forbid"),
        **new_fields,
    )


PartialThothConfig: type[BaseModel] = make_partial(ThothConfig)
"""Mechanically-derived runtime partial — used for CLI/profile-overlay
internals and as the alignment baseline for TS03."""
```

- [ ] **Step 4: Add `GeneralOverlay` for P21 user-only fields**

In `src/thoth/config_schema.py`, in the "Overlay / partial / user-file shapes" section (after `make_partial`):

```python
class GeneralOverlay(BaseModel):
    """`[general]` table as it can appear in user/profile/cli overlays.

    Mirrors `GeneralConfig`'s fields (all optional) plus the P21 user-only
    fields that are NOT part of `get_defaults()`.
    """

    model_config = ConfigDict(extra="forbid")
    # Mirror of GeneralConfig fields:
    default_project: str | None = None
    default_mode: str | None = None
    # P21 user-only overlay fields:
    default_profile: str | None = None
    prompt_prefix: str | None = None
```

Now add a regression test in `tests/test_config_schema.py` to catch drift between `GeneralConfig` and `GeneralOverlay`:

```python
def test_general_overlay_mirrors_general_config_fields() -> None:
    from thoth.config_schema import GeneralConfig, GeneralOverlay

    runtime = set(GeneralConfig.model_fields.keys())
    overlay = set(GeneralOverlay.model_fields.keys())
    # Every runtime field must exist in the overlay.
    missing = runtime - overlay
    assert not missing, (
        f"GeneralOverlay is missing fields present in GeneralConfig: {missing}. "
        f"Add them as `<name>: T | None = None` to GeneralOverlay."
    )
    # Overlay-only fields are documented:
    overlay_only = overlay - runtime
    assert overlay_only == {"default_profile", "prompt_prefix"}, (
        f"Unexpected overlay-only fields: {overlay_only}. "
        f"Update this test if you intentionally added a new P21-style field."
    )
```

- [ ] **Step 5: Add `ConfigOverlay`, `ProfileConfig`, `UserConfigFile`**

In `src/thoth/config_schema.py`, after `GeneralOverlay`, add:

```python
class ConfigOverlay(BaseModel):
    """A user/profile/cli config layer.

    Every runtime-default field is optional (mirror of `make_partial(ThothConfig)`)
    and `general` is replaced by `GeneralOverlay` so P21 user-only fields are
    accepted.
    """

    model_config = ConfigDict(extra="forbid")
    version: str | None = None
    general: GeneralOverlay | None = None
    paths: make_partial(PathsConfig) | None = None  # type: ignore[valid-type]
    execution: make_partial(ExecutionConfig) | None = None  # type: ignore[valid-type]
    output: make_partial(OutputConfig) | None = None  # type: ignore[valid-type]
    providers: dict[str, dict[str, Any]] | None = None  # finalized in Task 4
    clarification: make_partial(ClarificationConfig) | None = None  # type: ignore[valid-type]
    modes: dict[str, ModeConfig] | None = None


class ProfileConfig(ConfigOverlay):
    """Profile overlay schema.

    Same as `ConfigOverlay` plus a profile-root `prompt_prefix` (P21).
    """

    prompt_prefix: str | None = None


class UserConfigFile(ConfigOverlay):
    """Top-level shape of an actual `thoth.config.toml` on disk.

    `ConfigOverlay` fields plus a `profiles` super-table (validated by
    `ProfileConfig`) and an `experimental` carve-out (the only field that
    permits arbitrary keys).
    """

    profiles: dict[str, ProfileConfig] = Field(default_factory=dict)
    experimental: dict[str, Any] = Field(default_factory=dict)
```

> **Type-checker note:** Pydantic v2 supports dynamic types created by `create_model()` as field annotations, but ty/mypy may flag them. The `# type: ignore[valid-type]` comments are intentional. If `ty` rejects them, add the same comment until ty learns about Pydantic's dynamic types.

- [ ] **Step 6: Run all schema tests added so far**

```bash
uv run pytest tests/test_config_schema.py -v
```

Expected: all of TS01, TS02 (default + overlay paths), TS03, TS08 PASS.

If `test_user_only_overlay_paths_resolve` fails on `ConfigOverlay → modes → thinking → system_prompt`, verify `resolve_path` correctly recurses through the `dict[str, ModeConfig]` annotation. The helper in Task 2 Step 2 handles this case.

- [ ] **Step 7: Commit**

```bash
git add src/thoth/config_schema.py tests/test_config_schema.py
git commit -m "feat(config): add make_partial, ConfigOverlay, ProfileConfig, UserConfigFile (P33-T02, TS03/TS08)"
```

---

### Task 4: Add `ProviderConfigBase` + per-provider configs (P33-T06, TS07)

**Files:**
- Modify: `src/thoth/config_schema.py`
- Modify: `tests/test_config_schema.py`

- [ ] **Step 1: Write TS07 (provider-specific schema fields)**

Append to `tests/test_config_schema.py`:

```python
# ---------- TS07: provider-specific schema fields ----------


def test_openai_provider_temperature_validates() -> None:
    from thoth.config_schema import OpenAIConfig

    OpenAIConfig(api_key="${OPENAI_API_KEY}", temperature=0.7)


def test_perplexity_provider_search_context_size_validates() -> None:
    from thoth.config_schema import PerplexityConfig

    PerplexityConfig(api_key="${PERPLEXITY_API_KEY}", search_context_size="high")


def test_unknown_openai_field_rejected() -> None:
    from pydantic import ValidationError

    from thoth.config_schema import OpenAIConfig

    with pytest.raises(ValidationError) as exc:
        OpenAIConfig(api_key="${OPENAI_API_KEY}", bogus=1)
    assert "bogus" in str(exc.value)


def test_perplexity_rejects_openai_specific_fields() -> None:
    from pydantic import ValidationError

    from thoth.config_schema import PerplexityConfig

    # `organization` is OpenAI-specific; Perplexity must reject it.
    with pytest.raises(ValidationError) as exc:
        PerplexityConfig(api_key="${PERPLEXITY_API_KEY}", organization="acme")
    assert "organization" in str(exc.value)


def test_providers_config_holds_typed_subsections() -> None:
    from thoth.config_schema import ProvidersConfig

    p = ProvidersConfig()
    assert p.openai.api_key == "${OPENAI_API_KEY}"
    assert p.perplexity.api_key == "${PERPLEXITY_API_KEY}"
```

- [ ] **Step 2: Run TS07 to verify it fails**

```bash
uv run pytest tests/test_config_schema.py -v -k "openai_provider or perplexity_provider or unknown_openai or perplexity_rejects or providers_config_holds"
```

Expected: import errors — `OpenAIConfig`, `PerplexityConfig`, `ProvidersConfig` don't exist yet.

- [ ] **Step 3: Add provider config classes**

In `src/thoth/config_schema.py`, in the "Provider configs" section (between per-section sub-models and `ThothConfig`), add:

```python
class ProviderConfigBase(BaseModel):
    """Common provider config surface — shared by all providers.

    Renamed from `ProviderBase` per P33 review remediation #7 to avoid
    confusion with the runtime `ResearchProvider` class in
    `src/thoth/providers/base.py`.
    """

    model_config = ConfigDict(extra="forbid")
    api_key: str
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    timeout: float | None = None
    base_url: str | None = None


class OpenAIConfig(ProviderConfigBase):
    """OpenAI provider config (api_key + organization + base fields)."""

    organization: str | None = None


class PerplexityConfig(ProviderConfigBase):
    """Perplexity provider config (api_key + search_context_size + base fields)."""

    search_context_size: Literal["low", "medium", "high"] | None = None


class GeminiConfig(ProviderConfigBase):
    """Gemini provider config — placeholder for P28.

    No Gemini-specific fields yet; subclassing makes the addition site
    obvious when P28 lands.
    """

    pass


class ProvidersConfig(BaseModel):
    """`[providers]` super-table — typed per-provider section."""

    model_config = ConfigDict(extra="forbid")
    openai: OpenAIConfig = StarterField(
        default_factory=lambda: OpenAIConfig(api_key="${OPENAI_API_KEY}"),
    )
    perplexity: PerplexityConfig = StarterField(
        default_factory=lambda: PerplexityConfig(api_key="${PERPLEXITY_API_KEY}"),
    )
    # Gemini intentionally NOT in starter doc — P28 not landed yet.
```

- [ ] **Step 4: Replace the `providers` placeholder on `ThothConfig`**

In `src/thoth/config_schema.py`, find the `ThothConfig` class and replace the placeholder `providers: dict[str, dict[str, Any]] = Field(...)` with:

```python
    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)
```

Keep all other fields intact.

Also update `ConfigOverlay.providers` to use `make_partial(ProvidersConfig)`:

Find the `providers: dict[str, dict[str, Any]] | None = None` line in `ConfigOverlay` and replace with:

```python
    providers: make_partial(ProvidersConfig) | None = None  # type: ignore[valid-type]
```

- [ ] **Step 5: Run all schema tests (TS01–TS03, TS07, TS08)**

```bash
uv run pytest tests/test_config_schema.py -v
```

Expected: all PASS. Note that `test_get_defaults_equals_root_schema_dump` still fails until Task 6.

- [ ] **Step 6: Verify the historical defaults dict still matches the schema dump structurally**

```bash
uv run python -c "
from thoth.config import ConfigSchema
from thoth.config_schema import _ROOT_SCHEMA
legacy = ConfigSchema.get_defaults()
new = _ROOT_SCHEMA.model_dump(mode='python')
diff = {k: (legacy.get(k), new.get(k)) for k in set(legacy)|set(new) if legacy.get(k) != new.get(k)}
print('STILL DIFFERENT:', list(diff.keys()))
import json; print(json.dumps({k: v for k, v in diff.items()}, indent=2, default=repr))
"
```

Expected: only `providers` differs in shape — legacy has `{"openai": {"api_key": "..."}, "perplexity": {"api_key": "..."}}`, schema dump has the same shape (since `OpenAIConfig` only emits non-None fields when dumped via `mode="python"` if `exclude_none` is set, or includes None fields if not).

If the schema dump emits `"model": null, "temperature": null, ...` keys that legacy lacks, decide one of:
1. Use `model_dump(exclude_none=True)` in `_ROOT_SCHEMA.model_dump()` for the comparison **and** in `get_defaults()` (Task 6).
2. Set the optional provider fields to `Field(default=...)` with concrete defaults that match legacy.

**Decision: use `exclude_none=True`.** Add a constant:

```python
_ROOT_SCHEMA = ThothConfig()
_ROOT_DEFAULTS_DICT = _ROOT_SCHEMA.model_dump(mode="python", exclude_none=True)
```

…and update `test_get_defaults_equals_root_schema_dump` to compare against `_ROOT_DEFAULTS_DICT`:

```python
def test_get_defaults_equals_root_schema_dump() -> None:
    from thoth.config import ConfigSchema
    from thoth.config_schema import _ROOT_DEFAULTS_DICT

    assert ConfigSchema.get_defaults() == _ROOT_DEFAULTS_DICT
```

- [ ] **Step 7: Commit**

```bash
git add src/thoth/config_schema.py tests/test_config_schema.py
git commit -m "feat(config): add ProviderConfigBase, OpenAIConfig, PerplexityConfig, GeminiConfig (P33-T06, TS07)"
```

---

### Task 5: Add `ValidationReport`, `ConfigSchema.validate()`, and the `--no-validate` flag (P33-T03, TS05 + TS06)

**Files:**
- Modify: `src/thoth/config_schema.py`
- Modify: `src/thoth/cli.py`
- Create: `tests/test_config_validate.py`

- [ ] **Step 1: Write TS05 (warn-only) and TS06 (`[experimental]` carve-out)**

Create `tests/test_config_validate.py`:

```python
"""P33 validation behavior tests.

TS05: typos produce warnings (one per typo) but never raise.
TS06: `[experimental]` super-table accepts arbitrary keys.
"""

from __future__ import annotations

import pytest


# ---------- TS05: warn-only behavior ----------


def test_prompy_prefix_typo_produces_one_warning_no_raise() -> None:
    from thoth.config_schema import ConfigSchema

    data = {"general": {"prompy_prefix": "x"}}
    report = ConfigSchema.validate(data, layer="user")
    assert len(report.warnings) == 1
    w = report.warnings[0]
    assert w.path == "general.prompy_prefix"
    assert "extra" in w.message.lower() or "unknown" in w.message.lower()


def test_validate_does_not_raise_on_unknown_field() -> None:
    from thoth.config_schema import ConfigSchema

    # The whole point: validation reports, never raises.
    ConfigSchema.validate({"general": {"prompy_prefix": "x"}}, layer="user")


def test_no_validate_global_suppresses_warnings() -> None:
    from thoth import config_schema as cs

    cs._no_validate = True
    try:
        report = cs.ConfigSchema.validate(
            {"general": {"prompy_prefix": "x"}}, layer="user"
        )
        assert report.warnings == []
    finally:
        cs._no_validate = False


def test_strict_mode_raises_on_unknown_field() -> None:
    from pydantic import ValidationError

    from thoth.config_schema import ConfigSchema

    with pytest.raises(ValidationError):
        ConfigSchema.validate(
            {"general": {"prompy_prefix": "x"}}, layer="user", strict=True
        )


# ---------- TS06: [experimental] carve-out ----------


def test_experimental_table_accepts_arbitrary_keys() -> None:
    from thoth.config_schema import ConfigSchema

    data = {
        "experimental": {
            "anything": True,
            "nested": {"deep": {"keys": [1, 2, 3]}},
            "weird_thing": {"plugin_name": "foo"},
        }
    }
    report = ConfigSchema.validate(data, layer="user")
    assert report.warnings == []


def test_experimental_in_strict_mode_also_accepts() -> None:
    from thoth.config_schema import ConfigSchema

    # Strict mode doesn't tighten the [experimental] carve-out.
    ConfigSchema.validate(
        {"experimental": {"plugin_name": "foo"}}, layer="user", strict=True
    )
```

- [ ] **Step 2: Run TS05/TS06 to verify failure**

```bash
uv run pytest tests/test_config_validate.py -v
```

Expected: all FAIL — `ConfigSchema.validate` doesn't exist yet.

- [ ] **Step 3: Add `ValidationWarning`, `ValidationReport`, and `ConfigSchema.validate()`**

In `src/thoth/config_schema.py`, in the "Validation report types" section, add:

```python
@dataclass(frozen=True)
class ValidationWarning:
    """A single advisory finding from schema validation.

    Attributes:
        layer: which load layer surfaced this — `user`, `project`, `profile`,
            `cli`, or `defaults`.
        path: dotted field path (e.g. `general.prompy_prefix`).
        message: human-readable description.
        value_preview: short repr of the offending value (≤80 chars), or None.
    """

    layer: str
    path: str
    message: str
    value_preview: str | None = None


@dataclass(frozen=True)
class ValidationReport:
    """Result of `ConfigSchema.validate()`.

    Empty `warnings` list means "no diagnostic findings" — does NOT mean
    "fully valid", because validation is advisory.
    """

    warnings: list[ValidationWarning] = dc_field(default_factory=list)
```

In the "Public façade" section, add:

```python
class ConfigSchema:
    """Public façade for the schema module.

    Stable API surface — `get_defaults()` signature unchanged. `validate()`,
    `starter_keys()`, and `model()` are new and additive.
    """

    @staticmethod
    def get_defaults() -> dict[str, Any]:
        """Return the default configuration dict.

        After P33-T04, the body of `ConfigSchema.get_defaults()` in
        `src/thoth/config.py` proxies here.
        """
        return _ROOT_DEFAULTS_DICT

    @staticmethod
    def model() -> type[BaseModel]:
        """Return the typed runtime model class."""
        return ThothConfig

    @staticmethod
    def starter_keys() -> set[tuple[str, ...]]:
        """Return the set of leaf paths that ship in `thoth init`.

        Walks every model field and yields paths whose
        `json_schema_extra["in_starter"]` is truthy. Used by the writer
        and by the round-trip test.
        """
        result: set[tuple[str, ...]] = set()
        _collect_starter_paths(ThothConfig, prefix=(), out=result)
        return result

    @staticmethod
    def validate(
        data: dict[str, Any],
        *,
        layer: str = "user",
        strict: bool = False,
    ) -> ValidationReport:
        """Validate a config dict against the schema.

        - `layer="user"` validates against `UserConfigFile` (full document
          including `[profiles]` and `[experimental]`).
        - `layer="profile"` validates against `ProfileConfig` (a single
          profile overlay).
        - `layer="cli"` / `layer="env"` validates against `ConfigOverlay`
          (no `[profiles]` allowed at this layer).
        - `layer="defaults"` validates against `ThothConfig` (full defaults).

        With `strict=True`, raises `pydantic.ValidationError` on the first
        error. With `strict=False` (default), collects all errors as
        `ValidationWarning`s and returns them. If module global
        `_no_validate` is True, returns an empty report immediately.
        """
        if _no_validate:
            return ValidationReport()

        target = _layer_to_model(layer)

        if strict:
            target.model_validate(data)
            return ValidationReport()

        try:
            target.model_validate(data)
        except ValidationError as exc:
            warnings = [_pydantic_error_to_warning(layer, e) for e in exc.errors()]
            return ValidationReport(warnings=warnings)
        return ValidationReport()


def _layer_to_model(layer: str) -> type[BaseModel]:
    if layer == "user" or layer == "project":
        return UserConfigFile
    if layer == "profile":
        return ProfileConfig
    if layer == "cli" or layer == "env":
        return ConfigOverlay
    if layer == "defaults":
        return ThothConfig
    raise ValueError(f"unknown validation layer {layer!r}")


def _pydantic_error_to_warning(layer: str, error: dict[str, Any]) -> ValidationWarning:
    loc = error.get("loc", ())
    path = ".".join(str(p) for p in loc)
    msg = error.get("msg", "validation error")
    raw_value = error.get("input", None)
    preview: str | None = None
    if raw_value is not None:
        s = repr(raw_value)
        preview = s if len(s) <= 80 else s[:77] + "..."
    return ValidationWarning(layer=layer, path=path, message=msg, value_preview=preview)


def _collect_starter_paths(
    model: type[BaseModel],
    prefix: tuple[str, ...],
    out: set[tuple[str, ...]],
) -> None:
    for name, finfo in model.model_fields.items():
        extra = (finfo.json_schema_extra or {}) if isinstance(finfo.json_schema_extra, dict) else {}
        is_starter = bool(extra.get("in_starter"))
        path = prefix + (name,)
        annotation = finfo.annotation
        # Recurse into nested BaseModel only if THIS field is in_starter
        # (otherwise the whole subtree is excluded from the starter doc).
        if is_starter and isinstance(annotation, type) and issubclass(annotation, BaseModel):
            _collect_starter_paths(annotation, path, out)
        elif is_starter:
            out.add(path)
```

> **Note:** `ValidationError` import was already added at the top of the file in Task 2 Step 2.

- [ ] **Step 4: Run TS05/TS06**

```bash
uv run pytest tests/test_config_validate.py -v
```

Expected: all PASS.

- [ ] **Step 5: Wire the `--no-validate` flag into the CLI**

In `src/thoth/cli.py`, find the `_apply_config_path` helper (around line 93) and add a sibling helper:

```python
def _apply_no_validate(no_validate: bool) -> None:
    """Mirror of `_apply_config_path` for the `--no-validate` flag.

    Sets the module-global `_no_validate` in `thoth.config_schema` so that
    `ConfigSchema.validate()` short-circuits to an empty report. This is
    *loader metadata*, NOT a config root key — it is never threaded into
    `cli_args` and `ConfigManager.load_all_layers` rejects it as a config
    root by virtue of the existing `allowed_top_level` defense in
    `config.py:306`.
    """
    if no_validate:
        from thoth import config_schema as _thoth_config_schema

        _thoth_config_schema._no_validate = True
```

Find the top-level `cli` group (search for `def cli(` in `src/thoth/cli.py`). Add a `--no-validate` Click option to its decorator stack and a corresponding parameter to its signature. Mirror the pattern used for `config_path`:

```python
@click.option(
    "--no-validate",
    is_flag=True,
    default=False,
    help="Skip schema validation of config files (debug/triage). Validation is "
         "advisory; warnings normally print but do not block execution.",
)
# ... (existing decorators) ...
def cli(
    ctx,
    # ... existing params ...
    no_validate,
    # ... existing params ...
):
    """Top-level CLI entry."""
    # Apply BEFORE config loading.
    _apply_no_validate(no_validate)
    _apply_config_path(config_path)
    # ... rest unchanged ...
```

> **Implementation note for the engineer:** if `cli.py`'s decorator stack is built from `_RESEARCH_OPTIONS` rather than inline `@click.option` calls, append `(("--no-validate",), {"is_flag": True, "default": False, "help": "..."})` to the `_RESEARCH_OPTIONS` list in `src/thoth/cli_subcommands/_options.py:25`. The flag will then appear on every command that uses `_research_options` — that's intentional, since validation is per-command.

- [ ] **Step 6: Add a CLI integration test for `--no-validate`**

Append to `tests/test_config_validate.py`:

```python
# ---------- --no-validate CLI integration ----------


def test_no_validate_flag_suppresses_runtime_warnings(tmp_path) -> None:
    """`thoth --no-validate ...` must not surface warnings for config typos."""
    import subprocess

    cfg = tmp_path / "thoth.config.toml"
    cfg.write_text(
        '\n'.join(
            [
                'version = "2.0"',
                "[general]",
                'prompy_prefix = "x"  # typo',
            ]
        )
    )

    # Invoke the CLI with --no-validate; assert no "prompy_prefix" warning
    # appears on stdout/stderr. (`--config` is the only mechanism for picking
    # an alternate config file; there is no `THOTH_CONFIG` env var.)
    result = subprocess.run(
        ["uv", "run", "thoth", "--no-validate", "--config", str(cfg), "status"],
        capture_output=True,
        text=True,
    )
    combined = result.stdout + result.stderr
    assert "prompy_prefix" not in combined, (
        f"--no-validate should suppress validation warnings; saw: {combined}"
    )


def test_validate_flag_omitted_surfaces_warning(tmp_path) -> None:
    """Without --no-validate, the same typo should warn on stdout."""
    import subprocess

    cfg = tmp_path / "thoth.config.toml"
    cfg.write_text(
        '\n'.join(
            [
                'version = "2.0"',
                "[general]",
                'prompy_prefix = "x"',
            ]
        )
    )

    result = subprocess.run(
        ["uv", "run", "thoth", "--config", str(cfg), "status"],
        capture_output=True,
        text=True,
    )
    # NOTE: this test depends on Task 8 (runtime hookup). Until Task 8 is
    # complete, mark it expected-fail.
    pytest.xfail("runtime hookup not yet wired — Task 8 (P33-T07) gates this")
    combined = result.stdout + result.stderr
    assert "prompy_prefix" in combined
```

- [ ] **Step 7: Run validation tests**

```bash
uv run pytest tests/test_config_validate.py -v
```

Expected: TS05/TS06 PASS; the `--no-validate` CLI test passes (suppresses); the `validate flag omitted` test xfails (gated by Task 8).

- [ ] **Step 8: Commit**

```bash
git add src/thoth/config_schema.py src/thoth/cli.py src/thoth/cli_subcommands/_options.py tests/test_config_validate.py
git commit -m "feat(config): add ValidationReport, ConfigSchema.validate(), --no-validate flag (P33-T03, TS05/TS06)"
```

---

### Task 6: Refactor `ConfigSchema.get_defaults()` body to derive from the schema (P33-T04)

This is a single-statement change; the test surface is what verifies it.

**Files:**
- Modify: `src/thoth/config.py:225-280`

- [ ] **Step 1: Snapshot the current `get_defaults()` output**

```bash
uv run python -c "
import json
from thoth.config import ConfigSchema
print(json.dumps(ConfigSchema.get_defaults(), indent=2, default=str))
" > /tmp/p33_legacy_defaults.json
wc -l /tmp/p33_legacy_defaults.json
```

Expected: a non-empty JSON file with the legacy defaults dict. Keep this file as a one-shot reference for diffing.

- [ ] **Step 2: Replace the `get_defaults()` body**

In `src/thoth/config.py`, find the `ConfigSchema` class around line 221 and replace the entire `get_defaults` method body with:

```python
class ConfigSchema:
    """Configuration schema and defaults"""

    @staticmethod
    def get_defaults() -> dict[str, Any]:
        """Return default configuration.

        P33: derived from the typed schema in `thoth.config_schema`. Signature
        unchanged from pre-P33 callers' perspective.
        """
        from thoth.config_schema import _ROOT_DEFAULTS_DICT

        # Defensive copy so callers can mutate freely without poisoning the
        # singleton. This matches the pre-P33 contract: get_defaults() always
        # returned a fresh dict.
        import copy
        return copy.deepcopy(_ROOT_DEFAULTS_DICT)
```

Delete the entire literal-dict body that was there before. The class becomes a thin façade.

- [ ] **Step 3: Verify byte-identical output against the snapshot**

```bash
uv run python -c "
import json
from thoth.config import ConfigSchema
new = ConfigSchema.get_defaults()
old = json.load(open('/tmp/p33_legacy_defaults.json'))
def normalize(d):
    if isinstance(d, dict):
        return {k: normalize(v) for k, v in sorted(d.items())}
    if isinstance(d, list):
        return [normalize(x) for x in d]
    return d
assert normalize(new) == normalize(old), 'DEFAULTS DIFFER:\n' + json.dumps(
    {k: (old.get(k), new.get(k)) for k in set(old)|set(new) if old.get(k) != new.get(k)},
    indent=2, default=str
)
print('OK: defaults match snapshot')
"
```

Expected: prints `OK: defaults match snapshot`. If a diff is reported, the schema has a default value that doesn't match the legacy literal. Fix the schema (in `config_schema.py`) — not the legacy snapshot.

- [ ] **Step 4: Run TS01 dump-equality test**

```bash
uv run pytest tests/test_config_schema.py::test_get_defaults_equals_root_schema_dump -v
```

Expected: PASS.

- [ ] **Step 5: Run the full existing test suite to confirm no regressions**

```bash
uv run pytest -q
```

Expected: all green (excluding `extended` and `live_api` markers, which are gated). Pay particular attention to `test_config*.py` — these have the highest chance of catching a defaults-shape regression.

- [ ] **Step 6: Run thoth_test integration suite**

```bash
./thoth_test -r --skip-interactive -q
```

Expected: 76 passed, 1 skipped, 0 failed (or matching baseline).

- [ ] **Step 7: Commit**

```bash
git add src/thoth/config.py
git commit -m "refactor(config): derive ConfigSchema.get_defaults() from typed schema (P33-T04)"
```

---

### Task 7: Extract `STARTER_PROFILES` and refactor `_build_starter_*()` (P33-T05, TS04)

**Files:**
- Create: `src/thoth/_starter_data.py`
- Modify: `src/thoth/commands.py:36-159`
- Create: `tests/test_config_starter_round_trip.py`

- [ ] **Step 1: Write TS04 (round-trip test)**

Create `tests/test_config_starter_round_trip.py`:

```python
"""P33-TS04: starter document round-trip test.

Position C — three layers:
  L2 (parsed-dict equality, split projection):
    - non-`profiles` root tables == get_defaults() projected to starter_keys()
    - parsed `profiles` == STARTER_PROFILES
  L3 (strict-mode validation): full doc validates through UserConfigFile
  L1 (substring assertions): rendered TOML contains key section markers
"""

from __future__ import annotations

import tomlkit


def test_starter_doc_round_trips() -> None:
    from thoth.commands import _build_starter_document
    from thoth.config import ConfigSchema
    from thoth.config_schema import ConfigSchema as CSNew  # public façade
    from thoth._starter_data import STARTER_PROFILES

    doc = _build_starter_document()
    rendered = tomlkit.dumps(doc)
    parsed = tomlkit.loads(rendered).unwrap()

    # ---- L2a: non-profiles root tables ----
    starter_keys = CSNew.starter_keys()  # set of tuple paths
    parsed_no_profiles = {k: v for k, v in parsed.items() if k != "profiles"}
    defaults = ConfigSchema.get_defaults()

    def project(d: dict, paths: set) -> dict:
        out: dict = {}
        for path in paths:
            cur_in = d
            cur_out = out
            for key in path[:-1]:
                if not isinstance(cur_in, dict) or key not in cur_in:
                    cur_in = None
                    break
                cur_in = cur_in[key]
                cur_out = cur_out.setdefault(key, {})
            if cur_in is None:
                continue
            leaf = path[-1]
            if isinstance(cur_in, dict) and leaf in cur_in:
                cur_out[leaf] = cur_in[leaf]
        return out

    expected = project(defaults, starter_keys)
    actual = project(parsed_no_profiles, starter_keys)
    assert actual == expected, (
        f"Starter doc non-profiles roots disagree with get_defaults() "
        f"projected to starter_keys().\n"
        f"expected: {expected}\nactual:   {actual}"
    )

    # ---- L2b: profiles ----
    parsed_profiles = parsed.get("profiles") or {}
    expected_profiles = {p.name: p.body for p in STARTER_PROFILES}
    assert parsed_profiles == expected_profiles, (
        f"Starter profiles disagree with STARTER_PROFILES seed."
    )

    # ---- L3: strict-mode validation through UserConfigFile ----
    report = CSNew.validate(parsed, layer="user", strict=False)
    assert report.warnings == [], f"unexpected warnings: {report.warnings}"

    # ---- L1: section markers ----
    assert "# Thoth Configuration File" in rendered
    assert "[profiles]" in rendered
    assert "[profiles.daily]" in rendered
```

- [ ] **Step 2: Run TS04 to verify it fails**

```bash
uv run pytest tests/test_config_starter_round_trip.py -v
```

Expected: import error — `_starter_data` doesn't exist yet.

- [ ] **Step 3: Create the `_starter_data.py` module**

Create `src/thoth/_starter_data.py`:

```python
"""P33: seed data for `thoth init` starter content.

Frozen verbatim from pre-P33 `_build_starter_profiles()`. Reviewing the
*selection* of profiles is deferred to P37; this module owns the *content*.

Each entry is a `StarterProfile(name, body)` where `body` is a mapping that
matches `ProfileConfig`. The order of entries in `STARTER_PROFILES` is the
order they appear under `[profiles.*]` in the rendered TOML.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StarterProfile:
    name: str
    body: dict[str, Any]


STARTER_PROFILES: list[StarterProfile] = [
    StarterProfile(
        name="daily",
        body={
            "general": {
                "default_mode": "thinking",
                "default_project": "daily-notes",
            },
        },
    ),
    StarterProfile(
        name="quick",
        body={
            "general": {"default_mode": "thinking"},
        },
    ),
    StarterProfile(
        name="openai_deep",
        body={
            "general": {"default_mode": "deep_research"},
            "modes": {
                "deep_research": {
                    "providers": ["openai"],
                    "parallel": False,
                },
            },
        },
    ),
    StarterProfile(
        name="all_deep",
        body={
            "general": {"default_mode": "deep_research"},
            "modes": {
                "deep_research": {
                    "providers": ["openai", "perplexity"],
                    "parallel": True,
                },
            },
        },
    ),
    StarterProfile(
        name="interactive",
        body={
            "general": {"default_mode": "interactive"},
        },
    ),
    StarterProfile(
        name="deep_research",
        body={
            "general": {
                "default_mode": "deep_research",
                "prompt_prefix": "Be thorough. Cite primary sources where possible.",
            },
            "modes": {
                "deep_research": {
                    "providers": ["openai", "perplexity"],
                    "parallel": True,
                    "prompt_prefix": (
                        "Be thorough. Cite primary sources. Include counter-arguments."
                    ),
                },
            },
        },
    ),
]
```

- [ ] **Step 4: Add the `WRITER_COMMENTS` table and rewrite `_build_starter_profiles()` and `_build_starter_document()`**

In `src/thoth/commands.py`, replace the existing `_build_starter_profiles()` and `_build_starter_document()` functions (lines ~70–159) with schema-driven versions. Above them, add the writer-owned comment table and a small walker.

```python
# ---------------------------------------------------------------------------
# P33: writer-owned structural prose for `thoth init`.
# ---------------------------------------------------------------------------
# Inline help-comments live as field metadata on the schema (per P33
# locked-decision 8). Multi-line *structural* prose stays here, keyed by
# section path. Adding a comment for a new section: add an entry below.

WRITER_COMMENTS: dict[str, list[str]] = {
    "$header": ["Thoth Configuration File"],
    "profiles": [
        "Configuration profiles (P21). Activate with --profile NAME,",
        "THOTH_PROFILE=NAME, or general.default_profile.",
        "Profile values REPLACE top-level values when the profile is active.",
    ],
}


def _emit_starter_section(
    doc: tomlkit.TOMLDocument,
    section_name: str,
    section_model: type,
) -> None:
    """Walk one top-level section model and emit its in-starter fields.

    `section_model` is a Pydantic BaseModel subclass (e.g. `GeneralConfig`).
    Only fields whose `json_schema_extra["in_starter"]` is True are emitted.
    """
    table = tomlkit.table()
    for name, finfo in section_model.model_fields.items():
        extra = (
            finfo.json_schema_extra
            if isinstance(finfo.json_schema_extra, dict)
            else {}
        )
        if not extra.get("in_starter"):
            continue
        # Resolve the default value (factory or literal).
        if finfo.default_factory is not None:
            value = finfo.default_factory()
        else:
            value = finfo.default
        # Pydantic models emitted as nested tables — use model_dump if applicable.
        from pydantic import BaseModel as _BM

        if isinstance(value, _BM):
            sub_table = tomlkit.table()
            for sub_name, sub_finfo in type(value).model_fields.items():
                sub_extra = (
                    sub_finfo.json_schema_extra
                    if isinstance(sub_finfo.json_schema_extra, dict)
                    else {}
                )
                if not sub_extra.get("in_starter"):
                    continue
                sub_value = getattr(value, sub_name)
                sub_table[sub_name] = sub_value
            table[name] = sub_table
        else:
            table[name] = value
    doc[section_name] = table


def _build_starter_profiles() -> tomlkit.items.Table:
    """Build the `[profiles]` super-table shipped by `thoth init`.

    P33: source of truth is `STARTER_PROFILES` in `thoth._starter_data`.
    Profile *content* is frozen seed data; only the container construction
    lives here.
    """
    from thoth._starter_data import STARTER_PROFILES

    profiles = tomlkit.table()
    for entry in STARTER_PROFILES:
        profiles[entry.name] = _build_profile_section(entry.body)
    return profiles


def _build_starter_document() -> tomlkit.TOMLDocument:
    """Construct the full starter `~/.config/thoth/thoth.config.toml`.

    P33: schema-driven. The set of in-starter fields and their default
    values comes from `ThothConfig`'s field metadata; structural prose
    comes from `WRITER_COMMENTS`.
    """
    from thoth.config_schema import (
        ClarificationConfig,
        ExecutionConfig,
        GeneralConfig,
        OutputConfig,
        PathsConfig,
        ProvidersConfig,
        ThothConfig,
    )

    doc = tomlkit.document()
    for line in WRITER_COMMENTS.get("$header", []):
        doc.add(tomlkit.comment(line))
    doc["version"] = ThothConfig.model_fields["version"].default

    _emit_starter_section(doc, "general", GeneralConfig)
    _emit_starter_section(doc, "paths", PathsConfig)
    _emit_starter_section(doc, "execution", ExecutionConfig)
    _emit_starter_section(doc, "output", OutputConfig)
    _emit_starter_section(doc, "providers", ProvidersConfig)
    # `clarification` is intentionally NOT shipped (no StarterField fields).

    # Profiles get a structural-comment block.
    doc.add(tomlkit.nl())
    for line in WRITER_COMMENTS.get("profiles", []):
        doc.add(tomlkit.comment(line))
    doc["profiles"] = _build_starter_profiles()
    return doc
```

> **Note for the engineer:** `_build_profile_section()` (lines ~36–67 in the existing `commands.py`) is unchanged. It already walks a flat-key body and emits nested tables; `STARTER_PROFILES` uses a structurally identical body shape (top-level keys are TOML section names). If a `StarterProfile.body` uses dotted-path keys (e.g. `"modes.deep_research"`), `_build_profile_section()` handles that. If a body uses nested-dict keys (e.g. `{"modes": {"deep_research": {...}}}`), the helper will need a one-line adjustment — verify by running the round-trip test.

- [ ] **Step 5: Run TS04**

```bash
uv run pytest tests/test_config_starter_round_trip.py -v
```

Expected: PASS.

If `_build_profile_section()` needs adjustment to handle nested-dict bodies (the way `STARTER_PROFILES` is structured), update the helper to walk recursively. The reference body shape is dotted-path keys (the legacy form). To minimize churn, you may adjust `STARTER_PROFILES` to use dotted-path keys instead — this keeps `_build_profile_section()` byte-identical to today.

If you choose dotted-path keys, the `STARTER_PROFILES` body for `openai_deep` becomes:

```python
body={
    "general": {"default_mode": "deep_research"},
    "modes.deep_research": {"providers": ["openai"], "parallel": False},
},
```

- [ ] **Step 6: Verify init produces the same TOML as before**

Capture the pre-P33 init output for diffing (commit `f5e6700` is pre-P33):

```bash
git stash
git checkout f5e6700 -- src/thoth/commands.py
uv run python -c "
from thoth.commands import _build_starter_document
import tomlkit
print(tomlkit.dumps(_build_starter_document()))
" > /tmp/p33_pre_init.toml
git checkout HEAD -- src/thoth/commands.py
git stash pop || true
```

Now capture the post-P33 init output:

```bash
uv run python -c "
from thoth.commands import _build_starter_document
import tomlkit
print(tomlkit.dumps(_build_starter_document()))
" > /tmp/p33_post_init.toml

diff -u /tmp/p33_pre_init.toml /tmp/p33_post_init.toml
```

Expected: empty diff, or only formatting differences (tomlkit-controlled blank lines around tables). Inspect any structural differences manually.

- [ ] **Step 7: Run thoth_test integration**

```bash
./thoth_test -r --skip-interactive -q
```

Expected: green. The `M…: Init command creates user XDG config directory…` test exercises the writer end-to-end.

- [ ] **Step 8: Commit**

```bash
git add src/thoth/_starter_data.py src/thoth/commands.py tests/test_config_starter_round_trip.py
git commit -m "feat(config): derive thoth init from schema + STARTER_PROFILES seed (P33-T05, TS04)"
```

---

### Task 8: Hook `ConfigSchema.validate()` into `ConfigManager.load_all_layers` (P33-T07)

**Files:**
- Modify: `src/thoth/config.py:283-371`
- Modify: `tests/test_config_validate.py`

- [ ] **Step 1: Add `ConfigManager.validation_reports` and per-layer validation**

In `src/thoth/config.py`, modify `ConfigManager.__init__` (around line 286) to add the new field:

```python
def __init__(self, config_path: Path | None = None):
    self.user_config_path = config_path or user_config_file()
    self.project_config_paths = ["./thoth.config.toml", "./.thoth.config.toml"]
    self.layers: dict[str, dict[str, Any]] = {}
    self.data: dict[str, Any] = {}
    self.project_config_path: Path | None = None
    self.profile_selection: ProfileSelection = ProfileSelection(None, "none", None)
    self.active_profile: ProfileLayer | None = None
    self.profile_catalog: list[ProfileLayer] = []
    # P33: per-layer validation reports keyed by layer name.
    from thoth.config_schema import ValidationReport

    self.validation_reports: dict[str, ValidationReport] = {}
```

Then modify `load_all_layers()` to validate each layer immediately after loading. Find the existing layer-loading block (around lines 322–358) and insert validation calls. The simplest approach is a small helper method:

```python
def _validate_layer(self, layer: str, data: dict[str, Any]) -> None:
    """Validate a layer's raw data; collect warnings; emit to console."""
    from thoth.config_schema import ConfigSchema

    report = ConfigSchema.validate(data, layer=layer)
    self.validation_reports[layer] = report
    for w in report.warnings:
        _console.print(
            f"[yellow]config warning[/yellow] [{layer}] {w.path}: {w.message}",
            highlight=False,
        )
```

Insert calls inside `load_all_layers()` after each `self.layers[...] = ...` assignment:

```python
# Layer 2: User config file
if self.user_config_path.exists():
    user_raw = self._load_toml_file(self.user_config_path)
else:
    user_raw = {}
# … existing strip-profiles code …
self.layers["user"] = without_profiles(user_raw)
self._validate_layer("user", user_raw)  # NEW — validate the raw TOML

# Layer 3: Project config file
project_raw, project_path = self._load_project_config_with_path()
# … existing code …
self.layers["project"] = without_profiles(project_raw)
self._validate_layer("project", project_raw)  # NEW

# … profile resolution …
self.layers["profile"] = self.active_profile.data if self.active_profile else {}
self._validate_layer("profile", self.layers["profile"])  # NEW

# CLI layer:
self.layers["cli"] = cli_layer
self._validate_layer("cli", cli_layer)  # NEW
```

The defaults layer is trivially valid by construction (it IS the schema) — no validation call needed for `"defaults"`.

- [ ] **Step 2: Replace the legacy `_validate_config()` with a slim invariant check**

The pre-P33 `_validate_config()` checked for required top-level keys. After P33, schema validation handles that comprehensively, but the existing `_validate_user_modes_kind()` deprecation nudge should remain.

Replace `_validate_config()` (around line 504) with:

```python
def _validate_config(self):
    """Post-merge invariant checks.

    Schema validation runs per-layer in `load_all_layers`; this method
    only enforces post-merge invariants (e.g. the user-modes kind
    deprecation nudge).
    """
    self._validate_user_modes_kind()
```

- [ ] **Step 3: Add a regression test for `validation_reports`**

Append to `tests/test_config_validate.py`:

```python
def test_validation_reports_populated_per_layer(tmp_path) -> None:
    """ConfigManager.validation_reports must contain a report per layer."""
    from thoth.config import ConfigManager

    cfg = tmp_path / "thoth.config.toml"
    cfg.write_text(
        '\n'.join(
            [
                'version = "2.0"',
                "[general]",
                'prompy_prefix = "x"',  # typo
            ]
        )
    )

    mgr = ConfigManager(config_path=cfg)
    mgr.load_all_layers()

    # Every layer that ran validation should be present.
    assert "user" in mgr.validation_reports
    assert "project" in mgr.validation_reports
    assert "profile" in mgr.validation_reports
    assert "cli" in mgr.validation_reports

    # The user layer captured the typo.
    user_warns = mgr.validation_reports["user"].warnings
    assert any("prompy_prefix" in w.path for w in user_warns), (
        f"expected prompy_prefix warning in user layer; got {user_warns}"
    )

    # Defaults layer is trivially valid; not required to be present.


def test_existing_test_fixtures_produce_zero_warnings(tmp_path) -> None:
    """A *valid* P21-shape config produces no warnings."""
    from thoth.config import ConfigManager

    cfg = tmp_path / "thoth.config.toml"
    cfg.write_text(
        '\n'.join(
            [
                'version = "2.0"',
                "[general]",
                'default_profile = "fast"',
                'prompt_prefix = "Cite sources"',
                "[profiles.fast]",
                'prompt_prefix = "Be quick"',
                "[profiles.fast.modes.thinking]",
                'system_prompt = "Step by step"',
            ]
        )
    )

    mgr = ConfigManager(config_path=cfg)
    mgr.load_all_layers()

    for layer, report in mgr.validation_reports.items():
        assert report.warnings == [], (
            f"layer {layer} produced unexpected warnings: {report.warnings}"
        )
```

- [ ] **Step 4: Un-xfail the earlier `--no-validate` CLI test**

Open `tests/test_config_validate.py` and remove the `pytest.xfail(...)` line in `test_validate_flag_omitted_surfaces_warning` — it should pass now.

- [ ] **Step 5: Run all validation tests**

```bash
uv run pytest tests/test_config_validate.py -v
```

Expected: all PASS.

- [ ] **Step 6: Run the full pytest suite + thoth_test**

```bash
uv run pytest -q
./thoth_test -r --skip-interactive -q
```

Expected: green. Existing fixtures should produce zero warnings on every layer (otherwise they encode invalid shapes — fix the fixture, not the schema).

- [ ] **Step 7: Commit**

```bash
git add src/thoth/config.py tests/test_config_validate.py
git commit -m "feat(config): hook schema validation into load_all_layers, store reports per-layer (P33-T07)"
```

---

### Task 9: OpenAI runtime-consumption regression tests (P33-T09, TS09)

This task adds tests that verify the modeled OpenAI fields actually reach the OpenAI request builder when set in config / overlaid via profile.

**Files:**
- Create: `tests/test_openai_config_consumption.py`

- [ ] **Step 1: Write TS09**

Create `tests/test_openai_config_consumption.py`:

```python
"""P33-TS09: OpenAI runtime-consumption regression.

The schema-only acceptance tests (TS07) prove the schema *accepts* fields
like `providers.openai.temperature`. TS09 proves those fields actually
reach `OpenAIProvider.submit` / the request builder when set in config.

If a modeled OpenAI field is NOT consumed today, P33 must either wire it
or downgrade it to schema-only and remove the runtime claim.

Async test pattern: this repo uses `asyncio.run(coro)` to sync-wrap async
tests (see `tests/test_oai_background.py`), NOT `@pytest.mark.asyncio`.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock


def test_provider_temperature_reaches_request_builder(monkeypatch) -> None:
    """`[providers.openai] temperature = 0.2` for a non-`o*` model must
    appear in the request_params passed to `client.responses.create`."""
    from thoth.providers.openai import OpenAIProvider

    captured: dict[str, Any] = {}

    async def fake_create(**kwargs):
        captured.update(kwargs)
        # Mimic what the real OpenAI SDK returns
        resp = MagicMock()
        resp.id = "resp_test"
        resp.status = "completed"
        return resp

    # Use a non-deep-research model so the temperature branch is hit.
    config = {
        "model": "gpt-4o-mini",
        "temperature": 0.2,
        "kind": "immediate",
    }
    provider = OpenAIProvider(api_key="sk-test", config=config)
    monkeypatch.setattr(
        provider.client.responses,
        "create",
        AsyncMock(side_effect=fake_create),
    )

    asyncio.run(provider.submit(prompt="hello", mode="default", system_prompt=None))

    assert "temperature" in captured, (
        f"temperature not in request_params; saw keys {list(captured.keys())}. "
        f"P33 schema models providers.openai.temperature; either wire it through "
        f"or remove the runtime claim and downgrade TS07 to schema-only."
    )
    assert captured["temperature"] == 0.2


def test_profile_overlay_system_prompt_reaches_submit(monkeypatch, tmp_path) -> None:
    """A profile-overlaid `[profiles.fast.modes.thinking] system_prompt = "..."`
    must reach `OpenAIProvider.submit`'s `system_prompt` argument."""
    from thoth.config import ConfigManager
    from thoth.providers.openai import OpenAIProvider

    cfg = tmp_path / "thoth.config.toml"
    cfg.write_text(
        '\n'.join(
            [
                'version = "2.0"',
                "[general]",
                'default_profile = "fast"',
                "[profiles.fast.modes.thinking]",
                'system_prompt = "Profile-overlaid prompt"',
                'kind = "immediate"',
                'provider = "openai"',
                'model = "gpt-4o-mini"',
            ]
        )
    )

    mgr = ConfigManager(config_path=cfg)
    mgr.load_all_layers()

    mode_cfg = mgr.get_mode_config("thinking")
    assert mode_cfg.get("system_prompt") == "Profile-overlaid prompt", (
        f"profile overlay failed to reach merged mode config: {mode_cfg!r}"
    )

    # Submit and capture the system_prompt argument.
    captured: dict[str, Any] = {}

    async def fake_create(**kwargs):
        captured["kwargs"] = kwargs
        resp = MagicMock()
        resp.id = "resp_test"
        resp.status = "completed"
        return resp

    provider = OpenAIProvider(api_key="sk-test", config=mode_cfg)
    monkeypatch.setattr(
        provider.client.responses,
        "create",
        AsyncMock(side_effect=fake_create),
    )

    asyncio.run(
        provider.submit(
            prompt="hello",
            mode="thinking",
            system_prompt=mode_cfg.get("system_prompt"),
        )
    )

    # The system_prompt must appear in the structured input messages.
    inputs = captured["kwargs"]["input"]
    developer_msgs = [m for m in inputs if m.get("role") == "developer"]
    assert developer_msgs, "no developer message produced for system_prompt"
    text = developer_msgs[0]["content"][0]["text"]
    assert text == "Profile-overlaid prompt"
```

- [ ] **Step 2: Run TS09**

```bash
uv run pytest tests/test_openai_config_consumption.py -v
```

Expected: PASS. The repo uses `asyncio.run(coro)` to sync-wrap async tests — no `pytest-asyncio` plugin needed.

- [ ] **Step 3: If a modeled OpenAI field is NOT consumed**

For each modeled OpenAI field that fails the consumption assertion:

1. **Wire it** in `src/thoth/providers/openai.py` if it's a small change (e.g. read `self.config.get("max_tokens")` and pass through).
2. **Otherwise downgrade** the schema-only claim: remove the field from `OpenAIConfig` (or annotate it with a comment "P33 schema-only; runtime pickup deferred to <future P##>") and remove the corresponding TS09 assertion. Do not silently let the test be skipped.

- [ ] **Step 4: Commit**

```bash
git add tests/test_openai_config_consumption.py
# (… plus any provider wiring you added in Step 3, if any)
git commit -m "test(config): OpenAI runtime-consumption regression for typed provider fields (P33-T09, TS09)"
```

---

### Task 10: README/CHANGELOG note (P33-T08)

**Files:**
- Modify (conditional): `README.md`, `CHANGELOG.md`

- [ ] **Step 1: Verify whether existing test fixtures produce any warnings**

```bash
uv run pytest -q 2>&1 | grep -iE "config warning|prompy_prefix" | head -10
```

Expected: empty. If the fixtures are clean, P33 is invisible to existing users — no README change needed.

- [ ] **Step 2: Add a CHANGELOG entry (release-please-driven)**

The release-please workflow constructs the CHANGELOG from commit footers — so we don't hand-edit `CHANGELOG.md` here. Instead, ensure the merge commit message follows Conventional Commits with the right type. The previous task commits already do this; nothing to add.

- [ ] **Step 3: README update — only if user-visible behavior changed**

If Step 1 surfaced no warnings on existing fixtures, the user-visible delta is zero. Skip the README edit; record the decision in the project doc by opening `projects/P33-schema-driven-config-defaults.md` and appending under "Manual verification":

```markdown
- 2026-05-02: confirmed zero new warnings on existing test fixtures; no README/CHANGELOG entry needed for P33-T08.
```

If warnings DO appear on existing fixtures (a good signal that P33 caught a latent bug — fix the fixture, not the schema), add a short note to README's "Configuration" section:

```markdown
**Note:** Thoth now warns on unknown config keys (e.g. `prompy_prefix` typos). Warnings
are advisory and do not block execution. Pass `--no-validate` to suppress them. The
`[experimental]` super-table accepts arbitrary keys without warning.
```

- [ ] **Step 4: Commit**

```bash
git add projects/P33-schema-driven-config-defaults.md README.md  # README only if changed
git commit -m "docs(config): record P33-T08 — no user-visible behavior change for existing configs"
```

---

### Task 11: Final verification gate

- [ ] **Step 1: Run the full local gate**

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run ty check src/
uv run pytest -q
./thoth_test -r --skip-interactive -q
```

Expected: all green.

- [ ] **Step 2: Update task checkboxes in the project doc**

Open `projects/P33-schema-driven-config-defaults.md` and flip each `[ ] [P33-T##]` and `[ ] [P33-TS##]` line to `[x]` for tasks/tests now complete. Also flip the trunk row in `PROJECTS.md` from `- [ ] **P33** —` to `- [~] **P33** —` if any tasks landed (in-progress) or `- [x] **P33** —` if every task and the regression-test-status line are checked.

- [ ] **Step 3: Final commit**

```bash
git add projects/P33-schema-driven-config-defaults.md PROJECTS.md
git commit -m "docs(projects): mark P33 tasks complete; flip trunk to in-progress/done"
```

- [ ] **Step 4: Push branch and open PR**

```bash
git push -u origin p33-schema-driven-config-defaults
gh pr create --title "P33: Schema-Driven Config Defaults" --body "$(cat <<'EOF'
## Summary
- Pydantic v2 schema is now the single source of truth for runtime defaults, init starter content, and per-provider config surface
- `ConfigSchema.get_defaults()` derives from `_ROOT_SCHEMA.model_dump(...)` — signature unchanged
- `thoth init` walks the schema for in-starter fields; profile content is sourced from `STARTER_PROFILES` seed data
- Warn-only validation hooks into `ConfigManager.load_all_layers`; reports stored on `ConfigManager.validation_reports`; `--no-validate` flag and `[experimental]` carve-out provide escape hatches
- Provider config is forward-looking: `OpenAIConfig`, `PerplexityConfig`, `GeminiConfig` all subclass `ProviderConfigBase`; OpenAI fields are runtime-consumption regression-tested

## Test plan
- [ ] `uv run pytest tests/test_p33_pydantic_dep.py tests/test_config_schema.py tests/test_config_validate.py tests/test_config_starter_round_trip.py tests/test_openai_config_consumption.py -v` — TS00–TS09 green
- [ ] `./thoth_test -r --skip-interactive -q` — no regressions
- [ ] `just check` — lint + typecheck clean
- [ ] Manual: `thoth init --hidden /tmp/thoth-p33-check.toml`, diff against pre-P33 capture
- [ ] Manual: add `[general] prompy_prefix = "x"` to a config; run `thoth status`; observe one warning at `general.prompy_prefix`. Pass `--no-validate`; observe none
- [ ] Manual: add `[experimental] anything = true`; observe no warning

Closes P33.
EOF
)"
```

---

## Self-review checklist

After completing all tasks above, run this checklist:

- [ ] Every TS00–TS09 in the spec has a corresponding test file/test function in this plan.
- [ ] Every T00–T09 in the spec has a corresponding plan task.
- [ ] All type names used in later tasks match what was defined earlier:
  - `ThothConfig`, `GeneralConfig`, `PathsConfig`, `ExecutionConfig`, `OutputConfig`, `ProvidersConfig`, `ClarificationConfig`, `ClarificationCLIConfig`, `ClarificationInteractiveConfig`, `ModeConfig`
  - `ProviderConfigBase`, `OpenAIConfig`, `PerplexityConfig`, `GeminiConfig`
  - `make_partial`, `PartialThothConfig`, `GeneralOverlay`, `ConfigOverlay`, `ProfileConfig`, `UserConfigFile`
  - `StarterField`, `_ROOT_SCHEMA`, `_ROOT_DEFAULTS_DICT`, `_no_validate`
  - `ValidationWarning`, `ValidationReport`
  - `ConfigSchema.validate(data, *, layer="user", strict=False)`, `.starter_keys()`, `.model()`
  - `ConfigManager.validation_reports: dict[str, ValidationReport]`
  - `STARTER_PROFILES`, `StarterProfile(name, body)`, `WRITER_COMMENTS`
- [ ] No "TBD" / "TODO" / "implement later" placeholders.
- [ ] Every code-step contains complete code, not just a description.
- [ ] Test commands include expected output (PASS / FAIL).
- [ ] `--no-validate` is loader metadata, never a config root key.
- [ ] Defaults dict equality is verified at two points: dump-equality test (TS01) AND a one-shot snapshot diff in Task 6.
- [ ] Provider configs subclass `ProviderConfigBase` (not `ProviderBase`).
- [ ] `[experimental]` super-table is the only place `extra="allow"` applies.
