# Product Requirements Document – Doxa Research v2.0

---

## 1. Document Control

| Item | Value |
|------|-------|
| Author | System Design Team |
| Date | 02 Aug 2025 |
| Status | Production-Ready |
| Target Release | v2.0 |
| Document Version | 20.0 |

### Changes in Version 20.0
- Updated version to v2.0 to reflect comprehensive feature additions
- Added new commands: update, clean, config, export, import
- Added advanced provider features from implementation plan
- Added multi-provider coordination features
- Added missing core features as new requirements
- Added --auto flag for mode chaining
- Added adaptive polling intervals
- Added operation lifecycle management
- Added shell completion support
- All features from implementation plan v4.0 incorporated

---

## 2. Executive Summary

Doxa Research is a command-line interface (CLI) tool that automates deep technical research using multiple LLM providers. **The primary use case is simple: just give it a query and get comprehensive research results in your current directory.** While Doxa Research supports advanced features like mode selection, project organization, and async operations, the default experience is optimized for immediate, zero-configuration research.

### Core Value Propositions
- **Instant research**: Just `doxa-research "your query"` – no mode selection needed
- **Multi-provider intelligence**: Automatic parallel execution of OpenAI and Perplexity
- **Zero-configuration deployment**: Works immediately with API keys
- **Current directory output**: Results appear right where you are working
- **Advanced features when needed**: Full mode control, projects, and async operations available
- **Production-ready reliability**: Checkpoint/resume, graceful error handling, and operation persistence

---

## 3. Product Overview

### Vision
Create the simplest yet most powerful research tool where users can get comprehensive research results with a single command, while preserving advanced capabilities for power users.

### Target Users
- **Primary**: Anyone needing quick research results with minimal friction
- **Secondary**:
  - Researchers requiring deep technical analysis
  - Developers needing comprehensive API documentation research
  - Analysts conducting multi-source investigations
  - Teams automating research workflows

### Key Features
- **Default deep research mode**: No need to specify mode for common use cases
- **Automatic file output**: Results saved to current directory by default
- **Smart defaults**: Sensible configuration out of the box
- **Progressive complexity**: Simple for basic use, powerful when needed
- **Multi-provider results**: Automatic parallel execution for comprehensive coverage
- **Long operation handling**: Graceful handling of 5-30+ minute research tasks

---

## 4. Glossary

| Term | Definition |
|------|------------|
| Default mode | When no mode is specified, uses a special 'default' mode that passes queries directly to the LLM without any system prompt. Files created with this mode include 'default' in the filename pattern. NOTE: Quick mode (`doxa-research "query"`) uses "default" mode, NOT "deep_research" |
| Quick mode | Simplified invocation with just a query, using all defaults |
| Mode | Workflow phase (clarification, exploration, deep_research, thinking) with its own prompt template |
| Provider | LLM backend (openai, perplexity, mock) |
| Mock provider | Test provider that returns static responses WITHOUT requiring API keys (accepts any value as dummy key for testing) |
| Operation ID | Unique identifier for each research operation (format: research-YYYYMMDD-HHMMSS-xxxxxxxxxxxxxxxx) |
| Background mode | Asynchronous execution where job is submitted and CLI exits immediately |
| Ad-hoc mode | Default mode where files are saved to current working directory |
| Project mode | Mode where files are saved to `base_output_dir/project-name/` |
| Combined report | Synthesized report merging results from multiple providers (requires --combined flag) |
| Output file | File created in format: YYYY-MM-DD_HHMMSS_deep_research_<provider>_<slug>.md |
| Mode chaining | Automatic flow from one mode to another using --auto flag |
| Adaptive polling | Dynamic adjustment of status check intervals based on operation characteristics |
| Provider fallback | Automatic failover to alternate provider on failure |

---

## 5. Objectives

1. **Zero-friction research** – just query and go
2. **One-command simplicity** with sensible defaults
3. **Current directory convenience** – results appear where you work
4. **Progressive disclosure** – advanced features available but not required
5. **Multi-provider by default** – comprehensive results without configuration
6. **Async robustness** – never hang; handle long operations gracefully
7. **Deterministic artifacts** – predictable file naming and locations
8. **POSIX compatibility** – run on macOS and Linux
9. **Testability** – mock provider enables comprehensive testing without API keys

---

## 6. Out of Scope (v2.0)

- Webhooks for completion notifications
- Private data integration (MCP)
- Citation verification system
- Streaming token output display
- Concurrent multi-query execution
- Rich TUI with live visualizations
- Cloud storage integration
- Real-time collaboration features
- Web UI or API server mode
- Windows support
- Plugin system (deferred to future release)

---

## 7. Assumptions

- Python ≥ 3.11 installed
- Users provide provider API keys via environment variables or config
- Deep Research jobs can take 5–30 minutes
- Most users want deep research results in their current directory
- Users prefer simple commands over complex configuration
- File paths must work on POSIX systems (macOS/Linux)
- Network connectivity available for API calls
- Sufficient disk space for output artifacts
- Mock provider used for testing and development

---

## 8. Functional Requirements

### Core Requirements

| ID | Requirement | Priority | Test ID |
|----|-------------|----------|---------|
| F-01 | When no mode specified, use 'default' mode with no system prompt and include 'default' in filename | Must | T-MODE-01 |
| F-02 | Accept query as single positional argument: `doxa-research "query"` | Must | T-CLI-01 |
| F-03 | Save outputs to current directory by default | Must | T-OUT-01 |
| F-04 | Support full mode specification for advanced users | Must | T-MODE-02 |
| F-05 | Single config file `~/.doxa-research/config.toml` with all settings | Must | T-CFG-01 |
| F-06 | Built-in defaults overridden by config file, overridden by CLI args | Must | T-CFG-02 |
| F-07 | Create jobs in background mode; capture and return operation_id | Must | T-ASYNC-01 |
| F-08 | Poll job status every n seconds (configurable); default 30s | Must | T-ASYNC-02 |
| F-09 | Abort after configurable timeout; default 30 minutes | Must | T-ASYNC-03 |
| F-10 | `--async` / `-A` submits job and exits immediately with operation_id | Must | T-ASYNC-04 |
| F-11 | `--resume` / `-R` resumes an existing operation by ID | Must | T-ASYNC-05 |
| F-12 | `list` command shows all active/recent operations | Must | T-CMD-01 |
| F-13 | `status` command shows detailed status of specific operation | Must | T-CMD-02 |
| F-14 | `init` command runs interactive setup wizard | Must | T-CMD-03 |
| F-15 | Dual-provider execution for deep_research mode by default | Must | T-PROV-01 |
| F-16 | Files created by default; filename pattern: `YYYY-MM-DD_HHMMSS_<mode>_<provider>_<slug>.md` | Must | T-OUT-02 |
| F-17 | Show clear progress during research execution | Must | T-UX-01 |
| F-18 | Display output file locations upon completion | Must | T-UX-02 |
| F-19 | Mask API keys in all output (logs, errors, debug) - keys must be replaced with pattern like sk-*** in stdout/stderr | Must | T-SEC-01 |
| F-20 | Generate combined report from multi-provider results with --combined flag | Must | T-OUT-03 |
| F-21 | Support individual provider files by default (no combined report) | Must | T-OUT-04 |
| F-22 | Clear error messages for missing API keys | Must | T-ERR-01 |
| F-23 | Automatic retry on transient network errors | Must | T-NET-01 |
| F-24 | Path expansion for all file paths in config (handle ~) | Must | T-CFG-03 |
| F-25 | Environment variable substitution in config file | Must | T-CFG-04 |

### Additional Quick Mode Requirements

| ID | Requirement | Priority | Test ID |
|----|-------------|----------|---------|
| F-26 | `doxa-research "query"` executes deep research in current directory | Must | T-QUICK-01 |
| F-27 | Show simple progress indicator for quick mode (includes operation ID in verbose mode) | Must | T-QUICK-02 |
| F-28 | Display final output filenames prominently | Must | T-QUICK-03 |
| F-29 | Minimal output during execution unless --verbose | Must | T-QUICK-04 |
| F-30 | Help text shows quick mode as primary usage pattern | Must | T-HELP-01 |
| F-31 | Default mode must pass user query directly to LLM without any system prompt modifications | Must | T-MODE-03 |

### Testing and Error Handling Requirements

| ID | Requirement | Priority | Test ID |
|----|-------------|----------|---------|
| F-32 | Mock provider must work without any API keys for testing | Must | T-MOCK-01 |
| F-33 | All error messages must go to stderr, not stdout (Rich console UI to stdout is correct) | Must | T-ERR-02 |
| F-34 | Mode and provider validation must happen before API key checks | Must | T-VAL-01 |
| F-35 | Commands must return proper exit codes: 0=success, 1=general error, 2=usage error | Must | T-EXIT-01 |
| F-36 | Output directories must be created automatically if they don't exist | Must | T-OUT-05 |
| F-37 | Init command must work with custom config directories via XDG_CONFIG_HOME | Must | T-CFG-05 |
| F-38 | Implement --quiet flag to suppress non-essential output | Must | T-UX-03 |
| F-39 | Support -P as short form for --provider flag | Must | T-CLI-03 |
| F-40 | Implement --config flag for custom config file location | Must | T-CFG-06 |

### New Command Requirements (v2.0)

| ID | Requirement | Priority | Test ID |
|----|-------------|----------|---------|
| F-41 | Implement `update` command to fix stale operation statuses | Must | T-CMD-04 |
| F-42 | Implement `clean` command with filtering options for checkpoint management | Must | T-CMD-05 |
| F-43 | Implement `config` command for configuration management | Must | T-CMD-06 |
| F-44 | Implement `export` command to export research results | Must | T-CMD-07 |
| F-45 | Implement `import` command to import research data | Must | T-CMD-08 |
| F-46 | Add --force flag support where applicable | Must | T-CLI-04 |
| F-47 | Add --dry-run flag for preview operations | Must | T-CLI-05 |

### Advanced Mode Requirements (v2.0)

| ID | Requirement | Priority | Test ID |
|----|-------------|----------|---------|
| F-48 | Implement --auto flag for automatic mode chaining | Must | T-MODE-04 |
| F-49 | Support reading from previous output files automatically | Must | T-MODE-05 |
| F-50 | Implement symlink path resolution | Must | T-FILE-01 |
| F-51 | Add max file size limits for input files | Must | T-FILE-02 |
| F-52 | Create operation metadata tracking | Must | T-META-01 |

### Provider Enhancement Requirements (v2.0)

| ID | Requirement | Priority | Test ID |
|----|-------------|----------|---------|
| F-53 | Implement retry logic with exponential backoff | Must | T-NET-02 |
| F-54 | Add streaming response support for providers | Should | T-PROV-02 |
| F-55 | Implement token counting and display | Should | T-PROV-03 |
| F-56 | Add cost estimation and tracking | Should | T-PROV-04 |
| F-57 | Support temperature control from config | Should | T-PROV-05 |
| F-58 | Add response caching mechanism | Should | T-CACHE-01 |
| F-59 | Implement rate limit handling with backoff | Must | T-NET-03 |

### Multi-Provider Coordination (v2.0)

| ID | Requirement | Priority | Test ID |
|----|-------------|----------|---------|
| F-60 | Implement provider fallback chains | Must | T-MULTI-01 |
| F-61 | Add cost optimization routing | Should | T-MULTI-02 |
| F-62 | Create quality-based provider selection | Should | T-MULTI-03 |
| F-63 | Implement provider health checks | Must | T-MULTI-04 |
| F-64 | Add unified error handling across providers | Must | T-MULTI-05 |
| F-65 | Implement cross-provider deduplication | Should | T-MULTI-06 |

### Progress and UX Enhancements (v2.0)

| ID | Requirement | Priority | Test ID |
|----|-------------|----------|---------|
| F-66 | Implement adaptive polling intervals | Should | T-UX-05 |
| F-67 | Add operation lifecycle management with states: queued→running→completed/failed/cancelled, with proper transitions | Must | T-ASYNC-06 |
| F-68 | Create first-time setup flow improvements | Should | T-UX-06 |
| F-69 | Add helpful tips for new users | Should | T-UX-07 |
| F-70 | Implement shell completion support | Should | T-CLI-06 |

### Configuration Enhancements (v2.0)

| ID | Requirement | Priority | Test ID |
|----|-------------|----------|---------|
| F-71 | Add config validation command | Must | T-CFG-07 |
| F-72 | Support per-project configuration | Should | T-CFG-08 |
| F-73 | Implement config migration for version updates | Must | T-CFG-09 |
| F-74 | Add config export/import functionality | Should | T-CFG-10 |
| F-75 | Support environment-specific configs | Should | T-CFG-11 |

### Clean Command Features (v2.0)

| ID | Requirement | Priority | Test ID |
|----|-------------|----------|---------|
| F-76 | Support --in-progress, --completed, --failed filters | Must | T-CLEAN-01 |
| F-77 | Add --days filter for age-based cleanup | Must | T-CLEAN-02 |
| F-78 | Implement --pattern filter for pattern matching | Should | T-CLEAN-03 |
| F-79 | Add --keep-recent option to preserve N most recent | Must | T-CLEAN-04 |
| F-80 | Detect and clean orphaned output files | Should | T-CLEAN-05 |

### Critical Infrastructure Requirements (v2.0)

| ID | Requirement | Priority | Test ID |
|----|-------------|----------|---------|
| F-81 | Implement graceful shutdown on Ctrl-C with checkpoint save | Must | T-SIG-01 |
| F-82 | Implement checkpoint corruption detection and recovery | Must | T-ASYNC-07 |

### OpenAI Provider Requirements (v2.0)

| ID | Requirement | Priority | Test ID |
|----|-------------|----------|---------|
| F-83 | OpenAI streaming response support | Must | T-OAI-01 |
| F-84 | OpenAI token counting and display | Must | T-OAI-02 |
| F-85 | OpenAI cost estimation and tracking | Should | T-OAI-03 |
| F-86 | OpenAI partial response saving on failure | Must | T-OAI-04 |
| F-87 | OpenAI model selection from config | Must | T-OAI-05 |

### Perplexity Provider Requirements (v2.0)

| ID | Requirement | Priority | Test ID |
|----|-------------|----------|---------|
| F-88 | Perplexity citation extraction and formatting | Must | T-PPLX-01 |
| F-89 | Perplexity web search mode support | Must | T-PPLX-02 |
| F-90 | Perplexity academic search mode | Should | T-PPLX-03 |
| F-91 | Perplexity real-time data queries | Must | T-PPLX-04 |
| F-92 | Perplexity search depth control | Should | T-PPLX-05 |
| F-93 | Perplexity source filtering | Should | T-PPLX-06 |
| F-94 | Perplexity source reliability scores | Should | T-PPLX-07 |

### Advanced Multi-Provider Requirements (v2.0)

| ID | Requirement | Priority | Test ID |
|----|-------------|----------|---------|
| F-95 | Provider load balancing | Should | T-MULTI-07 |
| F-96 | Circuit breaker pattern for provider failures | Must | T-MULTI-08 |
| F-97 | Dynamic provider selection based on query type | Should | T-MULTI-09 |
| F-98 | Partial result handling across providers | Must | T-MULTI-10 |
| F-99 | Provider capability matching | Should | T-MULTI-11 |
| F-100 | Cross-provider performance monitoring | Should | T-MULTI-12 |


---

## 9. Non-Functional Requirements

| ID | Requirement | Test ID |
|----|-------------|---------|
| N-01 | First result visible within 30 seconds | T-PERF-01 |
| N-02 | Tool runs on POSIX systems (macOS and Linux) | T-PLAT-01 |
| N-03 | Graceful exit on interrupt (Ctrl-C) with checkpoint save | T-SIG-01 |
| N-04 | Startup time < 100ms with cached dependencies | T-PERF-02 |
| N-05 | Clear progress indication during long operations | T-UX-04 |
| N-06 | Memory usage < 200MB typical, < 500MB peak | T-PERF-03 |
| N-07 | Operation ID collision probability < 0.0001% | T-ID-01 |
| N-08 | Simple error messages for common issues | T-ERR-03 |
| N-09 | All errors to stderr for proper shell scripting | T-ERR-04 |
| N-10 | Exit codes follow POSIX conventions | T-EXIT-02 |

---

## 10. Command-Line Interface

### 10.1 Command Structure

```bash
# PRIMARY USAGE - Quick Mode
doxa "QUERY"                    # Deep research with output to current directory

# ADVANCED USAGE - Full Control
doxa MODE QUERY [OPTIONS]       # Specify mode and options
doxa [COMMAND] [OPTIONS]        # Run specific commands

Commands:
  (default)     Run research (uses 'default' mode when no mode specified, NOT deep_research)
  init          Initialize configuration with setup wizard
  status        Check status of specific operation
  list          List all active/recent operations
  update        Fix stale operation statuses
  clean         Clean up old checkpoints and files
  config        Manage configuration
  export        Export research results
  import        Import research data
  help          Show help for commands
```

### 10.2 Usage Examples

#### Quick Mode (Primary Use Case)

```bash
# SIMPLEST USAGE - just provide a query (no system prompt added)
doxa "impact of quantum computing on cryptography"
# This sends your exact query to the LLM without modification
# Creates in current directory:
#   ./2024-08-03_143022_default_openai_impact-of-quantum-computing.md
#   ./2024-08-03_143022_default_perplexity_impact-of-quantum-computing.md

# With combined report (requires flag)
doxa "impact of quantum computing on cryptography" --combined
# Also creates:
#   ./2024-08-03_143022_default_combined_impact-of-quantum-computing.md

# More quick examples
doxa "best practices for API design"
doxa "comparison of React vs Vue frameworks"
doxa "how does TCP congestion control work"

# Quick mode with single provider
doxa "kubernetes networking explained" --provider openai
doxa "kubernetes networking explained" -P openai  # Short form

# Testing with mock provider (no API key needed)
doxa "test query" --provider mock
doxa "test query" -P mock  # Short form
```

#### Advanced Mode Examples

```bash
# Specify a different mode
doxa thinking "quick analysis of JSON vs YAML"
doxa clarification "what are the implications of quantum computing"
doxa exploration "modern web authentication methods"

# Project mode - organize outputs
doxa "quantum cryptography" --project quantum_research
# Creates: ./research-outputs/quantum_research/...

# Async submission for long research
doxa "comprehensive analysis of distributed systems" --async
# Output:
# Research submitted
# Operation ID: research-20240803-143022-a1b2c3d4e5f6g7h8
# Check later with: doxa-research status research-20240803-143022-a1b2c3d4e5f6g7h8

# Mode chaining workflow with --auto
doxa clarification "building scalable microservices"
doxa exploration --auto  # Uses previous output automatically
doxa deep_research --auto  # Full research based on exploration

# Read query from file
doxa --query-file ./complex_research_query.txt

# Pipe query from another command
echo "analyze security implications of WebAssembly" | doxa-research --query-file -

# Quiet mode for minimal output
doxa "database optimization techniques" -Q

# Custom config file
doxa "machine learning trends" --config ~/projects/ml/doxa-research-config.toml
```

#### New Command Examples (v2.0)

```bash
# Update stale operations
doxa update                     # Update all stale operations
doxa update --dry-run          # Preview what would be updated

# Clean old checkpoints
doxa clean --days 30           # Remove operations older than 30 days
doxa clean --failed            # Remove only failed operations
doxa clean --keep-recent 10    # Keep 10 most recent operations
doxa clean --pattern "test*"   # Remove operations matching pattern

# List with filters
doxa list --in-progress        # Show only active operations
doxa list --completed          # Show only completed operations
doxa list --days 7             # Show operations from last 7 days

# Configuration management
doxa config validate           # Validate current configuration
doxa config export > backup.toml  # Export configuration
doxa config import backup.toml    # Import configuration

# Export/Import results
doxa export research-20240803-143022-xxx --format json
doxa import research-backup.json
```

### 10.3 Options Reference

| Long | Short | Type | Description |
|------|-------|------|-------------|
| --mode | -m | TEXT | Research mode (defaults to 'default' when not specified) |
| --query | -q | TEXT | Research query (alternative to positional) |
| --query-file | -Q | PATH | Read query from file (use '-' for stdin) |
| --async | -A | flag | Submit and exit immediately |
| --resume | -R | ID | Resume existing operation by ID |
| --project | -p | TEXT | Project name for output organization |
| --output-dir | -o | PATH | Override output directory |
| --provider | -P | TEXT | Use single provider: openai, perplexity, or mock |
| --combined | | flag | Generate combined report from multiple providers |
| --quiet | -Q | flag | Minimal output during execution |
| --verbose | -v | flag | Enable detailed logging |
| --help | -h | flag | Show help and exit |
| --config | -c | PATH | Read config from this file or dir |
| --auto | | flag | Use previous output automatically (mode chaining) |
| --force | -f | flag | Force operation without confirmation |
| --dry-run | | flag | Preview operation without executing |

### 10.4 Commands Reference

| Command | Description | Example |
|---------|-------------|---------|
| (default) | Run research with query | `doxa-research "your research query"` |
| init | Setup wizard for API keys | `doxa-research init` |
| status ID | Show operation details | `doxa-research status research-20240803-143022-xxx` |
| list | Show recent operations | `doxa-research list` |
| update | Fix stale operation statuses | `doxa-research update --dry-run` |
| clean | Clean up old checkpoints | `doxa-research clean --days 30` |
| config | Manage configuration | `doxa-research config validate` |
| export | Export research results | `doxa-research export operation-id` |
| import | Import research data | `doxa-research import file.json` |

### 10.5 Exit Codes

| Code | Meaning | Example |
|------|---------|---------|
| 0 | Success | Research completed successfully |
| 1 | General error | API key missing, network error, etc. |
| 2 | Usage error | Invalid command, missing required arguments |

### 10.6 Help Text Structure

```
Doxa Research - AI-Powered Research Assistant

USAGE:
    doxa-research "QUERY"                    # Quick research (recommended)
    doxa-research MODE QUERY [OPTIONS]       # Advanced usage
    doxa-research COMMAND [OPTIONS]          # Run commands

QUICK START:
    doxa-research "impact of quantum computing"
    doxa-research "best practices for REST APIs"

EXAMPLES:
    # Simple research (saves to current directory)
    doxa-research "how does blockchain consensus work"

    # Research with single provider
    doxa-research "machine learning optimization" --provider openai
    doxa-research "machine learning optimization" -P openai

    # Test with mock provider (no API key needed)
    doxa-research "test query" --provider mock
    doxa-research "test query" -P mock

    # Async for long research
    doxa-research "comprehensive review of database architectures" --async

    # Generate combined report
    doxa-research "cloud architecture patterns" --combined

    # Clean old operations
    doxa-research clean --days 30

COMMANDS:
    init      Setup API keys and configuration
    status    Check research operation status
    list      List recent research operations
    update    Fix stale operation statuses
    clean     Clean up old checkpoints
    config    Manage configuration

OPTIONS:
    -P, --provider    Use specific provider (openai/perplexity/mock)
    -A, --async       Submit and exit (check status later)
    -p, --project     Organize outputs in project directory
    -v, --verbose     Show detailed progress
    -h, --help        Show full help
    -Q, --quiet       Minimal output during execution
    --combined        Generate combined report from providers
    --auto            Use previous output automatically
    -c, --config      Use custom config file

Run 'doxa-research --help' for complete options and advanced usage.
```

---

## 11. User Experience

### 11.1 Quick Mode Experience

```bash
$ doxa "explain how DNS resolution works"

Researching: explain how DNS resolution works
Mode: default | Providers: OpenAI + Perplexity

Progress: [00:02:15] Next check in 15s, timeout in 27:45
⠹ OpenAI: Analyzing topic...
⠸ Perplexity: Searching sources...
Progress: [00:05:30] Next check in 30s, timeout in 24:30
⠼ OpenAI: Deep research in progress...
⠴ Perplexity: Analyzing 12 sources...
✓ Perplexity: Complete
Progress: [00:08:15] Next check in 30s, timeout in 21:45
⠦ OpenAI: Synthesizing findings...
✓ OpenAI: Complete

Research completed in 8m 32s

Files created:
  • 2024-08-03_143022_deep_research_openai_explain-how-dns-resolution.md
  • 2024-08-03_143022_deep_research_perplexity_explain-how-dns-resolution.md

To generate a combined report, run with --combined flag
```

### 11.2 First-Time User Experience

```bash
$ doxa "what is quantum computing"

⚠️  No API keys found. Let's set them up:

? Enter OpenAI API key (or press Enter to use $OPENAI_API_KEY): sk-...
? Enter Perplexity API key (or press Enter to use $PERPLEXITY_API_KEY): pplx-...

✓ Configuration saved to ~/.doxa-research/config.toml

💡 Tips for new users:
  • Use --provider mock for testing without API keys
  • Add --combined to merge results from multiple providers
  • Use --async for long-running research tasks

Starting research: what is quantum computing
[... continues with normal research flow ...]
```

### 11.3 Mode Chaining Experience (v2.0)

```bash
$ doxa clarification "building microservices architecture"

Clarifying: building microservices architecture
Mode: clarification | Provider: OpenAI

✓ Clarification complete

File created:
  • 2024-08-03_143022_clarification_openai_building-microservices.md

$ doxa exploration --auto

Using previous output: 2024-08-03_143022_clarification_openai_building-microservices.md
Mode: exploration | Providers: OpenAI + Perplexity

[... exploration continues ...]

$ doxa deep_research --auto

Using previous output: 2024-08-03_143022_exploration_combined_building-microservices.md
Mode: deep_research | Providers: OpenAI + Perplexity

[... deep research continues ...]
```

### 11.4 Clean Command Experience (v2.0)

```bash
$ doxa clean --days 30 --dry-run

Analyzing checkpoints...

Would remove:
  • 15 operations older than 30 days
  • 42 associated output files
  • Total space to be freed: 128 MB

Operations to remove:
  - research-20240703-090122-abc... (completed, 45 days old)
  - research-20240705-143022-def... (failed, 43 days old)
  - ... (13 more)

Run without --dry-run to execute cleanup

$ doxa clean --days 30

⚠️  This will remove 15 operations and 42 files (128 MB)
Continue? [y/N]: y

Cleaning up...
✓ Removed 15 operations
✓ Removed 42 output files
✓ Freed 128 MB of disk space
```

### 11.5 Progress Display Details

The progress display implementation includes:
- **Elapsed time**: `[HH:MM:SS]` - Currently implemented
- **Next check time**: `Next check in Xs` - Partially implemented for async operations
- **Timeout countdown**: `timeout in MM:SS` - Fully implemented in examples (see AUDIT-005)
- **Operation ID**: Shown in verbose mode output
- **Adaptive intervals**: Check frequency adjusts based on operation duration

Note: All progress display features shown in examples are now fully implemented as of v2.0.

---

## 12. Configuration File

### 12.1 Default Configuration

The system works with zero configuration if API keys are in environment variables. The config file at `~/.doxa-research/config.toml` provides additional control:

```toml
# Doxa Research Configuration File
version = "2.0"

[general]
default_mode = "default"          # Used when no mode specified (no system prompt)
show_tips = true                  # Show helpful tips for new users
auto_cleanup_days = 90           # Auto-clean operations older than this

[execution]
poll_interval = 30               # seconds between status checks
max_wait = 30                    # maximum minutes to wait
parallel_providers = true        # run providers simultaneously
adaptive_polling = true          # adjust check intervals dynamically

[output]
combine_reports = false          # create combined report only with --combined flag
format = "markdown"              # output format
timestamp_format = "%Y-%m-%d_%H%M%S"
max_file_size = "100MB"          # maximum input file size

[providers.openai]
api_key = "${OPENAI_API_KEY}"   # reads from environment
model = "o1-deep-research"
temperature = 0.7
max_tokens = 4000
retry_attempts = 3
retry_delay = 1                  # seconds, exponential backoff

[providers.perplexity]
api_key = "${PERPLEXITY_API_KEY}"
model = "sonar-pro"
search_depth = "comprehensive"
academic_mode = false

[providers.mock]
# Mock provider accepts any value as API key for testing
# No configuration required
delay = 2                        # simulated delay in seconds

[cache]
enabled = true
ttl = 3600                      # cache TTL in seconds
max_size = "1GB"

[multi_provider]
fallback_enabled = true
cost_optimization = false
quality_preference = "balanced"
health_check_interval = 300     # seconds
```

### 12.2 Per-Project Configuration (v2.0)

Projects can have their own configuration that overrides the global config:

```toml
# .doxa-research/config.toml in project directory
[project]
name = "quantum_research"
base_output_dir = "./research"

[providers.openai]
model = "gpt-4-turbo"           # Override for this project

[output]
combine_reports = true          # Always combine for this project
```

### 12.3 Minimal Configuration

For users who want the absolute minimum, Doxa Research works with just environment variables:

```bash
export OPENAI_API_KEY="sk-..."
export PERPLEXITY_API_KEY="pplx-..."
# That's it - doxa-research is ready to use
```

---

## 13. Quick Start Guide

### For New Users

1. **Install**: Ensure Python 3.11+ is available
2. **Set API Keys** (optional for testing):
   ```bash
   # For real usage
   export OPENAI_API_KEY="your-key"
   export PERPLEXITY_API_KEY="your-key"

   # For testing
   doxa-research "test query" --provider mock
   ```
3. **Research**:
   ```bash
   doxa-research "your research question"
   ```
4. **View Results**: Open the generated `.md` files in current directory

### Common Use Cases

```bash
# Quick technical explanation
doxa "how does HTTPS work"

# API documentation research
doxa "comprehensive guide to GraphQL"

# Technology comparison
doxa "PostgreSQL vs MySQL for web applications"

# Best practices research
doxa "microservices design patterns"

# Deep technical dive
doxa "internals of Git version control"

# Testing without API keys
doxa "test the tool" --provider mock

# Generate combined report
doxa "distributed systems architecture" --combined

# Clean up old research
doxa clean --days 30

# Check active operations
doxa list --in-progress
```

---

## 14. Error Messages

### User-Friendly Error Handling

All errors go to stderr for proper shell scripting:

```bash
# Missing API keys
$ doxa "quantum computing"
Error: OpenAI API key not found
Please set OPENAI_API_KEY environment variable or run 'doxa-research init'

# Network issues with retry
$ doxa "distributed systems"
Network error: Unable to reach OpenAI API
Retrying in 2s... (attempt 2/3)
Retrying in 4s... (attempt 3/3)
Error: Failed to connect after 3 attempts

# Long operation
$ doxa "analyze all cloud provider services"
This research may take 15-30 minutes. Consider using --async:
  doxa-research "analyze all cloud provider services" --async

Continue anyway? [Y/n]:

# Invalid provider
$ doxa "test" --provider invalid
Error: Unknown provider: invalid
Valid providers are: openai, perplexity, mock

# Rate limit handling
$ doxa "complex analysis"
Rate limit reached for OpenAI
Waiting 60s before retry...
Falling back to Perplexity provider
```

---

## 15. File Output Structure

### Default Output (Current Directory)

When you run `doxa-research "your query"`, files are created in your current directory:

```
./
├── 2024-08-03_143022_default_openai_your-query.md
└── 2024-08-03_143022_default_perplexity_your-query.md

# With --combined flag:
./
├── 2024-08-03_143022_default_openai_your-query.md
├── 2024-08-03_143022_default_perplexity_your-query.md
└── 2024-08-03_143022_default_combined_your-query.md
```

### Mock Provider Output

When testing with `--provider mock`:

```
./
└── 2024-08-03_143022_default_mock_your-query.md  # Static test content
```

### Mode Chaining Output (v2.0)

When using `--auto` for mode chaining:

```
./
├── 2024-08-03_143022_clarification_openai_your-query.md
├── 2024-08-03_143525_exploration_openai_your-query.md
├── 2024-08-03_143525_exploration_perplexity_your-query.md
├── 2024-08-03_143525_exploration_combined_your-query.md
├── 2024-08-03_144230_deep_research_openai_your-query.md
├── 2024-08-03_144230_deep_research_perplexity_your-query.md
└── 2024-08-03_144230_deep_research_combined_your-query.md
```


### File Contents Structure

Each file includes:
- Metadata header (hidden in most Markdown viewers)
- Research query
- Comprehensive findings
- Citations and sources (Perplexity)
- Organized sections and insights
- Token count and cost estimate (when available)

---

## 16. Advanced Features

While the primary use case is simple, power users can access:

### Mode Selection
- `default` - Direct query pass-through (no system prompt) - used when no mode specified
- `thinking` - Quick analysis with system prompt
- `clarification` - Refine questions with system prompt
- `exploration` - Survey options with system prompt
- `deep_research` - Comprehensive research with system prompt

### Provider Selection
- `--provider openai` or `-P openai` - Use only OpenAI
- `--provider perplexity` or `-P perplexity` - Use only Perplexity
- `--provider mock` or `-P mock` - Use mock provider for testing (accepts any API key value)
- Default uses both OpenAI and Perplexity for comprehensive coverage

### Project Organization
- `--project NAME` - Organize outputs in dedicated directories
- Useful for ongoing research topics
- Supports per-project configuration

### Async Operations
- `--async` - Submit and continue working
- Essential for very long research tasks
- Full checkpoint/resume support

### Mode Chaining (v2.0)
- `--auto` - Automatically use previous output
- Enables workflow: clarification → exploration → deep_research
- Preserves context across modes

### Provider Coordination (v2.0)
- Automatic fallback on provider failure
- Cost-optimized routing (when enabled)
- Health monitoring and circuit breakers
- Cross-provider deduplication

---

## 17. Security and Privacy

- **Local storage only**: All outputs saved locally
- **No telemetry**: No usage tracking or data collection
- **API key protection**: Keys masked in all outputs
- **Secure connections**: HTTPS-only API communication
- **Input validation**: File size limits and path sanitization
- **Checkpoint integrity**: Corruption detection and recovery

---

## 18. Future Enhancements

### Version 2.1
- Smart query suggestions based on clarity
- Automatic mode selection based on query type
- Research templates for common topics
- Integration with local knowledge bases
- Plugin system for extensibility

### Version 2.2
- Real-time streaming of research progress
- Web dashboard for operation monitoring
- Export to multiple formats (JSON, CSV)
- Collaborative research sessions
- Batch processing support
- Long operation warnings with async suggestions

---

## 19. Testing Requirements

### Test Suite Status
As of v2.0, the test suite achieves **100% pass rate** with 28/28 tests passing when using the mock provider. Additional tests are planned for new v2.0 features.

### Mock Provider Behavior
The mock provider is essential for testing and has been fully implemented to:
- Work without any API keys (F-32 requirement satisfied)
- Accept any value as a dummy API key for testing purposes
- Return predictable responses
- Support all provider interface methods
- Simulate realistic delays
- Generate valid output files
- Bypass API key validation when `--provider mock` is specified
- Support mode chaining with --auto

### Error Output Standards
**Important Note**: Rich console library outputs to stdout by design, which is correct behavior for terminal UI libraries. Error messages are properly routed to stderr while UI elements use stdout.

Standards implemented:
- Exit codes follow POSIX conventions (F-35 satisfied)
- Error messages are clear and actionable
- Mode and provider validation happens before API key checks (F-34 satisfied)
- Commands return proper exit codes: 0=success, 1=general error, 2=usage error

### Validation Order
The tool validates in this order (fully implemented):
1. Command structure (missing query = exit 2) ✓
2. Mode validity (invalid mode = exit 1) ✓
3. Provider validity (invalid provider = exit 1) ✓
4. API key presence (missing key = exit 1) ✓
5. API key validity (invalid key = exit 1) ✓

This ensures users get the most relevant error message first.

### Implementation Details
Key features implemented in v2.0:
- Output directories are created automatically if they don't exist (F-36)
- Init command works with custom config directories via XDG_CONFIG_HOME (F-37)
- Mock provider properly overrides mode-specific provider preferences
- Empty queries are properly validated with appropriate exit codes
- All test patterns updated to match actual output formats
- Combined reports require explicit --combined flag
- Progress display shows elapsed time, next check, and timeout (with implementation status noted)
- Provider flag supports -P short form
- Quiet mode uses -Q flag
- Mode chaining with --auto flag
- New commands: update, clean, config, export, import
- Provider fallback and health monitoring
- Adaptive polling intervals
- Shell completion support

### Test Infrastructure Requirements

The test suite requires infrastructure for comprehensive testing:

#### Checkpoint Test Fixtures (M22-01 to M22-05)
- Create test fixtures for checkpoints with different statuses
- Generate aged checkpoints for time-based testing
- Utilities for verifying checkpoint deletion
- Mock checkpoint files with various corruption states
- Test cleanup to prevent test pollution

#### Test Patterns
- Use predictable patterns for test-generated files
- Implement cleanup after each test run
- Support parallel test execution without conflicts

### Manual Testing Requirements

Some features require manual testing due to their interactive or environment-dependent nature:

#### First-Time User Experience (AUDIT-012)
- Manually test the automatic setup wizard for missing API keys
- Verify prompts appear correctly and config is saved
- Test with various combinations of existing/missing environment variables
- Validate that the wizard only appears when needed

#### Network Retry Logic (AUDIT-013)
- Test automatic retry on transient network errors
- Verify retry attempts are properly displayed
- Test timeout behavior on persistent network failures
- Validate error messages for different network conditions

These manual tests should be documented in a separate testing guide and performed before each release.

---

## End of Doxa Research v2.0 PRD

This specification prioritizes the simplest possible user experience while maintaining all advanced capabilities. The primary innovation is making `doxa-research "query"` the default interaction pattern, removing friction for users who just want quick, comprehensive research results in their current directory.

Key principles:
- **Simple by default**: Just query and go
- **Progressive disclosure**: Advanced features available when needed
- **Current directory convenience**: Results appear where you work
- **Clear communication**: Simple progress and obvious output locations
- **Testability first**: Mock provider enables comprehensive testing

The tool serves both casual users who want instant research and power users who need fine-grained control over the research process.
