# P11: `thoth modes` Discovery Command — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a single authoritative `thoth modes` command so users can see every research mode (built-in + user-defined) with provider, model, kind (immediate vs background), and origin source — without reading source or guessing from mode descriptions.

**Architecture:** One `ModeInfo` dataclass + one `list_all_modes(cm)` helper in a new `src/thoth/modes_cmd.py` become the single source of truth. `help.py` and `interactive.py` stop iterating `BUILTIN_MODES` directly and call the helper instead. A new `is_background_mode()` helper in `config.py` replaces the ad-hoc `"deep-research" in model` checks in the OpenAI provider and is reused by the new command. CLI dispatch in `cli.py` gains a `modes` branch that parallels the existing `config` branch.

**Tech Stack:** Python 3.11+, click, rich, tomlkit, pytest. Existing pytest fixtures `isolated_thoth_home` and `stub_config` in `tests/conftest.py`.

---

## File Structure

**Create:**
- `src/thoth/modes_cmd.py` — new module: `ModeInfo` dataclass, `list_all_modes()`, `modes_command()` dispatch, table/JSON/detail renderers.
- `tests/test_is_background_mode.py` — unit tests for the new helper.
- `tests/test_modes_cmd.py` — unit + subprocess tests for the new command.

**Modify:**
- `src/thoth/config.py` — add `is_background_mode()` helper near `BUILTIN_MODES`; change `BUILTIN_MODES["thinking"]["model"]` from `"o3-deep-research"` to `"o3"`.
- `src/thoth/providers/openai.py:175,182` — call `is_background_mode()` instead of inline `"deep-research" in self.model`.
- `src/thoth/cli.py:158,223,294` — add `"modes"` to the command list, dispatch to `modes_command()`, and handle `thoth help modes`.
- `src/thoth/help.py:12,58-91,254-288` — import + call `list_all_modes()` in the epilog and general-help mode listing; add `show_modes_help()`.
- `src/thoth/interactive.py:27,117-144,680-685,777-789` — route `BUILTIN_MODES` enumeration through `list_all_modes()`.

**Test paths:**
- `tests/test_is_background_mode.py`
- `tests/test_modes_cmd.py`

---

## Task 1: `is_background_mode` helper (TDD)

**Files:**
- Create: `tests/test_is_background_mode.py`
- Modify: `src/thoth/config.py` (add helper near line 155, after `BUILTIN_MODES`)

- [ ] **Step 1.1: Write the failing test file**

Create `tests/test_is_background_mode.py`:

```python
"""Tests for the is_background_mode helper."""

from __future__ import annotations

from thoth.config import is_background_mode


def test_explicit_async_true_overrides_missing_model() -> None:
    assert is_background_mode({"async": True}) is True


def test_explicit_async_false_overrides_deep_research_model() -> None:
    assert is_background_mode({"async": False, "model": "o3-deep-research"}) is False


def test_model_contains_deep_research_is_background() -> None:
    assert is_background_mode({"model": "o3-deep-research"}) is True


def test_model_contains_mini_deep_research_is_background() -> None:
    assert is_background_mode({"model": "o4-mini-deep-research"}) is True


def test_model_without_deep_research_is_immediate() -> None:
    assert is_background_mode({"model": "o3"}) is False


def test_missing_model_key_is_immediate() -> None:
    assert is_background_mode({}) is False


def test_model_none_is_immediate() -> None:
    assert is_background_mode({"model": None}) is False
```

- [ ] **Step 1.2: Run the test to confirm it fails**

Run: `uv run pytest tests/test_is_background_mode.py -x -v`
Expected: `ImportError: cannot import name 'is_background_mode' from 'thoth.config'`

- [ ] **Step 1.3: Add the helper to `src/thoth/config.py`**

Insert directly after the closing brace of `BUILTIN_MODES` (before `class ConfigSchema`), around line 155:

```python
def is_background_mode(mode_config: dict[str, Any]) -> bool:
    """Return True if a mode submits as a long-running background job.

    Precedence: explicit `async` key wins; otherwise derive from model name
    (any model containing "deep-research" is a background/long-running model).
    """
    if "async" in mode_config:
        return bool(mode_config["async"])
    model = mode_config.get("model") or ""
    return "deep-research" in model
```

- [ ] **Step 1.4: Run the test to confirm it passes**

Run: `uv run pytest tests/test_is_background_mode.py -x -v`
Expected: 7 passed.

- [ ] **Step 1.5: Commit**

```bash
git add tests/test_is_background_mode.py src/thoth/config.py
git commit -m "feat(config): add is_background_mode helper for mode-kind derivation"
```

---

## Task 2: Refactor OpenAI provider to use the helper

**Files:**
- Modify: `src/thoth/providers/openai.py:175,182`

- [ ] **Step 2.1: Replace the two inline checks**

In `src/thoth/providers/openai.py`, change lines 175 and 182.

Find (line 175):
```python
        if "deep-research" in self.model:
```
Replace with:
```python
        if is_background_mode({"model": self.model}):
```

Find (line 182):
```python
        use_background = "deep-research" in self.model or self.config.get("background", False)
```
Replace with:
```python
        use_background = is_background_mode({"model": self.model}) or self.config.get(
            "background", False
        )
```

- [ ] **Step 2.2: Add the import**

At the top of `src/thoth/providers/openai.py`, find the existing `from thoth.config import` line. If none exists, add:

```python
from thoth.config import is_background_mode
```

Verify by grepping:
```bash
grep -n "from thoth.config" src/thoth/providers/openai.py
```

- [ ] **Step 2.3: Run the existing OpenAI suite to confirm no regression**

Run: `uv run pytest tests/test_oai_background.py tests/test_vcr_openai.py tests/test_openai_errors.py -x -v`
Expected: all pass (same counts as before).

- [ ] **Step 2.4: Commit**

```bash
git add src/thoth/providers/openai.py
git commit -m "refactor(openai): route background detection through is_background_mode"
```

---

## Task 3: Fix `thinking` mode to actually be immediate

**Files:**
- Modify: `src/thoth/config.py` (inside `BUILTIN_MODES["thinking"]`)
- Create: `tests/test_modes_thinking_kind.py`

- [ ] **Step 3.1: Write a failing test**

Create `tests/test_modes_thinking_kind.py`:

```python
"""Regression test: `thinking` mode must be immediate (not deep-research)."""

from __future__ import annotations

from thoth.config import BUILTIN_MODES, is_background_mode


def test_thinking_mode_is_immediate() -> None:
    cfg = BUILTIN_MODES["thinking"]
    assert cfg["model"] == "o3", (
        "thinking mode's description claims 'quick analysis' — the model must "
        "be a non-deep-research model so it runs immediately"
    )
    assert is_background_mode(cfg) is False
```

- [ ] **Step 3.2: Run the test to confirm it fails**

Run: `uv run pytest tests/test_modes_thinking_kind.py -x -v`
Expected: FAIL with `AssertionError: ... model must be a non-deep-research model ...`

- [ ] **Step 3.3: Update `BUILTIN_MODES["thinking"]`**

In `src/thoth/config.py`, find:

```python
    "thinking": {
        "provider": "openai",
        "model": "o3-deep-research",  # Use deep research for thinking
        "temperature": 0.4,
```

Replace with:

```python
    "thinking": {
        "provider": "openai",
        "model": "o3",
        "temperature": 0.4,
```

- [ ] **Step 3.4: Run the test to confirm it passes**

Run: `uv run pytest tests/test_modes_thinking_kind.py -x -v`
Expected: 1 passed.

- [ ] **Step 3.5: Commit**

```bash
git add tests/test_modes_thinking_kind.py src/thoth/config.py
git commit -m "fix(modes): thinking mode uses o3 not o3-deep-research (matches description)"
```

---

## Task 4: `ModeInfo` dataclass + `list_all_modes` helper (TDD)

**Files:**
- Create: `src/thoth/modes_cmd.py`
- Create: `tests/test_modes_cmd.py`

- [ ] **Step 4.1: Write failing tests for `list_all_modes`**

Create `tests/test_modes_cmd.py`:

```python
"""Tests for thoth.modes_cmd.list_all_modes and ModeInfo."""

from __future__ import annotations

from pathlib import Path

import pytest

from thoth.config import ConfigManager
from thoth.modes_cmd import ModeInfo, list_all_modes


def _cm(isolated_thoth_home: Path, toml: str | None = None) -> ConfigManager:
    if toml is not None:
        cfg = Path(isolated_thoth_home) / "config" / "thoth" / "config.toml"
        cfg.parent.mkdir(parents=True, exist_ok=True)
        cfg.write_text(toml)
    cm = ConfigManager()
    cm.load_all_layers({})
    return cm


def test_returns_all_builtin_modes(isolated_thoth_home: Path) -> None:
    modes = list_all_modes(_cm(isolated_thoth_home))
    names = {m.name for m in modes}
    assert {"default", "clarification", "thinking", "deep_research"} <= names


def test_builtin_mode_fields_populated(isolated_thoth_home: Path) -> None:
    modes = list_all_modes(_cm(isolated_thoth_home))
    default = next(m for m in modes if m.name == "default")
    assert default.source == "builtin"
    assert default.providers == ["openai"]
    assert default.model == "o3"
    assert default.kind == "immediate"
    assert default.overrides == {}


def test_deep_research_mode_is_background(isolated_thoth_home: Path) -> None:
    modes = list_all_modes(_cm(isolated_thoth_home))
    dr = next(m for m in modes if m.name == "deep_research")
    assert dr.kind == "background"


def test_providers_list_normalization(isolated_thoth_home: Path) -> None:
    # deep_research uses `providers: ["openai"]` (list form) — must normalize.
    modes = list_all_modes(_cm(isolated_thoth_home))
    dr = next(m for m in modes if m.name == "deep_research")
    assert isinstance(dr.providers, list)
    assert dr.providers == ["openai"]


def test_user_only_mode(isolated_thoth_home: Path) -> None:
    toml = (
        'version = "2.0"\n'
        "[modes.my_brief]\n"
        'provider = "openai"\n'
        'model = "gpt-4o-mini"\n'
        'description = "my user-only mode"\n'
    )
    modes = list_all_modes(_cm(isolated_thoth_home, toml))
    mine = next(m for m in modes if m.name == "my_brief")
    assert mine.source == "user"
    assert mine.model == "gpt-4o-mini"
    assert mine.kind == "immediate"
    assert mine.overrides == {}


def test_overridden_mode_reports_diff(isolated_thoth_home: Path) -> None:
    toml = (
        'version = "2.0"\n'
        "[modes.deep_research]\n"
        "parallel = false\n"
    )
    modes = list_all_modes(_cm(isolated_thoth_home, toml))
    dr = next(m for m in modes if m.name == "deep_research")
    assert dr.source == "overridden"
    assert "parallel" in dr.overrides
    assert dr.overrides["parallel"] == {"builtin": True, "effective": False}


def test_malformed_user_mode_kind_unknown(isolated_thoth_home: Path) -> None:
    # No model, no provider — must NOT crash; must surface as unknown.
    toml = (
        'version = "2.0"\n'
        "[modes.broken]\n"
        'description = "missing model and provider"\n'
    )
    modes = list_all_modes(_cm(isolated_thoth_home, toml))
    broken = next(m for m in modes if m.name == "broken")
    assert broken.source == "user"
    assert broken.kind == "unknown"
    assert broken.warnings  # non-empty list of warning strings


def test_modeinfo_is_frozen_dataclass() -> None:
    m = ModeInfo(
        name="x",
        source="builtin",
        providers=["openai"],
        model="o3",
        kind="immediate",
        description="",
        overrides={},
        warnings=[],
        raw={},
    )
    with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
        m.name = "y"  # type: ignore[misc]
```

- [ ] **Step 4.2: Run tests to confirm they fail**

Run: `uv run pytest tests/test_modes_cmd.py -x -v`
Expected: `ImportError: No module named 'thoth.modes_cmd'` (all collection errors).

- [ ] **Step 4.3: Create `src/thoth/modes_cmd.py` with `ModeInfo` and `list_all_modes`**

```python
"""CLI surface for the `thoth modes` subcommand.

Single source of truth for mode enumeration: `list_all_modes(cm)` returns a
list of `ModeInfo` objects covering built-in modes (from `BUILTIN_MODES`),
user-defined modes (from `[modes.*]` in user/project TOML), and modes that
override a builtin (present in both).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from thoth.config import BUILTIN_MODES, ConfigManager, is_background_mode

Source = Literal["builtin", "user", "overridden"]
Kind = Literal["immediate", "background", "unknown"]


@dataclass(frozen=True)
class ModeInfo:
    name: str
    source: Source
    providers: list[str]
    model: str | None
    kind: Kind
    description: str
    overrides: dict[str, dict[str, Any]]
    warnings: list[str]
    raw: dict[str, Any]


def _normalize_providers(cfg: dict[str, Any]) -> list[str]:
    if "providers" in cfg and isinstance(cfg["providers"], list):
        return [str(p) for p in cfg["providers"]]
    if "provider" in cfg:
        return [str(cfg["provider"])]
    return []


def _derive_kind(cfg: dict[str, Any], warnings: list[str]) -> Kind:
    if not cfg.get("model") and "async" not in cfg:
        warnings.append("missing `model` and no explicit `async` — kind unknown")
        return "unknown"
    return "background" if is_background_mode(cfg) else "immediate"


def _compute_overrides(
    builtin: dict[str, Any], user: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    diff: dict[str, dict[str, Any]] = {}
    for key in sorted(set(builtin) | set(user)):
        b_val = builtin.get(key)
        u_val = user.get(key, b_val)
        if key in user and u_val != b_val:
            diff[key] = {"builtin": b_val, "effective": u_val}
    return diff


def list_all_modes(cm: ConfigManager) -> list[ModeInfo]:
    """Enumerate every research mode known to Thoth.

    Merges `BUILTIN_MODES` with user `[modes.*]` tables exposed by the
    ConfigManager. Each `ModeInfo` carries enough data for table, JSON, or
    detail-view rendering.
    """
    user_modes: dict[str, Any] = cm.data.get("modes") or {}
    names = sorted(set(BUILTIN_MODES) | set(user_modes))

    infos: list[ModeInfo] = []
    for name in names:
        builtin_cfg = BUILTIN_MODES.get(name, {})
        user_cfg = user_modes.get(name) or {}
        merged: dict[str, Any] = {**builtin_cfg, **user_cfg}

        if name in BUILTIN_MODES and name in user_modes:
            source: Source = "overridden"
        elif name in BUILTIN_MODES:
            source = "builtin"
        else:
            source = "user"

        warnings: list[str] = []
        kind = _derive_kind(merged, warnings)
        providers = _normalize_providers(merged)
        overrides = (
            _compute_overrides(builtin_cfg, user_cfg) if source == "overridden" else {}
        )

        infos.append(
            ModeInfo(
                name=name,
                source=source,
                providers=providers,
                model=merged.get("model"),
                kind=kind,
                description=str(merged.get("description", "")),
                overrides=overrides,
                warnings=warnings,
                raw=merged,
            )
        )
    return infos


__all__ = ["ModeInfo", "list_all_modes"]
```

- [ ] **Step 4.4: Run tests to confirm they pass**

Run: `uv run pytest tests/test_modes_cmd.py -x -v`
Expected: 8 passed.

- [ ] **Step 4.5: Commit**

```bash
git add src/thoth/modes_cmd.py tests/test_modes_cmd.py
git commit -m "feat(modes): add ModeInfo + list_all_modes enumeration helper"
```

---

## Task 5: Table rendering + `modes_command("list", [])` dispatch

**Files:**
- Modify: `src/thoth/modes_cmd.py`
- Modify: `tests/test_modes_cmd.py` (append)

- [ ] **Step 5.1: Append table-rendering tests**

Append to `tests/test_modes_cmd.py`:

```python
from thoth.modes_cmd import modes_command


def test_modes_command_list_default_prints_table(
    isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = modes_command("list", [])
    out = capsys.readouterr().out
    assert rc == 0
    # Column headers present
    for header in ("Mode", "Source", "Provider", "Model", "Kind", "Description"):
        assert header in out
    # Known mode rows present
    assert "default" in out
    assert "deep_research" in out


def test_modes_command_default_op_is_list(
    isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # `thoth modes` with no op should behave like `thoth modes list`.
    rc = modes_command(None, [])
    out = capsys.readouterr().out
    assert rc == 0
    assert "default" in out


def test_modes_command_unknown_op_returns_2(
    isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = modes_command("bogus", [])
    assert rc == 2


def test_modes_command_list_sort_order(
    isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Sort: source -> kind -> provider -> model -> name.
    # builtin + immediate modes (default, clarification, thinking) must appear
    # before builtin + background modes (deep_research, exploration, etc.).
    rc = modes_command("list", [])
    out = capsys.readouterr().out
    assert rc == 0
    # default (immediate) line number < deep_research (background) line number
    lines = out.splitlines()
    default_idx = next(i for i, ln in enumerate(lines) if " default " in ln)
    deep_idx = next(i for i, ln in enumerate(lines) if " deep_research " in ln)
    assert default_idx < deep_idx
```

- [ ] **Step 5.2: Run new tests to confirm they fail**

Run: `uv run pytest tests/test_modes_cmd.py -x -v -k "modes_command"`
Expected: `ImportError: cannot import name 'modes_command'`.

- [ ] **Step 5.3: Extend `src/thoth/modes_cmd.py` with table renderer + dispatch**

Append to `src/thoth/modes_cmd.py` (after `list_all_modes`):

```python
from rich.console import Console
from rich.table import Table

_SOURCE_ORDER = {"builtin": 0, "overridden": 1, "user": 2}
_KIND_ORDER = {"immediate": 0, "background": 1, "unknown": 2}

_console = Console()


def _sort_key(m: ModeInfo) -> tuple[int, int, str, str, str]:
    return (
        _SOURCE_ORDER.get(m.source, 99),
        _KIND_ORDER.get(m.kind, 99),
        ",".join(m.providers),
        m.model or "",
        m.name,
    )


def _truncate(text: str, limit: int = 60) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _render_table(infos: list[ModeInfo]) -> None:
    table = Table(show_header=True, header_style="bold")
    table.add_column("Mode")
    table.add_column("Source")
    table.add_column("Provider")
    table.add_column("Model")
    table.add_column("Kind")
    table.add_column("Description")

    for m in sorted(infos, key=_sort_key):
        table.add_row(
            f" {m.name} ",
            m.source,
            ",".join(m.providers) if m.providers else "-",
            m.model or "-",
            m.kind,
            _truncate(m.description),
        )
    _console.print(table)


def _op_list(args: list[str]) -> int:
    cm = ConfigManager()
    cm.load_all_layers({})
    infos = list_all_modes(cm)
    _render_table(infos)
    return 0


def modes_command(op: str | None, args: list[str]) -> int:
    """Dispatch `thoth modes <op>`. Returns a process exit code."""
    if op is None:
        return _op_list(args)
    ops = {"list": _op_list}
    if op not in ops:
        _console.print(f"[red]Error:[/red] unknown modes op: {op}")
        return 2
    return ops[op](args)


__all__ = ["ModeInfo", "list_all_modes", "modes_command"]
```

(Replace the previous `__all__` line at the bottom.)

- [ ] **Step 5.4: Run tests to confirm they pass**

Run: `uv run pytest tests/test_modes_cmd.py -x -v`
Expected: all tests pass (prior 8 + 4 new = 12).

- [ ] **Step 5.5: Commit**

```bash
git add src/thoth/modes_cmd.py tests/test_modes_cmd.py
git commit -m "feat(modes): render modes as a sorted Rich table via modes_command"
```

---

## Task 6: JSON output + secret masking

**Files:**
- Modify: `src/thoth/modes_cmd.py`
- Modify: `tests/test_modes_cmd.py` (append)

- [ ] **Step 6.1: Append tests for `--json`, `--show-secrets`, and masking**

Append to `tests/test_modes_cmd.py`:

```python
import json


def test_modes_list_json_shape(
    isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = modes_command("list", ["--json"])
    out = capsys.readouterr().out
    assert rc == 0
    data = json.loads(out)
    assert isinstance(data, dict)
    assert data["schema_version"] == "1"
    assert isinstance(data["modes"], list)
    default = next(m for m in data["modes"] if m["name"] == "default")
    assert default["kind"] == "immediate"
    assert default["providers"] == ["openai"]
    assert "description" in default


def test_modes_list_masks_api_key_inside_mode(
    isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = Path(isolated_thoth_home) / "config" / "thoth" / "config.toml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(
        'version = "2.0"\n'
        "[modes.secret_mode]\n"
        'provider = "openai"\n'
        'model = "o3"\n'
        'api_key = "sk-verysecretverysecret1234"\n'
    )
    rc = modes_command("list", ["--json"])
    out = capsys.readouterr().out
    assert rc == 0
    data = json.loads(out)
    secret = next(m for m in data["modes"] if m["name"] == "secret_mode")
    # Secret value masked: only last 4 chars retained.
    assert "sk-verysecretverysecret1234" not in out
    assert secret["raw"]["api_key"].startswith("****")
    assert secret["raw"]["api_key"].endswith("1234")


def test_modes_list_show_secrets_unmasks(
    isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = Path(isolated_thoth_home) / "config" / "thoth" / "config.toml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(
        'version = "2.0"\n'
        "[modes.secret_mode]\n"
        'provider = "openai"\n'
        'model = "o3"\n'
        'api_key = "sk-verysecretverysecret1234"\n'
    )
    rc = modes_command("list", ["--json", "--show-secrets"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "sk-verysecretverysecret1234" in out
```

- [ ] **Step 6.2: Run tests to confirm they fail**

Run: `uv run pytest tests/test_modes_cmd.py -x -v -k "json or mask or show_secrets"`
Expected: `KeyError` / assertion failures — `--json` not implemented yet.

- [ ] **Step 6.3: Extend `modes_cmd.py` with JSON + masking**

In `src/thoth/modes_cmd.py`, replace the `_op_list` function and add helpers above it:

```python
import json
from dataclasses import asdict

_SECRET_KEY_SUFFIX = "api_key"


def _is_secret_key(key: str) -> bool:
    return key.split(".")[-1] == _SECRET_KEY_SUFFIX


def _mask_secret(value: Any) -> Any:
    if not isinstance(value, str) or not value:
        return value
    if value.startswith("${") and value.endswith("}"):
        return value
    tail = value[-4:] if len(value) >= 4 else value
    return f"****{tail}"


def _mask_tree(data: Any, prefix: str = "") -> Any:
    if isinstance(data, dict):
        return {
            k: _mask_tree(v, f"{prefix}.{k}" if prefix else k) for k, v in data.items()
        }
    if isinstance(data, list):
        return [_mask_tree(v, prefix) for v in data]
    if prefix and _is_secret_key(prefix):
        return _mask_secret(data)
    return data


def _info_to_dict(m: ModeInfo, show_secrets: bool) -> dict[str, Any]:
    d = asdict(m)
    if not show_secrets:
        d["raw"] = _mask_tree(d["raw"])
        d["overrides"] = _mask_tree(d["overrides"])
    return d


def _parse_list_flags(args: list[str]) -> tuple[bool, bool]:
    as_json = "--json" in args
    show_secrets = "--show-secrets" in args
    return as_json, show_secrets


def _op_list(args: list[str]) -> int:
    as_json, show_secrets = _parse_list_flags(args)
    cm = ConfigManager()
    cm.load_all_layers({})
    infos = sorted(list_all_modes(cm), key=_sort_key)

    if as_json:
        payload = {
            "schema_version": "1",
            "modes": [_info_to_dict(m, show_secrets) for m in infos],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    # Table view — mask raw in-place is irrelevant (table doesn't show api_key),
    # but mask overrides values before rendering.
    _render_table(infos)
    return 0
```

- [ ] **Step 6.4: Run the full `test_modes_cmd.py` suite**

Run: `uv run pytest tests/test_modes_cmd.py -x -v`
Expected: all pass.

- [ ] **Step 6.5: Commit**

```bash
git add src/thoth/modes_cmd.py tests/test_modes_cmd.py
git commit -m "feat(modes): add --json output with schema_version and secret masking"
```

---

## Task 7: `--source` filter + `list` arg validation

**Files:**
- Modify: `src/thoth/modes_cmd.py`
- Modify: `tests/test_modes_cmd.py` (append)

- [ ] **Step 7.1: Append filter tests**

Append to `tests/test_modes_cmd.py`:

```python
def test_modes_list_source_filter_user(
    isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = Path(isolated_thoth_home) / "config" / "thoth" / "config.toml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(
        'version = "2.0"\n'
        "[modes.my_brief]\n"
        'provider = "openai"\n'
        'model = "gpt-4o-mini"\n'
    )
    rc = modes_command("list", ["--json", "--source", "user"])
    out = capsys.readouterr().out
    assert rc == 0
    data = json.loads(out)
    names = {m["name"] for m in data["modes"]}
    assert names == {"my_brief"}


def test_modes_list_source_filter_overridden(
    isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = Path(isolated_thoth_home) / "config" / "thoth" / "config.toml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(
        'version = "2.0"\n'
        "[modes.deep_research]\n"
        "parallel = false\n"
    )
    rc = modes_command("list", ["--json", "--source", "overridden"])
    out = capsys.readouterr().out
    assert rc == 0
    data = json.loads(out)
    assert [m["name"] for m in data["modes"]] == ["deep_research"]


def test_modes_list_invalid_source_returns_2(
    isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = modes_command("list", ["--source", "bogus"])
    assert rc == 2
```

- [ ] **Step 7.2: Run to confirm failures**

Run: `uv run pytest tests/test_modes_cmd.py -x -v -k "source_filter or invalid_source"`
Expected: FAIL — `--source` ignored.

- [ ] **Step 7.3: Extend flag parsing and filtering**

In `src/thoth/modes_cmd.py`, replace `_parse_list_flags` and `_op_list`:

```python
_VALID_SOURCES = ("builtin", "user", "overridden", "all")


def _parse_list_flags(args: list[str]) -> tuple[bool, bool, str, int]:
    """Return (as_json, show_secrets, source_filter, error_rc). rc=0 means ok."""
    as_json = False
    show_secrets = False
    source = "all"
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--json":
            as_json = True
            i += 1
        elif a == "--show-secrets":
            show_secrets = True
            i += 1
        elif a == "--source":
            if i + 1 >= len(args):
                _console.print("[red]Error:[/red] --source requires a value")
                return as_json, show_secrets, source, 2
            source = args[i + 1]
            if source not in _VALID_SOURCES:
                _console.print(
                    f"[red]Error:[/red] --source must be one of {', '.join(_VALID_SOURCES)}"
                )
                return as_json, show_secrets, source, 2
            i += 2
        else:
            _console.print(f"[red]Error:[/red] unknown arg: {a}")
            return as_json, show_secrets, source, 2
    return as_json, show_secrets, source, 0


def _op_list(args: list[str]) -> int:
    as_json, show_secrets, source, rc = _parse_list_flags(args)
    if rc != 0:
        return rc

    cm = ConfigManager()
    cm.load_all_layers({})
    infos = list_all_modes(cm)
    if source != "all":
        infos = [m for m in infos if m.source == source]
    infos = sorted(infos, key=_sort_key)

    if as_json:
        payload = {
            "schema_version": "1",
            "modes": [_info_to_dict(m, show_secrets) for m in infos],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    _render_table(infos)
    return 0
```

- [ ] **Step 7.4: Run full suite**

Run: `uv run pytest tests/test_modes_cmd.py -x -v`
Expected: all pass.

- [ ] **Step 7.5: Commit**

```bash
git add src/thoth/modes_cmd.py tests/test_modes_cmd.py
git commit -m "feat(modes): add --source filter with validation"
```

---

## Task 8: `--name` detail view + `--full`

**Files:**
- Modify: `src/thoth/modes_cmd.py`
- Modify: `tests/test_modes_cmd.py` (append)

- [ ] **Step 8.1: Append detail-view tests**

Append to `tests/test_modes_cmd.py`:

```python
def test_modes_detail_unknown_name_returns_1(
    isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = modes_command("list", ["--name", "no_such_mode"])
    err = capsys.readouterr().out + capsys.readouterr().err
    assert rc == 1


def test_modes_detail_builtin(
    isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = modes_command("list", ["--name", "default"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Mode: default" in out
    assert "Source: builtin" in out
    assert "Model: o3" in out
    assert "Kind: immediate" in out


def test_modes_detail_overridden_shows_diff(
    isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = Path(isolated_thoth_home) / "config" / "thoth" / "config.toml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(
        'version = "2.0"\n'
        "[modes.deep_research]\n"
        "parallel = false\n"
    )
    rc = modes_command("list", ["--name", "deep_research"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "parallel" in out
    assert "True" in out and "False" in out


def test_modes_detail_truncates_system_prompt_without_full(
    isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = modes_command("list", ["--name", "deep_research"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "use --full" in out


def test_modes_detail_full_dumps_system_prompt(
    isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = modes_command("list", ["--name", "deep_research", "--full"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "comprehensive research with citations" in out
```

- [ ] **Step 8.2: Confirm failures**

Run: `uv run pytest tests/test_modes_cmd.py -x -v -k "detail"`
Expected: FAIL — `--name` not implemented.

- [ ] **Step 8.3: Extend parsing + add detail renderer**

In `src/thoth/modes_cmd.py`, replace `_parse_list_flags` signature and `_op_list`, and add `_render_detail`:

```python
def _parse_list_flags(
    args: list[str],
) -> tuple[bool, bool, str, str | None, bool, int]:
    """Return (as_json, show_secrets, source, name, full, error_rc)."""
    as_json = False
    show_secrets = False
    source = "all"
    name: str | None = None
    full = False
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--json":
            as_json = True
            i += 1
        elif a == "--show-secrets":
            show_secrets = True
            i += 1
        elif a == "--full":
            full = True
            i += 1
        elif a == "--source":
            if i + 1 >= len(args):
                _console.print("[red]Error:[/red] --source requires a value")
                return as_json, show_secrets, source, name, full, 2
            source = args[i + 1]
            if source not in _VALID_SOURCES:
                _console.print(
                    f"[red]Error:[/red] --source must be one of {', '.join(_VALID_SOURCES)}"
                )
                return as_json, show_secrets, source, name, full, 2
            i += 2
        elif a == "--name":
            if i + 1 >= len(args):
                _console.print("[red]Error:[/red] --name requires a value")
                return as_json, show_secrets, source, name, full, 2
            name = args[i + 1]
            i += 2
        else:
            _console.print(f"[red]Error:[/red] unknown arg: {a}")
            return as_json, show_secrets, source, name, full, 2
    return as_json, show_secrets, source, name, full, 0


def _render_detail(m: ModeInfo, full: bool, show_secrets: bool) -> None:
    providers = ",".join(m.providers) if m.providers else "-"
    _console.print(f"Mode: {m.name}")
    _console.print(f"Source: {m.source}")
    _console.print(f"Providers: {providers}")
    _console.print(f"Model: {m.model or '-'}")
    _console.print(f"Kind: {m.kind}")
    if m.description:
        _console.print(f"Description: {m.description}")
    if m.warnings:
        for w in m.warnings:
            _console.print(f"[yellow]Warning:[/yellow] {w}")
    if m.overrides:
        _console.print("Overrides (builtin → effective):")
        rendered = _mask_tree(m.overrides) if not show_secrets else m.overrides
        for key, diff in rendered.items():
            _console.print(
                f"  {key}: {diff['builtin']!r} → {diff['effective']!r}"
            )
    system_prompt = m.raw.get("system_prompt")
    if system_prompt:
        if full:
            _console.print("System prompt:")
            _console.print(system_prompt)
        else:
            preview = _truncate(str(system_prompt), 200)
            _console.print(f"System prompt: {preview} [dim](use --full to see)[/dim]")


def _op_list(args: list[str]) -> int:
    as_json, show_secrets, source, name, full, rc = _parse_list_flags(args)
    if rc != 0:
        return rc

    cm = ConfigManager()
    cm.load_all_layers({})
    infos = list_all_modes(cm)

    if name is not None:
        match = next((m for m in infos if m.name == name), None)
        if match is None:
            _console.print(f"[red]Error:[/red] unknown mode: {name}")
            return 1
        if as_json:
            print(
                json.dumps(
                    {
                        "schema_version": "1",
                        "mode": _info_to_dict(match, show_secrets),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
        else:
            _render_detail(match, full, show_secrets)
        return 0

    if source != "all":
        infos = [m for m in infos if m.source == source]
    infos = sorted(infos, key=_sort_key)

    if as_json:
        payload = {
            "schema_version": "1",
            "modes": [_info_to_dict(m, show_secrets) for m in infos],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    _render_table(infos)
    return 0
```

- [ ] **Step 8.4: Run the suite**

Run: `uv run pytest tests/test_modes_cmd.py -x -v`
Expected: all pass.

- [ ] **Step 8.5: Commit**

```bash
git add src/thoth/modes_cmd.py tests/test_modes_cmd.py
git commit -m "feat(modes): add --name detail view with override diff and --full flag"
```

---

## Task 9: Wire `modes` into the CLI + `thoth help modes`

**Files:**
- Modify: `src/thoth/cli.py:158,223,294`
- Modify: `src/thoth/help.py` (add `show_modes_help`, import `list_all_modes`, update epilog)
- Append: `tests/test_modes_cmd.py`

- [ ] **Step 9.1: Append end-to-end subprocess test**

Append to `tests/test_modes_cmd.py`:

```python
from tests._fixture_helpers import run_thoth


def test_thoth_modes_subprocess_lists_modes(isolated_thoth_home: Path) -> None:
    rc, out, err = run_thoth(["modes"])
    assert rc == 0, f"stderr: {err}"
    assert "default" in out
    assert "deep_research" in out


def test_thoth_help_modes_subprocess(isolated_thoth_home: Path) -> None:
    rc, out, err = run_thoth(["help", "modes"])
    assert rc == 0, f"stderr: {err}"
    assert "thoth modes" in out
    assert "schema_version" in out  # JSON schema snippet in help
```

- [ ] **Step 9.2: Confirm failure**

Run: `uv run pytest tests/test_modes_cmd.py -x -v -k "subprocess"`
Expected: FAIL — `thoth modes` not dispatched, `thoth help modes` unknown.

- [ ] **Step 9.3: Update `src/thoth/cli.py` command list (line 158)**

Find:
```python
    if not (args and args[0] in ["init", "status", "list", "help", "providers", "config"]):
```
Replace with:
```python
    if not (args and args[0] in ["init", "status", "list", "help", "providers", "config", "modes"]):
```

Find (same file, later, line 223):
```python
    if args and args[0] in ["init", "status", "list", "help", "providers", "config"]:
```
Replace with:
```python
    if args and args[0] in ["init", "status", "list", "help", "providers", "config", "modes"]:
```

- [ ] **Step 9.4: Add `modes` dispatch branch in `src/thoth/cli.py`**

In the `elif command == "config":` block (around line 281-293), directly after the `sys.exit(rc)` line that closes the `config` branch, add:

```python
        elif command == "modes":
            from thoth.modes_cmd import modes_command

            op = args[1] if len(args) >= 2 else None
            rest = list(args[2:]) + list(ctx.args)
            rc = modes_command(op, rest)
            sys.exit(rc)
```

- [ ] **Step 9.5: Extend the `help` branch (line 294)**

In the `elif command == "help":` block, inside the `if len(args) > 1:` ladder, add after `elif help_command == "config":`:

```python
                elif help_command == "modes":
                    show_modes_help()
```

Then update the "Unknown command" error list to include "modes":

Find:
```python
                    console.print(
                        "[yellow]Available commands:[/yellow] init, status, list, providers, config"
                    )
```
Replace with:
```python
                    console.print(
                        "[yellow]Available commands:[/yellow] init, status, list, providers, config, modes"
                    )
```

Add `show_modes_help` to the imports at the top of `src/thoth/cli.py`. Find the existing `from thoth.help import` line and add `show_modes_help` to the list.

- [ ] **Step 9.6: Add `show_modes_help` + epilog pointer in `src/thoth/help.py`**

In `src/thoth/help.py`, append the following function before the `__all__` block:

```python
def show_modes_help():
    """Show detailed help for the modes command."""
    console.print("\n[bold]thoth modes[/bold] - List research modes with provider, model, and kind")
    console.print("\n[bold]Description:[/bold]")
    console.print("  Shows every research mode Thoth knows about: built-in modes,")
    console.print("  user-defined modes from `[modes.*]` in your config TOML, and")
    console.print("  modes that override a built-in.")
    console.print("\n[bold]Usage:[/bold]")
    console.print("  thoth modes [list] [OPTIONS]")
    console.print("\n[bold]Options:[/bold]")
    console.print("  --json                    Emit machine-readable JSON")
    console.print("  --source builtin|user|overridden|all   Filter by origin")
    console.print("  --name <mode>             Show detail view for one mode")
    console.print("  --full                    With --name, dump full system_prompt")
    console.print("  --show-secrets            Do not mask api_key values")
    console.print("\n[bold]Sort order:[/bold]")
    console.print("  source → kind → provider → model → name")
    console.print("\n[bold]JSON schema (schema_version: \"1\"):[/bold]")
    console.print("  { schema_version, modes: [")
    console.print("    { name, source, providers, model, kind, description,")
    console.print("      overrides, warnings, raw } ] }")
    console.print("\n[bold]Kind vs. --async flag:[/bold]")
    console.print("  The Kind column describes the mode's default submit style.")
    console.print("  The per-invocation `thoth --async` flag is orthogonal — it")
    console.print("  controls whether the CLI waits for results, not how the job")
    console.print("  is submitted.")
    console.print("\n[bold]Examples:[/bold]")
    console.print("  $ thoth modes")
    console.print("  $ thoth modes --json | jq '.modes[] | select(.kind == \"background\") | .name'")
    console.print("  $ thoth modes --name deep_research --full")
```

Add `show_modes_help` to the `__all__` tuple at the bottom of the file.

Now update the general-help output (line 270-275) to stop inlining descriptions and point at the new command. Find:

```python
    console.print("\n[bold]Research Modes:[/bold]")
    for mode_name, mode_config in BUILTIN_MODES.items():
        desc = str(mode_config.get("description", "No description"))
        if len(desc) > 60:
            desc = desc[:57] + "..."
        console.print(f"  {mode_name:<15} {desc}")
```

Replace with:

```python
    console.print("\n[bold]Research Modes:[/bold]")
    console.print(f"  {', '.join(BUILTIN_MODES.keys())}")
    console.print("  Run [bold]thoth modes[/bold] for provider, model, and kind per mode.")
```

Do the same replacement in `build_epilog()` (lines 70-76). Find:
```python
    lines.append("Research Modes:")
    for mode_name, mode_config in BUILTIN_MODES.items():
        desc = str(mode_config.get("description", "No description"))
        if len(desc) > 60:
            desc = desc[:57] + "..."
        lines.append(f"  {mode_name:<15} {desc}")
    lines.append("")
```
Replace with:
```python
    lines.append("Research Modes:")
    lines.append(f"  {', '.join(BUILTIN_MODES.keys())}")
    lines.append("  Run `thoth modes` for provider, model, and kind per mode.")
    lines.append("")
```

- [ ] **Step 9.7: Run subprocess tests**

Run: `uv run pytest tests/test_modes_cmd.py -x -v -k "subprocess"`
Expected: 2 passed.

- [ ] **Step 9.8: Run full `test_modes_cmd.py`**

Run: `uv run pytest tests/test_modes_cmd.py -x -v`
Expected: all pass.

- [ ] **Step 9.9: Commit**

```bash
git add src/thoth/cli.py src/thoth/help.py tests/test_modes_cmd.py
git commit -m "feat(cli): wire `thoth modes` + `thoth help modes` dispatch"
```

---

## Task 10: Route `interactive.py` and `help.py` through `list_all_modes`

**Files:**
- Modify: `src/thoth/interactive.py:27,113-146,677-685,777-789`
- Modify: `src/thoth/help.py` — `BUILTIN_MODES` import stays (for the names-only teaser) but remove the per-mode description iteration.

**Design decision:** `interactive.py` currently treats `BUILTIN_MODES` as both the listing source AND the validation source (for `/mode <name>`). We keep validation against `BUILTIN_MODES` (fast membership test), but switch the listing to `list_all_modes()` so the description/kind match the `thoth modes` table.

- [ ] **Step 10.1: Add a coverage test**

Append to `tests/test_modes_cmd.py`:

```python
def test_help_epilog_lists_mode_names(
    isolated_thoth_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc, out, err = run_thoth(["--help"])
    assert rc == 0, f"stderr: {err}"
    assert "thoth modes" in out
    # Teaser still shows at least one mode name.
    assert "default" in out
```

- [ ] **Step 10.2: Confirm pass (help already updated in Task 9)**

Run: `uv run pytest tests/test_modes_cmd.py -x -v -k "help_epilog"`
Expected: PASS.

- [ ] **Step 10.3: Update `interactive.py` `set_mode` listing**

In `src/thoth/interactive.py`, replace the body of `set_mode` (lines 113-146) — keep validation, switch listing:

Find:
```python
    def set_mode(self, args: str) -> str:
        """Set research mode"""
        if not args:
            self.console.print("[cyan]Available modes:[/cyan]")
            modes = list(BUILTIN_MODES.keys())
            for i, mode_name in enumerate(modes, 1):
                mode_config = BUILTIN_MODES[mode_name]
                desc = str(mode_config.get("description", "No description"))[:60]
                current = " [green]← current[/green]" if mode_name == self.current_mode else ""
                self.console.print(f"  {i}. {mode_name:<15} - {desc}{current}")
            self.console.print("\n[dim]Usage: /mode <name> or /mode <number>[/dim]")
            self.console.print(f"[dim]Current mode: {self.current_mode}[/dim]")
```

Replace with:
```python
    def set_mode(self, args: str) -> str:
        """Set research mode"""
        from thoth.modes_cmd import list_all_modes

        if not args:
            self.console.print("[cyan]Available modes:[/cyan]")
            cm = get_config()
            infos = list_all_modes(cm)
            modes = [m.name for m in infos]
            for i, info in enumerate(infos, 1):
                desc = (info.description or "")[:60]
                current = (
                    " [green]← current[/green]" if info.name == self.current_mode else ""
                )
                self.console.print(
                    f"  {i}. {info.name:<15} [{info.kind:<10}] {desc}{current}"
                )
            self.console.print("\n[dim]Usage: /mode <name> or /mode <number>[/dim]")
            self.console.print(f"[dim]Current mode: {self.current_mode}[/dim]")
```

The numeric-selection branch (line 127 onward) uses `modes = list(BUILTIN_MODES.keys())`; keep that line but move it inside the numeric branch for clarity:

Find:
```python
            if arg.isdigit():
                modes = list(BUILTIN_MODES.keys())
```
Leave unchanged. (Still valid — `BUILTIN_MODES` is the canonical built-in set for interactive selection.)

Find the name-validation branch (line 139):
```python
                if mode in BUILTIN_MODES:
```
Leave unchanged — validating against built-ins only is intentional for now (user-defined modes are not supported in interactive `/mode` — tracked as future work, out of scope for P11).

- [ ] **Step 10.4: Update `_show_mode_selection` (line 777)**

Find:
```python
    def _show_mode_selection(self):
        """Show available modes for selection"""

        def print_modes():
            print("\nAvailable modes:")
            for i, (name, config) in enumerate(BUILTIN_MODES.items(), 1):
                desc = str(config.get("description", "No description"))[:60]
                current = " ← current" if name == self.slash_registry.current_mode else ""
                print(f"  {i}. {name:15} - {desc}{current}")
            print("\nType: /mode <name> to select a mode")
            print()
```

Replace with:
```python
    def _show_mode_selection(self):
        """Show available modes for selection"""
        from thoth.modes_cmd import list_all_modes

        def print_modes():
            cm = get_config()
            infos = list_all_modes(cm)
            print("\nAvailable modes:")
            for i, info in enumerate(infos, 1):
                desc = (info.description or "")[:60]
                current = " ← current" if info.name == self.slash_registry.current_mode else ""
                print(f"  {i}. {info.name:15} [{info.kind:<10}] {desc}{current}")
            print("\nType: /mode <name> to select a mode")
            print()
```

Check `from thoth.config import ... get_config ...` is already imported at the top of `interactive.py` (line 27). If not, add it.

Run: `grep -n "from thoth.config import" src/thoth/interactive.py`
Expected: the line should include `get_config`; if not, add it.

- [ ] **Step 10.5: Remove unused `BUILTIN_MODES` iteration imports (optional cleanup)**

Leave `BUILTIN_MODES` imported in `interactive.py` — still used for `/mode <name>` validation. Leave `BUILTIN_MODES` imported in `help.py` — still used for the names teaser.

No action needed; just verify with:
```bash
grep -n "BUILTIN_MODES" src/thoth/interactive.py src/thoth/help.py
```
Expected: each file has <= 3 remaining references (validation / teaser only).

- [ ] **Step 10.6: Run the interactive-mode test suite**

Run: `uv run pytest tests/test_interactive_mode.py -x -v`
Expected: same pass count as before (no regression).

- [ ] **Step 10.7: Commit**

```bash
git add src/thoth/interactive.py tests/test_modes_cmd.py
git commit -m "refactor(interactive): route /mode listing through list_all_modes"
```

---

## Task 11: Final verification

- [ ] **Step 11.1: Lint + typecheck**

Run: `just check`
Expected: no errors.

If ruff complains about import ordering in `modes_cmd.py`, run `just fix` and re-run `just check`.

- [ ] **Step 11.2: Full pytest suite**

Run: `uv run pytest tests/ -x`
Expected: all green.

- [ ] **Step 11.3: thoth_test integration suite**

Run: `./thoth_test -r --provider mock --skip-interactive 2>&1 | tail -40`
Expected: same baseline as pre-change (no regressions; new command does not appear in thoth_test scope).

- [ ] **Step 11.4: Manual smoke checks**

Run each and eyeball the output:

```bash
./thoth modes
./thoth modes --json | jq '.modes[] | select(.kind == "background") | .name'
./thoth modes --source builtin
./thoth modes --name thinking
./thoth modes --name deep_research --full
./thoth help modes
./thoth --help | tail -20
```

Expected:
- Table is sorted by source → kind → provider → model → name.
- `thinking` shows `Kind: immediate` and `Model: o3`.
- `--help` now shows `Run \`thoth modes\` for provider, model, and kind per mode.` instead of per-mode descriptions.
- `--json` validates against the documented schema (`schema_version: "1"`).

- [ ] **Step 11.5: Final commit (if anything touched during verification)**

If `just fix` modified files during Step 11.1:
```bash
git add -A
git commit -m "chore(p11): apply ruff/ty auto-fixes"
```

- [ ] **Step 11.6: Mark P11 complete in `PROJECTS.md`**

Flip `## [ ] Project P11` to `## [x] Project P11` and each `- [ ]` line to `- [x]`. Commit:

```bash
git add PROJECTS.md
git commit -m "chore(projects): mark P11 modes-discovery command complete"
```

---

## Self-Review Checklist

- **Spec coverage:** Every task in the PROJECTS.md P11 entry (T00 – T06 and TS00 – TS06) maps to a Task in this plan. `is_background_mode` (Task 1), openai refactor (Task 2), `thinking` fix (Task 3), `ModeInfo` + `list_all_modes` (Task 4), table rendering (Task 5), JSON + masking (Task 6), `--source` filter (Task 7), `--name` detail view (Task 8), CLI/help wiring (Task 9), interactive routing (Task 10), final verification (Task 11). ✔
- **Placeholders:** No TBDs, no "implement later", every code block is complete. ✔
- **Type/name consistency:** `list_all_modes(cm)`, `ModeInfo`, `modes_command(op, args)`, `show_modes_help()` used consistently across tasks. `Source` literal `"builtin" | "user" | "overridden"` matches `_SOURCE_ORDER` keys. `Kind` literal `"immediate" | "background" | "unknown"` matches `_KIND_ORDER` keys. ✔
- **Scope:** No scope creep — interactive `/mode <name>` for user-defined modes is explicitly out of scope.
