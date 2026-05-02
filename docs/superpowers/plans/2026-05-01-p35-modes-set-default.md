# P35 — `thoth modes set-default` / `unset-default` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `thoth modes set-default NAME` and `thoth modes unset-default` commands plus a runtime resolution change so per-profile `default_mode` overrides the base.

**Architecture:** Mirror the existing `thoth config profiles set-default` pattern: TOML mutation primitives in `ConfigDocument`, pure-data functions in `config_cmd.py`, hand-written click leaves in `cli_subcommands/modes.py`. Extend `_config_default_mode()` in `cli.py` to read `THOTH_DEFAULT_MODE` first, then `profiles.<active>.default_mode`, then `general.default_mode`. Apply a strict same-tier rule when validating `--profile X` for `set-default` only.

**Tech Stack:** Python 3.11+, Click, tomlkit, pytest, ruff/ty, lefthook.

**Spec:** `docs/superpowers/specs/2026-05-01-p35-modes-set-default-design.md`
**Project file:** `projects/P35-modes-set-default.md`
**Worktree:** `/Users/stevemorin/c/thoth-worktrees/p35-modes-set-default` (branch `p35-modes-set-default`)

---

## File structure

| File | Action | Responsibility |
|---|---|---|
| `src/thoth/config_document.py` | Modify | Add `has_profile`, `set_default_mode`, `unset_default_mode`, `default_mode_name` (each accepting optional `profile=` kwarg). |
| `src/thoth/config_write_context.py` | Modify | Add `target_has_profile(name) -> bool` — a convenience wrapper that loads the target document and asks `has_profile`. |
| `src/thoth/config_cmd.py` | Modify | Add `get_modes_set_default_data`, `get_modes_unset_default_data`. Export in `__all__`. |
| `src/thoth/cli_subcommands/modes.py` | Modify | Add hand-written click leaves `modes_set_default`, `modes_unset_default`. Update `_MODES_EPILOG`. |
| `src/thoth/cli.py` | Modify | Update `_config_default_mode()` to honor env + active profile. |
| `tests/test_config_document_modes_default.py` | Create | Unit tests for the four new `ConfigDocument` methods. |
| `tests/test_modes_set_default.py` | Create | Data + CLI tests for `set-default` (validation, tier matrix, same-tier rule, JSON envelope). |
| `tests/test_modes_unset_default.py` | Create | Data + CLI tests for `unset-default` (idempotency, JSON envelope). |
| `tests/test_default_mode_resolution.py` | Create | Unit tests for the `_config_default_mode` precedence chain. |
| `thoth_test/specs/...` | Create | One integration spec exercising end-to-end set-default → ask resolution. |

DRY: shared helpers (`isolated_thoth_home`, `_load_manager`, `_write_context`) are reused everywhere — do not invent new fixtures.

---

## Task 1: ConfigDocument primitives (P35-T01)

**Files:**
- Modify: `src/thoth/config_document.py:73-83` (insert after `default_profile_name`)
- Create: `tests/test_config_document_modes_default.py`

- [ ] **Step 1.1: Write failing test for `default_mode_name` returning None on empty doc**

Create `tests/test_config_document_modes_default.py`:

```python
"""Pure unit tests for ConfigDocument default_mode primitives (P35 T01)."""

from __future__ import annotations

from pathlib import Path

from thoth.config_document import ConfigDocument


def _doc(path: Path) -> ConfigDocument:
    return ConfigDocument.load(path)


def test_default_mode_name_returns_none_when_unset(tmp_path: Path) -> None:
    doc = _doc(tmp_path / "thoth.config.toml")
    assert doc.default_mode_name() is None
    assert doc.default_mode_name(profile="work") is None


def test_set_default_mode_writes_general_key(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_default_mode("deep")
    doc.save()
    text = p.read_text()
    assert "[general]" in text
    assert 'default_mode = "deep"' in text


def test_set_default_mode_writes_profile_key(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.ensure_profile("work")
    doc.set_default_mode("deep", profile="work")
    doc.save()
    text = p.read_text()
    assert "[profiles.work]" in text
    assert 'default_mode = "deep"' in text


def test_default_mode_name_reads_back(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_default_mode("deep")
    doc.set_default_mode("fast", profile="work")
    doc.save()
    doc2 = _doc(p)
    assert doc2.default_mode_name() == "deep"
    assert doc2.default_mode_name(profile="work") == "fast"


def test_unset_default_mode_removes_general_key(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_default_mode("deep")
    assert doc.unset_default_mode() is True
    assert doc.default_mode_name() is None
    assert doc.unset_default_mode() is False  # idempotent


def test_unset_default_mode_leaves_general_table_in_place(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_default_mode("deep")
    doc.unset_default_mode()
    doc.save()
    # B17 precedent: empty [general] table is preserved.
    assert "[general]" in p.read_text()


def test_unset_default_mode_removes_profile_key(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.ensure_profile("work")
    doc.set_default_mode("deep", profile="work")
    assert doc.unset_default_mode(profile="work") is True
    assert doc.default_mode_name(profile="work") is None
    assert doc.unset_default_mode(profile="work") is False


def test_has_profile_true_after_ensure(tmp_path: Path) -> None:
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    assert doc.has_profile("work") is False
    doc.ensure_profile("work")
    assert doc.has_profile("work") is True


def test_has_profile_false_for_general_table(tmp_path: Path) -> None:
    """Sanity: has_profile only checks [profiles.X], not [general]."""
    p = tmp_path / "thoth.config.toml"
    doc = _doc(p)
    doc.set_default_mode("deep")  # creates [general] but no [profiles.*]
    assert doc.has_profile("work") is False
```

- [ ] **Step 1.2: Run tests, verify they fail with AttributeError**

```bash
uv run pytest tests/test_config_document_modes_default.py -x -v
```

Expected: 9 failures, all citing `AttributeError: 'ConfigDocument' object has no attribute 'set_default_mode'` (or similar).

- [ ] **Step 1.3: Implement the four methods in `ConfigDocument`**

In `src/thoth/config_document.py`, immediately after `unset_default_profile_if` (line 83), insert:

```python
    def has_profile(self, name: str) -> bool:
        """Return True iff `[profiles.<name>]` exists in this document."""
        return self._table_at(("profiles", name)) is not None

    def set_default_mode(self, name: str, *, profile: str | None = None) -> None:
        if profile is None:
            self.set_config_value("general.default_mode", name)
            return
        self.set_profile_value(profile, "default_mode", name)

    def unset_default_mode(self, *, profile: str | None = None) -> bool:
        if profile is None:
            return self.unset_config_value("general.default_mode", prune_empty=False)
        return self.unset_profile_value(profile, "default_mode")

    def default_mode_name(self, *, profile: str | None = None) -> str | None:
        if profile is None:
            general = self._table_at(("general",))
            if general is None or "default_mode" not in general:
                return None
            value = general["default_mode"]
        else:
            profile_table = self._table_at(("profiles", profile))
            if profile_table is None or "default_mode" not in profile_table:
                return None
            value = profile_table["default_mode"]
        return value if isinstance(value, str) and value else None
```

- [ ] **Step 1.4: Run tests, verify they pass**

```bash
uv run pytest tests/test_config_document_modes_default.py -x -v
```

Expected: 9 passed.

- [ ] **Step 1.5: Run lint + typecheck**

```bash
uv run ruff check src/thoth/config_document.py tests/test_config_document_modes_default.py
uv run ty check src/thoth/config_document.py
```

Expected: no warnings.

- [ ] **Step 1.6: Commit**

```bash
git add src/thoth/config_document.py tests/test_config_document_modes_default.py
git commit -m "feat(config): add default_mode and has_profile primitives to ConfigDocument"
```

Update the project file:

```bash
# In projects/P35-modes-set-default.md, flip [P35-T01] to [x].
```

Then commit the project tracking update separately:

```bash
git add projects/P35-modes-set-default.md
git commit -m "chore(projects): tick P35-T01 — ConfigDocument primitives"
```

---

## Task 2: ConfigWriteContext — `target_has_profile` helper

**Files:**
- Modify: `src/thoth/config_write_context.py:51-69` (add method after `raw_profile_catalog`)
- Modify: `tests/test_config_document_modes_default.py` (extend with one test for the helper)

- [ ] **Step 2.1: Add failing test for `target_has_profile`**

Append to `tests/test_config_document_modes_default.py`:

```python
def test_target_has_profile_reads_only_target_file(tmp_path: Path) -> None:
    """target_has_profile inspects the target file only — NOT the merged catalog."""
    from thoth.config_write_context import ConfigWriteContext

    target = tmp_path / "custom.toml"
    doc = ConfigDocument.load(target)
    doc.ensure_profile("scoped")
    doc.save()

    ctx = ConfigWriteContext.resolve(project=False, config_path=target)
    assert ctx.target_has_profile("scoped") is True
    assert ctx.target_has_profile("missing") is False
```

- [ ] **Step 2.2: Run, verify failure**

```bash
uv run pytest tests/test_config_document_modes_default.py::test_target_has_profile_reads_only_target_file -x -v
```

Expected: `AttributeError: 'ConfigWriteContext' object has no attribute 'target_has_profile'`.

- [ ] **Step 2.3: Implement helper**

In `src/thoth/config_write_context.py`, after `raw_profile_catalog` (line 69), add:

```python
    def target_has_profile(self, name: str) -> bool:
        """Return True iff `[profiles.<name>]` exists in the target file.

        Same-tier check used by P35's `modes set-default --profile X` rule.
        Inspects ONLY the target file — does not consider the merged
        catalog across user/project tiers.
        """
        if not self.target_path.exists():
            return False
        return self.load_document().has_profile(name)
```

- [ ] **Step 2.4: Run, verify pass**

```bash
uv run pytest tests/test_config_document_modes_default.py -x -v
```

Expected: 10 passed.

- [ ] **Step 2.5: Commit**

```bash
git add src/thoth/config_write_context.py tests/test_config_document_modes_default.py
git commit -m "feat(config): add ConfigWriteContext.target_has_profile for same-tier checks"
```

---

## Task 3: `get_modes_set_default_data` (P35-TS01/02/03 + P35-T02 part 1)

**Files:**
- Modify: `src/thoth/config_cmd.py` (insert after `get_config_profile_unset_default_data`, around line 858)
- Create: `tests/test_modes_set_default.py`

- [ ] **Step 3.1: Write failing tests for set-default**

Create `tests/test_modes_set_default.py`:

```python
"""Tests for `thoth modes set-default NAME` — data layer (P35)."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from thoth.config_cmd import (
    get_config_profile_add_data,
    get_modes_set_default_data,
)
from thoth.errors import ConfigProfileError


def test_set_default_general_writes_user_config(isolated_thoth_home: Path) -> None:
    out = get_modes_set_default_data("deep", project=False, profile=None, config_path=None)
    assert out["wrote"] is True
    assert out["default_mode"] == "deep"
    assert "profile" not in out

    from thoth.paths import user_config_file

    data = tomllib.loads(user_config_file().read_text())
    assert data["general"]["default_mode"] == "deep"


def test_set_default_general_accepts_builtin(isolated_thoth_home: Path) -> None:
    out = get_modes_set_default_data("default", project=False, profile=None, config_path=None)
    assert out["wrote"] is True


def test_set_default_general_rejects_unknown_mode(isolated_thoth_home: Path) -> None:
    with pytest.raises(Exception) as excinfo:
        get_modes_set_default_data(
            "no-such-mode",
            project=False,
            profile=None,
            config_path=None,
        )
    msg = str(excinfo.value)
    assert "no-such-mode" in msg or "not found" in msg.lower()


def test_set_default_project_conflicts_with_config_path(tmp_path: Path) -> None:
    out = get_modes_set_default_data(
        "deep",
        project=True,
        profile=None,
        config_path=tmp_path / "custom.toml",
    )
    assert out["error"] == "PROJECT_CONFIG_CONFLICT"
    assert out["wrote"] is False


def test_set_default_to_custom_config_path(tmp_path: Path) -> None:
    custom = tmp_path / "custom.toml"
    out = get_modes_set_default_data("deep", project=False, profile=None, config_path=custom)
    assert out["wrote"] is True
    data = tomllib.loads(custom.read_text())
    assert data["general"]["default_mode"] == "deep"


# --- Profile scope: same-tier rule ---


def test_set_default_profile_writes_profile_key(isolated_thoth_home: Path) -> None:
    get_config_profile_add_data("work", project=False, config_path=None)
    out = get_modes_set_default_data("deep", project=False, profile="work", config_path=None)
    assert out["wrote"] is True
    assert out["default_mode"] == "deep"
    assert out["profile"] == "work"

    from thoth.paths import user_config_file

    data = tomllib.loads(user_config_file().read_text())
    assert data["profiles"]["work"]["default_mode"] == "deep"


def test_set_default_profile_rejects_when_profile_missing_in_target_user(
    isolated_thoth_home: Path,
) -> None:
    """Same-tier rule: profile must exist in target tier (user, in this case)."""
    with pytest.raises(ConfigProfileError) as excinfo:
        get_modes_set_default_data(
            "deep",
            project=False,
            profile="ghost",
            config_path=None,
        )
    assert "ghost" in str(excinfo.value)


def test_set_default_profile_rejects_when_profile_only_in_other_tier(
    isolated_thoth_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Profile defined only in user; writing to --project tier rejects."""
    get_config_profile_add_data("work", project=False, config_path=None)
    # Switch CWD so project config lands in tmp_path.
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ConfigProfileError):
        get_modes_set_default_data(
            "deep",
            project=True,
            profile="work",
            config_path=None,
        )


def test_set_default_profile_accepts_builtin_mode_cross_tier(
    isolated_thoth_home: Path,
) -> None:
    """β: mode NAME can be a builtin even in profile scope."""
    get_config_profile_add_data("work", project=False, config_path=None)
    out = get_modes_set_default_data(
        "default",
        project=False,
        profile="work",
        config_path=None,
    )
    assert out["wrote"] is True


def test_set_default_profile_rejects_unknown_mode(isolated_thoth_home: Path) -> None:
    get_config_profile_add_data("work", project=False, config_path=None)
    with pytest.raises(Exception) as excinfo:
        get_modes_set_default_data(
            "ghost-mode",
            project=False,
            profile="work",
            config_path=None,
        )
    assert "ghost-mode" in str(excinfo.value)
```

- [ ] **Step 3.2: Run, verify failures**

```bash
uv run pytest tests/test_modes_set_default.py -x -v
```

Expected: all fail with `ImportError: cannot import name 'get_modes_set_default_data'`.

- [ ] **Step 3.3: Implement the data function**

In `src/thoth/config_cmd.py`, immediately after `get_config_profile_unset_default_data` (around line 858), insert:

```python
def get_modes_set_default_data(
    name: str,
    *,
    project: bool,
    profile: str | None = None,
    config_path: str | Path | None = None,
) -> dict:
    """Pure data function for `thoth modes set-default NAME`.

    Validation:
      1. --project + --config PATH → PROJECT_CONFIG_CONFLICT (exit 2).
      2. --profile X → X must exist in the target tier (same-tier rule).
         Else ConfigProfileError (exit 1).
      3. NAME must be resolvable when the default fires:
         general scope → builtins ∪ base [modes.*];
         profile scope → builtins ∪ base [modes.*] ∪ [profiles.X.modes.*].
    """
    from thoth.config import BUILTIN_MODES
    from thoth.errors import ConfigProfileError, ThothError

    if project and config_path is not None:
        envelope = {
            "default_mode": None,
            "wrote": False,
            "path": None,
            "error": "PROJECT_CONFIG_CONFLICT",
        }
        if profile is not None:
            envelope["profile"] = profile
        return envelope

    context = _write_context(project, config_path)

    # Same-tier profile-existence rule (P35).
    if profile is not None and not context.target_has_profile(profile):
        # Build the available list scoped to the target tier so the error
        # message is actionable.
        if context.target_path.exists():
            target_doc = context.load_document()
            target_profiles = sorted(
                _names_under_table(target_doc, ("profiles",))
            )
        else:
            target_profiles = []
        tier_label = (
            "project config" if project else
            f"config file {context.target_path}" if config_path else
            "user config"
        )
        raise ConfigProfileError(
            f"Profile {profile!r} not found in {tier_label}",
            available_profiles=target_profiles,
            source="thoth modes set-default",
        )

    # Mode NAME resolvability check (cross-tier — β rule).
    cm = _load_manager(config_path, profile=profile)
    resolvable = set(BUILTIN_MODES.keys())
    base_modes = cm.get("modes")
    if isinstance(base_modes, dict):
        resolvable.update(base_modes.keys())
    if profile is not None:
        for layer in cm.profile_catalog:
            if layer.name != profile:
                continue
            overlay_modes = layer.data.get("modes") if isinstance(layer.data, dict) else None
            if isinstance(overlay_modes, dict):
                resolvable.update(overlay_modes.keys())

    if name not in resolvable:
        raise ThothError(
            f"Mode {name!r} not found",
            suggestion=f"Available modes: {', '.join(sorted(resolvable))}",
        )

    doc = context.load_document()
    doc.set_default_mode(name, profile=profile)
    doc.save()

    out = {
        "default_mode": name,
        "wrote": True,
        "path": str(context.target_path),
    }
    if profile is not None:
        out["profile"] = profile
    return out


def _names_under_table(doc, segments: tuple[str, ...]) -> list[str]:
    """Helper: list the keys of a nested table, or [] if absent."""
    table = doc._table_at(segments)
    if table is None:
        return []
    return [str(k) for k in table.keys()]
```

Then update `__all__` at the bottom of the file. Find the existing `__all__` block (search for `"get_config_profile_unset_default_data"`) and add `"get_modes_set_default_data"` after it.

- [ ] **Step 3.4: Run tests, verify they pass**

```bash
uv run pytest tests/test_modes_set_default.py -x -v
```

Expected: 10 passed.

If any fail because the `_load_manager` call paths differ from what the test expects, debug by printing the catalog state — do NOT change validation semantics.

- [ ] **Step 3.5: Lint + typecheck**

```bash
uv run ruff check src/thoth/config_cmd.py tests/test_modes_set_default.py
uv run ty check src/thoth/config_cmd.py
```

Expected: clean.

- [ ] **Step 3.6: Commit**

```bash
git add src/thoth/config_cmd.py tests/test_modes_set_default.py
git commit -m "feat(modes): add get_modes_set_default_data with same-tier validation"
```

---

## Task 4: `get_modes_unset_default_data` (P35-TS04 + P35-T02 part 2)

**Files:**
- Modify: `src/thoth/config_cmd.py` (insert immediately after `get_modes_set_default_data`)
- Create: `tests/test_modes_unset_default.py`

- [ ] **Step 4.1: Write failing tests**

Create `tests/test_modes_unset_default.py`:

```python
"""Tests for `thoth modes unset-default` — data layer (P35)."""

from __future__ import annotations

import tomllib
from pathlib import Path

from thoth.config_cmd import (
    get_config_profile_add_data,
    get_modes_set_default_data,
    get_modes_unset_default_data,
)


def test_unset_default_general_removes_key(isolated_thoth_home: Path) -> None:
    get_modes_set_default_data("deep", project=False, profile=None, config_path=None)
    out = get_modes_unset_default_data(project=False, profile=None, config_path=None)
    assert out["removed"] is True

    from thoth.paths import user_config_file

    data = tomllib.loads(user_config_file().read_text())
    assert "default_mode" not in data.get("general", {})
    # B17: empty [general] table is preserved.
    assert "general" in data


def test_unset_default_general_no_file_returns_no_file(tmp_path: Path) -> None:
    custom = tmp_path / "absent.toml"
    out = get_modes_unset_default_data(project=False, profile=None, config_path=custom)
    assert out["removed"] is False
    assert out["reason"] == "NO_FILE"


def test_unset_default_general_key_absent_returns_not_found(
    isolated_thoth_home: Path,
) -> None:
    # Pre-create user config without default_mode.
    from thoth.config_document import ConfigDocument
    from thoth.paths import user_config_file

    doc = ConfigDocument.load(user_config_file())
    doc.save()  # writes empty doc
    out = get_modes_unset_default_data(project=False, profile=None, config_path=None)
    assert out["removed"] is False
    assert out["reason"] == "NOT_FOUND"


def test_unset_default_profile_removes_key(isolated_thoth_home: Path) -> None:
    get_config_profile_add_data("work", project=False, config_path=None)
    get_modes_set_default_data("deep", project=False, profile="work", config_path=None)
    out = get_modes_unset_default_data(project=False, profile="work", config_path=None)
    assert out["removed"] is True
    assert out["profile"] == "work"


def test_unset_default_profile_idempotent_without_profile_check(
    isolated_thoth_home: Path,
) -> None:
    """δ: unset does NOT enforce same-tier profile-existence."""
    out = get_modes_unset_default_data(project=False, profile="never-existed", config_path=None)
    assert out["removed"] is False
    # No ConfigProfileError raised.


def test_unset_default_project_conflicts_with_config_path(tmp_path: Path) -> None:
    out = get_modes_unset_default_data(
        project=True,
        profile=None,
        config_path=tmp_path / "x.toml",
    )
    assert out["error"] == "PROJECT_CONFIG_CONFLICT"
```

- [ ] **Step 4.2: Run, verify failures**

```bash
uv run pytest tests/test_modes_unset_default.py -x -v
```

Expected: all fail with `ImportError`.

- [ ] **Step 4.3: Implement the data function**

In `src/thoth/config_cmd.py`, immediately after `get_modes_set_default_data` (and the `_names_under_table` helper), insert:

```python
def get_modes_unset_default_data(
    *,
    project: bool,
    profile: str | None = None,
    config_path: str | Path | None = None,
) -> dict:
    """Pure data function for `thoth modes unset-default`.

    Idempotent: missing file → NO_FILE; key absent → NOT_FOUND; both exit 0.
    No same-tier profile check (δ rule from P35 spec).
    """
    if project and config_path is not None:
        envelope = {
            "removed": False,
            "path": None,
            "error": "PROJECT_CONFIG_CONFLICT",
        }
        if profile is not None:
            envelope["profile"] = profile
        return envelope

    context = _write_context(project, config_path)
    path = context.target_path
    if not path.exists():
        out = {"removed": False, "path": str(path), "reason": "NO_FILE"}
        if profile is not None:
            out["profile"] = profile
        return out

    doc = context.load_document()
    removed = doc.unset_default_mode(profile=profile)
    if not removed:
        out = {"removed": False, "path": str(path), "reason": "NOT_FOUND"}
        if profile is not None:
            out["profile"] = profile
        return out

    doc.save()
    out = {"removed": True, "path": str(path)}
    if profile is not None:
        out["profile"] = profile
    return out
```

Add `"get_modes_unset_default_data"` to the `__all__` list.

- [ ] **Step 4.4: Run, verify pass**

```bash
uv run pytest tests/test_modes_unset_default.py -x -v
```

Expected: 6 passed.

- [ ] **Step 4.5: Lint + typecheck**

```bash
uv run ruff check src/thoth/config_cmd.py tests/test_modes_unset_default.py
uv run ty check src/thoth/config_cmd.py
```

- [ ] **Step 4.6: Commit**

```bash
git add src/thoth/config_cmd.py tests/test_modes_unset_default.py
git commit -m "feat(modes): add get_modes_unset_default_data (idempotent, no profile check)"
```

---

## Task 5: Click leaves + JSON envelope (P35-T03 + P35-TS06)

**Files:**
- Modify: `src/thoth/cli_subcommands/modes.py` (add hand-written leaves before the `_make_modes_leaf` factory loop)
- Modify: `tests/test_modes_set_default.py` and `tests/test_modes_unset_default.py` (extend with CliRunner tests)

- [ ] **Step 5.1: Add CLI tests for set-default**

Append to `tests/test_modes_set_default.py`:

```python
import json

from click.testing import CliRunner

from thoth.cli import cli


def test_cli_modes_set_default_human(isolated_thoth_home: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["modes", "set-default", "deep"])
    assert result.exit_code == 0, result.output
    assert "deep" in result.output


def test_cli_modes_set_default_json_envelope(isolated_thoth_home: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["modes", "set-default", "deep", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["default_mode"] == "deep"
    assert data["wrote"] is True
    assert "path" in data


def test_cli_modes_set_default_with_profile_json(isolated_thoth_home: Path) -> None:
    runner = CliRunner()
    runner.invoke(cli, ["config", "profiles", "add", "work"])
    result = runner.invoke(
        cli, ["modes", "set-default", "deep", "--profile", "work", "--json"]
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["default_mode"] == "deep"
    assert data["profile"] == "work"


def test_cli_modes_set_default_unknown_mode_exit1(isolated_thoth_home: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["modes", "set-default", "no-such-mode"])
    assert result.exit_code == 1, result.output
    assert "no-such-mode" in result.output or "not found" in result.output.lower()


def test_cli_modes_set_default_project_config_conflict_exit2(
    isolated_thoth_home: Path, tmp_path: Path
) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--config", str(tmp_path / "x.toml"), "modes", "set-default", "deep", "--project"],
    )
    assert result.exit_code == 2, result.output
```

- [ ] **Step 5.2: Add CLI tests for unset-default**

Append to `tests/test_modes_unset_default.py`:

```python
import json

from click.testing import CliRunner

from thoth.cli import cli


def test_cli_modes_unset_default_human(isolated_thoth_home: Path) -> None:
    runner = CliRunner()
    runner.invoke(cli, ["modes", "set-default", "deep"])
    result = runner.invoke(cli, ["modes", "unset-default"])
    assert result.exit_code == 0, result.output


def test_cli_modes_unset_default_json_when_absent(isolated_thoth_home: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["modes", "unset-default", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["removed"] is False
    assert data["reason"] in {"NOT_FOUND", "NO_FILE"}
```

- [ ] **Step 5.3: Run, verify failures (commands not registered)**

```bash
uv run pytest tests/test_modes_set_default.py tests/test_modes_unset_default.py -x -v
```

Expected: CLI tests fail with `Error: No such command 'set-default'.`

- [ ] **Step 5.4: Implement the click leaves**

In `src/thoth/cli_subcommands/modes.py`, immediately after `_MODES_MUTATOR_HONOR` (line 164) and BEFORE `def _make_modes_leaf` (line 167), insert:

```python
@modes.command(name="set-default")
@click.argument("name")
@click.option("--project", "project", is_flag=True, help="Write to project config")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.pass_context
def modes_set_default(
    ctx: click.Context, name: str, project: bool, as_json: bool
) -> None:
    """Persist `general.default_mode` (or `profiles.<X>.default_mode`)."""
    from thoth.config_cmd import get_modes_set_default_data
    from thoth.errors import ConfigProfileError, ThothError
    from thoth.json_output import emit_error, emit_json, emit_thoth_error

    validate_inherited_options(ctx, "modes set-default", _MODES_MUTATOR_HONOR)
    config_path = inherited_value(ctx, "config_path")
    profile = inherited_value(ctx, "profile")

    try:
        data = get_modes_set_default_data(
            name,
            project=project,
            profile=profile,
            config_path=config_path,
        )
    except ConfigProfileError as exc:
        if as_json:
            emit_thoth_error(exc)
        click.echo(f"Error: {exc.message}", err=True)
        if exc.suggestion:
            click.echo(f"Suggestion: {exc.suggestion}", err=True)
        ctx.exit(exc.exit_code)
    except ThothError as exc:
        if as_json:
            emit_thoth_error(exc)
        click.echo(f"Error: {exc.message}", err=True)
        if getattr(exc, "suggestion", None):
            click.echo(f"Suggestion: {exc.suggestion}", err=True)
        ctx.exit(exc.exit_code)

    if as_json:
        if data.get("error") == "PROJECT_CONFIG_CONFLICT":
            emit_error(
                "PROJECT_CONFIG_CONFLICT",
                "--config cannot be used with --project",
                exit_code=2,
            )
        emit_json(data)

    if data.get("error") == "PROJECT_CONFIG_CONFLICT":
        click.echo("Error: --config cannot be used with --project", err=True)
        ctx.exit(2)

    if data.get("profile"):
        click.echo(f"Set default mode to '{data['default_mode']}' for profile '{data['profile']}'")
    else:
        click.echo(f"Set default mode to '{data['default_mode']}'")


@modes.command(name="unset-default")
@click.option("--project", "project", is_flag=True, help="Write to project config")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.pass_context
def modes_unset_default(ctx: click.Context, project: bool, as_json: bool) -> None:
    """Remove `general.default_mode` (or `profiles.<X>.default_mode`)."""
    from thoth.config_cmd import get_modes_unset_default_data
    from thoth.json_output import emit_error, emit_json

    validate_inherited_options(ctx, "modes unset-default", _MODES_MUTATOR_HONOR)
    config_path = inherited_value(ctx, "config_path")
    profile = inherited_value(ctx, "profile")

    data = get_modes_unset_default_data(
        project=project,
        profile=profile,
        config_path=config_path,
    )

    if as_json:
        if data.get("error") == "PROJECT_CONFIG_CONFLICT":
            emit_error(
                "PROJECT_CONFIG_CONFLICT",
                "--config cannot be used with --project",
                exit_code=2,
            )
        emit_json(data)

    if data.get("error") == "PROJECT_CONFIG_CONFLICT":
        click.echo("Error: --config cannot be used with --project", err=True)
        ctx.exit(2)

    if data.get("profile"):
        click.echo(f"Unset default mode for profile '{data['profile']}'")
    else:
        click.echo("Unset default mode")
```

Update `_MODES_EPILOG` (line 40-52) to mention the new commands. Replace the existing block with:

```python
_MODES_EPILOG = """\b
Mutation operations:
  thoth modes add NAME --model MODEL [--description D] [--kind K]
  thoth modes set NAME KEY VALUE
  thoth modes unset NAME KEY
  thoth modes remove NAME
  thoth modes rename OLD NEW
  thoth modes copy SRC DST [--from-profile X] [--override]
  thoth modes set-default NAME
  thoth modes unset-default

All mutators support: --project | --config PATH | --profile X | --json.
Use --override with add/copy to create a builtin-name override in the
selected tier.
"""
```

- [ ] **Step 5.5: Run, verify pass**

```bash
uv run pytest tests/test_modes_set_default.py tests/test_modes_unset_default.py -x -v
```

Expected: all tests pass (15+ in set-default, 8+ in unset-default).

- [ ] **Step 5.6: Visual sanity check**

```bash
uv run thoth modes --help
```

Expected: `set-default` and `unset-default` appear in the command list, and the epilog lists them under "Mutation operations".

- [ ] **Step 5.7: Lint + typecheck**

```bash
uv run ruff check src/thoth/cli_subcommands/modes.py tests/test_modes_set_default.py tests/test_modes_unset_default.py
uv run ty check src/thoth/cli_subcommands/modes.py
```

- [ ] **Step 5.8: Commit**

```bash
git add src/thoth/cli_subcommands/modes.py tests/test_modes_set_default.py tests/test_modes_unset_default.py
git commit -m "feat(cli): add 'thoth modes set-default' and 'unset-default' commands"
```

---

## Task 6: Resolution change in `_config_default_mode` (P35-TS05 + P35-T04)

**Files:**
- Modify: `src/thoth/cli.py:159-161` (replace `_config_default_mode`)
- Create: `tests/test_default_mode_resolution.py`

- [ ] **Step 6.1: Write failing tests for the precedence chain**

Create `tests/test_default_mode_resolution.py`:

```python
"""Tests for `_config_default_mode` precedence chain (P35-TS05)."""

from __future__ import annotations

from pathlib import Path

import pytest

from thoth.cli import _config_default_mode
from thoth.config import ConfigManager
from thoth.config_cmd import get_config_profile_add_data, get_modes_set_default_data


def test_resolution_empty_returns_default(isolated_thoth_home: Path) -> None:
    cm = ConfigManager()
    cm.load_all_layers()
    assert _config_default_mode(cm) == "default"


def test_resolution_general_default_mode(isolated_thoth_home: Path) -> None:
    get_modes_set_default_data("deep", project=False, profile=None, config_path=None)
    cm = ConfigManager()
    cm.load_all_layers()
    assert _config_default_mode(cm) == "deep"


def test_resolution_active_profile_overrides_general(isolated_thoth_home: Path) -> None:
    get_config_profile_add_data("work", project=False, config_path=None)
    get_modes_set_default_data("deep", project=False, profile=None, config_path=None)
    get_modes_set_default_data("fast", project=False, profile="work", config_path=None)

    cm = ConfigManager(profile="work")
    cm.load_all_layers()
    assert _config_default_mode(cm) == "fast"


def test_resolution_profile_without_default_mode_falls_through(
    isolated_thoth_home: Path,
) -> None:
    get_config_profile_add_data("work", project=False, config_path=None)
    get_modes_set_default_data("deep", project=False, profile=None, config_path=None)

    cm = ConfigManager(profile="work")
    cm.load_all_layers()
    assert _config_default_mode(cm) == "deep"


def test_resolution_env_beats_profile(
    isolated_thoth_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    get_config_profile_add_data("work", project=False, config_path=None)
    get_modes_set_default_data("fast", project=False, profile="work", config_path=None)
    monkeypatch.setenv("THOTH_DEFAULT_MODE", "env-mode")

    cm = ConfigManager(profile="work")
    cm.load_all_layers()
    assert _config_default_mode(cm) == "env-mode"


def test_resolution_inactive_profile_default_is_ignored(
    isolated_thoth_home: Path,
) -> None:
    """Profile X has default_mode but X is not active → only general counts."""
    get_config_profile_add_data("work", project=False, config_path=None)
    get_modes_set_default_data("fast", project=False, profile="work", config_path=None)
    get_modes_set_default_data("deep", project=False, profile=None, config_path=None)

    # No --profile → no active profile → fall through to general.
    cm = ConfigManager()
    cm.load_all_layers()
    assert _config_default_mode(cm) == "deep"
```

- [ ] **Step 6.2: Run, verify some pass and some fail**

```bash
uv run pytest tests/test_default_mode_resolution.py -x -v
```

Expected:
- `test_resolution_empty_returns_default` → PASS (current code already returns "default").
- `test_resolution_general_default_mode` → PASS (current code reads `general.default_mode`).
- `test_resolution_active_profile_overrides_general` → FAIL (current code doesn't check active profile).
- `test_resolution_profile_without_default_mode_falls_through` → PASS or FAIL depending on whether `config.get` walks profiles; expected FAIL/PASS based on existing behavior.
- `test_resolution_env_beats_profile` → likely PASS (env injection happens upstream).
- `test_resolution_inactive_profile_default_is_ignored` → PASS.

If `test_resolution_general_default_mode` fails because `_load_manager` differs from the test's manual `ConfigManager().load_all_layers()` flow, debug by printing `cm.data` — do NOT change spec semantics.

- [ ] **Step 6.3: Update `_config_default_mode`**

Replace the existing function in `src/thoth/cli.py` (lines 159-161) with:

```python
def _config_default_mode(config: ConfigManager) -> str:
    env = os.getenv("THOTH_DEFAULT_MODE")
    if env:
        return env

    profile_layer = getattr(config, "active_profile", None)
    if profile_layer is not None:
        data = profile_layer.data if isinstance(profile_layer.data, dict) else {}
        v = data.get("default_mode")
        if isinstance(v, str) and v:
            return v

    raw = config.get("general.default_mode", "default")
    return str(raw) if raw else "default"
```

Verify `import os` is present at the top of `cli.py` (it is — line 1-15 region).

- [ ] **Step 6.4: Run, verify all pass**

```bash
uv run pytest tests/test_default_mode_resolution.py -x -v
```

Expected: 6 passed.

- [ ] **Step 6.5: Run the broader CLI test set to confirm no regression**

```bash
uv run pytest tests/test_cli.py tests/test_modes_cli_integration.py -x -v
```

Expected: pass (no regression in mode dispatch).

- [ ] **Step 6.6: Lint + typecheck**

```bash
uv run ruff check src/thoth/cli.py tests/test_default_mode_resolution.py
uv run ty check src/thoth/cli.py
```

- [ ] **Step 6.7: Commit**

```bash
git add src/thoth/cli.py tests/test_default_mode_resolution.py
git commit -m "feat(cli): honor active profile's default_mode in _config_default_mode"
```

---

## Task 7: Integration test (P35-T06)

**Files:**
- Create: `thoth_test/specs/M*-modes-set-default.toml` (use the next available milestone slot)

- [ ] **Step 7.1: Find the next test ID slot**

```bash
ls thoth_test/specs/ | tail -10
./thoth_test --list | tail -5
```

Identify the next free milestone-test ID (e.g., `M9T-01` if M9T is the next free milestone, or extend the highest existing one). Match the existing naming convention.

- [ ] **Step 7.2: Author the integration test spec**

Create the TOML spec mirroring an existing modes integration entry. Use the mock provider. The test should:

1. `thoth modes set-default deep`
2. Assert exit 0 and that the user config now has `general.default_mode = "deep"`.
3. `thoth ask "test prompt"` (no `--mode`)
4. Assert the resolved mode used was `deep`.
5. `thoth modes unset-default`
6. Assert exit 0, key removed.

If the existing `thoth_test` framework doesn't have an easy hook to assert "the resolved mode used was X" (the prompt path may not log it), a sufficient surrogate is asserting that the run picked the model that's hard-wired to the `deep` mode in `BUILTIN_MODES`.

- [ ] **Step 7.3: Run the new spec in isolation**

```bash
./thoth_test -r --skip-interactive -q -t modes-set-default
```

Expected: pass.

- [ ] **Step 7.4: Run the full thoth_test suite**

```bash
./thoth_test -r --skip-interactive -q
```

Expected: green table.

- [ ] **Step 7.5: Commit**

```bash
git add thoth_test/specs/
git commit -m "test(modes): add integration coverage for set-default → ask resolution"
```

---

## Task 8: Final pre-commit gate + project tracking + PR

**Files:**
- Modify: `projects/P35-modes-set-default.md` (tick remaining tasks)

- [ ] **Step 8.1: Run the full local gate**

```bash
make env-check
just check
just test-lint
just test-typecheck
uv run pytest -q
./thoth_test -r --skip-interactive -q
```

Expected: all green.

- [ ] **Step 8.2: Manual verification of the worked examples**

Run the 8 worked examples from the spec by hand against `tmp` configs. For each, confirm exit code and output match the spec's "Worked examples" table. Capture a brief log in your head — no code commit needed unless something is off.

- [ ] **Step 8.3: Update project file**

Tick all `[ ]` boxes in `projects/P35-modes-set-default.md` to `[x]` (TS01–TS06, T01–T07). Leave T08–T10 unticked until they happen below.

```bash
git add projects/P35-modes-set-default.md
git commit -m "chore(projects): tick P35 implementation tasks"
```

- [ ] **Step 8.4: Push the branch**

```bash
git push -u origin p35-modes-set-default
```

- [ ] **Step 8.5: Open the PR**

```bash
gh pr create --title "feat(modes): set-default / unset-default commands (P35)" --body "$(cat <<'EOF'
## Summary
- Add `thoth modes set-default NAME` and `thoth modes unset-default` parallel to `thoth config profiles set-default`.
- Per-profile `default_mode` now overrides `general.default_mode` when its profile is active.
- Same-tier rule for `--profile X` on `set-default` prevents partial cross-tier `[profiles.X]` writes.

## Test plan
- [ ] `uv run pytest tests/test_modes_set_default.py tests/test_modes_unset_default.py tests/test_default_mode_resolution.py tests/test_config_document_modes_default.py -q`
- [ ] `./thoth_test -r --skip-interactive -q`
- [ ] `make env-check && just check && just test-lint && just test-typecheck`
- [ ] Manual verification of the 8 worked examples in the spec.

## References
- Spec: `docs/superpowers/specs/2026-05-01-p35-modes-set-default-design.md`
- Plan: `docs/superpowers/plans/2026-05-01-p35-modes-set-default.md`
- Project: `projects/P35-modes-set-default.md`
EOF
)"
```

- [ ] **Step 8.6: Close out P35 trunk after merge**

After the PR merges:

```bash
git checkout main
git pull
# Flip P35 trunk row from [ ] to [x] in PROJECTS.md and rename projects/P35-...md
# tasks T08-T10 to [x]; commit on main as a chore.
```

---

## Self-review checklist (run after writing the plan above)

**Spec coverage:**

| Spec section | Plan task |
|---|---|
| Surface | Task 5 (CLI leaves) |
| Tier matrix | Task 3 (data fn) + Task 5 (CLI tests) |
| Validation — same-tier rule | Task 3 (`target_has_profile` + `ConfigProfileError`) |
| Validation — NAME catalog | Task 3 (BUILTIN_MODES ∪ base ∪ overlay) |
| Validation — PROJECT_CONFIG_CONFLICT | Task 3 + Task 4 |
| Unset-default idempotency | Task 4 |
| Resolution change | Task 6 |
| JSON envelope | Task 5 (CLI tests cover envelope shape) |
| Worked examples | Task 8 (manual verification) |
| TDD tests TS01–TS06 | Tasks 1, 3, 4, 5, 6 (interleaved) |

**Type consistency:** `set_default_mode(name, *, profile=None)`, `unset_default_mode(*, profile=None)`, `default_mode_name(*, profile=None)`, `has_profile(name)`, `target_has_profile(name)`, `get_modes_set_default_data(name, *, project, profile, config_path)`, `get_modes_unset_default_data(*, project, profile, config_path)`. Used identically in tasks 1–5.

**No placeholders:** every code block is concrete; every command shows expected output; no "TBD" / "implement later".
