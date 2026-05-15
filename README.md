# Doxa Research - AI-Powered Research Assistant

[![PyPI version](https://img.shields.io/pypi/v/doxa-research.svg)](https://pypi.org/project/doxa-research/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/smorin/doxa-research/actions/workflows/ci.yml/badge.svg)](https://github.com/smorin/doxa-research/actions/workflows/ci.yml)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)

Doxa Research is a command-line tool that automates deep technical research using multiple LLM providers. It orchestrates parallel execution of OpenAI's Deep Research API and Perplexity's research models to deliver comprehensive, multi-perspective research reports.

## Features

- **Multi-provider intelligence**: Parallel execution of OpenAI and Perplexity for comprehensive results
- **Interactive prompt mode**: Enhanced terminal UI with slash commands, tab completion, and multiline input
- **Provider discovery**: List available providers, models, and API key configuration
- **Zero-configuration deployment**: UV inline script dependencies eliminate setup complexity
- **Flexible operation modes**: Support both interactive (wait) and background (submit and exit) workflows
- **Production-ready reliability**: Checkpoint/resume, graceful error handling, and operation persistence
- **Simple output structure**: Intuitive file placement with ad-hoc and project modes
- **Mode chaining**: Seamless workflow from clarification through exploration to deep research
- **Rich metadata**: Output files include model information and exact prompts sent to LLMs

**Origin of the name:** *Doxa* (Greek: δόξα) means "opinion", "belief", or "received wisdom" in ancient Greek philosophy. Doxa Research synthesizes multiple AI perspectives — OpenAI, Perplexity, Gemini — to surface consensus and divergence across views, in the spirit of dialectical inquiry.

> **Renamed in 3.0.0:** This project was previously released as `thoth` (versions ≤ 2.5.0 on PyPI). The CLI command (`thoth` → `doxa`), Python module (`thoth` → `doxa_research`), PyPI distribution (`thoth` → `doxa-research`), environment variables (`THOTH_*` → `DOXA_*`), and config directory (`~/.config/thoth/` → `~/.config/doxa/`) have all changed. Existing users must migrate manually — there is no automatic config migration. See [CHANGELOG.md](CHANGELOG.md) for the full migration guide.

## Prerequisites

- Python ≥ 3.11
- [UV](https://github.com/astral-sh/uv) package manager
- OpenAI API key (for OpenAI provider)
- Perplexity API key (for Perplexity provider)

## Installation

### From PyPI (recommended)

```bash
# Install and run with uvx (no setup required)
uvx doxa-research

# Or install permanently with uv
uv tool install doxa-research

# Or with pip
pip install doxa-research
```

### From source

```bash
# Clone the repository
git clone https://github.com/smorin/doxa-research.git
cd doxa-research

# Install in editable mode
uv sync

# Or run directly without installing
./doxa --help
```

## Authentication

Authentication — recommended order:

1. **Environment variables (recommended)**:
   ```bash
   export OPENAI_API_KEY=sk-...
   export PERPLEXITY_API_KEY=pplx-...
   ```

2. **Config file** (persistent, per-machine): `~/.config/doxa-research/doxa-research.config.toml`
   ```toml
   [providers.openai]
   api_key = "sk-..."
   ```

3. **CLI flags** (last resort — exposes keys in shell history; not recommended):
   ```bash
   doxa-research --api-key-openai sk-... deep_research "..."
   ```

For related command help, run `doxa-research config --help`.

## Quick Start

1. **Initialize configuration:**
   ```bash
   doxa-research init
   ```

2. **Set API keys:**
   ```bash
   export OPENAI_API_KEY="your-openai-key"
   export PERPLEXITY_API_KEY="your-perplexity-key"
   export GEMINI_API_KEY="your-gemini-key"
   ```

3. **Check provider configuration:**
   ```bash
   doxa-research providers list
   ```

4. **Run your first research:**
   ```bash
   doxa-research "impact of quantum computing on cryptography"
   ```

## Usage

### Basic Research
```bash
# Quick research (uses default mode)
doxa "your research prompt"

# Run research with a specific mode
doxa deep_research "your research prompt"
doxa clarification "ambiguous topic needing clarity"
doxa exploration "broad topic to explore"
doxa thinking "quick analysis task"
doxa openai_reasoning "grounded OpenAI reasoning task"

# Use specific provider
doxa "explain quantum computing" --provider openai
doxa deep_research "AI safety" --provider openai --timeout 120
```

### Project-Based Research
```bash
# Save outputs to a project directory
doxa deep_research "quantum algorithms" --project quantum_research
```

### Mode Chaining
```bash
# Start with clarification
doxa clarification "quantum computing security"

# Then explore with auto-input from previous mode
doxa exploration --auto

# Finally, deep research with all context
doxa deep_research --auto
```

### Provider-Specific API Keys
```bash
# Use specific API key for a provider
doxa "prompt" --api-key-openai "sk-..." --provider openai

# Multiple provider keys for multi-provider modes
doxa deep_research "prompt" --api-key-openai "sk-..." --api-key-perplexity "pplx-..."

# Testing with mock provider
doxa "test prompt" --api-key-mock "test-key" --provider mock
```

### Output Control
```bash
# Generate combined report from multiple providers
doxa "prompt" --combined

# Disable metadata headers and prompt section
doxa "prompt" --no-metadata

# Quiet mode for minimal output
doxa "prompt" --quiet
```

### Streaming output for immediate modes (P18, v3.1.0+)

Immediate-kind modes (`default`, `thinking`, `clarification`, `openai_reasoning`,
`perplexity_quick`, `perplexity_pro`, `perplexity_reasoning`, `gemini_quick`,
`gemini_pro`, `gemini_reasoning`) stream tokens
to stdout as they arrive — no progress bar, no operation-ID echo, no
resume hint, and no default result file. Use `--out` to redirect or tee:

```bash
# Stream to stdout (default)
doxa ask "what is X" --mode thinking

# Write to a file (truncate)
doxa ask "what is X" --mode thinking --out answer.md
doxa --out answer.md --provider mock "what is X"

# Tee to stdout AND a file
doxa ask "what is X" --mode thinking --out -,answer.md

# Append instead of truncating
doxa ask "what is X" --mode thinking --out answer.md --append
```

`openai_reasoning` is the built-in OpenAI immediate mode for grounded answers:
it sends `[modes.openai_reasoning.openai].reasoning_summary = "auto"` and
`web_search = true`. Custom OpenAI immediate modes can opt in or out with the
same namespace:

```toml
[modes.my_openai_reasoning]
provider = "openai"
model = "o3"
kind = "immediate"

[modes.my_openai_reasoning.openai]
reasoning_summary = "auto"
web_search = false  # set true to enable web_search_preview
```

Background-kind modes (e.g. `deep_research`, `quick_research`,
`exploration`, and the Gemini Deep Research modes: `gemini_quick_research`,
`gemini_exploration`, `gemini_deep_dive`, `gemini_tutorial`,
`gemini_solution`, `gemini_prd`, `gemini_tdd`, `gemini_deep_research`,
`gemini_comparison`) continue to use `--project` / `--output-dir` for
persistent output. `--out` is currently immediate-only.

### Cancelling a running operation

```bash
# Cancel an in-flight background operation by ID
doxa cancel a1b2c3d4-...

# Returns exit 6 if the operation isn't found; 0 otherwise.
# JSON envelope available:
doxa cancel a1b2c3d4-... --json
```

`doxa-research cancel` calls the provider's upstream cancel endpoint where
supported (OpenAI Responses API), then marks the local checkpoint as
cancelled. Providers without upstream cancel (e.g., Perplexity at the
time of writing) have the local checkpoint marked cancelled but the
upstream job runs to completion.

### Filtering modes by execution kind (P18)

Each mode is declared as `kind = "immediate"` (synchronous, streaming)
or `kind = "background"` (async, polling-loop). User-defined modes in
`~/.config/doxa-research/doxa-research.config.toml` should declare `kind` explicitly; missing
`kind` warns once and falls back to a substring heuristic on the model
name.

```bash
# Show only immediate-kind modes
doxa modes --kind immediate

# Show only background-kind modes
doxa modes --kind background
```

A misconfigured mode (e.g., declared `immediate` but using a
deep-research model) raises `ModeKindMismatchError` at submit time
with a config-edit suggestion — before any HTTP call hits the
provider.

### Interactive Mode
```bash
# Enter interactive prompt mode with enhanced UI
doxa -i
# or
doxa --interactive

# Interactive mode with specific provider
doxa -i --provider openai --api-key-openai "sk-..."

# Start with pre-configured settings and initial prompt
doxa -i --mode deep_research --provider openai "initial prompt text"

# Pipe prompt into interactive mode
echo "prompt from stdin" | doxa-research -i --prompt-file -

# Combined settings - all CLI arguments initialize the session
doxa -i --mode exploration --provider perplexity --async "test prompt"
```

Interactive mode features:
- **Command-line initialization**: All CLI arguments (mode, provider, prompt, async) initialize the session
- **Pre-populated prompt**: Initial prompt text appears in the input area, ready to edit or submit
- **Bordered text box**: Input appears in a blue-bordered frame with clear visual separation
- **Multiline input**: Enter to submit, multiple options for new lines:
  - **Shift+Return** - Works in modern terminals with CSI-u support (iTerm2, Warp, Windows Terminal, VSCode)
  - **Ctrl+J** - Universal option that works in all terminals (recommended)
  - **Option+Return** (Mac) or **Alt+Enter** (Linux/Windows) - Traditional fallback
- **Slash commands**:
  - `/help` - Show available commands
  - `/keybindings` - Show keyboard shortcuts (full-screen prompt UI)
  - `/mode [<name>]` - Change research mode or list available modes
  - `/provider [<name>]` - Set provider or list available providers
  - `/async` - Toggle async mode on/off
  - `/multiline` - Toggle multiline input mode (basic fallback prompt)
  - `/status` - Check last operation status
  - `/exit` or `/quit` - Exit interactive mode
- **Tab completion**: Start typing a slash command and press Tab for auto-completion
- **Unix shortcuts**: Ctrl+A (start), Ctrl+E (end), Ctrl+K (kill to end), Ctrl+U (kill to start)
- **Status bar**: Shows current mode and provider settings in help text
- **Override capability**: All CLI settings can be overridden using slash commands
- **Fallback mode**: Automatically switches to basic input when not in a terminal (e.g., piped input)

### Async Operations
```bash
# Submit research and exit immediately
doxa deep_research "long research topic" --async
# Output: Operation ID: research-20240803-143022-a1b2c3d4e5f6g7h8

# Check status later
doxa status research-20240803-143022-a1b2c3d4e5f6g7h8

# Resume operation
doxa resume research-20240803-143022-a1b2c3d4e5f6g7h8
```

### Provider Management
```bash
# List available providers and their status
doxa providers list

# Show API key configuration
doxa providers check

# List available models from all providers
doxa providers models

# List models from specific provider
doxa providers models --provider openai
doxa providers models -P perplexity
```

### List Operations
```bash
# List active operations
doxa list

# List all operations
doxa list --all
```

## Configuration

Configuration file is stored at `~/.config/doxa-research/doxa-research.config.toml`. Key settings:

- `default_project`: Default project name for outputs
- `default_mode`: Default research mode
- `base_output_dir`: Base directory for project outputs
- `poll_interval`: Seconds between status checks (default: 30)
- `max_wait`: Maximum wait time in minutes (default: 30)
- `parallel_providers`: Enable parallel provider execution
- `combine_reports`: Generate combined reports from multiple providers
- `execution.prompt_max_bytes`: Max bytes accepted from `--prompt-file` (file path or stdin). Files exceeding this are rejected before reading. Default: `1048576` (1 MiB).

### Configuration Profiles

Profiles let you keep shared config at the top level and define named overlays for different work contexts.

```toml
[general]
default_mode = "deep_research"

[profiles.fast.general]
default_mode = "thinking"
```

Selection precedence is `--profile` → `DOXA_PROFILE` → `general.default_profile` → no profile.

`doxa-research config get general.default_profile` reflects the **persisted pointer** in the file. `--profile` and `DOXA_PROFILE` are read-only runtime inputs — they never write back to `general.default_profile`. With persisted `general.default_profile = "fast"`, running `doxa-research --profile bar config get general.default_profile` returns `"fast"`; the runtime active selection is `bar`.

Profile CLI management is available through `doxa-research config profiles ...`.
Manual editing of `~/.config/doxa-research/doxa-research.config.toml` (or project-scoped
`./doxa.config.toml` / `./.doxa-research.config.toml`) still works when you need to
make larger structural changes.

#### Managing profiles from the CLI

The same profile from the hand-edit example above can be created end-to-end with:

```bash
doxa config profiles add fast
doxa config profiles set fast general.default_mode thinking
doxa config profiles set-default fast    # persists general.default_profile = "fast"
doxa config profiles current             # shows fast (from general.default_profile)
doxa config profiles list                # lists all profiles, marks active
doxa config profiles list --show-shadowed  # also shows user profiles shadowed by project profiles
doxa config profiles show fast --json    # full profile contents
doxa config profiles unset fast general.default_mode  # remove a single key
doxa config profiles remove fast         # delete the entire profile
doxa config profiles unset-default       # clear the persisted pointer
```

`--profile` is honored only by `list` and `current`. `show NAME` and mutator commands reject `--profile` because the profile they inspect or operate on is the positional argument.

### Migrating from earlier Doxa Research versions

Doxa Research previously read three different filenames depending on location. Starting with vX.Y.0, the canonical name is `doxa-research.config.toml` everywhere:

| Old | New |
|---|---|
| `~/.config/doxa-research/config.toml` | `~/.config/doxa-research/doxa-research.config.toml` |
| `./doxa.toml` | `./doxa.config.toml` *or* `./.doxa-research.config.toml` |
| `./.doxa-research/config.toml` | `./.doxa-research.config.toml` *or* `./doxa.config.toml` |

The old filenames are no longer read. Rename them with `mv`. If both `./doxa.config.toml` and `./.doxa-research.config.toml` exist in the same project, config-loading commands refuse to start until one is deleted. `doxa-research init --user` is a user-tier write and still creates or repairs `~/.config/doxa-research/doxa-research.config.toml` from that directory.

#### Change the default mode for a profile

```toml
[profiles.daily.general]
default_mode = "thinking"
default_project = "daily-notes"
```

```bash
doxa --profile daily "summarize today's notes"
```

#### Run all available deep-research providers

```toml
[profiles.all_deep.general]
default_mode = "deep_research"

[profiles.all_deep.modes.deep_research]
providers = ["openai", "perplexity"]
parallel = true
```

```bash
doxa --profile all_deep "compare vector databases"
```

> **Gemini support.** The `gemini` provider supports immediate grounded modes such as `gemini_quick`, `gemini_pro`, and `gemini_reasoning`, plus nine background deep-research modes (`gemini_quick_research`, `gemini_exploration`, `gemini_deep_dive`, `gemini_tutorial`, `gemini_solution`, `gemini_prd`, `gemini_tdd`, `gemini_deep_research`, `gemini_comparison`) added in P28.

#### Use one deep-research provider

```toml
[profiles.openai_deep.general]
default_mode = "deep_research"

[profiles.openai_deep.modes.deep_research]
providers = ["openai"]
parallel = false
```

```bash
doxa --profile openai_deep "research model routing"
```

#### Use an immediate default mode

```toml
[profiles.quick.general]
default_mode = "thinking"
```

```bash
doxa --profile quick "give me the short version"
```

#### Reserve an interactive default profile

```toml
[profiles.interactive.general]
default_mode = "interactive"
```

This profile can be stored, listed, and selected by P21 today (via hand-edit). The command behavior for a default interactive mode ships with a later interactive-default project.

#### Prepending a prompt prefix

A `prompt_prefix` value is prepended (with a blank line) to the user's prompt before it reaches the LLM. The mode's `system_prompt` is unaffected. Resolution walks a 4-level hierarchy from most-specific to least:

1. `[profiles.<active>.modes.<MODE>] prompt_prefix`
2. `[profiles.<active>] prompt_prefix`
3. `[modes.<MODE>] prompt_prefix`
4. `[general] prompt_prefix`

More-specific values **replace** less-specific ones (no concatenation). An empty string is treated as unset, so an inner-empty value falls through to the outer level.

```toml
[general]
prompt_prefix = "Be precise."

[modes.deep_research]
prompt_prefix = "Cite primary sources."

[profiles.deep.general]
default_mode = "deep_research"
prompt_prefix = "Be thorough. Cite primary sources where possible."

[profiles.deep.modes.deep_research]
prompt_prefix = "Be thorough. Cite primary sources. Include counter-arguments."
```

Resolution outcomes:

| Active profile | Mode | Resolved prefix |
|---|---|---|
| (none) | `default` | `Be precise.` (general) |
| (none) | `deep_research` | `Cite primary sources.` (modes.deep_research) |
| `deep` | `default` | `Be thorough. Cite primary sources where possible.` (profiles.deep) |
| `deep` | `deep_research` | `Be thorough. Cite primary sources. Include counter-arguments.` (profiles.deep.modes.deep_research) |

`doxa-research init` ships these profiles pre-populated in your config (`~/.config/doxa-research/doxa-research.config.toml`): `daily`, `quick`, `openai_deep`, `all_deep`, `interactive`, and `deep_research` — the last one demonstrates the `prompt_prefix` hierarchy end-to-end. Edit or delete them as you like.

## Provider Configuration

### OpenAI Provider

The OpenAI provider integrates with OpenAI's Chat Completions API for AI-powered research.

#### API Key Setup

Configure your OpenAI API key using one of these methods (in order of precedence):

1. **Command-line flag** (highest priority):
   ```bash
   doxa-research "prompt" --api-key-openai "sk-..." --provider openai
   ```

2. **Environment variable**:
   ```bash
   export OPENAI_API_KEY="sk-..."
   ```

3. **Configuration file** (`~/.config/doxa-research/doxa-research.config.toml`):
   ```toml
   [providers.openai]
   api_key = "${OPENAI_API_KEY}"  # Reference env var
   # Or directly:
   api_key = "sk-..."
   ```

#### Configuration Options

All OpenAI settings can be configured in `~/.config/doxa-research/doxa-research.config.toml`:

```toml
[providers.openai]
api_key = "${OPENAI_API_KEY}"  # API key (required)
model = "gpt-4o"                # Model to use (default: gpt-4o)
timeout = 30.0                  # Request timeout in seconds (default: 30.0)
temperature = 0.7               # Creativity/randomness (0.0-2.0, default: 0.7)
max_tokens = 4000               # Maximum response tokens (default: 4000)
```

#### Available Models

- `gpt-4o` (default) - Optimized GPT-4 model
- `gpt-4o-mini` - Smaller, faster, cost-effective version
- `gpt-3.5-turbo` - Fast and economical model

#### CLI Options

Override configuration via command-line:

```bash
# Set custom timeout
doxa "prompt" --provider openai --timeout 60.0

# Verbose mode shows configuration
doxa "prompt" --provider openai -v
```

#### Performance Tuning

**Temperature Settings:**
- `0.0-0.3`: Factual, consistent responses
- `0.4-0.7`: Balanced creativity (default)
- `0.8-1.2`: Creative, varied responses

**Timeout Recommendations:**
- Short prompts: 15-30 seconds
- Deep research: 60-120 seconds
- Complex analysis: 180+ seconds

### Gemini Deep Research costs (P28)

Gemini Deep Research is a paid-tier feature (Tier 1+ on Google AI Studio).
Estimated cost per task:
- `deep-research-preview-04-2026` (default for the 9 `gemini_*_research` modes): **$1–$3 per task**
- `deep-research-max-preview-04-2026` (deferred to a successor project): **$3–$7 per task**

Both agents are currently in **preview**; pricing and behavior may change.
The 60-minute hard research-time limit is enforced upstream — if you hit
this with longer prompts, set `[execution].max_wait = 60` in your config
(default is 30 minutes).

### Gemini modes (P28)

The 9 background deep-research modes added in P28 each map to the
`deep-research-preview-04-2026` model via the Gemini Interactions API:

| Mode | Description |
|---|---|
| `gemini_quick_research` | Quick Gemini Deep Research — short summary. |
| `gemini_exploration` | Open-ended exploratory Gemini Deep Research. |
| `gemini_deep_dive` | In-depth Gemini Deep Research dive. |
| `gemini_tutorial` | Tutorial-format Gemini Deep Research. |
| `gemini_solution` | Solution-recommendation Gemini Deep Research. |
| `gemini_prd` | PRD-format Gemini Deep Research. |
| `gemini_tdd` | TDD-plan Gemini Deep Research. |
| `gemini_deep_research` | Exhaustive Gemini Deep Research. |
| `gemini_comparison` | Comparison-table Gemini Deep Research. |

## Error Handling

### Authentication Errors
- **Invalid API Key**: Verify key at https://platform.openai.com/account/api-keys
- **Missing API Key**: Set via environment variable or config file

### Rate Limiting
- Automatic retry with exponential backoff (up to 3 attempts)
- Check usage at https://platform.openai.com/usage

### Timeout Errors
- Increase timeout: `--timeout 120`
- Check network connection
- Try simpler prompt first

### Network Errors
- Automatic connection retry
- Check API status at https://status.openai.com/

### Multi-Provider Failures
When running with multiple providers, a single provider failure does not abort the operation:
- The failed provider is logged with a warning (`⚠ Provider failed: <reason>`)
- Remaining providers continue polling normally
- Partial results from successful providers are saved to disk
- Only when **all** providers fail does the operation transition to a failed state

## Output Structure

### Ad-hoc Mode (default)
```
./2024-08-03_143022_default_openai_quantum-computing.md
./2024-08-03_143022_default_perplexity_quantum-computing.md
./2024-08-03_143022_default_combined_quantum-computing.md  # With --combined flag
```

### Output File Format

Each output file includes (unless `--no-metadata` is used):

```yaml
---
prompt: What is Python?
mode: default
provider: openai
model: gpt-4o
operation_id: research-20250802-154755-a38d159848984fa8
created_at: 2025-08-02T15:47:55.468596
---

### Prompt

```
What is Python?
```

[Research content follows...]
```

For modes with system prompts:
```yaml
---
query: explain kubernetes
mode: deep_research
provider: openai
model: gpt-4o
operation_id: research-20250802-154755-a38d159848984fa8
created_at: 2025-08-02T15:47:55.468596
---

### Prompt

```
System: Conduct comprehensive research with citations and multiple perspectives.
Organize findings clearly and highlight key insights.

User: explain kubernetes
```

[Research content follows...]
```

### Project Mode
```
./research-outputs/quantum_research/
  ├── 2024-08-03_143022_clarification_openai_quantum-security.md
  ├── 2024-08-03_150122_exploration_openai_quantum-security.md
  └── 2024-08-03_153022_deep_research_combined_quantum-security.md
```

## Development

### Bootstrap With `make`

`make` is bootstrap-only in this repo. Run `make env-check` first on a new machine or shell to verify the local environment before using `just`:

```bash
make env-check   # Verify uv, python3, and just are installed
make check-uv    # Verify uv is installed
make help        # Show bootstrap commands
```

For all development, quality, test, build, and release workflows, use `just`:

```bash
just --list              # Show all available tasks
just check               # Run code-quality checks for src/doxa_research/
just lint                # Lint src/doxa_research/
just typecheck           # Type-check src/doxa_research/
just fix                 # Auto-fix and format src/doxa_research/
just test-lint           # Lint doxa_test
just test-typecheck      # Type-check doxa_test
just test-fix            # Auto-fix and format doxa_test
just check-all           # Check src/doxa_research/ and doxa_test
just fix-all             # Fix and format src/doxa_research/ and doxa_test
just test                # Run ./doxa_test -r
just test-skip-interactive  # Run tests skipping interactive coverage
just test-vcr            # Run cassette-backed pytest coverage
just update-snapshots    # Regenerate pytest snapshot files
just clean               # Remove local build and cache artifacts
just install             # Sync dependencies with uv
just build               # Build distribution packages
just publish-test        # Publish to TestPyPI
just publish             # Publish to PyPI
```

### Running Tests

```bash
# Quick manual smoke check of the CLI itself (not the regression suite)
./doxa "test prompt" --provider mock
```

Use `doxa_test` for the actual regression suite. It mixes provider-agnostic CLI tests, mock-provider runs, interactive `pexpect` coverage, and provider-specific tests that only run when the needed API keys are present.

| Command | What it runs | When to use it |
|------|---------|---------|
| `just test` | Full `doxa_test` suite (`./doxa_test -r`) | Local full validation before merging |
| `./doxa_test -r` | All available tests for the current environment | Default comprehensive test run |
| `just test-skip-interactive` | Mock + provider-agnostic tests, skipping interactive `pexpect` cases | Fast CI-safe pass or non-TTY environments |
| `./doxa_test -r --interactive` | Interactive-only `pexpect` tests (`INT-*`) | Debugging terminal UI and interactive mode |
| `./doxa_test -r --provider mock` | Provider-agnostic tests plus mock-provider coverage | Fastest broad regression run with no real API keys |
| `./doxa_test -r --provider openai` | Provider-agnostic tests plus OpenAI-specific cases | Validating OpenAI integration with a real key |
| `./doxa_test -r --provider gemini` | Provider-agnostic tests plus Gemini-specific smoke cases | Validating Gemini runner wiring with a real key |
| `./doxa_test -r --all-providers` | Every provider test the suite knows about | Full provider matrix validation |
| `just test-extended` | Real-API provider contract tests (`pytest -m "extended and not extended_slow"`) | Nightly job; manual when investigating provider-API changes |
| `just test-extended-openai` / `just test-extended-perplexity` / `just test-extended-gemini` | Provider-scoped extended tests | Debugging one provider without running the full live contract matrix |
| `just test-live-api` | Real-API CLI workflow regression suite (`pytest -m "live_api and not extended_slow"`) | Weekly job (Sat 7pm PDT); manual when verifying user-visible streaming/file/secret behavior |
| `just test-live-api-openai` / `just test-live-api-perplexity` / `just test-live-api-gemini` | Provider-scoped live workflow tests | Debugging one provider's live CLI workflows |

`doxa_test -r` behaves like this:
- Always runs provider-agnostic tests.
- Always runs mock-provider tests because the suite auto-generates a mock key.
- Runs interactive tests unless you pass `--skip-interactive`.
- Skips OpenAI and Perplexity tests when their API keys are not set.

Useful commands:

```bash
# Full suite with whatever providers are available in your environment
./doxa_test -r

# Run tests skipping interactive (pexpect) tests — fast, CI-safe
./doxa_test -r --provider mock --skip-interactive
# or equivalently
just test-skip-interactive

# Run interactive tests only
./doxa_test -r --interactive

# Run the broad no-API-key path most contributors use
./doxa_test -r --provider mock

# Run OpenAI provider tests (requires API key)
./doxa_test -r --provider openai -t M8T

# Run all provider tests
./doxa_test -r --all-providers

# Run specific test pattern
./doxa_test -r -t "async" -v

# Save stdout/stderr and metadata for each test under test_outputs/
./doxa_test -r --provider mock --save-output
```

### Real Provider Extended Tests

The `extended` pytest marker is for live provider calls that mock tests cannot
prove. The default pytest selection excludes these tests, so they only run when
you ask for them explicitly.

Fast extended tests should stay intentional because they spend real API budget.
The current required live scenarios are:

| Scenario ID | What it proves | Cost behavior |
|------|---------|---------|
| `test_model_kind_matches_runtime_behavior[...]` | Every `KNOWN_MODELS` OpenAI, Perplexity, and Gemini model kind matches upstream runtime behavior | Immediate models complete; background models use best-effort cleanup |
| `test_ext_*_mode_*_passthrough` | OpenAI, Perplexity, and Gemini provider request settings reach the real provider-specific request shape | Non-live request-construction guard under the extended marker |
| `EXT-OAI-IMM-STREAM-TEE` | Immediate OpenAI streaming writes the same live text to stdout and an `--out` file | Completes immediately |
| `EXT-OAI-BG-JSON-AUTO-ASYNC` | Background `ask --json` auto-submits asynchronously without explicit `--async` | Cancels in cleanup |
| `EXT-OAI-BG-JSON-EXPLICIT-ASYNC` | Background `ask --async --json` returns the expected submit envelope | Cancels in cleanup |
| `EXT-OAI-BG-CANCEL-CMD` | `doxa-research cancel <op-id> --json` cancels a live OpenAI background job through the user-facing CLI | Cancels in test |
| `EXT-OAI-BG-ASYNC-BLOCKING-RESUME-COMPLETE` | Full lifecycle: async submit, blocking `resume`, completed checkpoint, and output file metadata | Runs to completion; opt-in with `DOXA_EXTENDED_SLOW=1` |

To run the fast live provider extended set manually:

```bash
# Export the provider keys you want this run to cover. If openai.env contains
# shell-style assignments:
set -a
source openai.env
set +a

# If openai.env is just the raw OpenAI key instead:
export OPENAI_API_KEY="$(cat openai.env)"

# Also export PERPLEXITY_API_KEY and GEMINI_API_KEY for those provider slices.

uv run pytest -m "extended and not extended_slow" tests/extended -v
```

To run only the slow full lifecycle tests:

```bash
DOXA_EXTENDED_SLOW=1 uv run pytest \
  -m "extended and extended_slow" \
  tests/extended \
  -v
```

The slow tests intentionally let background jobs finish so they can validate
blocking resume, final checkpoint state, result extraction, and output-file
metadata. Keep them out of routine local validation unless you are explicitly
checking those lifecycles.

Verification workflow used in this repo:

```bash
make env-check
just fix
just check
./doxa_test -r
just test-lint
just test-typecheck
just test-fix
just test-lint
just test-typecheck
```

## Environment Variables

- `OPENAI_API_KEY`: OpenAI API key
- `PERPLEXITY_API_KEY`: Perplexity API key
- `GEMINI_API_KEY`: Gemini API key
- `MOCK_API_KEY`: Mock provider API key (for testing)
- `DOXA_DEBUG`: Enable debug output (set to 1)

### API Key Precedence

API keys are resolved in the following order (highest to lowest priority):
1. Command-line arguments (`--api-key-openai`, `--api-key-perplexity`, `--api-key-gemini`, `--api-key-mock`)
2. Environment variables (`OPENAI_API_KEY`, `PERPLEXITY_API_KEY`, `GEMINI_API_KEY`, `MOCK_API_KEY`)
3. Configuration file (`~/.config/doxa-research/doxa-research.config.toml`)

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Validation error or user abort |
| 2 | Missing API key |
| 3 | Unsupported provider |
| 4 | API/network failure |
| 5 | Timeout exceeded |
| 6 | Operation not found |
| 7 | Config/IO error |
| 8 | Disk space error |
| 9 | API quota exceeded |
| 10 | Checkpoint corruption |
| 127 | Unexpected error |

## Commands Reference

### Main Commands

| Command | Description | Example |
|---------|-------------|---------|
| (default) | Run research with prompt | `doxa-research "your research prompt"` |
| ask | Run research with an explicit subcommand | `doxa-research ask "your research prompt"` |
| resume | Resume a checkpointed operation | `doxa-research resume research-20240803-143022-xxx` |
| cancel | Cancel an in-flight background operation | `doxa-research cancel research-20240803-143022-xxx` |
| init | Setup wizard for API keys | `doxa-research init` |
| status | Show operation details | `doxa-research status research-20240803-143022-xxx` |
| list | Show recent operations | `doxa-research list` |
| config | Inspect and edit configuration | `doxa-research config get general.default_mode` |
| modes | List research modes | `doxa-research modes list` |
| providers | Manage providers and models | `doxa-research providers list` |
| completion | Generate shell completion scripts | `doxa-research completion zsh` |
| help | Show help information | `doxa-research help [COMMAND]` |

### Providers Subcommands

| Subcommand | Description | Example |
|------------|-------------|---------|
| list | Show available providers and status | `doxa-research providers list` |
| models | List models from providers | `doxa-research providers models` |
| check | Show API key configuration | `doxa-research providers check` |
| --provider, -P | Filter by specific provider | `doxa-research providers models -P openai` |

## Version History

See [CHANGELOG.md](CHANGELOG.md) for the full version history.

## Shell completion

Generate an `eval`-able script:

```bash
eval "$(doxa-research completion bash)"   # or: zsh, fish
```

Persistent install (writes a fenced block to your shell's rc file):

```bash
doxa completion bash --install         # interactive: detect + prompt before overwrite
doxa completion bash --install --force # CI-friendly: write/overwrite silently
doxa completion bash --install --manual # print block + instructions; never write
```

After install, `doxa-research resume <TAB>`, `doxa-research status <TAB>`, `doxa-research config get <TAB>`,
`doxa-research modes list --name <TAB>`, and `doxa-research providers list --provider <TAB>` complete
with live data.

## JSON output

Every data/action admin command supports `--json`:

```bash
doxa status OP_ID --json | jq '.data.status'
doxa cancel OP_ID --json | jq '.data.status'
doxa providers list --json | jq '.data.providers[].name'
doxa list --json | jq '.data.operations[]'
```

See `docs/json-output.md` for the envelope contract and per-command schemas.

## License

[GNU Affero General Public License v3.0 or later](LICENSE) (AGPL-3.0-or-later).

In short: you may use, modify, and redistribute doxa-research, but if you offer a
modified version as a network service to others (a SaaS), you must also
make your full modified source code available to those users. See the
[GNU AGPL FAQ](https://www.gnu.org/licenses/why-affero-gpl.html) for the
rationale behind the network-service clause.

Copyright © 2025-2026 Steve Morin. Contributions are accepted under the
same AGPL-3.0-or-later terms.
