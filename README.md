# Thoth - AI-Powered Research Assistant

[![PyPI version](https://img.shields.io/pypi/v/thoth.svg)](https://pypi.org/project/thoth/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/smorin/thoth/actions/workflows/ci.yml/badge.svg)](https://github.com/smorin/thoth/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Thoth is a command-line tool that automates deep technical research using multiple LLM providers. It orchestrates parallel execution of OpenAI's Deep Research API and Perplexity's research models to deliver comprehensive, multi-perspective research reports.

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

Origin of the name: Thoth (also spelled Tehuti) is the god of wisdom, writing, hieroglyphs, science, magic, art, and judgment. He is often depicted as a man with the head of an ibis or a baboon, animals sacred to him. Thoth is also associated with the moon and is considered the scribe of the gods.

## Prerequisites

- Python ≥ 3.11
- [UV](https://github.com/astral-sh/uv) package manager
- OpenAI API key (for OpenAI provider)
- Perplexity API key (for Perplexity provider)

## Installation

### From PyPI (recommended)

```bash
# Install and run with uvx (no setup required)
uvx thoth

# Or install permanently with uv
uv tool install thoth

# Or with pip
pip install thoth
```

### From source

```bash
# Clone the repository
git clone https://github.com/smorin/thoth.git
cd thoth

# Install in editable mode
uv sync

# Or run directly without installing
./thoth --help
```

## Authentication

Authentication — recommended order:

1. **Environment variables (recommended)**:
   ```bash
   export OPENAI_API_KEY=sk-...
   export PERPLEXITY_API_KEY=pplx-...
   ```

2. **Config file** (persistent, per-machine): `~/.thoth/config.toml`
   ```toml
   [providers.openai]
   api_key = "sk-..."
   ```

3. **CLI flags** (last resort — exposes keys in shell history; not recommended):
   ```bash
   thoth --api-key-openai sk-... deep_research "..."
   ```

For related command help, run `thoth config --help`.

## Quick Start

1. **Initialize configuration:**
   ```bash
   thoth init
   ```

2. **Set API keys:**
   ```bash
   export OPENAI_API_KEY="your-openai-key"
   export PERPLEXITY_API_KEY="your-perplexity-key"
   ```

3. **Check provider configuration:**
   ```bash
   thoth providers list
   ```

4. **Run your first research:**
   ```bash
   thoth "impact of quantum computing on cryptography"
   ```

## Usage

### Basic Research
```bash
# Quick research (uses default mode)
thoth "your research prompt"

# Run research with a specific mode
thoth deep_research "your research prompt"
thoth clarification "ambiguous topic needing clarity"
thoth exploration "broad topic to explore"
thoth thinking "quick analysis task"

# Use specific provider
thoth "explain quantum computing" --provider openai
thoth deep_research "AI safety" --provider openai --timeout 120
```

### Project-Based Research
```bash
# Save outputs to a project directory
thoth deep_research "quantum algorithms" --project quantum_research
```

### Mode Chaining
```bash
# Start with clarification
thoth clarification "quantum computing security"

# Then explore with auto-input from previous mode
thoth exploration --auto

# Finally, deep research with all context
thoth deep_research --auto
```

### Provider-Specific API Keys
```bash
# Use specific API key for a provider
thoth "prompt" --api-key-openai "sk-..." --provider openai

# Multiple provider keys for multi-provider modes
thoth deep_research "prompt" --api-key-openai "sk-..." --api-key-perplexity "pplx-..."

# Testing with mock provider
thoth "test prompt" --api-key-mock "test-key" --provider mock
```

### Output Control
```bash
# Generate combined report from multiple providers
thoth "prompt" --combined

# Disable metadata headers and prompt section
thoth "prompt" --no-metadata

# Quiet mode for minimal output
thoth "prompt" --quiet
```

### Streaming output for immediate modes (P18, v3.1.0+)

Immediate-kind modes (`default`, `thinking`, `clarification`) stream tokens
to stdout as they arrive — no progress bar, no operation-ID echo, no
resume hint. Use `--out` to redirect or tee:

```bash
# Stream to stdout (default)
thoth ask "what is X" --mode thinking

# Write to a file (truncate)
thoth ask "what is X" --mode thinking --out answer.md

# Tee to stdout AND a file
thoth ask "what is X" --mode thinking --out -,answer.md

# Append instead of truncating
thoth ask "what is X" --mode thinking --out answer.md --append
```

Background-kind modes (e.g. `deep_research`, `quick_research`,
`exploration`, etc.) continue to use `--project` / `--output-dir` for
persistent output. `--out` is currently immediate-only.

### Cancelling a running operation

```bash
# Cancel an in-flight background operation by ID
thoth cancel a1b2c3d4-...

# Returns exit 6 if the operation isn't found; 0 otherwise.
# JSON envelope available:
thoth cancel a1b2c3d4-... --json
```

`thoth cancel` calls the provider's upstream cancel endpoint where
supported (OpenAI Responses API), then marks the local checkpoint as
cancelled. Providers without upstream cancel (e.g., Perplexity at the
time of writing) have the local checkpoint marked cancelled but the
upstream job runs to completion.

### Filtering modes by execution kind (P18)

Each mode is declared as `kind = "immediate"` (synchronous, streaming)
or `kind = "background"` (async, polling-loop). User-defined modes in
`~/.config/thoth/config.toml` should declare `kind` explicitly; missing
`kind` warns once and falls back to a substring heuristic on the model
name.

```bash
# Show only immediate-kind modes
thoth modes --kind immediate

# Show only background-kind modes
thoth modes --kind background
```

A misconfigured mode (e.g., declared `immediate` but using a
deep-research model) raises `ModeKindMismatchError` at submit time
with a config-edit suggestion — before any HTTP call hits the
provider.

### Interactive Mode
```bash
# Enter interactive prompt mode with enhanced UI
thoth -i
# or
thoth --interactive

# Interactive mode with specific provider
thoth -i --provider openai --api-key-openai "sk-..."

# Start with pre-configured settings and initial prompt
thoth -i --mode deep_research --provider openai "initial prompt text"

# Pipe prompt into interactive mode
echo "prompt from stdin" | thoth -i --prompt-file -

# Combined settings - all CLI arguments initialize the session
thoth -i --mode exploration --provider perplexity --async "test prompt"
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
  - `/keybindings` - Show keyboard shortcuts
  - `/mode [<name>]` - Change research mode or list available modes
  - `/provider [<name>]` - Set provider or list available providers
  - `/async` - Toggle async mode on/off
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
thoth deep_research "long research topic" --async
# Output: Operation ID: research-20240803-143022-a1b2c3d4e5f6g7h8

# Check status later
thoth status research-20240803-143022-a1b2c3d4e5f6g7h8

# Resume operation
thoth resume research-20240803-143022-a1b2c3d4e5f6g7h8
```

### Provider Management
```bash
# List available providers and their status
thoth providers list

# Show API key configuration
thoth providers check

# List available models from all providers
thoth providers models

# List models from specific provider
thoth providers models --provider openai
thoth providers models -P perplexity
```

### List Operations
```bash
# List active operations
thoth list

# List all operations
thoth list --all
```

## Configuration

Configuration file is stored at `~/.thoth/config.toml`. Key settings:

- `default_project`: Default project name for outputs
- `default_mode`: Default research mode
- `base_output_dir`: Base directory for project outputs
- `poll_interval`: Seconds between status checks (default: 30)
- `max_wait`: Maximum wait time in minutes (default: 30)
- `parallel_providers`: Enable parallel provider execution
- `combine_reports`: Generate combined reports from multiple providers
- `execution.prompt_max_bytes`: Max bytes accepted from `--prompt-file` (file path or stdin). Files exceeding this are rejected before reading. Default: `1048576` (1 MiB).

## Provider Configuration

### OpenAI Provider

The OpenAI provider integrates with OpenAI's Chat Completions API for AI-powered research.

#### API Key Setup

Configure your OpenAI API key using one of these methods (in order of precedence):

1. **Command-line flag** (highest priority):
   ```bash
   thoth "prompt" --api-key-openai "sk-..." --provider openai
   ```

2. **Environment variable**:
   ```bash
   export OPENAI_API_KEY="sk-..."
   ```

3. **Configuration file** (`~/.thoth/config.toml`):
   ```toml
   [providers.openai]
   api_key = "${OPENAI_API_KEY}"  # Reference env var
   # Or directly:
   api_key = "sk-..."
   ```

#### Configuration Options

All OpenAI settings can be configured in `~/.thoth/config.toml`:

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
thoth "prompt" --provider openai --timeout 60.0

# Verbose mode shows configuration
thoth "prompt" --provider openai -v
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
just check               # Run code-quality checks for src/thoth/
just lint                # Lint src/thoth/
just typecheck           # Type-check src/thoth/
just fix                 # Auto-fix and format src/thoth/
just test-lint           # Lint thoth_test
just test-typecheck      # Type-check thoth_test
just test-fix            # Auto-fix and format thoth_test
just check-all           # Check src/thoth/ and thoth_test
just fix-all             # Fix and format src/thoth/ and thoth_test
just test                # Run ./thoth_test -r
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
./thoth "test prompt" --provider mock
```

Use `thoth_test` for the actual regression suite. It mixes provider-agnostic CLI tests, mock-provider runs, interactive `pexpect` coverage, and provider-specific tests that only run when the needed API keys are present.

| Command | What it runs | When to use it |
|------|---------|---------|
| `just test` | Full `thoth_test` suite (`./thoth_test -r`) | Local full validation before merging |
| `./thoth_test -r` | All available tests for the current environment | Default comprehensive test run |
| `just test-skip-interactive` | Mock + provider-agnostic tests, skipping interactive `pexpect` cases | Fast CI-safe pass or non-TTY environments |
| `./thoth_test -r --interactive` | Interactive-only `pexpect` tests (`INT-*`) | Debugging terminal UI and interactive mode |
| `./thoth_test -r --provider mock` | Provider-agnostic tests plus mock-provider coverage | Fastest broad regression run with no real API keys |
| `./thoth_test -r --provider openai` | Provider-agnostic tests plus OpenAI-specific cases | Validating OpenAI integration with a real key |
| `./thoth_test -r --all-providers` | Every provider test the suite knows about | Full provider matrix validation |

`thoth_test -r` behaves like this:
- Always runs provider-agnostic tests.
- Always runs mock-provider tests because the suite auto-generates a mock key.
- Runs interactive tests unless you pass `--skip-interactive`.
- Skips OpenAI and Perplexity tests when their API keys are not set.

Useful commands:

```bash
# Full suite with whatever providers are available in your environment
./thoth_test -r

# Run tests skipping interactive (pexpect) tests — fast, CI-safe
./thoth_test -r --provider mock --skip-interactive
# or equivalently
just test-skip-interactive

# Run interactive tests only
./thoth_test -r --interactive

# Run the broad no-API-key path most contributors use
./thoth_test -r --provider mock

# Run OpenAI provider tests (requires API key)
./thoth_test -r --provider openai -t M8T

# Run all provider tests
./thoth_test -r --all-providers

# Run specific test pattern
./thoth_test -r -t "async" -v

# Save stdout/stderr and metadata for each test under test_outputs/
./thoth_test -r --provider mock --save-output
```

Verification workflow used in this repo:

```bash
make env-check
just fix
just check
./thoth_test -r
just test-lint
just test-typecheck
just test-fix
just test-lint
just test-typecheck
```

## Environment Variables

- `OPENAI_API_KEY`: OpenAI API key
- `PERPLEXITY_API_KEY`: Perplexity API key
- `MOCK_API_KEY`: Mock provider API key (for testing)
- `THOTH_DEBUG`: Enable debug output (set to 1)

### API Key Precedence

API keys are resolved in the following order (highest to lowest priority):
1. Command-line arguments (`--api-key-openai`, `--api-key-perplexity`, `--api-key-mock`)
2. Environment variables (`OPENAI_API_KEY`, `PERPLEXITY_API_KEY`, `MOCK_API_KEY`)
3. Configuration file (`~/.thoth/config.toml`)

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
| (default) | Run research with prompt | `thoth "your research prompt"` |
| init | Setup wizard for API keys | `thoth init` |
| status | Show operation details | `thoth status research-20240803-143022-xxx` |
| list | Show recent operations | `thoth list` |
| providers | Manage providers and models | `thoth providers list` |
| help | Show help information | `thoth help [COMMAND]` |

### Providers Subcommands

| Subcommand | Description | Example |
|------------|-------------|---------|
| list | Show available providers and status | `thoth providers list` |
| models | List models from providers | `thoth providers models` |
| check | Show API key configuration | `thoth providers check` |
| --provider, -P | Filter by specific provider | `thoth providers models -P openai` |

## Version History

See [CHANGELOG.md](CHANGELOG.md) for the full version history.

## Shell completion

Generate an `eval`-able script:

```bash
eval "$(thoth completion bash)"   # or: zsh, fish
```

Persistent install (writes a fenced block to your shell's rc file):

```bash
thoth completion bash --install         # interactive: detect + prompt before overwrite
thoth completion bash --install --force # CI-friendly: write/overwrite silently
thoth completion bash --install --manual # print block + instructions; never write
```

After install, `thoth resume <TAB>`, `thoth status <TAB>`, `thoth config get <TAB>`,
`thoth modes list --name <TAB>`, and `thoth providers list --provider <TAB>` complete
with live data.

## JSON output

Every data/action admin command supports `--json`:

```bash
thoth status OP_ID --json | jq '.data.status'
thoth providers list --json | jq '.data.providers[].name'
thoth list --json | jq '.data.operations[]'
```

See `docs/json-output.md` for the envelope contract and per-command schemas.

## License

[MIT License](LICENSE)
