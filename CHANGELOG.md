# Changelog

All notable changes to Thoth are documented here.

## [Unreleased]

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
