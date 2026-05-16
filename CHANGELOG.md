# Changelog

All notable changes to Doxa Research are documented here.

## [3.0.4](https://github.com/smorin/doxa-research/compare/v3.0.3...v3.0.4) (2026-05-16)


### Bug Fixes

* **ci:** wrap long publish.yml line to satisfy yamllint line-length(120) ([839b838](https://github.com/smorin/doxa-research/commit/839b83821be28c15d3e0affb7b017ee2ac2ecc92))


### Miscellaneous

* **release:** customize PR title to make publish action clearer ([8768d48](https://github.com/smorin/doxa-research/commit/8768d486de2ce21a95c50e2f093f3ef57f1c5f4e))

## [3.0.3](https://github.com/smorin/doxa-research/compare/v3.0.2...v3.0.3) (2026-05-16)


### Documentation

* **release:** add RELEASE-PLEASE-APP.md canonical App setup guide ([abb0742](https://github.com/smorin/doxa-research/commit/abb0742ed1a370dfb8381ac0f2166a91dd7028d4))

## [3.0.2](https://github.com/smorin/doxa-research/compare/v3.0.1...v3.0.2) (2026-05-16)


### Miscellaneous

* retrigger release-please after credentials fix ([f2fca18](https://github.com/smorin/doxa-research/commit/f2fca1865e24931d04f52c92c56e98a7820313c9))
* trigger release-please after App credentials setup ([4ea31a9](https://github.com/smorin/doxa-research/commit/4ea31a90c68ddc6ef57348213b158fecb33410a4))

## [3.0.1] — 2026-05-16

### Changed

- Re-release of 3.0.0 under a new version number. TestPyPI's permanent
  file-name-reuse policy blocked re-upload of `doxa_research-3.0.0-*`
  files after the original laptop-built artifacts were deleted (they had
  a different hash than the CI-built artifacts; deleting was the
  recovery, but PyPI/TestPyPI never allow reusing a filename even after
  deletion). 3.0.1 is the first publicly installable release of the
  doxa-research rebrand. No functional changes from the unpublished
  3.0.0 tag.

## [3.0.0] — 2026-05-15

### Renamed (BREAKING)

This release renames the project from `thoth` to `doxa-research`. Every public-facing identifier changes — there is **no automatic migration** for existing users.

| Surface | Old | New |
|---|---|---|
| PyPI distribution | `thoth` | `doxa-research` |
| Install command | `pip install thoth` | `pip install doxa-research` |
| Python import | `import thoth` | `import doxa_research` |
| CLI command | `thoth …` | `doxa …` (also `doxa-research …`) |
| Module entry point | `python -m thoth` | `python -m doxa_research` |
| Environment variables | `THOTH_*` (13 vars) | `DOXA_*` |
| Click completion env | `_THOTH_COMPLETE` | `_DOXA_COMPLETE` |
| User config dir | `~/.config/thoth/` | `~/.config/doxa/` |
| User state dir | `~/.local/state/thoth/` | `~/.local/state/doxa/` |
| User cache dir | `~/.cache/thoth/` | `~/.cache/doxa/` |
| Config file name | `thoth.config.toml` | `doxa.config.toml` |
| GitHub repo | `smorin/thoth` | `smorin/doxa-research` |
| Internal classes | `ThothError`, `ThothGroup`, `ThothConfig`, `ThothCommand`, `ThothOrchestrator` | `DoxaError`, `DoxaGroup`, `DoxaConfig`, `DoxaCommand`, `DoxaOrchestrator` |

**Migration for existing users** (one-time):

```bash
# 1. Install the new package
pip uninstall thoth
pip install doxa-research

# 2. Copy your config + state + cache (no auto-migration)
mkdir -p ~/.config/doxa ~/.cache/doxa ~/.local/state/doxa
cp -r ~/.config/thoth/. ~/.config/doxa/ 2>/dev/null || true
cp -r ~/.cache/thoth/. ~/.cache/doxa/ 2>/dev/null || true
cp -r ~/.local/state/thoth/. ~/.local/state/doxa/ 2>/dev/null || true
mv ~/.config/doxa/thoth.config.toml ~/.config/doxa/doxa.config.toml 2>/dev/null || true

# 3. Update shell init scripts: THOTH_* → DOXA_*, _THOTH_COMPLETE → _DOXA_COMPLETE
# 4. Old thoth 2.5.0 remains on PyPI (frozen, will not receive updates)
```

The `thothspinner` dependency is unrelated to this rename and keeps its name.

### Removed (BREAKING)

- The `--resume` / `-R` global flag is removed. Use `doxa-research resume OP_ID` instead.
- The `doxa-research providers -- --list` / `--models` / `--keys` / `--check` / `--refresh-cache` / `--no-cache` legacy `--`-separator forms are removed. Use `doxa-research providers list|models|check` instead.
- The `doxa-research providers --list` / `--models` / `--keys` / `--check` in-group flag forms (PR1.5 hidden subcommands) are removed. Same migration as above.
- The `doxa-research modes --json` / `--show-secrets` / `--full` / `--name X` / `--source X` flag-style forms are removed. Use `doxa-research modes list <flag>` instead.
- The `doxa-research --help <topic>` parse-time hijack is removed. Use `doxa-research help <topic>` (or `doxa-research <topic> --help` for real subcommands).
- The `auth` virtual help topic on `doxa-research help auth` is removed.
- `completion` was removed from the help renderer's command listing (it was a phantom — never registered as a real subcommand).

### Added

- `doxa-research ask "PROMPT"` — canonical scripted research entry point. Accepts the full research-options stack (per Q3-PR2-C, applied identically to the cli group).
- `doxa-research resume OP_ID` — canonical resume entry point. Honors `--verbose`, `--config`, `--quiet`, `--no-metadata`, `--timeout`, `--api-key-{openai,perplexity,mock}` per Q1-PR2-C.
- `doxa-research completion {bash,zsh,fish}` — emit eval-able shell init scripts. Supports `--install` (TTY-detect + prompt-before-overwrite), `--install --force` (CI-friendly silent overwrite), `--install --manual` (print block + instructions; never write), and `--json` (structured success/error envelopes for install metadata or shell-validation errors). Closes PRD F-70.
- TAB completion of operation IDs (`resume`, `status`), mode names (`modes list --name`), config keys (`config get`), and provider names (`providers list/models/check --provider`).
- `--json` flag on every data/action admin command: `init`, `status`, `list`, `providers list/models/check`, `config get/set/unset/list/path/edit`, `modes list`, `ask`, `resume`. Envelope contract documented in `docs/json-output.md`.
- `ask --json` immediate-mode returns full result inline; background-mode auto-asyncs and returns an op-id submit envelope.
- `resume --json` is a pure snapshot — never advances state, never polls. Use without `--json` to retry.

### Changed (BREAKING)

- `doxa-research config get KEY --raw` no longer bypasses secret masking. To reveal a secret value, use `--show-secrets` (with or without `--raw`). `--raw` now controls only output formatting. `--raw` is supported only on `doxa-research config get`; `doxa-research config list --raw` exits 2 with a clear message (use `doxa-research config list --json` for machine-readable list output).
- `doxa-research status` (no OP_ID) now exits 2 instead of 1 (matches Click's default for a missing required argument).
- `doxa-research providers` (no leaf) now exits 2 (was 0) — Click default for required-subcommand groups.
- `doxa-research modes` (no leaf) now exits 2 (was 0). Use `doxa-research modes list` for the previous default behavior.
- `doxa-research providers models --refresh-cache --no-cache` is now mutually exclusive (was a silent ambiguity that fell through to the provider implementation).
- `doxa-research modes list --name X --source Y` now intersects both filters (was: silently dropped `--source`).
- `doxa-research --clarify` (without `--interactive`) now exits 2 with `--clarify requires --interactive` (was: silent no-op).
- `doxa-research config get KEY --layer L` now validates `L` against the actual layer set (`defaults|user|project|env|cli`) and exits 2 on invalid values (was: silently returned wrong-layer data).

### Migration from v2.x

| Old form | New form |
|---|---|
| `doxa-research --resume OP_ID` | `doxa-research resume OP_ID` |
| `doxa-research providers -- --list` | `doxa-research providers list` |
| `doxa-research providers -- --models` | `doxa-research providers models` |
| `doxa-research providers -- --models --provider openai` | `doxa-research providers models --provider openai` |
| `doxa-research providers -- --models --refresh-cache` | `doxa-research providers models --refresh-cache` |
| `doxa-research providers -- --keys` (or `--check`) | `doxa-research providers check` |
| `doxa-research providers --list` (in-group shim) | `doxa-research providers list` |
| `doxa-research modes --json` | `doxa-research modes list --json` |
| `doxa-research modes --name deep_research` | `doxa-research modes list --name deep_research` |
| `doxa-research --help auth` | (no replacement — `auth` topic dropped) |
| `doxa-research config get KEY --raw` (revealing secrets) | `doxa-research config get KEY --show-secrets` |

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
- `doxa-research providers list`, `doxa-research providers models`, `doxa-research providers check` — explicit subcommands replace `doxa-research providers -- --list`.
- `doxa-research help auth` — in-CLI authentication guidance.
- `doxa-research cancel OP_ID` — cancels an in-flight background operation where the provider supports upstream cancellation and marks the local checkpoint cancelled.
- `--pick-model` / `-M` flag for interactively selecting a model on immediate (non-background) modes.
- Progress spinner during sync background-mode runs (via `thothspinner`).
- Config file path surfaced in `APIKeyError` messages.
- "Resume later: doxa-research resume OP_ID" hint on Ctrl-C.

### Changed
- `--help` now shows the workflow chain (clarification → … → tdd) and worked examples for `--auto`, `--async`/`--resume`, and `-v` debugging.
- `--input-file` / `--auto` help rewritten for clarity.
- `--api-key-openai` / `--api-key-perplexity` / `--api-key-mock` help now says "(not recommended; prefer env vars)".
- README Authentication section documents env-vars → config-file → CLI-flags in that order.

### Deprecated
- `doxa-research providers -- --list` — still works for one release; use `doxa-research providers list`.

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
- Provider discovery (`doxa-research providers -- --list`, `--models`, `--keys`)
- Provider-specific API key flags (`--api-key-openai`, `--api-key-perplexity`, `--api-key-mock`)
- Enhanced metadata headers in output files (model, operation_id, created_at)

## [2.1.0]

### Added
- `providers` command for listing available providers
- Dynamic model listing from provider APIs

## [2.0.0]

### Added
- Mode chaining (clarification → exploration → deep_research with `--auto`)
- Checkpoint/resume for async operations (`doxa-research --resume <operation-id>`)
- Operation management (`doxa-research list`, `doxa-research status <id>`)
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
- Config file support (`~/.doxa-research/config.toml`)
