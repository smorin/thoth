# P27 — Perplexity — Background Deep Research

**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)
- **Predecessor (architecture):** P18 (`projects/P18-immediate-vs-background-kind.md`, `docs/superpowers/specs/2026-04-26-p18-immediate-vs-background-design.md`) — established the kind split, runtime mismatch, and background lifecycle this project inherits.
- **Predecessor (resumability):** P06 (`projects/P06-hybrid-error-handling-resumable.md`) — checkpoint plumbing + transient/permanent error classification.
- **Predecessor (VCR infra):** P05 (`projects/P05-vcr-cassette-replay-tests.md`), `thoth_vcr.md`.
- **Sibling:** P23 (`projects/P23-perplexity-immediate-sync.md`) — Perplexity sync provider for non-deep-research models. P27 must NOT touch `sonar`/`sonar-pro`/`sonar-reasoning-pro`; P23 owns them. P27 must NOT touch the synchronous `/chat/completions` endpoint for `sonar-deep-research` (the doc explicitly warns against sync deep-research due to credit-on-timeout billing).
- **Adjacent:** P26 (`projects/P26-openai-background-deep-research.md`) — OpenAI background sibling (in-progress); same lifecycle shape.
- **Adjacent:** P28 (`projects/P28-gemini-background-deep-research.md`) — Gemini background sibling.
- **Adjacent:** P29 (`projects/P29-arch-review-background-deep-research.md`) — cross-background-provider review reads P26/P27/P28 once they ship.
- **Code (mirror target):** `src/thoth/providers/openai.py` — `submit()` (lines 166–253, with `background=True`), `check_status()` (lines 255–344), `get_result()` (lines 452–608), `reconnect()` (lines 346–353), `cancel()` (lines 355–391); `src/thoth/run.py` `_run_polling_loop` (lines 592–708); `src/thoth/checkpoint.py:CheckpointManager`; `src/thoth/cli_subcommands/cancel.py`, `resume.py`.
- **Errors:** `src/thoth/errors.py` — `APIKeyError`, `APIQuotaError`, `ProviderError`, `ModeKindMismatchError`.
- **Test infra (mirror targets):** `tests/test_oai_background.py` (status mapping), `tests/test_provider_cancel.py`, `tests/test_cancel_subcommand.py`, `tests/test_sigint_upstream_cancel.py`, `tests/test_async_checkpoint.py`, `tests/test_resume.py`, `tests/test_vcr_openai.py`.
- **Research (canonical):** `research/perplexity-deep-research-api.v1.md` — sections 5 (async API: submit, poll, retrieve workflow, status enum, 7-day TTL, rate limits), 6 (5-component billing), 8 (errors + the credit-on-timeout note that motivates async-only), 17 (truncation, async polling delay bug, `total_tokens` misleading), Conclusion ("**always use the async API** for production").
- **External (Perplexity async):** https://docs.perplexity.ai/api-reference/async-chat-completions
- **External (Perplexity rate-limit tiers):** https://docs.perplexity.ai/guides/usage-tiers

**Status:** `[ ]` Scoped, not started.

**Goal**: Implement a Perplexity background provider for **long-running deep research** via the async API (`POST /v1/async/sonar` → poll `GET /v1/async/sonar/{id}` → retrieve). Mirror OpenAI's background lifecycle (`submit/check_status/get_result/reconnect/cancel`) including kind-mismatch defense, checkpoint persistence, `thoth resume`, and `thoth cancel`. Default to `sonar-deep-research` (the only Perplexity model with the async API).

### Scope

- **Implement `PerplexityProvider` background path using the async API only.**
- **Default model: `sonar-deep-research`** — the only Perplexity model with `/v1/async/sonar`. Per `research/perplexity-deep-research-api.v1.md` Conclusion: "always use the async API for production workloads — the synchronous endpoint's multi-minute latency creates timeout and billing risks." Sync deep-research is explicitly out of scope.
- **Forward-compatibility:** the provider does NOT hard-reject other model strings at `__init__`. If Perplexity ships future deep-research models with the async API (e.g., `sonar-deep-research-v2`), they work without code changes — the API returns HTTP 422 for incompatible models, mapped to a clear error with a model hint.
- **Transport: pure-httpx.** The `/v1/async/sonar` endpoint isn't in the OpenAI SDK. Use `httpx.AsyncClient(base_url="https://api.perplexity.ai", headers={"Authorization": f"Bearer {key}"})`. No `openai` import in this provider.
- **Built-in mode** in `src/thoth/config.py:BUILTIN_MODES`:
  - `perplexity_deep_research` (`model: "sonar-deep-research"`, `kind: "background"`, `reasoning_effort: "medium"` (Perplexity's official default; ~$1.19/query — see `research/perplexity-deep-research-api.v1.md` §6)).
- **Lifecycle methods (mirror OpenAI background):**
  - **`submit(prompt, mode, system_prompt, verbose)`** — POST `/v1/async/sonar` with body `{"request": {"model", "messages", "reasoning_effort"?, ...search_options}, "idempotency_key": uuid4().hex}`. The `request` wrapper is required (Perplexity-specific, NOT OpenAI's flat shape). Capture `response.id` (the `request_id`) → `self.jobs[request_id]` → return as `job_id`. **The Perplexity `request_id` IS the job_id** — that lets `reconnect()` work after process restart with no local state.
  - **`check_status(job_id)`** — GET `/v1/async/sonar/{job_id}`. Map Perplexity status → Thoth internal status:
    - `CREATED` → `{"status":"queued","progress":0.0}`
    - `IN_PROGRESS` → `{"status":"running","progress":~0.5}` (no real progress signal; estimate from `created_at` if available)
    - `COMPLETED` → cache `data["response"]` in `self.jobs[job_id]`, return `{"status":"completed","progress":1.0}`
    - `FAILED` → `{"status":"permanent_error","error": data.get("error_message")}`
    - HTTP 404 → `{"status":"permanent_error","error":"Job expired (7-day TTL) or not found server-side"}`
    - Network/timeout during poll → `{"status":"transient_error","error":...}` (runner retries)
  - **`get_result(job_id, verbose)`** — fetch fresh response if not cached; extract content from `response["choices"][0]["message"]["content"]` via **dict access** (OpenAI SDK has no typedefs for Perplexity-specific fields per `research/perplexity-deep-research-api.v1.md` §9). Append:
    - `## Sources` from `response["search_results"]` (deprecated `citations` field ignored per §11).
    - `## Cost\n\nTotal: $X.XXXX` from `response["usage"]["cost"]["total_cost"]` (5-component billing: input + output + citation + reasoning + search-query tokens; reasoning dominates 54–77% of cost — surfacing total_cost is the only honest metric per §17).
    - `> ⚠ Possible truncation` warning if `finish_reason == "stop"` AND content tail lacks terminal punctuation (heuristic for the documented 25–50% truncation rate per §17). Conservative; user can ignore.
  - **`reconnect(job_id)`** — GET `/v1/async/sonar/{job_id}` to repopulate `self.jobs[job_id]` after a fresh process. HTTP 404 → `ProviderError("perplexity", "Job {id!r} not found. Async results expire 7 days after submission.")`. Enables `thoth resume <op_id>` after Ctrl-C / process restart.
  - **`cancel(job_id)`** — depends on Open Question: **does Perplexity expose server-side cancel?** P18-T19 research note said no; reverify in T01. If no upstream cancel: return `{"status":"upstream_unsupported"}` so the existing `cancel.py:122–129` rendering shows "⚠ {name}: upstream cancel not supported; local checkpoint marked cancelled" (matches OpenAI's behavior for the same case). If yes: implement the call.
- **Kind-mismatch defense:** `_validate_kind_for_model` raises `ModeKindMismatchError` BEFORE any HTTP for these cases:
  - `kind="background"` + non-deep-research model (e.g., `sonar-pro`) — those are P23's domain (sync only).
  - `kind="immediate"` + `sonar-deep-research` — P23's domain rejects this; P27 also defends in case the runner mis-routes.
- **Error mapping** (`_map_perplexity_error_async`): 401 → `APIKeyError("perplexity")`, 402 → `APIQuotaError("perplexity")` (insufficient credits), 422 → `ProviderError("perplexity", "Invalid async request — model {model!r} may not support /v1/async/sonar")`, 429 → `ProviderError("perplexity", "Rate limit exceeded")`, 5xx → transient ProviderError, `httpx.TimeoutException`/`ConnectError` → friendly network error.
- **Retry policy:** tenacity 3 attempts, `wait_exponential(multiplier=1, min=4, max=10)`, retry on `httpx.ConnectError` and `httpx.TimeoutException` only. Mirrors openai.py.
- **Polling cadence:** start at 10s, exponential backoff up to 30s (Perplexity doc recommendation). Reuse Thoth's existing polling-interval config (BUG-03 / P03 fix) where it makes sense; document any divergence.
- **Idempotency key on submit:** UUID4 hex. Prevents duplicate submissions on tenacity retry.
- **Checkpoint integration:** persist `request_id` in checkpoint via existing `CheckpointManager`. `thoth resume <op_id>` reads checkpoint, recreates provider, calls `provider.reconnect(request_id)`, re-enters `_run_polling_loop`.
- **Reasoning effort in mode config:** `low` / `medium` / `high` exposed as a mode-config field. Default `medium`. Document the cost tradeoff in mode docstring (low ≈ $0.41, medium ≈ $1.19, high ≈ $1.32 per query per §6).
- **CLI surface:** `thoth ask "deep query" --provider perplexity --mode perplexity_deep_research [--out FILE] [--api-key-perplexity sk-...]`. `thoth resume <op_id>` (existing). `thoth cancel <op_id>` (existing). `--cancel-on-interrupt` flag honored on Ctrl-C if upstream cancel becomes available.
- **Tests (Phase 1 — lands with the impl PR):**
  - **Pytest unit (offline):** submit body shape (idempotency_key + `request` wrapper), status mapping table, get_result extraction (sources/cost/truncation), reconnect happy-path + 404, cancel (`upstream_unsupported` if confirmed), kind-mismatch defense.
  - All HTTP mocked via `unittest.mock.AsyncMock` patching `provider._client.post/get`.
- **Tests (Phase 2 — separate PR, gated on `deepresearch_replay` P04):**
  - VCR cassette for happy-path async lifecycle: submit → IN_PROGRESS poll → COMPLETED with content/sources/cost. Cassette at `thoth_test_cassettes/perplexity/async-happy-path.yaml` per `thoth_vcr.md`.
  - VCR cassette for auth-error (401) and expired-job (404) wire formats.
  - Live-api gated tests (`@pytest.mark.live_api`, `tests/extended/test_perplexity_async_real_workflows.py`) for the full lifecycle. NOT in CI by default — real deep-research runs cost $0.41–$1.32 each and take 2–40 minutes.

### Out of scope

- **Synchronous `/chat/completions` for `sonar-deep-research`** — the doc warns explicitly: "credits charged on timeout with no output" (§8). Async-only.
- **Other Sonar models** (`sonar`, `sonar-pro`, `sonar-reasoning-pro`) — owned by P23 (sync immediate provider).
- **Streaming for deep-research** — long pauses between chunks (minutes), broken-stream third-party reports per §17. Async API is the recommended path; we don't implement streaming for this provider.
- **Webhook/callback** — Perplexity doesn't offer one for async; polling is the only option per §5.
- **The "list all jobs" endpoint** (`GET /v1/async/sonar` without an id) — no immediate use case.
- **Sync chat-completions retrieval as fallback** — even if a deep-research request started sync somehow (it shouldn't), don't try to recover it; let the kind-mismatch defense catch it pre-HTTP.

### Open questions

- **Cancel support**: P18-T19 said Perplexity doesn't expose server-side cancel for async jobs. **Re-verify against current docs** (T01). If still no: `cancel()` returns `{"status":"upstream_unsupported"}` and the local checkpoint is marked cancelled.
- **Polling cadence**: reuse Thoth's existing polling-interval config (BUG-03/P03 fix), or pick Perplexity-specific defaults (10s → 30s exponential per Perplexity doc)? Recommend reuse with a per-provider override knob.
- **Truncation heuristic**: conservative (terminal-punctuation-only) or stricter (minimum response length, expected sections, etc.)? Conservative recommended; users can ignore false positives.
- **Cost display gating**: always show `## Cost` footer, or only when `--show-cost` flag is set? Recommend always (deep-research is expensive enough that visibility matters).
- **VCR cassette IN_PROGRESS sequence**: include 1–2 IN_PROGRESS polls in the happy-path cassette (to test progress reporting), or collapse to submit+COMPLETED for simplicity? Recommend including 1 IN_PROGRESS poll.
- **`reasoning_effort` default**: `medium` (Perplexity's official default; ~$1.19) vs `low` (~$0.41)? Material cost difference. Recommend `low` for our default mode (cheapest sensible deep-research; users opt up via mode config).
- **Async polling delay bug**: `IN_PROGRESS` may show for 30–40 minutes when actual completion is ~2 minutes (per §17). Should we add a "poll-budget" timeout that abandons after N minutes regardless of API status? Out of scope for v1; document in mode docstring.

### Tests & Tasks

- [ ] [P27-TS01] Design tests for `submit()` POST body shape — `{"request": {...model, messages, reasoning_effort?}, "idempotency_key": <uuid>}`. Cover the request-wrapper requirement (NOT OpenAI's flat shape).
- [ ] [P27-TS02] Design tests for status mapping (CREATED/IN_PROGRESS/COMPLETED/FAILED → Thoth status enum + progress).
- [ ] [P27-TS03] Design tests for `get_result` extraction — dict-style `search_results` access (NOT attr-style; OpenAI SDK has no typedefs), `## Sources` formatting + dedup, `## Cost` footer from `usage.cost.total_cost`, truncation warning heuristic.
- [ ] [P27-TS04] Design tests for `reconnect()` — happy-path repopulates `self.jobs[job_id]`; HTTP 404 raises `ProviderError` with 7-day-TTL message.
- [ ] [P27-TS05] Design tests for `cancel()` — based on T01 finding, either upstream-cancel happy-path or `upstream_unsupported` returned (exact shape consumed by `cancel.py:122–129`).
- [ ] [P27-TS06] Design tests for kind-mismatch defense — `kind="background"` + `model="sonar-pro"` raises pre-HTTP; `kind="immediate"` + `model="sonar-deep-research"` raises pre-HTTP.
- [ ] [P27-TS07] Design VCR cassette test for happy-path async lifecycle — submit → 1× IN_PROGRESS poll → COMPLETED → `get_result()` returns content+sources+cost. Cassette path: `thoth_test_cassettes/perplexity/async-happy-path.yaml`.
- [ ] [P27-TS08] Design VCR cassette tests for auth-error (401) and expired-job (404) wire formats.
- [ ] [P27-TS09] Design live-api gated tests (`@pytest.mark.live_api`, `tests/extended/test_perplexity_async_real_workflows.py`) for the full lifecycle (submit → poll → result → cancel-or-cleanup).
- [ ] [P27-T01] Re-verify Perplexity server-side cancel support against current docs (https://docs.perplexity.ai/api-reference/async-chat-completions); update Open Questions section with finding before T08 starts.
- [ ] [P27-T02] Add Perplexity built-in mode `perplexity_deep_research` to `src/thoth/config.py:BUILTIN_MODES` with `model: "sonar-deep-research"`, `kind: "background"`, `reasoning_effort` exposed (default `low` or `medium` per Open Question).
- [ ] [P27-T03] Implement `PerplexityProvider.__init__` for the background path: `httpx.AsyncClient(base_url="https://api.perplexity.ai", headers={"Authorization":..., "Content-Type":...})`. Add `_validate_kind_for_model` covering both directions of the kind-split.
- [ ] [P27-T04] Implement module-level `_map_perplexity_error_async(exc, model, verbose) -> ThothError` for httpx exceptions and Perplexity HTTP status codes (401/402/422/429/5xx).
- [ ] [P27-T05] Implement `submit()` — POST `/v1/async/sonar` with idempotency_key, retry on transient. Capture `request_id` → `self.jobs[request_id]`, return as job_id.
- [ ] [P27-T06] Implement `check_status()` — GET `/v1/async/sonar/{id}` with full status mapping, 404 → expired-TTL message, network errors → transient.
- [ ] [P27-T07] Implement `get_result()` — fresh fetch, dict-style `search_results` access, `## Sources` dedup, `## Cost` footer from `usage.cost.total_cost`, truncation-warning heuristic.
- [ ] [P27-T08] Implement `reconnect()` — repopulate `self.jobs[job_id]`; 404 → `ProviderError` with 7-day-TTL hint.
- [ ] [P27-T09] Implement `cancel()` per T01 finding — either upstream call or `upstream_unsupported` return.
- [ ] [P27-T10] Wire CLI: `thoth ask --provider perplexity --mode perplexity_deep_research`, `thoth resume <op_id>` (uses `reconnect`), `thoth cancel <op_id>` (uses `cancel`), `--api-key-perplexity` with `mask_api_key()`.
- [ ] [P27-T11] Add `tests/test_provider_perplexity_async.py` covering TS01–TS06 with `httpx.AsyncClient` mocked via `unittest.mock.AsyncMock`.
- [ ] [P27-T12] Add `tests/test_async_checkpoint.py` extension verifying `request_id` round-trips through checkpoint (mirrors OpenAI's coverage).
- [ ] [P27-T13] Add VCR cassette tests once `deepresearch_replay` P04 lands cassettes (TS07, TS08). Phase 2 — separate PR; doesn't block T01–T12.
- [ ] [P27-T14] Add live-api gated test in `tests/extended/test_perplexity_async_real_workflows.py` per TS09. Costs $0.41–$1.32 per run; document in test docstring.
- [ ] [P27-T15] Update `tests/test_provider_registry.py` to assert `is_implemented() == True` and `default_model == "sonar-deep-research"`.

### Acceptance Criteria

- `thoth ask "Comprehensive analysis of mRNA vaccines in 2025" --provider perplexity --mode perplexity_deep_research` runs end-to-end:
  - Submits via `/v1/async/sonar`, polls until COMPLETED, retrieves content + sources + cost.
  - User sees progress updates during the 2–40min run (via the existing background polling spinner).
  - Output ends with `## Sources` and `## Cost` sections; if truncated mid-sentence, a `> ⚠ Possible truncation` warning appears.
- `thoth ask ... --provider perplexity --mode some_immediate_mode` (where mode declares `model: sonar`) raises `ModeKindMismatchError` — no HTTP — and points the user at P23's sync modes.
- Ctrl-C during polling: checkpoint marked cancelled; if upstream cancel exists (T01), upstream job cancelled too; otherwise `upstream_unsupported` rendered.
- `thoth resume <op_id>` after process restart: re-attaches to in-flight `request_id`, polls to completion. 7-day-TTL expiry produces a clear error.
- `tests/test_provider_perplexity_async.py` — all unit cases pass.
- `tests/test_provider_registry.py::test_perplexity_provider_is_implemented` — passes.
- A live-api manual run succeeds (one real $0.41+ deep-research call).

### Dependencies

- **`deepresearch_replay` P04** (Perplexity async capture) — needed for VCR cassettes (P27-T13). Phase 1 unit tests (T11) and live-api tests (T14) do not block on this; T13 lands as a separate Phase 2 PR after P04.
- **P26 (OpenAI background deep research)** — not a hard dependency, but P26 finalizing the background-provider polling-loop contract (in `_run_polling_loop`) before P27 starts means we mirror a stable target. Worth coordinating.

### Definition of Done

- All TS## and T## checkboxes flipped (Phase 1: T01–T12, T15; Phase 2: T13–T14).
- `is_implemented()` returns `True`; registry test asserts it.
- Pre-commit gate (lefthook: ruff/ty/bandit/gitleaks/codespell + `./thoth_test`) passes.
- One pytest run shows `tests/test_provider_perplexity_async.py`, `tests/test_provider_registry.py`, `tests/test_async_checkpoint.py` all green.
- A live-api manual run with `PERPLEXITY_API_KEY=...` returns a valid deep-research result with non-empty `## Sources` and `## Cost` sections.
- Trunk row flipped to `[x]` only after the full gate passes.
