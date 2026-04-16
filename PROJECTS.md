## [-] Project P05: VCR Cassette Replay Tests (v2.6.0)
**Goal**: Add pytest-based VCR cassette replay tests that exercise OpenAIProvider against recorded API traffic, using Option B (separate pytest test file) from thoth_vcr.md.

**Out of Scope**
- Gemini/Perplexity cassettes (blocked on deepresearch_replay P03/P04)
- Integration into thoth_test runner (Option A rejected)

### Tests & Tasks
- [x] [P05-T01] Add pytest and vcrpy to dev dependencies
- [x] [P05-T02] Create tests/conftest.py with shared VCR configuration
- [x] [P05-TS01] VCR-OAI-SUBMIT: submit() returns response ID from cassette
- [x] [P05-TS02] VCR-OAI-SUBMIT: submit() returns exact cassette ID
- [x] [P05-TS03] VCR-OAI-SUBMIT: submit() stores job info with background=True
- [x] [P05-TS04] VCR-OAI-POLL: first check_status() returns queued/in_progress
- [x] [P05-TS05] VCR-OAI-POLL: polling reaches completed status
- [x] [P05-TS06] VCR-OAI-RESULT: get_result() returns substantial text
- [x] [P05-TS07] VCR-OAI-RESULT: get_result() contains domain-relevant content
- [x] [P05-T03] Add test-vcr justfile recipe and wire into just all
- [-] [P05-T04] Update PROJECTS.md

### Automated Verification
- `make check` passes
- `just test-vcr` → 7/7 pass
- `just all` completes without errors

### Regression Test Status
- [ ] All existing thoth_test tests still pass
- [x] VCR tests run in `record_mode="none"` — no live API calls

---

## [x] Project P03: Fix BUG-03 OpenAI Poll Interval Scheduling (v2.5.1)
**Goal**: Make the background polling loop respect the configured poll cadence, including bounded jitter and sub-second intervals, while keeping the progress countdown aligned with the next real network poll.

**Out of Scope**
- BUG-02 (citation parsing), GAP-01 through GAP-05

### Tests & Tasks
- [x] [P03-TS01] Add virtual-time fixture tests for jittered and sub-second poll intervals
- [x] [P03-T01] Normalize poll interval math so jitter never truncates a 2s cadence into a 1s poll
- [x] [P03-T02] Schedule polling with absolute deadlines instead of a fixed 1s sleep cap
- [x] [P03-T03] Keep the progress countdown aligned with the next scheduled poll
- [x] [P03-TS02] Keep a mock-provider CLI regression for the end-to-end fixed polling loop
- [x] [P03-T04] Update OPENAI-BUGS.md and PROJECTS.md

### Automated Verification
- `make check` passes
- `./thoth_test -r -t BUG03 --skip-interactive` → 3/3 pass
- `./thoth_test -r -t OAI-BG --skip-interactive` → 14/14 pass

### Regression Test Status
- [x] BUG03-01 verifies -10% jitter still polls at 1.8s, not 1.0s
- [x] BUG03-02 verifies a 0.25s poll interval is honored exactly
- [x] BUG03-03 verifies the CLI still completes a mock-provider research run end to end

---

## [x] Project P02: Fix BUG-01 OpenAI Background Status Handling (v2.5.0)
**Goal**: Correctly handle all documented OpenAI Responses API background lifecycle states (`incomplete`, `cancelled`, `queued`, no-status-attr, stale-cache) so the CLI never silently misreports terminal failure states as success.

**Out of Scope**
- BUG-02 (citation parsing), GAP-01 through GAP-05

### Tests & Tasks
- [x] [P02-T01] Add `"fixture"` test_type dispatch + helpers to `thoth_test`
- [x] [P02-TS01] Add OAI-BG-01–08 fixture tests for `check_status()` (queued, failed, incomplete, cancelled, no-status-attr, stale-cache, good-cache, in_progress regression)
- [x] [P02-T02] Fix `check_status()` in `OpenAIProvider` — explicit branches for all 6 API statuses, fixed no-status-attr and stale-cache paths
- [x] [P02-TS02] Add OAI-BG-09–14 polling loop fixture tests (queued no premature exit, failed/cancelled/error propagate, not_found/unknown normalize to error)
- [x] [P02-T03] Fix polling loop in `_execute_research()` — queued keeps polling, terminal failures propagate
- [x] [P02-T04] Update OPENAI-BUGS.md (BUG-01 status → Fixed) and PROJECTS.md

### Automated Verification
- `make check` passes
- `./thoth_test -r -t OAI-BG --skip-interactive` → 14/14 pass
- `./thoth_test -r --provider mock --skip-interactive` → 67 passed, 0 failed

### Regression Test Status
- [x] All 14 OAI-BG fixture tests pass

---

## [x] Project P04: GAP-01 — max_tool_calls safeguard and tool-selection config (v2.6.0)
**Goal**: Expose `max_tool_calls` and `code_interpreter` as optional OpenAI provider config knobs so users can bound cost/latency and disable the code interpreter for prompt types that don't need it. Values must reach the Responses API request payload.

**Out of Scope**
- GAP-02 (file_search / MCP tools), GAP-03 (model aliases), GAP-04 (SDK floor), GAP-05 (fixture gaps)

### Tests & Tasks
- [x] [P04-TS01] Fixture test: `max_tool_calls` set in provider config → value present in request payload
- [x] [P04-TS02] Fixture test: `code_interpreter = false` in provider config → `code_interpreter` absent from tools array
- [x] [P04-TS03] Fixture test: no config keys → request has no `max_tool_calls` key and `code_interpreter` is included by default
- [x] [P04-T01] Read `max_tool_calls` from `self.config` in `OpenAIProvider.submit()` and conditionally add to `request_params`
- [x] [P04-T02] Read `code_interpreter` bool (default `True`) from `self.config` and conditionally include the tool in `tools` list
- [x] [P04-T03] Update OPENAI-BUGS.md (GAP-01 status → Fixed) and PROJECTS.md

### Automated Verification
- `make check` passes
- `./thoth_test -r -t GAP01 --skip-interactive` → 3/3 pass
- `./thoth_test -r --provider mock --skip-interactive` → no regressions

### Regression Test Status
- [x] GAP01-01 verifies max_tool_calls reaches the request payload
- [x] GAP01-02 verifies code_interpreter=False removes the tool
- [x] GAP01-03 verifies default behavior (no max_tool_calls key, code_interpreter included)

---

## [ ] Project P01: Developer Tooling & Automation (v2.6.0)
**Goal**: Add automated dependency updates, changelog generation, version bumping, GitHub contribution templates, snapshot test tooling, security linting, and devcontainer support.

### Tests & Tasks
- [ ] [P01-TS01] Verify `snapshot_report.html` does not appear in `git status` after test run
- [x] [P01-T01] Add `snapshot_report.html` to `.gitignore`
- [ ] [P01-TS02] Verify `make update-snapshots` runs without error
- [x] [P01-T02] Add `update-snapshots` Makefile target
- [ ] [P01-TS03] Validate `.github/dependabot.yml` with `uvx yamllint`
- [x] [P01-T03] Create `.github/dependabot.yml`
- [ ] [P01-TS04] Verify `uvx bandit -r src/thoth/ -ll -q` exits 0
- [x] [P01-T04] Add bandit hook to `lefthook.yml`
- [x] [P01-T05] Create `.github/PULL_REQUEST_TEMPLATE.md`
- [x] [P01-T06] Create `.github/ISSUE_TEMPLATE/bug_report.yml`
- [x] [P01-T07] Create `.github/ISSUE_TEMPLATE/feature_request.yml`
- [ ] [P01-TS05] Verify `make bump TYPE=patch` updates version in `pyproject.toml`
- [x] [P01-T08] Add `[tool.bumpversion]` to `pyproject.toml`
- [x] [P01-T09] Add `bump` Makefile target
- [ ] [P01-TS06] Verify `make changelog` produces valid CHANGELOG.md output
- [x] [P01-T10] Create `cliff.toml`
- [x] [P01-T11] Add `changelog` and `release` Makefile targets
- [x] [P01-T12] Create `.devcontainer/devcontainer.json`

### Deliverable
```bash
make bump TYPE=patch       # bumps version in pyproject.toml, commits, tags
make changelog             # regenerates CHANGELOG.md from git history
make release TYPE=minor    # bump + changelog in one step
make update-snapshots      # regenerate pytest snapshots
```

### Automated Verification
- `make check` passes
- `uvx yamllint .github/dependabot.yml` exits 0
- `uvx bandit -r src/thoth/ -ll -q` exits 0
- `make bump TYPE=patch` increments version in pyproject.toml

### Manual Verification
- Open repo in GitHub Codespaces — devcontainer auto-configures environment
- Create a PR — GitHub shows the PR template checklist
- Open a new issue — GitHub shows structured bug/feature forms
