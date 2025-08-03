# Thoth - AI-Powered Research Assistant

Thoth is a command-line tool that automates deep technical research using multiple LLM providers. It orchestrates parallel execution of OpenAI's Deep Research API and Perplexity's research models to deliver comprehensive, multi-perspective research reports.

## Features

- **Multi-provider intelligence**: Parallel execution of OpenAI and Perplexity for comprehensive results
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

```bash
# Clone the repository
git clone <repository-url>
cd thoth

# Make the script executable
chmod +x thoth

# Install to system (optional)
sudo make install
```

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
   thoth providers -- --list
   ```

4. **Run your first research:**
   ```bash
   thoth "impact of quantum computing on cryptography"
   ```

## Usage

### Basic Research
```bash
# Quick research (uses default mode)
thoth "your research query"

# Run research with a specific mode
thoth deep_research "your research query"
thoth clarification "ambiguous topic needing clarity"
thoth exploration "broad topic to explore"
thoth thinking "quick analysis task"
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
thoth "query" --api-key-openai "sk-..." --provider openai

# Multiple provider keys for multi-provider modes
thoth deep_research "query" --api-key-openai "sk-..." --api-key-perplexity "pplx-..."

# Testing with mock provider
thoth "test query" --api-key-mock "test-key" --provider mock
```

### Output Control
```bash
# Generate combined report from multiple providers
thoth "query" --combined

# Disable metadata headers and prompt section
thoth "query" --no-metadata

# Quiet mode for minimal output
thoth "query" --quiet
```

### Async Operations
```bash
# Submit research and exit immediately
thoth deep_research "long research topic" --async
# Output: Operation ID: research-20240803-143022-a1b2c3d4e5f6g7h8

# Check status later
thoth status research-20240803-143022-a1b2c3d4e5f6g7h8

# Resume operation
thoth --resume research-20240803-143022-a1b2c3d4e5f6g7h8
```

### Provider Management
```bash
# List available providers and their status
thoth providers -- --list

# Show API key configuration
thoth providers -- --keys

# List available models from all providers
thoth providers -- --models

# List models from specific provider
thoth providers -- --models --provider openai
thoth providers -- --models -P perplexity
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
query: What is Python?
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

```bash
# Run from source
./thoth --help

# Run tests
make test

# Lint code
make lint

# Format code
make format

# Test with mock provider (no API keys needed)
./thoth "test query" --provider mock
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
| (default) | Run research with query | `thoth "your research query"` |
| init | Setup wizard for API keys | `thoth init` |
| status | Show operation details | `thoth status research-20240803-143022-xxx` |
| list | Show recent operations | `thoth list` |
| providers | Manage providers and models | `thoth providers -- --list` |
| help | Show help information | `thoth help [COMMAND]` |

### Providers Command Options

| Option | Description | Example |
|--------|-------------|---------|  
| --list | Show available providers and status | `thoth providers -- --list` |
| --models | List models from providers | `thoth providers -- --models` |
| --keys | Show API key configuration | `thoth providers -- --keys` |
| --provider, -P | Filter by specific provider | `thoth providers -- --models -P openai` |

**Note**: Use `--` separator before options to prevent parsing conflicts.

## Version History

- **v2.2**: Provider discovery, provider-specific API keys, enhanced metadata
- **v2.1**: Providers command, dynamic model listing  
- **v2.0**: Mode chaining, checkpoint/resume, operation management
- **v1.5**: Core research functionality with multiple modes

## License

[License information here]