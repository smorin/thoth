# P12: CLI Mode Editing Implementation Plan

**References**
- **Project:** [projects/P12-cli-mode-editing.md](../../../projects/P12-cli-mode-editing.md) — P12 project file (scope, tasks, verification — canonical)
- **Trunk:** [PROJECTS.md](../../../PROJECTS.md)
- **Supersedes:** [2026-04-30-p12-cli-mode-editing.md](2026-04-30-p12-cli-mode-editing.md) — stale earlier draft (banner-marked superseded)
- **Code:** `src/thoth/config_profiles.py:107` (overlay-modes semantics that P12's `--profile X` integrates with)

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the mutation half of `thoth modes` — `add`, `set`, `unset`, `remove`, `rename`, `copy` — so users can author and edit research-mode definitions from the CLI instead of hand-editing TOML, with full `--project` / `--config PATH` / `--profile X` targeting parity with `thoth config set` and `thoth config profiles ...`.

**Architecture:** Mirror `thoth config profiles` (P21b, shipped) where applicable. Add six mode-aware primitives to `ConfigDocument` (parallel to its existing `ensure_profile` / `remove_profile` / `set_profile_value` / `unset_profile_value` quartet), plus `rename_mode` and `copy_mode`. Add `_op_add` / `_op_set` / `_op_unset` / `_op_remove` / `_op_rename` / `_op_copy` to `modes_cmd.py`, sharing one targeting-flag parser. Wire each op as a Click subcommand in `cli_subcommands/modes.py`. Help epilog updates land in `help.py`. Effective-config writes go through `ConfigDocument` only — no direct tomlkit in command code.

**Tech Stack:** Python 3.11+, Click, tomlkit (round-trip preserves comments/formatting), pytest with `isolated_thoth_home` fixture, `subprocess` for CLI integration tests, `ConfigWriteContext.resolve()` for write-target resolution.

**Source of truth:** [projects/P12-cli-mode-editing.md](../../../projects/P12-cli-mode-editing.md). If this plan and the project file disagree, the project file wins. The plan implements the spec; the spec defines the contract.

**Supersedes:** `docs/superpowers/plans/2026-04-30-p12-cli-mode-editing.md` (1438 lines, written 2026-04-30 earlier in the day, stale on five points: missing `remove NAME`, missing `--override` flag, missing `--from-profile X` flag for `copy`, wrong `add` idempotency rule, missing the cross-cutting layering test). That plan should be marked superseded after this one is reviewed; do not consult it during implementation.

---

## File Structure

| Action | Path | Responsibility |
|---|---|---|
| Modify | `src/thoth/config_document.py` | Add `ensure_mode`, `remove_mode`, `set_mode_value`, `unset_mode_value`, `rename_mode`, `copy_mode`. Each accepts an optional `profile: str \| None` parameter — when set, the target sub-tree becomes `profiles.<X>.modes.<NAME>` instead of `modes.<NAME>`. Pure file-mutation; no resolver logic. |
| Modify | `src/thoth/modes_cmd.py` | Add `get_modes_<op>_data` data functions, `get_modes_<op>_data_from_args` parser helpers for JSON wrappers, and `_op_<op>` human CLI wrappers for `add` / `set` / `unset` / `remove` / `rename` / `copy`. Add a shared `_parse_target_flags` helper for `--project` / `--config` / `--profile` / `--from-profile`. Wire ops into `modes_command` dispatch. |
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

## Task 1: Shared targeting-flag parser + schema-version constant

**Files:**
- Modify: `src/thoth/modes_cmd.py` (add `_parse_target_flags` helper near the top, `SCHEMA_VERSION` constant, `_TargetFlags` dataclass)
- Test: `tests/test_modes_mutations.py` (create)

This task lays the cross-cutting infrastructure used by all six commands. Doing it first so every later task can call `_parse_target_flags(args)` and stamp data receipts via the shared `SCHEMA_VERSION`. JSON wrapping still happens only in `cli_subcommands/modes.py`.

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
    assert flags.force_string is False
    assert flags.override is False
    assert remaining == []


def test_parse_target_flags_project_success() -> None:
    from thoth.modes_cmd import _parse_target_flags

    flags, remaining, rc = _parse_target_flags(
        [
            "alpha",
            "--project",
            "--profile",
            "dev",
            "--from-profile",
            "ci",
            "--string",
            "--override",
            "beta",
            "--model",
            "gpt-4o-mini",
        ]
    )
    assert rc == 0
    assert flags.project is True
    assert flags.config_path is None
    assert flags.profile == "dev"
    assert flags.from_profile == "ci"
    assert flags.force_string is True
    assert flags.override is True
    assert remaining == ["alpha", "beta", "--model", "gpt-4o-mini"]


def test_parse_target_flags_config_success() -> None:
    from thoth.modes_cmd import _parse_target_flags

    flags, remaining, rc = _parse_target_flags(
        ["alpha", "--config", "/tmp/x.toml", "beta"]
    )
    assert rc == 0
    assert flags.project is False
    assert flags.config_path == "/tmp/x.toml"
    assert remaining == ["alpha", "beta"]


def test_parse_target_flags_project_config_conflict() -> None:
    from thoth.modes_cmd import _parse_target_flags

    flags, remaining, rc = _parse_target_flags(
        ["--project", "--config", "/tmp/x.toml"]
    )
    assert rc == 2
    # rc=2 signals USAGE_ERROR; the caller is responsible for the error
    # message (the Click wrapper emits structured JSON errors when needed).


def test_parse_target_flags_override_without_profile_allowed() -> None:
    from thoth.modes_cmd import _parse_target_flags

    flags, remaining, rc = _parse_target_flags(["--override"])
    assert rc == 0
    assert flags.override is True
    assert flags.profile is None
    # Operation-specific parsers decide whether --override is accepted.
    # P12 accepts it for add/copy and rejects it for set/unset/remove/rename.
```

- [ ] **Step 1.2: Run tests to verify they fail**

```bash
uv run pytest tests/test_modes_mutations.py -x -v
```

Expected: 5 FAIL with `ImportError: cannot import name '_parse_target_flags' from 'thoth.modes_cmd'`.

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
    `override` is the builtin-shadow opt-in for add/copy; every other op
    rejects it as USAGE_ERROR.
    """

    project: bool = False
    config_path: str | None = None
    profile: str | None = None
    from_profile: str | None = None
    force_string: bool = False
    override: bool = False


def _parse_target_flags(
    args: list[str],
) -> tuple[_TargetFlags, list[str], int]:
    """Pull targeting flags out of `args`. Returns (flags, remaining, rc).

    rc == 0 → ok; rc == 2 → USAGE_ERROR (caller emits the message).
    Validates `--project` ⊥ `--config PATH`.
    Does NOT validate that an op accepts `--from-profile` or `--override` —
    that's per-op.
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

    return flags, remaining, 0
```

- [ ] **Step 1.4: Run tests to verify they pass**

```bash
uv run pytest tests/test_modes_mutations.py -x -v
```

Expected: 5 PASS.

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
    assert doc.copy_mode("src", "dst", profile="dev") is True
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
        doc.copy_mode("src", "dst", from_profile="dev", profile="ci")
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
        profile: str | None = None,
    ) -> bool:
        """Copy mode SRC (read from `from_profile`'s tier or base) into
        DST (written to `profile`'s tier or base) within the same file.

        The four directions are:

        - from_profile=None, profile=None  → base→base
        - from_profile=None, profile="X"   → base→overlay
        - from_profile="X",  profile=None  → overlay→base
        - from_profile="X",  profile="Y"   → overlay→overlay (incl. X==Y)

        Returns False if SRC is absent in its tier or DST already exists
        in its tier. The primitive does NOT layer with BUILTIN_MODES — the
        CLI caller is responsible for resolving "effective" config when
        SRC is a builtin without a user-side override (it pre-populates
        `[modes.<SRC>]` from `BUILTIN_MODES` before calling).
        """
        src_prefix = self._mode_segments(src, from_profile)
        dst_prefix = self._mode_segments(dst, profile)
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

## Task 3: Shared command infrastructure (TDD)

**Files:**
- Modify: `src/thoth/modes_cmd.py` — add `_ModesOpSpec` dataclass, `_OP_SPECS` registry, shared validation helpers (`_resolve_write_target`, `_check_builtin_guard`, `_check_override_strict`, `_check_dst_taken`), `_target_descriptor`, argument-parsing dispatcher (`parse_modes_args`, `get_modes_data_from_args`), human-output helpers (`_emit_usage_error`, `_emit_human_receipt`), and the `_op` dispatcher
- Modify: `src/thoth/cli_subcommands/modes.py` — add `_make_modes_leaf(op_name)` click factory and a registration loop that creates one leaf per `_OP_SPECS` entry
- Test: `tests/test_modes_mutations.py` — extend with infra tests

**Why this task exists:** P12 ships six mode mutators (`add`, `set`, `unset`, `remove`, `rename`, `copy`) that share an identical flag set, envelope shape, and error→exit-code mapping. Without consolidation, each command would reimplement the same parsing/validation/click-leaf boilerplate (~330 lines of duplicated code, ~6× drift surface). This task lays the shared infra so per-command tasks (4-9) become thin: each adds *one* `get_modes_<op>_data` function, *one* `_OP_SPECS` entry, and tests.

**Design contract (locked in for implementer):**
- `_OP_SPECS[op_name]` is the single source of truth for an op's CLI surface (positional shape, accepted op-specific flags, required flags, which targeting flags it honors).
- Every mutator's data function returns the same envelope shape: `{schema_version, op, mode, target: {file, tier}, …op-specific keys}` or `{schema_version, op, mode, error, message}`.
- `get_modes_data_from_args(op_name, args, *, config_path)` is the single JSON-path entry point used by Click wrappers — replaces the 6 separate `get_modes_<op>_data_from_args` helpers in earlier drafts of this plan (C1 finding from review).
- `_op(op_name, args, *, config_path)` is the single human-path entry point used by `modes_command` dispatch.
- Click leaves are generated by `_make_modes_leaf(op_name)` — mirrors the existing `_make_legacy_gate` factory pattern in `cli_subcommands/modes.py:56` and `cli_subcommands/providers.py:78`.

### 3A: `_ModesOpSpec` dataclass + empty `_OP_SPECS` registry

- [ ] **Step 3A.1: Write the failing test**

Append to `tests/test_modes_mutations.py`:

```python
def test_op_specs_registry_starts_empty() -> None:
    """The registry is populated by per-command tasks (4-9). Task 3 lays
    the type only — entries land later."""
    from thoth.modes_cmd import _OP_SPECS, _ModesOpSpec

    assert isinstance(_OP_SPECS, dict)
    # Per-command tasks register their specs; at infra-task time the
    # registry can be empty or partial — we only check the type.
    for spec in _OP_SPECS.values():
        assert isinstance(spec, _ModesOpSpec)
```

- [ ] **Step 3A.2: Implement `_ModesOpSpec` + empty registry in `modes_cmd.py`**

Append to `modes_cmd.py` (after the `_TargetFlags` block from Task 1):

```python
@dataclass(frozen=True)
class _ModesOpSpec:
    """Static CLI-surface description of one `thoth modes <op>` mutator.

    Drives both `get_modes_data_from_args` (JSON path) and the click-leaf
    factory `_make_modes_leaf` (human path). Per-command tasks register
    their spec via `_OP_SPECS[op_name] = _ModesOpSpec(...)`.
    """

    name: str
    positionals: tuple[str, ...]
    # Op-specific keyword flags: maps `--flag-name` to attribute name on the
    # parsed-kwargs dict. Example for `add`: {"--model": "model",
    # "--provider": "provider", "--description": "description", "--kind":
    # "kind"}.
    op_flags: dict[str, str]
    required_op_flags: frozenset[str]
    accepts_from_profile: bool = False  # only `copy`
    accepts_override: bool = False  # only `add` and `copy`
    accepts_string: bool = False  # only `set`


_OP_SPECS: dict[str, _ModesOpSpec] = {}
_OP_DATA_FNS: dict[str, Callable[..., dict]] = {}
```

(Add `from collections.abc import Callable` to the imports.)

- [ ] **Step 3A.3: Run, verify pass.**

```bash
uv run pytest tests/test_modes_mutations.py::test_op_specs_registry_starts_empty -x -v
```

- [ ] **Step 3A.4: Commit.**

```bash
git commit -am "feat(p12): _ModesOpSpec dataclass + _OP_SPECS registry (T3A)"
```

### 3B: Shared validation helpers

Five helpers, each one TDD cycle. They take pure inputs and return either `None` (valid) or an error-envelope `dict` so callers can short-circuit by truthiness.

- [ ] **Step 3B.1: Write the failing tests**

```python
def test_resolve_write_target_default(isolated_thoth_home: Path) -> None:
    from thoth.modes_cmd import _TargetFlags, _resolve_write_target

    flags = _TargetFlags()
    context, err = _resolve_write_target(flags, config_path=None)
    assert err is None
    assert context is not None
    assert context.target_path.name == "thoth.config.toml"


def test_resolve_write_target_project_config_conflict() -> None:
    from thoth.modes_cmd import _TargetFlags, _resolve_write_target

    flags = _TargetFlags(project=True, config_path="/tmp/x.toml")
    context, err = _resolve_write_target(flags, config_path=None)
    assert context is None
    assert err is not None
    assert err["error"] == "PROJECT_CONFIG_CONFLICT"


def test_check_builtin_guard_refuses_builtin_for_add_without_override() -> None:
    from thoth.modes_cmd import _check_builtin_guard

    err = _check_builtin_guard("deep_research", override=False, op_name="add")
    assert err is not None
    assert err["error"] == "BUILTIN_NAME_RESERVED"


def test_check_builtin_guard_allows_builtin_for_add_with_override() -> None:
    from thoth.modes_cmd import _check_builtin_guard

    assert _check_builtin_guard("deep_research", override=True, op_name="add") is None


def test_check_builtin_guard_refuses_builtin_for_remove_regardless_of_override() -> None:
    """`remove` and `rename` builtin guards are absolute — `--override`
    doesn't bypass them. Only `add` and `copy` (DST-side) honor override."""
    from thoth.modes_cmd import _check_builtin_guard

    err = _check_builtin_guard("deep_research", override=True, op_name="remove")
    assert err is not None
    assert err["error"] == "BUILTIN_NAME_RESERVED"


def test_check_override_strict_rejects_nonbuiltin_with_override() -> None:
    """BQ resolution: `--override` on a non-builtin name is USAGE_ERROR
    (the flag is the explicit shadow opt-in, not a no-op modifier)."""
    from thoth.modes_cmd import _check_override_strict

    err = _check_override_strict("my_brief", override=True, op_name="add")
    assert err is not None
    assert err["error"] == "USAGE_ERROR"


def test_check_override_strict_allows_nonbuiltin_without_override() -> None:
    from thoth.modes_cmd import _check_override_strict

    assert _check_override_strict("my_brief", override=False, op_name="add") is None
```

- [ ] **Step 3B.2: Implement the five helpers**

Append to `modes_cmd.py`:

```python
def _resolve_write_target(
    flags: _TargetFlags, *, config_path: str | None
) -> tuple[Any | None, dict | None]:
    """Resolve the file write target. Returns (context, error_envelope).

    Caller-supplied `config_path` (from inherited root flag) overrides
    `flags.config_path` only when the latter is None — this matches
    `cli_subcommands/_config_context` semantics.
    """
    from thoth.config_write_context import (
        ConfigTargetConflictError,
        ConfigWriteContext,
    )

    target_path = flags.config_path or config_path
    try:
        context = ConfigWriteContext.resolve(
            project=flags.project, config_path=target_path
        )
    except ConfigTargetConflictError as e:
        return None, {
            "error": "PROJECT_CONFIG_CONFLICT",
            "message": str(e),
        }
    return context, None


def _check_builtin_guard(
    name: str, *, override: bool, op_name: str
) -> dict | None:
    """Return an error envelope if NAME is reserved for the op, else None.

    `add`: refuse builtin unless `override`. `copy(dst)`: refuse builtin
    DST unless `override`. `remove` / `rename`: refuse builtin period
    (override does not bypass — those ops are not "shadow-create" ops).
    `set` / `unset`: never refuses on name; this helper isn't called.
    """
    from thoth.config import BUILTIN_MODES

    if name not in BUILTIN_MODES:
        return None

    if op_name in ("add", "copy") and override:
        return None

    return {
        "error": "BUILTIN_NAME_RESERVED",
        "message": f"'{name}' is a builtin mode and cannot be {op_name}'d directly.",
    }


def _check_override_strict(
    name: str, *, override: bool, op_name: str
) -> dict | None:
    """Return an error envelope if `--override` is passed on a non-builtin.

    Per BQ resolution: `--override` exists only to bypass the builtin
    guard. Passing it where there's no guard to bypass is a USAGE_ERROR.
    Applies symmetrically to `add NAME --override` (where NAME isn't
    builtin) and `copy SRC DST --override` (where DST isn't builtin).
    """
    from thoth.config import BUILTIN_MODES

    if not override:
        return None
    if name in BUILTIN_MODES:
        return None
    return {
        "error": "USAGE_ERROR",
        "message": (
            f"--override is only valid when {op_name.upper()}'s target name "
            f"shadows a builtin mode ({name!r} is not a builtin; "
            f"remove --override or use a different name)."
        ),
    }


def _check_dst_taken(
    dst: str, *, profile: str | None, op_name: str
) -> dict | None:
    """Return error envelope if DST already exists in the destination tier.

    Used by `rename` and `copy` after their op-specific guard checks.
    The actual `_table_at` lookup is in the per-op data function (which
    has the loaded `ConfigDocument`); this helper only formats the error.
    """
    return {
        "error": "DST_NAME_TAKEN",
        "message": (
            f"destination {dst!r} already exists "
            f"in {'profile ' + profile if profile else 'base'} tier"
        ),
    }


def _target_descriptor(path: Path, profile: str | None) -> dict[str, str]:
    """Standard `target: {file, tier}` envelope sub-object."""
    return {
        "file": str(path),
        "tier": f"profiles.{profile}.modes" if profile else "modes",
    }
```

- [ ] **Step 3B.3: Run, verify pass.**

```bash
uv run pytest tests/test_modes_mutations.py -x -v -k "resolve_write_target or check_builtin_guard or check_override_strict"
```

- [ ] **Step 3B.4: Commit.**

```bash
git commit -am "feat(p12): shared validation helpers + target descriptor (T3B)"
```

### 3C: `parse_modes_args` driven by `_OP_SPECS`

- [ ] **Step 3C.1: Write the failing test**

This test is *contractual* — it depends on per-command tasks registering their specs first. Mark it `@pytest.mark.skipif` until at least one spec is registered (Task 4 will register `add`).

```python
def test_parse_modes_args_unknown_op_returns_usage_error() -> None:
    from thoth.modes_cmd import parse_modes_args

    parsed_kwargs, target_flags, err = parse_modes_args("nonexistent_op", [])
    assert err is not None
    assert err["error"] == "USAGE_ERROR"
    assert "unknown" in err["message"].lower()
```

(More targeted parsing tests land in Task 4 once the `add` spec is registered.)

- [ ] **Step 3C.2: Implement `parse_modes_args`**

```python
def parse_modes_args(
    op_name: str, args: list[str]
) -> tuple[dict[str, Any], _TargetFlags, dict | None]:
    """Parse `args` against `_OP_SPECS[op_name]`.

    Returns (op_kwargs, target_flags, error_envelope_or_none).
    `op_kwargs` is a dict of op-specific values (positionals + op flags),
    keyed by the spec's positional names and op_flags values.

    Validates: targeting flags via `_parse_target_flags`; positional
    arity matches spec; only spec-allowed op-specific flags appear;
    required op-flags are present; --from-profile / --override / --string
    only appear on ops that accept them.
    """
    spec = _OP_SPECS.get(op_name)
    if spec is None:
        return ({}, _TargetFlags(), {"error": "USAGE_ERROR", "message": f"unknown op: {op_name}"})

    target_flags, remaining, rc = _parse_target_flags(args)
    if rc != 0:
        return ({}, target_flags, {"error": "USAGE_ERROR", "message": "invalid flag combination"})

    # Per-spec gating of targeting flags that aren't universally accepted.
    if target_flags.from_profile is not None and not spec.accepts_from_profile:
        return ({}, target_flags, {"error": "USAGE_ERROR", "message": f"--from-profile is not valid for `{op_name}`"})
    if target_flags.override and not spec.accepts_override:
        return ({}, target_flags, {"error": "USAGE_ERROR", "message": f"--override is not valid for `{op_name}`"})
    if target_flags.force_string and not spec.accepts_string:
        return ({}, target_flags, {"error": "USAGE_ERROR", "message": f"--string is not valid for `{op_name}`"})

    # Parse op-specific flags + positionals from `remaining`.
    op_kwargs: dict[str, Any] = {}
    positionals: list[str] = []
    i = 0
    while i < len(remaining):
        a = remaining[i]
        if a in spec.op_flags:
            if i + 1 >= len(remaining):
                return ({}, target_flags, {"error": "USAGE_ERROR", "message": f"{a} requires a value"})
            op_kwargs[spec.op_flags[a]] = remaining[i + 1]
            i += 2
        elif a.startswith("--"):
            return ({}, target_flags, {"error": "USAGE_ERROR", "message": f"unknown flag for `{op_name}`: {a}"})
        else:
            positionals.append(a)
            i += 1

    if len(positionals) != len(spec.positionals):
        return ({}, target_flags, {
            "error": "USAGE_ERROR",
            "message": f"`modes {op_name}` takes {' '.join(spec.positionals)}",
        })
    for pname, pvalue in zip(spec.positionals, positionals, strict=True):
        op_kwargs[pname.lower()] = pvalue

    missing = spec.required_op_flags - set(op_kwargs.keys())
    if missing:
        return ({}, target_flags, {
            "error": "USAGE_ERROR",
            "message": f"`modes {op_name}` requires {', '.join(sorted(missing))}",
        })

    return op_kwargs, target_flags, None
```

- [ ] **Step 3C.3: Run, verify pass.**

```bash
uv run pytest tests/test_modes_mutations.py::test_parse_modes_args_unknown_op_returns_usage_error -x -v
```

- [ ] **Step 3C.4: Commit.**

```bash
git commit -am "feat(p12): parse_modes_args dispatcher driven by _OP_SPECS (T3C)"
```

### 3D: `get_modes_data_from_args` + `_op` dispatchers

These two are the single entry points the click leaves and `modes_command` dispatch use.

- [ ] **Step 3D.1: Implement `get_modes_data_from_args` and `_op`**

```python
def get_modes_data_from_args(
    op_name: str, args: list[str], *, config_path: str | None = None
) -> tuple[dict, int]:
    """Single JSON-path entry point: parse `args`, call op data fn, return
    `(data_envelope, exit_code)`. Used by Click wrappers.
    """
    op_kwargs, target_flags, err = parse_modes_args(op_name, args)
    if err is not None:
        envelope = {
            "schema_version": SCHEMA_VERSION,
            "op": op_name,
            **err,
        }
        return envelope, 2 if err["error"] == "USAGE_ERROR" else 1

    data_fn = _OP_DATA_FNS[op_name]
    data = data_fn(
        **op_kwargs,
        project=target_flags.project,
        config_path=target_flags.config_path or config_path,
        profile=target_flags.profile,
        from_profile=target_flags.from_profile if target_flags.from_profile else None,
        force_string=target_flags.force_string,
        override=target_flags.override,
    )
    if data.get("error"):
        exit_code = 2 if data["error"] in ("USAGE_ERROR", "PROJECT_CONFIG_CONFLICT") else 1
    else:
        exit_code = 0
    return data, exit_code


def _op(op_name: str, args: list[str], *, config_path: str | None = None) -> int:
    """Single human-path entry point. Calls `get_modes_data_from_args` and
    emits a one-line confirmation via `_emit_human_receipt`. Returns
    process exit code.
    """
    data, exit_code = get_modes_data_from_args(op_name, args, config_path=config_path)
    return _emit_human_receipt(data, exit_code)


def _emit_usage_error(message: str) -> None:
    _get_console().print(f"[red]Error:[/red] {message}")


def _emit_human_receipt(data: dict, exit_code: int) -> int:
    """Emit a one-line confirmation. JSON emission is owned by
    cli_subcommands/modes.py via emit_json/emit_error — this helper is
    human-only.

    Per-op confirmation strings are extended in each per-command task:
    - add → `Added mode '{name}' (model={model}, kind={kind})`
    - set → `Set {name}.{key} = {value!r}`
    - unset → `Unset {name}.{key}` (+ "(table pruned)" if applicable)
    - remove → `Removed mode '{name}'` (+ "(reverted to builtin)" if applicable)
    - rename → `Renamed '{from}' → '{to}'`
    - copy → `Copied '{from}' → '{to}'`
    """
    if data.get("error"):
        _emit_usage_error(data.get("message", data["error"]))
        return exit_code

    op = data.get("op")
    name = data.get("mode")
    target = data.get("target", {})
    suffix = f" → {target['file']} [{target['tier']}.{name}]" if target else ""

    # Per-op switch — extended by per-command tasks (4-9).
    if op == "add":
        if data.get("created"):
            print(f"Added mode '{name}' (model={data['model']}, kind={data['kind']}){suffix}")
        else:
            print(f"Already exists: mode '{name}' (model={data['model']}){suffix}")
    elif op == "set":
        print(f"Set {name}.{data['key']} = {data['value']!r}{suffix}")
    elif op == "unset":
        pruned = " (table pruned)" if data.get("table_pruned") else ""
        if data.get("removed"):
            print(f"Unset {name}.{data['key']}{pruned}{suffix}")
        else:
            print(f"No-op: {name}.{data['key']} not present")
    elif op == "remove":
        reverted = " (reverted to builtin)" if data.get("reverted_to_builtin") else ""
        if data.get("removed"):
            print(f"Removed mode '{name}'{reverted}")
        else:
            print(f"No-op: mode '{name}' not present")
    elif op == "rename":
        print(f"Renamed '{data['from']}' → '{data['to']}'{suffix}")
    elif op == "copy":
        print(f"Copied '{data['from']}' → '{data['to']}'{suffix}")
    return 0
```

- [ ] **Step 3D.2: Wire dispatch — extend `modes_command`**

Replace `modes_command`'s `ops = {"list": _op_list}` (line ~371) with:

```python
def modes_command(op: str | None, args: list[str], *, config_path: str | None = None) -> int:
    """Dispatch `thoth modes <op>`. Returns a process exit code."""
    if op is None:
        return _op_list(args, config_path=config_path)
    if op == "list":
        return _op_list(args, config_path=config_path)
    if op in _OP_SPECS:
        return _op(op, args, config_path=config_path)
    _get_console().print(f"[red]Error:[/red] unknown modes op: {op}")
    return 2
```

- [ ] **Step 3D.3: Tests for `_emit_human_receipt` per-op format strings live in per-command tasks (4-9).** No new tests at this step — exercised indirectly when each op registers.

- [ ] **Step 3D.4: Commit.**

```bash
git commit -am "feat(p12): get_modes_data_from_args + _op + _emit_human_receipt dispatchers (T3D)"
```

### 3E: Click leaf factory `_make_modes_leaf`

- [ ] **Step 3E.1: Write the failing test (subprocess-level — leaves are registered at module load)**

In `tests/test_modes_cli_integration.py`:

```python
def test_all_six_modes_leaves_registered_at_module_load() -> None:
    """Smoke test: each of the six leaves responds to --help."""
    for op in ("add", "set", "unset", "remove", "rename", "copy"):
        res = run_thoth(["modes", op, "--help"])
        assert res.returncode == 0, f"`thoth modes {op} --help` failed"
        # Click prints the leaf's usage; minimum sanity check.
        assert op in res.stdout.lower()
```

- [ ] **Step 3E.2: Implement `_make_modes_leaf` in `cli_subcommands/modes.py`**

Replace the trailing `# Future: P12 adds add, set, unset leaves here.` comment with:

```python
_MODES_MUTATOR_HONOR: frozenset[str] = frozenset({"config_path", "profile"})


def _make_modes_leaf(op_name: str):
    """Generate a click leaf for `thoth modes <op_name>` driven by
    _OP_SPECS. Mirrors the existing _make_legacy_gate factory pattern.

    The leaf:
    - Uses _PASSTHROUGH_CONTEXT so positional args + op-specific flags
      flow through to modes_cmd's parser
    - Validates inherited options against _MODES_MUTATOR_HONOR (root
      --profile IS honored — overlay-tier writes)
    - Branches on --json: JSON path uses get_modes_data_from_args +
      emit_json/emit_error; human path uses modes_command (which calls
      _op which calls _emit_human_receipt)
    - Inherits root --profile by appending to args when present
    """

    @modes.command(
        name=op_name,
        context_settings=_PASSTHROUGH_CONTEXT,
        help=f"`thoth modes {op_name}` — see `thoth help modes` for examples.",
    )
    @click.argument("args", nargs=-1, type=click.UNPROCESSED)
    @click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
    @click.pass_context
    def _leaf(ctx: click.Context, args: tuple[str, ...], as_json: bool) -> None:
        validate_inherited_options(ctx, f"modes {op_name}", _MODES_MUTATOR_HONOR)
        config_path = inherited_value(ctx, "config_path")
        profile = inherited_value(ctx, "profile")

        rebuilt = list(args)
        if profile is not None and "--profile" not in rebuilt:
            rebuilt.extend(["--profile", profile])

        if as_json:
            from thoth.json_output import emit_error, emit_json
            from thoth.modes_cmd import get_modes_data_from_args

            data, exit_code = get_modes_data_from_args(
                op_name, rebuilt, config_path=config_path
            )
            if data.get("error"):
                emit_error(
                    data["error"], data.get("message", ""), exit_code=exit_code
                )
            emit_json(data)  # NoReturn
            return  # unreachable; emit_json calls sys.exit
        else:
            from thoth.modes_cmd import modes_command

            if config_path is None:
                rc = modes_command(op_name, rebuilt)
            else:
                rc = modes_command(op_name, rebuilt, config_path=config_path)
            sys.exit(rc)

    _leaf.__name__ = f"modes_{op_name}"
    return _leaf


# Generate all six mutator leaves at import time. Per-command tasks
# (4-9) register their _OP_SPECS entries; this loop instantiates the
# matching click leaf for each.
for _op_name in ("add", "set", "unset", "remove", "rename", "copy"):
    _make_modes_leaf(_op_name)
```

- [ ] **Step 3E.3: Run.** Note: `--help` should succeed even before any spec is registered, because Click's help comes from the decorator metadata. The test will pass at this step.

```bash
uv run pytest tests/test_modes_cli_integration.py::test_all_six_modes_leaves_registered_at_module_load -x -v
```

- [ ] **Step 3E.4: Commit.**

```bash
git commit -am "feat(p12): _make_modes_leaf click factory + 6 leaf registrations (T3E)"
```

### 3F: Run periodic full gate

- [ ] **Step 3F.1: Run the full gate**

```bash
uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/ && uv run ty check src/ && uv run pytest -q && ./thoth_test -r --skip-interactive -q
```

Expected: all green. The `_OP_SPECS` registry is empty at this point — the leaves exist but `modes_command(<op>, ...)` returns `unknown modes op` for any `<op>` other than `list`. Per-command tasks (4-9) populate the registry one at a time; each adds a single op and turns its `--help` and dispatch on.

---

## Task 4: `thoth modes add` (TS01a-j + T01)

**Files:**
- Modify: `src/thoth/modes_cmd.py` — add `get_modes_add_data` data function; register in `_OP_SPECS["add"]` and `_OP_DATA_FNS["add"]`
- Test: `tests/test_modes_mutations.py` — extend; `tests/test_modes_cli_integration.py` — extend (subprocess `--json` tests only — JSON emission is owned by the Click wrapper layer)

> **CONSOLIDATION DIRECTIVE — read this before writing any code:**
>
> Task 3 already shipped these — DO NOT re-implement them in Task 4:
> - `_target_descriptor(path, profile)` — use it; don't redefine
> - `_resolve_write_target(target_flags, config_path)` — use it for the
>   `--project + --config PATH` conflict envelope
> - `_check_builtin_guard(name, override, op_name)` — use it for the
>   builtin-name refusal envelope
> - `_check_override_strict(name, override, op_name)` — use it to reject
>   `--override` on non-builtin names (BQ resolution)
> - `_emit_usage_error`, `_emit_human_receipt` — already extended for
>   `add` in Task 3D
> - `_op_add` — DOES NOT EXIST. Dispatch goes through Task 3's `_op(op_name, args, ...)`
> - `get_modes_add_data_from_args` — DOES NOT EXIST. JSON-path callers use
>   Task 3's `get_modes_data_from_args(op_name, args, ...)`
> - The click leaf `modes_add` — already auto-generated by Task 3E's
>   `_make_modes_leaf` factory; nothing to write
>
> **What this task adds:** ONE per-op data function (`get_modes_add_data`)
> + ONE op-spec registration + tests. The code blocks below for tests are
> still authoritative; the implementation code blocks (Steps 4.3, 4.5,
> 4.6, 4.9 as written below) PREDATE the consolidation and contain
> duplicated helpers that ALREADY EXIST in Task 3 — translate them to use
> Task 3 helpers as you implement. The historical content is retained for
> reference; do not commit duplicates.

This task implements the full `add` surface. TDD per TS row, but grouped: write the first 2-3 tests, run them red, implement enough to make them green, then add remaining tests + minimal expansions.

- [ ] **Step 4.1: Write tests for TS01a (happy path) + TS01h (targeting matrix base case)**

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

- [ ] **Step 4.2: Verify both fail with `unknown modes op: add`.**

```bash
uv run pytest tests/test_modes_mutations.py::test_add_happy_path_creates_mode -x -v
```

- [ ] **Step 4.3: Implement `get_modes_add_data` and `_op_add` in `modes_cmd.py`**

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
    """Pure data function for `thoth modes add`. Returns a receipt dict.

    Idempotency: same NAME + same model = no-op exit 0; different model =
    `MODE_EXISTS_DIFFERENT_MODEL` exit 1. Other flags ignored on re-add.

    Builtin-name guard: refuses unless `--override` is set. `--override`
    writes a builtin-name override in the selected tier (base by default,
    profile overlay when `profile` is set).
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

    # Builtin-name guard. --override opts in for either base or profile tier.
    if name in BUILTIN_MODES:
        if not override:
            return {
                "schema_version": SCHEMA_VERSION,
                "op": "add",
                "mode": name,
                "error": "BUILTIN_NAME_RESERVED",
                "message": (
                    f"'{name}' is a builtin. To create an override, "
                    f"use `thoth modes add {name} --model M --override` "
                    f"(optionally with `--profile X`). "
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
        _emit_usage_error("invalid flag combination")
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
                _emit_usage_error("--model requires a value")
                return 2
            model = remaining[i + 1]
            i += 2
        elif a == "--provider":
            if i + 1 >= len(remaining):
                _emit_usage_error("--provider requires a value")
                return 2
            provider = remaining[i + 1]
            i += 2
        elif a == "--description":
            if i + 1 >= len(remaining):
                _emit_usage_error("--description requires a value")
                return 2
            description = remaining[i + 1]
            i += 2
        elif a == "--kind":
            if i + 1 >= len(remaining):
                _emit_usage_error("--kind requires a value")
                return 2
            kind = remaining[i + 1]
            i += 2
        elif a.startswith("--"):
            _emit_usage_error(f"unknown flag: {a}")
            return 2
        elif name is None:
            name = a
            i += 1
        else:
            _emit_usage_error(f"unexpected positional: {a}")
            return 2

    if name is None or model is None:
        _emit_usage_error("modes add takes NAME --model MODEL")
        return 2

    if flags.from_profile is not None:
        _emit_usage_error("--from-profile is only valid for `copy`")
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
    return _emit_human_receipt(data)


def _emit_usage_error(message: str) -> None:
    _get_console().print(f"[red]Error:[/red] {message}")


def _emit_human_receipt(data: dict) -> int:
    """Emit a human one-line confirmation; return exit code.

    JSON emission belongs in cli_subcommands/modes.py via emit_json/emit_error.
    Handler modules must stay JSON-agnostic per the repo JSON boundary.
    """
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
    elif op == "set":
        suffix = (
            f" → {target['file']} [{target['tier']}.{name}]"
            if target
            else ""
        )
        print(f"Set {name}.{data['key']} = {data['value']!r}{suffix}")
    return 0
```

- [ ] **Step 4.4: Wire `add` into `modes_command` dispatch**

In `modes_cmd.py`, replace `ops = {"list": _op_list}` (line 371) with:

```python
    ops = {
        "list": _op_list,
        "add": _op_add,
        # set, unset, remove, rename, copy added in subsequent tasks
    }
```

- [ ] **Step 4.5: Run tests, verify pass.**

```bash
uv run pytest tests/test_modes_mutations.py -x -v
```

Expected: all current tests pass.

- [ ] **Step 4.6: Commit.**

```bash
git commit -am "feat(p12): thoth modes add (TS01a, TS01h base) — happy path + project flag (T01 partial)"
```

- [ ] **Step 4.7: Add remaining `add` test cases**

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


def test_add_override_required_for_builtin(
    isolated_thoth_home: Path,
) -> None:  # TS01j
    from thoth.modes_cmd import modes_command

    # Without --override, even with --profile, builtin name is reserved.
    rc = modes_command(
        "add",
        ["deep_research", "--model", "gpt-4o-mini", "--profile", "dev"],
    )
    assert rc == 1

    # With --override and no --profile, writes a base-tier override.
    rc = modes_command(
        "add",
        ["deep_research", "--model", "gpt-4o-mini", "--override"],
    )
    assert rc == 0
    cfg = Path(isolated_thoth_home) / "config" / "thoth" / "thoth.config.toml"
    assert "[modes.deep_research]" in cfg.read_text()


def test_add_override_allows_builtin_in_profile_tier(
    isolated_thoth_home: Path,
) -> None:  # TS01j
    from thoth.modes_cmd import modes_command

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
    cfg = Path(isolated_thoth_home) / "config" / "thoth" / "thoth.config.toml"
    assert "[profiles.dev.modes.deep_research]" in cfg.read_text()


def test_add_override_on_nonbuiltin_rejected(
    isolated_thoth_home: Path,
) -> None:  # TS01j (strict)
    """`--override` is the builtin-shadow opt-in. Passing it on a
    non-builtin name (where there's no guard to bypass) is a
    USAGE_ERROR — surfaces typos like `--override` for `--provider`."""
    from thoth.modes_cmd import modes_command

    rc = modes_command(
        "add", ["my_brief", "--model", "gpt-4o-mini", "--override"]
    )
    assert rc == 2
```

- [ ] **Step 4.8: Run all `add` tests, verify green.**

```bash
uv run pytest tests/test_modes_mutations.py -x -v -k "add"
```

- [ ] **Step 4.9: Wire the click leaf in `cli_subcommands/modes.py`**

After line 148 (`# Future: P12 adds add, set, unset leaves here.`), add:

```python
_MODES_MUTATOR_HONOR: frozenset[str] = frozenset({"config_path", "profile"})


@modes.command(name="add", context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.pass_context
def modes_add(ctx: click.Context, args: tuple[str, ...], as_json: bool) -> None:
    """Create a new mode."""
    validate_inherited_options(ctx, "modes add", _MODES_MUTATOR_HONOR)
    config_path = inherited_value(ctx, "config_path")
    profile = inherited_value(ctx, "profile")

    from thoth.modes_cmd import get_modes_add_data_from_args, modes_command
    from thoth.json_output import emit_error, emit_json

    rebuilt = list(args)
    if profile is not None and "--profile" not in rebuilt:
        rebuilt.extend(["--profile", profile])

    if as_json:
        # Parse add args in the data/helper layer, then emit from the wrapper.
        # Do not call emit_json/emit_error from modes_cmd.py; the repo JSON
        # boundary keeps handlers JSON-agnostic.
        data, exit_code = get_modes_add_data_from_args(
            rebuilt,
            config_path=config_path,
        )
        if data.get("error"):
            emit_error(data["error"], data.get("message", ""), exit_code=exit_code)
        emit_json(data)

    if config_path is None:
        rc = modes_command("add", rebuilt)
    else:
        rc = modes_command("add", rebuilt, config_path=config_path)
    sys.exit(rc)
```

- [ ] **Step 4.10: Add a subprocess-level integration test**

Create `tests/test_modes_cli_integration.py`:

```python
"""Subprocess-level CLI integration tests for thoth modes mutations (P12 TS07c)."""

from __future__ import annotations

from pathlib import Path
import json

import pytest

from tests._fixture_helpers import run_thoth


def test_modes_add_via_subprocess(isolated_thoth_home: Path) -> None:
    res = run_thoth(["modes", "add", "brief", "--model", "gpt-4o-mini"])
    assert res.returncode == 0
    cfg = Path(isolated_thoth_home) / "config" / "thoth" / "thoth.config.toml"
    assert "[modes.brief]" in cfg.read_text()


def test_modes_add_json_via_subprocess(isolated_thoth_home: Path) -> None:
    res = run_thoth(["modes", "add", "brief", "--model", "gpt-4o-mini", "--json"])
    assert res.returncode == 0
    payload = json.loads(res.stdout)
    assert payload["status"] == "ok"
    data = payload["data"]
    assert data["schema_version"] == "1"
    assert data["op"] == "add"
    assert data["mode"] == "brief"
    assert data["created"] is True
    assert data["target"]["tier"] == "modes"
    assert "file" in data["target"]
```

- [ ] **Step 4.11: Run the integration test, verify green.**

```bash
uv run pytest tests/test_modes_cli_integration.py -x -v
```

- [ ] **Step 4.12: Tick TS01a-j and T01 in PROJECTS.md**

Mark each `- [ ] [P12-TS01a]` … `[P12-TS01j]` and `[P12-T01]` as `[x]` in the lines under the `#### thoth modes add` heading in `PROJECTS.md`.

- [ ] **Step 4.13: Commit.**

```bash
git add src/thoth/modes_cmd.py src/thoth/cli_subcommands/modes.py tests/test_modes_mutations.py tests/test_modes_cli_integration.py PROJECTS.md
git commit -m "feat(p12): thoth modes add — full surface + tests (T01)"
```

- [ ] **Step 4.14: Run periodic full gate (per CLAUDE.md "Periodic full-gate runs")**

```bash
uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/ && uv run ty check src/ && uv run pytest -q && ./thoth_test -r --skip-interactive -q
```

Expected: all green. If red, fix before moving to T02.

---

## Task 5: `thoth modes set` (TS02a-g + T02)

**Files:**
- Modify: `src/thoth/modes_cmd.py` — add `get_modes_set_data` data function; register in `_OP_SPECS["set"]` and `_OP_DATA_FNS["set"]`
- Test: `tests/test_modes_mutations.py` (extend), `tests/test_modes_cli_integration.py` (extend with subprocess `--json` tests)

> **CONSOLIDATION DIRECTIVE — same as Task 4.** All shared infra (write-target resolution, click leaf, `_op_set` dispatch, JSON wrapping, `--from-profile`/`--override` rejection) comes from Task 3. This task adds ONLY: `get_modes_set_data` + op-spec registration + tests. The `_op_set` and click-leaf code blocks below (Steps "5.6"-equivalent) PREDATE Task 3 and should NOT be implemented as written — replace with the registration step:
>
> ```python
> _OP_SPECS["set"] = _ModesOpSpec(
>     name="set",
>     positionals=("NAME", "KEY", "VALUE"),
>     op_flags={},
>     required_op_flags=frozenset(),
>     accepts_string=True,
> )
> _OP_DATA_FNS["set"] = get_modes_set_data
> ```
>
> Note: `set` does NOT register `accepts_override=True` — only `add` and
> `copy` do.

Mirror Task 4's structure. Key behavioral note: `set` IS allowed on builtin names — it implicitly creates an override in the chosen tier. Absent non-builtin names are rejected with `MODE_NOT_FOUND`.

- [ ] **Step 5.1: Write the happy-path test**

```python
def test_set_updates_existing_user_mode(isolated_thoth_home: Path) -> None:  # TS02a
    from thoth.modes_cmd import modes_command

    modes_command("add", ["brief", "--model", "gpt-4o-mini"])
    rc = modes_command("set", ["brief", "temperature", "0.2"])
    assert rc == 0
    cfg = Path(isolated_thoth_home) / "config" / "thoth" / "thoth.config.toml"
    assert "temperature = 0.2" in cfg.read_text()
```

- [ ] **Step 5.2: Run, verify FAIL (`unknown modes op: set`).**

- [ ] **Step 5.3: Implement `get_modes_set_data` and `_op_set` in `modes_cmd.py`**

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

    Setting on a builtin name implicitly creates an overriding
    `[modes.<NAME>]` (or `[profiles.<X>.modes.<NAME>]`) table.
    Absent non-builtin names are rejected with MODE_NOT_FOUND.
    """
    from thoth._secrets import _is_secret_key, _mask_secret
    from thoth.config import BUILTIN_MODES
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
    target_segments = (
        ("profiles", profile, "modes", name) if profile else ("modes", name)
    )
    if name not in BUILTIN_MODES and doc._table_at(target_segments) is None:  # type: ignore[attr-defined]
        return {
            "schema_version": SCHEMA_VERSION,
            "op": "set",
            "mode": name,
            "error": "MODE_NOT_FOUND",
            "message": f"mode {name!r} not found",
        }

    doc.set_mode_value(name, key, value, profile=profile)
    doc.save()
    receipt_value = _mask_secret(value) if _is_secret_key(key) else value

    return {
        "schema_version": SCHEMA_VERSION,
        "op": "set",
        "mode": name,
        "key": key,
        "value": receipt_value,
        "wrote": True,
        "target": _target_descriptor(context.target_path, profile),
    }


def _op_set(args: list[str], *, config_path: str | None = None) -> int:
    flags, remaining, rc = _parse_target_flags(args)
    if rc != 0:
        _emit_usage_error("invalid flag combination")
        return 2

    if flags.from_profile is not None:
        _emit_usage_error("--from-profile is only valid for `copy`")
        return 2
    if flags.override:
        _emit_usage_error("--override is only valid for `add` or `copy`")
        return 2

    if len(remaining) != 3:
        _emit_usage_error("modes set takes NAME KEY VALUE")
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
    return _emit_human_receipt(data)
```

Register in dispatch:

```python
    ops = {
        "list": _op_list,
        "add": _op_add,
        "set": _op_set,
    }
```

- [ ] **Step 5.4: Verify pass, commit.**

```bash
git commit -am "feat(p12): thoth modes set — happy path (T02 partial)"
```

- [ ] **Step 5.5: Add remaining set tests**

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


def test_set_absent_nonbuiltin_errors(isolated_thoth_home: Path) -> None:  # TS02e
    from thoth.modes_cmd import modes_command

    rc = modes_command("set", ["missing_mode", "model", "gpt-4o-mini"])
    assert rc == 1


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
```

TS02g (`--json`) belongs in `tests/test_modes_cli_integration.py` because JSON emission is owned by the Click wrapper. Add a subprocess test that asserts top-level `status == "ok"` and `data` fields for `schema_version`, `op`, `mode`, `key`, `value`, `wrote`, and `target`; include a secret-like key case that verifies `data["value"]` is masked.

- [ ] **Step 5.6: Wire `set` click leaf in `cli_subcommands/modes.py`**

Add after the `modes_add` definition:

```python
@modes.command(name="set", context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.pass_context
def modes_set(ctx: click.Context, args: tuple[str, ...], as_json: bool) -> None:
    """Set a key on a mode."""
    validate_inherited_options(ctx, "modes set", _MODES_MUTATOR_HONOR)
    config_path = inherited_value(ctx, "config_path")
    profile = inherited_value(ctx, "profile")
    from thoth.modes_cmd import get_modes_set_data_from_args, modes_command
    from thoth.json_output import emit_error, emit_json

    rebuilt = list(args)
    if profile is not None and "--profile" not in rebuilt:
        rebuilt.extend(["--profile", profile])

    if as_json:
        data, exit_code = get_modes_set_data_from_args(
            rebuilt,
            config_path=config_path,
        )
        if data.get("error"):
            emit_error(data["error"], data.get("message", ""), exit_code=exit_code)
        emit_json(data)

    if config_path is None:
        rc = modes_command("set", rebuilt)
    else:
        rc = modes_command("set", rebuilt, config_path=config_path)
    sys.exit(rc)
```

- [ ] **Step 5.7: Run all `set` tests + integration, verify green.**

```bash
uv run pytest tests/test_modes_mutations.py tests/test_modes_cli_integration.py -x -v -k "set"
```

- [ ] **Step 5.8: Tick TS02a-g and T02 in PROJECTS.md, commit.**

```bash
git add src/thoth/modes_cmd.py src/thoth/cli_subcommands/modes.py tests/test_modes_mutations.py tests/test_modes_cli_integration.py PROJECTS.md
git commit -m "feat(p12): thoth modes set — full surface + tests (T02)"
```

---

## Task 6: `thoth modes unset` (TS03a-g + T03)

> **CONSOLIDATION DIRECTIVE (applies to Tasks 6, 7, 8, 9):**
>
> Each per-command task adds ONLY a `get_modes_<op>_data` data function +
> op-spec registration + tests. ALL of the following come from Task 3 and
> must NOT be re-implemented:
> - Click leaves — auto-generated by `_make_modes_leaf` factory
> - `_op_<op>` per-op CLI wrappers — DO NOT EXIST; Task 3's `_op(op_name, args, ...)` is the single dispatcher
> - `get_modes_<op>_data_from_args` per-op parser helpers — DO NOT EXIST; Task 3's `get_modes_data_from_args(op_name, args, ...)` is the single dispatcher
> - JSON envelope wrapping — owned by `cli_subcommands/modes.py` via `emit_json`/`emit_error`; data functions return plain receipt dicts
> - `_emit_human_receipt` per-op format strings — already covered in Task 3D's `_emit_human_receipt` (extend its `elif` chain only if a format is unique)
> - Shared validation: `_resolve_write_target`, `_check_builtin_guard`, `_check_override_strict`, `_check_dst_taken`, `_target_descriptor` — all in Task 3
>
> The historical "wire click leaf" / "_op_<op>" sub-steps below are RETAINED for behavioral reference but supersede them with: register the op-spec, register the data fn, run the integration tests.

- [ ] **6.1:** Write happy-path TS03a test (`unset` drops a key, `cfg.read_text()` no longer contains it).
- [ ] **6.2:** Verify FAIL with `unknown modes op: unset` (the Task 3E click leaf exists, but Task 3D's dispatcher rejects the op until it's registered).
- [ ] **6.3:** Implement `get_modes_unset_data(name, key, *, project, config_path, profile)`:
  - Call `_resolve_write_target` for the file-axis envelope
  - Reject `--from-profile` / `--override` / `--string` if present (already handled by `parse_modes_args` via op-spec — but defensive check is fine)
  - Use `ConfigDocument.unset_mode_value(profile=...)` which returns `(removed, table_pruned)`
  - If pure-builtin NAME (no user-side override in chosen tier) → return `MODE_NOT_FOUND` envelope (use `BUILTIN_MODES` membership + `_table_at(...)` to disambiguate)
  - Idempotent on absent KEY → return `removed: False` with exit 0
  - Map to data payload `{schema_version, op: "unset", mode, target, key, removed, table_pruned}`
- [ ] **6.4:** Register `_OP_SPECS["unset"] = _ModesOpSpec(name="unset", positionals=("NAME", "KEY"), op_flags={}, required_op_flags=frozenset())` and `_OP_DATA_FNS["unset"] = get_modes_unset_data`.
- [ ] **6.5:** Verify happy-path PASS. Commit `feat(p12): thoth modes unset — happy path + spec registration (T03 partial)`.
- [ ] **6.6:** Add tests for TS03b-g:
  - **TS03b**: unset last key prunes empty `[modes.NAME]` table.
  - **TS03c**: unset overrides on a builtin override → `source` reverts to `builtin` (use `list_all_modes` to assert).
  - **TS03d**: idempotent on absent KEY (exit 0; receipt: `removed=False`).
  - **TS03e**: pure-builtin NAME → exit 1, error code `MODE_NOT_FOUND`.
  - **TS03f**: targeting matrix (`--project`, `--config PATH`, `--profile X` all work via the spec).
  - **TS03g** *(in `tests/test_modes_cli_integration.py`)*: subprocess test asserts `--json` returns `{"status": "ok", "data": {"op": "unset", ..., "removed": bool, "table_pruned": bool}}`.
- [ ] **6.7:** Run all `unset` tests + integration. Verify green.
- [ ] **6.8:** Tick TS03a-g and T03 in PROJECTS.md, commit `feat(p12): thoth modes unset — full surface (T03)`.

---

## Task 7: `thoth modes remove` (TS04a-f + T04)

> Consolidation directive from Task 6 applies. ONLY add a data fn + spec registration + tests.

- [ ] **7.1:** Write TS04a happy-path test: `remove` drops `[modes.brief]` after a prior `add`.
- [ ] **7.2:** Verify FAIL with `unknown modes op: remove`.
- [ ] **7.3:** Implement `get_modes_remove_data(name, *, project, config_path, profile)`:
  - Use `_check_builtin_guard(name, override=False, op_name="remove")` — `remove` builtin guard is **absolute** (override does NOT bypass; only `add` and `copy` honor it).
  - Use `_resolve_write_target` for file-axis envelope.
  - Call `ConfigDocument.remove_mode(profile=...)`.
  - Distinguish "removed user mode" vs "reverted override": if NAME was in `BUILTIN_MODES` AND the table existed AND was removed → `reverted_to_builtin=True`.
  - Absent (non-builtin) NAME → no-op exit 0, `removed=False`, `reverted_to_builtin=False`.
  - Data payload: `{schema_version, op: "remove", mode, target, removed, reverted_to_builtin}`.
- [ ] **7.4:** Register `_OP_SPECS["remove"] = _ModesOpSpec(name="remove", positionals=("NAME",), op_flags={}, required_op_flags=frozenset())` and `_OP_DATA_FNS["remove"] = get_modes_remove_data`.
- [ ] **7.5:** Happy-path PASS, commit partial.
- [ ] **7.6:** Add tests for TS04b-f:
  - **TS04b**: remove a builtin override; `list_all_modes` post-check reports `source=builtin` again; envelope has `reverted_to_builtin=True`.
  - **TS04c**: pure-builtin NAME → exit 1, `BUILTIN_NAME_RESERVED`.
  - **TS04d**: idempotent on absent NAME.
  - **TS04e**: targeting matrix.
  - **TS04f** *(in `tests/test_modes_cli_integration.py`)*: subprocess `--json` test for `{op: "remove", ..., removed, reverted_to_builtin}`.
- [ ] **7.7:** Run, verify green.
- [ ] **7.8:** Tick TS04a-f and T04 in PROJECTS.md, commit `feat(p12): thoth modes remove — full surface (T04)`.

---

## Task 8: `thoth modes rename` (TS05a-h + T05)

> Consolidation directive from Task 6 applies. ONLY add a data fn + spec registration + tests.

- [ ] **8.1:** Write TS05a test: `rename old new` works for a user-only mode.
- [ ] **8.2:** Verify FAIL with `unknown modes op: rename`.
- [ ] **8.3:** Implement `get_modes_rename_data(old, new, *, project, config_path, profile)`:
  - Use `_check_builtin_guard(old, override=False, op_name="rename")` — `rename` builtin guard is absolute.
  - Detect refusals (OLD overridden builtin, NEW is builtin, NEW exists in dst tier, OLD absent) using `_table_at` + `BUILTIN_MODES` membership.
  - Use `_resolve_write_target` for file-axis envelope.
  - Call `ConfigDocument.rename_mode(profile=...)`.
  - Data payload: `{schema_version, op: "rename", mode: new, from: old, to: new, target, renamed}`.
- [ ] **8.4:** Register `_OP_SPECS["rename"] = _ModesOpSpec(name="rename", positionals=("OLD", "NEW"), op_flags={}, required_op_flags=frozenset())` and `_OP_DATA_FNS["rename"] = get_modes_rename_data`.
- [ ] **8.5:** Happy path PASS. Commit partial.
- [ ] **8.6:** Add tests TS05b-h covering each refusal case + targeting matrix + `--json` (subprocess). The detection logic is the meat of this task — write a separate test per refusal so failure modes are unambiguous.
- [ ] **8.7:** Run, verify green.
- [ ] **8.8:** Tick TS05a-h and T05 in PROJECTS.md, commit `feat(p12): thoth modes rename — full surface (T05)`.

---

## Task 9: `thoth modes copy` (TS06a-h, g1-g5 + T06)

- [ ] **9.1:** Write TS06g1 test (base→base) — the simplest direction:

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

- [ ] **9.2:** Verify FAIL with `unknown modes op: copy`.

- [ ] **9.3:** Implement `get_modes_copy_data(src, dst, *, project, config_path, profile, from_profile, override)`:

  - **Use Task 3 helpers**: `_check_builtin_guard(dst, override, "copy")` for DST builtin guard (override DOES bypass for `copy`); `_check_override_strict(dst, override, "copy")` for the BQ-strict rejection on non-builtin DST + override; `_resolve_write_target` for the file-axis envelope.
  - **SRC resolution**: read from `[modes.SRC]` if no `from_profile`, else `[profiles.<X>.modes.SRC]`. If SRC is in `BUILTIN_MODES` AND no user-side override exists in the source tier, **layer with `BUILTIN_MODES`** before writing — pre-populate a temporary dict from the builtin and the user override (if any), then call `ConfigDocument.set_mode_value` for each key on DST. (The primitive doesn't know about `BUILTIN_MODES`, so the CLI layer does the layering.)
  - **DST validation**: `_table_at` for DST in destination tier; if exists → return `DST_NAME_TAKEN` envelope (use `_check_dst_taken` helper from Task 3).
  - **Refusal cases**: SRC absent → `MODE_NOT_FOUND` exit 1. DST conflict → `DST_NAME_TAKEN` exit 1.
  - **Data payload**: `{schema_version, op: "copy", mode: dst, from: src, to: dst, source_tier, target, copied}` — `source_tier` is `"modes"` or `"profiles.<X>.modes"`; `target.tier` reflects DST.

- [ ] **9.4:** Register `_OP_SPECS["copy"] = _ModesOpSpec(name="copy", positionals=("SRC", "DST"), op_flags={}, required_op_flags=frozenset(), accepts_from_profile=True, accepts_override=True)` and `_OP_DATA_FNS["copy"] = get_modes_copy_data`.

- [ ] **9.5:** TS06g1 PASS. Commit partial.

- [ ] **9.6:** Add tests for TS06a-c (read patterns), TS06d-f (refusals), TS06g2-g4 (other directions), TS06g5 (targeting), TS06h (JSON):

  - **TS06a**: SRC is builtin (`deep_research`, no user override) → DST table contains the builtin's keys (`provider`, `model`, `kind`, `description`, `system_prompt`, etc.).
  - **TS06b**: SRC is user-only.
  - **TS06c**: SRC is overridden — DST gets the *effective* (builtin layered with override) keys.
  - **TS06d-e**: DST refusals, plus `copy SRC <builtin> --override` success for base and profile destination tiers. Symmetric with `add`'s strict-on-non-builtin rule: `copy src new_dst --override` (where `new_dst` is not a builtin) is rejected with `USAGE_ERROR` exit 2 — `--override` is the explicit builtin-shadow opt-in, not a no-op modifier.
  - **TS06f**: SRC absent.
  - **TS06g2**: base → overlay (`--profile dev` on DST).
  - **TS06g3**: overlay → base (`--from-profile dev`, no `--profile`).
  - **TS06g4**: overlay → overlay cross-profile (`--from-profile dev --profile ci`).
  - **TS06g5**: file targeting (`--project`, `--config PATH`).
  - **TS06h** *(in `tests/test_modes_cli_integration.py`)*: subprocess `--json` shape with `source_tier` field.

- [ ] **9.7:** Run, verify green.

- [ ] **9.8:** Tick TS06a-h, g1-g5 and T06 in PROJECTS.md. Commit `feat(p12): thoth modes copy — 4 directions (T06)`.

---

## Task 10: Cross-cutting (TS07a-e + T07 help)

- [ ] **10.1: TS07a — tomlkit comment-preservation across all 6 mutations × 6 targeting combos**

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
    "case_name,targeting",
    [
        ("user-base", []),
        ("user-profile", ["--profile", "dev"]),
        ("project-base", ["--project"]),
        ("project-profile", ["--project", "--profile", "dev"]),
        ("config-base", ["--config", "{custom_config}"]),
        ("config-profile", ["--config", "{custom_config}", "--profile", "dev"]),
    ],
)
def test_tomlkit_preserves_top_comment(
    isolated_thoth_home: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    op: str,
    args: list[str],
    case_name: str,
    targeting: list[str],
) -> None:
    from thoth.modes_cmd import modes_command

    custom_config = tmp_path / "custom.toml"
    resolved_targeting = [
        str(custom_config) if token == "{custom_config}" else token
        for token in targeting
    ]
    if "--project" in resolved_targeting:
        monkeypatch.chdir(tmp_path)
        cfg = tmp_path / "thoth.config.toml"
    elif "--config" in resolved_targeting:
        cfg = custom_config
    else:
        cfg = Path(isolated_thoth_home) / "config" / "thoth" / "thoth.config.toml"

    cfg.parent.mkdir(parents=True, exist_ok=True)
    text = (
        '# preserved comment\n'
        'version = "2.0"\n'
        "[modes.x]\n"
        'model = "gpt-4o-mini"\n'
        "temperature = 0.5\n"
    )
    if "--profile" in resolved_targeting:
        text += (
            "\n[profiles.dev.modes.x]\n"
            'model = "gpt-4o-mini"\n'
            "temperature = 0.5\n"
        )
    cfg.write_text(text)

    rc = modes_command(op, args + resolved_targeting)
    assert rc == 0, f"op={op}, case={case_name}"
    text = cfg.read_text()
    assert "# preserved comment" in text, (
        f"top comment lost by op={op}, case={case_name}"
    )
```

- [ ] **10.2: TS07b — `SCHEMA_VERSION` constant uniformity**

```python
def test_schema_version_constant_uniform() -> None:
    from thoth.modes_cmd import SCHEMA_VERSION

    assert SCHEMA_VERSION == "1"
    # Sanity: all envelope-emitting data functions stamp this constant.
    from thoth.modes_cmd import (
        get_modes_add_data,
        get_modes_copy_data,
        get_modes_remove_data,
        get_modes_rename_data,
        get_modes_set_data,
        get_modes_unset_data,
    )
    assert all(
        callable(fn)
        for fn in (
            get_modes_add_data,
            get_modes_set_data,
            get_modes_unset_data,
            get_modes_remove_data,
            get_modes_rename_data,
            get_modes_copy_data,
        )
    )
    # Each is exercised in earlier task tests. This is a regression
    # tripwire: if the constant changes, every test calling it should
    # be updated in lockstep.
```

- [ ] **10.3: TS07c — subprocess test per op (extends `tests/test_modes_cli_integration.py`)**

For each of the 6 ops, a `run_thoth([...])` test that exits 0 on the happy path. Six small tests.

- [ ] **10.4: TS07d — help epilog content**

Test that `thoth help modes` (or `thoth modes --help`) output mentions all six new ops and the `--profile` / `--config PATH` / `--override` / `--from-profile` flags. Use `subprocess.run(...)` and `assert "modes set" in stdout`, etc.

- [ ] **10.5: TS07e — layering test**

```python
def test_layering_overlay_wins_when_active(isolated_thoth_home: Path) -> None:  # TS07e
    """When [modes.X] and [profiles.dev.modes.X] both exist:
    `thoth modes list --name X` reflects base; `--profile dev` reflects overlay."""
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

- [ ] **10.6: T07 — Help integration**

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
            "  thoth modes copy SRC DST [--from-profile X] [--override]",
            "",
            "All mutators support: --project | --config PATH | --profile X | --json.",
            "Use --override with add/copy to create a builtin-name override in the selected tier.",
        ):
            formatter.write_text(line)
```

- [ ] **10.7: Tick TS07a-e and T07 in PROJECTS.md, commit `feat(p12): cross-cutting tests + help integration (T07)`.**

---

## Task 11: Regression + finalize (TS08, glyph flip [~] → [x])

- [ ] **11.1: Run the full gate**

```bash
uv run ruff check src/ tests/ && \
uv run ruff format --check src/ tests/ && \
uv run ty check src/ && \
uv run pytest -q && \
./thoth_test -r --skip-interactive -q
```

Expected: all green. If anything is red, fix at root cause and re-run before flipping the glyph.

- [ ] **11.2: Verify P11 read paths still work**

Manual smoke test (the `Manual Verification` checklist from PROJECTS.md):

```bash
thoth modes list
thoth modes list --json
thoth modes list --name deep_research
thoth modes list --source builtin
thoth modes list --kind background
thoth modes list --name deep_research --full
```

All must produce the same output as before P12 (the read paths are unchanged — TS08 confirms).

- [ ] **11.3: Tick TS08 and "Regression Test Status" in PROJECTS.md.**

- [ ] **11.4: Flip P12 trunk glyph `[~]` → `[x]`**

Edit `PROJECTS.md` line 1241: change `## [~] Project P12:` → `## [x] Project P12:`.

- [ ] **11.5: Final commit**

```bash
git add PROJECTS.md
git commit -m "feat(p12): close P12 — full mutation surface for thoth modes (v2.12.0)"
```

The commit subject deliberately uses `feat(p12):` so release-please picks it up as a v2.12.0-bump candidate per the project's automated-release contract (CLAUDE.md "Releases are automated by release-please").

- [ ] **11.6: Push and merge the worktree**

```bash
cd /Users/stevemorin/c/thoth-worktrees/p12-modes-editing
git push -u origin p12-modes-editing
gh pr create --title "P12: CLI Mode Editing — thoth modes mutations (v2.12.0)" --body "$(cat <<'EOF'
## Summary

- Adds the mutation half of \`thoth modes\`: \`add\`, \`set\`, \`unset\`, \`remove\`, \`rename\`, \`copy\`
- Mirrors \`thoth config profiles\` (P21b) precedent; diverges where mode semantics require (builtins, model-on-create, empty-table pruning)
- Integrates with P18 \`kind\` field and P21* profile-overlay tier; root \`--profile X\` writes overlay; new \`--override\` (builtin-name override opt-in for add/copy) and \`--from-profile X\` (copy SRC tier) flags

## Test plan

- [ ] \`uv run pytest tests/test_modes_mutations.py tests/test_modes_cli_integration.py tests/test_config_document_modes.py -v\`
- [ ] \`./thoth_test -r --skip-interactive -q\`
- [ ] Manual: \`thoth modes add my_brief --model gpt-4o-mini\` then \`thoth modes list\` shows it as \`source=user\`
- [ ] Manual: \`thoth modes set deep_research parallel false\` then \`thoth modes list --name deep_research\` shows \`source=overridden\`
- [ ] Manual: \`thoth modes copy deep_research custom_research --profile dev\` writes to \`[profiles.dev.modes.custom_research]\`

Closes P12.
EOF
)"
```

---

## Plan Self-Review Notes

This section is metadata for plan reviewers, not execution steps.

**Spec coverage check:** Every task in PROJECTS.md `### Tests & Tasks` (TS01a-j, TS02a-g, TS03a-g, TS04a-f, TS05a-h, TS06a-h plus g1-g5, TS07a-e, TS08, T01-T07) is covered:

- Shared infra (Tasks 1-3): `_parse_target_flags`, `_ModesOpSpec`, `_OP_SPECS`/`_OP_DATA_FNS`, `_resolve_write_target`, `_check_builtin_guard`, `_check_override_strict`, `_check_dst_taken`, `_target_descriptor`, `parse_modes_args`, `get_modes_data_from_args`, `_op`, `_emit_human_receipt`, `_make_modes_leaf` — used by all per-command tasks.
- TS01a-j → Task 4 steps 4.1, 4.7
- TS02a-g → Task 5 steps 5.1, 5.5
- TS03a-g → Task 6 steps 6.1, 6.6
- TS04a-f → Task 7 steps 7.1, 7.6
- TS05a-h → Task 8 steps 8.1, 8.6
- TS06a-h, g1-g5 → Task 9 steps 9.1, 9.6
- TS07a-e → Task 10 steps 10.1, 10.2, 10.3, 10.4, 10.5
- TS08 → Task 11 step 11.1
- T01-T07 → Tasks 4-10 (each per-command task delivers its T row through the data fn + spec registration; T07 = help integration in Task 10.6)

**Type consistency check:**

- `SCHEMA_VERSION` is a module-level string `"1"` in `modes_cmd.py`; all data functions stamp it.
- `_TargetFlags` dataclass owns the targeting/output-flag bag; `_parse_target_flags(args)` returns `(flags, remaining, rc)`.
- `_target_descriptor(path, profile)` returns `{file, tier}`; every mutator's envelope has `target` of this shape.
- `ConfigDocument` mode primitives all accept `profile: str | None = None` (kw-only) for destination tier selection, plus `from_profile` on `copy_mode`.
- Click leaves use `_PASSTHROUGH_CONTEXT` and the new `_MODES_MUTATOR_HONOR` policy (`{"config_path", "profile"}`).

**Placeholder scan:** No "TBD" / "fill in details" / "similar to Task N" — every step has its actual content. The condensed Tasks 5–8 (which abbreviate TS rows by reference rather than full code) explicitly call out the assertion the test must make and the implementation behavior, so the engineer can write each test from the spec without consulting another task.

**Spec gaps surfaced:** Resolved during review. TS02e is authoritative: absent non-builtin `set` returns `MODE_NOT_FOUND`; builtin-only names may still implicitly create overrides. `--override` is an add/copy builtin-name opt-in for both base and profile tiers.
