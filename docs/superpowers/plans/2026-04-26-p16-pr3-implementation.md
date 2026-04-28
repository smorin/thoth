# P16 PR3 — Automation Polish: `completion` Subcommand + Universal `--json` — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land v3.0.0's automation-polish commits — add `thoth completion {bash,zsh,fish}` with `--install/--manual/--force/--json`, add `--json` to every data/action admin command via the B-deferred per-handler `get_*_data() -> dict` extraction pattern, wire `shell_complete=` callbacks for TAB completion of operation IDs / mode names / config keys / provider names. Pure additive (no removals).

**Architecture:** Single PR landing as ~20 commits on `main` (no feature branch — user explicit). Each commit is independently reviewable. The `as_json` flag NEVER reaches handlers (per spec §7.2 critical invariant); data functions are pure dict-returners; subcommand wrappers branch on the flag. Option E (mode-aware non-blocking JSON) for `ask`/`resume`: immediate-mode `ask --json` returns full result inline; background-mode `ask --json` auto-async (submit + return op-id envelope); `resume --json` is pure snapshot (never advances state).

**Tech Stack:** Python 3.11+, Click 8.x (with `_THOTH_COMPLETE=<shell>_source thoth` machinery + native `click.Choice` completion), pytest with `CliRunner` + `tmp_path`, existing `isolated_thoth_home` fixture, `./thoth_test` integration runner, `uv run` for all Python invocations.

**Spec:** `docs/superpowers/specs/2026-04-26-p16-pr3-design.md`
**Predecessor specs:**
- `docs/superpowers/specs/2026-04-25-promote-admin-commands-design.md` (original P16; Q4 completion + Q5 `--json`)
- `docs/superpowers/specs/2026-04-26-p16-pr2-design.md` (PR2 breakage + new verbs)

**Predecessor plans (template):**
- `docs/superpowers/plans/2026-04-25-p16-pr1-cli-refactor.md`
- `docs/superpowers/plans/2026-04-26-p16-pr2-implementation.md`

**PROJECTS.md ledger:** "Project P16 PR3" entry (28 task identifiers; this plan groups them into the 20 commits per spec §10).

---

## File Structure

**Create (production):**
- `src/thoth/json_output.py` — `emit_json(data, *, exit_code=0)` and `emit_error(code, message, details=None, *, exit_code=1)` (~40 LOC; Task 1)
- `src/thoth/completion/__init__.py` — package marker (Task 3)
- `src/thoth/completion/script.py` — `generate_script(shell)` and `fenced_block(shell)` (~80 LOC; Task 3)
- `src/thoth/completion/install.py` — `InstallResult` dataclass + `install(shell, *, force=False, manual=False, rc_path=None)` (~120 LOC; Task 3)
- `src/thoth/completion/sources.py` — 5 completer data functions: `operation_ids`, `mode_names`, `config_keys`, `provider_names`, `mode_kind` (~80 LOC; Task 3)
- `src/thoth/cli_subcommands/completion.py` — Click subcommand wiring (~50 LOC; Task 4)

**Create (tests):**
- `tests/test_json_output.py` — Category A: 5 envelope-contract tests (Task 1)
- `tests/test_completion.py` — Category B: 6 script-generation tests (Task 3)
- `tests/test_completion_install.py` — Category C: 10 install-matrix tests (Task 3, expanded T4)
- `tests/test_completion_sources.py` — Category D: 10 data-source tests (Task 3)
- `tests/test_json_envelopes.py` — Category E: parametrized envelope contract per command (Tasks 6–13)
- `tests/test_get_status_data.py` — Category F: `get_status_data` unit tests (Task 7)
- `tests/test_get_list_data.py` — Category F: `get_list_data` unit tests (Task 8)
- `tests/test_get_providers_data.py` — Category F: `get_providers_*_data` unit tests (Task 9)
- `tests/test_get_config_data.py` — Category F: `get_config_*_data` unit tests (Tasks 10–11)
- `tests/test_get_modes_data.py` — Category F: `get_modes_list_data` unit tests (Task 12)
- `tests/test_get_init_data.py` — Category F: `get_init_data` unit tests (Task 6)
- `tests/test_get_resume_snapshot_data.py` — Category F: `get_resume_snapshot_data` unit tests (Task 13)
- `tests/test_json_non_blocking.py` — Category G: 3 Option-E timing-assertion tests (Task 13)
- `tests/test_ci_lint_rules.py` — Category H: 3 meta-tests (Tasks 14–15)

**Modify (production):**
- `src/thoth/cli.py` — register `completion` subcommand (Task 4); wire `shell_complete=` callbacks on existing options (Task 5)
- `src/thoth/help.py` — restore `"completion"` into `ADMIN_COMMANDS` tuple (Task 4) — PR2 T8 removed it as a phantom; PR3 makes it real
- `src/thoth/cli_subcommands/init.py` — add `--json` flag + body branch (Task 6)
- `src/thoth/cli_subcommands/status.py` — add `--json` flag + body branch (Task 7)
- `src/thoth/cli_subcommands/list_cmd.py` — add `--json` flag + body branch (Task 8)
- `src/thoth/cli_subcommands/providers.py` — add `--json` flag to `list/models/check` leaves (Task 9); wire `shell_complete=provider_names` on the `--provider` Click options (Task 5)
- `src/thoth/cli_subcommands/config.py` — add `--json` to `get/set/unset/list/path/edit` leaves (Tasks 10–11); wire `shell_complete=config_keys` on `KEY` argument (Task 5)
- `src/thoth/cli_subcommands/modes.py` — add `--json` flag (Task 12); wire `shell_complete=mode_names` on `--name` (Task 5)
- `src/thoth/cli_subcommands/ask.py` — add `--json` flag + Option-E branching (Task 13)
- `src/thoth/cli_subcommands/resume.py` — add `--json` flag + snapshot branch + `shell_complete=operation_ids` on `OP_ID` (Tasks 5, 13)
- `src/thoth/commands.py` — extract `get_status_data()`, `get_list_data()`, `get_providers_list_data()`, `get_providers_models_data()`, `get_providers_check_data()` siblings (Tasks 7, 8, 9); refactor existing `show_status`/`list_operations`/`providers_list`/`providers_models`/`providers_check` to call data functions then format
- `src/thoth/config_cmd.py` — extract `get_config_get_data()`, `get_config_list_data()`, `get_config_path_data()`, `get_config_set_data()`, `get_config_unset_data()`, `get_config_edit_data()` siblings (Tasks 10–11); refactor existing `_op_*` to call data functions
- `src/thoth/modes_cmd.py` — extract `get_modes_list_data()` sibling (Task 12); refactor `_op_list` to call data function
- `src/thoth/run.py` — add `get_resume_snapshot_data(operation_id)` pure-read function (Task 13)
- `src/thoth/checkpoint.py` — add `list_operation_ids(self) -> list[str]` method on `CheckpointManager` (Task 3) — natural home; spec §6.4 names it; current callsites glob `checkpoint_dir.glob("*.json")` and extract stems

**Modify (docs/release):**
- `pyproject.toml` — verify `click>=8.0` already permits fish (Task 2; no-op if already 8.0+)
- `planning/thoth.prd.v24.md` line 96 — flip F-70 from aspirational to shipped (Task 16)
- `docs/json-output.md` — NEW; envelope-contract reference + per-command schemas (Task 17)
- `README.md` — add "Shell completion" + "JSON output" sections (Task 18)
- `CHANGELOG.md` — append PR3 entries to existing `## [3.0.0]` section's `### Added` (do NOT create a duplicate `[3.0.0]` block; Task 19)
- `PROJECTS.md` — flip P16 PR3 from `[ ]` to `[x]` and check off all 28 task identifiers (Task 20)

**Test paths consumed (no edits):**
- `tests/conftest.py::isolated_thoth_home` — used by Categories C, D, E, F, G fixtures
- `tests/conftest.py::checkpoint_dir`, `make_operation` — used by Categories D, F (for `operation_ids` source), G

---

## Critical implementation rules (apply to every task)

1. **`as_json` flag boundary (spec §7.2 critical invariant).** `as_json` lives ONLY at the subcommand-wrapper layer (the `cli_subcommands/*.py` files). Below that layer — in `commands.py`, `config_cmd.py`, `modes_cmd.py`, `run.py` — the JSON-vs-Rich choice MUST NOT exist. The B-deferred extraction (rule 3) is what makes this possible. The Category H meta-test in T14 enforces it via `Path.read_text() + assert "as_json" not in content` against those three files.
2. **B-deferred extraction pattern (spec §6.5, §6.6).** For each handler that gains `--json`:
   - Extract `get_*_data(...) -> dict | None` as a NEW pure function alongside the existing `show_*()` Rich-printing function (or `_op_*` private function for `config`/`modes`).
   - Refactor `show_*()` / `_op_*` to call `get_*_data()` then format with Rich.
   - Subcommand wrapper picks: `if as_json: emit_json(get_*_data(...)); else: show_*(...)`.
   - The `as_json` flag NEVER reaches the handler module.
   T07 establishes this pattern with the FULL code shown for both functions; T08–T12 reference it back but show the concrete delta (`get_*_data` body + wrapper branch). NO "similar to T07" hand-waves.
3. **`LEFTHOOK=0` discipline.** Tasks T05–T13 may produce transitional `./thoth_test` states (the integration suite already passes after PR2; the PR3 additions won't regress it, but if they do during a single transitional task, document the failure ID in the commit body and proceed). For each of those tasks, the per-task gate documents the targeted pytest invocation that MUST pass before invoking `LEFTHOOK=0 git commit`. **Task 20 (final commit) MUST go through the full hook set without bypass** per CLAUDE.md "Hook discipline".
4. **Option E (Q1-PR3) for ask/resume (spec §6.7, §6.8).** T13 implements both. `ask --json` branches on `_is_background_mode(mode)` — uses `BUILTIN_MODES[mode]` plus `is_background_mode(mode_config)` from `config.py:146` for the immediate-vs-background derivation. `resume --json` is pure snapshot via `get_resume_snapshot_data()` and NEVER advances state.
5. **`recoverable_failure` mapping (spec §8.5).** No checkpoint state is named `recoverable_failure` today; `commands.show_status` knows `queued|running|completed|cancelled|failed`, with `failure_type=permanent` distinguishing permanent failures. `get_resume_snapshot_data()` MAPS `status=="failed" and failure_type != "permanent"` to envelope-`data.status:"recoverable_failure"`. The Category G test constructs the corresponding fixture by writing a checkpoint with `status="failed"` and `failure_type="transient"` (or `None`).
6. **Test category bundling per spec §9.2.** Each task lists which test categories (A–H) get added in that commit. Final PR3 gate (post-T20) MUST show pytest count ≥ 460+ (391 PR2 baseline + ~70 PR3-new) and `./thoth_test -r` 63+ passing.
7. **No regression in PR1+PR2's gates.** All PR1+PR2 tests must stay green throughout. The only file that grows test counts is `tests/test_json_envelopes.py` (parametrize list grows per task) — but its assertions never tighten existing tests, only add new parametrize rows.
8. **Category H meta-tests (Tasks 14–15).** The `as_json` exclusion test is a 5-line `Path.read_text() + assert "as_json" not in content` check against `commands.py`, `config_cmd.py`, `modes_cmd.py`. The `JSON_COMMANDS` completeness test is the AST walker per spec §6.5 + §9.1 H — `ast.parse()` of every `cli_subcommands/*.py` file, walks for `@click.option` declarations naming `--json`, asserts each command appears in the parametrize list. ~30 LOC of stdlib AST visitor.
9. **Conventional Commits enforced.** Every commit message in this plan starts with `feat:`, `test:`, `docs:`, or `chore:`. The `commit-msg` lefthook + commitlint CI both reject malformed messages. Use `feat:` for any user-visible new behavior; `test:` for pure test additions (T14, T15); `docs:` for T16–T20.
10. **Click 8.x `protected_args` deprecation.** PR3 does NOT modify `ThothGroup.parse_args` or `ThothGroup.invoke` (PR2 already wraps `protected_args` in `warnings.catch_warnings()` and PR3 introduces no new uses).

---

## Task 1: Add `json_output.py` envelope contract

**Why first:** Every later task that adds `--json` will import `emit_json` and `emit_error` from this module. Landing it first as ~40 LOC + 5 tests gives every downstream commit a stable single-source-of-truth for the envelope shape.

**Files:**
- Create: `src/thoth/json_output.py`
- Create: `tests/test_json_output.py`

- [ ] **Step 1.1: Write the failing tests first**

Create `tests/test_json_output.py`:

```python
"""Envelope-contract tests for `thoth.json_output`.

Per spec §6.1 + §8.3, every `--json` command's output MUST satisfy:
1. Output parses as JSON (json.loads doesn't raise)
2. Top-level is a dict
3. Has "status" key with value "ok" or "error"
4. If "ok": has "data" key (dict)
5. If "error": has "error" key with "code" (str) and "message" (str);
   optionally "details" (dict)

This file tests the envelope-emitter functions in isolation. The
parametrized per-command contract test lives in test_json_envelopes.py.
"""

from __future__ import annotations

import json

import pytest


def test_emit_json_writes_success_envelope_and_exits_zero(capsys):
    from thoth.json_output import emit_json

    with pytest.raises(SystemExit) as excinfo:
        emit_json({"foo": 1, "bar": "baz"})

    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload == {"status": "ok", "data": {"foo": 1, "bar": "baz"}}


def test_emit_error_writes_error_envelope_with_default_exit_code_one(capsys):
    from thoth.json_output import emit_error

    with pytest.raises(SystemExit) as excinfo:
        emit_error("CODE", "human message", {"detail_key": 42})

    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload == {
        "status": "error",
        "error": {
            "code": "CODE",
            "message": "human message",
            "details": {"detail_key": 42},
        },
    }


def test_emit_error_omits_details_when_none(capsys):
    from thoth.json_output import emit_error

    with pytest.raises(SystemExit):
        emit_error("CODE", "msg")

    payload = json.loads(capsys.readouterr().out)
    assert "details" not in payload["error"]


def test_emit_error_honors_exit_code_override(capsys):
    from thoth.json_output import emit_error

    with pytest.raises(SystemExit) as excinfo:
        emit_error("CODE", "msg", exit_code=2)

    assert excinfo.value.code == 2


def test_emit_json_honors_exit_code_override(capsys):
    from thoth.json_output import emit_json

    with pytest.raises(SystemExit) as excinfo:
        emit_json({"x": 1}, exit_code=130)

    assert excinfo.value.code == 130
```

- [ ] **Step 1.2: Run the tests — should fail with ImportError**

```bash
uv run pytest tests/test_json_output.py -v
```

Expected: 5 errors, all `ModuleNotFoundError: No module named 'thoth.json_output'`.

- [ ] **Step 1.3: Implement the module**

Create `src/thoth/json_output.py`:

```python
"""Single source of truth for the `--json` envelope contract.

Per spec §6.1 of docs/superpowers/specs/2026-04-26-p16-pr3-design.md, every
`--json` command emits one of two envelope shapes and exits:

  Success:  {"status": "ok",    "data":  {...}}
  Error:    {"status": "error", "error": {"code": "...", "message": "...",
                                          "details": {...}?}}

This module is framework-free (stdlib only) so handlers can import it
without touching Click. The CI lint rule in tests/test_ci_lint_rules.py
enforces that the wrapper layer (cli_subcommands/) is the ONLY place that
calls emit_json/emit_error — handler modules (commands.py, config_cmd.py,
modes_cmd.py) MUST stay JSON-agnostic via the B-deferred get_*_data()
extraction pattern.
"""

from __future__ import annotations

import json
import sys
from typing import Any, NoReturn


def emit_json(data: dict[str, Any], *, exit_code: int = 0) -> NoReturn:
    """Emit a success envelope and exit.

    Args:
        data: The dict to wrap as `data` inside the envelope.
        exit_code: Process exit code. Defaults to 0; use 130 for SIGINT
            recovery paths.
    """
    sys.stdout.write(json.dumps({"status": "ok", "data": data}))
    sys.stdout.write("\n")
    sys.stdout.flush()
    sys.exit(exit_code)


def emit_error(
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    *,
    exit_code: int = 1,
) -> NoReturn:
    """Emit an error envelope and exit.

    Args:
        code: Stable machine-readable error code (e.g. ``OPERATION_NOT_FOUND``).
            See spec §8.1 for the catalog.
        message: Human-readable description.
        details: Optional dict for code-specific context.
        exit_code: Process exit code. Defaults to 1; common overrides are
            2 (usage), 6 (operation not found), 7 (operation failed
            permanently), 130 (SIGINT).
    """
    err: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        err["details"] = details
    sys.stdout.write(json.dumps({"status": "error", "error": err}))
    sys.stdout.write("\n")
    sys.stdout.flush()
    sys.exit(exit_code)


__all__ = ["emit_error", "emit_json"]
```

- [ ] **Step 1.4: Run the tests — should pass**

```bash
uv run pytest tests/test_json_output.py -v
```

Expected: 5 passed.

- [ ] **Step 1.5: Lint + typecheck**

```bash
just check
```

Expected: green.

- [ ] **Step 1.6: Commit**

```bash
git add src/thoth/json_output.py tests/test_json_output.py
git commit -m "feat: add json_output.py envelope contract"
```

The full hook set runs the integration suite (~60s); expect green because nothing else changed.

---

## Task 2: Verify Click pin permits fish completion

**Why now:** Spec §13 calls out Click 8.0+ for fish; PROJECTS.md notes the lockfile resolves 8.3.1. This is a verification task — likely a no-op `chore` commit if the pin is already correct. Doing it now (before T03 imports Click completion machinery) saves a debugging detour later.

**Files:**
- Read-only check: `pyproject.toml`, `uv.lock`
- Modify: `pyproject.toml` (only if pin is wrong)

- [ ] **Step 2.1: Verify the Click pin**

```bash
grep -n '"click' pyproject.toml
grep -A1 'name = "click"' uv.lock | head -10
```

Expected: `click>=8.0` (or stricter) in `pyproject.toml`; `version = "8.3.1"` (or any 8.x ≥ 8.0) in `uv.lock`.

- [ ] **Step 2.2: Decide outcome**

Two cases:

**Case A — pin already permits fish (expected):** No code change. Skip to Step 2.4. Per spec §13 + skeleton T02 note, this is the expected branch — `pyproject.toml` already pins `click>=8.0` and `uv.lock` resolves 8.3.1.

**Case B — pin too loose / too strict:** Update `pyproject.toml` to `click>=8.0` (the documented minimum for fish completion per Click changelog).

- [ ] **Step 2.3 (Case B only): Run linters**

```bash
just check
uv lock --upgrade-package click
```

- [ ] **Step 2.4: Commit (or skip if no-op)**

Only commit if Case B applied:

```bash
git add pyproject.toml uv.lock
git commit -m "chore(deps): verify Click pin for fish completion"
```

If Case A (no changes), skip the commit. Note in the task ledger that T02 was a verification no-op.

---

## Task 3: Add `completion/` package (script + install + sources) and `list_operation_ids()` on CheckpointManager

**Why next:** T04 (`completion` Click subcommand) imports from this package, and T05 (wire `shell_complete=` callbacks) imports from `completion/sources.py`. Building the entire package in one commit (with all four modules + the `CheckpointManager` glue) keeps the diff coherent.

**Files:**
- Create: `src/thoth/completion/__init__.py`
- Create: `src/thoth/completion/script.py`
- Create: `src/thoth/completion/install.py`
- Create: `src/thoth/completion/sources.py`
- Modify: `src/thoth/checkpoint.py` (add `list_operation_ids` method)
- Create: `tests/test_completion.py` (Category B)
- Create: `tests/test_completion_install.py` (Category C — minimal subset; full matrix expanded in T04)
- Create: `tests/test_completion_sources.py` (Category D)

- [ ] **Step 3.1: Failing test for `script.py` (Category B)**

Create `tests/test_completion.py`:

```python
"""Category B — completion script generation tests (spec §9.1)."""

from __future__ import annotations

import pytest


@pytest.mark.parametrize("shell", ["bash", "zsh", "fish"])
def test_generate_script_includes_THOTH_COMPLETE_marker(shell):
    from thoth.completion.script import generate_script

    out = generate_script(shell)
    assert "_THOTH_COMPLETE" in out
    assert shell in out


def test_generate_script_rejects_unknown_shell():
    from thoth.completion.script import generate_script

    with pytest.raises(ValueError, match="unsupported shell"):
        generate_script("powershell")


@pytest.mark.parametrize("shell", ["bash", "zsh", "fish"])
def test_fenced_block_brackets_with_thoth_completion_markers(shell):
    from thoth.completion.script import fenced_block

    out = fenced_block(shell)
    assert "# >>> thoth completion >>>" in out
    assert "# <<< thoth completion <<<" in out
    assert "_THOTH_COMPLETE" in out
```

- [ ] **Step 3.2: Failing tests for `sources.py` (Category D)**

Create `tests/test_completion_sources.py`:

```python
"""Category D — completion data-source unit tests (spec §9.1)."""

from __future__ import annotations

import json
from datetime import datetime

import pytest

from tests.conftest import make_operation


def _make_ctx_param():
    """Click passes (ctx, param, incomplete) to shell_complete callbacks.

    For unit tests we don't need real Context/Parameter objects; the source
    functions ignore ctx/param and only filter on `incomplete`.
    """
    return None, None


def test_operation_ids_returns_stems_of_checkpoint_files(checkpoint_dir):
    from thoth.completion.sources import operation_ids

    op1 = make_operation("research-20260427-000000-aaaaaaaaaaaaaaaa")
    op2 = make_operation("research-20260427-000001-bbbbbbbbbbbbbbbb")
    for op in (op1, op2):
        (checkpoint_dir / f"{op.id}.json").write_text(
            json.dumps(
                {
                    "id": op.id,
                    "prompt": op.prompt,
                    "mode": op.mode,
                    "status": op.status,
                    "created_at": op.created_at.isoformat(),
                    "updated_at": op.updated_at.isoformat(),
                    "output_paths": {},
                    "input_files": [],
                    "providers": {},
                    "project": None,
                    "output_dir": None,
                    "error": None,
                    "failure_type": None,
                }
            )
        )

    ctx, param = _make_ctx_param()
    out = operation_ids(ctx, param, "")
    assert op1.id in out
    assert op2.id in out


def test_operation_ids_filters_by_incomplete_prefix(checkpoint_dir):
    from thoth.completion.sources import operation_ids

    target = make_operation("research-20260427-000000-aaaaaaaaaaaaaaaa")
    other = make_operation("research-20260428-000000-bbbbbbbbbbbbbbbb")
    for op in (target, other):
        (checkpoint_dir / f"{op.id}.json").write_text(
            json.dumps(
                {
                    "id": op.id, "prompt": op.prompt, "mode": op.mode,
                    "status": op.status,
                    "created_at": op.created_at.isoformat(),
                    "updated_at": op.updated_at.isoformat(),
                    "output_paths": {}, "input_files": [], "providers": {},
                    "project": None, "output_dir": None,
                    "error": None, "failure_type": None,
                }
            )
        )

    ctx, param = _make_ctx_param()
    out = operation_ids(ctx, param, "research-20260427")
    assert target.id in out
    assert other.id not in out


def test_operation_ids_returns_empty_when_no_checkpoints(isolated_thoth_home):
    from thoth.completion.sources import operation_ids

    ctx, param = _make_ctx_param()
    assert operation_ids(ctx, param, "") == []


def test_mode_names_includes_default_and_other_builtins():
    from thoth.completion.sources import mode_names

    ctx, param = _make_ctx_param()
    out = mode_names(ctx, param, "")
    assert "default" in out


def test_mode_names_filters_by_incomplete_prefix():
    from thoth.completion.sources import mode_names

    ctx, param = _make_ctx_param()
    out = mode_names(ctx, param, "deep")
    assert all(name.startswith("deep") for name in out)


def test_config_keys_returns_dotted_keys_from_defaults(isolated_thoth_home):
    from thoth.completion.sources import config_keys

    ctx, param = _make_ctx_param()
    out = config_keys(ctx, param, "")
    assert any("." in key for key in out)


def test_config_keys_filters_by_incomplete_prefix(isolated_thoth_home):
    from thoth.completion.sources import config_keys

    ctx, param = _make_ctx_param()
    out = config_keys(ctx, param, "providers.")
    assert all(key.startswith("providers.") for key in out)


def test_provider_names_returns_known_providers():
    from thoth.completion.sources import provider_names

    ctx, param = _make_ctx_param()
    out = provider_names(ctx, param, "")
    assert set(out) >= {"openai", "perplexity", "mock"}


def test_provider_names_filters_by_incomplete_prefix():
    from thoth.completion.sources import provider_names

    ctx, param = _make_ctx_param()
    out = provider_names(ctx, param, "open")
    assert "openai" in out
    assert "perplexity" not in out


def test_mode_kind_returns_immediate_and_background_choices():
    """P18 forward-compat — currently dead code per spec §6.4."""
    from thoth.completion.sources import mode_kind

    ctx, param = _make_ctx_param()
    out = mode_kind(ctx, param, "")
    assert set(out) >= {"immediate", "background"}
```

- [ ] **Step 3.3: Failing tests for `install.py` (Category C — minimal subset)**

Create `tests/test_completion_install.py`:

```python
"""Category C — completion install behavior matrix (spec §6.3 + §9.1).

This file holds the minimal subset to validate the install dataclass and
the manual-mode path. The full TTY/non-TTY/force matrix lives here too;
T04 expands the parametrize coverage to the full 5-row matrix from
spec §6.3.
"""

from __future__ import annotations

from pathlib import Path

import pytest


def test_install_manual_mode_returns_preview_action_and_writes_nothing(tmp_path):
    from thoth.completion.install import install

    rc_path = tmp_path / ".bashrc"
    result = install("bash", manual=True, rc_path=rc_path)

    assert result.action == "preview"
    assert "thoth completion" in result.message
    assert not rc_path.exists()


def test_install_manual_force_mutex_raises(tmp_path):
    import click

    from thoth.completion.install import install

    with pytest.raises(click.BadParameter, match="mutex"):
        install("bash", manual=True, force=True, rc_path=tmp_path / ".bashrc")


def test_install_force_writes_silently(tmp_path):
    from thoth.completion.install import install

    rc_path = tmp_path / ".bashrc"
    result = install("bash", force=True, rc_path=rc_path)

    assert result.action == "written"
    assert rc_path.exists()
    text = rc_path.read_text()
    assert "# >>> thoth completion >>>" in text
    assert "# <<< thoth completion <<<" in text


def test_install_force_overwrites_existing_block(tmp_path):
    from thoth.completion.install import install

    rc_path = tmp_path / ".bashrc"
    rc_path.write_text(
        "# user content above\n"
        "# >>> thoth completion >>>\n"
        "OLD CONTENT\n"
        "# <<< thoth completion <<<\n"
        "# user content below\n"
    )
    install("bash", force=True, rc_path=rc_path)

    text = rc_path.read_text()
    assert text.count("# >>> thoth completion >>>") == 1
    assert "OLD CONTENT" not in text
    assert "# user content above" in text
    assert "# user content below" in text


def test_install_fish_uses_fish_completion_path_when_default(tmp_path, monkeypatch):
    """Fish convention: ~/.config/fish/completions/thoth.fish (per spec §6.3)."""
    from thoth.completion.install import install

    monkeypatch.setenv("HOME", str(tmp_path))
    result = install("fish", force=True)

    assert result.path == tmp_path / ".config" / "fish" / "completions" / "thoth.fish"
    assert result.path.exists()
```

- [ ] **Step 3.4: Run the tests — should fail with ImportError**

```bash
uv run pytest tests/test_completion.py tests/test_completion_install.py tests/test_completion_sources.py -v
```

Expected: all errors, `ModuleNotFoundError: No module named 'thoth.completion'`.

- [ ] **Step 3.5: Implement `completion/__init__.py`**

Create `src/thoth/completion/__init__.py`:

```python
"""Shell-completion package.

Per spec §5.2 of docs/superpowers/specs/2026-04-26-p16-pr3-design.md, this
package owns:
  - `script.py`   — generate `eval`-able shell init scripts
  - `install.py`  — write fenced blocks to user rc files
  - `sources.py`  — pure data functions for `shell_complete=` callbacks

The Click `completion` subcommand lives at
`src/thoth/cli_subcommands/completion.py` and imports from this package.
"""
```

- [ ] **Step 3.6: Implement `completion/script.py`**

Create `src/thoth/completion/script.py`:

```python
"""Generate shell init scripts that wire Click's `_THOTH_COMPLETE` machinery.

Per spec §6.2: each shell's snippet evaluates the appropriate
`_THOTH_COMPLETE=<shell>_source thoth` form to enable TAB completion.
"""

from __future__ import annotations

from typing import Literal

Shell = Literal["bash", "zsh", "fish"]
_SUPPORTED: tuple[str, ...] = ("bash", "zsh", "fish")

_BASH_TEMPLATE = 'eval "$(_THOTH_COMPLETE=bash_source thoth)"'
_ZSH_TEMPLATE = 'eval "$(_THOTH_COMPLETE=zsh_source thoth)"'
_FISH_TEMPLATE = "_THOTH_COMPLETE=fish_source thoth | source"


def generate_script(shell: str) -> str:
    """Return the eval-able shell init script for `shell`.

    Raises:
        ValueError: if `shell` is not one of bash/zsh/fish.
    """
    if shell not in _SUPPORTED:
        raise ValueError(f"unsupported shell: {shell!r} (supported: {_SUPPORTED})")
    if shell == "bash":
        return _BASH_TEMPLATE
    if shell == "zsh":
        return _ZSH_TEMPLATE
    return _FISH_TEMPLATE  # fish


def fenced_block(shell: str) -> str:
    """Return a fenced block (markers + script) for safe rc-file insertion.

    The fenced markers `# >>> thoth completion >>>` / `# <<< thoth
    completion <<<` make the block trivially removable via:

        sed -i '/# >>> thoth completion >>>/,/# <<< thoth completion <<</d' ~/.bashrc
    """
    if shell not in _SUPPORTED:
        raise ValueError(f"unsupported shell: {shell!r} (supported: {_SUPPORTED})")
    return (
        "# >>> thoth completion >>>\n"
        f"{generate_script(shell)}\n"
        "# <<< thoth completion <<<\n"
    )


__all__ = ["fenced_block", "generate_script"]
```

- [ ] **Step 3.7: Implement `completion/install.py`**

Create `src/thoth/completion/install.py`:

```python
"""Install completion fenced block into shell rc files.

Per spec §6.3 (Q3-A + manual sub-mode + force), the install logic:
  * `--install` (TTY): detect existing block, preview, prompt y/n, write.
  * `--install` (non-TTY): refuse with INSTALL_REQUIRES_TTY.
  * `--install --force`: write/overwrite silently (CI-friendly).
  * `--install --manual`: print fenced block + instructions, never write.
  * `--install --manual --force`: BadParameter (mutex).

The fenced markers in completion/script.py make the block removable
via a single `sed` invocation. A real `--uninstall` flag is a future PR.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import click

from thoth.completion.script import fenced_block

Shell = Literal["bash", "zsh", "fish"]

_DEFAULT_RC: dict[str, tuple[str, ...]] = {
    "bash": (".bashrc",),
    "zsh": (".zshrc",),
    "fish": (".config", "fish", "completions", "thoth.fish"),
}

_BLOCK_RE = re.compile(
    r"# >>> thoth completion >>>.*?# <<< thoth completion <<<\n?",
    re.DOTALL,
)


@dataclass(frozen=True)
class InstallResult:
    """Outcome of an `install()` call.

    Attributes:
        action: `"written"` (file changed), `"preview"` (manual mode — no
            write performed), or `"skipped"` (TTY prompt declined).
        path: The rc file path that was (or would have been) modified.
        message: Human-readable success/preview/skip message including
            the sed-uninstall hint per spec §13.
    """

    action: Literal["written", "preview", "skipped"]
    path: Path
    message: str


def _default_rc_path(shell: str) -> Path:
    """Conventional rc path for `shell`, anchored at $HOME."""
    home = Path.home()
    return home.joinpath(*_DEFAULT_RC[shell])


def install(
    shell: str,
    *,
    force: bool = False,
    manual: bool = False,
    rc_path: Path | None = None,
) -> InstallResult:
    """Install the completion fenced block per Q3-A behavior matrix.

    See spec §6.3 table for the full TTY/--manual/--force decision matrix.
    """
    if manual and force:
        raise click.BadParameter(
            "--manual and --force are mutex",
            param_hint="--manual / --force",
        )

    block = fenced_block(shell)

    if manual:
        msg = (
            "Add the following block to your shell rc file (or run with --install):\n\n"
            f"{block}\n"
            "Remove with:\n"
            "  sed -i '/# >>> thoth completion >>>/,/# <<< thoth completion <<</d' "
            f"{rc_path or _default_rc_path(shell)}\n"
        )
        return InstallResult(
            action="preview",
            path=rc_path or _default_rc_path(shell),
            message=msg,
        )

    target = rc_path or _default_rc_path(shell)
    target.parent.mkdir(parents=True, exist_ok=True)

    existing = target.read_text() if target.exists() else ""
    has_block = bool(_BLOCK_RE.search(existing))

    if has_block:
        # Replace the existing block in-place.
        new_text = _BLOCK_RE.sub(block, existing, count=1)
    else:
        new_text = existing
        if new_text and not new_text.endswith("\n"):
            new_text += "\n"
        new_text += block

    target.write_text(new_text)
    return InstallResult(
        action="written",
        path=target,
        message=(
            f"Wrote thoth completion block to {target}.\n"
            "Restart your shell (or `source` the file) to activate.\n"
            "Remove later with:\n"
            "  sed -i '/# >>> thoth completion >>>/,/# <<< thoth completion <<</d' "
            f"{target}\n"
        ),
    )


__all__ = ["InstallResult", "install"]
```

- [ ] **Step 3.8: Implement `completion/sources.py`**

Create `src/thoth/completion/sources.py`:

```python
"""Pure data functions for Click `shell_complete=` callbacks.

Each function takes Click's `(ctx, param, incomplete)` signature and
returns a `list[str]` of candidate completions filtered by `incomplete`
prefix. The functions are pure (no side effects) so they can also be
imported by `interactive.py::SlashCommandCompleter` in a future PR.

Per spec §6.4: `mode_kind` is committed as dead code (~5 LOC) for P18
forward-compat — P18 will wire `--kind` later.
"""

from __future__ import annotations

from typing import Any

from thoth.config import BUILTIN_MODES, ConfigManager, ConfigSchema
from thoth.paths import user_checkpoints_dir


def _starts_with(items: list[str], incomplete: str) -> list[str]:
    if not incomplete:
        return sorted(items)
    return sorted(item for item in items if item.startswith(incomplete))


def operation_ids(ctx: Any, param: Any, incomplete: str) -> list[str]:
    """Live operation IDs from the user's checkpoint store."""
    checkpoint_dir = user_checkpoints_dir()
    if not checkpoint_dir.exists():
        return []
    ids = [p.stem for p in checkpoint_dir.glob("*.json")]
    return _starts_with(ids, incomplete)


def mode_names(ctx: Any, param: Any, incomplete: str) -> list[str]:
    """Built-in + user-defined mode names.

    User modes are loaded lazily from a fresh ConfigManager; this is a
    completion path so the small extra IO is acceptable.
    """
    names = list(BUILTIN_MODES.keys())
    try:
        cm = ConfigManager()
        cm.load_all_layers({})
        user_modes = (cm.data.get("modes") or {}).keys()
        names.extend(str(name) for name in user_modes)
    except Exception:
        # Completion must never raise — degrade to builtins.
        pass
    return _starts_with(sorted(set(names)), incomplete)


def _flatten_keys(data: dict[str, Any], prefix: str = "") -> list[str]:
    out: list[str] = []
    for key, value in data.items():
        full = key if not prefix else f"{prefix}.{key}"
        if isinstance(value, dict):
            out.extend(_flatten_keys(value, full))
        else:
            out.append(full)
    return out


def config_keys(ctx: Any, param: Any, incomplete: str) -> list[str]:
    """Dotted config keys derived from ConfigSchema defaults."""
    try:
        defaults = ConfigSchema.get_defaults()
    except Exception:
        return []
    keys = _flatten_keys(defaults)
    return _starts_with(keys, incomplete)


def provider_names(ctx: Any, param: Any, incomplete: str) -> list[str]:
    """Static provider names — matches PROVIDER_CHOICES in providers.py."""
    return _starts_with(["openai", "perplexity", "mock"], incomplete)


def mode_kind(ctx: Any, param: Any, incomplete: str) -> list[str]:
    """P18 forward-compat — currently dead code per spec §6.4."""
    return _starts_with(["immediate", "background"], incomplete)


__all__ = [
    "config_keys",
    "mode_kind",
    "mode_names",
    "operation_ids",
    "provider_names",
]
```

- [ ] **Step 3.9: Add `list_operation_ids()` to `CheckpointManager`**

Spec §6.4 names this method. Add it as a small additive sibling on `CheckpointManager`. The implementation matches the existing glob pattern in `commands.list_operations`.

Edit `src/thoth/checkpoint.py` (append after `trigger_checkpoint`, before `_console`):

```python
    def list_operation_ids(self) -> list[str]:
        """Return all operation IDs known to the checkpoint store.

        Used by `completion/sources.py::operation_ids` and (transitively)
        by future `thoth list --json` callers that want to enumerate
        without loading every operation. Synchronous on purpose — this is
        a metadata-only filesystem listing.
        """
        return sorted(p.stem for p in self.checkpoint_dir.glob("*.json"))
```

(Note: `completion/sources.py::operation_ids` calls `user_checkpoints_dir()` directly rather than constructing a `CheckpointManager`, because completion code paths must never trigger ConfigManager/provider initialization. The new `list_operation_ids` method exists for future per-handler `get_*_data` callers — `get_list_data` in T08 uses it.)

- [ ] **Step 3.10: Run the tests — should pass**

```bash
uv run pytest tests/test_completion.py tests/test_completion_install.py tests/test_completion_sources.py -v
```

Expected: ~21 passed (3+5+10+3 dataclass paths). If `mode_names` test fails because BUILTIN_MODES doesn't include `default`, verify with `grep -n '"default"' src/thoth/config.py` — `default` is defined at config.py:43.

- [ ] **Step 3.11: Lint + typecheck**

```bash
just check
```

Expected: green.

- [ ] **Step 3.12: Commit**

```bash
git add src/thoth/completion src/thoth/checkpoint.py \
        tests/test_completion.py tests/test_completion_install.py \
        tests/test_completion_sources.py
git commit -m "feat(completion): add completion/ package + CheckpointManager.list_operation_ids"
```

Pre-commit gate: full hook set should pass — no JSON or `--json` paths touched yet.

---

## Task 4: Add `completion` Click subcommand and restore it to ADMIN_COMMANDS

**Why now:** With T01–T03 landed, the wiring layer can ship. This commit makes `thoth completion bash|zsh|fish` real for the first time.

**Files:**
- Create: `src/thoth/cli_subcommands/completion.py`
- Modify: `src/thoth/cli.py` (register subcommand)
- Modify: `src/thoth/help.py` (restore `"completion"` in `ADMIN_COMMANDS`)
- Append to: `tests/test_completion.py` (Category B — CLI invocation tests)
- Append to: `tests/test_completion_install.py` (Category C — full TTY matrix via CliRunner)

- [ ] **Step 4.1: Failing tests — Click subcommand surface**

Append to `tests/test_completion.py`:

```python
import json as _json

import click
from click.testing import CliRunner


def _invoke(args: list[str]):
    from thoth.cli import cli

    runner = CliRunner(mix_stderr=False)
    return runner.invoke(cli, args, catch_exceptions=False)


@pytest.mark.parametrize("shell", ["bash", "zsh", "fish"])
def test_cli_completion_emits_eval_able_script(shell):
    result = _invoke(["completion", shell])
    assert result.exit_code == 0
    assert "_THOTH_COMPLETE" in result.output
    assert shell in result.output


def test_cli_completion_unsupported_shell_exits_2_no_json():
    result = _invoke(["completion", "powershell"])
    assert result.exit_code == 2


def test_cli_completion_unsupported_shell_with_json_emits_envelope():
    result = _invoke(["completion", "powershell", "--json"])
    assert result.exit_code == 2
    payload = _json.loads(result.output)
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "UNSUPPORTED_SHELL"


def test_cli_completion_listed_in_help():
    result = _invoke(["--help"])
    assert "completion" in result.output
```

- [ ] **Step 4.2: Failing tests — full install matrix (Category C expansion)**

Append to `tests/test_completion_install.py`:

```python
import json as _json

import click
from click.testing import CliRunner


def _invoke(args: list[str], **kwargs):
    from thoth.cli import cli

    runner = CliRunner(mix_stderr=False)
    return runner.invoke(cli, args, catch_exceptions=False, **kwargs)


def test_cli_install_non_tty_without_force_or_manual_refuses(monkeypatch, tmp_path):
    """spec §6.3 row: non-TTY + no --force/--manual → INSTALL_REQUIRES_TTY."""
    monkeypatch.setenv("HOME", str(tmp_path))
    result = _invoke(["completion", "bash", "--install"])
    assert result.exit_code == 2
    assert "INSTALL_REQUIRES_TTY" in result.output or "INSTALL_REQUIRES_TTY" in result.stderr


def test_cli_install_non_tty_with_force_writes_silently(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    result = _invoke(["completion", "bash", "--install", "--force"])
    assert result.exit_code == 0
    bashrc = tmp_path / ".bashrc"
    assert bashrc.exists()
    assert "_THOTH_COMPLETE" in bashrc.read_text()


def test_cli_install_manual_prints_block_never_writes(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    result = _invoke(["completion", "bash", "--install", "--manual"])
    assert result.exit_code == 0
    assert "# >>> thoth completion >>>" in result.output
    assert not (tmp_path / ".bashrc").exists()


def test_cli_install_manual_with_force_exits_2_mutex(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    result = _invoke(["completion", "bash", "--install", "--manual", "--force"])
    assert result.exit_code == 2


def test_cli_install_with_json_envelope_on_success(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    result = _invoke(["completion", "bash", "--install", "--force", "--json"])
    assert result.exit_code == 0
    payload = _json.loads(result.output)
    assert payload["status"] == "ok"
    assert payload["data"]["action"] == "written"
    assert payload["data"]["path"].endswith(".bashrc")
```

- [ ] **Step 4.3: Run the tests — should fail**

```bash
uv run pytest tests/test_completion.py tests/test_completion_install.py -v
```

Expected: new tests fail with `Error: No such command 'completion'.` (Click's natural error before T04 implements + registers).

- [ ] **Step 4.4: Implement the subcommand**

Create `src/thoth/cli_subcommands/completion.py`:

```python
"""`thoth completion <shell>` Click subcommand.

Per spec §6.5: `shell` is intentionally NOT a `click.Choice`, because
invalid-shell errors must be emit-able as `UNSUPPORTED_SHELL` JSON
envelopes, which Click's choice validation can't do. The body validates
against `{"bash", "zsh", "fish"}`.

Behavior:
  - `thoth completion <shell>` (no flags) — emit eval-able script to stdout.
  - `thoth completion <shell> --install` (TTY) — write fenced block; prompt on overwrite.
  - `thoth completion <shell> --install --force` — write/overwrite silently.
  - `thoth completion <shell> --install --manual` — print block + instructions; never write.
  - Any of the above with `--json` — wrap result/error in JSON envelope.
"""

from __future__ import annotations

import sys

import click

from thoth.completion.install import install as do_install
from thoth.completion.script import generate_script
from thoth.json_output import emit_error, emit_json

_SUPPORTED_SHELLS = ("bash", "zsh", "fish")


@click.command(name="completion")
@click.argument("shell")
@click.option("--install", "do_install_flag", is_flag=True, help="Install completion to rc file")
@click.option("--force", is_flag=True, help="Overwrite existing block silently (CI-friendly)")
@click.option("--manual", is_flag=True, help="Print fenced block + instructions; never write")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.pass_context
def completion(
    ctx: click.Context,
    shell: str,
    do_install_flag: bool,
    force: bool,
    manual: bool,
    as_json: bool,
) -> None:
    """Generate or install shell-completion scripts."""
    if shell not in _SUPPORTED_SHELLS:
        msg = (
            f"unsupported shell: {shell!r} "
            f"(supported: {', '.join(_SUPPORTED_SHELLS)})"
        )
        if as_json:
            emit_error(
                "UNSUPPORTED_SHELL",
                msg,
                {"shell": shell, "supported": list(_SUPPORTED_SHELLS)},
                exit_code=2,
            )
        click.echo(f"Error: {msg}", err=True)
        ctx.exit(2)

    if do_install_flag:
        # Mutex: --manual vs --force is enforced inside completion.install.install().
        if not (force or manual) and not sys.stdin.isatty():
            if as_json:
                emit_error(
                    "INSTALL_REQUIRES_TTY",
                    "non-TTY install requires --force or --manual",
                    {"shell": shell},
                    exit_code=2,
                )
            click.echo(
                "Error: INSTALL_REQUIRES_TTY — non-TTY install requires --force or --manual",
                err=True,
            )
            ctx.exit(2)

        try:
            result = do_install(shell, force=force, manual=manual)
        except click.BadParameter:
            raise  # Click renders + exits 2.
        except PermissionError as exc:
            if as_json:
                emit_error(
                    "INSTALL_FILE_PERMISSION",
                    str(exc),
                    {"shell": shell},
                    exit_code=1,
                )
            click.echo(f"Error: INSTALL_FILE_PERMISSION — {exc}", err=True)
            ctx.exit(1)

        if as_json:
            emit_json(
                {
                    "shell": shell,
                    "action": result.action,
                    "path": str(result.path),
                    "message": result.message,
                }
            )
        click.echo(result.message)
        return

    # No --install: emit eval-able script to stdout (raw — not wrapped in JSON
    # even if --json is passed; per spec §3 + acceptance criteria, the script
    # stays raw for `eval "$(thoth completion zsh)"` use).
    click.echo(generate_script(shell))


__all__ = ["completion"]
```

- [ ] **Step 4.5: Register the subcommand**

Edit `src/thoth/cli.py` — add an import + `cli.add_command(...)` line near the existing registrations (around line 590, after `cli.add_command(_modes_mod.modes)`):

```python
from thoth.cli_subcommands import completion as _completion_mod
...
cli.add_command(_completion_mod.completion)
```

(Place the import next to the other `from thoth.cli_subcommands import ...` lines and the `add_command` line in registration order, before the `help_cmd` registration.)

- [ ] **Step 4.6: Restore `completion` in `ADMIN_COMMANDS`**

Edit `src/thoth/help.py` line 15-21 — restore `"completion"` to the tuple (PR2 T8 removed it as a phantom; PR3 makes it real):

```python
ADMIN_COMMANDS: tuple[str, ...] = (
    "init",
    "config",
    "modes",
    "providers",
    "completion",
    "help",
)
```

- [ ] **Step 4.7: Run the tests — should pass**

```bash
uv run pytest tests/test_completion.py tests/test_completion_install.py -v
```

Expected: all green. The 5 CLI completion tests + 5 CLI install tests join the 21 unit tests from T03 → 31 completion tests total.

- [ ] **Step 4.8: Spot-check the parity gate stays green**

```bash
uv run pytest tests/test_p16_dispatch_parity.py tests/test_p16_thothgroup.py -v
```

Expected: all 40 PR1 parity tests still green. The `--help` baseline includes `completion` in the listing now (PR2 baseline did NOT include it — PR2 T8 explicitly removed it from `ADMIN_COMMANDS`). If the help baseline test fails, recapture per the conftest_p16 baseline-update flow (single-line update); the change is documented in spec §3 + PROJECTS.md.

Note: review whether `tests/baselines/help_post_pr1.json` needs recapture. Inspect the failure first; if it's strictly the `completion` line being added, the baseline update is mechanical and goes in this commit. If anything else changed, stop and diagnose.

- [ ] **Step 4.9: Lint + typecheck**

```bash
just check
```

- [ ] **Step 4.10: Commit**

```bash
git add src/thoth/cli_subcommands/completion.py src/thoth/cli.py src/thoth/help.py \
        tests/test_completion.py tests/test_completion_install.py
# Include the help baseline only if regenerated in Step 4.8:
git add tests/baselines/help_post_pr1.json 2>/dev/null || true
git commit -m "feat(cli): add completion subcommand"
```

Pre-commit gate: full hook set must pass.

---

## Task 5: Wire `shell_complete=` callbacks on subcommand options

**Why now:** With `completion/sources.py` registered (T03) and the `completion` subcommand live (T04), the dynamic completers can be attached to existing subcommand options. This is the user-visible payoff of the completion package — `thoth resume <TAB>` actually completes operation IDs.

**Files:**
- Modify: `src/thoth/cli_subcommands/resume.py` — `shell_complete=operation_ids` on `OP_ID`
- Modify: `src/thoth/cli_subcommands/status.py` — `shell_complete=operation_ids` on `OP_ID`
- Modify: `src/thoth/cli_subcommands/config.py` — `shell_complete=config_keys` on `KEY` (in `config_get`; `set/unset` keep passthrough so completion is wired only on `get`)
- Modify: `src/thoth/cli_subcommands/modes.py` — `shell_complete=mode_names` on `--name` (it's a passthrough in PR2; T05 promotes `--name` to a typed option to enable `shell_complete=`)
- Modify: `src/thoth/cli_subcommands/providers.py` — `shell_complete=provider_names` on `--provider` Click options (3 sites: `list`, `models`, `check`)
- Append to: `tests/test_completion_sources.py` (assertions that the `shell_complete` callback is wired on each command)

- [ ] **Step 5.1: Failing test — `shell_complete` wiring assertions**

Append to `tests/test_completion_sources.py`:

```python
def test_resume_op_id_argument_has_operation_ids_completer():
    from thoth.cli_subcommands.resume import resume
    from thoth.completion.sources import operation_ids

    op_id_param = next(p for p in resume.params if p.name == "operation_id")
    assert op_id_param.shell_complete is operation_ids


def test_status_op_id_argument_has_operation_ids_completer():
    from thoth.cli_subcommands.status import status
    from thoth.completion.sources import operation_ids

    op_id_param = next(p for p in status.params if p.name == "operation_id")
    assert op_id_param.shell_complete is operation_ids


def test_config_get_key_argument_has_config_keys_completer():
    from thoth.cli_subcommands.config import config_get
    from thoth.completion.sources import config_keys

    key_param = next(p for p in config_get.params if p.name == "key")
    assert key_param.shell_complete is config_keys


def test_modes_list_name_option_has_mode_names_completer():
    from thoth.cli_subcommands.modes import modes_list
    from thoth.completion.sources import mode_names

    name_param = next(p for p in modes_list.params if p.name == "name")
    assert name_param.shell_complete is mode_names


def test_providers_list_provider_option_has_provider_names_completer():
    from thoth.cli_subcommands.providers import providers_list_cmd
    from thoth.completion.sources import provider_names

    provider_param = next(p for p in providers_list_cmd.params if p.name == "filter_provider")
    assert provider_param.shell_complete is provider_names
```

- [ ] **Step 5.2: Run the tests — should fail**

```bash
uv run pytest tests/test_completion_sources.py -v
```

Expected: 5 new failures, `AssertionError: ... is not <function ...>` (shell_complete is None on existing params).

- [ ] **Step 5.3: Wire the callbacks**

Edit `src/thoth/cli_subcommands/resume.py` line 37 — add `shell_complete=`:

```python
@click.argument(
    "operation_id",
    metavar="OP_ID",
    shell_complete=__import__("thoth.completion.sources", fromlist=["operation_ids"]).operation_ids,
)
```

Cleaner — at the top of `resume.py` import:

```python
from thoth.completion.sources import operation_ids as _operation_ids_completer
```

then:

```python
@click.argument("operation_id", metavar="OP_ID", shell_complete=_operation_ids_completer)
```

Apply the same pattern to:
- `status.py` line 13: `@click.argument("operation_id", metavar="OP_ID", required=False, shell_complete=_operation_ids_completer)` (preserve `required=False`).
- `config.py` line 50: `@click.argument("key", shell_complete=_config_keys_completer)`. Add the import: `from thoth.completion.sources import config_keys as _config_keys_completer`.
- `providers.py`: in EACH of the three `@click.option("--provider", "-P", ...)` decorators at lines 96–102, 134–138, 201–207 — add `shell_complete=_provider_names_completer`. Add the import once at the top of `providers.py`.

- [ ] **Step 5.4: Promote `modes list --name` to a typed option**

`modes.py:72-86` currently uses `args = nargs=-1, type=click.UNPROCESSED` passthrough so `_op_list` parses `--name` itself. To attach `shell_complete=mode_names`, promote `--name` to a real Click option AND keep `args` passthrough for the other flags. Edit `modes.py`:

```python
from thoth.completion.sources import mode_names as _mode_names_completer

@modes.command(name="list", context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.option(
    "--name",
    "name",
    default=None,
    help="Show detail for a single mode",
    shell_complete=_mode_names_completer,
)
@click.pass_context
def modes_list(ctx: click.Context, args: tuple[str, ...], name: str | None) -> None:
    """List research modes."""
    validate_inherited_options(ctx, "modes list", DEFAULT_HONOR)

    from thoth.modes_cmd import modes_command

    config_path = inherited_value(ctx, "config_path")
    rebuilt = list(args)
    if name is not None:
        rebuilt.extend(["--name", name])

    if config_path is None:
        rc = modes_command("list", rebuilt)
    else:
        rc = modes_command("list", rebuilt, config_path=config_path)
    sys.exit(rc)
```

This keeps `_op_list`'s arg-parsing unchanged (it already understands `--name X`), but exposes `--name` as a typed Click option for `shell_complete=` wiring. The behavior is identical because we re-emit `["--name", name]` into the passthrough `args`.

- [ ] **Step 5.5: Run the wiring tests — should pass**

```bash
uv run pytest tests/test_completion_sources.py -v
```

Expected: all green.

- [ ] **Step 5.6: Re-run the full PR2 baseline gate**

```bash
uv run pytest tests/test_p16_dispatch_parity.py tests/test_p16_thothgroup.py \
              tests/test_resume.py tests/test_modes_cli.py \
              tests/test_providers_subcommand.py -v
```

Expected: all green. Promoting `--name` to a typed option with `default=None` does not change `modes list --name X` behavior because we re-inject it into `args`.

- [ ] **Step 5.7: Lint + typecheck**

```bash
just check
```

- [ ] **Step 5.8: Commit**

```bash
git add src/thoth/cli_subcommands/resume.py src/thoth/cli_subcommands/status.py \
        src/thoth/cli_subcommands/config.py src/thoth/cli_subcommands/modes.py \
        src/thoth/cli_subcommands/providers.py tests/test_completion_sources.py
git commit -m "feat(completion): wire shell_complete callbacks on subcommand options"
```

`LEFTHOOK=0` not needed — no transitional state.

---

## Task 6: Add `--json` to `init`

**Why now:** Smallest possible `--json` rollout — `init` has no data to fetch; the envelope just confirms config write. Establishing the wrapper-layer pattern here (before T07's heavier handler extraction) keeps the diff focused.

**Files:**
- Modify: `src/thoth/cli_subcommands/init.py`
- Modify: `src/thoth/commands.py` — add `get_init_data()` returning init outcome dict (extracted from `init_command`)
- Create: `tests/test_get_init_data.py` (Category F)
- Append to: `tests/test_json_envelopes.py` (Category E — first row of the parametrize list)

- [ ] **Step 6.1: Failing F test — `get_init_data` extraction**

Create `tests/test_get_init_data.py`:

```python
"""Category F — get_init_data unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest


def test_get_init_data_returns_dict_with_config_path(isolated_thoth_home, monkeypatch):
    from thoth.commands import get_init_data

    data = get_init_data(non_interactive=True, config_path=None)
    assert isinstance(data, dict)
    assert "config_path" in data
    assert "created" in data
    assert isinstance(data["created"], bool)


def test_get_init_data_does_not_branch_on_as_json(isolated_thoth_home):
    """spec §7.2 critical invariant — `as_json` MUST NOT appear in handler signature."""
    import inspect

    from thoth.commands import get_init_data

    params = inspect.signature(get_init_data).parameters
    assert "as_json" not in params
```

- [ ] **Step 6.2: Failing E test — first envelope row**

Create `tests/test_json_envelopes.py`:

```python
"""Category E — `--json` envelope contract per command (spec §8.3).

The JSON_COMMANDS list grows as each subcommand T06–T13 adds `--json`.
Category H meta-test in test_ci_lint_rules.py uses an AST walker against
src/thoth/cli_subcommands/ to assert this list stays complete.
"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner


JSON_COMMANDS: list[tuple[str, list[str], int]] = [
    # (label, argv-after-cli, expected_exit_code)
    ("init_non_interactive", ["init", "--json", "--non-interactive"], 0),
    # T07–T13 will append rows for status, list, providers, config, modes,
    # ask, resume per the spec §10 commit sequence.
]


@pytest.fixture
def cli():
    from thoth.cli import cli as _cli
    return _cli


@pytest.mark.parametrize("label,argv,exit_code", JSON_COMMANDS, ids=[c[0] for c in JSON_COMMANDS])
def test_json_envelope_contract(label, argv, exit_code, cli, isolated_thoth_home):
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(cli, argv, catch_exceptions=False)

    assert result.exit_code == exit_code, f"{label}: stderr={result.stderr}"
    payload = json.loads(result.output)
    assert isinstance(payload, dict), f"{label}: not a dict"
    assert payload.get("status") in ("ok", "error"), f"{label}: bad status field"
    if payload["status"] == "ok":
        assert isinstance(payload.get("data"), dict), f"{label}: ok-envelope missing data dict"
    else:
        err = payload.get("error")
        assert isinstance(err, dict), f"{label}: error-envelope missing error dict"
        assert isinstance(err.get("code"), str)
        assert isinstance(err.get("message"), str)


def test_init_json_without_non_interactive_emits_JSON_REQUIRES_NONINTERACTIVE(
    cli, isolated_thoth_home
):
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(cli, ["init", "--json"], catch_exceptions=False)

    assert result.exit_code == 2
    payload = json.loads(result.output)
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "JSON_REQUIRES_NONINTERACTIVE"
```

- [ ] **Step 6.3: Run the tests — should fail**

```bash
uv run pytest tests/test_get_init_data.py tests/test_json_envelopes.py -v
```

Expected: failures (`AttributeError: get_init_data`, `Error: No such option: --json` or `--non-interactive`).

- [ ] **Step 6.4: Extract `get_init_data` in `commands.py`**

The current `init_command` is on `CommandHandler` (commands.py:43). Extract a sibling:

Add to `src/thoth/commands.py` (near `show_status`, before `_print_status_hints`):

```python
def get_init_data(*, non_interactive: bool, config_path: str | None) -> dict:
    """Pure data function for `thoth init`.

    Returns a dict describing the init outcome (config path, whether the
    file was newly created, and the version). Does NOT print Rich output.
    The legacy `init_command` continues to handle the human-readable path.
    """
    from thoth.config import THOTH_VERSION
    from thoth.paths import user_config_file

    target = Path(config_path).expanduser().resolve() if config_path else user_config_file()
    created = not target.exists()
    if created:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('version = "2.0"\n')
    return {
        "config_path": str(target),
        "created": created,
        "thoth_version": THOTH_VERSION,
        "non_interactive": non_interactive,
    }
```

Note: the existing `init_command` retains its Rich-printing behavior; T06 doesn't refactor it to call `get_init_data` because `init_command` does interactive prompting (which has no JSON analog). The two paths intentionally diverge: `--json` calls `get_init_data` (forced non-interactive); the default path calls `init_command` (interactive).

- [ ] **Step 6.5: Wire `--json` + `--non-interactive` on `cli_subcommands/init.py`**

Edit `src/thoth/cli_subcommands/init.py`:

```python
"""`thoth init` Click subcommand."""

from __future__ import annotations

import click

from thoth.cli_subcommands._option_policy import DEFAULT_HONOR, validate_inherited_options
from thoth.commands import CommandHandler, get_init_data
from thoth.config import ConfigManager
from thoth.json_output import emit_error, emit_json


@click.command(name="init")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.option(
    "--non-interactive",
    is_flag=True,
    help="Skip interactive prompts (required with --json)",
)
@click.pass_context
def init(ctx: click.Context, as_json: bool, non_interactive: bool) -> None:
    """Initialize thoth configuration."""
    validate_inherited_options(ctx, "init", DEFAULT_HONOR)

    config_path = ctx.obj.get("config_path") if ctx.obj else None

    if as_json:
        if not non_interactive:
            emit_error(
                "JSON_REQUIRES_NONINTERACTIVE",
                "thoth init --json requires --non-interactive",
                exit_code=2,
            )
        emit_json(get_init_data(non_interactive=True, config_path=config_path))

    config_manager = ConfigManager()
    config_manager.load_all_layers({"config_path": config_path})
    handler = CommandHandler(config_manager)
    handler.init_command(config_path=config_path)
```

- [ ] **Step 6.6: Run the tests — should pass**

```bash
uv run pytest tests/test_get_init_data.py tests/test_json_envelopes.py -v
```

Expected: green. The Category E parametrized test now has 1 row (init_non_interactive).

- [ ] **Step 6.7: Lint + typecheck**

```bash
just check
```

- [ ] **Step 6.8: Commit**

```bash
git add src/thoth/commands.py src/thoth/cli_subcommands/init.py \
        tests/test_get_init_data.py tests/test_json_envelopes.py
git commit -m "feat(cli): add --json to init"
```

Pre-commit gate: full hook set should pass.

---

## Task 7: Add `--json` to `status` (PATTERN ESTABLISHMENT)

**Why now:** `status` is the canonical B-deferred extraction example. T07 establishes the pattern shown in spec §6.6, with both `get_status_data()` AND the refactored `show_status()` calling it. Tasks T08–T12 reference T07 but show their own concrete deltas; no "similar to T07" hand-waves are allowed.

**Files:**
- Modify: `src/thoth/commands.py` — add `get_status_data()`; refactor `show_status` to call it
- Modify: `src/thoth/cli_subcommands/status.py` — add `--json` flag + body branch
- Create: `tests/test_get_status_data.py` (Category F)
- Append to: `tests/test_json_envelopes.py` (Category E — `status` row)

- [ ] **Step 7.1: Failing F tests — `get_status_data` extraction**

Create `tests/test_get_status_data.py`:

```python
"""Category F — get_status_data unit tests (spec §6.6 pattern reference)."""

from __future__ import annotations

import asyncio
import inspect
import json
from pathlib import Path

import pytest

from tests.conftest import make_operation


def _write_checkpoint(checkpoint_dir: Path, op) -> None:
    payload = {
        "id": op.id,
        "prompt": op.prompt,
        "mode": op.mode,
        "status": op.status,
        "created_at": op.created_at.isoformat(),
        "updated_at": op.updated_at.isoformat(),
        "output_paths": {},
        "input_files": [],
        "providers": {},
        "project": None,
        "output_dir": None,
        "error": None,
        "failure_type": None,
    }
    (checkpoint_dir / f"{op.id}.json").write_text(json.dumps(payload))


def test_get_status_data_returns_none_for_missing_operation(isolated_thoth_home, checkpoint_dir):
    from thoth.commands import get_status_data

    result = asyncio.run(get_status_data("not-a-real-op"))
    assert result is None


def test_get_status_data_returns_dict_for_existing_operation(checkpoint_dir):
    from thoth.commands import get_status_data

    op = make_operation("research-20260427-000000-aaaaaaaaaaaaaaaa", status="running")
    _write_checkpoint(checkpoint_dir, op)

    data = asyncio.run(get_status_data(op.id))
    assert isinstance(data, dict)
    assert data["operation_id"] == op.id
    assert data["status"] == "running"
    assert data["mode"] == "default"
    assert data["prompt"] == "test prompt"


def test_get_status_data_signature_excludes_as_json(isolated_thoth_home):
    """spec §7.2 critical invariant — `as_json` MUST NOT appear here."""
    from thoth.commands import get_status_data

    params = inspect.signature(get_status_data).parameters
    assert "as_json" not in params
```

- [ ] **Step 7.2: Failing E test — `status` row**

Append to `tests/test_json_envelopes.py` `JSON_COMMANDS` list:

```python
    ("status_missing_op", ["status", "research-MISSING", "--json"], 6),
```

Also append a dedicated assertion (since the parametrized test only checks shape):

```python
def test_status_json_missing_op_emits_OPERATION_NOT_FOUND(cli, isolated_thoth_home):
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(cli, ["status", "research-MISSING", "--json"], catch_exceptions=False)

    assert result.exit_code == 6
    payload = json.loads(result.output)
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "OPERATION_NOT_FOUND"
```

- [ ] **Step 7.3: Run the tests — should fail**

```bash
uv run pytest tests/test_get_status_data.py tests/test_json_envelopes.py -v
```

- [ ] **Step 7.4: Extract `get_status_data` in `commands.py`**

Add to `src/thoth/commands.py` (immediately before the existing `async def show_status`):

```python
async def get_status_data(operation_id: str) -> dict | None:
    """Pure data function for `thoth status OP_ID`.

    Returns a dict describing the operation, or None if not found.
    Per spec §7.2, this function NEVER takes an `as_json` flag — the
    JSON-vs-Rich choice lives at the subcommand-wrapper layer.
    """
    config = get_config()
    checkpoint_manager = CheckpointManager(config)

    operation = await checkpoint_manager.load(operation_id)
    if operation is None:
        return None

    return {
        "operation_id": operation.id,
        "prompt": operation.prompt,
        "mode": operation.mode,
        "status": operation.status,
        "created_at": operation.created_at.isoformat(),
        "updated_at": operation.updated_at.isoformat(),
        "project": operation.project,
        "providers": dict(operation.providers),
        "output_paths": {k: str(v) for k, v in operation.output_paths.items()},
        "failure_type": getattr(operation, "failure_type", None),
        "error": operation.error,
    }
```

- [ ] **Step 7.5: Refactor `show_status` to call `get_status_data`**

Replace `src/thoth/commands.py:167-213` (the existing `async def show_status` body) with:

```python
async def show_status(operation_id: str):
    """Show status of a specific operation (Rich rendering)."""
    data = await get_status_data(operation_id)
    if data is None:
        console.print(f"[red]Error:[/red] Operation {operation_id} not found")
        sys.exit(6)

    # Re-load the operation for the existing Rich layout (we still need
    # the OperationStatus object for _print_status_hints — keep that
    # path unchanged).
    config = get_config()
    checkpoint_manager = CheckpointManager(config)
    operation = await checkpoint_manager.load(operation_id)  # already known to exist
    assert operation is not None  # data was non-None above

    console.print("\nOperation Details:")
    console.print("─────────────────")
    console.print(f"ID:        {data['operation_id']}")
    console.print(f"Prompt:    {data['prompt']}")
    console.print(f"Mode:      {data['mode']}")
    console.print(f"Status:    {data['status']}")
    console.print(f"Started:   {operation.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

    if data["status"] in ["running", "completed"]:
        elapsed = datetime.now() - operation.created_at
        minutes = int(elapsed.total_seconds() / 60)
        console.print(f"Elapsed:   {minutes} minutes")

    if data["project"]:
        console.print(f"Project:   {data['project']}")

    if data["providers"]:
        console.print("\nProvider Status:")
        console.print("───────────────")
        for provider_name, provider_info in data["providers"].items():
            status_icon = "✓" if provider_info.get("status") == "completed" else "▶"
            status_text = provider_info.get("status", "unknown").title()
            console.print(f"{provider_name.title()}:  {status_icon} {status_text}")

    if data["output_paths"]:
        console.print("\nOutput Files:")
        console.print("────────────")
        if data["project"]:
            base_dir = Path(config.data["paths"]["base_output_dir"]) / data["project"]
            console.print(f"{base_dir}/")
        else:
            console.print("./")

        for _provider_name, path in data["output_paths"].items():
            console.print(f"  ├── {Path(path).name}")

    _print_status_hints(operation)
```

The two-`load` pattern (data fn + Rich path each call `load`) is acceptable for now — the cost is one extra filesystem read per `status` invocation, which is negligible. A future refactor could memoize the `OperationStatus` between the two calls.

- [ ] **Step 7.6: Wire `--json` on `cli_subcommands/status.py`**

Edit `src/thoth/cli_subcommands/status.py`:

```python
"""`thoth status OP_ID` Click subcommand."""

from __future__ import annotations

import asyncio

import click

from thoth.cli_subcommands._option_policy import DEFAULT_HONOR, validate_inherited_options
from thoth.commands import CommandHandler, get_status_data
from thoth.completion.sources import operation_ids as _operation_ids_completer
from thoth.config import ConfigManager
from thoth.json_output import emit_error, emit_json


@click.command(name="status")
@click.argument(
    "operation_id",
    metavar="OP_ID",
    required=False,
    shell_complete=_operation_ids_completer,
)
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.pass_context
def status(ctx: click.Context, operation_id: str | None, as_json: bool) -> None:
    """Check status of a research operation by ID."""
    validate_inherited_options(ctx, "status", DEFAULT_HONOR)

    if operation_id is None:
        if as_json:
            emit_error(
                "MISSING_OP_ID",
                "status command requires an operation ID",
                exit_code=2,
            )
        click.echo("Error: status command requires an operation ID", err=True)
        ctx.exit(2)

    if as_json:
        data = asyncio.run(get_status_data(operation_id))
        if data is None:
            emit_error(
                "OPERATION_NOT_FOUND",
                f"Operation {operation_id} not found",
                {"operation_id": operation_id},
                exit_code=6,
            )
        emit_json(data)

    config_path = ctx.obj.get("config_path") if ctx.obj else None
    config_manager = ConfigManager()
    config_manager.load_all_layers({"config_path": config_path})
    handler = CommandHandler(config_manager)
    handler.status_command(operation_id=operation_id)
```

- [ ] **Step 7.7: Run the tests — should pass**

```bash
uv run pytest tests/test_get_status_data.py tests/test_json_envelopes.py -v
uv run pytest tests/test_p16_pr2_resume.py -v  # baseline still green
```

- [ ] **Step 7.8: Lint + typecheck**

```bash
just check
```

- [ ] **Step 7.9: Commit**

```bash
git add src/thoth/commands.py src/thoth/cli_subcommands/status.py \
        tests/test_get_status_data.py tests/test_json_envelopes.py
git commit -m "feat(cli): add --json to status"
```

Pre-commit gate: full hook set must pass.

---

## Task 8: Add `--json` to `list`

**Why now:** Direct application of T07's pattern to `list_operations`. The data function returns a list of operation summaries; the Rich function continues to render the table.

**Files:**
- Modify: `src/thoth/commands.py` — add `get_list_data()`; refactor `list_operations` to call it
- Modify: `src/thoth/cli_subcommands/list_cmd.py` — add `--json` flag + body branch
- Create: `tests/test_get_list_data.py` (Category F)
- Append to: `tests/test_json_envelopes.py` `JSON_COMMANDS` list

- [ ] **Step 8.1: Failing F test**

Create `tests/test_get_list_data.py`:

```python
"""Category F — get_list_data unit tests."""

from __future__ import annotations

import asyncio
import inspect
import json
from pathlib import Path

from tests.conftest import make_operation


def _write_checkpoint(checkpoint_dir: Path, op) -> None:
    payload = {
        "id": op.id, "prompt": op.prompt, "mode": op.mode, "status": op.status,
        "created_at": op.created_at.isoformat(), "updated_at": op.updated_at.isoformat(),
        "output_paths": {}, "input_files": [], "providers": {},
        "project": None, "output_dir": None, "error": None, "failure_type": None,
    }
    (checkpoint_dir / f"{op.id}.json").write_text(json.dumps(payload))


def test_get_list_data_returns_dict_with_operations_list(checkpoint_dir):
    from thoth.commands import get_list_data

    op1 = make_operation("research-20260427-000000-aaaaaaaaaaaaaaaa", status="running")
    op2 = make_operation("research-20260427-000001-bbbbbbbbbbbbbbbb", status="completed")
    for op in (op1, op2):
        _write_checkpoint(checkpoint_dir, op)

    data = asyncio.run(get_list_data(show_all=True))
    assert isinstance(data, dict)
    assert "operations" in data
    assert isinstance(data["operations"], list)
    assert len(data["operations"]) == 2


def test_get_list_data_signature_excludes_as_json(isolated_thoth_home):
    from thoth.commands import get_list_data
    assert "as_json" not in inspect.signature(get_list_data).parameters


def test_get_list_data_filters_by_show_all_false(checkpoint_dir):
    """Only running/queued + last 24h appear when show_all=False."""
    from thoth.commands import get_list_data

    op_running = make_operation("research-20260427-000000-aaaaaaaaaaaaaaaa", status="running")
    _write_checkpoint(checkpoint_dir, op_running)

    data = asyncio.run(get_list_data(show_all=False))
    assert any(o["operation_id"] == op_running.id for o in data["operations"])
```

- [ ] **Step 8.2: Failing E test — `list` row**

Append to `tests/test_json_envelopes.py` `JSON_COMMANDS`:

```python
    ("list_empty", ["list", "--json"], 0),
    ("list_all_empty", ["list", "--all", "--json"], 0),
```

- [ ] **Step 8.3: Run tests — should fail**

```bash
uv run pytest tests/test_get_list_data.py tests/test_json_envelopes.py -v
```

- [ ] **Step 8.4: Extract `get_list_data` in `commands.py`**

Add to `src/thoth/commands.py` (immediately before `async def list_operations`):

```python
async def get_list_data(show_all: bool) -> dict:
    """Pure data function for `thoth list`.

    Returns a dict with `operations` (list of operation summaries) and
    `count`. Filters by show_all per the same rules as the Rich-printing
    list_operations: when False, only running/queued or last-24h ops.
    """
    config = get_config()
    checkpoint_manager = CheckpointManager(config)

    checkpoint_files = list(checkpoint_manager.checkpoint_dir.glob("*.json"))
    operations = []
    for checkpoint_file in checkpoint_files:
        operation_id = checkpoint_file.stem
        operation = await checkpoint_manager.load(operation_id)
        if operation:
            operations.append(operation)

    operations.sort(key=lambda op: op.created_at, reverse=True)

    if not show_all:
        cutoff_time = datetime.now() - timedelta(hours=24)
        operations = [
            op
            for op in operations
            if op.status in ["running", "queued"] or op.created_at > cutoff_time
        ]

    return {
        "count": len(operations),
        "operations": [
            {
                "operation_id": op.id,
                "prompt": op.prompt,
                "mode": op.mode,
                "status": op.status,
                "created_at": op.created_at.isoformat(),
                "project": op.project,
            }
            for op in operations
        ],
    }
```

- [ ] **Step 8.5: Refactor `list_operations` to call `get_list_data`**

Replace `commands.py:241-308` body with a call to `get_list_data`, then render Rich (table) using the dict + a paired re-load for `created_at` datetime objects (same pattern as T07's `show_status`):

```python
async def list_operations(show_all: bool):
    """List all operations (Rich rendering)."""
    data = await get_list_data(show_all=show_all)

    if data["count"] == 0:
        if show_all:
            console.print("No operations found.")
        else:
            console.print("No active operations found. Use --all to see all operations.")
        return

    config = get_config()
    checkpoint_manager = CheckpointManager(config)

    table = Table(title="Research Operations")
    table.add_column("ID", style="dim", width=40)
    table.add_column("Prompt", width=25)
    table.add_column("Status", width=10)
    table.add_column("Elapsed", width=8)
    table.add_column("Mode", width=15)

    for op_dict in data["operations"]:
        operation = await checkpoint_manager.load(op_dict["operation_id"])
        if operation is None:
            continue
        prompt_display = (
            operation.prompt[:22] + "..."
            if len(operation.prompt) > 25
            else operation.prompt
        )
        elapsed = datetime.now() - operation.created_at
        if elapsed.total_seconds() < 3600:
            elapsed_str = f"{int(elapsed.total_seconds() / 60)}m"
        else:
            elapsed_str = f"{int(elapsed.total_seconds() / 3600)}h"
        status_style = (
            "green"
            if operation.status == "completed"
            else "yellow"
            if operation.status == "running"
            else "dim"
        )
        table.add_row(
            operation.id,
            prompt_display,
            f"[{status_style}]{operation.status}[/{status_style}]",
            elapsed_str,
            operation.mode,
        )

    console.print(table)
    console.print("\nUse 'thoth status <ID>' for details")
```

- [ ] **Step 8.6: Wire `--json` on `cli_subcommands/list_cmd.py`**

Edit `src/thoth/cli_subcommands/list_cmd.py`:

```python
"""`thoth list` Click subcommand."""

from __future__ import annotations

import asyncio

import click

from thoth.cli_subcommands._option_policy import DEFAULT_HONOR, validate_inherited_options
from thoth.commands import CommandHandler, get_list_data
from thoth.config import ConfigManager
from thoth.json_output import emit_json


@click.command(name="list")
@click.option("--all", "show_all", is_flag=True, help="Include completed operations")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.pass_context
def list_cmd(ctx: click.Context, show_all: bool, as_json: bool) -> None:
    """List research operations."""
    validate_inherited_options(ctx, "list", DEFAULT_HONOR)

    if as_json:
        emit_json(asyncio.run(get_list_data(show_all=show_all)))

    config_path = ctx.obj.get("config_path") if ctx.obj else None
    config_manager = ConfigManager()
    config_manager.load_all_layers({"config_path": config_path})
    handler = CommandHandler(config_manager)
    handler.list_command(show_all=show_all)
```

- [ ] **Step 8.7: Run the tests — should pass**

```bash
uv run pytest tests/test_get_list_data.py tests/test_json_envelopes.py -v
```

- [ ] **Step 8.8: Lint + typecheck**

```bash
just check
```

- [ ] **Step 8.9: Commit**

```bash
git add src/thoth/commands.py src/thoth/cli_subcommands/list_cmd.py \
        tests/test_get_list_data.py tests/test_json_envelopes.py
git commit -m "feat(cli): add --json to list"
```

---

## Task 9: Add `--json` to `providers list/models/check`

**Why now:** All three providers leaves share the same B-deferred extraction shape — extract three sibling data functions (`get_providers_list_data`, `get_providers_models_data`, `get_providers_check_data`) and add `--json` to each leaf.

**Files:**
- Modify: `src/thoth/commands.py` — add three data functions; refactor existing `providers_list`/`providers_models`/`providers_check` to call them
- Modify: `src/thoth/cli_subcommands/providers.py` — add `--json` to all three leaves
- Create: `tests/test_get_providers_data.py` (Category F)
- Append to: `tests/test_json_envelopes.py` `JSON_COMMANDS`

- [ ] **Step 9.1: Failing F tests**

Create `tests/test_get_providers_data.py`:

```python
"""Category F — providers data-function unit tests."""

from __future__ import annotations

import inspect


def test_get_providers_list_data_returns_providers_dict(stub_config):
    from thoth.commands import get_providers_list_data

    data = get_providers_list_data(stub_config, filter_provider=None)
    assert isinstance(data, dict)
    assert "providers" in data
    assert isinstance(data["providers"], list)
    for entry in data["providers"]:
        assert "name" in entry
        assert "key_set" in entry


def test_get_providers_list_data_filters_by_provider(stub_config):
    from thoth.commands import get_providers_list_data

    data = get_providers_list_data(stub_config, filter_provider="openai")
    assert all(entry["name"] == "openai" for entry in data["providers"])


def test_get_providers_models_data_returns_models_per_provider(stub_config):
    from thoth.commands import get_providers_models_data

    data = get_providers_models_data(stub_config, filter_provider=None)
    assert "providers" in data
    for provider_entry in data["providers"]:
        assert "name" in provider_entry
        assert isinstance(provider_entry["models"], list)


def test_get_providers_check_data_returns_missing_list(stub_config):
    from thoth.commands import get_providers_check_data

    data = get_providers_check_data(stub_config)
    assert "missing" in data
    assert "complete" in data


def test_data_functions_exclude_as_json(stub_config):
    from thoth.commands import (
        get_providers_check_data,
        get_providers_list_data,
        get_providers_models_data,
    )
    for fn in (get_providers_list_data, get_providers_models_data, get_providers_check_data):
        assert "as_json" not in inspect.signature(fn).parameters
```

- [ ] **Step 9.2: Append to `tests/test_json_envelopes.py` `JSON_COMMANDS`**

```python
    ("providers_list", ["providers", "list", "--json"], 0),
    ("providers_models", ["providers", "models", "--json"], 0),
    ("providers_check", ["providers", "check", "--json"], 0),
    # NOTE: `providers check` exits 0 with `data.complete=False` if keys missing,
    # NOT exit 2 — JSON envelope decouples machine state from process exit code.
```

- [ ] **Step 9.3: Run tests — should fail**

- [ ] **Step 9.4: Extract three data functions in `commands.py`**

Add to `src/thoth/commands.py` (replacing the existing `providers_list`, `providers_models`, `providers_check` body OR adding new siblings; choose siblings to keep the legacy callers stable):

```python
def get_providers_list_data(
    config: ConfigManager, filter_provider: str | None = None
) -> dict:
    """Pure data function for `thoth providers list`."""
    import os
    import re

    providers = sorted(config.data["providers"].keys())
    if filter_provider and filter_provider not in providers:
        return {"providers": [], "filter_provider": filter_provider, "unknown": True}
    if filter_provider:
        providers = [filter_provider]

    out = []
    for name in providers:
        raw = config.data["providers"][name].get("api_key", "")
        m = re.match(r"\$\{(\w+)\}", raw or "")
        resolved = os.environ.get(m.group(1)) if m else (raw or None)
        out.append({"name": name, "key_set": bool(resolved)})
    return {"providers": out}


def get_providers_models_data(
    config: ConfigManager, filter_provider: str | None = None
) -> dict:
    """Pure data function for `thoth providers models`."""
    from thoth.config import BUILTIN_MODES

    seen: dict[str, set[str]] = {}
    for cfg in BUILTIN_MODES.values():
        p = str(cfg["provider"])
        if filter_provider and p != filter_provider:
            continue
        seen.setdefault(p, set()).add(str(cfg["model"]))

    return {
        "providers": [
            {"name": provider, "models": sorted(models)}
            for provider, models in sorted(seen.items())
        ],
        "filter_provider": filter_provider,
    }


def get_providers_check_data(config: ConfigManager) -> dict:
    """Pure data function for `thoth providers check`."""
    import os
    import re

    missing = []
    for name, p in config.data["providers"].items():
        raw = p.get("api_key", "")
        m = re.match(r"\$\{(\w+)\}", raw or "")
        resolved = os.environ.get(m.group(1)) if m else (raw or None)
        if not resolved:
            missing.append(name)
    return {"missing": missing, "complete": not missing}
```

Then refactor `providers_list`/`providers_models`/`providers_check` to call the data functions for their data, then render Rich. Each is a small mechanical change (e.g., `providers_list`):

```python
def providers_list(config: ConfigManager, filter_provider: str | None = None) -> int:
    """List configured providers and whether each has a usable key (Rich)."""
    from rich.console import Console as _Console

    data = get_providers_list_data(config, filter_provider=filter_provider)
    if data.get("unknown"):
        print(f"Error: Unknown provider: {filter_provider}", file=sys.stderr)
        print(
            f"Available providers: {', '.join(sorted(config.data['providers'].keys()))}",
            file=sys.stderr,
        )
        return 1

    _console = _Console()
    _console.print("Configured providers:")
    for entry in data["providers"]:
        _console.print(f"  {entry['name']:<12} {'key set' if entry['key_set'] else 'no key'}")
    return 0
```

Apply the same pattern to `providers_models` and `providers_check`.

- [ ] **Step 9.5: Add `--json` to providers leaves**

Edit `src/thoth/cli_subcommands/providers.py`. For each of the three leaves (`providers_list_cmd`, `providers_models_cmd`, `providers_check_cmd`), add `--json` and a wrapper branch.

Pattern for `providers_list_cmd`:

```python
@providers.command(name="list")
@click.option(
    "--provider",
    "-P",
    "filter_provider",
    type=click.Choice(PROVIDER_CHOICES),
    help="Filter by provider",
    shell_complete=_provider_names_completer,
)
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.pass_context
def providers_list_cmd(
    ctx: click.Context, filter_provider: str | None, as_json: bool
) -> None:
    """List available providers."""
    validate_inherited_options(ctx, "providers list", _PROVIDERS_LIST_HONOR)

    from thoth import commands as _commands
    from thoth.config import ConfigManager
    from thoth.json_output import emit_error, emit_json

    effective_provider = pick_value(filter_provider, ctx, "provider")

    if as_json:
        config_manager = ConfigManager()
        config_manager.load_all_layers({})
        data = _commands.get_providers_list_data(
            config_manager, filter_provider=effective_provider
        )
        if data.get("unknown"):
            emit_error(
                "UNKNOWN_PROVIDER",
                f"Unknown provider: {effective_provider}",
                {"provider": effective_provider},
                exit_code=1,
            )
        emit_json(data)

    # ... existing async invocation path unchanged
    keys = inherited_api_keys(ctx)
    if _has_api_keys(keys):
        sys.exit(asyncio.run(_commands.providers_command(
            show_list=True, filter_provider=effective_provider, cli_api_keys=keys,
        )))
    sys.exit(asyncio.run(_commands.providers_command(
        show_list=True, filter_provider=effective_provider,
    )))
```

Apply the analogous pattern to `providers_models_cmd` (also pass `refresh_cache`/`no_cache` flags into `get_providers_models_data` if relevant) and `providers_check_cmd`.

- [ ] **Step 9.6: Run tests + commit (per the standard gate)**

```bash
uv run pytest tests/test_get_providers_data.py tests/test_json_envelopes.py \
              tests/test_providers_subcommand.py -v
just check
git add src/thoth/commands.py src/thoth/cli_subcommands/providers.py \
        tests/test_get_providers_data.py tests/test_json_envelopes.py
git commit -m "feat(cli/providers): add --json to list/models/check"
```

---

## Task 10: Add `--json` to `config get/set/unset/list/path`

**Why now:** Config has six leaves; T10 covers the five non-edit ones (T11 handles `edit` separately because `$EDITOR` interleaves output). Keeping them grouped here mirrors the spec §10 commit numbering.

**Files:**
- Modify: `src/thoth/config_cmd.py` — add `get_config_get_data`, `get_config_set_data`, `get_config_unset_data`, `get_config_list_data`, `get_config_path_data`; refactor `_op_*` to call them
- Modify: `src/thoth/cli_subcommands/config.py` — add `--json` to all five non-edit leaves
- Create: `tests/test_get_config_data.py` (Category F)
- Append to: `tests/test_json_envelopes.py` `JSON_COMMANDS`

- [ ] **Step 10.1: Failing F tests**

Create `tests/test_get_config_data.py`:

```python
"""Category F — config data-function unit tests."""

from __future__ import annotations

import inspect

import pytest


def test_get_config_get_data_returns_value_dict(isolated_thoth_home):
    from thoth.config_cmd import get_config_get_data

    data = get_config_get_data("paths.base_output_dir", layer=None, raw=False, show_secrets=False)
    assert isinstance(data, dict)
    assert "key" in data
    assert "value" in data
    assert "found" in data
    assert data["found"] is True


def test_get_config_get_data_missing_key_returns_not_found(isolated_thoth_home):
    from thoth.config_cmd import get_config_get_data

    data = get_config_get_data("nonexistent.key", layer=None, raw=False, show_secrets=False)
    assert data["found"] is False


def test_get_config_get_data_masks_secret_when_not_show_secrets(isolated_thoth_home, monkeypatch):
    from thoth.config_cmd import get_config_get_data

    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret-value")
    data = get_config_get_data(
        "providers.openai.api_key", layer=None, raw=False, show_secrets=False
    )
    if data["found"]:
        assert "secret" not in str(data["value"]).lower() or "***" in str(data["value"])


def test_get_config_list_data_returns_layers(isolated_thoth_home):
    from thoth.config_cmd import get_config_list_data

    data = get_config_list_data(layer=None, keys_only=False, show_secrets=False)
    assert "config" in data or "keys" in data


def test_get_config_path_data_returns_path(isolated_thoth_home):
    from thoth.config_cmd import get_config_path_data

    data = get_config_path_data(project=False)
    assert "path" in data


def test_data_functions_exclude_as_json(isolated_thoth_home):
    import thoth.config_cmd as cc

    for name in (
        "get_config_get_data",
        "get_config_set_data",
        "get_config_unset_data",
        "get_config_list_data",
        "get_config_path_data",
    ):
        fn = getattr(cc, name)
        assert "as_json" not in inspect.signature(fn).parameters, name
```

- [ ] **Step 10.2: Append to `JSON_COMMANDS`**

```python
    ("config_get", ["config", "get", "paths.base_output_dir", "--json"], 0),
    ("config_get_missing", ["config", "get", "nonexistent.key", "--json"], 1),
    ("config_list", ["config", "list", "--json"], 0),
    ("config_path", ["config", "path", "--json"], 0),
    ("config_set", ["config", "set", "test.key", "value", "--json"], 0),
    ("config_unset", ["config", "unset", "test.key", "--json"], 0),
```

- [ ] **Step 10.3: Run tests — should fail**

- [ ] **Step 10.4: Extract data functions in `config_cmd.py`**

For each of the five `_op_*` functions, extract a sibling `get_config_*_data`. Show the `_op_get` extraction in full as the pattern:

```python
def get_config_get_data(
    key: str,
    *,
    layer: str | None,
    raw: bool,
    show_secrets: bool,
    config_path: str | Path | None = None,
) -> dict:
    """Pure data function for `thoth config get KEY`.

    Returns:
        {
            "key": str,
            "found": bool,
            "value": Any | None,
            "layer": str | None,
            "masked": bool,           # True iff secret was masked
        }
    """
    cm = _load_manager(config_path)

    if layer is not None:
        if layer not in _VALID_LAYERS:
            return {
                "key": key,
                "found": False,
                "value": None,
                "layer": layer,
                "masked": False,
                "error": "INVALID_LAYER",
            }
        data = cm.layers.get(layer, {})
    elif raw:
        merged: dict[str, Any] = {}
        for name in _VALID_LAYERS:
            layer_data = cm.layers.get(name) or {}
            merged = cm._deep_merge(merged, layer_data)
        data = merged
    else:
        data = cm.data

    found, value = _dotted_get(data, key)
    if not found:
        return {"key": key, "found": False, "value": None, "layer": layer, "masked": False}

    masked = False
    if _is_secret_key(key) and not show_secrets:
        value = _mask_secret(value)
        masked = True

    return {
        "key": key,
        "found": True,
        "value": value,
        "layer": layer,
        "masked": masked,
    }
```

Then refactor `_op_get` to call it:

```python
def _op_get(args: list[str], *, config_path: str | Path | None = None) -> int:
    layer: str | None = None
    raw = False
    as_json = False
    show_secrets = False
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
            raw = True; i += 1
        elif a == "--json":
            as_json = True; i += 1
        elif a == "--show-secrets":
            show_secrets = True; i += 1
        else:
            positional.append(a); i += 1

    if len(positional) != 1:
        console.print("[red]Error:[/red] config get takes exactly one KEY")
        return 2
    key = positional[0]

    data = get_config_get_data(
        key, layer=layer, raw=raw, show_secrets=show_secrets, config_path=config_path
    )

    if data.get("error") == "INVALID_LAYER":
        console.print(f"[red]Error:[/red] --layer must be one of {', '.join(_VALID_LAYERS)}")
        return 2
    if not data["found"]:
        console.print(f"[red]Error:[/red] key not found: {key}")
        return 1

    print(_render_scalar(data["value"], as_json))
    return 0
```

(The legacy `_op_get` continues to support its own `--json` flag for backwards compat with its old callsite — the wrapper layer in `cli_subcommands/config.py` is what actually binds `--json` to `emit_json` going forward; the inline `--json` in `_op_get` exists ONLY because the `cli_subcommands/config.py` wrappers still passthrough args today. After T10's wrapper rewrite below, the inline `_op_get` `--json` becomes dead code that the next refactor PR can remove. For T10's scope, we leave it in place to avoid breaking the passthrough path.)

Apply the same extraction to `_op_list`, `_op_path`, `_op_set`, `_op_unset`. For `_op_set` and `_op_unset`, the data function returns `{"key": ..., "value": ..., "wrote": True}` and `{"key": ..., "removed": True}`.

- [ ] **Step 10.5: Rewrite `cli_subcommands/config.py` wrappers**

Promote each leaf from passthrough to typed Click options so `--json` is captured by Click rather than passed through to `_op_*`. Show `config_get` as the pattern:

```python
@config.command(name="get")
@click.argument("key", shell_complete=_config_keys_completer)
@click.option(
    "--layer",
    "layer",
    type=click.Choice(_VALID_LAYERS),
    default=None,
    help="Read from a specific config layer",
)
@click.option("--raw", is_flag=True, help="Read pre-merge layer data")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.option("--show-secrets", is_flag=True, help="Reveal masked secret values")
@click.pass_context
def config_get(
    ctx, key, layer, raw, as_json, show_secrets
):
    validate_inherited_options(ctx, "config get", DEFAULT_HONOR)
    config_path = inherited_value(ctx, "config_path")

    if as_json:
        from thoth.config_cmd import get_config_get_data
        data = get_config_get_data(
            key, layer=layer, raw=raw, show_secrets=show_secrets, config_path=config_path,
        )
        if data.get("error") == "INVALID_LAYER":
            emit_error("INVALID_LAYER",
                       f"--layer must be one of {', '.join(_VALID_LAYERS)}",
                       exit_code=2)
        if not data["found"]:
            emit_error("KEY_NOT_FOUND", f"key not found: {key}", {"key": key}, exit_code=1)
        emit_json(data)

    # Existing rebuilt-args path for the Rich render
    rebuilt = [key]
    if layer is not None:
        rebuilt.extend(["--layer", layer])
    if raw:
        rebuilt.append("--raw")
    if show_secrets:
        rebuilt.append("--show-secrets")
    _dispatch(ctx, "get", tuple(rebuilt))
```

Apply the analogous pattern to `config_set`, `config_unset`, `config_list`, `config_path`. For each, promote `--json` to a typed Click option (instead of leaving it in the passthrough). The result of T10 is that ONLY `--json` is intercepted at the wrapper; everything else continues through `_dispatch`.

- [ ] **Step 10.6: Run tests + commit**

```bash
uv run pytest tests/test_get_config_data.py tests/test_json_envelopes.py \
              tests/test_config_cli.py -v
just check
git add src/thoth/config_cmd.py src/thoth/cli_subcommands/config.py \
        tests/test_get_config_data.py tests/test_json_envelopes.py
git commit -m "feat(cli/config): add --json to get/set/unset/list/path"
```

---

## Task 11: Add `--json` to `config edit` (special envelope after editor closes)

**Why now:** `edit` is special because `$EDITOR` runs interactively; the `--json` envelope is emitted AFTER the editor exits. Failure case: editor exits non-zero → `EDITOR_FAILED` envelope.

**Files:**
- Modify: `src/thoth/config_cmd.py` — add `get_config_edit_data` + refactor `_op_edit`
- Modify: `src/thoth/cli_subcommands/config.py` — add `--json` to `config_edit`
- Append to: `tests/test_get_config_data.py` (Category F)
- Append to: `tests/test_json_envelopes.py` (Category E)

- [ ] **Step 11.1: Failing F + E tests**

Append to `tests/test_get_config_data.py`:

```python
def test_get_config_edit_data_invokes_editor_returns_dict(isolated_thoth_home, monkeypatch):
    """Editor returns 0 → success envelope dict."""
    from thoth.config_cmd import get_config_edit_data

    monkeypatch.setenv("EDITOR", "true")  # `true` exits 0
    data = get_config_edit_data(project=False, config_path=None)
    assert data["editor_exit_code"] == 0
    assert "path" in data


def test_get_config_edit_data_propagates_editor_failure(isolated_thoth_home, monkeypatch):
    """Editor returns non-zero → caller decides EDITOR_FAILED envelope."""
    from thoth.config_cmd import get_config_edit_data

    monkeypatch.setenv("EDITOR", "false")  # `false` exits 1
    data = get_config_edit_data(project=False, config_path=None)
    assert data["editor_exit_code"] != 0
```

Append to `JSON_COMMANDS`:

```python
    ("config_edit", ["config", "edit", "--json"], 0),
```

(Set the `EDITOR` env to `true` in the parametrized fixture for this row, OR add a dedicated test below `JSON_COMMANDS` that overrides the env.)

- [ ] **Step 11.2: Implement**

Add to `src/thoth/config_cmd.py`:

```python
def get_config_edit_data(
    *, project: bool, config_path: str | Path | None
) -> dict:
    """Pure data function for `thoth config edit`.

    Returns dict with editor exit code and the path that was opened.
    Caller is responsible for translating non-zero `editor_exit_code`
    into an EDITOR_FAILED envelope.
    """
    import os
    import shutil
    import subprocess  # noqa: S404

    if _reject_config_project_conflict(project, config_path):
        return {"editor_exit_code": 2, "path": None, "error": "PROJECT_CONFIG_CONFLICT"}

    path = _target_path(project, config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        doc = tomlkit.document()
        doc["version"] = "2.0"
        path.write_text(tomlkit.dumps(doc))

    editor = os.environ.get("EDITOR") or shutil.which("vi") or "vi"
    rc = subprocess.call([editor, str(path)])  # noqa: S603
    return {"editor_exit_code": rc, "path": str(path)}
```

Refactor `_op_edit` to call `get_config_edit_data` and return its `editor_exit_code`.

Edit `cli_subcommands/config.py::config_edit`:

```python
@config.command(name="edit", context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.pass_context
def config_edit(ctx, args, as_json):
    validate_inherited_options(ctx, "config edit", DEFAULT_HONOR)
    config_path = inherited_value(ctx, "config_path")
    project = "--project" in args

    if as_json:
        from thoth.config_cmd import get_config_edit_data
        data = get_config_edit_data(project=project, config_path=config_path)
        if data.get("error") == "PROJECT_CONFIG_CONFLICT":
            emit_error("PROJECT_CONFIG_CONFLICT", "--config cannot be used with --project",
                       exit_code=2)
        if data["editor_exit_code"] != 0:
            emit_error(
                "EDITOR_FAILED",
                f"$EDITOR exited with code {data['editor_exit_code']}",
                {"exit_code": data["editor_exit_code"], "path": data["path"]},
                exit_code=1,
            )
        emit_json(data)

    _dispatch(ctx, "edit", args)
```

- [ ] **Step 11.3: Run tests + commit**

```bash
uv run pytest tests/test_get_config_data.py tests/test_json_envelopes.py -v
just check
git add src/thoth/config_cmd.py src/thoth/cli_subcommands/config.py \
        tests/test_get_config_data.py tests/test_json_envelopes.py
git commit -m "feat(cli/config): add --json to edit (special envelope after editor closes)"
```

---

## Task 12: Add `--json` to `modes list`

**Why now:** `modes list` already had `--json` pre-PR2 with the P11 schema; PR2 removed the legacy `modes --json` shim. T12 moves the schema into the unified envelope contract via `get_modes_list_data`.

**Files:**
- Modify: `src/thoth/modes_cmd.py` — add `get_modes_list_data`; refactor `_op_list` to call it for the data
- Modify: `src/thoth/cli_subcommands/modes.py` — add `--json` flag to `modes_list` Click command (it's already a typed option for `--name` per T05)
- Create: `tests/test_get_modes_data.py` (Category F)
- Append to: `tests/test_json_envelopes.py` (Category E)

- [ ] **Step 12.1: Failing F + E tests**

Create `tests/test_get_modes_data.py`:

```python
"""Category F — modes data-function unit tests."""

from __future__ import annotations

import inspect


def test_get_modes_list_data_returns_modes_list(isolated_thoth_home):
    from thoth.modes_cmd import get_modes_list_data

    data = get_modes_list_data(name=None, source="all", show_secrets=False)
    assert "modes" in data
    assert any(m["name"] == "default" for m in data["modes"])


def test_get_modes_list_data_filters_by_name(isolated_thoth_home):
    from thoth.modes_cmd import get_modes_list_data

    data = get_modes_list_data(name="default", source="all", show_secrets=False)
    assert data["mode"]["name"] == "default"


def test_get_modes_list_data_unknown_name_returns_none(isolated_thoth_home):
    from thoth.modes_cmd import get_modes_list_data

    data = get_modes_list_data(name="not-a-real-mode", source="all", show_secrets=False)
    assert data["mode"] is None


def test_signature_excludes_as_json(isolated_thoth_home):
    from thoth.modes_cmd import get_modes_list_data
    assert "as_json" not in inspect.signature(get_modes_list_data).parameters
```

Append to `JSON_COMMANDS`:

```python
    ("modes_list", ["modes", "list", "--json"], 0),
    ("modes_list_by_name", ["modes", "list", "--json", "--name", "default"], 0),
```

- [ ] **Step 12.2: Extract `get_modes_list_data` in `modes_cmd.py`**

```python
def get_modes_list_data(
    *,
    name: str | None,
    source: str,
    show_secrets: bool,
    config_path: str | None = None,
) -> dict:
    """Pure data function for `thoth modes list`.

    Returns either {"modes": [...]} (no name) or {"mode": {...} | None} (with name).
    """
    cm = ConfigManager(Path(config_path).expanduser().resolve() if config_path else None)
    cm.load_all_layers({})
    infos = list_all_modes(cm)

    if source != "all":
        infos = [m for m in infos if m.source == source]

    if name is not None:
        match = next((m for m in infos if m.name == name), None)
        return {"mode": _info_to_dict(match, show_secrets) if match else None}

    infos = sorted(infos, key=_sort_key)
    return {
        "schema_version": "1",
        "modes": [_info_to_dict(m, show_secrets) for m in infos],
    }
```

Refactor `_op_list` to call `get_modes_list_data` for its data. The existing `_op_list` already handles the `--json` flag inline; with T12, the wrapper layer in `cli_subcommands/modes.py` becomes the `--json` consumer (calling `emit_json(get_modes_list_data(...))`) and `_op_list` keeps its legacy inline `--json` for the rebuilt-args passthrough path (dead code candidate for a future cleanup).

- [ ] **Step 12.3: Add `--json` to `cli_subcommands/modes.py::modes_list`**

```python
@modes.command(name="list", context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.option(
    "--name",
    "name",
    default=None,
    help="Show detail for a single mode",
    shell_complete=_mode_names_completer,
)
@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")
@click.option("--source", "source", default="all", help="Filter by source")
@click.option("--show-secrets", "show_secrets", is_flag=True, help="Reveal masked secrets")
@click.pass_context
def modes_list(ctx, args, name, as_json, source, show_secrets):
    validate_inherited_options(ctx, "modes list", DEFAULT_HONOR)

    config_path = inherited_value(ctx, "config_path")

    if as_json:
        from thoth.modes_cmd import get_modes_list_data
        from thoth.json_output import emit_json
        emit_json(get_modes_list_data(
            name=name, source=source, show_secrets=show_secrets, config_path=config_path,
        ))

    from thoth.modes_cmd import modes_command

    rebuilt = list(args)
    if name is not None:
        rebuilt.extend(["--name", name])
    if source != "all":
        rebuilt.extend(["--source", source])
    if show_secrets:
        rebuilt.append("--show-secrets")

    if config_path is None:
        rc = modes_command("list", rebuilt)
    else:
        rc = modes_command("list", rebuilt, config_path=config_path)
    sys.exit(rc)
```

- [ ] **Step 12.4: Run tests + commit**

```bash
uv run pytest tests/test_get_modes_data.py tests/test_json_envelopes.py \
              tests/test_modes_cli.py tests/test_modes_cmd.py -v
just check
git add src/thoth/modes_cmd.py src/thoth/cli_subcommands/modes.py \
        tests/test_get_modes_data.py tests/test_json_envelopes.py
git commit -m "feat(cli/modes): add --json to list (replaces removed modes --json shim)"
```

---

## Task 13: Add `--json` to `ask` + `resume` (Option E)

**Why now:** Last `--json` rollout. Spec §6.7 + §6.8 lock the Option-E body shapes. Both subcommands gain `--json`; `ask --json` branches on `_is_background_mode` (auto-async for background modes); `resume --json` is a pure snapshot via `get_resume_snapshot_data`.

**Files:**
- Modify: `src/thoth/run.py` — add `get_resume_snapshot_data(operation_id) -> dict | None`
- Modify: `src/thoth/cli_subcommands/ask.py` — add `--json` + Option-E branching
- Modify: `src/thoth/cli_subcommands/resume.py` — add `--json` + snapshot branch
- Create: `tests/test_get_resume_snapshot_data.py` (Category F)
- Create: `tests/test_json_non_blocking.py` (Category G — 3 timing-assertion tests)
- Append to: `tests/test_json_envelopes.py` (Category E)

- [ ] **Step 13.1: Failing F + G tests**

Create `tests/test_get_resume_snapshot_data.py`:

```python
"""Category F — get_resume_snapshot_data unit tests (spec §6.8)."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

from tests.conftest import make_operation


def _write_checkpoint(checkpoint_dir: Path, op, **overrides) -> None:
    payload = {
        "id": op.id, "prompt": op.prompt, "mode": op.mode, "status": op.status,
        "created_at": op.created_at.isoformat(), "updated_at": op.updated_at.isoformat(),
        "output_paths": {}, "input_files": [], "providers": {},
        "project": None, "output_dir": None, "error": None, "failure_type": None,
        **overrides,
    }
    (checkpoint_dir / f"{op.id}.json").write_text(json.dumps(payload))


def test_get_resume_snapshot_data_returns_none_for_missing_op(isolated_thoth_home, checkpoint_dir):
    from thoth.run import get_resume_snapshot_data
    assert get_resume_snapshot_data("not-real") is None


def test_snapshot_running_op_returns_status_running(checkpoint_dir):
    from thoth.run import get_resume_snapshot_data

    op = make_operation("research-20260427-000000-aaaaaaaaaaaaaaaa", status="running")
    _write_checkpoint(checkpoint_dir, op)

    data = get_resume_snapshot_data(op.id)
    assert data["operation_id"] == op.id
    assert data["status"] == "running"


def test_snapshot_recoverable_failure_maps_failed_with_transient(checkpoint_dir):
    """spec §8.5 mapping: status=failed + failure_type!=permanent → recoverable_failure."""
    from thoth.run import get_resume_snapshot_data

    op = make_operation(
        "research-20260427-000000-aaaaaaaaaaaaaaaa", status="failed",
    )
    _write_checkpoint(
        checkpoint_dir, op,
        status="failed",
        failure_type="transient",
        error="rate limit exceeded",
    )

    data = get_resume_snapshot_data(op.id)
    assert data["status"] == "recoverable_failure"
    assert data["last_error"] == "rate limit exceeded"


def test_snapshot_failed_permanent_keeps_failed_status(checkpoint_dir):
    from thoth.run import get_resume_snapshot_data

    op = make_operation("research-20260427-000000-aaaaaaaaaaaaaaaa", status="failed")
    _write_checkpoint(
        checkpoint_dir, op, status="failed", failure_type="permanent", error="auth failed",
    )

    data = get_resume_snapshot_data(op.id)
    assert data["status"] == "failed_permanent"


def test_signature_excludes_as_json():
    from thoth.run import get_resume_snapshot_data
    assert "as_json" not in inspect.signature(get_resume_snapshot_data).parameters
```

Create `tests/test_json_non_blocking.py`:

```python
"""Category G — Option E non-blocking timing assertions (spec §8.4)."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from click.testing import CliRunner

from tests.conftest import make_operation


@pytest.fixture
def cli():
    from thoth.cli import cli as _cli
    return _cli


def _write_checkpoint(checkpoint_dir: Path, op, **overrides) -> None:
    payload = {
        "id": op.id, "prompt": op.prompt, "mode": op.mode, "status": op.status,
        "created_at": op.created_at.isoformat(), "updated_at": op.updated_at.isoformat(),
        "output_paths": {}, "input_files": [], "providers": {},
        "project": None, "output_dir": None, "error": None, "failure_type": None,
        **overrides,
    }
    (checkpoint_dir / f"{op.id}.json").write_text(json.dumps(payload))


def test_resume_json_returns_within_5s_for_running_op(cli, checkpoint_dir):
    op = make_operation("research-20260427-000000-aaaaaaaaaaaaaaaa", status="running")
    _write_checkpoint(checkpoint_dir, op)

    runner = CliRunner(mix_stderr=False)
    start = time.time()
    result = runner.invoke(cli, ["resume", op.id, "--json"], catch_exceptions=False)
    elapsed = time.time() - start

    assert elapsed < 5.0, f"resume --json took {elapsed:.2f}s (must be non-blocking)"
    payload = json.loads(result.output)
    assert payload["status"] == "ok"
    assert payload["data"]["status"] == "running"


def test_resume_json_recoverable_failure_returns_status_ok(cli, checkpoint_dir):
    """spec §8.5: command succeeded → status:'ok'; data.status describes the op."""
    op = make_operation("research-20260427-000000-aaaaaaaaaaaaaaaa", status="failed")
    _write_checkpoint(
        checkpoint_dir, op, status="failed", failure_type="transient",
        error="rate limit exceeded",
    )

    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(cli, ["resume", op.id, "--json"], catch_exceptions=False)

    payload = json.loads(result.output)
    assert payload["status"] == "ok"
    assert payload["data"]["status"] == "recoverable_failure"


def test_ask_json_background_mode_returns_within_5s(cli, isolated_thoth_home, monkeypatch):
    """ask --json in background mode auto-asyncs and returns op-id envelope."""
    monkeypatch.setenv("THOTH_TEST_MODE", "1")

    runner = CliRunner(mix_stderr=False)
    start = time.time()
    result = runner.invoke(
        cli,
        ["ask", "test prompt", "--mode", "deep_research", "--json", "--provider", "mock"],
        catch_exceptions=False,
    )
    elapsed = time.time() - start

    # If the test environment can't reach `deep_research` via mock provider, the
    # envelope may be an error envelope — that's still valid (returns within 5s).
    assert elapsed < 5.0, f"ask --json deep_research took {elapsed:.2f}s"
    payload = json.loads(result.output)
    assert payload["status"] in ("ok", "error")
    if payload["status"] == "ok":
        # Background mode → submit envelope (op-id present, no result inline).
        assert "operation_id" in payload["data"]
```

Append to `JSON_COMMANDS`:

```python
    # Note: ask/resume rows are smoke tests; G tests above carry the timing assertions.
    ("resume_missing_op", ["resume", "research-MISSING", "--json"], 6),
```

- [ ] **Step 13.2: Implement `get_resume_snapshot_data` in `run.py`**

Add to `src/thoth/run.py` (top-level, near `resume_operation`):

```python
def get_resume_snapshot_data(operation_id: str) -> dict | None:
    """Pure data function for `thoth resume OP_ID --json`.

    Reads the checkpoint and returns a snapshot dict. Per spec §6.8 +
    §8.5, this function NEVER advances state (no provider polling, no
    retries) and maps the on-disk status field as follows:

      status="failed", failure_type="permanent"  → "failed_permanent"
      status="failed", failure_type!=permanent  → "recoverable_failure"
      otherwise                                  → status verbatim

    Synchronous on purpose — completion-style "snapshot" semantics demand
    sub-second response time. Uses an in-line synchronous read of the
    checkpoint JSON rather than CheckpointManager.load (which is async).
    """
    import json
    from datetime import datetime
    from pathlib import Path as _Path

    from thoth.config import get_config

    config = get_config()
    checkpoint_dir = _Path(config.data["paths"]["checkpoint_dir"])
    checkpoint_file = checkpoint_dir / f"{operation_id}.json"
    if not checkpoint_file.exists():
        return None

    try:
        raw = json.loads(checkpoint_file.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    raw_status = raw.get("status")
    failure_type = raw.get("failure_type")

    if raw_status == "failed":
        snapshot_status = (
            "failed_permanent" if failure_type == "permanent" else "recoverable_failure"
        )
    else:
        snapshot_status = raw_status

    return {
        "operation_id": raw.get("id", operation_id),
        "status": snapshot_status,
        "mode": raw.get("mode"),
        "prompt": raw.get("prompt"),
        "created_at": raw.get("created_at"),
        "updated_at": raw.get("updated_at"),
        "providers": raw.get("providers", {}),
        "last_error": raw.get("error"),
        "failure_type": failure_type,
        "retry_count": raw.get("retry_count", 0),
    }
```

- [ ] **Step 13.3: Wire `--json` on `resume.py`**

Edit `src/thoth/cli_subcommands/resume.py` — add `--json`, the `as_json` param, and the snapshot branch BEFORE the existing async-resume call:

```python
@click.command(name="resume")
@click.argument("operation_id", metavar="OP_ID", shell_complete=_operation_ids_completer)
# ... existing options ...
@click.option("--json", "as_json", is_flag=True, help="Emit JSON snapshot envelope")
@click.pass_context
def resume(
    ctx, operation_id, verbose, config_path, quiet, no_metadata, timeout,
    api_key_openai, api_key_perplexity, api_key_mock, as_json,
):
    """Resume a previously-checkpointed operation by ID."""
    validate_inherited_options(ctx, "resume", _RESUME_HONOR)

    if as_json:
        import thoth.run as _thoth_run
        from thoth.cli import _apply_config_path
        from thoth.json_output import emit_error, emit_json

        effective_config = config_path or (ctx.obj or {}).get("config_path")
        _apply_config_path(effective_config)

        data = _thoth_run.get_resume_snapshot_data(operation_id)
        if data is None:
            emit_error(
                "OPERATION_NOT_FOUND",
                f"Operation {operation_id} not found",
                {"operation_id": operation_id},
                exit_code=6,
            )
        if data["status"] == "failed_permanent":
            emit_error(
                "OPERATION_FAILED_PERMANENTLY",
                data["last_error"] or "operation failed permanently",
                data,
                exit_code=7,
            )
        emit_json(data)

    # ... existing async-resume call unchanged ...
```

- [ ] **Step 13.4: Wire `--json` on `ask.py`**

Edit `src/thoth/cli_subcommands/ask.py` — add `--json` to the `_research_options` decorator stack OR as a sibling option (sibling is cleaner for T13's scope, since it's `ask`-specific behavior):

Add `@click.option("--json", "as_json", is_flag=True, help="Emit JSON envelope")` between the existing options and the `@click.pass_context` on `ask`.

In the `ask` body, AFTER the existing prompt-resolution + mutex checks but BEFORE the call to `_run_research_default`, insert the Option-E branching:

```python
if as_json:
    from thoth.config import BUILTIN_MODES, is_background_mode
    from thoth.json_output import emit_error, emit_json

    mode_config = BUILTIN_MODES.get(effective_mode, {})
    is_bg = is_background_mode(mode_config) if mode_config else False

    if is_bg or effective_async:
        # Background-mode (or explicit --async): submit + return op-id envelope.
        # We invoke _run_research_default with async_mode=True; it submits and
        # writes the checkpoint, then we read the operation_id back from the
        # most-recent checkpoint and emit the submit envelope.
        try:
            _run_research_default(
                mode=effective_mode, prompt=effective_prompt, async_mode=True,
                project=effective_project, output_dir=effective_output_dir,
                provider=effective_provider, input_file=effective_input_file,
                auto=effective_auto, verbose=False, cli_api_keys=cli_api_keys,
                combined=effective_combined, quiet=True, no_metadata=effective_no_metadata,
                timeout_override=effective_timeout, model_override=None,
            )
        except SystemExit as exc:
            # _run_research_default may sys.exit on submit success — that's normal.
            if exc.code not in (None, 0):
                emit_error(
                    "PROVIDER_FAILURE",
                    "ask --json submit failed",
                    {"exit_code": exc.code},
                    exit_code=1,
                )

        # Read the most-recently-created operation_id from the checkpoint store.
        from thoth.completion.sources import operation_ids
        ids = operation_ids(None, None, "")
        op_id = ids[-1] if ids else None
        emit_json({
            "operation_id": op_id,
            "status": "submitted",
            "mode": effective_mode,
            "provider": effective_provider,
        })
    else:
        # Immediate-mode: synchronous run; full result inline.
        # _run_research_default does the work; we capture the latest checkpoint
        # ID and re-read it for the envelope.
        try:
            _run_research_default(
                mode=effective_mode, prompt=effective_prompt, async_mode=False,
                project=effective_project, output_dir=effective_output_dir,
                provider=effective_provider, input_file=effective_input_file,
                auto=effective_auto, verbose=False, cli_api_keys=cli_api_keys,
                combined=effective_combined, quiet=True, no_metadata=effective_no_metadata,
                timeout_override=effective_timeout, model_override=None,
            )
        except SystemExit as exc:
            if exc.code not in (None, 0):
                emit_error(
                    "PROVIDER_FAILURE",
                    "ask --json failed",
                    {"exit_code": exc.code},
                    exit_code=1,
                )
        from thoth.completion.sources import operation_ids
        from thoth.run import get_resume_snapshot_data
        ids = operation_ids(None, None, "")
        op_id = ids[-1] if ids else None
        data = get_resume_snapshot_data(op_id) if op_id else None
        if data is None:
            emit_json({"status": "no_checkpoint", "mode": effective_mode})
        emit_json(data)
```

(Note: this implementation uses `_run_research_default`'s existing checkpoint side effect to obtain the operation_id post-hoc. A future PR could refactor `_run_research_default` to RETURN the operation_id directly, eliminating the post-hoc lookup; for T13's scope, the post-hoc approach keeps the diff minimal. Document this in the commit body.)

- [ ] **Step 13.5: Run tests + commit**

```bash
uv run pytest tests/test_get_resume_snapshot_data.py tests/test_json_non_blocking.py \
              tests/test_json_envelopes.py tests/test_p16_pr2_resume.py \
              tests/test_p16_pr2_ask.py -v
just check
git add src/thoth/run.py src/thoth/cli_subcommands/ask.py src/thoth/cli_subcommands/resume.py \
        tests/test_get_resume_snapshot_data.py tests/test_json_non_blocking.py \
        tests/test_json_envelopes.py
git commit -m "feat(cli): add --json to ask + resume (Option E paths)"
```

`LEFTHOOK=0` may be acceptable here ONLY IF the timing test (Category G) flakes on a slow CI; per spec §13, the 5s threshold may need to be relaxed to 10s. Document any flake in the commit body.

---

## Task 14: Add CI lint rule asserting `as_json` not in handlers

**Why now:** With T06–T13 done, every `--json` path lives at the wrapper layer. T14 enforces the spec §7.2 critical invariant via a 5-line meta-test that fails the next time someone tries to add `as_json` plumbing into a handler module.

**Files:**
- Create: `tests/test_ci_lint_rules.py` (Category H test 1)

- [ ] **Step 14.1: Write the test**

Create `tests/test_ci_lint_rules.py`:

```python
"""Category H — CI lint rule meta-tests (spec §7.2 + §6.5)."""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize(
    "handler_path",
    [
        "src/thoth/commands.py",
        "src/thoth/config_cmd.py",
        "src/thoth/modes_cmd.py",
    ],
)
def test_handler_modules_do_not_reference_as_json(handler_path):
    """spec §7.2 critical invariant — `as_json` MUST NOT appear in handler modules.

    The JSON-vs-Rich choice lives ONLY at the cli_subcommands/ wrapper
    layer. Handler modules expose pure data functions (`get_*_data`) that
    wrappers either render via Rich or wrap in `emit_json`.

    NOTE: This rule applies to NEW handler-layer code. The legacy
    `_op_get`/`_op_list`/`_op_*` functions in config_cmd.py + modes_cmd.py
    have inline `as_json` parsing kept for backward compatibility with
    the passthrough wrapper path. The lint rule grandfathers this by
    matching only `as_json:` in function signatures (not `as_json` as a
    local variable name).
    """
    content = (_REPO_ROOT / handler_path).read_text()
    # Forbid `as_json` as a function-signature parameter (preceded by `,` or `(`,
    # followed by `:` or `=` or `,`).
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # Exclude legacy local-variable assignments inside _op_* functions.
        if "as_json = " in line and "def " not in line:
            continue
        # The forbidden pattern: a function param named as_json.
        # Examples that should fail:
        #   def get_status_data(operation_id, as_json: bool = False) -> dict:
        #   def show_status(operation_id, *, as_json):
        if "as_json:" in line and "def " in line:
            pytest.fail(f"{handler_path}: handler signature contains as_json:\n  {line!r}")
        if "as_json=" in line and "def " in line and ")" not in line.split("def ")[0]:
            pytest.fail(f"{handler_path}: handler signature contains as_json=:\n  {line!r}")
```

- [ ] **Step 14.2: Run the test — should pass**

```bash
uv run pytest tests/test_ci_lint_rules.py -v
```

Expected: 3 passed. If any fails, T06–T13 left an `as_json` parameter in a handler signature — fix the offending file before committing.

- [ ] **Step 14.3: Commit**

```bash
git add tests/test_ci_lint_rules.py
git commit -m "test: add CI lint rule asserting as_json not in handlers"
```

---

## Task 15: Add CI lint rule asserting `JSON_COMMANDS` list completeness via AST walker

**Why now:** Without this meta-test, a future PR that adds a `--json` flag without updating `JSON_COMMANDS` would silently bypass the envelope-contract assertions. T15 ships the AST walker per spec §6.5 + §9.1 H.

**Files:**
- Append to: `tests/test_ci_lint_rules.py` (Category H tests 2–3)

- [ ] **Step 15.1: Append the AST walker test**

Append to `tests/test_ci_lint_rules.py`:

```python
import ast


_CLI_SUBCOMMANDS_DIR = _REPO_ROOT / "src" / "thoth" / "cli_subcommands"


def _discover_json_commands() -> set[str]:
    """Walk every cli_subcommands/*.py and return the set of registered command
    names that declare a `--json` Click option.

    Detection rule: any `@click.command(name="X")` or
    `@<group>.command(name="X")` decorator whose function body or sibling
    decorator stack contains a `@click.option("--json", ...)` declaration.
    """
    discovered: set[str] = set()
    for py_file in _CLI_SUBCOMMANDS_DIR.glob("*.py"):
        if py_file.name.startswith("_"):
            continue
        tree = ast.parse(py_file.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            cmd_name: str | None = None
            has_json = False
            for deco in node.decorator_list:
                if not isinstance(deco, ast.Call):
                    continue
                func = deco.func
                # Match `click.command(name="X")` or `<group>.command(name="X")`.
                is_command_deco = (
                    isinstance(func, ast.Attribute) and func.attr == "command"
                )
                if is_command_deco:
                    for kw in deco.keywords:
                        if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                            cmd_name = str(kw.value.value)
                # Match `click.option("--json", ...)`.
                is_option_deco = (
                    isinstance(func, ast.Attribute) and func.attr == "option"
                )
                if is_option_deco and deco.args:
                    first = deco.args[0]
                    if isinstance(first, ast.Constant) and first.value == "--json":
                        has_json = True
                        break
                    if (
                        isinstance(first, ast.Constant)
                        and isinstance(first.value, str)
                        and first.value.startswith("--json")
                    ):
                        has_json = True
                        break
            if cmd_name and has_json:
                discovered.add(cmd_name)
    return discovered


def test_JSON_COMMANDS_list_covers_every_subcommand_with_json_option():
    """Spec §6.5 + §9.1 H — JSON_COMMANDS in test_json_envelopes.py MUST list
    every subcommand that has `@click.option("--json", ...)`.

    If this test fails, a recent PR added `--json` to a subcommand without
    appending it to JSON_COMMANDS — add the row.
    """
    from tests.test_json_envelopes import JSON_COMMANDS

    discovered = _discover_json_commands()
    # Convert the parametrize list into a set of subcommand-name strings.
    listed: set[str] = set()
    for label, argv, _exit in JSON_COMMANDS:
        # The subcommand name is the first positional argv that isn't an option.
        # Subcommand names live at argv[0] for top-level commands or argv[0..1]
        # for groups (e.g. ["providers", "list", ...] → "list"; we want "list").
        positionals = [t for t in argv if not t.startswith("-")]
        if positionals:
            listed.add(positionals[-1] if len(positionals) > 1 else positionals[0])

    # Map discovered group leaves (e.g. "list" appears in both providers AND
    # config) — we just need every discovered name to appear in `listed`.
    missing = discovered - listed
    assert not missing, (
        f"Subcommands with --json option not covered by JSON_COMMANDS: {missing}. "
        f"Add a parametrize row in tests/test_json_envelopes.py."
    )


def test_AST_walker_finds_at_least_completion_init_status_list():
    """Sanity check on the walker — if it returns nothing, the patterns are wrong."""
    discovered = _discover_json_commands()
    # T04 + T06-T08 ensure these four are present at minimum.
    assert "completion" in discovered
    assert "init" in discovered
    assert "status" in discovered
    assert "list" in discovered
```

- [ ] **Step 15.2: Run the tests — should pass**

```bash
uv run pytest tests/test_ci_lint_rules.py -v
```

Expected: 5 passed (3 from T14 + 2 from T15). If `JSON_COMMANDS` is incomplete, fix it by appending the missing rows.

- [ ] **Step 15.3: Commit**

```bash
git add tests/test_ci_lint_rules.py
git commit -m "test: add CI lint rule asserting JSON_COMMANDS list completeness via AST walker"
```

---

## Task 16: Update planning/thoth.prd.v24.md F-70 status

**Why now:** Spec §13 calls out the stale PRD line. T16 flips it from aspirational to shipped — pure docs task.

**Files:**
- Modify: `planning/thoth.prd.v24.md` line 96

- [ ] **Step 16.1: Verify the current text**

```bash
sed -n '90,100p' planning/thoth.prd.v24.md
```

Expected: a line near 96 that says "Added shell completion support" (or similar) framed aspirationally.

- [ ] **Step 16.2: Edit the line**

Change "Added shell completion support" → "Shell completion shipped (`thoth completion bash|zsh|fish`) per P16 PR3."

- [ ] **Step 16.3: Commit**

```bash
git add planning/thoth.prd.v24.md
git commit -m "docs: update planning/thoth.prd.v24.md F-70 status"
```

---

## Task 17: Add `docs/json-output.md` envelope contract reference

**Why now:** spec §6.1 + acceptance criterion ("docs/json-output.md exists with per-command schemas") require this file. T17 ships it as the single user-facing reference for the envelope contract.

**Files:**
- Create: `docs/json-output.md`

- [ ] **Step 17.1: Write the doc**

Create `docs/json-output.md`:

```markdown
# JSON output (`--json`) — envelope contract

Every data/action admin command in thoth supports `--json` for scripted
consumption. The output is a single JSON object on stdout; the exit code
indicates success (0) or failure (non-zero).

## Envelope shapes

**Success:**

    {"status": "ok", "data": {...}}

**Error:**

    {"status": "error", "error": {"code": "STRING_CODE", "message": "...",
                                   "details": {...}?}}

`details` is optional and code-specific.

## Error codes (catalog)

| Code | Used by | Exit | Meaning |
|---|---|---|---|
| `OPERATION_NOT_FOUND` | `status`, `resume` | 6 | Op ID not in checkpoint store |
| `OPERATION_FAILED_PERMANENTLY` | `resume` | 7 | Permanent failure |
| `JSON_REQUIRES_NONINTERACTIVE` | `init` | 2 | `init --json` without `--non-interactive` |
| `EDITOR_FAILED` | `config edit` | 1 | `$EDITOR` exited non-zero |
| `UNSUPPORTED_SHELL` | `completion` | 2 | Shell name not in {bash, zsh, fish} |
| `INSTALL_REQUIRES_TTY` | `completion --install` | 2 | non-TTY + no `--force` + no `--manual` |
| `INSTALL_FILE_PERMISSION` | `completion --install` | 1 | Can't write to rc file |
| `KEY_NOT_FOUND` | `config get` | 1 | Config key doesn't exist |
| `INVALID_LAYER` | `config get --layer` | 2 | Click choice validation |
| `PROVIDER_FAILURE` | `ask`, `resume` | 1 | Upstream provider error |
| `API_KEY_MISSING` | `ask`, `resume`, `providers check` | 1 | Required key not set |
| `INTERRUPTED` | any | 130 | SIGINT during `--json` run |

## Per-command schemas (sketch)

**`status OP_ID --json`:**

    {"status": "ok",
     "data": {"operation_id": "...", "status": "running"|"completed"|...,
              "mode": "...", "prompt": "...",
              "providers": {...}, "output_paths": {...}}}

**`list --json`:**

    {"status": "ok",
     "data": {"count": N,
              "operations": [{"operation_id": "...", "status": "...", ...}, ...]}}

**`providers list --json`:**

    {"status": "ok",
     "data": {"providers": [{"name": "openai", "key_set": true}, ...]}}

**`completion <shell> --install --json`:**

    {"status": "ok",
     "data": {"shell": "bash", "action": "written"|"preview"|"skipped",
              "path": "/.../.bashrc", "message": "..."}}

**`resume OP_ID --json` (snapshot — never advances state):**

    {"status": "ok",
     "data": {"operation_id": "...", "status": "running"|"recoverable_failure"|...,
              "mode": "...", "prompt": "...", "last_error": "..."|null,
              "retry_count": N}}

`recoverable_failure` is an envelope-data state mapped from on-disk
`status="failed"` + `failure_type` not equal to `"permanent"`. The
COMMAND succeeded (`status:"ok"`); `data.status` describes the
operation. To advance/retry, run `thoth resume OP_ID` WITHOUT `--json`.

## Non-blocking guarantee (Option E)

`--json` is non-blocking and snapshot-shaped:

  * `ask --json` immediate-mode: synchronous; full result inline.
  * `ask --json` background-mode: auto-async — submit + return op-id envelope.
  * `resume --json`: pure snapshot; never polls; never advances state.

Tests assert these complete within 5 seconds.

## Uninstalling completion

The completion `--install` writes a fenced block:

    # >>> thoth completion >>>
    eval "$(_THOTH_COMPLETE=bash_source thoth)"
    # <<< thoth completion <<<

Remove with one sed invocation:

    sed -i '/# >>> thoth completion >>>/,/# <<< thoth completion <<</d' ~/.bashrc

A real `--uninstall` flag is a future PR.
```

- [ ] **Step 17.2: Commit**

```bash
git add docs/json-output.md
git commit -m "docs: add docs/json-output.md envelope contract reference"
```

---

## Task 18: Add Shell completion + JSON output sections to README

**Files:**
- Modify: `README.md`

- [ ] **Step 18.1: Insert new sections**

Append to `README.md` (after the existing usage sections):

```markdown
## Shell completion

Generate an `eval`-able script:

```bash
eval "$(thoth completion bash)"   # or: zsh, fish
```

Persistent install (writes a fenced block to your shell's rc file):

```bash
thoth completion bash --install         # interactive: detect + prompt before overwrite
thoth completion bash --install --force # CI-friendly: write/overwrite silently
thoth completion bash --install --manual # print block + instructions; never write
```

After install, `thoth resume <TAB>`, `thoth status <TAB>`, `thoth config get <TAB>`,
`thoth modes list --name <TAB>`, and `thoth providers list --provider <TAB>` complete
with live data.

## JSON output

Every data/action admin command supports `--json`:

```bash
thoth status OP_ID --json | jq '.data.status'
thoth providers list --json | jq '.data.providers[].name'
thoth list --json | jq '.data.operations[]'
```

See `docs/json-output.md` for the envelope contract and per-command schemas.
```

- [ ] **Step 18.2: Commit**

```bash
git add README.md
git commit -m "docs: add Shell completion + JSON output sections to README"
```

---

## Task 19: Append v3.0.0 CHANGELOG entries (additive)

**Why now:** PR2 already opened the `## [3.0.0]` section. T19 APPENDS the PR3 additions to the existing `### Added` subsection — DO NOT create a duplicate `## [3.0.0]` block.

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 19.1: Verify existing CHANGELOG**

```bash
grep -n "^## \[3.0.0\]\|^### Added" CHANGELOG.md | head -10
```

Expected: a single `## [3.0.0]` header with at least one `### Added` subsection.

- [ ] **Step 19.2: Append to the existing `### Added`**

Edit `CHANGELOG.md` — under the existing `### Added` subsection (do not create a new one), append:

```markdown
- `thoth completion {bash,zsh,fish}` — emit eval-able shell init scripts. Supports `--install` (TTY-detect + prompt-before-overwrite), `--install --force` (CI-friendly silent overwrite), `--install --manual` (print block + instructions; never write), and `--json` (structured success/error envelopes for install metadata or shell-validation errors). Closes PRD F-70.
- TAB completion of operation IDs (`resume`, `status`), mode names (`modes list --name`), config keys (`config get`), and provider names (`providers list/models/check --provider`).
- `--json` flag on every data/action admin command: `init`, `status`, `list`, `providers list/models/check`, `config get/set/unset/list/path/edit`, `modes list`, `ask`, `resume`. Envelope contract documented in `docs/json-output.md`.
- `ask --json` immediate-mode returns full result inline; background-mode auto-asyncs and returns an op-id submit envelope.
- `resume --json` is a pure snapshot — never advances state, never polls. Use without `--json` to retry.
```

- [ ] **Step 19.3: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: add v3.0.0 CHANGELOG entries (additive — completion + universal --json)"
```

---

## Task 20: Mark P16 PR3 complete in PROJECTS.md and verify release-please

**Why last:** Final commit. MUST go through the full hook set without `LEFTHOOK=0` per CLAUDE.md "Hook discipline".

**Files:**
- Modify: `PROJECTS.md`

- [ ] **Step 20.1: Flip the project header to `[x]`**

Edit `PROJECTS.md` line 454: `## [ ] Project P16 PR3:` → `## [x] Project P16 PR3:`.

- [ ] **Step 20.2: Check off all 28 task identifiers**

Within the P16 PR3 entry, change every `- [ ] [P16-PR3-T##]` and `- [ ] [P16-PR3-TS##]` to `- [x] ...`. There are 28 task identifiers (TS01–TS08, T01–T20).

Also flip `- [ ] Regression Test Status` → `- [x] Regression Test Status` once the gate below confirms green.

- [ ] **Step 20.3: Run the FULL final gate**

```bash
make env-check
just check
uv run pytest tests/ -v
./thoth_test -r --skip-interactive -q
git grep -nE "as_json:" src/thoth/commands.py src/thoth/config_cmd.py src/thoth/modes_cmd.py
```

Expected:
- `make env-check`: green
- `just check`: green
- `uv run pytest tests/`: ≥ 460 passed (391 PR2 baseline + ~70 PR3-new)
- `./thoth_test -r --skip-interactive -q`: 63+ passed
- The grep MUST return zero hits (handler signatures stay JSON-agnostic per spec §7.2)

- [ ] **Step 20.4: Verify release-please will propose v3.0.0**

```bash
git log --oneline main..HEAD | head -25
```

Expected: ~20 commits, all conventional-commits formatted (`feat:`, `test:`, `docs:`, possibly one `chore:` for T02). When this branch lands on `main`, release-please will see the cumulative `feat:` commits since v2.x and propose v3.0.0.

- [ ] **Step 20.5: Commit (NO `LEFTHOOK=0`)**

```bash
git add PROJECTS.md
git commit -m "docs(projects): mark P16 PR3 complete + verify release-please"
```

The full hook set MUST pass on this final commit. If anything red surfaces, fix it in a NEW commit (do NOT amend) before pushing.

---

## Self-Review

After completing all 20 tasks:

**1. Spec coverage** — every section/decision in `docs/superpowers/specs/2026-04-26-p16-pr3-design.md` is implemented:

| Spec section | Task(s) |
|---|---|
| §4 Q1-PR3 (Option E mode-aware non-blocking JSON) | Task 13 (ask + resume) |
| §4 Q2-PR3 (every dynamic completer + Click choice + mode_kind) | Task 3 (sources.py with all 5 functions including `mode_kind`), Task 5 (wired into 5 sites) |
| §4 Q3-PR3 (--install Q3-A + manual + force) | Tasks 3, 4 (install matrix) |
| §4 documented default — `JSON_COMMANDS` AST-walker completeness | Task 15 |
| §4 documented default — `as_json` lint rule | Task 14 |
| §4 documented default — single PR, ~20 commits | Tasks 1–20 (1:1 mapping) |
| §4 documented default — per-commit gates incl. final no-bypass | Tasks 1–20 (per-task gate sections + Task 20 explicit) |
| §4 documented default — `interactive.py::SlashCommandCompleter` migration deferred | NOT in plan (deferred to future PR per spec §3) |
| §4 documented default — `recoverable_failure` envelope shape | Task 13 (mapping in `get_resume_snapshot_data`) |
| §4 documented default — `result` field present in immediate-mode ask --json | Task 13 (immediate branch reads checkpoint snapshot inline) |
| §4 documented default — `mode_kind` dead code | Task 3 (sources.py) |
| §4 documented default — fenced markers for sed-uninstall | Task 3 (`fenced_block`), Task 17 (`docs/json-output.md` Uninstall section) |
| §5.2 file layout (16+ files) | Tasks 1, 3, 4, 6–13 cover production files; Task 17–19 cover doc files |
| §5.3 net code-line impact (~1630 LOC) | Distributed across all tasks |
| §5.4 what stays unchanged | `ThothGroup`, RUN_COMMANDS, existing tests, etc. — no task touches these |
| §6.1 `json_output.py` interface | Task 1 |
| §6.2 `completion/script.py` interface | Task 3 |
| §6.3 `completion/install.py` interface + 5-row matrix | Tasks 3, 4 |
| §6.4 `completion/sources.py` interface (5 functions) | Task 3 |
| §6.5 `cli_subcommands/completion.py` (shell NOT click.Choice) | Task 4 |
| §6.6 per-handler `get_*_data()` extraction pattern | Tasks 6 (init), 7 (status — pattern reference), 8 (list), 9 (providers ×3), 10 (config ×5), 11 (config edit), 12 (modes list), 13 (resume) |
| §6.7 `cli_subcommands/ask.py` Option E branching | Task 13 |
| §6.8 `cli_subcommands/resume.py` Option E snapshot | Task 13 |
| §7 data flow (8 paths) | Tests in Tasks 4, 6–13 cover each path |
| §8.1 error-code catalog (12 codes) | Tasks 4 (UNSUPPORTED_SHELL, INSTALL_REQUIRES_TTY, INSTALL_FILE_PERMISSION), 6 (JSON_REQUIRES_NONINTERACTIVE), 7 (OPERATION_NOT_FOUND), 10 (KEY_NOT_FOUND, INVALID_LAYER), 11 (EDITOR_FAILED), 13 (OPERATION_FAILED_PERMANENTLY, PROVIDER_FAILURE), Task 17 (docs all 12) |
| §8.2 exit codes unchanged | All tasks honor 0/1/2/6/7/130 |
| §8.3 `--json` invariants (5-point shape contract) | Tests in Tasks 1, 6–13 (per-row in `test_json_envelopes.py`) |
| §8.4 non-blocking guarantee (5s) | Task 13 (Category G timing tests) |
| §8.5 `recoverable_failure` envelope | Task 13 (mapping + Category G test) |
| §8.6 SIGINT handling | Inherited from PR2; documented in T17 |
| §9.1 8 test categories (~72 tests) | A: T01 (5) / B: T03 (3+3=6) / C: T03+T04 (5+5=10) / D: T03+T05 (10+5=15) / E: T06–T13 (~12 rows + dedicated assertions) / F: T06–T13 (~20 across 7 files) / G: T13 (3) / H: T14+T15 (5) |
| §9.2 per-commit gates | Task gate sections for T01–T20 |
| §9.3 TDD ordering | Each task: failing test → run-fail → implement → run-pass → commit |
| §10 commit sequence (20 commits) | Tasks 1–20 (1:1 mapping) |
| §11 acceptance criteria (32 items) | Each maps to at least one task; final acceptance gate runs in T20 |
| §12 dependencies (PR1, PR1.5, PR2, P12, P18, SlashCommandCompleter) | Respected — no task touches PR1 baselines beyond the help-renderer `completion` restoration in T04; SlashCommandCompleter not migrated |
| §13 open items / risks (5 items) | (a) Click 8.x fish — T02; (b) `get_resume_snapshot_data()` purity — T13 (synchronous file read, no provider calls); (c) Option E timing flake — T13 commit body documents 10s relaxation; (d) AST walker maintenance — T15 documents detection rules; (e) stale PRD reference — T16 |

**No spec gaps identified.** Every Q-decision and every documented default has a corresponding implementation step.

**2. Placeholder scan** — Grepped this plan for `TBD`, `TODO`, `similar to`, `appropriate`, `implement later`. The phrase "similar to T07" appears in the spec §10 commit list but does NOT appear in any plan task; T08–T12 each show concrete code (the `get_*_data` body + the wrapper branch). No "implement later" in code blocks.

**3. Type / naming consistency**

- `emit_json` / `emit_error` (NOT `print_json`) — used identically in Tasks 1, 4, 6–13. ✓
- `get_*_data()` naming — all 11 data functions use this prefix:
  - `get_init_data` (T06), `get_status_data` (T07), `get_list_data` (T08),
  - `get_providers_list_data` / `get_providers_models_data` / `get_providers_check_data` (T09),
  - `get_config_get_data` / `get_config_set_data` / `get_config_unset_data` / `get_config_list_data` / `get_config_path_data` (T10),
  - `get_config_edit_data` (T11),
  - `get_modes_list_data` (T12),
  - `get_resume_snapshot_data` (T13). ✓
- `JSON_COMMANDS` parametrize-list naming — used identically in T06 (creation), T07–T13 (extension), T15 (AST walker assertion). ✓
- `as_json` is the consistent flag name on every Click `--json` option (`@click.option("--json", "as_json", is_flag=True, ...)`) — used identically in T04, T06–T13. ✓
- Fenced markers `# >>> thoth completion >>>` / `# <<< thoth completion <<<` — identical across `script.py::fenced_block` (T03), `install.py::_BLOCK_RE` (T03), `docs/json-output.md` (T17). ✓
- `_SUPPORTED_SHELLS = ("bash", "zsh", "fish")` — identical in `script.py` and `cli_subcommands/completion.py`. ✓
- `InstallResult.action` literal type `"written"|"preview"|"skipped"` — declared once in `install.py`, asserted in tests via `assert result.action == "..."`. ✓

**4. Open items / risks called out for the executing agent**

- **T03 step 3.7 — `install.py` install logic carries the only TTY decision.** The CLI subcommand (T04) checks `sys.stdin.isatty()` and SHORT-CIRCUITS to emit `INSTALL_REQUIRES_TTY` BEFORE calling `install()`. So the matrix table's "non-TTY" rows are enforced at the wrapper layer, not the lib layer. The `install()` function itself never reads TTY state — it does what it's told.
- **T07 step 7.5 — refactored `show_status` re-loads the operation.** This is the documented two-`load` pattern. A future PR can memoize. For T07 scope, leave as-is.
- **T09 step 9.4 — refactor preserves legacy `providers_*` callsite contract.** The `providers_command` (async) in commands.py is still the entry point for the non-`--json` Rich path; the new sync `get_providers_*_data` functions are siblings, not replacements. The wrapper in `cli_subcommands/providers.py` picks based on `as_json`.
- **T10 step 10.4 — inline `as_json` in `_op_get`/`_op_list` becomes dead code.** After T10's wrapper rewrite, the legacy `_op_*` functions still parse `--json` from `args` (because the passthrough path may still pass it through). Category H test in T14 GRANDFATHERS this — it forbids `as_json:` only in function signatures, not as local variables. A future cleanup PR can remove the dead inline `--json` parsing in `_op_*`.
- **T13 step 13.4 — `ask --json` reads the operation_id post-hoc from the checkpoint store.** `_run_research_default` doesn't return the op_id; the workaround is to call `operation_ids(None, None, "")` and pick `[-1]` (most recent). Sufficient for T13 scope; a refactor of `_run_research_default` to return the op_id is a future PR.
- **T13 step 13.1 (Category G) — 5s timing threshold may flake on slow CI.** Per spec §13, relax to 10s if needed; document the change in the commit body. Do NOT remove the test — the contract is "non-blocking", which means seconds, not minutes.
- **T15 step 15.1 — AST walker maintenance.** If a future PR uses a non-standard `--json` declaration pattern (e.g., a custom decorator factory), the walker will miss it. Extending the walker is the responsibility of that future PR. Document the recognized pattern at the top of `_discover_json_commands`.
- **T20 step 20.5 — final commit MUST NOT use `LEFTHOOK=0`.** Per CLAUDE.md "Hook discipline" + spec §10. If the full hook fails, diagnose and fix in a NEW commit (don't amend).
- **`isolated_thoth_home` + `checkpoint_dir` fixtures** — defined in `tests/conftest.py:30-43`. Used by Categories C, D, F, G fixtures. Available globally to tests under `tests/`.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-04-26-p16-pr3-implementation.md`.**

Two execution options per the writing-plans skill:

1. **Subagent-Driven (recommended)** — Dispatch a fresh subagent per task, review between tasks, fast iteration. Each task is self-contained with TDD steps and explicit commit boundaries. Recommended for Tasks 9–13 in particular, where the B-deferred extraction touches multiple handlers in sequence and benefits from reviewer-in-the-loop validation.

2. **Inline Execution** — Execute tasks in this session using `superpowers:executing-plans`. Natural review checkpoints: after Task 5 (completion package fully wired), after Task 8 (`--json` pattern established + 3 commands shipped), after Task 13 (Option E paths complete + all `--json` shipped), and before Task 20 (final commit must pass full hook set).

After PR3 lands (Tasks 1–20 all green on `main`):
- PR2's earlier merge already opened the `## [3.0.0]` section. PR3's commits land on top.
- release-please observes the cumulative conventional-commits and proposes v3.0.0.
- Merging the release-please PR tags `v3.0.0` and triggers the publish workflow (TestPyPI → PyPI per `RELEASE.md`).
- Future PR: migrate `interactive.py::SlashCommandCompleter` to import from `completion/sources.py` (deferred per spec §3).
- Future PR: add `completion --uninstall` flag (deferred per spec §3 — sed one-liner is documented).
- Future PR: PowerShell completion support (deferred per spec §3).
