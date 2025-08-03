# Product Requirements Document – Thoth v0.6

---

## 1. Document Control

| Item | Value |
|------|-------|
| Author | System Design Team |
| Date | 29 Jul 2025 |
| Status | Draft |
| Target Release | v0.6 (unified specification) |
| Document Version | 6.0 |

---

## 2. Executive Summary

Thoth v0.6 is a command-line interface (CLI) tool that automates deep technical research using multiple LLM providers. It orchestrates parallel execution of OpenAI's Deep Research API and Perplexity's research models to deliver comprehensive, multi-perspective research reports. Built as a single-file Python tool with UV script dependencies for zero-configuration deployment, Thoth provides both synchronous and asynchronous operation modes, intelligent provider selection, and robust handling of long-running operations (5-30+ minutes).

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
- Persistent defaults stored in `~/.thoth/defaults.toml`
- Comprehensive command-line interface with extensive options

---

## 4. Glossary

| Term | Definition |
|------|------------|
| Mode | Workflow phase (clarification, exploration, deep_research, thinking) with its own prompt template |
| Model slot | Alias that maps to {provider, model, options} |
| Provider | LLM backend (openai, perplexity) |
| Research ID | Unique identifier returned when a Deep Research job starts |
| Operation ID | Alternative term for Research ID used in status commands |
| Background mode | Asynchronous execution in Deep Research (background=True) |
| Polling | Repeated status checks until a job completes or times out |
| Structured output | Files saved in `deep_research/<project>/` with deterministic names |
| Defaults file | `~/.thoth/defaults.toml`; user-set system-wide defaults |
| Checkpoint | Saved state of an in-progress research operation |

---

## 5. Objectives

1. **One-command research** with sensible defaults
2. **Async robustness** – never hang; offer `--async`, `--resume`, listing, and configurable polling
3. **Deterministic, auditable artifacts** for repeatability
4. **Zero system friction** via UV inline dependencies
5. **Config-over-code** – modes, model-slots, and defaults overridable in user TOML
6. **Multi-provider orchestration** – leverage multiple LLMs in parallel by default
7. **Graceful long operation handling** – support for 5-30+ minute research tasks
8. **Universal compatibility** – run on macOS, Linux, and Windows

---

## 6. Out of Scope (v0.6)

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

- Python ≥ 3.11 and Astral UV installed
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
| F-01 | Built-in modes hard-coded; merge user file `~/.thoth/modes.toml` | Must |
| F-02 | Built-in model-slots hard-coded; merge `~/.thoth/models.toml` | Must |
| F-03 | Built-in defaults file `~/.thoth/defaults.toml` overrides code when present | Must |
| F-04 | Any CLI value may reference an external file with `@/path` or stdin with `@-` | Must |
| F-05 | Create jobs in background; capture research_id/operation_id | Must |
| F-06 | Poll job status every n seconds (`--poll-interval`); default 30s | Must |
| F-07 | Abort after x minutes (`--max-wait`); default 30 min | Must |
| F-08 | `--async` submits the job, prints research_id, and exits 0 | Must |
| F-09 | `--research-id` (alias `--resume`/`-R`) resumes an existing job | Must |
| F-10 | `--list-research` (alias `-L`) lists queued/in-progress jobs | Should |
| F-11 | Dual-provider run for model-slot `deep_research` unless `--provider` given | Must |
| F-12 | Structured output filenames: `YYYYMMDD_HHMM-<mode>-<provider>-<slug>.{md,json}` | Must |
| F-13 | Slug deduplication by suffix (-1, -2, …) | Should |
| F-14 | Config directory (`~/.thoth`) auto-created on first run | Should |
| F-15 | Interactive wizard: plain-text prompts; escape with Ctrl-C | Must |
| F-16 | All diagnostics to stderr; DEBUG enabled with `--verbose` or `THOTH_DEBUG=1` | Must |
| F-17 | Persistent default project: `--set-default-project` writes to defaults file | Must |
| F-18 | Command-line overrides beat defaults file; defaults beat code | Must |
| F-19 | Retry transient network/5xx errors up to 3 times with exponential back-off | Should |
| F-20 | Safety: mask API keys in logs and exceptions | Must |
| F-21 | Support `status` command to check operation status | Must |
| F-22 | Checkpoint operations every 2 minutes for recovery | Should |
| F-23 | Project-based and ad-hoc output organization modes | Must |
| F-24 | Combined report generation from multi-provider results | Should |

---

## 9. Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| N-01 | Poll requests ≤2 per minute by default |
| N-02 | Tool runs on macOS, Linux, Windows |
| N-03 | Only libraries declared in inline metadata are imported |
| N-04 | Graceful exit on interrupt or validation errors |
| N-05 | Startup time < 100ms for cached dependencies |
| N-06 | Time to first result < 30 seconds (Perplexity quick results) |
| N-07 | Checkpoint save time < 500ms |
| N-08 | Provider success rate > 95% for each provider |
| N-09 | Recovery success > 99% from checkpoints |

---

## 10. Command-Line Interface

### 10.1 Invocation Patterns

```bash
thoth <mode> "Query..." [OPTIONS]             # one-shot (sync)
thoth -A <mode> -q "Query..."                 # async submit & exit
thoth -R <ID> [OPTIONS]                       # resume job
thoth -L                                      # list jobs
thoth status <ID>                             # check operation status
thoth interactive                             # wizard
thoth init                                    # setup wizard
```

### 10.2 Options Matrix

| Long | Short | Value | Description |
|------|-------|-------|-------------|
| --mode | -m | NAME | Workflow mode (optional if first arg is mode) |
| --query | -q | TEXT/@file/@- | Research prompt |
| --structured | -s | flag | Enable file output |
| --project | -p | NAME | Project folder; spaces→underscore |
| --set-default-project | -S | NAME | Persist as default in defaults.toml |
| --output-dir | -o | PATH | Root directory for structured output |
| --model-slot | -M | SLOT | Override mode's slot |
| --provider | -P | NAME | openai / perplexity (single provider mode) |
| --api-key | -k | KEY | Override provider key |
| --raw | -r | flag | Save raw JSON or print if not structured |
| --fast | -f | flag | Use faster mini deep-research model |
| --no-code | | flag | Disable code interpreter tool |
| --poll-interval | -I | SECS | Seconds between status checks (default 30) |
| --max-wait | -W | MINS | Max minutes to wait (default 30) |
| --async | -A | flag | Fire-and-forget submit (alias: --no-wait) |
| --research-id / --resume | -R | ID | Resume existing research ID |
| --list-research | -L | flag | List queued/in-progress jobs |
| --verbose | -v | flag | DEBUG log level |
| --quiet | | flag | Suppress spinner/progress messages |
| --interactive | -i | flag | Launch wizard |
| --version | -V | flag | Print version |
| --help | -h | flag | Help |
| --parallel | | flag | Force parallel provider execution |
| --organization | | MODE | Output organization: project/adhoc |

### 10.3 Mutual Exclusivity Rules
- `-A` (async) cannot be combined with `-R` or `-L`
- `-L` ignores all other flags except verbosity
- When `--structured` is used without `--project` and a default project exists, the default is applied; else validation error
- `--provider` disables parallel multi-provider execution
- `--no-wait` is an alias for `--async`

---

## 11. Interactive Modes

### 11.1 Setup Wizard (`thoth init`)

```bash
$ thoth init
Welcome to Thoth Research Assistant Setup!

? Select LLM providers: (Use arrow keys to move, space to select)
 ◉ OpenAI Deep Research
 ◉ Perplexity
 ○ Anthropic Claude (future)
 
? How should Thoth organize outputs?
 ❯ Project-based (recommended for ongoing research)
   Date-based (simple chronological organization)
   
? Default operation mode:
 ❯ Interactive (wait for results)
   Background (submit and exit)

? Default polling interval (seconds): 30
? Maximum wait time (minutes): 30

Configuration saved to ~/.thoth/config.toml
```

### 11.2 Interactive Research Wizard (`thoth interactive`)

```
Step 1: Select Mode
  → deep_research (default)
  → thinking
  → clarification
  → exploration

Step 2: Enter Research Query
  → Multi-line input supported (Ctrl+D to finish)

Step 3: Enable Structured Output?
  → Yes/No (default: Yes)

Step 4: Project Name
  → Prefilled with default if exists
  → Spaces converted to underscores

Step 5: Provider Selection (if deep_research)
  → Both (parallel execution)
  → OpenAI only
  → Perplexity only

Step 6: Advanced Options
  → Async mode (y/n)
  → Custom polling interval
  → Raw output
  → Fast mode

Confirmation Screen:
  → Display all selections
  → Confirm or restart
```

---

## 12. Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Validation error or user abort |
| 2 | Missing API key |
| 3 | Unsupported provider |
| 4 | API/network failure after retries |
| 5 | Max-wait timeout |
| 6 | Research ID not found |
| 7 | Config/IO error (e.g., cannot write file) |
| 127 | Uncaught exception |

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
#   "typer>=0.12",
#   "click>=8.0",
#   "rich>=13.7",
#   "questionary>=2.0",
#   "tenacity>=8.0",
#   "platformdirs>=3.0",
#   'tomli>=2.0; python_version<"3.11"'
# ]
# ///
```

### 13.2 Async Workflow Implementation

```python
async def submit_job(query, model, tools, provider="openai"):
    if provider == "openai":
        resp = await openai_client.responses.create(
            model=model,
            input=[
                {"role": "developer", "content": [{"type": "input_text", "text": system_prompt}]},
                {"role": "user", "content": [{"type": "input_text", "text": query}]}
            ],
            background=True,
            reasoning={"summary": "auto"},
            tools=tools
        )
    else:  # perplexity
        resp = await perplexity_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": query}],
            search_domain_filter=["arxiv.org", "nature.com"],
            search_recency_filter="month",
            return_related_questions=True,
            max_tokens=4000
        )
    return resp.id if hasattr(resp, 'id') else generate_operation_id()

async def poll_job(job_id, poll_int, max_wait, provider="openai"):
    start = time.monotonic()
    while True:
        if provider == "openai":
            resp = await openai_client.responses.retrieve(job_id)
            if resp.status in ("completed", "failed"):
                return resp
        else:
            # Perplexity polling logic
            pass
        
        if time.monotonic() - start > max_wait:
            raise TimeoutError(f"Operation {job_id} exceeded max wait time")
        
        await asyncio.sleep(poll_int)
```

### 13.3 Dependencies
- **openai** – Deep Research & Responses API
- **httpx** – HTTP client with retry/back-off support
- **typer** – Modern CLI framework
- **click** – Additional CLI utilities
- **rich** – Progress bars, tables, formatted output
- **questionary** – Interactive prompts for wizard
- **tenacity** – Retry logic with exponential backoff
- **platformdirs** – Cross-platform config directory support
- **tomli/tomllib** – TOML parsing (built-in for Python 3.11+)
- **Standard library**: asyncio, argparse (fallback), logging, pathlib, textwrap, json, time, re, dataclasses

---

## 14. Configuration Files

### 14.1 `~/.thoth/models.toml`

```toml
[thinking]
provider = "openai"
model = "gpt-4o-mini"
options = { temperature = 0.4 }

[deep_research]
providers = ["openai", "perplexity"]
parallel = true

[deep_research.openai]
model = "o3-deep-research-2025-06-26"
options = { reasoning = { summary = "auto" } }

[deep_research.perplexity]
model = "sonar-pro"
options = { search_domains = ["arxiv.org", "nature.com"] }

[fast_research]
provider = "openai"
model = "o4-mini-deep-research"
options = { reasoning = { summary = "auto" } }
```

### 14.2 `~/.thoth/modes.toml`

```toml
[clarification]
description = "Clarify ambiguous queries"
default_slot = "thinking"
prompt = """
The user asks: «{query}»
Identify ambiguities and suggest clarifications.
"""
next = "exploration"

[exploration]
description = "Initial exploration of topic"
default_slot = "thinking"
prompt = """
Explore the topic: «{query}»
Provide an overview and identify key areas for deep research.
"""
next = "deep_research"

[deep_research]
description = "Comprehensive research with citations"
default_slot = "deep_research"
prompt = """
Conduct deep research on: «{query}»
Include citations, multiple perspectives, and technical details.
"""

[competitive_analysis]
description = "Competitive landscape research"
default_slot = "deep_research"
prompt = """
Analyse «{query}» with respect to market share, pricing, and strategy.
Include competitor comparisons and market trends.
"""
next = "solution"
```

### 14.3 `~/.thoth/defaults.toml`

```toml
[general]
default_project = "research_notes"
default_mode = "deep_research"
output_dir = "~/research"
organization = "project"  # "project" or "adhoc"

[execution]
poll_interval = 30        # seconds
max_wait = 30             # minutes
parallel_providers = true
checkpoint_interval = 120 # seconds

[output]
format = "markdown"       # "markdown" or "json"
include_metadata = true
combine_reports = true
```

---

## 15. Implementation Architecture

### 15.1 Core Components

```python
from dataclasses import dataclass
from typing import List, Optional, Dict, Literal
import asyncio
from abc import ABC, abstractmethod

@dataclass
class ResearchOperation:
    id: str
    query: str
    mode: str
    status: Literal["queued", "running", "completed", "failed"]
    providers: List["ProviderStatus"]
    created_at: datetime
    checkpoint_data: Optional[Dict]
    output_path: Optional[Path]

@dataclass
class ProviderStatus:
    name: str
    status: Literal["pending", "running", "completed", "failed"]
    progress: float  # 0.0 to 1.0
    message: str
    result: Optional[Any]

class ThothOrchestrator:
    """Main orchestration engine for multi-provider research"""
    
    def __init__(self, config_dir: Path = None):
        self.config_dir = config_dir or Path.home() / ".thoth"
        self.checkpoint_manager = CheckpointManager(self.config_dir)
        self.providers = self._initialize_providers()
    
    async def execute_research(
        self,
        query: str,
        mode: str = "deep_research",
        wait: bool = True,
        providers: Optional[List[str]] = None
    ) -> ResearchResult:
        # Provider selection based on mode and override
        selected_providers = providers or self._select_providers(mode)
        
        # Create research operation
        operation = ResearchOperation(
            id=self._generate_operation_id(),
            query=query,
            mode=mode,
            status="queued",
            providers=[
                ProviderStatus(name=p, status="pending", progress=0.0, message="Queued")
                for p in selected_providers
            ],
            created_at=datetime.now(),
            checkpoint_data=None,
            output_path=None
        )
        
        # Execute based on wait mode
        if wait:
            return await self._execute_sync(operation)
        else:
            await self._submit_async(operation)
            return ResearchResult(operation_id=operation.id, status="submitted")

class CheckpointManager:
    """Handles operation persistence and recovery"""
    
    def __init__(self, config_dir: Path):
        self.checkpoint_dir = config_dir / "checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    async def save_checkpoint(self, operation: ResearchOperation) -> None:
        checkpoint_file = self.checkpoint_dir / f"{operation.id}.json"
        temp_file = checkpoint_file.with_suffix(".tmp")
        
        # Atomic write
        with open(temp_file, 'w') as f:
            json.dump(asdict(operation), f, default=str)
        temp_file.replace(checkpoint_file)
    
    async def restore_operation(self, operation_id: str) -> Optional[ResearchOperation]:
        checkpoint_file = self.checkpoint_dir / f"{operation_id}.json"
        if not checkpoint_file.exists():
            return None
        
        with open(checkpoint_file) as f:
            data = json.load(f)
        return ResearchOperation(**data)
```

### 15.2 Provider Abstraction

```python
class ResearchProvider(ABC):
    """Abstract base class for research providers"""
    
    @abstractmethod
    async def submit_research(self, query: str, options: Dict) -> str:
        """Submit research and return operation/job ID"""
        pass
    
    @abstractmethod
    async def check_status(self, job_id: str) -> ProviderStatus:
        """Check status of a research job"""
        pass
    
    @abstractmethod
    async def get_result(self, job_id: str) -> Dict:
        """Retrieve completed research result"""
        pass

class OpenAIDeepResearch(ResearchProvider):
    """OpenAI Deep Research implementation"""
    
    def __init__(self, api_key: str, model: str = "o3-deep-research-2025-06-26"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
    
    async def submit_research(self, query: str, options: Dict) -> str:
        response = await self.client.responses.create(
            model=self.model,
            input=[
                {"role": "developer", "content": [{"type": "input_text", "text": "You are a research assistant."}]},
                {"role": "user", "content": [{"type": "input_text", "text": query}]}
            ],
            background=True,
            **options
        )
        return response.id

class PerplexityResearch(ResearchProvider):
    """Perplexity research implementation"""
    
    def __init__(self, api_key: str, model: str = "sonar-pro"):
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.perplexity.ai"
        )
        self.model = model
```

### 15.3 Output Management

```python
class OutputManager:
    """Manages research output organization and storage"""
    
    def __init__(self, base_dir: Path, organization: str = "project"):
        self.base_dir = base_dir
        self.organization = organization
    
    def get_output_path(
        self,
        operation: ResearchOperation,
        provider: str,
        format: str = "md"
    ) -> Path:
        timestamp = operation.created_at.strftime("%Y%m%d_%H%M")
        
        if self.organization == "project":
            # Project-based organization
            project_name = operation.checkpoint_data.get("project", "default")
            output_dir = self.base_dir / project_name / "analysis"
        else:
            # Ad-hoc date-based organization
            date_dir = operation.created_at.strftime("%Y-%m-%d")
            output_dir = self.base_dir / date_dir / f"research-{timestamp}-{operation.id[:8]}"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename with deduplication
        base_name = f"{timestamp}-{operation.mode}-{provider}"
        filename = f"{base_name}.{format}"
        
        # Handle deduplication
        counter = 1
        while (output_dir / filename).exists():
            filename = f"{base_name}-{counter}.{format}"
            counter += 1
        
        return output_dir / filename
```

---

## 16. User Experience

### 16.1 Progress Display

```
╭─────────────────────── Research Progress ───────────────────────╮
│ Query: "Impact of quantum computing on cryptography"            │
│ Mode: deep_research | Started: 2024-01-15 14:30:22             │
│ Elapsed: 12:45 | Operation ID: research-20240115-143022-a1b2c3 │
├─────────────────────────────────────────────────────────────────┤
│ ▶ OpenAI Deep Research      [████████░░] 80% - Analyzing        │
│   └─ 15 sources found, deep analysis in progress                │
│ ▶ Perplexity Research       [██████░░░░] 60% - Gathering        │
│   └─ Searching academic databases...                            │
├─────────────────────────────────────────────────────────────────┤
│ Last checkpoint: 2 minutes ago | Next poll: 18 seconds         │
╰─────────────────────────────────────────────────────────────────╯
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
    exit_code = 7

class APIKeyError(ThothError):
    """Missing or invalid API key"""
    exit_code = 2

# Usage with rich formatting
try:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise APIKeyError(
            "OpenAI API key not found",
            "Set OPENAI_API_KEY environment variable or run 'thoth init'"
        )
except ThothError as e:
    console.print(f"[red]Error:[/red] {e.message}")
    if e.suggestion:
        console.print(f"[yellow]Suggestion:[/yellow] {e.suggestion}")
    sys.exit(e.exit_code)
```

---

## 17. Error-Handling Strategy

- **Validation errors** (exit 1): Unknown mode/flag combos, mutually exclusive violations
- **API key errors** (exit 2): Missing or invalid API keys with clear guidance
- **Provider errors** (exit 3): Unsupported provider specified
- **Network/API errors** (exit 4): Retry 3x with exponential backoff; log and abort if persistent
- **Timeout errors** (exit 5): Job exceeds `--max-wait` threshold
- **Not found errors** (exit 6): Research ID doesn't exist or already completed
- **Config/IO errors** (exit 7): Cannot read/write config or output files
- **Unexpected errors** (exit 127): Caught at top level with full traceback to stderr

All errors logged via `logging` module with API keys automatically scrubbed from output.

---

## 18. Security and Privacy

### 18.1 API Key Management
- Never store API keys in plain text files
- Use environment variables as primary method
- Support secure credential stores (keyring) in future versions
- Validate API keys during setup wizard
- Automatic key masking in all logs and error messages

### 18.2 Data Handling
- All data stored locally (no cloud dependency)
- Optional encryption for sensitive research (future)
- Clear data retention policies in documentation
- No telemetry or usage tracking
- Checkpoint files include only operational metadata

### 18.3 Security Best Practices
- Input sanitization for file paths and queries
- No shell command execution from user input
- Secure handling of temporary files
- Rate limiting to prevent API abuse

---

## 19. Success Metrics

### 19.1 Performance Targets
- **Startup time**: < 100ms for cached dependencies
- **Time to first result**: < 30 seconds (Perplexity quick results)
- **Full research completion**: 5-30 minutes depending on depth
- **Checkpoint save time**: < 500ms
- **Memory usage**: < 200MB for typical operations

### 19.2 Quality Metrics
- **Provider success rate**: > 95% for each provider
- **Result completeness**: Both providers return results in > 90% of runs
- **Recovery success**: > 99% successful resume from checkpoints
- **Error clarity**: < 5% support requests for common errors

### 19.3 User Experience Metrics
- **Setup completion rate**: > 80% complete initial wizard
- **Command success rate**: > 95% valid commands execute successfully
- **Progress visibility**: 100% operations show real-time progress
- **Documentation coverage**: 100% of features documented with examples

---

## 20. Open Issues

| # | Issue | Mitigation |
|---|-------|------------|
| O-1 | Perplexity async semantics not finalized | Behind experimental flag until stable |
| O-2 | Rate-limit tuning for high concurrency | Allow user to increase poll interval |
| O-3 | Large outputs overwhelm terminal | Auto-enable structured output when > 20k tokens |
| O-4 | Defaults file corruption risk | Validate on load; backup & regenerate if corrupt |
| O-5 | Windows path handling inconsistencies | Use pathlib exclusively; test on all platforms |
| O-6 | Credential storage security | Document secure practices; keyring support planned |

---

## 21. Future Enhancements

### Version 0.7-0.9
- Webhook callbacks for completion notifications
- `--resume` with automatic file write upon completion
- Private data integration via MCP protocol
- Citation verification and deduplication
- Token usage and cost summary reporting
- Export to HTML/PDF with formatting
- Anthropic Claude integration
- Google Gemini support

### Version 1.0 Vision
- Full research pipeline automation
- Integration with knowledge management systems
- Advanced caching and result deduplication
- Research quality scoring and confidence metrics
- Multi-language support for queries and outputs
- Plugin system for custom providers
- Web UI for result visualization and management
- Real-time collaboration features
- Research templates and workflows

---

## 22. Appendix: API Response Schemas

### 22.1 OpenAI Deep Research Response

```json
{
  "id": "resp_abc123",
  "object": "realtime.response",
  "status": "completed",
  "status_details": null,
  "created_at": 1234567890,
  "updated_at": 1234567900,
  "usage": {
    "input_tokens": 1000,
    "output_tokens": 5000,
    "input_token_details": {
      "reasoning": 200
    },
    "output_token_details": {
      "reasoning": 1000
    }
  },
  "output": [{
    "type": "message",
    "content": [{
      "type": "output_text",
      "text": "# Research Report\n\n## Executive Summary\n\nDetailed research findings with citations [1] and analysis...",
      "annotations": [{
        "type": "citation",
        "text": "[1]",
        "url": "https://example.com/source",
        "title": "Source Title"
      }]
    }]
  }]
}
```

### 22.2 Perplexity Response

```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "sonar-pro",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "Based on my research [1][2], here are the key findings..."
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
      "url": "https://arxiv.org/abs/1234.5678",
      "title": "Quantum Computing and Post-Quantum Cryptography"
    },
    {
      "url": "https://nature.com/articles/s41586-023-1234",
      "title": "Recent Advances in Quantum Computing"
    }
  ],
  "related_questions": [
    "What are the current limitations of quantum computers?",
    "Which cryptographic algorithms are quantum-resistant?"
  ]
}
```

---

## End of Thoth v0.6 PRD

This unified specification combines the comprehensive features from both v0.5 PRDs, resolving naming conflicts and preserving all functionality. The document maintains the detailed command-line specifications from the ChatGPT version while incorporating the rich architectural details and implementation examples from the Claude version.