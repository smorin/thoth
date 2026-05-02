# P23 - Perplexity - Immediate (Synchronous) Calls

**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)
- **Predecessor:** P22 (`projects/P22-openai-immediate-sync.md`) - validated the current OpenAI immediate path and streaming executor.
- **Adjacent:** P25 (`projects/P25-arch-review-immediate-providers.md`) - cross-immediate-provider review after P23/P24 ship.
- **Adjacent:** P27 (`projects/P27-perplexity-background-deep-research.md`) - owns Perplexity async/background deep research.
- **Follow-up:** P38 (`projects/P38-perplexity-sync-vcr-replay.md`) - owns Perplexity sync VCR replay; P23 does not depend on it.
- **Code:** `src/thoth/providers/openai.py`, `src/thoth/providers/base.py`, `src/thoth/run.py`, `src/thoth/providers/__init__.py`, `src/thoth/config.py`, `src/thoth/errors.py`.
- **Research:** `research/perplexity-deep-research-api.v1.md` - useful background, but not canonical when it disagrees with current official Perplexity docs.
- **External:** https://docs.perplexity.ai/docs/sonar/openai-compatibility
- **External:** https://docs.perplexity.ai/api-reference/sonar-post
- **External:** https://docs.perplexity.ai/docs/sonar/pro-search/stream-mode

**Status:** `[ ]` Scoped, not started.

**Goal**: Implement Perplexity synchronous Sonar support for immediate Thoth runs using the OpenAI Python SDK compatibility path. P23 adds Perplexity built-in immediate modes, request construction, streaming, non-stream execution, side-channel output handling, live coverage, and user-facing provider surfaces.

### Scope

- Implement `PerplexityProvider` with `AsyncOpenAI(api_key=..., base_url="https://api.perplexity.ai")` and `client.chat.completions.create(...)`. Perplexity accepts `/chat/completions` as an OpenAI SDK compatibility alias for the canonical `/v1/sonar` endpoint.
- Supported synchronous models in built-ins: `sonar`, `sonar-pro`, `sonar-reasoning-pro`. `PerplexityProvider` defaults to `sonar` only when no effective mode or CLI model is present.
- Add `--model MODEL` to the shared research CLI surface. Model strings are passed through to the selected provider without local provider/model compatibility validation, except for the known immediate-vs-background guard below. Invalid provider/model combinations should surface provider/API errors.
- Existing mode model values remain pass-through. Example: `thoth ask "hi" --provider perplexity` with the default OpenAI-owned mode may pass the default OpenAI model to Perplexity and fail; users can choose `--mode perplexity_quick` or `--model sonar`.
- Add built-in modes in `src/thoth/config.py:BUILTIN_MODES`, all `kind: "immediate"`:
  - `perplexity_quick`: `provider = "perplexity"`, `model = "sonar"`, `perplexity.web_search_options.search_context_size = "low"`, `perplexity.stream_mode = "full"`.
  - `perplexity_pro`: `provider = "perplexity"`, `model = "sonar-pro"`, `perplexity.web_search_options.search_context_size = "high"`, `perplexity.stream_mode = "full"`.
  - `perplexity_reasoning`: `provider = "perplexity"`, `model = "sonar-reasoning-pro"`, `perplexity.web_search_options.search_context_size = "medium"`, `perplexity.stream_mode = "concise"`.
- If no Perplexity-specific `web_search_options.search_context_size` is configured, default to `"medium"`.
- If no Perplexity-specific `stream_mode` is configured, default to `"concise"`.
- Use provider-specific request configuration namespaces. Perplexity request-only keys live under a nested `perplexity` mode config namespace and are passed through to `extra_body`.

Example advanced mode:

```toml
[modes.perplexity_academic]
provider = "perplexity"
model = "sonar-pro"
kind = "immediate"
system_prompt = "Answer with source-grounded academic context."

[modes.perplexity_academic.perplexity]
search_mode = "academic"
return_images = true
web_search_options = { search_context_size = "high" }
```

- Direct OpenAI-compatible chat kwargs: `model`, `messages`, `max_tokens`, `stream`, `stop`, `response_format` (`text` / `json_schema`), `temperature`, `top_p`.
- Perplexity-specific `extra_body` kwargs: every key in the nested `perplexity` namespace, including `stream_mode`, `web_search_options`, `search_recency_filter`, `search_domain_filter`, `return_related_questions`, and future documented keys. Do not local-validate every provider/model/key combination.
- `system_prompt` becomes a Perplexity chat-completions system message, followed by the user prompt as a user message.
- `stream()` translates Perplexity SDK stream chunks into `StreamEvent`:
  - `delta.content` -> `StreamEvent("text", delta)`.
  - `<think>...</think>` content on `sonar-reasoning-pro` -> `StreamEvent("reasoning", text)` and stripped from final answer text.
  - Final `search_results` / citation metadata -> `StreamEvent("citation", "title|url")`, deduplicated by URL by the executor.
  - End of stream -> `StreamEvent("done", "")`.
- `_execute_immediate` must handle all supported `StreamEvent` kinds. It writes final rendered answer, reasoning, and sources to every selected sink (`stdout`, file, tee) and to persisted project output.
- Explicit `stream = false` skips `provider.stream()` before any stream request starts and uses `submit()` / `check_status()` / `get_result()`.
- Real stream errors are failures. Do not retry/fallback to non-stream after a stream request has started.
- Non-stream `submit()` performs one-shot synchronous chat completion. `check_status()` returns completed immediately. `get_result()` extracts answer text and appends deduped `## Sources`.
- Known background-only guard: P23 must not implement or call Perplexity async/deep-research endpoints and must not add `sonar-deep-research` as a supported immediate model. P23 may recognize `sonar-deep-research` only to reject immediate-kind usage before any HTTP call with the existing generic `ModeKindMismatchError` suggestion. P27 owns background submission/polling.
- Error mapping uses OpenAI SDK exception classes because P23 uses the OpenAI SDK compatibility path. Map `openai.AuthenticationError`, `openai.RateLimitError`, `openai.BadRequestError`, `openai.PermissionDeniedError`, `openai.InternalServerError`, `openai.APITimeoutError`, `openai.APIConnectionError`, and `openai.APIError` to Thoth errors under provider name `"perplexity"`.
- Retry policy for non-stream `submit()` mirrors OpenAI precedent: tenacity `stop_after_attempt(3)`, `wait_exponential(multiplier=1, min=4, max=10)`, retrying `openai.APITimeoutError` and `openai.APIConnectionError` only. Streaming failures are mapped but not retried after start.
- Update all user-facing provider surfaces that currently say Perplexity is not implemented: provider list/model output, interactive provider menus, provider status/docstrings, README/docs, and tests/specs that assert the old text.

### Out of scope

- Perplexity async/background API endpoints (`/v1/async/sonar`) and polling - P27.
- Implementing `sonar-deep-research` - P27. P23 only rejects it on immediate paths.
- Pro Search behavior (`web_search_options.search_type = "pro"`) beyond passthrough. P23 does not enforce Pro Search combinations.
- VCR replay coverage - P38. P23 does not block on P38.
- Provider implementation refactor - P25.

### Resolved Design Decisions

- `--model` is added and model strings pass through without provider/model validation.
- Provider-specific request keys are namespaced under the provider (`perplexity`) and passed to `extra_body`.
- Built-in modes use explicit `search_context_size`; fallback is `"medium"`.
- Built-in modes use explicit `stream_mode`; fallback is `"concise"`.
- `_execute_immediate` renders `reasoning` and `citation` side-channel events.
- `stream = false` is an explicit pre-request non-stream opt-out.
- Use OpenAI SDK exception classes for Perplexity error mapping and retry.
- Keep the known `sonar-deep-research` immediate guard, but use the generic `ModeKindMismatchError` suggestion.
- Add Perplexity to both `extended` model-kind/runtime tests and weekly `live_api` workflow tests.
- Move Perplexity sync VCR replay to P38; P23 has no P38 dependency.

### Tests & Tasks

- [x] [P23-TS01] Add failing CLI/model-resolution tests for `--model` passthrough. Cover `--provider perplexity --model sonar-pro`, an arbitrary future model string, mode-provided model passthrough, Perplexity provider default `sonar` when no model is configured, and no local provider/model compatibility validation.
      Tests added to `tests/test_provider_config.py` (3 unit tests on `create_provider`) and `tests/test_cli_option_policy.py` (3 CLI integration tests, incl. mutual-exclusion with `--pick-model` per design choice C). All 6 fail; T01 turns them green.
- [x] [P23-T01] Implement `--model` in the shared research option surface and thread it through `cli.py`, `cli_subcommands/ask.py`, `run.py`, and `create_provider()`. Make P23-TS01 pass.
      Added `--model` to `_options.py` shared stack; threaded through root `cli.py` (callback signature, ctx.obj, fallback parser, mutex check before `pick_model`), through both `_run_research_default` callsites in `ask.py` (live + JSON path), through `create_provider` (gate extended openai→perplexity), and flipped `PerplexityProvider` default to `sonar`. All 6 TS01 tests green; 50 tests in neighboring suites still pass.

- [ ] [P23-TS02] Add failing built-in mode and request-construction tests. Mock `AsyncOpenAI.chat.completions.create` and assert exact `messages`, direct SDK kwargs, `extra_body`, Perplexity namespace passthrough, explicit built-in `search_context_size` / `stream_mode`, fallback `search_context_size = "medium"`, fallback `stream_mode = "concise"`, and `system_prompt` as a system message.
- [ ] [P23-T02] Add the three built-in Perplexity modes and implement Perplexity request construction. Make P23-TS02 pass.

- [ ] [P23-TS03] Add failing `_map_perplexity_error` and retry tests using OpenAI SDK exception objects. Cover auth, quota/rate limit, bad request/model hints, permission denied, 5xx, timeout, connection error, generic SDK errors, raw unknown exceptions, and non-stream retry count for timeout/connection failures.
- [ ] [P23-T03] Implement `_map_perplexity_error(...)` and non-stream retry policy. Make P23-TS03 pass.

- [ ] [P23-TS04] Add failing provider stream tests for Perplexity chunk translation. Cover text deltas, cumulative-content guard, final `search_results`/citations, terminal `done`, `<think>` extraction, missing `<think>` tolerance, `stream_mode = "full"`, and `stream_mode = "concise"`.
- [ ] [P23-T04] Implement `PerplexityProvider.stream()`. Make P23-TS04 pass.

- [ ] [P23-TS05] Add failing executor/sink tests for side-channel stream events. Use a fake provider emitting `text`, `reasoning`, `citation`, and `done`; assert stdout, file-only, tee, and project-persisted output all contain the same rendered answer, reasoning section, and `## Sources` section.
- [ ] [P23-T05] Update `_execute_immediate` to collect/render `reasoning` and `citation` events and write them to all sinks and persisted output. Make P23-TS05 pass.

- [ ] [P23-TS06] Add failing non-stream opt-out tests. Cover `stream = false` skipping `provider.stream()` entirely, calling `submit()` / `check_status()` / `get_result()`, appending sources, and preserving current behavior where `NotImplementedError` from `stream()` falls back but other stream errors fail.
- [ ] [P23-T06] Implement explicit `stream = false` handling and Perplexity `submit()` / `check_status()` / `get_result()` one-shot behavior. Make P23-TS06 pass.

- [ ] [P23-TS07] Add failing kind-mismatch tests for `sonar-deep-research` with `kind = "immediate"`. Assert `ModeKindMismatchError` fires before any HTTP call and uses the existing generic config-edit suggestion.
- [ ] [P23-T07] Implement Perplexity kind-mismatch guard. Make P23-TS07 pass.

- [ ] [P23-TS08] Add failing provider-registry, model-listing, and user-facing surface tests. Cover `PerplexityProvider.is_implemented()`, default model `sonar`, supported sync model list, provider list output without "(not implemented)", interactive provider menus, README/docs text, and any legacy tests/spec assertions that freeze old not-implemented copy.
- [ ] [P23-T08] Flip Perplexity implementation status and update user-facing provider surfaces. Make P23-TS08 pass.

- [ ] [P23-TS09] Add failing live/extended coverage. Add Perplexity immediate models to `KNOWN_MODELS`, remove or narrow the current Perplexity skip in `tests/extended/test_model_kind_runtime.py`, add `tests/extended/test_perplexity_real_workflows.py` under `@pytest.mark.live_api` for end-to-end `--api-key-perplexity`, `--provider perplexity --model sonar`, `--mode perplexity_quick`, and tee `--out -,FILE`, and assert the CI workflow exposes `PERPLEXITY_API_KEY` to the gated collections.
- [ ] [P23-T09] Implement the extended and weekly live-api Perplexity test coverage. Update `.github/workflows/extended.yml` and `.github/workflows/live-api.yml` to pass `PERPLEXITY_API_KEY: ${{ secrets.PERPLEXITY_API_KEY }}` alongside `OPENAI_API_KEY`. Make P23-TS09 pass.

- [ ] [P23-T10] Final verification and project closeout. Run targeted pytest for new/changed tests, `just check`, `./thoth_test -r`, `just test-lint`, `just test-typecheck`, and the Perplexity live-api command when `PERPLEXITY_API_KEY` is available. Flip P23 to `[x]` only after the full gate passes.

### Acceptance Criteria

- `thoth ask "What's new in CRISPR?" --mode perplexity_quick` returns a grounded answer with a `## Sources` section using `sonar`.
- `thoth ask "What's new in CRISPR?" --provider perplexity --model sonar` returns a grounded answer with a `## Sources` section.
- `thoth ask "hello" --provider perplexity --model future-model-id` passes the model string to Perplexity without local compatibility validation; any invalid model error is surfaced from the provider/API layer.
- `thoth ask --mode perplexity_reasoning ...` exposes reasoning separately from answer text and strips `<think>...</think>` from the answer when present.
- `thoth ask --provider perplexity --model sonar-deep-research ...` with immediate kind raises `ModeKindMismatchError` before any HTTP call, with the existing generic suggestion.
- `stream = false` in Perplexity mode config uses non-stream one-shot execution and still appends sources.
- stdout, file-only, tee, and project output contain the same final rendered answer/reasoning/sources for side-channel stream events.
- `--api-key-perplexity sk-...` works without `PERPLEXITY_API_KEY` in env; the key never appears in stdout/stderr/logs.
- Perplexity is surfaced as implemented in provider listings, model listings, interactive provider menus, and docs.
- Unit/provider/registry tests pass, and Perplexity is covered in both extended model-kind tests and weekly live-api workflow tests.

### Dependencies

- P23 does not depend on P38 or `deepresearch_replay` P03. VCR replay is tracked in P38.
- Live Perplexity tests require `PERPLEXITY_API_KEY`, CI must pass it from repo secrets into `extended` and `live_api` jobs, and the tests remain gated out of default pytest by markers.

### Definition of Done

- All P23 `TS##` and `T##` checkboxes are flipped.
- `is_implemented()` returns `True`; registry tests assert it.
- `tests/test_provider_perplexity.py`, provider registry tests, executor/sink tests, and relevant CLI option tests pass.
- `extended` collection includes Perplexity immediate models, the CI workflow passes `PERPLEXITY_API_KEY`, and tests skip only when that key is absent.
- `live_api` collection includes Perplexity workflow tests, the CI workflow passes `PERPLEXITY_API_KEY`, and tests skip only when that key is absent.
- Full local quality gate passes per `CLAUDE.md` / `AGENTS.md`.
- Trunk row flips to `[x]` only after the full gate passes.
