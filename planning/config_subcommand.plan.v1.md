# `thoth config` Subcommand + XDG Layout — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `thoth config` subcommand (get/set/unset/list/path/edit/help) and migrate all user-writable paths to XDG Base Directory Spec. No legacy-path migration.

**Architecture:** New `src/thoth/paths.py` centralizes XDG path resolution; every `platformdirs.user_config_dir("thoth")` callsite switches to the new helpers. New `src/thoth/config_cmd.py` owns the CLI surface for the `config` subcommand, dispatched from `cli.py` the same way as `init`/`status`/`list`. `tomllib` stays the reader; `tomlkit` is used for writes to preserve user comments.

**Tech Stack:** Python 3.11+, click, tomllib (stdlib), tomlkit (new), rich, pytest + pytest-xdist, ruff, ty.

**Spec:** `planning/config_subcommand.v1.md`

---

## File Structure

**New files:**
- `src/thoth/paths.py` — XDG path helpers (pure functions, no side effects)
- `src/thoth/config_cmd.py` — `config_command(op, rest, ...)` dispatcher + per-op functions
- `tests/test_paths.py`
- `tests/test_config_cmd.py`

**Modified files:**
- `src/thoth/config.py` — swap `platformdirs` import for `thoth.paths`; update `get_defaults()["paths"]["checkpoint_dir"]` and `ConfigManager.__init__`
- `src/thoth/models.py` — swap `ModelCache` default dir to `paths.user_cache_dir() / "model_cache"`
- `src/thoth/commands.py` — swap `init_command` default config path; register `config` in `CommandHandler.commands`
- `src/thoth/cli.py` — dispatch `"config"` in subcommand chain + help intercept
- `src/thoth/help.py` — `show_config_help()`, extend `build_epilog()`, extend `show_general_help()`
- `tests/conftest.py` — extend `isolated_thoth_home` to also set `XDG_STATE_HOME` + `XDG_CACHE_HOME`; update `checkpoint_dir` fixture to use new state path
- `pyproject.toml` — add `tomlkit>=0.13`; drop `platformdirs` once last callsite is migrated

---

## Conventions (apply to every task)

- Commits follow Conventional Commits: `feat(config): ...`, `refactor(paths): ...`, `test(paths): ...`, `chore(deps): ...`.
- Never include `Co-Authored-By: Claude` or `🤖 Generated with` lines (per `CLAUDE.md`).
- After each implementation step, run the verification workflow from `CLAUDE.md`:
  - `make env-check` (first time only in session)
  - `just fix`
  - `just check`
  - `uv run pytest tests/<relevant file> -v`
- Full-suite verification runs only in Task 11 (final).
- TDD strictly: write the failing test first, run it to confirm it fails, then write the code.

---

## Task 1: Add `tomlkit` dependency

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add dependency via uv**

Run:
```bash
uv add 'tomlkit>=0.13'
```

Expected: `pyproject.toml` gains `"tomlkit>=0.13"` under `dependencies`; `uv.lock` updated.

- [ ] **Step 2: Verify import works**

Run:
```bash
uv run python -c "import tomlkit; print(tomlkit.__version__)"
```

Expected: version prints, no errors.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore(deps): add tomlkit for config writes"
```

---

## Task 2: XDG path helpers (`paths.py`) — tests first

**Files:**
- Create: `tests/test_paths.py`
- Create: `src/thoth/paths.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_paths.py`:

```python
"""Tests for XDG-compliant path helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from thoth import paths


@pytest.mark.parametrize(
    ("env_name", "func", "subpath", "default_rel"),
    [
        ("XDG_CONFIG_HOME", paths.user_config_dir, "thoth", ".config/thoth"),
        ("XDG_STATE_HOME", paths.user_state_dir, "thoth", ".local/state/thoth"),
        ("XDG_CACHE_HOME", paths.user_cache_dir, "thoth", ".cache/thoth"),
    ],
)
def test_dir_honors_env_when_set(
    env_name: str,
    func,
    subpath: str,
    default_rel: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(env_name, str(tmp_path))
    assert func() == tmp_path / subpath


@pytest.mark.parametrize(
    ("env_name", "func", "default_rel"),
    [
        ("XDG_CONFIG_HOME", paths.user_config_dir, ".config/thoth"),
        ("XDG_STATE_HOME", paths.user_state_dir, ".local/state/thoth"),
        ("XDG_CACHE_HOME", paths.user_cache_dir, ".cache/thoth"),
    ],
)
def test_dir_falls_back_when_env_unset(
    env_name: str,
    func,
    default_rel: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(env_name, raising=False)
    assert func() == Path.home() / default_rel


@pytest.mark.parametrize(
    ("env_name", "func", "default_rel"),
    [
        ("XDG_CONFIG_HOME", paths.user_config_dir, ".config/thoth"),
        ("XDG_STATE_HOME", paths.user_state_dir, ".local/state/thoth"),
        ("XDG_CACHE_HOME", paths.user_cache_dir, ".cache/thoth"),
    ],
)
def test_dir_falls_back_when_env_empty(
    env_name: str,
    func,
    default_rel: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Per XDG spec: empty string is treated as unset.
    monkeypatch.setenv(env_name, "")
    assert func() == Path.home() / default_rel


def test_user_config_file_under_config_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert paths.user_config_file() == tmp_path / "thoth" / "config.toml"


def test_user_checkpoints_dir_under_state_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    assert paths.user_checkpoints_dir() == tmp_path / "thoth" / "checkpoints"


def test_user_model_cache_dir_under_cache_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    assert paths.user_model_cache_dir() == tmp_path / "thoth" / "model_cache"
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `uv run pytest tests/test_paths.py -v`
Expected: ImportError / ModuleNotFoundError for `thoth.paths`.

- [ ] **Step 3: Implement `paths.py`**

Create `src/thoth/paths.py`:

```python
"""XDG Base Directory Specification path helpers for Thoth.

Per the spec, when an XDG_* env var is unset or empty, fall back to the
spec default relative to the user's home directory.
"""

from __future__ import annotations

import os
from pathlib import Path

_APP = "thoth"


def _xdg_dir(env_name: str, default_rel: str) -> Path:
    value = os.environ.get(env_name)
    if value:
        return Path(value) / _APP
    return Path.home() / default_rel / _APP


def user_config_dir() -> Path:
    return _xdg_dir("XDG_CONFIG_HOME", ".config")


def user_state_dir() -> Path:
    return _xdg_dir("XDG_STATE_HOME", ".local/state")


def user_cache_dir() -> Path:
    return _xdg_dir("XDG_CACHE_HOME", ".cache")


def user_config_file() -> Path:
    return user_config_dir() / "config.toml"


def user_checkpoints_dir() -> Path:
    return user_state_dir() / "checkpoints"


def user_model_cache_dir() -> Path:
    return user_cache_dir() / "model_cache"


__all__ = [
    "user_cache_dir",
    "user_checkpoints_dir",
    "user_config_dir",
    "user_config_file",
    "user_model_cache_dir",
    "user_state_dir",
]
```

- [ ] **Step 4: Run tests, verify pass**

Run: `uv run pytest tests/test_paths.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Lint + typecheck**

Run:
```bash
just fix
just check
```

Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add src/thoth/paths.py tests/test_paths.py
git commit -m "feat(paths): add XDG path helpers"
```

---

## Task 3: Migrate `config.py` + `models.py` + `commands.py` + `help.py` to `paths.py`

**Files:**
- Modify: `src/thoth/config.py`
- Modify: `src/thoth/models.py`
- Modify: `src/thoth/commands.py`
- Modify: `src/thoth/help.py`
- Modify: `tests/conftest.py`

- [ ] **Step 1: Update `conftest.py` to set XDG_STATE_HOME and XDG_CACHE_HOME**

Replace the `isolated_thoth_home` and `checkpoint_dir` fixtures in `tests/conftest.py`:

```python
@pytest.fixture
def isolated_thoth_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Per-test XDG_* roots so config/state/cache never hit the real user dir."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    return tmp_path


@pytest.fixture
def checkpoint_dir(isolated_thoth_home: Path) -> Path:
    """Thoth's checkpoint directory under the isolated test state dir."""
    from thoth.paths import user_checkpoints_dir

    path = user_checkpoints_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path
```

Also remove the now-unused `from platformdirs import user_config_dir` import from `conftest.py`.

- [ ] **Step 2: Migrate `src/thoth/config.py`**

Replace line 20:
```python
from platformdirs import user_config_dir
```
with:
```python
from thoth.paths import user_checkpoints_dir, user_config_file
```

Replace line 147 (inside `get_defaults`):
```python
"checkpoint_dir": str(Path(user_config_dir("thoth")) / "checkpoints"),
```
with:
```python
"checkpoint_dir": str(user_checkpoints_dir()),
```

Replace line 197 (inside `ConfigManager.__init__`):
```python
self.user_config_path = config_path or Path(user_config_dir("thoth")) / "config.toml"
```
with:
```python
self.user_config_path = config_path or user_config_file()
```

- [ ] **Step 3: Migrate `src/thoth/models.py`**

Replace line 19:
```python
from platformdirs import user_config_dir
```
with:
```python
from thoth.paths import user_model_cache_dir
```

Replace line 108:
```python
self.cache_dir = Path(user_config_dir("thoth")) / "model_cache"
```
with:
```python
self.cache_dir = user_model_cache_dir()
```

- [ ] **Step 4: Migrate `src/thoth/commands.py`**

Replace line 18:
```python
from platformdirs import user_config_dir
```
with:
```python
from thoth.paths import user_config_file
```

Replace the init_command default-path assignment (around line 71-72):
```python
if config_path is None:
    config_path = Path(user_config_dir("thoth")) / "config.toml"
```
with:
```python
if config_path is None:
    config_path = user_config_file()
```

- [ ] **Step 5: Migrate `src/thoth/help.py`**

Replace line 12:
```python
from platformdirs import user_config_dir
```
with:
```python
from thoth.paths import user_config_file
```

Replace line 106 (inside `show_init_help`):
```python
console.print(f"  {Path(user_config_dir('thoth')) / 'config.toml'}")
```
with:
```python
console.print(f"  {user_config_file()}")
```

Remove the now-unused `from pathlib import Path` import if no other callers remain in `help.py` (grep to confirm before removing).

- [ ] **Step 6: Remove `platformdirs` from pyproject dependencies**

Run:
```bash
uv remove platformdirs
```

Expected: `pyproject.toml` no longer lists `platformdirs`; lockfile updated.

- [ ] **Step 7: Verify no stragglers**

Run:
```bash
uv run python -c "import subprocess; subprocess.run(['grep', '-rn', 'platformdirs', 'src/', 'tests/'], check=False)"
```

Expected: empty output (no matches).

- [ ] **Step 8: Lint, typecheck, run existing tests**

Run:
```bash
just fix
just check
uv run pytest tests/ -x -q
```

Expected: all existing tests pass; no lint/type errors.

- [ ] **Step 9: Commit**

```bash
git add src/thoth/config.py src/thoth/models.py src/thoth/commands.py src/thoth/help.py tests/conftest.py pyproject.toml uv.lock
git commit -m "refactor(paths): migrate all callsites from platformdirs to XDG helpers"
```

---

## Task 4: `config_cmd.py` scaffold + `get` op (tests first)

**Files:**
- Create: `tests/test_config_cmd.py`
- Create: `src/thoth/config_cmd.py`

- [ ] **Step 1: Write failing tests for `get`**

Create `tests/test_config_cmd.py`:

```python
"""Tests for the `thoth config` subcommand."""

from __future__ import annotations

from pathlib import Path

import pytest

from thoth.config_cmd import config_command


def test_get_returns_merged_value(
    isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = config_command("get", ["general.default_mode"])
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert out == "default"


def test_get_missing_key_exits_nonzero(
    isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = config_command("get", ["nonexistent.key"])
    assert rc == 1


def test_get_layer_defaults(
    isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Write a user override, confirm --layer defaults still returns the default.
    user_toml = Path(isolated_thoth_home) / "config" / "thoth" / "config.toml"
    user_toml.parent.mkdir(parents=True, exist_ok=True)
    user_toml.write_text('version = "2.0"\n[general]\ndefault_mode = "exploration"\n')

    rc = config_command("get", ["--layer", "defaults", "general.default_mode"])
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert out == "default"


def test_get_raw_preserves_env_template(
    isolated_thoth_home: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    rc = config_command("get", ["--raw", "providers.openai.api_key"])
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert out == "${OPENAI_API_KEY}"
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `uv run pytest tests/test_config_cmd.py -v`
Expected: ImportError on `thoth.config_cmd`.

- [ ] **Step 3: Implement scaffold + `get`**

Create `src/thoth/config_cmd.py`:

```python
"""CLI surface for the `thoth config` subcommand."""

from __future__ import annotations

import json
import sys
from typing import Any

from rich.console import Console

from thoth.config import ConfigManager
from thoth.paths import user_config_file

console = Console()

_VALID_LAYERS = ("defaults", "user", "project", "env", "cli")


def _load_manager() -> ConfigManager:
    cm = ConfigManager()
    cm.load_all_layers({})
    return cm


def _dotted_get(data: dict[str, Any], key: str) -> tuple[bool, Any]:
    current: Any = data
    for part in key.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return False, None
    return True, current


def _render_scalar(value: Any, as_json: bool) -> str:
    if as_json:
        return json.dumps(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return value
    return str(value)


def _op_get(args: list[str]) -> int:
    layer: str | None = None
    raw = False
    as_json = False
    positional: list[str] = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--layer":
            if i + 1 >= len(args):
                console.print("[red]Error:[/red] --layer requires a value")
                return 2
            layer = args[i + 1]
            i += 2
        elif a == "--raw":
            raw = True
            i += 1
        elif a == "--json":
            as_json = True
            i += 1
        else:
            positional.append(a)
            i += 1

    if len(positional) != 1:
        console.print("[red]Error:[/red] config get takes exactly one KEY")
        return 2
    key = positional[0]

    cm = _load_manager()

    if layer is not None:
        if layer not in _VALID_LAYERS:
            console.print(
                f"[red]Error:[/red] --layer must be one of {', '.join(_VALID_LAYERS)}"
            )
            return 2
        data = cm.layers.get(layer, {})
    elif raw:
        # Rebuild merged dict without env substitution.
        merged: dict[str, Any] = {}
        for name in _VALID_LAYERS:
            layer_data = cm.layers.get(name) or {}
            merged = cm._deep_merge(merged, layer_data)
        data = merged
    else:
        data = cm.data

    found, value = _dotted_get(data, key)
    if not found:
        console.print(f"[red]Error:[/red] key not found: {key}")
        return 1

    print(_render_scalar(value, as_json))
    return 0


def config_command(op: str, args: list[str]) -> int:
    """Dispatch `thoth config <op>`. Returns a process exit code."""
    ops = {
        "get": _op_get,
    }
    if op not in ops:
        console.print(f"[red]Error:[/red] unknown config op: {op}")
        return 2
    return ops[op](args)


__all__ = ["config_command"]
```

- [ ] **Step 4: Run tests, verify pass**

Run: `uv run pytest tests/test_config_cmd.py -v -k "test_get"`
Expected: the four `get` tests pass.

- [ ] **Step 5: Lint + typecheck**

Run:
```bash
just fix
just check
```

- [ ] **Step 6: Commit**

```bash
git add src/thoth/config_cmd.py tests/test_config_cmd.py
git commit -m "feat(config): add config_command dispatcher with get op"
```

---

## Task 5: `set` op with TOML round-trip (tests first)

**Files:**
- Modify: `src/thoth/config_cmd.py`
- Modify: `tests/test_config_cmd.py`

- [ ] **Step 1: Append failing tests for `set`**

Append to `tests/test_config_cmd.py`:

```python
def test_set_writes_user_toml(
    isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = config_command("set", ["general.default_mode", "exploration"])
    assert rc == 0

    from thoth.paths import user_config_file

    path = user_config_file()
    assert path.exists()
    content = path.read_text()
    assert "exploration" in content

    # Effective merged read reflects it.
    rc2 = config_command("get", ["general.default_mode"])
    out = capsys.readouterr().out.strip().splitlines()[-1]
    assert rc2 == 0
    assert out == "exploration"


def test_set_project_writes_project_toml(
    isolated_thoth_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    rc = config_command("set", ["--project", "general.default_mode", "deep_dive"])
    assert rc == 0
    project_path = tmp_path / "thoth.toml"
    assert project_path.exists()
    assert "deep_dive" in project_path.read_text()

    # User file should not have been created.
    from thoth.paths import user_config_file
    assert not user_config_file().exists()


def test_set_parses_bool(isolated_thoth_home: Path) -> None:
    rc = config_command("set", ["execution.parallel_providers", "false"])
    assert rc == 0
    cm_rc = config_command("get", ["execution.parallel_providers"])
    assert cm_rc == 0


def test_set_parses_int(isolated_thoth_home: Path) -> None:
    rc = config_command("set", ["execution.poll_interval", "15"])
    assert rc == 0

    from thoth.paths import user_config_file
    import tomllib
    data = tomllib.loads(user_config_file().read_text())
    assert data["execution"]["poll_interval"] == 15


def test_set_string_flag_forces_string(isolated_thoth_home: Path) -> None:
    rc = config_command("set", ["--string", "execution.poll_interval", "15"])
    assert rc == 0

    from thoth.paths import user_config_file
    import tomllib
    data = tomllib.loads(user_config_file().read_text())
    assert data["execution"]["poll_interval"] == "15"


def test_set_preserves_existing_comments(isolated_thoth_home: Path) -> None:
    from thoth.paths import user_config_file
    path = user_config_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '# my header comment\nversion = "2.0"\n\n'
        "[general]\n# default mode picks the LLM prompt shape\n"
        'default_mode = "default"\n'
    )

    rc = config_command("set", ["general.default_mode", "exploration"])
    assert rc == 0

    content = path.read_text()
    assert "# my header comment" in content
    assert "# default mode picks the LLM prompt shape" in content
    assert "exploration" in content
```

- [ ] **Step 2: Run tests, verify failures**

Run: `uv run pytest tests/test_config_cmd.py -v -k "test_set"`
Expected: FAIL with "unknown config op: set".

- [ ] **Step 3: Implement `_op_set`**

In `src/thoth/config_cmd.py`, add imports at top:

```python
from pathlib import Path

import tomlkit
```

Add helper functions and `_op_set` above `config_command`:

```python
_ROOT_KEYS_ALLOW_UNKNOWN = ("modes",)


def _parse_value(raw: str, force_string: bool) -> Any:
    if force_string:
        return raw
    lower = raw.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    try:
        if "." in raw:
            return float(raw)
        return int(raw)
    except ValueError:
        return raw


def _target_path(project: bool) -> Path:
    if project:
        return Path.cwd() / "thoth.toml"
    return user_config_file()


def _load_toml_doc(path: Path):
    if path.exists():
        return tomlkit.parse(path.read_text())
    doc = tomlkit.document()
    doc.add("version", "2.0")
    return doc


def _warn_on_validation(key: str, value: Any) -> None:
    from thoth.config import ConfigSchema

    defaults = ConfigSchema.get_defaults()
    parts = key.split(".")
    if parts[0] in _ROOT_KEYS_ALLOW_UNKNOWN:
        return
    if parts[0] not in defaults:
        console.print(f"[yellow]Warning:[/yellow] unknown root key: {parts[0]}")
        return

    current: Any = defaults
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return
    if type(current) is not type(value) and current is not None:
        console.print(
            f"[yellow]Warning:[/yellow] type mismatch: default for {key} "
            f"is {type(current).__name__}, got {type(value).__name__}"
        )


def _set_in_doc(doc, key: str, value: Any) -> None:
    parts = key.split(".")
    current = doc
    for part in parts[:-1]:
        if part not in current or not hasattr(current[part], "keys"):
            current[part] = tomlkit.table()
        current = current[part]
    current[parts[-1]] = value


def _op_set(args: list[str]) -> int:
    project = False
    force_string = False
    positional: list[str] = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--project":
            project = True
            i += 1
        elif a == "--string":
            force_string = True
            i += 1
        else:
            positional.append(a)
            i += 1

    if len(positional) != 2:
        console.print("[red]Error:[/red] config set takes KEY VALUE")
        return 2
    key, raw = positional

    value = _parse_value(raw, force_string)
    _warn_on_validation(key, value)

    path = _target_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = _load_toml_doc(path)
    _set_in_doc(doc, key, value)
    path.write_text(tomlkit.dumps(doc))
    return 0
```

Register in the dispatcher:

```python
ops = {
    "get": _op_get,
    "set": _op_set,
}
```

- [ ] **Step 4: Run tests, verify pass**

Run: `uv run pytest tests/test_config_cmd.py -v -k "test_set"`
Expected: all `test_set_*` pass.

- [ ] **Step 5: Lint + typecheck**

Run:
```bash
just fix
just check
```

- [ ] **Step 6: Commit**

```bash
git add src/thoth/config_cmd.py tests/test_config_cmd.py
git commit -m "feat(config): add set op with tomlkit round-trip"
```

---

## Task 6: `unset` op (tests first)

**Files:**
- Modify: `src/thoth/config_cmd.py`
- Modify: `tests/test_config_cmd.py`

- [ ] **Step 1: Append failing tests**

Append to `tests/test_config_cmd.py`:

```python
def test_unset_removes_key(isolated_thoth_home: Path) -> None:
    config_command("set", ["general.default_mode", "exploration"])
    rc = config_command("unset", ["general.default_mode"])
    assert rc == 0

    from thoth.paths import user_config_file
    import tomllib
    data = tomllib.loads(user_config_file().read_text())
    # Empty [general] table should be pruned.
    assert "general" not in data


def test_unset_missing_key_is_noop(
    isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = config_command("unset", ["general.default_mode"])
    assert rc == 0
    err = capsys.readouterr().err
    # A stderr note is acceptable but not required for the no-op.
    assert err is not None


def test_unset_project_target(
    isolated_thoth_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    config_command("set", ["--project", "general.default_mode", "deep_dive"])
    rc = config_command("unset", ["--project", "general.default_mode"])
    assert rc == 0
    import tomllib
    data = tomllib.loads((tmp_path / "thoth.toml").read_text())
    assert "general" not in data
```

- [ ] **Step 2: Run tests, verify failures**

Run: `uv run pytest tests/test_config_cmd.py -v -k "test_unset"`
Expected: FAIL with "unknown config op: unset".

- [ ] **Step 3: Implement `_op_unset`**

Add in `config_cmd.py`:

```python
def _unset_in_doc(doc, key: str) -> bool:
    parts = key.split(".")
    stack = [doc]
    current = doc
    for part in parts[:-1]:
        if part not in current or not hasattr(current[part], "keys"):
            return False
        current = current[part]
        stack.append(current)

    leaf = parts[-1]
    if leaf not in current:
        return False
    del current[leaf]

    # Prune empty tables bottom-up.
    for container, part in zip(reversed(stack[:-1]), reversed(parts[:-1])):
        child = container[part]
        if hasattr(child, "keys") and len(child) == 0:
            del container[part]
        else:
            break
    return True


def _op_unset(args: list[str]) -> int:
    project = False
    positional: list[str] = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--project":
            project = True
            i += 1
        else:
            positional.append(a)
            i += 1

    if len(positional) != 1:
        console.print("[red]Error:[/red] config unset takes KEY")
        return 2
    key = positional[0]

    path = _target_path(project)
    if not path.exists():
        print(f"note: {path} does not exist; nothing to unset", file=sys.stderr)
        return 0

    doc = tomlkit.parse(path.read_text())
    removed = _unset_in_doc(doc, key)
    if not removed:
        print(f"note: key not found: {key}", file=sys.stderr)
        return 0

    path.write_text(tomlkit.dumps(doc))
    return 0
```

Register: add `"unset": _op_unset` in the `ops` dict inside `config_command`.

- [ ] **Step 4: Run tests, verify pass**

Run: `uv run pytest tests/test_config_cmd.py -v -k "test_unset"`
Expected: all `test_unset_*` pass.

- [ ] **Step 5: Commit**

```bash
git add src/thoth/config_cmd.py tests/test_config_cmd.py
just fix
git commit -m "feat(config): add unset op with empty-table pruning"
```

---

## Task 7: `list` + `path` ops (tests first)

**Files:**
- Modify: `src/thoth/config_cmd.py`
- Modify: `tests/test_config_cmd.py`

- [ ] **Step 1: Append failing tests**

Append to `tests/test_config_cmd.py`:

```python
def test_list_prints_toml(
    isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = config_command("list", [])
    out = capsys.readouterr().out
    assert rc == 0
    assert 'version = "2.0"' in out
    assert "[general]" in out


def test_list_keys_emits_sorted_dotted(
    isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = config_command("list", ["--keys"])
    out = capsys.readouterr().out.strip().splitlines()
    assert rc == 0
    assert "general.default_mode" in out
    assert out == sorted(out)


def test_list_json_is_valid_json(
    isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    import json
    rc = config_command("list", ["--json"])
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "version" in data


def test_list_layer_shows_one_layer(
    isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config_command("set", ["general.default_mode", "exploration"])
    capsys.readouterr()
    rc = config_command("list", ["--layer", "defaults"])
    out = capsys.readouterr().out
    assert rc == 0
    # defaults layer should still have "default", not "exploration".
    assert 'default_mode = "default"' in out


def test_path_prints_user_config_path(
    isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from thoth.paths import user_config_file

    rc = config_command("path", [])
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert out == str(user_config_file())


def test_path_project_prints_project_path(
    isolated_thoth_home: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    rc = config_command("path", ["--project"])
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert out == str(tmp_path / "thoth.toml")
```

- [ ] **Step 2: Run, confirm failure**

Run: `uv run pytest tests/test_config_cmd.py -v -k "test_list or test_path"`
Expected: FAIL with "unknown config op: list" etc.

- [ ] **Step 3: Implement `_op_list` and `_op_path`**

Add in `config_cmd.py`:

```python
def _flatten_keys(data: dict[str, Any], prefix: str = "") -> list[str]:
    out: list[str] = []
    for k, v in data.items():
        full = f"{prefix}{k}" if not prefix else f"{prefix}.{k}"
        if isinstance(v, dict):
            out.extend(_flatten_keys(v, full))
        else:
            out.append(full)
    return out


def _to_plain(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: _to_plain(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_to_plain(v) for v in data]
    if isinstance(data, Path):
        return str(data)
    return data


def _op_list(args: list[str]) -> int:
    layer: str | None = None
    keys_only = False
    as_json = False
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--layer":
            if i + 1 >= len(args):
                console.print("[red]Error:[/red] --layer requires a value")
                return 2
            layer = args[i + 1]
            i += 2
        elif a == "--keys":
            keys_only = True
            i += 1
        elif a == "--json":
            as_json = True
            i += 1
        else:
            console.print(f"[red]Error:[/red] unknown arg: {a}")
            return 2

    cm = _load_manager()

    if layer is not None:
        if layer not in _VALID_LAYERS:
            console.print(
                f"[red]Error:[/red] --layer must be one of {', '.join(_VALID_LAYERS)}"
            )
            return 2
        data: dict[str, Any] = cm.layers.get(layer) or {}
    else:
        data = cm.data

    if keys_only:
        for key in sorted(_flatten_keys(data)):
            print(key)
        return 0

    if as_json:
        print(json.dumps(_to_plain(data), indent=2, sort_keys=True))
        return 0

    # Default: TOML render.
    print(tomlkit.dumps(_to_plain(data)))
    return 0


def _op_path(args: list[str]) -> int:
    project = "--project" in args
    path = _target_path(project)
    print(str(path))
    return 0
```

Register in dispatcher: `"list": _op_list, "path": _op_path`.

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_config_cmd.py -v -k "test_list or test_path"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
just fix
git add src/thoth/config_cmd.py tests/test_config_cmd.py
git commit -m "feat(config): add list and path ops"
```

---

## Task 8: Secrets masking on `get` and `list` (tests first)

**Files:**
- Modify: `src/thoth/config_cmd.py`
- Modify: `tests/test_config_cmd.py`

- [ ] **Step 1: Append failing tests**

Append to `tests/test_config_cmd.py`:

```python
def test_get_masks_api_key_by_default(
    isolated_thoth_home: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-abcdef123456wxyz")
    rc = config_command("get", ["providers.openai.api_key"])
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert out == "****wxyz"


def test_get_show_secrets_reveals(
    isolated_thoth_home: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-abcdef123456wxyz")
    rc = config_command("get", ["--show-secrets", "providers.openai.api_key"])
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert out == "sk-abcdef123456wxyz"


def test_list_masks_api_keys_by_default(
    isolated_thoth_home: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-abcdef123456wxyz")
    rc = config_command("list", [])
    out = capsys.readouterr().out
    assert rc == 0
    assert "sk-abcdef123456wxyz" not in out
    assert "****wxyz" in out
```

- [ ] **Step 2: Run, confirm failure**

Run: `uv run pytest tests/test_config_cmd.py -v -k "mask or show_secrets"`
Expected: FAIL.

- [ ] **Step 3: Implement masking helpers**

Add to `config_cmd.py`:

```python
_SECRET_KEY_SUFFIX = "api_key"


def _mask_secret(value: Any) -> Any:
    if not isinstance(value, str) or not value:
        return value
    if value.startswith("${") and value.endswith("}"):
        return value  # env template, leave as-is
    tail = value[-4:] if len(value) >= 4 else value
    return f"****{tail}"


def _is_secret_key(key: str) -> bool:
    return key.split(".")[-1] == _SECRET_KEY_SUFFIX


def _mask_in_tree(data: Any, prefix: str = "") -> Any:
    if isinstance(data, dict):
        return {
            k: _mask_in_tree(v, f"{prefix}.{k}" if prefix else k)
            for k, v in data.items()
        }
    if prefix and _is_secret_key(prefix):
        return _mask_secret(data)
    return data
```

Update `_op_get` — parse `--show-secrets` and apply masking:

```python
# In _op_get arg-parse loop, add:
elif a == "--show-secrets":
    show_secrets = True
    i += 1

# Initialize near the top:
show_secrets = False

# Replace the final print with:
if _is_secret_key(key) and not show_secrets and not raw:
    value = _mask_secret(value)
print(_render_scalar(value, as_json))
```

Update `_op_list` — parse `--show-secrets`, apply `_mask_in_tree` before output when not `show_secrets`:

```python
# Add to arg loop:
elif a == "--show-secrets":
    show_secrets = True
    i += 1

# Initialize:
show_secrets = False

# Before rendering, if not show_secrets:
rendered = _to_plain(data)
if not show_secrets:
    rendered = _mask_in_tree(rendered)

# Then use `rendered` in place of _to_plain(data) in the TOML/JSON/keys branches
# (keys branch unaffected — keys aren't secrets).
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_config_cmd.py -v -k "mask or show_secrets"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
just fix
git add src/thoth/config_cmd.py tests/test_config_cmd.py
git commit -m "feat(config): mask api_key values by default with --show-secrets opt-in"
```

---

## Task 9: `edit` and `help` ops (tests first)

**Files:**
- Modify: `src/thoth/config_cmd.py`
- Modify: `src/thoth/help.py`
- Modify: `tests/test_config_cmd.py`

- [ ] **Step 1: Append failing tests**

Append to `tests/test_config_cmd.py`:

```python
def test_edit_invokes_editor_and_creates_file(
    isolated_thoth_home: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Stub editor writes a sentinel to its first argv arg.
    stub = tmp_path / "editor.sh"
    stub.write_text('#!/bin/sh\necho "EDITED" >> "$1"\n')
    stub.chmod(0o755)
    monkeypatch.setenv("EDITOR", str(stub))

    from thoth.paths import user_config_file
    assert not user_config_file().exists()

    rc = config_command("edit", [])
    assert rc == 0
    content = user_config_file().read_text()
    assert "version" in content
    assert "EDITED" in content


def test_help_renders_text(capsys: pytest.CaptureFixture[str]) -> None:
    rc = config_command("help", [])
    out = capsys.readouterr().out
    assert rc == 0
    assert "thoth config" in out
    assert "get" in out
    assert "set" in out
    assert "unset" in out
```

- [ ] **Step 2: Run, confirm failure**

Run: `uv run pytest tests/test_config_cmd.py -v -k "test_edit or test_help"`
Expected: FAIL.

- [ ] **Step 3: Add `show_config_help()` in `help.py`**

In `src/thoth/help.py`, add before the `__all__` list:

```python
def show_config_help():
    """Show detailed help for the config command."""
    console.print("\n[bold]thoth config[/bold] - Inspect and edit configuration")
    console.print("\n[bold]Usage:[/bold]")
    console.print("  thoth config <OP> [ARGS...]")
    console.print("\n[bold]Ops:[/bold]")
    console.print("  get <KEY> [--layer L] [--raw] [--json] [--show-secrets]")
    console.print("     Print a single value from the merged config.")
    console.print("  set <KEY> <VALUE> [--project] [--string]")
    console.print("     Write a value to the user config (or project with --project).")
    console.print("  unset <KEY> [--project]")
    console.print("     Remove a key from the target file (empty tables are pruned).")
    console.print("  list [--layer L] [--keys] [--json] [--show-secrets]")
    console.print("     Print the merged config (or a single layer).")
    console.print("  path [--project]")
    console.print("     Print the target config file path.")
    console.print("  edit [--project]")
    console.print("     Open the target config file in $EDITOR (fallback: vi).")
    console.print("  help")
    console.print("     Show this help.")
    console.print("\n[bold]Examples:[/bold]")
    console.print('  $ thoth config get general.default_mode')
    console.print('  $ thoth config set general.default_mode exploration')
    console.print('  $ thoth config set --project execution.poll_interval 15')
    console.print('  $ thoth config list --keys')
    console.print('  $ thoth config path')
    console.print("\n[bold]Notes:[/bold]")
    console.print("  API key values are masked by default; use --show-secrets to reveal.")
    console.print("  Writes preserve comments and formatting of the target TOML file.")
```

Add `"show_config_help"` to `__all__` and update the imports in `commands.py` and `cli.py` later tasks to use it.

- [ ] **Step 4: Implement `_op_edit` and `_op_help` in `config_cmd.py`**

```python
def _op_help(args: list[str]) -> int:
    from thoth.help import show_config_help

    show_config_help()
    return 0


def _op_edit(args: list[str]) -> int:
    import os
    import shutil
    import subprocess  # noqa: S404

    project = "--project" in args
    path = _target_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        doc = tomlkit.document()
        doc.add("version", "2.0")
        path.write_text(tomlkit.dumps(doc))

    editor = os.environ.get("EDITOR") or shutil.which("vi") or "vi"
    rc = subprocess.call([editor, str(path)])  # noqa: S603
    return rc
```

Register: `"edit": _op_edit, "help": _op_help`.

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_config_cmd.py -v -k "test_edit or test_help"`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
just fix
git add src/thoth/config_cmd.py src/thoth/help.py tests/test_config_cmd.py
git commit -m "feat(config): add edit and help ops"
```

---

## Task 10: Wire `config` into `cli.py` + `commands.py` + help system

**Files:**
- Modify: `src/thoth/cli.py`
- Modify: `src/thoth/commands.py`
- Modify: `src/thoth/help.py`
- Modify: `tests/test_config_cmd.py`

- [ ] **Step 1: Append end-to-end test via click runner**

Append to `tests/test_config_cmd.py`:

```python
def test_cli_config_get_via_click(
    isolated_thoth_home: Path,
) -> None:
    from click.testing import CliRunner

    from thoth.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "get", "general.default_mode"])
    assert result.exit_code == 0
    assert result.stdout.strip().splitlines()[-1] == "default"


def test_cli_config_help_listed_in_epilog() -> None:
    from click.testing import CliRunner

    from thoth.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert "config" in result.stdout
```

- [ ] **Step 2: Run, confirm failure**

Run: `uv run pytest tests/test_config_cmd.py -v -k "test_cli_config"`
Expected: FAIL (config not dispatched).

- [ ] **Step 3: Register in `cli.py` subcommand list**

In `src/thoth/cli.py`, update the two `if args and args[0] in [...]` checks (lines 157 and 222) to include `"config"`:

```python
if not (args and args[0] in ["init", "status", "list", "help", "providers", "config"]):
```

and:

```python
if args and args[0] in ["init", "status", "list", "help", "providers", "config"]:
```

Inside the dispatch block, after the existing `elif command == "providers":` branch and before `elif command == "help":`, add:

```python
elif command == "config":
    from thoth.config_cmd import config_command

    if len(args) < 2:
        console.print("[red]Error:[/red] config command requires an op (get|set|unset|list|path|edit|help)")
        sys.exit(2)
    op = args[1]
    rest = list(args[2:]) + list(ctx.args)
    rc = config_command(op, rest)
    sys.exit(rc)
```

Also extend the `thoth help <cmd>` dispatch in `cli.py` to recognize `config`:

```python
elif help_command == "config":
    show_config_help()
```

And add the import at top of `cli.py`:

```python
from thoth.help import (
    ThothCommand,
    build_epilog,
    show_config_help,
    show_init_help,
    ...
)
```

- [ ] **Step 4: Extend `ThothCommand.parse_args` in `help.py` to intercept `--help config`**

In `help.py`, inside `ThothCommand.parse_args`, add a branch for `"config"`:

```python
elif subcommand == "config":
    show_config_help()
    ctx.exit(0)
```

- [ ] **Step 5: Extend `build_epilog()` and `show_general_help()` in `help.py`**

In `build_epilog()` Commands list, insert before the `help` line:

```python
lines.append("  config          Inspect and edit configuration")
```

In `show_general_help()` Commands list, insert before the `help` line:

```python
console.print("  config          Inspect and edit configuration")
```

- [ ] **Step 6: Register in `CommandHandler` (commands.py)**

In `src/thoth/commands.py`, add `"config"` to the `self.commands` dict inside `CommandHandler.__init__`:

```python
self.commands = {
    "init": self.init_command,
    "status": self.status_command,
    "list": self.list_command,
    "providers": self.providers_command,
    "research": self.research_command,
    "help": self.help_command,
    "config": self.config_command,
}
```

Add a thin wrapper method on `CommandHandler`:

```python
def config_command(self, op: str | None = None, rest: list[str] | None = None, **params) -> int:
    from thoth.config_cmd import config_command as _cfg

    if op is None:
        raise ThothError(
            "config requires an op",
            "Run `thoth config help` for usage",
        )
    return _cfg(op, rest or [])
```

- [ ] **Step 7: Run CLI tests + full existing suite**

Run:
```bash
uv run pytest tests/test_config_cmd.py -v
uv run pytest tests/ -x -q
```

Expected: all pass.

- [ ] **Step 8: Lint + typecheck**

Run:
```bash
just fix
just check
```

- [ ] **Step 9: Commit**

```bash
git add src/thoth/cli.py src/thoth/commands.py src/thoth/help.py tests/test_config_cmd.py
git commit -m "feat(config): wire config subcommand into CLI dispatch and help system"
```

---

## Task 11: Final verification per CLAUDE.md workflow

**Files:** none modified; this task only runs checks.

- [ ] **Step 1: Environment check**

Run: `make env-check`
Expected: no errors.

- [ ] **Step 2: Lint auto-fix**

Run: `just fix`
Expected: no changes left.

- [ ] **Step 3: Check (lint + typecheck)**

Run: `just check`
Expected: no errors.

- [ ] **Step 4: Full test run**

Run: `./thoth_test -r`
Expected: all tests pass.

- [ ] **Step 5: Test-suite lint/typecheck**

Run:
```bash
just test-fix
just test-lint
just test-typecheck
```

Expected: no errors.

- [ ] **Step 6: Smoke test the new subcommand manually**

Run (in a throwaway dir):
```bash
export XDG_CONFIG_HOME="$(mktemp -d)"
export XDG_STATE_HOME="$(mktemp -d)"
export XDG_CACHE_HOME="$(mktemp -d)"
uv run thoth config path
uv run thoth config get general.default_mode
uv run thoth config set general.default_mode exploration
uv run thoth config get general.default_mode
uv run thoth config list --keys
uv run thoth config help
```

Expected (abbreviated):
- `path` prints `${XDG_CONFIG_HOME}/thoth/config.toml`
- first `get` prints `default`
- after `set`, `get` prints `exploration`
- `list --keys` prints sorted dotted keys including `general.default_mode`
- `help` renders the help text

- [ ] **Step 7: Update PROJECTS.md**

Per project convention, append a new Project entry to `PROJECTS.md`:

```markdown
## [x] Project P25: Config Subcommand + XDG Layout (v2.6.0)
**Goal**: Add `thoth config` subcommand (get/set/unset/list/path/edit/help) and migrate user-writable paths to XDG Base Directory Spec.

### Tests & Tasks
- [x] [P25-T01] Add tomlkit dep
- [x] [P25-T02] XDG path helpers (paths.py) with TDD
- [x] [P25-T03] Migrate all platformdirs callsites to paths.py
- [x] [P25-T04] config_cmd.py scaffold + get op
- [x] [P25-T05] set op with tomlkit round-trip
- [x] [P25-T06] unset op with table pruning
- [x] [P25-T07] list + path ops
- [x] [P25-T08] Secrets masking
- [x] [P25-T09] edit + help ops
- [x] [P25-T10] Wire into CLI and help system
- [x] [P25-T11] Final verification
```

Numbering note: inspect existing PROJECTS.md to pick the next free `P##` if `P25` is taken.

- [ ] **Step 8: Commit**

```bash
git add PROJECTS.md
git commit -m "docs(projects): mark config subcommand + XDG project complete"
```

---

## Self-Review Notes

**Spec coverage:** Every section of the spec (XDG layout, 7 ops, secrets, validation, tomlkit writes, help/discoverability, tests, files touched, out-of-scope items) maps to at least one task. Secrets masking is Task 8; validation warnings are covered in `_warn_on_validation` in Task 5.

**Type consistency:** `config_command(op, args)` signature is stable across Tasks 4–10. Helper names (`_op_get`, `_op_set`, `_op_unset`, `_op_list`, `_op_path`, `_op_edit`, `_op_help`) are consistent. `_target_path`, `_load_toml_doc`, `_set_in_doc`, `_unset_in_doc`, `_mask_secret`, `_mask_in_tree`, `_is_secret_key`, `_flatten_keys`, `_to_plain`, `_render_scalar` are each defined once and reused.

**Placeholder scan:** No `TBD`, `TODO`, "implement later", or "similar to Task N" references. Every code step shows the actual code.

**Known small deviations worth flagging to the executor:**
- `_warn_on_validation` in Task 5 uses `type(current) is not type(value)` which treats `int`/`float` as distinct. This is acceptable because `set` returns warnings, not errors. If future refinement is needed, substitute `isinstance(value, type(current))` with numeric relaxation.
- The `_op_set` parse-value `int(raw)` path will accept negative numbers and arbitrarily large ints; strings like `"3.14.15"` fall through to string, which is correct.
- `conftest.py` fixture edit in Task 3 is non-trivial and affects **all** tests. Run the full suite after Task 3 before proceeding.
