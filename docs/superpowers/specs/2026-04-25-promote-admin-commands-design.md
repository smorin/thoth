# Design — Promote Admin Commands to Click Subcommands (P16)

**Status:** Draft, awaiting user review
**Created:** 2026-04-25
**Project ID:** P16
**Target version:** v3.0.0 (MAJOR — contains breaking changes)
**Predecessors:** Defers from `planning/project_promote_commands.md`; supersedes that file's task draft
**Related:** P12 (CLI Mode Editing) lands `add/set/unset` *inside* this project's `modes` subgroup
**Closes:** PRD F-70 (`shell completion support`), Plan M21-07 (same)

---

## 1. Goal

Refactor `thoth`'s CLI from a single `@click.command()` with positional pseudo-dispatch into a real `@click.group()` with first-class subcommands, deliver shell completion as a built-in surface, and grow `--json` coverage to every admin command — landing as v3.0.0.

## 2. Motivation

1. **Self-documenting surface.** `thoth --help` should make the two-namespace model (admin commands vs research) immediately visible to new users. The current ~130-line imperative dispatch in `cli.py:292-421` is invisible at help time.
2. **Shell completion.** Click's built-in completion machinery requires a real `Group`. Without it, no `thoth resume <TAB>` op-id completion, no `thoth config get <TAB>` key completion. Today there is **zero** shell completion (verified: only an in-process `SlashCommandCompleter` in `interactive.py:235` for the prompt_toolkit REPL — unrelated to shell-level completion).
3. **First-class commands for automation.** External tools (justfiles, CI scripts, shell pipelines) need stable, predictable, machine-readable surfaces — not a positional pseudo-dispatch with awkward separators. JSON output coverage is currently inconsistent: `config list` and `modes` have `--json`; `status`, `list`, `providers`, `init` do not.

## 3. Out of scope

- Renaming any existing mode (`deep_research`, `clarification`, etc.) or admin command name
- Changing the *behavior* of any existing handler (handlers in `commands.py`/`config_cmd.py`/`modes_cmd.py` keep their semantics)
- Modifying `interactive.py` (verified decoupled from CLI dispatch; optional polish only — `SlashCommandCompleter` *may* migrate to importing from `completion/sources.py` if trivial)
- New mode-editing operations (`modes set/add/unset`) — those land in **P12** and slot into this project's `modes` subgroup
- A `thoth admin` namespace prefix (rejected — doubles invocation length, breaks every existing script for no help-clarity gain over the two-section split)
- Performance-tuning the dispatch (refactor is structural; if Click groups are noticeably slower than the imperative dispatch, address as follow-up)

## 4. Decisions locked during brainstorming

| # | Question | Decision |
|---|---|---|
| Q1 | Primary motivation | **B+ plus automation/scripting as a first-class motivator.** Self-documenting surface AND shell completion AND scriptable verbs. |
| Q2 | What about `thoth "bare prompt"`? | **D — keep bare-prompt indefinitely + add `thoth ask PROMPT` as the canonical scripted form**. `ask` is a positional-argument equivalent to the existing top-level `-q/--prompt` flag; both forms continue to work. The bare form (`thoth "..."`) also keeps working. |
| Q3 | What about `--resume OP_ID`? | **D — subcommand-only.** `thoth resume OP_ID` is the only form. `--resume` flag is REMOVED in this release. Breaking change → MAJOR bump. |
| Q4 | Shell completion scope | **C — `thoth completion bash\|zsh\|fish` subcommand + dynamic completers**, with shared-data-source design constraint: completer data sources live in `completion/sources.py`, importable by both shell completers and the existing interactive REPL `SlashCommandCompleter`. |
| Q5 | `--json` coverage | **C — full coverage.** Every admin command grows `--json`. `init --json` requires `--non-interactive` (errors clearly if missing). `config edit --json` emits success envelope after editor closes. |
| Q6 | Help section structure | **D — two sections + labeled epilog.** "Run research" cluster (`ask`, `resume`, `status`, `list`) + "Manage thoth" cluster (`init`, `config`, `modes`, `providers`, `completion`, `help`) + "Modes (positional)" epilog block + worked examples. |
| Q7 | Rollout shape | **B — three-PR sequence into single v3.0.0 release.** PR1 refactor only (no behavior change), PR2 breakage + new verbs (`ask`, `resume`, removals), PR3 automation polish (`completion` + `--json` everywhere). |

**Follow-up clarifications:**

- **Legacy removal is aggressive.** No backward-compat shims for any removed surface. `--resume` flag → gone. `thoth providers -- --list` shim → gone (folded in from the original proposal's `[P##-T08]` "remove deprecation shim" task; cheapest moment is now since we're already breaking). `COMMAND_NAMES` frozenset, `ThothCommand` class, `nargs=-1` top-level `args`, `ignore_unknown_options=True` group flag — all gone.
- **`thoth help [TOPIC]`** — kept as thin alias forwarding to `thoth [TOPIC] --help`. The `auth` topic is preserved because there is no `auth` subcommand to forward to (auth lives in env vars + `config set`).
- **Exit codes** — keep today's 0/1/2 scheme. JSON envelopes expose granular `error.code` strings as advisory metadata, but the OS exit code stays coarse. No new 3/4 codes.
- **JSON-vs-handler seam** — Option **B-deferred-to-PR3**: handlers stay 100% untouched in PR1+PR2; each one gets a `get_*_data() -> dict` extraction at the moment its `--json` lands in PR3. No `as_json` flag ever exists in the codebase.
- **Surprising parses** — `thoth init` (subcommand) vs `thoth "init the database"` (bare-prompt) disambiguated by Click's argv parsing. Documented in `--help` epilog and CHANGELOG; no runtime warning.

## 5. Architecture

### 5.1 The shape

`thoth` becomes `@click.group(cls=ThothGroup, ...)`. `ThothGroup` is a custom `click.Group` subclass that handles three dispatch paths the default group can't:

1. **Registered subcommand** — standard Click dispatch (the common case)
2. **Mode-name positional** — `args[0] ∈ BUILTIN_MODES` → routes to research execution path
3. **Bare-prompt fallback** — `args[0]` is neither subcommand nor mode → routes to default-mode research

`ThothGroup` is also where the two-section help layout (Q6-D) is rendered.

### 5.2 File layout

| File | State | Responsibility |
|---|---|---|
| `src/thoth/cli.py` | shrinks ~280 lines | `@click.group(cls=ThothGroup)` + bare-prompt/mode-fallback callback + explicit `cli.add_command(...)` registrations |
| `src/thoth/help.py` | shrinks ~200 lines | `ThothGroup` class + two-section help renderer + `show_auth_help()` (sole `show_*_help` survivor) |
| `src/thoth/cli_subcommands/` | NEW directory | One module per subcommand cluster; each defines `@click.command()` decorated function(s) delegating to existing handlers |
| `src/thoth/completion/` | NEW directory | `script.py` (shell init script generation) + `sources.py` (dynamic completer data: op-ids, mode names, config keys, provider names) |
| `src/thoth/json_output.py` | NEW file | Uniform JSON envelope contract: `emit_json(data)` and `emit_error(code, message, details)` |
| `src/thoth/commands.py` | unchanged in PR1+PR2; refactored per-handler in PR3 | Existing handlers; gain `get_*_data() -> dict` siblings as `--json` for each lands |
| `src/thoth/config_cmd.py`, `modes_cmd.py` | same as `commands.py` | Same B-deferred pattern |
| `src/thoth/interactive.py` | unchanged | Decoupled from CLI dispatch; optional polish to import from `completion/sources.py` |
| `src/thoth/__main__.py` | unchanged | Entry-point shim |

### 5.3 What gets removed

**PR1:** `if args[0] in COMMAND_NAMES` block (`cli.py:292-421`) · `nargs=-1` positional `args` on top-level command · `ThothCommand` class entirely · `parse_args` `--help SUBCOMMAND` interceptor (`help.py:34-90ish`) · `COMMAND_NAMES` frozenset · `show_init_help()`, `show_status_help()`, `show_list_help()`, `show_providers_help()`, `show_config_help()`, `show_modes_help()`, `HELP_TOPICS` tuple · help-string examples in `cli.py:184-188` rewritten from `thoth help X` to `thoth X --help`.

**PR2:** `--resume` global option declaration (`cli.py:97`) · `providers -- --` legacy shim (`cli.py:327-370`, ~45 lines) · `ctx.args` plumbing (verify all uses; remove if safe) · `ignore_unknown_options=True` on top-level group (no longer needed once shim is gone — Click reverts to strict option parsing, catching script typos).

**PR3:** Nothing removed; pure addition.

**Net code-line impact PR1+PR2:** roughly **+400 added, ~600 removed = net negative ~200 lines** before counting cleaner surface gains.

### 5.4 What stays the same (user-visible)

All current invocation strings except `thoth --resume OP_ID` and `thoth providers -- --list` continue to work bit-identically: `thoth init`, `thoth status OP_ID`, `thoth list`, `thoth deep_research "topic"`, `thoth "bare prompt"`, `thoth -i`, `thoth -m deep_research -q "..."`, `thoth providers list`, `thoth config list`, `thoth modes`, `thoth -V`, `thoth --version`. All non-removed global flags (`--project`, `--async`, `--auto`, `--input-file`, `--verbose`, `--quiet`, `--config`, `--output-dir`, etc.) stay on the top-level group.

## 6. Components

### 6.1 `ThothGroup` (in `help.py`)

- **Purpose:** Single chokepoint for dispatch + help rendering.
- **Interface:** ~3 overrides (`invoke`, `format_commands`, `resolve_command`), ~50 lines total.
- **Depends on:** `BUILTIN_MODES`, `_run_research_default()` (extracted from current bare-prompt code).

### 6.2 `cli_subcommands/` (10 modules — explicit registration, not auto-discovery)

| File | Subcommand(s) |
|---|---|
| `init.py` | `thoth init [--non-interactive] [--json]` |
| `status.py` | `thoth status OP_ID [--json]` (OP_ID has dynamic completer) |
| `list_cmd.py` | `thoth list [--all] [--json]` (file name avoids Python keyword shadow) |
| `providers.py` | Click subgroup with leaves `list`, `models`, `check` (UX is flat: `thoth providers list`) |
| `config.py` | Click subgroup with leaves `get`, `set`, `unset`, `list`, `path`, `edit` |
| `modes.py` | Click subgroup with leaves `list` (P16); `add`, `set`, `unset` slot in via P12 |
| `ask.py` | `thoth ask PROMPT [--mode] [--async] [--auto] [--input-file] [--json] ...` (full inheriting flag set) |
| `resume.py` | `thoth resume OP_ID [--json]` (OP_ID has dynamic completer) |
| `completion.py` | `thoth completion {bash,zsh,fish} [--install]` |
| `help_cmd.py` | `thoth help [TOPIC]` — thin forwarder |

Registered explicitly in `cli.py` via `cli.add_command(...)` — no auto-discovery (explicit beats magic; the surface is visible at one place).

### 6.3 `completion/`

- **`sources.py`** — pure functions for completer data:
  - `operation_ids(ctx, param, incomplete)` — globs `~/.thoth/operations/*.json`
  - `mode_names(ctx, param, incomplete)` — filters `BUILTIN_MODES`
  - `config_keys(ctx, param, incomplete)` — flattens TOML keys from current resolved config
  - `provider_names(ctx, param, incomplete)` — reads from the same source as the `--provider` Click choice (`["openai", "perplexity", "mock"]` today, sourced from `cli.py:103`'s `click.Choice`). If the provider list moves to a registry in the future, this function follows.
- **`script.py`** — wraps Click's `_THOTH_COMPLETE=<shell>_source thoth` machinery with friendlier UX (better error messages, `--install` writes to conventional shell rc location with prompt-before-overwrite in tty, refusal in non-tty unless `--force`).
- **Shared with `interactive.py`** — `SlashCommandCompleter` MAY migrate to importing `mode_names`. Polish, not blocker.

### 6.4 `json_output.py`

- **Contract:** Every `--json` output is a top-level JSON object. Success: `{"status": "ok", "data": {...}}`. Error: `{"status": "error", "error": {"code": "STRING_CODE", "message": "...", "details": {...}?}}`.
- **API:** `emit_json(data: dict) -> NoReturn` (writes + exit 0) and `emit_error(code: str, message: str, details: dict | None = None, exit_code: int = 1) -> NoReturn`.
- **Dependencies:** `json`, `sys` (stdlib only). Framework-free.

### 6.5 Existing handlers (`commands.py`, `config_cmd.py`, `modes_cmd.py`)

- **PR1+PR2:** untouched.
- **PR3:** Each command needing `--json` gets a `get_*_data() -> dict` sibling extracted (the B-deferred pattern). Existing handler stays as Rich-printing entry; refactored internally to call the new data function then format with Rich.

## 7. Data flow

### 7.1 Five paths through the group

1. **Registered subcommand** (common): Click parses → `ThothGroup.invoke` → `cli_subcommands/<name>.py::<name>(...)` → handler delegate (or `get_*_data()` → `emit_json` if `--json`).
2. **Mode positional**: `thoth deep_research "topic"` → `resolve_command` returns None → `invoke` detects `args[0] ∈ BUILTIN_MODES` → packages and calls `_run_research_default(mode, prompt, **opts)`.
3. **Bare-prompt fallback**: `thoth "explain X"` → same as path 2 with `mode=DEFAULT_MODE`, `prompt=" ".join(args)`.
4. **Completion** (install + runtime): `eval "$(thoth completion zsh)"` registers shell handler; subsequent TAB invocations re-call `thoth` with `COMP_WORDS` env, Click matches command + arg position, looks up the registered `shell_complete` callback in `completion/sources.py`.
5. **`thoth help [TOPIC]` alias**: dispatches to `cli_subcommands/help_cmd.py` → looks up target subcommand → `ctx.invoke(target_cmd, ['--help'])` (or `show_auth_help()` for `auth` special case).

### 7.2 The critical invariant

**The subcommand wrapper is the only place that knows about `--json`.** Handlers below never see the flag. This is what makes B-deferred work; if a handler ever started branching on a JSON flag, the architecture would degrade. CI lint rule recommended: `! grep -rn "as_json\|.json:" src/thoth/commands.py src/thoth/config_cmd.py src/thoth/modes_cmd.py`.

## 8. Error handling

### 8.1 Click-handled (free, replaces hand-rolled error code in `cli.py:302-305`, `cli.py:377-382`)

Unknown subcommand · bad option type · missing required argument · `--help` rendering — all native Click. Exit 2 for usage errors; exit 0 for `--help`.

### 8.2 Custom (uniform via `json_output.py` when `--json` is set)

| Case | Behavior |
|---|---|
| `thoth init --json` (no `--non-interactive`) | `emit_error("JSON_REQUIRES_NONINTERACTIVE", ...)`. Exit 2. |
| `thoth config edit --json` | Success: `{"status":"ok","data":{"config_path":"...","editor":"vim","editor_exit_code":0}}`. Editor failure: `emit_error("EDITOR_FAILED", ..., {"exit_code": N})`. |
| `thoth resume INVALID_ID --json` | `emit_error("OPERATION_NOT_FOUND", ...)`. Exit 1. |
| `thoth completion <unsupported>` | `emit_error("UNSUPPORTED_SHELL", ...)`. Exit 2. |
| `thoth completion install` overwrite | Detect existing `_thoth_completion` block; preview + prompt y/n in tty; refuse silently in non-tty unless `--force`. |
| Bare-prompt with first word matching a subcommand | NOT an error; subcommand wins. Disambiguation via quoting documented in `--help` epilog. |

### 8.3 Backward compat for exit codes

Today's exit codes (0=success, 1=runtime, 2=usage) preserved for non-`--json` invocations across PR1 and PR2. PR3's `--json` paths add granular `error.code` strings inside the envelope but keep OS exit codes in the existing 0/1/2 set.

### 8.4 Signals & API key errors

`signals.py::handle_sigint` wired in `main()` (`cli.py:472`) — unchanged. P14-T10 SIGINT resume hint preserved (downstream of dispatch). `APIKeyError` continues to surface via existing handlers; `--json` wrappers convert to `emit_error("API_KEY_MISSING", ..., {"provider": ..., "config_path": ...})` using `format_config_context` (P14-T01).

## 9. Testing strategy

### 9.1 Test taxonomy (10 categories)

| ID | Category | Scope |
|---|---|---|
| A | Snapshot tests — help output | `thoth --help`, every subcommand `--help`, completion script output for each shell |
| B | `CliRunner` invocation tests | Per subcommand: happy + sad + `--json` happy + `--json` sad + missing-arg |
| C | **Dispatch parity** (PR1 gate) | Pre-refactor baselines captured; CI compares post-refactor exit + stdout for every existing invocation pattern |
| D | `ThothGroup` unit tests | `resolve_command`, `invoke` mode-routing, `invoke` bare-prompt routing, `format_commands` two-section structure |
| E | Surprising parses | `thoth init` vs `thoth "init the database"`, `thoth deep_research` (no prompt), `thoth ask` (no arg) |
| F | **Breakage** (PR2 gate) | `thoth --resume OP_ID` exits 2 with helpful suggestion; `thoth providers -- --list` exits 2 directing to new form |
| G | JSON envelope contract | Parametrized over every `--json` command: top-level object, has `status`, parses cleanly |
| H | Completion | `sources.py` unit tests + script-output snapshots + `install` integration test (writes safely, doesn't clobber) |
| I | `thoth_test` integration | One-time sweep of cases using `thoth --resume` → migrate to `thoth resume`; new cases for `ask`/`resume`/`completion` |
| J | Regression | Every pre-existing pytest + thoth_test case continues to pass after each PR |

### 9.2 Per-PR gates

| PR | Required green |
|---|---|
| PR1 | C, D, E, J. (No new behavior → A and B for *new* commands not yet relevant.) |
| PR2 | All above + F. Sweep thoth_test cases using `--resume`. |
| PR3 | All above + A, B (full coverage), G, H. |

### 9.3 TDD ordering

Per CLAUDE.md "Test-driven development": for every task, **write the test first** (red), then minimal implementation (green), then widen to file-level pytest, then full gate (`just check && ./thoth_test -r --skip-interactive -q`) before commit. Pre-commit hook enforces full gate.

### 9.4 Estimates

Roughly **~100 new tests** across the 10 categories. Most are 5-line `CliRunner` assertions; the expensive ones (D, H) are bounded.

### 9.5 Out of test scope (deliberate)

Click's own dispatch correctness · existing handlers' Rich rendering byte-for-byte (color codes drift) · performance of the dispatch refactor.

## 10. Rollout

### PR1 — refactor only (no behavior change)

Click group · `ThothGroup` · `cli_subcommands/*` (delegating to existing handlers) · two-section help renderer · `help.py` shrink · removal of `COMMAND_NAMES`/`ThothCommand`/imperative dispatch · `thoth help [TOPIC]` thin alias.

**Test gate:** Categories C, D, E, J. Pre-refactor baselines captured as **P16-T01** before any other code is written.

**Lands as:** intermediate commit on `main`; not yet a release.

### PR2 — breakage + new verbs

`ask` subcommand · `resume` subcommand · `--resume` flag REMOVED · `providers -- --` shim REMOVED · `ignore_unknown_options=True` removed · CHANGELOG breaking-change entries.

**Test gate:** Above + Category F. Sweep `thoth_test` cases.

**Lands as:** intermediate commit on `main`; not yet a release.

### PR3 — automation polish

`completion` subcommand + `sources.py` + `script.py` · `--json` for every admin command (per-handler `get_*_data()` extraction as needed) · `json_output.py` contract module · CI lint rule for JSON-flag-not-in-handlers · CI lint rule for `JSON_COMMANDS` parametrize-list completeness.

**Test gate:** All above + A, B, G, H.

**Lands as:** final commit on `main`; release-please opens v3.0.0 PR; merge → tag → publish.

### Release sequencing

All three PRs merge to `main` consecutively. release-please observes the breaking-change commits (`feat!:` or `BREAKING CHANGE:` footer) and proposes v3.0.0 with the consolidated CHANGELOG. Single MAJOR bump for the cumulative change set.

**Discipline requirement:** all three PRs must land within ~1–2 weeks. If PR1 ships and the team stalls, the codebase enters a state where PR2's removals are not yet done — we still ship a v2.x patch, but the v3.0 narrative drifts. Mitigation: don't merge PR1 until PR2 is in review.

## 11. Acceptance criteria

- [ ] `thoth --help` shows two clearly-labeled sections ("Run research" / "Manage thoth") + "Modes (positional)" epilog block + worked examples
- [ ] Every admin command is a real Click subcommand (verified by `cli.commands` keys)
- [ ] `thoth init`, `thoth status OP_ID`, `thoth list`, `thoth providers list`, `thoth config list`, `thoth modes`, `thoth deep_research "topic"`, `thoth "bare prompt"`, `thoth -i`, `thoth -m X -q Y` — all work bit-identically to pre-refactor
- [ ] `thoth ask "prompt"` runs default-mode research (canonical scripted form)
- [ ] `thoth resume OP_ID` resumes operations; `thoth --resume OP_ID` exits 2 with suggestion
- [ ] `thoth providers -- --list` exits 2 with suggestion
- [ ] `thoth completion bash` and `thoth completion zsh` emit working init scripts (required for v3.0.0)
- [ ] `thoth completion fish` emits a working init script if Click ≥ 8.x is already pinned in `pyproject.toml`; otherwise fish support defers to a follow-up (see §13)
- [ ] `thoth resume <TAB>`, `thoth status <TAB>`, `thoth config get <TAB>` complete with live data
- [ ] Every admin command supports `--json`; output is a valid top-level JSON object with `status` field
- [ ] `thoth init --json --non-interactive` works end-to-end without prompting
- [ ] `thoth init --json` (no `--non-interactive`) errors clearly with code 2
- [ ] CHANGELOG documents v3.0.0 with the breaking changes and migration paths
- [ ] PRD F-70 and Plan M21-07 marked complete (shell completion shipped)
- [ ] PRD `thoth.prd.v24.md:96` "Added shell completion support" line moved from aspirational to actually-shipped
- [ ] All pre-existing tests pass (J)
- [ ] `make env-check && just check && ./thoth_test -r` green
- [ ] `just test-fix && just test-lint && just test-typecheck` green

## 12. Dependencies & coordination

- **P12 (CLI Mode Editing)** is `[ ]` not-started and overlaps. P16 ships the `modes` Click subgroup with `list` only; P12's `add/set/unset` slot in as additional `@modes.command()` decorations. **Coordination required:** decide order. Recommendation: P16 ships first (P12 then has a Click subgroup to add commands to, instead of having to invent the dispatch); P12 follows in v3.1.0.
- **P14 (Thoth CLI Ergonomics v1)** is `[x]` complete. The `providers list/models/check` subcommands and `--pick-model` interactive picker land cleanly into the new structure. P14-T01 (`format_config_context`) is reused by `--json` API-key error paths.
- **P08 (Typed Exceptions)** is `[-]` in-progress; doesn't conflict (different code surface).

## 13. Open items / risks

- **Per-handler refactor scope in PR3.** B-deferred means each handler's `get_*_data()` extraction is a per-handler unknown. Worst-case: a handler is so intertwined with Rich that we end up doing C (full inversion) for that one. Bounded — only affects that command's `--json` ship date, not the whole project.
- **Click version pinning.** `thoth completion fish` requires Click ≥ 8.x. Verify current pin in `pyproject.toml` and bump if needed; if bump is non-trivial, fish support can defer to a follow-up (bash + zsh ship in v3.0).
- **Discipline risk on three-PR sequence.** If team stalls between PR1 and PR2, codebase carries un-shipped breakage intentions. Mitigation in §10.
- **`syrupy` snapshot library** — verify it's a project dependency before relying on it for category A; if not, hand-rolled fixtures in `tests/snapshots/` are fine. Decide in plan phase.
- **Stale PRD line** at `planning/thoth.prd.v24.md:96` ("Added shell completion support") needs correction as part of PR3's documentation pass.
