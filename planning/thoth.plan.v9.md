# Thoth Ergonomics v1 — Implementation Plan (v9, supersedes v8)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Related:**
- Spec: `docs/superpowers/specs/2026-04-24-thoth-ergonomics-design.md`
- Already-landed dependency: P11 (`thoth modes` + `is_background_mode`) → commit `4cbc5ec`
- Already-landed dependency: P13 (`is_background_model(str)` primitive) → commit `89498ef`

**Goal:** Land the ergonomic improvements from the approved spec on top of the P11/P13 foundation. Net surface change: `providers list/models/check` subcommands + deprecation shim, sync-deep-research progress spinner, restructured help with workflow ladder + worked examples + `-v` example, API-key documentation pass with `thoth help auth`, `--input-file`/`--auto` clearer help, `--pick-model` flag (immediate-modes only), and config-path-on-errors.

**Architecture:** Reuse the P11/P13 helper `is_background_model(model: str | None) -> bool` from `thoth.config` everywhere we need a quick/deep classification. Two new shared helpers: `format_config_context()` in `errors.py` (consistent error bodies) and a `render_auth_help()` renderer in `help.py` (in-CLI auth guidance). The `providers` command becomes a real Click subcommand group with a one-release deprecation shim for the old `providers -- --list` form. Spinner integration is a small `src/thoth/progress.py` module + a wrapper in `run.py`.

**Tech Stack:** Python 3.11+, click, rich, `thothspinner` (new dep), pytest + `click.testing.CliRunner` + `./thoth_test`, ruff + ty.

**Diff from v8:**
- ❌ **Drop v8 Task 1** — `is_deep_research_model` is unnecessary; `is_background_model` already exists at `src/thoth/config.py:136`. All v8 references rewritten to use the existing name.
- ❌ **Drop v8 Task 6** — `thoth workflow` command. User direction; `thoth modes` already shows kind.
- ✏️ **Simplify Task 4 (help epilog)** — `thoth modes` already lists modes by kind. Limit epilog edit to: add the workflow chain line + new worked examples (`--auto` chain, `--resume`, `-v` debug). Skip the quick/deep grouping inside the epilog.
- ✏️ **Task 7 (providers subgroup)** — leverage the existing `COMMANDS` tuple at `src/thoth/help.py` introduced by commit `2e14333`.

---

## 0. Test design (TDD — designed before any implementation)

| Scope | Test file | What it asserts |
|---|---|---|
| `format_config_context()` helper | `tests/test_error_context.py` (new) | Path present/absent × env var set/unset (4 cases) |
| `APIKeyError` body | `tests/test_error_context.py` | Message contains config path + env-var status |
| `--input-file`/`--auto` help text | `tests/test_cli_help.py` (new) | Both new descriptions present in `--help` |
| Workflow chain + examples in epilog | `tests/test_cli_help.py` | Ladder line + `--resume` + `-v` example all present |
| `thoth help auth` ordering | `tests/test_help_auth.py` (new) | env-vars first, config-file second, CLI-flags last with deprecation hint |
| `thoth providers list/models/check` | `tests/test_providers_subcommand.py` (new) | Each subcommand exits 0 with expected output shape |
| `providers -- --list` deprecation | `tests/test_providers_subcommand.py` | Old form exits 0 + prints deprecation line on stderr |
| Spinner gate | `tests/test_progress_spinner.py` (new) | Engages only when background AND not `--async` AND not `-v` AND TTY |
| SIGINT during spinner | `tests/test_progress_spinner.py` | Checkpoint saved + "Resume later" hint printed |
| `--pick-model` on background mode | `tests/test_pick_model.py` (new) | Exit non-zero, stderr matches |
| `--pick-model` on immediate mode | `tests/test_pick_model.py` | Picker called, model_override propagated |
| Regression | `./thoth_test -r --provider mock --skip-interactive` | 63/64 pass, 1 skip, 0 fail |

**Per-task iteration command (fast):** `uv run pytest tests/<file>::<test> -x -v`

**End-of-project gate:** `make env-check && just fix && just check && ./thoth_test -r && just test-fix && just test-lint && just test-typecheck`

---

## 1. File Structure

| File | Create/Modify | Responsibility |
|---|---|---|
| `src/thoth/errors.py` | Modify | `format_config_context()`; enrich `APIKeyError` body |
| `src/thoth/help.py` | Modify | Workflow chain + examples + `-v` block in epilog; `render_auth_help()`; `show_auth_help()`; soften `--api-key-*` help via existing renderers |
| `src/thoth/cli.py` | Modify | Reword `--input-file`/`--auto`; soften `--api-key-*` help; add `--pick-model/-M`; route `providers <sub>`; add `auth` to help-topic dispatch |
| `src/thoth/commands.py` | Modify | `providers_list`, `providers_models`, `providers_check` handlers |
| `src/thoth/run.py` | Modify | Apply `--pick-model` override; wrap sync-poll with spinner via gate |
| `src/thoth/signals.py` | Modify | Print "Resume later" hint on SIGINT when an op is in flight |
| `src/thoth/progress.py` | Create | `should_show_spinner()` gate + `run_with_spinner()` context manager |
| `src/thoth/interactive_picker.py` | Create | Model picker UI used by `--pick-model` (immediate modes only) |
| `pyproject.toml` | Modify | Add `thothspinner` dep |
| `README.md` | Modify | New Authentication section; `--input-file`/`--auto` examples |
| `CHANGELOG.md` | Modify | One unreleased section summarizing the change |
| `PROJECTS.md` | Modify | Add `P14: Thoth CLI Ergonomics v1` block |
| `tests/test_error_context.py` | Create | Helper + APIKeyError tests |
| `tests/test_cli_help.py` | Create | Help-string assertions |
| `tests/test_help_auth.py` | Create | `thoth help auth` ordering |
| `tests/test_providers_subcommand.py` | Create | Subgroup + deprecation shim |
| `tests/test_progress_spinner.py` | Create | Gate + SIGINT |
| `tests/test_pick_model.py` | Create | Allow/reject paths |

---

## Task 1: `format_config_context()` helper

**Files:**
- Create: `tests/test_error_context.py`
- Modify: `src/thoth/errors.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_error_context.py
from thoth.errors import format_config_context


def test_context_path_exists_env_set(tmp_path, monkeypatch):
    cfg = tmp_path / "config.toml"
    cfg.write_text("")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-x")
    out = format_config_context(cfg, env_vars=["OPENAI_API_KEY"])
    assert str(cfg) in out
    assert "(exists)" in out
    assert "OPENAI_API_KEY" in out
    assert "(set)" in out


def test_context_path_missing_env_unset(tmp_path, monkeypatch):
    cfg = tmp_path / "missing.toml"
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    out = format_config_context(cfg, env_vars=["OPENAI_API_KEY"])
    assert "(does not exist)" in out
    assert "(unset)" in out


def test_context_multiple_env_vars(tmp_path, monkeypatch):
    monkeypatch.setenv("A", "1")
    monkeypatch.delenv("B", raising=False)
    out = format_config_context(tmp_path / "c.toml", env_vars=["A", "B"])
    assert "A" in out and "(set)" in out
    assert "B" in out and "(unset)" in out


def test_context_no_env_vars(tmp_path):
    out = format_config_context(tmp_path / "c.toml", env_vars=[])
    assert "Config file:" in out
    assert "Env checked:" not in out
```

- [ ] **Step 2: Run — expect fail**

```bash
uv run pytest tests/test_error_context.py -x -v
```

Expected: `ImportError: cannot import name 'format_config_context'`

- [ ] **Step 3: Implement**

Add to `src/thoth/errors.py`:

```python
import os
from pathlib import Path


def format_config_context(
    config_path: Path | str, env_vars: list[str] | None = None
) -> str:
    """Return a multi-line "Resolved from:" block for error bodies.

    Shows the config file path + whether it exists, and optional env vars
    + whether each is set. Used by APIKeyError so users can see what the
    tool consulted when resolving credentials.
    """
    p = Path(config_path)
    lines = [f"  Config file: {p}  ({'exists' if p.exists() else 'does not exist'})"]
    if env_vars:
        parts = [
            f"{name} ({'set' if os.environ.get(name) else 'unset'})"
            for name in env_vars
        ]
        lines.append(f"  Env checked: {', '.join(parts)}")
    return "\n".join(lines)
```

- [ ] **Step 4: Run — expect pass**

```bash
uv run pytest tests/test_error_context.py -x -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add tests/test_error_context.py src/thoth/errors.py
git commit -m "feat(errors): add format_config_context helper"
```

---

## Task 2: Enrich `APIKeyError` with config context

**Files:**
- Modify: `tests/test_error_context.py`
- Modify: `src/thoth/errors.py`

- [ ] **Step 1: Append failing test**

```python
# Append to tests/test_error_context.py
from thoth.errors import APIKeyError


def test_api_key_error_includes_config_path(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    err = APIKeyError("openai")
    assert err.suggestion is not None
    assert "config.toml" in err.suggestion
    assert "OPENAI_API_KEY" in err.suggestion
    assert "(unset)" in err.suggestion
```

- [ ] **Step 2: Run — expect fail**

```bash
uv run pytest tests/test_error_context.py::test_api_key_error_includes_config_path -x -v
```

- [ ] **Step 3: Update `APIKeyError`**

Replace the body in `src/thoth/errors.py`:

```python
class APIKeyError(ThothError):
    """Missing or invalid API key"""

    def __init__(self, provider: str):
        from thoth.paths import user_config_file  # local import to avoid cycles

        env_var = f"{provider.upper()}_API_KEY"
        cfg_path = user_config_file()
        suggestion = (
            f"Set {env_var} (or edit {cfg_path})\n"
            + format_config_context(cfg_path, env_vars=[env_var])
        )
        super().__init__(
            f"{provider} API key not found",
            suggestion,
            exit_code=2,
        )
```

- [ ] **Step 4: Run full error-context tests + nearby regression — expect pass**

```bash
uv run pytest tests/test_error_context.py tests/test_api_key_resolver.py tests/test_openai_errors.py -x -v
```

- [ ] **Step 5: Commit**

```bash
git add tests/test_error_context.py src/thoth/errors.py
git commit -m "feat(errors): surface config file path in APIKeyError"
```

---

## Task 3: `--input-file` / `--auto` clearer help

**Files:**
- Create: `tests/test_cli_help.py`
- Modify: `src/thoth/cli.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cli_help.py
from click.testing import CliRunner

from thoth.cli import cli


def _help() -> str:
    return CliRunner().invoke(cli, ["--help"]).output


def test_auto_help_mentions_happy_path():
    assert "happy path for chaining modes" in _help()


def test_input_file_help_mentions_advanced_usage():
    assert "non-thoth document" in _help()
```

- [ ] **Step 2: Run — expect fail**

```bash
uv run pytest tests/test_cli_help.py -x -v
```

- [ ] **Step 3: Rewrite help strings**

In `src/thoth/cli.py`, replace the existing `--input-file` and `--auto` decorators:

```python
@click.option(
    "--input-file",
    help=(
        "Use the file at PATH as input for this mode. Use when feeding a "
        "non-thoth document, an older run, or a file from a different project."
    ),
)
@click.option(
    "--auto",
    is_flag=True,
    help=(
        "Pick up the latest output from the previous mode in the same "
        "--project directory. The happy path for chaining modes."
    ),
)
```

- [ ] **Step 4: Run — expect pass**

```bash
uv run pytest tests/test_cli_help.py -x -v
```

- [ ] **Step 5: Commit**

```bash
git add tests/test_cli_help.py src/thoth/cli.py
git commit -m "docs(cli): clarify --auto vs --input-file help text"
```

---

## Task 4: Workflow chain + worked examples in epilog

**Files:**
- Modify: `tests/test_cli_help.py`
- Modify: `src/thoth/help.py`

- [ ] **Step 1: Append failing tests**

```python
# Append to tests/test_cli_help.py
def test_help_has_workflow_chain():
    out = _help()
    assert "Workflow chain" in out
    assert "clarification → exploration → deep_dive" in out


def test_help_has_resume_example():
    out = _help()
    assert "thoth --resume" in out


def test_help_has_verbose_example():
    out = _help()
    assert "Debug API issues" in out
    assert "-v" in out


def test_help_has_async_chain_example():
    out = _help()
    assert "thoth deep_research --auto" in out
    assert "--async" in out
```

- [ ] **Step 2: Run — expect fail**

```bash
uv run pytest tests/test_cli_help.py -x -v
```

- [ ] **Step 3: Update `build_epilog()`**

In `src/thoth/help.py`, edit `build_epilog()` so the section after `Research Modes:` includes the workflow chain + new examples. Keep the `thoth modes` reference for full per-mode detail. Replace the existing `Research Modes` and `Examples` sections with:

```python
    lines.append("Research Modes:")
    lines.append(f"  {', '.join(BUILTIN_MODES.keys())}")
    lines.append("  Run `thoth modes` for provider, model, and kind per mode.")
    lines.append("")
    lines.append("  Workflow chain (each step feeds the next via --auto):")
    lines.append("    clarification → exploration → deep_dive → tutorial → solution → prd → tdd")
    lines.append("")

    lines.append("Examples:")
    lines.append("  # Quick")
    lines.append('  $ thoth "how does DNS work"')
    lines.append("")
    lines.append("  # Sharpen, then research (chain with --auto)")
    lines.append('  $ thoth clarification "k8s networking" --project k8s')
    lines.append("  $ thoth exploration --auto --project k8s")
    lines.append("  $ thoth deep_research --auto --project k8s --async")
    lines.append("")
    lines.append("  # Resume a backgrounded job")
    lines.append("  $ thoth --resume op_abc123")
    lines.append("")
    lines.append("  # Debug API issues — show model, provider, timeouts, retries")
    lines.append('  $ thoth deep_research "topic" -v')
    lines.append("")
    lines.append("For detailed command help: thoth help [COMMAND]")
```

- [ ] **Step 4: Run — expect pass**

```bash
uv run pytest tests/test_cli_help.py -x -v
```

- [ ] **Step 5: Commit**

```bash
git add tests/test_cli_help.py src/thoth/help.py
git commit -m "docs(help): add workflow chain + chained/async/resume/-v examples"
```

---

## Task 5: `thoth help auth` + README authentication section

**Files:**
- Create: `tests/test_help_auth.py`
- Modify: `src/thoth/help.py`
- Modify: `src/thoth/cli.py` (soften `--api-key-*` help)
- Modify: `README.md`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_help_auth.py
from click.testing import CliRunner

from thoth.cli import cli


def test_help_auth_lists_env_first():
    r = CliRunner().invoke(cli, ["--help", "auth"])
    assert r.exit_code == 0
    out = r.output
    i_env = out.find("Environment variables")
    i_cfg = out.find("Config file")
    i_flag = out.find("CLI flags")
    assert 0 <= i_env < i_cfg < i_flag


def test_help_auth_marks_cli_flag_as_last_resort():
    r = CliRunner().invoke(cli, ["--help", "auth"])
    assert "not recommended" in r.output or "last resort" in r.output


def test_api_key_cli_flag_help_soft_warning():
    r = CliRunner().invoke(cli, ["--help"])
    assert "not recommended" in r.output
```

- [ ] **Step 2: Run — expect fail**

```bash
uv run pytest tests/test_help_auth.py -x -v
```

- [ ] **Step 3: Add renderer + dispatcher**

Append to `src/thoth/help.py`:

```python
def render_auth_help() -> str:
    return (
        "Authentication — recommended order:\n"
        "\n"
        "1. Environment variables (recommended):\n"
        "     export OPENAI_API_KEY=sk-...\n"
        "     export PERPLEXITY_API_KEY=pplx-...\n"
        "\n"
        "2. Config file (persistent, per-machine): ~/.thoth/config.toml\n"
        "     [providers.openai]\n"
        '     api_key = "sk-..."\n'
        "\n"
        "3. CLI flags (last resort — exposes keys in shell history; not recommended):\n"
        '     thoth --api-key-openai sk-... deep_research "..."\n'
    )


def show_auth_help() -> None:
    console.print(render_auth_help())
```

In `ThothCommand.parse_args` (existing chain in `help.py`), add an `auth` branch:

```python
elif subcommand == "auth":
    show_auth_help()
    ctx.exit(0)
```

If the existing `HELP_TOPICS` tuple in `help.py` is the source of truth for valid `thoth help <topic>` names, append `"auth"` (and add a corresponding entry to `COMMANDS` only if the auth helper should also appear under `Commands:`; per the spec it should not — auth is help-only).

- [ ] **Step 4: Soften CLI-flag help strings**

In `src/thoth/cli.py`:

```python
@click.option("--api-key-openai", help="API key for OpenAI provider (not recommended; prefer env vars)")
@click.option("--api-key-perplexity", help="API key for Perplexity provider (not recommended; prefer env vars)")
@click.option("--api-key-mock", help="API key for Mock provider (not recommended; prefer env vars)")
```

- [ ] **Step 5: Run — expect pass**

```bash
uv run pytest tests/test_help_auth.py -x -v
```

- [ ] **Step 6: Update README**

Replace the Authentication section of `README.md` with the exact text from `render_auth_help()`, plus a one-line note pointing readers at `thoth help auth` for the in-CLI version.

- [ ] **Step 7: Commit**

```bash
git add tests/test_help_auth.py src/thoth/help.py src/thoth/cli.py README.md
git commit -m "docs(auth): add 'thoth help auth' and authentication ordering pass"
```

---

## Task 6: `providers list/models/check` subcommands + deprecation shim

**Files:**
- Create: `tests/test_providers_subcommand.py`
- Modify: `src/thoth/commands.py`
- Modify: `src/thoth/cli.py`
- Modify: `src/thoth/help.py` (deprecation message hooks; keep `providers` in `COMMANDS`)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_providers_subcommand.py
from click.testing import CliRunner

from thoth.cli import cli


def test_providers_list_exits_zero():
    r = CliRunner().invoke(cli, ["providers", "list"])
    assert r.exit_code == 0
    assert "openai" in r.output.lower()


def test_providers_models_exits_zero():
    r = CliRunner().invoke(cli, ["providers", "models"])
    assert r.exit_code == 0


def test_providers_check_returns_status():
    r = CliRunner().invoke(cli, ["providers", "check"])
    # 0 if all keys present, 2 if any missing — both are valid clean exits.
    assert r.exit_code in (0, 2)


def test_old_form_deprecated_but_works():
    r = CliRunner(mix_stderr=False).invoke(cli, ["providers", "--", "--list"])
    assert r.exit_code == 0
    combined = (r.stderr or "") + r.output
    assert "deprecated" in combined.lower()
    assert "openai" in r.output.lower()
```

- [ ] **Step 2: Run — expect fail**

```bash
uv run pytest tests/test_providers_subcommand.py -x -v
```

- [ ] **Step 3: Add handler functions**

In `src/thoth/commands.py` add (or replace, if there is an existing `providers` handler) three handlers. Reuse existing key-resolution helpers if present in `commands.py` or `config.py`; the snippet below is a self-contained reference to keep this plan complete.

```python
def providers_list(config) -> int:
    """List configured providers and whether each has a usable key."""
    import os
    import re
    from rich.console import Console

    console = Console()
    console.print("Configured providers:")
    for name in sorted(config.data["providers"].keys()):
        raw = config.data["providers"][name].get("api_key", "")
        m = re.match(r"\$\{(\w+)\}", raw or "")
        resolved = os.environ.get(m.group(1)) if m else (raw or None)
        console.print(f"  {name:<12} {'key set' if resolved else 'no key'}")
    return 0


def providers_models(config) -> int:
    """List models known per provider, derived from BUILTIN_MODES."""
    from rich.console import Console
    from thoth.config import BUILTIN_MODES

    seen: dict[str, set[str]] = {}
    for cfg in BUILTIN_MODES.values():
        seen.setdefault(cfg["provider"], set()).add(cfg["model"])
    console = Console()
    for provider, models in sorted(seen.items()):
        console.print(f"{provider}:")
        for m in sorted(models):
            console.print(f"  {m}")
    return 0


def providers_check(config) -> int:
    """Exit 0 if every configured provider has a usable key; else 2."""
    import os
    import re
    from rich.console import Console

    missing = []
    for name, p in config.data["providers"].items():
        raw = p.get("api_key", "")
        m = re.match(r"\$\{(\w+)\}", raw or "")
        resolved = os.environ.get(m.group(1)) if m else (raw or None)
        if not resolved:
            missing.append(name)
    console = Console()
    if missing:
        console.print(f"[red]Missing keys for:[/] {', '.join(missing)}")
        return 2
    console.print("[green]All providers have keys set[/]")
    return 0
```

- [ ] **Step 4: Wire `providers` dispatch in `cli.py`**

Find the existing block in `src/thoth/cli.py` that catches commands by name (the block that uses `COMMAND_NAMES`). Where it currently dispatches `providers` to the legacy handler, replace with subcommand routing:

```python
if first_arg == "providers":
    sub = args[1] if len(args) >= 2 else None
    config_manager = ConfigManager()
    config_manager.load_all_layers({"config_path": config_path})
    cfg = config_manager
    if sub == "list":
        ctx.exit(providers_list(cfg))
    elif sub == "models":
        ctx.exit(providers_models(cfg))
    elif sub == "check":
        ctx.exit(providers_check(cfg))
    elif sub == "--" and len(args) >= 3 and args[2] == "--list":
        click.echo(
            "warning: 'thoth providers -- --list' is deprecated; "
            "use 'thoth providers list'",
            err=True,
        )
        ctx.exit(providers_list(cfg))
    elif sub in (None, "--help", "help"):
        from thoth.help import show_providers_help
        show_providers_help()
        ctx.exit(0)
    else:
        click.echo(f"Unknown providers subcommand: {sub}", err=True)
        ctx.exit(2)
```

(`config_manager.load_all_layers` use must match how the rest of `cli.py` already loads config — match the existing pattern; do not introduce a new one.)

- [ ] **Step 5: Run — expect pass**

```bash
uv run pytest tests/test_providers_subcommand.py -x -v
```

- [ ] **Step 6: Run thoth_test regression**

```bash
./thoth_test -r --provider mock --skip-interactive 2>&1 | tail -10
```

Expected: 63 passed, 1 skipped, 0 failed.

- [ ] **Step 7: Commit**

```bash
git add tests/test_providers_subcommand.py src/thoth/commands.py src/thoth/cli.py src/thoth/help.py
git commit -m "feat(cli): 'providers list/models/check' subcommands + deprecation shim"
```

---

## Task 7: Add `thothspinner` dependency

**Files:**
- Modify: `pyproject.toml`, `uv.lock`

- [ ] **Step 1: Add dep**

```bash
uv add thothspinner
```

- [ ] **Step 2: Verify import**

```bash
uv run python -c "from thothspinner import ThothSpinner; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore(deps): add thothspinner for progress indicator"
```

---

## Task 8: Progress spinner module + gate

**Files:**
- Create: `tests/test_progress_spinner.py`
- Create: `src/thoth/progress.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_progress_spinner.py
import pytest

from thoth.progress import should_show_spinner


class FakeTTY:
    def isatty(self):
        return True


class FakePipe:
    def isatty(self):
        return False


@pytest.mark.parametrize(
    "model,async_mode,verbose,stream,expected",
    [
        ("o3-deep-research", False, False, FakeTTY(), True),
        ("o3-deep-research", True, False, FakeTTY(), False),    # async
        ("o3-deep-research", False, True, FakeTTY(), False),    # -v
        ("o3-deep-research", False, False, FakePipe(), False),  # piped
        ("o3", False, False, FakeTTY(), False),                  # immediate
        (None, False, False, FakeTTY(), False),
    ],
)
def test_gate(model, async_mode, verbose, stream, expected):
    assert should_show_spinner(
        model=model, async_mode=async_mode, verbose=verbose, stream=stream
    ) is expected
```

- [ ] **Step 2: Run — expect fail**

```bash
uv run pytest tests/test_progress_spinner.py -x -v
```

- [ ] **Step 3: Implement module**

Create `src/thoth/progress.py`:

```python
"""Progress spinner integration for sync background-mode operations."""

from __future__ import annotations

import sys
from contextlib import contextmanager
from typing import IO, Iterator

from thoth.config import is_background_model


def should_show_spinner(
    *,
    model: str | None,
    async_mode: bool,
    verbose: bool,
    stream: IO[str] | None = None,
) -> bool:
    """Decide whether to engage the progress spinner.

    Engages only when ALL hold:
      - the resolved model is a background (deep-research) model
      - --async is NOT set (sync caller is the one waiting)
      - --verbose is NOT set (verbose keeps raw-log UX)
      - the output stream is a TTY (avoid clobbering pipes/CI)
    """
    if async_mode or verbose:
        return False
    if not is_background_model(model):
        return False
    s = stream if stream is not None else sys.stdout
    return bool(getattr(s, "isatty", lambda: False)())


@contextmanager
def run_with_spinner(label: str, expected_minutes: int = 20) -> Iterator[None]:
    """Display a ThothSpinner while the wrapped block runs.

    Caller pre-decides via should_show_spinner(); this context manager assumes
    the gate already returned True.
    """
    from rich.console import Console
    from rich.live import Live
    from thothspinner import ThothSpinner

    console = Console()
    spinner = ThothSpinner()
    if hasattr(spinner, "set_message"):
        spinner.set_message(
            f"{label} · ~{expected_minutes} min expected · Ctrl-C to background"
        )
    with Live(spinner, console=console, refresh_per_second=10):
        spinner.start()
        try:
            yield
            if hasattr(spinner, "success"):
                spinner.success(f"{label} complete")
        except BaseException:
            if hasattr(spinner, "error"):
                spinner.error(f"{label} interrupted")
            raise
```

- [ ] **Step 4: Run — expect pass**

```bash
uv run pytest tests/test_progress_spinner.py -x -v
```

- [ ] **Step 5: Commit**

```bash
git add tests/test_progress_spinner.py src/thoth/progress.py
git commit -m "feat(progress): add spinner gate + run_with_spinner context"
```

---

## Task 9: Wire spinner into `run.py`

**Files:**
- Modify: `src/thoth/run.py`
- Modify: `tests/test_progress_spinner.py`

- [ ] **Step 1: Append integration test**

```python
# Append to tests/test_progress_spinner.py
from contextlib import contextmanager


def test_maybe_spinner_calls_spinner_when_gate_passes(monkeypatch):
    called = {"entered": False}

    @contextmanager
    def fake_spinner(label, expected_minutes=20):
        called["entered"] = True
        yield

    monkeypatch.setattr("thoth.run.run_with_spinner", fake_spinner)
    monkeypatch.setattr("thoth.run.should_show_spinner", lambda **kw: True)

    from thoth.run import _maybe_spinner

    with _maybe_spinner(
        model="o3-deep-research", async_mode=False, verbose=False,
        label="Deep research running",
    ):
        pass
    assert called["entered"] is True


def test_maybe_spinner_is_noop_when_gate_fails(monkeypatch):
    called = {"entered": False}

    @contextmanager
    def fake_spinner(label, expected_minutes=20):
        called["entered"] = True
        yield

    monkeypatch.setattr("thoth.run.run_with_spinner", fake_spinner)
    monkeypatch.setattr("thoth.run.should_show_spinner", lambda **kw: False)

    from thoth.run import _maybe_spinner

    with _maybe_spinner(
        model="o3", async_mode=False, verbose=False, label="x",
    ):
        pass
    assert called["entered"] is False
```

- [ ] **Step 2: Run — expect fail**

```bash
uv run pytest tests/test_progress_spinner.py -x -v
```

- [ ] **Step 3: Add helper + wrap polling in `run.py`**

Add near the top of `src/thoth/run.py`:

```python
from contextlib import contextmanager

from thoth.progress import run_with_spinner, should_show_spinner


@contextmanager
def _maybe_spinner(*, model, async_mode, verbose, label, expected_minutes=20):
    if should_show_spinner(model=model, async_mode=async_mode, verbose=verbose):
        with run_with_spinner(label, expected_minutes=expected_minutes):
            yield
    else:
        yield
```

Then locate the sync poll loop further down (the block that loops awaiting `provider.get_status` / `poll_interval`). Wrap it:

```python
mode_model = mode_config.get("model")
with _maybe_spinner(
    model=mode_model,
    async_mode=async_mode,
    verbose=verbose,
    label="Deep research running",
):
    # existing poll loop as-is
    ...
```

- [ ] **Step 4: Run — expect pass**

```bash
uv run pytest tests/test_progress_spinner.py -x -v
```

- [ ] **Step 5: Run regression**

```bash
./thoth_test -r --provider mock --skip-interactive 2>&1 | tail -10
```

Expected: 63 passed, 1 skipped, 0 failed.

- [ ] **Step 6: Commit**

```bash
git add tests/test_progress_spinner.py src/thoth/run.py
git commit -m "feat(run): show progress spinner during sync background-mode runs"
```

---

## Task 10: SIGINT "Resume later" hint

**Files:**
- Modify: `tests/test_progress_spinner.py`
- Modify: `src/thoth/signals.py`

- [ ] **Step 1: Append failing test**

```python
# Append to tests/test_progress_spinner.py
def test_sigint_prints_resume_hint(capsys):
    import thoth.signals as sig

    class FakeOp:
        id = "op_abc123"

    class FakeManager:
        def save_sync(self, op):  # noqa: ARG002
            return None

    sig._current_operation = FakeOp()
    sig._current_checkpoint_manager = FakeManager()
    try:
        sig._handle_sigint(None, None)
    except SystemExit:
        pass
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert "Resume later: thoth --resume op_abc123" in output
```

If the SIGINT handler in `src/thoth/signals.py` uses different function names, run `grep -n "def.*sigint\|signal.SIGINT\|handler" src/thoth/signals.py` and adjust the test accordingly. The assertion (output contains the hint) is the part that must hold.

- [ ] **Step 2: Run — expect fail**

```bash
uv run pytest tests/test_progress_spinner.py::test_sigint_prints_resume_hint -x -v
```

- [ ] **Step 3: Add hint print in the handler**

In `src/thoth/signals.py`, locate the SIGINT handler (the function that calls the checkpoint save). After the save and before `sys.exit(...)`, add:

```python
import click

if _current_operation is not None:
    click.echo(
        f"\nBackgrounded. Resume later: thoth --resume {_current_operation.id}"
    )
```

- [ ] **Step 4: Run — expect pass**

```bash
uv run pytest tests/test_progress_spinner.py::test_sigint_prints_resume_hint tests/test_sigint_handler.py -x -v
```

- [ ] **Step 5: Commit**

```bash
git add tests/test_progress_spinner.py src/thoth/signals.py
git commit -m "feat(signals): print resume hint when SIGINT backgrounds an op"
```

---

## Task 11: `--pick-model` rejection on background modes

**Files:**
- Create: `tests/test_pick_model.py`
- Modify: `src/thoth/cli.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_pick_model.py
from click.testing import CliRunner

from thoth.cli import cli


def test_pick_model_rejected_on_deep_research():
    r = CliRunner(mix_stderr=False).invoke(
        cli, ["--pick-model", "deep_research", "some prompt"]
    )
    assert r.exit_code != 0
    combined = (r.stderr or "") + r.output
    assert "only supported for quick" in combined or "only supported for immediate" in combined


def test_pick_model_rejected_on_exploration():
    r = CliRunner(mix_stderr=False).invoke(
        cli, ["--pick-model", "exploration", "some prompt"]
    )
    assert r.exit_code != 0
```

- [ ] **Step 2: Run — expect fail**

```bash
uv run pytest tests/test_pick_model.py -x -v
```

- [ ] **Step 3: Add flag + guard**

In `src/thoth/cli.py`, add the option:

```python
@click.option(
    "--pick-model",
    "-M",
    "pick_model",
    is_flag=True,
    help="Interactively pick a model (immediate modes only)",
)
```

Add `pick_model` to the `cli()` function signature. After the mode/positional resolution block (where `final_mode` is set), add the guard:

```python
if pick_model:
    from thoth.config import BUILTIN_MODES, is_background_model

    mode_cfg = BUILTIN_MODES.get(final_mode, {})
    if is_background_model(mode_cfg.get("model")):
        click.echo(
            "Error: --pick-model is only supported for quick (non-deep-research) modes.\n"
            f"       Mode '{final_mode}' uses {mode_cfg.get('model')}.\n"
            "       Interactive model selection for deep-research models would change\n"
            "       the research quality and cost profile; edit ~/.thoth/config.toml\n"
            "       to override the model for a deep-research mode.",
            err=True,
        )
        ctx.exit(2)
```

- [ ] **Step 4: Run — expect pass**

```bash
uv run pytest tests/test_pick_model.py -x -v
```

- [ ] **Step 5: Commit**

```bash
git add tests/test_pick_model.py src/thoth/cli.py
git commit -m "feat(cli): reject --pick-model on background-mode modes"
```

---

## Task 12: `--pick-model` interactive picker for immediate modes

**Files:**
- Create: `src/thoth/interactive_picker.py`
- Modify: `tests/test_pick_model.py`
- Modify: `src/thoth/cli.py`
- Modify: `src/thoth/run.py`

- [ ] **Step 1: Append failing test**

```python
# Append to tests/test_pick_model.py
def test_pick_model_quick_mode_uses_picker(monkeypatch):
    picked = {}

    def fake_pick(models):
        picked["called"] = True
        return "gpt-4o-mini"

    monkeypatch.setattr("thoth.interactive_picker.pick_model", fake_pick)

    captured = {}

    def fake_run(*args, **kwargs):
        captured.update(kwargs)
        return 0

    # The runner entrypoint name must match cli.py's call. If the existing
    # entrypoint differs, adjust BOTH this monkeypatch target AND the cli.py
    # call site so they line up.
    monkeypatch.setattr("thoth.run.run_research", fake_run)

    r = CliRunner().invoke(cli, ["--pick-model", "default", "hello world"])
    assert r.exit_code == 0
    assert picked.get("called") is True
    assert captured.get("model_override") == "gpt-4o-mini"
```

- [ ] **Step 2: Run — expect fail**

```bash
uv run pytest tests/test_pick_model.py::test_pick_model_quick_mode_uses_picker -x -v
```

- [ ] **Step 3: Create picker module**

Create `src/thoth/interactive_picker.py`:

```python
"""Interactive model picker — only used for immediate (non-background) modes."""

from __future__ import annotations


def pick_model(models: list[str]) -> str:
    """Show a numbered picker and return the selected model string.

    Tests monkeypatch this function directly so the picker UI is never
    actually shown during pytest runs.
    """
    import click

    if not models:
        raise RuntimeError("No models available to pick from")
    click.echo("Available immediate-mode models:")
    for i, m in enumerate(models, start=1):
        click.echo(f"  {i}. {m}")
    idx = click.prompt("Pick a model", type=click.IntRange(1, len(models)))
    return models[idx - 1]


def immediate_models_for_provider(provider: str) -> list[str]:
    """Return known immediate (non-background) models for the provider."""
    from thoth.config import BUILTIN_MODES, is_background_model

    seen: set[str] = set()
    for cfg in BUILTIN_MODES.values():
        if cfg.get("provider") == provider and not is_background_model(cfg.get("model")):
            seen.add(cfg["model"])
    if provider == "openai":
        seen.update({"o3", "gpt-4o-mini", "gpt-4o"})
    return sorted(seen)
```

- [ ] **Step 4: Wire into `cli.py`**

Extend the Task 11 block: in the `else` branch (immediate mode), call the picker and capture the override.

```python
else:
    from thoth.interactive_picker import pick_model as _pick, immediate_models_for_provider
    provider_name = mode_cfg.get("provider", "openai")
    model_override = _pick(immediate_models_for_provider(provider_name))
```

If `pick_model` is False, set `model_override = None`. Pass `model_override` through to whatever runner entrypoint `cli.py` already invokes for sync runs.

- [ ] **Step 5: Honor override in `run.py`**

Add a `model_override: str | None = None` kwarg to the runner entrypoint (whichever name `cli.py` calls — `run_research` is the working assumption; verify before editing). Apply at the point where `mode_config` is finalized:

```python
if model_override is not None:
    mode_config = {**mode_config, "model": model_override}
```

- [ ] **Step 6: Run — expect pass**

```bash
uv run pytest tests/test_pick_model.py -x -v
```

- [ ] **Step 7: Commit**

```bash
git add tests/test_pick_model.py src/thoth/interactive_picker.py src/thoth/cli.py src/thoth/run.py
git commit -m "feat(cli): --pick-model interactive picker for immediate modes"
```

---

## Task 13: CHANGELOG + PROJECTS.md

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `PROJECTS.md`

- [ ] **Step 1: CHANGELOG entry**

Prepend to `CHANGELOG.md` under a new unreleased section:

```markdown
## [Unreleased]

### Added
- `thoth providers list`, `thoth providers models`, `thoth providers check` — explicit subcommands replace `thoth providers -- --list`.
- `thoth help auth` — in-CLI authentication guidance.
- `--pick-model` / `-M` flag for interactively selecting a model on immediate (non-background) modes.
- Progress spinner during sync background-mode runs (via `thothspinner`).
- Config file path surfaced in `APIKeyError` messages.
- "Resume later: thoth --resume OP_ID" hint on Ctrl-C.

### Changed
- `--help` now shows the workflow chain (clarification → … → tdd) and worked examples for `--auto`, `--async`/`--resume`, and `-v` debugging.
- `--input-file` / `--auto` help rewritten for clarity.
- `--api-key-openai` / `--api-key-perplexity` / `--api-key-mock` help now says "(not recommended; prefer env vars)".
- README Authentication section documents env-vars → config-file → CLI-flags in that order.

### Deprecated
- `thoth providers -- --list` — still works for one release; use `thoth providers list`.
```

- [ ] **Step 2: PROJECTS.md entry**

Insert at the top of `PROJECTS.md` (before P13 since project numbers count up):

```markdown
## [x] Project P14: Thoth CLI Ergonomics v1 (v2.12.0)
**Goal**: Reduce first-time-user friction in the thoth CLI.

### Tests & Tasks
- [x] [P14-T01] format_config_context helper + APIKeyError enrichment
- [x] [P14-T02] --input-file/--auto clearer help
- [x] [P14-T03] Workflow chain + worked examples in --help epilog
- [x] [P14-T04] thoth help auth + README authentication ordering pass
- [x] [P14-T05] providers list/models/check subcommands + deprecation shim
- [x] [P14-T06] thothspinner dependency
- [x] [P14-T07] Progress spinner module + gate
- [x] [P14-T08] Wire spinner into run.py polling
- [x] [P14-T09] SIGINT Resume-later hint
- [x] [P14-T10] --pick-model rejection on background modes
- [x] [P14-T11] --pick-model interactive picker for immediate modes
```

(Adjust version `v2.12.0` if `pyproject.toml` shows a different next bump.)

- [ ] **Step 3: Commit**

```bash
git add CHANGELOG.md PROJECTS.md
git commit -m "docs(projects): add P14 ergonomics-v1 + CHANGELOG entry"
```

---

## Task 14: Final gate

- [ ] **Step 1: Full pre-commit equivalent**

```bash
make env-check
just fix
just check
./thoth_test -r
just test-fix
just test-lint
just test-typecheck
```

Expected: every step green; `./thoth_test` reports 63 passed / 1 skipped / 0 failed.

- [ ] **Step 2: Manual smoke checks**

```bash
thoth --help | head -60                          # workflow chain + examples visible
thoth --help auth                                # auth ordering visible
thoth providers list                             # exits 0
thoth providers -- --list                        # works + deprecation line on stderr
thoth --pick-model deep_research "x"             # exit 2, clear error
thoth --pick-model default "x"                   # picker prompt (pipe `echo 1 |` to auto-pick)
thoth deep_research "hello" --provider mock      # spinner appears
```

- [ ] **Step 3: Hand off for tag/push**

Hand control back to the user for the version-bump + tag + push step (do not push from a subagent).

---

## Self-Review

**Spec coverage:**

| Spec § | Plan task |
|---|---|
| 3.1 `providers` subgroup | Task 6 |
| 3.2 Progress spinner | Tasks 7, 8, 9 |
| 3.3 Mode-ladder help | Task 4 (workflow chain line + examples) |
| 3.4 `thoth workflow` | **Dropped** — covered by existing `thoth modes` + Task 4 ladder line |
| 3.5 API-key docs | Task 5 |
| 3.6 `--input-file`/`--auto` | Task 3 |
| 3.7 `-v` example | Task 4 (combined) |
| 3.8 Config path in errors | Tasks 1, 2 |
| 3.9 `--pick-model` | Tasks 11, 12 |
| §4 helper `is_background_model` | **Already in repo** (P13) |
| §4 `format_config_context` | Task 1 |
| §4 help renderers | Tasks 4, 5 |
| §5 testing approach (TDD) | Section 0 + every task |
| §6 rollout | Tasks 13, 14 |
| §7 risks: non-TTY, deprecation, non-interactive | Tasks 6, 8, 11 |

**Placeholder scan:** Two judgment calls left in the plan, both flagged inline with explicit instructions to adjust to the existing code:
- Task 6 Step 4 — note about matching `cli.py`'s existing `ConfigManager` load pattern.
- Task 12 Step 4 — note about runner entrypoint name (`run_research` is the working assumption; the implementer must verify before editing).

These are not "TBD"s — they are bounded ambiguities resolved by reading two specific call sites. Acceptable in a plan.

**Type consistency:** `is_background_model(model: str | None) -> bool` used identically across Tasks 8, 11, 12. `format_config_context(path, env_vars)` consistent across Tasks 1 and 2. `should_show_spinner(model=, async_mode=, verbose=, stream=)` and `run_with_spinner(label, expected_minutes)` signatures match between Tasks 8 and 9. `model_override: str | None` threads identically through Tasks 11 → 12 → `run.py`.
