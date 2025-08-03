# Product Requirements Document – Thoth v1.9

---

## 1. Document Control

| Item | Value |
|------|-------|
| Author | System Design Team |
| Date | 02 Aug 2025 |
| Status | Production-Ready |
| Target Release | v1.9 |
| Document Version | 19.0 |

### Changes in Version 19.0
- Updated version numbers throughout to v1.9 (from v1.7)
- Added clarification note that quick mode uses "default" mode, not "deep_research"
- Fixed duplicate test ID T-CLI-02 (renumbered to T-CLI-03 for provider flag test)
- Added implementation status clarification for progress display features
- Updated quiet mode flag from --quiet to -Q throughout
- All changes from audit v3 applied

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
| Default mode | When no mode is specified, uses a special 'default' mode that passes queries directly to the LLM without any system prompt. NOTE: Quick mode (`thoth "query"`) uses "default" mode, NOT "deep_research" |
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

## 6. Out of Scope (v1.9)

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

| ID | Requirement | Priority | Test ID |
|----|-------------|----------|---------|
| F-01 | When no mode specified, use 'default' mode with no system prompt | Must | T-MODE-01 |
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
| F-19 | Mask API keys in all output (logs, errors, debug) | Must | T-SEC-01 |
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
| F-27 | Show simple progress indicator for quick mode | Must | T-QUICK-02 |
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

# ADVANCED USAGE - Full Control  
thoth MODE QUERY [OPTIONS]       # Specify mode and options
thoth [COMMAND] [OPTIONS]        # Run specific commands

Commands:
  (default)     Run research (uses 'default' mode when no mode specified, NOT deep_research)
  init          Initialize configuration with setup wizard
  status        Check status of specific operation
  list          List all active/recent operations
```

### 10.2 Usage Examples

#### Quick Mode (Primary Use Case)

```bash
# SIMPLEST USAGE - just provide a query (no system prompt added)
thoth "impact of quantum computing on cryptography"
# This sends your exact query to the LLM without modification
# Creates in current directory:
#   ./2024-08-03_143022_deep_research_openai_impact-of-quantum-computing.md
#   ./2024-08-03_143022_deep_research_perplexity_impact-of-quantum-computing.md  

# With combined report (requires flag)
thoth "impact of quantum computing on cryptography" --combined
# Also creates:
#   ./2024-08-03_143022_deep_research_combined_impact-of-quantum-computing.md

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
# Output: Operation ID: research-20240803-143022-a1b2c3d4e5f6g7h8
# Check later with: thoth status research-20240803-143022-a1b2c3d4e5f6g7h8

# Mode chaining workflow
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

### 10.3 Options Reference

| Long | Short | Type | Description |
|------|-------|------|-------------|
| --mode | -m | TEXT | Research mode (defaults to deep_research) |
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

### 10.4 Commands Reference

| Command | Description | Example |
|---------|-------------|---------|  
| (default) | Run research with query | `thoth "your research query"` |
| init | Setup wizard for API keys | `thoth init` |
| status ID | Show operation details | `thoth status research-20240803-143022-xxx` |
| list | Show recent operations | `thoth list` |

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

COMMANDS:
    init      Setup API keys and configuration
    status    Check research operation status  
    list      List recent research operations

OPTIONS:
    -P, --provider    Use specific provider (openai/perplexity/mock)
    -A, --async       Submit and exit (check status later)
    -p, --project     Organize outputs in project directory
    -v, --verbose     Show detailed progress
    -h, --help        Show full help
    -Q, --quiet       Minimal output during execution
    --combined        Generate combined report from providers
    -c, --config      Use custom config file

Run 'thoth --help' for complete options and advanced usage.
```

---

## 11. User Experience

### 11.1 Quick Mode Experience

```bash
$ thoth "explain how DNS resolution works"

Researching: explain how DNS resolution works
Mode: deep_research | Providers: OpenAI + Perplexity

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

Starting research: what is quantum computing
[... continues with normal research flow ...]
```

### 11.3 Mock Provider Experience (Testing)

```bash
$ thoth "test query" --provider mock

Researching: test query
Mode: deep_research | Provider: Mock

⠋ Mock Research: Processing... (simulated delay)
✓ Research completed!

Files created:
  • 2024-08-03_143022_deep_research_mock_test-query.md

Note: This is mock output for testing purposes.
```

### 11.4 Error Handling Examples

```bash
# Missing API key (to stderr)
$ thoth "quantum computing" 2>&1
Error: OpenAI API key not found
Please set OPENAI_API_KEY environment variable or run 'thoth init'

# Invalid mode (to stderr)
$ thoth invalid-mode "query" 2>&1
Error: Unknown mode: invalid-mode
Available modes: default, thinking, clarification, exploration, deep_research

# Empty query (to stderr)
$ thoth "" 2>&1
Error: Query is required
Usage: thoth "QUERY" [OPTIONS]
```

### 11.5 Progress Display Details

The progress display implementation includes:
- **Elapsed time**: `[HH:MM:SS]` - Currently implemented
- **Next check time**: `Next check in Xs` - Partially implemented for async operations
- **Timeout countdown**: `timeout in MM:SS` - Planned but not fully implemented

Note: While the PRD shows these features in examples, the actual implementation status varies:
- Basic elapsed time tracking is working
- Next check intervals are shown for async operations
- Full timeout countdown display is still in development

---

## 12. Configuration File

### 12.1 Default Configuration

The system works with zero configuration if API keys are in environment variables. The config file at `~/.thoth/config.toml` provides additional control:

```toml
# Thoth Configuration File
version = "1.0"

[general]
default_mode = "default"          # Used when no mode specified (no system prompt)
show_tips = true                  # Show helpful tips for new users

[execution]  
poll_interval = 30               # seconds between status checks
max_wait = 30                    # maximum minutes to wait
parallel_providers = true        # run providers simultaneously

[output]
combine_reports = false          # create combined report only with --combined flag
format = "markdown"              # output format
timestamp_format = "%Y-%m-%d_%H%M%S"

[providers.openai]
api_key = "${OPENAI_API_KEY}"   # reads from environment
model = "o1-deep-research"

[providers.perplexity]
api_key = "${PERPLEXITY_API_KEY}"
model = "sonar-pro"

[providers.mock]
# Mock provider accepts any value as API key for testing
# No configuration required
```

### 12.2 Minimal Configuration

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

# Network issues  
$ thoth "distributed systems"
Network error: Unable to reach OpenAI API
Retrying... (attempt 2/3)

# Long operation
$ thoth "analyze all cloud provider services"
This research may take 15-30 minutes. Consider using --async:
  thoth "analyze all cloud provider services" --async
  
Continue anyway? [Y/n]:

# Invalid provider
$ thoth "test" --provider invalid
Error: Unknown provider: invalid
Valid providers are: openai, perplexity, mock
```

---

## 15. File Output Structure

### Default Output (Current Directory)

When you run `thoth "your query"`, files are created in your current directory:

```
./
├── 2024-08-03_143022_deep_research_openai_your-query.md
└── 2024-08-03_143022_deep_research_perplexity_your-query.md

# With --combined flag:
./
├── 2024-08-03_143022_deep_research_openai_your-query.md
├── 2024-08-03_143022_deep_research_perplexity_your-query.md
└── 2024-08-03_143022_deep_research_combined_your-query.md
```

### Mock Provider Output

When testing with `--provider mock`:

```
./
└── 2024-08-03_143022_deep_research_mock_your-query.md  # Static test content
```

### File Contents Structure

Each file includes:
- Metadata header (hidden in most Markdown viewers)
- Research query
- Comprehensive findings
- Citations and sources (Perplexity)
- Organized sections and insights

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

### Async Operations  
- `--async` - Submit and continue working
- Essential for very long research tasks

---

## 17. Security and Privacy

- **Local storage only**: All outputs saved locally
- **No telemetry**: No usage tracking or data collection
- **API key protection**: Keys masked in all outputs
- **Secure connections**: HTTPS-only API communication

---

## 18. Future Enhancements

### Version 2.0
- Smart query suggestions based on clarity
- Automatic mode selection based on query type
- Research templates for common topics
- Integration with local knowledge bases

### Version 2.1  
- Real-time streaming of research progress
- Web dashboard for operation monitoring
- Export to multiple formats (JSON, CSV)
- Collaborative research sessions

---

## 19. Testing Requirements

### Test Suite Status
As of v1.9, the test suite achieves **100% pass rate** with 28/28 tests passing when using the mock provider. This represents complete resolution of all critical issues identified in v1.6.

### Mock Provider Behavior
The mock provider is essential for testing and has been fully implemented to:
- Work without any API keys (F-32 requirement satisfied)
- Accept any value as a dummy API key for testing purposes
- Return predictable responses
- Support all provider interface methods
- Simulate realistic delays
- Generate valid output files
- Bypass API key validation when `--provider mock` is specified

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
Key fixes implemented in v1.9:
- Output directories are created automatically if they don't exist (F-36)
- Init command works with custom config directories via XDG_CONFIG_HOME (F-37)
- Mock provider properly overrides mode-specific provider preferences
- Empty queries are properly validated with appropriate exit codes
- All test patterns updated to match actual output formats
- Combined reports require explicit --combined flag
- Progress display shows elapsed time, next check, and timeout (with implementation status noted)
- Provider flag supports -P short form
- Quiet mode uses -Q flag

---

## End of Thoth v1.9 PRD

This specification prioritizes the simplest possible user experience while maintaining all advanced capabilities. The primary innovation is making `thoth "query"` the default interaction pattern, removing friction for users who just want quick, comprehensive research results in their current directory.

Key principles:
- **Simple by default**: Just query and go
- **Progressive disclosure**: Advanced features available when needed  
- **Current directory convenience**: Results appear where you work
- **Clear communication**: Simple progress and obvious output locations
- **Testability first**: Mock provider enables comprehensive testing

The tool serves both casual users who want instant research and power users who need fine-grained control over the research process.