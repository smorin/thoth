# P12: CLI Mode Editing Implementation Plan

> ⚠️ **SUPERSEDED — DO NOT IMPLEMENT FROM THIS PLAN.**
>
> This plan was written 2026-04-30 (earlier in the day) and has been
> superseded by **[`projects/P12-cli-mode-editing.md`](../../../projects/P12-cli-mode-editing.md)**, which reflects the
> seven design decisions (D1–D8) and four ambiguity resolutions (Q1–Q4)
> made later that day during the project-refine and audit rounds.
>
> **Stale on five points** (this plan does NOT match the spec in
> `PROJECTS.md`):
>
> 1. Goal line lists `add / set / unset / rename / copy` — missing
>    `remove NAME` (D1, the parallel of `config profiles remove`).
> 2. Architecture says "four mode-aware helpers" — actually six are
>    needed: `ensure_mode`, `set_mode_value`, `unset_mode_value`,
>    `remove_mode`, `rename_mode`, `copy_mode`.
> 3. No mention of `--override` flag (Q2, overlay-only opt-in for
>    builtin-name shadowing).
> 4. No mention of `--from-profile X` flag for `copy` (Q3, enables the
>    four directions: base→base, base→overlay, overlay→base,
>    overlay→overlay).
> 5. No cross-cutting layering test (Q4, asserts overlay-tier writes
>    are visible to P21*'s overlay reader).
>
> Idempotency wording is also subtly out of date (the canonical rule
> is **model-only** — same NAME + same model = no-op; differing
> `--description` / `--provider` / `--kind` are ignored on re-add per
> Q1).
>
> **For implementation, follow [`projects/P12-cli-mode-editing.md`](../../../projects/P12-cli-mode-editing.md).** This file is
> retained only as a historical record of the day's iteration.

---

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `thoth modes add / set / unset / rename / copy` so users can author and edit research-mode definitions from the CLI instead of hand-editing TOML, with the same `--project` / `--config PATH` / `--profile <name>` targeting that `thoth config set` already supports.

**Architecture:** Mirror `config_cmd._op_set/_op_unset` exactly. Add four mode-aware helpers to `ConfigDocument` (parallel to its existing `ensure_profile/remove_profile/set_profile_value/unset_profile_value` quartet). Add `_op_add/_op_set/_op_unset/_op_rename/_op_copy` to `modes_cmd.py`, sharing one targeting-flag parser. Wire each op as a Click subcommand in `cli_subcommands/modes.py`. Help epilog updates land in `help.py`'s `_ModesGroup.format_epilog`.

**Tech Stack:** Python 3.11+, Click, tomlkit (round-trip preserves comments/formatting), pytest, `subprocess` for CLI integration tests, `ConfigWriteContext.resolve()` for write-target resolution.

---

## File Structure

| Action | Path | Responsibility |
|---|---|---|
| Modify | `src/thoth/config_document.py` | Add `ensure_mode`, `remove_mode`, `set_mode_value`, `unset_mode_value` (+ profile-scoped variants). Pure file mutation; no resolver logic. |
| Modify | `src/thoth/modes_cmd.py` | Add `_op_add/_op_set/_op_unset/_op_rename/_op_copy`, a shared `_parse_target_flags` helper, and dispatch entries. |
| Modify | `src/thoth/cli_subcommands/modes.py` | Register five new Click leaves: `add`, `set`, `unset`, `rename`, `copy`. Each uses `_PASSTHROUGH_CONTEXT` and forwards to `modes_command`. |
| Modify | `src/thoth/help.py` | Extend `_ModesGroup.format_epilog` (around line 161) with new ops + worked examples. |
| Create | `tests/test_modes_cmd.py` | Unit tests calling `modes_command` directly with `isolated_thoth_home`. Covers TS01–TS04, TS02b. |
| Create | `tests/test_modes_cli_integration.py` | Subprocess tests (`subprocess.run([sys.executable, "-m", "thoth", ...])`). Covers TS06. |
| Modify | `PROJECTS.md` | Flip P12 `[ ]` → `[~]` at start, then check off rows as each task lands, then `[~]` → `[x]` at finish. |

**Decomposition rationale:** `modes_cmd.py` (today: 379 lines, only `_op_list`) will roughly double. That's acceptable — the file's responsibility is single (`thoth modes` CLI). Don't preemptively split. `ConfigDocument` already has the same pattern for profiles; mode helpers mirror that.

---

## Pre-flight (do this before Task 1)

- [ ] **P0.1: Create a worktree for the work**

```bash
cd /Users/stevemorin/c/thoth
git worktree add /Users/stevemorin/c/thoth-worktrees/p12-modes-editing -b p12-modes-editing main
cd /Users/stevemorin/c/thoth-worktrees/p12-modes-editing
```

- [ ] **P0.2: Verify the gate is green before starting**

```bash
just check && uv run pytest -q && ./thoth_test -r --skip-interactive -q
```

Expected: all green. If anything is red, stop and fix on `main` first.

- [ ] **P0.3: Flip P12 to in-progress in PROJECTS.md**

Edit `PROJECTS.md` line 1240: change `## [ ] Project P12:` → `## [~] Project P12:`. Commit:

```bash
git add PROJECTS.md
git commit -m "chore(p12): start — flip [ ] to [~]"
```

---

## Task 1: ConfigDocument mode helpers

**Files:**
- Modify: `src/thoth/config_document.py` (insert after the existing `unset_default_profile_if` method, around line 84)
- Test: `tests/test_config_document.py` (append)

**Why this first:** `_op_*` in modes_cmd will call `set_mode_value` / `unset_mode_value` / `ensure_mode` / `remove_mode`. Build them bottom-up so each later task has clean primitives.

- [ ] **Step 1: Write the failing test for `set_mode_value`**

Append to `tests/test_config_document.py`:

```python
def test_set_mode_value_creates_top_level_modes_table(tmp_path: Path) -> None:
    path = tmp_path / "thoth.config.toml"
    doc = ConfigDocument.load(path)
    doc.set_mode_value("brief", "model", "gpt-4o-mini")
    doc.save()
    text = path.read_text()
    assert "[modes.brief]" in text
    assert 'model = "gpt-4o-mini"' in text


def test_set_mode_value_under_profile(tmp_path: Path) -> None:
    path = tmp_path / "thoth.config.toml"
    doc = ConfigDocument.load(path)
    doc.set_mode_value("brief", "model", "gpt-4o-mini", profile="dev")
    doc.save()
    text = path.read_text()
    assert "[profiles.dev.modes.brief]" in text
    assert 'model = "gpt-4o-mini"' in text


def test_unset_mode_value_prunes_empty_table(tmp_path: Path) -> None:
    path = tmp_path / "thoth.config.toml"
    path.write_text(
        'version = "2.0"\n[modes.brief]\nmodel = "gpt-4o-mini"\n'
    )
    doc = ConfigDocument.load(path)
    removed = doc.unset_mode_value("brief", "model")
    doc.save()
    assert removed is True
    assert "[modes.brief]" not in path.read_text()


def test_remove_mode_drops_entire_table(tmp_path: Path) -> None:
    path = tmp_path / "thoth.config.toml"
    path.write_text(
        'version = "2.0"\n[modes.brief]\nmodel = "gpt-4o-mini"\n'
    )
    doc = ConfigDocument.load(path)
    removed = doc.remove_mode("brief")
    doc.save()
    assert removed is True
    assert "[modes.brief]" not in path.read_text()


def test_remove_mode_returns_false_when_absent(tmp_path: Path) -> None:
    path = tmp_path / "thoth.config.toml"
    doc = ConfigDocument.load(path)
    assert doc.remove_mode("nope") is False


def test_remove_mode_under_profile(tmp_path: Path) -> None:
    path = tmp_path / "thoth.config.toml"
    path.write_text(
        'version = "2.0"\n[profiles.dev.modes.brief]\nmodel = "x"\n'
    )
    doc = ConfigDocument.load(path)
    assert doc.remove_mode("brief", profile="dev") is True
    assert "[profiles.dev.modes.brief]" not in path.read_text()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_config_document.py -k "mode" -v
```

Expected: FAIL with `AttributeError: 'ConfigDocument' object has no attribute 'set_mode_value'`.

- [ ] **Step 3: Add the four helpers to `ConfigDocument`**

Insert into `src/thoth/config_document.py` after line 83 (`unset_default_profile_if`):

```python
    def ensure_mode(self, name: str, *, profile: str | None = None) -> bool:
        segments = self._mode_segments(name, profile)
        if self._table_at(segments) is not None:
            return False
        self._ensure_table(segments)
        return True

    def remove_mode(self, name: str, *, profile: str | None = None) -> bool:
        parent_segments = self._mode_parent_segments(profile)
        parent = self._table_at(parent_segments)
        if parent is None or name not in parent:
            return False
        child = parent[name]
        if not hasattr(child, "keys"):
            return False
        del parent[name]
        # Prune empty `profiles.<name>.modes` and `profiles.<name>` if applicable.
        if profile is not None and len(parent) == 0:
            self._unset_segments(parent_segments, prune_empty=True)
        return True

    def set_mode_value(
        self, name: str, key: str, value: Any, *, profile: str | None = None
    ) -> None:
        segments = (*self._mode_segments(name, profile), *_parse_config_key(key))
        self._set_segments(segments, value)

    def unset_mode_value(
        self,
        name: str,
        key: str,
        *,
        profile: str | None = None,
        prune_empty: bool = True,
    ) -> bool:
        segments = (*self._mode_segments(name, profile), *_parse_config_key(key))
        return self._unset_segments(segments, prune_empty=prune_empty)

    @staticmethod
    def _mode_parent_segments(profile: str | None) -> tuple[str, ...]:
        if profile is None:
            return ("modes",)
        return ("profiles", profile, "modes")

    @staticmethod
    def _mode_segments(name: str, profile: str | None) -> tuple[str, ...]:
        return (*ConfigDocument._mode_parent_segments(profile), name)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_config_document.py -k "mode" -v
```

Expected: 6 PASS.

- [ ] **Step 5: Run full test_config_document.py to confirm no regression**

```bash
uv run pytest tests/test_config_document.py -v
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add src/thoth/config_document.py tests/test_config_document.py
git commit -m "feat(config-document): add mode helpers (ensure/remove/set/unset, profile-aware)"
```

---

## Task 2: Shared targeting-flag parser in `modes_cmd.py`

**Files:**
- Modify: `src/thoth/modes_cmd.py` (insert above `modes_command`)
- Test: `tests/test_modes_cmd.py` (create new file)

**Why this first among ops:** All five ops (`add`, `set`, `unset`, `rename`, `copy`) parse `--project`, `--config PATH`, `--profile NAME` identically. Single helper avoids drift.

- [ ] **Step 1: Create the failing test file**

Create `tests/test_modes_cmd.py`:

```python
"""Tests for `thoth modes` mutation ops (P12)."""

from __future__ import annotations

from pathlib import Path

import pytest

from thoth.modes_cmd import _parse_target_flags


def test_parse_target_flags_no_flags() -> None:
    project, config_path, profile, force_string, rest = _parse_target_flags(
        ["foo", "bar"]
    )
    assert project is False
    assert config_path is None
    assert profile is None
    assert force_string is False
    assert rest == ["foo", "bar"]


def test_parse_target_flags_extracts_all() -> None:
    project, config_path, profile, force_string, rest = _parse_target_flags(
        ["--project", "--profile", "dev", "--string", "name", "key", "val"]
    )
    assert project is True
    assert config_path is None
    assert profile == "dev"
    assert force_string is True
    assert rest == ["name", "key", "val"]


def test_parse_target_flags_config_path() -> None:
    project, config_path, profile, force_string, rest = _parse_target_flags(
        ["--config", "/tmp/x.toml", "name", "key", "val"]
    )
    assert project is False
    assert config_path == "/tmp/x.toml"
    assert rest == ["name", "key", "val"]


def test_parse_target_flags_missing_value_raises() -> None:
    with pytest.raises(ValueError, match="--config requires"):
        _parse_target_flags(["--config"])
    with pytest.raises(ValueError, match="--profile requires"):
        _parse_target_flags(["--profile"])
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_modes_cmd.py -v
```

Expected: FAIL with `ImportError: cannot import name '_parse_target_flags' from 'thoth.modes_cmd'`.

- [ ] **Step 3: Implement `_parse_target_flags`**

Add to `src/thoth/modes_cmd.py` (above `modes_command`, around line 366):

```python
def _parse_target_flags(
    args: list[str],
) -> tuple[bool, str | None, str | None, bool, list[str]]:
    """Extract --project / --config PATH / --profile NAME / --string from args.

    Returns: (project, config_path, profile, force_string, positional_rest).
    Raises ValueError on malformed flag usage (missing value).
    """
    project = False
    config_path: str | None = None
    profile: str | None = None
    force_string = False
    rest: list[str] = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--project":
            project = True
            i += 1
        elif a == "--string":
            force_string = True
            i += 1
        elif a == "--config":
            if i + 1 >= len(args):
                raise ValueError("--config requires a path")
            config_path = args[i + 1]
            i += 2
        elif a == "--profile":
            if i + 1 >= len(args):
                raise ValueError("--profile requires a name")
            profile = args[i + 1]
            i += 2
        else:
            rest.append(a)
            i += 1
    return project, config_path, profile, force_string, rest
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_modes_cmd.py -v
```

Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/thoth/modes_cmd.py tests/test_modes_cmd.py
git commit -m "feat(modes-cmd): add shared --project/--config/--profile/--string parser"
```

---

## Task 3: `thoth modes add`

**Files:**
- Modify: `src/thoth/modes_cmd.py` (add `_op_add`, register in dispatch)
- Test: `tests/test_modes_cmd.py` (append)

- [ ] **Step 1: Write failing tests for `_op_add`**

Append to `tests/test_modes_cmd.py`:

```python
from thoth.modes_cmd import modes_command
from thoth.paths import user_config_file


def test_add_writes_user_toml_default(isolated_thoth_home: Path) -> None:
    rc = modes_command(
        "add",
        ["my_brief", "--model", "gpt-4o-mini"],
    )
    assert rc == 0
    text = user_config_file().read_text()
    assert "[modes.my_brief]" in text
    assert 'model = "gpt-4o-mini"' in text
    assert 'provider = "openai"' in text  # default
    assert 'kind = "immediate"' in text  # default


def test_add_with_kind_background(isolated_thoth_home: Path) -> None:
    rc = modes_command(
        "add",
        ["bg", "--model", "o3-deep-research", "--kind", "background"],
    )
    assert rc == 0
    assert 'kind = "background"' in user_config_file().read_text()


def test_add_to_project_toml(
    isolated_thoth_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    rc = modes_command(
        "add",
        ["team_review", "--model", "o1-preview", "--project"],
    )
    assert rc == 0
    project_toml = tmp_path / "thoth.config.toml"
    assert project_toml.exists()
    assert "[modes.team_review]" in project_toml.read_text()


def test_add_under_profile(isolated_thoth_home: Path) -> None:
    rc = modes_command(
        "add",
        ["cheap", "--model", "gpt-4o-mini", "--profile", "dev"],
    )
    assert rc == 0
    text = user_config_file().read_text()
    assert "[profiles.dev.modes.cheap]" in text


def test_add_to_explicit_config_path(
    isolated_thoth_home: Path, tmp_path: Path
) -> None:
    target = tmp_path / "scratch.toml"
    rc = modes_command(
        "add",
        ["scratch_mode", "--model", "gpt-4o-mini", "--config", str(target)],
    )
    assert rc == 0
    assert "[modes.scratch_mode]" in target.read_text()


def test_add_rejects_config_and_project_together(
    isolated_thoth_home: Path, tmp_path: Path
) -> None:
    rc = modes_command(
        "add",
        [
            "x",
            "--model",
            "gpt-4o-mini",
            "--project",
            "--config",
            str(tmp_path / "f.toml"),
        ],
    )
    assert rc == 2


def test_add_refuses_existing_mode(isolated_thoth_home: Path) -> None:
    modes_command("add", ["dup", "--model", "gpt-4o-mini"])
    rc = modes_command("add", ["dup", "--model", "gpt-4o"])
    assert rc == 2  # already exists
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_modes_cmd.py -k "add" -v
```

Expected: FAIL with "unknown modes op: add".

- [ ] **Step 3: Implement `_op_add`**

Add to `src/thoth/modes_cmd.py` (near `_op_list`):

```python
from thoth._secrets import _is_secret_key  # if not already imported
from thoth.config_cmd import _parse_value  # reuse the same coercion
from thoth.config_write_context import ConfigTargetConflictError, ConfigWriteContext
from thoth.config import BUILTIN_MODES


def _op_add(args: list[str], *, config_path: str | None = None) -> int:
    try:
        project, op_config_path, profile, _force_string, rest = _parse_target_flags(args)
    except ValueError as exc:
        _get_console().print(f"[red]Error:[/red] {exc}")
        return 2

    # Parse: NAME [--model M] [--provider P] [--description D] [--kind K]
    name: str | None = None
    model: str | None = None
    provider: str | None = None
    description: str | None = None
    kind: str | None = None
    i = 0
    while i < len(rest):
        a = rest[i]
        if a == "--model":
            model = rest[i + 1] if i + 1 < len(rest) else None
            i += 2
        elif a == "--provider":
            provider = rest[i + 1] if i + 1 < len(rest) else None
            i += 2
        elif a == "--description":
            description = rest[i + 1] if i + 1 < len(rest) else None
            i += 2
        elif a == "--kind":
            kind = rest[i + 1] if i + 1 < len(rest) else None
            i += 2
        elif name is None:
            name = a
            i += 1
        else:
            _get_console().print(f"[red]Error:[/red] unexpected arg: {a}")
            return 2

    if not name or not model:
        _get_console().print("[red]Error:[/red] modes add takes NAME --model M [--provider P] [--description D] [--kind immediate|background]")
        return 2
    if kind is not None and kind not in ("immediate", "background"):
        _get_console().print("[red]Error:[/red] --kind must be 'immediate' or 'background'")
        return 2

    target_path_arg = op_config_path if op_config_path is not None else config_path
    try:
        context = ConfigWriteContext.resolve(project=project, config_path=target_path_arg)
    except ConfigTargetConflictError as exc:
        _get_console().print(f"[red]Error:[/red] {exc}")
        return 2

    doc = context.load_document()
    if doc.ensure_mode(name, profile=profile) is False:
        # Already exists. Refuse — user should `set` existing.
        _get_console().print(f"[red]Error:[/red] mode '{name}' already exists at {context.target_path}")
        return 2
    doc.set_mode_value(name, "model", model, profile=profile)
    doc.set_mode_value(name, "provider", provider or "openai", profile=profile)
    doc.set_mode_value(name, "kind", kind or "immediate", profile=profile)
    if description is not None:
        doc.set_mode_value(name, "description", description, profile=profile)
    doc.save()

    scope = f"profile '{profile}'" if profile else ("project" if project else "user")
    _get_console().print(
        f"Added mode '{name}' under {scope} (kind={kind or 'immediate'}, model={model})"
    )
    return 0
```

Then update the `modes_command` dispatch table:

```python
def modes_command(op: str | None, args: list[str], *, config_path: str | None = None) -> int:
    if op is None:
        return _op_list(args, config_path=config_path)
    ops = {"list": _op_list, "add": _op_add}
    if op not in ops:
        _get_console().print(f"[red]Error:[/red] unknown modes op: {op}")
        return 2
    return ops[op](args, config_path=config_path)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_modes_cmd.py -k "add" -v
```

Expected: 7 PASS.

- [ ] **Step 5: Run full modes_cmd tests to confirm no regression**

```bash
uv run pytest tests/test_modes_cmd.py -v
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add src/thoth/modes_cmd.py tests/test_modes_cmd.py
git commit -m "feat(modes-cmd): add 'thoth modes add' with --project/--config/--profile targeting"
```

---

## Task 4: `thoth modes set`

**Files:**
- Modify: `src/thoth/modes_cmd.py` (add `_op_set`, register in dispatch)
- Test: `tests/test_modes_cmd.py` (append)

- [ ] **Step 1: Write failing tests**

Append to `tests/test_modes_cmd.py`:

```python
def test_set_updates_existing_user_mode(isolated_thoth_home: Path) -> None:
    modes_command("add", ["my_brief", "--model", "gpt-4o-mini"])
    rc = modes_command("set", ["my_brief", "temperature", "0.2"])
    assert rc == 0
    text = user_config_file().read_text()
    assert "temperature = 0.2" in text


def test_set_creates_override_for_builtin(isolated_thoth_home: Path) -> None:
    # 'default' is a builtin. Setting a key on it implicitly creates an
    # overriding [modes.default] table in user TOML.
    rc = modes_command("set", ["default", "model", "gpt-4o"])
    assert rc == 0
    text = user_config_file().read_text()
    assert "[modes.default]" in text
    assert 'model = "gpt-4o"' in text


def test_set_string_flag_keeps_secret_unparsed(isolated_thoth_home: Path) -> None:
    # Without --string the value '1234' would coerce to int.
    rc = modes_command("set", ["my_brief", "label", "1234", "--string"])
    # Need to add my_brief first so the [modes.my_brief] table exists; but
    # set should also implicitly create it for user-side keys per existing
    # config_cmd._op_set behavior. Both forms are tested for parity.
    assert rc == 0
    text = user_config_file().read_text()
    assert 'label = "1234"' in text


def test_set_under_profile(isolated_thoth_home: Path) -> None:
    modes_command("add", ["cheap", "--model", "gpt-4o-mini", "--profile", "dev"])
    rc = modes_command("set", ["cheap", "temperature", "0.5", "--profile", "dev"])
    assert rc == 0
    text = user_config_file().read_text()
    assert "[profiles.dev.modes.cheap]" in text
    assert "temperature = 0.5" in text


def test_set_rejects_config_and_project(
    isolated_thoth_home: Path, tmp_path: Path
) -> None:
    rc = modes_command(
        "set",
        ["x", "k", "v", "--project", "--config", str(tmp_path / "f.toml")],
    )
    assert rc == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_modes_cmd.py -k "set" -v
```

Expected: FAIL with "unknown modes op: set".

- [ ] **Step 3: Implement `_op_set`**

Add to `src/thoth/modes_cmd.py`:

```python
def _op_set(args: list[str], *, config_path: str | None = None) -> int:
    try:
        project, op_config_path, profile, force_string, rest = _parse_target_flags(args)
    except ValueError as exc:
        _get_console().print(f"[red]Error:[/red] {exc}")
        return 2

    if len(rest) != 3:
        _get_console().print("[red]Error:[/red] modes set takes NAME KEY VALUE")
        return 2
    name, key, raw_value = rest
    value = _parse_value(raw_value, force_string)

    target_path_arg = op_config_path if op_config_path is not None else config_path
    try:
        context = ConfigWriteContext.resolve(project=project, config_path=target_path_arg)
    except ConfigTargetConflictError as exc:
        _get_console().print(f"[red]Error:[/red] {exc}")
        return 2

    doc = context.load_document()
    doc.set_mode_value(name, key, value, profile=profile)
    doc.save()
    _get_console().print(f"Updated {name}.{key} = {raw_value}")
    return 0
```

Update dispatch:

```python
    ops = {"list": _op_list, "add": _op_add, "set": _op_set}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_modes_cmd.py -k "set" -v
```

Expected: 5 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/thoth/modes_cmd.py tests/test_modes_cmd.py
git commit -m "feat(modes-cmd): add 'thoth modes set' with type coercion + --string + targeting"
```

---

## Task 5: `thoth modes unset`

**Files:**
- Modify: `src/thoth/modes_cmd.py` (add `_op_unset`, register in dispatch)
- Test: `tests/test_modes_cmd.py` (append)

- [ ] **Step 1: Write failing tests**

Append to `tests/test_modes_cmd.py`:

```python
def test_unset_single_key_prunes_empty_table(isolated_thoth_home: Path) -> None:
    modes_command("add", ["my_brief", "--model", "gpt-4o-mini"])
    modes_command("set", ["my_brief", "temperature", "0.2"])
    # Unset every key one at a time — table should disappear after the last.
    modes_command("unset", ["my_brief", "temperature"])
    modes_command("unset", ["my_brief", "kind"])
    modes_command("unset", ["my_brief", "provider"])
    rc = modes_command("unset", ["my_brief", "model"])
    assert rc == 0
    assert "[modes.my_brief]" not in user_config_file().read_text()


def test_unset_no_key_removes_entire_user_table(
    isolated_thoth_home: Path,
) -> None:
    modes_command("add", ["my_brief", "--model", "gpt-4o-mini"])
    rc = modes_command("unset", ["my_brief"])
    assert rc == 0
    assert "[modes.my_brief]" not in user_config_file().read_text()


def test_unset_no_key_drops_user_override_of_builtin(
    isolated_thoth_home: Path,
) -> None:
    modes_command("set", ["default", "model", "gpt-4o"])  # creates override
    rc = modes_command("unset", ["default"])
    assert rc == 0
    text = user_config_file().read_text()
    assert "[modes.default]" not in text


def test_unset_under_profile(isolated_thoth_home: Path) -> None:
    modes_command("add", ["cheap", "--model", "gpt-4o-mini", "--profile", "dev"])
    rc = modes_command("unset", ["cheap", "--profile", "dev"])
    assert rc == 0
    text = user_config_file().read_text()
    assert "[profiles.dev.modes.cheap]" not in text


def test_unset_missing_returns_zero_with_note(
    isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = modes_command("unset", ["never_existed"])
    err = capsys.readouterr().err
    assert rc == 0
    assert "not found" in err.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_modes_cmd.py -k "unset" -v
```

Expected: FAIL with "unknown modes op: unset".

- [ ] **Step 3: Implement `_op_unset`**

Add to `src/thoth/modes_cmd.py`:

```python
import sys


def _op_unset(args: list[str], *, config_path: str | None = None) -> int:
    try:
        project, op_config_path, profile, _force_string, rest = _parse_target_flags(args)
    except ValueError as exc:
        _get_console().print(f"[red]Error:[/red] {exc}")
        return 2

    if not 1 <= len(rest) <= 2:
        _get_console().print("[red]Error:[/red] modes unset takes NAME [KEY]")
        return 2
    name = rest[0]
    key = rest[1] if len(rest) == 2 else None

    target_path_arg = op_config_path if op_config_path is not None else config_path
    try:
        context = ConfigWriteContext.resolve(project=project, config_path=target_path_arg)
    except ConfigTargetConflictError as exc:
        _get_console().print(f"[red]Error:[/red] {exc}")
        return 2

    if not context.target_path.exists():
        print(f"note: {context.target_path} does not exist; nothing to unset", file=sys.stderr)
        return 0

    doc = context.load_document()
    if key is None:
        removed = doc.remove_mode(name, profile=profile)
    else:
        removed = doc.unset_mode_value(name, key, profile=profile)
    if not removed:
        print(f"note: not found: {name}{('.' + key) if key else ''}", file=sys.stderr)
        return 0
    doc.save()
    _get_console().print(
        f"Removed {name}" + (f".{key}" if key else "")
    )
    return 0
```

Update dispatch:

```python
    ops = {"list": _op_list, "add": _op_add, "set": _op_set, "unset": _op_unset}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_modes_cmd.py -k "unset" -v
```

Expected: 5 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/thoth/modes_cmd.py tests/test_modes_cmd.py
git commit -m "feat(modes-cmd): add 'thoth modes unset' with empty-table pruning + targeting"
```

---

## Task 6: `thoth modes copy`

**Files:**
- Modify: `src/thoth/modes_cmd.py` (add `_op_copy`, register in dispatch)
- Test: `tests/test_modes_cmd.py` (append)

**Why copy before rename:** Copy is the higher-value op (fork builtin into custom). Rename is cheaper to add after copy is in place.

- [ ] **Step 1: Write failing tests**

Append to `tests/test_modes_cmd.py`:

```python
def test_copy_builtin_to_user_mode(isolated_thoth_home: Path) -> None:
    rc = modes_command("copy", ["deep_research", "custom_research"])
    assert rc == 0
    text = user_config_file().read_text()
    assert "[modes.custom_research]" in text
    # copied keys from builtin
    assert 'provider = "openai"' in text
    assert 'kind = "background"' in text


def test_copy_user_mode_to_user_mode(isolated_thoth_home: Path) -> None:
    modes_command("add", ["src", "--model", "gpt-4o-mini", "--description", "src"])
    rc = modes_command("copy", ["src", "dst"])
    assert rc == 0
    text = user_config_file().read_text()
    assert "[modes.dst]" in text
    assert 'description = "src"' in text


def test_copy_refuses_when_dst_exists(isolated_thoth_home: Path) -> None:
    modes_command("add", ["a", "--model", "gpt-4o-mini"])
    modes_command("add", ["b", "--model", "gpt-4o-mini"])
    rc = modes_command("copy", ["a", "b"])
    assert rc == 2


def test_copy_under_profile(isolated_thoth_home: Path) -> None:
    rc = modes_command(
        "copy", ["deep_research", "custom_dr", "--profile", "dev"]
    )
    assert rc == 0
    text = user_config_file().read_text()
    assert "[profiles.dev.modes.custom_dr]" in text
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_modes_cmd.py -k "copy" -v
```

Expected: FAIL with "unknown modes op: copy".

- [ ] **Step 3: Implement `_op_copy`**

Add to `src/thoth/modes_cmd.py`:

```python
def _op_copy(args: list[str], *, config_path: str | None = None) -> int:
    try:
        project, op_config_path, profile, _force_string, rest = _parse_target_flags(args)
    except ValueError as exc:
        _get_console().print(f"[red]Error:[/red] {exc}")
        return 2

    if len(rest) != 2:
        _get_console().print("[red]Error:[/red] modes copy takes SRC DST")
        return 2
    src, dst = rest

    target_path_arg = op_config_path if op_config_path is not None else config_path
    try:
        context = ConfigWriteContext.resolve(project=project, config_path=target_path_arg)
    except ConfigTargetConflictError as exc:
        _get_console().print(f"[red]Error:[/red] {exc}")
        return 2

    # Resolve src from current effective view (builtin or user/project/profile).
    cm = ConfigManager(Path(target_path_arg).expanduser().resolve() if target_path_arg else None)
    cli_args: dict[str, Any] = {}
    if profile:
        cli_args["_profile"] = profile
    cm.load_all_layers(cli_args)
    src_data: dict[str, Any] = {}
    builtin = BUILTIN_MODES.get(src)
    if builtin and "_deprecated_alias_for" not in builtin:
        src_data.update(builtin)
    user_modes = (cm.layers.get("user") or {}).get("modes") or {}
    if src in user_modes:
        src_data.update(user_modes[src])
    if not src_data:
        _get_console().print(f"[red]Error:[/red] source mode not found: {src}")
        return 2

    doc = context.load_document()
    if doc.ensure_mode(dst, profile=profile) is False:
        _get_console().print(f"[red]Error:[/red] destination mode '{dst}' already exists")
        return 2
    for key, value in src_data.items():
        doc.set_mode_value(dst, key, value, profile=profile)
    doc.save()
    _get_console().print(f"Copied '{src}' to '{dst}'")
    return 0
```

Update dispatch:

```python
    ops = {
        "list": _op_list,
        "add": _op_add,
        "set": _op_set,
        "unset": _op_unset,
        "copy": _op_copy,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_modes_cmd.py -k "copy" -v
```

Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/thoth/modes_cmd.py tests/test_modes_cmd.py
git commit -m "feat(modes-cmd): add 'thoth modes copy' (builtin or user → user/profile)"
```

---

## Task 7: `thoth modes rename`

**Files:**
- Modify: `src/thoth/modes_cmd.py` (add `_op_rename`, register in dispatch)
- Test: `tests/test_modes_cmd.py` (append)

- [ ] **Step 1: Write failing tests**

Append to `tests/test_modes_cmd.py`:

```python
def test_rename_user_mode(isolated_thoth_home: Path) -> None:
    modes_command("add", ["old", "--model", "gpt-4o-mini"])
    rc = modes_command("rename", ["old", "new"])
    assert rc == 0
    text = user_config_file().read_text()
    assert "[modes.new]" in text
    assert "[modes.old]" not in text


def test_rename_refuses_builtin(isolated_thoth_home: Path) -> None:
    rc = modes_command("rename", ["default", "renamed_default"])
    assert rc == 2


def test_rename_refuses_when_src_missing(isolated_thoth_home: Path) -> None:
    rc = modes_command("rename", ["nope", "neu"])
    assert rc == 2


def test_rename_refuses_when_dst_exists(isolated_thoth_home: Path) -> None:
    modes_command("add", ["a", "--model", "gpt-4o-mini"])
    modes_command("add", ["b", "--model", "gpt-4o-mini"])
    rc = modes_command("rename", ["a", "b"])
    assert rc == 2


def test_rename_under_profile(isolated_thoth_home: Path) -> None:
    modes_command("add", ["a", "--model", "gpt-4o-mini", "--profile", "dev"])
    rc = modes_command("rename", ["a", "b", "--profile", "dev"])
    assert rc == 0
    text = user_config_file().read_text()
    assert "[profiles.dev.modes.b]" in text
    assert "[profiles.dev.modes.a]" not in text
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_modes_cmd.py -k "rename" -v
```

Expected: FAIL with "unknown modes op: rename".

- [ ] **Step 3: Implement `_op_rename`**

Add to `src/thoth/modes_cmd.py`:

```python
def _op_rename(args: list[str], *, config_path: str | None = None) -> int:
    try:
        project, op_config_path, profile, _force_string, rest = _parse_target_flags(args)
    except ValueError as exc:
        _get_console().print(f"[red]Error:[/red] {exc}")
        return 2

    if len(rest) != 2:
        _get_console().print("[red]Error:[/red] modes rename takes OLD NEW")
        return 2
    old, new = rest

    if old in BUILTIN_MODES and "_deprecated_alias_for" not in BUILTIN_MODES[old]:
        _get_console().print(f"[red]Error:[/red] cannot rename builtin mode '{old}' (use copy instead)")
        return 2

    target_path_arg = op_config_path if op_config_path is not None else config_path
    try:
        context = ConfigWriteContext.resolve(project=project, config_path=target_path_arg)
    except ConfigTargetConflictError as exc:
        _get_console().print(f"[red]Error:[/red] {exc}")
        return 2

    doc = context.load_document()
    parent = doc._table_at(("profiles", profile, "modes") if profile else ("modes",))
    if parent is None or old not in parent:
        _get_console().print(f"[red]Error:[/red] source mode not found: {old}")
        return 2
    if new in parent:
        _get_console().print(f"[red]Error:[/red] destination mode '{new}' already exists")
        return 2

    src_table = parent[old]
    src_data = {k: src_table[k] for k in src_table.keys()}
    doc.ensure_mode(new, profile=profile)
    for key, value in src_data.items():
        doc.set_mode_value(new, key, value, profile=profile)
    doc.remove_mode(old, profile=profile)
    doc.save()
    _get_console().print(f"Renamed '{old}' to '{new}'")
    return 0
```

Update dispatch:

```python
    ops = {
        "list": _op_list,
        "add": _op_add,
        "set": _op_set,
        "unset": _op_unset,
        "copy": _op_copy,
        "rename": _op_rename,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_modes_cmd.py -k "rename" -v
```

Expected: 5 PASS.

- [ ] **Step 5: Run full modes_cmd tests**

```bash
uv run pytest tests/test_modes_cmd.py -v
```

Expected: all PASS (Tasks 2–7's tests, ~30 cases).

- [ ] **Step 6: Commit**

```bash
git add src/thoth/modes_cmd.py tests/test_modes_cmd.py
git commit -m "feat(modes-cmd): add 'thoth modes rename' (user-modes only)"
```

---

## Task 8: Click subcommand wiring

**Files:**
- Modify: `src/thoth/cli_subcommands/modes.py` (add 5 leaves)
- Test: `tests/test_modes_cli_integration.py` (create)

- [ ] **Step 1: Create the failing subprocess integration test file**

Create `tests/test_modes_cli_integration.py`:

```python
"""Subprocess integration tests for `thoth modes` add/set/unset/rename/copy."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


def _thoth(*args: str, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "thoth", "modes", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
        env=env,
        timeout=15,
    )


@pytest.fixture
def cli_env(
    isolated_thoth_home: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, str]:
    import os
    env = dict(os.environ)
    env["XDG_CONFIG_HOME"] = str(isolated_thoth_home / "config")
    return env


def test_cli_add_creates_user_toml(
    isolated_thoth_home: Path, tmp_path: Path, cli_env: dict[str, str]
) -> None:
    res = _thoth("add", "x", "--model", "gpt-4o-mini", cwd=tmp_path, env=cli_env)
    assert res.returncode == 0, res.stderr
    user_toml = isolated_thoth_home / "config" / "thoth" / "thoth.config.toml"
    assert user_toml.exists()
    assert "[modes.x]" in user_toml.read_text()


def test_cli_add_project(
    isolated_thoth_home: Path, tmp_path: Path, cli_env: dict[str, str]
) -> None:
    res = _thoth(
        "add", "team", "--model", "o1-preview", "--project",
        cwd=tmp_path, env=cli_env,
    )
    assert res.returncode == 0, res.stderr
    project_toml = tmp_path / "thoth.config.toml"
    assert project_toml.exists()
    assert "[modes.team]" in project_toml.read_text()


def test_cli_add_config_path(
    isolated_thoth_home: Path, tmp_path: Path, cli_env: dict[str, str]
) -> None:
    target = tmp_path / "scratch.toml"
    res = _thoth(
        "add", "s", "--model", "gpt-4o-mini", "--config", str(target),
        cwd=tmp_path, env=cli_env,
    )
    assert res.returncode == 0, res.stderr
    assert "[modes.s]" in target.read_text()


def test_cli_set_then_unset_round_trip(
    isolated_thoth_home: Path, tmp_path: Path, cli_env: dict[str, str]
) -> None:
    _thoth("add", "rt", "--model", "gpt-4o-mini", cwd=tmp_path, env=cli_env)
    _thoth("set", "rt", "temperature", "0.2", cwd=tmp_path, env=cli_env)
    _thoth("unset", "rt", cwd=tmp_path, env=cli_env)
    user_toml = isolated_thoth_home / "config" / "thoth" / "thoth.config.toml"
    assert "[modes.rt]" not in user_toml.read_text()


def test_cli_copy_then_rename(
    isolated_thoth_home: Path, tmp_path: Path, cli_env: dict[str, str]
) -> None:
    _thoth("copy", "deep_research", "fork", cwd=tmp_path, env=cli_env)
    _thoth("rename", "fork", "fork2", cwd=tmp_path, env=cli_env)
    user_toml = isolated_thoth_home / "config" / "thoth" / "thoth.config.toml"
    text = user_toml.read_text()
    assert "[modes.fork2]" in text
    assert "[modes.fork]" not in text


def test_cli_add_under_profile(
    isolated_thoth_home: Path, tmp_path: Path, cli_env: dict[str, str]
) -> None:
    res = _thoth(
        "add", "cheap", "--model", "gpt-4o-mini", "--profile", "dev",
        cwd=tmp_path, env=cli_env,
    )
    assert res.returncode == 0, res.stderr
    user_toml = isolated_thoth_home / "config" / "thoth" / "thoth.config.toml"
    assert "[profiles.dev.modes.cheap]" in user_toml.read_text()
```

- [ ] **Step 2: Run subprocess tests to verify they fail**

```bash
uv run pytest tests/test_modes_cli_integration.py -v
```

Expected: FAIL with `Usage: thoth modes [OPTIONS] COMMAND [ARGS]... Error: No such command 'add'`.

- [ ] **Step 3: Register the five Click leaves**

In `src/thoth/cli_subcommands/modes.py`, replace the trailing comment `# Future: P12 adds 'add', 'set', 'unset' leaves here.` (line 148) with:

```python
def _make_mutator_leaf(op_name: str, takes_kwargs: bool = False):
    @modes.command(name=op_name, context_settings=_PASSTHROUGH_CONTEXT)
    @click.argument("args", nargs=-1, type=click.UNPROCESSED)
    @click.pass_context
    def _leaf(ctx: click.Context, args: tuple[str, ...]) -> None:
        validate_inherited_options(ctx, f"modes {op_name}", DEFAULT_HONOR)
        config_path = inherited_value(ctx, "config_path")
        from thoth.modes_cmd import modes_command
        rc = modes_command(op_name, list(args), config_path=config_path)
        sys.exit(rc)
    return _leaf


for _op in ("add", "set", "unset", "rename", "copy"):
    _make_mutator_leaf(_op)
```

- [ ] **Step 4: Run subprocess tests to verify they pass**

```bash
uv run pytest tests/test_modes_cli_integration.py -v
```

Expected: 6 PASS.

- [ ] **Step 5: Run full modes test surface**

```bash
uv run pytest tests/test_modes_cmd.py tests/test_modes_cli_integration.py -v
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add src/thoth/cli_subcommands/modes.py tests/test_modes_cli_integration.py
git commit -m "feat(modes-cli): wire add/set/unset/rename/copy click leaves through to modes_command"
```

---

## Task 9: Help epilog refresh

**Files:**
- Modify: `src/thoth/help.py` (around line 161, `_ModesGroup.format_epilog`)

- [ ] **Step 1: Read the current epilog block**

```bash
sed -n '160,200p' src/thoth/help.py
```

Note exact text so the replacement is precise.

- [ ] **Step 2: Replace the epilog with the new content**

In `src/thoth/help.py`, locate the `format_epilog` block of `_ModesGroup` (line ~161). Replace its body with:

```python
def format_epilog(self, ctx: click.Context, formatter):
    """Render the modes-positional epilog block + worked examples."""
    formatter.write_paragraph()
    with formatter.section("Examples"):
        formatter.write_text("List modes:")
        formatter.write_text("  thoth modes")
        formatter.write_text("  thoth modes list --json")
        formatter.write_paragraph()
        formatter.write_text("Edit modes (P12):")
        formatter.write_text("  thoth modes add my_brief --model gpt-4o-mini --description \"terse brief\"")
        formatter.write_text("  thoth modes set my_brief temperature 0.2")
        formatter.write_text("  thoth modes copy deep_research custom_research")
        formatter.write_text("  thoth modes rename my_brief brief")
        formatter.write_text("  thoth modes unset my_brief")
        formatter.write_paragraph()
        formatter.write_text("Targeting (mirrors `thoth config set`):")
        formatter.write_text("  --project           write to ./thoth.config.toml")
        formatter.write_text("  --config PATH       write to PATH")
        formatter.write_text("  --profile NAME      write to [profiles.NAME.modes.<mode>]")
        formatter.write_paragraph()
        formatter.write_text("Run `thoth modes` for provider, model, and kind per mode.")
```

- [ ] **Step 3: Smoke-test the help output**

```bash
uv run python -m thoth modes --help
```

Expected: the new "Edit modes (P12)" and "Targeting" blocks appear in the epilog.

- [ ] **Step 4: Confirm no test regression**

```bash
uv run pytest tests/ -q
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/thoth/help.py
git commit -m "docs(help): document modes add/set/unset/rename/copy + targeting flags"
```

---

## Task 10: Full-gate run + flip P12 to done

**Files:**
- Modify: `PROJECTS.md`

- [ ] **Step 1: Run the full lefthook-equivalent gate**

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run ty check src/
uv run pytest -q
./thoth_test -r --skip-interactive -q
```

Expected: every command exits 0. If any fail, fix and re-run before proceeding.

- [ ] **Step 2: Edit `PROJECTS.md` to flip P12**

In `PROJECTS.md`, find the P12 block (around line 1240). Apply these edits:

1. Header: `## [~] Project P12:` → `## [x] Project P12:`
2. Each `- [ ] [P12-T0X]` and `- [ ] [P12-TS0X]` row → `- [x] [...]` with the ID preserved.
3. The trailing `- [ ] Regression Test Status` → `- [x] Regression Test Status`.

Leave the two `[>] [P12-T05]` and `[>] [P12-TS05]` rows untouched.

- [ ] **Step 3: Commit the closeout**

```bash
git add PROJECTS.md
git commit -m "chore(p12): close P12 — mode editing CLI shipped, flip to [x]"
```

- [ ] **Step 4: Push the worktree branch and open a PR**

```bash
git push -u origin p12-modes-editing
gh pr create --title "feat: P12 — thoth modes add/set/unset/rename/copy with --project/--config/--profile" \
  --body "$(cat <<'EOF'
## Summary
- Implements P12: CLI mode editing (add/set/unset/rename/copy)
- Targeting flags mirror `thoth config set`: `--project`, `--config PATH`, `--profile NAME`
- Profile-scoped writes land at `[profiles.<name>.modes.<mode>]`
- `_secrets.py` extraction was already done under P13 (P12-T05/TS05 marked `[>]`)

## Test plan
- [x] Unit tests in `tests/test_modes_cmd.py`
- [x] Subprocess integration tests in `tests/test_modes_cli_integration.py`
- [x] `tests/test_config_document.py` covers the new mode helpers
- [x] Full gate: `just check`, `uv run pytest -q`, `./thoth_test -r --skip-interactive -q`
- [x] Help epilog updated; smoke-tested via `thoth modes --help`
EOF
)"
```

---

## Self-Review (run after writing the plan)

**Spec coverage check** — every P12 row from PROJECTS.md mapped to a task:

| P12 row | Covered by |
|---|---|
| TS01 (add user TOML default + kind=immediate default) | Task 3, Step 1 |
| T01 (`_op_add`) | Task 3, Step 3 |
| TS02 (set user mode + builtin override + --project + --config + mutex) | Task 4 (set), Task 3 (--config + mutex coverage shared) |
| T02 (`_op_set` with `--string` + `--project` + `--config`) | Task 4, Step 3 |
| TS02b (`--profile` writes) | Task 3 (add --profile), Task 4 (set --profile) |
| T02b (plumb `--profile` through ops) | Tasks 3, 4, 5 (each op accepts profile via `_parse_target_flags`) |
| TS03 (unset single key, no-key, refuse builtin, drop override, --profile) | Task 5, Step 1 |
| T03 (`_op_unset` with pruning + profile) | Task 5, Step 3 |
| TS04 (rename + copy targeting) | Tasks 6, 7 |
| T04 (`_op_rename`, `_op_copy`) | Tasks 6, 7 |
| TS05 / T05 (secrets extraction) | Already done — `[>]` markers preserved, no work needed |
| TS06 (subprocess CLI tests) | Task 8 |
| T06 (wire ops into dispatch) | Tasks 3–7 (each updates the `ops` dict) |
| T07 (help epilog) | Task 9 |
| TS07 (full regression green) | Task 10, Step 1 |

**Type-consistency check** — function names used in later tasks against earlier definitions:

- `_parse_target_flags` returns `(project, config_path, profile, force_string, rest)` — all five ops in Tasks 3–7 unpack this shape consistently.
- `ConfigDocument.set_mode_value(name, key, value, *, profile=None)` — Tasks 3, 4, 6, 7 call with `profile=profile` keyword argument; signature matches.
- `ConfigDocument.remove_mode(name, *, profile=None)` — Tasks 5, 7 call as `remove_mode(name, profile=profile)`; signature matches.
- `ConfigDocument.unset_mode_value(name, key, *, profile=None, prune_empty=True)` — Task 5 relies on default `prune_empty=True`; consistent.
- `ConfigDocument.ensure_mode(name, *, profile=None) -> bool` — Tasks 3, 6, 7 check the False-return for "already exists"; signature matches.
- `ConfigWriteContext.resolve(project=..., config_path=...)` — already in code; raises `ConfigTargetConflictError` on `--project` + `--config`; Tasks 3–7 catch and convert to exit 2.

**Placeholder scan** — no "TODO", "TBD", "implement later", or "similar to Task N" detected.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-04-30-p12-cli-mode-editing.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
