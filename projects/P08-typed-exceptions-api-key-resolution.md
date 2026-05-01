# P08 — Typed Exceptions, Unified API Key Resolution, Drop Legacy Config Shim (v2.8.0)

**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)

**Status:** `[x]` Completed (v2.8.0).

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
