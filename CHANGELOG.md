# Changelog

All notable changes to Thoth are documented here.

## [3.0.0] — 2026-04-26

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

## [Unreleased]

### Fixed
- **BUG-01**: Sync deep-research mode no longer renders two `rich.Live` displays simultaneously. `_execute_research` now picks the polling-progress bar XOR the `thothspinner` Live via the new `_poll_display` helper.
- **BUG-02**: `--pick-model` is rejected (with a helpful message) when combined with `--resume`, `--interactive`, a subcommand, or no prompt — previously the picker fired and the user's selection was silently discarded.
- **BUG-03**: `--prompt-file` now stat-checks file size before reading and rejects non-UTF-8 input. Cap is configurable via `[execution].prompt_max_bytes` (default: `1048576` = 1 MiB).
- **BUG-06**: Interactive picker walks the merged config (`config.data["modes"]`) so user-defined modes appear in `--pick-model`. Removed the OpenAI-only hardcoded `{o3, gpt-4o-mini, gpt-4o}` extras for provider symmetry.

### Changed
- `run_with_spinner` accepts a `console` kwarg so the spinner shares the caller's `rich.Console` (preventing cross-Console Live conflicts).
- ThothSpinner construction in `progress.py` sets `spinner_style="npm_dots"`, `message_shimmer=True`, `timer_format="auto"`, `hint_text="Ctrl-C to background"`, and hides the (zero-progress) progress component for deep-research UX.

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

## [2.6.0] — In Development

### Added
- Clarification mode in interactive session (Shift+Tab toggle)
- `--clarify` flag for starting in Clarification Mode
- Virtual environment management in Makefile (`make venv`, `make venv-install`, `make venv-sync`, `make venv-clean`)
- UV export for dependency extraction

## [2.5.0]

### Added
- Operation lifecycle state machine with full checkpoint recovery
- Interactive mode with Clarification Mode support
- Enhanced signal handling for graceful shutdown with checkpoint save

## [2.2.0]

### Added
- Provider discovery (`thoth providers -- --list`, `--models`, `--keys`)
- Provider-specific API key flags (`--api-key-openai`, `--api-key-perplexity`, `--api-key-mock`)
- Enhanced metadata headers in output files (model, operation_id, created_at)

## [2.1.0]

### Added
- `providers` command for listing available providers
- Dynamic model listing from provider APIs

## [2.0.0]

### Added
- Mode chaining (clarification → exploration → deep_research with `--auto`)
- Checkpoint/resume for async operations (`thoth --resume <operation-id>`)
- Operation management (`thoth list`, `thoth status <id>`)
- Project-based output organization (`--project`)
- Async submit-and-exit mode (`--async`)

## [1.5.0]

### Added
- Core research functionality with multiple modes: `default`, `deep_research`, `clarification`, `exploration`, `thinking`
- OpenAI and Perplexity provider support
- Mock provider for testing
- Rich terminal UI with progress indicators
- Interactive prompt mode with slash commands and tab completion
- Combined report generation (`--combined`)
- Config file support (`~/.thoth/config.toml`)
