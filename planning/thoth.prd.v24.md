# Product Requirements Document – Thoth v2.4

---

## 1. Document Control

| Item | Value |
|------|-------|
| Author | System Design Team |
| Date | 03 Aug 2025 |
| Status | In Development |
| Target Release | v2.4 |
| Document Version | 24.0 |

### Changes in Version 24.0
- Updated version to v2.4 based on v2.3
- Implemented clean architecture with class-based organization in single file
- Added ConfigManager for layered configuration with clear precedence hierarchy
- Created CommandHandler for unified command execution across interfaces
- Implemented ProviderRegistry for better provider management
- Added configuration validation and schema enforcement
- Improved separation of concerns while maintaining single-file distribution
- Configuration precedence: defaults < user < project < env vars < CLI < interactive

### Changes in Version 23.0
- Updated version to v2.3 based on v2.2
- Added interactive query mode with `-i` or `--interactive` flag
- Implemented bordered input box with multi-line support
- Added slash commands for dynamic option modification
- Added help text display above input box in dim color
- Support for placeholder text in input box (implementation-dependent)
- Added Unix line editing shortcuts (Ctrl+A, Ctrl+E, Ctrl+K)
- Single query per interactive session with automatic exit after submission
- Added model caching for OpenAI provider with automatic refresh after 1 week
- Implemented `--refresh-cache` flag to force refresh model lists
- Enhanced `--list` output to show cache age and status
- Added ModelCache class for managing cached model lists in ~/.thoth/model_cache/
- Added `--no-cache` flag to bypass model cache without updating it

### Changes in Version 22.0
- Updated version to v2.2 based on v2.1
- Enhanced `providers` command with `--list` flag to show available providers
- Added provider status display (configured/not configured)
- Added `--keys` flag to show API key configuration for each provider
- Changed CLI API key options to be provider-specific (e.g., `--api-key-openai` instead of generic `--api-key`)
- Providers automatically detected from registry
- Consistent use of `--` separator for subcommand options
- Added model information to metadata headers (F-114)
- Mock provider shows "None" as the model (F-115)
- Added prompt section to output files showing exact prompts sent to LLM (F-116)
- Added --no-metadata flag to disable metadata headers and prompt section (F-117)

### Changes in Version 21.0
- Updated version to v2.1 based on v2.0
- Added `providers` command to list available models from each provider
- OpenAI models fetched dynamically via API
- Perplexity models hardcoded as specified
- Implemented dynamic column width for model ID display to prevent truncation

### Changes in Version 20.0
- Updated version to v2.1 to reflect comprehensive feature additions
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

Thoth is a command-line interface (CLI) tool that automates deep technical research using multiple LLM providers. **The primary use case is simple: just give it a query and get comprehensive research results in your current directory.** While Thoth supports advanced features like mode selection, project organization, and async operations, the default experience is optimized for immediate, zero-configuration research.

### Core Value Propositions
- **Instant research**: Just `thoth "your query"` – no mode selection needed
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
| Default mode | When no mode is specified, uses a special 'default' mode that passes queries directly to the LLM without any system prompt. Files created with this mode include 'default' in the filename pattern. NOTE: Quick mode (`thoth "query"`) uses "default" mode, NOT "deep_research" |
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
| Model cache | Local storage of provider model lists to reduce API calls and improve performance. Stored in ~/.thoth/model_cache/ |
| Cache refresh | Process of updating cached model lists, either automatically (after 1 week) or manually via --refresh-cache flag |

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

## 6. Out of Scope (v2.1)

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
| F-02 | Accept query as single positional argument: `thoth "query"` | Must | T-CLI-01 |
| F-03 | Save outputs to current directory by default | Must | T-OUT-01 |
| F-04 | Support full mode specification for advanced users | Must | T-MODE-02 |
| F-05 | Single config file `~/.thoth/config.toml` with all settings | Must | T-CFG-01 |
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
| F-26 | `thoth "query"` executes deep research in current directory | Must | T-QUICK-01 |
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

### New Command Requirements (v2.1)

| ID | Requirement | Priority | Test ID |
|----|-------------|----------|---------|
| F-41 | Implement `update` command to fix stale operation statuses | Must | T-CMD-04 |
| F-42 | Implement `clean` command with filtering options for checkpoint management | Must | T-CMD-05 |
| F-43 | Implement `config` command for configuration management | Must | T-CMD-06 |
| F-44 | Implement `export` command to export research results | Must | T-CMD-07 |
| F-45 | Implement `import` command to import research data | Must | T-CMD-08 |
| F-46 | Add --force flag support where applicable | Must | T-CLI-04 |
| F-47 | Add --dry-run flag for preview operations | Must | T-CLI-05 |

### Advanced Mode Requirements (v2.1)

| ID | Requirement | Priority | Test ID |
|----|-------------|----------|---------|
| F-48 | Implement --auto flag for automatic mode chaining | Must | T-MODE-04 |
| F-49 | Support reading from previous output files automatically | Must | T-MODE-05 |
| F-50 | Implement symlink path resolution | Must | T-FILE-01 |
| F-51 | Add max file size limits for input files | Must | T-FILE-02 |
| F-52 | Create operation metadata tracking | Must | T-META-01 |

### Provider Enhancement Requirements (v2.1)

| ID | Requirement | Priority | Test ID |
|----|-------------|----------|---------|
| F-53 | Implement retry logic with exponential backoff | Must | T-NET-02 |
| F-54 | Add streaming response support for providers | Should | T-PROV-02 |
| F-55 | Implement token counting and display | Should | T-PROV-03 |
| F-56 | Add cost estimation and tracking | Should | T-PROV-04 |
| F-57 | Support temperature control from config | Should | T-PROV-05 |
| F-58 | Add response caching mechanism | Should | T-CACHE-01 |
| F-59 | Implement rate limit handling with backoff | Must | T-NET-03 |

### Multi-Provider Coordination (v2.1)

| ID | Requirement | Priority | Test ID |
|----|-------------|----------|---------|
| F-60 | Implement provider fallback chains | Must | T-MULTI-01 |
| F-61 | Add cost optimization routing | Should | T-MULTI-02 |
| F-62 | Create quality-based provider selection | Should | T-MULTI-03 |
| F-63 | Implement provider health checks | Must | T-MULTI-04 |
| F-64 | Add unified error handling across providers | Must | T-MULTI-05 |
| F-65 | Implement cross-provider deduplication | Should | T-MULTI-06 |

### Progress and UX Enhancements (v2.1)

| ID | Requirement | Priority | Test ID |
|----|-------------|----------|---------|
| F-66 | Implement adaptive polling intervals | Should | T-UX-05 |
| F-67 | Add operation lifecycle management with states: queued→running→completed/failed/cancelled, with proper transitions | Must | T-ASYNC-06 |
| F-68 | Create first-time setup flow improvements | Should | T-UX-06 |
| F-69 | Add helpful tips for new users | Should | T-UX-07 |
| F-70 | Implement shell completion support | Should | T-CLI-06 |

### Configuration Enhancements (v2.1)

| ID | Requirement | Priority | Test ID |
|----|-------------|----------|---------|
| F-71 | Add config validation command | Must | T-CFG-07 |
| F-72 | Support per-project configuration | Should | T-CFG-08 |
| F-73 | Implement config migration for version updates | Must | T-CFG-09 |
| F-74 | Add config export/import functionality | Should | T-CFG-10 |
| F-75 | Support environment-specific configs | Should | T-CFG-11 |

### Clean Command Features (v2.1)

| ID | Requirement | Priority | Test ID |
|----|-------------|----------|---------|
| F-76 | Support --in-progress, --completed, --failed filters | Must | T-CLEAN-01 |
| F-77 | Add --days filter for age-based cleanup | Must | T-CLEAN-02 |
| F-78 | Implement --pattern filter for pattern matching | Should | T-CLEAN-03 |
| F-79 | Add --keep-recent option to preserve N most recent | Must | T-CLEAN-04 |
| F-80 | Detect and clean orphaned output files | Should | T-CLEAN-05 |

### Critical Infrastructure Requirements (v2.1)

| ID | Requirement | Priority | Test ID |
|----|-------------|----------|---------|
| F-81 | Implement graceful shutdown on Ctrl-C with checkpoint save | Must | T-SIG-01 |
| F-82 | Implement checkpoint corruption detection and recovery | Must | T-ASYNC-07 |

### OpenAI Provider Requirements (v2.1)

| ID | Requirement | Priority | Test ID |
|----|-------------|----------|---------|
| F-83 | OpenAI streaming response support | Must | T-OAI-01 |
| F-84 | OpenAI token counting and display | Must | T-OAI-02 |
| F-85 | OpenAI cost estimation and tracking | Should | T-OAI-03 |
| F-86 | OpenAI partial response saving on failure | Must | T-OAI-04 |
| F-87 | OpenAI model selection from config | Must | T-OAI-05 |

### Perplexity Provider Requirements (v2.1)

| ID | Requirement | Priority | Test ID |
|----|-------------|----------|---------|
| F-88 | Perplexity citation extraction and formatting | Must | T-PPLX-01 |
| F-89 | Perplexity web search mode support | Must | T-PPLX-02 |
| F-90 | Perplexity academic search mode | Should | T-PPLX-03 |
| F-91 | Perplexity real-time data queries | Must | T-PPLX-04 |
| F-92 | Perplexity search depth control | Should | T-PPLX-05 |
| F-93 | Perplexity source filtering | Should | T-PPLX-06 |
| F-94 | Perplexity source reliability scores | Should | T-PPLX-07 |

### Advanced Multi-Provider Requirements (v2.1)

| ID | Requirement | Priority | Test ID |
|----|-------------|----------|---------|
| F-95 | Provider load balancing | Should | T-MULTI-07 |
| F-96 | Circuit breaker pattern for provider failures | Must | T-MULTI-08 |
| F-97 | Dynamic provider selection based on query type | Should | T-MULTI-09 |
| F-98 | Partial result handling across providers | Must | T-MULTI-10 |
| F-99 | Provider capability matching | Should | T-MULTI-11 |
| F-100 | Cross-provider performance monitoring | Should | T-MULTI-12 |

### Provider Discovery Requirements (v2.1)

| ID | Requirement | Priority | Test ID |
|----|-------------|----------|---------|
| F-101 | Implement `providers` command to list available models | Must | T-PROV-06 |
| F-102 | Fetch OpenAI models dynamically via API endpoint and cache locally for 1 week | Must | T-PROV-07 |
| F-103 | Return hardcoded model list for Perplexity provider | Must | T-PROV-08 |
| F-104 | Support --models flag to display available models | Must | T-PROV-09 |
| F-105 | Support filtering by provider with --provider flag | Must | T-PROV-10 |
| F-106 | Format model list output using Rich tables with dynamic column width | Should | T-PROV-11 |
| F-107 | Handle API errors gracefully when fetching models | Must | T-PROV-12 |
| F-108 | Show list of available providers with cache status when `thoth providers -- --list` is run | Must | T-PROV-13 |
| F-109 | Automatically detect available providers from the provider registry | Must | T-PROV-14 |
| F-110 | Display provider status (configured/not configured) based on API key presence | Must | T-PROV-15 |
| F-111 | Support both `--list` and `--models` flags after `--` separator | Must | T-PROV-16 |
| F-112 | Update help text to show both provider listing and model listing options | Must | T-PROV-17 |
| F-113 | Show API key configuration with --keys flag displaying env vars and provider-specific CLI args | Must | T-PROV-18 |
| F-114 | Implement model caching for OpenAI provider with 1-week expiration | Must | T-CACHE-02 |
| F-115 | Support --refresh-cache flag to force model list refresh | Must | T-CACHE-03 |
| F-116 | Display cache age and status in provider list output | Must | T-CACHE-04 |
| F-117 | Auto-refresh cache when older than 1 week | Must | T-CACHE-05 |
| F-118 | Store model cache in ~/.thoth/model_cache/ directory | Must | T-CACHE-06 |
| F-123 | Support --no-cache flag to bypass model cache without updating it | Must | T-CACHE-07 |

### Output Format Requirements (v2.2)

| ID | Requirement | Priority | Test ID |
|----|-------------|----------|---------|
| F-119 | Metadata headers must include the model used by each provider | Must | T-OUT-06 |
| F-120 | Mock provider must show "None" as the model in metadata | Must | T-OUT-07 |
| F-121 | Output files must include the prompt section showing system prompt and user query | Must | T-OUT-08 |
| F-122 | Support --no-metadata flag to disable metadata headers and prompt section in output files | Must | T-OUT-09 |

### Interactive Mode Requirements (v2.3)

| ID | Requirement | Priority | Test ID |
|----|-------------|----------|---------|
| F-118 | Support `-i` or `--interactive` flag to enter interactive query mode | Must | T-INT-01 |
| F-119 | Display bordered input box with configurable width (default 80% terminal width) | Must | T-INT-02 |
| F-120 | Support multi-line input with Shift+Enter for new lines, Enter to submit | Must | T-INT-03 |
| F-121 | Display prompt character ">" at beginning of each input line | Must | T-INT-04 |
| F-122 | Support slash commands for dynamic option modification | Must | T-INT-05 |
| F-123 | Implement `/help` command to show available slash commands | Must | T-INT-06 |
| F-124 | Implement `/exit` and `/quit` commands to exit without submitting | Must | T-INT-07 |
| F-125 | Implement `/mode <mode>` command to change research mode with auto-completion | Must | T-INT-08 |
| F-126 | Implement `/provider <provider>` command to set provider | Must | T-INT-09 |
| F-127 | Implement `/async` toggle command for async submission | Must | T-INT-10 |
| F-128 | Support standard Unix line editing shortcuts (Ctrl+A, Ctrl+E, Ctrl+K) | Must | T-INT-11 |
| F-129 | Execute query with same behavior as non-interactive mode after submission | Must | T-INT-12 |
| F-130 | Implement `/status` command to check operation status | Must | T-INT-13 |
| F-131 | Display help text above input box in dimmed/light color with key commands | Must | T-INT-14 |

### Architecture and Code Organization Requirements (v2.4)

| ID | Requirement | Priority | Test ID |
|----|-------------|----------|---------|
| F-132 | Implement layered configuration with clear precedence hierarchy (defaults < user < project < env < CLI < interactive) | Must | T-ARCH-01 |
| F-133 | Create ConfigManager class for unified configuration handling | Must | T-ARCH-02 |
| F-134 | Implement CommandHandler class for unified command execution across interfaces | Must | T-ARCH-03 |
| F-135 | Create ProviderRegistry for dynamic provider management | Must | T-ARCH-04 |
| F-136 | Add configuration schema validation at load time | Must | T-ARCH-05 |
| F-137 | Support project-level configuration file (./thoth.toml or ./.thoth/config.toml) | Should | T-ARCH-06 |
| F-138 | Implement configuration merging with deep merge support | Must | T-ARCH-07 |
| F-139 | Add dot notation config access (e.g., config.get('providers.openai.model')) | Should | T-ARCH-08 |
| F-140 | Maintain single-file distribution while improving internal organization | Must | T-ARCH-09 |

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
thoth "QUERY"                    # Deep research with output to current directory

# INTERACTIVE MODE - Visual Query Input
thoth -i                         # Enter interactive query mode
thoth --interactive              # Same as above

# ADVANCED USAGE - Full Control  
thoth MODE QUERY [OPTIONS]       # Specify mode and options
thoth [COMMAND] [OPTIONS]        # Run specific commands

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
  providers     List available models from each provider
  help          Show help for commands

Interactive Mode Commands:
  /help         Show available slash commands
  /mode <mode>  Set research mode (with auto-completion)
  /provider <p> Set provider (openai, perplexity, mock)
  /async        Toggle async submission mode
  /status       Check operation status
  /exit, /quit  Exit without submitting query
```

### 10.2 Usage Examples

#### Quick Mode (Primary Use Case)

```bash
# SIMPLEST USAGE - just provide a query (no system prompt added)
thoth "impact of quantum computing on cryptography"
# This sends your exact query to the LLM without modification
# Creates in current directory:
#   ./2024-08-03_143022_default_openai_impact-of-quantum-computing.md
#   ./2024-08-03_143022_default_perplexity_impact-of-quantum-computing.md  

# With combined report (requires flag)
thoth "impact of quantum computing on cryptography" --combined
# Also creates:
#   ./2024-08-03_143022_default_combined_impact-of-quantum-computing.md

# More quick examples
thoth "best practices for API design"
thoth "comparison of React vs Vue frameworks"
thoth "how does TCP congestion control work"

# Quick mode with single provider
thoth "kubernetes networking explained" --provider openai
thoth "kubernetes networking explained" -P openai  # Short form

# Testing with mock provider (no API key needed)
thoth "test query" --provider mock
thoth "test query" -P mock  # Short form
```

#### Interactive Mode Examples

```bash
# Enter interactive mode
thoth -i
# or
thoth --interactive

# Interactive session example:
$ thoth -i

[dim]Enter query • Shift+Enter: new line • Enter: submit • /help: commands[/dim]
┌────────────────────────────────────────────────────────────────────┐
│ > /mode deep_research                                              │
└────────────────────────────────────────────────────────────────────┘
[green]Mode set to: deep_research[/green]

┌────────────────────────────────────────────────────────────────────┐
│ > What are the security implications of                            │
│   quantum computing on current encryption methods?                 │
└────────────────────────────────────────────────────────────────────┘
[Submits query and exits to normal processing]

# Interactive mode with provider change
$ thoth -i
> /provider openai
[green]Provider set to: openai[/green]
> /async
[green]Async mode: enabled[/green]
> How does DNS work?
[Submits with openai provider in async mode]
```

#### Advanced Mode Examples

```bash
# Specify a different mode
thoth thinking "quick analysis of JSON vs YAML"
thoth clarification "what are the implications of quantum computing"
thoth exploration "modern web authentication methods"

# Project mode - organize outputs
thoth "quantum cryptography" --project quantum_research
# Creates: ./research-outputs/quantum_research/...

# Async submission for long research
thoth "comprehensive analysis of distributed systems" --async
# Output:
# Research submitted
# Operation ID: research-20240803-143022-a1b2c3d4e5f6g7h8
# Check later with: thoth status research-20240803-143022-a1b2c3d4e5f6g7h8

# Mode chaining workflow with --auto
thoth clarification "building scalable microservices"
thoth exploration --auto  # Uses previous output automatically
thoth deep_research --auto  # Full research based on exploration

# Read query from file
thoth --query-file ./complex_research_query.txt

# Pipe query from another command
echo "analyze security implications of WebAssembly" | thoth --query-file -

# Quiet mode for minimal output
thoth "database optimization techniques" -Q

# Custom config file
thoth "machine learning trends" --config ~/projects/ml/thoth-config.toml
```

#### New Command Examples (v2.1)

```bash
# Update stale operations
thoth update                     # Update all stale operations
thoth update --dry-run          # Preview what would be updated

# Clean old checkpoints
thoth clean --days 30           # Remove operations older than 30 days
thoth clean --failed            # Remove only failed operations
thoth clean --keep-recent 10    # Keep 10 most recent operations
thoth clean --pattern "test*"   # Remove operations matching pattern

# List with filters
thoth list --in-progress        # Show only active operations
thoth list --completed          # Show only completed operations
thoth list --days 7             # Show operations from last 7 days

# Configuration management
thoth config validate           # Validate current configuration
thoth config export > backup.toml  # Export configuration
thoth config import backup.toml    # Import configuration

# Export/Import results
thoth export research-20240803-143022-xxx --format json
thoth import research-backup.json

# List available models
thoth providers --models                      # List all models for all providers
thoth providers --models --provider openai    # List OpenAI models only
thoth providers --models -P perplexity        # List Perplexity models only

# Model cache management
thoth providers -- --list                     # Show providers with cache status
thoth providers -- --models --refresh-cache   # Force refresh model cache
thoth providers -- --models --provider openai --refresh-cache  # Refresh specific provider
thoth providers -- --models --no-cache        # Bypass cache completely without updating it
```

### 10.3 Options Reference

| Long | Short | Type | Description |
|------|-------|------|-------------|
| --interactive | -i | flag | Enter interactive query mode with visual input box |
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
| --no-metadata | | flag | Disable metadata headers and prompt section in output files |
| --help | -h | flag | Show help and exit |
| --config | -c | PATH | Read config from this file or dir |
| --auto | | flag | Use previous output automatically (mode chaining) |
| --force | -f | flag | Force operation without confirmation |
| --dry-run | | flag | Preview operation without executing |
| --refresh-cache | | flag | Force refresh of cached model lists (providers command) |
| --no-cache | | flag | Bypass model cache without updating it (providers command) |

### 10.4 Commands Reference

| Command | Description | Example |
|---------|-------------|---------|  
| (default) | Run research with query | `thoth "your research query"` |
| init | Setup wizard for API keys | `thoth init` |
| status ID | Show operation details | `thoth status research-20240803-143022-xxx` |
| list | Show recent operations | `thoth list` |
| update | Fix stale operation statuses | `thoth update --dry-run` |
| clean | Clean up old checkpoints | `thoth clean --days 30` |
| config | Manage configuration | `thoth config validate` |
| export | Export research results | `thoth export operation-id` |
| import | Import research data | `thoth import file.json` |
| providers | List available models | `thoth providers --models` |

### 10.5 Exit Codes

| Code | Meaning | Example |
|------|---------|---------|
| 0 | Success | Research completed successfully |
| 1 | General error | API key missing, network error, etc. |
| 2 | Usage error | Invalid command, missing required arguments |

### 10.6 Help Text Structure

```
Thoth - AI-Powered Research Assistant

USAGE:
    thoth "QUERY"                    # Quick research (recommended)
    thoth MODE QUERY [OPTIONS]       # Advanced usage
    thoth COMMAND [OPTIONS]          # Run commands

QUICK START:
    thoth "impact of quantum computing"
    thoth "best practices for REST APIs"
    
EXAMPLES:
    # Simple research (saves to current directory)
    thoth "how does blockchain consensus work"
    
    # Research with single provider
    thoth "machine learning optimization" --provider openai
    thoth "machine learning optimization" -P openai
    
    # Test with mock provider (no API key needed)
    thoth "test query" --provider mock
    thoth "test query" -P mock
    
    # Async for long research
    thoth "comprehensive review of database architectures" --async
    
    # Generate combined report
    thoth "cloud architecture patterns" --combined
    
    # Clean old operations
    thoth clean --days 30

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

Run 'thoth --help' for complete options and advanced usage.
```

---

## 11. User Experience

### 11.1 Quick Mode Experience

```bash
$ thoth "explain how DNS resolution works"

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
$ thoth "what is quantum computing"

⚠️  No API keys found. Let's set them up:

? Enter OpenAI API key (or press Enter to use $OPENAI_API_KEY): sk-...
? Enter Perplexity API key (or press Enter to use $PERPLEXITY_API_KEY): pplx-...

✓ Configuration saved to ~/.thoth/config.toml

💡 Tips for new users:
  • Use --provider mock for testing without API keys
  • Add --combined to merge results from multiple providers
  • Use --async for long-running research tasks

Starting research: what is quantum computing
[... continues with normal research flow ...]
```

### 11.3 Mode Chaining Experience (v2.1)

```bash
$ thoth clarification "building microservices architecture"

Clarifying: building microservices architecture
Mode: clarification | Provider: OpenAI

✓ Clarification complete

File created:
  • 2024-08-03_143022_clarification_openai_building-microservices.md

$ thoth exploration --auto

Using previous output: 2024-08-03_143022_clarification_openai_building-microservices.md
Mode: exploration | Providers: OpenAI + Perplexity

[... exploration continues ...]

$ thoth deep_research --auto

Using previous output: 2024-08-03_143022_exploration_combined_building-microservices.md
Mode: deep_research | Providers: OpenAI + Perplexity

[... deep research continues ...]
```

### 11.4 Clean Command Experience (v2.1)

```bash
$ thoth clean --days 30 --dry-run

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

$ thoth clean --days 30

⚠️  This will remove 15 operations and 42 files (128 MB)
Continue? [y/N]: y

Cleaning up...
✓ Removed 15 operations
✓ Removed 42 output files
✓ Freed 128 MB of disk space
```

### 11.5 Providers Command Experience (v2.2)

```bash
$ thoth providers -- --list

Available Providers:
┌─────────────┬──────────┬─────────────────────────┬──────────────────────────────┐
│ Provider    │ Status   │ Description             │ Model Cache                  │
├─────────────┼──────────┼─────────────────────────┼──────────────────────────────┤
│ openai      │ ✓ Ready  │ OpenAI GPT models       │ 3 days old (refresh in 4 days) │
│ perplexity  │ ✗ No key │ Perplexity search AI    │ N/A                          │
│ mock        │ ✓ Ready  │ Mock provider for tests │ N/A                          │
└─────────────┴──────────┴─────────────────────────┴──────────────────────────────┘

To see available models, use: thoth providers -- --models
To refresh model cache, use: thoth providers -- --models --refresh-cache

$ thoth providers -- --models

Fetching available models...

OpenAI Models:
┌─────────────────────────┬──────────────┬─────────────┐
│ Model ID                │ Created      │ Owned By    │
├─────────────────────────┼──────────────┼─────────────┤
│ gpt-4-turbo-preview     │ 2024-01-25   │ openai      │
│ gpt-4o                  │ 2024-05-13   │ openai      │
│ gpt-4o-mini             │ 2024-07-18   │ openai      │
│ gpt-3.5-turbo           │ 2022-12-01   │ openai      │
│ o1-preview              │ 2024-09-12   │ openai      │
│ o1-mini                 │ 2024-09-12   │ openai      │
└─────────────────────────┴──────────────┴─────────────┘

Perplexity Models:
┌─────────────────────────┐
│ Model ID                │
├─────────────────────────┤
│ sonar-deep-research     │
└─────────────────────────┘

Mock Models:
┌─────────────────────────┐
│ Model ID                │
├─────────────────────────┤
│ mock-model-v1           │
│ mock-model-v2           │
└─────────────────────────┘

$ thoth providers -- --models --provider openai

OpenAI Models:
┌─────────────────────────┬──────────────┬─────────────┐
│ Model ID                │ Created      │ Owned By    │
├─────────────────────────┼──────────────┼─────────────┤
│ gpt-4-turbo-preview     │ 2024-01-25   │ openai      │
│ gpt-4o                  │ 2024-05-13   │ openai      │
│ gpt-4o-mini             │ 2024-07-18   │ openai      │
│ gpt-3.5-turbo           │ 2022-12-01   │ openai      │
│ o1-preview              │ 2024-09-12   │ openai      │
│ o1-mini                 │ 2024-09-12   │ openai      │
└─────────────────────────┴──────────────┴─────────────┘

$ thoth providers -- --keys

                Provider API Key Configuration                 
╭───────────────┬────────────────────────┬───────────────────╮
│ Provider      │ Environment Variable   │ CLI Argument      │
├───────────────┼────────────────────────┼───────────────────┤
│ openai        │ OPENAI_API_KEY         │ --api-key-openai  │
│ perplexity    │ PERPLEXITY_API_KEY     │ --api-key-perplexity │
│ mock          │ MOCK_API_KEY           │ --api-key-mock    │
╰───────────────┴────────────────────────┴───────────────────╯

Examples:
  # Set via environment variable
  $ export OPENAI_API_KEY="your-key-here"

  # Set via command line for single provider
  $ thoth "query" --api-key-openai "your-key-here" --provider openai

  # Set multiple API keys for multi-provider modes
  $ thoth deep_research "query" --api-key-openai "sk-..." --api-key-perplexity "pplx-..."

$ thoth providers -- --models --refresh-cache

Fetching available models (refreshing cache)...

OpenAI Models:
┌─────────────────────────┬──────────────┬─────────────┐
│ Model ID                │ Created      │ Owned By    │
├─────────────────────────┼──────────────┼─────────────┤
│ gpt-4-turbo-preview     │ 2024-01-25   │ openai      │
│ gpt-4o                  │ 2024-05-13   │ openai      │
│ gpt-4o-mini             │ 2024-07-18   │ openai      │
└─────────────────────────┴──────────────┴─────────────┘

[Cache refreshed and saved locally]
```

### 11.6 Progress Display Details

The progress display implementation includes:
- **Elapsed time**: `[HH:MM:SS]` - Currently implemented
- **Next check time**: `Next check in Xs` - Partially implemented for async operations
- **Timeout countdown**: `timeout in MM:SS` - Fully implemented in examples (see AUDIT-005)
- **Operation ID**: Shown in verbose mode output
- **Adaptive intervals**: Check frequency adjusts based on operation duration

Note: All progress display features shown in examples are now fully implemented as of v2.1.

---

## 12. Configuration File

### 12.1 Default Configuration

The system works with zero configuration if API keys are in environment variables. The config file at `~/.thoth/config.toml` provides additional control:

```toml
# Thoth Configuration File
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

### 12.2 Per-Project Configuration (v2.1)

Projects can have their own configuration that overrides the global config:

```toml
# .thoth/config.toml in project directory
[project]
name = "quantum_research"
base_output_dir = "./research"

[providers.openai]
model = "gpt-4-turbo"           # Override for this project

[output]
combine_reports = true          # Always combine for this project
```

### 12.3 Minimal Configuration

For users who want the absolute minimum, Thoth works with just environment variables:

```bash
export OPENAI_API_KEY="sk-..."
export PERPLEXITY_API_KEY="pplx-..."
# That's it - thoth is ready to use
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
   thoth "test query" --provider mock
   ```
3. **Research**: 
   ```bash
   thoth "your research question"
   ```
4. **View Results**: Open the generated `.md` files in current directory

### Common Use Cases

```bash
# Quick technical explanation
thoth "how does HTTPS work"

# API documentation research  
thoth "comprehensive guide to GraphQL"

# Technology comparison
thoth "PostgreSQL vs MySQL for web applications"

# Best practices research
thoth "microservices design patterns"

# Deep technical dive
thoth "internals of Git version control"

# Testing without API keys
thoth "test the tool" --provider mock

# Generate combined report
thoth "distributed systems architecture" --combined

# Clean up old research
thoth clean --days 30

# Check active operations
thoth list --in-progress
```

---

## 14. Error Messages

### User-Friendly Error Handling

All errors go to stderr for proper shell scripting:

```bash
# Missing API keys
$ thoth "quantum computing"
Error: OpenAI API key not found
Please set OPENAI_API_KEY environment variable or run 'thoth init'

# Network issues with retry
$ thoth "distributed systems"
Network error: Unable to reach OpenAI API
Retrying in 2s... (attempt 2/3)
Retrying in 4s... (attempt 3/3)
Error: Failed to connect after 3 attempts

# Long operation
$ thoth "analyze all cloud provider services"
This research may take 15-30 minutes. Consider using --async:
  thoth "analyze all cloud provider services" --async
  
Continue anyway? [Y/n]:

# Invalid provider
$ thoth "test" --provider invalid
Error: Unknown provider: invalid
Valid providers are: openai, perplexity, mock

# Rate limit handling
$ thoth "complex analysis"
Rate limit reached for OpenAI
Waiting 60s before retry...
Falling back to Perplexity provider
```

---

## 15. File Output Structure

### Default Output (Current Directory)

When you run `thoth "your query"`, files are created in your current directory:

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

### Mode Chaining Output (v2.1)

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

### Example Output File Formats

**Default mode with OpenAI:**
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

**Deep research mode with system prompt:**
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

**Mock provider output:**
```yaml
---
query: test query
mode: default
provider: mock
model: None
operation_id: research-20250802-154755-a38d159848984fa8
created_at: 2025-08-02T15:47:55.468596
---

### Prompt

```
test query
```

[Mock response content...]
```

### File Contents Structure

Each file includes (unless --no-metadata is used):

1. **Metadata header** (YAML front matter, hidden in most Markdown viewers):
   - query: The user's research query
   - mode: The research mode used
   - provider: The LLM provider used
   - model: The specific model used (e.g., gpt-4o, sonar-pro, None for mock)
   - operation_id: Unique identifier for the operation
   - created_at: Timestamp of creation
   - input_files: List of input files (if any)

2. **Prompt section** (visible in markdown):
   - Shows the exact prompt sent to the LLM
   - For modes with system prompts: displays both system and user prompts
   - For default mode: shows only the user query

3. **Research content**:
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

### Mode Chaining (v2.1)
- `--auto` - Automatically use previous output
- Enables workflow: clarification → exploration → deep_research
- Preserves context across modes

### Provider Coordination (v2.1)
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
As of v2.1, the test suite achieves **100% pass rate** with 28/28 tests passing when using the mock provider. Additional tests are planned for new v2.1 features.

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
Key features implemented in v2.1:
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
- Providers command with dynamic model discovery for OpenAI (F-101, F-102)
- Hardcoded model list for Perplexity provider (F-103)
- Provider filtering with --provider flag (F-105)
- Rich table formatting for model display with dynamic column width (F-106)
  - Model ID column width automatically adjusts based on longest model name
  - Ensures model IDs like `gpt-4o-mini-audio-preview-2024-12-17` are never truncated
  - Minimum width of 20 characters for consistent formatting
- Graceful error handling for invalid providers (F-107)
- Note: Due to Click option parsing, providers command requires -- separator: `thoth providers -- --models`
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

## End of Thoth v2.1 PRD

This specification prioritizes the simplest possible user experience while maintaining all advanced capabilities. The primary innovation is making `thoth "query"` the default interaction pattern, removing friction for users who just want quick, comprehensive research results in their current directory.

Key principles:
- **Simple by default**: Just query and go
- **Progressive disclosure**: Advanced features available when needed  
- **Current directory convenience**: Results appear where you work
- **Clear communication**: Simple progress and obvious output locations
- **Testability first**: Mock provider enables comprehensive testing

The tool serves both casual users who want instant research and power users who need fine-grained control over the research process.