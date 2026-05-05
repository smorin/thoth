# P24 - Gemini - Immediate (Synchronous) Calls

**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)
- **Predecessor:** P22 (`projects/P22-openai-immediate-sync.md`) - validated the current OpenAI immediate path and streaming executor.
- **Sibling pattern:** P23 (`projects/P23-perplexity-immediate-sync.md`) - the immediate-provider pattern P24 mirrors (built-in modes, `_execute_immediate` side-channel rendering, `## Reasoning` / `## Sources` blocks, `_map_*_error`, tenacity retry, kind-mismatch guard, extended + live_api coverage).
- **Adjacent:** P25 (`projects/P25-arch-review-immediate-providers.md`) - cross-immediate-provider review after P23/P24 ship.
- **Consolidation spec:** [planning/p24-immediate-providers-consolidation.v1.md](../planning/p24-immediate-providers-consolidation.v1.md) - factor-dedup output classifying drift across OpenAI/Perplexity/Gemini. **Per user decision 2026-05-03**, cross-provider consistency fixes are folded into P24 itself rather than spun up as a sibling project — see the **Cross-provider consistency (extended)** subsection of Tests & Tasks below.
- **Adjacent:** P28 (`projects/P28-gemini-background-deep-research.md`) - owns Gemini async/background deep research using `deep-research-pro-preview-12-2025`.
- **Code:** `src/thoth/providers/openai.py`, `src/thoth/providers/perplexity.py`, `src/thoth/providers/base.py`, `src/thoth/run.py`, `src/thoth/providers/__init__.py`, `src/thoth/config.py`, `src/thoth/errors.py`.
- **External (SDK package):** https://pypi.org/project/google-genai/ - PyPI page for `google-genai`; current minimum P24 targets is `>=1.74.0`.
- **External (SDK repo):** https://github.com/googleapis/python-genai - repository root; issues / changelog / examples.
- **External (SDK reference):** https://googleapis.github.io/python-genai/ - `google-genai` async client reference (`genai.Client(...).aio.models.generate_content` / `generate_content_stream`).
- **External (SDK source - types):** https://github.com/googleapis/python-genai/blob/main/google/genai/types.py - typed access to `GenerateContentConfig`, `GroundingMetadata`, `GroundingChunk`, `Tool`, `GoogleSearch`, `ThinkingConfig`, `Part.thought`.
- **External (SDK source - errors):** https://github.com/googleapis/python-genai/blob/main/google/genai/errors.py - `APIError` / `ClientError` / `ServerError` taxonomy.
- **External (deep-research announcement, P28 cross-ref):** https://blog.google/innovation-and-ai/models-and-research/gemini-models/next-generation-gemini-deep-research/ - context for what P24 deliberately excludes; deep research is P28's lane.
- **External (deep-research docs, P28 cross-ref):** https://ai.google.dev/gemini-api/docs/deep-research - referenced only to enforce the kind-mismatch guard for `*-deep-research-*` models; not used for any P24 immediate-path implementation.
- **External (Interactions API, P28 cross-ref):** https://ai.google.dev/gemini-api/docs/interactions - background-only API surface; explicitly out of scope for P24.
- **External (text generation):** https://ai.google.dev/gemini-api/docs/text-generation
- **External (thinking):** https://ai.google.dev/gemini-api/docs/thinking - `thinkingBudget` (2.5), `thinkingLevel` (3.x), `include_thoughts`, `Part.thought`.
- **External (grounding):** https://ai.google.dev/gemini-api/docs/google-search - `tools=[Tool(google_search=GoogleSearch())]`, `groundingMetadata` shape.
- **External (structured output):** https://ai.google.dev/gemini-api/docs/structured-output - `response_mime_type` + `response_json_schema`.
- **External (models):** https://ai.google.dev/gemini-api/docs/models - GA model IDs and lifecycle.
- **External (pricing):** https://ai.google.dev/gemini-api/docs/pricing - thinking tokens billed as output tokens.
- **External (terms - grounding):** https://ai.google.dev/gemini-api/terms#grounding-with-google-search - `searchEntryPoint.renderedContent` display obligation.
- **External (canonical-error codes):** https://google.aip.dev/193 - HTTP-to-`google.rpc.Code` `status` mapping used for error discrimination.

**Status:** `[ ]` Scoped, not started.

**Goal**: Implement Gemini synchronous chat support for immediate Thoth runs using the official `google-genai` Python SDK (NOT the OpenAI-compat compatibility endpoint, which omits grounding/thinking). P24 adds Gemini built-in immediate modes, request construction, streaming, non-stream execution, side-channel output handling (`reasoning` from thought parts; `citation` from grounding metadata), live coverage, and user-facing provider surfaces. Reuses P23's `_execute_immediate`, `Citation`, `StreamEvent`, `## Reasoning` / `## Sources` rendering, and `--model` plumbing without modification.

### Scope

- Add `google-genai` (>= 1.74.0) as a runtime dependency. The legacy `google-generativeai` package reached end-of-support 2025-11-30 - do not use it.
- Implement `GeminiProvider` using `genai.Client(api_key=...)` and `client.aio.models.generate_content_stream(...)` / `generate_content(...)` for streaming and non-stream paths respectively. Do not route through Gemini's OpenAI-compat endpoint - that layer omits grounding metadata, thought parts, and `thinkingBudget`.
- Supported synchronous models in built-ins (GA only): `gemini-2.5-flash-lite`, `gemini-2.5-pro`. `GeminiProvider` defaults to `gemini-2.5-flash-lite` only when no effective mode or CLI model is present.
- `--model` CLI passthrough is already shipped in P23 and is unchanged here. Model strings are passed through to the selected provider without local provider/model compatibility validation, except for the kind-mismatch guard below.
- Add built-in modes in `src/thoth/config.py:BUILTIN_MODES`, all `kind: "immediate"`:
  - `gemini_quick`: `provider = "gemini"`, `model = "gemini-2.5-flash-lite"`, `gemini.tools = ["google_search"]`, `gemini.thinking_budget = 0` (off; Flash-Lite default is off but make it explicit).
  - `gemini_pro`: `provider = "gemini"`, `model = "gemini-2.5-pro"`, `gemini.tools = ["google_search"]`, `gemini.thinking_budget = -1` (dynamic; Pro defaults to dynamic but make it explicit).
  - `gemini_reasoning`: `provider = "gemini"`, `model = "gemini-2.5-pro"`, `gemini.tools = ["google_search"]`, `gemini.thinking_budget = -1`, `gemini.include_thoughts = true`.
- Provider-namespaced mode config: `[modes.X.gemini]` keys are translated into `GenerateContentConfig` fields by `GeminiProvider`. Recognized keys: `tools` (list of tool names; `"google_search"` -> `Tool(google_search=GoogleSearch())`), `thinking_budget` (int 0-32768 or `-1`), `include_thoughts` (bool), `safety_settings` (list of `{category, threshold}` dicts), `temperature`, `top_p`, `top_k`, `max_output_tokens`, `stop_sequences`, `response_mime_type`, `response_json_schema`. Unrecognized keys under `gemini.*` are passed through to `GenerateContentConfig` by name; do not local-validate every key.
- Define module-level `_DIRECT_SDK_KEYS_GEMINI: tuple[str, ...]` enumerating native `GenerateContentConfig` field names so a reviewer can audit the allowlist in one place. Suffix-named per the cross-provider convention (`_DIRECT_SDK_KEYS_<PROVIDER>`); the Cross-immediate-providers consolidation prerequisite project introduces `_DIRECT_SDK_KEYS_OPENAI` (new) and renames Perplexity's bare `_DIRECT_SDK_KEYS` to `_DIRECT_SDK_KEYS_PERPLEXITY`. Anything outside this allowlist under `[modes.X.gemini]` is passed through `GenerateContentConfig(**extra)` by name.
- Define module-level `_PROVIDER_NAME_GEMINI = "gemini"` constant; use it in every `_map_gemini_error(...)` ThothError construction. Suffix-named per the cross-provider convention (`_PROVIDER_NAME_<PROVIDER>`); the Cross-immediate-providers consolidation prerequisite project introduces `_PROVIDER_NAME_OPENAI = "openai"` (new) and renames Perplexity's bare `_PROVIDER_NAME` to `_PROVIDER_NAME_PERPLEXITY`. The full-suffix naming makes the constants unique across modules — useful when grep'ing repo-wide or extracting future cross-provider helpers.
- All `## Sources` rendering MUST use `md_link_title()` and `md_link_url()` from `thoth.utils` for HTML/scheme-injection defense. Mirrors `perplexity.py:463`'s `f"- [{md_link_title(title)}]({md_link_url(url)})"` pattern. Never inline raw `f"- [{title}]({url})"` interpolation. (OpenAI currently uses raw interpolation at `openai.py:614-622`; that's a known bug tracked by the Cross-immediate-providers consolidation prerequisite project.)
- Auth-invalid `ThothError` (`code=401, status=UNAUTHENTICATED` with `_INVALID_KEY_PHRASES_GEMINI` matching the message) MUST set `exit_code=2`, mirroring `perplexity.py`'s invalid-key path. Auth-missing maps to bare `APIKeyError("gemini")` (default exit code).
- For `INVALID_ARGUMENT 400` errors carrying an offending-parameter hint (e.g. `"Unrecognized argument: 'temperature'"`), extract the parameter name via the same regex pattern OpenAI uses (`r"'(\w+)'"`) and surface a CLI-friendly hint. Mirrors `openai.py:95-113`'s pattern.
- Gemini `NotFoundError`-equivalent (`ClientError(404)` with `status="NOT_FOUND"`) MUST map to `ProviderError("gemini", "Model {model!r} not found...")` with the `models` CLI hint. Mirrors `openai.py:87-93`. Without this, model-id typos surface as a generic API error with no actionable hint.
- Default fallbacks when no `gemini.*` is configured: no tools (no grounding), no thinking knobs (model default applies), no safety overrides.
- `system_prompt` becomes `GenerateContentConfig.system_instruction`. The user prompt becomes `contents=[Content(role="user", parts=[Part(text=...)])]`.
- `stream()` translates Gemini SDK chunks into `StreamEvent`:
  - For each chunk, walk `chunk.candidates[0].content.parts`. For each `Part`:
    - `part.thought is True` -> `StreamEvent("reasoning", part.text)`.
    - `part.text` (and `thought` not True) -> `StreamEvent("text", part.text)`.
  - On the terminal chunk (or on any chunk where `candidates[0].grounding_metadata` is populated), read `grounding_metadata.grounding_chunks`. Project each `chunk.web` to `Citation(title=web.title or _domain_of(web.uri), url=web.uri)`, dedupe by `url`, and emit `StreamEvent(kind="citation", citation=Citation(...))` for each. The executor already dedupes citations across the stream, so multiple emissions are safe.
  - End of stream -> `StreamEvent("done", "")`.
  - **No `<think>` parser.** Gemini's reasoning surfaces as structured `Part.thought` flags, not delimiter strings. Do not introduce a stateful `<think>` segmenter for the Gemini path.
- `_execute_immediate` is unchanged. It already handles `text` / `reasoning` / `citation` / `done` events and renders `## Reasoning` and `## Sources` per P23.
- Explicit `stream = false` skips `provider.stream()` before any stream request starts and uses `submit()` / `check_status()` / `get_result()`.
- Real stream errors are failures. Do not retry/fallback to non-stream after a stream request has started. Wrap the `async for` body, not just the `generate_content_stream(...)` call - mid-iteration errors fire there.
- Non-stream `submit()` performs one-shot `generate_content`. `check_status()` returns completed immediately. `get_result()` extracts answer text (concatenating non-thought parts), separately collects thought parts as `## Reasoning` content, reads `grounding_metadata.grounding_chunks` once, dedupes by URL, and appends `## Sources`.
- Citation URLs are rendered **verbatim** as the `vertexaisearch.cloud.google.com/grounding-api-redirect/<token>` URLs Gemini returns. Server-side redirect resolution is out of scope for v1 (Resolved Design Decision below).
- Known background-only guard: P24 must not implement or call Gemini deep-research / Interactions endpoints and must not add `deep-research-pro-preview-12-2025` (or any `*-deep-research-*` model) as a supported immediate model. P24 may recognize such IDs only to reject immediate-kind usage before any HTTP call with the existing generic `ModeKindMismatchError` suggestion. P28 owns background submission/polling.
- Error mapping uses `google.genai.errors.{APIError, ClientError, ServerError}` plus raw `httpx.{TimeoutException, ConnectError, RequestError}` (the SDK does NOT wrap client-side transport errors). Map by HTTP `code` and canonical `status`:
  - `code == 401` / `status == "UNAUTHENTICATED"` -> `APIKeyError`.
  - `code == 429` / `status == "RESOURCE_EXHAUSTED"` -> discriminate quota vs rate-limit by message substring and `error.details[].reason`. Treat as `APIQuotaError` if message contains `"per day"`, `"You exceeded your current quota"`, `"free tier"`, or details `reason` is `"FREE_TIER_LIMIT_EXCEEDED"`/quota-shaped; else `APIRateLimitError`.
  - `code == 400` / `status in {"INVALID_ARGUMENT", "FAILED_PRECONDITION", "OUT_OF_RANGE"}` -> `ProviderError` with model-hint extraction.
  - `code == 403` / `status == "PERMISSION_DENIED"` -> `ProviderError`.
  - `ServerError` (`500 <= code < 600`) -> `ProviderError` (5xx).
  - `httpx.TimeoutException` / `code == 504` / `status == "DEADLINE_EXCEEDED"` -> `ProviderError` flagged transient.
  - `httpx.ConnectError` / `httpx.RequestError` -> `ProviderError` flagged transient.
  - Bare `APIError` and unmapped exceptions -> `ProviderError` (catch-all).
  - All errors carry provider name `"gemini"`.
- Retry policy for non-stream `submit()` mirrors OpenAI/Perplexity precedent: tenacity `stop_after_attempt(3)`, `wait_exponential(multiplier=1, min=4, max=10)`, retrying `ServerError` with `code in {500, 503, 504}`, `httpx.TimeoutException`, `httpx.ConnectError`, `httpx.RemoteProtocolError`, AND `APIRateLimitError` (rate-limit 429 only - not `APIQuotaError`). Streaming failures are mapped but not retried after start.
- ToS compliance for grounding: `searchEntryPoint.renderedContent` is **not** rendered to stdout/file by P24. The CLI text-mode output cannot meaningfully display the embedded HTML widget, and the redirect URLs in `## Sources` already provide click-through attribution. Document this in the project file so future readers understand the omission.
- Auth: add `--api-key-gemini` to the shared root option surface and read `GEMINI_API_KEY` from env. Mirror P23's `--api-key-perplexity` plumbing exactly. Do not add Vertex AI / ADC support in P24.
- Update all user-facing provider surfaces that currently say Gemini is not implemented: provider list/model output, interactive provider menus, provider status/docstrings, and tests/specs that assert the old text. Audit `tests/baselines/providers_list.json` snapshot and regenerate.

Example advanced mode:

```toml
[modes.gemini_grounded_strict]
provider = "gemini"
model = "gemini-2.5-pro"
kind = "immediate"
system_prompt = "Answer with source-grounded factual context."

[modes.gemini_grounded_strict.gemini]
tools = ["google_search"]
thinking_budget = 4096
include_thoughts = true
temperature = 0.0

[[modes.gemini_grounded_strict.gemini.safety_settings]]
category = "HARM_CATEGORY_HARASSMENT"
threshold = "BLOCK_LOW_AND_ABOVE"
```

### Out of scope

- Gemini async/background API endpoints (Interactions API at `/v1beta/interactions`, deep-research) and polling - P28.
- Implementing `deep-research-pro-preview-12-2025` - P28. P24 only rejects it on immediate paths.
- Vertex AI deployment / Application Default Credentials. P24 is API-key-only.
- Gemini 3.x preview models (`gemini-3-flash-preview`, `gemini-3.1-pro-preview`, etc.). GA-only for built-in modes; users can opt in via `--model` passthrough but P24 does not pre-register or test preview models.
- Server-side resolution of `vertexaisearch.cloud.google.com/grounding-api-redirect/...` URLs to canonical source URLs. Sources block renders the redirect URLs verbatim. (Tracked as a follow-up enhancement.)
- Display of `searchEntryPoint.renderedContent` HTML widget. P24 omits it from CLI output. (Documented above; ToS allows omission - the requirement is "must display verbatim *if* surfaced".)
- Multimodal input (images, audio, video). Text-only request payloads.
- Function-calling / tool use beyond `google_search` grounding. No multi-turn `thoughtSignature` round-trip in P24.
- Provider implementation refactor across providers - P25.
- VCR replay coverage for Gemini sync - separate follow-up project (analog of P38 for Perplexity).

### Resolved Design Decisions

- Use the official `google-genai` SDK (>= 1.74.0), not Gemini's OpenAI-compat endpoint. Reason: OpenAI-compat omits grounding metadata, thought parts, and the thinking-budget knob - the features that motivate using Gemini for the `_reasoning` and grounded built-in modes.
- Built-in mode triple uses GA models only: `gemini-2.5-flash-lite` for `quick`, `gemini-2.5-pro` for both `pro` and `reasoning`. The `pro` vs `reasoning` distinction is a config flag (`include_thoughts` + thinking budget), not a separate model SKU - Gemini does not ship a `*-reasoning-pro` analog.
- Reasoning rendering uses the structured `Part.thought` flag, not a `<think>...</think>` segmenter. P24 emits `StreamEvent("reasoning", part.text)` directly when `part.thought is True`. The `## Reasoning` block in `_execute_immediate` is reused unchanged from P23.
- Citation URLs render verbatim as the Vertex redirect URLs Gemini supplies. Reasons: (1) zero out-of-band HTTP at render time, (2) redirect tokens are stable click-through (~30-day lifetime is fine for CLI session output), (3) Google explicitly designs the redirect as the canonical citation URL. Server-side resolution is a future enhancement, not a P24 blocker.
- Citation `title` falls back to `urlparse(uri).netloc` when `web.title` is absent or empty. Gemini commonly returns the bare domain as the title (e.g. `"uefa.com"`); the fallback covers the absent case.
- `--api-key-gemini` + `GEMINI_API_KEY` only. No Vertex/ADC. Reason: keeps the auth surface uniform across OpenAI/Perplexity/Gemini for `thoth ask`; Vertex is a different deployment model and would warrant its own project.
- Provider-specific request keys are namespaced under `gemini.*` and translated to `GenerateContentConfig` fields. Mirrors P23's `perplexity.*` namespacing convention.
- Use `google.genai.errors` exception classes plus raw `httpx` exceptions for the transport layer. Distinguish quota/credits exhaustion from ordinary 429 rate limiting via message substring + `error.details[].reason` heuristic, because Gemini's 429 emits a single `ClientError` for both cases.
- Add Gemini to both `extended` model-kind/runtime tests and weekly `live_api` workflow tests.
- Skip `searchEntryPoint.renderedContent` display in v1. ToS only requires display *if* surfaced; CLI text output cannot meaningfully render embedded HTML.
- Keep the known `*-deep-research-*` immediate guard, using the generic `ModeKindMismatchError` suggestion (mirrors P23's `sonar-deep-research` guard).
- Do not retry mid-stream errors after stream start. Mirrors P23 / OpenAI precedent.

### Cross-provider parity matrix

Distilled from a `factor-dedup` pass over `src/thoth/providers/openai.py` (immediate path) and `src/thoth/providers/perplexity.py` (full file). Used at implementation time to verify nothing is forgotten and at review time to confirm symmetry. Full classification + drift bookkeeping lives in [planning/p24-immediate-providers-consolidation.v1.md](../planning/p24-immediate-providers-consolidation.v1.md).

| # | Capability | OpenAI today | Perplexity today | P24 (Gemini) plan |
|---|---|---|---|---|
| 1 | Default model when none configured | `"o3"` (`openai.py:152`) | `"sonar"` (`perplexity.py:226`) | `"gemini-2.5-flash-lite"` |
| 2 | `is_implemented()` | True (inherited) | True (explicit) | True (explicit) |
| 3 | Supported sync model whitelist | Hardcoded 3 + dynamic SDK merge (`openai.py:626-673`) | Enumerated 3 (`perplexity.py:242-251`) | Enumerated 2 (`gemini-2.5-flash-lite`, `gemini-2.5-pro`) |
| 4 | System-prompt rendering | `role="developer"` input message (`openai.py:211-217`) | `{"role":"system", "content": ...}` (`perplexity.py:268-273`) | `GenerateContentConfig.system_instruction` |
| 5 | Provider config namespace | NONE — flat `self.config.get(...)` | `[modes.X.perplexity]` → `extra_body` (`perplexity.py:282-294`) | `[modes.X.gemini]` → `GenerateContentConfig` fields |
| 6 | Direct-SDK-keys allowlist constant | none — distributed in `_submit_with_retry` (drift) | `_DIRECT_SDK_KEYS` (`perplexity.py:211-217`) — drift: bare name, no provider suffix | `_DIRECT_SDK_KEYS_GEMINI`. Follow-up renames Perplexity's to `_DIRECT_SDK_KEYS_PERPLEXITY` and adds `_DIRECT_SDK_KEYS_OPENAI` for uniformity. |
| 7 | Provider-name constant | inline literal `"openai"` (drift) | `_PROVIDER_NAME = "perplexity"` (`perplexity.py:102`) — drift: bare name, no provider suffix | `_PROVIDER_NAME_GEMINI = "gemini"`. Follow-up renames Perplexity's to `_PROVIDER_NAME_PERPLEXITY` and adds `_PROVIDER_NAME_OPENAI` for uniformity. |
| 8 | Sources-block sanitization | RAW (`f"- [{title}]({url})"` at `openai.py:614-622`) — known security gap | `md_link_title` + `md_link_url` (`perplexity.py:463`) | `md_link_title` + `md_link_url` (mandatory) |
| 9 | `stream()` emits `text` | YES | YES | YES |
| 10 | `stream()` emits `reasoning` | NO (Responses API limitation; reasoning surfaced only at `get_result`) | YES via `_ThinkStreamParser` on `*-reasoning-*` models | YES via `Part.thought is True` flag |
| 11 | `stream()` emits `citation` | NO (annotations harvested at `get_result`) | YES from terminal-chunk `search_results`, deduped by URL | YES from terminal-chunk `grounding_metadata.grounding_chunks`, deduped by URL |
| 12 | `stream()` emits `done` | YES | YES | YES |
| 13 | Cumulative-content guard in stream | NO (Responses API gives true deltas) | YES (`perplexity.py:388-393`) | NO (`google-genai` gives true deltas; verify empirically during T03) |
| 14 | Retry decorator (tenacity) | `stop_after_attempt(3)`, `wait_exponential(min=4, max=10)`, `(APITimeoutError, APIConnectionError)`, reraise | identical | identical, but retry-class set is `(httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError, ServerError-with-code-{500,503,504}, APIRateLimitError)` — see delta #4 below |
| 15 | Stream not retried after start | YES | YES | YES |
| 16 | Kind-mismatch guard pattern | `_validate_kind_for_model` called from submit + stream entries | identical | identical |
| 17 | `ModeKindMismatchError` re-raise unmapped | YES | YES | YES |
| 18 | Auth-invalid-vs-missing distinction | substring check on `"incorrect api key"` (`openai.py:73-80`) | `_INVALID_KEY_PHRASES` constant (`perplexity.py:103`) | `_INVALID_KEY_PHRASES_GEMINI` constant matching common Gemini auth-rejection phrases |
| 19 | Auth-invalid `exit_code` | DEFAULT (drift — should be 2) | `exit_code=2` | `exit_code=2` |
| 20 | Quota-vs-rate-limit discriminator | string-marker classifier (`openai.py:36-59`, ~9 keywords) | string-marker classifier (`perplexity.py:106-129`, ~8 keywords) | string-markers PLUS `details[].reason` JSON inspection (Gemini exposes `RATE_LIMIT_EXCEEDED` reason structurally) |
| 21 | `NotFoundError` model-hint mapping | YES (`openai.py:87-93`) | NO (drift — falls through to APIError) | YES (`ClientError(404, NOT_FOUND)` → ProviderError with hint) |
| 22 | `unsupported parameter` regex extraction | YES (`r"'(\w+)'"` at `openai.py:95-113`) | NO (drift) | YES (same regex applied to `INVALID_ARGUMENT 400` messages) |
| 23 | Empty-content debug-print on `verbose=True` | YES (`openai.py:567-588`) | NO (drift) | NO — does not translate to `google-genai` response shape; verbose only attaches `raw_error` |
| 24 | Retry on rate-limit | NO (rate-limit not in retry-class set) | NO | YES — `APIRateLimitError` in retry-class set (Gemini-specific delta — quota is excluded; rate-limit is included per Google's official 429-handling guidance) |
| 25 | `reconnect` / `cancel` overrides | YES (background path) | NOT overridden (Perplexity has NO async cancel API) | NOT overridden (P24 is immediate-only; P28 owns Gemini background) |
| 26 | `## Reasoning` rendering target | non-stream `get_result` only (prepended `## Reasoning Summary`) | streaming side-channel (interleaved with text via `_ThinkStreamParser`) | both — streaming side-channel via `Part.thought=True`; non-stream `get_result` aggregates thought parts into `## Reasoning` |

### Provider-specific deltas vs unified target surface

Places where Gemini's API forces P24 to diverge from a pure mirror — captured here so reviewers can audit each delta against the API research.

1. **No `<think>` parser; structured `Part.thought` flag instead.** Gemini returns reasoning as separate `Part` objects with `thought=True`, not as `<think>...</think>` delimited text. P24's `stream()` MUST NOT introduce a stateful `_ThinkStreamParser` analog — it walks `parts` and dispatches by `part.thought`. This is API-shape, not drift.
2. **`thinking_budget` knob name varies across model generations.** 2.5 family uses `thinkingBudget` (int 0–32768, `-1`=dynamic); 3.x family uses `thinkingLevel` (`minimal|low|medium|high`). P24 targets 2.5 only (GA), so built-in modes set `thinkingBudget`; passthrough under `[modes.X.gemini]` accepts either name and routes correctly.
3. **`include_thoughts=True` required to surface reasoning.** Without it, the model still thinks but does not return thought summaries. `gemini_reasoning` built-in mode sets it; `gemini_quick` and `gemini_pro` do not.
4. **Retry-class set is wider than OpenAI/Perplexity.** Gemini's `google-genai` SDK does NOT wrap client-side transport errors — `httpx.{TimeoutException, ConnectError, RemoteProtocolError}` leak through raw alongside the SDK's own `ServerError`. P24 retries: `httpx.{TimeoutException, ConnectError, RemoteProtocolError}` + `ServerError` with `code in {500, 503, 504}` + `APIRateLimitError` (Google's documented 429-rate-limit guidance). Quota-exhausted `APIQuotaError` is NOT retried.
5. **Quota discriminator is structural in addition to string-marker.** Gemini emits `error.details[].reason` (e.g. `"RATE_LIMIT_EXCEEDED"`, `"FREE_TIER_LIMIT_EXCEEDED"`); inspect that field first, fall back to message-substring matching. OpenAI/Perplexity discriminators are string-only because their APIs don't expose this field.
6. **Citation URLs are Vertex redirects, not canonical.** Gemini's `groundingChunks[i].web.uri` is always `https://vertexaisearch.cloud.google.com/grounding-api-redirect/<token>`. P23/Perplexity returns canonical URLs. v1 renders verbatim (Resolved Design Decision); canonical resolution is a follow-up enhancement.
7. **`title` fallback to URL netloc.** Gemini commonly returns the bare domain as `web.title` (e.g. `"uefa.com"`); the `Citation(title, url)` projection falls back to `urlparse(uri).netloc` when `web.title` is empty. OpenAI/Perplexity falls back to the full URL. Minor cosmetic delta in the `## Sources` block.
8. **Grounding enabled per built-in mode via `tools=[Tool(google_search=GoogleSearch())]`.** Perplexity bakes web search into the model itself (`sonar` family is grounded by default); OpenAI Responses API uses `tools=[{type:"web_search_preview"}]` only on background deep-research. Gemini requires explicit per-mode opt-in for grounded immediate calls.
9. **`searchEntryPoint.renderedContent` ToS obligation.** If P24 ever surfaced this field, ToS would require displaying it verbatim. P24 omits it from CLI text output; this satisfies the "must display *if* surfaced" reading.

### Tests & Tasks

- [x] [P24-TS01] Add failing built-in mode and request-construction tests. Mock `genai.Client(...).aio.models.generate_content_stream` and `generate_content`; assert exact `model`, `contents` shape, `config.system_instruction`, `config.tools` (containing `Tool(google_search=GoogleSearch())` for built-ins), `config.thinking_config.thinking_budget`, `config.thinking_config.include_thoughts`, namespace passthrough from `[modes.X.gemini]` for `safety_settings` / `temperature` / `top_p` / `max_output_tokens` / `stop_sequences` / `response_mime_type` / `response_json_schema`, and `system_prompt` as `system_instruction`. Cover Pro defaults (`thinking_budget=-1`), Flash-Lite defaults (`thinking_budget=0`), and reasoning mode (`include_thoughts=True`). Assert `_DIRECT_SDK_KEYS_GEMINI` constant exists at module top and contains the documented native-kwarg set.
- [x] [P24-T01] Add the three built-in Gemini modes and implement Gemini request construction. Add `google-genai>=1.74.0` to `pyproject.toml`. Define `_DIRECT_SDK_KEYS_GEMINI` and `_PROVIDER_NAME_GEMINI` module-level constants. Make P24-TS01 pass.

- [x] [P24-TS02] Add failing `_map_gemini_error` and retry tests using `google.genai.errors` exception objects and `httpx` exception objects. Cover: `ClientError(401)` invalid-key (matched by `_INVALID_KEY_PHRASES_GEMINI`) -> bare `ThothError("Gemini API key is invalid", exit_code=2, hint=...)`; `ClientError(401)` missing-key -> `APIKeyError("gemini")`; `ClientError(429)` per-minute message -> `APIRateLimitError`; `ClientError(429)` per-day / quota-exhausted message -> `APIQuotaError`; `ClientError(429)` with `details.reason="RATE_LIMIT_EXCEEDED"` -> `APIRateLimitError`; `ClientError(400, INVALID_ARGUMENT)` with offending-parameter regex extraction (`r"'(\w+)'"`); `ClientError(404, NOT_FOUND)` -> `ProviderError("gemini", "Model {model!r} not found...")` with `models` CLI hint; `ClientError(403, PERMISSION_DENIED)`; `ServerError(500/503/504)`; raw `httpx.TimeoutException`; raw `httpx.ConnectError`; bare `APIError`; raw unknown `Exception` fallback. Add non-stream retry-count assertions for `httpx.TimeoutException`, `httpx.ConnectError`, `ServerError(503)`, and `APIRateLimitError` (each retried up to 3 attempts); assert no retry on `APIKeyError` and on `APIQuotaError`. Assert every mapped error carries `provider="gemini"` (using the `_PROVIDER_NAME_GEMINI` constant).
- [x] [P24-T02] Implement `_map_gemini_error(...)` and non-stream retry policy. Include the 12-class branch shape (auth-invalid / auth-missing / rate-limit / quota / not-found / bad-request-with-regex-extraction / permission-denied / 5xx / httpx-timeout / httpx-connect / APIError / generic catch-all). Make P24-TS02 pass.

- [x] [P24-TS03] Add failing provider stream tests for Gemini chunk translation. Cover: text-part deltas -> `StreamEvent("text", ...)`; `Part.thought=True` parts -> `StreamEvent("reasoning", ...)` and stripped from final answer text; mixed text+thought parts within a single chunk emitted in part-order; terminal-chunk `grounding_metadata.grounding_chunks` -> deduped `StreamEvent("citation", Citation(...))` events; `web.title` absent -> `Citation.title = netloc(uri)`; `web` absent (image/maps/retrievedContext oneof) skipped; missing `grounding_metadata` tolerated (no citation events); terminal `done` always emitted; mid-iteration `ClientError(400)` raised through to caller (no retry mid-stream); non-empty `searchEntryPoint.renderedContent` ignored without raising.
- [x] [P24-T03] Implement `GeminiProvider.stream()`. Make P24-TS03 pass. Errors mapped through `_map_gemini_error`.

- [x] [P24-TS04] Add failing executor/sink tests confirming Gemini's side-channel events flow through unchanged P23-shipped `_execute_immediate`. Use a fake provider emitting `text` + `reasoning` + `citation` + `done` events; assert stdout, file-only, tee, and project-persisted output all contain the same rendered answer, `## Reasoning` section, and `## Sources` section. (This is regression coverage for the Gemini-specific event shapes; the executor itself is not modified.)
- [x] [P24-T04] Verify `_execute_immediate` produces correct output for Gemini event shapes; if any divergence is found from P23 behavior, narrow the fix to the executor change rather than to the Gemini provider. Make P24-TS04 pass.

- [x] [P24-TS05] Add failing non-stream opt-out tests. Cover `stream = false` skipping `provider.stream()` entirely, calling `submit()` / `check_status()` / `get_result()`, appending sources from `grounding_metadata` rendered with `md_link_title()` / `md_link_url()` sanitization helpers, separating `Part.thought` content into `## Reasoning`, and preserving fallback behavior where `NotImplementedError` from `stream()` falls back but other stream errors fail. Include adversarial title/URL inputs (HTML in title, `javascript:` scheme in URL) and assert sanitization defends against injection.
- [x] [P24-T05] Implement explicit `stream = false` handling and Gemini `submit()` / `check_status()` / `get_result()` one-shot behavior. Use `md_link_title()` / `md_link_url()` from `thoth.utils` for the `## Sources` block. Make P24-TS05 pass.

- [x] [P24-TS06] Add failing kind-mismatch tests for Gemini deep-research model IDs with `kind = "immediate"`. Assert `ModeKindMismatchError` fires before any HTTP call for `deep-research-pro-preview-12-2025` and any `*-deep-research-*` substring match, and uses the existing generic config-edit suggestion. Plain `gemini-2.5-pro` / `gemini-2.5-flash-lite` are still allowed.
- [x] [P24-T06] Implement Gemini kind-mismatch guard. Make P24-TS06 pass. Mirror P23/OpenAI's `_validate_kind_for_model()` shape.

- [x] [P24-TS07] Add failing CLI auth tests. Cover `--api-key-gemini sk-...` accepted by research commands, rejected by non-research subcommands (root-option policy); `GEMINI_API_KEY` env var honored; key never appears in stdout/stderr/logs (extend `assert_no_secret_leaked` to redact `GEMINI_API_KEY`).
- [x] [P24-T07] Implement `--api-key-gemini` in the shared root option surface and thread it through `cli.py`, `cli_subcommands/ask.py`, `run.py`, `create_provider()`, and the inherited root-option policy. Make P24-TS07 pass. Mirror P23-T01 / P23-R02.

- [x] [P24-TS08] Add failing provider-registry, model-listing, and user-facing surface tests. Cover `GeminiProvider.is_implemented()`, default model `gemini-2.5-flash-lite`, supported sync model list (`gemini-2.5-flash-lite`, `gemini-2.5-pro`), provider list output without "(not implemented)", interactive provider menus, and any legacy tests/spec assertions that freeze old not-implemented copy. Regenerate `tests/baselines/providers_list.json` snapshot.
- [x] [P24-T08] Flip Gemini implementation status and update user-facing provider surfaces. Make P24-TS08 pass. (Provider-list snapshot regenerated and interactive/menu copy updated under T07's commit; supported-sync-model-list coverage is provided by the registry surface tests and the regenerated `providers_list.json` baseline snapshot, which both freeze `gemini-2.5-flash-lite` and `gemini-2.5-pro` as the supported sync set.)

- [x] [P24-TS09] Add failing live/extended coverage. Add Gemini immediate models to `KNOWN_MODELS` (auto-derives from `BUILTIN_MODES`); narrow or remove any current Gemini skip in `tests/extended/test_model_kind_runtime.py`; add `tests/extended/test_gemini_real_workflows.py` under `@pytest.mark.live_api` for end-to-end `--api-key-gemini`, `--provider gemini --model gemini-2.5-flash-lite`, `--mode gemini_quick`, `--mode gemini_reasoning`, and tee `--out -,FILE`. Assert the `extended.yml` and `live-api.yml` workflows expose `GEMINI_API_KEY` to the gated collections; parse YAML (don't substring-scan, per P23-R10).
- [x] [P24-T09] Implement the extended and weekly live-api Gemini test coverage. Update `.github/workflows/extended.yml` and `.github/workflows/live-api.yml` to pass `GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}`. Add `live_gemini_env` fixture and `require_gemini_key()` helper to `tests/extended/conftest.py`. Extend `assert_no_secret_leaked` to redact `GEMINI_API_KEY`. Make P24-TS09 pass.

#### Core Gemini implementation closeout

- [x] [P24-T10] Gemini implementation closeout (after T01–T09 + the cross-provider extended tasks below). Run targeted pytest for new/changed tests, `just check`, `./thoth_test -r`, `just test-lint`, `just test-typecheck`, and the Gemini live-api command when `GEMINI_API_KEY` is available. Flip P24 to `[x]` only after the full gate passes — including the cross-provider extended tasks.

#### Cross-provider consistency (extended) — OpenAI & Perplexity normalization

These tasks are outside P24's narrow "implement Gemini" goal but were surfaced by the factor-dedup pass and folded into P24 per user decision 2026-05-03. They normalize OpenAI and Perplexity to the unified canonical surface defined in the **Cross-provider parity matrix**, so P24 ships with all three immediate providers consistent.

**OpenAI normalization:**

- [x] [P24-TS10] Add failing tests for OpenAI namespace migration. Cover: `[modes.X.openai]`-namespaced keys in mode TOML are translated to native SDK kwargs by the equivalent of `_build_request_params`; module-level `_DIRECT_SDK_KEYS_OPENAI: tuple[str, ...]` constant exists and contains the documented native-kwarg set; module-level `_PROVIDER_NAME_OPENAI = "openai"` constant exists and is referenced in every `_map_openai_error(...)` ThothError construction; backwards-compat read path emits a `DeprecationWarning` (one release cycle) when flat mode keys (`temperature`, `code_interpreter`, `max_tool_calls`) appear without the namespace; existing user mode TOMLs with flat keys continue to work during the transition. Include negative tests: a flat key that conflicts with a namespaced key prefers the namespaced value with a warning.
- [x] [P24-T11] Implement OpenAI namespace migration. Define `_DIRECT_SDK_KEYS_OPENAI` and `_PROVIDER_NAME_OPENAI` module-level constants. Refactor `_submit_with_retry` to read from `self.config.get("openai", {})` namespace; add backwards-compat fallback to flat keys with `warnings.warn(DeprecationWarning, ...)`. Replace the ~9 inline `"openai"` literals in `_map_openai_error` with `_PROVIDER_NAME_OPENAI`. Make P24-TS10 pass.

- [x] [P24-TS11] Add failing adversarial-input tests for OpenAI's `## Sources` block sanitization. Inputs include: HTML in title (`<script>alert(1)</script>`), `javascript:` scheme in URL, `data:` URI in URL, brackets and parens in title, control chars. Assert escapes match Perplexity's behavior under the same inputs.
- [x] [P24-T12] Backport `md_link_title()` and `md_link_url()` from `thoth.utils` to `openai.py:614-622`'s `## Sources` rendering. Replace the raw `f"- [{title}]({url})"` interpolation. Make P24-TS11 pass.

- [x] [P24-TS12] Add failing tests for OpenAI Responses API streaming side-channel events. Audit the API empirically (real or recorded fixture) to determine whether: (a) reasoning summary chunks are emitted as stream events vs only at `get_result` time; (b) annotation/citation chunks are emitted as stream events vs only at `get_result` time. If supported, assert `StreamEvent("reasoning", ...)` and/or `StreamEvent("citation", Citation(...))` are emitted with correct content and ordering. If NOT supported (Responses API limitation), assert `stream()` continues emitting only `text + done` and document this as the intentional outcome.
- [x] [P24-T13] Either wire reasoning + citation events through `openai.py:455-466`'s `stream()` (if TS12's audit shows the API supports them), or document the API limitation in `### Provider-specific deltas` of [P24's project file](../projects/P24-gemini-immediate-sync.md). Make P24-TS12 pass under whichever outcome the audit determined.

- [x] [P24-TS13] Add failing test asserting OpenAI's `_map_openai_error` invalid-key path raises `ThothError` with `exit_code=2`, matching Perplexity's `perplexity.py` behavior.
- [x] [P24-T14] Update `openai.py:73-80` to set `exit_code=2` on the invalid-key `ThothError` construction. Make P24-TS13 pass.

**Perplexity normalization:**

- [x] [P24-TS14] Add failing tests for Perplexity rename + missing error mappings. Cover: `_DIRECT_SDK_KEYS_PERPLEXITY` and `_PROVIDER_NAME_PERPLEXITY` constants exist (the bare `_DIRECT_SDK_KEYS` and `_PROVIDER_NAME` no longer exist); `openai.NotFoundError` raised at submit-time maps to `ProviderError("perplexity", "Model {model!r} not found...")` with the `models` CLI hint; `openai.BadRequestError` containing an offending-parameter hint (e.g. `"unsupported parameter 'top_logprobs'"`) extracts the parameter name via `r"'(\w+)'"` and surfaces a CLI-friendly hint. Decide via test fixtures whether the regex behavior is portable enough to share with OpenAI as a `_extract_unsupported_param(message: str) -> str | None` helper, or whether each provider keeps its own inline regex due to message-format divergence.
- [x] [P24-T15] Rename Perplexity constants (`_DIRECT_SDK_KEYS` → `_DIRECT_SDK_KEYS_PERPLEXITY`, `_PROVIDER_NAME` → `_PROVIDER_NAME_PERPLEXITY`) via mechanical `replace_all`. Add `openai.NotFoundError` → `ProviderError` mapping to `_map_perplexity_error` mirroring `openai.py:87-93`. Add `unsupported parameter` regex extraction to the `BadRequestError` branch. Either extract the regex helper to `thoth/providers/_helpers.py` (if TS14 found portable shapes) or document the divergence inline. Make P24-TS14 pass.

- [x] [P24-TS15] Add failing test asserting Perplexity's `verbose=True` path emits an empty-content debug print when `response.choices[0].message.content` is empty / null, mirroring `openai.py:567-588`'s pattern.
- [x] [P24-T16] Backport the empty-content debug-print pattern to `perplexity.py`'s `get_result()`. Use the same `model_dump_json` → `__dict__` → `repr` ladder. Make P24-TS15 pass.

**`[providers.X]` root-namespace passthrough investigation:**

- [-] [P24-TS16] Decided not to do here — PUNTed to a focused follow-up project. Aspirational tests landed as `@pytest.mark.skip` in `tests/test_provider_config.py` (`test_root_providers_namespace_*` + `test_mode_level_openai_temperature_overrides_root_providers_default`) so they can be un-skipped in the successor project. See `planning/p24-providers-root-namespace-investigation.v1.md`.
- [-] [P24-T17] Decided not to do here — investigation report at `planning/p24-providers-root-namespace-investigation.v1.md` documents the half-baked current behavior (root-level values like `[providers.openai].temperature` already flow through via the flat-key fallback but trigger a misleading `[modes.X.openai]` migration `DeprecationWarning`), explains why a clean SHIP requires schema design + cross-provider resolver changes (not just ~30 lines in `create_provider`), and recommends a successor project to ship the layering + warning fix together.

#### Post-ship follow-ups (deferred / reviewer-flagged)

These tasks emerged during P24 review (factor-dedup pass + spec/code-quality reviewers across all 19 implementation tasks). They were either explicitly punted (item 1: root-namespace, captured as `[-]` TS16/T17 above) or flagged by reviewers as out-of-P24-scope. None are correctness defects in P24's shipping contract — they are tracked here so the rationale and concrete file:line context stay close to the work that surfaced them, rather than disappearing into a successor project's scoping doc. Each task is independent; pick up in any order or bundle into a focused successor.

The original P24 contract (Tasks 1.1–7.1) shipped via PR #54 and met its goal: ship Gemini synchronous chat + close all 8 Bucket-3 findings from the factor-dedup consolidation pass. P24's trunk glyph reflects that follow-up work remains tracked here.

##### 2. OpenAI streaming handlers wired-but-dormant (request shape doesn't trigger them)

**What it is.** Task 6.1 (T13) shipped two new event-type handlers in `OpenAIProvider.stream()` (`src/thoth/providers/openai.py:545-572`) for cross-provider 4-kind parity: `response.reasoning_summary_text.delta` → `StreamEvent("reasoning", ...)` and `response.output_text.annotation.added` → `StreamEvent("citation", Citation(...))`. The handlers are correct and unit-tested but **never fire on real API calls** because `stream()`'s request shape (`openai.py:533-541`) opts out of the upstream features that produce these events.

**What's missing in the request.** The streaming `request_params` includes only `model`, `input`, and conditional `temperature`. Notably absent vs the non-stream `_submit_with_retry` (`openai.py:269`):
- `reasoning={"summary": "auto"}` — without this, the API doesn't generate reasoning summaries; `response.reasoning_summary_text.delta` events never fire.
- `tools=[{type: "web_search_preview"}]` (or similar) — without grounding tools, `response.output_text.annotation.added` events with `url_citation` annotations never fire.

**What to achieve.** Decide whether immediate-path streaming should opt into reasoning summaries and/or web-search grounding. Pros: parity with Perplexity/Gemini, surfaces reasoning live. Cons: cost (`web_search_preview` is billed per call), latency (the API waits for grounding), doubled output tokens (reasoning summaries are billed as output).

- [ ] [P24-TS17] Add a failing test asserting that, given `[modes.openai_reasoning].openai.reasoning_summary = "auto"`, the streaming request to `client.responses.stream(...)` includes `reasoning={"summary": "auto"}` in its kwargs. Assert symmetric for a `web_search` opt-in flag if added.
- [ ] [P24-T18] Implement the namespace passthrough: extend `_resolve_provider_config_value` consumers in `OpenAIProvider.stream()` to read `reasoning_summary` (e.g. `"auto"`) and a `web_search` flag from `[modes.X.openai]`, translating them into `request_params["reasoning"] = {"summary": ...}` and `request_params["tools"] = [...]` respectively. Define a built-in `openai_reasoning` mode (analog to `gemini_reasoning`) that sets `reasoning_summary = "auto"` by default. Add a `tests/extended/test_openai_real_workflows.py::test_openai_reasoning_emits_reasoning_section` live-api case asserting reasoning events appear when `--mode openai_reasoning` is used. Make P24-TS17 pass. See `planning/p24-openai-stream-audit.v1.md` and the inline caveat at `openai.py:501-510`.

##### 3. Perplexity flat-key reads not migrated to `[modes.X.perplexity]` namespace

**What it is.** OpenAI received the namespace migration in Task 3.1 (`src/thoth/providers/openai.py:195` `_resolve_provider_config_value` reads `self.config["openai"][key]` first, falls back to flat with `DeprecationWarning`). Perplexity has *partial* namespacing: bag-of-options keys (`web_search_options`, `stream_mode`, `search_recency_filter`) already use `[modes.X.perplexity]`, but **SDK-direct kwargs still read flat** at `src/thoth/providers/perplexity.py:493-497`:

```python
for key in _DIRECT_SDK_KEYS_PERPLEXITY:
    if key in self.config:
        params[key] = self.config[key]
```

`_DIRECT_SDK_KEYS_PERPLEXITY` (`perplexity.py:371-377`) lists: `max_tokens`, `temperature`, `top_p`, `stop`, `response_format`. Today, `[modes.X.perplexity].temperature = 0.5` does NOT reach the request — users must set it flat at the mode level (the old style).

**What to achieve.** Cross-provider symmetry. After this task, `[modes.X.perplexity].temperature` flows through the same way `[modes.X.openai].temperature` does, with a deprecation warning bridging one release for any user mode TOMLs still on flat keys.

- [ ] [P24-TS18] Add failing tests covering: `[modes.X.perplexity].temperature` reaches the request kwargs; flat `temperature` still works but emits `DeprecationWarning`; namespace value wins over flat with no warning when both present; framework-level keys (`kind`, `model`, `timeout`) stay flat without warning. Mirror `tests/test_provider_config.py:281-335`'s OpenAI shape exactly.
- [ ] [P24-T19] Add `_resolve_provider_config_value(key, default)` to `PerplexityProvider`, mirroring `openai.py:195-230`. Define `_FRAMEWORK_FLAT_KEYS_PERPLEXITY = {"perplexity", "kind", "model", "timeout"}`. Refactor the `_DIRECT_SDK_KEYS_PERPLEXITY` loop at `perplexity.py:493-497` to use the resolver. Update existing test fixtures using flat Perplexity `temperature` to use the namespace. Make P24-TS18 pass.

##### 4. Async sibling `_map_perplexity_error_async` missing NotFoundError + regex-extraction backports

**What it is.** `perplexity.py` has two error mappers documented as preserving "byte-identical wording" (`perplexity.py:151`):
- `_map_perplexity_error` (`perplexity.py:146-243`) — sync immediate path (uses OpenAI SDK)
- `_map_perplexity_error_async` (`perplexity.py:245+`) — background async path (uses raw httpx for `/v1/async/sonar`)

Tasks 2.3 and 2.4 added two branches to the **sync** mapper:
- `perplexity.py:175-181`: `openai.NotFoundError` → `ProviderError("perplexity", "Model X not found... thoth providers --models...")` with the CLI hint.
- `perplexity.py:188-198`: `openai.BadRequestError` with `_extract_unsupported_param(msg)` → `ProviderError("perplexity", "Perplexity does not support parameter 'X' for this model.")`.

The async mapper has neither. A user passing an invalid model on `--mode perplexity_deep_research` (background) gets the generic "HTTP 422 from Perplexity async API: <body excerpt>" message instead of the actionable model-name + CLI hint they'd get on the immediate path.

**What to achieve.** Restore the docstring's "byte-identical wording" claim. Both paths produce equally helpful errors when the same kind of failure occurs.

- [ ] [P24-TS19] Add failing tests against `_map_perplexity_error_async` that mirror the sync mapper's NotFoundError + unsupported-parameter assertions: a 404 response surfaces the model name + `thoth providers --models` hint; a 422 response with `"unsupported parameter 'X'"` in the body extracts X via `_extract_unsupported_param`.
- [ ] [P24-T20] Backport both branches to `_map_perplexity_error_async` (`perplexity.py:295-340`). For 404, produce `ProviderError("perplexity", "Model X not found...")` with the same CLI hint as the sync mapper. For the existing 422 path (already at `perplexity.py:309`), additionally try `_extract_unsupported_param(body_text)` and surface the offending parameter name when matched. Keep the docstring's "byte-identical wording" promise by mirroring the message strings exactly. Make P24-TS19 pass.

##### 5. Cross-provider duplication of `_render_sources` + `_debug_print_empty_response` (factor-dedup target)

**What it is.** Three providers now ship near-identical helpers for the same two purposes:

| Helper | OpenAI | Perplexity | Gemini |
|---|---|---|---|
| Empty-content debug ladder (`model_dump_json` → `__dict__` → `repr`) | `openai.py:592-611` (inline in `get_result`) | `perplexity.py:951-971` `_debug_print_empty_response()` | `gemini.py:532-550` `_debug_print_empty_response()` |
| Sources block rendering (deduped `## Sources` via `md_link_*`) | `openai.py:614-622` (inline in `get_result`) | `perplexity.py:973-1010` `_render_answer_with_sources()` | `gemini.py:511-530` `_render_sources()` |

Each helper is ~17-25 lines. The shape is the same (walk response → extract title+URL → dedupe by URL → render `- [{md_link_title(t)}]({md_link_url(u)})`) with subtle divergences in title-extraction logic, URL field name (`url` vs `uri`), and debug-ladder truncation (per-call `[:1000]` vs per-field `[:100]` vs none).

**What to achieve.** DRY. After Tasks 2.2 (`_invalid_key_thotherror`) and 2.4 (`_extract_unsupported_param`), `src/thoth/providers/_helpers.py` is the established home for cross-provider helpers. The third + duplicate of the same pattern is now load-bearing evidence for `factor-dedup` consolidation.

- [ ] [P24-TS20] Run `factor-dedup` over the three sites; document the divergences in a planning note. Pin the unified contract via tests in `tests/test_provider_helpers.py`: `render_sources_block(citations: Iterable[Citation]) -> str` produces correct deduped markdown; `debug_print_empty_response(response, provider_label) -> None` emits the truncated ladder to stderr.
- [ ] [P24-T21] Extract `render_sources_block` and `debug_print_empty_response` to `src/thoth/providers/_helpers.py`. Each provider's `get_result()` calls `render_sources_block(self._extract_citations(response))` and `debug_print_empty_response(response, "OpenAI" / "Perplexity" / "Gemini")`. Provider-specific code keeps only the *extraction* logic (which genuinely differs because chunk vocabularies differ: OpenAI annotation, Perplexity search_result, Gemini grounding_chunk.web). Make P24-TS20 pass. Estimated: ~50 lines added + ~50 lines removed across 3 providers + 6-8 tests refactored.

##### 6. OpenAI `_PROVIDER_NAME_OPENAI` unused at non-error sites (cosmetic cleanup)

**What it is.** Task 1.2 introduced `_PROVIDER_NAME_OPENAI = "openai"` at `src/thoth/providers/openai.py:49` and replaced 12 inline `"openai"` literals inside `_map_openai_error()` with the constant. But 4 inline literals remain *outside* the error mapper (verified by `grep -nE '"openai"' src/thoth/providers/openai.py | grep -v _PROVIDER_NAME_OPENAI`):

- `openai.py:189` — `self.model_cache = ModelCache("openai")`
- `openai.py:746,753,760` — `"owned_by": "openai"` entries in `list_models()`
- `openai.py:784` — `raise ProviderError("openai", f"Failed to fetch models: ...")` in `get_models()`

(The set literal at `openai.py:66` `{"openai", "kind", "model", "timeout", "background"}` is a hardcoded framework-keys allowlist, not a provider tag — leave alone.)

**What to achieve.** Single source of truth. Future-proof against any structural introspection of "what providers are registered" — having the literal repeated is a small future-trap.

- [ ] [P24-T22] Replace the 4 inline `"openai"` literals listed above with `_PROVIDER_NAME_OPENAI`. No new tests required — existing tests at `tests/test_openai_errors.py::test_openai_constants_use_suffix_naming` already pin the constant's value, so any reference-site swap that breaks string-equality is caught. Pure mechanical change, no behavior delta. Effort: ~5 minutes. (No TS pair — refactor is one-liner per site, covered by existing literal-equality tests.)

##### 7. OpenAI URL-citation type-string filter is presence-based, not type-based (robustness)

**What it is.** Task 6.1's stream-event handler for `response.output_text.annotation.added` (`src/thoth/providers/openai.py:551-572`) filters annotations to URL-citations by checking *whether the annotation has a `url` attribute*, not by checking its `type` discriminator:

```python
url = getattr(ann, "url", None) or (ann.get("url") if isinstance(ann, dict) else None)
if not url:
    continue
```

The OpenAI SDK ships at least 4 annotation variants (per the audit at `planning/p24-openai-stream-audit.v1.md`): `url_citation` (has `url`, `title`), `file_citation` (has `file_id`, `quote`), `file_path` (has `file_id`), `container_file_citation` (has `container_id`). Today the presence-based filter correctly drops the latter three because they don't have a `url` attribute. **But** if a future SDK ships, say, a `FileDownloadCitation` with both `file_id` AND a download `url`, it would be misclassified and emitted as a `StreamEvent("citation", Citation(...))` with a download URL — broken markdown link in user output.

`get_result()`'s existing filter at `openai.py:602-610` uses the same presence-based pattern, so streaming + non-stream are consistently lax (not asymmetric).

**What to achieve.** Robustness against SDK schema drift. Tighten both filters together so they degrade safely if a new annotation variant adds a `url` field.

- [ ] [P24-TS21] Add failing tests against both `OpenAIProvider.stream()` and `OpenAIProvider.get_result()` that simulate a hypothetical annotation variant with `type="file_download_citation"` AND a `url` field; assert the stream/get_result paths skip it (no `StreamEvent("citation", ...)` emitted; no `## Sources` line rendered).
- [ ] [P24-T23] Tighten both filters to use the explicit `type` discriminator: `ann_type = getattr(ann, "type", None) or (ann.get("type") if isinstance(ann, dict) else None); if ann_type != "url_citation": continue`. Apply at `openai.py:551-572` (streaming) AND `openai.py:602-610` (get_result) symmetrically. Make P24-TS21 pass.

##### 8. `_RESEARCH_OPTIONS` count test is a strict pin (documentation note)

**What it is.** `tests/test_p16_pr2_options_decorator.py:11-19` asserts the *exact count* of options in the shared `_RESEARCH_OPTIONS` decorator stack at `src/thoth/cli_subcommands/_options.py`. P24 Task 5.1 bumped it 26 → 27 because `--api-key-gemini` was added.

```python
assert len(_RESEARCH_OPTIONS) == 27, (
    f"expected 27 research-options entries (21 from PR2 + 2 from P18 Phase E + "
    f"1 from P21 + 1 from P18-T27 + 1 from P23 --model + 1 from P24 --api-key-gemini), "
    f"got {len(_RESEARCH_OPTIONS)}"
)
```

The pin pattern is intentional and useful — strict pins catch silent option drift (e.g., someone deleting `--cancel-on-interrupt` but forgetting to update docs) better than fuzzy "approximate count" tests. But it's a tripwire that needs to be acknowledged when adding options.

**What to achieve.** Make the convention discoverable. Future contributors adding a new shared root option need to: (1) add the option to `_RESEARCH_OPTIONS` in `_options.py`; (2) bump the count in the test; (3) append a one-line note to the test's comment explaining the new option's source project.

- [ ] [P24-T24] Add a one-paragraph `CONTRIBUTING.md`-style note (or a docstring on the test itself) explaining the strict-pin convention for `_RESEARCH_OPTIONS`. Cross-reference from `src/thoth/cli_subcommands/_options.py`'s module docstring so contributors find it before they trip over the test failure. No code change required; documentation only. (No TS pair — documentation work, no behavior to test.)

### Open questions

- **Citation URL rendering.** Verbatim Vertex redirect URLs (current default) vs server-side HEAD resolution to canonical URLs. v1 picks verbatim. Confirm or override before T03.
- **`pro` mode model choice.** Current pick: `gemini-2.5-pro`. Alternative: `gemini-2.5-flash` with `thinking_budget=-1` for a cheaper / faster mid-tier, reserving `gemini-2.5-pro` for `reasoning`. Confirm.
- **Per-mode thinking budget tuning.** Built-in modes hardcode `thinking_budget` (0 / -1 / -1). Should advanced users be able to override via `[modes.X.gemini].thinking_budget` only, or should there also be a `--thinking-budget` CLI flag? Current scope: namespace-only (no CLI flag). Confirm.
- **`searchEntryPoint.renderedContent` ToS interpretation.** Current scope: omit entirely. Verify with project owner that ToS "must display *if* surfaced" reading is correct (i.e. omission is compliant; only re-display would trigger the obligation).
- **Preview models exposure.** Should `--model gemini-3-flash-preview` (or similar) be allowed without a warning, blocked, or warned? Current scope: passthrough without local validation, mirroring P23. Confirm.

### Acceptance Criteria

- `thoth ask "What's new in CRISPR?" --mode gemini_quick` returns a grounded answer with a `## Sources` section using `gemini-2.5-flash-lite`.
- `thoth ask "What's new in CRISPR?" --provider gemini --model gemini-2.5-pro` returns a grounded answer with a `## Sources` section.
- `thoth ask "hello" --provider gemini --model future-model-id` passes the model string to Gemini without local compatibility validation; any invalid model error is surfaced from the provider/API layer.
- `thoth ask --mode gemini_reasoning ...` exposes thought-summary content separately from answer text in a `## Reasoning` block (no `<think>` tags appear in user-visible output).
- `thoth ask --provider gemini --model deep-research-pro-preview-12-2025 ...` with immediate kind raises `ModeKindMismatchError` before any HTTP call, with the existing generic suggestion.
- `stream = false` in Gemini mode config uses non-stream one-shot execution and still appends sources.
- stdout, file-only, tee, and project output contain the same final rendered answer/reasoning/sources for side-channel stream events.
- `--api-key-gemini sk-...` works without `GEMINI_API_KEY` in env; the key never appears in stdout/stderr/logs.
- Gemini is surfaced as implemented in provider listings, model listings, and interactive provider menus.
- Unit/provider/registry tests pass, and Gemini is covered in both extended model-kind tests and weekly live-api workflow tests.
- Quota-vs-rate-limit discriminator correctly classifies a per-day quota-exhaustion 429 as `APIQuotaError` and a per-minute throttling 429 as `APIRateLimitError`.

### Dependencies

- Live Gemini tests require `GEMINI_API_KEY`; CI must pass it from repo secrets into `extended` and `live_api` jobs; tests remain gated out of default pytest by markers.
- P24 depends on P23-shipped infrastructure: `--model` CLI plumbing, `_execute_immediate` side-channel rendering, `Citation` / `StreamEvent` types, `## Reasoning` / `## Sources` rendering, `APIRateLimitError` / `APIQuotaError` split. None of these are modified by P24.
- P24 has no dependency on P28 (background deep-research). P28 owns the Interactions API path and the `deep-research-pro-preview-12-2025` model.

### Definition of Done

- All P24 `TS##` and `T##` checkboxes are flipped.
- `is_implemented()` returns `True`; registry tests assert it.
- `tests/test_provider_gemini.py`, provider registry tests, executor/sink regression tests for Gemini event shapes, and relevant CLI option tests pass.
- `extended` collection includes Gemini immediate models, the CI workflow passes `GEMINI_API_KEY`, and tests skip only when that key is absent.
- `live_api` collection includes Gemini workflow tests, the CI workflow passes `GEMINI_API_KEY`, and tests skip only when that key is absent.
- Full local quality gate passes per `CLAUDE.md` / `AGENTS.md`.
- Trunk row flips to `[x]` only after the full gate passes.
