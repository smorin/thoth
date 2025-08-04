# Thoth v1.5 Development Milestones

## Overview
This document tracks the implementation progress of Thoth v1.5, with checkboxes indicating the status of each task.

**Legend:**
- `[x]` Completed
- `[-]` In Progress
- `[ ]` Not Started

---

## [x] Milestone 1: Core CLI Foundation (v0.1.0)
**Goal**: Establish the basic CLI structure with simple command parsing and mock functionality

### Tasks
- [x] [M1-T1] Set up Python project structure with UV script header
- [x] [M1-T2] Implement basic Click CLI with version display
- [x] [M1-T3] Add query parsing for quick mode (`thoth "query"`)
- [x] [M1-T4] Create mock provider that returns static responses
- [x] [M1-T5] Implement basic file output to current directory
- [x] [M1-T6] Add timestamp-based filename generation
- [x] [M1-T7] Create basic progress display (spinner)
- [x] [M1-T8] Add help text with quick mode examples
- [x] [M1-T9] Implement Ctrl-C graceful shutdown
- [x] [M1-T10] Create basic error handling structure

### Deliverable
```bash
$ thoth "explain DNS"
⠋ Researching...
✓ Research completed!

Files created:
  • 2024-08-03_143022_deep_research_openai_explain-dns.md
```

### Verification
- [x] `thoth --version` displays version
- [ ] `thoth "test query"` creates output file
- [ ] Filename follows correct pattern
- [ ] Ctrl-C exits cleanly
- [ ] Help text shows quick mode prominently

---

## [x] Milestone 2: Configuration System (v0.2.0)
**Goal**: Implement configuration management with environment variable support

### Tasks
- [x] [M2-T1] Create Config class for loading configuration
- [x] [M2-T2] Implement TOML config file parsing
- [x] [M2-T3] Add environment variable substitution (`${VAR}`)
- [x] [M2-T4] Create default configuration structure
- [x] [M2-T5] Implement config file path resolution (`~/.thoth/config.toml`)
- [x] [M2-T6] Add path expansion for file paths
- [x] [M2-T7] Create init command skeleton
- [x] [M2-T8] Add API key validation and masking
- [ ] [M2-T9] Implement two-level help system with command-specific help

### Deliverable
Configuration system that reads from environment, config file, and CLI args with proper precedence.

### Verification
- [ ] Environment variables are read correctly
- [ ] Config file overrides defaults
- [ ] CLI args override config file
- [x] API keys are masked in output

---

## [x] Milestone 3: Provider Architecture (v0.3.0)
**Goal**: Build the provider abstraction and integrate real LLM providers

### Tasks
- [x] [M3-T1] Create ResearchProvider base class
- [x] [M3-T2] Implement MockProvider with configurable delays
- [x] [M3-T3] Create OpenAIProvider skeleton
- [x] [M3-T4] Create PerplexityProvider skeleton
- [x] [M3-T5] Implement provider job submission interface
- [x] [M3-T6] Add provider status checking mechanism
- [x] [M3-T7] Implement result retrieval interface
- [x] [M3-T8] Add provider-specific error handling
- [ ] [M3-T9] Create provider factory/registry
- [x] [M3-T10] Implement parallel provider execution

### Deliverable
Working provider system with mock provider for testing.

### Verification
- [ ] Mock provider completes after delay
- [ ] Multiple providers run in parallel
- [ ] Provider errors are handled gracefully
- [ ] --provider flag limits execution
- [ ] Progress shows all active providers

---

## [x] Milestone 4: Mode System (v0.4.0)
**Goal**: Implement the mode system with built-in and custom modes

### Tasks
- [x] [M4-T1] Define built-in modes dictionary
- [x] [M4-T2] Implement mode configuration loading
- [x] [M4-T3] Add default mode selection (deep_research)
- [x] [M4-T4] Create mode-specific system prompts
- [x] [M4-T5] Implement mode command parsing
- [ ] [M4-T6] Add mode validation
- [x] [M4-T7] Create mode-specific provider selection
- [x] [M4-T8] Implement mode chaining metadata
- [x] [M4-T9] Create special "default" mode with no system prompt
- [x] [M4-T10] Update default mode selection to use "default" instead of "deep_research"

### Deliverable
Mode system allowing different research workflows.

### Verification
- [ ] Default mode is "default" (not deep_research)
- [ ] All built-in modes are accessible
- [ ] Mode-specific prompts are used
- [ ] Unknown modes show helpful error
- [ ] Default mode passes query without system prompt
- [ ] `thoth "query"` uses default mode, not deep_research

---

## [x] Milestone 5: Async Operations (v0.5.0)
**Goal**: Implement background operation support with checkpointing

### Tasks
- [x] [M5-T1] Create OperationStatus data model
- [x] [M5-T2] Implement CheckpointManager class
- [x] [M5-T3] Add operation ID generation (unique format)
- [x] [M5-T4] Create checkpoint save/load functionality
- [x] [M5-T5] Implement --async flag handling
- [x] [M5-T6] Add status command implementation
- [x] [M5-T7] Create list command for operations
- [x] [M5-T8] Implement resume functionality
- [x] [M5-T9] Add checkpoint corruption recovery
- [ ] [M5-T10] Create operation lifecycle management

### Deliverable
Async operations with checkpoint/resume capability.

### Verification
- [ ] --async returns operation ID immediately
- [ ] status command shows operation details
- [ ] list command shows recent operations
- [ ] Checkpoints persist across runs
- [ ] Corrupted checkpoints are handled

---

## [x] Milestone 6: Output Management (v0.6.0)
**Goal**: Implement sophisticated output file handling and combined reports

### Tasks
- [x] [M6-T1] Create OutputManager class
- [x] [M6-T2] Implement filename generation with deduplication
- [x] [M6-T3] Add project-based output directory support
- [x] [M6-T4] Create markdown metadata headers
- [x] [M6-T5] Implement combined report generation
- [x] [M6-T6] Add disk space checking
- [x] [M6-T7] Create output file organization
- [ ] [M6-T8] Implement --no-combined flag

### Deliverable
Robust output file management with combined reports.

### Verification
- [ ] Files are created in current directory by default
- [ ] Project mode creates subdirectories
- [ ] Combined reports merge all providers
- [ ] Duplicate filenames are handled

---

## [-] Milestone 7: Progress and UX (v0.7.0)
**Goal**: Implement rich progress display and user experience improvements

### Tasks
- [x] [M7-T1] Integrate Rich progress bars
- [x] [M7-T2] Add provider-specific progress tracking
- [x] [M7-T3] Implement elapsed time display
- [ ] [M7-T4] Create adaptive polling intervals
- [x] [M7-T5] Add verbose and quiet modes
- [ ] [M7-T6] Implement first-time setup flow
- [ ] [M7-T7] Add helpful tips for new users
- [x] [M7-T8] Create operation time estimates

### Deliverable
Professional progress display and improved UX.

### Verification
- [ ] Progress shows percentage and time
- [ ] Quiet mode suppresses output
- [ ] Verbose mode shows detailed info
- [ ] First-time users see setup prompt

---

## [ ] Milestone 8: Real Provider Integration (v1.0.0)
**Goal**: Implement actual OpenAI and Perplexity provider connections

### Tasks
- [ ] [M8-T1] Implement OpenAI API client setup
- [ ] [M8-T2] Create OpenAI job submission logic
- [ ] [M8-T3] Add OpenAI status polling
- [ ] [M8-T4] Implement OpenAI result retrieval
- [ ] [M8-T5] Create Perplexity API integration
- [ ] [M8-T6] Add retry logic with exponential backoff
- [ ] [M8-T7] Implement rate limiting handling
- [ ] [M8-T8] Add quota exceeded error handling
- [ ] [M8-T9] Create provider-specific timeout logic
- [ ] [M8-T10] Implement network error recovery

### Deliverable
Working integration with real LLM providers.

### Verification
- [ ] OpenAI provider submits real requests
- [ ] Perplexity returns search results
- [ ] Network errors trigger retries
- [ ] API errors show helpful messages
- [ ] Long operations complete successfully

---

## [-] Milestone 9: Advanced Features (v1.2.0)
**Goal**: Implement mode chaining, auto-input, and other advanced features

### Tasks
- [x] [M9-T1] Implement --auto flag for mode chaining
- [x] [M9-T2] Create previous output detection logic
- [x] [M9-T3] Add --query-file support with stdin
- [ ] [M9-T4] Implement input file content inclusion
- [x] [M9-T5] Add mode-specific auto-input config
- [x] [M9-T6] Create operation metadata tracking
- [x] [M9-T7] Implement max file size limits
- [x] [M9-T8] Add symlink path resolution

### Deliverable
Advanced features for power users.

### Verification
- [ ] --auto finds previous outputs
- [ ] stdin input works with size limit
- [ ] Mode chains work correctly
- [ ] Input files are tracked in metadata

---

## [-] Milestone 10: Polish and Production (v1.5.0)
**Goal**: Final polish, error handling, and production readiness

### Tasks
- [x] [M10-T1] Comprehensive error message improvements
- [ ] [M10-T2] Add operation cleanup for old checkpoints
- [ ] [M10-T3] Implement all edge case handling
- [ ] [M10-T4] Create performance optimizations
- [ ] [M10-T5] Add security validations
- [x] [M10-T6] Implement final help text formatting
- [ ] [M10-T7] Create shell completion support
- [ ] [M10-T8] Add final testing and bug fixes

### Deliverable
Production-ready Thoth v1.5 with all features implemented and tested.

### Verification
- [ ] All error paths show helpful messages
- [ ] Performance meets requirements
- [ ] Security (API key masking, etc)
- [ ] Full end-to-end integration tests
- [ ] Cross-platform compatibility tests

---

## [x] Milestone 28: Interactive Query Mode (v2.3.0)
**Goal**: Implement interactive query input with bordered UI and slash commands

### Tasks
- [x] [M28-T1] Add -i/--interactive CLI option to Click command
- [x] [M28-T2] Implement bordered text box rendering using Prompt Toolkit Frame widget
- [x] [M28-T3] Create multi-line input handler with Alt+Enter support (prompt_toolkit limitation)
- [x] [M28-T4] Display help instructions above box in dim color
- [x] [M28-T5] Implement placeholder text or hint system (prompt text shown as '>' prompt)
- [x] [M28-T6] Implement slash command parser and registry
- [x] [M28-T7] Add /help command with command listing
- [x] [M28-T8] Add /mode command with auto-completion
- [x] [M28-T9] Add /provider command for provider selection
- [x] [M28-T10] Add /async toggle command
- [x] [M28-T11] Add /status command for operation checking
- [x] [M28-T12] Add /exit and /quit commands
- [x] [M28-T13] Implement Unix line editing shortcuts (Ctrl+A, Ctrl+E, Ctrl+K)
- [x] [M28-T14] Add terminal width detection and box sizing
- [x] [M28-T15] Integrate with existing research execution flow
- [x] [M28-T16] Add tests for interactive mode
- [x] [M28-T17] Update documentation and README

### Deliverable
```bash
$ thoth -i
[dim]Enter query • Shift+Enter: new line • Enter: submit • /help: commands[/dim]
┌────────────────────────────────────────────────────────────────────┐
│ > /mode deep_research                                              │
└────────────────────────────────────────────────────────────────────┘
[green]Mode set to: deep_research[/green]

┌────────────────────────────────────────────────────────────────────┐
│ > What is quantum computing?                                       │
└────────────────────────────────────────────────────────────────────┘
[Submits and exits to normal processing]
```

### Verification
- [x] Interactive mode launches with -i flag
- [x] Instructions appear in dim color above box
- [x] Box renders correctly with borders (when terminal available)
- [x] Placeholder text shown as '>' prompt
- [x] Multi-line input works with Alt+Enter (Meta+Enter)
- [x] All slash commands function correctly
- [x] Unix line editing shortcuts work (Ctrl+A, Ctrl+E, Ctrl+K)
- [x] Integrates seamlessly with existing features
- [x] Single query per session with automatic exit
- [x] Tab completion for slash commands
- [x] Numbered selection menus for modes and providers
- [x] Tests verify all interactive mode functionality

---

## [x] Milestone 29: Interactive Mode CLI Initialization (v2.4.0)
**Goal**: Enable interactive mode to be initialized with command-line settings

### Tasks
- [x] [M29-T1] Create InteractiveInitialSettings dataclass for passing CLI parameters
- [x] [M29-T2] Update CLI function to determine mode and query before entering interactive mode
- [x] [M29-T3] Modify enter_interactive_mode to accept initial settings
- [x] [M29-T4] Update InteractiveSession class to use initial settings
- [x] [M29-T5] Pre-populate text area with initial query if provided
- [x] [M29-T6] Initialize slash registry with mode/provider from CLI
- [x] [M29-T7] Support reading query from stdin with --query-file -
- [x] [M29-T8] Add Shift+Return support via CSI-u extended keyboard mode
- [x] [M29-T9] Maintain fallback keyboard shortcuts (Ctrl+J, Alt+Enter)
- [x] [M29-T10] Create comprehensive pexpect test suite for interactive features
- [x] [M29-T11] Update documentation with new initialization capabilities

### Deliverable
```bash
# Start interactive mode with pre-configured settings
$ thoth -i --mode deep_research --provider openai "initial query"
[Interactive mode starts with query pre-populated, mode and provider set]

# Pipe query into interactive mode
$ echo "query from stdin" | thoth -i --query-file -
[Interactive mode starts with piped query]

# Combined settings
$ thoth -i --mode exploration --provider perplexity --async "test query"
[All settings initialized from command line]
```

### Verification
- [x] Initial query populates in text area
- [x] Mode is set from --mode argument
- [x] Provider is set from --provider argument
- [x] Async mode is set from --async flag
- [x] Query from stdin works with --query-file -
- [x] Settings can be overridden with slash commands
- [x] Shift+Return works in supported terminals (CSI-u)
- [x] Ctrl+J and Alt+Enter work as fallbacks
- [x] All interactive mode tests pass

---

## [x] Milestone 30: Model Cache Control Enhancements (v2.3.1)
**Goal**: Enhance model cache control with --no-cache option

### Tasks
- [x] [M30-T1] Add --no-cache flag to CLI argument parsing
- [x] [M30-T2] Update list_models_cached to support no_cache parameter
- [x] [M30-T3] Modify providers_command to handle --no-cache flag
- [x] [M30-T4] Ensure --no-cache and --refresh-cache are mutually exclusive
- [x] [M30-T5] Update help text and documentation
- [x] [M30-T6] Add tests for --no-cache functionality
- [x] [M30-T7] Update PRD with new requirement

### Deliverable
```bash
# Bypass cache without updating it
$ thoth providers -- --models --no-cache

# This fetches directly from API but doesn't save to cache
# Useful for checking current models without affecting cache
```

### Verification
- [x] --no-cache fetches fresh data from API
- [x] Cache file remains unchanged after --no-cache
- [x] --no-cache and --refresh-cache cannot be used together
- [x] Help text clearly explains the difference

---

## [x] Milestone 31: Interactive Test Framework Integration (v2.5.0)
**Goal**: Integrate pexpect-based interactive tests into the main test framework

### Tasks
- [x] [M31-T1] Add pexpect dependency to thoth_test requirements
- [x] [M31-T2] Create InteractiveTestRunner class for handling pexpect tests
- [x] [M31-T3] Extend TestCase dataclass with interactive test fields
- [x] [M31-T4] Add keyboard key constants for terminal control
- [x] [M31-T5] Implement run_interactive_test method in TestRunner
- [x] [M31-T6] Add 12 interactive test cases (INT-01 through INT-12)
- [x] [M31-T7] Add --interactive CLI flag to filter interactive tests
- [x] [M31-T8] Test framework with both subprocess and interactive tests
- [x] [M31-T9] Verify all 12 interactive tests pass

### Deliverable
```bash
# Run only interactive mode tests
$ ./thoth_test -r --interactive

# Run specific interactive test
$ ./thoth_test -r --provider mock -t INT-09

# Run mix of test types
$ ./thoth_test -r --provider mock
```

### Verification
- [x] Interactive tests run using pexpect terminal emulation
- [x] Subprocess tests continue to work as before
- [x] --interactive flag filters to only interactive tests
- [x] All 12 interactive tests pass successfully
- [x] Framework handles both test types seamlessly

---

## [x] Milestone 32: Architecture Cleanup (v2.4.0)
**Goal**: Refactor monolithic codebase into clean class-based architecture while maintaining single-file distribution

### Tasks
- [x] [M32-T1] Create ConfigManager class with layered configuration support
- [x] [M32-T2] Implement configuration precedence (defaults < user < project < env < CLI)
- [x] [M32-T3] Create CommandHandler class for unified command execution
- [x] [M32-T4] Implement ProviderRegistry for better provider management  
- [x] [M32-T5] Add configuration schema and validation
- [x] [M32-T6] Reorganize code with clear section headers and class structure
- [x] [M32-T7] Simplify main CLI function using new classes
- [x] [M32-T8] Add support for project-level config files
- [x] [M32-T9] Test backward compatibility with existing commands
- [x] [M32-T10] Update documentation for new architecture

### Deliverable
```python
# Clean architecture with class-based organization
config_manager = ConfigManager()
config_manager.load_all_layers(cli_args)
config = config_manager.get_effective_config()

handler = CommandHandler(config_manager)
result = handler.execute(command, **params)
```

### Verification
- [x] Configuration precedence works correctly
- [x] All existing commands function as before
- [x] Project-level configs override user configs
- [x] Code is better organized with clear separation
- [x] Single file maintained for easy distribution

---

## [ ] Milestone 33: Integrated Clarification Mode (v2.6.0)
**Goal**: Integrate clarification mode seamlessly into interactive mode with mode toggling

### Tasks
- [ ] [M33-T1] Add mode state tracking to InteractiveSession (Edit/Clarification)
- [ ] [M33-T2] Implement Shift+Tab key binding for mode toggle
- [ ] [M33-T3] Update status line to show current mode
- [ ] [M33-T4] Create clarification prompt template for query refinement
- [ ] [M33-T5] Implement query interception in Clarification Mode
- [ ] [M33-T6] Send query to LLM for clarification suggestions
- [ ] [M33-T7] Display clarification response in input box
- [ ] [M33-T8] Allow editing of refined query before acceptance
- [ ] [M33-T9] Implement Enter behavior based on current mode
- [ ] [M33-T10] Add --clarify flag to start in Clarification Mode
- [ ] [M33-T11] Update help text with mode toggle instructions
- [ ] [M33-T12] Preserve query content when switching modes
- [ ] [M33-T13] Support multiple clarification rounds
- [ ] [M33-T14] Add visual indicators for mode status
- [ ] [M33-T15] Write tests for mode toggling and clarification
- [ ] [M33-T16] Update documentation with clarification workflow

### Deliverable
```bash
$ thoth -i
[Interactive mode with Shift+Tab to toggle between Edit and Clarification modes]

$ thoth -i --clarify
[Starts directly in Clarification Mode]
```

### Verification
- [ ] Shift+Tab toggles between modes correctly
- [ ] Mode indicator clearly shows current mode
- [ ] Clarification Mode intercepts query submission
- [ ] Clarification suggestions are helpful and relevant
- [ ] Refined query can be edited before acceptance
- [ ] Enter key behavior changes based on mode
- [ ] --clarify flag starts in correct mode
- [ ] Query preserved when switching modes
- [ ] Multiple clarification rounds work
- [ ] Visual feedback is clear and intuitive
- [ ] All tests pass

---

## Current Status

**Version**: 1.5.0 (in development)

**Completed Milestones**: 
- Core CLI Foundation (90%)
- Configuration System (100%)
- Provider Architecture (90%)
- Mode System (87%)
- Async Operations (90%)
- Output Management (87%)

**In Progress**:
- Progress and UX (62%)
- Advanced Features (75%)
- Polish and Production (25%)

**Not Started**:
- Real Provider Integration (0%)

**Key Remaining Tasks**:
1. Fix quick mode command parsing (`thoth "query"`)
2. Implement real OpenAI provider
3. Complete remaining UX improvements
4. Run comprehensive test suite