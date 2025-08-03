# Product Requirements Document – Thoth v1.5

---

## 1. Document Control

| Item | Value |
|------|-------|
| Author | System Design Team |
| Date | 30 Jul 2025 |
| Status | Production-Ready |
| Target Release | v1.5 |
| Document Version | 15.0 |

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
| Default mode | When no mode is specified, automatically uses `deep_research` mode |
| Quick mode | Simplified invocation with just a query, using all defaults |
| Mode | Workflow phase (clarification, exploration, deep_research, thinking) with its own prompt template |
| Provider | LLM backend (openai, perplexity) |
| Operation ID | Unique identifier for each research operation (format: research-YYYYMMDD-HHMMSS-xxxxxxxxxxxxxxxx) |
| Background mode | Asynchronous execution where job is submitted and CLI exits immediately |
| Ad-hoc mode | Default mode where files are saved to current working directory |
| Project mode | Mode where files are saved to `base_output_dir/project-name/` |
| Combined report | Synthesized report merging results from multiple providers |
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

---

## 6. Out of Scope (v1.5)

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
- Most users want deep research results in their current directory
- Users prefer simple commands over complex configuration
- File paths must work on POSIX systems (macOS/Linux)
- Network connectivity available for API calls
- Sufficient disk space for output artifacts

---

## 8. Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| F-01 | When no mode specified, default to `deep_research` mode | Must |
| F-02 | Accept query as single positional argument: `thoth "query"` | Must |
| F-03 | Save outputs to current directory by default | Must |
| F-04 | Support full mode specification for advanced users | Must |
| F-05 | Single config file `~/.thoth/config.toml` with all settings | Must |
| F-06 | Built-in defaults overridden by config file, overridden by CLI args | Must |
| F-07 | Create jobs in background mode; capture and return operation_id | Must |
| F-08 | Poll job status every n seconds (configurable); default 30s | Must |
| F-09 | Abort after configurable timeout; default 30 minutes | Must |
| F-10 | `--async` / `-A` submits job and exits immediately with operation_id | Must |
| F-11 | `--resume` / `-R` resumes an existing operation by ID | Must |
| F-12 | `list` command shows all active/recent operations | Must |
| F-13 | `status` command shows detailed status of specific operation | Must |
| F-14 | `init` command runs interactive setup wizard | Must |
| F-15 | Dual-provider execution for deep_research mode by default | Must |
| F-16 | Files created by default; filename pattern: `YYYY-MM-DD_HHMMSS_<mode>_<provider>_<slug>.md` | Must |
| F-17 | Show clear progress during research execution | Must |
| F-18 | Display output file locations upon completion | Must |
| F-19 | Mask API keys in all output (logs, errors, debug) | Must |
| F-20 | Generate combined report from multi-provider results by default | Must |
| F-21 | Support `--no-combined` flag to skip combined report | Should |
| F-22 | Clear error messages for missing API keys | Must |
| F-23 | Automatic retry on transient network errors | Must |
| F-24 | Path expansion for all file paths in config (handle ~) | Must |
| F-25 | Environment variable substitution in config file | Must |

### Additional Quick Mode Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| F-26 | `thoth "query"` executes deep research in current directory | Must |
| F-27 | Show simple progress indicator for quick mode | Must |
| F-28 | Display final output filenames prominently | Must |
| F-29 | Minimal output during execution unless --verbose | Must |
| F-30 | Help text shows quick mode as primary usage pattern | Must |

---

## 9. Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| N-01 | First result visible within 30 seconds |
| N-02 | Tool runs on POSIX systems (macOS and Linux) |
| N-03 | Graceful exit on interrupt (Ctrl-C) with checkpoint save |
| N-04 | Startup time < 100ms with cached dependencies |
| N-05 | Clear progress indication during long operations |
| N-06 | Memory usage < 200MB typical, < 500MB peak |
| N-07 | Operation ID collision probability < 0.0001% |
| N-08 | Simple error messages for common issues |

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
  (default)     Run research (defaults to deep_research mode)
  init          Initialize configuration with setup wizard
  status        Check status of specific operation
  list          List all active/recent operations
```

### 10.2 Usage Examples

#### Quick Mode (Primary Use Case)

```bash
# SIMPLEST USAGE - just provide a query
thoth "impact of quantum computing on cryptography"
# Creates in current directory:
#   ./2024-08-03_143022_deep_research_openai_impact-of-quantum-computing.md
#   ./2024-08-03_143022_deep_research_perplexity_impact-of-quantum-computing.md  
#   ./2024-08-03_143022_deep_research_combined_impact-of-quantum-computing.md

# More quick examples
thoth "best practices for API design"
thoth "comparison of React vs Vue frameworks"
thoth "how does TCP congestion control work"

# Quick mode with single provider
thoth "kubernetes networking explained" --provider openai
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
| --provider | -P | TEXT | Use single provider: openai or perplexity |
| --no-combined | | flag | Skip combined report generation |
| --quiet | | flag | Minimal output during execution |
| --verbose | -v | flag | Enable detailed logging |
| --help | -h | flag | Show help and exit |

### 10.4 Commands Reference

| Command | Description | Example |
|---------|-------------|---------|  
| (default) | Run research with query | `thoth "your research query"` |
| init | Setup wizard for API keys | `thoth init` |
| status ID | Show operation details | `thoth status research-20240803-143022-xxx` |
| list | Show recent operations | `thoth list` |

### 10.5 Help Text Structure

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
    
    # Async for long research
    thoth "comprehensive review of database architectures" --async

COMMANDS:
    init      Setup API keys and configuration
    status    Check research operation status  
    list      List recent research operations

OPTIONS:
    -P, --provider    Use specific provider (openai/perplexity)
    -A, --async       Submit and exit (check status later)
    -p, --project     Organize outputs in project directory
    -v, --verbose     Show detailed progress
    -h, --help        Show full help

Run 'thoth --help' for complete options and advanced usage.
```

---

## 11. User Experience

### 11.1 Quick Mode Experience

```bash
$ thoth "explain how DNS resolution works"

Researching: explain how DNS resolution works
Mode: deep_research | Providers: OpenAI + Perplexity

⠙ Starting research...
⠹ OpenAI: Analyzing topic...
⠸ Perplexity: Searching sources...
⠼ OpenAI: Deep research in progress (this may take 5-30 minutes)...
⠴ Perplexity: Analyzing 12 sources...
✓ Perplexity: Complete
⠦ OpenAI: Synthesizing findings...
✓ OpenAI: Complete

Research completed in 8m 32s

Files created:
  • 2024-08-03_143022_deep_research_openai_explain-how-dns-resolution.md
  • 2024-08-03_143022_deep_research_perplexity_explain-how-dns-resolution.md  
  • 2024-08-03_143022_deep_research_combined_explain-how-dns-resolution.md

View your research: open 2024-08-03_143022_deep_research_combined_explain-how-dns-resolution.md
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

### 11.3 Async Mode for Long Research

```bash
$ thoth "comprehensive analysis of modern cryptography algorithms" --async

Research submitted successfully!
Operation ID: research-20240803-143022-a1b2c3d4e5f6g7h8

Check status:  thoth status research-20240803-143022-a1b2c3d4e5f6g7h8
List all:      thoth list
```

### 11.4 Progress Display Variations

#### Quick Mode (Default)
```
⠋ Researching... (2m 15s elapsed)
```

#### Verbose Mode
```
Research: Modern web frameworks comparison
Mode: deep_research | Started: 14:30:22

┌─────────────────────────────────────────────────────┐
│ OpenAI Deep Research    ████████░░ 80% Analyzing     │
│ Perplexity Research     ██████████ 100% Complete     │
└─────────────────────────────────────────────────────┘

Operation ID: research-20240803-143022-a1b2c3d4e5f6g7h8
Elapsed: 12:45 | Next poll: 15s
```

---

## 12. Configuration File

### 12.1 Default Configuration

The system works with zero configuration if API keys are in environment variables. The config file at `~/.thoth/config.toml` provides additional control:

```toml
# Thoth Configuration File
version = "1.0"

[general]
default_mode = "deep_research"    # Used when no mode specified
show_tips = true                  # Show helpful tips for new users

[execution]  
poll_interval = 30               # seconds between status checks
max_wait = 30                    # maximum minutes to wait
parallel_providers = true        # run providers simultaneously

[output]
combine_reports = true           # create combined report by default
format = "markdown"              # output format
timestamp_format = "%Y-%m-%d_%H%M%S"

[providers.openai]
api_key = "${OPENAI_API_KEY}"   # reads from environment
model = "o1-deep-research"

[providers.perplexity]
api_key = "${PERPLEXITY_API_KEY}"
model = "sonar-pro"
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
2. **Set API Keys**: 
   ```bash
   export OPENAI_API_KEY="your-key"
   export PERPLEXITY_API_KEY="your-key"
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
```

---

## 14. Error Messages

### User-Friendly Error Handling

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
```

---

## 15. File Output Structure

### Default Output (Current Directory)

When you run `thoth "your query"`, files are created in your current directory:

```
./
├── 2024-08-03_143022_deep_research_openai_your-query.md
├── 2024-08-03_143022_deep_research_perplexity_your-query.md
└── 2024-08-03_143022_deep_research_combined_your-query.md  # Best starting point
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
- `thinking` - Quick analysis  
- `clarification` - Refine questions
- `exploration` - Survey options
- `deep_research` - Comprehensive research (default)

### Project Organization
- `--project NAME` - Organize outputs in dedicated directories
- Useful for ongoing research topics

### Async Operations  
- `--async` - Submit and continue working
- Essential for very long research tasks

### Provider Control
- `--provider openai` - Use only OpenAI
- `--provider perplexity` - Use only Perplexity  
- Default uses both for comprehensive coverage

---

## 17. Security and Privacy

- **Local storage only**: All outputs saved locally
- **No telemetry**: No usage tracking or data collection
- **API key protection**: Keys masked in all outputs
- **Secure connections**: HTTPS-only API communication

---

## 18. Future Enhancements

### Version 1.6
- Smart query suggestions based on clarity
- Automatic mode selection based on query type
- Research templates for common topics
- Integration with local knowledge bases

### Version 1.7  
- Real-time streaming of research progress
- Web dashboard for operation monitoring
- Export to multiple formats (PDF, HTML)
- Collaborative research sessions

---

## End of Thoth v1.5 PRD

This specification prioritizes the simplest possible user experience while maintaining all advanced capabilities. The primary innovation is making `thoth "query"` the default interaction pattern, removing friction for users who just want quick, comprehensive research results in their current directory.

Key principles:
- **Simple by default**: Just query and go
- **Progressive disclosure**: Advanced features available when needed  
- **Current directory convenience**: Results appear where you work
- **Clear communication**: Simple progress and obvious output locations

The tool serves both casual users who want instant research and power users who need fine-grained control over the research process.