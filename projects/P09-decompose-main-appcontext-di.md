# P09 — Decompose __main__.py + AppContext DI + Provider Registry (v2.9.0)

**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)

**Status:** `[x]` Completed (v2.9.0).

**Goal**: Split the ~5000-line src/doxa_research/__main__.py into a package of focused modules (errors, config, models, providers/*, checkpoint, output, signals, run, cli, interactive, help, commands), replace module-level singletons with an injected `AppContext` dataclass, and collapse the two provider factories (`ProviderRegistry.create` + `create_provider`) into a single `PROVIDERS` dict lookup. Behavior-preserving physical relocation; no new features.

**Out of Scope**
- Renaming any public symbols (OpenAIProvider, OperationStatus, _execute_research, etc. keep their names)
- Changing the public import path used by tests/doxa_test (both continue to import from `doxa-research.__main__`)
- Changing click CLI commands/options/help text
- CHANGELOG/docs rewrites (track under P08-T12)
- Further decomposing InteractiveSession (~800 lines) — flagged for follow-up
- Decorator-based provider auto-registration — literal dict only

### Tests & Tasks
Phase 1 — Foundations (pure extraction, no DI yet)
- [x] [P09-TS01] tests/test_imports.py: `from doxa-research.__main__ import X` still works for all 40+ symbols currently used by tests/doxa_test
- [x] [P09-T01] Extract src/doxa_research/errors.py (DoxaError, APIKeyError, APIQuotaError, ProviderError, DiskSpaceError, handle_error)
- [x] [P09-T02] Extract src/doxa_research/utils.py (generate_operation_id, sanitize_slug, mask_api_key, check_disk_space, _is_placeholder)
- [x] [P09-T03] Extract src/doxa_research/models.py (InputMode, OperationStatus, InteractiveInitialSettings, ModelCache)
- [x] [P09-T04] Extract src/doxa_research/config.py (ConfigSchema, ConfigManager, get_config, _config_path, DOXA_VERSION, CONFIG_VERSION, BUILTIN_MODES)
- [x] [P09-T05] Add re-export shim to src/doxa_research/__main__.py for extracted symbols; run full test + doxa_test suite GREEN

Phase 2 — Signals + I/O managers
- [x] [P09-TS02] tests/test_sigint_handler.py still green after signals moved to doxa-research.signals
- [x] [P09-T06] Extract src/doxa_research/signals.py (_interrupt_event, _last_interrupt_at, _INTERRUPT_FORCE_EXIT_WINDOW_S, _raise_if_interrupted, handle_sigint)
- [x] [P09-T07] Extract src/doxa_research/checkpoint.py (CheckpointManager)
- [x] [P09-T08] Extract src/doxa_research/output.py (OutputManager; atomic-write logic preserved verbatim)
- [x] [P09-T09] Update __main__.py shim; full suite GREEN

Phase 3 — Providers package + R02 registry
- [x] [P09-TS03] tests/test_openai_errors.py still green after _map_openai_error moves to doxa-research.providers.openai
- [x] [P09-TS04] tests/test_api_key_resolver.py still green after resolve_api_key moves to doxa-research.providers
- [x] [P09-TS05] tests/test_vcr_openai.py still green (VCR cassette replays)
- [x] [P09-TS06] tests/test_provider_registry.py (NEW): create_provider("mock") returns MockProvider; create_provider("bogus") raises ValueError; PROVIDERS dict contains {openai, perplexity, mock}
- [x] [P09-T10] Create src/doxa_research/providers/base.py (ResearchProvider Protocol)
- [x] [P09-T11] Extract src/doxa_research/providers/mock.py (MockProvider)
- [x] [P09-T12] Extract src/doxa_research/providers/openai.py (OpenAIProvider, _map_openai_error)
- [x] [P09-T13] Extract src/doxa_research/providers/perplexity.py (PerplexityProvider)
- [x] [P09-T14] Create src/doxa_research/providers/__init__.py with PROVIDERS dict, PROVIDER_ENV_VARS, resolve_api_key, create_provider
- [x] [P09-T15] Delete ProviderRegistry class — only caller was the old create_provider itself
- [x] [P09-T16] Update __main__.py shim; full suite GREEN

Phase 4 — Run loop + commands + help + CLI + interactive
- [x] [P09-TS07] doxa_test (black-box) full run still matches P06 baseline + P08 additions
- [x] [P09-T17] Extract src/doxa_research/run.py (find_latest_outputs, get_estimated_duration, run_research, _run_polling_loop, _execute_research, resume_operation)
- [x] [P09-T18] Extract src/doxa_research/commands.py (CommandHandler, status_command, list_command, show_status, list_operations, providers_command)
- [x] [P09-T19] Extract src/doxa_research/help.py (DoxaCommand, build_epilog, show_*_help)
- [x] [P09-T20] Extract src/doxa_research/interactive.py (SlashCommandRegistry, SlashCommandCompleter, ClarificationSession, InteractiveSession, enter_interactive_mode)
- [x] [P09-T21] Extract src/doxa_research/cli.py (click cli(), main())
- [x] [P09-T22] Reduce __main__.py to the re-export shim + `if __name__ == "__main__": main()`
- [x] [P09-T23] Verify `doxa-research = "doxa-research.__main__:main"` entry point still executes `doxa-research --help` successfully

Phase 5 — R12 AppContext wiring
- [x] [P09-TS08] tests/test_app_context.py (NEW): AppContext instance constructible; defaults sane; verbose propagates
- [x] [P09-T24] Create src/doxa_research/context.py with AppContext dataclass
- [x] [P09-T25] Thread `ctx: AppContext` parameter through run_research → _execute_research → _run_polling_loop signatures
- [x] [P09-T26] Replace reads of module-level `console` with `ctx.console` inside run/commands/interactive modules
- [x] [P09-T27] Replace reads of `_current_checkpoint_manager` / `_current_operation` with `ctx.checkpoint_manager` / `ctx.current_operation`
- [x] [P09-T28] In cli.main(), construct AppContext once and pass to all async entry points
- [x] [P09-T29] Keep signals module-globals (`_interrupt_event` etc.) aliased to `ctx.interrupt_event` for test back-compat
- [x] [P09-T30] Full suite GREEN

Phase 6 — Cleanup
- [x] [P09-T31] Remove unused imports from each new module (ruff)
- [x] [P09-T32] Ensure `just check` passes (ruff + ty) on entire src/doxa_research/ tree
- [x] [P09-T33] Ensure `just test-fix && just test-lint && just test-typecheck` all pass
- [x] [P09-T34] Update PROJECTS.md task states

### Regression Test Status
- [x] tests/ full pytest suite: 55 tests green (new test_imports, test_provider_registry, test_app_context added)
- [x] doxa_test full run: 115 passed / 11 skipped / 0 failed — no regressions
- [x] `doxa-research --help` exit 0
- [x] Manual smoke: `MOCK_API_KEY=test uv run doxa-research --provider mock "hello phase5"` completes end-to-end
