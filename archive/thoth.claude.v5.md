# Product Requirements Document: Thoth v0.5

## Executive Summary

Thoth v0.5 is a command-line interface (CLI) tool that automates deep technical research using multiple LLM providers. It orchestrates parallel execution of OpenAI's Deep Research API and Perplexity's research models to deliver comprehensive, multi-perspective research reports. Built with UV script dependencies for zero-configuration deployment, Thoth provides both synchronous and asynchronous operation modes, intelligent provider selection, and robust handling of long-running operations (5-30+ minutes).

## Product Overview

### Vision
Create the most efficient CLI tool for automated research that leverages the complementary strengths of multiple LLM providers to deliver superior research outcomes.

### Core Value Propositions
- **Multi-provider intelligence**: Parallel execution of OpenAI and Perplexity for comprehensive results
- **Zero-configuration deployment**: UV inline script dependencies eliminate setup complexity
- **Flexible operation modes**: Support both interactive (wait) and background (submit and exit) workflows
- **Production-ready reliability**: Checkpoint/resume, graceful error handling, and operation persistence

### Target Users
- Researchers requiring deep technical analysis
- Developers needing comprehensive API documentation research
- Analysts conducting multi-source investigations
- Teams automating research workflows

## Core Features and Requirements

### 1. Multi-Provider Orchestration

**Requirement**: Execute research tasks using both OpenAI Deep Research and Perplexity APIs in parallel by default.

**Implementation Details**:
- **Default behavior**: Run both providers for `deep_research` tasks
- **OpenAI-only mode**: Use exclusively for quick "thinking" tasks
- **Provider selection**: Task-based automatic selection with manual override capability
- **Parallel execution**: AsyncIO-based concurrent API calls with semaphore control

**Configuration**:
```toml
[modes.deep_research]
providers = ["openai", "perplexity"]
parallel = true
timeout_minutes = 30

[modes.thinking]
providers = ["openai"]
parallel = false
timeout_minutes = 5
```

### 2. Operation Modes

**Synchronous Mode (Default)**:
- Block and display real-time progress
- Show provider status for each operation
- Stream results as they become available
- Exit only when all operations complete

**Asynchronous Mode**:
- Submit research request and return immediately
- Return operation ID for status tracking
- Support resumption and result retrieval
- Enable fire-and-forget workflows

**CLI Interface**:
```bash
# Synchronous (default)
thoth research "impact of quantum computing on cryptography"

# Asynchronous
thoth research "impact of quantum computing on cryptography" --no-wait
# Returns: research-20240115-143022-a1b2c3d4

# Status checking
thoth status research-20240115-143022-a1b2c3d4
thoth logs research-20240115-143022-a1b2c3d4 --follow
```

### 3. Output Organization

**Project-Based Mode**:
```
research-outputs/
├── quantum-cryptography-2024/
│   ├── metadata.yaml
│   ├── sources/
│   ├── analysis/
│   │   ├── openai-deep-research.md
│   │   └── perplexity-research.md
│   ├── combined-report.md
│   └── artifacts/
```

**Ad-Hoc Mode**:
```
thoth-outputs/
├── 2024-01-15/
│   └── research-143022-quantum-crypto/
│       ├── openai-result.md
│       ├── perplexity-result.md
│       └── metadata.json
```

**Deterministic Naming**: `YYYY-MM-DD_HHMMSS_<operation>_<hash>`

### 4. Long Operation Handling

**Progress Display**:
```
Research: Quantum Computing Impact [25%] ━━━━━━━━━░░░░░░░░░░░░░░░░░░ 8/30 min
├─ OpenAI Deep Research    [████████░░] 80% - Analyzing sources
├─ Perplexity Research     [██████░░░░] 60% - Gathering papers
└─ Status: 15 sources found, 8 analyzed
```

**Resilience Features**:
- Automatic checkpointing every 2 minutes
- Network interruption recovery
- System sleep/hibernation handling
- Partial result preservation

## Technical Specifications

### 1. OpenAI Deep Research Integration

**API Configuration**:
```python
# Async request submission
response = client.responses.create(
    model="o3-deep-research-2025-06-26",
    input=[
        {"role": "developer", "content": [{"type": "input_text", "text": system_message}]},
        {"role": "user", "content": [{"type": "input_text", "text": query}]}
    ],
    background=True,  # Required for async mode
    reasoning={"summary": "auto"},
    tools=[
        {"type": "web_search_preview"},
        {"type": "code_interpreter"}
    ]
)

# Polling pattern
while response.status in {"queued", "in_progress"}:
    await asyncio.sleep(min(wait_time * 1.2, 30))
    response = client.responses.retrieve(response.id)
```

**Cost Management**:
- Model: o3-deep-research ($10/1M input, $40/1M output tokens)
- Alternative: o4-mini-deep-research ($2/1M input, $8/1M output tokens)
- Automatic model selection based on query complexity

### 2. Perplexity API Integration

**Configuration**:
```python
perplexity_client = AsyncOpenAI(
    api_key=PERPLEXITY_API_KEY,
    base_url="https://api.perplexity.ai"
)

response = await perplexity_client.chat.completions.create(
    model="sonar-pro",  # For deep research
    messages=[{"role": "user", "content": query}],
    search_domain_filter=["arxiv.org", "nature.com"],
    search_recency_filter="month",
    return_related_questions=True,
    max_tokens=4000
)
```

**Model Selection**:
- `sonar-pro`: Complex research queries
- `sonar`: Cost-effective standard research
- `sonar-deep-research`: Exhaustive research reports

### 3. UV Script Dependencies

**Script Header**:
```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "click>=8.0",
#     "rich>=13.0",
#     "httpx>=0.24.0",
#     "openai>=1.0",
#     "tomli>=2.0; python_version < '3.11'",
#     "questionary>=2.0",
#     "tenacity>=8.0",
#     "platformdirs>=3.0",
# ]
# ///
```

### 4. Configuration Management

**TOML Configuration Structure**:
```toml
[thoth]
version = "0.2.0"
default_mode = "deep_research"

[providers.openai]
api_key_env = "OPENAI_API_KEY"
model = "o3-deep-research-2025-06-26"
max_concurrent = 1
timeout_minutes = 30

[providers.perplexity]
api_key_env = "PERPLEXITY_API_KEY"
model = "sonar-pro"
max_concurrent = 3
timeout_minutes = 10

[output]
base_directory = "./research-outputs"
organization = "project"  # "project" or "adhoc"
format = "markdown"
include_metadata = true

[execution]
max_parallel_providers = 2
checkpoint_interval_seconds = 120
retry_attempts = 3
```

## Implementation Architecture

### Core Components

```python
class ThothOrchestrator:
    """Main orchestration engine for multi-provider research"""
    
    async def execute_research(
        self,
        query: str,
        mode: str = "deep_research",
        wait: bool = True
    ) -> ResearchResult:
        # Provider selection based on mode
        providers = self._select_providers(mode)
        
        # Create research tasks
        tasks = [
            self._create_provider_task(provider, query)
            for provider in providers
        ]
        
        # Execute with progress tracking
        if wait:
            return await self._execute_sync(tasks)
        else:
            operation_id = self._submit_async(tasks)
            return ResearchResult(operation_id=operation_id)
```

### State Management

```python
@dataclass
class ResearchOperation:
    id: str
    query: str
    status: Literal["queued", "running", "completed", "failed"]
    providers: List[ProviderStatus]
    created_at: datetime
    checkpoint_data: Optional[Dict]
    
class CheckpointManager:
    """Handles operation persistence and recovery"""
    
    async def save_checkpoint(
        self,
        operation: ResearchOperation
    ) -> None:
        # Atomic save with metadata
        pass
    
    async def restore_operation(
        self,
        operation_id: str
    ) -> Optional[ResearchOperation]:
        # Restore from checkpoint
        pass
```

### CLI Interface

```python
import click
from rich.console import Console
from rich.progress import Progress

@click.group()
def cli():
    """Thoth - AI-Powered Deep Research Automation"""
    pass

@cli.command()
@click.argument('query')
@click.option('--mode', default='deep_research', 
              type=click.Choice(['deep_research', 'thinking']))
@click.option('--wait/--no-wait', default=True,
              help='Wait for completion or run in background')
@click.option('--output-dir', type=click.Path(),
              help='Output directory (default: auto-generated)')
def research(query: str, mode: str, wait: bool, output_dir: Optional[str]):
    """Execute research with the specified query"""
    orchestrator = ThothOrchestrator()
    
    if wait:
        with Progress() as progress:
            result = asyncio.run(
                orchestrator.execute_research(query, mode, wait=True)
            )
            console.print(f"[green]Research complete![/green]")
            console.print(f"Results saved to: {result.output_path}")
    else:
        result = asyncio.run(
            orchestrator.execute_research(query, mode, wait=False)
        )
        console.print(f"Research submitted: {result.operation_id}")
        console.print("Check status with: thoth status {result.operation_id}")
```

## User Experience

### Interactive Setup Wizard

```bash
$ thoth init
Welcome to Thoth Research Assistant Setup!

? Select LLM providers: (Use arrow keys to move, space to select)
 ◉ OpenAI Deep Research
 ◉ Perplexity
 ○ Anthropic Claude
 
? How should Thoth organize outputs?
 ❯ Project-based (recommended for ongoing research)
   Date-based (simple chronological organization)
   
? Default operation mode:
 ❯ Interactive (wait for results)
   Background (submit and exit)

Configuration saved to ~/.thoth/config.toml
```

### Progress Indicators

**Multi-Provider Progress**:
```
╭─────────────────────── Research Progress ───────────────────────╮
│ Query: "Impact of quantum computing on cryptography"            │
│ Started: 2024-01-15 14:30:22 | Elapsed: 12:45                  │
├─────────────────────────────────────────────────────────────────┤
│ ▶ OpenAI Deep Research      [████████░░] 80% - Analyzing        │
│   └─ 15 sources found, deep analysis in progress                │
│ ▶ Perplexity Research       [██████░░░░] 60% - Gathering        │
│   └─ Searching academic databases...                            │
╰─────────────────────────────────────────────────────────────────╯
```

### Error Handling

```python
class ThothError(Exception):
    """Base exception with user-friendly messages"""
    
    def __init__(self, message: str, suggestion: str = None):
        self.message = message
        self.suggestion = suggestion
        super().__init__(message)

# Usage
if not api_key:
    raise ThothError(
        "OpenAI API key not found",
        "Set OPENAI_API_KEY environment variable or run 'thoth config'"
    )
```

## Success Metrics

### Performance Targets
- **Startup time**: < 100ms for cached dependencies
- **Time to first result**: < 30 seconds (Perplexity quick results)
- **Full research completion**: 5-30 minutes depending on depth
- **Checkpoint save time**: < 500ms

### Quality Metrics
- **Provider success rate**: > 95% for each provider
- **Result completeness**: Both providers return results in > 90% of runs
- **Recovery success**: > 99% successful resume from checkpoints

### User Experience Metrics
- **Setup completion rate**: > 80% complete initial wizard
- **Error message clarity**: < 5% support requests for common errors
- **Progress visibility**: 100% operations show real-time progress

## Security and Privacy

### API Key Management
- Never store API keys in plain text
- Use environment variables or secure credential stores
- Validate API keys during setup wizard

### Data Handling
- Local storage only (no cloud dependency)
- Optional encryption for sensitive research
- Clear data retention policies

## Future Enhancements

### Version 0.3 Considerations
- Additional provider support (Anthropic, Google)
- Web UI for result visualization
- Collaborative research features
- Custom provider plugins

### Version 1.0 Vision
- Full research pipeline automation
- Integration with knowledge management systems
- Advanced caching and deduplication
- Research quality scoring

## Appendix: API Response Schemas

### OpenAI Deep Research Response
```json
{
  "id": "resp_abc123",
  "status": "completed",
  "output": [{
    "type": "message",
    "content": [{
      "type": "output_text",
      "text": "Research findings...",
      "annotations": [...]
    }]
  }],
  "usage": {
    "input_tokens": 1000,
    "output_tokens": 5000
  }
}
```

### Perplexity Response
```json
{
  "choices": [{
    "message": {
      "content": "Research results with [1] citations..."
    }
  }],
  "citations": ["https://source1.com"],
  "usage": {
    "total_tokens": 2000
  }
}
```

This PRD provides a comprehensive specification for implementing Thoth v0.5 with all discovered API details, best practices, and implementation patterns integrated into a cohesive product vision.