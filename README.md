# Thoth - AI-Powered Research Assistant

Thoth is a command-line tool that automates deep technical research using multiple LLM providers. It orchestrates parallel execution of OpenAI's Deep Research API and Perplexity's research models to deliver comprehensive, multi-perspective research reports.

## Features

- **Multi-provider intelligence**: Parallel execution of OpenAI and Perplexity for comprehensive results
- **Zero-configuration deployment**: UV inline script dependencies eliminate setup complexity
- **Flexible operation modes**: Support both interactive (wait) and background (submit and exit) workflows
- **Production-ready reliability**: Checkpoint/resume, graceful error handling, and operation persistence
- **Simple output structure**: Intuitive file placement with ad-hoc and project modes
- **Mode chaining**: Seamless workflow from clarification through exploration to deep research

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

3. **Run your first research:**
   ```bash
   thoth deep_research "impact of quantum computing on cryptography"
   ```

## Usage

### Basic Research
```bash
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
./2024-08-03_143022_deep_research_openai_quantum-computing.md
./2024-08-03_143022_deep_research_perplexity_quantum-computing.md
./2024-08-03_143022_deep_research_combined_quantum-computing.md
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
```

## Environment Variables

- `OPENAI_API_KEY`: OpenAI API key
- `PERPLEXITY_API_KEY`: Perplexity API key
- `THOTH_DEBUG`: Enable debug output (set to 1)

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

## License

[License information here]