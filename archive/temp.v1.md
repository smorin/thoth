# Thoth PRD v8 Recommendations

## 1. Configuration File Structure
**Recommendation: Use a single config.toml file**

Benefits:
- Simpler for users to manage
- Single source of truth
- Easier backup and sharing
- Less file system clutter

Proposed structure for single `~/.thoth/config.toml`:
```toml
[general]
default_project = ""  # Empty means ad-hoc mode (current directory)
default_mode = "deep_research"

[paths]
base_output_dir = "./research-outputs"  # Default base directory for projects
checkpoint_dir = "~/.thoth/checkpoints"

[execution]
poll_interval = 30
max_wait = 30
parallel_providers = true

[providers.openai]
api_key = "${OPENAI_API_KEY}"  # Environment variable reference
model = "o1-deep-research"
tools = ["web_search", "code_interpreter"]

[providers.perplexity]
api_key = "${PERPLEXITY_API_KEY}"
model = "sonar-pro"
search_domains = ["arxiv.org", "nature.com"]

[modes.thinking]
provider = "openai"
model = "gpt-4o-mini"
temperature = 0.4

[modes.deep_research]
providers = ["openai", "perplexity"]
parallel = true
```

## 2. Command-Line Interface Clarifications

### Async Flag
- Use `--async` / `-A` as the primary flag (it's clearer than --no-wait)
- `-A` is just a flag, not accepting arguments
- Correct usage: `thoth deep_research "query" -A`

### Command Matrix Additions
Add these to the options matrix:

| Command | Description |
|---------|-------------|
| init | Initialize configuration and run setup wizard |
| status ID | Check status of a specific research operation |
| list | List all active/recent research operations |

### Research ID vs Resume Comparison

| Aspect | --research-id | --resume |
|--------|---------------|----------|
| Purpose | Original flag name | Clearer alias |
| Short form | None | -R |
| Usage | `--research-id ID` | `--resume ID` or `-R ID` |
| Recommendation | **Use --resume as primary, keep --research-id for backwards compatibility** |

**Rationale**: "Resume" is more intuitive - users understand they're resuming an operation.

### Output Directory Structure (Simplified)
**Remove organization concept entirely** - Just use simple directory structure:

**Project Mode** (when --project specified):
```
research-outputs/
└── project-name/
    ├── 2024-08-03_050145_clarification-arguments_clarification.md
    └── 2024-08-04_070321_deep_research-quantum_crypto.md
```

**Ad-Hoc Mode** (default - no project specified):
- Files created in current working directory
- No subdirectories created
```
./2024-08-03_050145_clarification-arguments_clarification.md
./2024-08-04_070321_deep_research-quantum_crypto.md
```

**Command-line Override**:
- `--output-dir PATH` overrides destination for structured output
- In ad-hoc mode (no --structured flag), files always go to current directory

**Filename Format**: `YYYY-MM-DD_HHMMSS_<mode>-<slug>.md`

## 3. Typer vs Click Comparison

### Click
**Pros:**
- More mature, battle-tested (10+ years)
- Extremely flexible and customizable
- Larger ecosystem of extensions
- Better for complex nested commands
- More control over parsing behavior

**Cons:**
- More verbose syntax
- Steeper learning curve
- Requires more boilerplate code
- Less automatic type inference

### Typer
**Pros:**
- Built on top of Click (inherits stability)
- Modern Python type hints for automatic CLI generation
- Much less boilerplate code
- Automatic help generation from docstrings
- Better IDE support due to type hints
- Easier to maintain

**Cons:**
- Newer library (less battle-tested)
- Less flexibility for edge cases
- Smaller community
- Fewer advanced features

### Recommendation: Use Click

**Rationale for our requirements:**
1. We need fine control over command structure (modes as positional args)
2. Complex mutual exclusivity rules require custom validation
3. We're building a single-file script where verbosity is less of an issue
4. Click's maturity important for production CLI tool
5. Better documentation for advanced use cases

Example implementation with Click:
```python
import click

@click.command()
@click.argument('mode', required=False)
@click.argument('query', required=False)
@click.option('--async', '-A', is_flag=True, help='Submit and exit')
@click.option('--resume', '-R', 'resume_id', help='Resume by ID')
@click.option('--project', '-p', help='Project name')
def main(mode, query, async_, resume_id, project):
    # Validation logic
    if async_ and resume_id:
        raise click.BadParameter("Cannot use --async with --resume")
```

## 4. Implementation Corrections

### OpenAI Role Fix
Change from "developer" to "system":
```python
messages = [
    {"role": "system", "content": "You are a deep research assistant."},
    {"role": "user", "content": query}
]
```

### Path Expansion in Configuration
Ensure all paths in config are properly expanded:
```python
from pathlib import Path

def load_config():
    config = load_toml("~/.thoth/config.toml")
    
    # Expand all paths
    if "paths" in config:
        for key, value in config["paths"].items():
            config["paths"][key] = str(Path(value).expanduser())
    
    # Also handle output_dir at top level if present
    if "output_dir" in config.get("general", {}):
        config["general"]["output_dir"] = str(
            Path(config["general"]["output_dir"]).expanduser()
        )
    
    return config
```

## 5. Additional Recommendations

### Remove Overlapping Features
- Remove --no-wait (keep only --async)
- Remove --research-id (keep --resume with backwards compatibility)
- Remove --organization concept entirely (no flag, no config)

### Standardize Naming
- Use "operation_id" consistently (not "research_id")
- Use "system" role for OpenAI (not "developer")
- Use "~/.thoth/config.toml" as single config file

### Python Version
- Require Python ≥ 3.11 (remove tomli dependency)
- Use built-in tomllib for TOML parsing

### Fix Polling Rate
- Keep 30-second default (exactly 2 per minute)
- Update N-01 to "≤ 2 per minute" (not less than)

## Summary of Changes for v8

1. **Single config file**: `~/.thoth/config.toml` with all settings
2. **Use Click**: Better suited for our complex CLI requirements  
3. **Standardize on --async/-A**: Remove --no-wait
4. **Use --resume/-R**: Keep --research-id for compatibility
5. **Fix role names**: Use "system" not "developer"
6. **Path expansion**: Handle ~ properly in all paths
7. **Python 3.11+**: Use built-in tomllib
8. **Simplified output**: Remove organization concept entirely
9. **Fix polling math**: 30s = 2/minute exactly

## New Output Behavior

1. **Ad-hoc mode (default)**: 
   - No --project specified → files go to current directory
   - No subdirectories created
   - Simple filenames: `YYYY-MM-DD_HHMMSS_<mode>-<slug>.md`

2. **Project mode**:
   - --project specified → files go to `base_output_dir/project-name/`
   - Default base_output_dir is `./research-outputs`
   - Can be overridden in config

3. **Override options**:
   - `--output-dir PATH` overrides destination for any structured output
   - Without --structured flag, output goes to stdout only