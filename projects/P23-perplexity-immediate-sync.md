# P23 — Perplexity — Immediate (Synchronous) Calls

**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)
- **Predecessor:** P22 (`projects/P22-openai-immediate-sync.md`) — validated OpenAI immediate path; P23 mirrors its option surface and test pattern.
- **Adjacent:** P25 (`projects/P25-arch-review-immediate-providers.md`) — cross-immediate-provider review reads P23/P24 once they ship.
- **Adjacent:** P27 (`projects/P27-perplexity-background-deep-research.md`) — sibling Perplexity project for the async deep-research path. P23 must NOT touch `sonar-deep-research`; P27 owns it.
- **Code (mirror target):** `src/thoth/providers/openai.py:393` (`OpenAIProvider.stream()`), `src/thoth/providers/openai.py:144–164` (`_validate_kind_for_model`), `src/thoth/run.py` `_execute_immediate`, `src/thoth/providers/base.py` (`StreamEvent`, `ResearchProvider`).
- **Config (mirror target):** `src/thoth/config.py:182` (`mode_kind()`), `src/thoth/config.py:53–159` (`BUILTIN_MODES` — every mode carries `kind: "immediate" | "background"`).
- **Errors:** `src/thoth/errors.py` — `APIKeyError`, `APIQuotaError`, `ProviderError`, `ModeKindMismatchError`.
- **Research (in-repo, canonical):** `research/perplexity-deep-research-api.v1.md` — sections 2 (request schema, full param table), 3 (response schema), 9 (OpenAI compat layer), 13 (context windows), 18 (per-model feature matrix).
- **External (Perplexity API reference):** https://docs.perplexity.ai/api-reference/chat-completions-post
- **External (Perplexity models / pricing / tiers):** https://docs.perplexity.ai/getting-started/models, https://docs.perplexity.ai/getting-started/pricing, https://docs.perplexity.ai/guides/usage-tiers
- **External (Pro Search GA, sonar-pro streaming requirement):** https://community.perplexity.ai/t/pro-search-now-generally-available-for-sonar-pro/4742
- **External (`<think>` block on sonar-reasoning-pro):** https://community.perplexity.ai/t/did-perplexity-remove-the-think-tags-from-sonar-reasoning-pro-api/3555

**Status:** `[ ]` Scoped, not started.

**Goal**: Implement a Perplexity provider for **synchronous, immediate-response** chat completions that mirrors the option surface and CLI ergonomics of the OpenAI immediate path (P22). Default to a single built-in synchronous model so users get a working `--provider perplexity` out of the box.

### Scope

- Implement `PerplexityProvider` using the OpenAI Python SDK in drop-in mode: `AsyncOpenAI(api_key=..., base_url="https://api.perplexity.ai")`. The SDK auto-appends `/chat/completions`; per-request Perplexity-specific params go through `extra_body=` (any other shape raises `TypeError` per the SDK).
- **Models supported (sync only):** `sonar`, `sonar-pro`, `sonar-reasoning-pro`. **Default model: `sonar`** (cheapest at $1/$1 + $5/1K context-low fee, fastest, returns `search_results` / citations — best fit for a "default sync provider with web grounding"; mirrors OpenAI's `o3` immediate default).
- **Built-in modes** in `src/thoth/config.py:BUILTIN_MODES`, all `kind: "immediate"`:
  - `perplexity_quick` (`sonar`) — default sync mode
  - `perplexity_pro` (`sonar-pro`) — deeper retrieval, more expensive
  - `perplexity_reasoning` (`sonar-reasoning-pro`) — exposes `<think>` chain-of-thought
- **`stream()` method** translates Perplexity SSE → `StreamEvent`:
  - `delta.content` → `StreamEvent("text", delta)`
  - `<think>...</think>` block on `sonar-reasoning-pro` → split out as `StreamEvent("reasoning", ...)` (parser handles cumulative-content edge case noted in `research/perplexity-deep-research-api.v1.md` §4)
  - Final chunk's `search_results` → `StreamEvent("citation", title|url)` per result, then terminal `StreamEvent("done", "")`
- **Non-stream fallback** (when `stream()` raises or caller opts out) — `submit()` performs one-shot call, `check_status()` returns `{"status":"completed","progress":1.0}` immediately, `get_result()` extracts content + appends `## Sources\n\n- [title](url)` deduped from `search_results`. Mirrors `OpenAIProvider`'s non-background sync path.
- **Option surface (mode config → API request):**
  - **OpenAI-mirroring:** `system_prompt`, `max_tokens`, `stream`/`stream_mode`, `stop`, `response_format` (text / json_schema / regex), `temperature`, `top_p` (Perplexity accepts both per current schema; document as best-effort since search step is non-stochastic).
  - **Perplexity-specific (via `extra_body`) — curated v1 subset:** `web_search_options.search_context_size` (low/med/high — drives the per-request fee), `search_recency_filter` (hour/day/week/month/year), `search_domain_filter` (≤20 entries; allow- and deny-list mutually exclusive per request), `return_related_questions`. Other Perplexity options are deferred — see Out of scope. Rationale: smaller v1 surface is easier to grow than to shrink (any field shipped in BUILTIN_MODES help becomes a soft contract with users who put it in their config).
- **Default `web_search_options.search_context_size = "high"`** for richest retrieval out of the box; remains configurable per mode config (users who want to lower cost can override to `"low"` or `"medium"`). Note: at `"high"` the per-request fee for `sonar` is ~$12/1K.
- **Kind-mismatch defense** mirrors `OpenAIProvider._validate_kind_for_model`: passing `model="sonar-deep-research"` with `kind="immediate"` raises `ModeKindMismatchError` BEFORE any HTTP call. (`sonar-deep-research` is P27's domain.)
- **Error mapping** (`_map_perplexity_error`): 401 → `APIKeyError("perplexity")`, 402 → `APIQuotaError("perplexity")`, 422 → `ProviderError("perplexity", ...)` with model hint, 429 → `ProviderError(rate-limit)`, 5xx → transient ProviderError, `httpx.TimeoutException`/`ConnectError` → friendly network error. Mirrors `_map_openai_error` shape.
- **Retry policy:** tenacity `stop_after_attempt(3)`, `wait_exponential(multiplier=1, min=4, max=10)`, retry on `httpx.ConnectError` and `httpx.TimeoutException` only. Exact mirror of openai.py's policy.
- **CLI surface:** `thoth ask "prompt" --provider perplexity [--mode perplexity_quick|perplexity_pro|perplexity_reasoning] [--out FILE] [--append] [--quiet] [--api-key-perplexity sk-...]`. `--api-key-perplexity` masked in verbose output via existing `mask_api_key()` helper.
- **Tests:**
  - **Pytest unit (offline):** stream contract, error mapping table, kind-mismatch defense, dict-style `search_results` access, `<think>` parsing, retry on transient.
  - **VCR cassette (offline replay):** happy-path sync request once `deepresearch_replay` P03 lands cassettes at `thoth_test_cassettes/perplexity/sync-happy-path.yaml` (per `thoth_vcr.md`).
  - **Live-api gated** (`@pytest.mark.live_api`, `tests/extended/test_perplexity_real_workflows.py`): real `--provider perplexity --api-key-perplexity` smoke test mirroring `test_openai_real_workflows.py`.

### Out of scope

- **`sonar-deep-research` model** — owned by P27. P23 explicitly raises `ModeKindMismatchError` if a user tries to use it on the immediate path.
- **Perplexity async API endpoints** (`/v1/async/sonar`) — owned by P27.
- **Pro Search mode** (`web_search_options.search_type: "pro"` on `sonar-pro`) — requires `stream: true` and special handling per [community announcement](https://community.perplexity.ai/t/pro-search-now-generally-available-for-sonar-pro/4742). Defer to a follow-up unless explicitly requested.
- **Custom `safe_search` flag** — absent from current Perplexity OpenAPI schema per researcher; do not surface.
- **Multi-turn conversation memory** — Perplexity is stateless; client manages history (same as OpenAI). Out of P23's scope; thoth's existing single-turn pattern stands.
- **Perplexity options not in the v1 curated subset** — `search_mode` (web/academic/sec), `search_after_date_filter` / `search_before_date_filter` (MM/DD/YYYY format footgun, easy to misuse), `search_language_filter`, `enable_search_classifier`, `disable_search`, `language_preference`, `return_images`. All trivially addable later via mode-config; held back from v1 to keep the user-facing surface (BUILTIN_MODES help text, mode-config docstrings, test matrix) manageable.
- **Provider implementation refactor** — P25 (`projects/P25-arch-review-immediate-providers.md`) handles cross-provider cleanup once P23/P24 ship.

### Open questions — resolved during refinement (2026-04-30)

All open questions were closed during the project-refine pass. Decisions recorded here for audit trail; relevant constraints folded into Scope / Out of scope above.

- **`<think>` separation** — **Resolved: strip-and-emit `StreamEvent("reasoning", ...)`.** Parser strips `<think>...</think>` from `message.content`, emits the contents as one or more `kind="reasoning"` events, then continues with `kind="text"` for the post-think answer. Tolerates intermittent tag-stripping (community-reported bug) and the cumulative-content caveat per `research/perplexity-deep-research-api.v1.md` §4. This finally uses the `StreamEvent("reasoning", ...)` slot P18 cut for exactly this case. Covered by TS03 + T04.
- **`temperature` / `top_p` exposure** — **Resolved: expose both in mode config with "best-effort" caveat in docstrings.** Mirrors OpenAI immediate-path option surface; users who want them get them; mode-config docstring documents the Perplexity caveat ("search step is non-stochastic; effects are best-effort"). Already covered in Scope's OpenAI-mirroring bullet.
- **VCR cassette dependency** — **Resolved: block on `deepresearch_replay` P03** per the on-disk `thoth_vcr.md` maintainer note ("Gemini and Perplexity cassettes will land when `deepresearch_replay` P03/P04 complete"). T09 (`tests/test_vcr_perplexity_sync.py`) is staged but lands fully only after P03 publishes `thoth_test_cassettes/perplexity/sync-happy-path.yaml`. Captured in Dependencies section.
- **Default `search_context_size`** — **Resolved: `"high"`, configurable per mode config.** Trade-off: richest retrieval out of the box at the cost of higher per-request fee (~$12/1K for `sonar`). Users who want to lower cost override via mode-config overlay (which is already the v1 design — no extra plumbing needed). Updated in Scope above.
- **Pro Search streaming requirement on `sonar-pro`** — **Resolved: silent degrade — let Perplexity handle it.** P23 does not inspect mode config for `web_search_options.search_type`; if a user puts `"pro"` there without `stream=True`, the API silently falls back to standard Sonar Pro (its native behavior). Zero validation logic in P23. Pro Search is documented as out-of-scope; revisit in a follow-up project when it's officially supported.

### Tests & Tasks

- [ ] [P23-TS01] Design tests for Perplexity sync `stream()` contract — SSE chunks → `StreamEvent("text", delta)`, final-chunk `search_results` → `StreamEvent("citation", ...)`, terminal `StreamEvent("done", "")`. Cover the cumulative-content caveat from `research/perplexity-deep-research-api.v1.md` §4.
- [ ] [P23-TS02] Design tests for `_map_perplexity_error` table — 401/402/422/429/5xx/network/timeout → expected `ThothError` subclass + message substring. Parametrize.
- [ ] [P23-TS03] Design tests for `<think>` block parsing on `sonar-reasoning-pro` (strip from `message.content`, emit as `StreamEvent("reasoning", ...)`). Include the case where `<think>` is absent (community-reported intermittent removal — code must tolerate both).
- [ ] [P23-TS04] Design tests for kind-mismatch defense — `model="sonar-deep-research"` + `kind="immediate"` raises `ModeKindMismatchError` BEFORE any HTTP call.
- [ ] [P23-TS05] Design VCR cassette test for sync happy-path once `thoth_test_cassettes/perplexity/sync-happy-path.yaml` exists (gated on `deepresearch_replay` P03).
- [ ] [P23-TS06] Design live-api gated tests (`@pytest.mark.live_api`, `tests/extended/test_perplexity_real_workflows.py`) for `--api-key-perplexity` end-to-end smoke + tee `--out -,FILE` (mirrors `test_ext_oai_imm_stream_tee_writes_stdout_and_file`).
- [ ] [P23-T01] Add three Perplexity built-in modes (`perplexity_quick` / `perplexity_pro` / `perplexity_reasoning`) to `src/thoth/config.py:BUILTIN_MODES` with `kind: "immediate"` and sensible defaults (`search_context_size: "low"`).
- [ ] [P23-T02] Implement `PerplexityProvider.__init__` with `AsyncOpenAI(base_url=PERPLEXITY_BASE_URL, api_key=...)` + `httpx.Timeout` config. Add `_validate_kind_for_model` mirroring openai.py.
- [ ] [P23-T03] Implement module-level `_map_perplexity_error(exc, model, verbose) -> ThothError`.
- [ ] [P23-T04] Implement `PerplexityProvider.stream()` — SSE chunks → `StreamEvent` translator with cumulative-content guard, `<think>` parser for sonar-reasoning-pro, final-chunk citation emission, terminal done.
- [ ] [P23-T05] Implement `submit()`/`check_status()`/`get_result()` non-stream fallback path (sync; immediate-style).
- [ ] [P23-T06] Flip `is_implemented()` → `True` and update `tests/test_provider_registry.py` to assert `PerplexityProvider().is_implemented() is True` and default model is `sonar`.
- [ ] [P23-T07] Wire `--api-key-perplexity` CLI flag end-to-end with `mask_api_key()` secret masking (mirrors `--api-key-openai`).
- [ ] [P23-T08] Add `tests/test_provider_perplexity.py` covering TS01–TS04 unit tests with mocked `AsyncOpenAI`/`httpx.AsyncClient`.
- [ ] [P23-T09] Add `tests/test_vcr_perplexity_sync.py` once cassettes land at `thoth_test_cassettes/perplexity/sync-happy-path.yaml`. Mirror `tests/test_vcr_openai.py` pattern.
- [ ] [P23-T10] Add live-api gated test in `tests/extended/test_perplexity_real_workflows.py` per TS06.
- [ ] [P23-T11] Update `src/thoth/help.py` and any provider-listing logic in `src/thoth/cli.py` / `src/thoth/commands.py` to surface Perplexity as a real provider (drop "(not implemented)" text once T06 lands).

### Acceptance Criteria

- `thoth ask "What's new in CRISPR?" --provider perplexity` returns a grounded answer with a `## Sources` section using the default `sonar` model.
- `thoth ask --provider perplexity --mode perplexity_reasoning ...` exposes `<think>` chain-of-thought as a separate stream event (or appended section in non-stream).
- `thoth ask --provider perplexity --mode some_deep_research_mode ...` (where mode declares `model: sonar-deep-research`) raises `ModeKindMismatchError` with a suggestion pointing at P27 — no HTTP call made.
- `tests/test_provider_perplexity.py` — all unit cases pass.
- `tests/test_provider_registry.py::test_perplexity_provider_is_implemented` — passes.
- VCR test passes once cassettes land.
- `--api-key-perplexity sk-...` works without `PERPLEXITY_API_KEY` in env; key never appears in stdout/stderr/logs.

### Dependencies

- **`deepresearch_replay` P03** (sync Perplexity capture) — needed for VCR cassettes (P23-T09). P23 unit tests (T08) and live-api tests (T10) do not block on this.

### Definition of Done

- All TS## and T## checkboxes flipped.
- `is_implemented()` returns `True`; registry test asserts it.
- Pre-commit gate (lefthook: ruff/ty/bandit/gitleaks/codespell + `./thoth_test`) passes.
- One pytest run shows `tests/test_provider_perplexity.py` and `tests/test_provider_registry.py` both green.
- A live-api manual run (`PERPLEXITY_API_KEY=... uv run pytest tests/extended/test_perplexity_real_workflows.py -v`) succeeds.
- Trunk row flipped to `[x]` only after the full gate passes.
