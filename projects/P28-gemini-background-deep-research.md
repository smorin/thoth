# P28 — Gemini — Background Deep Research

**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)
- **Predecessor (immediate-vs-background design):** P18 — `docs/superpowers/specs/2026-04-26-p18-immediate-vs-background-design.md`, `docs/superpowers/plans/2026-04-26-p18-immediate-vs-background.md`. Defines the `kind` field, `ModeKindMismatchError`, and the immediate-vs-background runtime split P28 inherits.
- **Adjacent (predecessor, completed):** [P26 — OpenAI Background Deep Research](P26-openai-background-deep-research.md). Canonical background-provider surface in `src/doxa_research/providers/openai.py`. P28 mirrors `submit/check_status/get_result/cancel/reconnect/list_models` and the 12-branch shape of `_map_openai_error`.
- **Adjacent (predecessor, completed):** [P27 — Perplexity Background Deep Research](P27-perplexity-background-deep-research.md). Second-mover conventions in `src/doxa_research/providers/perplexity.py`: module-level `_PROVIDER_NAME` constant; shared `_invalid_key_doxaerror(provider, settings_url)` helper; sync/async error-mapper split (`_map_perplexity_error` + `_map_perplexity_error_async`); `_validate_kind_for_model()` method; async-internal helper layout (`_submit_async`, `_poll_async_job`, `_get_async_result`). P28 adopts the P27 conventions where applicable — the sync/async error-mapper split collapses to just the async form because the Gemini Interactions API is async-only via `client.aio.interactions.*`.
- **Adjacent (validated cross-provider survey):** [P22 — OpenAI Immediate (Synchronous) Calls](P22-openai-immediate-sync.md) §T03/T04. Confirmed `ResearchProvider` base contract is sufficient for new providers; no refactor required before P28 begins.
- **Adjacent (successor cleanup):** [P29 — Architecture Review & Cleanup — Background Deep Research Providers](P29-arch-review-background-deep-research.md). Runs after P26, P27, P28 land; owns cross-provider deduplication.
- **Code (mirror target — provider methods + error mapper):** `src/doxa_research/providers/openai.py` (`submit/check_status/get_result/cancel/reconnect`, `_map_openai_error`); `src/doxa_research/providers/perplexity.py` (same surface, second-mover conventions: `_PROVIDER_NAME`, `_invalid_key_doxaerror`, async-internal helpers).
- **Code (runtime, provider-agnostic):** `src/doxa_research/run.py` (`_run_polling_loop`, `resume_operation`, `_maybe_cancel_upstream_and_raise`).
- **Code (state machine + persistence):** `src/doxa_research/checkpoint.py`, `src/doxa_research/models.py` (`OperationStatus`).
- **Code (SIGINT):** `src/doxa_research/signals.py`.
- **Code (config schema):** `src/doxa_research/config.py` (`KNOWN_MODELS`, `mode_kind`, `is_background_model`).
- **Branch (port-not-merge reference):** `origin/claude/plan-next-tasks-xR2e4` commit `7c9d124`. Frozen reference for Gemini API knowledge (endpoint, headers, payload shape, citation extraction). Written against the pre-package monolithic `doxa-research` script; do not rebase. Use as a wire-shape cross-check only.
- **Research:** [research/gemini-deep-research-api.v1.md](../research/gemini-deep-research-api.v1.md). Authoritative API reference; sections 1-2 (auth + surface), 5-6 (lifecycle + polling), 10 (known bugs + workarounds) drive implementation.
- **External (SDK package):** https://pypi.org/project/google-genai/ - PyPI page for `google-genai`; P28 minimum is `>=1.55.0`.
- **External (SDK repo):** https://github.com/googleapis/python-genai - repository root; issues / changelog / examples.
- **External (SDK reference):** https://googleapis.github.io/python-genai/ - reference docs for the async client and Interactions surface.
- **External (deep-research announcement):** https://blog.google/innovation-and-ai/models-and-research/gemini-models/next-generation-gemini-deep-research/ - product framing for the `deep-research-preview-04-2026` agent P28 wires up.
- **External (deep-research docs):** https://ai.google.dev/gemini-api/docs/deep-research - authoritative API surface for Gemini Deep Research.
- **External (Interactions API docs):** https://ai.google.dev/gemini-api/docs/interactions - the `client.aio.interactions.{create,get,cancel}` surface P28 calls; companion to the REST endpoint `https://generativelanguage.googleapis.com/v1beta/interactions`.
- **Tests (mirror target):** `tests/test_oai_background.py`, `tests/test_async_checkpoint.py`, `tests/test_resume.py`, `tests/test_vcr_openai.py`, `tests/extended/test_openai_real_workflows.py`, `tests/extended/test_model_kind_runtime.py`.

**Status:** `[~]` In progress — v1 implementation complete pending PR. Plan v2 at `docs/superpowers/plans/2026-05-11-p28-gemini-deep-research-background.md` executed (Tasks 1-16 + collateral fixes for Tasks 10/11). Tasks 6b (incomplete-recoverability spike), 6c (revise mapping per spike), 8a (cancel re-verify spike) deferred to a v1.1 follow-up project; v1 ships with conservative `incomplete` → `permanent_error` mapping and defensive `cancel()` (5xx best-effort).

**Goal**: Add long-running Deep Research operations via Google Gemini, submitted and polled to completion. Mirror the surface and capabilities of the OpenAI background Deep Research path (P26's analog) such that `doxa-research ask --mode <gemini_mode> "query"` and `doxa-research resume <op-id>` work end-to-end with full UX parity. Use the `google-genai>=1.55.0` SDK against the Interactions API (`agent="deep-research-preview-04-2026"`, `background=True`) and integrate cleanly with the existing provider-agnostic runtime (`_run_polling_loop`, `OperationStatus` state machine, `MultiSink` output, `MultiSink`-bypass `OutputManager` save, SIGINT cooperative cancel).

### Scope

In scope — mirror the **eleven categories** of OpenAI's background Deep Research surface, adapted for Gemini's API:

1. **Provider class** — `GeminiProvider` at `src/doxa_research/providers/gemini.py` extending `ResearchProvider`, implementing `submit/check_status/get_result/cancel/reconnect/list_models/list_models_cached`. The `stream()` method is **not** implemented for v1 (background path only); base class default raises `NotImplementedError`, which the runtime tolerates.
2. **Error mapper** — `_map_gemini_error()` translating `google.genai.errors.*` SDK exceptions and HTTP error responses (401/403/429/5xx, plus the doc §10 known bugs) into `DoxaError` / `APIKeyError` / `APIQuotaError` / `ProviderError`. Mirror the 12-branch shape of `_map_openai_error()` in `src/doxa_research/providers/openai.py:35-126`.
3. **Mode set** — Add **9 new background modes** to `KNOWN_MODELS` mirroring OpenAI's set: `gemini_quick_research`, `gemini_exploration`, `gemini_deep_dive`, `gemini_tutorial`, `gemini_solution`, `gemini_prd`, `gemini_tdd`, `gemini_deep_research`, `gemini_comparison`. All declare `provider="gemini"`, `kind="background"`, `model="deep-research-preview-04-2026"`. `system_prompt` and `description` mirror the OpenAI analog (purpose is provider-independent). `previous`/`next` chain links use the matching OpenAI modes where applicable, enabling cross-provider mode chaining (`exploration` → `gemini_deep_dive` → `tutorial`).
4. **Provider registration** — `PROVIDERS["gemini"] = GeminiProvider` and `PROVIDER_ENV_VARS["gemini"] = "GEMINI_API_KEY"` in `src/doxa_research/providers/__init__.py`. `create_provider()` dispatches via the registry dict (no if/elif chain).
5. **CLI flag** — `--api-key-gemini` added to `doxa-research ask` and `doxa-research resume` flag groups (and any other subcommands inheriting the API-key flag set). Mirrors `--api-key-openai` exactly.
6. **Config schema** — Default `[providers.gemini]` block with `api_key="${GEMINI_API_KEY}"` in the config schema. Resolution order matches OpenAI: CLI flag → env var → config file. Empty / `${VAR}` placeholders treated as missing at every tier (per `resolve_api_key()` semantics).
7. **Polling and timeouts** — Use the existing `_run_polling_loop` runtime. Provider-specific tunables in `[providers.gemini]` config:
   - `poll_interval` default **10 seconds** (per doc §6 community guidance; OpenAI uses 30s).
   - `max_wait_minutes` default **20** (per doc §10 stuck-in-progress bug workaround; OpenAI uses 30).
   - Existing per-provider transient error counter (`max_transient_errors`, default 5 in `run.py`) is reused unchanged.
8. **Citation extraction** — Parse `interaction.outputs[-1].annotations[]` for `{url, start_index, end_index}` records. Dedupe by URL. Render under `## Sources` heading using the markdown `- [domain](url)` form (matching OpenAI's pattern from `openai.py:599-606`). Handle empty/missing annotations gracefully — emit no Sources section, never fail the result.
9. **SIGINT cooperative cancel** — `provider.cancel(job_id)` calls `client.aio.interactions.cancel(interaction_id)`. The runtime's existing `_maybe_cancel_upstream_and_raise()` (`run.py:530-585`) handles parallel cancel + 5s timeout + `--cancel-on-interrupt` honoring without modification. Cancellation is a first-class P28 capability (Gemini's Interactions API supports it natively).
10. **Reconnect / resume** — `provider.reconnect(job_id)` calls `client.aio.interactions.get(interaction_id)` to re-attach state after process restart. Mirrors `openai.py:346-353`. `OperationStatus.providers["gemini"]["job_id"]` persists the Interaction ID across runs. Resume flow inherited unchanged from `resume_operation()` in `run.py`.
11. **Test coverage** — Three layers:
    - **Default (always-run):** `tests/test_gem_background.py` (unit tests with monkeypatched `client.aio.interactions.*` covering the 6 provider methods + error mapping), `tests/test_vcr_gemini.py` (cassette replays mirroring `test_vcr_openai.py` shape).
    - **Cassettes:** `doxa_test_cassettes/gemini/happy-path.yaml` recorded once against live API, replayed with dummy key (`gemini-replay-dummy`).
    - **Gated `live_api` (weekly via `.github/workflows/live-api.yml`):** `tests/extended/test_gemini_real_workflows.py` — end-to-end CLI workflows (`doxa-research ask --provider gemini`, resume, cancel) requiring `GEMINI_API_KEY` repo secret.
    - **Gated `extended` (nightly via `.github/workflows/extended.yml`):** the new 9 mode entries in `KNOWN_MODELS` are auto-covered by the existing `tests/extended/test_model_kind_runtime.py` (iterates KNOWN_MODELS to verify declared kind matches runtime behavior).

### Out of scope

| # | Capability | Why deferred |
|---|---|---|
| 1 | Streaming via SSE (`stream=True`) | Polling matches OpenAI background path; doc §10 notes streams die silently mid-execution; client-side accumulation non-trivial. Revisit if/when OpenAI's background path adds streaming. |
| 2 | `file_search` store integration | Doc §4 labels it experimental; known 503 errors >10KB; OpenAI background path has no analog. |
| 3 | Multi-turn / `previous_interaction_id` chaining | `ResearchProvider` interface is single-shot; OpenAI doesn't expose this either. |
| 4 | Multimodal input (images, PDFs, video as input content) | Text-prompt-only matches OpenAI; would expand the cross-provider interface for one provider. |
| 5 | Vertex AI Enterprise surface (`discoveryengine.googleapis.com`) | Separate API, OAuth-based, not on the Gemini Developer API path; doc §11 notes no convergence timeline. |
| 6 | `countTokens` integration | Doc §10: doesn't work with agent-based interactions. Document the limitation; no implementation. |
| 7 | `thinking_summaries` reasoning display | Polling-only; reasoning chunks only arrive over SSE. Defers with #1. |
| 8 | Per-call cost cap / token budget UI | Gemini API has no analog to OpenAI's `max_tool_calls`; the 20-min `max_wait` is the de-facto budget cap. Surface in docs only — no code. |
| 9 | Free-tier interactive upgrade flow | Free tier explicitly lacks Deep Research per doc §8. Map 403 to a useful `DoxaError` message (~5 lines in `_map_gemini_error`) but no full upgrade flow. |
| 10 | Re-implementing P26's surface | P26 owns OpenAI background. P28 only owns Gemini. |

### Conventions to carry forward from P26 + P27

P26 (OpenAI background) and P27 (Perplexity background) both shipped before P28 begins. P28 inherits the conventions both implementations validated, with P27's second-mover refinements taking precedence where they differ from P26's first-mover defaults.

| Convention | Origin | What P28 does |
|---|---|---|
| Module-level `_PROVIDER_NAME = "<name>"` constant | P27 (`perplexity.py:103`) | Add `_PROVIDER_NAME = "gemini"` at module top; use in every `ProviderError(_PROVIDER_NAME, ...)` call instead of string literals. |
| Shared `_invalid_key_doxaerror(provider, settings_url)` helper | P27 (`perplexity.py:143`) | Reuse the existing helper for Gemini's invalid-key path; pass `"gemini"` and `"https://aistudio.google.com/apikey"` as the settings URL (verify URL stability per Open Question #8). |
| Sync + async error-mapper split (`_map_<p>_error` + `_map_<p>_error_async`) | P27 (`perplexity.py:163`, `:246`) | Collapses to a single async-only `_map_gemini_error` because the Gemini Interactions API surface (`client.aio.interactions.*`) is async-only. Document the reason in a module docstring so future cross-provider refactor (P29) understands why Gemini diverges from P27's split. |
| `_validate_kind_for_model(mode)` method on the provider class | P27 (`perplexity.py:431`) | Add the same method to `GeminiProvider`; raise `ModeKindMismatchError` when a `kind="immediate"` mode is dispatched against a Gemini model that only supports `background`. |
| `_rate_limit_error_is_quota(exc)` helper at module top | P26 (`openai.py:49`) + P27 (`perplexity.py:117`) | Replicate for Gemini if the SDK distinguishes 429-quota from 429-rate-limit; otherwise document why a single branch suffices. |
| Async-internal helper layout (`_submit_async`, `_poll_async_job`, `_get_async_result`) | P27 (`perplexity.py:568`, `:724`, `:852`) | Adopt the same internal-helper naming for Gemini's background path. Public `submit/check_status/get_result` are thin wrappers that delegate to the `_*_async` helpers. |
| Provider-specific helpers grouped at module bottom (below the class) | P27 (`perplexity.py:873-979`) | Place Gemini's annotation-parsing + Sources-rendering helpers below `GeminiProvider`, matching the Perplexity layout. Avoids spreading provider-specific logic across the class body. |
| Tenacity `@retry` on `submit()` (3 attempts, exp 4-10s, timeout/conn only) | P26 (`openai.py:182-187`) | Adopted unchanged — both P26 and P27 use the same shape; retry exception filter swaps to `google.genai.errors.APIError` subclasses indicating transient-network states. |

**Open Question (deferred to implementation):** are there P27 conventions that proved problematic in practice and should *not* be carried forward? The P27 follow-up factor-dedup plan (`docs/superpowers/plans/2026-05-03-p27-followup-factor-dedup.md`) lists 5 intentional divergences from the cross-provider walk; review those before committing to the conventions table above.

### Parity matrix

Capability-by-capability mapping of P28 → the existing background Deep Research surface (P26 OpenAI canonical; P27 Perplexity refinements noted inline where relevant). Used at implementation time to verify nothing is forgotten and at review time to confirm symmetry.

| # | Category | OpenAI today (file:line) | P28 plan |
|---|---|---|---|
| 1 | CLI surface (`ask`/`resume`/`status`/`cancel` subcommands) | `src/doxa_research/cli_subcommands/{ask,resume,status,cancel}.py` | Inherit unchanged. Add `--api-key-gemini` flag in `_options.py`. |
| 2 | Mode-config schema (`kind`, `provider`, `model`, `system_prompt`, etc.) | `src/doxa_research/config.py:53-163` `KNOWN_MODELS` | Add 9 `gemini_*` mode entries with same fields; no schema change. |
| 3 | Provider methods (`submit/check_status/get_result/cancel/reconnect/list_models`) | `src/doxa_research/providers/openai.py:166-688` | New `src/doxa_research/providers/gemini.py` with same 6 methods. `stream()` not implemented (background-only). |
| 4 | Error mapping (12 exception branches → `DoxaError` types) | `src/doxa_research/providers/openai.py:35-126` `_map_openai_error` | New `_map_gemini_error` mapping `google.genai.errors.*` + HTTP codes + doc §10 known bugs. |
| 5 | Polling loop (interval + jitter + timeout + transient retries) | `src/doxa_research/run.py:588-760` `_run_polling_loop` | Inherit unchanged. Provider-specific config: `poll_interval=10s`, `max_wait_minutes=20`. |
| 6 | Checkpoint / `OperationStatus` state machine | `src/doxa_research/checkpoint.py`, `src/doxa_research/models.py:109-146` | Inherit unchanged. Persisted `job_id` is Gemini's `interaction.id`. |
| 7 | SIGINT cooperative cancel | `src/doxa_research/signals.py`, `src/doxa_research/run.py:530-585` | Inherit runtime unchanged. `provider.cancel(job_id)` → `client.aio.interactions.cancel(id)`. |
| 8 | Output sinks / `OutputManager.save_result()` | `src/doxa_research/sinks.py`, `src/doxa_research/run.py:508-527` | Inherit unchanged. Background path always writes via `OutputManager`. |
| 9 | Citation extraction (`annotations` → `## Sources`) | `src/doxa_research/providers/openai.py:517-525,599-606` | New: parse `interaction.outputs[-1].annotations[]`. Dedupe by URL. Same `## Sources` rendering. Empty annotations OK. |
| 10 | Tenacity `@retry` on `submit()` (3 attempts, exp 4-10s, timeout/conn only) | `src/doxa_research/providers/openai.py:182-187` | Same decorator shape; retry on `google.genai.errors.APIError` subclasses indicating timeout/connection. |
| 11 | Test coverage (unit + VCR + extended/live markers) | `tests/test_oai_background.py`, `tests/test_vcr_openai.py`, `tests/extended/test_openai_real_workflows.py`, `tests/extended/test_model_kind_runtime.py` | New analogs: `tests/test_gem_background.py`, `tests/test_vcr_gemini.py`, `tests/extended/test_gemini_real_workflows.py`. Mode-kind drift covered automatically by existing test iterating `KNOWN_MODELS`. |

### Provider-specific deltas vs OpenAI

The places where Gemini's API forces P28 to diverge from a pure mirror — captured here so reviewers can audit each delta against the research doc:

1. **Polling cadence: 10s (vs OpenAI 30s).** Per research doc §6 community guidance.
2. **Polling timeout: 20 min (vs OpenAI 30 min).** Per research doc §10 — Deep Research interactions can stick indefinitely in `in_progress` state with no terminal transition. The 20-min hard timeout is the documented workaround.
3. **403-on-GET-after-POST intermittent quirk** — research doc §10 critical bug. `check_status()` must treat HTTP 403 from `client.interactions.get(id)` as **transient** (return `{"status": "transient_error", ...}`), letting the existing `max_transient_errors=5` counter handle it. Do not silently swallow as the reference branch did.
4. **Server-initiated cancel disambiguation** — Gemini's `status="cancelled"` can come from user action OR server-side capacity rejection (research doc §10 "instant cancel with no output"). `GeminiProvider` must track a local `_cancel_requested[job_id]: bool` flag set immediately before calling `client.cancel()`. On status check, `cancelled` + `_cancel_requested == True` → user-initiated (return `cancelled` status); `cancelled` + `_cancel_requested == False` → server-initiated (return `permanent_error` with explanatory message).
5. **Empty annotations are normal** — research doc §10 confirms the `annotations` array is inconsistently returned even on completed runs. Result text MUST emit successfully even when annotations are empty/absent. The "## Sources" section is conditional on non-empty annotations.
6. **Free-tier rejection** — research doc §8 confirms Deep Research is not available on the free tier. `_map_gemini_error` maps the resulting 403 to `DoxaError("Gemini Deep Research requires a paid tier (Tier 1+); see https://ai.google.dev/pricing")`.
7. **Stored result fragility** — research doc §10 "lost or reverted interaction results" warns completed interactions can revert to `in_progress` with `outputs=None` after completion. The runtime already persists result text to `OutputManager` immediately on completion, so we inherit the right behavior — but document the constraint in `GeminiProvider.get_result()` comments.
8. **No `max_tool_calls` analog** — Gemini Deep Research auto-determines search depth. The mode-config field `max_tool_calls` is ignored when `provider="gemini"`. Document this in the mode-config schema docstring.
9. **No `code_interpreter` analog** — Gemini Deep Research has fixed built-in tools (`google_search`, `url_context`); cannot disable or add code execution. Mode-config `code_interpreter` field is ignored when `provider="gemini"`.
10. **Cost surfacing** — research doc §9 estimates ~$2-3 per standard task, ~$4-6 complex. Surface in `doxa-research providers --models --provider gemini` output and add a one-line README callout. No in-code cap (see Out-of-scope #8).

### Test strategy

Mirror P22's verified test posture for OpenAI, three-layered:

- **Default suite (every CI run, no marker):** Unit tests with monkeypatched SDK client + cassette replays. Validates contract-level behavior: provider method shapes, error mapping, status enum translation, citation extraction, state-machine integration, resume reconnect.
- **`@pytest.mark.live_api` (weekly via `live-api.yml`):** End-to-end CLI workflow tests against live Gemini. Validates: `doxa-research ask --provider gemini` happy path, `doxa-research resume`, `doxa-research cancel`, secret masking on `--api-key-gemini`, file output, error surfacing for invalid keys. Required repo secret: `GEMINI_API_KEY` (Tier 1+ account). Estimated cost: ~$10-20 per run (3-5 happy-path tests at ~$2-4 each).
- **`@pytest.mark.extended` (nightly via `extended.yml`):** Model-kind drift watch. Inherited automatically — the existing `tests/extended/test_model_kind_runtime.py` iterates `KNOWN_MODELS`, so all 9 new `gemini_*` modes are covered. Catches Google deprecating the agent ID or changing the interaction shape.

Both gated workflows already have `continue-on-error: true` (informational, not blocking) per CLAUDE.md.

### Open questions

1. **VCR-vs-`google-genai` transport compatibility.** The OpenAI cassettes work because the SDK uses httpx underneath. `google-genai` *also* uses httpx for REST endpoints (Interactions API is REST), so VCR *should* work — but unverified. Resolution: experiment during cassette-recording step. If VCR cannot intercept specific calls, fall back to monkeypatched SDK for those scenarios (same fallback `tests/test_provider_stream_contract.py` already uses for OpenAI's deferred `stream()` cassette).
2. **`google-genai` version pinning strategy.** Doc requires `>=1.55.0`. Should `pyproject.toml` pin `>=1.55,<2` to insulate against major-version SDK breakage, or accept the looser `>=1.55.0`? Lean toward `>=1.55,<2` — preview-grade APIs change shape across major releases.
3. **Citation prompt-prepend workaround.** Research doc §10 recommends embedding "include inline source URLs" in the prompt as a workaround for empty annotations. Should P28 auto-prepend this to user prompts, or rely solely on annotation parsing and emit no Sources section when annotations are empty? Lean toward not auto-prepending — the user's prompt is sacred; document the workaround in README so users can opt in.
4. **Resume after retention expiry.** Free tier retains interactions for 1 day, paid for 55 days (doc §5). Resume after retention expiry will hit a 404 from `interactions.get(id)`. `_map_gemini_error` should catch this and surface `DoxaError("Gemini interaction expired (retention: 55 days paid / 1 day free); start a new operation")`. Mirror OpenAI's `NotFoundError` handling. Resolution: confirm 404 shape during VCR recording.
5. **`extended` marker scope clarity.** The `extended` workflow currently runs nightly with `OPENAI_API_KEY` repo secret. Adding Gemini coverage requires a `GEMINI_API_KEY` repo secret. Workflow YAML edit is straightforward; need to confirm both secrets live in the `Extended Contract Tests` workflow without auth conflicts.
6. ~~**Single-agent assumption.** Doc §3 confirms `deep-research-pro-preview-12-2025` is the only built-in agent currently.~~ **Resolved 2026-05-12 (corrected — legacy IS still listed):** upstream docs (https://ai.google.dev/gemini-api/docs/deep-research) list a two-tier set — `deep-research-preview-04-2026` (speed/efficiency, "ideal to be streamed back to a client UI") and `deep-research-max-preview-04-2026` (max comprehensiveness, "for automated context gathering and synthesis"). Per Plan v2 Task 1 spike (`research/gemini-dr-api-spike-2026-05-11.md` §1), the legacy `deep-research-pro-preview-12-2025` **IS still listed** by the live API as of 2026-05-12 alongside the two new tiers, contradicting the earlier "no longer appears" assumption. **P28 v1 scope:** ship only the speed-efficiency tier (`deep-research-preview-04-2026`) across all 9 modes; defer max-tier opt-in to a successor project; do not consume the legacy ID. The spike confirmed all three are reachable, so v1 mode-list selection is a scope choice, not a forced one.
7. **Cancel-on-Ctrl-C default.** `--cancel-on-interrupt` defaults to True per CLAUDE.md execution config. Gemini's `cancel()` works on running background interactions; should the default be the same as OpenAI's, or should we be more conservative given the documented "instant-cancel-no-output" server quirk? Lean toward keeping default True — server-initiated cancels are surfaced as `permanent_error` (per delta #4 above), so user-initiated cancel still has a clean path.
8. **Free-tier error message URL stability.** "https://ai.google.dev/pricing" used in the free-tier rejection message. URL stability not audited. Resolution: verify URL during implementation; pin the message if stable, or use a more durable target.

### Tests & Tasks

- [x] [P28-T01] Flesh out requirements for Gemini background deep research.
      Done as part of this refinement: References block populated, Scope/Out-of-scope nailed down, parity matrix vs OpenAI documented, provider-specific deltas captured, test strategy decided, open questions surfaced.
- [x] [P28-TS01] Design tests for Gemini background submission, polling, cassette replay, and live-test gating before implementation.
      Subsumed by plan v2 — monkeypatched-SDK unit tests (TestGeminiDeepResearchSubmit/CheckStatus/GetResult/Cancel/Reconnect/Modes), live-API gated tests (`tests/extended/test_gemini_dr_real_workflows.py`), extended-marker drift auto-coverage via the existing iterator over KNOWN_MODELS.
- [x] [P28-T02] Implement async deep research submission and polling.
      Subsumed by plan v2 Tasks 2-11: `_map_gemini_error` extended for `_interactions` exceptions, router refactor (submit/check_status/get_result), `kind` discriminator, `_deep_research_submit/check_status/get_result/cancel/reconnect`, 9 `gemini_*_research` modes, GeminiConfig DR tunables (forward-compat schema).
- [-] [P28-T03] Add VCR recording/replay coverage for local testing.
      **Decided not to do** — P24's `tests/test_provider_gemini.py` uses `unittest.mock.patch` + `AsyncMock`-based monkeypatching (1157 lines, no VCR). P28 follows the same pattern. VCR remains an option for v1.1+ if happy-path cassette replay becomes desirable.
- [x] [P28-T04] Add live testing capability disabled by default.
      Subsumed by plan v2 Task 15: `tests/extended/test_gemini_dr_real_workflows.py` with `@pytest.mark.live_api`. GEMINI_API_KEY was already wired in `.github/workflows/live-api.yml` (line 41) by P24.

The original 4 high-level tasks are subsumed by **plan v2** at `docs/superpowers/plans/2026-05-11-p28-gemini-deep-research-background.md` — 18 fine-grained tasks (1-18) plus 4 follow-up spike/revise tasks (6a/6b/6c/8a) targeting only what's net-new on top of P24's merged `GeminiProvider`. The original 2026-05-01 plan (scoped before P24 merged) is preserved at `archive/2026-05-01-p28-gemini-background-deep-research.md` for history.

**v1 ship status (2026-05-13):** plan tasks 1-16 complete; 13 (full gate) implicit via pre-commit; 17 (this file + PROJECTS.md flip) in progress; 18 (final + PR) pending. Tasks 6b (incomplete recoverability spike), 6c (revise mapping per spike), 8a (cancel re-verify spike) deferred to a v1.1 follow-up.

### Acceptance Criteria

- `doxa-research ask --mode gemini_deep_research "test query"` submits and polls a Gemini Deep Research interaction end-to-end, writes the result to the project directory.
- `doxa-research resume <op-id>` re-attaches to a Gemini interaction after process restart.
- `doxa-research cancel <op-id>` calls `client.aio.interactions.cancel()` and marks the operation cancelled.
- Ctrl-C during a running Gemini operation cooperatively cancels and writes a resume hint.
- `doxa-research providers --models --provider gemini` lists the available Deep Research agent.
- All 9 `gemini_*` modes appear in `doxa-research modes` and pass the existing `tests/extended/test_model_kind_runtime.py` model-kind drift check.
- VCR cassette replay tests pass with no real API calls.
- Default test suite (`uv run pytest`) green; gated `live_api` and `extended` workflows green when run manually with secrets configured.
- `_map_gemini_error` covers all 8 error classes documented in research doc §10 + standard HTTP error codes.
- Output filenames follow the existing `<timestamp>_<mode>_gemini_<slug>.md` pattern.
- All existing tests continue to pass (no regressions in OpenAI / mock / Perplexity paths).
