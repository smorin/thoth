# Thoth `config` Subcommand + XDG Layout — Design v1

**Status:** Approved design (2026-04-17). Implementation via TDD.
**Scope:** New `thoth config` subcommand (get/set/unset/list/path/edit/help) and switch of all user-writable filesystem paths to XDG Base Directory Specification. No migration of legacy paths.
**Related:** `planning/config_arch.md` (broader config/CLI architecture discussion — informs but does not gate this work).

---

## 1. Motivation

Thoth's config is layered (defaults → user TOML → project TOML → env → CLI) but there is no in-CLI way to inspect or modify it. Users must hand-edit TOML. The current user-writable directory is chosen by `platformdirs`, which returns `~/Library/Application Support/thoth` on macOS — this is neither XDG-compliant nor consistent with the Linux path users expect. Additionally, checkpoints (state) and the model cache are stored under the config dir, mixing three XDG categories into one.

Goals:

- Give users `thoth config {get,set,list,...}` for introspection and edits without hand-editing TOML.
- Standardize path layout on XDG Base Directory Spec across all platforms.
- Keep `config.py` focused on schema/loading; route CLI surface through a new module.

## 2. XDG path layout

All three XDG categories, on all platforms (overrides `platformdirs` behavior on macOS). Fallback applies when the env var is **unset or empty** (per spec).

| Purpose | Env var | Default | Thoth subpath |
|---|---|---|---|
| Config | `XDG_CONFIG_HOME` | `~/.config` | `thoth/thoth.config.toml` |
| State (checkpoints) | `XDG_STATE_HOME` | `~/.local/state` | `thoth/checkpoints/` |
| Cache (model cache) | `XDG_CACHE_HOME` | `~/.cache` | `thoth/model_cache/` |

**No migration, no legacy fallback.** Users on a pre-existing install will see fresh empty paths; existing config/checkpoints/caches stay where they are on disk but are not read. If needed, users can manually copy files to the new locations.

### New module: `src/thoth/paths.py`

```python
def user_config_dir() -> Path:  # $XDG_CONFIG_HOME/thoth or ~/.config/thoth
def user_state_dir() -> Path:   # $XDG_STATE_HOME/thoth or ~/.local/state/thoth
def user_cache_dir() -> Path:   # $XDG_CACHE_HOME/thoth or ~/.cache/thoth

def user_config_file() -> Path:       # user_config_dir() / "thoth.config.toml"
def user_checkpoints_dir() -> Path:   # user_state_dir() / "checkpoints"
def user_model_cache_dir() -> Path:   # user_cache_dir() / "model_cache"
```

### Callsites to update (4 files)

- `src/thoth/config.py` (L20, L147, L197) — defaults + `ConfigManager.__init__`.
- `src/thoth/models.py` (L19, L108) — `ModelCache` default cache dir.
- `src/thoth/commands.py` (L18, L72) — `init_command` default config path.
- `src/thoth/help.py` (L12, L106) — `show_init_help` displayed path.

`platformdirs` dependency is dropped from `pyproject.toml` unless another consumer remains. Verified during implementation via grep.

## 3. Subcommand dispatch

Same pattern as existing subcommands — `cli.py` recognizes `"config"` as `args[0]` and routes to `config_command(op, rest, ...)` in a new `src/thoth/config_cmd.py` module. `config.py` stays the schema/loader; `config_cmd.py` owns the CLI surface.

Operations: `get`, `set`, `unset`, `list`, `path`, `edit`, `help`.

## 4. Per-op semantics

### 4.1 `thoth config get <KEY>`

Prints the value for `<KEY>` (dot notation) from the merged effective config.

Flags:
- `--layer {defaults,user,project,env,cli}` — read from one layer only.
- `--raw` — disable `${ENV_VAR}` substitution (show the literal template).
- `--json` — emit JSON instead of the default TOML-scalar rendering.

Exit codes: `0` found; `1` missing key.

### 4.2 `thoth config set <KEY> <VALUE>`

Writes `<KEY>=<VALUE>` to the user config file (creating the file if missing).

Flags:
- `--project` — target `./thoth.config.toml` instead.
- `--string` — force value to be stored as a string regardless of parse.

Value parsing (TOML scalar inference):
- `true`/`false` → bool.
- Unquoted digits (optional leading `-`, optional single `.`) → int or float.
- Anything else → string.

Validation (warn, do not block):
- Unknown root key (not in `ConfigSchema.get_defaults()` top-level keys) → warning.
- Type mismatch with the default at the same path → warning.
- Writes under `modes.*.*` skip the unknown-root warning (user-defined modes are always allowed).

### 4.3 `thoth config unset <KEY>`

Removes `<KEY>` from the target layer's TOML file. Empty parent tables are pruned. No-op on missing key: exit 0 with a note on stderr.

Flags:
- `--project` — target `./thoth.config.toml`.

### 4.4 `thoth config list`

Prints the merged effective config as TOML.

Flags:
- `--layer <name>` — show a single layer.
- `--keys` — emit just the dotted key paths (sorted), for scripting.
- `--json` — machine-readable output.

### 4.5 `thoth config path`

Prints the target config file path (absolute).

Flags:
- `--project` — print `./thoth.config.toml` (prints the would-be path if not yet created).

No flag: prints the user config file path.

### 4.6 `thoth config edit`

Opens the target config file in `$EDITOR` (fallback: `vi`). Creates the file with a minimal header (`# Thoth Configuration File\nversion = "2.0"\n`) if it doesn't exist.

Flags:
- `--project` — edit `./thoth.config.toml`.

### 4.7 `thoth config help`

Renders `show_config_help()` from `help.py`. Also reachable via `thoth help config` and `thoth --help config` (existing dispatch patterns in `ThothCommand.parse_args` and the `help` subcommand in `cli.py`).

## 5. Secrets handling

`providers.*.api_key` values are masked by default in `get` and `list` output (last 4 chars, e.g. `****abcd`). `--show-secrets` reveals. Under `--raw`, `${OPENAI_API_KEY}`-style references are shown literally (unmasked because no substitution happened); absent `--raw`, the substituted value is masked before display.

## 6. TOML writes preserve comments

`tomllib` (stdlib) remains the reader in the precedence loader. `config set`/`unset` and the `edit` scaffold use `tomlkit` to round-trip the target file, preserving user comments and layout. `tomlkit` is added as a dependency in `pyproject.toml`.

## 7. Help text & discoverability

- New `show_config_help()` in `help.py` covers all ops with examples.
- `build_epilog()` gains a `config` line under **Commands**.
- `ThothCommand.parse_args` and the `help` subcommand in `cli.py` recognize `config`.
- `show_general_help` lists `config` alongside `init`, `status`, `list`.

## 8. Testing (TDD — tests first)

### 8.1 Path resolution (`tests/test_paths.py`)

- `user_config_dir()` returns `$XDG_CONFIG_HOME/thoth` when env set; `~/.config/thoth` when unset; `~/.config/thoth` when empty string (per spec).
- Same matrix for `user_state_dir` and `user_cache_dir`.
- Behavior identical across `darwin`/`linux`/`win32` (monkeypatch `sys.platform`).

### 8.2 Config subcommand (`tests/config/test_config_cmd.py`)

- `set general.default_mode exploration` writes to user TOML; merged read returns `exploration`.
- `set --project general.default_mode deep_dive` writes to `./thoth.config.toml`; user TOML untouched.
- Value parsing: `set execution.poll_interval 15` → int; `set execution.parallel_providers true` → bool; `set paths.base_output_dir "./out"` → string.
- `--string execution.poll_interval 15` → string `"15"`.
- Unknown root key emits a warning and still writes.
- Type mismatch emits a warning and still writes.
- `modes.my_mode.model gpt-5` skips the unknown-root warning.
- Existing comments in the target TOML survive a round-trip through `set`.

### 8.3 Get / list / unset

- `get general.default_mode` returns the merged value.
- `get --layer defaults general.default_mode` returns `"default"` even if user overrides it.
- `get --raw providers.openai.api_key` returns the literal `"${OPENAI_API_KEY}"`.
- `list --keys` emits sorted dotted paths.
- `list --json` is valid JSON.
- `unset general.default_mode` removes the key; an empty `[general]` table is pruned.
- `unset` on missing key exits 0 with a stderr note.

### 8.4 Secrets

- `get providers.openai.api_key` masks value to `****` + last 4 chars.
- `--show-secrets` reveals.
- `list` masks by default; `list --show-secrets` reveals.

### 8.5 Path / edit / help

- `config path` prints the user path; `--project` prints `./thoth.config.toml`.
- `config edit` invokes `$EDITOR` with the target path; creates the file when missing (stub editor writes a sentinel; test verifies file contents).
- `config help`, `thoth help config`, and `thoth --help config` all print identical text.

## 9. Files touched

**New:**
- `src/thoth/paths.py`
- `src/thoth/config_cmd.py`
- `tests/test_paths.py`
- `tests/config/test_config_cmd.py` (or split by op)

**Modified:**
- `src/thoth/config.py` — swap `platformdirs.user_config_dir("thoth")` for `paths.user_config_dir()`; update `get_defaults()["paths"]["checkpoint_dir"]`.
- `src/thoth/models.py` — swap to `paths.user_cache_dir() / "model_cache"`.
- `src/thoth/commands.py` — swap `init_command` default config path; register `config` op in `CommandHandler.commands`.
- `src/thoth/cli.py` — dispatch `"config"` in the subcommand chain; extend `--help config` interception.
- `src/thoth/help.py` — `show_config_help()`, `build_epilog()`, `show_general_help`.
- `pyproject.toml` — add `tomlkit`; drop `platformdirs` if no remaining consumers.

## 10. Out of scope (explicitly excluded)

- Migration of existing `~/Library/Application Support/thoth` or prior `~/.config/thoth` content.
- Read-through fallback to legacy locations.
- Interactive `thoth init` wizard rewrite.
- Per-mode config editing UI beyond raw dotted-key writes.
- Config schema versioning or auto-upgrade.
- Refactor of broader CLI/config-precedence gaps called out in `config_arch.md`.

## 11. Open assumptions (approved)

1. Secrets masked by default; `--show-secrets` reveals.
2. `set` validation is warn-only, not blocking.
3. `tomlkit` for writes to preserve user comments.
4. New module `src/thoth/config_cmd.py` keeps `config.py` focused on schema/loading.
