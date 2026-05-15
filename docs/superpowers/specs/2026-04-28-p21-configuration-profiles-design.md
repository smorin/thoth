# Design — Configuration Profile Resolution & Overlay (P21)

**Status:** Draft for review
**Created:** 2026-04-28
**Project ID:** P21
**Target version:** v3.2.0, tentative minor release after the P18/P20 line stabilizes
**Tracking:** `PROJECTS.md` § "Project P21: Configuration Profile Resolution & Overlay"
**Research basis:** `research/configuration_profile_pattern.v1.md`
**Successor:** P21b (CRUD commands) — `docs/superpowers/specs/2026-04-28-p21b-configuration-profiles-crud-design.md`

---

## 1. Goal

Add configuration profile **resolution and overlay** to Doxa Research so users can keep shared config at the normal top level, define named profile overlays in TOML, and select one active profile per invocation. Profiles follow the Configuration Profile Pattern: selection is resolved separately from per-setting overrides, profile keys replace top-level keys per path, missing selected profiles are hard errors, and profile inheritance/multiple active profiles are out of scope.

P21 is intentionally a **read/select** project: users hand-edit `[profiles.<name>]` blocks in TOML. CLI commands for managing profiles (`doxa-research config profiles add/set/use/...`) are deferred to **P21b**. Splitting the work this way means P21 ships a fully usable feature on its own — `--profile`, `DOXA_PROFILE`, and `general.default_profile` all work the moment P21 lands — without bundling the much larger CRUD surface into one project.

## 2. Motivation

Doxa Research already has layered config: defaults, user TOML, project TOML, environment, and CLI. That supports machine-wide and project-specific configuration, but not named "work contexts" such as:

```toml
[general]
default_mode = "thinking"

[providers.openai]
api_key = "${OPENAI_API_KEY}"

[profiles.quick.general]
default_mode = "thinking"

[profiles.research.general]
default_mode = "deep_research"

[profiles.research.execution]
poll_interval = 10
```

Users should be able to run `doxa-research --profile research "topic"` or persist `general.default_profile = "research"` without copying the whole config into separate files. P21 makes that work via hand-edited TOML. P21b adds CLI commands so users don't have to hand-edit.

## 3. Source Pattern Mapping

P21 adopts `research/configuration_profile_pattern.v1.md` as the behavioral source of truth, with Doxa Research-specific names:

| CPP requirement | P21 choice |
|---|---|
| Profile sections overlay top-level settings | Root `[profiles.<name>]` table. Nested keys mirror normal config paths, e.g. `[profiles.prod.general]`. |
| Stage 1 profile selection | `--profile NAME` → `DOXA_PROFILE` → `general.default_profile` → no profile. |
| Stage 2 per-setting resolution | CLI setting override → environment setting override → active profile overlay → normal user/project top-level config → defaults. |
| Per-key replace | A profile value replaces the top-level value at that config path. Dict/list/scalar values replace wholesale; no deep merge inside a profile key. |
| Hard error on missing selected profile | Missing selected profile raises `ConfigProfileError` with the source: flag, env, or config pointer. |
| No privileged profile name | `default`, `current`, and `prod` are ordinary names. There is no implicit `[profiles.default]`. |
| No prompts | Profile resolution never prompts; no profile means no overlay. |
| CRUD out of CPP scope | Deferred to **P21b**. P21 ships hand-edit-only profile management. |

## 4. Decisions

### Q1. Where does profile selection live?

Profile selection is global, not research-only. The root Click command gets a new `--profile PROFILE` option. Subcommands that load config honor it through the same inherited-option policy that already honors `--config`. Research fallback forms, `doxa-research ask`, `doxa-research config get/list`, `doxa-research providers list/check`, `doxa-research modes list`, `status`, `list`, and `init` load config through `ConfigManager` and therefore see the active profile when they honor inherited config options.

### Q2. What is the persisted pointer field?

P21 uses `general.default_profile`, not a root-level `default_profile`. CPP allows the pointer field name to be configured, and Doxa Research already keeps persistent defaults under `[general]` (`default_mode`, `default_project`). Keeping `default_profile` there avoids adding a new root scalar convention.

### Q3. How does profile overlay compose with user/project tiers?

P21 keeps existing base layering, then adds a single `profile` layer between project config and environment overrides:

```text
defaults
user top-level config
project top-level config
active profile overlay
environment per-setting overrides
CLI per-setting overrides
```

Profile lookup uses project before user. If both user and project define `[profiles.prod]`, the project profile shadows the user profile wholesale. They are not merged. The selected profile name is resolved once, then the winning profile table becomes `layers["profile"]`.

### Q4. How are profiles represented in TOML?

Profiles live under the reserved root key `profiles`. A profile's nested structure mirrors normal config paths:

```toml
[profiles.fast.general]
default_mode = "thinking"

[profiles.fast.execution]
poll_interval = 5

[profiles.fast.providers.openai]
api_key = "${OPENAI_FAST_API_KEY}"
```

Profile command keys are dotted relative to the profile root. This command:

```bash
doxa config profiles set fast general.default_mode thinking
```

writes:

```toml
[profiles.fast.general]
default_mode = "thinking"
```

### Q5. How are profiles managed in P21?

By **hand-editing TOML.** P21 ships no CLI commands for adding, setting, or removing profile keys. Users open `~/.config/doxa-research/doxa-research.config.toml` (or the project `./doxa.config.toml` / `./.doxa-research.config.toml`) and write `[profiles.<name>.<section>]` tables directly. Selection (`--profile`, `DOXA_PROFILE`, `general.default_profile`) works the moment P21 lands.

CLI management commands ship in **P21b** (`doxa-research config profiles list/show/current/set-default/unset-default/add/set/unset/remove`). The split is intentional: P21 delivers the runtime feature; P21b delivers the convenience UI. Hand-editing remains supported even after P21b ships — the CLI is additive.

**`--profile` and `DOXA_PROFILE` are read-only runtime inputs (B12, B20).** Neither writes back to `general.default_profile`. With persisted `general.default_profile = "fast"` and a `--profile bar` invocation:

- `doxa-research config get general.default_profile` returns `"fast"` (the file value).
- The runtime active selection — observable via `cm.profile_selection.name` in P21, and via `doxa-research config profiles current` once P21b lands — is `bar` from source `flag`.

The two views can disagree, by design. CPP REQ-CPP-301 requires reporting the active profile and its source; CPP §6.4 implies the persisted pointer remains static across invocations.

### Q6. What is out of scope for P21?

- All `doxa-research config profiles ...` CLI commands (deferred to P21b).
- Profile inheritance, `source_profile`, `extends`, and profile composition.
- Multiple active profiles.
- Deep-merge behavior inside a key.
- Interactive selection prompts.
- Runtime profile switching after config is loaded.
- A new top-level `doxa-research profiles` command group.
- Provider-specific credential chains beyond normal config values.

## 5. Architecture

### 5.1 New module: `src/doxa_research/config_profiles.py`

This module owns pure profile logic so `config.py` does not grow another large responsibility.

Core types:

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

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
```

Responsibilities:

- Extract profile tables from user/project config dictionaries.
- Resolve `ProfileSelection`.
- Select the winning profile layer by tier.
- Validate missing profile and invalid profile names.
- Return profile-list metadata for `config profiles list`.

### 5.2 `ConfigManager` changes

`ConfigManager.load_all_layers(cli_args)` will:

1. Load defaults, user, project, environment, and CLI as today.
2. Split user/project raw data into top-level config and profile tables.
3. Resolve profile selection from `cli_args["_profile"]`, `DOXA_PROFILE`, and the merged top-level `general.default_profile`.
4. Populate:
   - `self.profile_selection: ProfileSelection`
   - `self.active_profile: ProfileLayer | None`
   - `self.profile_catalog: list[ProfileLayer]`
5. Record the actual project config path used by `_load_project_config()` (one of `./doxa.config.toml`, `./.doxa-research.config.toml`, or `None` if no project file exists) so profile diagnostics can name the source file. `_load_project_config` is updated to return `(data, path)` (or to set a sibling `self._project_config_path`); the catalog only adds project entries when a real path was loaded.
6. Merge `layers["profile"]` after project and before env/cli.

The profile selector key in `cli_args` is private (`"_profile"`) so it does not leak into effective config output as a normal setting.

**`DOXA_PROFILE` is not in `_get_env_overrides`.** Selection (Stage 1) and per-setting overrides (Stage 2) are separate chains per CPP REQ-CPP-004. `DOXA_PROFILE` is read by `resolve_profile_selection`, never as a per-setting override mapped onto `general.default_profile`. Adding it to `env_mappings` would conflate the two stages and reintroduce the AWS aws/aws-cli#113 wart.

### 5.3 CLI root option

`src/doxa_research/cli_subcommands/_options.py` adds:

```python
(("--profile", "profile"), {"help": "Configuration profile to apply"})
```

`src/doxa_research/cli.py` stores `ctx.obj["profile"] = profile`. `_apply_config_path` stays separate; a new helper passes `profile` into config loads that happen inside command handlers.

`src/doxa_research/cli_subcommands/_option_policy.py` adds `"profile": "--profile"` to `ROOT_OPTION_LABELS`, and `DEFAULT_HONOR` becomes `{"config_path", "profile"}` for config-loading commands.

### 5.4 Threading `--profile` into existing config-loading entry points

The plan's "thread profile through subcommands" sweep MUST include `src/doxa_research/config_cmd.py` (specifically `_load_manager` and every `get_config_*_data` entry that builds a merged view) and the existing `cli_subcommands/config.py` leaves (`get`, `list`, etc.). Without this, `doxa-research --profile fast config get general.default_mode` would silently load without the profile applied. Concretely:

- `_load_manager(config_path, profile=None)` accepts an optional profile and forwards it as `cli_args={"_profile": profile}`.
- `get_config_get_data(...)` and siblings accept `profile: str | None = None` and pass it down to `_load_manager`.
- Click leaves call `inherited_value(ctx, "profile")` and forward it.

P21 does not add new `config profiles ...` leaves; it only ensures the existing leaves honor `--profile`. New leaves (`list`/`show`/`current`/`use`/...) are P21b's responsibility.

### 5.5 Errors

`src/doxa_research/errors.py` adds `ConfigProfileError(DoxaError)`. Error messages include the offending profile and source:

```text
Profile 'prdo' not found (from --profile flag).
Available profiles: prod, research.
```

In P21 the suggestion text points to hand-editing:

```text
Add a [profiles.prdo] block to your config file, or check the spelling.
Available profiles: prod, research.
```

Once P21b lands, the suggestion text is updated to point at `doxa-research config profiles list` and `doxa-research config profiles add NAME`. The error class itself is unchanged across the two projects.

## 6. Testing Strategy

Tests are written before implementation. The P21 test surface is `tests/test_config_profiles.py` only. CRUD tests (`tests/test_config_profiles_cmd.py`) belong to P21b.

- `tests/test_config_profiles.py`
  - no profile leaves current config unchanged;
  - `--profile` beats `DOXA_PROFILE`;
  - `DOXA_PROFILE` beats `general.default_profile`;
  - profile values overlay top-level values;
  - environment and CLI per-setting values beat profile values;
  - project profile shadows user profile wholesale;
  - missing selected profiles raise `ConfigProfileError` naming the source for **all three** sources (flag, env, config pointer) — load-time error per REQ-CPP-103;
  - `general.default_profile` survives the user/project profile-table splitting (i.e. is still readable via `cm.get(...)`);
  - the catalog records the actual project config path (`./doxa.config.toml` *or* `./.doxa-research.config.toml`) used by `_load_project_config`;
  - `DOXA_PROFILE` is not added to `_get_env_overrides` (regression guard);
  - root `--profile` reaches `doxa-research config get` / `doxa-research config list` (proves the threading sweep is complete);
  - persisted `general.default_profile` is not mutated by runtime `--profile`/`DOXA_PROFILE` (B20: `cm.profile_selection.name == "bar"` from source `flag` while `cm.get("general.default_profile") == "fast"`).
- Existing regression slices:
  - `tests/test_config_cmd.py`
  - `tests/test_p16_dispatch_parity.py`
  - targeted `./doxa_test` rows for config/help if profile flags touch help output.

## 7. Documentation

Docs updated in P21:

- `README.md`: hand-edit profile config examples and invocation examples for:
  - changing the default mode/project through a selected profile;
  - running all currently-available deep-research providers from one `deep_research` mode profile (`["openai", "perplexity"]` today, with a "future-ready" callout pointing at the planned gemini provider — analogous to the interactive-mode treatment);
  - forcing `deep_research` to a single provider/agent;
  - using an immediate default mode such as `thinking`;
  - storing a future-ready profile whose default points at an interactive mode name even before that runtime mode exists;
  - explaining that `doxa-research config get general.default_profile` shows the persisted pointer only, and that `--profile`/`DOXA_PROFILE` are read-only runtime inputs;
  - a forward pointer noting that `doxa-research config profiles ...` CLI commands ship in P21b.
- `manual_testing_instructions.md`: profile resolution smoke checks (no CRUD checks — those land in P21b).
- `src/doxa_research/help.py`: `doxa-research help config` mentions `--profile` and the hand-edit path.
- `PROJECTS.md`: P21 references this spec, the implementation plan, and `research/configuration_profile_pattern.v1.md`.

## 8. Acceptance Criteria

- `research/configuration_profile_pattern.v1.md` is referenced from P21.
- `doxa-research --profile prod ...` applies `[profiles.prod]`.
- `DOXA_PROFILE=prod doxa-research ...` applies `[profiles.prod]` when `--profile` is absent.
- `general.default_profile = "prod"` applies `[profiles.prod]` when flag and env are absent.
- Missing selected profile is a hard error and names the selection source for all three selection sources (flag, env, and config pointer), surfaced at config load time.
- Environment and CLI per-setting overrides still beat active profile values.
- Project profile shadows user profile of the same name; no profile table merging.
- The catalog reports the actual project file (`./doxa.config.toml` or `./.doxa-research.config.toml`) used by `_load_project_config`, not a hardcoded path.
- Root `--profile` reaches `doxa-research config get` and other existing config-loading subcommands via the threaded plumbing; `doxa-research --profile fast config get general.default_mode` returns the profile's value.
- `--profile` and `DOXA_PROFILE` never write back to `general.default_profile`. With persisted `general.default_profile = "fast"`, running `doxa-research --profile bar config get general.default_profile` returns `"fast"`, while `cm.profile_selection` reports `name="bar"` from source `flag`.
- Profile overlay is data-driven: a profile can store and list future config values, including `general.default_mode = "interactive"`, even if command execution for that mode lands in a later project.
- README/profile docs include hand-edit examples for changing defaults, all-currently-available-provider deep research (with a future-ready gemini callout), single-provider deep research, immediate mode, and future interactive default mode, plus a forward pointer to P21b for CLI management.
- `git diff --check`, targeted pytest, `just check`, and relevant `./doxa_test` slices pass before implementation is marked complete.
