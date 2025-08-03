# Thoth v1.5 Implementation Plan - Version 1.0

## Overview

This plan reflects the actual implementation status based on comprehensive test suite results. The focus remains on delivering a working tool incrementally, starting with the core functionality and progressively adding features.

**Test Results Summary**: 5/25 tests passing (20% pass rate)
- 17 tests fail due to missing API keys
- 3 tests fail due to other implementation issues

## Development Principles

- **Incremental delivery**: Each milestone produces a working version
- **Test-first approach**: Test plans guide implementation
- **User-centric design**: Prioritize the simplest use cases first
- **Progressive enhancement**: Add complexity only after basics work

---

## Milestone 1: Core CLI Foundation (M1-01 to M1-10)

**Goal**: Establish the basic CLI structure with simple command parsing and mock functionality

**Status**: Partially complete - basic structure exists but mock provider requires API keys

### Implementation Tasks

- [x] **M1-01**: Set up Python project structure with UV script header
- [x] **M1-02**: Implement basic Click CLI with version display
- [x] **M1-03**: Add query parsing for quick mode (`thoth "query"`)
- [ ] **M1-04**: Create mock provider that returns static responses ❌ *Mock provider requires API key*
- [ ] **M1-05**: Implement basic file output to current directory ❌ *Cannot test without working provider*
- [ ] **M1-06**: Add timestamp-based filename generation ❌ *Cannot test without working provider*
- [x] **M1-07**: Create basic progress display (spinner)
- [x] **M1-08**: Add help text with quick mode examples
- [ ] **M1-09**: Implement Ctrl-C graceful shutdown ❌ *Not tested*
- [x] **M1-10**: Create basic error handling structure

### Test Plan (M1T-01 to M1T-05)

- [x] **M1T-01**: Verify `thoth --version` displays version ✅
- [ ] **M1T-02**: Verify `thoth "test query"` creates output file ❌ *API key required*
- [ ] **M1T-03**: Verify filename follows correct pattern ❌ *API key required*
- [ ] **M1T-04**: Verify Ctrl-C exits cleanly ❌ *Not tested*
- [x] **M1T-05**: Verify help text shows quick mode prominently ✅

### Critical Issue
**Mock provider does not bypass API key checks** - This defeats the purpose of having a mock provider for testing.

---

## Milestone 2: Configuration System (M2-01 to M2-08)

**Goal**: Implement configuration management with environment variable support

**Status**: Mostly complete but with issues

### Implementation Tasks

- [x] **M2-01**: Create Config class for loading configuration
- [x] **M2-02**: Implement TOML config file parsing
- [x] **M2-03**: Add environment variable substitution (`${VAR}`)
- [x] **M2-04**: Create default configuration structure
- [x] **M2-05**: Implement config file path resolution (`~/.thoth/config.toml`)
- [x] **M2-06**: Add path expansion for file paths
- [x] **M2-07**: Create init command skeleton
- [ ] **M2-08**: Add API key validation and masking ❌ *Errors appear in stdout not stderr*
- [ ] **M2-09**: Add config file location option

### Test Plan (M2T-01 to M2T-05)

- [ ] **M2T-01**: Verify environment variables are read correctly ❌ *Error in wrong stream*
- [ ] **M2T-02**: Verify config file overrides defaults ❌ *Not tested*
- [ ] **M2T-03**: Verify CLI args override config file ❌ *Not tested*
- [ ] **M2T-04**: Verify API keys are masked in output ❌ *Not tested*
- [ ] **M2T-05**: Verify config file location works ❌ *Not tested*

### Issues
- Error messages appear in stdout instead of stderr
- API key errors shown even with empty string (should detect empty as missing)

---

## Milestone 3: Provider Architecture (M3-01 to M3-10)

**Goal**: Build the provider abstraction and integrate real LLM providers

**Status**: Structure exists but not functional

### Implementation Tasks

- [x] **M3-01**: Create ResearchProvider base class
- [ ] **M3-02**: Implement MockProvider with configurable delays ❌ *Requires API key*
- [x] **M3-03**: Create OpenAIProvider skeleton
- [x] **M3-04**: Create PerplexityProvider skeleton
- [x] **M3-05**: Implement provider job submission interface
- [x] **M3-06**: Add provider status checking mechanism
- [x] **M3-07**: Implement result retrieval interface
- [x] **M3-08**: Add provider-specific error handling
- [x] **M3-09**: Create provider factory/registry ✅ *Implemented as create_provider()*
- [ ] **M3-10**: Implement parallel provider execution ❌ *Cannot test*

### Test Plan (M3T-01 to M3T-05)

- [ ] **M3T-01**: Verify mock provider completes after delay ❌ *API key required*
- [ ] **M3T-02**: Verify multiple providers run in parallel ❌ *API key required*
- [ ] **M3T-03**: Verify provider errors are handled gracefully ❌ *Wrong error shown*
- [ ] **M3T-04**: Verify --provider flag limits execution ❌ *API key required*
- [ ] **M3T-05**: Verify progress shows all active providers ❌ *Cannot test*

### Critical Issue
**Mock provider should work without API keys** for testing purposes

---

## Milestone 4: Mode System (M4-01 to M4-08)

**Goal**: Implement the mode system with built-in and custom modes

**Status**: Structure exists but cannot be tested

### Implementation Tasks

- [x] **M4-01**: Define built-in modes dictionary
- [x] **M4-02**: Implement mode configuration loading
- [x] **M4-03**: Add default mode selection (deep_research)
- [x] **M4-04**: Create mode-specific system prompts
- [x] **M4-05**: Implement mode command parsing
- [ ] **M4-06**: Add mode validation ❌ *Validation happens after API key check*
- [x] **M4-07**: Create mode-specific provider selection
- [x] **M4-08**: Implement mode chaining metadata
- [x] **M4-09**: Create special "default" mode with no system prompt
- [x] **M4-10**: Update default mode selection to use "default" instead of "deep_research"

### Test Plan (M4T-01 to M4T-06)

- [ ] **M4T-01**: Verify default mode is "default" (not deep_research) ❌ *API key required*
- [ ] **M4T-02**: Verify all built-in modes are accessible ❌ *API key required*
- [ ] **M4T-03**: Verify mode-specific prompts are used ❌ *Cannot test*
- [ ] **M4T-04**: Verify unknown modes show helpful error ❌ *API key check happens first*
- [ ] **M4T-05**: Verify default mode passes query without system prompt ❌ *Cannot test*
- [ ] **M4T-06**: Verify `thoth "query"` uses default mode, not deep_research ❌ *Cannot test*

### Issue
Mode validation should happen before provider initialization

---

## Milestone 5: Async Operations (M5-01 to M5-10)

**Goal**: Implement background operation support with checkpointing

**Status**: Basic structure exists but untested

### Implementation Tasks

- [x] **M5-01**: Create OperationStatus data model
- [x] **M5-02**: Implement CheckpointManager class
- [x] **M5-03**: Add operation ID generation (unique format)
- [x] **M5-04**: Create checkpoint save/load functionality
- [x] **M5-05**: Implement --async flag handling
- [x] **M5-06**: Add status command implementation
- [x] **M5-07**: Create list command for operations
- [x] **M5-08**: Implement resume functionality
- [x] **M5-09**: Add checkpoint corruption recovery
- [ ] **M5-10**: Create operation lifecycle management

### Test Plan (M5T-01 to M5T-05)

- [ ] **M5T-01**: Verify --async returns operation ID immediately ❌ *API key required*
- [ ] **M5T-02**: Verify status command shows operation details ❌ *Wrong exit code*
- [ ] **M5T-03**: Verify list command shows recent operations ❌ *Pattern mismatch*
- [ ] **M5T-04**: Verify checkpoints persist across runs ❌ *Not tested*
- [ ] **M5T-05**: Verify corrupted checkpoints are handled ❌ *Not tested*

### Issues
- Status command returns exit code 1 instead of 2 for missing arguments
- List command output doesn't match expected pattern

---

## Milestone 6: Output Management (M6-01 to M6-08)

**Goal**: Implement sophisticated output file handling and combined reports

**Status**: Cannot be tested without working providers

### Implementation Tasks

- [x] **M6-01**: Create OutputManager class
- [x] **M6-02**: Implement filename generation with deduplication
- [x] **M6-03**: Add project-based output directory support
- [x] **M6-04**: Create markdown metadata headers
- [x] **M6-05**: Implement combined report generation
- [x] **M6-06**: Add disk space checking
- [x] **M6-07**: Create output file organization
- [ ] **M6-08**: Implement --no-combined flag

### Test Plan (M6T-01 to M6T-04)

- [ ] **M6T-01**: Verify files are created in current directory by default ❌ *API key required*
- [ ] **M6T-02**: Verify project mode creates subdirectories ❌ *Skipped*
- [ ] **M6T-03**: Verify combined reports merge all providers ❌ *Cannot test*
- [ ] **M6T-04**: Verify duplicate filenames are handled ❌ *Cannot test*

---

## Milestone 7: Progress and UX (M7-01 to M7-08)

**Goal**: Implement rich progress display and user experience improvements

**Status**: Basic implementation exists but cannot be fully tested

### Implementation Tasks

- [x] **M7-01**: Integrate Rich progress bars
- [x] **M7-02**: Add provider-specific progress tracking
- [x] **M7-03**: Implement elapsed time display
- [ ] **M7-04**: Create adaptive polling intervals
- [x] **M7-05**: Add verbose and quiet modes
- [ ] **M7-06**: Implement first-time setup flow
- [ ] **M7-07**: Add helpful tips for new users
- [x] **M7-08**: Create operation time estimates

### Test Plan (M7T-01 to M7T-04)

- [ ] **M7T-01**: Verify progress shows percentage and time ❌ *Cannot test*
- [ ] **M7T-02**: Verify quiet mode suppresses output ❌ *API key required*
- [ ] **M7T-03**: Verify verbose mode shows detailed info ❌ *API key required*
- [ ] **M7T-04**: Verify first-time users see setup prompt ❌ *Not implemented*

---

## Milestone 8: Real Provider Integration (M8-01 to M8-10)

**Goal**: Implement actual OpenAI and Perplexity provider connections

**Status**: Partially started

### Implementation Tasks

- [x] **M8-01**: Implement OpenAI API client setup ✅ *AsyncOpenAI initialized*
- [x] **M8-02**: Create OpenAI job submission logic ✅ *Basic implementation exists*
- [ ] **M8-03**: Add OpenAI status polling
- [ ] **M8-04**: Implement OpenAI result retrieval
- [ ] **M8-05**: Create Perplexity API integration
- [ ] **M8-06**: Add retry logic with exponential backoff
- [ ] **M8-07**: Implement rate limiting handling
- [ ] **M8-08**: Add quota exceeded error handling
- [ ] **M8-09**: Create provider-specific timeout logic
- [ ] **M8-10**: Implement network error recovery

---

## Milestone 9: Advanced Features (M9-01 to M9-08)

**Goal**: Implement mode chaining, auto-input, and other advanced features

**Status**: Structure exists but untested

### Implementation Tasks

- [x] **M9-01**: Implement --auto flag for mode chaining
- [x] **M9-02**: Create previous output detection logic
- [x] **M9-03**: Add --query-file support with stdin
- [ ] **M9-04**: Implement input file content inclusion
- [x] **M9-05**: Add mode-specific auto-input config
- [x] **M9-06**: Create operation metadata tracking
- [x] **M9-07**: Implement max file size limits
- [x] **M9-08**: Add symlink path resolution

---

## Milestone 10: Polish and Production (M10-01 to M10-08)

**Goal**: Final polish, error handling, and production readiness

**Status**: Basic error handling exists

### Implementation Tasks

- [x] **M10-01**: Comprehensive error message improvements
- [ ] **M10-02**: Add operation cleanup for old checkpoints
- [ ] **M10-03**: Implement all edge case handling ❌ *Empty query returns 0, not 2*
- [ ] **M10-04**: Create performance optimizations
- [ ] **M10-05**: Add security validations
- [x] **M10-06**: Implement final help text formatting
- [ ] **M10-07**: Create shell completion support
- [ ] **M10-08**: Add final testing and bug fixes

---

## Critical Issues Summary

1. **Mock Provider Requires API Key**: The mock provider should work without any API keys for testing purposes. This is the single biggest blocker for testing.

2. **Error Stream Confusion**: Errors are appearing in stdout instead of stderr, making it difficult for scripts to properly handle errors.

3. **Validation Order**: Mode and provider validation happens after API key checks, preventing proper error messages for invalid modes/providers.

4. **Exit Codes**: Several commands return incorrect exit codes (e.g., empty query returns 0 instead of 2).

5. **Pattern Mismatches**: Some output patterns don't match expected formats (e.g., list command output).

## Recommendations

1. **Priority 1**: Fix mock provider to bypass API key checks entirely
2. **Priority 2**: Ensure all errors go to stderr, not stdout
3. **Priority 3**: Validate modes and providers before checking API keys
4. **Priority 4**: Fix exit codes to match CLI best practices
5. **Priority 5**: Update output formats to match documented patterns

## Test Coverage

- **Total Tests**: 25
- **Passing**: 5 (20%)
- **API Key Failures**: 17 (68%)
- **Other Failures**: 3 (12%)

Once the mock provider works without API keys, we can properly test approximately 80% of the functionality.