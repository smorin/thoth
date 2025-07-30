# Thoth v1.5 Implementation Plan

## Overview

This plan breaks down the implementation of Thoth v1.5 into logical milestones, each with specific deliverables and corresponding test plans. The focus is on delivering a working tool incrementally, starting with the core functionality and progressively adding features.

## Development Principles

- **Incremental delivery**: Each milestone produces a working version
- **Test-first approach**: Test plans guide implementation
- **User-centric design**: Prioritize the simplest use cases first
- **Progressive enhancement**: Add complexity only after basics work

---

## Milestone 1: Core CLI Foundation (M1-01 to M1-10)

**Goal**: Establish the basic CLI structure with simple command parsing and mock functionality

### Implementation Tasks

- **M1-01**: Set up Python project structure with UV script header
- **M1-02**: Implement basic Click CLI with version display
- **M1-03**: Add query parsing for quick mode (`thoth "query"`)
- **M1-04**: Create mock provider that returns static responses
- **M1-05**: Implement basic file output to current directory
- **M1-06**: Add timestamp-based filename generation
- **M1-07**: Create basic progress display (spinner)
- **M1-08**: Add help text with quick mode examples
- **M1-09**: Implement Ctrl-C graceful shutdown
- **M1-10**: Create basic error handling structure

### Test Plan (M1T-01 to M1T-05)

- **M1T-01**: Verify `thoth --version` displays version
- **M1T-02**: Verify `thoth "test query"` creates output file
- **M1T-03**: Verify filename follows correct pattern
- **M1T-04**: Verify Ctrl-C exits cleanly
- **M1T-05**: Verify help text shows quick mode prominently

### Deliverable

```bash
$ thoth "explain DNS"
⠋ Researching...
✓ Research completed!

Files created:
  • 2024-08-03_143022_deep_research_mock_explain-dns.md
```

---

## Milestone 2: Configuration System (M2-01 to M2-08)

**Goal**: Implement configuration management with environment variable support

### Implementation Tasks

- **M2-01**: Create Config class for loading configuration
- **M2-02**: Implement TOML config file parsing
- **M2-03**: Add environment variable substitution (`${VAR}`)
- **M2-04**: Create default configuration structure
- **M2-05**: Implement config file path resolution (`~/.thoth/config.toml`)
- **M2-06**: Add path expansion for file paths
- **M2-07**: Create init command skeleton
- **M2-08**: Add API key validation and masking

### Test Plan (M2T-01 to M2T-04)

- **M2T-01**: Verify environment variables are read correctly
- **M2T-02**: Verify config file overrides defaults
- **M2T-03**: Verify CLI args override config file
- **M2T-04**: Verify API keys are masked in output

### Deliverable

```bash
$ export OPENAI_API_KEY="sk-test123"
$ thoth init
✓ Configuration saved to ~/.thoth/config.toml
```

---

## Milestone 3: Provider Architecture (M3-01 to M3-10)

**Goal**: Build the provider abstraction and integrate real LLM providers

### Implementation Tasks

- **M3-01**: Create ResearchProvider base class
- **M3-02**: Implement MockProvider with configurable delays
- **M3-03**: Create OpenAIProvider skeleton
- **M3-04**: Create PerplexityProvider skeleton
- **M3-05**: Implement provider job submission interface
- **M3-06**: Add provider status checking mechanism
- **M3-07**: Implement result retrieval interface
- **M3-08**: Add provider-specific error handling
- **M3-09**: Create provider factory/registry
- **M3-10**: Implement parallel provider execution

### Test Plan (M3T-01 to M3T-05)

- **M3T-01**: Verify mock provider completes after delay
- **M3T-02**: Verify multiple providers run in parallel
- **M3T-03**: Verify provider errors are handled gracefully
- **M3T-04**: Verify --provider flag limits execution
- **M3T-05**: Verify progress shows all active providers

### Deliverable

```bash
$ thoth "test query" --provider mock
⠹ Mock Research: 80% complete
✓ Research completed!
```

---

## Milestone 4: Mode System (M4-01 to M4-08)

**Goal**: Implement the mode system with built-in and custom modes

### Implementation Tasks

- **M4-01**: Define built-in modes dictionary
- **M4-02**: Implement mode configuration loading
- **M4-03**: Add default mode selection (deep_research)
- **M4-04**: Create mode-specific system prompts
- **M4-05**: Implement mode command parsing
- **M4-06**: Add mode validation
- **M4-07**: Create mode-specific provider selection
- **M4-08**: Implement mode chaining metadata

### Test Plan (M4T-01 to M4T-04)

- **M4T-01**: Verify default mode is deep_research
- **M4T-02**: Verify all built-in modes are accessible
- **M4T-03**: Verify mode-specific prompts are used
- **M4T-04**: Verify unknown modes show helpful error

### Deliverable

```bash
$ thoth thinking "quick analysis"
$ thoth exploration "web frameworks"
$ thoth "default uses deep_research"
```

---

## Milestone 5: Async Operations (M5-01 to M5-10)

**Goal**: Implement background operation support with checkpointing

### Implementation Tasks

- **M5-01**: Create OperationStatus data model
- **M5-02**: Implement CheckpointManager class
- **M5-03**: Add operation ID generation (unique format)
- **M5-04**: Create checkpoint save/load functionality
- **M5-05**: Implement --async flag handling
- **M5-06**: Add status command implementation
- **M5-07**: Create list command for operations
- **M5-08**: Implement resume functionality
- **M5-09**: Add checkpoint corruption recovery
- **M5-10**: Create operation lifecycle management

### Test Plan (M5T-01 to M5T-05)

- **M5T-01**: Verify --async returns operation ID immediately
- **M5T-02**: Verify status command shows operation details
- **M5T-03**: Verify list command shows recent operations
- **M5T-04**: Verify checkpoints persist across runs
- **M5T-05**: Verify corrupted checkpoints are handled

### Deliverable

```bash
$ thoth "long research" --async
Operation ID: research-20240803-143022-a1b2c3d4e5f6g7h8

$ thoth status research-20240803-143022-a1b2c3d4e5f6g7h8
Status: running
Progress: 45%
```

---

## Milestone 6: Output Management (M6-01 to M6-08)

**Goal**: Implement sophisticated output file handling and combined reports

### Implementation Tasks

- **M6-01**: Create OutputManager class
- **M6-02**: Implement filename generation with deduplication
- **M6-03**: Add project-based output directory support
- **M6-04**: Create markdown metadata headers
- **M6-05**: Implement combined report generation
- **M6-06**: Add disk space checking
- **M6-07**: Create output file organization
- **M6-08**: Implement --no-combined flag

### Test Plan (M6T-01 to M6T-04)

- **M6T-01**: Verify files are created in current directory by default
- **M6T-02**: Verify project mode creates subdirectories
- **M6T-03**: Verify combined reports merge all providers
- **M6T-04**: Verify duplicate filenames are handled

### Deliverable

```bash
$ thoth "research topic"
Files created:
  • 2024-08-03_143022_deep_research_openai_research-topic.md
  • 2024-08-03_143022_deep_research_perplexity_research-topic.md
  • 2024-08-03_143022_deep_research_combined_research-topic.md
```

---

## Milestone 7: Progress and UX (M7-01 to M7-08)

**Goal**: Implement rich progress display and user experience improvements

### Implementation Tasks

- **M7-01**: Integrate Rich progress bars
- **M7-02**: Add provider-specific progress tracking
- **M7-03**: Implement elapsed time display
- **M7-04**: Create adaptive polling intervals
- **M7-05**: Add verbose and quiet modes
- **M7-06**: Implement first-time setup flow
- **M7-07**: Add helpful tips for new users
- **M7-08**: Create operation time estimates

### Test Plan (M7T-01 to M7T-04)

- **M7T-01**: Verify progress shows percentage and time
- **M7T-02**: Verify quiet mode suppresses output
- **M7T-03**: Verify verbose mode shows detailed info
- **M7T-04**: Verify first-time users see setup prompt

### Deliverable

```bash
$ thoth "complex research"
Researching: complex research
Mode: deep_research | Providers: OpenAI + Perplexity

┌─────────────────────────────────────────┐
│ OpenAI Research    ████████░░ 80%       │
│ Perplexity Research ██████████ 100%     │
└─────────────────────────────────────────┘
Elapsed: 5:23 | Next poll: 15s
```

---

## Milestone 8: Real Provider Integration (M8-01 to M8-10)

**Goal**: Implement actual OpenAI and Perplexity provider connections

### Implementation Tasks

- **M8-01**: Implement OpenAI API client setup
- **M8-02**: Create OpenAI job submission logic
- **M8-03**: Add OpenAI status polling
- **M8-04**: Implement OpenAI result retrieval
- **M8-05**: Create Perplexity API integration
- **M8-06**: Add retry logic with exponential backoff
- **M8-07**: Implement rate limiting handling
- **M8-08**: Add quota exceeded error handling
- **M8-09**: Create provider-specific timeout logic
- **M8-10**: Implement network error recovery

### Test Plan (M8T-01 to M8T-05)

- **M8T-01**: Verify OpenAI provider submits real requests
- **M8T-02**: Verify Perplexity returns search results
- **M8T-03**: Verify network errors trigger retries
- **M8T-04**: Verify API errors show helpful messages
- **M8T-05**: Verify long operations complete successfully

### Deliverable

```bash
$ thoth "real research query"
⠸ OpenAI: Deep research in progress...
⠼ Perplexity: Analyzing 15 sources...
✓ Research completed in 8m 32s
```

---

## Milestone 9: Advanced Features (M9-01 to M9-08)

**Goal**: Implement mode chaining, auto-input, and other advanced features

### Implementation Tasks

- **M9-01**: Implement --auto flag for mode chaining
- **M9-02**: Create previous output detection logic
- **M9-03**: Add --query-file support with stdin
- **M9-04**: Implement input file content inclusion
- **M9-05**: Add mode-specific auto-input config
- **M9-06**: Create operation metadata tracking
- **M9-07**: Implement max file size limits
- **M9-08**: Add symlink path resolution

### Test Plan (M9T-01 to M9T-04)

- **M9T-01**: Verify --auto finds previous outputs
- **M9T-02**: Verify stdin input works with size limit
- **M9T-03**: Verify mode chains work correctly
- **M9T-04**: Verify input files are tracked in metadata

### Deliverable

```bash
$ thoth clarification "building microservices"
$ thoth exploration --auto
Using input from: 2024-08-03_143022_clarification_combined_building-microservices.md
```

---

## Milestone 10: Polish and Production (M10-01 to M10-08)

**Goal**: Final polish, error handling, and production readiness

### Implementation Tasks

- **M10-01**: Comprehensive error message improvements
- **M10-02**: Add operation cleanup for old checkpoints
- **M10-03**: Implement all edge case handling
- **M10-04**: Create performance optimizations
- **M10-05**: Add security validations
- **M10-06**: Implement final help text formatting
- **M10-07**: Create shell completion support
- **M10-08**: Add final testing and bug fixes

### Test Plan (M10T-01 to M10T-05)

- **M10T-01**: Verify all error paths show helpful messages
- **M10T-02**: Verify performance meets requirements
- **M10T-03**: Verify security (API key masking, etc)
- **M10T-04**: Full end-to-end integration tests
- **M10T-05**: Cross-platform compatibility tests

### Deliverable

Production-ready Thoth v1.5 with all features implemented and tested.

---

## Testing Strategy

### Unit Tests
- Test each component in isolation
- Mock external dependencies
- Focus on edge cases and error conditions

### Integration Tests
- Test provider interactions
- Test file system operations
- Test configuration loading

### End-to-End Tests
- Full workflow tests
- Multi-provider scenarios
- Long-running operation tests

### User Acceptance Tests
- Quick mode simplicity
- First-time user experience
- Advanced feature workflows

---

## Risk Mitigation

1. **API Changes**: Abstract provider interfaces to isolate changes
2. **Long Operations**: Implement robust checkpointing early
3. **File Conflicts**: Comprehensive deduplication logic
4. **Network Issues**: Retry logic and clear error messages
5. **Cross-platform**: Test on macOS and Linux throughout

---

## Success Criteria

1. `thoth "query"` works with zero configuration (just env vars)
2. Results appear in current directory within 30 seconds
3. Long operations can be submitted async and resumed
4. Clear progress indication throughout execution
5. All errors have helpful messages and recovery suggestions

---

## Timeline Estimate

- Milestone 1-3: Core foundation (Week 1-2)
- Milestone 4-6: Mode and output systems (Week 3-4)
- Milestone 7-8: Real providers and UX (Week 5-6)
- Milestone 9-10: Advanced features and polish (Week 7-8)

Total estimated time: 8 weeks for full implementation

This plan provides a systematic approach to building Thoth v1.5, with each milestone delivering tangible value and building upon previous work.