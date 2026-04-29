# P21c Config Filename Standardization — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Tests are written before implementation in every task.

**Goal:** Standardize Thoth's config filename to `thoth.config.toml`. One user-tier location (`$XDG_CONFIG_HOME/thoth/thoth.config.toml`) and two project-tier locations (`./thoth.config.toml` or `./.thoth.config.toml`, mutually exclusive — both present is a hard error). Legacy filenames (`config.toml` in user dir, `thoth.toml`, `.thoth/config.toml`) are no longer read. A "config not found" error path detects legacy files only to enrich the suggestion with rename guidance.

**Architecture:** `paths.py` returns the canonical user path. `ConfigManager` loads exactly the canonical filenames; `_load_project_config_with_path` raises `ConfigAmbiguousError` if both project-tier files exist. A new `detect_legacy_paths()` helper lives in `config.py` and is called *only* by the "config not found" error formatter — never on the happy load path. `thoth init` gains `--user` and `--hidden` flags (mutually exclusive); `--force` semantics extend to `--user`.

**Tech Stack:** Python 3.11+, Click 8.x, tomllib (read), existing `ConfigManager`, existing `init` command path, pytest.

**Spec:** `docs/superpowers/specs/2026-04-28-p21c-config-filename-standardization-design.md`
**Tracking:** `PROJECTS.md` § "Project P21c: Config Filename Standardization"
**Sequencing:** P21c → P21 → P21b preferred (lock canonical names before P21 implementation).

---

## File Map

- Modify: `src/thoth/paths.py` — `user_config_file()` returns the canonical path.
- Modify: `src/thoth/config.py` — `project_config_paths` shrinks to the two canonical names; `_load_project_config_with_path` raises on ambiguity; user-tier load skips legacy; new `detect_legacy_paths()` helper.
- Modify: `src/thoth/errors.py` — add `ConfigNotFoundError`, `ConfigAmbiguousError`.
- Modify: `src/thoth/commands.py` — `init_command` and `get_init_data` accept `user`, `hidden`, `force` parameters; respect mutual exclusion; write to the chosen target.
- Modify: `src/thoth/cli_subcommands/init.py` — add `--user`, `--hidden`, `--force` Click options; enforce mutual exclusion at the Click layer; thread through to `init_command` / `get_init_data`.
- Modify: `src/thoth/help.py`, `src/thoth/cli_subcommands/config.py` — string sweep for canonical filename.
- Modify: `README.md`, `manual_testing_instructions.md` — canonical filename + short "Migrating from earlier Thoth versions" note.
- Modify: `docs/superpowers/specs/2026-04-28-p21-configuration-profiles-design.md`, `.../p21b-...crud-design.md`, `docs/superpowers/plans/2026-04-28-p21-configuration-profiles.md`, `.../p21b-...crud.md` — replace legacy filenames with canonical names.
- Modify: `PROJECTS.md` — task-by-task progress.
- Test: `tests/test_config_filename.py` — new file, owns all P21c scenarios.

P21c does NOT touch profile resolution code (P21) or profile CRUD (P21b) beyond canonical-name string updates in their docs.

---

## Test Scenario Matrix

Every scenario below maps to a named test in `tests/test_config_filename.py`. The matrix is the contract — Task 1 writes these tests first, all failing, before any implementation moves.

### A. User-tier loading

| ID | Scenario | Expected |
|---|---|---|
| A1 | `~/.config/thoth/thoth.config.toml` exists | Loads it; `cm.user_config_path` points to it. |
| A2 | Only legacy `~/.config/thoth/config.toml` exists (canonical absent) | Treated as no user config (existing optional-user-config behavior). Legacy file is **not** loaded. `cm.user_config_path` is the canonical path (which doesn't exist). |
| A3 | Both canonical and legacy user files exist | Canonical loads; legacy ignored silently (no warning, no error — they are different filenames at different paths and ambiguity rule applies only at the project tier). |
| A4 | Neither user file exists, no project file either, command requires config | `ConfigNotFoundError` raised; message lists the canonical user path **and** the canonical project paths. |
| A5 | Same as A4 but legacy `config.toml` is on disk | `ConfigNotFoundError` message additionally names the legacy path with rename target (`thoth.config.toml`). |

### B. Project-tier loading

| ID | Scenario | Expected |
|---|---|---|
| B1 | Only `./thoth.config.toml` exists | Loads it; `cm.project_config_path` points to it. |
| B2 | Only `./.thoth.config.toml` exists | Loads it; `cm.project_config_path` points to it. |
| B3 | Both `./thoth.config.toml` and `./.thoth.config.toml` exist | `ConfigAmbiguousError` raised. Message names both files and tells the user to delete one. No precedence. |
| B4 | Neither canonical project file exists | Returns no project config (existing optional-project-config behavior). |
| B5 | Only legacy `./thoth.toml` exists | Treated as no project config. Legacy file is **not** loaded. |
| B6 | Only legacy `./.thoth/config.toml` exists | Treated as no project config. Legacy file is **not** loaded. |
| B7 | `ConfigNotFoundError` path with legacy `./thoth.toml` on disk | Error suggestion names the legacy file and the rename target. |
| B8 | `ConfigNotFoundError` path with legacy `./.thoth/config.toml` on disk | Error suggestion names the legacy file and the rename target. |

### C. Legacy detection helper

| ID | Scenario | Expected |
|---|---|---|
| C1 | `detect_legacy_paths()` returns only paths that exist | Pure function; no side effects. |
| C2 | Successful load (canonical files present) does NOT call `detect_legacy_paths()` | Spy / monkeypatch confirms zero calls. Regression guard against accidental fallback-by-accident. |
| C3 | `ConfigNotFoundError` formatter calls `detect_legacy_paths()` exactly once | Spy / monkeypatch confirms one call. |

### D. `thoth init` flag combinations

| ID | Invocation | Target | Notes |
|---|---|---|---|
| D1 | `thoth init` | `./thoth.config.toml` | Default project write. |
| D2 | `thoth init --hidden` | `./.thoth.config.toml` | Dotfile form. |
| D3 | `thoth init --user` | `$XDG_CONFIG_HOME/thoth/thoth.config.toml` | User-tier write. Creates parent dir if missing. |
| D4 | `thoth init --user --hidden` | ERROR | Mutual exclusion enforced at Click layer (UsageError). |
| D5 | `thoth init` when `./thoth.config.toml` already exists, no `--force` | Refuses to overwrite; error. |
| D6 | `thoth init --force` when `./thoth.config.toml` exists | Overwrites. |
| D7 | `thoth init --user` when user file exists, no `--force` | Refuses to overwrite; error. |
| D8 | `thoth init --user --force` when user file exists | Overwrites. *(Confirmed in spec §9 Q2.)* |
| D9 | `thoth init --hidden` when `./thoth.config.toml` already exists (no `--force`) | Writes `./.thoth.config.toml`. The next `thoth` invocation hits B3 ambiguity — this is documented but is **not** prevented at `init` time (B3 catches it on next load, with a clearer error than `init` could give pre-write). |
| D10 | `thoth init --hidden --force` when `./.thoth.config.toml` exists | Overwrites `./.thoth.config.toml`. |
| D11 | `thoth init --json --non-interactive` | Honors `--user` and `--hidden` selection in the JSON envelope (`config_path` field reflects target). |

### E. String sweep regression guards

| ID | Scenario | Expected |
|---|---|---|
| E1 | `grep -r "config.toml" src/ tests/` excluding the legacy detector and docstrings | Only canonical references remain. |
| E2 | `grep -r "thoth.toml" src/ tests/` excluding the legacy detector | Only canonical references remain. |
| E3 | `grep -r "\.thoth/config" src/ tests/` excluding the legacy detector | Only canonical references remain. |

E1–E3 run as actual pytest assertions over file contents, not just a grep — the test reads files and asserts no forbidden tokens outside the allowlisted lines.

---

## Task 1: Test Scenario Matrix as Failing Tests

**Files:**
- Create: `tests/test_config_filename.py`

- [ ] **Step 1: Skeleton with imports and fixtures**

```python
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from thoth.config import ConfigManager, detect_legacy_paths
from thoth.errors import ConfigAmbiguousError, ConfigNotFoundError
from thoth.paths import user_config_file


@pytest.fixture
def isolated_xdg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolate XDG_CONFIG_HOME and CWD into tmp_path/{xdg, project}."""
    xdg = tmp_path / "xdg"
    project = tmp_path / "project"
    xdg.mkdir()
    project.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    monkeypatch.chdir(project)
    return tmp_path
```

- [ ] **Step 2: Write A1–A5 user-tier tests** (failing — module/symbols don't exist yet).
- [ ] **Step 3: Write B1–B8 project-tier tests** including the `ConfigAmbiguousError` assertions.
- [ ] **Step 4: Write C1–C3 legacy-detection helper tests.** C2 uses `monkeypatch.setattr` on `thoth.config.detect_legacy_paths` to assert zero calls during a successful load.
- [ ] **Step 5: Write D1–D11 init-flag tests** using `click.testing.CliRunner`. D4 asserts `result.exit_code != 0` and `"mutually exclusive"` in stderr.
- [ ] **Step 6: Write E1–E3 string-sweep tests** that walk `src/` and `tests/` and assert forbidden tokens appear only on allowlisted lines.

- [ ] **Step 7: Verify all tests fail** with `ImportError` / `AttributeError` (symbols don't exist yet) or `AssertionError`. This is the red phase.

```bash
uv run pytest tests/test_config_filename.py -v
# All A/B/C/D/E tests should fail or error.
```

- [ ] **Step 8: Commit**

```bash
git add tests/test_config_filename.py
git commit -m "test(p21c): add failing test scenario matrix for canonical config filename"
```

---

## Task 2: Path Helper and Error Classes

**Files:**
- Modify: `src/thoth/paths.py`
- Modify: `src/thoth/errors.py`

- [ ] **Step 1: Update `user_config_file()`**

```python
# src/thoth/paths.py
def user_config_file() -> Path:
    return user_config_dir() / "thoth.config.toml"
```

Do **not** add a `legacy_user_config_file()` helper. The legacy path lives only inside `detect_legacy_paths()` in Task 3.

- [ ] **Step 2: Add error classes**

```python
# src/thoth/errors.py
class ConfigNotFoundError(ThothError):
    """No canonical Thoth config file found at any expected location."""

class ConfigAmbiguousError(ThothError):
    """Both canonical project-tier config files exist; user must pick one."""
```

Match the existing `ThothError` constructor pattern (message + suggestion) used by `ConfigProfileError`.

- [ ] **Step 3: Verify A1, B1, B2 now pass partially**

A1/B1/B2 should reach further into `ConfigManager` than they did. Some will still fail on Task 3 changes — that's expected. C2 should now fail with `ImportError` on `detect_legacy_paths` (we add it in Task 3).

- [ ] **Step 4: Commit**

```bash
git add src/thoth/paths.py src/thoth/errors.py
git commit -m "feat(p21c): canonical user_config_file() and config error classes"
```

---

## Task 3: Loader Changes

**Files:**
- Modify: `src/thoth/config.py`

- [ ] **Step 1: Update `project_config_paths` and ambiguity check**

```python
# src/thoth/config.py
class ConfigManager:
    def __init__(self, config_path: Path | None = None):
        self.user_config_path = config_path or user_config_file()
        self.project_config_paths = [
            "./thoth.config.toml",
            "./.thoth.config.toml",
        ]
        ...
```

In `_load_project_config_with_path` (or the equivalent helper):

```python
def _load_project_config_with_path(self) -> tuple[dict[str, Any], Path | None]:
    candidates = [Path(p) for p in self.project_config_paths]
    existing = [p for p in candidates if p.exists()]
    if len(existing) > 1:
        raise ConfigAmbiguousError(
            f"Two Thoth config files found in the project root:\n"
            f"  {existing[0]}\n"
            f"  {existing[1]}\n"
            f"\nDelete one before continuing. They are not merged and Thoth "
            f"will not pick between them.",
        )
    if not existing:
        return {}, None
    return self._load_toml_file(existing[0]), existing[0]
```

User-tier load: keep the current `if self.user_config_path.exists()` check; do **not** add a legacy fallback path.

- [ ] **Step 2: Add `detect_legacy_paths()` helper**

```python
# src/thoth/config.py — module level, not on ConfigManager.
LEGACY_USER_FILENAME = "config.toml"
LEGACY_PROJECT_PATHS: tuple[str, ...] = ("./thoth.toml", "./.thoth/config.toml")


def detect_legacy_paths() -> list[Path]:
    """Return any legacy Thoth config files that exist on disk.

    Used to enrich 'config not found' error messages — never to load.
    """
    found: list[Path] = []
    legacy_user = user_config_dir() / LEGACY_USER_FILENAME
    if legacy_user.exists():
        found.append(legacy_user)
    for rel in LEGACY_PROJECT_PATHS:
        p = Path(rel)
        if p.exists():
            found.append(p)
    return found
```

C2 (regression guard) requires that `detect_legacy_paths` is **not** called from any code path that runs during a successful `load_all_layers`. Verify by structuring `config.py` so the only call site is the `ConfigNotFoundError` formatter.

- [ ] **Step 3: Wire `ConfigNotFoundError` raise + formatter**

Identify the call sites that today silently tolerate "no config" vs those that require config to be present. P21c does not change *which* commands require config — it only changes the error message when a required-config command runs without one.

The formatter:

```python
def _format_config_not_found() -> ConfigNotFoundError:
    canonical = [
        str(user_config_file()),
        "./thoth.config.toml",
        "./.thoth.config.toml",
    ]
    legacy = detect_legacy_paths()
    lines = ["No Thoth config found.", "  Looked for:"]
    for path in canonical:
        lines.append(f"    {path}")
    if legacy:
        lines.append("")
        if len(legacy) == 1:
            lines.append(f"  Detected legacy file: {legacy[0]}")
        else:
            lines.append("  Detected legacy files:")
            for p in legacy:
                lines.append(f"    {p}")
        lines.append(
            "  These filenames are no longer read. Rename to "
            "thoth.config.toml (or .thoth.config.toml in the project root)."
        )
    return ConfigNotFoundError("\n".join(lines))
```

- [ ] **Step 4: Run A1–C3**

```bash
uv run pytest tests/test_config_filename.py -k "test_a or test_b or test_c" -v
```

All A and B and C tests should pass.

- [ ] **Step 5: Commit**

```bash
git add src/thoth/config.py
git commit -m "feat(p21c): canonical-only config loading with ambiguity error and legacy-detection helper"
```

---

## Task 4: `thoth init` — `--user`, `--hidden`, `--force`

**Files:**
- Modify: `src/thoth/cli_subcommands/init.py`
- Modify: `src/thoth/commands.py`

- [ ] **Step 1: Update `init_command` / `get_init_data` signatures**

```python
# src/thoth/commands.py
def init_command(
    self,
    config_path: Path | None = None,
    *,
    user: bool = False,
    hidden: bool = False,
    force: bool = False,
    **params,
) -> None:
    if user and hidden:
        raise ThothError(
            "thoth init: --user and --hidden are mutually exclusive",
        )

    target = self._resolve_init_target(config_path, user=user, hidden=hidden)
    if target.exists() and not force:
        raise ThothError(
            f"thoth init: refusing to overwrite existing {target}. "
            f"Pass --force to overwrite.",
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    self._write_default_config(target)
```

```python
def _resolve_init_target(
    self,
    config_path: Path | None,
    *,
    user: bool,
    hidden: bool,
) -> Path:
    if config_path is not None:
        return Path(config_path).expanduser().resolve()
    if user:
        return user_config_file()
    if hidden:
        return Path("./.thoth.config.toml").resolve()
    return Path("./thoth.config.toml").resolve()
```

`get_init_data` mirrors the same parameter set so D11 (JSON envelope reflects target) passes:

```python
def get_init_data(
    *,
    non_interactive: bool,
    config_path: str | None,
    user: bool = False,
    hidden: bool = False,
    force: bool = False,
) -> dict:
    ...
```

- [ ] **Step 2: Update Click leaf**

```python
# src/thoth/cli_subcommands/init.py
@click.command(name="init")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.option("--non-interactive", is_flag=True, help="Skip interactive prompts (required with --json)")
@click.option("--user", "user", is_flag=True, help="Write to the user-tier config (XDG)")
@click.option("--hidden", "hidden", is_flag=True, help="Write to ./.thoth.config.toml instead of ./thoth.config.toml")
@click.option("--force", "force", is_flag=True, help="Overwrite an existing config file")
@click.pass_context
def init(
    ctx: click.Context,
    as_json: bool,
    non_interactive: bool,
    user: bool,
    hidden: bool,
    force: bool,
) -> None:
    if user and hidden:
        raise click.UsageError("--user and --hidden are mutually exclusive")
    ...
```

The `click.UsageError` raise is what makes D4 pass cleanly with a non-zero exit code and a clear message.

- [ ] **Step 3: Run D1–D11**

```bash
uv run pytest tests/test_config_filename.py -k "test_d" -v
```

All D tests pass.

- [ ] **Step 4: Commit**

```bash
git add src/thoth/cli_subcommands/init.py src/thoth/commands.py
git commit -m "feat(p21c): thoth init --user, --hidden, --force flags"
```

---

## Task 5: String Sweep — Source Code

**Files:**
- Modify: `src/thoth/help.py`
- Modify: `src/thoth/cli_subcommands/config.py`
- Modify: any other `src/**/*.py` containing legacy filename literals (audit via `grep`).

- [ ] **Step 1: Inventory**

```bash
grep -rn "config.toml\|thoth.toml\|\.thoth/" src/thoth/ \
  | grep -v "detect_legacy_paths\|LEGACY_USER_FILENAME\|LEGACY_PROJECT_PATHS\|test_"
```

Each remaining hit is a candidate. Update text strings (help, error messages, docstrings) to canonical forms. Code that names paths via `user_config_file()` / `project_config_paths` is already canonical and needs no change.

- [ ] **Step 2: Run E1–E3**

```bash
uv run pytest tests/test_config_filename.py -k "test_e" -v
```

E1–E3 are the regression guards for this sweep.

- [ ] **Step 3: Commit**

```bash
git add src/
git commit -m "refactor(p21c): sweep source strings to canonical thoth.config.toml"
```

---

## Task 6: Documentation Sweep

**Files:**
- Modify: `README.md`
- Modify: `manual_testing_instructions.md`
- Modify: `docs/superpowers/specs/2026-04-28-p21-configuration-profiles-design.md`
- Modify: `docs/superpowers/specs/2026-04-28-p21b-configuration-profiles-crud-design.md`
- Modify: `docs/superpowers/plans/2026-04-28-p21-configuration-profiles.md`
- Modify: `docs/superpowers/plans/2026-04-28-p21b-configuration-profiles-crud.md`
- Audit + modify if found: `CLAUDE.md`, `AGENTS.md`, `planning/*.md`.

- [ ] **Step 1: Inventory doc references**

```bash
grep -rn "config.toml\|thoth.toml\|\.thoth/config" \
  README.md manual_testing_instructions.md docs/ planning/ CLAUDE.md AGENTS.md \
  2>/dev/null
```

- [ ] **Step 2: README — config section + migration note**

Add a short "Migrating from earlier Thoth versions" callout in the config section:

```markdown
### Migrating from earlier Thoth versions

Thoth previously read three different filenames depending on location. Starting with vX.Y.0, the canonical name is `thoth.config.toml` everywhere:

| Old | New |
|---|---|
| `~/.config/thoth/config.toml` | `~/.config/thoth/thoth.config.toml` |
| `./thoth.toml` | `./thoth.config.toml` *or* `./.thoth.config.toml` |
| `./.thoth/config.toml` | `./.thoth.config.toml` *or* `./thoth.config.toml` |

The old filenames are no longer read. Rename them with `mv`. If both `./thoth.config.toml` and `./.thoth.config.toml` exist in the same project, Thoth will refuse to start until one is deleted.
```

- [ ] **Step 3: P21 + P21b spec/plan rewrites**

Per the sequencing preference (P21c → P21 → P21b), the P21 and P21b spec/plan documents are still in draft. Update every legacy filename literal in those four files to canonical forms. Examples to grep for in those four files:

- `./thoth.toml` → `./thoth.config.toml`
- `./.thoth/config.toml` → `./.thoth.config.toml`
- `~/.config/thoth/config.toml` → `~/.config/thoth/thoth.config.toml`

If the P21 spec's "the catalog records the actual project config path (`./thoth.toml` or `./.thoth/config.toml`)" line still exists, replace with the canonical pair `(./thoth.config.toml or ./.thoth.config.toml)`.

- [ ] **Step 4: manual_testing_instructions.md**

Update every smoke test that writes or names a config path. Pay special attention to any test that creates `./thoth.toml` as a fixture — those become `./thoth.config.toml`.

- [ ] **Step 5: Commit**

```bash
git add README.md manual_testing_instructions.md docs/ planning/ CLAUDE.md AGENTS.md
git commit -m "docs(p21c): sweep documentation to canonical thoth.config.toml"
```

---

## Task 7: PROJECTS.md Progress Updates

**Files:**
- Modify: `PROJECTS.md`

- [ ] **Step 1: As each task above lands, check its `[P21c-T##]` / `[P21c-TS##]` box.**
- [ ] **Step 2: Final commit when all P21c tasks are checked**

```bash
git add PROJECTS.md
git commit -m "chore(p21c): mark implementation tasks complete in PROJECTS.md"
```

---

## Final Verification (run before declaring P21c done)

- [ ] `uv run pytest tests/test_config_filename.py tests/test_config.py tests/test_config_cmd.py -v` — all pass.
- [ ] `just check` passes.
- [ ] `./thoth_test -r --skip-interactive -q` passes.
- [ ] `just test-lint` passes.
- [ ] `just test-typecheck` passes.
- [ ] `git diff --check` passes.
- [ ] Manual smoke (one fresh shell):
  - `thoth init` in an empty dir → file at `./thoth.config.toml`.
  - `thoth init --hidden` in another empty dir → file at `./.thoth.config.toml`.
  - Touch both files in the same dir → next `thoth config get general.default_mode` (or any config-loading command) errors with `ConfigAmbiguousError`.
  - `thoth init --user` → file at `~/.config/thoth/thoth.config.toml`.
  - `thoth init --user --hidden` → `UsageError: --user and --hidden are mutually exclusive`.
  - Place a legacy `./thoth.toml`, no canonical → command requiring config errors with the canonical paths listed AND the legacy file named in the suggestion.

---

## Risk Register

| Risk | Mitigation |
|---|---|
| Users on existing installs get a "config not found" error after upgrading. | The error names the legacy file and the rename target. README migration note documents it. Release notes call it out as a breaking change in the version bump. |
| Sequencing slip — P21c lands after P21 implementation. | Task 6 Step 3 already accounts for this: it sweeps P21 and P21b spec/plan docs whether they're draft or already implemented. If P21 is implemented first, add a small follow-up sub-task to also sweep P21's `tests/test_config_profiles.py` literals. |
| Test E1–E3 false positives from third-party docs in `tests/fixtures/`. | The string-sweep test allowlists known fixture paths. Audit during Task 1 Step 6. |
| `init --hidden` after a legacy `./thoth.toml` exists creates a confusing two-file state. | Documented in D9. Spec position: B3 ambiguity catches this on the next load with a clearer message than `init` could give pre-write. If user feedback shows this is too subtle, add a follow-up project that has `init` warn when legacy files are detected at write time. |
