# Thoth CLI Ergonomics — Design

**Date:** 2026-04-24
**Owner:** steve.morin@gmail.com
**Status:** Approved (pending implementation plan)
**Scope project name (PROJECTS.md):** `thoth-ergonomics-v1`

## Implementation status

This spec was round-tripped against `PROJECTS.md` under **P17**. Every §3
in-scope item and §4 helper has either shipped or been explicitly retired.

| Spec § | Item | Outcome | Where |
|---|---|---|---|
| 3.1 | `providers` subcommand group | ✅ Shipped | P14-T06 (`v2.13.0`) |
| 3.2 | thothspinner sync-poll progress | ✅ Shipped | P14-T07/T08/T09 (`v2.13.0`) |
| 3.3 | Mode-ladder help reorganization | ✅ Shipped (simplified per v9 plan) | P14-T04 (`v2.13.0`) — `help.py:127` workflow chain string |
| **3.4** | **`thoth workflow` / `thoth guide` command** | **Dropped — superseded by `thoth modes` (P11)** | Decision: `planning/thoth.plan.v9.md:18`. Rationale: `thoth modes` already lists every mode with provider/model/`kind=immediate\|background`/source/description in one table, making a separate workflow-ladder command redundant. |
| 3.5 | API-key documentation pass + `thoth help auth` | ✅ Shipped | P14-T05 (`v2.13.0`) |
| 3.6 | `--input-file` vs `--auto` clearer help | ✅ Shipped | P14-T03 (`v2.13.0`) |
| 3.7 | `-v` / `--verbose` worked example in help | ✅ Shipped (one-liner form) | P14-T04 (`v2.13.0`) — `help.py:135`; test at `tests/test_cli_help.py:29`. Per spec line 230 ("documentation follows behavior"), the realized form is a single example line, not the multi-line block originally drafted in §3.7. |
| 3.8 | Surface config path on errors | ✅ Shipped | P14-T01/T02 (`v2.13.0`) — `format_config_context()` in `errors.py` |
| 3.9 | `--pick-model` interactive flag | ✅ Shipped | P14-T11/T12 (`v2.13.0`); P15 follow-up bug fixes |
| §4 | `is_deep_research_model` shared helper | ✅ Shipped (renamed) | P11 / P13 — became `is_background_mode` / `is_background_model` |
| §4 | `format_config_context` helper | ✅ Shipped | P14-T01 |
| §4 | Help rendering helpers | ✅ Shipped | P14-T04, P14-T05 |

**Net:** 8 of 9 §3 items shipped + 3 of 3 §4 helpers shipped; 1 item (§3.4)
explicitly retired with rationale.

## 1. Goal

Reduce the friction a first-time thoth user hits between installation and a
useful research output. Target the places real users stumble today:

- obscure CLI syntax for `providers`
- minutes of silence on sync deep-research runs
- hard-to-scan help output that mixes commands with modes and hides the
  intended workflow ladder
- three overlapping ways to set API keys with no recommended path
- errors that don't tell the user which config file was consulted
- no way to pick a model at run time for quick modes

The intended outcome is a CLI where a new user can run `thoth --help`, see
a clear ladder of quick vs long modes, understand which commands are for
research vs administration, and get feedback during long operations.

## 2. Non-goals

- Finishing the `thoth init` interactive wizard (separate project, later)
- A model comparison / cost table in README (skipped by user)
- Promoting `init/status/list/providers/config` from positional args to real
  Click subcommands — captured as a **separate project** in
  `planning/project_promote_commands.md`, not implemented here
- Fixing `thinking` mode's "quick" description vs `o3-deep-research` model
  mismatch (flagged, not addressed)
- Provider-specific progress ETAs beyond a generic elapsed timer

## 3. In-scope changes

Each item below is independently shippable. The implementation plan will
sequence them, starting with tests for each.

### 3.1 `providers` subcommand group

**Change:** convert `providers` from a positional command taking `-- --list`
into a real Click `@click.group()` with three subcommands.

**User-visible:**

| Before | After |
|---|---|
| `thoth providers -- --list` | `thoth providers list` |
| (no equivalent) | `thoth providers models` |
| (no equivalent) | `thoth providers check` |

`thoth providers -- --list` continues to work for one release and prints a
deprecation notice: `providers -- --list is deprecated; use 'thoth providers list'`.

**Files:** `src/thoth/cli.py`, `src/thoth/commands.py`, `src/thoth/help.py`.

### 3.2 Progress indicator via thothspinner

**Change:** add `thothspinner` as a dependency. Wrap the sync-poll loop in
`src/thoth/run.py` so any deep-research mode run without `--async` or `-v`
shows a live spinner + elapsed timer + expected-duration hint + Ctrl-C hint.

**Rule for when the spinner runs:**

- Mode resolves to a model matching `is_deep_research_model()` (see 3.7)
- `--async` is **not** set
- `--verbose` / `-v` is **not** set (verbose keeps raw-log UX)
- stdout is a TTY (piped output keeps current plain-print behavior)

**Ctrl-C behavior:** the existing SIGINT handler in `src/thoth/signals.py`
already persists a checkpoint. The spinner wrapper prints a one-line hint:

```
Backgrounded. Resume later: thoth --resume op_abc123
```

**User-visible:**

```
$ thoth deep_research "k8s networking"
⠋ Deep research running · 02:14 elapsed · ~20 min expected · Ctrl-C to background
✅ Complete: research/2026-04-24_130512_deep_research.md
```

**Files:** `pyproject.toml`, `src/thoth/run.py`, `src/thoth/signals.py`
(touch only if needed to integrate the spinner lifecycle cleanly).

**Reference:** https://github.com/smorin/thothspinner

### 3.3 Mode-ladder help reorganization

**Change:** restructure the `--help` epilog (`src/thoth/help.py:build_epilog`)
into three labeled groups: Quick, Deep Research, Workflow Chain. Examples
show the canonical sync path, the async path with `--resume`, and a single
quick one-liner.

**User-visible (epilog excerpt):**

```
Research Modes:

  Quick (sync, seconds):
    default          Pass prompt straight to LLM (o3)
    clarification    Ask back to sharpen the question (o3)

  Deep Research (minutes — use --async or expect a progress bar):
    mini_research    Fast lightweight deep research (o4-mini-deep-research)
    deep_research    Comprehensive multi-source research
    comparison       Compare options / technologies

  Workflow chain (each step feeds the next via --auto):
    clarification → exploration → deep_dive → tutorial → solution → prd → tdd

Examples:
  # Quick
  $ thoth "how does DNS work"

  # Sharpen, then research
  $ thoth clarification "k8s networking" --project k8s
  $ thoth exploration --auto --project k8s
  $ thoth deep_research --auto --project k8s --async

  # Resume a backgrounded job
  $ thoth --resume op_abc123
```

The Quick/Deep classification is derived from each mode's model via the
`is_deep_research_model()` helper added in 3.7, so the list stays correct
as `BUILTIN_MODES` evolves.

**Files:** `src/thoth/help.py`.

### 3.4 `thoth workflow` command

> **Status:** Dropped per `planning/thoth.plan.v9.md:18` — superseded by `thoth modes` (P11).

**Change:** add a new `thoth workflow` (alias `thoth guide`) top-level
command that prints the workflow ladder with one-line descriptions and the
recommended invocation per step. Thin wrapper around shared rendering
helpers in `help.py`; no new behavior beyond the restructured help.

**User-visible:**

```
$ thoth workflow
Recommended research workflow:

  1. clarification   Sharpen the question before researching
                     $ thoth clarification "..." --project NAME
  2. exploration     Survey options, trade-offs
                     $ thoth exploration --auto --project NAME
  3. deep_dive       Focus on one technology
                     $ thoth deep_dive --auto --project NAME
  4. tutorial        Concrete examples and code
                     $ thoth tutorial --auto --project NAME
  5. solution        Design a specific solution
                     $ thoth solution --auto --project NAME
  6. prd             Product requirements document
                     $ thoth prd --auto --project NAME
  7. tdd             Technical design document
                     $ thoth tdd --auto --project NAME

For long-running steps use --async and later: thoth --resume OP_ID
```

**Files:** `src/thoth/cli.py`, `src/thoth/help.py`, `src/thoth/commands.py`.

### 3.5 API-key documentation pass

**Change:** documentation-only. Rewrite the Authentication section of
`README.md` to present a single ranked path. Add a new
`thoth help auth` renderer. Soften `--api-key-openai` / `--api-key-perplexity`
help strings to include "(not recommended; prefer env vars)".

**User-visible (README excerpt):**

```
Authentication — recommended order

1. Environment variables (recommended):
     export OPENAI_API_KEY=sk-...
     export PERPLEXITY_API_KEY=pplx-...
2. Config file (persistent, per-machine): ~/.thoth/config.toml
     [providers.openai]
     api_key = "sk-..."
3. CLI flags (last resort — exposes keys in shell history):
     thoth --api-key-openai sk-... deep_research "..."
```

**Files:** `README.md`, `src/thoth/help.py`, `src/thoth/cli.py` (help-string
text only).

### 3.6 `--input-file` vs `--auto` clearer help

**Change:** rewrite the help strings for both flags at
`src/thoth/cli.py:91-92` and add a section in `thoth help` plus the README
with worked examples. No code-behavior change.

**User-visible help text:**

```
--auto               Pick up the latest output from the previous mode in
                     the same --project directory. The happy path for
                     chaining modes.
--input-file PATH    Use the file at PATH as input for this mode. Use
                     when you want to feed a non-thoth document, an older
                     run, or a file from a different project.
```

**Files:** `src/thoth/cli.py`, `README.md`, `src/thoth/help.py`.

### 3.7 `-v` / `--verbose` example

**Change:** add a worked `-v` example to the `--help` examples block so
users know when to reach for it.

**User-visible:**

```
# Debug API issues — show model, provider, timeouts, retries
$ thoth deep_research "topic" -v
[thoth] Operation ID: op_abc123
[thoth] Provider: openai · Model: o3-deep-research · Timeout: 1800s
[thoth] POST /v1/responses (attempt 1/3) → 200 in 482ms
[thoth] Polling op_abc123 every 30s…
```

No change to `-v` behavior — only to the help example. If current verbose
output diverges materially from this example, the example is updated to
match (documentation follows behavior, not the reverse).

**Files:** `src/thoth/help.py`.

### 3.8 Surface config path on errors

**Change:** update `src/thoth/errors.py` to append a "Resolved from:"
section to `APIKeyError`, `MissingProviderError`, and `UnknownModeError`
exception messages. The section lists the config file path (and whether
it exists) plus the env var checked (and whether it was set).

**User-visible:**

```
Error: OPENAI_API_KEY not set
  Suggestion: export OPENAI_API_KEY=sk-... (or edit ~/.thoth/config.toml)
  Config file: /Users/steve/.thoth/config.toml  (does not exist)
  Env checked: OPENAI_API_KEY (unset)
```

**Files:** `src/thoth/errors.py`, `src/thoth/paths.py` (may expose a helper).

### 3.9 `--pick-model` interactive flag (quick-only)

**Change:** add `--pick-model` / `-M` flag on the main command. When
passed, behavior depends on whether the selected mode is classified as
deep-research:

- **Quick mode:** open an interactive picker (prompt-toolkit, already a
  transitive dep via `click`/`rich` stack — confirm at implementation
  time) listing available quick models from the selected provider.
  Selected model overrides the mode's configured model for this run only.
- **Deep-research mode:** exit with a clear error (no fallback, no
  silent ignore):

```
Error: --pick-model is only supported for quick (non-deep-research) modes.
       Mode 'deep_research' uses o3-deep-research.
       Interactive model selection for deep-research models would change
       the research quality and cost profile; edit ~/.thoth/config.toml
       to override the model for a deep-research mode.
```

**Classification helper:** new `is_deep_research_model(model: str) -> bool`
in `src/thoth/config.py`. Rule: model string contains `-deep-research`.
The helper is also used by 3.2 (spinner gate) and 3.3 (help grouping) so
the rule lives in one place.

**Files:** `src/thoth/config.py` (helper), `src/thoth/cli.py` (flag),
`src/thoth/run.py` (apply override), `src/thoth/commands.py` (model list
for picker), new module or extension of `src/thoth/interactive.py` for the
picker UI.

## 4. Architecture and shared helpers

Three bits of shared state keep the items from drifting apart:

1. **`is_deep_research_model(model)` in `src/thoth/config.py`** — single
   source of truth for the quick/deep split. Consumed by spinner gate,
   help grouping, and `--pick-model` validation. Unit-tested directly.
2. **Help rendering helpers in `src/thoth/help.py`** — shared between
   `--help` epilog (3.3), `thoth workflow` (3.4), and `thoth help auth`
   (3.5). Each renderer is a small pure function that returns a string,
   so they are snapshot-testable.
3. **Error-context helper in `src/thoth/errors.py`** — a
   `format_config_context()` builder that each error class calls to
   append the "Resolved from:" block. Keeps message formatting consistent.

## 5. Testing approach (TDD-first)

Per project CLAUDE.md, tests are designed **before** implementation. The
implementation plan will open each task with a test that fails, then make
it pass.

### 5.1 Unit tests

- `is_deep_research_model`: table-driven cases covering every built-in
  model string plus edge cases (empty, `None`, custom config model)
- `format_config_context`: path present/absent × env var set/unset (4 cases)
- Help renderers: snapshot output; assert each section header + example
  block appears

### 5.2 CLI tests (Click `CliRunner`)

- `thoth providers list/models/check` → exit 0 + expected output shape
- `thoth providers -- --list` → exit 0 + deprecation notice on stderr
- `thoth workflow` → lists all 7 ladder steps in order
- `thoth --pick-model default "..."` with mocked picker → runs, uses picked model
- `thoth --pick-model deep_research "..."` → exit non-zero, error text matches

### 5.3 Integration / spinner tests

- Run a mock provider that sleeps 2s and returns; assert the spinner
  started, an elapsed timer ticked at least once, and the spinner cleared
  before the result print
- `--async` path: assert spinner is **not** started
- `-v` path: assert spinner is **not** started
- Non-TTY stdout: assert spinner is **not** started
- SIGINT during spinner: assert checkpoint is saved and "Resume later"
  line is printed

### 5.4 Regression

`./thoth_test -r` full integration suite remains green. New thoth_test
cases added for:

- `providers` subcommand flow
- `--pick-model` quick-mode happy path (using mock provider)
- `--pick-model` deep-research rejection path (no API call made)

## 6. Rollout

1. Land changes behind no feature flag — pure UX surface, all additive
   or clearly-documented deprecations.
2. Bump minor version (CLI surface change).
3. CHANGELOG entry lists new commands, the `providers -- --list`
   deprecation, and the `--pick-model` flag.
4. PROJECTS.md tracks tasks under `thoth-ergonomics-v1`.

## 7. Risks

- **thothspinner on non-TTY** — mitigated by TTY check before engaging
  the spinner.
- **Click subgroup for `providers` breaks old muscle-memory** — mitigated
  by one-release deprecation shim.
- **`--pick-model` interactive UI in non-interactive shells** — flag
  errors cleanly when stdin is not a TTY, similar to the deep-research
  rejection path.

## 8. References

- thothspinner: https://github.com/smorin/thothspinner
- Current CLI: `src/thoth/cli.py`
- Current mode table: `src/thoth/config.py:38` (`BUILTIN_MODES`)
- Current help: `src/thoth/help.py`
- Current run loop: `src/thoth/run.py`
- Current errors: `src/thoth/errors.py`
- Deferred project: `planning/project_promote_commands.md`
