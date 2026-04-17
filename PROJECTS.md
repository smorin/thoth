## [x] Project P09: Decompose __main__.py + AppContext DI + Provider Registry (v2.9.0)
**Goal**: Split the ~5000-line src/thoth/__main__.py into a package of focused modules (errors, config, models, providers/*, checkpoint, output, signals, run, cli, interactive, help, commands), replace module-level singletons with an injected `AppContext` dataclass, and collapse the two provider factories (`ProviderRegistry.create` + `create_provider`) into a single `PROVIDERS` dict lookup. Behavior-preserving physical relocation; no new features.

**Out of Scope**
- Renaming any public symbols (OpenAIProvider, OperationStatus, _execute_research, etc. keep their names)
- Changing the public import path used by tests/thoth_test (both continue to import from `thoth.__main__`)
- Changing click CLI commands/options/help text
- CHANGELOG/docs rewrites (track under P08-T12)
- Further decomposing InteractiveSession (~800 lines) — flagged for follow-up
- Decorator-based provider auto-registration — literal dict only

### Tests & Tasks
Phase 1 — Foundations (pure extraction, no DI yet)
- [x] [P09-TS01] tests/test_imports.py: `from thoth.__main__ import X` still works for all 40+ symbols currently used by tests/thoth_test
- [x] [P09-T01] Extract src/thoth/errors.py (ThothError, APIKeyError, APIQuotaError, ProviderError, DiskSpaceError, handle_error)
- [x] [P09-T02] Extract src/thoth/utils.py (generate_operation_id, sanitize_slug, mask_api_key, check_disk_space, _is_placeholder)
- [x] [P09-T03] Extract src/thoth/models.py (InputMode, OperationStatus, InteractiveInitialSettings, ModelCache)
- [x] [P09-T04] Extract src/thoth/config.py (ConfigSchema, ConfigManager, get_config, _config_path, THOTH_VERSION, CONFIG_VERSION, BUILTIN_MODES)
- [x] [P09-T05] Add re-export shim to src/thoth/__main__.py for extracted symbols; run full test + thoth_test suite GREEN

Phase 2 — Signals + I/O managers
- [x] [P09-TS02] tests/test_sigint_handler.py still green after signals moved to thoth.signals
- [x] [P09-T06] Extract src/thoth/signals.py (_interrupt_event, _last_interrupt_at, _INTERRUPT_FORCE_EXIT_WINDOW_S, _raise_if_interrupted, handle_sigint)
- [x] [P09-T07] Extract src/thoth/checkpoint.py (CheckpointManager)
- [x] [P09-T08] Extract src/thoth/output.py (OutputManager; atomic-write logic preserved verbatim)
- [x] [P09-T09] Update __main__.py shim; full suite GREEN

Phase 3 — Providers package + R02 registry
- [x] [P09-TS03] tests/test_openai_errors.py still green after _map_openai_error moves to thoth.providers.openai
- [x] [P09-TS04] tests/test_api_key_resolver.py still green after resolve_api_key moves to thoth.providers
- [x] [P09-TS05] tests/test_vcr_openai.py still green (VCR cassette replays)
- [x] [P09-TS06] tests/test_provider_registry.py (NEW): create_provider("mock") returns MockProvider; create_provider("bogus") raises ValueError; PROVIDERS dict contains {openai, perplexity, mock}
- [x] [P09-T10] Create src/thoth/providers/base.py (ResearchProvider Protocol)
- [x] [P09-T11] Extract src/thoth/providers/mock.py (MockProvider)
- [x] [P09-T12] Extract src/thoth/providers/openai.py (OpenAIProvider, _map_openai_error)
- [x] [P09-T13] Extract src/thoth/providers/perplexity.py (PerplexityProvider)
- [x] [P09-T14] Create src/thoth/providers/__init__.py with PROVIDERS dict, PROVIDER_ENV_VARS, resolve_api_key, create_provider
- [x] [P09-T15] Delete ProviderRegistry class — only caller was the old create_provider itself
- [x] [P09-T16] Update __main__.py shim; full suite GREEN

Phase 4 — Run loop + commands + help + CLI + interactive
- [x] [P09-TS07] thoth_test (black-box) full run still matches P06 baseline + P08 additions
- [x] [P09-T17] Extract src/thoth/run.py (find_latest_outputs, get_estimated_duration, run_research, _run_polling_loop, _execute_research, resume_operation)
- [x] [P09-T18] Extract src/thoth/commands.py (CommandHandler, status_command, list_command, show_status, list_operations, providers_command)
- [x] [P09-T19] Extract src/thoth/help.py (ThothCommand, build_epilog, show_*_help)
- [x] [P09-T20] Extract src/thoth/interactive.py (SlashCommandRegistry, SlashCommandCompleter, ClarificationSession, InteractiveSession, enter_interactive_mode)
- [x] [P09-T21] Extract src/thoth/cli.py (click cli(), main())
- [x] [P09-T22] Reduce __main__.py to the re-export shim + `if __name__ == "__main__": main()`
- [x] [P09-T23] Verify `thoth = "thoth.__main__:main"` entry point still executes `thoth --help` successfully

Phase 5 — R12 AppContext wiring
- [x] [P09-TS08] tests/test_app_context.py (NEW): AppContext instance constructible; defaults sane; verbose propagates
- [x] [P09-T24] Create src/thoth/context.py with AppContext dataclass
- [x] [P09-T25] Thread `ctx: AppContext` parameter through run_research → _execute_research → _run_polling_loop signatures
- [x] [P09-T26] Replace reads of module-level `console` with `ctx.console` inside run/commands/interactive modules
- [x] [P09-T27] Replace reads of `_current_checkpoint_manager` / `_current_operation` with `ctx.checkpoint_manager` / `ctx.current_operation`
- [x] [P09-T28] In cli.main(), construct AppContext once and pass to all async entry points
- [x] [P09-T29] Keep signals module-globals (`_interrupt_event` etc.) aliased to `ctx.interrupt_event` for test back-compat
- [x] [P09-T30] Full suite GREEN

Phase 6 — Cleanup
- [x] [P09-T31] Remove unused imports from each new module (ruff)
- [x] [P09-T32] Ensure `just check` passes (ruff + ty) on entire src/thoth/ tree
- [x] [P09-T33] Ensure `just test-fix && just test-lint && just test-typecheck` all pass
- [x] [P09-T34] Update PROJECTS.md task states

### Regression Test Status
- [x] tests/ full pytest suite: 55 tests green (new test_imports, test_provider_registry, test_app_context added)
- [x] thoth_test full run: 115 passed / 11 skipped / 0 failed — no regressions
- [x] `thoth --help` exit 0
- [x] Manual smoke: `MOCK_API_KEY=test uv run thoth --provider mock "hello phase5"` completes end-to-end

---

## [-] Project P08: Typed Exceptions, Unified API Key Resolution, Drop Legacy Config Shim (v2.8.0)
**Goal**: Replace string-based error discrimination in OpenAIProvider.submit with typed openai SDK exceptions, unify API key resolution precedence (CLI > env > config) via a single resolver, and delete the legacy `Config` shim now that `ConfigManager` is used everywhere.

**Out of Scope**
- Decomposing src/thoth/__main__.py (R01, separate future project)
- Unifying ProviderRegistry.create and create_provider factories (R02, separate future project)
- Reworking get_result / list_models error handling
- Changing APIKeyError's effective exit code at the CLI boundary (click.Abort clobbers it to 1)

### Tests & Tasks
- [x] [P08-TS01] tests/test_config.py: get_config() returns ConfigManager instance
- [x] [P08-T01] Inline ConfigManager construction in get_config; call .load_all_layers()
- [x] [P08-T02] Replace `Config` type annotations with `ConfigManager` at all call sites
- [x] [P08-T03] Delete legacy `Config` class and simplify "handle both" shim in ProviderRegistry.create
- [x] [P08-TS02] tests/test_openai_errors.py: AuthenticationError → APIKeyError("openai")
- [x] [P08-TS03] RateLimitError (no quota body) → ProviderError with rate-limit message
- [x] [P08-TS04] RateLimitError with `insufficient_quota` body → APIQuotaError("openai")
- [x] [P08-TS05] NotFoundError → ProviderError referencing self.model
- [x] [P08-TS06] BadRequestError → ProviderError (including temperature-parameter guidance sub-case)
- [x] [P08-TS07] PermissionDeniedError → ProviderError
- [x] [P08-TS08] InternalServerError → ProviderError
- [x] [P08-TS09] APIConnectionError → ProviderError (non-retryable path)
- [x] [P08-TS10] Unknown Exception subclass → ProviderError fallback (defensive)
- [x] [P08-TS11] openai.APITimeoutError triggers 3 tenacity retries, then maps to ProviderError
- [x] [P08-TS12] VCR happy-path unchanged: _map_openai_error is not invoked during successful submit replay
- [x] [P08-T04] Add module-level `_map_openai_error(exc, model=None, verbose=False) -> ThothError`
- [x] [P08-T05] Rewrite OpenAIProvider.submit exception handling with typed openai.* catches
- [x] [P08-T06] Update tenacity `retry_if_exception_type` to (openai.APITimeoutError, openai.APIConnectionError)
- [x] [P08-T07] Delete the 16-elif string-matching block in submit
- [x] [P08-TS13] tests/test_api_key_resolver.py: CLI arg beats env var
- [x] [P08-TS14] env var beats config dict
- [x] [P08-TS15] Missing key everywhere raises APIKeyError with provider name in message
- [x] [P08-TS16] Unresolved `${VAR}` placeholder treated as missing key, raises APIKeyError
- [x] [P08-TS17] Empty-string CLI flag falls through to env (not treated as "explicit empty")
- [x] [P08-TS18] thoth_test: perplexity with empty PERPLEXITY_API_KEY fails with APIKeyError matching `r"perplexity API key not found"`
- [x] [P08-T08] Add PROVIDER_ENV_VARS constant + resolve_api_key function at module scope
- [x] [P08-T09] Replace mock-branch API-key resolution in create_provider with resolve_api_key call
- [x] [P08-T10] Replace real-provider-branch API-key resolution in create_provider with resolve_api_key call
- [x] [P08-T11] Mirror the update in ProviderRegistry.create for consistency
- [ ] [P08-T12] Update CHANGELOG.md under v2.8.0
- [x] [P08-T13] Update PROJECTS.md (mark tasks complete as each ships)

### Automated Verification
- `make env-check` passes
- `just check` passes (lint + typecheck)
- `uv run pytest tests/` passes (existing + ~17 new tests)
- `./thoth_test -r` passes with no regressions vs. P06 baseline (124 passed, 1 skipped) plus one new perplexity empty-key case

### Regression Test Status
- [ ] tests/test_vcr_openai.py happy-path still passes (7/7)
- [ ] tests/test_sigint_handler.py still passes (uses SimpleNamespace, not Config — should be unaffected)
- [ ] thoth_test MOCK-01, MOCK-02, M2T-01, M2T-08 still pass
- [ ] thoth_test OAI-BG-01..14 still pass (check_status unchanged)

---

## [x] Project P06: Hybrid Transient/Permanent Error Handling with Resumable Recovery (v2.7.0)
**Goal**: Classify provider errors as transient vs permanent, retry transient ones in-place with bounded backoff, and make recoverable failures (and Ctrl-C) resumable via `thoth --resume <id>` by reconnecting to persisted job IDs.

**Out of Scope**
- Checkpoint schema migration (backward-compat handled via `setdefault("failure_type", None)`)
- Perplexity / Gemini providers (still not implemented)
- Decorrelated-jitter backoff (simple exponential backoff is sufficient)

### Tests & Tasks
- [x] [P06-T01] Extend MockProvider with THOTH_MOCK_BEHAVIOR env (flake:N, permanent)
- [x] [P06-T02] Add `OperationStatus.failure_type` + checkpoint serialization
- [x] [P06-T03] Allow failed → running state transition so resume can re-enter
- [x] [P06-T04] Classify errors in `OpenAIProvider.check_status` (transient vs permanent)
- [x] [P06-T05] Add `max_transient_errors` config default
- [x] [P06-T06] Extract `_run_polling_loop` helper shared by run and resume
- [x] [P06-T07] Add retry loop + exponential backoff for transient errors
- [x] [P06-T08] Add `OpenAIProvider.reconnect` + `MockProvider.reconnect`
- [x] [P06-T09] Implement `resume_operation` to rebuild providers and re-enter poll loop
- [x] [P06-T10] Surface "Resume with: thoth --resume <id>" hint on recoverable failure and SIGINT
- [x] [P06-TS01] TR-01: transient errors below threshold retried and job completes
- [x] [P06-TS02] TR-02: transient errors above threshold fail recoverable with resume hint
- [x] [P06-TS03] TR-03: permanent error fails immediately with no resume hint
- [x] [P06-TS04] RES-01: resume recoverable failure reattaches and completes
- [x] [P06-TS05] RES-02: resume refuses permanent failure with exit code 7
- [x] [P06-TS06] RES-03: resume of already-completed operation is a no-op

### Automated Verification
- `make env-check` passes
- `just lint` / `just typecheck` pass
- `just test-lint` / `just test-typecheck` pass
- `./thoth_test -r` → 124 passed, 1 skipped, 0 failed

### Regression Test Status
- [x] OAI-BG-01..08 updated for new `permanent_error` / `transient_error` return values
- [x] Existing BUG-03 jitter/poll-interval fixture tests still pass (share module globals)
- [x] P07 async-mode tests still pass (async path now actually submits to providers)

---

## [x] Project P05: VCR Cassette Replay Tests (v2.6.0)
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
- [x] [P05-T04] Update PROJECTS.md

### Automated Verification
- `make check` passes
- `just test-vcr` → 7/7 pass
- `just all` completes without errors

### Regression Test Status
- [x] All existing thoth_test tests still pass
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
