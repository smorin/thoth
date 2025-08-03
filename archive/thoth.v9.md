# Product Requirements Document – Thoth v0.9

---

## 1. Document Control

| Item | Value |
|------|-------|
| Author | System Design Team |
| Date | 29 Jul 2025 |
| Status | Draft |
| Target Release | v0.9 (simplified output structure) |
| Document Version | 9.0 |

---

## 2. Executive Summary

Thoth v0.9 is a command-line interface (CLI) tool that automates deep technical research using multiple LLM providers. It orchestrates parallel execution of OpenAI's Deep Research API and Perplexity's research models to deliver comprehensive, multi-perspective research reports. Built as a single-file Python script with UV inline dependencies for zero-configuration deployment, Thoth provides both synchronous and asynchronous operation modes, intelligent provider selection, and robust handling of long-running operations (5-30+ minutes).

### Core Value Propositions
- **Multi-provider intelligence**: Parallel execution of OpenAI and Perplexity for comprehensive results
- **Zero-configuration deployment**: UV inline script dependencies eliminate setup complexity
- **Flexible operation modes**: Support both interactive (wait) and background (submit and exit) workflows
- **Production-ready reliability**: Checkpoint/resume, graceful error handling, and operation persistence
- **Simple output structure**: Intuitive file placement with ad-hoc and project modes

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

---

## 4. Glossary

| Term | Definition |
|------|------------|
| Mode | Workflow phase (clarification, exploration, deep_research, thinking) with its own prompt template |
| Model slot | Configuration section that maps to specific provider settings |
| Provider | LLM backend (openai, perplexity) |
| Operation ID | Unique identifier for each research operation (format: research-YYYYMMDD-HHMMSS-xxxxxxxx) |
| Background mode | Asynchronous execution where job is submitted and CLI exits immediately |
| Polling | Repeated status checks until a job completes or times out |
| Structured output | Files saved to disk (either current directory or project directory) |
| Ad-hoc mode | Default mode where files are saved to current working directory |
| Project mode | Mode where files are saved to `base_output_dir/project-name/` |
| Config file | Single TOML file at `~/.thoth/config.toml` containing all settings |
| Checkpoint | Saved state of an in-progress research operation for recovery |
| Slug | Sanitized version of the research query used in filenames (alphanumeric + hyphens) |

---

## 5. Objectives

1. **One-command research** with sensible defaults
2. **Async robustness** – never hang; offer `--async`, `--resume`, listing, and configurable polling
3. **Deterministic, auditable artifacts** for repeatability
4. **Zero system friction** via UV inline dependencies
5. **Config-over-code** – all settings in single TOML file, overridable via CLI
6. **Multi-provider orchestration** – leverage multiple LLMs in parallel by default
7. **Graceful long operation handling** – support for 5-30+ minute research tasks
8. **Universal compatibility** – run on macOS, Linux, and Windows

---

## 6. Out of Scope (v0.9)

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

---

## 7. Assumptions

- Python ≥ 3.11 installed (UV will handle dependency management)
- Users provide provider API keys via environment variables or config
- Deep Research jobs can take 5–30 minutes
- File paths must be cross-platform compatible
- Network connectivity available for API calls
- Sufficient disk space for output artifacts
- Users understand basic CLI operations

---

## 8. Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| F-01 | Single config file `~/.thoth/config.toml` with all settings | Must |
| F-02 | Built-in defaults overridden by config file, overridden by CLI args | Must |
| F-03 | CLI values may reference external files with `@/path` or stdin with `@-` | Must |
| F-04 | Create jobs in background mode; capture and return operation_id | Must |
| F-05 | Poll job status every n seconds (configurable); default 30s | Must |
| F-06 | Abort after configurable timeout; default 30 minutes | Must |
| F-07 | `--async` / `-A` submits job and exits immediately with operation_id | Must |
| F-08 | `--resume` / `-R` resumes an existing operation by ID | Must |
| F-09 | `list` command shows all active/recent operations | Must |
| F-10 | `status` command shows detailed status of specific operation | Must |
| F-11 | `init` command runs interactive setup wizard | Must |
| F-12 | Dual-provider execution for deep_research mode by default | Must |
| F-13 | Structured output filenames: `YYYY-MM-DD_HHMMSS_<mode>-<slug>.md` | Must |
| F-14 | Filename deduplication with numeric suffix when conflicts occur | Should |
| F-15 | Config directory auto-created on first run | Must |
| F-16 | All diagnostics to stderr; DEBUG with `--verbose` or `THOTH_DEBUG=1` | Must |
| F-17 | Persistent default project via config file | Must |
| F-18 | Retry transient errors with exponential backoff | Should |
| F-19 | Mask API keys in all output (logs, errors, debug) | Must |
| F-20 | Checkpoint operations every 2 minutes for recovery | Should |
| F-21 | Ad-hoc mode saves to current directory when no project specified | Must |
| F-22 | Project mode saves to `base_output_dir/project-name/` | Must |
| F-23 | Generate combined report from multi-provider results | Should |
| F-24 | Path expansion for all file paths in config (handle ~) | Must |
| F-25 | Environment variable substitution in config file | Must |

---

## 9. Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| N-01 | Poll requests ≤ 2 per minute (30-second default interval) |
| N-02 | Tool runs identically on macOS, Linux, Windows |
| N-03 | Only libraries declared in UV script metadata are imported |
| N-04 | Graceful exit on interrupt (Ctrl-C) with checkpoint save |
| N-05 | Startup time < 100ms with cached UV dependencies |
| N-06 | Time to first result < 30 seconds (Perplexity) |
| N-07 | Checkpoint save time < 500ms |
| N-08 | Provider success rate > 95% |
| N-09 | Recovery success > 99% from valid checkpoints |
| N-10 | Memory usage < 200MB typical, < 500MB peak |

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
# Creates: ./2024-08-03_143022_deep_research-impact-quantum.md

# Project mode - saves to project directory
thoth deep_research "quantum cryptography" --project quantum_research
# Creates: ./research-outputs/quantum_research/2024-08-03_143022_deep_research-quantum-crypto.md

# Async submission (returns immediately)
thoth deep_research "quantum cryptography" --async
# Output: Operation ID: research-20240803-143022-a1b2c3d4

# Resume operation
thoth --resume research-20240803-143022-a1b2c3d4

# Check status
thoth status research-20240803-143022-a1b2c3d4

# List operations
thoth list

# Setup wizard
thoth init
```

### 10.3 Options Reference

| Long | Short | Type | Description |
|------|-------|------|-------------|
| --mode | -m | TEXT | Research mode (can be first positional argument) |
| --query | -q | TEXT/@file/@- | Research query (can be second positional argument) |
| --async | -A | flag | Submit and exit immediately |
| --resume | -R | ID | Resume existing operation by ID |
| --structured | -s | flag | Save output to files (default: false) |
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
| --verbose | -v | flag | Enable debug logging |
| --quiet | | flag | Suppress progress output |
| --version | -V | flag | Show version and exit |
| --help | -h | flag | Show help and exit |

### 10.4 Commands Reference

| Command | Description | Example |
|---------|-------------|---------|
| init | Run interactive setup wizard | `thoth init` |
| status ID | Show detailed operation status | `thoth status research-20240803-143022-a1b2c3d4` |
| list | List all operations | `thoth list` |

### 10.5 Validation Rules
- `--async` cannot be used with `--resume`
- `--structured` with no `--project` saves to current directory
- `--structured` with `--project` saves to `base_output_dir/project/`
- `--api-key` requires `--provider` to be specified
- Mode and query can be positional or use `--mode` and `--query`
- `list` command ignores all other options except `--verbose`

---

## 11. Interactive Mode

### 11.1 Setup Wizard (`thoth init`)

```
Welcome to Thoth Research Assistant Setup!

Checking environment...
✓ Python 3.11.5 detected
✓ UV package manager available

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

Configuration saved to ~/.thoth/config.toml

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
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from platformdirs import user_config_dir
from tenacity import retry, stop_after_attempt, wait_exponential
from openai import AsyncOpenAI
import httpx

console = Console()

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
        
        # Expand paths
        if "paths" in config:
            for key, value in config["paths"].items():
                config["paths"][key] = str(Path(value).expanduser())
        
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
                "retry_attempts": 3
            }
        }

# Utility Functions
def generate_operation_id() -> str:
    """Generate unique operation ID"""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    unique_suffix = str(uuid4())[:8]
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

# Click CLI Implementation
@click.group(invoke_without_command=True)
@click.pass_context
@click.argument('mode', required=False)
@click.argument('query', required=False)
@click.option('--mode', '-m', 'mode_opt', help='Research mode')
@click.option('--query', '-q', 'query_opt', help='Research query')
@click.option('--async', '-A', 'async_mode', is_flag=True, help='Submit and exit')
@click.option('--resume', '-R', 'resume_id', help='Resume operation by ID')
@click.option('--structured', '-s', is_flag=True, help='Save output to files')
@click.option('--project', '-p', help='Project name')
@click.option('--output-dir', '-o', help='Override output directory')
@click.option('--provider', '-P', type=click.Choice(['openai', 'perplexity']), help='Single provider')
@click.option('--verbose', '-v', is_flag=True, help='Enable debug output')
def cli(ctx, mode, query, mode_opt, query_opt, async_mode, resume_id, 
        structured, project, output_dir, provider, verbose):
    """Thoth - AI-Powered Research Assistant
    
    Run research with: thoth MODE "QUERY"
    Or use commands: init, status, list
    """
    # If no subcommand, run research
    if ctx.invoked_subcommand is None:
        # Resolve mode and query from positional or options
        final_mode = mode or mode_opt
        final_query = query or query_opt
        
        # Handle file references
        if final_query and final_query.startswith('@'):
            if final_query == '@-':
                final_query = sys.stdin.read()
            else:
                with open(final_query[1:], 'r') as f:
                    final_query = f.read()
        
        # Validation
        if async_mode and resume_id:
            raise click.BadParameter("Cannot use --async with --resume")
        
        if resume_id:
            # Resume existing operation
            asyncio.run(resume_operation(resume_id, verbose))
        elif final_mode and final_query:
            # Run new research
            asyncio.run(run_research(
                mode=final_mode,
                query=final_query,
                async_mode=async_mode,
                structured=structured,
                project=project,
                output_dir=output_dir,
                provider=provider,
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
                      structured: bool, project: Optional[str], 
                      output_dir: Optional[str], provider: Optional[str], 
                      verbose: bool):
    """Execute research operation"""
    config = Config()
    
    # Create operation
    operation_id = generate_operation_id()
    
    if verbose:
        console.print(f"[dim]Operation ID: {operation_id}[/dim]")
    
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
            console=console
        ) as progress:
            task = progress.add_task("Researching...", total=100)
            
            # Simulate progress (replace with actual implementation)
            for i in range(100):
                await asyncio.sleep(0.1)
                progress.update(task, advance=1)
        
        console.print(f"\n[green]✓[/green] Research completed!")
        if structured:
            if project:
                console.print(f"Results saved to: [dim]research-outputs/{project}/[/dim]")
            else:
                console.print(f"Results saved to: [dim]current directory[/dim]")

# API Integration
class ResearchProvider:
    """Base class for research providers"""
    
    async def submit(self, query: str, mode: str) -> str:
        """Submit research and return job ID"""
        raise NotImplementedError
    
    async def check_status(self, job_id: str) -> Dict[str, Any]:
        """Check job status"""
        raise NotImplementedError

class OpenAIProvider(ResearchProvider):
    """OpenAI Deep Research implementation"""
    
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def submit(self, query: str, mode: str) -> str:
        """Submit to OpenAI"""
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
```

### 13.3 Dependencies
- **click**: Command-line interface framework
- **openai**: OpenAI API client
- **httpx**: Async HTTP client with retry support
- **rich**: Terminal formatting and progress display
- **platformdirs**: Cross-platform config directory paths
- **aiofiles**: Async file I/O
- **tenacity**: Retry logic with exponential backoff
- **python-dateutil**: Date/time utilities

---

## 14. Configuration File

Single configuration file at `~/.thoth/config.toml`:

```toml
# Thoth Configuration File
# Environment variables can be referenced with ${VAR_NAME}

[general]
default_project = ""  # Empty string means ad-hoc mode (current directory)
default_mode = "deep_research"

[paths]
base_output_dir = "./research-outputs"  # Base directory for project outputs
checkpoint_dir = "~/.thoth/checkpoints"

[execution]
poll_interval = 30        # seconds
max_wait = 30            # minutes  
parallel_providers = true
retry_attempts = 3
retry_delay = 2          # seconds (exponential backoff)

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
provider = "openai"
model = "gpt-4o-mini"
temperature = 0.4
system_prompt = "You are a helpful assistant for quick analysis."

[modes.deep_research]
providers = ["openai", "perplexity"]
parallel = true
system_prompt = """
Conduct comprehensive research with citations and multiple perspectives.
Organize findings clearly and highlight key insights.
"""

[modes.clarification]
provider = "openai"
model = "gpt-4o-mini"
system_prompt = "Help clarify ambiguous queries before deep research."

[modes.exploration]
provider = "openai"
model = "gpt-4o"
system_prompt = "Provide initial exploration and identify research directions."

[output]
format = "markdown"      # "markdown" or "json"
include_metadata = true
combine_reports = true
timestamp_format = "%Y-%m-%d_%H%M%S"

[logging]
level = "INFO"           # DEBUG, INFO, WARNING, ERROR
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
            project=project
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

# Checkpoint Management
class CheckpointManager:
    """Handles operation persistence"""
    
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
        
        async with aiofiles.open(temp_file, 'w') as f:
            await f.write(json.dumps(data, indent=2))
        
        temp_file.replace(checkpoint_file)
    
    async def load(self, operation_id: str) -> Optional[OperationStatus]:
        """Load operation from checkpoint"""
        checkpoint_file = self.checkpoint_dir / f"{operation_id}.json"
        
        if not checkpoint_file.exists():
            return None
        
        async with aiofiles.open(checkpoint_file, 'r') as f:
            data = json.loads(await f.read())
        
        # Convert back to proper types
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        data["output_paths"] = {
            k: Path(v) for k, v in data["output_paths"].items()
        }
        
        return OperationStatus(**data)

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
            # Explicit override
            base_dir = Path(output_dir)
        elif operation.project:
            # Project mode
            base_dir = self.base_output_dir / operation.project
        else:
            # Ad-hoc mode - current directory
            base_dir = Path.cwd()
        
        # Ensure directory exists
        base_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        ext = "md" if self.format == "markdown" else "json"
        base_name = f"{timestamp}_{operation.mode}-{slug}"
        if provider != "combined":
            base_name = f"{base_name}_{provider}"
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
        
        if self.format == "markdown" and self.config.data["output"]["include_metadata"]:
            # Add metadata header
            metadata = f"""---
query: {operation.query}
mode: {operation.mode}
provider: {provider}
operation_id: {operation.id}
created_at: {operation.created_at.isoformat()}
---

"""
            content = metadata + content
        
        # Write file
        async with aiofiles.open(output_path, 'w', encoding='utf-8') as f:
            await f.write(content)
        
        return output_path
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

Operation ID: research-20240803-143022-a1b2c3d4
Elapsed: 12:45 | Next poll: 15s
```

### 16.2 Status Display

```
$ thoth status research-20240803-143022-a1b2c3d4

Operation Details:
─────────────────
ID:        research-20240803-143022-a1b2c3d4
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
  └── 2024-08-03_143022_deep_research-impact-quantum_perplexity.md
```

### 16.3 List Display

```
$ thoth list

Active Research Operations:
──────────────────────────

ID                               Query                    Status    Elapsed  Mode
research-20240803-143022-a1b2c3  Impact of quantum...    running   12m      deep_research
research-20240803-141555-b4c5d6  Post-quantum crypto...   complete  45m      deep_research  
research-20240803-140233-e7f8g9  Clarify requirements...  complete  2m       clarification

Use 'thoth status <ID>' for details
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

### 17.3 Best Practices
- Input sanitization for filenames
- Path traversal prevention
- No shell command execution
- Secure temp file handling
- HTTPS-only API calls

---

## 18. Performance Metrics

### 18.1 Targets
- Startup: < 100ms (UV cached)
- First result: < 30s
- Checkpoint save: < 500ms
- Memory: < 200MB typical
- CPU during poll: < 5%

### 18.2 Quality
- Provider success: > 95%
- Multi-provider success: > 90%
- Checkpoint recovery: > 99%
- Clear errors: < 5% confusion

---

## 19. Future Enhancements

### Version 1.0
- Webhook notifications
- Anthropic Claude support
- HTML/PDF export
- Cost tracking

### Version 1.1
- Plugin architecture
- Web UI companion
- Knowledge graphs
- API server mode

---

## End of Thoth v0.9 PRD

This specification simplifies the output structure by removing the organization concept and providing intuitive ad-hoc (current directory) and project-based output modes, making the tool easier to understand and use.