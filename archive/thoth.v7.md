# Product Requirements Document – Thoth v0.7

---

## 1. Document Control

| Item | Value |
|------|-------|
| Author | System Design Team |
| Date | 29 Jul 2025 |
| Status | Draft |
| Target Release | v0.7 (corrected specification) |
| Document Version | 7.0 |

---

## 2. Executive Summary

Thoth v0.7 is a command-line interface (CLI) tool that automates deep technical research using multiple LLM providers. It orchestrates parallel execution of OpenAI's Deep Research API and Perplexity's research models to deliver comprehensive, multi-perspective research reports. Built as a single-file Python script with UV inline dependencies for zero-configuration deployment, Thoth provides both synchronous and asynchronous operation modes, intelligent provider selection, and robust handling of long-running operations (5-30+ minutes).

### Core Value Propositions
- **Multi-provider intelligence**: Parallel execution of OpenAI and Perplexity for comprehensive results
- **Zero-configuration deployment**: UV inline script dependencies eliminate setup complexity
- **Flexible operation modes**: Support both interactive (wait) and background (submit and exit) workflows
- **Production-ready reliability**: Checkpoint/resume, graceful error handling, and operation persistence
- **Deterministic outputs**: Auditable artifacts with consistent naming and organization

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
- Two output styles: stdout or structured Markdown/JSON artifacts
- Interactive wizard for users who prefer guided prompts
- Persistent defaults stored in `~/.thoth/` configuration files
- Comprehensive command-line interface with extensive options

---

## 4. Glossary

| Term | Definition |
|------|------------|
| Mode | Workflow phase (clarification, exploration, deep_research, thinking) with its own prompt template |
| Model slot | Alias that maps to {provider, model, options} |
| Provider | LLM backend (openai, perplexity) |
| Research ID | Unique identifier returned when a Deep Research job starts (same as Operation ID) |
| Operation ID | Alternative term for Research ID used in status commands (same as Research ID) |
| Background mode | Asynchronous execution in Deep Research (background=True) |
| Polling | Repeated status checks until a job completes or times out |
| Structured output | Files saved in `research-outputs/<project>/` with deterministic names |
| Defaults file | `~/.thoth/defaults.toml`; user-set system-wide defaults |
| Checkpoint | Saved state of an in-progress research operation |
| Slug | Sanitized version of the research query used in filenames (spaces to hyphens, special chars removed) |

---

## 5. Objectives

1. **One-command research** with sensible defaults
2. **Async robustness** – never hang; offer `--async`, `--resume`, listing, and configurable polling
3. **Deterministic, auditable artifacts** for repeatability
4. **Zero system friction** via UV inline dependencies
5. **Config-over-code** – modes, model-slots, and defaults overridable in user TOML files
6. **Multi-provider orchestration** – leverage multiple LLMs in parallel by default
7. **Graceful long operation handling** – support for 5-30+ minute research tasks
8. **Universal compatibility** – run on macOS, Linux, and Windows

---

## 6. Out of Scope (v0.7)

- Webhooks for completion notifications
- Private data integration (MCP)
- PDF/HTML export functionality
- Citation verification system
- Streaming token output display
- Concurrent multi-query execution
- Rich TUI with live visualizations
- Cloud storage integration
- Real-time collaboration features

---

## 7. Assumptions

- Python ≥ 3.11 installed (UV will handle dependency management)
- Users provide provider API keys via environment variables or CLI
- Deep Research jobs can take 5–30 minutes
- File paths must be cross-platform compatible
- Network connectivity available for API calls
- Sufficient disk space for output artifacts
- Users understand basic CLI operations

---

## 8. Functional Requirements – Consolidated

| ID | Requirement | Priority |
|----|-------------|----------|
| F-01 | Built-in modes hard-coded; merge user file `~/.thoth/modes.toml` if exists | Must |
| F-02 | Built-in model-slots hard-coded; merge `~/.thoth/models.toml` if exists | Must |
| F-03 | Defaults file `~/.thoth/defaults.toml` overrides built-in defaults when present | Must |
| F-04 | Any CLI value may reference an external file with `@/path` or stdin with `@-` | Must |
| F-05 | Create jobs in background mode; capture and return research_id | Must |
| F-06 | Poll job status every n seconds (`--poll-interval`); default 30s | Must |
| F-07 | Abort after x minutes (`--max-wait`); default 30 min | Must |
| F-08 | `--async` submits the job, prints research_id, and exits with code 0 | Must |
| F-09 | `--resume`/`-R` resumes an existing job by research_id | Must |
| F-10 | `--list`/`-L` lists all queued/in-progress jobs | Should |
| F-11 | Dual-provider run for mode `deep_research` unless `--provider` specified | Must |
| F-12 | Structured output filenames: `YYYYMMDD_HHMMSS-<mode>-<provider>-<slug>.{md,json}` | Must |
| F-13 | Filename deduplication by numeric suffix (-1, -2, …) when conflicts occur | Should |
| F-14 | Config directory (`~/.thoth/`) auto-created on first run | Should |
| F-15 | Interactive wizard: plain-text prompts; escape with Ctrl-C or Ctrl-D | Must |
| F-16 | All diagnostics to stderr; DEBUG enabled with `--verbose` or `THOTH_DEBUG=1` | Must |
| F-17 | Persistent default project: `--set-default-project` writes to defaults.toml | Must |
| F-18 | Command-line args override config files; config files override built-in defaults | Must |
| F-19 | Retry transient network/5xx errors up to 3 times with exponential back-off | Should |
| F-20 | Safety: mask API keys in all logs, errors, and debug output | Must |
| F-21 | Support `thoth status <id>` command to check operation status | Must |
| F-22 | Checkpoint operations every 2 minutes for crash recovery | Should |
| F-23 | Support both project-based and date-based output organization | Must |
| F-24 | Generate combined report from multi-provider results when both complete | Should |

---

## 9. Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| N-01 | Poll requests ≤ 2 per minute by default (30-second interval) |
| N-02 | Tool runs on macOS, Linux, Windows with identical behavior |
| N-03 | Only libraries declared in UV script metadata are imported |
| N-04 | Graceful exit on interrupt (Ctrl-C) or validation errors |
| N-05 | Startup time < 100ms for cached UV dependencies |
| N-06 | Time to first result < 30 seconds (Perplexity quick results) |
| N-07 | Checkpoint save time < 500ms |
| N-08 | Provider success rate > 95% for each provider |
| N-09 | Recovery success > 99% from valid checkpoints |

---

## 10. Command-Line Interface

### 10.1 Command Structure

```bash
# Primary commands
thoth [COMMAND] [OPTIONS]
thoth MODE QUERY [OPTIONS]

# Commands:
#   (default)     Run research with mode and query
#   init          Initialize configuration
#   status        Check operation status
#   list          List active operations
#   interactive   Launch interactive wizard
```

### 10.2 Usage Examples

```bash
# Basic research (synchronous)
thoth deep_research "impact of quantum computing on cryptography"

# Async submission
thoth deep_research "quantum cryptography" --async
# Returns: research-20240729-143022-a1b2c3d4

# Resume operation
thoth --resume research-20240729-143022-a1b2c3d4

# Check status
thoth status research-20240729-143022-a1b2c3d4

# List active operations
thoth list

# Interactive mode
thoth interactive

# Setup wizard
thoth init
```

### 10.3 Options Reference

| Long | Short | Value | Description |
|------|-------|-------|-------------|
| --mode | -m | NAME | Workflow mode (can also be first positional arg) |
| --query | -q | TEXT/@file/@- | Research query (can also be second positional arg) |
| --structured | -s | flag | Enable file output to disk |
| --project | -p | NAME | Project name for output organization |
| --set-default-project | -S | NAME | Set persistent default project |
| --output-dir | -o | PATH | Base directory for all outputs (default: ./research-outputs) |
| --model-slot | -M | SLOT | Override default model slot for mode |
| --provider | -P | NAME | Use single provider: openai or perplexity |
| --api-key | -k | KEY | Override API key for current run only |
| --raw | -r | flag | Output raw JSON instead of formatted markdown |
| --fast | -f | flag | Use faster, less expensive model variant |
| --no-code | | flag | Disable code interpreter for OpenAI |
| --poll-interval | -I | SECS | Seconds between status checks (default: 30) |
| --max-wait | -W | MINS | Maximum minutes to wait (default: 30) |
| --async | -A | flag | Submit and exit immediately |
| --resume | -R | ID | Resume existing operation by ID |
| --list | -L | flag | List all active operations |
| --verbose | -v | flag | Enable debug logging |
| --quiet | | flag | Suppress progress indicators |
| --version | -V | flag | Show version and exit |
| --help | -h | flag | Show help and exit |
| --parallel | | flag | Force parallel execution (default for deep_research) |
| --organization | | MODE | Output organization: project or date |

### 10.4 Mutual Exclusivity Rules
- `--async` cannot be used with `--resume`
- `--list` is a standalone command (ignores other options except `--verbose`)
- `--structured` requires either `--project` or a default project to be set
- `--provider` disables parallel multi-provider execution
- `--api-key` only applies to the provider specified by `--provider`

---

## 11. Interactive Modes

### 11.1 Setup Wizard (`thoth init`)

```bash
$ thoth init
Welcome to Thoth Research Assistant Setup!

Checking environment...
✓ Python 3.11+ detected
✓ UV package manager available

? Select default LLM providers: (Use arrow keys to move, space to select)
 ◉ OpenAI Deep Research
 ◉ Perplexity
 ○ Anthropic Claude (coming in v0.8)
 
? Enter OpenAI API key (or press Enter to use env var): ***********
? Enter Perplexity API key (or press Enter to use env var): ***********

? Default output organization:
 ❯ Project-based (recommended for ongoing research)
   Date-based (simple chronological organization)
   
? Default project name: research_notes

? Default operation mode:
 ❯ Interactive (wait for results)
   Background (submit and exit)

? Default polling interval (seconds) [30]: 30
? Maximum wait time (minutes) [30]: 30

Configuration saved to:
- ~/.thoth/defaults.toml
- ~/.thoth/models.toml (created with defaults)
- ~/.thoth/modes.toml (created with defaults)

Run 'thoth deep_research "your query"' to start researching!
```

### 11.2 Interactive Research Wizard (`thoth interactive`)

```
Thoth Interactive Research Assistant

Step 1: Select Research Mode
  1. deep_research - Comprehensive research with citations
  2. thinking - Quick analysis without deep research
  3. clarification - Clarify ambiguous queries
  4. exploration - Initial topic exploration
  
Choice [1]: 1

Step 2: Enter Your Research Query
(Multi-line input supported, press Ctrl+D when done)
> Impact of quantum computing on modern cryptography
> ^D

Step 3: Output Options
Save to file? [Y/n]: y
Project name [research_notes]: quantum_crypto_2024

Step 4: Provider Selection
For deep research, select providers:
  1. Both providers (parallel execution) [recommended]
  2. OpenAI Deep Research only
  3. Perplexity only
  
Choice [1]: 1

Step 5: Advanced Options
Use async mode? [y/N]: n
Custom poll interval (seconds) [30]: 
Enable raw JSON output? [y/N]: n
Use fast mode? [y/N]: n

Confirming your choices:
- Mode: deep_research
- Query: "Impact of quantum computing on modern cryptography"
- Providers: OpenAI + Perplexity (parallel)
- Output: Structured files in project 'quantum_crypto_2024'
- Mode: Synchronous (wait for results)

Proceed? [Y/n]: y

Starting research...
```

---

## 12. Exit Codes

| Code | Meaning | Example Scenario |
|------|---------|------------------|
| 0 | Success | Research completed successfully |
| 1 | Validation error or user abort | Invalid mode specified or Ctrl-C pressed |
| 2 | Missing API key | Required API key not found in env or config |
| 3 | Unsupported provider | User specified unknown provider name |
| 4 | API/network failure after retries | Connection failed after 3 retry attempts |
| 5 | Max-wait timeout exceeded | Research took longer than --max-wait |
| 6 | Research ID not found | Invalid ID passed to --resume or status |
| 7 | Config/IO error | Cannot write output files or read config |
| 127 | Uncaught exception | Unexpected error (bug) |

---

## 13. Technical Requirements

### 13.1 Script Header

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "openai>=1.14.0",
#   "httpx>=0.27.0",
#   "click>=8.0",
#   "rich>=13.7",
#   "questionary>=2.0",
#   "tenacity>=8.0",
#   "platformdirs>=3.0",
#   "pydantic>=2.0",
#   "aiofiles>=23.0"
# ]
# ///
```

### 13.2 Core Implementation

```python
import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Literal, Any
from uuid import uuid4

import click
from rich.console import Console
from rich.progress import Progress
import questionary
from tenacity import retry, stop_after_attempt, wait_exponential
from platformdirs import user_config_dir
from openai import AsyncOpenAI
import httpx

console = Console()

def generate_operation_id() -> str:
    """Generate unique operation ID with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    unique_id = str(uuid4())[:8]
    return f"research-{timestamp}-{unique_id}"

def sanitize_slug(text: str, max_length: int = 50) -> str:
    """Convert text to filename-safe slug"""
    # Remove special characters, convert spaces to hyphens
    slug = "".join(c if c.isalnum() or c in " -_" else "" for c in text)
    slug = "-".join(slug.split())[:max_length]
    return slug.lower()

async def submit_job(query: str, model: str, tools: List[str], provider: str = "openai") -> str:
    """Submit research job to provider"""
    if provider == "openai":
        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        resp = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a deep research assistant."},
                {"role": "user", "content": query}
            ],
            extra_body={
                "background": True,
                "reasoning": {"summary": "auto"},
                "tools": [{"type": tool} for tool in tools]
            }
        )
        return resp.id
    else:  # perplexity
        client = AsyncOpenAI(
            api_key=os.getenv("PERPLEXITY_API_KEY"),
            base_url="https://api.perplexity.ai"
        )
        resp = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": query}],
            search_domain_filter=["arxiv.org", "nature.com"],
            search_recency_filter="month",
            return_related_questions=True,
            max_tokens=4000
        )
        # Perplexity returns immediately, create tracking ID
        return generate_operation_id()

async def poll_job(job_id: str, poll_interval: int, max_wait: int, provider: str = "openai") -> Dict:
    """Poll for job completion"""
    start = time.monotonic()
    max_wait_seconds = max_wait * 60
    
    while True:
        elapsed = time.monotonic() - start
        if elapsed > max_wait_seconds:
            raise TimeoutError(f"Operation {job_id} exceeded {max_wait} minute timeout")
        
        if provider == "openai":
            client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            # Use the responses API for deep research
            resp = await client.beta.responses.retrieve(job_id)
            if resp.status in ("completed", "failed"):
                return {"status": resp.status, "content": resp.output}
        else:
            # Perplexity completes synchronously
            return {"status": "completed", "content": "Perplexity results"}
        
        await asyncio.sleep(poll_interval)
```

### 13.3 Dependencies Explained
- **openai**: OpenAI API client for Deep Research
- **httpx**: Async HTTP client with retry support
- **click**: Command-line interface framework
- **rich**: Terminal formatting and progress display
- **questionary**: Interactive prompts for wizard mode
- **tenacity**: Retry logic with exponential backoff
- **platformdirs**: Cross-platform config directory paths
- **pydantic**: Data validation for configs
- **aiofiles**: Async file I/O operations

---

## 14. Configuration Files

All configuration files are stored in `~/.thoth/` directory, which is created automatically on first run.

### 14.1 `~/.thoth/models.toml`

```toml
# Model slot definitions
# Each slot maps to provider + model + options

[thinking]
provider = "openai"
model = "gpt-4o-mini"
options = { temperature = 0.4 }

[deep_research]
# Special slot that supports multiple providers
providers = ["openai", "perplexity"]
parallel = true

[deep_research.openai]
model = "o1-deep-research"
options = { 
    tools = ["web_search", "code_interpreter"],
    reasoning = { summary = "auto" }
}

[deep_research.perplexity]
model = "sonar-pro"
options = { 
    search_domains = ["arxiv.org", "nature.com", "pubmed.ncbi.nlm.nih.gov"],
    search_recency_filter = "month",
    return_citations = true
}

[fast_research]
provider = "openai"
model = "o1-mini"
options = { 
    reasoning = { summary = "auto" },
    max_thinking_tokens = 10000
}
```

### 14.2 `~/.thoth/modes.toml`

```toml
# Research mode definitions
# Each mode has a description, default model slot, and prompt template

[clarification]
description = "Clarify ambiguous queries before deep research"
default_slot = "thinking"
prompt = """
The user's query is: "{query}"

Please identify any ambiguities or unclear aspects of this query and suggest clarifying questions that would help provide a more focused research response.
"""
next = "exploration"

[exploration]
description = "Initial exploration of a topic"
default_slot = "thinking"
prompt = """
Research topic: "{query}"

Provide an initial exploration of this topic including:
1. Overview of the subject
2. Key concepts and terminology
3. Major areas for deeper investigation
4. Suggested research directions
"""
next = "deep_research"

[deep_research]
description = "Comprehensive research with citations"
default_slot = "deep_research"
prompt = """
Conduct comprehensive research on: "{query}"

Requirements:
- Include citations from reputable sources
- Provide multiple perspectives
- Include technical details where relevant
- Organize findings clearly
- Highlight key insights and implications
"""

[competitive_analysis]
description = "Analyze competitive landscape"
default_slot = "deep_research"
prompt = """
Perform competitive analysis for: "{query}"

Include:
- Market overview
- Key players and market share
- Pricing strategies
- Strengths and weaknesses
- Recent developments
- Future trends
"""
```

### 14.3 `~/.thoth/defaults.toml`

```toml
# User preferences and defaults
# Command-line arguments override these values

[general]
default_project = "research_notes"
default_mode = "deep_research"
organization = "project"  # "project" or "date"

[paths]
output_dir = "~/Documents/thoth-research"  # Expands to full path
checkpoint_dir = "~/.thoth/checkpoints"

[execution]
poll_interval = 30        # seconds
max_wait = 30             # minutes
parallel_providers = true
retry_attempts = 3
retry_delay = 2           # seconds (exponential backoff)

[output]
format = "markdown"       # "markdown" or "json"
include_metadata = true
combine_reports = true
timestamp_format = "%Y%m%d_%H%M%S"

[api_keys]
# Store API keys here (optional - env vars take precedence)
# openai_api_key = "sk-..."
# perplexity_api_key = "pplx-..."
```

---

## 15. Implementation Architecture

### 15.1 Core Components

```python
from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict, Literal, Any
from datetime import datetime
from pathlib import Path
import asyncio
import json
from abc import ABC, abstractmethod

@dataclass
class ResearchOperation:
    """Represents a research operation"""
    id: str
    query: str
    mode: str
    status: Literal["queued", "running", "completed", "failed", "cancelled"]
    providers: List[ProviderStatus]
    created_at: datetime
    updated_at: datetime
    checkpoint_data: Dict[str, Any] = field(default_factory=dict)
    output_paths: Dict[str, Path] = field(default_factory=dict)
    error: Optional[str] = None

@dataclass
class ProviderStatus:
    """Status of a single provider within an operation"""
    name: str
    status: Literal["pending", "running", "completed", "failed", "skipped"]
    progress: float = 0.0  # 0.0 to 1.0
    message: str = ""
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

@dataclass
class ResearchResult:
    """Result returned from research execution"""
    operation_id: str
    status: str
    providers: Dict[str, Any]
    output_paths: Optional[Dict[str, Path]] = None
    combined_report_path: Optional[Path] = None

class ThothOrchestrator:
    """Main orchestration engine for multi-provider research"""
    
    def __init__(self, config_dir: Path = None):
        self.config_dir = config_dir or Path(user_config_dir("thoth"))
        self.checkpoint_manager = CheckpointManager(self.config_dir)
        self.output_manager = OutputManager(self.config_dir)
        self.providers = self._initialize_providers()
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create necessary directories"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        (self.config_dir / "checkpoints").mkdir(exist_ok=True)
    
    async def execute_research(
        self,
        query: str,
        mode: str = "deep_research",
        wait: bool = True,
        providers: Optional[List[str]] = None,
        project: Optional[str] = None,
        **options
    ) -> ResearchResult:
        """Execute research with specified parameters"""
        # Load mode configuration
        mode_config = self._load_mode_config(mode)
        
        # Select providers
        selected_providers = providers or self._select_providers_for_mode(mode)
        
        # Create operation
        operation = ResearchOperation(
            id=generate_operation_id(),
            query=query,
            mode=mode,
            status="queued",
            providers=[
                ProviderStatus(name=p, status="pending", message="Waiting to start")
                for p in selected_providers
            ],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            checkpoint_data={"project": project} if project else {}
        )
        
        # Save initial checkpoint
        await self.checkpoint_manager.save_checkpoint(operation)
        
        if wait:
            return await self._execute_sync(operation, mode_config, options)
        else:
            # Submit async and return immediately
            asyncio.create_task(self._execute_async(operation, mode_config, options))
            return ResearchResult(
                operation_id=operation.id,
                status="submitted",
                providers={p.name: "queued" for p in operation.providers}
            )
    
    async def _execute_sync(self, operation: ResearchOperation, mode_config: Dict, options: Dict) -> ResearchResult:
        """Execute research synchronously (wait for completion)"""
        operation.status = "running"
        operation.updated_at = datetime.now()
        
        # Create provider tasks
        tasks = []
        for provider_status in operation.providers:
            provider = self.providers[provider_status.name]
            task = self._run_provider(provider, provider_status, operation, mode_config, options)
            tasks.append(task)
        
        # Run providers (parallel or sequential based on config)
        if mode_config.get("parallel", True) and len(tasks) > 1:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            results = []
            for task in tasks:
                result = await task
                results.append(result)
        
        # Update operation status
        all_completed = all(p.status == "completed" for p in operation.providers)
        any_failed = any(p.status == "failed" for p in operation.providers)
        
        operation.status = "completed" if all_completed else "failed" if any_failed else "partial"
        operation.updated_at = datetime.now()
        
        # Generate combined report if multiple providers succeeded
        if sum(1 for p in operation.providers if p.status == "completed") > 1:
            combined_path = await self._generate_combined_report(operation)
            operation.output_paths["combined"] = combined_path
        
        # Final checkpoint
        await self.checkpoint_manager.save_checkpoint(operation)
        
        return ResearchResult(
            operation_id=operation.id,
            status=operation.status,
            providers={p.name: p.status for p in operation.providers},
            output_paths=operation.output_paths,
            combined_report_path=operation.output_paths.get("combined")
        )

class CheckpointManager:
    """Manages operation persistence and recovery"""
    
    def __init__(self, config_dir: Path):
        self.checkpoint_dir = config_dir / "checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    async def save_checkpoint(self, operation: ResearchOperation) -> None:
        """Save operation state atomically"""
        checkpoint_file = self.checkpoint_dir / f"{operation.id}.json"
        temp_file = checkpoint_file.with_suffix(".tmp")
        
        # Convert to JSON-serializable format
        data = asdict(operation)
        data["created_at"] = operation.created_at.isoformat()
        data["updated_at"] = operation.updated_at.isoformat()
        
        # Convert paths to strings
        if data.get("output_paths"):
            data["output_paths"] = {k: str(v) for k, v in data["output_paths"].items()}
        
        # Atomic write
        with open(temp_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        temp_file.replace(checkpoint_file)
    
    async def restore_operation(self, operation_id: str) -> Optional[ResearchOperation]:
        """Restore operation from checkpoint"""
        checkpoint_file = self.checkpoint_dir / f"{operation_id}.json"
        if not checkpoint_file.exists():
            return None
        
        with open(checkpoint_file) as f:
            data = json.load(f)
        
        # Convert back from JSON
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        
        # Restore paths
        if data.get("output_paths"):
            data["output_paths"] = {k: Path(v) for k, v in data["output_paths"].items()}
        
        # Reconstruct provider status objects
        data["providers"] = [ProviderStatus(**p) for p in data["providers"]]
        
        return ResearchOperation(**data)
    
    async def list_operations(self, status_filter: Optional[List[str]] = None) -> List[ResearchOperation]:
        """List all operations, optionally filtered by status"""
        operations = []
        for checkpoint_file in self.checkpoint_dir.glob("*.json"):
            operation = await self.restore_operation(checkpoint_file.stem)
            if operation and (not status_filter or operation.status in status_filter):
                operations.append(operation)
        
        # Sort by created_at descending
        operations.sort(key=lambda op: op.created_at, reverse=True)
        return operations
```

### 15.2 Provider Implementation

```python
class ResearchProvider(ABC):
    """Abstract base class for research providers"""
    
    @abstractmethod
    async def submit_research(self, query: str, options: Dict[str, Any]) -> str:
        """Submit research and return job ID"""
        pass
    
    @abstractmethod
    async def check_status(self, job_id: str) -> ProviderStatus:
        """Check status of a research job"""
        pass
    
    @abstractmethod
    async def get_result(self, job_id: str) -> Dict[str, Any]:
        """Retrieve completed research result"""
        pass

class OpenAIDeepResearch(ResearchProvider):
    """OpenAI Deep Research implementation"""
    
    def __init__(self, api_key: str, model: str = "o1-deep-research"):
        self.api_key = api_key
        self.model = model
        self.client = None
    
    def _get_client(self) -> AsyncOpenAI:
        """Get or create client instance"""
        if not self.client:
            self.client = AsyncOpenAI(api_key=self.api_key)
        return self.client
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def submit_research(self, query: str, options: Dict[str, Any]) -> str:
        """Submit research to OpenAI Deep Research API"""
        client = self._get_client()
        
        # Prepare the request
        messages = [
            {"role": "system", "content": "You are a deep research assistant. Provide comprehensive, well-cited research."},
            {"role": "user", "content": query}
        ]
        
        # Use the deep research endpoint with background processing
        response = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            **options,
            extra_body={
                "background": True,
                "tools": options.get("tools", ["web_search", "code_interpreter"]),
                "reasoning": options.get("reasoning", {"summary": "auto"})
            }
        )
        
        return response.id
    
    async def check_status(self, job_id: str) -> ProviderStatus:
        """Check status of OpenAI research job"""
        client = self._get_client()
        
        try:
            # Check job status via responses API
            response = await client.beta.responses.retrieve(job_id)
            
            if response.status == "completed":
                return ProviderStatus(
                    name="openai",
                    status="completed",
                    progress=1.0,
                    message="Research completed",
                    result={"content": response.output}
                )
            elif response.status == "failed":
                return ProviderStatus(
                    name="openai",
                    status="failed",
                    progress=0.0,
                    message="Research failed",
                    error=response.error
                )
            else:  # in_progress, queued
                progress = 0.3 if response.status == "queued" else 0.6
                return ProviderStatus(
                    name="openai",
                    status="running",
                    progress=progress,
                    message=f"Status: {response.status}"
                )
        except Exception as e:
            return ProviderStatus(
                name="openai",
                status="failed",
                progress=0.0,
                message="Error checking status",
                error=str(e)
            )

class PerplexityResearch(ResearchProvider):
    """Perplexity research implementation"""
    
    def __init__(self, api_key: str, model: str = "sonar-pro"):
        self.api_key = api_key
        self.model = model
        self.client = None
        self._completed_jobs = {}  # Cache for synchronous results
    
    def _get_client(self) -> AsyncOpenAI:
        """Get or create Perplexity client"""
        if not self.client:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url="https://api.perplexity.ai"
            )
        return self.client
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def submit_research(self, query: str, options: Dict[str, Any]) -> str:
        """Submit research to Perplexity (completes synchronously)"""
        client = self._get_client()
        
        # Perplexity completes immediately
        response = await client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": query}],
            **{k: v for k, v in options.items() if k not in ["tools", "reasoning"]}
        )
        
        # Generate ID and cache result
        job_id = f"pplx-{generate_operation_id()}"
        self._completed_jobs[job_id] = {
            "content": response.choices[0].message.content,
            "citations": getattr(response, "citations", []),
            "usage": response.usage
        }
        
        return job_id
    
    async def check_status(self, job_id: str) -> ProviderStatus:
        """Check status (always completed for Perplexity)"""
        if job_id in self._completed_jobs:
            return ProviderStatus(
                name="perplexity",
                status="completed",
                progress=1.0,
                message="Research completed",
                result=self._completed_jobs[job_id]
            )
        else:
            return ProviderStatus(
                name="perplexity",
                status="failed",
                progress=0.0,
                message="Job not found",
                error="Invalid job ID"
            )
```

### 15.3 Output Management

```python
class OutputManager:
    """Manages research output organization and storage"""
    
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.config = self._load_config()
        self.base_dir = Path(self.config.get("paths", {}).get("output_dir", "./research-outputs")).expanduser()
    
    def _load_config(self) -> Dict:
        """Load defaults.toml configuration"""
        defaults_file = self.config_dir / "defaults.toml"
        if defaults_file.exists():
            import tomllib
            with open(defaults_file, "rb") as f:
                return tomllib.load(f)
        return {}
    
    def get_output_path(
        self,
        operation: ResearchOperation,
        provider: str,
        format: str = "md"
    ) -> Path:
        """Generate output path for a provider's results"""
        organization = self.config.get("general", {}).get("organization", "project")
        timestamp = operation.created_at.strftime(
            self.config.get("output", {}).get("timestamp_format", "%Y%m%d_%H%M%S")
        )
        
        if organization == "project":
            # Project-based organization
            project = operation.checkpoint_data.get("project", "default")
            output_dir = self.base_dir / project / "analysis"
        else:
            # Date-based organization
            date_dir = operation.created_at.strftime("%Y-%m-%d")
            output_dir = self.base_dir / date_dir / f"research-{operation.id[:15]}"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        slug = sanitize_slug(operation.query)
        base_name = f"{timestamp}-{operation.mode}-{provider}-{slug}"
        filename = f"{base_name}.{format}"
        
        # Handle deduplication
        output_path = output_dir / filename
        counter = 1
        while output_path.exists():
            filename = f"{base_name}-{counter}.{format}"
            output_path = output_dir / filename
            counter += 1
        
        return output_path
    
    async def save_result(
        self,
        operation: ResearchOperation,
        provider: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> Path:
        """Save provider result to file"""
        format = self.config.get("output", {}).get("format", "markdown")
        output_path = self.get_output_path(operation, provider, "md" if format == "markdown" else "json")
        
        if format == "markdown":
            # Add metadata header if configured
            if self.config.get("output", {}).get("include_metadata", True):
                header = f"""---
query: {operation.query}
mode: {operation.mode}
provider: {provider}
operation_id: {operation.id}
created_at: {operation.created_at.isoformat()}
---

"""
                content = header + content
        else:
            # JSON format
            output_data = {
                "query": operation.query,
                "mode": operation.mode,
                "provider": provider,
                "operation_id": operation.id,
                "created_at": operation.created_at.isoformat(),
                "content": content,
                "metadata": metadata or {}
            }
            content = json.dumps(output_data, indent=2)
        
        # Write file
        output_path.write_text(content, encoding="utf-8")
        return output_path
    
    async def generate_combined_report(
        self,
        operation: ResearchOperation,
        provider_results: Dict[str, str]
    ) -> Path:
        """Generate combined report from multiple provider results"""
        output_path = self.get_output_path(operation, "combined", "md")
        
        # Build combined report
        report = f"""# Research Report: {operation.query}

**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Operation ID**: {operation.id}  
**Providers**: {', '.join(provider_results.keys())}

---

## Executive Summary

This report combines research findings from multiple AI providers to give a comprehensive overview of the topic.

"""
        
        # Add each provider's results
        for provider, content in provider_results.items():
            report += f"\n## {provider.title()} Research Findings\n\n"
            report += content
            report += "\n\n---\n"
        
        # Write combined report
        output_path.write_text(report, encoding="utf-8")
        return output_path
```

---

## 16. User Experience

### 16.1 Progress Display

```
╭─────────────────────── Research Progress ───────────────────────╮
│ Query: "Impact of quantum computing on cryptography"            │
│ Mode: deep_research | Started: 2024-07-29 14:30:22             │
│ Elapsed: 12:45 | Operation ID: research-20240729-143022-a1b2c3 │
├─────────────────────────────────────────────────────────────────┤
│ ▶ OpenAI Deep Research      [████████░░] 80% - Analyzing        │
│   └─ 15 sources found, deep analysis in progress                │
│ ▶ Perplexity Research       [██████████] 100% - Completed       │
│   └─ Research saved to output file                              │
├─────────────────────────────────────────────────────────────────┤
│ Saving to: ~/Documents/thoth-research/quantum_crypto_2024/      │
│ Last checkpoint: 30 seconds ago | Next poll: 0 seconds         │
╰─────────────────────────────────────────────────────────────────╯

Press Ctrl+C to cancel operation (progress will be saved)
```

### 16.2 Error Handling

```python
class ThothError(Exception):
    """Base exception with user-friendly messages"""
    
    def __init__(self, message: str, suggestion: str = None, exit_code: int = 1):
        self.message = message
        self.suggestion = suggestion
        self.exit_code = exit_code
        super().__init__(message)

class ConfigError(ThothError):
    """Configuration-related errors"""
    def __init__(self, message: str, suggestion: str = None):
        super().__init__(message, suggestion, exit_code=7)

class APIKeyError(ThothError):
    """Missing or invalid API key"""
    def __init__(self, provider: str):
        message = f"{provider} API key not found"
        suggestion = f"Set {provider.upper()}_API_KEY environment variable or run 'thoth init'"
        super().__init__(message, suggestion, exit_code=2)

class ProviderError(ThothError):
    """Provider-related errors"""
    def __init__(self, provider: str, message: str):
        suggestion = f"Check {provider} API status or try again later"
        super().__init__(message, suggestion, exit_code=3)

# Error display with Rich
def display_error(error: ThothError):
    """Display error with formatting"""
    console.print(f"\n[red]✗ Error:[/red] {error.message}")
    if error.suggestion:
        console.print(f"[yellow]→ Suggestion:[/yellow] {error.suggestion}")
    console.print(f"\n[dim]Exit code: {error.exit_code}[/dim]")

# Usage example
try:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise APIKeyError("openai")
except ThothError as e:
    display_error(e)
    sys.exit(e.exit_code)
except Exception as e:
    # Unexpected errors
    console.print(f"\n[red]✗ Unexpected error:[/red] {str(e)}")
    console.print("\n[dim]Please report this issue at: https://github.com/thoth/issues[/dim]")
    sys.exit(127)
```

---

## 17. Error-Handling Strategy

### Comprehensive Error Handling

1. **Validation Errors** (exit 1)
   - Invalid mode or command
   - Conflicting options
   - Missing required arguments
   - User cancellation (Ctrl+C)

2. **API Key Errors** (exit 2)
   - Missing API keys
   - Invalid API key format
   - Expired or revoked keys
   - Clear guidance on resolution

3. **Provider Errors** (exit 3)
   - Unknown provider specified
   - Provider service unavailable
   - Provider-specific errors

4. **Network/API Errors** (exit 4)
   - Connection timeouts
   - DNS resolution failures
   - HTTP 5xx errors after retries
   - Rate limiting (with backoff)

5. **Timeout Errors** (exit 5)
   - Operation exceeds --max-wait
   - Provider unresponsive
   - Checkpoint saved for resume

6. **Not Found Errors** (exit 6)
   - Invalid research ID
   - Completed operation (can't resume)
   - Checkpoint file missing

7. **Config/IO Errors** (exit 7)
   - Permission denied
   - Disk full
   - Invalid TOML syntax
   - Path resolution failures

8. **Unexpected Errors** (exit 127)
   - Programming errors
   - Full stack trace to stderr
   - Request to file bug report

### Error Logging
- All errors logged with timestamps
- API keys automatically masked with `***`
- Sensitive data scrubbed from logs
- Debug mode shows full details

---

## 18. Security and Privacy

### 18.1 API Key Management
- **Environment variables** as primary storage method
- **Config file** option with appropriate warnings
- **Never logged** - automatic masking in all outputs
- **Validation** during setup with clear error messages
- **Keyring support** planned for v0.8

### 18.2 Data Handling
- **Local storage only** - no cloud dependencies
- **User-controlled paths** - full transparency
- **No telemetry** - completely offline operation
- **Checkpoint privacy** - only operational metadata
- **Output security** - follows OS file permissions

### 18.3 Security Best Practices
- **Input sanitization** - safe handling of user queries
- **Path traversal prevention** - restrict to configured directories
- **No shell execution** - all operations use Python APIs
- **Secure temp files** - proper cleanup on exit
- **Rate limiting** - prevent API abuse
- **HTTPS only** - all API communications encrypted

---

## 19. Success Metrics

### 19.1 Performance Targets
- **Startup time**: < 100ms with UV cache
- **First result**: < 30s (Perplexity synchronous)
- **Full completion**: 5-30 minutes typical
- **Checkpoint saves**: < 500ms
- **Memory usage**: < 200MB typical, < 500MB peak
- **CPU usage**: < 10% while polling

### 19.2 Quality Metrics
- **Provider success**: > 95% completion rate
- **Multi-provider**: > 90% both succeed
- **Recovery rate**: > 99% from valid checkpoints
- **Error clarity**: < 5% user confusion
- **Result quality**: Comprehensive, well-cited

### 19.3 User Experience Metrics
- **Setup success**: > 80% complete wizard
- **Command success**: > 95% valid commands work
- **Progress clarity**: 100% show real-time status
- **Documentation**: 100% features documented
- **Time to value**: < 5 minutes from install

---

## 20. Open Issues

| # | Issue | Mitigation | Priority |
|---|-------|------------|----------|
| O-1 | Perplexity async API not available | Simulate async with immediate completion | High |
| O-2 | Rate limits vary by provider/tier | Configurable delays, clear error messages | Medium |
| O-3 | Large outputs (>1MB) slow terminal | Auto-switch to file output, progress indicator | Medium |
| O-4 | Config corruption risk | Validation, auto-backup, regenerate option | Low |
| O-5 | Windows path separators | Use pathlib exclusively, extensive testing | Medium |
| O-6 | API key storage security | Document best practices, keyring in v0.8 | High |
| O-7 | Partial results on failure | Save any completed provider results | Medium |

---

## 21. Future Enhancements

### Version 0.8 (Q1 2025)
- Webhook support for completion notifications
- Keyring integration for secure credential storage
- Anthropic Claude provider support
- Export to HTML with styling
- Basic citation verification

### Version 0.9 (Q2 2025)
- Google Gemini provider integration
- Private data sources (MCP protocol)
- Research templates system
- Cost tracking and reporting
- Streaming progress updates

### Version 1.0 (Q3 2025)
- Full plugin architecture
- Web UI companion app
- Knowledge graph integration
- Multi-language query support
- Research quality scoring
- Collaborative features
- API server mode
- Mobile app support

---

## 22. Appendix: API Response Schemas

### 22.1 OpenAI Deep Research Response

```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "o1-deep-research",
  "status": "completed",
  "usage": {
    "prompt_tokens": 1000,
    "completion_tokens": 5000,
    "total_tokens": 6000,
    "reasoning_tokens": 2000
  },
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "# Comprehensive Research Report\n\n## Executive Summary\n\nBased on analysis of 15 sources...\n\n## Detailed Findings\n\n### 1. Current State\n[Content with [1] citations...]\n\n### 2. Technical Analysis\n[Deep technical content...]\n\n## References\n[1] Source Title - https://example.com\n[2] Another Source - https://example.org"
    },
    "finish_reason": "stop"
  }]
}
```

### 22.2 Perplexity Response

```json
{
  "id": "pplx-response-123",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "sonar-pro",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "Based on my research across academic databases and recent publications:\n\n## Key Findings\n\n1. **Quantum Computing Threats**\n   - Current RSA and ECC encryption vulnerable to Shor's algorithm [1]\n   - Timeline estimates range from 10-20 years [2]\n\n2. **Post-Quantum Cryptography**\n   - NIST standardization completed in 2024 [3]\n   - Lattice-based schemes show promise [4]\n\n[Detailed content continues...]"
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 500,
    "completion_tokens": 1500,
    "total_tokens": 2000
  },
  "citations": [
    {
      "index": 1,
      "url": "https://arxiv.org/abs/2024.12345",
      "title": "Quantum Computing and Cryptographic Security",
      "snippet": "Analysis of quantum threats to current encryption..."
    },
    {
      "index": 2,
      "url": "https://nature.com/articles/quantum-timeline-2024",
      "title": "Realistic Timeline for Cryptographically Relevant Quantum Computers",
      "snippet": "Expert consensus on quantum computing development..."
    }
  ],
  "related_questions": [
    "What are the current NIST post-quantum standards?",
    "How can organizations prepare for quantum threats?",
    "Which industries are most at risk?"
  ]
}
```

---

## End of Thoth v0.7 PRD

This corrected specification resolves all identified inconsistencies, completes missing implementations, and provides a clear, coherent design for the Thoth research automation tool. All conflicts have been resolved, naming has been standardized, and the document now provides complete implementation guidance.