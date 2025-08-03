# Product Requirements Document – Thoth v1.4

---

## 1. Document Control

| Item | Value |
|------|-------|
| Author | System Design Team |
| Date | 30 Jul 2025 |
| Status | Production-Ready |
| Target Release | v1.4 |
| Document Version | 14.0 |

---

## 2. Executive Summary

Thoth is a command-line interface (CLI) tool that automates deep technical research using multiple LLM providers. It orchestrates parallel execution of OpenAI's Deep Research API and Perplexity's research models to deliver comprehensive, multi-perspective research reports. Thoth provides both synchronous and asynchronous operation modes, intelligent provider selection, and robust handling of long-running operations (5-30+ minutes).

### Core Value Propositions
- **Multi-provider intelligence**: Parallel execution of OpenAI and Perplexity for comprehensive results
- **Zero-configuration deployment**: Simplified dependency management eliminates setup complexity
- **Flexible operation modes**: Support both interactive (wait) and background (submit and exit) workflows
- **Production-ready reliability**: Checkpoint/resume, graceful error handling, and operation persistence
- **Simple output structure**: Intuitive file placement with ad-hoc and project modes
- **Mode chaining**: Seamless workflow from clarification through exploration to deep research

---

## 3. Product Overview

### Vision
Create the most efficient CLI tool for automated research that leverages the complementary strengths of multiple LLM providers to deliver superior research outcomes with minimal user friction.

### Target Users
- Researchers requiring deep technical analysis
- Developers needing comprehensive API documentation research
- Analysts conducting multi-source investigations
- Teams automating research workflows
- Individual users seeking one-command research capabilities

### Key Features
- Async-safe integration with OpenAI Deep Research (long-running, background jobs)
- Optional Perplexity provider for complementary research perspectives
- Zero-install execution capability
- Two output modes: ad-hoc (current directory) or project-based
- Interactive wizard for users who prefer guided prompts
- Single configuration file at `~/.thoth/config.toml`
- Comprehensive command-line interface with extensive options
- Mode chaining for multi-step research workflows

---

## 4. Glossary

| Term | Definition |
|------|------------|
| Mode | Workflow phase (clarification, exploration, deep_research, thinking) with its own prompt template |
| Model slot | Configuration section that maps to specific provider settings |
| Provider | LLM backend (openai, perplexity) |
| Operation ID | Unique identifier for each research operation (format: research-YYYYMMDD-HHMMSS-xxxxxxxxxxxxxxxx) |
| Background mode | Asynchronous execution where job is submitted and CLI exits immediately |
| Polling | Repeated status checks until a job completes or times out |
| Structured output | Files saved to disk (either current directory or project directory) |
| Ad-hoc mode | Default mode where files are saved to current working directory |
| Project mode | Mode where files are saved to `base_output_dir/project-name/` |
| Config file | Single TOML file at `~/.thoth/config.toml` containing all settings |
| Config version | Version number tracking configuration schema changes |
| Checkpoint | Saved state of an in-progress research operation for recovery |
| Slug | Sanitized version of the research query used in filenames (alphanumeric + hyphens) |
| Mode chaining | Sequential execution of modes where outputs from one mode become inputs to the next |
| Auto-input | Automatic use of previous mode outputs as inputs for the current mode |
| Single-provider mode | Mode configured to use one LLM provider |
| Multi-provider mode | Mode configured to use multiple LLM providers in parallel |
| Combined report | Synthesized report merging results from multiple providers |
| Valid output file | File matching pattern YYYY-MM-DD_HHMMSS_<mode>_<provider>_<slug>.(md|json) |

---

## 5. Objectives

1. **One-command research** with sensible defaults
2. **Async robustness** – never hang; offer `--async`, `--resume`, listing, and configurable polling
3. **Deterministic, auditable artifacts** for repeatability
4. **Zero system friction** via simplified dependency management
5. **Config-over-code** – all settings in single TOML file, overridable via CLI
6. **Multi-provider orchestration** – leverage multiple LLMs in parallel by default
7. **Graceful long operation handling** – support for 5-30+ minute research tasks
8. **POSIX compatibility** – run on macOS and Linux

---

## 6. Out of Scope (v1.4)

- Webhooks for completion notifications
- Private data integration (MCP)
- PDF/HTML export functionality
- Citation verification system
- Streaming token output display
- Concurrent multi-query execution
- Rich TUI with live visualizations
- Cloud storage integration
- Real-time collaboration features
- Web UI or API server mode
- Windows support

---

## 7. Assumptions

- Python ≥ 3.11 installed
- Users provide provider API keys via environment variables or config
- Deep Research jobs can take 5–30 minutes
- File paths must work on POSIX systems (macOS/Linux)
- Network connectivity available for API calls
- Sufficient disk space for output artifacts
- Users understand basic CLI operations
- Forward slashes used for all paths in configuration

---

## 8. Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| F-01 | Single config file `~/.thoth/config.toml` with all settings | Must |
| F-02 | Built-in defaults overridden by config file, overridden by CLI args | Must |
| F-03 | Create jobs in background mode; capture and return operation_id | Must |
| F-04 | Poll job status every n seconds (configurable); default 30s | Must |
| F-05 | Abort after configurable timeout; default 30 minutes | Must |
| F-06 | `--async` / `-A` submits job and exits immediately with operation_id | Must |
| F-07 | `--resume` / `-R` resumes an existing operation by ID | Must |
| F-08 | `list` command shows all active/recent operations | Must |
| F-09 | `status` command shows detailed status of specific operation | Must |
| F-10 | `init` command runs interactive setup wizard | Must |
| F-11 | Dual-provider execution for deep_research mode by default | Must |
| F-12 | Files created by default; filename pattern: `YYYY-MM-DD_HHMMSS_<mode>_<provider>_<slug>.md` | Must |
| F-13 | Filename deduplication with numeric suffix when conflicts occur | Should |
| F-14 | Config directory auto-created on first run | Must |
| F-15 | All diagnostics to stderr; DEBUG with `--verbose` or `THOTH_DEBUG=1` | Must |
| F-16 | Persistent default project via config file | Must |
| F-17 | Retry transient errors with exponential backoff | Should |
| F-18 | Mask API keys in all output (logs, errors, debug) | Must |
| F-19 | Checkpoint operations at meaningful state changes | Should |
| F-20 | Ad-hoc mode saves to current directory when no project specified | Must |
| F-21 | Project mode saves to `base_output_dir/project-name/` | Must |
| F-22 | Generate combined report from multi-provider results when configured | Should |
| F-23 | Path expansion for all file paths in config (handle ~) | Must |
| F-24 | Environment variable substitution in config file | Must |
| F-25 | Modes can reference previous outputs via --input-file flag | Must |
| F-26 | Mode-specific auto_input overrides global execution.auto_input | Must |
| F-27 | When mode specifies "previous", automatically look for latest output | Must |
| F-28 | For multi-provider previous steps, use latest file from each provider | Must |
| F-29 | If one provider fails in multi-provider mode, continue with others | Must |
| F-30 | --output-dir flag overrides all other output location logic | Must |
| F-31 | Support --query-file flag for reading query from file | Must |
| F-32 | If no previous outputs found in mode chaining, warn and continue | Must |
| F-33 | Mode chaining should gracefully handle missing provider outputs | Must |
| F-34 | Research operations require both mode and query parameters | Must |
| F-35 | Use strict pattern matching for output file discovery | Must |
| F-36 | Provide detailed provider progress tracking | Should |
| F-37 | When --provider specified with multi-provider mode, use only that provider | Must |
| F-38 | Progress percentages estimated based on typical operation times | Should |
| F-39 | Handle checkpoint file corruption gracefully | Must |
| F-40 | Automatic retry on transient network errors | Must |
| F-41 | Clear error messages for disk space, API quota, and network issues | Must |
| F-42 | Configuration file includes version field | Should |
| F-43 | Operation IDs use 16-character UUID suffix for uniqueness | Must |
| F-44 | Combined reports saved as <timestamp>_<mode>_combined_<slug>.md | Must |
| F-45 | "Thinking" mode is single-provider only | Must |

---

## 9. Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| N-01 | Poll requests ≤ 2 per minute (30-second default interval) |
| N-02 | Tool runs on POSIX systems (macOS and Linux) |
| N-03 | Graceful exit on interrupt (Ctrl-C) with checkpoint save |
| N-04 | Startup time < 100ms with cached dependencies |
| N-05 | Time to first result < 30 seconds (Perplexity) |
| N-06 | Checkpoint save time < 500ms |
| N-07 | Provider success rate > 95% |
| N-08 | Recovery success > 99% from valid checkpoints |
| N-09 | Memory usage < 200MB typical, < 500MB peak |
| N-10 | Handle symlinks by resolving to absolute paths |
| N-11 | Operation ID collision probability < 0.0001% with 16-char UUID |

---

## 10. Command-Line Interface

### 10.1 Command Structure

```bash
thoth [COMMAND] [OPTIONS]
thoth MODE QUERY [OPTIONS]

Commands:
  (default)     Run research with mode and query
  init          Initialize configuration with setup wizard
  status        Check status of specific operation
  list          List all active/recent operations
```

### 10.2 Usage Examples

```bash
# Ad-hoc mode - saves to current directory
thoth deep_research "impact of quantum computing"
# Creates: 
#   ./2024-08-03_143022_deep_research_openai_impact-quantum.md
#   ./2024-08-03_143022_deep_research_perplexity_impact-quantum.md
#   ./2024-08-03_143022_deep_research_combined_impact-quantum.md (if combine_reports=true)

# Project mode - saves to project directory
thoth deep_research "quantum cryptography" --project quantum_research
# Creates: 
#   ./research-outputs/quantum_research/2024-08-03_143022_deep_research_openai_quantum-crypto.md
#   ./research-outputs/quantum_research/2024-08-03_143022_deep_research_perplexity_quantum-crypto.md

# Single provider operation (overrides multi-provider mode)
thoth deep_research "quantum algorithms" --provider openai
# Creates only:
#   ./2024-08-03_143022_deep_research_openai_quantum-algorithms.md

# Read query from file
thoth deep_research --query-file ./research_query.txt

# Read query from stdin (max 1MB)
echo "quantum computing security" | thoth deep_research --query-file -

# Mode chaining example
thoth clarification "quantum computing security implications"
# Creates: ./2024-08-03_143022_clarification_openai_quantum-computing.md

thoth exploration --input-file ./2024-08-03_143022_clarification_openai_quantum-computing.md
# Or with auto-input (if configured):
thoth exploration --auto

# Async submission (returns immediately)
thoth deep_research "quantum cryptography" --async
# Output: Operation ID: research-20240803-143022-a1b2c3d4e5f6g7h8

# Resume operation
thoth --resume research-20240803-143022-a1b2c3d4e5f6g7h8

# Check status
thoth status research-20240803-143022-a1b2c3d4e5f6g7h8

# List operations
thoth list

# Setup wizard
thoth init
```

### 10.3 Options Reference

| Long | Short | Type | Description |
|------|-------|------|-------------|
| --mode | -m | TEXT | Research mode (can be first positional argument) |
| --query | -q | TEXT | Research query (can be second positional argument) |
| --query-file | -Q | PATH | Read query from file (use '-' for stdin, max 1MB) |
| --async | -A | flag | Submit and exit immediately |
| --resume | -R | ID | Resume existing operation by ID |
| --project | -p | TEXT | Project name for output organization |
| --set-default-project | -S | TEXT | Save project as default in config |
| --output-dir | -o | PATH | Override output directory for this run |
| --model | -M | TEXT | Override model for this run |
| --provider | -P | TEXT | Use single provider: openai or perplexity |
| --api-key | -k | TEXT | Override API key for this run |
| --raw | -r | flag | Output raw JSON |
| --fast | -f | flag | Use faster/cheaper model variant |
| --no-code | | flag | Disable code interpreter (OpenAI) |
| --poll-interval | -I | INT | Seconds between polls (default: 30) |
| --max-wait | -W | INT | Maximum wait in minutes (default: 30) |
| --input-file | | PATH | Use output from previous mode as input |
| --auto | | flag | Automatically use latest relevant output as input |
| --verbose | -v | flag | Enable debug logging |
| --quiet | | flag | Suppress progress output |
| --version | -V | flag | Show version and exit |
| --help | -h | flag | Show help and exit |

### 10.4 Commands Reference

| Command | Description | Example |
|---------|-------------|---------|  
| init | Run interactive setup wizard | `thoth init` |
| status ID | Show detailed operation status | `thoth status research-20240803-143022-a1b2c3d4e5f6g7h8` |
| list | List all operations | `thoth list` |

### 10.5 Validation Rules
- `--async` cannot be used with `--resume`
- Files are created by default
- `--api-key` requires `--provider` to be specified
- Mode and query can be positional or use `--mode` and `--query`
- `list` command ignores all other options except `--verbose`
- `--output-dir` overrides all other output location logic
- `--query-file` and `--query` are mutually exclusive
- `--input-file` and `--auto` cannot be used together
- When `--provider` is used with multi-provider mode, only that provider runs

---

## 11. Interactive Mode

### 11.1 Setup Wizard (`thoth init`)

```
Welcome to Thoth Research Assistant Setup!

Checking environment...
✓ Python 3.11.5 detected
✓ UV package manager available
✓ Operating System: macOS 14.2 (supported)

Configuration file will be created at: ~/.thoth/config.toml

? Enter OpenAI API key (or press Enter to use $OPENAI_API_KEY): ***********
✓ OpenAI API key validated

? Enter Perplexity API key (or press Enter to use $PERPLEXITY_API_KEY): ***********
✓ Perplexity API key validated

? Base output directory for projects [./research-outputs]: 
? Default project name (empty for ad-hoc mode) []: 

? Default polling interval in seconds [30]: 
? Maximum wait time in minutes [30]: 

? Enable parallel provider execution by default? [Y/n]: 
? Enable mode chaining auto-input by default? [Y/n]: 
? Generate combined reports for multi-provider modes? [Y/n]:

Configuration saved to ~/.thoth/config.toml (version 1.0)

You can now run: thoth deep_research "your query"
```

---

## 12. Exit Codes

| Code | Meaning | Example |
|------|---------|---------|  
| 0 | Success | Research completed successfully |
| 1 | Validation error or user abort | Invalid arguments or Ctrl-C |
| 2 | Missing API key | Required API key not found |
| 3 | Unsupported provider | Unknown provider specified |
| 4 | API/network failure | Connection failed after retries |
| 5 | Timeout exceeded | Operation exceeded max-wait |
| 6 | Operation not found | Invalid operation ID |
| 7 | Config/IO error | Cannot read/write files |
| 8 | Disk space error | Insufficient disk space |
| 9 | API quota exceeded | Provider quota limit reached |
| 10 | Checkpoint corruption | Checkpoint file corrupted (recreated) |
| 127 | Unexpected error | Programming bug |

---

## 13. Configuration File

Single configuration file at `~/.thoth/config.toml`:

```toml
# Thoth Configuration File
# Environment variables can be referenced with ${VAR_NAME}
# All paths use forward slashes, even on Windows (automatically converted)

version = "1.0"  # Configuration schema version

[general]
default_project = ""  # Empty string means ad-hoc mode (current directory)
default_mode = "deep_research"

[paths]
base_output_dir = "./research-outputs"  # Base directory for project outputs
checkpoint_dir = "~/.thoth/checkpoints"  # Checkpoint storage (symlinks resolved)

[execution]
poll_interval = 30        # seconds
max_wait = 30            # minutes  
parallel_providers = true
retry_attempts = 3
retry_delay = 2          # seconds (exponential backoff)
auto_input = true        # Enable automatic input from previous modes

[providers.openai]
api_key = "${OPENAI_API_KEY}"
model = "o1-deep-research"
tools = ["web_search", "code_interpreter"]
reasoning_summary = "auto"

[providers.openai.fast]
model = "o1-mini"
max_thinking_tokens = 10000

[providers.perplexity]
api_key = "${PERPLEXITY_API_KEY}"
model = "sonar-pro"
search_domains = ["arxiv.org", "nature.com", "pubmed.ncbi.nlm.nih.gov"]
search_recency_filter = "month"
return_citations = true
max_tokens = 4000

[modes.thinking]
provider = "openai"  # Single-provider mode
model = "gpt-4o-mini"
temperature = 0.4
system_prompt = "You are a helpful assistant for quick analysis."

[modes.clarification]
provider = "openai"  # Single-provider mode
model = "gpt-4o-mini"
system_prompt = "Help clarify ambiguous queries before deep research."

[modes.exploration]
provider = "openai"  # Single-provider mode
model = "gpt-4o"
system_prompt = "Provide initial exploration and identify research directions."
previous = "clarification"  # Indicates this mode typically follows clarification
auto_input = true           # Automatically use latest clarification output

[modes.deep_research]
providers = ["openai", "perplexity"]  # Multi-provider mode
parallel = true
system_prompt = """
Conduct comprehensive research with citations and multiple perspectives.
Organize findings clearly and highlight key insights.
"""
previous = "exploration"    # Can chain from exploration
auto_input = true

[output]
format = "markdown"          # "markdown" or "json"
include_metadata = true
combine_reports = true       # Generate combined report from multi-provider results
timestamp_format = "%Y-%m-%d_%H%M%S"

[logging]
level = "INFO"               # DEBUG, INFO, WARNING, ERROR
log_file = "~/.thoth/thoth.log"
max_log_size = "10MB"
```

---

## 14. Available Research Modes

### Built-in Modes

1. **Clarification Mode**
   - Provider: Single (OpenAI)
   - Purpose: Clarify ambiguous queries and refine research questions
   - Default Model: gpt-4o-mini
   - Chains to: Exploration

2. **Exploration Mode**  
   - Provider: Single (OpenAI)
   - Purpose: Initial exploration of topics, alternatives, and trade-offs
   - Default Model: gpt-4o
   - Chains from: Clarification
   - Chains to: Deep Research

3. **Deep Research Mode**
   - Providers: Multiple (OpenAI + Perplexity)
   - Purpose: Comprehensive multi-perspective research with citations
   - Default Models: o1-deep-research (OpenAI), sonar-pro (Perplexity)
   - Chains from: Exploration
   - Parallel execution by default

4. **Thinking Mode**
   - Provider: Single (OpenAI)
   - Purpose: Quick analysis and simple questions
   - Default Model: gpt-4o-mini
   - Single-provider only

5. **Deep Dive Mode**
   - Provider: Configurable
   - Purpose: Technical deep dives into specific technologies or APIs
   - Chains to: Tutorial

6. **Tutorial Mode**
   - Provider: Configurable
   - Purpose: Detailed tutorials with examples and implementation steps
   - Chains from: Deep Dive
   - Chains to: Solution

7. **Solution Mode**
   - Provider: Configurable
   - Purpose: Design specific solutions to problems
   - Chains from: Tutorial
   - Chains to: PRD

8. **PRD Mode**
   - Provider: Configurable
   - Purpose: Generate Product Requirements Documents
   - Chains from: Solution
   - Chains to: TDD

9. **TDD Mode**
   - Provider: Configurable
   - Purpose: Create Technical Design Documents
   - Chains from: PRD

---

## 15. User Experience

### 15.1 Progress Display

```
Research: Quantum Computing Impact
Mode: deep_research | Started: 14:30:22

┌─────────────────────────────────────────────────────┐
│ OpenAI Deep Research    ████████░░ 80% Analyzing     │
│ Perplexity Research     ██████████ 100% Complete     │
└─────────────────────────────────────────────────────┘

Operation ID: research-20240803-143022-a1b2c3d4e5f6g7h8
Elapsed: 12:45 | Next poll: 15s

[Note: Progress percentages are estimated based on typical operation times]
```

### 15.2 Status Display

```
$ thoth status research-20240803-143022-a1b2c3d4e5f6g7h8

Operation Details:
─────────────────
ID:        research-20240803-143022-a1b2c3d4e5f6g7h8
Query:     Impact of quantum computing on cryptography
Mode:      deep_research
Status:    running
Started:   2024-08-03 14:30:22
Elapsed:   12 minutes
Project:   quantum_research

Provider Status:
───────────────
OpenAI:      ▶ Running (80%) - Analyzing 15 sources
Perplexity:  ✓ Complete - Results saved

Output Files:
────────────
./research-outputs/quantum_research/
  ├── 2024-08-03_143022_deep_research_perplexity_impact-quantum.md
  └── 2024-08-03_143022_deep_research_combined_impact-quantum.md
```

### 15.3 List Display

```
$ thoth list

Active Research Operations:
──────────────────────────

ID                                       Query                    Status    Elapsed  Mode
research-20240803-143022-a1b2c3d4e5f6g7  Impact of quantum...    running   12m      deep_research
research-20240803-141555-b4c5d6e7f8g9h0  Post-quantum crypto...   complete  45m      deep_research  
research-20240803-140233-e7f8g9h0i1j2k3  Clarify requirements...  complete  2m       clarification

Use 'thoth status <ID>' for details
```

### 15.4 Error Messages

```
# Disk space error
[red]Error:[/red] Insufficient disk space to save results
[yellow]Suggestion:[/yellow] Free up disk space and try again

# API quota error
[red]API quota exceeded for openai[/red]
Provider perplexity failed: API quota exceeded
[yellow]Warning:[/yellow] Partial failure: openai failed

# Network error with automatic retry
[yellow]Warning:[/yellow] Network error, retrying... (attempt 2/3)
[green]✓[/green] Retry successful

# Checkpoint corruption
[yellow]Warning:[/yellow] Checkpoint file corrupted: ~/.thoth/checkpoints/research-20240803-143022-a1b2c3d4e5f6g7h8.json
[yellow]Creating new checkpoint. Previous state lost.[/yellow]
```

---

## 16. Security and Privacy

### 16.1 API Key Management
- Environment variables as primary method
- Config file with `${VAR}` substitution
- Automatic masking in all output
- Never stored in checkpoints
- Validation during `init` setup

### 16.2 Data Handling
- All data stored locally
- User controls all paths
- No telemetry or tracking
- Checkpoints contain only metadata
- Standard OS file permissions
- Symlinks resolved to absolute paths

### 16.3 Best Practices
- Input sanitization for filenames
- Path traversal prevention
- No shell command execution
- Secure temp file handling
- HTTPS-only API calls
- 1MB limit on stdin input

---

## 17. Troubleshooting

### Common Issues

1. **"No previous outputs found for auto-input"**
   - Ensure previous mode was run in the same directory/project
   - Check that output files match the expected pattern
   - Use `--input-file` to manually specify the input

2. **"Configuration version mismatch"**
   - Run `thoth init` to update your configuration
   - Backup your current config if you have custom settings

3. **"Provider failed: Network error"**
   - Check internet connectivity
   - Verify API endpoints are accessible
   - Tool will automatically retry 3 times

4. **"API quota exceeded"**
   - Wait for quota reset (usually hourly/daily)
   - Use `--provider` to try a different provider
   - Check your API plan limits

5. **"Operation ID not found"**
   - Verify the complete operation ID (16-char suffix)
   - Check if operation completed and was cleaned up
   - List active operations with `thoth list`

---

## 18. Future Enhancements

### Version 1.5
- Webhook notifications for completion
- Anthropic Claude provider support
- HTML/PDF export functionality
- Cost tracking and estimation
- Multiple provider specification (--providers)
- Configuration migration system

### Version 1.6
- Plugin architecture for custom providers
- Web UI companion application
- Knowledge graph generation
- API server mode
- Windows support (if demand exists)
- Provider-specific progress tracking

---

## 19. Checkpoint File Schema

```json
{
  "id": "research-20240803-143022-a1b2c3d4e5f6g7h8",
  "query": "Impact of quantum computing on cryptography",
  "mode": "deep_research",
  "status": "running",
  "created_at": "2024-08-03T14:30:22.123456",
  "updated_at": "2024-08-03T14:42:15.789012",
  "providers": {
    "openai": {
      "status": "running",
      "progress": 0.8
    },
    "perplexity": {
      "status": "completed"
    }
  },
  "output_paths": {
    "perplexity": "/path/to/output.md"
  },
  "error": null,
  "progress": 0.9,
  "project": "quantum_research",
  "input_files": [
    "/path/to/previous/output.md"
  ]
}
```

---

## 20. Future Considerations

### 20.1 Progress Reporting Granularity
**Current State**: Progress percentages are estimated based on typical operation times.

**Future Enhancement**: 
- Add configurable progress estimates in the config file
- Support provider APIs that report actual progress when available

### 20.2 Combined Report Conflict Resolution
**Current State**: Combined reports concatenate results from different providers with section headers.

**Future Enhancement**:
- Identify and highlight conflicting information between providers
- Add a summary section synthesizing key findings across providers

### 20.3 Auto-input Time Window
**Current State**: Auto-input finds the latest files from the previous mode without time constraints.

**Future Enhancement**:
- Add optional `auto_input_max_age` config setting
- Prevent accidentally using very old outputs in long-running projects

### 20.4 Provider Failover Strategy
**Current State**: When a provider fails, the system continues with other providers and notes the failure.

**Future Enhancement**:
- Automatic retry with different models
- Different behaviors based on error type

### 20.5 Operation Cleanup Policy
**Current State**: No automatic cleanup of old operations.

**Future Enhancement**:
- Automatic cleanup of completed operations older than N days
- Add `thoth list --clean` option to remove old operations
- Configurable retention policies

---

## End of Thoth v1.4 PRD

This specification provides a complete foundation for implementing Thoth as a robust research automation tool. All major design decisions have been made, with comprehensive coverage of:

✓ Clear provider selection behavior  
✓ Well-defined file matching patterns  
✓ Comprehensive error handling  
✓ Configuration versioning system  
✓ Detailed progress tracking approach  
✓ Complete CLI interface specification  
✓ Robust checkpoint/resume functionality  

The specification addresses all previously outstanding questions and provides clear implementation guidance for a production-quality tool on macOS and Linux environments.