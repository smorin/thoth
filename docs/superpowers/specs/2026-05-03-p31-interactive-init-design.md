# P31 — Interactive Init Wizard — Design

**Project:** [P31](../../../projects/P31-interactive-init-command.md)
**Status:** Approved design, pending implementation plan.
**Date:** 2026-05-03

## Goal

Replace the placeholder line in `init_command()` (`src/thoth/commands.py:217`,
"Interactive setup wizard not yet implemented") with a real wizard that
collects the minimum information needed to make `thoth` usable on a fresh
machine: which providers the user has, where their API keys live, and which
default mode they want.

The non-interactive path (`thoth init --non-interactive`,
`thoth init --json --non-interactive`) is unchanged. The wizard runs only
when `init` is invoked without `--non-interactive` and without `--json`.

## Scope

In scope:

- Provider multi-select (openai, perplexity, gemini, plus a "skip all" option).
- For each picked provider: detect-then-decide API-key handling (env-var ref,
  literal value in file, or skip).
- Default-mode pick from the four built-ins (`default`, `thinking`,
  `deep_research`, `interactive`).
- Review-and-confirm screen before writing.
- TOML round-trip preserving unknown sections when `--force` is used on an
  existing file.

Out of scope (explicit, not deferred-by-omission):

- API-key validation (no `/v1/models` call). May land later as
  `--validate-keys`.
- Auto-trigger from `thoth research` on missing config.
- Provider-registry-driven dynamic provider list. The list is statically
  declared and grows with explicit edits.
- Profile picker (`general.default_profile`).
- Output-directory / poll-interval / any other config field beyond the four
  named above.
- Arrow-key TUI (`questionary` / `inquirerpy`). Numbered list + `rich.prompt`
  is the agreed UX.
- Modifying `thoth_test` unless an integration test demands it.

## Architecture and boundaries

A new module `src/thoth/init_wizard.py` owns all interactive prompting.
`init_command()` (in `commands.py`) becomes the dispatcher: it resolves the
target path, decides interactive vs non-interactive vs JSON, and either calls
`init_wizard.run(...)` or the existing static-starter path.

```
cli_subcommands/init.py     ← unchanged surface; just passes flags through
        │
        ▼
commands.py: init_command   ← dispatcher: pick path → call wizard OR static
        │
        ├── non-interactive  ──► _build_starter_document()        (today)
        │                         + tomlkit.dumps + write
        │
        └── interactive       ──► init_wizard.run(target, prefill)
                                  ├── collect WizardAnswers
                                  ├── review-and-confirm loop
                                  └── return WizardAnswers
                                         │
                                         ▼
                            commands.py: merge answers into base doc
                                         (round-trip if exists)
                                         + tomlkit.dumps + write
```

The wizard module is **pure data flow**: it returns a `WizardAnswers`
dataclass and does **not** write the file itself. The dispatcher in
`commands.py` owns file I/O. This keeps the wizard testable without touching
disk and leaves only one write site to worry about.

## Components

| File | Role |
|---|---|
| `src/thoth/init_wizard.py` | New. `WizardAnswers` dataclass, `run()` entry, all prompts, the numbered-list helper, the review-and-confirm loop. |
| `src/thoth/commands.py` | Modified. `init_command` learns the dispatch. Add `_apply_wizard_answers(doc, answers)` to merge into a `tomlkit` doc (used by both fresh-doc and `--force` round-trip). |
| `src/thoth/cli_subcommands/init.py` | Unchanged. Existing flag set already covers what the wizard needs. |
| `tests/test_init_wizard.py` | New. Drives `run()` with a stubbed prompt fn; covers all branches. |
| `tests/test_init_command_dispatch.py` | New (or extends existing init test file). Covers the dispatcher (non-interactive vs interactive vs `--json`), `--force` round-trip, file-write site. |
| `thoth_test` integration script | One new case driving the wizard through scripted stdin against the real binary. |

### Data shape

`WizardAnswers` is a frozen dataclass containing only the four wizard-managed
fields. The wizard never decides about `paths`, `execution`, `output`,
`profiles`, or `version`.

```python
@dataclass(frozen=True)
class ProviderChoice:
    name: Literal["openai", "perplexity", "gemini"]
    storage: Literal["env_ref", "literal", "skip"]
    literal_value: str | None  # only when storage == "literal"

@dataclass(frozen=True)
class WizardAnswers:
    providers: tuple[ProviderChoice, ...]
    default_mode: Literal["default", "thinking", "deep_research", "interactive"]
    target_path: Path  # echoed back so the review screen can show it
```

## Data flow (one wizard run)

1. **Resolve target**: existing `_resolve_init_target` logic, unchanged.
2. **Pre-fill**: if target exists and `--force`, parse with `tomlkit` and
   extract the four wizard-relevant fields into a `WizardAnswers`-shaped
   dict (best-effort; missing or malformed fields default to `None`).
3. **Prompt loop** (linear, runs once per "edit" iteration):
   - Q1 — provider multi-select. Numbered list (`1) openai 2) perplexity
     3) gemini 4) skip all`); accept comma-separated input (e.g. `1,3`).
   - Q2 — *per picked provider*: if `os.environ[VAR]` is set and non-empty,
     `Confirm.ask("$OPENAI_API_KEY detected (...abc1) — use it?")`. If yes,
     `storage=env_ref`. Otherwise prompt with three numbered choices: paste
     key now (literal), I'll set the env var (still write `${VAR}` ref), skip
     this provider.

     Env-var mapping (matches today's starter for openai/perplexity; gemini
     follows `planning/references.md`):

     | Provider | Env var |
     |---|---|
     | `openai` | `OPENAI_API_KEY` |
     | `perplexity` | `PERPLEXITY_API_KEY` |
     | `gemini` | `GEMINI_API_KEY` |
   - Q3 — default-mode pick. Numbered list of four with one-line
     descriptions; default is the pre-filled value or `default`.
4. **Review screen**: prints a summary block (target path, each provider's
   storage decision with last-4 chars where applicable, `default_mode`) and
   asks `[Y]es write / [n]o cancel / [e]dit`. `edit` re-runs steps 3a–3c
   with current answers as defaults. `n` exits with no file change, exit
   code 0 — a deliberate cancel is not an error.
5. **Merge into doc**: load base doc (existing path → `tomlkit`-parsed,
   fresh path → `_build_starter_document()`), apply answers via
   `_apply_wizard_answers`. The merge only touches
   `[providers.<name>].api_key` and `[general].default_mode`. All other
   keys preserved verbatim.
6. **Write**: same `target.write_text(tomlkit.dumps(doc))` line that
   exists today.

## Error handling

- **`KeyboardInterrupt` (Ctrl-C) at any prompt**: caught at
  `init_wizard.run()`, prints `"Init cancelled."`, raises `click.Abort()`
  (Click's standard cancel; produces exit code 1, same as today's `^C`).
- **Empty / malformed input on a numbered list**: re-prompts up to three
  times, then aborts with a `ThothError("invalid selection")`, consistent
  with today's CLI errors.
- **TOML round-trip fails on existing file** (corrupt): `ThothError("Cannot
  parse existing config at <path>: <reason>. Pass --non-interactive to
  overwrite with defaults, or fix the file.")`. Note: `--force` is already
  set on the path that triggers round-trip, so the message points at the
  remaining escape hatches.
- **Detected env-var has empty string value**: treated as "not set". We do
  not offer the env-ref path with an empty value — that's a footgun.
- **Literal key with whitespace**: trimmed once, then accepted as-is. We do
  not validate format; that lives behind a future `--validate-keys` flag.
- **Empty Q1 selection** (user hits `<enter>` on the multi-select without
  picking a number and without choosing the explicit `skip all` option):
  re-prompt once. On a second empty answer, treat as `skip all` and accept
  the zero-provider outcome. The resulting file keeps every `api_key` field
  as a `${ENV}` reference — equivalent to today's static starter. Choosing
  `skip all` directly skips this re-prompt and is the documented happy path
  for "I'll configure providers later".

## Testing strategy

`init_wizard.run()` accepts an injected `prompt_fn` parameter (defaults to a
thin wrapper around `rich.prompt`). Tests pass a deterministic stub that
yields scripted answers. **No `monkeypatch` of `rich` internals; no stdin
redirection.** This is the single most important testability decision and
is what makes P31-TS01 tractable.

```python
def test_wizard_happy_path_openai_only(tmp_path):
    answers = init_wizard.run(
        target=tmp_path / "thoth.config.toml",
        prefill=None,
        prompt_fn=ScriptedPrompts([
            "1",                 # provider select: openai
            "y",                 # use $OPENAI_API_KEY
            "2",                 # default mode: thinking
            "y",                 # confirm write
        ]),
        env={"OPENAI_API_KEY": "sk-test"},
    )
    assert answers.providers == (ProviderChoice("openai", "env_ref", None),)
    assert answers.default_mode == "thinking"
```

### P31-TS01 test matrix

| ID | Case |
|---|---|
| TS01-a | Single provider, env-var detected, accepts. |
| TS01-b | Single provider, env-var missing, pastes literal. |
| TS01-c | Multi-provider (input `1,3`) — openai + gemini. |
| TS01-d | "Skip all providers" — writes config with default `${ENV}` references. |
| TS01-e | Default-mode pick rendered, `<enter>` accepts shipped default. |
| TS01-f | Review screen `n` → no file written, exit 0. |
| TS01-g | Review screen `e` → re-prompts, second-pass answers are the ones written. |
| TS01-h | `KeyboardInterrupt` at provider prompt → `click.Abort`. |
| TS01-i | Malformed numbered input retries three times then `ThothError`. |
| TS01-j | Pre-fill from existing TOML: `default_mode=deep_research` shows as default. |
| TS01-k | `_apply_wizard_answers` preserves unknown sections (`[paths]`, `[execution]`, `[output]`, `[profiles]`). |
| TS01-l | `--non-interactive` does NOT call `init_wizard.run()` (dispatcher test). |
| TS01-m | `--json --non-interactive` produces existing JSON envelope (regression). |

Plus one `thoth_test` integration case driving the wizard through scripted
stdin against the real binary, to catch any regression where the wizard
breaks on real terminal I/O. The unit tests cover logic; this catches
integration drift.

## Defaults adopted (no further questions asked)

- Non-interactive path is unchanged. `thoth init --non-interactive` and
  `thoth init --json --non-interactive` continue to write today's static
  starter doc; the wizard never runs in those paths.
- Auto-trigger on missing config from `thoth research` is out of scope.
- TOML round-trip on existing file (`--force`) uses `tomlkit` like
  `thoth config set` does (P10). The wizard touches only its four fields;
  unknown sections are preserved verbatim.
- Mock provider stays out of the wizard's provider list.
- Exit codes unchanged: 0 success, 1 generic `ThothError`, 2 usage error.
