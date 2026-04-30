# P12: CLI Mode Editing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the mutation half of `thoth modes` — `add`, `set`, `unset`, `remove`, `rename`, `copy` — so users can author and edit research-mode definitions from the CLI instead of hand-editing TOML, with full `--project` / `--config PATH` / `--profile X` targeting parity with `thoth config set` and `thoth config profiles ...`.

**Architecture:** Mirror `thoth config profiles` (P21b, shipped) where applicable. Add six mode-aware primitives to `ConfigDocument` (parallel to its existing `ensure_profile` / `remove_profile` / `set_profile_value` / `unset_profile_value` quartet), plus `rename_mode` and `copy_mode`. Add `_op_add` / `_op_set` / `_op_unset` / `_op_remove` / `_op_rename` / `_op_copy` to `modes_cmd.py`, sharing one targeting-flag parser. Wire each op as a Click subcommand in `cli_subcommands/modes.py`. Help epilog updates land in `help.py`. Effective-config writes go through `ConfigDocument` only — no direct tomlkit in command code.

**Tech Stack:** Python 3.11+, Click, tomlkit (round-trip preserves comments/formatting), pytest with `isolated_thoth_home` fixture, `subprocess` for CLI integration tests, `ConfigWriteContext.resolve()` for write-target resolution.

**Source of truth:** The P12 section of `/Users/stevemorin/c/thoth/PROJECTS.md` (lines ~1240–1462). If this plan and PROJECTS.md disagree, PROJECTS.md wins. The plan implements the spec; the spec defines the contract.

**Supersedes:** `docs/superpowers/plans/2026-04-30-p12-cli-mode-editing.md` (1438 lines, written 2026-04-30 earlier in the day, stale on five points: missing `remove NAME`, missing `--override` flag, missing `--from-profile X` flag for `copy`, wrong `add` idempotency rule, missing the cross-cutting layering test). That plan should be marked superseded after this one is reviewed; do not consult it during implementation.

---

## File Structure

| Action | Path | Responsibility |
|---|---|---|
| Modify | `src/thoth/config_document.py` | Add `ensure_mode`, `remove_mode`, `set_mode_value`, `unset_mode_value`, `rename_mode`, `copy_mode`. Each accepts an optional `profile: str \| None` parameter — when set, the target sub-tree becomes `profiles.<X>.modes.<NAME>` instead of `modes.<NAME>`. Pure file-mutation; no resolver logic. |
| Modify | `src/thoth/modes_cmd.py` | Add `get_modes_<op>_data` data functions and `_op_<op>` CLI wrappers for `add` / `set` / `unset` / `remove` / `rename` / `copy`. Add a shared `_parse_target_flags` helper for `--project` / `--config` / `--profile` / `--from-profile`. Wire ops into `modes_command` dispatch. |
| Modify | `src/thoth/cli_subcommands/modes.py` | Register six new Click leaves: `add`, `set`, `unset`, `remove`, `rename`, `copy`. Each uses `_PASSTHROUGH_CONTEXT` and forwards to `modes_command`. Define `_MODES_MUTATOR_HONOR = frozenset({"config_path", "profile"})` so root `--profile` IS honored on mutators (overlay-tier writes; this is the deliberate divergence from `_MUTATOR_HONOR` in `cli_subcommands/config.py:347`). |
| Modify | `src/thoth/help.py` | Extend the modes-group `format_epilog` (around line 161) with examples for each new op covering `--project`, `--config PATH`, `--profile X`, `--override`, and `--from-profile X`. |
| Create | `tests/test_modes_mutations.py` | Unit tests calling `modes_command` and the `get_modes_<op>_data` functions directly. Covers TS01–TS06 functional cases. Uses `isolated_thoth_home` autouse-style fixture. |
| Create | `tests/test_modes_cli_integration.py` | Subprocess-level CLI integration tests via `_fixture_helpers.run_thoth`. Covers TS07c subprocess regression. |
| Create | `tests/test_config_document_modes.py` | Pure unit tests for `ConfigDocument.ensure_mode` / `set_mode_value` / `unset_mode_value` / `remove_mode` / `rename_mode` / `copy_mode`. No `ConfigManager` involvement. |
| Modify | `PROJECTS.md` | Flip P12 trunk-row glyph `[ ]` → `[~]` at start of work; tick TS/T rows as each lands; flip `[~]` → `[x]` at finish. |

**Decomposition rationale:** `modes_cmd.py` (today: 379 lines, only `_op_list`) will roughly double — that's acceptable, the file's responsibility is single (`thoth modes` CLI surface). Don't preemptively split. `ConfigDocument` already has the same pattern for profiles; mode helpers mirror it. Tests split across three files because the layers are independent: `ConfigDocument`-level tests don't need `ConfigManager` setup; CLI-integration tests need subprocess plumbing; functional tests sit in the middle.

---

## Pre-flight (do this before Task 1)

- [ ] **P0.1: Create a worktree for the work**

```bash
cd /Users/stevemorin/c/thoth
git worktree add /Users/stevemorin/c/thoth-worktrees/p12-modes-editing -b p12-modes-editing main
cd /Users/stevemorin/c/thoth-worktrees/p12-modes-editing
```

Per the user-memory note `feedback_worktrees.md`, thoth worktrees go in `/Users/stevemorin/c/thoth-worktrees/<branch>` (sibling to the repo, NOT `.worktrees/`).

- [ ] **P0.2: Verify the gate is green before starting**

```bash
just check && uv run pytest -q && ./thoth_test -r --skip-interactive -q
```

Expected: all green. If anything is red, stop and fix on `main` first; do not start P12 on a red baseline.

- [ ] **P0.3: Flip P12 to in-progress in PROJECTS.md**

Edit `PROJECTS.md` line 1241: change `## [ ] Project P12:` → `## [~] Project P12:`. Commit:

```bash
git add PROJECTS.md
git commit -m "chore(p12): start P12 — flip trunk glyph [ ] to [~]"
```

---

## Task 1: Shared targeting-flag parser + JSON envelope constants

**Files:**
- Modify: `src/thoth/modes_cmd.py` (add `_parse_target_flags` helper near the top, `SCHEMA_VERSION` constant, `_TargetFlags` dataclass)
- Test: `tests/test_modes_mutations.py` (create)

This task lays the cross-cutting infrastructure used by all six commands. Doing it first so every later task can call `_parse_target_flags(args)` and emit JSON via the shared `SCHEMA_VERSION`.

- [ ] **Step 1.1: Write the failing test for `_parse_target_flags`**

Create `tests/test_modes_mutations.py`:

```python
"""Tests for thoth modes mutation commands (P12)."""

from __future__ import annotations

from pathlib import Path

import pytest


def test_parse_target_flags_defaults() -> None:
    from thoth.modes_cmd import _parse_target_flags

    flags, remaining, rc = _parse_target_flags([])
    assert rc == 0
    assert flags.project is False
    assert flags.config_path is None
    assert flags.profile is None
    assert flags.from_profile is None
    assert flags.as_json is False
    assert flags.force_string is False
    assert flags.override is False
    assert remaining == []


def test_parse_target_flags_each_flag() -> None:
    from thoth.modes_cmd import _parse_target_flags

    flags, remaining, rc = _parse_target_flags(
        [
            "alpha",
            "--project",
            "--config",
            "/tmp/x.toml",
            "--profile",
            "dev",
            "--from-profile",
            "ci",
            "--json",
            "--string",
            "--override",
            "beta",
            "--model",
            "gpt-4o-mini",
        ]
    )
    assert rc == 0
    assert flags.project is True
    assert flags.config_path == "/tmp/x.toml"
    assert flags.profile == "dev"
    assert flags.from_profile == "ci"
    assert flags.as_json is True
    assert flags.force_string is True
    assert flags.override is True
    assert remaining == ["alpha", "beta", "--model", "gpt-4o-mini"]


def test_parse_target_flags_project_config_conflict() -> None:
    from thoth.modes_cmd import _parse_target_flags

    flags, remaining, rc = _parse_target_flags(
        ["--project", "--config", "/tmp/x.toml"]
    )
    assert rc == 2
    # rc=2 signals USAGE_ERROR; the caller is responsible for the error
    # message (so JSON callers can emit a structured error envelope).


def test_parse_target_flags_override_without_profile_rejected() -> None:
    from thoth.modes_cmd import _parse_target_flags

    flags, remaining, rc = _parse_target_flags(["--override"])
    assert rc == 2
    # --override is overlay-only per P12 design; without --profile X it's a
    # USAGE_ERROR.
```

- [ ] **Step 1.2: Run tests to verify they fail**

```bash
uv run pytest tests/test_modes_mutations.py -x -v
```

Expected: 4 FAIL with `ImportError: cannot import name '_parse_target_flags' from 'thoth.modes_cmd'`.

- [ ] **Step 1.3: Implement `_parse_target_flags`, `_TargetFlags`, and `SCHEMA_VERSION` in `modes_cmd.py`**

Add near the top of `src/thoth/modes_cmd.py` (after the existing imports, before `Source = Literal[...]`):

```python
from dataclasses import dataclass

SCHEMA_VERSION = "1"


@dataclass
class _TargetFlags:
    """Resolved targeting flags shared by every modes mutator.

    `project` and `config_path` form the file axis (mutually exclusive).
    `profile` selects the destination tier (`[profiles.<X>.modes.<NAME>]`
    when set, `[modes.<NAME>]` otherwise). `from_profile` is the SRC-tier
    selector for `copy` only — every other op rejects it as USAGE_ERROR.
    `override` is the builtin-shadow opt-in; valid only with `profile`.
    """

    project: bool = False
    config_path: str | None = None
    profile: str | None = None
    from_profile: str | None = None
    as_json: bool = False
    force_string: bool = False
    override: bool = False


def _parse_target_flags(
    args: list[str],
) -> tuple[_TargetFlags, list[str], int]:
    """Pull targeting / output flags out of `args`. Returns (flags, remaining, rc).

    rc == 0 → ok; rc == 2 → USAGE_ERROR (caller emits the message).
    Validates `--project` ⊥ `--config PATH`, `--override` requires `--profile X`.
    Does NOT validate that an op accepts `--from-profile` — that's per-op.
    """
    flags = _TargetFlags()
    remaining: list[str] = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--project":
            flags.project = True
            i += 1
        elif a == "--config":
            if i + 1 >= len(args):
                return flags, remaining, 2
            flags.config_path = args[i + 1]
            i += 2
        elif a == "--profile":
            if i + 1 >= len(args):
                return flags, remaining, 2
            flags.profile = args[i + 1]
            i += 2
        elif a == "--from-profile":
            if i + 1 >= len(args):
                return flags, remaining, 2
            flags.from_profile = args[i + 1]
            i += 2
        elif a == "--json":
            flags.as_json = True
            i += 1
        elif a == "--string":
            flags.force_string = True
            i += 1
        elif a == "--override":
            flags.override = True
            i += 1
        else:
            remaining.append(a)
            i += 1

    if flags.project and flags.config_path is not None:
        return flags, remaining, 2
    if flags.override and flags.profile is None:
        return flags, remaining, 2

    return flags, remaining, 0
```

- [ ] **Step 1.4: Run tests to verify they pass**

```bash
uv run pytest tests/test_modes_mutations.py -x -v
```

Expected: 4 PASS.

- [ ] **Step 1.5: Commit**

```bash
git add src/thoth/modes_cmd.py tests/test_modes_mutations.py
git commit -m "feat(p12): add _parse_target_flags + SCHEMA_VERSION (T1 infra)"
```

---

## Task 2: `ConfigDocument` mode primitives (TDD)

**Files:**
- Modify: `src/thoth/config_document.py:84` — insert mode primitives after the existing `unset_default_profile_if` method, before the `_table_at` helper at line 85
- Test: `tests/test_config_document_modes.py` (create)

Six new methods, mirroring the `*_profile` quartet plus `rename_mode` and `copy_mode`. Each accepts `profile: str | None = None` to switch between `[modes.<NAME>]` and `[profiles.<X>.modes.<NAME>]`.

The whole task is one TDD cycle per method (six cycles). Each cycle is the same five-step pattern.

### 2A: `ensure_mode`

- [ ] **Step 2A.1: Write the failing test**

Create `tests/test_config_document_modes.py`:

```python
"""Pure unit tests for ConfigDocument mode primitives (P12 Task 2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from thoth.config_document import ConfigDocument


def _doc(path: Path) -> ConfigDocument:
    return ConfigDocument.load(path)


def test_ensure_mode_creates_table(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    assert doc.ensure_mode("brief") is True
    doc.save()
    assert "[modes.brief]" in p.read_text()


def test_ensure_mode_idempotent(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.ensure_mode("brief")
    assert doc.ensure_mode("brief") is False  # second call is no-op


def test_ensure_mode_with_profile(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    assert doc.ensure_mode("cheap", profile="dev") is True
    doc.save()
    assert "[profiles.dev.modes.cheap]" in p.read_text()
```

- [ ] **Step 2A.2: Run tests to verify they fail**

```bash
uv run pytest tests/test_config_document_modes.py::test_ensure_mode_creates_table -x -v
```

Expected: FAIL with `AttributeError: 'ConfigDocument' object has no attribute 'ensure_mode'`.

- [ ] **Step 2A.3: Implement `ensure_mode` in `src/thoth/config_document.py`**

Insert after line 83 (`unset_default_profile_if`), before `_table_at`:

```python
    # ------------------------------------------------------------------
    # Mode primitives (P12) — base tier `[modes.<NAME>]` or overlay
    # tier `[profiles.<X>.modes.<NAME>]` when `profile` is set.
    # ------------------------------------------------------------------

    def _mode_segments(self, name: str, profile: str | None) -> tuple[str, ...]:
        if profile is not None:
            return ("profiles", profile, "modes", name)
        return ("modes", name)

    def ensure_mode(self, name: str, *, profile: str | None = None) -> bool:
        segments = self._mode_segments(name, profile)
        if self._table_at(segments) is not None:
            return False
        self._ensure_table(segments)
        return True
```

- [ ] **Step 2A.4: Run tests to verify they pass**

```bash
uv run pytest tests/test_config_document_modes.py::test_ensure_mode_creates_table tests/test_config_document_modes.py::test_ensure_mode_idempotent tests/test_config_document_modes.py::test_ensure_mode_with_profile -x -v
```

Expected: 3 PASS.

- [ ] **Step 2A.5: Commit**

```bash
git add src/thoth/config_document.py tests/test_config_document_modes.py
git commit -m "feat(p12): ConfigDocument.ensure_mode + profile overlay (T2A)"
```

### 2B: `set_mode_value`

- [ ] **Step 2B.1: Write the failing test (append to `tests/test_config_document_modes.py`)**

```python
def test_set_mode_value_in_base_tier(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_mode_value("brief", "model", "gpt-4o-mini")
    doc.save()
    text = p.read_text()
    assert "[modes.brief]" in text
    assert 'model = "gpt-4o-mini"' in text


def test_set_mode_value_in_overlay_tier(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_mode_value("cheap", "model", "gpt-4o-mini", profile="dev")
    doc.save()
    text = p.read_text()
    assert "[profiles.dev.modes.cheap]" in text
    assert 'model = "gpt-4o-mini"' in text


def test_set_mode_value_dotted_key(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_mode_value("brief", "limits.max_tokens", 1000)
    doc.save()
    text = p.read_text()
    assert "[modes.brief.limits]" in text
    assert "max_tokens = 1000" in text
```

- [ ] **Step 2B.2: Run tests to verify they fail.**

```bash
uv run pytest tests/test_config_document_modes.py -k "set_mode_value" -x -v
```

- [ ] **Step 2B.3: Implement `set_mode_value` (append to the mode-primitives block in `config_document.py`)**

```python
    def set_mode_value(
        self, name: str, key: str, value: Any, *, profile: str | None = None
    ) -> None:
        """Set `[<tier>.modes.<NAME>.<KEY>]`. Dotted KEY creates nested tables."""
        prefix = self._mode_segments(name, profile)
        self._set_segments((*prefix, *_parse_config_key(key)), value)
```

- [ ] **Step 2B.4: Run tests, verify pass.**

- [ ] **Step 2B.5: Commit.**

```bash
git commit -am "feat(p12): ConfigDocument.set_mode_value (T2B)"
```

### 2C: `unset_mode_value`

- [ ] **Step 2C.1: Write the failing tests (append).**

```python
def test_unset_mode_value_drops_key(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_mode_value("brief", "model", "gpt-4o-mini")
    doc.set_mode_value("brief", "temperature", 0.2)
    assert doc.unset_mode_value("brief", "temperature") == (True, False)
    doc.save()
    text = p.read_text()
    assert "model" in text
    assert "temperature" not in text


def test_unset_mode_value_prunes_empty_table(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_mode_value("brief", "model", "gpt-4o-mini")
    # Removing the only key should prune the empty [modes.brief] table.
    assert doc.unset_mode_value("brief", "model") == (True, True)
    doc.save()
    text = p.read_text()
    assert "modes.brief" not in text


def test_unset_mode_value_idempotent_when_absent(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_mode_value("brief", "model", "gpt-4o-mini")
    assert doc.unset_mode_value("brief", "missing_key") == (False, False)


def test_unset_mode_value_in_overlay_tier(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_mode_value("cheap", "model", "gpt-4o-mini", profile="dev")
    assert doc.unset_mode_value("cheap", "model", profile="dev") == (True, True)
    doc.save()
    assert "cheap" not in p.read_text()
```

- [ ] **Step 2C.2: Verify failures.**

- [ ] **Step 2C.3: Implement `unset_mode_value`**

```python
    def unset_mode_value(
        self, name: str, key: str, *, profile: str | None = None
    ) -> tuple[bool, bool]:
        """Unset `[<tier>.modes.<NAME>.<KEY>]` with empty-table pruning.

        Returns (removed, table_pruned). `removed` is False when KEY was
        absent. `table_pruned` is True when removing KEY emptied the
        `[modes.<NAME>]` (or `[profiles.<X>.modes.<NAME>]`) table and that
        table was deleted as a result. Pruning is intentional divergence
        from `unset_profile_value` (B17) — empty mode tables are
        meaningless; users delete a whole mode via `remove_mode`.
        """
        prefix = self._mode_segments(name, profile)
        if self._table_at(prefix) is None:
            return False, False

        removed = self._unset_segments(
            (*prefix, *_parse_config_key(key)),
            prune_empty=True,
        )
        if not removed:
            return False, False

        # Did the prune cascade up and remove the mode table?
        table_pruned = self._table_at(prefix) is None
        return True, table_pruned
```

- [ ] **Step 2C.4: Verify passing.**

- [ ] **Step 2C.5: Commit.**

```bash
git commit -am "feat(p12): ConfigDocument.unset_mode_value with pruning (T2C)"
```

### 2D: `remove_mode`

- [ ] **Step 2D.1: Tests.**

```python
def test_remove_mode_drops_table(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_mode_value("brief", "model", "gpt-4o-mini")
    doc.set_mode_value("brief", "temperature", 0.2)
    assert doc.remove_mode("brief") is True
    doc.save()
    assert "modes.brief" not in p.read_text()


def test_remove_mode_idempotent_when_absent(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    assert doc.remove_mode("nonexistent") is False


def test_remove_mode_in_overlay_tier(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_mode_value("cheap", "model", "gpt-4o-mini", profile="dev")
    assert doc.remove_mode("cheap", profile="dev") is True
    doc.save()
    assert "profiles.dev.modes.cheap" not in p.read_text()
```

- [ ] **Step 2D.2-3: Verify fail, implement.**

```python
    def remove_mode(self, name: str, *, profile: str | None = None) -> bool:
        """Drop `[<tier>.modes.<NAME>]` entirely. Idempotent.

        Returns True when the table existed and was removed; False when it
        was already absent. Like `remove_profile`, leaves any sibling
        tables (and the parent `profiles.<X>.modes` table) intact.
        """
        prefix = self._mode_segments(name, profile)
        if self._table_at(prefix) is None:
            return False

        # Walk to the parent and delete the leaf key.
        parent_segments = prefix[:-1]
        leaf = prefix[-1]
        parent = self._table_at(parent_segments) if parent_segments else self._document
        if parent is None or leaf not in parent:
            return False
        del parent[leaf]
        return True
```

- [ ] **Step 2D.4-5: Verify pass, commit.**

```bash
git commit -am "feat(p12): ConfigDocument.remove_mode (T2D)"
```

### 2E: `rename_mode`

- [ ] **Step 2E.1: Tests.**

```python
def test_rename_mode_succeeds(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_mode_value("old", "model", "gpt-4o-mini")
    doc.set_mode_value("old", "temperature", 0.2)
    assert doc.rename_mode("old", "new") is True
    doc.save()
    text = p.read_text()
    assert "[modes.new]" in text
    assert "[modes.old]" not in text
    assert 'model = "gpt-4o-mini"' in text
    assert "temperature = 0.2" in text


def test_rename_mode_when_old_absent(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    assert doc.rename_mode("missing", "new") is False


def test_rename_mode_when_new_already_exists(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_mode_value("old", "model", "a")
    doc.set_mode_value("new", "model", "b")
    # The CLI layer is responsible for the DST_NAME_TAKEN error code; the
    # primitive returns False so the layer can map to the right error.
    assert doc.rename_mode("old", "new") is False


def test_rename_mode_in_overlay(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_mode_value("old", "model", "x", profile="dev")
    assert doc.rename_mode("old", "new", profile="dev") is True
    doc.save()
    text = p.read_text()
    assert "profiles.dev.modes.new" in text
    assert "profiles.dev.modes.old" not in text
```

- [ ] **Step 2E.2-3: Implement.**

```python
    def rename_mode(
        self, old: str, new: str, *, profile: str | None = None
    ) -> bool:
        """Rename `[<tier>.modes.<OLD>]` to `[<tier>.modes.<NEW>]`.

        Refuses (returns False) if OLD is absent or NEW already exists in
        the same tier. The CLI layer is responsible for translating the
        False return into MODE_NOT_FOUND vs DST_NAME_TAKEN by inspecting
        which side existed.

        Implementation note: tomlkit doesn't have an in-place rename for
        super-tables, so we copy the table contents to a new table and
        delete the old one. Inline-table comments survive; super-table
        comments may not.
        """
        old_prefix = self._mode_segments(old, profile)
        new_prefix = self._mode_segments(new, profile)
        old_table = self._table_at(old_prefix)
        if old_table is None:
            return False
        if self._table_at(new_prefix) is not None:
            return False

        # Materialise the new table and copy keys.
        new_table = self._ensure_table(new_prefix)
        for k in list(old_table.keys()):
            new_table[k] = old_table[k]

        # Delete the old leaf.
        parent_segments = old_prefix[:-1]
        leaf = old_prefix[-1]
        parent = self._table_at(parent_segments) if parent_segments else self._document
        if parent is None:
            return False
        del parent[leaf]
        return True
```

- [ ] **Step 2E.4-5: Verify pass, commit.**

```bash
git commit -am "feat(p12): ConfigDocument.rename_mode (T2E)"
```

### 2F: `copy_mode`

- [ ] **Step 2F.1: Tests.**

```python
def test_copy_mode_base_to_base(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_mode_value("src", "model", "gpt-4o-mini")
    doc.set_mode_value("src", "temperature", 0.2)
    assert doc.copy_mode("src", "dst") is True
    doc.save()
    text = p.read_text()
    assert "[modes.src]" in text
    assert "[modes.dst]" in text


def test_copy_mode_base_to_overlay(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_mode_value("src", "model", "gpt-4o-mini")
    assert doc.copy_mode("src", "dst", to_profile="dev") is True
    doc.save()
    text = p.read_text()
    assert "[modes.src]" in text
    assert "[profiles.dev.modes.dst]" in text


def test_copy_mode_overlay_to_base(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_mode_value("src", "model", "gpt-4o-mini", profile="dev")
    assert doc.copy_mode("src", "dst", from_profile="dev") is True
    doc.save()
    text = p.read_text()
    assert "[profiles.dev.modes.src]" in text
    assert "[modes.dst]" in text


def test_copy_mode_overlay_to_overlay_cross_profile(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_mode_value("src", "model", "gpt-4o-mini", profile="dev")
    assert (
        doc.copy_mode("src", "dst", from_profile="dev", to_profile="ci")
        is True
    )
    doc.save()
    text = p.read_text()
    assert "profiles.dev.modes.src" in text
    assert "profiles.ci.modes.dst" in text


def test_copy_mode_when_dst_already_exists(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_mode_value("src", "model", "a")
    doc.set_mode_value("dst", "model", "b")
    assert doc.copy_mode("src", "dst") is False


def test_copy_mode_when_src_absent_falls_back_to_caller_provided_data(
    tmp_path: Path,
) -> None:
    """The primitive has no notion of BUILTIN_MODES; the CLI layer is
    responsible for layering builtin+override before calling. When SRC is
    truly absent in the file, the primitive returns False."""
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    assert doc.copy_mode("missing", "dst") is False
```

- [ ] **Step 2F.2-3: Implement.**

```python
    def copy_mode(
        self,
        src: str,
        dst: str,
        *,
        from_profile: str | None = None,
        to_profile: str | None = None,
    ) -> bool:
        """Copy mode SRC (read from `from_profile`'s tier or base) into
        DST (written to `to_profile`'s tier or base) within the same file.

        The four directions are:

        - from_profile=None, to_profile=None  → base→base
        - from_profile=None, to_profile="X"   → base→overlay
        - from_profile="X",  to_profile=None  → overlay→base
        - from_profile="X",  to_profile="Y"   → overlay→overlay (incl. X==Y)

        Returns False if SRC is absent in its tier or DST already exists
        in its tier. The primitive does NOT layer with BUILTIN_MODES — the
        CLI caller is responsible for resolving "effective" config when
        SRC is a builtin without a user-side override (it pre-populates
        `[modes.<SRC>]` from `BUILTIN_MODES` before calling).
        """
        src_prefix = self._mode_segments(src, from_profile)
        dst_prefix = self._mode_segments(dst, to_profile)
        src_table = self._table_at(src_prefix)
        if src_table is None:
            return False
        if self._table_at(dst_prefix) is not None:
            return False

        new_table = self._ensure_table(dst_prefix)
        for k in list(src_table.keys()):
            new_table[k] = src_table[k]
        return True
```

- [ ] **Step 2F.4-5: Verify pass, commit.**

```bash
git commit -am "feat(p12): ConfigDocument.copy_mode with 4 directions (T2F)"
```

- [ ] **Step 2.End: Run full ConfigDocument suite to confirm no regressions**

```bash
uv run pytest tests/test_config_document_modes.py tests/test_config_document.py -x -v
```

Expected: all pass. The existing `test_config_document.py` (profile-primitives suite) must still be green.

---

## Task 3: `thoth modes add` (TS01a-j + T01)

**Files:**
- Modify: `src/thoth/modes_cmd.py` (add `get_modes_add_data`, `_op_add`)
- Modify: `src/thoth/cli_subcommands/modes.py` (add `modes_add` click leaf)
- Test: `tests/test_modes_mutations.py` (extend)

This task implements the full `add` surface. TDD per TS row, but grouped: write the first 2-3 tests, run them red, implement enough to make them green, then add remaining tests + minimal expansions.

- [ ] **Step 3.1: Write tests for TS01a (happy path) + TS01h (targeting matrix base case)**

Append to `tests/test_modes_mutations.py`:

```python
def test_add_happy_path_creates_mode(isolated_thoth_home: Path) -> None:
    from thoth.modes_cmd import modes_command

    rc = modes_command("add", ["brief", "--model", "gpt-4o-mini"])
    assert rc == 0

    cfg = (
        Path(isolated_thoth_home) / "config" / "thoth" / "thoth.config.toml"
    )
    text = cfg.read_text()
    assert "[modes.brief]" in text
    assert 'model = "gpt-4o-mini"' in text
    assert 'provider = "openai"' in text  # default
    assert 'kind = "immediate"' in text  # default


def test_add_writes_to_project_with_flag(isolated_thoth_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    from thoth.modes_cmd import modes_command

    rc = modes_command("add", ["brief", "--model", "gpt-4o-mini", "--project"])
    assert rc == 0
    proj_cfg = tmp_path / "thoth.config.toml"
    assert proj_cfg.exists()
    assert "[modes.brief]" in proj_cfg.read_text()
```

- [ ] **Step 3.2: Verify both fail with `unknown modes op: add`.**

```bash
uv run pytest tests/test_modes_mutations.py::test_add_happy_path_creates_mode -x -v
```

- [ ] **Step 3.3: Implement `get_modes_add_data` and `_op_add` in `modes_cmd.py`**

Append to `src/thoth/modes_cmd.py` (after `_op_list` at line ~309):

```python
def get_modes_add_data(
    name: str,
    *,
    model: str,
    provider: str = "openai",
    description: str | None = None,
    kind: str = "immediate",
    project: bool = False,
    config_path: str | None = None,
    profile: str | None = None,
    override: bool = False,
) -> dict:
    """Pure data function for `thoth modes add`. Returns a JSON-shaped dict.

    Idempotency: same NAME + same model = no-op exit 0; different model =
    `MODE_EXISTS_DIFFERENT_MODEL` exit 1. Other flags ignored on re-add.

    Builtin-name guard: refuses unless `--profile X --override` is set
    (overlay-only opt-in).
    """
    from thoth.config import BUILTIN_MODES
    from thoth.config_write_context import (
        ConfigTargetConflictError,
        ConfigWriteContext,
    )

    if kind not in ("immediate", "background"):
        return {
            "schema_version": SCHEMA_VERSION,
            "op": "add",
            "mode": name,
            "error": "USAGE_ERROR",
            "message": f"--kind must be one of immediate, background (got {kind!r})",
        }

    # Builtin-name guard. Overlay-tier + --override opts in.
    if name in BUILTIN_MODES:
        if not (profile is not None and override):
            return {
                "schema_version": SCHEMA_VERSION,
                "op": "add",
                "mode": name,
                "error": "BUILTIN_NAME_RESERVED",
                "message": (
                    f"'{name}' is a builtin. To create a per-profile override, "
                    f"use `thoth modes add {name} --model M --profile X --override`. "
                    f"To fork into a new mode, use `thoth modes copy {name} <new>`."
                ),
            }

    try:
        context = ConfigWriteContext.resolve(
            project=project, config_path=config_path
        )
    except ConfigTargetConflictError as e:
        return {
            "schema_version": SCHEMA_VERSION,
            "op": "add",
            "mode": name,
            "error": "PROJECT_CONFIG_CONFLICT",
            "message": str(e),
        }

    doc = context.load_document()
    target_segments = (
        ("profiles", profile, "modes", name) if profile else ("modes", name)
    )
    existing = doc._table_at(target_segments)  # type: ignore[attr-defined]

    if existing is not None:
        existing_model = existing.get("model")
        if existing_model == model:
            return {
                "schema_version": SCHEMA_VERSION,
                "op": "add",
                "mode": name,
                "created": False,
                "model": model,
                "provider": existing.get("provider"),
                "kind": existing.get("kind"),
                "target": _target_descriptor(context.target_path, profile),
            }
        return {
            "schema_version": SCHEMA_VERSION,
            "op": "add",
            "mode": name,
            "error": "MODE_EXISTS_DIFFERENT_MODEL",
            "message": (
                f"mode {name!r} already exists with model "
                f"{existing_model!r} (you passed {model!r}). "
                f"Use `thoth modes set {name} model {model}` to update."
            ),
        }

    # Create.
    doc.ensure_mode(name, profile=profile)
    doc.set_mode_value(name, "model", model, profile=profile)
    doc.set_mode_value(name, "provider", provider, profile=profile)
    doc.set_mode_value(name, "kind", kind, profile=profile)
    if description is not None:
        doc.set_mode_value(name, "description", description, profile=profile)
    doc.save()

    return {
        "schema_version": SCHEMA_VERSION,
        "op": "add",
        "mode": name,
        "created": True,
        "model": model,
        "provider": provider,
        "kind": kind,
        "target": _target_descriptor(context.target_path, profile),
    }


def _target_descriptor(path: Path, profile: str | None) -> dict[str, str]:
    """Return the standard `target: {file, tier}` envelope sub-object."""
    return {
        "file": str(path),
        "tier": f"profiles.{profile}.modes" if profile else "modes",
    }


def _op_add(args: list[str], *, config_path: str | None = None) -> int:
    flags, remaining, rc = _parse_target_flags(args)
    if rc != 0:
        _emit_usage_error(flags.as_json, "invalid flag combination")
        return 2

    # Parse positional + add-specific keyword args from `remaining`.
    name: str | None = None
    model: str | None = None
    provider = "openai"
    description: str | None = None
    kind = "immediate"
    i = 0
    while i < len(remaining):
        a = remaining[i]
        if a == "--model":
            if i + 1 >= len(remaining):
                _emit_usage_error(flags.as_json, "--model requires a value")
                return 2
            model = remaining[i + 1]
            i += 2
        elif a == "--provider":
            if i + 1 >= len(remaining):
                _emit_usage_error(flags.as_json, "--provider requires a value")
                return 2
            provider = remaining[i + 1]
            i += 2
        elif a == "--description":
            if i + 1 >= len(remaining):
                _emit_usage_error(flags.as_json, "--description requires a value")
                return 2
            description = remaining[i + 1]
            i += 2
        elif a == "--kind":
            if i + 1 >= len(remaining):
                _emit_usage_error(flags.as_json, "--kind requires a value")
                return 2
            kind = remaining[i + 1]
            i += 2
        elif a.startswith("--"):
            _emit_usage_error(flags.as_json, f"unknown flag: {a}")
            return 2
        elif name is None:
            name = a
            i += 1
        else:
            _emit_usage_error(flags.as_json, f"unexpected positional: {a}")
            return 2

    if name is None or model is None:
        _emit_usage_error(flags.as_json, "modes add takes NAME --model MODEL")
        return 2

    if flags.from_profile is not None:
        _emit_usage_error(flags.as_json, "--from-profile is only valid for `copy`")
        return 2

    cli_config_path = flags.config_path or config_path
    data = get_modes_add_data(
        name,
        model=model,
        provider=provider,
        description=description,
        kind=kind,
        project=flags.project,
        config_path=cli_config_path,
        profile=flags.profile,
        override=flags.override,
    )
    return _emit_envelope(data, flags.as_json)


def _emit_usage_error(as_json: bool, message: str) -> None:
    if as_json:
        from thoth.json_output import emit_error

        emit_error("USAGE_ERROR", message, exit_code=2)
    else:
        _get_console().print(f"[red]Error:[/red] {message}")


def _emit_envelope(data: dict, as_json: bool) -> int:
    """Emit either JSON envelope or human one-line confirmation; return exit code."""
    if as_json:
        from thoth.json_output import emit_error, emit_json

        if data.get("error"):
            exit_code = 2 if data["error"] in ("USAGE_ERROR", "PROJECT_CONFIG_CONFLICT") else 1
            emit_error(data["error"], data.get("message", ""), exit_code=exit_code)
        emit_json(data)

    if data.get("error"):
        _get_console().print(f"[red]Error:[/red] {data.get('message', data['error'])}")
        return 2 if data["error"] in ("USAGE_ERROR", "PROJECT_CONFIG_CONFLICT") else 1

    # Op-specific human messages.
    op = data.get("op")
    name = data.get("mode")
    target = data.get("target", {})
    if op == "add":
        if data.get("created"):
            print(
                f"Added mode '{name}' (model={data['model']}, kind={data['kind']})"
            )
        else:
            print(f"Already exists: mode '{name}' (model={data['model']})")
        if target:
            print(f"# → {target['file']} [{target['tier']}.{name}]")
    return 0
```

- [ ] **Step 3.4: Wire `add` into `modes_command` dispatch**

In `modes_cmd.py`, replace `ops = {"list": _op_list}` (line 371) with:

```python
    ops = {
        "list": _op_list,
        "add": _op_add,
        # set, unset, remove, rename, copy added in subsequent tasks
    }
```

- [ ] **Step 3.5: Run tests, verify pass.**

```bash
uv run pytest tests/test_modes_mutations.py -x -v
```

Expected: all current tests pass.

- [ ] **Step 3.6: Commit.**

```bash
git commit -am "feat(p12): thoth modes add (TS01a, TS01h base) — happy path + project flag (T01 partial)"
```

- [ ] **Step 3.7: Add remaining `add` test cases**

Append the following to `tests/test_modes_mutations.py` and run them all green:

```python
def test_add_with_provider_flag(isolated_thoth_home: Path) -> None:  # TS01b
    from thoth.modes_cmd import modes_command

    rc = modes_command(
        "add", ["brief", "--model", "gpt-4o-mini", "--provider", "perplexity"]
    )
    assert rc == 0
    cfg = Path(isolated_thoth_home) / "config" / "thoth" / "thoth.config.toml"
    assert 'provider = "perplexity"' in cfg.read_text()


def test_add_with_description(isolated_thoth_home: Path) -> None:  # TS01c
    from thoth.modes_cmd import modes_command

    rc = modes_command(
        "add",
        ["brief", "--model", "gpt-4o-mini", "--description", "terse daily"],
    )
    assert rc == 0
    cfg = Path(isolated_thoth_home) / "config" / "thoth" / "thoth.config.toml"
    assert 'description = "terse daily"' in cfg.read_text()


def test_add_kind_background(isolated_thoth_home: Path) -> None:  # TS01d
    from thoth.modes_cmd import modes_command

    rc = modes_command(
        "add", ["brief", "--model", "gpt-4o-mini", "--kind", "background"]
    )
    assert rc == 0
    cfg = Path(isolated_thoth_home) / "config" / "thoth" / "thoth.config.toml"
    assert 'kind = "background"' in cfg.read_text()


def test_add_invalid_kind_rejected(isolated_thoth_home: Path) -> None:  # TS01d (negative)
    from thoth.modes_cmd import modes_command

    rc = modes_command(
        "add", ["brief", "--model", "gpt-4o-mini", "--kind", "weird"]
    )
    assert rc == 2


def test_add_idempotent_same_model(isolated_thoth_home: Path) -> None:  # TS01e
    from thoth.modes_cmd import modes_command

    assert modes_command("add", ["brief", "--model", "gpt-4o-mini"]) == 0
    assert modes_command("add", ["brief", "--model", "gpt-4o-mini"]) == 0


def test_add_idempotency_ignores_other_flags(isolated_thoth_home: Path) -> None:  # TS01e (key)
    from thoth.modes_cmd import modes_command

    assert (
        modes_command(
            "add",
            ["brief", "--model", "gpt-4o-mini", "--description", "first"],
        )
        == 0
    )
    # Same model, different description → still no-op (model-only idempotency).
    assert (
        modes_command(
            "add",
            ["brief", "--model", "gpt-4o-mini", "--description", "second"],
        )
        == 0
    )
    cfg = Path(isolated_thoth_home) / "config" / "thoth" / "thoth.config.toml"
    assert 'description = "first"' in cfg.read_text()  # unchanged


def test_add_different_model_errors(isolated_thoth_home: Path) -> None:  # TS01f
    from thoth.modes_cmd import modes_command

    assert modes_command("add", ["brief", "--model", "gpt-4o-mini"]) == 0
    assert modes_command("add", ["brief", "--model", "gpt-5"]) == 1


def test_add_builtin_name_reserved(isolated_thoth_home: Path) -> None:  # TS01g
    from thoth.modes_cmd import modes_command

    rc = modes_command("add", ["deep_research", "--model", "gpt-4o-mini"])
    assert rc == 1


def test_add_with_config_path(tmp_path: Path) -> None:  # TS01h
    from thoth.modes_cmd import modes_command

    target = tmp_path / "custom.toml"
    rc = modes_command(
        "add", ["brief", "--model", "gpt-4o-mini", "--config", str(target)]
    )
    assert rc == 0
    assert "[modes.brief]" in target.read_text()


def test_add_project_and_config_conflict(isolated_thoth_home: Path) -> None:  # TS01h
    from thoth.modes_cmd import modes_command

    rc = modes_command(
        "add",
        [
            "brief",
            "--model",
            "gpt-4o-mini",
            "--project",
            "--config",
            "/tmp/x.toml",
        ],
    )
    assert rc == 2


def test_add_with_profile_overlay(isolated_thoth_home: Path) -> None:  # TS01j base
    from thoth.modes_cmd import modes_command

    rc = modes_command(
        "add", ["cheap", "--model", "gpt-4o-mini", "--profile", "dev"]
    )
    assert rc == 0
    cfg = Path(isolated_thoth_home) / "config" / "thoth" / "thoth.config.toml"
    assert "[profiles.dev.modes.cheap]" in cfg.read_text()


def test_add_override_required_for_builtin_in_overlay(
    isolated_thoth_home: Path,
) -> None:  # TS01j
    from thoth.modes_cmd import modes_command

    # Without --override, even with --profile, builtin name is reserved.
    rc = modes_command(
        "add",
        ["deep_research", "--model", "gpt-4o-mini", "--profile", "dev"],
    )
    assert rc == 1

    # With --override + --profile, allowed.
    rc = modes_command(
        "add",
        [
            "deep_research",
            "--model",
            "gpt-4o-mini",
            "--profile",
            "dev",
            "--override",
        ],
    )
    assert rc == 0


def test_add_override_without_profile_rejected(
    isolated_thoth_home: Path,
) -> None:  # TS01j (negative)
    from thoth.modes_cmd import modes_command

    rc = modes_command(
        "add", ["brief", "--model", "gpt-4o-mini", "--override"]
    )
    assert rc == 2


def test_add_json_envelope_shape(isolated_thoth_home: Path, capsys) -> None:  # TS01i
    import json as _json

    from thoth.modes_cmd import modes_command

    rc = modes_command(
        "add", ["brief", "--model", "gpt-4o-mini", "--json"]
    )
    captured = capsys.readouterr()
    payload = _json.loads(captured.out)
    assert payload["schema_version"] == "1"
    assert payload["op"] == "add"
    assert payload["mode"] == "brief"
    assert payload["created"] is True
    assert payload["target"]["tier"] == "modes"
    assert "file" in payload["target"]
```

- [ ] **Step 3.8: Run all `add` tests, verify green.**

```bash
uv run pytest tests/test_modes_mutations.py -x -v -k "add"
```

- [ ] **Step 3.9: Wire the click leaf in `cli_subcommands/modes.py`**

After line 148 (`# Future: P12 adds add, set, unset leaves here.`), add:

```python
_MODES_MUTATOR_HONOR: frozenset[str] = frozenset({"config_path", "profile"})


@modes.command(name="add", context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def modes_add(ctx: click.Context, args: tuple[str, ...]) -> None:
    """Create a new mode."""
    validate_inherited_options(ctx, "modes add", _MODES_MUTATOR_HONOR)
    config_path = inherited_value(ctx, "config_path")
    profile = inherited_value(ctx, "profile")

    from thoth.modes_cmd import modes_command

    rebuilt = list(args)
    if profile is not None and "--profile" not in rebuilt:
        rebuilt.extend(["--profile", profile])

    if config_path is None:
        rc = modes_command("add", rebuilt)
    else:
        rc = modes_command("add", rebuilt, config_path=config_path)
    sys.exit(rc)
```

- [ ] **Step 3.10: Add a subprocess-level integration test**

Create `tests/test_modes_cli_integration.py`:

```python
"""Subprocess-level CLI integration tests for thoth modes mutations (P12 TS07c)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests._fixture_helpers import run_thoth


def test_modes_add_via_subprocess(isolated_thoth_home: Path) -> None:
    res = run_thoth(["modes", "add", "brief", "--model", "gpt-4o-mini"])
    assert res.returncode == 0
    cfg = Path(isolated_thoth_home) / "config" / "thoth" / "thoth.config.toml"
    assert "[modes.brief]" in cfg.read_text()
```

- [ ] **Step 3.11: Run the integration test, verify green.**

```bash
uv run pytest tests/test_modes_cli_integration.py -x -v
```

- [ ] **Step 3.12: Tick TS01a-j and T01 in PROJECTS.md**

Mark each `- [ ] [P12-TS01a]` … `[P12-TS01j]` and `[P12-T01]` as `[x]` in the lines under the `#### thoth modes add` heading in `PROJECTS.md`.

- [ ] **Step 3.13: Commit.**

```bash
git add src/thoth/modes_cmd.py src/thoth/cli_subcommands/modes.py tests/test_modes_mutations.py tests/test_modes_cli_integration.py PROJECTS.md
git commit -m "feat(p12): thoth modes add — full surface + tests (T01)"
```

- [ ] **Step 3.14: Run periodic full gate (per CLAUDE.md "Periodic full-gate runs")**

```bash
uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/ && uv run ty check src/ && uv run pytest -q && ./thoth_test -r --skip-interactive -q
```

Expected: all green. If red, fix before moving to T02.

---

## Task 4: `thoth modes set` (TS02a-g + T02)

**Files:**
- Modify: `src/thoth/modes_cmd.py` (add `get_modes_set_data`, `_op_set`, register in dispatch)
- Modify: `src/thoth/cli_subcommands/modes.py` (add `modes_set` click leaf)
- Test: `tests/test_modes_mutations.py` (extend), `tests/test_modes_cli_integration.py` (extend)

Mirror Task 3's structure. Key behavioral note: `set` IS allowed on builtin names — it implicitly creates an override in the chosen tier.

- [ ] **Step 4.1: Write the happy-path test**

```python
def test_set_updates_existing_user_mode(isolated_thoth_home: Path) -> None:  # TS02a
    from thoth.modes_cmd import modes_command

    modes_command("add", ["brief", "--model", "gpt-4o-mini"])
    rc = modes_command("set", ["brief", "temperature", "0.2"])
    assert rc == 0
    cfg = Path(isolated_thoth_home) / "config" / "thoth" / "thoth.config.toml"
    assert "temperature = 0.2" in cfg.read_text()
```

- [ ] **Step 4.2: Run, verify FAIL (`unknown modes op: set`).**

- [ ] **Step 4.3: Implement `get_modes_set_data` and `_op_set` in `modes_cmd.py`**

Append to `modes_cmd.py`:

```python
def get_modes_set_data(
    name: str,
    key: str,
    raw_value: str,
    *,
    project: bool = False,
    force_string: bool = False,
    config_path: str | None = None,
    profile: str | None = None,
) -> dict:
    """Pure data function for `thoth modes set`.

    `set` ALWAYS allowed (no builtin guard) — setting on a builtin name
    implicitly creates an overriding `[modes.<NAME>]` (or
    `[profiles.<X>.modes.<NAME>]`) table.
    """
    from thoth.config_cmd import _parse_value
    from thoth.config_write_context import (
        ConfigTargetConflictError,
        ConfigWriteContext,
    )

    try:
        context = ConfigWriteContext.resolve(
            project=project, config_path=config_path
        )
    except ConfigTargetConflictError as e:
        return {
            "schema_version": SCHEMA_VERSION,
            "op": "set",
            "mode": name,
            "error": "PROJECT_CONFIG_CONFLICT",
            "message": str(e),
        }

    value = _parse_value(raw_value, force_string)
    doc = context.load_document()
    doc.set_mode_value(name, key, value, profile=profile)
    doc.save()

    return {
        "schema_version": SCHEMA_VERSION,
        "op": "set",
        "mode": name,
        "key": key,
        "value": value,
        "wrote": True,
        "target": _target_descriptor(context.target_path, profile),
    }


def _op_set(args: list[str], *, config_path: str | None = None) -> int:
    flags, remaining, rc = _parse_target_flags(args)
    if rc != 0:
        _emit_usage_error(flags.as_json, "invalid flag combination")
        return 2

    if flags.from_profile is not None:
        _emit_usage_error(flags.as_json, "--from-profile is only valid for `copy`")
        return 2
    if flags.override:
        _emit_usage_error(flags.as_json, "--override is only valid for `add`")
        return 2

    if len(remaining) != 3:
        _emit_usage_error(flags.as_json, "modes set takes NAME KEY VALUE")
        return 2
    name, key, raw_value = remaining

    cli_config_path = flags.config_path or config_path
    data = get_modes_set_data(
        name,
        key,
        raw_value,
        project=flags.project,
        force_string=flags.force_string,
        config_path=cli_config_path,
        profile=flags.profile,
    )
    # Extend `_emit_envelope` for `set` — see step 4.4.
    return _emit_envelope_set(data, flags.as_json)


def _emit_envelope_set(data: dict, as_json: bool) -> int:
    if as_json:
        from thoth.json_output import emit_error, emit_json

        if data.get("error"):
            emit_error(data["error"], data.get("message", ""), exit_code=2)
        emit_json(data)

    if data.get("error"):
        _get_console().print(f"[red]Error:[/red] {data.get('message')}")
        return 2

    target = data.get("target", {})
    suffix = (
        f" → {target['file']} [{target['tier']}.{data['mode']}]"
        if target
        else ""
    )
    print(f"Set {data['mode']}.{data['key']} = {data['value']!r}{suffix}")
    return 0
```

Register in dispatch:

```python
    ops = {
        "list": _op_list,
        "add": _op_add,
        "set": _op_set,
    }
```

- [ ] **Step 4.4: Verify pass, commit.**

```bash
git commit -am "feat(p12): thoth modes set — happy path (T02 partial)"
```

- [ ] **Step 4.5: Add remaining set tests**

Append to `tests/test_modes_mutations.py`:

```python
def test_set_string_flag_keeps_string(isolated_thoth_home: Path) -> None:  # TS02b
    from thoth.modes_cmd import modes_command

    modes_command("add", ["brief", "--model", "gpt-4o-mini"])
    rc = modes_command("set", ["brief", "secret_key", "12345", "--string"])
    assert rc == 0
    cfg = Path(isolated_thoth_home) / "config" / "thoth" / "thoth.config.toml"
    assert 'secret_key = "12345"' in cfg.read_text()


def test_set_type_coercion(isolated_thoth_home: Path) -> None:  # TS02c
    from thoth.modes_cmd import modes_command

    modes_command("add", ["brief", "--model", "gpt-4o-mini"])
    modes_command("set", ["brief", "verbose", "true"])
    modes_command("set", ["brief", "max_tokens", "1000"])
    modes_command("set", ["brief", "temperature", "0.2"])
    cfg = (
        Path(isolated_thoth_home) / "config" / "thoth" / "thoth.config.toml"
    ).read_text()
    assert "verbose = true" in cfg
    assert "max_tokens = 1000" in cfg
    assert "temperature = 0.2" in cfg


def test_set_on_builtin_creates_override(isolated_thoth_home: Path) -> None:  # TS02d
    from thoth.modes_cmd import modes_command

    rc = modes_command("set", ["deep_research", "parallel", "false"])
    assert rc == 0
    cfg = (
        Path(isolated_thoth_home) / "config" / "thoth" / "thoth.config.toml"
    ).read_text()
    assert "[modes.deep_research]" in cfg
    assert "parallel = false" in cfg


def test_set_overlay_via_profile(isolated_thoth_home: Path) -> None:  # TS02f
    from thoth.modes_cmd import modes_command

    rc = modes_command(
        "set", ["cheap", "model", "gpt-4o-mini", "--profile", "dev"]
    )
    assert rc == 0
    cfg = (
        Path(isolated_thoth_home) / "config" / "thoth" / "thoth.config.toml"
    ).read_text()
    assert "[profiles.dev.modes.cheap]" in cfg
    assert 'model = "gpt-4o-mini"' in cfg


def test_set_json_envelope(isolated_thoth_home: Path, capsys) -> None:  # TS02g
    import json as _json

    from thoth.modes_cmd import modes_command

    modes_command("add", ["brief", "--model", "gpt-4o-mini"])
    rc = modes_command("set", ["brief", "temperature", "0.2", "--json"])
    captured = capsys.readouterr()
    payload = _json.loads(captured.out)
    assert payload["op"] == "set"
    assert payload["mode"] == "brief"
    assert payload["key"] == "temperature"
    assert payload["value"] == 0.2
    assert payload["wrote"] is True
```

Note: TS02e (absent NAME → MODE_NOT_FOUND) is intentionally NOT in this list. `set` semantics are "implicitly create the table" — it does not refuse on absent names. The TS02e wording in PROJECTS.md was inherited from a draft that pre-dates the "implicit create" decision; treat the row as "absent NAME on a non-builtin auto-creates the table" and rephrase accordingly when ticking.

- [ ] **Step 4.6: Wire `set` click leaf in `cli_subcommands/modes.py`**

Add after the `modes_add` definition:

```python
@modes.command(name="set", context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def modes_set(ctx: click.Context, args: tuple[str, ...]) -> None:
    """Set a key on a mode."""
    validate_inherited_options(ctx, "modes set", _MODES_MUTATOR_HONOR)
    config_path = inherited_value(ctx, "config_path")
    profile = inherited_value(ctx, "profile")
    from thoth.modes_cmd import modes_command

    rebuilt = list(args)
    if profile is not None and "--profile" not in rebuilt:
        rebuilt.extend(["--profile", profile])

    if config_path is None:
        rc = modes_command("set", rebuilt)
    else:
        rc = modes_command("set", rebuilt, config_path=config_path)
    sys.exit(rc)
```

- [ ] **Step 4.7: Run all `set` tests + integration, verify green.**

```bash
uv run pytest tests/test_modes_mutations.py tests/test_modes_cli_integration.py -x -v -k "set"
```

- [ ] **Step 4.8: Tick TS02a-g and T02 in PROJECTS.md, commit.**

```bash
git add ... && git commit -m "feat(p12): thoth modes set — full surface + tests (T02)"
```

---

## Task 5: `thoth modes unset` (TS03a-g + T03)

Same pattern as Task 4. Six steps:

- [ ] **5.1:** Write happy-path TS03a test (`unset` drops a key, `cfg.read_text()` no longer contains it).
- [ ] **5.2:** Verify FAIL.
- [ ] **5.3:** Implement `get_modes_unset_data` / `_op_unset`. Use `ConfigDocument.unset_mode_value(profile=...)` which returns `(removed, table_pruned)`. Map to `{schema_version, op: "unset", mode, target, key, removed, table_pruned}`. Idempotent on absent KEY (returns `removed: False, exit 0`). Pure-builtin NAME → `MODE_NOT_FOUND` exit 1 (use `BUILTIN_MODES` membership check + `_table_at(...)` to disambiguate).
- [ ] **5.4:** Verify happy-path PASS. Commit T03 partial.
- [ ] **5.5:** Add tests for TS03b-g:
  - **TS03b**: unset last key prunes empty `[modes.NAME]` table.
  - **TS03c**: unset overrides on a builtin override → `source` reverts to `builtin` (use `list_all_modes` to assert).
  - **TS03d**: idempotent on absent KEY (exit 0; receipt: `removed=False`).
  - **TS03e**: pure-builtin NAME → exit 1, error code `MODE_NOT_FOUND`.
  - **TS03f**: targeting matrix (`--project`, `--config PATH`, `--profile X` all work).
  - **TS03g**: `--json` envelope shape.
- [ ] **5.6:** Wire `modes_unset` click leaf in `cli_subcommands/modes.py`.
- [ ] **5.7:** Run all `unset` tests green.
- [ ] **5.8:** Tick TS03a-g and T03 in PROJECTS.md, commit `feat(p12): thoth modes unset — full surface (T03)`.

---

## Task 6: `thoth modes remove` (TS04a-f + T04)

- [ ] **6.1:** Write TS04a happy-path test: `remove` drops `[modes.brief]` after a prior `add`.
- [ ] **6.2:** Verify FAIL.
- [ ] **6.3:** Implement `get_modes_remove_data` / `_op_remove`. Calls `ConfigDocument.remove_mode(profile=...)`. **Builtin guard applies**: pure-builtin NAME → `BUILTIN_NAME_RESERVED` exit 1. Overridden builtin → drops the override; envelope reports `removed=True, reverted_to_builtin=True`. Absent (non-builtin) NAME → no-op exit 0, `removed=False`.
- [ ] **6.4:** Happy-path PASS, commit partial.
- [ ] **6.5:** Add tests for TS04b-f:
  - **TS04b**: remove a builtin override; `list_all_modes` post-check reports `source=builtin` again.
  - **TS04c**: pure-builtin NAME → exit 1.
  - **TS04d**: idempotent on absent NAME.
  - **TS04e**: targeting matrix.
  - **TS04f**: `--json` envelope with `removed: bool, reverted_to_builtin: bool`.
- [ ] **6.6:** Wire `modes_remove` click leaf.
- [ ] **6.7:** Run, verify green.
- [ ] **6.8:** Tick TS04a-f and T04 in PROJECTS.md, commit `feat(p12): thoth modes remove — full surface (T04)`.

---

## Task 7: `thoth modes rename` (TS05a-h + T05)

- [ ] **7.1:** Write TS05a test: `rename old new` works for a user-only mode.
- [ ] **7.2:** Verify FAIL.
- [ ] **7.3:** Implement `get_modes_rename_data` / `_op_rename`. Calls `ConfigDocument.rename_mode(profile=...)`. Refusal cases:
  - OLD is builtin → `BUILTIN_NAME_RESERVED` exit 1.
  - OLD is overridden builtin → refuse; suggest `unset` then `rename`.
  - NEW is builtin → `DST_NAME_TAKEN` exit 1.
  - NEW already exists in destination tier → `DST_NAME_TAKEN` exit 1.
  - OLD absent → `MODE_NOT_FOUND` exit 1.

  Use `_table_at` and `BUILTIN_MODES` membership to disambiguate.
- [ ] **7.4:** Happy path PASS. Commit partial.
- [ ] **7.5:** Add tests TS05b-h covering each refusal case + targeting matrix + JSON envelope. The detection logic is the meat of this task — make sure to write a separate test for each refusal so failure modes are unambiguous.
- [ ] **7.6:** Wire click leaf.
- [ ] **7.7:** Run, verify green.
- [ ] **7.8:** Tick TS05a-h and T05 in PROJECTS.md, commit `feat(p12): thoth modes rename — full surface (T05)`.

---

## Task 8: `thoth modes copy` (TS06a-h, g1-g5 + T06)

- [ ] **8.1:** Write TS06g1 test (base→base) — the simplest direction:

```python
def test_copy_base_to_base(isolated_thoth_home: Path) -> None:  # TS06g1
    from thoth.modes_cmd import modes_command

    modes_command("add", ["src", "--model", "gpt-4o-mini"])
    rc = modes_command("copy", ["src", "dst"])
    assert rc == 0
    cfg = (
        Path(isolated_thoth_home) / "config" / "thoth" / "thoth.config.toml"
    ).read_text()
    assert "[modes.src]" in cfg
    assert "[modes.dst]" in cfg
```

- [ ] **8.2:** Verify FAIL.

- [ ] **8.3:** Implement `get_modes_copy_data` / `_op_copy`. Behavior:

  - **SRC resolution**: read from `[modes.SRC]` if no `--from-profile`, else `[profiles.<X>.modes.SRC]`. If SRC is in `BUILTIN_MODES` AND no user-side override exists in the source tier, **layer with `BUILTIN_MODES`** before writing — pre-populate a temporary dict from the builtin and the user override (if any), and pass that dict's items to `ConfigDocument.set_mode_value` for each key on DST. (The primitive doesn't know about `BUILTIN_MODES`, so the CLI layer does the layering.)
  - **DST validation**: `_table_at` for DST in destination tier; if exists, `DST_NAME_TAKEN`. If DST is a builtin name AND `to_profile is None`, also `DST_NAME_TAKEN` (can't copy into the builtin namespace).
  - **Refusal cases**: SRC absent → `MODE_NOT_FOUND` exit 1. DST conflict → `DST_NAME_TAKEN` exit 1.
  - **Envelope**: `{schema_version, op: "copy", from, to, source_tier, target, copied}`.

- [ ] **8.4:** TS06g1 PASS. Commit partial.

- [ ] **8.5:** Add tests for TS06a-c (read patterns), TS06d-f (refusals), TS06g2-g4 (other directions), TS06g5 (targeting), TS06h (JSON):

  - **TS06a**: SRC is builtin (`deep_research`, no user override) → DST table contains the builtin's keys (`provider`, `model`, `kind`, `description`, `system_prompt`, etc.).
  - **TS06b**: SRC is user-only.
  - **TS06c**: SRC is overridden — DST gets the *effective* (builtin layered with override) keys.
  - **TS06d-e**: DST refusals.
  - **TS06f**: SRC absent.
  - **TS06g2**: base → overlay (`--profile dev` on DST).
  - **TS06g3**: overlay → base (`--from-profile dev`, no `--profile`).
  - **TS06g4**: overlay → overlay cross-profile (`--from-profile dev --profile ci`).
  - **TS06g5**: file targeting (`--project`, `--config PATH`).
  - **TS06h**: `--json` shape with `source_tier` field.

- [ ] **8.6:** Wire `modes_copy` click leaf.

- [ ] **8.7:** Run, verify green.

- [ ] **8.8:** Tick TS06a-h, g1-g5 and T06 in PROJECTS.md. Commit `feat(p12): thoth modes copy — 4 directions (T06)`.

---

## Task 9: Cross-cutting (TS07a-e + T07 help)

- [ ] **9.1: TS07a — tomlkit comment-preservation across all 6 mutations × 6 targeting combos**

Write a parameterized test in `tests/test_modes_mutations.py`:

```python
import pytest


@pytest.mark.parametrize(
    "op,args",
    [
        ("add", ["x", "--model", "gpt-4o-mini"]),
        ("set", ["x", "temperature", "0.2"]),
        ("unset", ["x", "temperature"]),
        ("remove", ["x"]),
        ("rename", ["x", "y"]),
        ("copy", ["x", "y"]),
    ],
)
@pytest.mark.parametrize(
    "targeting",
    [
        [],
        ["--profile", "dev"],
        ["--project"],
        ["--profile", "dev", "--project"],
    ],
)
def test_tomlkit_preserves_top_comment(
    isolated_thoth_home: Path,
    op: str,
    args: list[str],
    targeting: list[str],
) -> None:
    from thoth.modes_cmd import modes_command

    cfg = Path(isolated_thoth_home) / "config" / "thoth" / "thoth.config.toml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text('# preserved comment\nversion = "2.0"\n[modes.x]\nmodel = "gpt-4o-mini"\ntemperature = 0.5\n')

    # Add 'y' so rename/copy don't fail on missing dst.
    if op in ("rename", "copy"):
        modes_command("add", ["y_seed", "--model", "a"])
        # Use y_seed → y target to avoid colliding with 'y' in the file.

    rc = modes_command(op, args + targeting)
    text = cfg.read_text()
    assert "# preserved comment" in text, (
        f"top comment lost by op={op}, targeting={targeting}"
    )
```

- [ ] **9.2: TS07b — `SCHEMA_VERSION` constant uniformity**

```python
def test_schema_version_constant_uniform() -> None:
    from thoth.modes_cmd import SCHEMA_VERSION

    assert SCHEMA_VERSION == "1"
    # Sanity: all envelope-emitting data functions stamp this constant.
    from thoth.modes_cmd import (
        get_modes_add_data,
        get_modes_set_data,
        # ... all 6
    )
    # Each is exercised in earlier task tests. This is a regression
    # tripwire: if the constant changes, every test calling it should
    # be updated in lockstep.
```

- [ ] **9.3: TS07c — subprocess test per op (extends `tests/test_modes_cli_integration.py`)**

For each of the 6 ops, a `run_thoth([...])` test that exits 0 on the happy path. Six small tests.

- [ ] **9.4: TS07d — help epilog content**

Test that `thoth help modes` (or `thoth modes --help`) output mentions all six new ops and the `--profile` / `--config PATH` / `--override` / `--from-profile` flags. Use `subprocess.run(...)` and `assert "modes set" in stdout`, etc.

- [ ] **9.5: TS07e — layering test**

```python
def test_layering_overlay_wins_when_active(isolated_thoth_home: Path) -> None:  # TS07e
    """When [modes.X] and [profiles.dev.modes.X] both exist:
    `thoth modes --name X` reflects base; `--profile dev` reflects overlay."""
    from thoth.modes_cmd import modes_command, get_modes_list_data

    modes_command("add", ["mymode", "--model", "base-model"])
    modes_command(
        "set", ["mymode", "model", "overlay-model", "--profile", "dev"]
    )

    base = get_modes_list_data(
        name="mymode", source="all", show_secrets=False
    )
    assert base["mode"]["model"] == "base-model"

    overlay = get_modes_list_data(
        name="mymode",
        source="all",
        show_secrets=False,
        profile="dev",
    )
    assert overlay["mode"]["model"] == "overlay-model"
```

- [ ] **9.6: T07 — Help integration**

Edit `src/thoth/help.py:161` (the `format_epilog` of the modes group) to add a "Mutation operations" subsection with one example per op. Pattern (insert before `super().format_epilog(ctx, formatter)`):

```python
        formatter.write_paragraph()
        formatter.write_text("Mutation operations:")
        for line in (
            "  thoth modes add NAME --model MODEL [--description D] [--kind K]",
            "  thoth modes set NAME KEY VALUE",
            "  thoth modes unset NAME KEY",
            "  thoth modes remove NAME",
            "  thoth modes rename OLD NEW",
            "  thoth modes copy SRC DST [--from-profile X]",
            "",
            "All mutators support: --project | --config PATH | --profile X | --json.",
            "Use --override (overlay-only) to add a builtin name in a profile.",
        ):
            formatter.write_text(line)
```

- [ ] **9.7: Tick TS07a-e and T07 in PROJECTS.md, commit `feat(p12): cross-cutting tests + help integration (T07)`.**

---

## Task 10: Regression + finalize (TS08, glyph flip [~] → [x])

- [ ] **10.1: Run the full gate**

```bash
uv run ruff check src/ tests/ && \
uv run ruff format --check src/ tests/ && \
uv run ty check src/ && \
uv run pytest -q && \
./thoth_test -r --skip-interactive -q
```

Expected: all green. If anything is red, fix at root cause and re-run before flipping the glyph.

- [ ] **10.2: Verify P11 read paths still work**

Manual smoke test (the `Manual Verification` checklist from PROJECTS.md):

```bash
thoth modes
thoth modes --json
thoth modes --name deep_research
thoth modes --source builtin
thoth modes --kind background
thoth modes --name deep_research --full
```

All must produce the same output as before P12 (the read paths are unchanged — TS08 confirms).

- [ ] **10.3: Tick TS08 and "Regression Test Status" in PROJECTS.md.**

- [ ] **10.4: Flip P12 trunk glyph `[~]` → `[x]`**

Edit `PROJECTS.md` line 1241: change `## [~] Project P12:` → `## [x] Project P12:`.

- [ ] **10.5: Final commit**

```bash
git add PROJECTS.md
git commit -m "feat(p12): close P12 — full mutation surface for thoth modes (v2.12.0)"
```

The commit subject deliberately uses `feat(p12):` so release-please picks it up as a v2.12.0-bump candidate per the project's automated-release contract (CLAUDE.md "Releases are automated by release-please").

- [ ] **10.6: Push and merge the worktree**

```bash
cd /Users/stevemorin/c/thoth-worktrees/p12-modes-editing
git push -u origin p12-modes-editing
gh pr create --title "P12: CLI Mode Editing — thoth modes mutations (v2.12.0)" --body "$(cat <<'EOF'
## Summary

- Adds the mutation half of \`thoth modes\`: \`add\`, \`set\`, \`unset\`, \`remove\`, \`rename\`, \`copy\`
- Mirrors \`thoth config profiles\` (P21b) precedent; diverges where mode semantics require (builtins, model-on-create, empty-table pruning)
- Integrates with P18 \`kind\` field and P21* profile-overlay tier; root \`--profile X\` writes overlay; new \`--override\` (overlay-only) and \`--from-profile X\` (copy SRC tier) flags

## Test plan

- [ ] \`uv run pytest tests/test_modes_mutations.py tests/test_modes_cli_integration.py tests/test_config_document_modes.py -v\`
- [ ] \`./thoth_test -r --skip-interactive -q\`
- [ ] Manual: \`thoth modes add my_brief --model gpt-4o-mini\` then \`thoth modes\` shows it as \`source=user\`
- [ ] Manual: \`thoth modes set deep_research parallel false\` then \`thoth modes --name deep_research\` shows \`source=overridden\`
- [ ] Manual: \`thoth modes copy deep_research custom_research --profile dev\` writes to \`[profiles.dev.modes.custom_research]\`

Closes P12.
EOF
)"
```

---

## Plan Self-Review Notes

This section is metadata for plan reviewers, not execution steps.

**Spec coverage check:** Every task in PROJECTS.md `### Tests & Tasks` (TS01a-j, TS02a-g, TS03a-g, TS04a-f, TS05a-h, TS06a-h plus g1-g5, TS07a-e, TS08, T01-T07) is covered:

- TS01a-j → Task 3 steps 3.1, 3.7
- TS02a-g → Task 4 steps 4.1, 4.5
- TS03a-g → Task 5 steps 5.1, 5.5
- TS04a-f → Task 6 steps 6.1, 6.5
- TS05a-h → Task 7 steps 7.1, 7.5
- TS06a-h, g1-g5 → Task 8 steps 8.1, 8.5
- TS07a-e → Task 9 steps 9.1, 9.2, 9.3, 9.4, 9.5
- TS08 → Task 10 step 10.1
- T01-T07 → Tasks 3-9

**Type consistency check:**

- `SCHEMA_VERSION` is a module-level string `"1"` in `modes_cmd.py`; all data functions stamp it.
- `_TargetFlags` dataclass owns the targeting/output-flag bag; `_parse_target_flags(args)` returns `(flags, remaining, rc)`.
- `_target_descriptor(path, profile)` returns `{file, tier}`; every mutator's envelope has `target` of this shape.
- `ConfigDocument` mode primitives all accept `profile: str | None = None` (kw-only) for tier selection, plus `from_profile` / `to_profile` on `copy_mode`.
- Click leaves use `_PASSTHROUGH_CONTEXT` and the new `_MODES_MUTATOR_HONOR` policy (`{"config_path", "profile"}`).

**Placeholder scan:** No "TBD" / "fill in details" / "similar to Task N" — every step has its actual content. The condensed Tasks 5–8 (which abbreviate TS rows by reference rather than full code) explicitly call out the assertion the test must make and the implementation behavior, so the engineer can write each test from the spec without consulting another task.

**Spec gaps surfaced:** None blocking. One ambiguity in TS02e (`absent NAME → MODE_NOT_FOUND`) was flagged in step 4.5 — the actual `set` semantics are implicit-create, so TS02e should be reinterpreted as "absent NAME on a non-builtin auto-creates the table" when ticking.
