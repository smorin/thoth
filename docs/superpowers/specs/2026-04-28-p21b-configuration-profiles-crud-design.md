# Design — Configuration Profile CRUD Commands (P21b)

**Status:** Draft for review
**Created:** 2026-04-28
**Project ID:** P21b
**Target version:** v3.3.0 (or later, after P21 ships)
**Tracking:** `PROJECTS.md` § "Project P21b: Configuration Profile CRUD Commands"
**Depends on:** P21 — `docs/superpowers/specs/2026-04-28-p21-configuration-profiles-design.md`
**Research basis:** `research/configuration_profile_pattern.v1.md`

---

## 1. Goal

Add `thoth config profiles ...` CLI commands so users can manage configuration profiles without hand-editing TOML. P21b is purely additive: profile *behavior* (selection, overlay, error semantics) is fully delivered by P21 and stays unchanged. P21b adds the management UI on top.

The new subgroup:

```text
thoth config profiles list [--json] [--show-shadowed]
thoth config profiles show NAME [--json] [--show-secrets]
thoth config profiles current [--json]
thoth config profiles set-default NAME [--project] [--json]
thoth config profiles unset-default [--project] [--json]
thoth config profiles add NAME [--project] [--json]
thoth config profiles set NAME KEY VALUE [--project] [--string] [--json]
thoth config profiles unset NAME KEY [--project] [--json]
thoth config profiles remove NAME [--project] [--json]
```

Default writes target the user config. `--project` targets `./thoth.config.toml`, matching `thoth config set --project`. `--config PATH` and `--project` remain mutually exclusive.

## 2. Motivation

P21 ships profile resolution and overlay. Users can run `thoth --profile fast "topic"` and persist `general.default_profile = "fast"` — but only by hand-editing TOML. This is fine for v1 but cumbersome for day-to-day workflows: adding a new profile means opening an editor; persisting a selection means knowing the exact key path.

P21b removes that friction. The data functions and Click leaves use the same `tomlkit` patterns as the existing `thoth config set/unset/list` commands, so the surface is familiar and the implementation reuses existing helpers (`_target_path`, `_reject_config_project_conflict`, `_load_toml_doc`, `_parse_value`, `_mask_in_tree`, `_to_plain`). Profile `unset` and `unset-default` must use a no-prune leaf-removal helper rather than `_unset_in_doc`, because empty parent tables and their comments are part of the P21b contract.

## 3. Decisions

### Q1. Where do the new commands live in the command tree?

Under `thoth config profiles`. Not at the top level. Reasons:

- `thoth config` is already the established home for config-management subcommands (`get`, `set`, `unset`, `list`).
- A top-level `thoth profiles` group would collide with the future research-options surface and create a second discovery surface.
- `thoth config profiles` is consistent with `thoth modes` (which lives at top level because modes are a research concept, not a config concept).

The two persisted-default mutators are named **`set-default NAME`** and **`unset-default`** rather than the shorter `use NAME` / `clear`. The shorter names were rejected for ambiguity:

- `use` reads as shell-style "activate for this session" but the actual behavior is a persistent file write to `general.default_profile`. The naming mismatch is a typo trap.
- `clear` does not say *what* it clears (the persisted default pointer? a profile's contents? the runtime selection?). `unset-default` mirrors the persisted key (`general.default_profile`) and pairs symmetrically with the existing `config set` / `config unset`.

### Q2. How are read-only leaves vs mutator leaves treated for inherited `--profile`?

**Read-only leaves** (`list`, `show`, `current`) honor the inherited root `--profile` because they read merged config; the active profile changes the values they report. They include `"profile"` in `honored_options` (i.e. `DEFAULT_HONOR`).

**Mutator leaves** (`add`, `set`, `unset`, `remove`, `set-default`, `unset-default`) reject the inherited root `--profile`. They omit `"profile"` from `honored_options`. Click rejects `thoth --profile foo config profiles add bar` with the standard "no such option" error. Mutators operate on the positional `NAME` argument only; the runtime active profile is irrelevant to a mutation target. Accepting `--profile` here would be a typo trap with no useful behavior.

### Q3. How does `set-default NAME` validate the target?

Before persisting `general.default_profile = NAME`, build a transient `ConfigManager` for the same target view that the command will write. When inherited `--config PATH` is present, pass that path to the constructor (`ConfigManager(PATH)`) so profiles defined only in the custom config participate in `cm.profile_catalog`; do not pass `config_path` through `load_all_layers(...)`. Then call `load_all_layers({})` and check `NAME` against `cm.profile_catalog` (the union of the target user/custom tier plus the current project tier, computed by P21). If `NAME` is absent from the catalog, raise `ConfigProfileError(f"Profile {NAME!r} not found", available_profiles=..., source="thoth config profiles set-default")`.

Cross-tier resolution is allowed: `thoth config profiles set-default prod` succeeds when `prod` is defined only in the project tier even though the pointer is being written to the user config. `thoth --config /tmp/thoth.config.toml config profiles set-default fast` succeeds when `fast` exists only in `/tmp/thoth.config.toml`. The next load resolves the pointer via the same catalog entry.

This honors REQ-CPP-103's spirit (always-loadable file state) and prevents the most common typo class.

### Q4. What does `unset KEY` do to empty parent tables?

`unset` removes exactly the named leaf key. Empty parent tables are left in place:

- `unset fast general.default_mode` removes `default_mode` but leaves `[profiles.fast.general] = {}` and `[profiles.fast]`.
- `unset-default` (which removes `general.default_profile`) leaves `[general]` even if it becomes empty.

Pruning empty parents would surprise users who expect `unset` to be a one-key operation, and would risk eating user comments attached to the table header. Users who want a profile gone can run `remove NAME`. Users who want a parent table gone can hand-edit.

### Q5. What does `current` report?

`thoth config profiles current` reports the runtime active selection plus its source (`flag`, `env`, `config`, or `none`). Honors `--profile` and `THOTH_PROFILE` so:

```bash
$ thoth --profile bar config profiles current
Active profile: bar (from --profile flag)

$ THOTH_PROFILE=fast thoth config profiles current --json
{"status": "ok", "data": {"active_profile": "fast", "selection_source": "env", ...}}
```

This is the runtime view. It can disagree with `thoth config get general.default_profile` (which is the persisted view). See P21 §4.Q5 for the read-only-runtime-input invariant.

### Q6. What does `list --show-shadowed` report?

P21 profile resolution already defines the shadowing rule: when user and project tiers both define the same profile name, the project profile shadows the user profile wholesale. `thoth config profiles list` uses that same rule.

Default `list` output shows one winning row per profile name. For duplicate names, the project row is shown and the user row is hidden. `--show-shadowed` includes the hidden lower-precedence row so users can diagnose why a user profile is not active. Rows are sorted by profile name; for duplicate names in `--show-shadowed` output, the winning row appears first and the shadowed row follows it.

Each JSON profile row includes:

```json
{
  "name": "prod",
  "tier": "project",
  "path": "/repo/thoth.config.toml",
  "active": true,
  "shadowed": false,
  "shadowed_by": null
}
```

For a shadowed user row:

```json
{
  "name": "prod",
  "tier": "user",
  "path": "/home/user/.config/thoth/thoth.config.toml",
  "active": false,
  "shadowed": true,
  "shadowed_by": {
    "tier": "project",
    "path": "/repo/thoth.config.toml"
  }
}
```

`active` means "this row is the winning active layer", so a shadowed row is never active even when it has the selected profile name. Human output includes a status marker such as `active`, `available`, or `shadowed by project`.

### Q7. Idempotence of `add` and `remove`

`add NAME` and `remove NAME` are **idempotent**. Repeating either against a stable target is a no-op that exits 0.

- `add NAME` on a missing profile creates `[profiles.<name>]` and returns `{"created": True, "profile": NAME, "path": ...}`. On an existing profile it returns `{"created": False, "profile": NAME, "path": ...}` without touching the file.
- `remove NAME` on an existing profile deletes the `[profiles.<name>]` block and returns `{"removed": True, "profile": NAME, "path": ...}`. On a missing profile it returns `{"removed": False, "profile": NAME, "path": ...}` without touching the file.

Rationale: matches `mkdir -p` / `kubectl apply` semantics, makes both commands script-safe, and keeps the surface symmetric. Users who want strict-not-found feedback for typos in `remove` can read the `removed` field; the JSON envelope is unambiguous.

### Q8. Naming convention for data functions

All nine data functions are singular-named:

```
get_config_profile_list_data
get_config_profile_show_data
get_config_profile_current_data
get_config_profile_set_default_data
get_config_profile_unset_default_data
get_config_profile_add_data
get_config_profile_set_data
get_config_profile_unset_data
get_config_profile_remove_data
```

Singular for all is a deliberate symmetry choice — easier to grep, easier to autocomplete, no exception cases to remember.

## 4. Architecture

### 4.1 `src/thoth/config_cmd.py`

Add nine `get_config_profile_*_data` functions next to the existing `get_config_*_data` functions. Each function:

- Accepts `project: bool`, `config_path: str | Path | None`, and any operation-specific arguments.
- Calls `_reject_config_project_conflict(project, config_path)` first.
- Resolves the target file via `_target_path(project, config_path)`.
- Loads the TOML document via `_load_toml_doc(path)`.
- For nested profile keys, prepends `profiles.<name>.` to the dotted key path.
- For mutators, writes via `tomlkit` and saves; for readers, returns plain dict data via `_to_plain`.
- Returns a structured `dict` with operation-specific keys (e.g. `{"created": True}` for `add`, `{"wrote": True, "profile": ..., "key": ..., "path": ...}` for `set`).

Add corresponding helpers:

```python
def _profiles_table(doc: tomlkit.TOMLDocument) -> Any:
    if "profiles" not in doc:
        doc["profiles"] = tomlkit.table()
    return doc["profiles"]


def _profile_table(doc: tomlkit.TOMLDocument, name: str, *, create: bool) -> Any | None:
    profiles = _profiles_table(doc)
    if name not in profiles:
        if not create:
            return None
        profiles[name] = tomlkit.table()
    return profiles[name]
```

`set-default NAME` validation builds a transient `ConfigManager` with the inherited `config_path` when present, calls `load_all_layers({})`, and checks the name against `cm.profile_catalog` before calling `tomlkit` to write `general.default_profile`.

`list` builds rows from `cm.profile_catalog`. Without `show_shadowed`, collapse duplicate names to the same winning layer that `resolve_profile_layer(...)` would choose (project beats user). With `show_shadowed=True`, include shadowed lower-precedence rows and set their `shadowed` / `shadowed_by` fields.

`current` builds a transient `ConfigManager` (honoring inherited `config_path` and `profile`) and returns `cm.profile_selection.name`, `.source`, and `.source_detail`.

### 4.2 `src/thoth/cli_subcommands/config.py`

Add a nested Click group `profiles` and nine leaf commands. Group definition:

```python
@config.group(name="profiles", invoke_without_command=True)
@click.pass_context
def config_profiles(ctx: click.Context) -> None:
    """Manage configuration profiles."""
    if ctx.invoked_subcommand is None:
        validate_inherited_options(ctx, "config profiles", DEFAULT_HONOR)
        click.echo(
            "Error: config profiles requires an op "
            "(list|show|current|set-default|unset-default|add|set|unset|remove)",
            err=True,
        )
        ctx.exit(2)
```

Leaf commands:

- `list`, `show`, `current`: `validate_inherited_options(ctx, ..., DEFAULT_HONOR)` — honor both `config_path` and `profile`. The `list` leaf also has a typed `--show-shadowed` flag.
- `add`, `set`, `unset`, `remove`, `set-default`, `unset-default`: `validate_inherited_options(ctx, ..., honored_options={"config_path"})` — drop `profile` so Click rejects `thoth --profile foo config profiles add bar`.

JSON output uses the existing envelope helpers (`emit_json`).

Human-readable output is terse:

```text
Added profile 'fast'
Updated profile 'fast': general.default_mode = thinking
Set default profile to 'fast'
Unset default profile
Removed profile 'fast'
Active profile: fast (from --profile flag)
Active profile: (none)
```

### 4.3 Lint and JSON-envelope fixtures

`tests/test_json_envelopes.py` adds rows for the new JSON-capable commands; `tests/test_ci_lint_rules.py` adds the new commands to the JSON command inventory.

## 5. Testing Strategy

Tests live in `tests/test_config_profiles_cmd.py`.

- Round-trip CRUD: `add` → `set` → `show` → `unset` → `remove` for the user config.
- `set-default` and `unset-default` write `general.default_profile` to the target file; `unset-default` leaves an empty `[general]` in place.
- `--project` writes `./thoth.config.toml`; `--config PATH` writes the custom file; `--project` + `--config` errors with `PROJECT_CONFIG_CONFLICT`.
- Deep-path coverage: `set fast general.default_mode thinking` produces `[profiles.fast.general]` at depth 4; `unset` removes only the leaf and leaves `[profiles.fast.general] = {}` in place.
- tomlkit comment preservation: a comment above `[profiles.fast]` and a comment on `default_mode` line both survive a `set` then `unset` round-trip (asserted via `Path.read_text()` containing the comment text).
- `set-default ghost` raises `ConfigProfileError` (catalog rejection); `set-default prod` succeeds when `prod` lives only in the project tier; inherited `--config PATH` succeeds when the profile exists only in that custom file.
- Mutator leaves reject `--profile foo`; read-only leaves accept it.
- `list` hides shadowed same-name user profiles by default and includes them with `shadowed=true` plus `shadowed_by` metadata when `--show-shadowed` is passed.
- `current` reports the runtime active selection plus its source for `flag`, `env`, `config`, and `none`.
- B20 end-to-end: persisted `fast` + `--profile bar` → `config get general.default_profile` returns `fast`, `config profiles current` returns `bar` from source `flag`, the file is unchanged after the flag invocation.
- JSON envelopes for `list`, `show`, `current`, `set-default`, `unset-default`, `add`, `set`, `unset`, `remove` have correct status/data/error shape.

Existing regression slices: `tests/test_config_cmd.py`, `tests/test_p16_dispatch_parity.py`.

## 6. Documentation

Docs updated in P21b:

- `README.md`: command examples for each leaf, plus the `config get general.default_profile` (persisted) vs `config profiles current` (runtime) distinction.
- `manual_testing_instructions.md`: `thoth config profiles ...` smoke checks, including expected error cases (`set-default ghost`, `--profile foo add bar`).
- `src/thoth/help.py`: `thoth help config` includes the new `config profiles` subgroup.
- `PROJECTS.md`: P21b references this spec, the P21b plan, P21 (predecessor), and `research/configuration_profile_pattern.v1.md`.
- Update P21's README forward pointer ("CLI commands ship in P21b") to remove the "ship in" phrasing once P21b lands.

## 7. Acceptance Criteria

- All nine `get_config_profile_*_data` functions exist with singular naming, are exported in `__all__`, and round-trip via `tomlkit`.
- All nine Click leaves under `thoth config profiles` exist and are wired into the `config` group.
- Read-only leaves (`list`, `show`, `current`) honor inherited `--profile`; mutator leaves (`add`/`set`/`unset`/`remove`/`set-default`/`unset-default`) reject it with the standard "no such option" Click error.
- `list --show-shadowed` includes same-name lower-precedence rows with stable `shadowed` / `shadowed_by` JSON metadata; default `list` hides those rows.
- `set-default NAME` rejects unknown names against the resolved catalog; cross-tier and inherited `--config PATH` profile definitions are valid.
- `unset` removes only the named leaf; empty parent tables are left in place.
- `remove NAME` deletes the whole `[profiles.<name>]` block.
- TOML comments and formatting survive `set`/`unset` round-trips through `tomlkit`, asserted by a test that reads the file as text.
- `--config PATH` and `--project` remain mutually exclusive (`PROJECT_CONFIG_CONFLICT` error).
- JSON envelopes have correct status/data/error shape for every JSON-capable leaf.
- `current` reports `name` plus `source` (`flag`, `env`, `config`, `none`).
- B20 invariant verified end-to-end: `--profile bar` does not mutate `general.default_profile` written by `set-default fast`.
- README, manual testing instructions, and `help.py` updated; PROJECTS.md task list reflects the implemented commands.
- `git diff --check`, targeted pytest, `just check`, and relevant `./thoth_test` slices pass before implementation is marked complete.
