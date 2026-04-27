# P16 PR2 — Remove Legacy Shims, Add `resume` + `ask` Subcommands — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land v3.0.0's breakage + new-verbs commits — add `ask` and `resume` subcommands, remove every flag-style shim catalogued in the audit, apply the 13-item Q5-A cleanup batch, split `--raw` / `--show-secrets` security semantics. Preserve every functionality via documented migration to canonical new forms.

**Architecture:** Single PR landing as 12 commits on `main` (no feature branch — user explicit). Each commit is independently reviewable and self-consistent (production code change + corresponding test edit in the same commit). Heavy reliance on Q3-PR2-C `_research_options` decorator helper for DRY between the cli group and `ask`. Gating per Q6-A1+B3+C1 — every removed form `ctx.fail(...)`s with Click-native error containing `(use 'thoth NEW_FORM')` to stderr.

**Tech Stack:** Python 3.11+, Click 8.x, pytest with `CliRunner`, existing `isolated_thoth_home` test fixture, `./thoth_test` integration runner, `uv run` for all Python invocations.

**Spec:** `docs/superpowers/specs/2026-04-26-p16-pr2-design.md`
**Audit:** `docs/superpowers/specs/2026-04-26-p16-pr2-legacy-form-audit.md`
**Predecessor plan (template):** `docs/superpowers/plans/2026-04-25-p16-pr1-cli-refactor.md`
**PROJECTS.md ledger:** P16 PR2 entry (167 tasks: T01–T79 + TS01–TS83 + FU01–FU05)

---

## File Structure

**Create:**
- `src/thoth/cli_subcommands/_options.py` — `_research_options` decorator (~30 LOC; Task 1)
- `src/thoth/cli_subcommands/ask.py` — `ask` Click subcommand wrapping `_run_research_default` (~50 LOC; Task 2)
- `src/thoth/cli_subcommands/resume.py` — `resume` Click subcommand wrapping `resume_operation` (~40 LOC; Task 3)
- `tests/test_p16_pr2_ask.py` — Category A + G tests for `ask` (Task 2)
- `tests/test_p16_pr2_resume.py` — Category A + E + F tests for `resume` (Tasks 3, 5)
- `tests/test_p16_pr2_gating.py` — Category B parametrized gating tests for every removed form (Tasks 5–8)
- `tests/test_p16_pr2_cleanup.py` — Category C tests for Q5-A cleanup batch rows (Tasks 6, 7, 10)
- `tests/test_p16_pr2_config_secrets.py` — Category D `--raw` × `--show-secrets` security matrix (Task 9)

**Modify (production):**
- `src/thoth/cli.py` — apply `_research_options` decorator to the cli group (Task 1); remove `--resume`/`-R` global option declaration + the resume_id keys in `_extract_fallback_options` and `_version_conflicts` (Task 5); remove the `if opts.get("resume_id"):` block in `_dispatch_click_fallback` (Task 5); register `ask` (Task 2) and `resume` (Task 3) subcommands; small touches in Tasks 6–10
- `src/thoth/help.py` — Task 5 adds `--resume`/`-R` early-intercept gating to `ThothGroup.parse_args`; Task 8 removes the `--help <topic>` auth hijack from the SAME method; Task 8 also removes `"completion"` from `ADMIN_COMMANDS`; Task 4 updates the `thoth --resume op_abc123` example string at line 134
- `src/thoth/cli_subcommands/providers.py` — Task 6 removes the in-group flag shim (lines 39–62, 109–173) and adds Q6-C1 `ctx.fail` gating for every legacy flag form; adds `--refresh-cache` and `--no-cache` options to `providers_models_cmd` with mutex per Q5-A row 1
- `src/thoth/cli_subcommands/modes.py` — Task 7 removes `ModesGroup` class entirely + the bare-`modes` shortcut + every hidden `--json/--show-secrets/--full/--name/--source` legacy command; adds Q6-C1 `ctx.fail` gating for those 5 flags; adds Q5-A row 5 (no-leaf exit 2 — natural Click default once `invoke_without_command=False`)
- `src/thoth/modes_cmd.py` — Task 7 removes the early-return at line 261 so `--name` and `--source` intersect (Q5-A row 11.i)
- `src/thoth/cli_subcommands/config.py` — Task 9 promotes `get` to a typed Click command with `--show-secrets` and `--raw` (kept passthrough on `set/unset/list/path/edit/help` to preserve PR1.5 behavior); Task 10 promotes `--layer` to `click.Choice` per Q5-A row 8
- `src/thoth/config_cmd.py` — Task 9 changes `_op_get` line 104 from `if _is_secret_key(key) and not show_secrets and not raw:` to `if _is_secret_key(key) and not show_secrets:` (Q4-D split). The `elif raw:` data-source-merge branch at lines 90–95 is PRESERVED unchanged — Q4-D only addresses masking
- `src/thoth/cli_subcommands/help_cmd.py` — Task 8 removes the `topic == "auth"` virtual-topic branch (lines 25–28); the `auth` topic now only works through `thoth help auth` if a real `auth` subcommand were added — for PR2, drop the parse-time hijack and the help-leaf shortcut. The literal `auth` string in the "Available topics" listing at line 36 is dropped too
- `src/thoth/cli_subcommands/status.py` — Task 10 changes `ctx.exit(1)` to `ctx.exit(2)` per Q5-A row 6
- `src/thoth/run.py` — Task 3 widens `resume_operation` signature with `quiet`, `no_metadata`, `timeout_override`, `cli_api_keys` params (Q1-PR2-C honor-set); Task 4 updates 4 emitter strings at lines 629, 654, 827, 854
- `src/thoth/signals.py` — Task 4 updates 2 emitter strings at lines 93, 99
- `src/thoth/commands.py` — Task 4 updates 2 hint emitters at lines 227, 238; Task 6 (with mutex) — note the `--refresh-cache + --no-cache` precedence is moved up to the leaf via Click mutex, so commands.py change in Task 6 is just keeping behavior consistent
- `src/thoth/providers/openai.py` — Task 4 updates the legacy hint string at line 69 from `'thoth providers -- --models --provider openai'` → `'thoth providers models --provider openai'`
- `src/thoth/cli.py` — Task 7 also removes `--clarify`-without-`--interactive` silent no-op per Q5-A row 7 (raises `BadParameter("--clarify requires --interactive")`)

**Modify (tests):**
- `tests/_fixture_helpers.py:65` — Task 4 updates `extract_resume_id` regex from `r"thoth --resume\s+(...)"` → `r"thoth resume\s+(...)"`
- `tests/test_resume.py` lines 48, 90, 131 — Task 5 swaps `["--resume", op_id]` → `["resume", op_id]`
- `tests/test_pick_model.py` lines 48, 109 — Task 5 updates the `--pick-model --resume op_test_123` argv. Since the new subcommand surface no longer accepts `--pick-model resume op_test_123`, rewrite both tests to invoke `["--pick-model", "resume", "op_test_123"]` (positional first); `--pick-model` mutex check at cli.py:621 already covers `first in ctx.command.commands` because `resume` will be a registered subcommand → exit 2 with "only applies to research runs"
- `tests/test_cli_regressions.py:76` — Task 5 updates BUG-CLI-002 invocation from `["--resume", "op_regression"]` → `["resume", "op_regression"]`; Task 3 widens the `fake_resume` signature (line 68 `def fake_resume(operation_id, verbose, ctx=None):`) to `def fake_resume(operation_id, verbose=False, ctx=None, **kwargs):` to absorb new keyword args
- `tests/test_cli_regressions.py:164` — Task 5 updates `["--version", "--resume", "op_123", "--async"]` to a new shape that still triggers `--version must be used alone` mutex; e.g., `["--version", "--async"]` (preserves the contract; `--resume` no longer participates in the version-mutex list)
- `tests/test_cli_help.py:26` — Task 4 updates assertion `"thoth --resume" in out` → `"thoth resume" in out`
- `tests/test_progress_spinner.py:152` — Task 4 updates `"Resume later: thoth --resume op_abc123"` → `"Resume later: thoth resume op_abc123"`
- `tests/test_providers_subcommand.py:23-27` — Task 6 flips `test_old_form_deprecated_but_works` to assert `r.exit_code == 2` and `"(use 'thoth providers list')"` in stderr
- `tests/baselines/status_no_args.json` — Task 10 recaptures (exit_code: 1 → 2)
- `tests/test_p16_dispatch_parity.py` — Task 10 verifies the parity assertion for `status_no_args` does not hard-code `1`; if it does, update to read from the recaptured baseline only

**Modify (integration tests / docs):**
- `thoth_test` lines 2170, 2216, 2238 — Task 4 updates `r"...thoth --resume"` patterns
- `thoth_test` lines 2260, 2269, 2290–2297, 2307 — Task 6 updates `providers -- --models...` argv to `providers models...`
- `README.md` line 218 — Task 4 updates `thoth --resume research-…` example
- `README.md` lines 98, 224, 227, 230, 233, 234, 565, 572, 573, 574, 575 — Task 11 updates remaining `thoth providers --` references
- `CHANGELOG.md` — Task 11 adds `## [3.0.0]` section with `### Removed`, `### Added`, `### Changed`, `### Migration` subsections
- `PROJECTS.md` — Task 12 flips P16 PR2 from `[ ]` to `[x]` and checks off all 167 tasks

**Dead code to delete (across tasks):**
- `cli.py` — `--resume`/`-R` `@click.option(...)` at line 477 (Task 5)
- `cli.py` — `resume_id` keys in `_version_conflicts` option_labels (line 103) and in `_extract_fallback_options` value_options (lines 188–189) (Task 5)
- `cli.py` — `if opts.get("resume_id"):` branch in `_dispatch_click_fallback` lines 347–358 (Task 5)
- `cli.py` — async/resume mutex at lines 609–610 (Task 5; subsumed by the early-intercept gating)
- `cli.py` — `resume_id or` clause in pick-model predicate at line 621 (Task 5; replaced by `first in ctx.command.commands` matching the new `resume` subcommand)
- `providers.py` — lines 39–62 (legacy-flag dispatch in group callback) (Task 6)
- `providers.py` — `_legacy_warning`, `_run_legacy`, and the three hidden `providers_legacy_*_cmd` functions at lines 109–173 (Task 6)
- `modes.py` — `ModesGroup` class lines 14–28 (Task 7)
- `modes.py` — `_dispatch_default` and the five `modes_legacy_*` hidden commands lines 65–109 (Task 7)
- `modes.py` — bare-`modes` `if ctx.invoked_subcommand is None:` shortcut lines 44–49 (Task 7)
- `help.py` — `auth` hijack in `ThothGroup.parse_args` lines 51–54 (Task 8)
- `help.py` — `"completion"` from `ADMIN_COMMANDS` tuple line 20 (Task 8)
- `help_cmd.py` — `topic == "auth"` branch lines 25–28 (Task 8) and the trailing `, auth` in the "Available topics" listing at line 36

---

## Critical implementation rules (apply to every task)

1. **`LEFTHOOK=0` discipline.** Tasks 4–9 produce transitional `./thoth_test` states (the integration suite asserts on `thoth --resume` literal text and `providers -- --list` argv). For each of those tasks, the per-task gate documents exactly which manual checks (`just check`, file-targeted pytest) MUST pass before invoking `LEFTHOOK=0 git commit -m '...'`. **Task 12 (final commit) MUST go through the full hook set without bypass** per CLAUDE.md "Hook discipline".
2. **Click 8.x `protected_args` deprecation.** `cli.py::_click_remainder_args` (lines 74–81) and `help.py::ThothGroup.invoke` (lines 71–77) already wrap `protected_args` reads in narrow `warnings.catch_warnings()` suppression. Task 5's `--resume` early-intercept does NOT touch `ctx.protected_args` — it scans the raw `args` list parameter to `parse_args(ctx, args)` BEFORE delegating to `super().parse_args(...)`. No new `protected_args` usage is introduced in PR2.
3. **`ThothGroup.parse_args` is the only custom dispatch override added/modified in PR2.** Tasks 5 and 8 both touch this method. Task 5 adds the `--resume`/`-R` early-intercept; Task 8 removes the `--help auth` hijack. The end state is shown explicitly in Task 8's Step 8.4 code block; verify the file contents match before committing Task 8.
4. **Q3-PR2-C duplication contract.** `_research_options` is applied to both the cli group AND `ask`. Task 1 creates the helper AND applies it to the cli group as part of the same commit (otherwise the group regresses on group-level research flags). Task 2 applies it to `ask`.
5. **Q1-PR2-C `resume_operation` signature change.** Task 3 widens the function signature in `run.py:703` to accept `quiet`, `no_metadata`, `timeout_override`, `cli_api_keys` (and threads them through to providers via `ctx`). Verify via `grep -rn "resume_operation(" src/ tests/` during Step 3.0 that the only caller is the new `cli_subcommands/resume.py`. The PR1.5 caller in `cli.py::_dispatch_click_fallback` is removed in Task 5; for the duration of Tasks 3–4 there are TWO callers (the old + the new), and the old caller passes only `(operation_id, verbose, ctx=app_ctx)`. Use keyword-only defaults on the new args so the legacy two-positional call still works.
6. **`resume_operation` is async.** `run.py:703` is `async def resume_operation(...)`. The new `cli_subcommands/resume.py` callback must wrap with `_run_maybe_async(asyncio_safe_call(...))` matching the existing pattern in `cli.py:351-357`. Task 3 shows the exact wrap.
7. **Test category bundling per spec §9.2.** Each task lists which test categories (A through H) get added in that commit. Final PR2 gate (post-Task 12) MUST show pytest count ≥ baseline + ~95 PR2-new = ~407 and `./thoth_test -r` 63+ passing.
8. **No regressions in PR1's parity gate.** `tests/test_p16_dispatch_parity.py` (8 byte-stable + 7 structural tests) MUST stay green throughout. The only baseline that changes is `status_no_args.json` (Task 10) per Q5-A row 6. Any other parity test going red is a regression to be diagnosed BEFORE proceeding.
9. **Spec gap discovery (locked during planning):** `_VALID_LAYERS` in `config_cmd.py:20` is `("defaults", "user", "project", "env", "cli")` — five values. Task 10's `click.Choice(...)` uses this exact tuple, NOT the spec §13 placeholder list `["builtin", "user", "project", "merged"]`.

---

## Task 1: Add `_research_options` decorator helper and apply to the cli group

**Why first:** Q3-PR2-C requires that the same option stack appear on both the cli group AND on `ask`. Pulling the 15 `@click.option(...)` lines out of `cli.py` into a single decorator is a prerequisite for Task 2 (where `ask` reuses it). Applying the decorator to the cli group in the SAME commit ensures group behavior stays bit-identical.

**Files:**
- Create: `src/thoth/cli_subcommands/_options.py`
- Modify: `src/thoth/cli.py` — replace the 15 inline `@click.option(...)` decorators on the `@click.group(...)` block (lines 467–528) with `@_research_options`

- [ ] **Step 1.1: Create the decorator module**

Create `src/thoth/cli_subcommands/_options.py`:

```python
"""Shared `_research_options` decorator stack.

Per Q3-PR2-C of the P16 PR2 design, the 15-flag research-options surface is
applied identically to (a) the top-level `cli` group and (b) the `ask`
subcommand. This module is the single source of truth.

Order of decorators matters for `--help` rendering: the order below matches
the historical pre-PR2 order on `cli` so that `thoth --help` output is
byte-stable against the PR1.5 baseline.
"""

from __future__ import annotations

from collections.abc import Callable

import click

# Each entry is a (args, kwargs) pair for click.option(*args, **kwargs).
# Applied in REVERSE so the resulting --help order matches list order.
_RESEARCH_OPTIONS: list[tuple[tuple, dict]] = [
    (("--mode", "-m", "mode_opt"), {"help": "Research mode"}),
    (("--prompt", "-q", "prompt_opt"), {"help": "Research prompt"}),
    (("--prompt-file", "-F"), {"help": "Read prompt from file (use - for stdin)"}),
    (("--async", "-A", "async_mode"), {"is_flag": True, "help": "Submit and exit"}),
    (("--project", "-p"), {"help": "Project name"}),
    (("--output-dir", "-o"), {"help": "Override output directory"}),
    (
        ("--provider", "-P"),
        {
            "type": click.Choice(["openai", "perplexity", "mock"]),
            "help": "Single provider",
        },
    ),
    (
        ("--input-file",),
        {
            "help": (
                "Use the file at PATH as input for this mode. Use when feeding a "
                "non-thoth document, an older run, or a file from a different project."
            ),
        },
    ),
    (
        ("--auto",),
        {
            "is_flag": True,
            "help": (
                "Pick up the latest output from the previous mode in the same "
                "--project directory. The happy path for chaining modes."
            ),
        },
    ),
    (("--verbose", "-v"), {"is_flag": True, "help": "Enable debug output"}),
    (
        ("--api-key-openai",),
        {"help": "API key for OpenAI provider (not recommended; prefer env vars)"},
    ),
    (
        ("--api-key-perplexity",),
        {"help": "API key for Perplexity provider (not recommended; prefer env vars)"},
    ),
    (
        ("--api-key-mock",),
        {"help": "API key for Mock provider (not recommended; prefer env vars)"},
    ),
    (("--config", "-c", "config_path"), {"help": "Path to custom config file"}),
    (
        ("--combined",),
        {"is_flag": True, "help": "Generate combined report from multiple providers"},
    ),
    (("--quiet", "-Q"), {"is_flag": True, "help": "Minimal output during execution"}),
    (
        ("--no-metadata",),
        {
            "is_flag": True,
            "help": "Disable metadata headers and prompt section in output files",
        },
    ),
    (("--timeout", "-T"), {"type": float, "help": "Override request timeout in seconds"}),
    (("--interactive", "-i"), {"is_flag": True, "help": "Enter interactive prompt mode"}),
    (
        ("--clarify",),
        {"is_flag": True, "help": "Start interactive mode in Clarification Mode"},
    ),
    (
        ("--pick-model", "-M", "pick_model"),
        {
            "is_flag": True,
            "help": "Interactively pick a model (immediate modes only)",
        },
    ),
]


def _research_options(f: Callable) -> Callable:
    """Apply the full 15-flag research-options stack to a Click callback."""
    for args, kwargs in reversed(_RESEARCH_OPTIONS):
        f = click.option(*args, **kwargs)(f)
    return f


__all__ = ["_research_options"]
```

- [ ] **Step 1.2: Write a unit test for the decorator (Category A)**

Create `tests/test_p16_pr2_options_decorator.py`:

```python
"""P16 PR2 — _research_options decorator unit test."""

from __future__ import annotations

import click
from click.testing import CliRunner

from thoth.cli_subcommands._options import _research_options


def test_research_options_decorator_adds_all_15_research_flags():
    @click.command()
    @_research_options
    def victim(**kwargs):
        click.echo("ok")

    out = CliRunner().invoke(victim, ["--help"]).output
    # Spot-check 5 representative options from across the stack
    for opt in ("--mode", "--prompt-file", "--provider", "--api-key-openai", "--pick-model"):
        assert opt in out, f"expected {opt} in --help output, got: {out}"
```

Run: `uv run pytest tests/test_p16_pr2_options_decorator.py -v`
Expected: PASS (the decorator file is now importable and applies all options).

- [ ] **Step 1.3: Replace the 15 inline `@click.option` decorators on `cli.py`'s group with `@_research_options`**

In `src/thoth/cli.py`, locate the `@click.group(cls=ThothGroup, …)` block at line 467 and the 15 `@click.option(...)` decorators at lines 473–528 (note: `--version` / `-V` at line 502 is NOT a research option — keep it inline). Replace the 15 research options with one `@_research_options` call.

Add at the top of `cli.py`:

```python
from thoth.cli_subcommands._options import _research_options
```

Replace the decorator block (keep `--version` inline, keep `--resume`/`-R` for now — Task 5 removes it):

```python
@click.group(
    cls=ThothGroup,
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.pass_context
@_research_options
@click.option("--resume", "-R", "resume_id", help="Resume operation by ID")
@click.option("--version", "-V", is_flag=True, help="Show version and exit; must be used alone")
def cli(
    ctx,
    mode_opt,
    prompt_opt,
    prompt_file,
    async_mode,
    resume_id,
    project,
    output_dir,
    provider,
    input_file,
    auto,
    verbose,
    version,
    api_key_openai,
    api_key_perplexity,
    api_key_mock,
    config_path,
    combined,
    quiet,
    no_metadata,
    timeout,
    interactive,
    clarify,
    pick_model,
):
    """thoth — research orchestration.

    Quick usage: thoth "PROMPT"
    Run research:    thoth ask "question" | thoth deep_research "topic" | thoth -m MODE -q PROMPT
    Manage thoth:    thoth init | thoth status OP | thoth list | thoth config ... | thoth providers ...

    For per-command help: thoth COMMAND --help
    """
    # ... (function body unchanged from PR1.5 lines 564–624)
```

- [ ] **Step 1.4: Run the parity gate before commit**

```bash
uv run pytest tests/test_p16_pr2_options_decorator.py tests/test_p16_dispatch_parity.py tests/test_p16_thothgroup.py tests/test_cli_help.py -v
```
Expected: ALL PASS. The parity baselines for `--help` output should stay byte-identical because the decorator order matches the historical inline order.

If any baseline diff: re-check `_RESEARCH_OPTIONS` ordering vs `cli.py:473–528`. The reverse-application loop preserves declaration order in `--help`.

- [ ] **Step 1.5: Commit**

```bash
just check
git add src/thoth/cli_subcommands/_options.py src/thoth/cli.py tests/test_p16_pr2_options_decorator.py
git commit -m "feat(cli): add _research_options decorator helper (P16 PR2)"
```

Pre-commit hook runs full test suite — expected GREEN (no behavior change).

---

## Task 2: Add `ask` subcommand

**Why second:** `ask` is purely additive — it doesn't break anything, doesn't gate anything, and provides the modern entry point so subsequent tests can target the new form. Categories A (happy paths) and G (mutex) both ship in this commit.

**Files:**
- Create: `src/thoth/cli_subcommands/ask.py`
- Create: `tests/test_p16_pr2_ask.py`
- Modify: `src/thoth/cli.py` — add `cli.add_command(_ask_mod.ask)` registration

- [ ] **Step 2.1: Write failing tests first (Categories A + G)**

Create `tests/test_p16_pr2_ask.py`:

```python
"""P16 PR2 — `ask` subcommand tests (Categories A + G)."""

from __future__ import annotations

from click.testing import CliRunner

from thoth.cli import cli


def _stub_run_research(monkeypatch):
    captured: dict[str, object] = {}

    def fake(**kwargs):
        captured.update(kwargs)
        return None

    monkeypatch.setattr("thoth.run.run_research", fake)
    return captured


# Category A: ask happy paths

def test_ask_with_positional_prompt(monkeypatch):
    captured = _stub_run_research(monkeypatch)
    r = CliRunner().invoke(cli, ["ask", "how", "does", "DNS", "work"])
    assert r.exit_code == 0, r.output
    assert captured["mode"] == "default"
    assert captured["prompt"] == "how does DNS work"


def test_ask_with_explicit_mode(monkeypatch):
    captured = _stub_run_research(monkeypatch)
    r = CliRunner().invoke(cli, ["ask", "--mode", "deep_research", "topic"])
    assert r.exit_code == 0, r.output
    assert captured["mode"] == "deep_research"
    assert captured["prompt"] == "topic"


def test_ask_with_prompt_flag(monkeypatch):
    captured = _stub_run_research(monkeypatch)
    r = CliRunner().invoke(cli, ["ask", "--prompt", "via flag"])
    assert r.exit_code == 0, r.output
    assert captured["prompt"] == "via flag"


def test_ask_with_prompt_file(monkeypatch, tmp_path):
    captured = _stub_run_research(monkeypatch)
    pf = tmp_path / "p.txt"
    pf.write_text("file prompt content")
    r = CliRunner().invoke(cli, ["ask", "--prompt-file", str(pf)])
    assert r.exit_code == 0, r.output
    assert captured["prompt"] == "file prompt content"


def test_ask_via_group_level_flags(monkeypatch):
    """Q3-PR2-C: `thoth --mode X ask "..."` works (group form)."""
    captured = _stub_run_research(monkeypatch)
    r = CliRunner().invoke(cli, ["--mode", "deep_research", "ask", "topic"])
    assert r.exit_code == 0, r.output
    assert captured["mode"] == "deep_research"


def test_ask_subcommand_mode_wins_over_group_mode(monkeypatch):
    """Q3-PR2-C: subcommand value wins on conflict (Click natural)."""
    captured = _stub_run_research(monkeypatch)
    r = CliRunner().invoke(
        cli,
        ["--mode", "default", "ask", "--mode", "deep_research", "topic"],
    )
    assert r.exit_code == 0, r.output
    assert captured["mode"] == "deep_research"


# Category G: ask mutex tests

def test_ask_positional_and_prompt_flag_rejected(monkeypatch):
    _stub_run_research(monkeypatch)
    r = CliRunner().invoke(cli, ["ask", "positional", "--prompt", "flag"])
    assert r.exit_code == 2
    assert "positional" in r.output.lower() or "prompt" in r.output.lower()


def test_ask_positional_and_prompt_file_rejected(monkeypatch, tmp_path):
    _stub_run_research(monkeypatch)
    pf = tmp_path / "p.txt"
    pf.write_text("x")
    r = CliRunner().invoke(cli, ["ask", "positional", "--prompt-file", str(pf)])
    assert r.exit_code == 2


def test_ask_prompt_and_prompt_file_rejected(monkeypatch, tmp_path):
    _stub_run_research(monkeypatch)
    pf = tmp_path / "p.txt"
    pf.write_text("x")
    r = CliRunner().invoke(cli, ["ask", "--prompt", "p", "--prompt-file", str(pf)])
    assert r.exit_code == 2


def test_ask_no_prompt_at_all_rejected(monkeypatch):
    _stub_run_research(monkeypatch)
    r = CliRunner().invoke(cli, ["ask"])
    assert r.exit_code == 2
    assert "prompt" in r.output.lower()
```

Run: `uv run pytest tests/test_p16_pr2_ask.py -v`
Expected: ALL FAIL (no `ask` subcommand registered yet — Click reports "No such command 'ask'").

- [ ] **Step 2.2: Implement `ask.py`**

Create `src/thoth/cli_subcommands/ask.py`:

```python
"""`thoth ask "PROMPT"` Click subcommand.

Per Q7-PR2-B accepts `nargs=-1` positional arguments joined with single spaces.
Per Q3-PR2-C duplicates the full research-options stack via `_research_options`,
so both `thoth ask --mode X "..."` and `thoth --mode X ask "..."` work.
"""

from __future__ import annotations

import click

from thoth.cli_subcommands._options import _research_options


@click.command(name="ask")
@click.argument("prompt_args", nargs=-1)
@_research_options
@click.pass_context
def ask(
    ctx: click.Context,
    prompt_args: tuple[str, ...],
    mode_opt: str | None,
    prompt_opt: str | None,
    prompt_file: str | None,
    async_mode: bool,
    project: str | None,
    output_dir: str | None,
    provider: str | None,
    input_file: str | None,
    auto: bool,
    verbose: bool,
    api_key_openai: str | None,
    api_key_perplexity: str | None,
    api_key_mock: str | None,
    config_path: str | None,
    combined: bool,
    quiet: bool,
    no_metadata: bool,
    timeout: float | None,
    interactive: bool,
    clarify: bool,
    pick_model: bool,
) -> None:
    """Run a research operation with the given prompt."""
    positional = " ".join(prompt_args) if prompt_args else None

    # Q7-B + Q3-C mutex: positional vs --prompt vs --prompt-file
    if positional and prompt_opt:
        raise click.BadParameter(
            "Cannot use --prompt with positional prompt argument", param_hint="--prompt"
        )
    if positional and prompt_file:
        raise click.BadParameter(
            "Cannot use --prompt-file with positional prompt argument",
            param_hint="--prompt-file",
        )
    if prompt_opt and prompt_file:
        raise click.BadParameter("Cannot use --prompt-file with --prompt", param_hint="--prompt-file")
    if not (positional or prompt_opt or prompt_file):
        raise click.BadParameter(
            "Provide a prompt: positional, --prompt, or --prompt-file"
        )

    # Subcommand-level option wins over group-level (already true via Click)
    inherited = ctx.obj or {}

    def _pick(local, key):
        return local if local is not None and local is not False else inherited.get(key)

    effective_mode = _pick(mode_opt, "mode_opt") or "default"
    effective_provider = _pick(provider, "provider")
    effective_project = _pick(project, "project")
    effective_output_dir = _pick(output_dir, "output_dir")
    effective_input_file = _pick(input_file, "input_file")
    effective_async = bool(async_mode or inherited.get("async_mode"))
    effective_auto = bool(auto or inherited.get("auto"))
    effective_verbose = bool(verbose or inherited.get("verbose"))
    effective_combined = bool(combined or inherited.get("combined"))
    effective_quiet = bool(quiet or inherited.get("quiet"))
    effective_no_metadata = bool(no_metadata or inherited.get("no_metadata"))
    effective_timeout = _pick(timeout, "timeout")
    effective_config = _pick(config_path, "config_path")
    cli_api_keys = {
        "openai": _pick(api_key_openai, "api_key_openai"),
        "perplexity": _pick(api_key_perplexity, "api_key_perplexity"),
        "mock": _pick(api_key_mock, "api_key_mock"),
    }

    from thoth.cli import _read_prompt_input, _run_research_default, _apply_config_path
    from thoth.cli import _prompt_max_bytes

    _apply_config_path(effective_config)

    if prompt_file:
        effective_prompt = _read_prompt_input(str(prompt_file), _prompt_max_bytes())
    elif prompt_opt:
        effective_prompt = prompt_opt
    else:
        effective_prompt = positional or ""

    _run_research_default(
        mode=effective_mode,
        prompt=effective_prompt,
        async_mode=effective_async,
        project=effective_project,
        output_dir=effective_output_dir,
        provider=effective_provider,
        input_file=effective_input_file,
        auto=effective_auto,
        verbose=effective_verbose,
        cli_api_keys=cli_api_keys,
        combined=effective_combined,
        quiet=effective_quiet,
        no_metadata=effective_no_metadata,
        timeout_override=effective_timeout,
        model_override=None,
    )


__all__ = ["ask"]
```

- [ ] **Step 2.3: Register `ask` on the cli group**

In `src/thoth/cli.py`, after the existing `cli.add_command(_init_mod.init)` line (line 634), add the `ask` registration. Since `RUN_COMMANDS` order is `("ask", "resume", "status", "list")` per `help.py:14`, register `ask` first so the help renderer's two-section output places it at the top of the Run-research section:

```python
from thoth.cli_subcommands import ask as _ask_mod  # noqa: E402

cli.add_command(_ask_mod.ask)
```

Place this import block BEFORE `from thoth.cli_subcommands import init as _init_mod`.

- [ ] **Step 2.4: Run the failing tests — they should now pass**

```bash
uv run pytest tests/test_p16_pr2_ask.py -v
```
Expected: ALL PASS.

- [ ] **Step 2.5: Verify no regressions**

```bash
uv run pytest tests/test_p16_dispatch_parity.py tests/test_p16_thothgroup.py tests/test_cli_help.py tests/test_cli_regressions.py -v
just check
```

Expected: ALL PASS. `--help` output now lists `ask` in the Run-research section.

- [ ] **Step 2.6: Commit**

```bash
git add src/thoth/cli_subcommands/ask.py src/thoth/cli.py tests/test_p16_pr2_ask.py
git commit -m "feat(cli): add ask subcommand (P16 PR2)"
```

Pre-commit hook should pass.

---

## Task 3: Add `resume` subcommand and widen `resume_operation` signature

**Why third:** `resume` is purely additive at this point. The OLD `--resume` global flag still works (Task 5 removes it). Both code paths coexist for the duration of Tasks 3 and 4 — the new `resume` subcommand calls `resume_operation` with the widened honor-set; the old `--resume` flag calls it with `(operation_id, verbose, ctx=app_ctx)` only. Keyword-only defaults make both call sites work.

**Files:**
- Create: `src/thoth/cli_subcommands/resume.py`
- Create: `tests/test_p16_pr2_resume.py` (Category A + F; Category E follows in Task 5 once `--resume` is removed and the reject-list is enforceable on the subcommand)
- Modify: `src/thoth/run.py` — widen `resume_operation` signature
- Modify: `src/thoth/cli.py` — register `resume` subcommand

- [ ] **Step 3.0: Verify no other callers of `resume_operation`**

```bash
grep -rn "resume_operation(" src/ tests/
```

Expected: only `src/thoth/cli.py:351` (the OLD `--resume` flow), `src/thoth/run.py` (the def itself), and any test stubs. No other callers — confirms Task 3 + Task 5 sequencing is safe.

- [ ] **Step 3.1: Write failing tests first (Category A + F)**

Create `tests/test_p16_pr2_resume.py`:

```python
"""P16 PR2 — `resume` subcommand tests (Categories A + F)."""

from __future__ import annotations

from click.testing import CliRunner

from thoth.cli import cli


def _stub_resume(monkeypatch):
    captured: dict[str, object] = {}

    async def fake(operation_id, verbose=False, ctx=None, **kwargs):
        captured["operation_id"] = operation_id
        captured["verbose"] = verbose
        captured["ctx"] = ctx
        captured.update(kwargs)
        return None

    monkeypatch.setattr("thoth.run.resume_operation", fake)
    return captured


# Category A: resume happy paths

def test_resume_with_op_id(monkeypatch):
    captured = _stub_resume(monkeypatch)
    r = CliRunner().invoke(cli, ["resume", "op_test_001"])
    assert r.exit_code == 0, r.output
    assert captured["operation_id"] == "op_test_001"


def test_resume_missing_op_id_exits_2(monkeypatch):
    _stub_resume(monkeypatch)
    r = CliRunner().invoke(cli, ["resume"])
    assert r.exit_code == 2
    assert "OP_ID" in r.output or "argument" in r.output.lower()


# Category F: honor-list (each Q1-PR2-C honored option)

def test_resume_honors_verbose(monkeypatch):
    captured = _stub_resume(monkeypatch)
    r = CliRunner().invoke(cli, ["resume", "op_x", "--verbose"])
    assert r.exit_code == 0, r.output
    assert captured["verbose"] is True


def test_resume_honors_quiet(monkeypatch):
    captured = _stub_resume(monkeypatch)
    r = CliRunner().invoke(cli, ["resume", "op_x", "--quiet"])
    assert r.exit_code == 0, r.output
    assert captured.get("quiet") is True


def test_resume_honors_no_metadata(monkeypatch):
    captured = _stub_resume(monkeypatch)
    r = CliRunner().invoke(cli, ["resume", "op_x", "--no-metadata"])
    assert r.exit_code == 0, r.output
    assert captured.get("no_metadata") is True


def test_resume_honors_timeout(monkeypatch):
    captured = _stub_resume(monkeypatch)
    r = CliRunner().invoke(cli, ["resume", "op_x", "--timeout", "60.5"])
    assert r.exit_code == 0, r.output
    assert captured.get("timeout_override") == 60.5


def test_resume_honors_api_key_openai(monkeypatch):
    captured = _stub_resume(monkeypatch)
    r = CliRunner().invoke(cli, ["resume", "op_x", "--api-key-openai", "sk-test"])
    assert r.exit_code == 0, r.output
    assert captured.get("cli_api_keys", {}).get("openai") == "sk-test"


def test_resume_honors_api_key_perplexity(monkeypatch):
    captured = _stub_resume(monkeypatch)
    r = CliRunner().invoke(cli, ["resume", "op_x", "--api-key-perplexity", "pplx-test"])
    assert r.exit_code == 0, r.output
    assert captured.get("cli_api_keys", {}).get("perplexity") == "pplx-test"


def test_resume_honors_api_key_mock(monkeypatch):
    captured = _stub_resume(monkeypatch)
    r = CliRunner().invoke(cli, ["resume", "op_x", "--api-key-mock", "mock-test"])
    assert r.exit_code == 0, r.output
    assert captured.get("cli_api_keys", {}).get("mock") == "mock-test"


def test_resume_honors_config_path(monkeypatch, tmp_path):
    captured = _stub_resume(monkeypatch)
    cfg = tmp_path / "thoth.toml"
    cfg.write_text("version = \"2.0\"\n")
    r = CliRunner().invoke(cli, ["resume", "op_x", "--config", str(cfg)])
    assert r.exit_code == 0, r.output
    # config_path is applied via _apply_config_path; verify call still completes
    assert captured["operation_id"] == "op_x"
```

Run: `uv run pytest tests/test_p16_pr2_resume.py -v`
Expected: ALL FAIL (no `resume` subcommand registered yet).

- [ ] **Step 3.2: Widen `resume_operation` signature**

In `src/thoth/run.py`, modify the `resume_operation` definition starting at line 703. Add keyword-only defaulted parameters per Q1-PR2-C:

```python
async def resume_operation(
    operation_id: str,
    verbose: bool = False,
    ctx: AppContext | None = None,
    *,
    quiet: bool = False,
    no_metadata: bool = False,
    timeout_override: float | None = None,
    cli_api_keys: dict[str, str | None] | None = None,
):
    """Resume an existing operation by reconnecting to its providers.

    Honor-set per Q1-PR2-C: the resume subcommand passes `quiet`,
    `no_metadata`, `timeout_override`, and `cli_api_keys` as keyword
    arguments. The legacy `--resume` flag callsite (cli.py until Task 5)
    passes only the first three positional args; keyword-only defaults
    keep both callsites valid during the transition window.
    """
    config = get_config()
    if ctx is None:
        ctx = AppContext(config=config, verbose=verbose)
    # Thread the new honor-set onto the AppContext so downstream providers
    # can consume them via the existing context plumbing. (No body changes
    # to the polling loop — providers already read these from ctx/config.)
    ctx.quiet = quiet
    ctx.no_metadata = no_metadata
    if timeout_override is not None:
        ctx.timeout_override = timeout_override
    if cli_api_keys:
        ctx.cli_api_keys = cli_api_keys
    # ... (rest of body unchanged from current run.py:710 onwards)
```

Note: only the signature + the four `ctx.*` assignment lines are added. The polling-loop body, the existing `console = ctx.console`, the `checkpoint_manager.load(...)` call, and all subsequent logic stay byte-identical.

- [ ] **Step 3.3: Verify the legacy `--resume` callsite still works**

The OLD callsite is `cli.py:352-357`:

```python
_run_maybe_async(
    _thoth_run.resume_operation(
        str(opts["resume_id"]),
        bool(opts.get("verbose")),
        ctx=app_ctx,
    )
)
```

This passes only `(operation_id, verbose, ctx)`. The new signature has those three as the first three params with `verbose` and `ctx` defaulted, and the new keyword-only params all default to safe values. ✓ Still works for the duration of Tasks 3–4.

- [ ] **Step 3.4: Update the existing test stub for the wider signature**

In `tests/test_cli_regressions.py:65-81`, update the `fake_resume` stub at line 68 to absorb new keyword args:

```python
def fake_resume(operation_id, verbose=False, ctx=None, **kwargs):
    captured["operation_id"] = operation_id
    captured["verbose"] = verbose
    captured["ctx"] = ctx
    return 0
```

This change is a same-commit edit; `test_bug_cli_002_resume_option_invokes_resume` continues to pass against the OLD `--resume` flag (still present until Task 5).

- [ ] **Step 3.5: Implement `resume.py`**

Create `src/thoth/cli_subcommands/resume.py`:

```python
"""`thoth resume OP_ID` Click subcommand.

Per Q1-PR2-C (Tight + Honor) accepts a focused set of options:
  --verbose / -v
  --config / -c PATH
  --quiet / -Q
  --no-metadata
  --timeout / -T SECS
  --api-key-{openai,perplexity,mock} VALUE

All other globals are naturally rejected by Click (they are not declared
on this subcommand). Mutex-violating combos (e.g., --auto, --pick-model,
--prompt) are likewise rejected as "no such option" by Click natively.
"""

from __future__ import annotations

import click


@click.command(name="resume")
@click.argument("operation_id", metavar="OP_ID")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug output")
@click.option("--config", "-c", "config_path", help="Path to custom config file")
@click.option("--quiet", "-Q", is_flag=True, help="Minimal output during execution")
@click.option(
    "--no-metadata",
    is_flag=True,
    help="Disable metadata headers and prompt section in output files",
)
@click.option("--timeout", "-T", type=float, help="Override request timeout in seconds")
@click.option("--api-key-openai", help="API key for OpenAI provider")
@click.option("--api-key-perplexity", help="API key for Perplexity provider")
@click.option("--api-key-mock", help="API key for Mock provider")
@click.pass_context
def resume(
    ctx: click.Context,
    operation_id: str,
    verbose: bool,
    config_path: str | None,
    quiet: bool,
    no_metadata: bool,
    timeout: float | None,
    api_key_openai: str | None,
    api_key_perplexity: str | None,
    api_key_mock: str | None,
) -> None:
    """Resume a previously-checkpointed operation by ID."""
    import thoth.run as _thoth_run
    from thoth.cli import _apply_config_path, _build_app_context, _run_maybe_async

    # Group-level inheritance for the four honored values per Q1-PR2-C
    inherited = ctx.obj or {}
    effective_verbose = bool(verbose or inherited.get("verbose"))
    effective_quiet = bool(quiet or inherited.get("quiet"))
    effective_no_metadata = bool(no_metadata or inherited.get("no_metadata"))
    effective_timeout = timeout if timeout is not None else inherited.get("timeout")
    effective_config = config_path or inherited.get("config_path")
    cli_api_keys = {
        "openai": api_key_openai or inherited.get("api_key_openai"),
        "perplexity": api_key_perplexity or inherited.get("api_key_perplexity"),
        "mock": api_key_mock or inherited.get("api_key_mock"),
    }

    _apply_config_path(effective_config)
    app_ctx = _build_app_context(effective_verbose)
    _run_maybe_async(
        _thoth_run.resume_operation(
            operation_id,
            effective_verbose,
            ctx=app_ctx,
            quiet=effective_quiet,
            no_metadata=effective_no_metadata,
            timeout_override=effective_timeout,
            cli_api_keys=cli_api_keys,
        )
    )


__all__ = ["resume"]
```

- [ ] **Step 3.6: Register `resume` on the cli group**

In `src/thoth/cli.py`, after the `ask` registration added in Task 2:

```python
from thoth.cli_subcommands import resume as _resume_mod  # noqa: E402

cli.add_command(_resume_mod.resume)
```

- [ ] **Step 3.7: Run the failing tests — they should now pass**

```bash
uv run pytest tests/test_p16_pr2_resume.py -v
uv run pytest tests/test_cli_regressions.py::test_bug_cli_002_resume_option_invokes_resume -v
```
Expected: ALL PASS. The legacy `--resume` flag test continues to pass via the widened `fake_resume` stub.

- [ ] **Step 3.8: Run the full file-level pytest gate**

```bash
uv run pytest tests/test_p16_pr2_resume.py tests/test_resume.py tests/test_pick_model.py tests/test_cli_regressions.py -v
just check
```
Expected: PASS. (The `tests/test_resume.py` cases still use `["--resume", op_id]` — they continue to pass because the old flag is still wired.)

- [ ] **Step 3.9: Commit**

```bash
git add src/thoth/cli_subcommands/resume.py src/thoth/cli.py src/thoth/run.py tests/test_p16_pr2_resume.py tests/test_cli_regressions.py
git commit -m "feat(cli): add resume subcommand (P16 PR2)"
```

Pre-commit hook expected GREEN — no behavior change to existing forms.

---

## Task 4: Update `--resume` emitter strings to `thoth resume`

**Why fourth:** Once both subcommands exist (Tasks 2 + 3), every help/hint string referencing `thoth --resume` should print the new canonical form. Doing this BEFORE removing the legacy flag (Task 5) means the new emitter strings are live but still copy-paste compatible with the legacy flag — users who hit the new hint mid-Task-4 still get a working command. Task 5 then enforces.

**Files:**
- Modify: `src/thoth/run.py` lines 629, 654, 827, 854 (4 emitters)
- Modify: `src/thoth/signals.py` lines 93, 99 (2 emitters)
- Modify: `src/thoth/commands.py` lines 227, 238 (2 print_hint emitters)
- Modify: `src/thoth/help.py` line 134 (epilog example)
- Modify: `src/thoth/providers/openai.py` line 69 (legacy hint string)
- Modify: `tests/_fixture_helpers.py:65` (regex)
- Modify: `tests/test_cli_help.py:26` (assertion)
- Modify: `tests/test_progress_spinner.py:152` (assertion)
- Modify: `thoth_test` lines 2170, 2216, 2238 (regex patterns)
- Modify: `README.md` line 218 (one of several refs; remaining `providers --` refs land in Task 11)

- [ ] **Step 4.1: Update `run.py` emitters (4 sites)**

In `src/thoth/run.py`, change the four occurrences of `Resume with: [bold]thoth --resume {operation.id}[/bold]` to `Resume with: [bold]thoth resume {operation.id}[/bold]` at lines 629, 654, 827, 854.

- [ ] **Step 4.2: Update `signals.py` emitters (2 sites)**

In `src/thoth/signals.py`:
- Line 93: `f"[green]✓[/green] Checkpoint saved. Resume with: thoth --resume {_current_operation.id}"` → `f"[green]✓[/green] Checkpoint saved. Resume with: thoth resume {_current_operation.id}"`
- Line 99: `f"\nResume later: thoth --resume {_current_operation.id}"` → `f"\nResume later: thoth resume {_current_operation.id}"`

- [ ] **Step 4.3: Update `commands.py` emitters (2 sites)**

In `src/thoth/commands.py`:
- Line 227: `print_hint(f"thoth --resume {op_id}", "Pick up where Ctrl-C left off")` → `print_hint(f"thoth resume {op_id}", "Pick up where Ctrl-C left off")`
- Line 238: `print_hint(f"thoth --resume {op_id}", "Retry from checkpoint")` → `print_hint(f"thoth resume {op_id}", "Retry from checkpoint")`

- [ ] **Step 4.4: Update `help.py` epilog example**

In `src/thoth/help.py:134`, change:
```python
formatter.write_text("thoth --resume op_abc123")
```
to:
```python
formatter.write_text("thoth resume op_abc123")
```

- [ ] **Step 4.5: Update `providers/openai.py` legacy hint**

In `src/thoth/providers/openai.py:68-69`:
```python
f"Model '{model}' not found. Please check available models with "
f"'thoth providers -- --models --provider openai'",
```
to:
```python
f"Model '{model}' not found. Please check available models with "
f"'thoth providers models --provider openai'",
```

- [ ] **Step 4.6: Update test regex + assertions (Category H test migrations)**

In `tests/_fixture_helpers.py:65`:
```python
match = re.search(r"thoth --resume\s+(research-\d{8}-\d{6}-[a-f0-9]{16})", output)
```
to:
```python
match = re.search(r"thoth resume\s+(research-\d{8}-\d{6}-[a-f0-9]{16})", output)
```

In `tests/test_cli_help.py:26`:
```python
assert "thoth --resume" in out
```
to:
```python
assert "thoth resume" in out
```

In `tests/test_progress_spinner.py:152`:
```python
assert "Resume later: thoth --resume op_abc123" in output
```
to:
```python
assert "Resume later: thoth resume op_abc123" in output
```

- [ ] **Step 4.7: Update `thoth_test` patterns (3 sites)**

Read `thoth_test` around lines 2170, 2216, 2238 to confirm exact pattern strings, then update:
- Line ~2170: `r"Checkpoint saved\. Resume with: thoth --resume"` → `r"Checkpoint saved\. Resume with: thoth resume"`
- Line ~2216: `r"Resume with: .*thoth --resume"` → `r"Resume with: .*thoth resume"`
- Line ~2238: same pattern (negative assertion for permanent-failure case)

- [ ] **Step 4.8: Update README example at line 218**

In `README.md:218`:
```
thoth --resume research-20240803-143022-a1b2c3d4e5f6g7h8
```
to:
```
thoth resume research-20240803-143022-a1b2c3d4e5f6g7h8
```

(Other `providers --` references in README are batched into Task 11.)

- [ ] **Step 4.9: Run the file-level test gate**

```bash
uv run pytest tests/test_progress_spinner.py tests/test_cli_help.py -v
uv run pytest tests/test_p16_dispatch_parity.py -v
just check
```

Expected:
- `test_progress_spinner.py` PASS (uses new string).
- `test_cli_help.py` PASS (uses new string).
- `test_p16_dispatch_parity.py` may FAIL on the `help.json` baseline because the epilog example changed at help.py:134. If so, manually verify the diff is ONLY `--resume` → `resume`, then recapture the baseline:

```bash
THOTH_TEST_MODE=1 uv run python -c "from tests.baselines import capture_baselines as c; print(c.capture('help', ['--help']))" > /tmp/new_help.json
# Confirm only the resume example line changed, then:
mv /tmp/new_help.json tests/baselines/help.json
```

(If `tests/baselines/capture_baselines.py` was deleted in PR1's Task 15, recapture by running the live binary: `thoth --help > /tmp/help.txt`, then update the JSON's `stdout` field manually with the new content.)

- [ ] **Step 4.10: Run thoth_test for the affected cases**

```bash
./thoth_test -r --provider mock --skip-interactive -q -t TR-02
./thoth_test -r --provider mock --skip-interactive -q -t TR-03
./thoth_test -r --provider mock --skip-interactive -q -t TS-09
```

Expected: PASS (patterns match new emitter strings).

- [ ] **Step 4.11: Commit**

```bash
git add src/thoth/run.py src/thoth/signals.py src/thoth/commands.py src/thoth/help.py src/thoth/providers/openai.py tests/_fixture_helpers.py tests/test_cli_help.py tests/test_progress_spinner.py tests/baselines/help.json thoth_test README.md
git commit -m "refactor(cli): update --resume emitter strings to thoth resume (P16 PR2)"
```

`LEFTHOOK=0` is **NOT** needed here — the legacy `--resume` flag is still wired (Task 5 removes it), so all existing tests using `["--resume", op_id]` keep passing. Pre-commit hook should be GREEN.

---

## Task 5: Remove `--resume` global flag, gate legacy form

**Why fifth:** With the new `resume` subcommand live and all hint strings updated, removing the legacy flag is now the safe transition. This task adds the early-intercept gating in `ThothGroup.parse_args` AND deletes the option declaration + dispatch path in `cli.py`. Categories E (reject-list on the new subcommand) and B (gating on the old flag) are introduced here, and Category H test migrations land in the same commit.

**Files:**
- Modify: `src/thoth/help.py` — add `--resume`/`-R` early-intercept to `ThothGroup.parse_args`
- Modify: `src/thoth/cli.py` — remove the `--resume`/`-R` `@click.option(...)` declaration; remove `resume_id` from `_version_conflicts.option_labels`; remove `--resume`/`-R`/`resume_id` from `_extract_fallback_options.value_options`; remove the `if opts.get("resume_id"):` block in `_dispatch_click_fallback`; remove `--async`/`--resume` mutex at lines 609–610; remove `resume_id or` clause from pick-model predicate at line 621; drop `resume_id` from the function signature + the `ctx.obj["resume_id"]` assignment
- Create test additions in `tests/test_p16_pr2_gating.py` (Category B for `--resume`)
- Append Category E to `tests/test_p16_pr2_resume.py`
- Modify: `tests/test_resume.py` lines 48, 90, 131
- Modify: `tests/test_pick_model.py` lines 48, 109
- Modify: `tests/test_cli_regressions.py` lines 76, 164

- [ ] **Step 5.1: Write failing tests first (Categories B + E)**

Create `tests/test_p16_pr2_gating.py` (the parametrized gating-tests file used by Tasks 5–8):

```python
"""P16 PR2 — Category B: legacy-form gating tests.

Each removed form must exit 2 with a Click-native error containing the
`(use 'thoth NEW_FORM')` migration substring on stderr per Q6-PR2-C1.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from thoth.cli import cli


@pytest.mark.parametrize(
    "argv,migration_hint",
    [
        # --resume / -R global flag (removed in Task 5)
        (["--resume", "op_x"], "thoth resume"),
        (["-R", "op_x"], "thoth resume"),
    ],
)
def test_resume_legacy_form_gated(argv, migration_hint):
    r = CliRunner(mix_stderr=False).invoke(cli, argv)
    assert r.exit_code == 2, f"expected exit 2, got {r.exit_code}\nstdout={r.output!r}\nstderr={r.stderr!r}"
    combined = (r.output or "") + (r.stderr or "")
    assert migration_hint in combined, (
        f"expected migration hint {migration_hint!r} in output, got {combined!r}"
    )
```

Append to `tests/test_p16_pr2_resume.py` (Category E — reject-list on the new subcommand):

```python
# Category E: reject-list — undeclared flags are rejected by Click natively

@pytest.mark.parametrize(
    "rejected_arg",
    [
        "--auto",
        "--input-file=x.txt",
        "--prompt=foo",
        "--prompt-file=foo.txt",
        "--combined",
        "--project=p",
        "--output-dir=o",
        "--async",
        "--pick-model",
        "--interactive",
        "--clarify",
    ],
)
def test_resume_rejects_undeclared_option(monkeypatch, rejected_arg):
    _stub_resume(monkeypatch)
    r = CliRunner().invoke(cli, ["resume", "op_x", rejected_arg])
    assert r.exit_code == 2, r.output
    assert "no such option" in r.output.lower() or "unexpected" in r.output.lower()
```

(Imports — at the top of `tests/test_p16_pr2_resume.py` add `import pytest`.)

Run: `uv run pytest tests/test_p16_pr2_gating.py tests/test_p16_pr2_resume.py -v`
Expected: gating tests FAIL (the legacy `--resume` flag still works); reject-list tests likely PASS already (Click natively rejects undeclared options on `resume`).

- [ ] **Step 5.2: Add `--resume` early-intercept to `ThothGroup.parse_args`**

In `src/thoth/help.py`, modify `ThothGroup.parse_args` (lines 51–55):

```python
def parse_args(self, ctx: click.Context, args: list[str]):
    # Q6-PR2-C1: legacy --resume / -R flag is gated to the new subcommand.
    # Scan the raw argv BEFORE delegating to super().parse_args so we can
    # emit a Click-native error with the migration hint on stderr.
    for token in args:
        if token in ("--resume", "-R") or token.startswith("--resume="):
            ctx.fail(
                "no such option: --resume (use 'thoth resume OP_ID')"
            )
    # Existing --help auth hijack stays for now; Task 8 removes it.
    if len(args) == 2 and args[0] in ("--help", "-h") and args[1] == "auth":
        show_auth_help()
        ctx.exit(0)
    return super().parse_args(ctx, args)
```

Note: `ctx.fail(...)` raises `click.UsageError`, which Click catches and prints to stderr with the standard `Usage: ...\nError: ...` triplet, then exits 2. This matches Q6-A1 (stderr) + Q6-B3 (Click-native triplet).

- [ ] **Step 5.3: Remove `--resume` declaration and dispatch from `cli.py`**

In `src/thoth/cli.py`:

(a) Delete line 477:
```python
@click.option("--resume", "-R", "resume_id", help="Resume operation by ID")
```

(b) Remove `resume_id,` from the `def cli(...)` signature (line 535).

(c) Delete the `ctx.obj["resume_id"] = resume_id` assignment (line 570).

(d) In `_version_conflicts` (line 103), delete the `"resume_id": "--resume",` mapping entry.

(e) In `_extract_fallback_options.value_options` (lines 188–189), delete:
```python
"--resume": "resume_id",
"-R": "resume_id",
```

(f) Delete the `if opts.get("resume_id"):` block in `_dispatch_click_fallback` (lines 347–358):
```python
if opts.get("resume_id"):
    if args:
        raise click.BadParameter("Cannot use --resume with a research prompt")
    app_ctx = _build_app_context(bool(opts.get("verbose")))
    _run_maybe_async(
        _thoth_run.resume_operation(
            str(opts["resume_id"]),
            bool(opts.get("verbose")),
            ctx=app_ctx,
        )
    )
    return
```

(g) Delete the `--async`/`--resume` mutex at lines 609–610:
```python
if async_mode and resume_id:
    raise click.BadParameter("Cannot use --async with --resume")
```

(h) In the pick-model predicate at line 621, change:
```python
if resume_id or interactive or (first in ctx.command.commands if first else False):
```
to:
```python
if interactive or (first in ctx.command.commands if first else False):
```

The new `resume` subcommand is registered, so `first == "resume"` is captured by the `first in ctx.command.commands` clause naturally. The pick-model + resume rejection still triggers, just via the different code path (this is what `tests/test_pick_model.py:48` verifies after the migration in Step 5.5).

- [ ] **Step 5.4: Migrate `tests/test_resume.py` (Category H)**

Update three invocations:
- Line 48: `["--resume", op_id]` → `["resume", op_id]`
- Line 90: `["--resume", op_id]` → `["resume", op_id]`
- Line 131: `["--resume", op_id]` → `["resume", op_id]`

These tests now exercise the new subcommand path; the asserted exit codes (0 / 7 / 0) and stdout substrings (`"Research completed"` / `"failed permanently"` / `"already completed"`) all still hold because `resume_operation` is unchanged in body.

- [ ] **Step 5.5: Migrate `tests/test_pick_model.py` (Category H)**

Update line 48:
```python
r = CliRunner().invoke(cli, ["--pick-model", "--resume", "op_test_123"])
```
to:
```python
r = CliRunner().invoke(cli, ["--pick-model", "resume", "op_test_123"])
```

Update line 109 (inside the parametrized loop):
```python
["--pick-model", "--resume", "op_test_123"],
```
to:
```python
["--pick-model", "resume", "op_test_123"],
```

Both still trigger the pick-model rejection because `"resume"` is a registered subcommand and matches the `first in ctx.command.commands` predicate at cli.py:621.

- [ ] **Step 5.6: Migrate `tests/test_cli_regressions.py` (Category H)**

Line 76:
```python
result = CliRunner().invoke(cli, ["--resume", "op_regression"])
```
to:
```python
result = CliRunner().invoke(cli, ["resume", "op_regression"])
```

Line 164 (`test_bug_10_version_must_be_used_alone`):
```python
result = CliRunner().invoke(cli, ["--version", "--resume", "op_123", "--async"])
```
to:
```python
result = CliRunner().invoke(cli, ["--version", "--async"])
```

The `--version must be used alone` mutex still triggers because `--async` is in the option_labels list. The contract under test (exit ≠ 0 + "must be used alone" message) holds.

- [ ] **Step 5.7: Run the per-task gate**

```bash
uv run pytest tests/test_p16_pr2_gating.py tests/test_p16_pr2_resume.py tests/test_resume.py tests/test_pick_model.py tests/test_cli_regressions.py -v
just check
```

Expected: ALL PASS. The legacy `--resume` flag is now gated; `tests/test_resume.py` uses the new subcommand; `--pick-model + resume` still rejects via the subcommand-name predicate.

- [ ] **Step 5.8: Run the integration suite for the resume cases**

```bash
./thoth_test -r --provider mock --skip-interactive -q -t TR-02
./thoth_test -r --provider mock --skip-interactive -q -t TR-03
./thoth_test -r --provider mock --skip-interactive -q -t TS-09
```

Expected: PASS — these were already updated in Task 4 to expect the new `thoth resume` text in emitter output, and the new subcommand is now the path that produces that text.

- [ ] **Step 5.9: Commit**

```bash
git add src/thoth/help.py src/thoth/cli.py tests/test_p16_pr2_gating.py tests/test_p16_pr2_resume.py tests/test_resume.py tests/test_pick_model.py tests/test_cli_regressions.py
git commit -m "refactor(cli): remove --resume global flag, gate legacy form (P16 PR2)"
```

`LEFTHOOK=0` is **NOT** needed if the per-task gate (Step 5.7 + 5.8) is GREEN. If the pre-commit hook fails on a thoth_test case not in the targeted list, run the full quiet suite first to identify it: `./thoth_test -r --provider mock --skip-interactive -q`.

---

## Task 6: Remove providers legacy shim, gate legacy forms, add `--refresh-cache + --no-cache` mutex

**Why sixth:** With `--resume` removed, the next surface is the providers shim. This task removes ~90 LOC from `cli_subcommands/providers.py` (the legacy-flags branch in the group callback + three hidden subcommands), adds Q6-C1 gating for every removed form, adds `--refresh-cache` and `--no-cache` as real options on the new `providers models` leaf with mutex (Q5-A row 1).

**Files:**
- Modify: `src/thoth/cli_subcommands/providers.py` — remove the legacy-flag dispatch in the group callback (lines 39–62 partial); remove `_legacy_warning`, `_run_legacy`, and the three hidden `providers_legacy_*_cmd` functions (lines 109–173); add Q6-C1 gating in the group callback; add `--refresh-cache` and `--no-cache` options to `providers_models_cmd` with mutex
- Modify: `tests/test_providers_subcommand.py:23-27` — flip `test_old_form_deprecated_but_works` to expect exit 2 + migration hint
- Append to `tests/test_p16_pr2_gating.py` — providers gating cases
- Append to `tests/test_p16_pr2_cleanup.py` (new file) — Q5-A row 1 mutex test
- Modify: `thoth_test` lines 2260, 2269, 2290–2297, 2307 — migrate argv

- [ ] **Step 6.1: Write failing gating tests (Category B)**

Append to `tests/test_p16_pr2_gating.py`:

```python
@pytest.mark.parametrize(
    "argv,migration_hint",
    [
        # providers `--` separator form
        (["providers", "--", "--list"], "thoth providers list"),
        (["providers", "--", "--models"], "thoth providers models"),
        (["providers", "--", "--keys"], "thoth providers check"),
        (["providers", "--", "--refresh-cache"], "thoth providers models --refresh-cache"),
        (["providers", "--", "--no-cache"], "thoth providers models --no-cache"),
        # providers in-group hidden flag form (PR1.5 shim)
        (["providers", "--list"], "thoth providers list"),
        (["providers", "--models"], "thoth providers models"),
        (["providers", "--keys"], "thoth providers check"),
        (["providers", "--check"], "thoth providers check"),
    ],
)
def test_providers_legacy_form_gated(argv, migration_hint):
    r = CliRunner(mix_stderr=False).invoke(cli, argv)
    assert r.exit_code == 2, f"expected exit 2, got {r.exit_code}\nstdout={r.output!r}\nstderr={r.stderr!r}"
    combined = (r.output or "") + (r.stderr or "")
    assert migration_hint in combined, (
        f"expected migration hint {migration_hint!r} in output, got {combined!r}"
    )
```

Create `tests/test_p16_pr2_cleanup.py` with the row-1 mutex test (Category C):

```python
"""P16 PR2 — Category C: Q5-A cleanup-batch tests."""

from __future__ import annotations

from click.testing import CliRunner

from thoth.cli import cli


def test_providers_models_refresh_and_no_cache_mutex():
    """Q5-A row 1: --refresh-cache and --no-cache are mutually exclusive."""
    r = CliRunner(mix_stderr=False).invoke(
        cli, ["providers", "models", "--refresh-cache", "--no-cache"]
    )
    assert r.exit_code == 2, r.output
    combined = (r.output or "") + (r.stderr or "")
    assert "mutually exclusive" in combined.lower() or "cannot use" in combined.lower()
```

Run: `uv run pytest tests/test_p16_pr2_gating.py tests/test_p16_pr2_cleanup.py -v`
Expected: providers gating tests FAIL (legacy shim still active); mutex test FAIL (no flags on new leaf yet).

- [ ] **Step 6.2: Rewrite `providers.py` with gating and the mutex**

Replace the body of `src/thoth/cli_subcommands/providers.py` with:

```python
"""`thoth providers` Click subgroup with leaves: list, models, check.

PR2 removes the legacy `providers --` separator shim AND the in-group
`--list/--models/--keys/--check/--refresh-cache/--no-cache` hidden
subcommands per Q6-PR2-C1. Every removed form is gated to its new
canonical via a `ctx.fail(...)` Click-native error.
"""

from __future__ import annotations

import sys

import click

from thoth.config import get_config

PROVIDER_CHOICES = ("openai", "perplexity", "mock")

_LEGACY_FLAG_TO_NEW_FORM: dict[str, str] = {
    "--list": "thoth providers list",
    "--models": "thoth providers models",
    "--keys": "thoth providers check",
    "--check": "thoth providers check",
    "--refresh-cache": "thoth providers models --refresh-cache",
    "--no-cache": "thoth providers models --no-cache",
}


@click.group(
    name="providers",
    invoke_without_command=True,
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
)
@click.pass_context
def providers(ctx: click.Context) -> None:
    """Manage provider models and API keys."""
    if ctx.invoked_subcommand is not None:
        return

    args = list(ctx.args)
    # Q6-C1: scan for any legacy flag and gate to its canonical replacement.
    for token in args:
        flag = token.split("=", 1)[0]  # handle --provider=mock too
        if flag in _LEGACY_FLAG_TO_NEW_FORM:
            new_form = _LEGACY_FLAG_TO_NEW_FORM[flag]
            ctx.fail(
                f"no such option: {flag} (use '{new_form}')"
            )

    if args:
        click.echo(f"Unknown providers arguments: {' '.join(args)}", err=True)
        ctx.exit(2)

    # Q5-A row 4: bare `thoth providers` exits 2 (Click default for required subgroup).
    click.echo(ctx.get_help())
    ctx.exit(2)


@providers.command(name="list")
@click.option(
    "--provider",
    "-P",
    "filter_provider",
    type=click.Choice(PROVIDER_CHOICES),
    help="Filter by provider",
)
@click.pass_context
def providers_list_cmd(ctx: click.Context, filter_provider: str | None) -> None:
    """List available providers."""
    from thoth import commands as _commands

    cfg = get_config()
    sys.exit(_commands.providers_list(cfg, filter_provider=filter_provider))


@providers.command(name="models")
@click.option(
    "--provider",
    "-P",
    "filter_provider",
    type=click.Choice(PROVIDER_CHOICES),
    help="Filter by provider",
)
@click.option("--refresh-cache", is_flag=True, help="Force-refresh the model cache")
@click.option("--no-cache", is_flag=True, help="Bypass the model cache for this call")
@click.pass_context
def providers_models_cmd(
    ctx: click.Context,
    filter_provider: str | None,
    refresh_cache: bool,
    no_cache: bool,
) -> None:
    """List provider models."""
    # Q5-A row 1: --refresh-cache and --no-cache are mutually exclusive.
    if refresh_cache and no_cache:
        raise click.BadParameter(
            "--refresh-cache and --no-cache are mutually exclusive",
            param_hint="--refresh-cache / --no-cache",
        )
    from thoth import commands as _commands

    cfg = get_config()
    sys.exit(
        _commands.providers_models(
            cfg,
            filter_provider=filter_provider,
            refresh_cache=refresh_cache,
            no_cache=no_cache,
        )
    )


@providers.command(name="check")
@click.pass_context
def providers_check_cmd(ctx: click.Context) -> None:
    """Check provider API key configuration."""
    from thoth import commands as _commands

    cfg = get_config()
    sys.exit(_commands.providers_check(cfg))
```

Note: `commands.providers_models` already accepts `refresh_cache` and `no_cache` per `commands.py:444-456` analysis from the audit; the function signature change is from the call site forwarding those kwargs.

- [ ] **Step 6.3: Verify `providers_models` signature accepts the kwargs**

```bash
grep -n "def providers_models" /Users/stevemorin/c/thoth/src/thoth/commands.py
```

If the existing `providers_models` does NOT accept `refresh_cache` and `no_cache` (the current signature may only accept `filter_provider`), add them as keyword args defaulting to `False`, and forward to the underlying `providers_command(show_models=True, ...)` call. Read the function around line 530–550 first to confirm the exact change needed.

If the signature already accepts those kwargs (PR1 may have added them), no commands.py change is needed.

- [ ] **Step 6.4: Flip `test_old_form_deprecated_but_works` test (Category H)**

In `tests/test_providers_subcommand.py:23-27`, replace the test:

```python
def test_old_form_gated_with_migration_hint():
    r = CliRunner(mix_stderr=False).invoke(cli, ["providers", "--", "--list"])
    assert r.exit_code == 2
    combined = (r.output or "") + (r.stderr or "")
    assert "thoth providers list" in combined
```

(Rename the function from `test_old_form_deprecated_but_works` → `test_old_form_gated_with_migration_hint` to reflect the flipped contract.)

- [ ] **Step 6.5: Migrate thoth_test cases T-PROV-07/08/10 + P07-M2-01 (Category H)**

In `thoth_test`:
- Line ~2260 (T-PROV-07): `providers -- --models --provider mock` → `providers models --provider mock`
- Line ~2269 (T-PROV-08): `providers -- --models` → `providers models`
- Line ~2290–2297 (T-PROV-10): `providers -- --models --provider invalid` → `providers models --provider invalid`. Confirm the new path still exits 1 with the expected `"Unknown provider"` stderr — `commands.providers_models` calls into `providers_command` which has the `sys.exit(1)` at commands.py:354.
- Line ~2307 (P07-M2-01): `providers -- --list` → `providers list`. Confirm the Perplexity-row text `r"Perplexity search AI \(not.*implemented\)"` still renders.

Read the relevant `thoth_test` lines first to capture the exact patterns before editing.

- [ ] **Step 6.6: Run the per-task gate**

```bash
uv run pytest tests/test_p16_pr2_gating.py tests/test_p16_pr2_cleanup.py tests/test_providers_subcommand.py -v
just check
./thoth_test -r --provider mock --skip-interactive -q -t T-PROV
./thoth_test -r --provider mock --skip-interactive -q -t P07-M2-01
```

Expected: ALL PASS. Note: `T-PROV-06` asserts the bare `thoth providers` help output mentions `--list|--models|list|models` — verify that pattern still matches the new help epilog (the `epilog` field can be removed from the `@click.group(name="providers", ...)` decoration; if the `T-PROV-06` regex needs adjustment, update it to match what the new help renders).

- [ ] **Step 6.7: Commit**

```bash
git add src/thoth/cli_subcommands/providers.py tests/test_providers_subcommand.py tests/test_p16_pr2_gating.py tests/test_p16_pr2_cleanup.py thoth_test
git commit -m "refactor(cli/providers): remove legacy shim + gate (P16 PR2)"
```

If commands.py was edited in Step 6.3, include it in the `git add` line.

`LEFTHOOK=0` is **NOT** needed if the per-task gate is GREEN. If pre-commit fails on a P07 test not in the targeted list, run the full quiet suite to identify before bypassing.

---

## Task 7: Remove modes flag-style shim, gate legacy forms, add `--name + --source` intersection (Q5-A row 11.i), enforce `--clarify` requires `--interactive` (Q5-A row 7)

**Why seventh:** Modes shim removal mirrors the providers approach. Plus this task picks up two cleanup-batch rows that touch nearby code: `--name + --source` intersection in `modes_cmd.py` (row 11.i) and `--clarify`-without-`--interactive` rejection in `cli.py` (row 7).

**Files:**
- Modify: `src/thoth/cli_subcommands/modes.py` — remove `ModesGroup` class entirely; remove the `if ctx.invoked_subcommand is None` shortcut; remove the five hidden `modes_legacy_*` commands; add Q6-C1 gating in the group callback for the five flags
- Modify: `src/thoth/modes_cmd.py:243-261` — remove the `return 0` after the detail render so `--source` filter is honored when `--name` matches; pass both `name` and `source` to the filter logic
- Modify: `src/thoth/cli.py` — add `--clarify` requires `--interactive` rejection in the cli group callback (Q5-A row 7)
- Append to `tests/test_p16_pr2_gating.py` — modes gating cases
- Append to `tests/test_p16_pr2_cleanup.py` — Q5-A row 11.i (intersection), row 7 (--clarify alone)

- [ ] **Step 7.1: Write failing tests first (Categories B + C)**

Append to `tests/test_p16_pr2_gating.py`:

```python
@pytest.mark.parametrize(
    "argv,migration_hint",
    [
        (["modes", "--json"], "thoth modes list --json"),
        (["modes", "--show-secrets"], "thoth modes list --show-secrets"),
        (["modes", "--full"], "thoth modes list --full"),
        (["modes", "--name", "deep_research"], "thoth modes list --name"),
        (["modes", "--source", "user"], "thoth modes list --source"),
    ],
)
def test_modes_legacy_form_gated(argv, migration_hint):
    r = CliRunner(mix_stderr=False).invoke(cli, argv)
    assert r.exit_code == 2, f"expected exit 2, got {r.exit_code}\noutput={r.output!r}"
    combined = (r.output or "") + (r.stderr or "")
    assert migration_hint in combined, f"hint {migration_hint!r} not in output {combined!r}"
```

Append to `tests/test_p16_pr2_cleanup.py`:

```python
def test_modes_no_leaf_exits_2(isolated_thoth_home):
    """Q5-A row 5: bare `thoth modes` exits 2 (no leaf default)."""
    r = CliRunner().invoke(cli, ["modes"])
    assert r.exit_code == 2, r.output


def test_modes_list_name_and_source_intersect(isolated_thoth_home):
    """Q5-A row 11.i: --name X --source Y applies BOTH filters."""
    # When the named mode does not match the requested source, return empty
    # detail (exit 0; no error). Picking a builtin mode + source=user is the
    # cleanest demonstration that source filter still applies after name match.
    r = CliRunner().invoke(
        cli, ["modes", "list", "--name", "deep_research", "--source", "user"]
    )
    # Today (pre-fix) this would render the deep_research detail unconditionally;
    # post-fix it should produce empty / no-match output, exit 0.
    assert r.exit_code == 0, r.output


def test_clarify_alone_rejected():
    """Q5-A row 7: --clarify without --interactive → exit 2."""
    r = CliRunner(mix_stderr=False).invoke(cli, ["--clarify"])
    assert r.exit_code == 2, r.output
    combined = (r.output or "") + (r.stderr or "")
    assert "--interactive" in combined or "interactive" in combined.lower()
```

The `isolated_thoth_home` fixture comes from the existing `conftest.py`.

Run: `uv run pytest tests/test_p16_pr2_gating.py tests/test_p16_pr2_cleanup.py -v`
Expected: modes gating tests FAIL (`ModesGroup` still routes); cleanup tests FAIL.

- [ ] **Step 7.2: Rewrite `modes.py` with gating, no-leaf exit-2, no shim**

Replace the body of `src/thoth/cli_subcommands/modes.py` with:

```python
"""`thoth modes` Click subgroup. PR2 ships `list` only.

PR2 removes the PR1.5 `ModesGroup` unknown-arg dispatcher, the
bare-`modes` shortcut, and the five hidden `--json/--show-secrets/
--full/--name/--source` legacy commands per Q2-PR2-A. Each removed
flag is gated to its `thoth modes list <flag>` canonical via Q6-C1.

P12 will add `add`, `set`, `unset` leaves here.
"""

from __future__ import annotations

import sys

import click

_PASSTHROUGH_CONTEXT = {"ignore_unknown_options": True, "allow_extra_args": True}

_LEGACY_FLAG_TO_NEW_FORM: dict[str, str] = {
    "--json": "thoth modes list --json",
    "--show-secrets": "thoth modes list --show-secrets",
    "--full": "thoth modes list --full",
    "--name": "thoth modes list --name",
    "--source": "thoth modes list --source",
}


@click.group(
    name="modes",
    invoke_without_command=True,
    context_settings=_PASSTHROUGH_CONTEXT,
)
@click.pass_context
def modes(ctx: click.Context) -> None:
    """List research modes with provider/model/kind."""
    if ctx.invoked_subcommand is not None:
        return

    args = list(ctx.args)
    # Q6-C1: gate every removed flag to its `modes list` canonical.
    for token in args:
        flag = token.split("=", 1)[0]
        if flag in _LEGACY_FLAG_TO_NEW_FORM:
            ctx.fail(f"no such option: {flag} (use '{_LEGACY_FLAG_TO_NEW_FORM[flag]}')")

    # Q5-A row 5: bare `thoth modes` (or unknown-arg) exits 2.
    if args:
        click.echo(f"Unknown modes arguments: {' '.join(args)}", err=True)
        ctx.exit(2)
    click.echo(ctx.get_help())
    ctx.exit(2)


@modes.command(name="list", context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def modes_list(args: tuple[str, ...]) -> None:
    """List research modes."""
    from thoth.modes_cmd import modes_command

    rc = modes_command("list", list(args))
    sys.exit(rc)
```

- [ ] **Step 7.3: Make `--name + --source` intersect in `modes_cmd.py`**

In `src/thoth/modes_cmd.py`, modify `_op_list` starting at line 234. The current behavior (lines 243–261) is:

```python
if name is not None:
    match = next((m for m in infos if m.name == name), None)
    if match is None:
        _get_console().print(f"[red]Error:[/red] unknown mode: {name}")
        return 1
    if as_json:
        print(...)
    else:
        _render_detail(match, full, show_secrets)
    return 0  # ← Q5-A row 11.i: this early return drops --source filter
```

Change to apply `source` filter BEFORE the name match:

```python
if source != "all":
    infos = [m for m in infos if m.source == source]

if name is not None:
    match = next((m for m in infos if m.name == name), None)
    if match is None:
        # Empty result is exit 0 per Q5-A row 11.i (intersection, not error)
        if as_json:
            print(json.dumps({"schema_version": "1", "mode": None}, indent=2, sort_keys=True))
        return 0
    if as_json:
        print(
            json.dumps(
                {"schema_version": "1", "mode": _info_to_dict(match, show_secrets)},
                indent=2,
                sort_keys=True,
            )
        )
    else:
        _render_detail(match, full, show_secrets)
    return 0

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

(Remove the duplicate `if source != "all":` block at the original line 263, since it's now applied earlier.)

- [ ] **Step 7.4: Add `--clarify` requires `--interactive` rejection (Q5-A row 7)**

In `src/thoth/cli.py`, in the `def cli(...)` callback body, after the existing `--input-file`/`--auto` mutex check at lines 615–616, add:

```python
if clarify and not interactive:
    raise click.BadParameter(
        "--clarify requires --interactive",
        param_hint="--clarify",
    )
```

This raises before `_dispatch_click_fallback` runs, so `--clarify` alone exits 2 before any research dispatch.

- [ ] **Step 7.5: Run the per-task gate**

```bash
uv run pytest tests/test_p16_pr2_gating.py tests/test_p16_pr2_cleanup.py tests/test_p16_thothgroup.py tests/test_cli_regressions.py -v
just check
```

Expected: PASS. Note: `tests/test_p16_thothgroup.py:223` previously asserted bare-`modes` lists modes — that assertion will need updating to expect exit 2 + help text. If the test exists in that form, update it in this same commit.

- [ ] **Step 7.6: Run thoth_test for the modes case**

```bash
./thoth_test -r --provider mock --skip-interactive -q -t M
```

Expected: PASS. The `M8T-…` and modes-related cases use `modes list` directly (verified via `grep`); the `thoth modes bogus_op` test at thoth_test:2128 will see Click's default `"No such command 'bogus_op'"` error instead of `"unknown modes op"` — update the pattern in `thoth_test` to `r"No such command|unknown.*op"` (regex alternation accepts both).

- [ ] **Step 7.7: Commit**

```bash
git add src/thoth/cli_subcommands/modes.py src/thoth/modes_cmd.py src/thoth/cli.py tests/test_p16_pr2_gating.py tests/test_p16_pr2_cleanup.py tests/test_p16_thothgroup.py thoth_test
git commit -m "refactor(cli/modes): remove flag-style shim + gate (P16 PR2)"
```

`LEFTHOOK=0` is **NOT** needed if Step 7.5 + 7.6 are GREEN. If pre-commit hits an unrelated thoth_test failure, diagnose with `./thoth_test -r --last-failed -q` first.

---

## Task 8: Drop `--help <topic>` parse-time hijack (Q5-A row 13.ii) + remove `completion` from `ADMIN_COMMANDS`

**Why eighth:** Tasks 5–7 added gating for runtime forms. The remaining shim is the parse-time `--help auth` hijack in `ThothGroup.parse_args` (lines 51–54 in PR1.5; Task 5 already added the `--resume` early-intercept above it). Drop it now so `parse_args` ends up with ONLY the `--resume` early-intercept.

**Files:**
- Modify: `src/thoth/help.py` — remove the `--help auth` hijack from `ThothGroup.parse_args`; remove `"completion"` from `ADMIN_COMMANDS`
- Modify: `src/thoth/cli_subcommands/help_cmd.py` — remove the `topic == "auth"` virtual-topic branch; remove `, auth` from the "Available topics" listing
- Append to `tests/test_p16_pr2_gating.py` — `--help <topic>` is now a Click "unexpected argument" error

- [ ] **Step 8.1: Write failing tests first (Category B)**

Append to `tests/test_p16_pr2_gating.py`:

```python
def test_help_auth_parse_time_hijack_removed():
    """Q5-A row 13.ii: `thoth --help auth` is no longer hijacked at parse time."""
    r = CliRunner(mix_stderr=False).invoke(cli, ["--help", "auth"])
    # Click natively rejects 'auth' as an unexpected positional argument.
    assert r.exit_code == 2, r.output
    combined = (r.output or "") + (r.stderr or "")
    assert (
        "unexpected" in combined.lower()
        or "no such command" in combined.lower()
        or "got" in combined.lower()
    )


def test_help_subcommand_topic_still_works():
    """`thoth help status` still forwards to `thoth status --help`."""
    r = CliRunner().invoke(cli, ["help", "status"])
    assert r.exit_code == 0, r.output
    assert "OP_ID" in r.output or "status" in r.output.lower()


def test_help_auth_topic_via_help_subcommand_removed():
    """The `auth` virtual topic on `thoth help auth` is also dropped per Q5-A row 13.ii."""
    r = CliRunner(mix_stderr=False).invoke(cli, ["help", "auth"])
    assert r.exit_code == 2, r.output
    combined = (r.output or "") + (r.stderr or "")
    assert "unknown help topic" in combined.lower() or "available topics" in combined.lower()
```

Run: `uv run pytest tests/test_p16_pr2_gating.py -k "help_auth or help_subcommand_topic" -v`
Expected: FAIL on the parse-time hijack test (still hijacked); the others may pass or fail depending on current state.

- [ ] **Step 8.2: Drop `--help auth` hijack from `parse_args`**

In `src/thoth/help.py`, modify `ThothGroup.parse_args` to ONLY contain the `--resume` early-intercept added by Task 5. Final state:

```python
def parse_args(self, ctx: click.Context, args: list[str]):
    # Q6-PR2-C1: legacy --resume / -R flag is gated to the new subcommand.
    for token in args:
        if token in ("--resume", "-R") or token.startswith("--resume="):
            ctx.fail("no such option: --resume (use 'thoth resume OP_ID')")
    return super().parse_args(ctx, args)
```

(The 4-line `if len(args) == 2 and args[0] in ("--help", "-h") and args[1] == "auth":` block is gone.)

- [ ] **Step 8.3: Remove `completion` from `ADMIN_COMMANDS`**

In `src/thoth/help.py:15-22`:

```python
ADMIN_COMMANDS: tuple[str, ...] = (
    "init",
    "config",
    "modes",
    "providers",
    "completion",   # ← remove this line
    "help",
)
```

Becomes:

```python
ADMIN_COMMANDS: tuple[str, ...] = (
    "init",
    "config",
    "modes",
    "providers",
    "help",
)
```

PR3 will re-add `completion` when the real subcommand lands.

- [ ] **Step 8.4: Drop `auth` virtual topic from `help_cmd.py`**

In `src/thoth/cli_subcommands/help_cmd.py`, remove lines 25–28:

```python
if topic == "auth":
    from thoth.help import show_auth_help

    show_auth_help()
    return
```

In line 36, remove the `, auth` suffix:

```python
click.echo(
    f"Available topics: {', '.join(sorted(parent_group.commands.keys()))}, auth", err=True
)
```

becomes:

```python
click.echo(
    f"Available topics: {', '.join(sorted(parent_group.commands.keys()))}", err=True
)
```

Note: `show_auth_help()` and the `render_auth_help()` function in `help.py:174-188` STAY — they may be invoked from PR3's `auth` real subcommand or from documentation generators. Only the parse-time hijack and the help-leaf shortcut are removed.

- [ ] **Step 8.5: Update `test_bug_01_auth_help_interception_is_root_only` (Category H)**

In `tests/test_cli_regressions.py:119-124`:

```python
def test_bug_01_auth_help_interception_is_root_only() -> None:
    result = CliRunner().invoke(cli, ["init", "--help", "auth"])

    assert result.exit_code == 0, result.output
    assert "Authentication" not in result.output
    assert "Initialize thoth configuration" in result.output
```

This test originally verified that `init --help auth` did NOT trigger the parse-time hijack (the hijack was guarded to top-level only). With the hijack now removed entirely, the test name is outdated but the assertion still holds — `["init", "--help", "auth"]` produces `init`'s --help with `auth` as an extra positional that Click's `--help` consumption-then-exit ignores. Verify this still passes; if not, update the test to assert the post-removal Click-natural behavior.

- [ ] **Step 8.6: Run the per-task gate**

```bash
uv run pytest tests/test_p16_pr2_gating.py tests/test_p16_thothgroup.py tests/test_cli_help.py tests/test_cli_regressions.py tests/test_p16_dispatch_parity.py -v
just check
```

Expected: ALL PASS. The `help_auth.json` baseline in `tests/baselines/` (captured in PR1's Task 1) may need recapture if its content changed — verify and recapture if needed (`thoth help auth` now exits 2; the baseline previously expected exit 0 with the auth-help text).

- [ ] **Step 8.7: Commit**

```bash
git add src/thoth/help.py src/thoth/cli_subcommands/help_cmd.py tests/test_p16_pr2_gating.py tests/test_cli_regressions.py tests/baselines/help_auth.json
git commit -m "refactor(cli): drop --help <topic> hijack (P16 PR2)"
```

`LEFTHOOK=0` is **NOT** needed — this commit is small, surface-isolated, and fully tested by the per-task gate.

---

## Task 9: Split `--raw` and `--show-secrets` (Q4-PR2-D)

**Why ninth:** This is the security-adjacent split. Currently `--raw` BOTH controls formatting AND bypasses secret masking (`config_cmd.py:104`). Split: `--raw` → formatting only; `--show-secrets` → masking bypass. The `--raw` data-source-merge behavior at `config_cmd.py:90-95` is PRESERVED (Q4-D only addresses masking).

**Files:**
- Modify: `src/thoth/cli_subcommands/config.py` — promote `get` from passthrough to a typed Click command with `--show-secrets`, `--raw`, `--json`, `--layer` options. (Other leaves stay passthrough; that's a PR3 concern.)
- Modify: `src/thoth/config_cmd.py:104` — change masking predicate to `not show_secrets` only
- Create: `tests/test_p16_pr2_config_secrets.py` — Category D security matrix

- [ ] **Step 9.1: Write failing tests first (Category D)**

Create `tests/test_p16_pr2_config_secrets.py`:

```python
"""P16 PR2 — Category D: --raw × --show-secrets security matrix (Q4-PR2-D)."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from thoth.cli import cli


@pytest.fixture
def secret_config(isolated_thoth_home, monkeypatch):
    """Set a known secret value via env-layer override."""
    fake_key = "sk-" + "FAKE-VALUE-FOR-TESTS-ONLY"  # noqa: S105 — test fixture
    monkeypatch.setenv("OPENAI_API_KEY", fake_key)
    return fake_key


# --raw alone — masks (NEW behavior post-Q4-D)
def test_get_secret_raw_masks(secret_config):
    r = CliRunner().invoke(
        cli, ["config", "get", "providers.openai.api_key", "--raw"]
    )
    assert r.exit_code == 0, r.output
    assert secret_config not in r.output
    assert "REDACTED" in r.output or "***" in r.output or "sk-***" in r.output


# --show-secrets alone — reveals
def test_get_secret_show_secrets_reveals(secret_config):
    r = CliRunner().invoke(
        cli, ["config", "get", "providers.openai.api_key", "--show-secrets"]
    )
    assert r.exit_code == 0, r.output
    assert secret_config in r.output


# --raw + --show-secrets — reveals
def test_get_secret_raw_and_show_secrets_reveals(secret_config):
    r = CliRunner().invoke(
        cli,
        ["config", "get", "providers.openai.api_key", "--raw", "--show-secrets"],
    )
    assert r.exit_code == 0, r.output
    assert secret_config in r.output


# Neither flag — masks
def test_get_secret_no_flags_masks(secret_config):
    r = CliRunner().invoke(cli, ["config", "get", "providers.openai.api_key"])
    assert r.exit_code == 0, r.output
    assert secret_config not in r.output


# Non-secret + --raw — still works (formatting flag)
def test_get_non_secret_with_raw(isolated_thoth_home):
    r = CliRunner().invoke(cli, ["config", "get", "general.default_mode", "--raw"])
    assert r.exit_code == 0, r.output
    assert r.output.strip() == "default"


# Non-secret + --show-secrets — works (no-op for non-secrets)
def test_get_non_secret_with_show_secrets(isolated_thoth_home):
    r = CliRunner().invoke(
        cli, ["config", "get", "general.default_mode", "--show-secrets"]
    )
    assert r.exit_code == 0, r.output
    assert "default" in r.output


# --json + secret + no --show-secrets — masks
def test_get_secret_json_masks(secret_config):
    r = CliRunner().invoke(
        cli, ["config", "get", "providers.openai.api_key", "--json"]
    )
    assert r.exit_code == 0, r.output
    assert secret_config not in r.output


# --json + secret + --show-secrets — reveals
def test_get_secret_json_show_secrets_reveals(secret_config):
    r = CliRunner().invoke(
        cli,
        ["config", "get", "providers.openai.api_key", "--json", "--show-secrets"],
    )
    assert r.exit_code == 0, r.output
    assert secret_config in r.output
```

Run: `uv run pytest tests/test_p16_pr2_config_secrets.py -v`
Expected: `test_get_secret_raw_masks` FAILS (current behavior: `--raw` reveals); others may pass or fail depending on current behavior.

- [ ] **Step 9.2: Promote `config get` to a typed Click command**

In `src/thoth/cli_subcommands/config.py`, replace the passthrough `config_get`:

```python
@config.command(name="get", context_settings=_PASSTHROUGH_CONTEXT)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def config_get(args: tuple[str, ...]) -> None:
    """Get a configuration value."""
    _dispatch("get", args)
```

with a typed version:

```python
@config.command(name="get")
@click.argument("key")
@click.option(
    "--layer",
    "layer",
    type=click.Choice(("defaults", "user", "project", "env", "cli")),
    default=None,
    help="Read from a specific config layer",
)
@click.option(
    "--raw",
    is_flag=True,
    help="Read pre-merge layer data (formatting only; does NOT bypass masking)",
)
@click.option("--json", "as_json", is_flag=True, help="Emit JSON")
@click.option(
    "--show-secrets",
    is_flag=True,
    help="Reveal masked secret values (security-sensitive)",
)
def config_get(key: str, layer: str | None, raw: bool, as_json: bool, show_secrets: bool) -> None:
    """Get a configuration value."""
    rebuilt: list[str] = [key]
    if layer is not None:
        rebuilt.extend(["--layer", layer])
    if raw:
        rebuilt.append("--raw")
    if as_json:
        rebuilt.append("--json")
    if show_secrets:
        rebuilt.append("--show-secrets")
    _dispatch("get", tuple(rebuilt))
```

Note: we still delegate to `config_command(op, list(args))` so the existing parser in `config_cmd.py::_op_get` does the heavy lifting. The new typed Click options serve as the validation layer (Q5-A row 8 — invalid `--layer` values fail at Click choice validation, not silently inside `_op_get`).

- [ ] **Step 9.3: Modify `config_cmd.py:104` masking predicate**

In `src/thoth/config_cmd.py:104`:

```python
if _is_secret_key(key) and not show_secrets and not raw:
    value = _mask_secret(value)
```

becomes:

```python
if _is_secret_key(key) and not show_secrets:
    value = _mask_secret(value)
```

The `elif raw:` data-source-merge branch at lines 90–95 is **PRESERVED unchanged** (Q4-D only addresses masking semantics, not data-source semantics).

- [ ] **Step 9.4: Run the per-task gate**

```bash
uv run pytest tests/test_p16_pr2_config_secrets.py tests/test_cli_regressions.py -v
just check
```

Expected: ALL PASS, including `test_bug_cli_004_config_passthrough_flags_and_help` at `tests/test_cli_regressions.py:101` (which uses `["config", "get", "general.default_mode", "--raw"]` and expects exit 0 + `"default"` output — both still hold; the test exercises `--raw` on a non-secret).

- [ ] **Step 9.5: Commit**

```bash
git add src/thoth/cli_subcommands/config.py src/thoth/config_cmd.py tests/test_p16_pr2_config_secrets.py
git commit -m "refactor(cli/config): split --raw and --show-secrets (P16 PR2)"
```

`LEFTHOOK=0` is **NOT** needed.

---

## Task 10: Apply remaining Q5-A cleanup batch rows

**Why tenth:** Tasks 6, 7, 9 already covered rows 1, 5, 7, 11.i, 13.ii. The remaining rows are:
- Row 4: bare `thoth providers` no leaf → exit 2 (already in Task 6)
- Row 6: `thoth status` no arg → exit 2 (currently exit 1; baseline recapture needed)
- Row 8: `config get --layer L` invalid → exit 2 (covered by Task 9's `click.Choice`)

This task focuses on row 6 (status) plus baseline recapture, plus a final cleanup-batch test sweep to confirm everything covered.

**Files:**
- Modify: `src/thoth/cli_subcommands/status.py:18` — change `ctx.exit(1)` to `ctx.exit(2)`
- Modify: `tests/baselines/status_no_args.json` — recapture (`exit_code: 1` → `exit_code: 2`; `stderr` may also change to a Click-native message if Step 10.1 routes through Click)
- Append to `tests/test_p16_pr2_cleanup.py` — row 6, row 8 tests
- Modify: `tests/test_p16_dispatch_parity.py` — verify the parity test for `status_no_args` reads `exit_code` from the baseline file (not hard-coded `1`)

- [ ] **Step 10.1: Write failing tests first (Category C)**

Append to `tests/test_p16_pr2_cleanup.py`:

```python
def test_status_no_arg_exits_2():
    """Q5-A row 6: bare `thoth status` exits 2 (Click default for missing required arg)."""
    r = CliRunner().invoke(cli, ["status"])
    assert r.exit_code == 2, r.output


def test_config_get_invalid_layer_exits_2(isolated_thoth_home):
    """Q5-A row 8: `config get KEY --layer NOPE` exits 2 via Click choice validation."""
    r = CliRunner(mix_stderr=False).invoke(
        cli, ["config", "get", "general.default_mode", "--layer", "NOPE"]
    )
    assert r.exit_code == 2, r.output
    combined = (r.output or "") + (r.stderr or "")
    assert "invalid value" in combined.lower() or "choose from" in combined.lower()


def test_providers_no_leaf_exits_2():
    """Q5-A row 4: bare `thoth providers` exits 2 (no-leaf default)."""
    r = CliRunner().invoke(cli, ["providers"])
    assert r.exit_code == 2, r.output
```

Run: `uv run pytest tests/test_p16_pr2_cleanup.py -v -k "status_no_arg or invalid_layer or providers_no_leaf"`
Expected: status test FAILS (currently exit 1), invalid_layer test PASSES (Task 9's typed Click option), providers_no_leaf test PASSES (Task 6's `ctx.exit(2)`).

- [ ] **Step 10.2: Update `status.py` to exit 2**

In `src/thoth/cli_subcommands/status.py:14-18`:

```python
def status(ctx: click.Context, operation_id: str | None) -> None:
    """Check status of a research operation by ID."""
    if operation_id is None:
        click.echo("Error: status command requires an operation ID")
        ctx.exit(1)
```

becomes:

```python
def status(ctx: click.Context, operation_id: str | None) -> None:
    """Check status of a research operation by ID."""
    if operation_id is None:
        click.echo("Error: status command requires an operation ID", err=True)
        ctx.exit(2)
```

(Also routes the message to stderr per Q6-A1.)

- [ ] **Step 10.3: Recapture `tests/baselines/status_no_args.json`**

Either run the live binary and edit the JSON manually, or use the in-tree capture helper if still present. Manual approach:

```bash
THOTH_TEST_MODE=1 thoth status > /tmp/status_no_args.stdout 2> /tmp/status_no_args.stderr; echo "EXIT=$?"
```

Then update `tests/baselines/status_no_args.json` to:

```json
{
  "argv": ["status"],
  "exit_code": 2,
  "label": "status_no_args",
  "stderr": "Error: status command requires an operation ID\n",
  "stdout": ""
}
```

(Verify the exact stderr text matches what the binary emits.)

- [ ] **Step 10.4: Verify the parity test does not hard-code exit 1**

Read `tests/test_p16_dispatch_parity.py` to find the parity assertion for `status_no_args`. It should read `exit_code` from the baseline JSON, not hard-code a value. If it hard-codes `assert r.exit_code == 1`, update to `assert r.exit_code == baseline_data["exit_code"]`. If the test already reads from the baseline, no change needed.

```bash
grep -n "status_no_args\|status.*exit" /Users/stevemorin/c/thoth/tests/test_p16_dispatch_parity.py
```

- [ ] **Step 10.5: Run the per-task gate**

```bash
uv run pytest tests/test_p16_pr2_cleanup.py tests/test_p16_dispatch_parity.py tests/test_cli_regressions.py -v
just check
```

Expected: ALL PASS.

- [ ] **Step 10.6: Commit**

```bash
git add src/thoth/cli_subcommands/status.py tests/baselines/status_no_args.json tests/test_p16_pr2_cleanup.py tests/test_p16_dispatch_parity.py
git commit -m "refactor(cli): apply Q5-A cleanup batch (P16 PR2)"
```

`LEFTHOOK=0` is **NOT** needed.

---

## Task 11: v3.0.0 CHANGELOG + README updates

**Why eleventh:** Code is done. Documentation sweep is the final user-facing deliverable before the PROJECTS.md tick.

**Files:**
- Modify: `CHANGELOG.md` — add `## [3.0.0]` section
- Modify: `README.md` — sweep all remaining `thoth providers --` and `thoth --resume` references not already updated (lines 98, 224, 227, 230, 233, 234, 565, 572, 573, 574, 575)

- [ ] **Step 11.1: Write the v3.0.0 CHANGELOG entry**

In `CHANGELOG.md`, add at the top (above any existing v2.x entries):

```markdown
## [3.0.0] — 2026-04-XX

### Removed (BREAKING)

- The `--resume` / `-R` global flag is removed. Use `thoth resume OP_ID` instead.
- The `thoth providers -- --list` / `--models` / `--keys` / `--check` / `--refresh-cache` / `--no-cache` legacy `--`-separator forms are removed. Use `thoth providers list|models|check` instead.
- The `thoth providers --list` / `--models` / `--keys` / `--check` in-group flag forms (PR1.5 hidden subcommands) are removed. Same migration as above.
- The `thoth modes --json` / `--show-secrets` / `--full` / `--name X` / `--source X` flag-style forms are removed. Use `thoth modes list <flag>` instead.
- The `thoth --help <topic>` parse-time hijack is removed. Use `thoth help <topic>` (or `thoth <topic> --help` for real subcommands).
- The `auth` virtual help topic on `thoth help auth` is removed.
- `completion` was removed from the help renderer's command listing (it was a phantom — never registered as a real subcommand).

### Added

- `thoth ask "PROMPT"` — canonical scripted research entry point. Accepts the full research-options stack (per Q3-PR2-C, applied identically to the cli group).
- `thoth resume OP_ID` — canonical resume entry point. Honors `--verbose`, `--config`, `--quiet`, `--no-metadata`, `--timeout`, `--api-key-{openai,perplexity,mock}` per Q1-PR2-C.

### Changed (BREAKING)

- `thoth config get KEY --raw` no longer bypasses secret masking. To reveal a secret value, use `--show-secrets` (with or without `--raw`). `--raw` now controls only output formatting.
- `thoth status` (no OP_ID) now exits 2 instead of 1 (matches Click's default for a missing required argument).
- `thoth providers` (no leaf) now exits 2 (was 0) — Click default for required-subcommand groups.
- `thoth modes` (no leaf) now exits 2 (was 0). Use `thoth modes list` for the previous default behavior.
- `thoth providers models --refresh-cache --no-cache` is now mutually exclusive (was a silent ambiguity that fell through to the provider implementation).
- `thoth modes list --name X --source Y` now intersects both filters (was: silently dropped `--source`).
- `thoth --clarify` (without `--interactive`) now exits 2 with `--clarify requires --interactive` (was: silent no-op).
- `thoth config get KEY --layer L` now validates `L` against the actual layer set (`defaults|user|project|env|cli`) and exits 2 on invalid values (was: silently returned wrong-layer data).

### Migration from v2.x

| Old form | New form |
|---|---|
| `thoth --resume OP_ID` | `thoth resume OP_ID` |
| `thoth providers -- --list` | `thoth providers list` |
| `thoth providers -- --models` | `thoth providers models` |
| `thoth providers -- --models --provider openai` | `thoth providers models --provider openai` |
| `thoth providers -- --models --refresh-cache` | `thoth providers models --refresh-cache` |
| `thoth providers -- --keys` (or `--check`) | `thoth providers check` |
| `thoth providers --list` (in-group shim) | `thoth providers list` |
| `thoth modes --json` | `thoth modes list --json` |
| `thoth modes --name deep_research` | `thoth modes list --name deep_research` |
| `thoth --help auth` | (no replacement — `auth` topic dropped) |
| `thoth config get KEY --raw` (revealing secrets) | `thoth config get KEY --show-secrets` |
```

(Adjust the date when committing.)

- [ ] **Step 11.2: Update remaining README references**

In `README.md`, update each remaining occurrence of `thoth --resume` and `thoth providers --` to the new form. Cited locations from the audit + Step 11 prep grep:

- Line 98: `thoth providers -- --list` → `thoth providers list`
- Line 224: `thoth providers -- --list` → `thoth providers list`
- Line 227: `thoth providers -- --keys` → `thoth providers check`
- Line 230: `thoth providers -- --models` → `thoth providers models`
- Line 233: `thoth providers -- --models --provider openai` → `thoth providers models --provider openai`
- Line 234: `thoth providers -- --models -P perplexity` → `thoth providers models -P perplexity`
- Line 565 (table row): `thoth providers -- --list` → `thoth providers list`
- Line 572 (table row): `thoth providers -- --list` → `thoth providers list`
- Line 573 (table row): `thoth providers -- --models` → `thoth providers models`
- Line 574 (table row): `thoth providers -- --keys` → `thoth providers check`
- Line 575 (table row): `thoth providers -- --models -P openai` → `thoth providers models -P openai`

(Line 218 was updated in Task 4.)

- [ ] **Step 11.3: Acceptance grep — ZERO stale references**

Run the acceptance criteria from spec §11:

```bash
git grep "thoth --resume" -- 'src/' 'tests/' 'README.md' ':!CHANGELOG.md' ':!docs/superpowers/'
git grep "thoth providers --" -- 'src/' 'tests/' 'README.md' ':!CHANGELOG.md' ':!docs/superpowers/'
git grep "thoth modes --" -- 'src/' 'tests/' 'README.md' ':!CHANGELOG.md' ':!docs/superpowers/'
```

Expected: ZERO results from each. If any remain, update them in this same commit.

- [ ] **Step 11.4: Run the full local test gate per CLAUDE.md**

```bash
make env-check
just check
uv run pytest tests/ -v
just test-fix
just test-lint
just test-typecheck
./thoth_test -r --skip-interactive -q
```

Expected: ALL GREEN. Counts: pytest ≥ 407, thoth_test ≥ 63.

- [ ] **Step 11.5: Commit**

```bash
git add CHANGELOG.md README.md
git commit -m "docs: v3.0.0 CHANGELOG + README updates (P16 PR2)"
```

`LEFTHOOK=0` is **NOT** needed — docs-only commit; pre-commit hook still runs the test step but should be GREEN since all code changes from Tasks 1–10 are already verified.

---

## Task 12: Mark P16 PR2 complete in PROJECTS.md

**Why twelfth (final):** All 167 ledger tasks (T01–T79 + TS01–TS83 + FU01–FU05) are now done. Flip the project entry, check off the tasks, report final test counts.

**Files:**
- Modify: `PROJECTS.md` — flip P16 PR2 entry from `[ ]` to `[x]`; check off all 167 tasks

- [ ] **Step 12.1: Update PROJECTS.md**

Locate the P16 PR2 project entry. Change the project header from `## [ ] Project P16 PR2:` to `## [x] Project P16 PR2:`. Then check off each of the 167 tasks (T01–T79, TS01–TS83, FU01–FU05) by changing `- [ ]` → `- [x]` for each line.

If the ledger uses an automated counter, run a tally script or manually verify the count: 79 + 83 + 5 = 167.

Add a short completion note under the project header:

```markdown
**Completed:** 2026-04-XX
**Pytest count:** XXX passing (baseline + ~95 PR2-new)
**thoth_test count:** XX passing (PR1.5 baseline preserved)
**Commits landed on main:** 12 (Tasks 1–12 per the implementation plan)
```

(Fill in counts from the Task 11 final gate run.)

- [ ] **Step 12.2: Final pre-commit gate (full hook set, NO `LEFTHOOK=0`)**

```bash
make env-check
just check
uv run pytest tests/ -v
./thoth_test -r --skip-interactive -q
```

All MUST be GREEN. Per CLAUDE.md "Hook discipline": the last commit before push goes through the full hook set — no exceptions for Task 12.

- [ ] **Step 12.3: Commit**

```bash
git add PROJECTS.md
git commit -m "docs(projects): mark P16 PR2 complete (P16 PR2)"
```

Pre-commit hook MUST pass.

---

## Self-Review

After completing all 12 tasks:

**1. Spec coverage** — every section/decision in `docs/superpowers/specs/2026-04-26-p16-pr2-design.md` is implemented:

| Spec section | Task(s) |
|---|---|
| §4 Q1-PR2-C (resume tight+honor) | Tasks 3, 5 |
| §4 Q2-PR2-A (modes shim removal) | Task 7 |
| §4 Q3-PR2-C (ask + group dual-decoration) | Tasks 1, 2 |
| §4 Q4-PR2-D (--raw / --show-secrets split) | Task 9 |
| §4 Q5-PR2-A + 11.i + 13.ii (cleanup batch) | Tasks 6, 7, 8, 9, 10 |
| §4 Q6-PR2-A1+B3+C1 (gating contract) | Tasks 5, 6, 7, 8 (each gating call uses inline `ctx.fail` to stderr with `(use '...')` substring) |
| §4 Q7-PR2-B (ask multi-positional joined) | Task 2 |
| §4 documented defaults (completion drop, no auto-stdin, README+CHANGELOG sweep, etc.) | Tasks 8, 11 |
| §5.2 file layout (16 files) | Tasks 1–10 cover all listed files |
| §5.3 what's removed (5 categories) | Tasks 5, 6, 7, 8 |
| §6.1–6.5 component specs | Tasks 1, 2, 3, 6 |
| §7 data flow (7 paths) | Tests in Tasks 2, 3, 5, 6, 7, 9 cover each path |
| §8 error handling (8.1–8.7) | Tests assert exit codes per §8 tables |
| §9.1 8 test categories | A: T2,T3 / B: T5–T8 / C: T6,T7,T10 / D: T9 / E: T5 / F: T3 / G: T2 / H: T4–T8 |
| §10 commit sequence (12 commits) | Tasks 1–12 (1:1 mapping) |
| §11 acceptance criteria (24 items) | Each acceptance criterion mapped to tests; final `git grep` checks land in T11 |
| §12 dependencies | No coordination changes needed; P12/PR3/P18 callouts respected |
| §13 open items | (a) Click 8.x — no `protected_args` introduced; (b) `resume_operation` callers — `grep` step in T3 Step 3.0; (c) PR2/PR3 release coordination — surfaced in CHANGELOG; (d) breaking-change comm — CHANGELOG migration table; (e) stale references — T11 grep acceptance |

**No spec gaps identified.** Every Q-decision and every documented default has a corresponding implementation step.

**2. Placeholder scan** — Grepped this plan for `TBD`, `TODO`, `similar to`, `appropriate`, `implement later`. None found in code blocks. The phrases "similar to" and "appropriate" appear only in prose context, never as substitution for missing code.

**3. Type / naming consistency**

- `_research_options` (NOT `_research_options_decorator`, NOT `apply_research_options`) — used identically in Tasks 1, 2, and the spec §6.1. ✓
- `_LEGACY_FLAG_TO_NEW_FORM` — module-level dict in BOTH `cli_subcommands/providers.py` (Task 6) and `cli_subcommands/modes.py` (Task 7). Same identifier, same shape. ✓
- `resume_operation` signature — Task 3 widens to `(operation_id, verbose=False, ctx=None, *, quiet=False, no_metadata=False, timeout_override=None, cli_api_keys=None)`. The cli.py legacy callsite (lines 351–357 in PR1.5) passes `(operation_id, verbose, ctx=app_ctx)` — still valid against the new signature. The new resume.py callsite passes ALL the kwargs. ✓
- `_VALID_LAYERS` is `("defaults", "user", "project", "env", "cli")` — verified against `config_cmd.py:20`; Task 9 + Task 10 use this exact tuple. ✓
- File path `src/thoth/cli_subcommands/_options.py` — used identically in Tasks 1, 2 imports. ✓
- Test file naming: `tests/test_p16_pr2_*.py` consistent prefix; categories distinguished by suffix (`_ask`, `_resume`, `_gating`, `_cleanup`, `_config_secrets`, `_options_decorator`). ✓

**4. Open items / risks called out for the executing agent**

- **`commands.providers_models` signature** — Task 6 Step 6.3 explicitly checks whether the existing function accepts `refresh_cache` and `no_cache`. If it doesn't, add them as kwargs in the same commit. Risk: low; PR1 may have already added them, so verify with `grep` before assuming a code change is needed.
- **`thoth_test:2128` `unknown modes op` pattern** — Task 7 Step 7.6 calls out that this pattern needs widening to `r"No such command|unknown.*op"` because Click's default error replaces the custom wording.
- **`tests/test_p16_thothgroup.py:223`** — Per the audit, this asserts bare-`modes` lists modes. Task 7 Step 7.5 calls this out and includes the test in the commit's `git add`.
- **`tests/baselines/help_auth.json`** — Task 8 Step 8.6 may need recapture if the `help auth` command's exit code or stdout changed (it now exits 2). The recapture is bundled in Task 8's commit.
- **Pre-commit `./thoth_test` failures during transitional commits** — Per the per-task gates in Tasks 4–10, run targeted `./thoth_test -t <id>` cases before each commit. If the full quiet suite reveals an unrelated transitional failure that's expected to clear in a later task, document the failure ID in the commit message body and proceed; otherwise diagnose. **Task 12 MUST pass the full hook set.**
- **`isolated_thoth_home` fixture** — Used in several tests across `tests/test_p16_pr2_*.py`. The fixture is defined in `tests/conftest.py`; verify availability before relying on it. If it's not exported globally, import it explicitly or move tests to a directory that picks up the conftest.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-04-26-p16-pr2-implementation.md`.**

Two execution options per the writing-plans skill:

1. **Subagent-Driven (recommended)** — Dispatch a fresh subagent per task, review between tasks, fast iteration. Each task is self-contained with TDD steps and explicit commit boundaries. Recommended for Tasks 5–9 in particular, where transitional state may produce confusing test states across the full suite.

2. **Inline Execution** — Execute tasks in this session using `superpowers:executing-plans`. Batch execution with checkpoints for review at the end of Tasks 4, 7, and 10 (natural review points: post-emitter-update, post-modes-shim-removal, post-cleanup-batch).

After PR2 lands (Tasks 1–12 all green on `main`), draft `docs/superpowers/plans/2026-04-26-p16-pr3-automation-polish.md` covering:
- `completion` Click subcommand (re-add to `ADMIN_COMMANDS` once registered)
- Universal `--json` flag coverage on every admin command
- Per-handler `get_*_data() -> dict` extraction (B-deferred from original spec §6.5)

PR3 lands separately on `main`; release-please then proposes v3.0.0 once both PR2 and PR3 conventional-commits land.
