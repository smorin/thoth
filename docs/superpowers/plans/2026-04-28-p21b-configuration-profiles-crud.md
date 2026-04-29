# P21b Configuration Profile CRUD Commands — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `thoth config profiles list/show/current/set-default/unset-default/add/set/unset/remove` so users can manage profiles from the CLI without hand-editing TOML.

**Architecture:** Reuse `src/thoth/config_cmd.py` data-function patterns and `tomlkit` helpers. Add nine `get_config_profile_*_data` functions and a nested Click group `profiles` under `thoth config`. Read-only leaves (`list`/`show`/`current`) honor inherited `--profile`; mutator leaves (`add`/`set`/`unset`/`remove`/`set-default`/`unset-default`) reject it.

**Tech Stack:** Python 3.11+, Click 8.x, tomlkit, pytest.

**Spec:** `docs/superpowers/specs/2026-04-28-p21b-configuration-profiles-crud-design.md`
**Predecessor:** `docs/superpowers/plans/2026-04-28-p21-configuration-profiles.md` (P21 — must merge first)
**Research:** `research/configuration_profile_pattern.v1.md`

---

## Prerequisites

P21 must be merged before starting P21b. P21b assumes:

- `src/thoth/config_profiles.py` exists with `ProfileSelection`, `ProfileLayer`, `collect_profile_catalog`, `resolve_profile_selection`, `resolve_profile_layer`.
- `ConfigManager` exposes `profile_selection`, `active_profile`, `profile_catalog`.
- `ConfigProfileError` is in `src/thoth/errors.py`.
- Root `--profile` option is registered, threaded through `_load_manager`, and honored by existing `config get` / `config list`.
- `DEFAULT_HONOR` already includes `"profile"`.

If any of these are missing, finish P21 first.

---

## File Map

- Modify: `src/thoth/config_cmd.py` — add nine `get_config_profile_*_data` functions and TOML helpers (`_profiles_table`, `_profile_table`).
- Modify: `src/thoth/cli_subcommands/config.py` — add `config profiles` Click group with nine leaves.
- Modify: `src/thoth/help.py`, `README.md`, `manual_testing_instructions.md`, `PROJECTS.md` — document command examples and the persisted-vs-runtime distinction.
- Create: `tests/test_config_profiles_cmd.py` — data functions + Click commands + comment preservation + deep-path + B12/B16/B17/B20 invariants.
- Modify: `tests/test_json_envelopes.py` — add rows for new JSON-capable profile commands.
- Modify: `tests/test_ci_lint_rules.py` — add the new commands to the JSON command inventory.

---

## Task 1: Profile Management Data Functions

**Files:**
- Create: `tests/test_config_profiles_cmd.py`
- Modify: `src/thoth/config_cmd.py`

- [ ] **Step 1: Write failing command data tests**

Create `tests/test_config_profiles_cmd.py`:

```python
from __future__ import annotations

from pathlib import Path

import tomllib

from thoth.config_cmd import (
    get_config_profile_add_data,
    get_config_profile_current_data,
    get_config_profile_list_data,
    get_config_profile_remove_data,
    get_config_profile_set_data,
    get_config_profile_set_default_data,
    get_config_profile_show_data,
    get_config_profile_unset_data,
    get_config_profile_unset_default_data,
)


def test_profile_add_set_show_unset_remove_round_trip(isolated_thoth_home: Path) -> None:
    add = get_config_profile_add_data("fast", project=False, config_path=None)
    assert add["created"] is True

    set_data = get_config_profile_set_data(
        "fast",
        "general.default_mode",
        "thinking",
        project=False,
        force_string=False,
        config_path=None,
    )
    assert set_data["wrote"] is True

    show = get_config_profile_show_data(
        "fast",
        show_secrets=False,
        config_path=None,
    )
    assert show["profile"]["general"]["default_mode"] == "thinking"

    unset = get_config_profile_unset_data(
        "fast",
        "general.default_mode",
        project=False,
        config_path=None,
    )
    assert unset["removed"] is True

    remove = get_config_profile_remove_data("fast", project=False, config_path=None)
    assert remove["removed"] is True


def test_profile_set_default_and_unset_default_write_general_default_profile(
    isolated_thoth_home: Path,
) -> None:
    get_config_profile_add_data("fast", project=False, config_path=None)
    set_default = get_config_profile_set_default_data(
        "fast", project=False, config_path=None
    )
    assert set_default["default_profile"] == "fast"

    from thoth.paths import user_config_file

    data = tomllib.loads(user_config_file().read_text())
    assert data["general"]["default_profile"] == "fast"

    unset_default = get_config_profile_unset_default_data(
        project=False, config_path=None
    )
    assert unset_default["removed"] is True
    data = tomllib.loads(user_config_file().read_text())
    assert "default_profile" not in data.get("general", {})


def test_profile_project_conflicts_with_config_path(tmp_path: Path) -> None:
    data = get_config_profile_add_data(
        "fast",
        project=True,
        config_path=tmp_path / "custom.toml",
    )
    assert data["error"] == "PROJECT_CONFIG_CONFLICT"


def test_profile_list_reports_active_and_source(isolated_thoth_home: Path) -> None:
    get_config_profile_add_data("fast", project=False, config_path=None)
    get_config_profile_set_default_data("fast", project=False, config_path=None)
    data = get_config_profile_list_data(config_path=None)
    assert data["active_profile"] == "fast"
    assert data["selection_source"] == "config"
    assert [p["name"] for p in data["profiles"]] == ["fast"]


def test_profile_set_default_rejects_unknown_profile(isolated_thoth_home: Path) -> None:
    """B16: `set-default NAME` validates against the resolved catalog before persisting."""
    from thoth.errors import ConfigProfileError

    import pytest

    with pytest.raises(ConfigProfileError) as exc:
        get_config_profile_set_default_data("ghost", project=False, config_path=None)
    assert "ghost" in exc.value.message


def test_profile_set_default_accepts_project_only_profile_against_user_config(
    isolated_thoth_home: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """B16 cross-tier: `set-default prod` when prod lives in project tier writes pointer to user config."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "thoth.toml").write_text(
        'version = "2.0"\n[profiles.prod.general]\ndefault_mode = "thinking"\n'
    )

    out = get_config_profile_set_default_data("prod", project=False, config_path=None)
    assert out["default_profile"] == "prod"


def test_profile_current_reports_runtime_active_and_source(
    isolated_thoth_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """B12: `config profiles current` shows runtime active selection + source."""
    monkeypatch.delenv("THOTH_PROFILE", raising=False)
    get_config_profile_add_data("fast", project=False, config_path=None)
    get_config_profile_set_default_data("fast", project=False, config_path=None)

    monkeypatch.setenv("THOTH_PROFILE", "fast")
    data = get_config_profile_current_data(config_path=None)
    assert data["active_profile"] == "fast"
    assert data["selection_source"] == "env"


def test_profile_set_unset_preserves_tomlkit_comments(
    isolated_thoth_home: Path,
) -> None:
    """B9: TOML comments around the profile section survive set/unset."""
    from thoth.paths import user_config_file

    user_config_file().write_text(
        '# pinned profile\n[profiles.fast.general]\n# default mode\ndefault_mode = "thinking"\n'
    )
    get_config_profile_set_data(
        "fast", "general.timeout", "30",
        project=False, force_string=False, config_path=None,
    )
    text = user_config_file().read_text()
    assert "# pinned profile" in text
    assert "# default mode" in text

    get_config_profile_unset_data(
        "fast", "general.timeout", project=False, config_path=None,
    )
    text = user_config_file().read_text()
    assert "# pinned profile" in text
    assert "# default mode" in text


def test_profile_unset_leaves_empty_parent_table_in_place(
    isolated_thoth_home: Path,
) -> None:
    """B17: unset removes only the leaf; empty parent tables remain."""
    import tomllib

    from thoth.paths import user_config_file

    get_config_profile_add_data("fast", project=False, config_path=None)
    get_config_profile_set_data(
        "fast", "general.default_mode", "thinking",
        project=False, force_string=False, config_path=None,
    )
    get_config_profile_unset_data(
        "fast", "general.default_mode", project=False, config_path=None,
    )

    data = tomllib.loads(user_config_file().read_text())
    assert "fast" in data["profiles"]
    assert "general" in data["profiles"]["fast"]
    assert "default_mode" not in data["profiles"]["fast"]["general"]


def test_profile_set_unset_handles_deep_four_level_path(
    isolated_thoth_home: Path,
) -> None:
    """B10: depth-4 path `profiles.fast.general.default_mode` set/unset round-trip."""
    import tomllib

    from thoth.paths import user_config_file

    get_config_profile_add_data("fast", project=False, config_path=None)
    set_out = get_config_profile_set_data(
        "fast", "general.default_mode", "thinking",
        project=False, force_string=False, config_path=None,
    )
    assert set_out["wrote"] is True

    data = tomllib.loads(user_config_file().read_text())
    assert data["profiles"]["fast"]["general"]["default_mode"] == "thinking"

    unset_out = get_config_profile_unset_data(
        "fast", "general.default_mode", project=False, config_path=None,
    )
    assert unset_out["removed"] is True
```

- [ ] **Step 2: Run command data tests and confirm failure**

```bash
uv run pytest tests/test_config_profiles_cmd.py -v
```

Expected: import failures for new data functions.

- [ ] **Step 3: Add TOML helpers**

In `src/thoth/config_cmd.py`, add helpers near `_load_toml_doc`:

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
    table = profiles[name]
    return table if hasattr(table, "keys") else None
```

- [ ] **Step 4: Add profile CRUD data functions**

Add the nine functions named by the tests, all singular (`get_config_profile_{list,show,current,set_default,unset_default,add,set,unset,remove}_data`). Reuse `_target_path`, `_reject_config_project_conflict`, `_load_toml_doc`, `_parse_value`, `_unset_in_doc`, `_mask_in_tree`, and `_to_plain`. For nested profile keys, prepend `profiles.<name>.` when writing or deleting:

```python
profile_key = f"profiles.{name}.{key}"
```

Use the existing `get_config_set_data(...)` and `get_config_unset_data(...)` patterns where possible, but keep profile commands explicit so error data includes `profile`, `key`, `path`, and command-specific booleans.

**`set-default NAME` validation (B16):** before writing `general.default_profile = NAME`, build a transient `ConfigManager`, call `load_all_layers({})`, and check `NAME` against `cm.profile_catalog`. If absent, raise `ConfigProfileError(f"Profile {name!r} not found", available_profiles=..., source="thoth config profiles set-default")`. The cross-tier case (e.g. `prod` defined only in the project tier) is allowed because the catalog spans both tiers.

**`current` data function (B12):** loads a fresh `ConfigManager`, returns:

```python
{
    "active_profile": cm.profile_selection.name,    # str | None
    "selection_source": cm.profile_selection.source,  # "flag" | "env" | "config" | "none"
    "selection_detail": cm.profile_selection.source_detail,  # str | None
}
```

It honors inherited `--profile` so `thoth --profile foo config profiles current` reports `flag` as the source.

**`unset` semantics (B17):** `_unset_in_doc` removes only the leaf key. Do **not** prune empty parent tables. Leave `[profiles.fast.general] = {}` and `[general] = {}` in place; users can `remove fast` to delete a whole profile and hand-edit if they want a parent table gone.

- [ ] **Step 5: Export the data functions**

Add every new `get_config_profile_*_data` function to `__all__`.

- [ ] **Step 6: Run command data tests**

```bash
uv run pytest tests/test_config_profiles_cmd.py -v
```

Expected: data-function tests pass.

- [ ] **Step 7: Commit Task 1**

```bash
git add src/thoth/config_cmd.py tests/test_config_profiles_cmd.py
git commit -m "feat: add profile config data functions"
```

---

## Task 2: `thoth config profiles` Click Commands

**Files:**
- Modify: `tests/test_config_profiles_cmd.py`
- Modify: `src/thoth/cli_subcommands/config.py`
- Modify: `tests/test_json_envelopes.py`
- Modify: `tests/test_ci_lint_rules.py`

- [ ] **Step 1: Add failing Click command tests**

Append to `tests/test_config_profiles_cmd.py`:

```python
from click.testing import CliRunner

from thoth.cli import cli


def test_config_profiles_click_set_and_set_default(isolated_thoth_home: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "profiles", "add", "fast"])
    assert result.exit_code == 0, result.output

    result = runner.invoke(
        cli,
        ["config", "profiles", "set", "fast", "general.default_mode", "thinking"],
    )
    assert result.exit_code == 0, result.output

    result = runner.invoke(cli, ["config", "profiles", "set-default", "fast"])
    assert result.exit_code == 0, result.output

    result = runner.invoke(cli, ["config", "get", "general.default_mode"])
    assert result.exit_code == 0, result.output
    assert result.output.strip().splitlines()[-1] == "thinking"


def test_config_profiles_click_list_json(isolated_thoth_home: Path) -> None:
    import json

    runner = CliRunner()
    assert runner.invoke(cli, ["config", "profiles", "add", "fast"]).exit_code == 0
    result = runner.invoke(cli, ["config", "profiles", "list", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "ok"
    assert payload["data"]["profiles"][0]["name"] == "fast"


def test_config_profiles_mutators_reject_root_profile_flag(
    isolated_thoth_home: Path,
) -> None:
    """B7: --profile is not honored by mutator leaves."""
    runner = CliRunner()
    for op_args in (
        ["config", "profiles", "add", "bar"],
        ["config", "profiles", "set", "bar", "general.default_mode", "thinking"],
        ["config", "profiles", "set-default", "bar"],
        ["config", "profiles", "unset-default"],
        ["config", "profiles", "unset", "bar", "general.default_mode"],
        ["config", "profiles", "remove", "bar"],
    ):
        result = runner.invoke(cli, ["--profile", "foo", *op_args])
        assert result.exit_code != 0, f"{op_args} should reject --profile"
        assert "--profile" in result.output


def test_config_profiles_readers_honor_root_profile_flag(
    isolated_thoth_home: Path,
) -> None:
    """B7: --profile IS honored by read-only leaves."""
    runner = CliRunner()
    assert runner.invoke(cli, ["config", "profiles", "add", "fast"]).exit_code == 0
    for op_args in (
        ["config", "profiles", "list"],
        ["config", "profiles", "show", "fast"],
        ["config", "profiles", "current"],
    ):
        result = runner.invoke(cli, ["--profile", "fast", *op_args])
        assert result.exit_code == 0, f"{op_args} should accept --profile: {result.output}"


def test_config_profiles_current_reports_flag_source(
    isolated_thoth_home: Path,
) -> None:
    """B12: profiles current reports the runtime source as 'flag' under --profile."""
    import json

    runner = CliRunner()
    assert runner.invoke(cli, ["config", "profiles", "add", "fast"]).exit_code == 0
    result = runner.invoke(
        cli, ["--profile", "fast", "config", "profiles", "current", "--json"]
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["data"]["active_profile"] == "fast"
    assert payload["data"]["selection_source"] == "flag"


def test_runtime_selection_does_not_mutate_persisted_pointer(
    isolated_thoth_home: Path,
) -> None:
    """B20 end-to-end: --profile/THOTH_PROFILE are read-only; persisted default_profile is unchanged.

    With persisted general.default_profile = "fast", running with --profile bar:
      - `config get general.default_profile` returns "fast" (the persisted file value).
      - `config profiles current` returns "bar" with source "flag".
    Only `config profiles set-default NAME` / `unset-default` mutate the persisted pointer.
    """
    import json

    runner = CliRunner()
    assert runner.invoke(cli, ["config", "profiles", "add", "fast"]).exit_code == 0
    assert runner.invoke(cli, ["config", "profiles", "add", "bar"]).exit_code == 0
    assert runner.invoke(cli, ["config", "profiles", "set-default", "fast"]).exit_code == 0

    # Persisted pointer is "fast"; runtime selection is "bar".
    get_result = runner.invoke(
        cli, ["--profile", "bar", "config", "get", "general.default_profile"]
    )
    assert get_result.exit_code == 0, get_result.output
    assert get_result.output.strip().splitlines()[-1] == "fast"

    current_result = runner.invoke(
        cli, ["--profile", "bar", "config", "profiles", "current", "--json"]
    )
    assert current_result.exit_code == 0, current_result.output
    payload = json.loads(current_result.output)
    assert payload["data"]["active_profile"] == "bar"
    assert payload["data"]["selection_source"] == "flag"

    # Confirm the file is unchanged: re-read without any flag.
    get_after = runner.invoke(cli, ["config", "get", "general.default_profile"])
    assert get_after.output.strip().splitlines()[-1] == "fast"
```

- [ ] **Step 2: Run Click command tests and confirm failure**

```bash
uv run pytest tests/test_config_profiles_cmd.py -k "click or current or runtime" -v
```

Expected: Click reports no `profiles` command.

- [ ] **Step 3: Add nested Click group**

In `src/thoth/cli_subcommands/config.py`, add:

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

Add leaves for `list`, `show`, `current`, `set-default`, `unset-default`, `add`, `set`, `unset`, and `remove`. Each leaf calls the matching data function and emits JSON with `emit_json(data)` when `--json` is passed. Human output should be terse:

```text
Added profile 'fast'
Updated profile 'fast': general.default_mode = thinking
Set default profile to 'fast'
Unset default profile
Removed profile 'fast'
Active profile: fast (from --profile flag)
Active profile: (none)
```

- [ ] **Step 4: Inherited-option policy by leaf (B7)**

Read-only leaves (`list`, `show`, `current`) honor `DEFAULT_HONOR` (which already includes both `"config_path"` and `"profile"` from P21).

Mutator leaves (`add`, `set`, `unset`, `remove`, `set-default`, `unset-default`) call `validate_inherited_options(ctx, "config profiles <op>", honored_options={"config_path"})` — explicitly drop `"profile"` from honored options. This makes `thoth --profile foo config profiles add bar` error with the standard "no such option" message rather than silently ignoring `--profile foo`. Mutators forward only `config_path` via `inherited_value(ctx, "config_path")`.

- [ ] **Step 5: Add JSON envelope rows**

In `tests/test_json_envelopes.py`, add rows for:

```python
("config_profiles_list", ["config", "profiles", "list", "--json"], 0),
("config_profiles_show_missing", ["config", "profiles", "show", "missing", "--json"], 1),
("config_profiles_current", ["config", "profiles", "current", "--json"], 0),
```

In `tests/test_ci_lint_rules.py`, add `config profiles list`, `config profiles show`, and `config profiles current` to the JSON command inventory checked by the lint rule.

- [ ] **Step 6: Run command tests**

```bash
uv run pytest tests/test_config_profiles_cmd.py tests/test_json_envelopes.py -v
```

Expected: profile Click commands and JSON envelope tests pass.

- [ ] **Step 7: Commit Task 2**

```bash
git add src/thoth/cli_subcommands/config.py tests/test_config_profiles_cmd.py tests/test_json_envelopes.py tests/test_ci_lint_rules.py
git commit -m "feat: add config profile commands"
```

---

## Task 3: Help, Docs, and Tracker

**Files:**
- Modify: `src/thoth/help.py`
- Modify: `README.md`
- Modify: `manual_testing_instructions.md`
- Modify: `PROJECTS.md`

- [ ] **Step 1: Add help/doc assertion**

Add a test to `tests/test_config_profiles_cmd.py`:

```python
def test_config_profiles_appears_in_config_help(isolated_thoth_home: Path) -> None:
    result = CliRunner().invoke(cli, ["config", "--help"])
    assert result.exit_code == 0
    assert "profiles" in result.output
```

- [ ] **Step 2: Run the help test and confirm failure if help is missing**

```bash
uv run pytest tests/test_config_profiles_cmd.py::test_config_profiles_appears_in_config_help -v
```

Expected: fail until help output includes the subgroup.

- [ ] **Step 3: Update help text**

Update `src/thoth/help.py` config help text to include:

```text
thoth config profiles list
thoth config profiles current
thoth config profiles add fast
thoth config profiles set fast general.default_mode thinking
thoth config profiles set-default fast
```

- [ ] **Step 4: Update README**

P21 already added a README "Configuration Profiles" section with hand-edit examples and the persisted-vs-runtime explanation. P21b appends a "Managing profiles from the CLI" subsection:

````markdown
#### Managing profiles from the CLI

Once P21b ships, you no longer need to hand-edit `[profiles.<name>]` blocks. The same profile from the hand-edit example above can be created end-to-end with:

```bash
thoth config profiles add fast
thoth config profiles set fast general.default_mode thinking
thoth config profiles set-default fast    # persists general.default_profile = "fast"
thoth config profiles current             # shows fast (from general.default_profile)
thoth config profiles list                # lists all profiles, marks active
thoth config profiles show fast --json    # full profile contents
thoth config profiles unset fast general.default_mode  # remove a single key
thoth config profiles remove fast         # delete the entire profile
thoth config profiles unset-default       # clear the persisted pointer
```

`--profile` is honored only by `list`, `show`, and `current`. Mutator commands reject `--profile` because the profile they operate on is the positional argument.
````

- [ ] **Step 5: Update manual testing instructions**

Append to `manual_testing_instructions.md`:

```bash
thoth config profiles add fast
thoth config profiles set fast general.default_mode thinking
thoth config profiles set-default fast
thoth config get general.default_mode
THOTH_PROFILE=fast thoth config get general.default_mode
thoth config profiles current
thoth --profile fast config profiles current
thoth --profile missing config get general.default_mode
thoth config profiles set-default ghost      # expect ConfigProfileError
thoth --profile foo config profiles add bar  # expect 'no such option' error
thoth config profiles add interactive
thoth config profiles set interactive general.default_mode interactive
thoth config profiles show interactive
```

- [ ] **Step 6: Update P21b tracker**

In `PROJECTS.md`, mark planning deliverables present and check off tasks as code lands.

- [ ] **Step 7: Run documentation and targeted tests**

```bash
uv run pytest tests/test_config_profiles_cmd.py tests/test_config_profiles.py -v
git diff --check
```

Expected: tests pass and no whitespace errors.

- [ ] **Step 8: Commit Task 3**

```bash
git add src/thoth/help.py README.md manual_testing_instructions.md PROJECTS.md tests/test_config_profiles_cmd.py
git commit -m "docs: document config profile CLI commands"
```

---

## Final Verification

Run after all tasks land:

```bash
make env-check
just fix
just check
uv run pytest tests/test_config_profiles_cmd.py tests/test_config_profiles.py tests/test_config_cmd.py tests/test_json_envelopes.py tests/test_ci_lint_rules.py -v
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

---

## Execution Options

Plan complete and saved to `docs/superpowers/plans/2026-04-28-p21b-configuration-profiles-crud.md`. Two execution options:

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints.
