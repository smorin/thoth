# Product Requirements Document – Thoth v1.2

---

## 1. Document Control

| Item | Value |
|------|-------|
| Author | System Design Team |
| Date | 29 Jul 2025 |
| Status | Production-Ready |
| Target Release | v1.2 (initial release specification) |
| Document Version | 13.0 |

---

## 2. Executive Summary

Thoth v1.2 is a command-line interface (CLI) tool that automates deep technical research using multiple LLM providers. It orchestrates parallel execution of OpenAI's Deep Research API and Perplexity's research models to deliver comprehensive, multi-perspective research reports. Built as a single-file Python script with UV inline dependencies for zero-configuration deployment, Thoth provides both synchronous and asynchronous operation modes, intelligent provider selection, and robust handling of long-running operations (5-30+ minutes).

### Core Value Propositions
- **Multi-provider intelligence**: Parallel execution of OpenAI and Perplexity for comprehensive results
- **Zero-configuration deployment**: UV inline script dependencies eliminate setup complexity
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
- UV inline dependency block for zero-install execution
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
4. **Zero system friction** via UV inline dependencies
5. **Config-over-code** – all settings in single TOML file, overridable via CLI
6. **Multi-provider orchestration** – leverage multiple LLMs in parallel by default
7. **Graceful long operation handling** – support for 5-30+ minute research tasks
8. **POSIX compatibility** – run on macOS and Linux

---

## 6. Out of Scope (v1.2)

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

- Python ≥ 3.11 installed (UV will handle dependency management)
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
| F-19 | Checkpoint operations at meaningful state changes: operation_start, provider_start, provider_complete, provider_fail, operation_complete, operation_fail | Should |
| F-20 | Ad-hoc mode saves to current directory when no project specified | Must |
| F-21 | Project mode saves to `base_output_dir/project-name/` (directory created automatically if needed) | Must |
| F-22 | Generate combined report from multi-provider results when combine_reports=true in config | Should |
| F-23 | Path expansion for all file paths in config (handle ~) | Must |
| F-24 | Environment variable substitution in config file | Must |
| F-25 | Modes can reference previous outputs via --input-file flag | Must |
| F-26 | Mode-specific auto_input overrides global execution.auto_input | Must |
| F-27 | When mode specifies "previous", automatically look for latest output from previous mode in chain | Must |
| F-28 | For multi-provider previous steps, use latest file from each provider as inputs; support stdin via --query-file - | Must |
| F-29 | If one provider fails in multi-provider mode, continue with others and note failure | Must |
| F-30 | --output-dir flag overrides all other output location logic | Must |
| F-31 | Support --query-file flag for reading query from file (use '-' for stdin, max 1MB) | Must |
| F-32 | If no previous outputs found in mode chaining, warn user and continue without inputs | Must |
| F-33 | Mode chaining should gracefully handle missing or incompatible provider outputs | Must |
| F-34 | Research operations require both mode and query parameters | Must |
| F-35 | Use strict pattern matching (YYYY-MM-DD_HHMMSS_<mode>_<provider>_<slug>.(md|json)) when finding output files | Must |
| F-36 | Provide detailed provider progress tracking showing elapsed time and next poll time | Should |
| F-37 | When --provider specified with multi-provider mode, use only that provider | Must |
| F-38 | Progress percentages estimated based on typical operation times for each provider | Should |
| F-39 | Handle checkpoint file corruption gracefully with warning and recreation | Must |
| F-40 | Automatic retry on transient network errors with exponential backoff | Must |
| F-41 | Clear error messages for disk space, API quota, and network connectivity issues | Must |
| F-42 | Configuration file includes version field; warn on schema mismatch | Should |
| F-43 | Operation IDs use 16-character UUID suffix for uniqueness | Must |
| F-44 | Combined reports saved as <timestamp>_<mode>_combined_<slug>.md | Must |
| F-45 | "Thinking" mode is single-provider only | Must |

---

## 9. Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| N-01 | Poll requests ≤ 2 per minute (30-second default interval) |
| N-02 | Tool runs on POSIX systems (macOS and Linux) |
| N-03 | Only libraries declared in UV script metadata are imported |
| N-04 | Graceful exit on interrupt (Ctrl-C) with checkpoint save |
| N-05 | Startup time < 100ms with cached UV dependencies |
| N-06 | Time to first result < 30 seconds (Perplexity) |
| N-07 | Checkpoint save time < 500ms |
| N-08 | Provider success rate > 95% |
| N-09 | Recovery success > 99% from valid checkpoints |
| N-10 | Memory usage < 200MB typical, < 500MB peak |
| N-11 | Handle symlinks by resolving to absolute paths |
| N-12 | Operation ID collision probability < 0.0001% with 16-char UUID |

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
- Files are created by default (no `--structured` flag needed)
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

## 13. Technical Specifications

### 13.1 Script Header

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "click>=8.0",
#   "openai>=1.14.0",
#   "httpx>=0.27.0",
#   "rich>=13.7",
#   "platformdirs>=3.0",
#   "aiofiles>=23.0",
#   "tenacity>=8.0",
#   "python-dateutil>=2.8"
# ]
# ///
```

### 13.2 Core Implementation Structure

```python
import asyncio
import json
import os
import sys
import time
import tomllib
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Literal, Any
from uuid import uuid4

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from platformdirs import user_config_dir
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from openai import AsyncOpenAI
import httpx

console = Console()

# Version tracking
CONFIG_VERSION = "1.0"

# Configuration Management
class Config:
    """Manages configuration loading and validation"""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path(user_config_dir("thoth")) / "config.toml"
        self.data = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load and validate configuration"""
        if not self.config_path.exists():
            return self._default_config()
        
        with open(self.config_path, "rb") as f:
            config = tomllib.load(f)
        
        # Check configuration version
        config_version = config.get("version", "0.0")
        if config_version != CONFIG_VERSION:
            console.print(f"[yellow]Warning:[/yellow] Configuration version mismatch. Expected {CONFIG_VERSION}, found {config_version}")
            console.print("[yellow]Some settings may not work as expected. Run 'thoth init' to update.[/yellow]")
        
        # Expand paths - handle symlinks by resolving to absolute paths
        if "paths" in config:
            for key, value in config["paths"].items():
                path = Path(value).expanduser()
                if path.exists() and path.is_symlink():
                    path = path.resolve()
                config["paths"][key] = str(path)
        
        # Handle environment variables
        config = self._substitute_env_vars(config)
        
        return config
    
    def _substitute_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Replace ${VAR} with environment variable values"""
        def substitute(value):
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                var_name = value[2:-1]
                return os.getenv(var_name, value)
            elif isinstance(value, dict):
                return {k: substitute(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [substitute(v) for v in value]
            return value
        
        return substitute(config)
    
    def _default_config(self) -> Dict[str, Any]:
        """Return default configuration"""
        return {
            "version": CONFIG_VERSION,
            "general": {
                "default_project": "",  # Empty means ad-hoc mode
                "default_mode": "deep_research"
            },
            "paths": {
                "base_output_dir": "./research-outputs",
                "checkpoint_dir": str(Path(user_config_dir("thoth")) / "checkpoints")
            },
            "execution": {
                "poll_interval": 30,
                "max_wait": 30,
                "parallel_providers": True,
                "retry_attempts": 3,
                "auto_input": True
            },
            "output": {
                "combine_reports": True
            }
        }

# Utility Functions
def generate_operation_id() -> str:
    """Generate unique operation ID with 16-char UUID suffix"""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    unique_suffix = str(uuid4()).replace('-', '')[:16]  # 16 chars for better uniqueness
    return f"research-{timestamp}-{unique_suffix}"

def sanitize_slug(text: str, max_length: int = 50) -> str:
    """Convert text to filename-safe slug"""
    import re
    # Keep alphanumeric and spaces, replace spaces with hyphens
    slug = re.sub(r'[^a-zA-Z0-9\s-]', '', text)
    slug = re.sub(r'\s+', '-', slug.strip())
    return slug[:max_length].lower()

def mask_api_key(key: str) -> str:
    """Mask API key for display"""
    if not key or len(key) < 8:
        return "***"
    return f"{key[:3]}...{key[-3:]}"

def check_disk_space(path: Path, required_mb: int = 100) -> bool:
    """Check if sufficient disk space is available"""
    import shutil
    stat = shutil.disk_usage(path)
    available_mb = stat.free / (1024 * 1024)
    return available_mb >= required_mb

# Data Models
@dataclass
class OperationStatus:
    """Status of a research operation"""
    id: str
    query: str
    mode: str
    status: Literal["queued", "running", "completed", "failed", "cancelled"]
    created_at: datetime
    updated_at: datetime
    providers: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    output_paths: Dict[str, Path] = field(default_factory=dict)
    error: Optional[str] = None
    progress: float = 0.0  # 0.0 to 1.0
    project: Optional[str] = None
    input_files: List[Path] = field(default_factory=list)

# Click CLI Implementation
@click.group(invoke_without_command=True)
@click.pass_context
@click.argument('mode', required=False)
@click.argument('query', required=False)
@click.option('--mode', '-m', 'mode_opt', help='Research mode')
@click.option('--query', '-q', 'query_opt', help='Research query')
@click.option('--query-file', '-Q', help='Read query from file (use - for stdin)')
@click.option('--async', '-A', 'async_mode', is_flag=True, help='Submit and exit')
@click.option('--resume', '-R', 'resume_id', help='Resume operation by ID')
@click.option('--project', '-p', help='Project name')
@click.option('--output-dir', '-o', help='Override output directory')
@click.option('--provider', '-P', type=click.Choice(['openai', 'perplexity']), help='Single provider')
@click.option('--input-file', help='Use output from previous mode as input')
@click.option('--auto', is_flag=True, help='Automatically use latest relevant output as input')
@click.option('--verbose', '-v', is_flag=True, help='Enable debug output')
def cli(ctx, mode, query, mode_opt, query_opt, query_file, async_mode, resume_id, 
        project, output_dir, provider, input_file, auto, verbose):
    """Thoth - AI-Powered Research Assistant
    
    Run research with: thoth MODE "QUERY"
    Or use commands: init, status, list
    """
    # If no subcommand, run research
    if ctx.invoked_subcommand is None:
        # Resolve mode and query from positional or options
        final_mode = mode or mode_opt
        final_query = query or query_opt
        
        # Handle query file
        if query_file:
            if query_file == '-':
                # Read from stdin with size limit
                stdin_data = sys.stdin.read(1024 * 1024)  # 1MB limit
                if len(stdin_data) >= 1024 * 1024:
                    raise click.BadParameter("Stdin input exceeds 1MB limit")
                final_query = stdin_data
            else:
                with open(query_file, 'r') as f:
                    final_query = f.read()
        
        # Validation
        if async_mode and resume_id:
            raise click.BadParameter("Cannot use --async with --resume")
        
        if query_file and (query or query_opt):
            raise click.BadParameter("Cannot use --query-file with --query")
            
        if input_file and auto:
            raise click.BadParameter("Cannot use --input-file with --auto")
        
        if resume_id:
            # Resume existing operation
            asyncio.run(resume_operation(resume_id, verbose))
        elif final_mode and final_query:
            # Run new research
            asyncio.run(run_research(
                mode=final_mode,
                query=final_query,
                async_mode=async_mode,
                project=project,
                output_dir=output_dir,
                provider=provider,
                input_file=input_file,
                auto=auto,
                verbose=verbose
            ))
        else:
            # Show help if no valid command
            console.print(ctx.get_help())

@cli.command()
def init():
    """Initialize Thoth configuration"""
    console.print("[bold]Welcome to Thoth Research Assistant Setup![/bold]\n")
    
    # Implementation of interactive setup wizard
    # ... (wizard code here)
    
    console.print("\n[green]✓[/green] Configuration saved!")

@cli.command()
@click.argument('operation_id')
def status(operation_id):
    """Check status of a research operation"""
    asyncio.run(show_status(operation_id))

@cli.command()
@click.option('--all', is_flag=True, help='Show all operations')
def list(all):
    """List research operations"""
    asyncio.run(list_operations(show_all=all))

# Async Functions
async def run_research(mode: str, query: str, async_mode: bool, 
                      project: Optional[str], 
                      output_dir: Optional[str], provider: Optional[str],
                      input_file: Optional[str], auto: bool, verbose: bool):
    """Execute research operation"""
    config = Config()
    
    # Check disk space
    output_path = Path(output_dir) if output_dir else Path.cwd()
    if not check_disk_space(output_path):
        raise ThothError("Insufficient disk space", "Free up at least 100MB", exit_code=8)
    
    # Validate that mode and query are provided
    if not mode or not query:
        raise click.BadParameter("Both mode and query are required for research operations")
    
    # Create operation
    operation_id = generate_operation_id()
    
    if verbose:
        console.print(f"[dim]Operation ID: {operation_id}[/dim]")
    
    # Handle input files
    input_files = []
    if input_file:
        input_files.append(Path(input_file))
    elif auto:
        # Check mode-specific auto_input first, then global
        mode_config = config.data.get("modes", {}).get(mode, {})
        mode_auto = mode_config.get("auto_input")
        global_auto = config.data["execution"].get("auto_input", False)
        
        if mode_auto is not None:
            use_auto = mode_auto
        else:
            use_auto = global_auto
            
        if use_auto:
            # Find latest relevant output
            input_files = await find_latest_outputs(mode, project)
            if not input_files:
                console.print("[yellow]Warning:[/yellow] No previous outputs found for auto-input")
    
    # Submit to providers
    if async_mode:
        # Submit and exit
        console.print(f"[green]✓[/green] Research submitted")
        console.print(f"Operation ID: [bold]{operation_id}[/bold]")
        console.print(f"\nCheck status: [dim]thoth status {operation_id}[/dim]")
    else:
        # Wait for completion with progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            TextColumn("| Next poll: {task.fields[next_poll]}s"),
            console=console
        ) as progress:
            task = progress.add_task("Researching...", total=100, next_poll=30)
            
            # Simulate progress with estimated times
            start_time = time.time()
            estimated_duration = get_estimated_duration(mode, provider)
            
            for i in range(100):
                await asyncio.sleep(0.1)
                elapsed = time.time() - start_time
                
                # Calculate progress based on estimated duration
                if elapsed < estimated_duration:
                    estimated_progress = int((elapsed / estimated_duration) * 100)
                    actual_progress = min(i, estimated_progress)
                else:
                    actual_progress = i
                
                next_poll = max(0, 30 - int(elapsed % 30))
                progress.update(task, completed=actual_progress, next_poll=next_poll)
        
        console.print(f"\n[green]✓[/green] Research completed!")
        if project:
            console.print(f"Results saved to: [dim]research-outputs/{project}/[/dim]")
        else:
            console.print(f"Results saved to: [dim]current directory[/dim]")

def get_estimated_duration(mode: str, provider: Optional[str]) -> float:
    """Get estimated duration in seconds based on mode and provider"""
    estimates = {
        "thinking": {"openai": 10, "perplexity": 8},
        "clarification": {"openai": 15, "perplexity": 12},
        "exploration": {"openai": 60, "perplexity": 45},
        "deep_research": {"openai": 300, "perplexity": 180, "combined": 300}
    }
    
    mode_estimates = estimates.get(mode, {"default": 60})
    if provider:
        return mode_estimates.get(provider, 60)
    else:
        # For multi-provider modes, use the max time
        return mode_estimates.get("combined", max(mode_estimates.values(), default=60))

async def find_latest_outputs(current_mode: str, project: Optional[str]) -> List[Path]:
    """Find latest outputs from previous mode in chain"""
    config = Config()
    mode_config = config.data.get("modes", {}).get(current_mode, {})
    previous_mode = mode_config.get("previous")
    
    if not previous_mode:
        return []
    
    # Determine search directory
    if project:
        search_dir = Path(config.data["paths"]["base_output_dir"]) / project
    else:
        search_dir = Path.cwd()
    
    # Use strict pattern matching to avoid false matches
    # Pattern: YYYY-MM-DD_HHMMSS_<mode>_<provider>_<slug>.(md|json)
    pattern = f"*_*_{previous_mode}_*_*.md"
    files = sorted(search_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    
    # Validate files match expected pattern more strictly
    valid_files = []
    for file in files:
        parts = file.stem.split('_')
        if len(parts) >= 5:  # Ensure we have all expected parts
            # Validate timestamp format
            try:
                datetime.strptime(f"{parts[0]}_{parts[1]}", "%Y-%m-%d_%H%M%S")
                if parts[2] == previous_mode:  # Confirm mode matches
                    valid_files.append(file)
            except ValueError:
                continue
    
    # Return latest file for each provider
    providers_found = set()
    result = []
    for file in valid_files:
        parts = file.stem.split('_')
        if len(parts) >= 4:
            provider = parts[3]
            # Skip combined reports when collecting inputs
            if provider != "combined" and provider not in providers_found:
                providers_found.add(provider)
                result.append(file)
    
    return result

# API Integration
class ResearchProvider:
    """Base class for research providers"""
    
    async def submit(self, query: str, mode: str) -> str:
        """Submit research and return job ID"""
        raise NotImplementedError
    
    async def check_status(self, job_id: str) -> Dict[str, Any]:
        """Check job status with progress information"""
        raise NotImplementedError
    
    def supports_progress(self) -> bool:
        """Whether this provider supports progress reporting"""
        return False

class OpenAIProvider(ResearchProvider):
    """OpenAI Deep Research implementation"""
    
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException))
    )
    async def submit(self, query: str, mode: str) -> str:
        """Submit to OpenAI with automatic retry on network errors"""
        try:
            response = await self.client.chat.completions.create(
                model="o1-deep-research",
                messages=[
                    {"role": "system", "content": "You are a deep research assistant."},
                    {"role": "user", "content": query}
                ],
                extra_body={
                    "background": True,
                    "tools": ["web_search", "code_interpreter"]
                }
            )
            return response.id
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise APIQuotaError("openai")
            raise
        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] OpenAI provider failed: {str(e)}")
            raise
```

### 13.3 Dependencies
- **click**: Command-line interface framework
- **openai**: OpenAI API client
- **httpx**: Async HTTP client with retry support
- **rich**: Terminal formatting and progress display
- **platformdirs**: POSIX systems config directory paths
- **aiofiles**: Async file I/O
- **tenacity**: Retry logic with exponential backoff
- **python-dateutil**: Date/time utilities

---

## 14. Configuration File

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

## 15. Implementation Architecture

### 15.1 Project Structure

```
thoth                          # Single Python file
├── Script header with UV deps
├── Configuration management
├── Data models
├── CLI implementation (Click)
├── Provider abstractions
├── Async orchestration
├── Output management
├── Error handling
└── Main entry point
```

### 15.2 Core Components

```python
# Main Orchestrator
class ThothOrchestrator:
    """Coordinates multi-provider research operations"""
    
    def __init__(self, config: Config):
        self.config = config
        self.checkpoint_manager = CheckpointManager(config)
        self.output_manager = OutputManager(config)
        self.providers = self._init_providers()
    
    async def execute_research(
        self,
        query: str,
        mode: str,
        wait: bool = True,
        project: Optional[str] = None,
        output_dir: Optional[str] = None,
        providers: Optional[List[str]] = None,
        input_files: Optional[List[Path]] = None,
        **options
    ) -> OperationStatus:
        """Execute research with specified parameters"""
        operation = OperationStatus(
            id=generate_operation_id(),
            query=query,
            mode=mode,
            status="queued",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            project=project,
            input_files=input_files or []
        )
        
        # Save initial checkpoint
        await self.checkpoint_manager.save(operation)
        
        if wait:
            return await self._execute_sync(operation, output_dir, providers, options)
        else:
            # Submit async
            asyncio.create_task(
                self._execute_async(operation, output_dir, providers, options)
            )
            return operation
    
    async def _execute_sync(self, operation: OperationStatus, output_dir: Optional[str],
                           providers: Optional[List[str]], options: Dict[str, Any]) -> OperationStatus:
        """Execute research synchronously with multi-provider support"""
        # Trigger checkpoint for operation start
        if self.checkpoint_manager.trigger_checkpoint("operation_start"):
            await self.checkpoint_manager.save(operation)
            
        # Get providers to use
        mode_config = self.config.data.get("modes", {}).get(operation.mode, {})
        
        # Check if this is a single-provider mode (thinking is always single-provider)
        if operation.mode == "thinking" or "provider" in mode_config:
            # Single-provider mode
            default_provider = mode_config.get("provider", "openai")
            providers_to_use = [providers[0]] if providers else [default_provider]
        elif "providers" in mode_config:
            # Multi-provider mode
            if providers:
                # When --provider is specified, use only that provider
                providers_to_use = providers
            else:
                providers_to_use = mode_config.get("providers", ["openai"])
        else:
            # Default to single provider
            providers_to_use = [providers[0]] if providers else ["openai"]
        
        # Track failures
        failed_providers = []
        successful_providers = []
        
        # Execute providers
        if self.config.data["execution"]["parallel_providers"] and len(providers_to_use) > 1:
            # Parallel execution
            tasks = []
            for provider_name in providers_to_use:
                if provider_name in self.providers:
                    # Trigger provider start checkpoint
                    if self.checkpoint_manager.trigger_checkpoint("provider_start"):
                        operation.providers[provider_name] = {"status": "starting"}
                        await self.checkpoint_manager.save(operation)
                        
                    task = self._execute_provider(operation, provider_name, output_dir)
                    tasks.append((provider_name, task))
            
            # Wait for all tasks
            for provider_name, task in tasks:
                try:
                    await task
                    successful_providers.append(provider_name)
                    # Trigger provider complete checkpoint
                    if self.checkpoint_manager.trigger_checkpoint("provider_complete"):
                        operation.providers[provider_name]["status"] = "completed"
                        await self.checkpoint_manager.save(operation)
                except APIQuotaError as e:
                    console.print(f"[red]API quota exceeded for {provider_name}[/red]")
                    failed_providers.append(provider_name)
                    operation.providers[provider_name] = {"status": "failed", "error": "API quota exceeded"}
                except DiskSpaceError as e:
                    console.print(f"[red]Insufficient disk space[/red]")
                    raise  # Critical error, abort everything
                except Exception as e:
                    console.print(f"[yellow]Provider {provider_name} failed:[/yellow] {str(e)}")
                    failed_providers.append(provider_name)
                    # Trigger provider fail checkpoint  
                    if self.checkpoint_manager.trigger_checkpoint("provider_fail"):
                        operation.providers[provider_name]["status"] = "failed"
                        operation.providers[provider_name]["error"] = str(e)
                        await self.checkpoint_manager.save(operation)
        else:
            # Sequential execution
            for provider_name in providers_to_use:
                if provider_name in self.providers:
                    try:
                        # Trigger provider start checkpoint
                        if self.checkpoint_manager.trigger_checkpoint("provider_start"):
                            operation.providers[provider_name] = {"status": "starting"}
                            await self.checkpoint_manager.save(operation)
                            
                        await self._execute_provider(operation, provider_name, output_dir)
                        successful_providers.append(provider_name)
                        
                        # Trigger provider complete checkpoint
                        if self.checkpoint_manager.trigger_checkpoint("provider_complete"):
                            operation.providers[provider_name]["status"] = "completed"
                            await self.checkpoint_manager.save(operation)
                    except APIQuotaError as e:
                        console.print(f"[red]API quota exceeded for {provider_name}[/red]")
                        failed_providers.append(provider_name)
                        operation.providers[provider_name] = {"status": "failed", "error": "API quota exceeded"}
                    except DiskSpaceError as e:
                        console.print(f"[red]Insufficient disk space[/red]")
                        raise  # Critical error, abort everything
                    except Exception as e:
                        console.print(f"[yellow]Provider {provider_name} failed:[/yellow] {str(e)}")
                        failed_providers.append(provider_name)
                        # Trigger provider fail checkpoint
                        if self.checkpoint_manager.trigger_checkpoint("provider_fail"):
                            operation.providers[provider_name]["status"] = "failed"
                            operation.providers[provider_name]["error"] = str(e)
                            await self.checkpoint_manager.save(operation)
        
        # Update operation status
        if failed_providers and len(failed_providers) == len(providers_to_use):
            operation.status = "failed"
            operation.error = "All providers failed"
            # Trigger operation fail checkpoint
            if self.checkpoint_manager.trigger_checkpoint("operation_fail"):
                await self.checkpoint_manager.save(operation)
        else:
            operation.status = "completed"
            if failed_providers:
                operation.error = f"Partial failure: {', '.join(failed_providers)} failed"
            # Trigger operation complete checkpoint
            if self.checkpoint_manager.trigger_checkpoint("operation_complete"):
                await self.checkpoint_manager.save(operation)
                
            # Generate combined report if configured and multiple providers succeeded
            if (self.config.data["output"].get("combine_reports", False) and 
                len(successful_providers) > 1 and 
                len(operation.output_paths) > 1):
                await self._generate_combined_report(operation, output_dir)
        
        operation.updated_at = datetime.now()
        await self.checkpoint_manager.save(operation)
        
        return operation

# Checkpoint Management
class CheckpointManager:
    """Handles operation persistence with corruption recovery"""
    
    def __init__(self, config: Config):
        self.checkpoint_dir = Path(config.data["paths"]["checkpoint_dir"])
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    async def save(self, operation: OperationStatus) -> None:
        """Save operation state atomically"""
        checkpoint_file = self.checkpoint_dir / f"{operation.id}.json"
        temp_file = checkpoint_file.with_suffix(".tmp")
        
        data = asdict(operation)
        # Convert datetime and Path objects to strings
        data["created_at"] = operation.created_at.isoformat()
        data["updated_at"] = operation.updated_at.isoformat()
        data["output_paths"] = {
            k: str(v) for k, v in operation.output_paths.items()
        }
        data["input_files"] = [str(p) for p in operation.input_files]
        
        async with aiofiles.open(temp_file, 'w') as f:
            await f.write(json.dumps(data, indent=2))
        
        temp_file.replace(checkpoint_file)
    
    async def load(self, operation_id: str) -> Optional[OperationStatus]:
        """Load operation from checkpoint with corruption handling"""
        checkpoint_file = self.checkpoint_dir / f"{operation_id}.json"
        
        if not checkpoint_file.exists():
            return None
        
        try:
            async with aiofiles.open(checkpoint_file, 'r') as f:
                data = json.loads(await f.read())
            
            # Convert back to proper types
            data["created_at"] = datetime.fromisoformat(data["created_at"])
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
            data["output_paths"] = {
                k: Path(v) for k, v in data["output_paths"].items()
            }
            data["input_files"] = [Path(p) for p in data.get("input_files", [])]
            
            return OperationStatus(**data)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            console.print(f"[yellow]Warning:[/yellow] Checkpoint file corrupted: {checkpoint_file}")
            console.print(f"[yellow]Creating new checkpoint. Previous state lost.[/yellow]")
            # Remove corrupted file
            checkpoint_file.unlink()
            return None
    
    def trigger_checkpoint(self, event: str) -> bool:
        """Determine if checkpoint should be saved based on event"""
        checkpoint_events = [
            "operation_start",
            "provider_start",
            "provider_complete",
            "provider_fail",
            "operation_complete",
            "operation_fail"
        ]
        return event in checkpoint_events

# Output Management
class OutputManager:
    """Manages research output files"""
    
    def __init__(self, config: Config):
        self.config = config
        self.base_output_dir = Path(config.data["paths"]["base_output_dir"])
        self.format = config.data["output"]["format"]
    
    def get_output_path(
        self,
        operation: OperationStatus,
        provider: str,
        output_dir: Optional[str] = None
    ) -> Path:
        """Generate output path based on mode"""
        timestamp = operation.created_at.strftime(
            self.config.data["output"]["timestamp_format"]
        )
        slug = sanitize_slug(operation.query)
        
        # Determine output directory
        if output_dir:
            # Explicit override - takes precedence over everything
            base_dir = Path(output_dir)
        elif operation.project:
            # Project mode
            base_dir = self.base_output_dir / operation.project
        else:
            # Ad-hoc mode - current directory
            base_dir = Path.cwd()
        
        # Ensure directory exists
        base_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename with provider
        ext = "md" if self.format == "markdown" else "json"
        if provider == "combined":
            # Special case for combined reports: <timestamp>_<mode>_combined_<slug>.md
            base_name = f"{timestamp}_{operation.mode}_combined_{slug}"
        else:
            base_name = f"{timestamp}_{operation.mode}_{provider}_{slug}"
        filename = f"{base_name}.{ext}"
        
        # Handle deduplication
        output_path = base_dir / filename
        counter = 1
        while output_path.exists():
            filename = f"{base_name}-{counter}.{ext}"
            output_path = base_dir / filename
            counter += 1
        
        return output_path
    
    async def save_result(
        self,
        operation: OperationStatus,
        provider: str,
        content: str,
        output_dir: Optional[str] = None
    ) -> Path:
        """Save research result to file"""
        output_path = self.get_output_path(operation, provider, output_dir)
        
        # Check disk space before writing
        if not check_disk_space(output_path.parent, 10):  # 10MB minimum
            raise DiskSpaceError("Insufficient disk space to save results")
        
        if self.format == "markdown" and self.config.data["output"]["include_metadata"]:
            # Add metadata header
            metadata = f"""---
query: {operation.query}
mode: {operation.mode}
provider: {provider}
operation_id: {operation.id}
created_at: {operation.created_at.isoformat()}
"""
            if operation.input_files:
                metadata += "input_files:\n"
                for f in operation.input_files:
                    metadata += f"  - {f}\n"
            metadata += "---\n\n"
            content = metadata + content
        
        # Write file
        async with aiofiles.open(output_path, 'w', encoding='utf-8') as f:
            await f.write(content)
        
        return output_path
    
    async def generate_combined_report(
        self,
        operation: OperationStatus,
        contents: Dict[str, str],
        output_dir: Optional[str] = None
    ) -> Path:
        """Generate a combined report from multiple provider results"""
        # Create synthesized content
        combined_content = f"# Combined Research Report: {operation.query}\n\n"
        combined_content += f"Generated: {datetime.now().isoformat()}\n\n"
        
        for provider, content in contents.items():
            combined_content += f"\n## {provider.title()} Results\n\n"
            combined_content += content
            combined_content += "\n\n---\n\n"
        
        # Save combined report
        return await self.save_result(operation, "combined", combined_content, output_dir)
```

### 15.3 Error Handling

```python
class ThothError(Exception):
    """Base exception for Thoth errors"""
    def __init__(self, message: str, suggestion: str = None, exit_code: int = 1):
        self.message = message
        self.suggestion = suggestion
        self.exit_code = exit_code
        super().__init__(message)

class APIKeyError(ThothError):
    """Missing or invalid API key"""
    def __init__(self, provider: str):
        super().__init__(
            f"{provider} API key not found",
            f"Set {provider.upper()}_API_KEY or run 'thoth init'",
            exit_code=2
        )

class ProviderError(ThothError):
    """Provider-specific error"""
    def __init__(self, provider: str, message: str):
        super().__init__(
            f"{provider} error: {message}",
            "Check API status or try again later",
            exit_code=3
        )

class DiskSpaceError(ThothError):
    """Insufficient disk space"""
    def __init__(self, message: str):
        super().__init__(
            message,
            "Free up disk space and try again",
            exit_code=8
        )

class APIQuotaError(ThothError):
    """API quota exceeded"""
    def __init__(self, provider: str):
        super().__init__(
            f"{provider} API quota exceeded",
            "Wait for quota reset or upgrade your plan",
            exit_code=9
        )

def handle_error(error: Exception):
    """Display error with appropriate formatting"""
    if isinstance(error, ThothError):
        console.print(f"\n[red]Error:[/red] {error.message}")
        if error.suggestion:
            console.print(f"[yellow]Suggestion:[/yellow] {error.suggestion}")
        sys.exit(error.exit_code)
    elif isinstance(error, KeyboardInterrupt):
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(1)
    elif isinstance(error, httpx.NetworkError):
        console.print(f"\n[red]Network error:[/red] {str(error)}")
        console.print("[yellow]Check your internet connection and try again[/yellow]")
        sys.exit(4)
    else:
        console.print(f"\n[red]Unexpected error:[/red] {str(error)}")
        console.print("[dim]Please report this issue[/dim]")
        if os.getenv("THOTH_DEBUG"):
            console.print_exception()
        sys.exit(127)
```

---

## 16. User Experience

### 16.1 Progress Display

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

### 16.2 Status Display

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

### 16.3 List Display

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

### 16.4 Error Messages

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

## 17. Security and Privacy

### 17.1 API Key Management
- Environment variables as primary method
- Config file with `${VAR}` substitution
- Automatic masking in all output
- Never stored in checkpoints
- Validation during `init` setup

### 17.2 Data Handling
- All data stored locally
- User controls all paths
- No telemetry or tracking
- Checkpoints contain only metadata
- Standard OS file permissions
- Symlinks resolved to absolute paths

### 17.3 Best Practices
- Input sanitization for filenames
- Path traversal prevention
- No shell command execution
- Secure temp file handling
- HTTPS-only API calls
- 1MB limit on stdin input

---

## 18. Troubleshooting

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

## 19. Future Enhancements

### Version 1.3
- Webhook notifications for completion
- Anthropic Claude provider support
- HTML/PDF export functionality
- Cost tracking and estimation
- Multiple provider specification (--providers)
- Configuration migration system

### Version 1.4
- Plugin architecture for custom providers
- Web UI companion application
- Knowledge graph generation
- API server mode
- Windows support (if demand exists)
- Provider-specific progress tracking

---

## 20. Checkpoint File Schema

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

## 21. Future Considerations

The following minor optimizations and enhancements can be considered in future versions based on user feedback:

### 21.1 Progress Reporting Granularity
**Current State**: Progress percentages are estimated based on typical operation times with hardcoded estimates for each mode/provider combination.

**Future Enhancement**: 
- Add configurable progress estimates in the config file for users with consistent timing patterns
- Support provider APIs that report actual progress when available

### 21.2 Combined Report Conflict Resolution
**Current State**: Combined reports concatenate results from different providers with section headers.

**Future Enhancement**:
- Identify and highlight conflicting information between providers
- Add a summary section synthesizing key findings across providers

### 21.3 Auto-input Time Window
**Current State**: Auto-input finds the latest files from the previous mode without time constraints.

**Future Enhancement**:
- Add optional `auto_input_max_age` config setting (e.g., only use outputs from last 24 hours)
- Prevent accidentally using very old outputs in long-running projects

### 21.4 Provider Failover Strategy
**Current State**: When a provider fails, the system continues with other providers and notes the failure.

**Future Enhancement**:
- Automatic retry with different models (e.g., fallback from o1-deep-research to gpt-4)
- Different behaviors based on error type (quota vs network vs invalid request)

### 21.5 Operation Cleanup Policy
**Current State**: No automatic cleanup of old operations.

**Future Enhancement**:
- Automatic cleanup of completed operations older than N days
- Add `thoth list --clean` option to remove old operations
- Configurable retention policies

---

## End of Thoth v1.3 PRD

This production-ready specification provides a complete foundation for implementing Thoth as a robust research automation tool. All major design decisions have been made, with comprehensive coverage of:

✓ Clear provider selection behavior  
✓ Well-defined file matching patterns  
✓ Comprehensive error handling  
✓ Configuration versioning system  
✓ Detailed progress tracking approach  
✓ Complete CLI interface specification  
✓ Robust checkpoint/resume functionality  

The specification addresses all previously outstanding questions and provides clear implementation guidance for a production-quality tool on macOS and Linux environments.



Clarification (default: thinking, next: exploration) - Description: clarifying takes the prompt to get. Ask clarifying questions to get rid of anything that's ambiguous, unclear, and also make suggestions on what would be a better question. 
Exploration (default: deep research, next: deep dive) - Description: exploration looks at the topic at hand and explores some options and alternatives, different trade-offs, and makes recommendations based on the use case or just alternative and related technologies. 
Deep dive tech (default: deep research, next: tutorial) - Description: this deep dives into a specific technology, giving an overview of it, going deep on it, discussing it, and exploring it. If it's about APIs, we'll go deep into what the API is, how it works, assumptions, dependencies, if it's deprecated, common pitfalls. If it's about other technologies, we'll cover what the technology is and how it's used. 
Tutorial (default: deep research, next: solution) - Description: the tutorial goes into a detailed explanation with examples of how the technologies are used in common scenarios to get started, along with code samples, the command-line execution process, and other things that are useful to generally understand it. 
Solution (default: deep research, next: PRD) - Description: a solution generally goes into a specific solution is to solve a specific problem using technology, typically 
PRD (default: deep research, next: ) - Description: Product Requirements Document based on prior research, we'll carry the PRD looking at previous research on solutions to technologies to create a requirements document. 
TDD (default: deep research) - Description: the Technical Design Document the base on the PRD and prior research puts together a technical design document, considering best practices on the architecture and good abstractions to make things maintainable and well-structured in code. 


I don't want you to follow the above question and instructions; I want you to tell me the ways this is unclear, point out any ambiguities or anything you don't understand. Follow that by asking questions to help clarify the ambiguous points. Once there are no more unclear, ambiguous or not understood portions, help me draft a clear version of the question/instruction.