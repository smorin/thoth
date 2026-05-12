# Cross-immediate-providers consolidation spec (v1)

**Goal:** Document the canonical immediate-provider surface across `openai.py`, `perplexity.py`, and the upcoming `gemini.py` (P24). Classify drift across the existing two implementations as intentional vs accidental, and assign each accidental-drift fix to the recipient project that should land it.

**Generated:** 2026-05-03 by the `factor-dedup` skill running over `src/thoth/providers/{openai,perplexity}.py` immediate paths. Companion to [P24's project file](../projects/P24-gemini-immediate-sync.md), which embeds the **Cross-provider parity matrix** distilled from this spec.

**Skill output type:** consolidation spec (per `factor-dedup` Step 7) ready to feed to `superpowers:writing-plans` for executable plans.

## Implementations consolidated

- **`src/thoth/providers/openai.py`** (immediate path only — synchronous chat via Responses API; `_submit_with_retry` and `stream()` for non-`is_background_model` models). The dual-mode background path is excluded from this comparison.
- **`src/thoth/providers/perplexity.py`** (full file — immediate-only by design; P27 owns Perplexity background separately).
- **`src/thoth/providers/gemini.py`** (planned — P24 design captured in [P24's project file](../projects/P24-gemini-immediate-sync.md)).

## Method

Two `factor-comparator`-shape subagents dispatched in parallel against the two existing implementations, each producing a structured report on contract conformance, file structure, request construction, stream translation, non-stream path, error mapping, retry policy, kind-mismatch guard, edge cases, and caller assumptions — all with file:line citations.

The reports were collated into the three buckets the `factor-dedup` skill prescribes:

- **Bucket 1 — Truly identical** (consolidate freely; no decision needed).
- **Bucket 2 — Intentionally different** (document, don't consolidate).
- **Bucket 3 — Accidentally divergent** (per-finding walk; each may be a bug).

A user walk-through assigned each Bucket-3 finding to either *fix in P24*, *fix as a follow-up project*, or *skip*.

## Bucket 1 — Truly identical

| # | Capability | OpenAI / Perplexity reference |
|---|---|---|
| 1 | Tenacity retry decorator (`stop_after_attempt(3)`, `wait_exponential(multiplier=1, min=4, max=10)`, `reraise=True`) | `openai.py:198-203`, `perplexity.py:334-339` |
| 2 | No retry decorator on `stream()` | both |
| 3 | `_validate_kind_for_model` called from both `submit()` and `stream()` entry; raises `ModeKindMismatchError` BEFORE any HTTP attempt | `openai.py:160-180,190,429`, `perplexity.py:253-266,319,352` |
| 4 | `ModeKindMismatchError` re-raised UNMAPPED (excepted before generic catch) in error mappers | `openai.py:193-194`, `perplexity.py:322-323,358-359` |
| 5 | Quota-vs-rate-limit string-marker discriminator (lower-cased message + body inspection; `~9` keywords each, near-identical set: `insufficient_quota`, `quota`, `billing`, `credit(s)`, `monthly spend`, `exhausted`, `no credits`, `blocked`) | `openai.py:36-59`, `perplexity.py:106-129` |
| 6 | Job ID synthesis fallback when SDK response lacks `.id`: `f"{provider}-{YYYYMMDDHHMMSS}-{8hex}"` | `openai.py:258-262`, `perplexity.py:327-330` |
| 7 | `check_status` immediate shortcut returns `{"status": "completed", "progress": 1.0}` | `openai.py:285-286`, `perplexity.py:434-437` |
| 8 | Auth-invalid distinguished from auth-missing by phrase-substring check on the auth error body | `openai.py:73-80`, `perplexity.py:142-152` |

**P24 inheritance:** all 8 — direct mirror.

## Bucket 2 — Intentionally different (preserve, document)

| # | Capability | OpenAI | Perplexity | Why kept separate |
|---|---|---|---|---|
| 1 | Default model | `"o3"` | `"sonar"` | Provider-specific; no unification possible. |
| 2 | System-prompt rendering | `role="developer"` input message (Responses API quirk) | `{"role":"system", "content":...}` chat completion message | API-shape difference at the wire level. |
| 3 | Cumulative-content guard in stream | NO (Responses API gives true deltas) | YES (`perplexity.py:388-393`) | Defends against APIs that send cumulative state; Responses API doesn't need it. |
| 4 | `list_models()` shape | hardcoded 3 + dynamic SDK merge (`openai.py:626-673`) | enumerated 3 (`perplexity.py:242-251`) | Verified empirically (2026-05-03 web check): Perplexity's `/v1/models` returns the **Agent API** catalog (e.g. `perplexity/sonar`), not chat-completions IDs. The hardcoded chat-completions allowlist is the curated subset. |
| 5 | `reconnect()` / `cancel()` overrides | YES (background path uses both) | NOT overridden (`stream()` is the only path) | Verified empirically (2026-05-03 web check): Perplexity's async API has no DELETE/cancel endpoint. Cancel cannot be implemented for Perplexity background; immediate path has nothing to cancel. |

**P24 inheritance:** Gemini-flavored equivalent of each row — `gemini-2.5-flash-lite` default; `GenerateContentConfig.system_instruction`; no cumulative-content guard (verify empirically during T03); enumerated 2-model whitelist; `reconnect`/`cancel` not overridden in P24 (immediate-only — P28 owns Gemini background where Gemini's API natively supports cancel).

## Bucket 3 — Accidentally divergent (per-finding walk)

Each row has been walked with the user. Disposition column shows the agreed action; **Recipient project** column shows where the work lands.

| # | Finding | OpenAI today | Perplexity today | Disposition | Recipient project |
|---|---|---|---|---|---|
| 3a | Provider config namespace | NONE — flat `self.config.get(...)` | `[modes.X.perplexity]` → `extra_body` | **Fix in BOTH places**: Gemini adopts `[modes.X.gemini]` (P24 core); OpenAI migrated to `[modes.X.openai]` with backwards-compat deprecation. Plus: investigate `[providers.X]` root-namespace passthrough for default settings. | P24 — TS01/T01 (Gemini), TS10/T11 (OpenAI), TS16/T17 (root-namespace) |
| 3b | Sources-block sanitization | RAW `f"- [{title}]({url})"` (`openai.py:614-622`) — **security gap** | `md_link_title()` + `md_link_url()` (`perplexity.py:463`) | **Fix in BOTH places**: Gemini uses sanitized helpers (P24 core); OpenAI backports. | P24 — TS05/T05 (Gemini), TS11/T12 (OpenAI) |
| 3c | `stream()` emits `reasoning` and `citation` events | NO (only `text` + `done`) | YES (both) | **Investigate + close gap if API supports it**: P24 emits both (Gemini's API supports both natively). For OpenAI, audit the Responses API to determine whether reasoning summary chunks and annotation chunks can be surfaced during `stream()` vs only at `get_result()`. If the API supports them, wire them through; if not, document as intentional API limitation. | P24 — TS03/T03 (Gemini), TS12/T13 (OpenAI audit + outcome) |
| 3d | `NotFoundError` model-hint mapping | YES (`openai.py:87-93`) | NO (drift — falls through to `APIError`) | **Fix in both**: Gemini maps `ClientError(404, NOT_FOUND)` (P24 core); Perplexity backports. | P24 — TS02/T02 (Gemini), TS14/T15 (Perplexity) |
| 3e | `unsupported parameter` regex extraction | YES (`r"'(\w+)'"` at `openai.py:95-113`) | NO (drift) | **Fix in both**: Gemini extracts on `INVALID_ARGUMENT 400` (P24 core); Perplexity backports. **Helper-extraction analysis:** worth attempting — both providers receive an OpenAI-shape error body with a parameter name in single quotes; a shared `_extract_unsupported_param(message: str) -> str \| None` helper in `thoth.providers._helpers` could deduplicate. **Caveat:** Gemini's error body comes from `google.genai.errors.ClientError`, not the OpenAI SDK, so the message format may differ subtly. Decide during T15 implementation whether shapes overlap enough to share. | P24 — TS02/T02 (Gemini), TS14/T15 (Perplexity + helper decision) |
| 3f | `_DIRECT_SDK_KEYS` constant | NONE (logic distributed in `_submit_with_retry`) | `_DIRECT_SDK_KEYS` constant — bare name, no provider suffix (`perplexity.py:211-217`) | **Fix in all three** with uniform naming convention `_DIRECT_SDK_KEYS_<PROVIDER>`: Gemini defines `_DIRECT_SDK_KEYS_GEMINI` (P24 core); OpenAI introduces `_DIRECT_SDK_KEYS_OPENAI` (new); Perplexity renames bare `_DIRECT_SDK_KEYS` → `_DIRECT_SDK_KEYS_PERPLEXITY` (`replace_all` mechanical rename). | P24 — TS01/T01 (Gemini), TS10/T11 (OpenAI), TS14/T15 (Perplexity rename) |
| 3g | Auth-invalid `exit_code` | DEFAULT (drift) | `exit_code=2` | **Fix in both**: Gemini sets `exit_code=2` (P24 core); OpenAI aligned. | P24 — TS02/T02 (Gemini), TS13/T14 (OpenAI) |
| 3h | Empty-content debug-print on `verbose=True` | YES (`openai.py:567-588`) | NO (drift) | **Backport to Perplexity** (and Gemini if applicable): Add the empty-content debug-print pattern to Perplexity. For Gemini, evaluate during T05 whether `response.text` empty + diagnostic info available shape applies. | P24 — TS15/T16 (Perplexity); Gemini evaluated during T05 |
| 3f-bis | `_PROVIDER_NAME` constant | inline literals (`"openai"` repeated ~9 times in `_map_openai_error`) | `_PROVIDER_NAME = "perplexity"` — bare name, no provider suffix (`perplexity.py:102`) | **Fix in all three** with uniform naming convention `_PROVIDER_NAME_<PROVIDER>`: Gemini defines `_PROVIDER_NAME_GEMINI = "gemini"` (P24 core); OpenAI introduces `_PROVIDER_NAME_OPENAI = "openai"` (new — replaces the ~9 inline literals); Perplexity renames bare `_PROVIDER_NAME` → `_PROVIDER_NAME_PERPLEXITY` (`replace_all` mechanical rename). **Reverses prior "skip OpenAI cosmetic" call** per user directive — uniformity wins over churn-avoidance for grep + future cross-provider helper extraction. | P24 — TS01/T01 (Gemini), TS10/T11 (OpenAI), TS14/T15 (Perplexity rename) |

## Unified canonical surface (target for all three immediate providers)

After Bucket-3 fixes land, every immediate provider in `src/thoth/providers/` MUST satisfy this surface:

1. **Module-level constants**, suffix-named for uniform repo-wide grep'ability: `_PROVIDER_NAME_<PROVIDER>: str` (matching the registry key); `_DIRECT_SDK_KEYS_<PROVIDER>: tuple[str, ...]` (allowlist of native SDK kwargs). Naming convention: provider name in UPPER_SNAKE_CASE matches the dict key in `PROVIDERS` (`openai`, `perplexity`, `gemini`).
2. **Provider config namespace**: `[modes.X.<provider>]` keys translated to native SDK request fields. Anything in `_DIRECT_SDK_KEYS_<NAME>` is a top-level kwarg; everything else is provider-extension passthrough.
3. **Class methods** (subset of `ResearchProvider`):
   - `__init__(api_key, config)` — store key + config.
   - `is_implemented() -> bool` — explicitly returns True (don't rely on base inheritance).
   - `_validate_kind_for_model(mode)` — raises `ModeKindMismatchError` BEFORE any HTTP if `config["kind"] == "immediate"` and the model is background-only.
   - `_build_messages(prompt, system_prompt) -> ...` — provider-native shape.
   - `_build_request_params(...) -> dict` — assembles native kwargs + provider-extension passthrough.
   - `submit(...)` — wraps `_submit_with_retry`; re-raises `ModeKindMismatchError` unmapped before mapping other errors.
   - `_submit_with_retry(...)` — tenacity-decorated; retry-class set is provider-specific (timeout + connect at minimum; rate-limit if Google-style guidance applies).
   - `stream(...)` — emits `text` + `reasoning` (if API supports it) + `citation` (if API supports it) + `done`. Mid-stream errors map through provider error mapper; stream NOT retried after start.
   - `check_status(job_id)` — returns `{"status": "completed", "progress": 1.0}` for known immediate jobs.
   - `get_result(job_id, verbose)` — renders text + optional `## Reasoning` + optional `## Sources` (using `md_link_title` / `md_link_url` sanitization).
   - `list_models()` — provider-specific (enumerated allowlist or dynamic + hardcoded merge).
4. **Module-level error mapper** `_map_<provider>_error(exc, model, verbose) -> ThothError`:
   - 12-class branch shape: auth-invalid (with `exit_code=2`) / auth-missing → `APIKeyError` / rate-limit → `APIRateLimitError` / quota → `APIQuotaError` / not-found → `ProviderError` with `models` CLI hint / bad-request with offending-parameter regex extraction → `ProviderError` with hint / permission-denied / 5xx → `ProviderError` / timeout (transient) / connection (transient) / `APIError` (catch-all SDK) / generic `Exception` fallback.
   - Every constructed error carries `provider=_PROVIDER_NAME`.
   - `ModeKindMismatchError` re-raised UNMAPPED.
5. **Sanitization**: every `## Sources` block uses `md_link_title()` and `md_link_url()` from `thoth.utils`. Never raw `f"- [{title}]({url})"` interpolation.
6. **Verbose flag**: attaches `raw_error` to mapped exceptions; emits empty-content diagnostic when `response.text` (or equivalent) is unexpectedly empty.

## Risks

- **OpenAI namespace migration is a behavior-changing refactor.** Existing config files / mode TOMLs that use flat `temperature` / `code_interpreter` / `max_tool_calls` keys at the mode top level will need a backwards-compatible read path during transition (read from both flat and nested for one release; deprecate flat with a warning). Otherwise this breaks any user with custom modes — which the codebase has shipped for several P##s.
- **Responses API stream-event audit (3c-OpenAI) may conclude "API doesn't support it during stream".** That's an acceptable outcome — the spec then documents the gap as intentional rather than forcing an unsupported shape.
- **Shared helper extraction (3e) may not be worth it.** The two providers' error message shapes are similar but not identical; a too-generic helper may obscure provider-specific quirks. Decide during implementation, not now.
- **`[providers.X]` root-namespace investigation (new directive)** is greenfield work — no existing scaffold for default-settings passthrough beyond `api_key`. Out of scope for the consolidation work itself; tracked as a separate sub-investigation.

## Suggested sequencing

1. **NEW follow-up project (placement TBD — see below):**
   - Migrate OpenAI to `[modes.X.openai]` namespace with backwards-compat read path; introduce `_DIRECT_SDK_KEYS_OPENAI`.
   - Backport `md_link_*` sanitization to OpenAI's `## Sources` rendering (security fix; should be highest priority within this project).
   - Audit OpenAI Responses API for reasoning + citation streaming feasibility; either wire through or document.
   - Backport `NotFoundError` mapping + `unsupported parameter` regex extraction (with helper-extraction decision) to Perplexity.
   - Backport `exit_code=2` to OpenAI auth-invalid path; ensure all three are aligned.
   - Backport empty-content debug-print to Perplexity.
   - Investigate `[providers.X]` root-namespace passthrough for default settings.
2. **P24 (Gemini implementation)** — already scoped; can land independently of (1) but should ideally land AFTER OpenAI namespace migration so all three providers ship consistent. Acceptable to land before if (1)'s scope expands.
3. **P25 (post-3-providers cleanup)** — runs after both (1) and (2) ship. Re-evaluate what's left to consolidate (likely shared helpers, test fixtures, `_extract_unsupported_param` decision if deferred).

## Placement decision

**User chose Option C (2026-05-03)**: fold the cross-provider consistency fixes into P24 itself rather than spinning up a sibling project. The work is scoped under a clearly-labeled `### Tests & Tasks` subsection — `Cross-provider consistency (extended) — OpenAI & Perplexity normalization` — so reviewers can distinguish core-Gemini tasks (TS01–TS09 + T01–T10) from cross-provider work (TS10–TS16 + T11–T17).

**Implications**:
- P25 keeps its original placeholder mandate ("Architecture Review & Cleanup — Immediate Providers" — runs after all three are in place; re-evaluates what's left to consolidate, e.g. shared helper extraction).
- P24's blast radius is wider than originally scoped: it now touches `openai.py`, `perplexity.py`, plus the new `gemini.py`. This raises review burden but ships normalization atomically with the new provider.
- Backwards-compat risk concentrates in P24-T11 (OpenAI namespace migration with deprecation warning) — affects any user with custom mode TOMLs using flat keys.

Original options (preserved for traceability):
- Option A — Re-scope P25 to be the cross-provider consolidation. Rejected: user wants the work bundled with P24.
- Option B — New project P39. Rejected: user wants the work bundled with P24.
- **Option C — Embed in P24 itself. Chosen.** Original "Not recommended" annotation reversed.

## Decision log (for traceability)

- 2026-05-03 — `factor-dedup` run produced this spec from the immediate-path comparator reports.
- 2026-05-03 — User walked all 9 Bucket-3 findings; dispositions captured in the table above.
- 2026-05-03 — User added new directive: investigate `[providers.X]` root-namespace passthrough for default settings.
- 2026-05-03 — User directive: enforce uniform `_DIRECT_SDK_KEYS_<PROVIDER>` and `_PROVIDER_NAME_<PROVIDER>` constant naming across all three modules. Reverses earlier "skip OpenAI `_PROVIDER_NAME` backport — pure cosmetic" disposition; OpenAI now gets the constant introduced, Perplexity gets the bare names renamed. Justification: uniqueness for grep + future cross-provider helper extraction.
- 2026-05-03 — Branch fast-forwarded; absorbed 4 P27 closure commits. Refresh review surfaced: `perplexity.py` is now DUAL-MODE (immediate + background); P27 polish extracted `_invalid_key_thotherror(provider, settings_url) -> ThothError` to `perplexity.py:143` (partial consolidation already done — plan now PROMOTES this helper to `thoth.providers._helpers` for cross-provider use); `_map_perplexity_error_async` exists at line 246 as the background-path sibling (out of scope, deliberate parallel by docstring); `_PERPLEXITY_STATUS_TABLE` constant at line 109 is background-path; `list_models` adds `sonar-deep-research`. Line numbers in plan tasks are stale — executors grep, don't chase line numbers.
- 2026-05-03 — Bucket-2 row 4 (Perplexity dynamic models) and row 5 (Perplexity async cancel) verified empirically against docs.perplexity.ai; both stand as intentional.
