# P16 PR1 — CLI Refactor (Click Group, No Behavior Change)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor `thoth`'s top-level CLI from a single `@click.command()` with positional pseudo-dispatch into a `@click.group(cls=ThothGroup)` with first-class subcommands, while preserving every user-visible behavior bit-identically.

**Architecture:** Introduce a custom `ThothGroup(click.Group)` in `help.py` that handles three dispatch paths: registered subcommands (standard Click), positional mode names (routes to research), and bare-prompt fallback (default-mode research). Move each admin command into its own module under `src/thoth/cli_subcommands/` as a thin Click wrapper that delegates to existing handlers in `commands.py`/`config_cmd.py`/`modes_cmd.py`. Delete the imperative `if args[0] in COMMAND_NAMES` dispatch block. Replace the custom `ThothCommand.parse_args` `--help SUBCOMMAND` interceptor with Click's native `thoth SUBCOMMAND --help` support.

**Tech Stack:** Python 3.11+, Click 8.x, pytest, existing `isolated_thoth_home` test fixture, `./thoth_test` integration runner.

**Spec:** `docs/superpowers/specs/2026-04-25-promote-admin-commands-design.md` §5–§7

**Successor plans:** `2026-04-25-p16-pr2-breakage-and-verbs.md` (deferred), `2026-04-25-p16-pr3-automation-polish.md` (deferred)

---

## File Structure

**Create:**
- `src/thoth/cli_subcommands/__init__.py` — empty package marker.
- `src/thoth/cli_subcommands/init.py` — `init` Click subcommand wrapping `CommandHandler.init_command()`.
- `src/thoth/cli_subcommands/status.py` — `status` Click subcommand wrapping `CommandHandler.status_command()`.
- `src/thoth/cli_subcommands/list_cmd.py` — `list` Click subcommand (file named `list_cmd.py` to avoid Python keyword collision; decorator name is `"list"`).
- `src/thoth/cli_subcommands/providers.py` — `providers` Click subgroup with leaves `list`, `models`, `check` wrapping `providers_list`/`providers_models`/`providers_check`.
- `src/thoth/cli_subcommands/config.py` — `config` Click subgroup with leaves `get`, `set`, `unset`, `list`, `path`, `edit` wrapping `config_command(op, rest)`.
- `src/thoth/cli_subcommands/modes.py` — `modes` Click subgroup with leaf `list` (P12 will add `add`/`set`/`unset` later) wrapping `modes_command(op, rest)`.
- `src/thoth/cli_subcommands/help_cmd.py` — `help [TOPIC]` thin forwarder to `thoth [TOPIC] --help` (preserves `auth` topic).
- `tests/baselines/` — directory holding captured pre-refactor stdout fixtures (one file per invocation pattern).
- `tests/test_p16_thothgroup.py` — unit tests for `ThothGroup`'s three overrides.
- `tests/test_p16_dispatch_parity.py` — parametrized parity tests comparing post-refactor invocations against captured baselines.
- `tests/test_p16_surprising_parses.py` — explicit edge-case tests (subcommand-vs-bare-prompt, missing-args).
- `tests/conftest_p16.py` — fixtures for parity baseline loading and `CliRunner` setup.

**Modify:**
- `src/thoth/cli.py` — replace `@click.command()` + positional `args` with `@click.group(cls=ThothGroup)`; delete imperative dispatch block (lines 292-421); add `cli.add_command(...)` registrations; update help-string examples (lines 184-188).
- `src/thoth/help.py` — replace `ThothCommand` class with `ThothGroup`; delete `show_init_help()`, `show_status_help()`, `show_list_help()`, `show_providers_help()`, `show_config_help()`, `show_modes_help()`; delete `HELP_TOPICS` and `COMMAND_NAMES`; keep `show_auth_help()`; rename `COMMANDS` tuple to `RUN_COMMANDS` + `ADMIN_COMMANDS`; implement two-section help renderer.

**Test paths:**
- `tests/baselines/*.json` (created)
- `tests/test_p16_thothgroup.py` (created)
- `tests/test_p16_dispatch_parity.py` (created)
- `tests/test_p16_surprising_parses.py` (created)
- `tests/conftest_p16.py` (created)
- All existing `tests/test_*.py` continue to pass unchanged
- `./thoth_test -r` continues to pass (integration suite)

---

## Task 1: Capture pre-refactor parity baselines (the test foundation)

**Why first:** PR1's "no user-visible behavior change" promise is verifiable only if we capture baseline outputs *before* any code changes. Run this task on the current `main` branch state; commit baselines; then begin refactor work in subsequent tasks.

**Files:**
- Create: `tests/baselines/` directory
- Create: `tests/conftest_p16.py`
- Create: `tests/test_p16_dispatch_parity.py`
- Create: `tests/baselines/capture_baselines.py` (one-shot script, removed after baselines committed)

- [ ] **Step 1.1: Create the baseline-capture script**

Create `tests/baselines/capture_baselines.py`:

```python
#!/usr/bin/env python
"""One-shot script: capture current `thoth` output for every parity-tested invocation.

Run BEFORE any refactor code lands. Writes JSON baseline files into
tests/baselines/. Each baseline records exit code, stdout, stderr.

Usage:
    THOTH_TEST_MODE=1 python tests/baselines/capture_baselines.py

After baselines are committed, this script is deleted in Task 15.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

BASELINES_DIR = Path(__file__).parent

# (label, argv) pairs. Label is the baseline filename stem.
INVOCATIONS: list[tuple[str, list[str]]] = [
    ("help", ["--help"]),
    ("version_short", ["-V"]),
    ("version_long", ["--version"]),
    ("init_help", ["init", "--help"]),
    ("status_no_args", ["status"]),
    ("list_help", ["list", "--help"]),
    ("providers_no_args", ["providers"]),
    ("providers_list", ["providers", "list"]),
    ("config_no_args", ["config"]),
    ("config_list", ["config", "list"]),
    ("modes_no_args", ["modes"]),
    ("help_init", ["help", "init"]),
    ("help_auth", ["help", "auth"]),
    ("help_unknown_topic", ["help", "nosuchtopic"]),
    ("unknown_command", ["nonexistentword"]),
]


def capture(label: str, argv: list[str]) -> dict:
    result = subprocess.run(
        ["thoth", *argv],
        capture_output=True,
        text=True,
        timeout=30,
        env={"THOTH_TEST_MODE": "1", "PATH": "/usr/bin:/bin"},
    )
    return {
        "label": label,
        "argv": argv,
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def main() -> int:
    BASELINES_DIR.mkdir(exist_ok=True)
    for label, argv in INVOCATIONS:
        baseline = capture(label, argv)
        out_path = BASELINES_DIR / f"{label}.json"
        out_path.write_text(json.dumps(baseline, indent=2, sort_keys=True))
        print(f"captured: {label} (exit={baseline['exit_code']})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 1.2: Run baseline capture against pre-refactor `thoth`**

Run: `python tests/baselines/capture_baselines.py`
Expected: 15 JSON files appear in `tests/baselines/`. Each has `exit_code`, `stdout`, `stderr` keys. Manually spot-check `tests/baselines/help.json` to confirm it contains the current `--help` output.

- [ ] **Step 1.3: Create the parity-test fixture module**

Create `tests/conftest_p16.py`:

```python
"""Test fixtures for P16 PR1 parity testing."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import TypedDict

import pytest

BASELINES_DIR = Path(__file__).parent / "baselines"


class BaselineRecord(TypedDict):
    label: str
    argv: list[str]
    exit_code: int
    stdout: str
    stderr: str


@pytest.fixture
def baseline() -> callable:
    def _load(label: str) -> BaselineRecord:
        path = BASELINES_DIR / f"{label}.json"
        return json.loads(path.read_text())

    return _load


@pytest.fixture
def run_thoth() -> callable:
    def _run(argv: list[str]) -> tuple[int, str, str]:
        result = subprocess.run(
            ["thoth", *argv],
            capture_output=True,
            text=True,
            timeout=30,
            env={"THOTH_TEST_MODE": "1", "PATH": "/usr/bin:/bin"},
        )
        return result.returncode, result.stdout, result.stderr

    return _run
```

- [ ] **Step 1.4: Write parity tests against baselines**

Create `tests/test_p16_dispatch_parity.py`:

```python
"""P16-TS01..15: post-refactor invocations match pre-refactor baselines.

Each test parametrizes one captured invocation. CI runs these in PR1 to
prove "no user-visible behavior change."

Skipped before parity is in scope (e.g. if THOTH_PARITY_SKIP=1 env is set
during early refactor scaffolding). Re-enabled by Task 15.
"""

from __future__ import annotations

import os

import pytest

PARITY_LABELS = [
    "help",
    "version_short",
    "version_long",
    "init_help",
    "status_no_args",
    "list_help",
    "providers_no_args",
    "providers_list",
    "config_no_args",
    "config_list",
    "modes_no_args",
    "help_init",
    "help_auth",
    "help_unknown_topic",
    "unknown_command",
]


@pytest.mark.parametrize("label", PARITY_LABELS)
def test_dispatch_parity(label: str, baseline, run_thoth):
    """P16-TS01: post-refactor exit_code matches baseline; stdout structurally
    equivalent (allowing for whitespace/color drift); stderr similar."""
    if os.getenv("THOTH_PARITY_SKIP") == "1":
        pytest.skip("parity gate temporarily disabled during scaffolding")

    expected = baseline(label)
    exit_code, stdout, stderr = run_thoth(expected["argv"])

    assert exit_code == expected["exit_code"], (
        f"exit_code mismatch for {label}: got {exit_code}, "
        f"baseline {expected['exit_code']}"
    )
    # stdout: line-set equality (tolerates re-ordering of help sections; we
    # explicitly assert structure in test_p16_thothgroup.py for help layout)
    assert sorted(stdout.splitlines()) == sorted(expected["stdout"].splitlines()), (
        f"stdout drift for {label}"
    )
```

> **Note on `help` parity**: The two-section help layout is an *intentional* user-visible change in PR1. Task 11 will replace this `help` test entry with structural assertions (sections present, modes listed, examples present) rather than line-set equality. For now, the test will fail post-refactor on `help` — that's expected and is the trigger for Task 11.

- [ ] **Step 1.5: Run baseline capture and parity test on current code (sanity)**

Run: `pytest tests/test_p16_dispatch_parity.py -v`
Expected: All 15 tests PASS (we captured and tested against current code; parity is trivial pre-refactor).

If any fail, the baseline capture script has a bug — fix before proceeding.

- [ ] **Step 1.6: Commit baselines + parity test**

```bash
git add tests/baselines/ tests/conftest_p16.py tests/test_p16_dispatch_parity.py
git commit -m "test(p16): capture pre-refactor parity baselines for PR1 gate"
```

---

## Task 2: Add `ThothGroup` skeleton (TDD)

**Files:**
- Modify: `src/thoth/help.py` (add `ThothGroup` class)
- Create: `tests/test_p16_thothgroup.py`

- [ ] **Step 2.1: Write failing tests for `ThothGroup.resolve_command`**

Create `tests/test_p16_thothgroup.py`:

```python
"""P16-TS02..06: ThothGroup unit tests."""

from __future__ import annotations

import click
import pytest
from click.testing import CliRunner

from thoth.help import ThothGroup


@pytest.fixture
def fake_group() -> click.Group:
    """Minimal ThothGroup with one registered subcommand for testing."""

    @click.group(cls=ThothGroup)
    def cli():
        pass

    @cli.command(name="known")
    def known_cmd():
        click.echo("known invoked")

    return cli


def test_resolve_command_returns_none_for_unknown(fake_group):
    """P16-TS02: resolve_command returns None for unregistered args
    (so invoke can take over for mode-positional / bare-prompt fallback)."""
    runner = CliRunner()
    ctx = click.Context(fake_group)
    result = fake_group.resolve_command(ctx, ["unknown_word"])
    assert result == (None, None, ["unknown_word"]) or result is None
```

Note: Click's `resolve_command` signature is `(ctx, args) -> (name, command, remaining_args)`. The exact return shape for the "not found" case differs between Click versions; the test asserts the *behavior* (no exception, no command) rather than the exact tuple.

- [ ] **Step 2.2: Run test to verify it fails**

Run: `pytest tests/test_p16_thothgroup.py::test_resolve_command_returns_none_for_unknown -v`
Expected: FAIL with `ImportError` or `AttributeError` — `ThothGroup` doesn't exist yet.

- [ ] **Step 2.3: Add minimal `ThothGroup` to `help.py`**

In `src/thoth/help.py`, after the existing imports and before the `ThothCommand` class definition, add:

```python
class ThothGroup(click.Group):
    """Top-level Click group for `thoth`.

    Adds three behaviors a stock click.Group can't provide:
      1. resolve_command returns None instead of raising on unknown args
         (so invoke can dispatch mode-positional or bare-prompt fallback).
      2. invoke routes positional mode names to the research path.
      3. invoke routes bare prompts to default-mode research.

    The two-section help renderer is added in Task 11.
    """

    def resolve_command(self, ctx: click.Context, args: list[str]):
        try:
            return super().resolve_command(ctx, args)
        except click.UsageError:
            # Caller (invoke) will handle mode-positional and bare-prompt cases.
            return None, None, args
```

- [ ] **Step 2.4: Run test to verify it passes**

Run: `pytest tests/test_p16_thothgroup.py::test_resolve_command_returns_none_for_unknown -v`
Expected: PASS.

- [ ] **Step 2.5: Add `invoke` override for mode-positional and bare-prompt routing**

Append to the `ThothGroup` class:

```python
    def invoke(self, ctx: click.Context):
        from thoth.config import BUILTIN_MODES

        args = ctx.protected_args + ctx.args
        if args:
            first = args[0]
            # Path 1: registered subcommand → standard dispatch
            if first in self.commands:
                return super().invoke(ctx)
            # Path 2: positional mode dispatch
            if first in BUILTIN_MODES:
                prompt = " ".join(args[1:]) if len(args) > 1 else ""
                return _run_research_default(
                    mode=first, prompt=prompt, ctx_obj=ctx.obj
                )
            # Path 3: bare-prompt fallback (whole arg vector is the prompt)
            prompt = " ".join(args)
            return _run_research_default(
                mode="default", prompt=prompt, ctx_obj=ctx.obj
            )
        # No args: standard group help (Click default)
        return super().invoke(ctx)
```

`_run_research_default` is extracted from current `cli.py` bare-prompt code in Task 3.

- [ ] **Step 2.6: Write test for mode-positional routing**

Append to `tests/test_p16_thothgroup.py`:

```python
def test_invoke_routes_mode_positional(fake_group, monkeypatch):
    """P16-TS03: invoke routes BUILTIN_MODES first arg to research path."""
    captured = {}

    def fake_run(mode, prompt, ctx_obj):
        captured["mode"] = mode
        captured["prompt"] = prompt

    # Stub _run_research_default in the help module
    monkeypatch.setattr("thoth.help._run_research_default", fake_run)
    monkeypatch.setattr("thoth.config.BUILTIN_MODES", {"deep_research", "default"})

    runner = CliRunner()
    result = runner.invoke(fake_group, ["deep_research", "explain", "X"])

    assert captured == {"mode": "deep_research", "prompt": "explain X", "ctx_obj": None}
    assert result.exit_code == 0


def test_invoke_routes_bare_prompt(fake_group, monkeypatch):
    """P16-TS04: invoke routes unknown first-word to default-mode bare-prompt."""
    captured = {}

    def fake_run(mode, prompt, ctx_obj):
        captured["mode"] = mode
        captured["prompt"] = prompt

    monkeypatch.setattr("thoth.help._run_research_default", fake_run)
    monkeypatch.setattr("thoth.config.BUILTIN_MODES", {"deep_research", "default"})

    runner = CliRunner()
    result = runner.invoke(fake_group, ["explain", "transformers"])

    assert captured == {"mode": "default", "prompt": "explain transformers"}


def test_invoke_routes_registered_subcommand(fake_group):
    """P16-TS05: invoke routes a registered subcommand via standard Click."""
    runner = CliRunner()
    result = runner.invoke(fake_group, ["known"])
    assert result.exit_code == 0
    assert "known invoked" in result.output
```

- [ ] **Step 2.7: Run new tests to verify they fail correctly**

Run: `pytest tests/test_p16_thothgroup.py -v`
Expected: `test_resolve_command_returns_none_for_unknown` PASS; the three new tests FAIL with `AttributeError: module 'thoth.help' has no attribute '_run_research_default'`.

- [ ] **Step 2.8: Add `_run_research_default` stub in `help.py`**

In `src/thoth/help.py`, before the `ThothGroup` class:

```python
def _run_research_default(mode: str, prompt: str, ctx_obj=None) -> None:
    """Run a research operation in the given mode with the given prompt.

    Extracted from cli.py's bare-prompt path in Task 3 (this is currently a
    stub — the real implementation arrives when cli.py is converted).
    """
    raise NotImplementedError("Wired up in Task 3 when cli.py converts to group")
```

- [ ] **Step 2.9: Re-run tests; expect them to PASS now (the stub is monkeypatched in tests)**

Run: `pytest tests/test_p16_thothgroup.py -v`
Expected: All 4 tests PASS (the tests `monkeypatch` the stub, so the `NotImplementedError` is never raised).

- [ ] **Step 2.10: Commit**

```bash
git add src/thoth/help.py tests/test_p16_thothgroup.py
git commit -m "feat(cli): add ThothGroup skeleton with three dispatch paths (P16 PR1)"
```

---

## Task 3: Convert top-level `cli` to `@click.group(cls=ThothGroup)` and wire `_run_research_default`

**Files:**
- Modify: `src/thoth/cli.py` (replace `@click.command()` with `@click.group(cls=ThothGroup, ...)`; remove `nargs=-1` `args`; add `_run_research_default` extracted from current bare-prompt block)
- Modify: `src/thoth/help.py` (replace `_run_research_default` stub with `from thoth.cli import _run_research_default` indirection — or move the function to a shared module)

**Note:** This task creates a temporary state where the imperative `if args[0] in COMMAND_NAMES` block is still present but unused (it was reachable via `nargs=-1`; once we remove that, it becomes dead code). Tasks 4-10 wire each subcommand into the group; Task 14 deletes the dead dispatch block.

- [ ] **Step 3.1: Disable parity tests temporarily**

Run: `THOTH_PARITY_SKIP=1 pytest tests/test_p16_dispatch_parity.py -v`
Expected: 15 SKIPPED.

(We re-enable in Task 15. The parity tests would fail mid-refactor in inconsistent ways; gating them keeps the test signal meaningful.)

- [ ] **Step 3.2: Extract `_run_research_default` from current `cli.py` bare-prompt path**

In `src/thoth/cli.py`, identify the existing bare-prompt code that runs research when `final_mode and final_prompt` are both set (currently around lines 438-466). Extract it into a new module-level function:

```python
def _run_research_default(
    mode: str,
    prompt: str,
    *,
    async_mode: bool = False,
    project: str | None = None,
    output_dir: str | None = None,
    provider: str | None = None,
    input_file: str | None = None,
    auto: bool = False,
    verbose: bool = False,
    cli_api_keys: dict | None = None,
    combined: bool = False,
    quiet: bool = False,
    no_metadata: bool = False,
    timeout_override: float | None = None,
    model_override: str | None = None,
    ctx_obj=None,
) -> None:
    """Execute a research run with the given mode and prompt.

    Extracted from the bare-prompt branch of the pre-refactor cli callback.
    Called by ThothGroup.invoke for both mode-positional and bare-prompt paths.
    """
    app_ctx = _build_app_context(verbose) if ctx_obj is None else ctx_obj
    _result = _thoth_run.run_research(
        mode=mode,
        prompt=prompt,
        async_mode=async_mode,
        project=project,
        output_dir=output_dir,
        provider=provider,
        input_file=input_file,
        auto=auto,
        verbose=verbose,
        cli_api_keys=cli_api_keys or {},
        combined=combined,
        quiet=quiet,
        no_metadata=no_metadata,
        timeout_override=timeout_override,
        ctx=app_ctx,
        model_override=model_override,
    )
    import inspect

    if inspect.iscoroutine(_result):
        asyncio.run(_result)
```

- [ ] **Step 3.3: Update `help.py` to import the real function**

Replace the stub in `src/thoth/help.py`:

```python
# Replace the stub _run_research_default with:
def _run_research_default(*args, **kwargs):
    # Lazy import to avoid circular import (cli.py imports from help.py)
    from thoth.cli import _run_research_default as _impl
    return _impl(*args, **kwargs)
```

- [ ] **Step 3.4: Convert top-level `@click.command` to `@click.group`**

In `src/thoth/cli.py`, replace:

```python
@click.command(
    cls=ThothCommand,
    epilog=...,
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
)
@click.pass_context
@click.argument("args", nargs=-1)
@click.option("--mode", "-m", "mode_opt", help="Research mode")
# ... rest of options
def cli(ctx, args, mode_opt, ...):
    ...
```

With:

```python
@click.group(
    cls=ThothGroup,
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.pass_context
@click.option("--mode", "-m", "mode_opt", help="Research mode")
@click.option("--prompt", "-q", "prompt_opt", help="Research prompt")
@click.option("--prompt-file", "-F", help="Read prompt from file (use - for stdin)")
@click.option("--async", "-A", "async_mode", is_flag=True, help="Submit and exit")
@click.option("--resume", "-R", "resume_id", help="Resume operation by ID")
# ... all other current global options ...
def cli(ctx, mode_opt, prompt_opt, prompt_file, async_mode, resume_id, ...):
    """thoth — research orchestration.

    Run research:    thoth ask "question" | thoth deep_research "topic" | thoth -m MODE -q PROMPT
    Manage thoth:    thoth init | thoth status OP | thoth list | thoth config ... | thoth providers ...

    For per-command help: thoth COMMAND --help
    """
    # Build shared context object that subcommands access via ctx.obj
    ctx.ensure_object(dict)
    ctx.obj["mode_opt"] = mode_opt
    ctx.obj["prompt_opt"] = prompt_opt
    # ... store all global opts on ctx.obj for subcommands to inherit
    # ... existing flag-validation logic moves into a helper called here ...
```

The `args` positional argument is **removed** (subcommands handle their own arguments). The `nargs=-1` collection no longer happens at the group level; instead `ThothGroup.invoke` reads from `ctx.protected_args + ctx.args`.

- [ ] **Step 3.5: Verify the imperative dispatch block is unreachable**

The block starting `if args and args[0] in COMMAND_NAMES:` (currently around `cli.py:292`) used `args` from the removed `@click.argument`. Confirm it now references an undefined name.

Run: `python -c "import thoth.cli"`
Expected: ImportError or NameError pointing at the dead block.

- [ ] **Step 3.6: Comment out the dead dispatch block (temporary; deleted in Task 14)**

Wrap the block in `if False:` to keep the code visible during PR review but unreachable:

```python
    if False:  # P16 PR1: imperative dispatch removed in Task 14
        if args and args[0] in COMMAND_NAMES:
            ...
```

- [ ] **Step 3.7: Verify the module imports cleanly**

Run: `python -c "from thoth.cli import cli; print(cli)"`
Expected: prints `<Group cli>`.

- [ ] **Step 3.8: Verify no subcommands are registered yet (the group is bare)**

Run: `python -c "from thoth.cli import cli; print(list(cli.commands.keys()))"`
Expected: `[]`.

- [ ] **Step 3.9: Run ThothGroup unit tests**

Run: `pytest tests/test_p16_thothgroup.py -v`
Expected: All 4 tests PASS (the real `_run_research_default` is now wired but tests still monkeypatch it).

- [ ] **Step 3.10: Commit**

```bash
git add src/thoth/cli.py src/thoth/help.py
git commit -m "feat(cli): convert top-level cli to @click.group(cls=ThothGroup) (P16 PR1)"
```

---

## Task 4: Migrate `init` to `cli_subcommands/init.py`

**Files:**
- Create: `src/thoth/cli_subcommands/__init__.py` (empty)
- Create: `src/thoth/cli_subcommands/init.py`
- Modify: `src/thoth/cli.py` (add `cli.add_command(...)` registration)

**Note:** This is the first subcommand migration. Tasks 5-10 follow this exact pattern. Each subcommand: create the module, define a thin `@click.command` wrapper that delegates to the existing handler, register on the group.

- [ ] **Step 4.1: Create empty package marker**

Create `src/thoth/cli_subcommands/__init__.py`:

```python
"""Click subcommand modules. Each file defines one subcommand or subgroup
and is registered explicitly in cli.py."""
```

- [ ] **Step 4.2: Write failing test for `thoth init` invocation**

Append to `tests/test_p16_thothgroup.py` (or create `tests/test_p16_subcommands.py` if growing large):

```python
def test_init_subcommand_registered():
    """P16-TS06: init is registered as a Click subcommand on the cli group."""
    from thoth.cli import cli

    assert "init" in cli.commands


def test_init_subcommand_invokes_handler(monkeypatch):
    """P16-TS07: thoth init dispatches through Click to CommandHandler.init_command."""
    from thoth.cli import cli

    called = {}

    def fake_init(self, config_path=None):
        called["config_path"] = config_path

    monkeypatch.setattr(
        "thoth.commands.CommandHandler.init_command", fake_init
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["init"])
    assert result.exit_code == 0
    assert "config_path" in called
```

- [ ] **Step 4.3: Run tests to verify failure**

Run: `pytest tests/test_p16_thothgroup.py::test_init_subcommand_registered -v`
Expected: FAIL — `assert "init" in cli.commands` fails (no subcommand registered yet).

- [ ] **Step 4.4: Create `cli_subcommands/init.py`**

```python
"""`thoth init` Click subcommand.

Thin wrapper around CommandHandler.init_command(). Behavior is unchanged
from the pre-P16 imperative dispatch (cli.py:298-300).
"""

from __future__ import annotations

import click

from thoth.commands import CommandHandler
from thoth.config import ConfigManager


@click.command(name="init")
@click.pass_context
def init(ctx: click.Context) -> None:
    """Initialize thoth configuration."""
    config_path = ctx.obj.get("config_path") if ctx.obj else None

    config_manager = ConfigManager()
    config_manager.load_all_layers({"config_path": config_path})
    handler = CommandHandler(config_manager)
    handler.init_command(config_path=config_path)
```

- [ ] **Step 4.5: Register the subcommand on the cli group**

In `src/thoth/cli.py`, after the `@click.group` definition and before the `def main()` function, add:

```python
# === Subcommand registrations ===
from thoth.cli_subcommands import init as _init_mod
cli.add_command(_init_mod.init)
```

- [ ] **Step 4.6: Run tests to verify passage**

Run: `pytest tests/test_p16_thothgroup.py::test_init_subcommand_registered tests/test_p16_thothgroup.py::test_init_subcommand_invokes_handler -v`
Expected: Both PASS.

- [ ] **Step 4.7: Verify the subcommand shows in `thoth --help`**

Run: `thoth --help | grep -A1 "Commands"`
Expected: output contains `init` as a listed command.

- [ ] **Step 4.8: Commit**

```bash
git add src/thoth/cli_subcommands/__init__.py src/thoth/cli_subcommands/init.py src/thoth/cli.py tests/test_p16_thothgroup.py
git commit -m "feat(cli): migrate init to cli_subcommands/init.py (P16 PR1)"
```

---

## Task 5: Migrate `status` to `cli_subcommands/status.py`

Apply the Task 4 pattern. Differences: `status` takes a required `OP_ID` argument.

**Files:**
- Create: `src/thoth/cli_subcommands/status.py`
- Modify: `src/thoth/cli.py` (add registration)
- Modify: `tests/test_p16_thothgroup.py` (add tests)

- [ ] **Step 5.1: Write failing tests**

Append to test file:

```python
def test_status_subcommand_registered():
    from thoth.cli import cli
    assert "status" in cli.commands


def test_status_requires_op_id():
    """P16-TS08: thoth status (no OP_ID) → Click missing-arg error, exit 2."""
    from thoth.cli import cli
    runner = CliRunner()
    result = runner.invoke(cli, ["status"])
    assert result.exit_code == 2
    assert "Missing argument" in result.output or "OP_ID" in result.output


def test_status_invokes_handler(monkeypatch):
    from thoth.cli import cli
    called = {}

    def fake_status(self, operation_id):
        called["op_id"] = operation_id

    monkeypatch.setattr(
        "thoth.commands.CommandHandler.status_command", fake_status
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["status", "abc123"])
    assert result.exit_code == 0
    assert called["op_id"] == "abc123"
```

- [ ] **Step 5.2: Run failing tests**

Run: `pytest tests/test_p16_thothgroup.py -k status -v`
Expected: 3 FAIL.

- [ ] **Step 5.3: Create `cli_subcommands/status.py`**

```python
"""`thoth status OP_ID` Click subcommand."""

from __future__ import annotations

import click

from thoth.commands import CommandHandler
from thoth.config import ConfigManager


@click.command(name="status")
@click.argument("operation_id", metavar="OP_ID")
@click.pass_context
def status(ctx: click.Context, operation_id: str) -> None:
    """Check status of a research operation by ID."""
    config_path = ctx.obj.get("config_path") if ctx.obj else None
    config_manager = ConfigManager()
    config_manager.load_all_layers({"config_path": config_path})
    handler = CommandHandler(config_manager)
    handler.status_command(operation_id=operation_id)
```

- [ ] **Step 5.4: Register on cli group**

In `src/thoth/cli.py`, append to the registrations block:

```python
from thoth.cli_subcommands import status as _status_mod
cli.add_command(_status_mod.status)
```

- [ ] **Step 5.5: Run tests**

Run: `pytest tests/test_p16_thothgroup.py -k status -v`
Expected: All 3 PASS.

- [ ] **Step 5.6: Commit**

```bash
git add src/thoth/cli_subcommands/status.py src/thoth/cli.py tests/test_p16_thothgroup.py
git commit -m "feat(cli): migrate status to cli_subcommands/status.py (P16 PR1)"
```

---

## Task 6: Migrate `list` to `cli_subcommands/list_cmd.py`

Apply the Task 4 pattern. Differences: file named `list_cmd.py` (avoid Python keyword); `--all` flag.

- [ ] **Step 6.1: Write failing tests**

```python
def test_list_subcommand_registered():
    from thoth.cli import cli
    assert "list" in cli.commands


def test_list_all_flag(monkeypatch):
    from thoth.cli import cli
    called = {}

    def fake_list(self, show_all=False):
        called["show_all"] = show_all

    monkeypatch.setattr("thoth.commands.CommandHandler.list_command", fake_list)
    runner = CliRunner()
    result = runner.invoke(cli, ["list", "--all"])
    assert result.exit_code == 0
    assert called["show_all"] is True
```

- [ ] **Step 6.2: Create `cli_subcommands/list_cmd.py`**

```python
"""`thoth list` Click subcommand. File named list_cmd.py to avoid Python
keyword shadow; the registered command name is "list"."""

from __future__ import annotations

import click

from thoth.commands import CommandHandler
from thoth.config import ConfigManager


@click.command(name="list")
@click.option("--all", "show_all", is_flag=True, help="Include completed operations")
@click.pass_context
def list_cmd(ctx: click.Context, show_all: bool) -> None:
    """List research operations."""
    config_path = ctx.obj.get("config_path") if ctx.obj else None
    config_manager = ConfigManager()
    config_manager.load_all_layers({"config_path": config_path})
    handler = CommandHandler(config_manager)
    handler.list_command(show_all=show_all)
```

- [ ] **Step 6.3: Register**

In `cli.py`:

```python
from thoth.cli_subcommands import list_cmd as _list_mod
cli.add_command(_list_mod.list_cmd)
```

- [ ] **Step 6.4: Run tests**

Run: `pytest tests/test_p16_thothgroup.py -k list -v`
Expected: PASS.

- [ ] **Step 6.5: Commit**

```bash
git add src/thoth/cli_subcommands/list_cmd.py src/thoth/cli.py tests/test_p16_thothgroup.py
git commit -m "feat(cli): migrate list to cli_subcommands/list_cmd.py (P16 PR1)"
```

---

## Task 7: Migrate `providers` (subgroup with leaves `list`, `models`, `check`)

Apply the Task 4 pattern, but the subcommand is itself a group. The legacy `providers -- --list` shim is **NOT removed in PR1** (PR2 handles that breakage). PR1 preserves the existing `providers` callable shape and the shim continues to work.

- [ ] **Step 7.1: Write failing tests**

```python
def test_providers_subgroup_registered():
    from thoth.cli import cli
    assert "providers" in cli.commands
    assert isinstance(cli.commands["providers"], click.Group)


def test_providers_list_invokes_correct_function(monkeypatch):
    from thoth.cli import cli
    called = {}

    def fake_list(cfg):
        called["invoked"] = True
        return 0

    monkeypatch.setattr("thoth.commands.providers_list", fake_list)
    runner = CliRunner()
    result = runner.invoke(cli, ["providers", "list"])
    assert result.exit_code == 0
    assert called["invoked"] is True
```

- [ ] **Step 7.2: Create `cli_subcommands/providers.py`**

```python
"""`thoth providers` Click subgroup with leaves: list, models, check.

PR1 preserves the existing `providers -- --list` legacy shim path by
NOT routing the bare `thoth providers` invocation through this subgroup —
that bare-no-leaf path falls through to the imperative dispatch in cli.py
which still handles the legacy form. PR2 removes that shim entirely.
"""

from __future__ import annotations

import sys

import click

from thoth.commands import providers_check, providers_list, providers_models
from thoth.config import ConfigManager


@click.group(name="providers")
def providers() -> None:
    """Manage provider models and API keys."""


@providers.command(name="list")
@click.pass_context
def providers_list_cmd(ctx: click.Context) -> None:
    """List available providers."""
    cfg = ConfigManager()
    cfg.load_all_layers({})
    sys.exit(providers_list(cfg))


@providers.command(name="models")
@click.pass_context
def providers_models_cmd(ctx: click.Context) -> None:
    """List provider models."""
    cfg = ConfigManager()
    cfg.load_all_layers({})
    sys.exit(providers_models(cfg))


@providers.command(name="check")
@click.pass_context
def providers_check_cmd(ctx: click.Context) -> None:
    """Check provider API key configuration."""
    cfg = ConfigManager()
    cfg.load_all_layers({})
    sys.exit(providers_check(cfg))
```

- [ ] **Step 7.3: Register**

In `cli.py`:

```python
from thoth.cli_subcommands import providers as _providers_mod
cli.add_command(_providers_mod.providers)
```

- [ ] **Step 7.4: Run tests**

Run: `pytest tests/test_p16_thothgroup.py -k providers -v`
Expected: PASS.

- [ ] **Step 7.5: Verify the legacy shim still works**

Run: `THOTH_TEST_MODE=1 thoth providers -- --list`
Expected: Still emits the deprecation warning and works (the imperative dispatch handles this until PR2 removes it).

- [ ] **Step 7.6: Commit**

```bash
git add src/thoth/cli_subcommands/providers.py src/thoth/cli.py tests/test_p16_thothgroup.py
git commit -m "feat(cli): migrate providers to cli_subcommands/providers.py (P16 PR1)"
```

---

## Task 8: Migrate `config` (subgroup with leaves `get`, `set`, `unset`, `list`, `path`, `edit`)

Apply the Task 7 pattern. The existing `config_command(op, rest)` function in `config_cmd.py` handles dispatch — each leaf passes through to it.

- [ ] **Step 8.1: Write failing tests**

```python
def test_config_subgroup_registered():
    from thoth.cli import cli
    assert "config" in cli.commands
    assert isinstance(cli.commands["config"], click.Group)


def test_config_list_invokes_handler(monkeypatch):
    from thoth.cli import cli
    called = {}

    def fake_config_command(op, rest):
        called["op"] = op
        called["rest"] = rest
        return 0

    monkeypatch.setattr("thoth.config_cmd.config_command", fake_config_command)
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "list"])
    assert result.exit_code == 0
    assert called["op"] == "list"
```

- [ ] **Step 8.2: Create `cli_subcommands/config.py`**

```python
"""`thoth config` Click subgroup with leaves: get, set, unset, list, path, edit."""

from __future__ import annotations

import sys

import click


@click.group(name="config")
def config() -> None:
    """Inspect and edit configuration."""


def _dispatch(op: str, args: tuple[str, ...]) -> None:
    from thoth.config_cmd import config_command
    rc = config_command(op, list(args))
    sys.exit(rc)


@config.command(name="get")
@click.argument("args", nargs=-1)
def config_get(args: tuple[str, ...]) -> None:
    """Get a configuration value."""
    _dispatch("get", args)


@config.command(name="set")
@click.argument("args", nargs=-1)
def config_set(args: tuple[str, ...]) -> None:
    """Set a configuration value."""
    _dispatch("set", args)


@config.command(name="unset")
@click.argument("args", nargs=-1)
def config_unset(args: tuple[str, ...]) -> None:
    """Unset a configuration value."""
    _dispatch("unset", args)


@config.command(
    name="list",
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
)
@click.argument("args", nargs=-1)
def config_list(args: tuple[str, ...]) -> None:
    """List all configuration values. Supports --json."""
    _dispatch("list", args)


@config.command(name="path")
@click.argument("args", nargs=-1)
def config_path(args: tuple[str, ...]) -> None:
    """Show config file path."""
    _dispatch("path", args)


@config.command(name="edit")
@click.argument("args", nargs=-1)
def config_edit(args: tuple[str, ...]) -> None:
    """Open config file in $EDITOR."""
    _dispatch("edit", args)
```

> The `--json` flag on `config list` continues to be parsed inside `config_command` (which already supports it), via `ignore_unknown_options=True`. PR3 will replace this with native Click `@click.option("--json")` declarations.

- [ ] **Step 8.3: Register**

In `cli.py`:

```python
from thoth.cli_subcommands import config as _config_mod
cli.add_command(_config_mod.config)
```

- [ ] **Step 8.4: Run tests**

Run: `pytest tests/test_p16_thothgroup.py -k config -v`
Expected: PASS.

- [ ] **Step 8.5: Verify `thoth config list --json` still works**

Run: `THOTH_TEST_MODE=1 thoth config list --json | head -3`
Expected: Valid JSON output (existing behavior preserved).

- [ ] **Step 8.6: Commit**

```bash
git add src/thoth/cli_subcommands/config.py src/thoth/cli.py tests/test_p16_thothgroup.py
git commit -m "feat(cli): migrate config to cli_subcommands/config.py (P16 PR1)"
```

---

## Task 9: Migrate `modes` to `cli_subcommands/modes.py`

The existing `modes_command(op, rest)` is the dispatcher. PR1 ships only the `list` leaf (which is the current default behavior); P12 adds `add`/`set`/`unset` later.

- [ ] **Step 9.1: Write failing tests**

```python
def test_modes_registered():
    from thoth.cli import cli
    assert "modes" in cli.commands


def test_modes_list_invokes_handler(monkeypatch):
    from thoth.cli import cli
    called = {}

    def fake_modes_command(op, rest):
        called["op"] = op
        return 0

    monkeypatch.setattr("thoth.modes_cmd.modes_command", fake_modes_command)
    runner = CliRunner()
    result = runner.invoke(cli, ["modes"])
    assert result.exit_code == 0
    # When no op is given, modes shows the list (current behavior)
    assert called["op"] is None or called["op"] == "list"
```

- [ ] **Step 9.2: Create `cli_subcommands/modes.py`**

```python
"""`thoth modes` Click subgroup. PR1 ships `list` only (= current default
behavior); P12 will add `add`, `set`, `unset`."""

from __future__ import annotations

import sys

import click


@click.group(
    name="modes",
    invoke_without_command=True,
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
)
@click.argument("args", nargs=-1)
@click.pass_context
def modes(ctx: click.Context, args: tuple[str, ...]) -> None:
    """List research modes with provider/model/kind."""
    if ctx.invoked_subcommand is None:
        # No leaf: behave as `modes list` (current default)
        from thoth.modes_cmd import modes_command
        rc = modes_command(None, list(args))
        sys.exit(rc)


# Future: P12 adds `add`, `set`, `unset` leaves here.
```

- [ ] **Step 9.3: Register and test**

In `cli.py`:

```python
from thoth.cli_subcommands import modes as _modes_mod
cli.add_command(_modes_mod.modes)
```

Run: `pytest tests/test_p16_thothgroup.py -k modes -v`
Expected: PASS.

- [ ] **Step 9.4: Verify `thoth modes --json` still works**

Run: `THOTH_TEST_MODE=1 thoth modes --json | python -m json.tool >/dev/null && echo VALID`
Expected: prints `VALID`.

- [ ] **Step 9.5: Commit**

```bash
git add src/thoth/cli_subcommands/modes.py src/thoth/cli.py tests/test_p16_thothgroup.py
git commit -m "feat(cli): migrate modes to cli_subcommands/modes.py (P16 PR1)"
```

---

## Task 10: Migrate `help` as thin alias to `cli_subcommands/help_cmd.py`

`thoth help [TOPIC]` forwards to `thoth [TOPIC] --help`. The `auth` topic is special — there is no `auth` subcommand to forward to, so it calls `show_auth_help()` directly.

- [ ] **Step 10.1: Write failing tests**

```python
def test_help_subcommand_registered():
    from thoth.cli import cli
    assert "help" in cli.commands


def test_help_no_topic_shows_group_help():
    from thoth.cli import cli
    runner = CliRunner()
    result = runner.invoke(cli, ["help"])
    assert result.exit_code == 0
    # Group help contains "Commands:" or similar
    assert "Commands" in result.output or "Usage" in result.output


def test_help_with_topic_forwards_to_subcommand_help():
    from thoth.cli import cli
    runner = CliRunner()
    result = runner.invoke(cli, ["help", "init"])
    assert result.exit_code == 0
    # `thoth init --help` output should be included
    assert "init" in result.output.lower()


def test_help_auth_calls_show_auth_help(monkeypatch):
    from thoth.cli import cli
    called = {}

    def fake_show_auth():
        called["invoked"] = True

    monkeypatch.setattr("thoth.help.show_auth_help", fake_show_auth)
    runner = CliRunner()
    result = runner.invoke(cli, ["help", "auth"])
    assert result.exit_code == 0
    assert called["invoked"] is True


def test_help_unknown_topic_errors():
    from thoth.cli import cli
    runner = CliRunner()
    result = runner.invoke(cli, ["help", "nosuchtopic"])
    assert result.exit_code == 2
    assert "nosuchtopic" in result.output.lower() or "unknown" in result.output.lower()
```

- [ ] **Step 10.2: Create `cli_subcommands/help_cmd.py`**

```python
"""`thoth help [TOPIC]` thin alias. Forwards to `thoth [TOPIC] --help`
except for the `auth` topic, which has no corresponding subcommand and
maps to show_auth_help() directly."""

from __future__ import annotations

import click


@click.command(name="help")
@click.argument("topic", required=False)
@click.pass_context
def help_cmd(ctx: click.Context, topic: str | None) -> None:
    """Show help (general or for a specific topic)."""
    if topic is None:
        # Show top-level group help
        click.echo(ctx.parent.get_help())
        return

    if topic == "auth":
        from thoth.help import show_auth_help
        show_auth_help()
        return

    # Forward to the subcommand's --help
    parent = ctx.parent
    target_cmd = parent.command.get_command(parent, topic)
    if target_cmd is None:
        click.echo(f"Unknown help topic: {topic}", err=True)
        click.echo(f"Available topics: {', '.join(sorted(parent.command.commands.keys()))}, auth", err=True)
        ctx.exit(2)

    sub_ctx = click.Context(target_cmd, info_name=topic, parent=parent)
    click.echo(sub_ctx.get_help())
```

- [ ] **Step 10.3: Register**

In `cli.py`:

```python
from thoth.cli_subcommands import help_cmd as _help_mod
cli.add_command(_help_mod.help_cmd)
```

- [ ] **Step 10.4: Run tests**

Run: `pytest tests/test_p16_thothgroup.py -k help_ -v`
Expected: 5 PASS.

- [ ] **Step 10.5: Commit**

```bash
git add src/thoth/cli_subcommands/help_cmd.py src/thoth/cli.py tests/test_p16_thothgroup.py
git commit -m "feat(cli): migrate help to thin alias (P16 PR1)"
```

---

## Task 11: Implement two-section help renderer

Replace the alphabetical Click default with the "Run research" / "Manage thoth" two-section split + modes epilog. Per spec §6.1 and Q6-D.

**Files:**
- Modify: `src/thoth/help.py` (extend `ThothGroup` with `format_commands` override)

- [ ] **Step 11.1: Write failing structural test**

Append to `tests/test_p16_thothgroup.py`:

```python
def test_help_has_two_sections():
    """P16-TS09: thoth --help has 'Run research' and 'Manage thoth' sections."""
    from thoth.cli import cli
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Run research" in result.output
    assert "Manage thoth" in result.output


def test_help_run_section_contains_research_verbs():
    from thoth.cli import cli
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    # ask and resume don't exist until PR2, but status and list do in PR1
    out = result.output
    run_idx = out.find("Run research")
    manage_idx = out.find("Manage thoth")
    run_section = out[run_idx:manage_idx]
    assert "status" in run_section
    assert "list" in run_section


def test_help_manage_section_contains_admin_verbs():
    from thoth.cli import cli
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    out = result.output
    manage_idx = out.find("Manage thoth")
    manage_section = out[manage_idx:]
    assert "init" in manage_section
    assert "config" in manage_section
    assert "providers" in manage_section
    assert "modes" in manage_section
    assert "help" in manage_section


def test_help_has_modes_epilog():
    """P16-TS10: --help mentions the positional modes."""
    from thoth.cli import cli
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    out = result.output
    assert "Modes" in out  # epilog header
    # At least one builtin mode listed
    assert "deep_research" in out or "default" in out
```

- [ ] **Step 11.2: Run tests to verify failure**

Run: `pytest tests/test_p16_thothgroup.py -k help -v`
Expected: 4 FAIL (the new structural tests).

- [ ] **Step 11.3: Add command-classification constants in `help.py`**

In `src/thoth/help.py`, replace the current `COMMANDS` tuple with:

```python
# Two-section split for the Click group help renderer.
RUN_COMMANDS: tuple[str, ...] = ("ask", "resume", "status", "list")
ADMIN_COMMANDS: tuple[str, ...] = (
    "init",
    "config",
    "modes",
    "providers",
    "completion",
    "help",
)
# COMMAND_NAMES is removed in Task 13 once the imperative dispatch is gone.
```

> `ask`, `resume`, `completion` aren't registered until PR2/PR3 — that's fine. The renderer iterates over what's actually registered AND in the classification list.

- [ ] **Step 11.4: Implement `format_commands` on `ThothGroup`**

Append to the `ThothGroup` class:

```python
    def format_commands(self, ctx: click.Context, formatter):
        """Render commands in two sections: Run research / Manage thoth."""
        registered = set(self.commands.keys())

        run_rows = [
            (name, self.commands[name].get_short_help_str(limit=60))
            for name in RUN_COMMANDS
            if name in registered
        ]
        admin_rows = [
            (name, self.commands[name].get_short_help_str(limit=60))
            for name in ADMIN_COMMANDS
            if name in registered
        ]

        if run_rows:
            with formatter.section("Run research"):
                formatter.write_dl(run_rows)
        if admin_rows:
            with formatter.section("Manage thoth"):
                formatter.write_dl(admin_rows)

    def format_epilog(self, ctx: click.Context, formatter):
        """Render the modes-positional epilog block + worked examples."""
        from thoth.config import BUILTIN_MODES

        with formatter.section("Modes (positional)"):
            modes_str = ", ".join(sorted(BUILTIN_MODES))
            formatter.write_text(
                f"Pass as the first positional argument: {modes_str}"
            )
            formatter.write_paragraph()
            formatter.write_text(
                'Example: thoth deep_research "explain transformers"'
            )

        super().format_epilog(ctx, formatter)
```

- [ ] **Step 11.5: Run tests to verify they pass**

Run: `pytest tests/test_p16_thothgroup.py -k help -v`
Expected: 4 PASS.

- [ ] **Step 11.6: Commit**

```bash
git add src/thoth/help.py tests/test_p16_thothgroup.py
git commit -m "feat(cli): two-section help layout (Run research / Manage thoth) (P16 PR1)"
```

---

## Task 12: Update `cli.py` help-string examples

The current docstring at `cli.py:184-188` references the deprecated `thoth help X` form. Update to `thoth X --help` (canonical Click form).

**Files:**
- Modify: `src/thoth/cli.py`

- [ ] **Step 12.1: Find current docstring lines**

Run: `sed -n '180,200p' src/thoth/cli.py`
Note the lines mentioning `thoth help init` / `thoth help status`.

- [ ] **Step 12.2: Replace help references in the cli docstring**

In `src/thoth/cli.py`, in the `def cli(ctx, ...)` docstring (the function-level docstring), replace any line like:

```
      thoth help init
      thoth help status
```

with:

```
      thoth init --help
      thoth status --help
```

> The `thoth help [TOPIC]` form continues to work (Task 10), but the canonical Click form is recommended for discoverability.

- [ ] **Step 12.3: Verify docstring rendering**

Run: `THOTH_TEST_MODE=1 thoth --help | grep -A2 "thoth.*--help"`
Expected: shows the updated examples.

- [ ] **Step 12.4: Commit**

```bash
git add src/thoth/cli.py
git commit -m "docs(cli): canonical 'thoth X --help' in docstring examples (P16 PR1)"
```

---

## Task 13: Remove `ThothCommand`, `COMMAND_NAMES`, `show_*_help` functions

The custom `parse_args` interceptor and the `show_*_help` family are obsolete — Click handles `thoth SUBCOMMAND --help` natively, and each subcommand's help lives on its own decorator.

**Files:**
- Modify: `src/thoth/help.py` (delete `ThothCommand` class, delete five `show_*_help` functions, delete `COMMAND_NAMES` and `HELP_TOPICS`)

- [ ] **Step 13.1: Verify nothing else references these names**

Run: `grep -rn "ThothCommand\|COMMAND_NAMES\|HELP_TOPICS\|show_init_help\|show_status_help\|show_list_help\|show_providers_help\|show_config_help\|show_modes_help" src/ tests/`
Expected: only references in `help.py` itself (we'll delete those) and possibly the imperative dispatch block in `cli.py` (which is still wrapped in `if False:` from Task 3 — those references will go in Task 14).

If anything else references them, add a fix step here for that file.

- [ ] **Step 13.2: Delete `ThothCommand` class from `help.py`**

Remove the entire class definition (currently `help.py:31` through approximately line 100).

- [ ] **Step 13.3: Delete `show_init_help`, `show_status_help`, `show_list_help`, `show_providers_help`, `show_config_help`, `show_modes_help`**

Find and remove these six functions from `help.py`. Keep `show_auth_help`.

- [ ] **Step 13.4: Delete `COMMAND_NAMES` and `HELP_TOPICS` constants**

Remove these two constants from `help.py`.

- [ ] **Step 13.5: Verify the module still imports**

Run: `python -c "from thoth.help import ThothGroup, show_auth_help; print('ok')"`
Expected: prints `ok`.

- [ ] **Step 13.6: Run all tests**

Run: `pytest tests/ -x -q`
Expected: all PASS (we deleted only unused code).

- [ ] **Step 13.7: Commit**

```bash
git add src/thoth/help.py
git commit -m "refactor(help): remove ThothCommand, show_*_help, COMMAND_NAMES (P16 PR1)"
```

---

## Task 14: Remove dead imperative dispatch from `cli.py`

The `if False:` block from Task 3 wrapping the old `if args[0] in COMMAND_NAMES:` dispatch is now safe to delete — every subcommand it handled is registered via Click.

**Files:**
- Modify: `src/thoth/cli.py`

- [ ] **Step 14.1: Locate the dead block**

Run: `grep -n "if False:.*P16 PR1.*Task 14" src/thoth/cli.py`
Expected: matches the line wrapping the dead dispatch block (around the original `cli.py:292`).

- [ ] **Step 14.2: Delete the entire `if False:` block and its body**

Remove the conditional and all lines until the next sibling code (the `if async_mode and resume_id:` validation block).

- [ ] **Step 14.3: Verify no imports become unused**

Check `cli.py`'s imports for: `providers_check`, `providers_command`, `providers_list`, `providers_models` from `commands.py` — these were imported for the dead dispatch. They're no longer needed at the cli.py top level (subcommand modules import them directly).

```python
# Remove (or trim):
from thoth.commands import (
    providers_check,
    providers_command,
    providers_list,
    providers_models,
)
```

Also remove imports of: `show_config_help`, `show_init_help`, `show_list_help`, `show_modes_help`, `show_providers_help`, `show_status_help` from `thoth.help` (deleted in Task 13).

Keep: `show_auth_help` (still used? verify), `THOTH_VERSION`, `BUILTIN_MODES`, `ConfigManager`.

- [ ] **Step 14.4: Run linter to catch unused imports**

Run: `just check`
Expected: PASS (or unused-import warning that you immediately address).

- [ ] **Step 14.5: Run all tests**

Run: `pytest tests/ -x -q`
Expected: all PASS.

- [ ] **Step 14.6: Commit**

```bash
git add src/thoth/cli.py
git commit -m "refactor(cli): remove dead imperative dispatch block (P16 PR1)"
```

---

## Task 15: Re-enable parity tests, run full regression, capture new help baseline

Now that the refactor is complete, the parity gate from Task 1 must turn green for all tests *except* `help` (which is intentionally different — two-section layout). Update the `help` parity test to assert structural properties; capture an updated `help.json` baseline for future drift detection.

**Files:**
- Modify: `tests/test_p16_dispatch_parity.py` (update `help` test to use structural assertions)
- Re-capture: `tests/baselines/help.json`
- Delete: `tests/baselines/capture_baselines.py` (one-shot script no longer needed)

- [ ] **Step 15.1: Re-enable parity tests**

Run: `pytest tests/test_p16_dispatch_parity.py -v`
Expected: 14 PASS, 1 FAIL on `help` (intentional — Task 11 changed the help layout).

- [ ] **Step 15.2: Replace `help` parity assertion with structural test**

In `tests/test_p16_dispatch_parity.py`, modify `PARITY_LABELS` to remove `"help"` from the list, then add a dedicated structural test:

```python
def test_help_layout_structural(run_thoth):
    """P16-TS11: thoth --help has the two-section layout post-refactor."""
    exit_code, stdout, stderr = run_thoth(["--help"])
    assert exit_code == 0
    assert "Run research" in stdout
    assert "Manage thoth" in stdout
    assert "Modes" in stdout  # epilog
    assert "Usage:" in stdout
```

- [ ] **Step 15.3: Re-run all parity + structural tests**

Run: `pytest tests/test_p16_dispatch_parity.py tests/test_p16_thothgroup.py -v`
Expected: all PASS.

- [ ] **Step 15.4: Update the help baseline for drift detection (post-PR1 reference)**

Run: `THOTH_TEST_MODE=1 thoth --help > /tmp/new_help.txt`
Manually inspect `/tmp/new_help.txt` to confirm two-section layout looks correct.

If correct, capture as new baseline (will be referenced by future PRs):

```bash
mkdir -p tests/baselines
python -c "
import json
from pathlib import Path
text = Path('/tmp/new_help.txt').read_text()
out = {'label': 'help_post_pr1', 'argv': ['--help'], 'exit_code': 0, 'stdout': text, 'stderr': ''}
Path('tests/baselines/help_post_pr1.json').write_text(json.dumps(out, indent=2))
"
```

- [ ] **Step 15.5: Delete the one-shot capture script**

```bash
rm tests/baselines/capture_baselines.py
```

- [ ] **Step 15.6: Run the full local test gate per CLAUDE.md**

Run:

```bash
just check
```

Expected: PASS (ruff + ty clean).

Run:

```bash
./thoth_test -r --skip-interactive -q
```

Expected: All previously-passing thoth_test cases continue to pass. No new test failures.

- [ ] **Step 15.7: Run the full pytest suite**

Run: `uv run pytest tests/ -v`
Expected: All PASS (or expected-skip count unchanged from pre-refactor).

- [ ] **Step 15.8: Final commit**

```bash
git add tests/test_p16_dispatch_parity.py tests/baselines/
git rm tests/baselines/capture_baselines.py
git commit -m "test(p16): finalize PR1 parity gate (14 invocations + structural help test)"
```

- [ ] **Step 15.9: Update PROJECTS.md with PR1 progress**

In `PROJECTS.md`, add a new project entry:

```markdown
## [-] Project P16: CLI Click Group Refactor (v3.0.0 — PR1 of 3)
**Goal**: Refactor thoth's CLI from a single @click.command() with positional pseudo-dispatch to @click.group() with first-class subcommands.

**Status**: PR1 (refactor only, no behavior change) — IN PROGRESS / DONE
PR2 (breakage + new verbs) — DEFERRED
PR3 (automation polish) — DEFERRED

**Out of Scope (PR1)**
- Adding `ask` subcommand (PR2)
- Removing `--resume` flag (PR2)
- Adding `completion` subcommand (PR3)
- Adding `--json` to commands without it (PR3)

### Tests & Tasks
- [x] [P16-T01] Capture pre-refactor parity baselines
- [x] [P16-T02] ThothGroup skeleton with three dispatch paths
- [x] [P16-T03] Convert top-level cli to @click.group(cls=ThothGroup)
- [x] [P16-T04] Migrate init to cli_subcommands/init.py
- [x] [P16-T05] Migrate status
- [x] [P16-T06] Migrate list
- [x] [P16-T07] Migrate providers (subgroup)
- [x] [P16-T08] Migrate config (subgroup)
- [x] [P16-T09] Migrate modes
- [x] [P16-T10] Migrate help as thin alias
- [x] [P16-T11] Two-section help renderer
- [x] [P16-T12] Update cli.py help-string examples
- [x] [P16-T13] Remove ThothCommand, COMMAND_NAMES, show_*_help
- [x] [P16-T14] Remove dead imperative dispatch
- [x] [P16-T15] Final parity test sweep + regression
- [x] [P16-TS01..TS11] All PR1 tests passing
```

Commit:

```bash
git add PROJECTS.md
git commit -m "docs(projects): record P16 PR1 completion"
```

---

## Self-Review

After completing all 15 tasks:

**1. Spec coverage** — every PR1 deliverable in `docs/superpowers/specs/2026-04-25-promote-admin-commands-design.md` §10 PR1 row is covered:
- Click group ✓ (T3)
- ThothGroup ✓ (T2)
- cli_subcommands/* ✓ (T4-T10)
- two-section help renderer ✓ (T11)
- help.py shrink ✓ (T13)
- removal of COMMAND_NAMES/ThothCommand/imperative dispatch ✓ (T13, T14)
- thoth help [TOPIC] thin alias ✓ (T10)

**2. Test categories** (from spec §9.2 PR1 gate):
- C (dispatch parity) ✓ (T1, T15)
- D (ThothGroup unit) ✓ (T2)
- E (surprising parses) — **gap**: explicit `thoth "init the database"` vs `thoth init` test missing. Consider adding to T15 or a new T16.
- J (full regression) ✓ (T15.6, T15.7)

**3. Open items for the executing agent:**
- The `cli.py` global-options surface (currently ~30 options on the `@click.group` decorator) needs each option deliberately preserved during T3.4. Run `grep -n "@click.option" src/thoth/cli.py` *before* converting to capture the full list, and ensure every option appears on the new `@click.group` decoration.
- The `ctx.obj` dict pattern is introduced in T3.4 for inheriting global opts to subcommands. Each subcommand wrapper in T4-T10 needs to read from `ctx.obj` for any global state it needs (e.g., `config_path`). Verify each subcommand correctly inherits.
- Pre-commit hook will run the full `./thoth_test` suite on every commit. Some intermediate commits (e.g., T3 with the dead `if False:` block) may temporarily break thoth_test cases that exercise the imperative dispatch. If pre-commit fails on those intermediate commits, use `LEFTHOOK=0` per CLAUDE.md exception ONLY for those intermediate WIP commits — and run `./thoth_test -r --skip-interactive -q` manually first to verify the failure is the expected transitional one. The **final commit** (T15.8) MUST pass the full hook set.

**4. Spec gaps surfaced during planning:**
- The spec §11 acceptance criteria mentions "every existing invocation form continues to work bit-identically" but doesn't enumerate them. T1 enumerates 15 invocation patterns into the parity baseline; if the spec ever needs to be updated, that's the canonical list.
- The spec §6.2 mentions `interactive.py` is "untouched"; PR1 doesn't touch it, but the optional polish (importing from `completion/sources.py`) is a PR3 concern. Worth a sentence in PR3's plan when it's drafted.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-04-25-p16-pr1-cli-refactor.md`.**

Two execution options per writing-plans skill:

1. **Subagent-Driven (recommended)** — Dispatch a fresh subagent per task, review between tasks, fast iteration. Each task is self-contained with TDD steps and explicit commit boundaries.

2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints for review.

After PR1 lands, draft the next plan: `docs/superpowers/plans/2026-04-25-p16-pr2-breakage-and-verbs.md` (covering `ask` + `resume` + `--resume` removal + providers shim removal). PR3's plan follows after PR2.
