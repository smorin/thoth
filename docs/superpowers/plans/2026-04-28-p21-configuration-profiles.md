# P21 Configuration Profile Resolution & Overlay — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add CPP-style configuration profile *resolution and overlay* — root `--profile`, `THOTH_PROFILE`, `general.default_profile`, and `[profiles.<name>]` overlay between project config and env/CLI per-setting overrides. Users hand-edit TOML in P21; CLI management commands (`thoth config profiles ...`) ship in P21b.

**Architecture:** Put pure profile resolution and profile catalog logic in `src/thoth/config_profiles.py`. `ConfigManager` loads user/project profile tables, resolves a single active profile, inserts a `profile` layer between project config and environment overrides, and exposes selection metadata. Click gets a root `--profile` option threaded through every existing config-loading call site (including `config_cmd._load_manager` and the existing `config get/list` Click leaves).

**Tech Stack:** Python 3.11+, Click 8.x, tomlkit (already in use), pytest, existing `ConfigManager`, existing `config_cmd.py` data-function pattern.

**Spec:** `docs/superpowers/specs/2026-04-28-p21-configuration-profiles-design.md`
**Research:** `research/configuration_profile_pattern.v1.md`
**Successor plan:** `docs/superpowers/plans/2026-04-28-p21b-configuration-profiles-crud.md`

---

## File Map

- Create: `src/thoth/config_profiles.py` — profile selection, catalog, validation.
- Modify: `src/thoth/config.py` — call profile resolver, add `profile` layer, expose metadata, refactor `_load_project_config` to also return the actual path.
- Modify: `src/thoth/errors.py` — add `ConfigProfileError`.
- Modify: `src/thoth/cli_subcommands/_options.py` — add root `--profile`.
- Modify: `src/thoth/cli_subcommands/_option_policy.py` — `DEFAULT_HONOR` includes `"profile"`.
- Modify: `src/thoth/cli.py` — store profile option, conflict labels, fallback parsing.
- Modify: `src/thoth/config_cmd.py` — thread profile through `_load_manager` and existing `get_config_*_data` entries (no new CRUD functions in P21).
- Modify: `src/thoth/cli_subcommands/config.py` — existing leaves (`get`, `list`, etc.) forward inherited `profile`.
- Modify: `src/thoth/help.py`, `README.md`, `manual_testing_instructions.md`, `PROJECTS.md` — document hand-edit profile behavior, forward-pointer to P21b.
- Test: `tests/test_config_profiles.py` — profile resolution, overlay behavior, root-flag threading.

P21 does NOT touch `tests/test_config_profiles_cmd.py`, `tests/test_json_envelopes.py`, or `tests/test_ci_lint_rules.py` (those land in P21b).

---

## Task 1: Profile Resolver Unit

**Files:**
- Create: `tests/test_config_profiles.py`
- Create: `src/thoth/config_profiles.py`
- Modify: `src/thoth/errors.py`

- [ ] **Step 1: Write failing resolver tests**

Add to `tests/test_config_profiles.py`:

```python
from __future__ import annotations

from pathlib import Path

import pytest

from thoth.config_profiles import (
    ProfileSelection,
    collect_profile_catalog,
    resolve_profile_layer,
    resolve_profile_selection,
)
from thoth.errors import ConfigProfileError


def test_resolve_profile_selection_prefers_flag_over_env_and_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("THOTH_PROFILE", "env-profile")
    selection = resolve_profile_selection(
        cli_profile="flag-profile",
        base_config={"general": {"default_profile": "config-profile"}},
    )
    assert selection == ProfileSelection(
        name="flag-profile",
        source="flag",
        source_detail="--profile flag",
    )


def test_resolve_profile_selection_uses_env_before_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("THOTH_PROFILE", "env-profile")
    selection = resolve_profile_selection(
        cli_profile=None,
        base_config={"general": {"default_profile": "config-profile"}},
    )
    assert selection.name == "env-profile"
    assert selection.source == "env"
    assert selection.source_detail == "THOTH_PROFILE"


def test_resolve_profile_selection_uses_config_pointer_when_flag_and_env_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("THOTH_PROFILE", raising=False)
    selection = resolve_profile_selection(
        cli_profile=None,
        base_config={"general": {"default_profile": "config-profile"}},
    )
    assert selection.name == "config-profile"
    assert selection.source == "config"
    assert selection.source_detail == "general.default_profile"


def test_resolve_profile_selection_none_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("THOTH_PROFILE", raising=False)
    selection = resolve_profile_selection(cli_profile=None, base_config={"general": {}})
    assert selection.name is None
    assert selection.source == "none"
    assert selection.source_detail is None


def test_project_profile_shadows_user_profile_wholesale(tmp_path: Path) -> None:
    catalog = collect_profile_catalog(
        user_config={"profiles": {"prod": {"general": {"default_mode": "thinking"}}}},
        project_config={"profiles": {"prod": {"execution": {"poll_interval": 5}}}},
        user_path=tmp_path / "user.toml",
        project_path=tmp_path / "thoth.config.toml",
    )
    layer = resolve_profile_layer(
        ProfileSelection("prod", "flag", "--profile flag"),
        catalog,
    )
    assert layer is not None
    assert layer.tier == "project"
    assert layer.data == {"execution": {"poll_interval": 5}}


def test_collect_catalog_skips_project_when_no_project_file(tmp_path: Path) -> None:
    catalog = collect_profile_catalog(
        user_config={"profiles": {"prod": {"general": {}}}},
        project_config={},
        user_path=tmp_path / "user.toml",
        project_path=None,
    )
    assert {entry.tier for entry in catalog} == {"user"}


def test_missing_selected_profile_raises_with_source(tmp_path: Path) -> None:
    catalog = collect_profile_catalog(
        user_config={"profiles": {"prod": {"general": {"default_mode": "thinking"}}}},
        project_config={},
        user_path=tmp_path / "user.toml",
        project_path=None,
    )
    with pytest.raises(ConfigProfileError) as exc:
        resolve_profile_layer(
            ProfileSelection("prdo", "flag", "--profile flag"),
            catalog,
        )
    assert "prdo" in exc.value.message
    assert "--profile flag" in exc.value.message
    assert "prod" in (exc.value.suggestion or "")


@pytest.mark.parametrize(
    "selection,detail_substring",
    [
        (ProfileSelection("ghost", "env", "THOTH_PROFILE"), "THOTH_PROFILE"),
        (ProfileSelection("ghost", "config", "general.default_profile"), "general.default_profile"),
    ],
)
def test_missing_profile_raises_for_each_selection_source(
    tmp_path: Path,
    selection: ProfileSelection,
    detail_substring: str,
) -> None:
    catalog = collect_profile_catalog(
        user_config={"profiles": {"prod": {"general": {"default_mode": "thinking"}}}},
        project_config={},
        user_path=tmp_path / "user.toml",
        project_path=None,
    )
    with pytest.raises(ConfigProfileError) as exc:
        resolve_profile_layer(selection, catalog)
    assert detail_substring in exc.value.message
```

- [ ] **Step 2: Run resolver tests and confirm failure**

Run:

```bash
uv run pytest tests/test_config_profiles.py -v
```

Expected: import failures for `thoth.config_profiles` and `ConfigProfileError`.

- [ ] **Step 3: Add `ConfigProfileError`**

In `src/thoth/errors.py`, add:

```python
class ConfigProfileError(ThothError):
    """Configuration profile selection or validation failed."""

    def __init__(
        self,
        message: str,
        *,
        available_profiles: list[str] | None = None,
        source: str | None = None,
    ):
        details = message if source is None else f"{message} (from {source})"
        suggestion_parts = ["Run `thoth config profiles list` to see available profiles."]
        if available_profiles:
            suggestion_parts.append(f"Available profiles: {', '.join(available_profiles)}.")
        super().__init__(
            details,
            " ".join(suggestion_parts),
            exit_code=1,
        )
```

- [ ] **Step 4: Add profile resolver module**

Create `src/thoth/config_profiles.py`:

```python
"""Configuration profile resolution for Thoth."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from thoth.errors import ConfigProfileError

ProfileSelectionSource = Literal["flag", "env", "config", "none"]
ProfileTier = Literal["project", "user"]


@dataclass(frozen=True)
class ProfileSelection:
    name: str | None
    source: ProfileSelectionSource
    source_detail: str | None


@dataclass(frozen=True)
class ProfileLayer:
    name: str
    tier: ProfileTier
    path: Path
    data: dict[str, Any]


def _profiles_from(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = config.get("profiles") or {}
    if not isinstance(raw, dict):
        return {}
    return {str(name): value for name, value in raw.items() if isinstance(value, dict)}


def collect_profile_catalog(
    *,
    user_config: dict[str, Any],
    project_config: dict[str, Any],
    user_path: Path,
    project_path: Path | None,
) -> list[ProfileLayer]:
    catalog: list[ProfileLayer] = []
    for name, data in _profiles_from(user_config).items():
        catalog.append(ProfileLayer(name=name, tier="user", path=user_path, data=data))
    if project_path is not None:
        for name, data in _profiles_from(project_config).items():
            catalog.append(ProfileLayer(name=name, tier="project", path=project_path, data=data))
    return catalog


def resolve_profile_selection(
    *,
    cli_profile: str | None,
    base_config: dict[str, Any],
) -> ProfileSelection:
    if cli_profile:
        return ProfileSelection(cli_profile, "flag", "--profile flag")
    env_profile = os.getenv("THOTH_PROFILE")
    if env_profile:
        return ProfileSelection(env_profile, "env", "THOTH_PROFILE")
    general = base_config.get("general") or {}
    config_profile = general.get("default_profile") if isinstance(general, dict) else None
    if config_profile:
        return ProfileSelection(str(config_profile), "config", "general.default_profile")
    return ProfileSelection(None, "none", None)


def resolve_profile_layer(
    selection: ProfileSelection,
    catalog: list[ProfileLayer],
) -> ProfileLayer | None:
    if selection.name is None:
        return None

    matches = [entry for entry in catalog if entry.name == selection.name]
    if not matches:
        available = sorted({entry.name for entry in catalog})
        raise ConfigProfileError(
            f"Profile {selection.name!r} not found",
            available_profiles=available,
            source=selection.source_detail,
        )

    project_matches = [entry for entry in matches if entry.tier == "project"]
    if project_matches:
        return project_matches[-1]
    return matches[-1]
```

- [ ] **Step 5: Run resolver tests**

Run:

```bash
uv run pytest tests/test_config_profiles.py -v
```

Expected: resolver tests pass.

- [ ] **Step 6: Commit Task 1**

```bash
git add src/thoth/config_profiles.py src/thoth/errors.py tests/test_config_profiles.py
git commit -m "feat: add config profile resolver"
```

---

## Task 2: Apply Active Profile in `ConfigManager`

**Files:**
- Modify: `tests/test_config_profiles.py`
- Modify: `src/thoth/config.py`
- Modify: `src/thoth/config_profiles.py`

- [ ] **Step 1: Add failing ConfigManager overlay tests**

Append to `tests/test_config_profiles.py`:

```python
from thoth.config import ConfigManager


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_config_manager_no_profile_keeps_existing_effective_config(
    isolated_thoth_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("THOTH_PROFILE", raising=False)
    cm = ConfigManager()
    cm.load_all_layers({})
    assert cm.get("general.default_mode") == "default"
    assert cm.profile_selection.name is None
    assert cm.active_profile is None


def test_config_manager_applies_profile_between_project_and_env(
    isolated_thoth_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from thoth.paths import user_config_file

    monkeypatch.setenv("THOTH_PROFILE", "fast")
    monkeypatch.setenv("THOTH_DEFAULT_MODE", "clarification")
    _write(
        user_config_file(),
        """
version = "2.0"

[general]
default_mode = "deep_research"

[profiles.fast.general]
default_mode = "thinking"
""".strip()
        + "\n",
    )

    cm = ConfigManager()
    cm.load_all_layers({})

    assert cm.get("general.default_mode") == "clarification"
    assert cm.layers["profile"]["general"]["default_mode"] == "thinking"
    assert cm.profile_selection.name == "fast"
    assert cm.active_profile is not None
    assert cm.active_profile.tier == "user"


def test_cli_setting_override_beats_active_profile(isolated_thoth_home: Path) -> None:
    from thoth.paths import user_config_file

    _write(
        user_config_file(),
        """
version = "2.0"

[profiles.fast.execution]
poll_interval = 5
""".strip()
        + "\n",
    )

    cm = ConfigManager()
    cm.load_all_layers({"_profile": "fast", "execution": {"poll_interval": 99}})

    assert cm.get("execution.poll_interval") == 99
    assert cm.layers["profile"]["execution"]["poll_interval"] == 5


def test_default_profile_pointer_survives_profile_splitting(
    isolated_thoth_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from thoth.paths import user_config_file

    monkeypatch.delenv("THOTH_PROFILE", raising=False)
    _write(
        user_config_file(),
        """
version = "2.0"

[general]
default_profile = "fast"

[profiles.fast.general]
default_mode = "thinking"
""".strip()
        + "\n",
    )

    cm = ConfigManager()
    cm.load_all_layers({})

    assert cm.get("general.default_profile") == "fast"
    assert cm.profile_selection.name == "fast"
    assert cm.profile_selection.source == "config"


def test_config_manager_uses_dot_thoth_project_file_when_present(
    isolated_thoth_home: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catalog must report the actual project file used (covers both project_config_paths)."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("THOTH_PROFILE", raising=False)
    _write(
        tmp_path / ".thoth.config.toml",
        """
version = "2.0"

[profiles.proj.general]
default_mode = "thinking"
""".strip()
        + "\n",
    )

    cm = ConfigManager()
    cm.load_all_layers({"_profile": "proj"})

    assert cm.active_profile is not None
    assert cm.active_profile.tier == "project"
    assert cm.active_profile.path == Path(".thoth.config.toml") or \
           cm.active_profile.path.name == "thoth.config.toml"


def test_thoth_profile_is_not_a_per_setting_env_override() -> None:
    """Regression guard: THOTH_PROFILE must not be added to env_mappings."""
    import inspect

    from thoth import config as thoth_config

    src = inspect.getsource(thoth_config.ConfigManager._get_env_overrides)
    assert "THOTH_PROFILE" not in src, (
        "THOTH_PROFILE belongs to Stage 1 selection (read by resolve_profile_selection), "
        "not Stage 2 per-setting overrides. See CPP REQ-CPP-004."
    )
```

- [ ] **Step 2: Run overlay tests and confirm failure**

Run:

```bash
uv run pytest tests/test_config_profiles.py -k "config_manager" -v
```

Expected: failures for missing `profile_selection`, missing `active_profile`, or missing profile layer.

- [ ] **Step 3: Add helpers for stripping profile metadata**

In `src/thoth/config_profiles.py`, add:

```python
def without_profiles(config: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in config.items() if key != "profiles"}
```

- [ ] **Step 4: Wire profiles into `ConfigManager.load_all_layers`**

First, refactor `_load_project_config` to also return the path it loaded (or `None`), so the catalog can name the real file:

```python
def _load_project_config_with_path(self) -> tuple[dict[str, Any], Path | None]:
    for config_path in self.project_config_paths:
        path = Path(config_path)
        if path.exists():
            return self._load_toml_file(path), path
    return {}, None


def _load_project_config(self) -> dict[str, Any]:
    data, _ = self._load_project_config_with_path()
    return data
```

Update `collect_profile_catalog` so `project_path: Path | None`. When `project_path is None`, do not append project entries to the catalog (there is no project file).

In `src/thoth/config.py`, import profile helpers:

```python
from thoth.config_profiles import (
    ProfileLayer,
    ProfileSelection,
    collect_profile_catalog,
    resolve_profile_layer,
    resolve_profile_selection,
    without_profiles,
)
```

In `ConfigManager.__init__`, add:

```python
self.profile_selection = ProfileSelection(None, "none", None)
self.active_profile: ProfileLayer | None = None
self.profile_catalog: list[ProfileLayer] = []
```

In `load_all_layers`, replace the simple layer merge with:

```python
raw_cli_args = cli_args or {}
cli_profile = raw_cli_args.get("_profile")
cli_layer = {key: value for key, value in raw_cli_args.items() if key != "_profile"}

self.layers["defaults"] = ConfigSchema.get_defaults()

if self.user_config_path.exists():
    user_raw = self._load_toml_file(self.user_config_path)
else:
    user_raw = {}

project_raw, project_path = self._load_project_config_with_path()
self.project_config_path = project_path
self.profile_catalog = collect_profile_catalog(
    user_config=user_raw,
    project_config=project_raw,
    user_path=self.user_config_path,
    project_path=project_path,
)

self.layers["user"] = without_profiles(user_raw)
self.layers["project"] = without_profiles(project_raw)

base_config: dict[str, Any] = {}
for layer_name in ["defaults", "user", "project"]:
    base_config = self._deep_merge(base_config, self.layers[layer_name])

self.profile_selection = resolve_profile_selection(
    cli_profile=str(cli_profile) if cli_profile else None,
    base_config=base_config,
)
self.active_profile = resolve_profile_layer(self.profile_selection, self.profile_catalog)
self.layers["profile"] = self.active_profile.data if self.active_profile else {}

self.layers["env"] = self._get_env_overrides()
self.layers["cli"] = cli_layer
self.data = self._merge_layers()
self.data = self._substitute_env_vars(self.data)
self._validate_config()
```

Update `_merge_layers` order:

```python
for layer_name in ["defaults", "user", "project", "profile", "env", "cli"]:
```

- [ ] **Step 5: Run profile tests**

Run:

```bash
uv run pytest tests/test_config_profiles.py -v
```

Expected: all profile resolver and ConfigManager tests pass.

- [ ] **Step 6: Run existing config tests**

Run:

```bash
uv run pytest tests/test_config.py tests/test_config_cmd.py -v
```

Expected: existing config behavior still passes.

- [ ] **Step 7: Commit Task 2**

```bash
git add src/thoth/config.py src/thoth/config_profiles.py tests/test_config_profiles.py
git commit -m "feat: apply active config profile"
```

---

## Task 3: Root `--profile` and Inherited Option Policy

**Files:**
- Modify: `tests/test_config_profiles.py`
- Modify: `src/thoth/cli_subcommands/_options.py`
- Modify: `src/thoth/cli_subcommands/_option_policy.py`
- Modify: `src/thoth/cli.py`
- Modify: selected subcommands that instantiate `ConfigManager()` directly

- [ ] **Step 1: Add failing Click tests for `--profile`**

Append to `tests/test_config_profiles.py`:

```python
from click.testing import CliRunner

from thoth.cli import cli


def test_root_profile_reaches_config_get(isolated_thoth_home: Path) -> None:
    from thoth.paths import user_config_file

    _write(
        user_config_file(),
        """
version = "2.0"

[profiles.fast.general]
default_mode = "thinking"
""".strip()
        + "\n",
    )

    result = CliRunner().invoke(
        cli,
        ["--profile", "fast", "config", "get", "general.default_mode"],
    )

    assert result.exit_code == 0
    assert result.output.strip().splitlines()[-1] == "thinking"


def test_unknown_root_profile_errors_before_config_get(isolated_thoth_home: Path) -> None:
    result = CliRunner().invoke(
        cli,
        ["--profile", "missing", "config", "get", "general.default_mode"],
    )

    assert result.exit_code == 1
    assert "Profile 'missing' not found" in result.output
```

- [ ] **Step 2: Run Click tests and confirm failure**

Run:

```bash
uv run pytest tests/test_config_profiles.py -k "root_profile" -v
```

Expected: Click rejects `--profile` before implementation.

- [ ] **Step 3: Add root option and policy**

In `src/thoth/cli_subcommands/_options.py`, add `--profile` near `--config`:

```python
(("--profile", "profile"), {"help": "Configuration profile to apply"}),
```

In `src/thoth/cli_subcommands/_option_policy.py`, add:

```python
"profile": "--profile",
```

and update:

```python
DEFAULT_HONOR: frozenset[str] = frozenset({"config_path", "profile"})
```

- [ ] **Step 4: Store profile in `cli.py`**

Add `profile` to the `cli(...)` callback parameter list immediately after `config_path`, and store:

```python
ctx.obj["profile"] = profile
```

Update `_version_conflicts` labels:

```python
"profile": "--profile",
```

Update `_extract_fallback_options` value options:

```python
"--profile": "profile",
```

When `_run_research_default` builds config through `get_config()`, the active profile must be passed to config loading. Add a helper:

```python
def _config_cli_args(opts: dict) -> dict:
    args: dict = {}
    if opts.get("config_path"):
        args["config_path"] = opts.get("config_path")
    if opts.get("profile"):
        args["_profile"] = opts.get("profile")
    return args
```

Use `{"_profile": profile}` in direct `ConfigManager.load_all_layers(...)` calls introduced by this task.

- [ ] **Step 5: Thread profile through every config-loading entry point**

Run a complete sweep, **including `src/thoth/config_cmd.py`**:

```bash
rg "ConfigManager\(|load_all_layers|_load_manager" \
  src/thoth/cli_subcommands src/thoth/commands.py src/thoth/run.py \
  src/thoth/config_cmd.py src/thoth/cli.py
```

For each direct load, pass `_profile` alongside `config_path` where the command honors inherited config:

```python
profile = inherited_value(ctx, "profile")
config_manager.load_all_layers({"config_path": config_path, "_profile": profile})
```

In `src/thoth/config_cmd.py`, update `_load_manager` to accept a profile and forward it as `cli_args`:

```python
def _load_manager(
    config_path: str | Path | None = None,
    *,
    profile: str | None = None,
) -> ConfigManager:
    cm = ConfigManager(_normalize_config_path(config_path))
    cli_args: dict[str, Any] = {}
    if profile:
        cli_args["_profile"] = profile
    cm.load_all_layers(cli_args)
    return cm
```

Add `profile: str | None = None` to every `get_config_*_data(...)` entry that builds a merged view (`get_config_get_data`, `get_config_list_data`, etc.) and forward it to `_load_manager`. Update `src/thoth/cli_subcommands/config.py` leaves to call `inherited_value(ctx, "profile")` and pass it down.

For `get_config()`, add an optional `profile: str | None = None` argument in `src/thoth/config.py`:

```python
def get_config(profile: str | None = None) -> ConfigManager:
    config = ConfigManager(_config_path)
    cli_args: dict[str, Any] = {}
    if profile:
        cli_args["_profile"] = profile
    config.load_all_layers(cli_args)
    return config
```

**Critical regression test**: `test_root_profile_reaches_config_get` (Task 3 Step 1) only passes after `_load_manager` is profile-aware. If it green-lights without those changes, it is asserting the wrong thing.

- [ ] **Step 6: Run profile Click tests**

Run:

```bash
uv run pytest tests/test_config_profiles.py -k "root_profile" -v
```

Expected: both tests pass.

- [ ] **Step 7: Run inherited-option regression tests**

Run:

```bash
uv run pytest tests/test_p16_pr2_cleanup.py tests/test_p16_dispatch_parity.py -v
```

Expected: inherited option validation remains intentional.

- [ ] **Step 8: Commit Task 3**

```bash
git add src/thoth/cli.py src/thoth/cli_subcommands/_options.py src/thoth/cli_subcommands/_option_policy.py src/thoth/config.py src/thoth/cli_subcommands tests/test_config_profiles.py
git commit -m "feat: add profile selection option"
```

---

## Task 4: Help, Docs, and Tracker (P21 — hand-edit only)

**Files:**
- Modify: `src/thoth/help.py`
- Modify: `README.md`
- Modify: `manual_testing_instructions.md`
- Modify: `PROJECTS.md`

P21 documents profile *behavior* and the hand-edit workflow. The CLI management commands ship in P21b; P21's docs end with a forward pointer.

- [ ] **Step 1: Update help text**

Update `src/thoth/help.py` so `thoth help config` mentions `--profile` and the hand-edit path:

```text
Profile selection: --profile NAME (also THOTH_PROFILE env, or general.default_profile in config)
Profile sections live under [profiles.<name>] and overlay top-level config.
CLI management commands (`thoth config profiles ...`) ship in a follow-up project (P21b).
```

- [ ] **Step 2: Add the README "Configuration Profiles" section**

````markdown
### Configuration Profiles

Profiles let you keep shared config at the top level and define named overlays for different work contexts.

```toml
[general]
default_mode = "deep_research"

[profiles.fast.general]
default_mode = "thinking"
```

Selection precedence is `--profile` → `THOTH_PROFILE` → `general.default_profile` → no profile.

`thoth config get general.default_profile` reflects the **persisted pointer** in the file. `--profile` and `THOTH_PROFILE` are read-only runtime inputs — they never write back to `general.default_profile`. With persisted `general.default_profile = "fast"`, running `thoth --profile bar config get general.default_profile` returns `"fast"`; the runtime active selection is `bar`.

> **CLI management coming in P21b.** Today, manage profiles by editing `~/.config/thoth/thoth.config.toml` (or `./thoth.config.toml`/`./.thoth.config.toml` for project-scoped profiles) directly. The next project (P21b) adds `thoth config profiles list/show/current/set-default/unset-default/add/set/unset/remove` so you don't have to hand-edit.
````

- [ ] **Step 3: Add concrete README examples**

````markdown
#### Change the default mode for a profile

```toml
[profiles.daily.general]
default_mode = "thinking"
default_project = "daily-notes"
```

```bash
thoth --profile daily "summarize today's notes"
```

#### Run all available deep-research providers

```toml
[profiles.all_deep.general]
default_mode = "deep_research"

[profiles.all_deep.modes.deep_research]
providers = ["openai", "perplexity"]
parallel = true
```

```bash
thoth --profile all_deep "compare vector databases"
```

> **Future-ready: gemini.** A `gemini` provider is planned (see `research/gemini-deep-research-api.v1.md`). Once it ships, you'll be able to add it to the `providers` list above. The profile schema is already future-ready; the runtime support lands in a later project — analogous to the interactive default-mode example below.

#### Use one deep-research provider

```toml
[profiles.openai_deep.general]
default_mode = "deep_research"

[profiles.openai_deep.modes.deep_research]
providers = ["openai"]
parallel = false
```

```bash
thoth --profile openai_deep "research model routing"
```

#### Use an immediate default mode

```toml
[profiles.quick.general]
default_mode = "thinking"
```

```bash
thoth --profile quick "give me the short version"
```

#### Reserve an interactive default profile

```toml
[profiles.interactive.general]
default_mode = "interactive"
```

This profile can be stored, listed, and selected by P21 today (via hand-edit). The command behavior for a default interactive mode ships with a later interactive-default project.
````

- [ ] **Step 4: Update manual testing instructions**

Append to `manual_testing_instructions.md`:

```bash
# Hand-edit ~/.config/thoth/thoth.config.toml first to add:
#
#   [profiles.fast.general]
#   default_mode = "thinking"
#
#   [general]
#   default_profile = "fast"

thoth config get general.default_mode                      # expect "thinking" (from profile)
THOTH_PROFILE=fast thoth config get general.default_mode   # expect "thinking"
thoth --profile missing config get general.default_mode    # expect ConfigProfileError naming '--profile flag'
thoth config get general.default_profile                   # expect "fast" (persisted)
thoth --profile bar config get general.default_profile     # expect "fast" (NOT mutated by --profile)
```

- [ ] **Step 5: Update P21 tracker**

In `PROJECTS.md`, mark planning deliverables present and check off tasks as code lands. Note that P21b is the follow-up project for CRUD commands.

- [ ] **Step 6: Run documentation and targeted tests**

```bash
uv run pytest tests/test_config_profiles.py -v
git diff --check
```

Expected: tests pass and no whitespace errors.

- [ ] **Step 7: Commit Task 4**

```bash
git add src/thoth/help.py README.md manual_testing_instructions.md PROJECTS.md
git commit -m "docs: document config profile resolution"
```

---

## Final Verification

Run after all P21 tasks land:

```bash
make env-check
just fix
just check
uv run pytest tests/test_config_profiles.py tests/test_config_cmd.py -v
./thoth_test -r --skip-interactive -q
just test-fix
just test-lint
just test-typecheck
git diff --check
```

Expected:

- `make env-check` exits 0.
- `just check` exits 0.
- Targeted pytest exits 0.
- `./thoth_test -r --skip-interactive -q` exits 0.
- `just test-lint` and `just test-typecheck` exit 0.
- `git diff --check` exits 0.

P21b's verification runs `tests/test_config_profiles_cmd.py` etc.; P21 does not include those files.

---

## Execution Options

Plan complete and saved to `docs/superpowers/plans/2026-04-28-p21-configuration-profiles.md`. Two execution options:

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints.

After P21 merges, start P21b: `docs/superpowers/plans/2026-04-28-p21b-configuration-profiles-crud.md`.
