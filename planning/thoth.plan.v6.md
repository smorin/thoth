# Thoth v2.5 Implementation Plan - Version 6.0

## Overview

This plan reflects the current state as of March 2026 and identifies the next
priorities for Thoth development. It supersedes plan v5.0 with updated milestone
statuses and a new critical fix milestone.

**Current Status**:
- 84 total tests (44/46 mock, 26/28 provider-agnostic; 16 interactive tests all failing)
- OpenAI provider: Implemented with retry logic and background polling
- Perplexity provider: Skeleton only (raises `NotImplementedError`)
- Gemini provider: Not started
- Interactive mode: Crashes on startup (`AttributeError: TextArea has no attribute 'height'`)

## Development Principles

- **Test-first approach**: Write tests before implementation
- **Incremental delivery**: Each milestone produces a working version
- **User-centric design**: Prioritize the simplest use cases first
- **Provider isolation**: Complete one provider before starting another

---

## Milestone A: Fix Interactive Mode Crash (CRITICAL — Do First)

**Goal**: Fix the `AttributeError: 'TextArea' object has no attribute 'height'`
crash that causes all 16 INT tests to fail.

**Status**: Not started — HIGHEST PRIORITY

**Root Cause**: `InteractiveSession._create_help_text()` (thoth:3795) reads
`self.input_area.height`, but `prompt_toolkit.widgets.TextArea` does not
expose a `.height` attribute. The correct approach is to store the configured
height as an instance variable (`self.input_height`) and read that instead.

### Test Plan (MA-T01 to MA-T05) — Write Tests First

- [ ] **MA-T01**: `thoth -i --provider mock` launches without crashing [INT-smoke]
- [ ] **MA-T02**: Interactive mode shows "Thoth Interactive Mode" banner [INT-01 subset]
- [ ] **MA-T03**: `/help` slash command responds with "Available commands:" [INT-01]
- [ ] **MA-T04**: `/exit` slash command terminates cleanly with exit code 0 [INT-smoke]
- [ ] **MA-T05**: All existing 16 INT test scenarios pass after fix

### Implementation Tasks

- [ ] **MA-01**: Store `input_height` as `self.input_height` in `InteractiveSession.__init__`
- [ ] **MA-02**: Replace `self.input_area.height` with `self.input_height` in `_create_help_text`
- [ ] **MA-03**: Audit all other places that read `TextArea` attributes that don't exist
- [ ] **MA-04**: Run `./thoth_test -r --interactive` and verify all INT tests pass
- [ ] **MA-05**: Run `make check && make fix` and confirm no lint errors

### Acceptance Criteria

- `./thoth_test -r --interactive` passes all 16 INT tests
- `make check` passes without errors
- No regression in non-interactive tests

---

## Milestone B: Perplexity Provider — Basic Implementation

**Goal**: Implement the Perplexity `sonar-deep-research` provider so that
`thoth --provider perplexity "query"` returns a real response.

**Status**: Not started (skeleton with `NotImplementedError` exists at thoth:2286)

**Note**: Perplexity uses the OpenAI-compatible chat completions API.
Model: `sonar-deep-research`. See `planning/references.md` for API docs.

### Test Plan (MB-T01 to MB-T10) — Write Tests First

- [ ] **MB-T01**: `PerplexityProvider.submit()` returns a non-empty string
- [ ] **MB-T02**: Response is saved to a file with `perplexity` in the filename
- [ ] **MB-T03**: Invalid API key shows a helpful error message (not a traceback)
- [ ] **MB-T04**: Network timeout is handled and shows "Connection error" or similar
- [ ] **MB-T05**: Response includes citations from the API response
- [ ] **MB-T06**: Metadata header is included in the output file
- [ ] **MB-T07**: `--provider perplexity` flag selects the correct provider
- [ ] **MB-T08**: Retry logic fires on transient HTTP errors (5xx)
- [ ] **MB-T09**: `thoth providers -- --models` lists `sonar-deep-research`
- [ ] **MB-T10**: Empty or failed response is handled gracefully

### Implementation Tasks

- [ ] **MB-01**: Replace `NotImplementedError` stub with real `httpx` call to
  `https://api.perplexity.ai/chat/completions` (OpenAI-compatible endpoint)
- [ ] **MB-02**: Build request: `{"model": "sonar-deep-research", "messages": [...]}`
- [ ] **MB-03**: Parse response: extract `choices[0].message.content` and
  `citations` array
- [ ] **MB-04**: Append citations section to the output content
- [ ] **MB-05**: Add `@retry` decorator (tenacity) matching OpenAI provider pattern
- [ ] **MB-06**: Add auth via `Authorization: Bearer {api_key}` header
- [ ] **MB-07**: Update `ProviderRegistry` to include Perplexity in provider listing
- [ ] **MB-08**: Add `PERPLEXITY_API_KEY` to config defaults and env substitution

### Acceptance Criteria

- `./thoth_test -r --provider perplexity` passes all Perplexity tests (requires key)
- `./thoth_test -r --provider mock` still passes (no regression)
- `make check` passes

---

## Milestone C: Gemini Deep Research Provider — Basic Implementation

**Goal**: Implement the Gemini Deep Research provider via the Interactions API.

**Status**: Not started (no `GeminiProvider` class exists)

**Technical Notes** (from references.md and PRD v24):
- Agent: `deep-research-pro-preview-12-2025`
- API: `https://generativelanguage.googleapis.com/v1beta/interactions`
- Auth: `x-goog-api-key` header (NOT Bearer token)
- All requests require `background=True`; poll for completion

### Test Plan (MC-T01 to MC-T10) — Write Tests First

- [ ] **MC-T01**: `GeminiProvider.submit()` returns a non-empty string
- [ ] **MC-T02**: Response saved to file with `gemini` in the filename
- [ ] **MC-T03**: Invalid API key shows a helpful error (not a traceback)
- [ ] **MC-T04**: Network timeout handled gracefully
- [ ] **MC-T05**: `--provider gemini` flag selects Gemini provider
- [ ] **MC-T06**: Provider registered in `ProviderRegistry`
- [ ] **MC-T07**: `thoth providers -- --models` lists Gemini models
- [ ] **MC-T08**: Polling loop transitions from `in_progress` to `completed`
- [ ] **MC-T09**: Citations extracted from response and appended to output
- [ ] **MC-T10**: Metadata header included in output file

### Implementation Tasks

- [ ] **MC-01**: Create `GeminiProvider` class extending `ResearchProvider`
  (add after `PerplexityProvider` in Section 12)
- [ ] **MC-02**: Implement `__init__`: store `api_key`, build `httpx.AsyncClient`
  with `x-goog-api-key` header
- [ ] **MC-03**: Implement `submit()`: POST to Interactions API with
  `background=True`, poll until `status == "completed"` or `"failed"`
- [ ] **MC-04**: Implement result parsing: extract text content and citations
- [ ] **MC-05**: Add error handling for auth errors (401), quota exceeded (429),
  and network failures
- [ ] **MC-06**: Register `"gemini": GeminiProvider` in `ProviderRegistry`
- [ ] **MC-07**: Add `GEMINI_API_KEY` to config defaults
- [ ] **MC-08**: Add `gemini` to mode provider options and `deep_research` mode

### Acceptance Criteria

- `./thoth_test -r --provider mock` still passes (no regression)
- Gemini tests pass with a valid `GEMINI_API_KEY`
- `make check` passes

---

## Milestone D: Update and Clean Commands

**Goal**: Implement `thoth update` and `thoth clean` commands (Milestones 23 and 24
from plan v5, consolidated).

**Status**: Not started

### Test Plan (MD-T01 to MD-T10) — Write Tests First

- [ ] **MD-T01**: `thoth update` detects stale queued operations and marks them failed
- [ ] **MD-T02**: `thoth update --dry-run` shows changes without applying
- [ ] **MD-T03**: `thoth clean --completed` deletes completed checkpoints
- [ ] **MD-T04**: `thoth clean --failed` deletes failed checkpoints
- [ ] **MD-T05**: `thoth clean --days 7` deletes checkpoints older than 7 days
- [ ] **MD-T06**: `thoth clean --dry-run` shows what would be deleted
- [ ] **MD-T07**: `thoth clean` prompts for confirmation before deletion
- [ ] **MD-T08**: `thoth clean` with `--force` skips confirmation
- [ ] **MD-T09**: `thoth list --completed` shows only completed operations
- [ ] **MD-T10**: `thoth list --failed` shows only failed operations

### Implementation Tasks

- [ ] **MD-01**: Add `update` command to CLI
- [ ] **MD-02**: Implement stale detection: queued/running operations older than
  their timeout are marked as failed
- [ ] **MD-03**: Add `--dry-run` to `update` command
- [ ] **MD-04**: Add `clean` command to CLI with `--completed`, `--failed`,
  `--in-progress`, `--days N` filters
- [ ] **MD-05**: Implement `--dry-run` for `clean`
- [ ] **MD-06**: Add confirmation prompt with deletion summary (bypass with `--force`)
- [ ] **MD-07**: Add `--completed`, `--failed`, `--in-progress`, `--days` filters
  to `list` command

---

## Milestone E: Fix Remaining Test Failures

**Goal**: Get to 100% pass rate on all non-API-key-dependent tests.

**Status**: Not started

**Known failures from current test run**:
- `M8T-10`: Timeout error message pattern not matching
- `INT-06`: Exit code 127 (command not found — investigate pexpect env PATH)

### Test Plan

- [ ] **ME-T01**: `./thoth_test -r --provider mock` passes 100% of mock tests
- [ ] **ME-T02**: `./thoth_test -r` (provider-agnostic) passes 100% of agnostic tests

### Implementation Tasks

- [ ] **ME-01**: Fix `M8T-10`: update timeout error message to match test pattern
  `Request timed out|Timeout|Connection error`
- [ ] **ME-02**: Investigate and fix `INT-06` exit code 127 (likely PATH issue
  in pexpect spawn environment)
- [ ] **ME-03**: Fix any other test failures discovered after Milestone A

---

## Updated Priority Order

| Priority | Milestone | Reason |
|----------|-----------|--------|
| 1 | **Milestone A** | Fixes 16 failing INT tests; interactive mode is broken |
| 2 | **Milestone E** | Clean up remaining non-interactive test failures |
| 3 | **Milestone B** | Perplexity provider (skeleton exists, easy win) |
| 4 | **Milestone C** | Gemini provider (new capability, high value) |
| 5 | **Milestone D** | Clean/update commands (operational utility) |

---

## Milestone Status Summary (from Plan v5)

| Milestone | Description | Status |
|-----------|-------------|--------|
| M1 | Core CLI Foundation | ✅ Complete |
| M2 | Configuration System | ✅ Complete |
| M3 | Provider Architecture | ✅ Complete |
| M4 | Mode System | ✅ Complete |
| M5 | Async Operations | ✅ Complete |
| M6 | Output Management | ✅ Complete |
| M7 | Progress and UX | 🔶 Partial (quiet mode, first-run flow missing) |
| M8 | OpenAI Basic | ✅ Complete |
| M9 | OpenAI Advanced | 🔶 Partial (retry done; streaming/caching missing) |
| M10 | OpenAI Async | ❌ Not started |
| M11 | Perplexity Basic | ❌ Not started (NotImplementedError) |
| M12 | Perplexity Advanced | ❌ Not started |
| M13 | Perplexity Async | ❌ Not started |
| M14 | Multi-Provider Coordination | ❌ Not started |
| M15-M18 | Commands & Config | ❌ Not started |
| M22-M26 | Update/Clean/List | ❌ Not started |
| M27 | Provider Discovery | ❌ Not started |
| M34-M36 | Gemini Provider | ❌ Not started |
| **A** | **Fix Interactive Crash** | ❌ **CRITICAL — Do first** |

---

## Version History

- **v1.0** – v4.0: Initial plan iterations
- **v5.0**: Added Gemini milestones (M34-M36); provider discovery (M27)
- **v6.0**: Identified interactive mode crash (TextArea.height bug); added
  Milestones A (fix crash), B (Perplexity), C (Gemini), D (clean/update),
  E (remaining test failures); updated all milestone statuses to reflect
  March 2026 state
