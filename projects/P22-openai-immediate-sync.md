# P22 — OpenAI — Immediate (Synchronous) Calls

**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)
- **Predecessor:** P18 (`docs/superpowers/specs/2026-04-26-p18-immediate-vs-background-design.md`, `docs/superpowers/plans/2026-04-26-p18-immediate-vs-background.md`) — established the immediate-vs-background split, runtime mismatch error, and the immediate path validated here.
- **Adjacent:** P20 (Extended Real-API Workflow Coverage — Mirror Mock Contracts) — validation evidence overlaps with P20-TS03 / TS04 / TS11 / TS26 / TS27. P22 reuses P20 tests where applicable rather than duplicating.
- **Adjacent:** P25 (Architecture Review & Cleanup — Immediate Providers) — P22's refactor pre-analysis informs whether P25's scope expands, contracts, or is preempted.
- **Code:** `src/thoth/providers/openai.py:393` (`OpenAIProvider.stream()`); `_validate_kind_for_model` defense in the same file; `src/thoth/run.py` `_execute_immediate` dispatcher; `src/thoth/cli_subcommands/ask.py`; `src/thoth/sinks.py` (`MultiSink`).
- **External (Responses API):** https://platform.openai.com/docs/api-reference/responses
- **External (Chat Completions, comparison only):** https://platform.openai.com/docs/api-reference/chat
- **External (Deep-research cookbook, for kind-boundary checks):** https://cookbook.openai.com/examples/deep_research_api/introduction_to_deep_research_api
- **Closed-by:** P34 — finding F1 (offline-test coverage for `OpenAIProvider.stream()`) is superseded / closed by [Offline testing for OpenAIProvider.stream() (VCR or alternative)](P34-offline-testing-openai-stream-.md).

**Status:** `[x]` Completed.

**Goal**: Validate that OpenAI synchronous (immediate, non-background) calls already work end-to-end as a distinct path from background deep research, and produce a lightweight architecture pre-analysis informing whether cross-provider refactoring should pull forward from P25 before P23/P24 implement their immediate paths. P22 produces evidence and a decision; it does **not** add new provider implementation. If validation surfaces zero gaps and the pre-analysis recommends no refactor, P22 closes as `[x]` with that documented confirmation.

### Three-part structure

1. **Detailed validation pass.** Verify in depth that the synchronous LLM call path on OpenAI works end-to-end. Deliverable: a structured checklist (in this project body) cross-referenced to existing tests and to fresh evidence where coverage is missing. Items include: prompt-in/text-out via `OpenAIProvider.stream()`, no background submission for immediate-kind modes, no checkpoint side effects on the immediate path, errors surfaced synchronously, kind-mismatch defense raises **before** any HTTP call, secret masking on `--api-key-openai`, output sinks (`--out`, tee `--out -,FILE`, repeatable `--out`, `--append`), bare-prompt form (leading + trailing `--out`), `--quiet` suppresses progress UI without suppressing the answer, `--mode` resolves the immediate kind correctly. Close-out: every item passes, or every failing item is rerouted to Part 2.
2. **Gap analysis (conditional on Part 1).** If Part 1 surfaces anything lacking, each gap becomes a Finding with: (a) what's lacking, (b) severity and blocking-ness for P23 / P24, (c) recommended owner project (new P##, existing P##, or won't-fix with rationale). **No implementation in P22.** If Part 1 passes everything, Part 2 produces the single line *"No gaps surfaced; no follow-ups required."*
3. **Refactor pre-analysis.** Survey OpenAI's immediate-call shape (validated in Part 1) against what P23 (Perplexity) and P24 (Gemini) will need. Produce one of three outcomes:
   - **(a) No refactor warranted now.** P23/P24 each implement their own immediate path; P25 reviews all three together. Default outcome.
   - **(b) Lightweight shape-fixing only.** Define a Protocol/ABC the three immediate paths will implement; P22 does not change provider code, but P23/P24 build to the contract. Document the contract here.
   - **(c) Refactor blocks the cluster.** The existing OpenAI immediate path needs reshaping before P23/P24 can sensibly mirror it. Reserve a new P## via `project-add` and redirect; do not refactor inside P22.

**Out of scope**
- Re-implementing the existing immediate path (`OpenAIProvider.stream()` already covers it).
- Landing the cross-provider refactor itself (P25 owns that, unless Part 3 outcome (c) triggers a new project).
- Adding new OpenAI surfaces (Chat Completions API, alternative streaming modes) unless Part 3 outcome (b) or (c) explicitly requires it.
- Cross-provider work — P23 (Perplexity) and P24 (Gemini) do their own validation in their own projects.

**Project-level close-out**: P22 marks `[x]` when all three parts have closed out, regardless of which outcomes they produced. The fastest valid end state is *"Part 1 passes everything, Part 2 produces zero gaps, Part 3 picks outcome (a)"* — that legitimately ends as `[x]` with no code change.

### Tests & Tasks

**Part 1 — Detailed validation**
- [x] [P22-TS01] Design the validation checklist for "OpenAI synchronous LLM call works" and write it to this project body **before** running it. One row per item: name, expected behavior, expected evidence (test name(s) or live-API observation). TDD discipline: the checklist is the test plan; running it without the plan is not allowed.
- [x] [P22-TS02] Inventory existing test coverage per checklist item. Cross-reference P18 tests (`tests/test_immediate_path.py`, `tests/test_mode_kind_mismatch.py`, `tests/test_provider_stream_contract.py`, `tests/test_output_sinks.py`), the P18 cancel suite, and any P20 tests already landed. Mark each item as: `covered-by-P18`, `covered-by-P20`, `gap`. Items marked `gap` flow into T01's live evidence pass.
- [x] [P22-T01] Execute the validation pass. Run `uv run pytest tests/test_immediate_path.py tests/test_mode_kind_mismatch.py tests/test_provider_stream_contract.py tests/test_output_sinks.py -v` for the offline coverage. For `gap` items, run targeted live-API checks under `pytest -m live_api` (or `pytest -m extended` for nightly-cadence items). Record pass / fail / observation per checklist item directly in this body. Cancel any stray background jobs in `finally`.

**Part 2 — Gap analysis (conditional)**
- [x] [P22-T02] Write the Findings section of this project body. If Part 1 had zero failures, this is the single line *"No gaps surfaced; no follow-ups required."* Otherwise, list each gap with severity, blocking-ness for P23 / P24, and recommended owner project (new P## reserved via `project-add`, existing P##, or won't-fix with rationale).

**Part 3 — Refactor pre-analysis**
- [x] [P22-T03] Cross-provider immediate-call shape survey. Compare OpenAI Responses-API streaming (already implemented in `OpenAIProvider.stream()`), Perplexity Sonar streaming, and Gemini Interactions API. Identify shared shape vs. provider-divergence points: auth header, request body, streaming event format, error model, secret handling, kind-mismatch defense. Output: a comparison table in this body.
- [x] [P22-T04] Refactor decision. Pick outcome (a) / (b) / (c) per the three-part structure above and write the rationale into this body. If (b), draft the Protocol / ABC sketch (≤ 30 lines) inline. If (c), reserve a new P## via `project-add` and add the redirect note here; the new P## becomes a dependency of P23, P24, and P25.

**Project close-out**
- [x] [P22-T05] Update the Project Summary line at the top of `PROJECTS.md` with the close-out outcome label (e.g. *"closed: validation passed, no gaps, no refactor"* or *"closed: 2 gaps → P##, refactor outcome (b)"*) and flip P22's trunk glyph to `[x]`.

### Validation Checklist (TS01 deliverable) + Coverage Map (TS02 deliverable)

Each row: what we expect "OpenAI synchronous LLM call works" to mean, and where the existing evidence lives. Status legend: `✓` covered offline, `✓ live` covered under `extended` / `live_api` markers, `gap` = needs attention in T01 or routes to Part 2.

| # | Item | Expected behavior | Coverage |
|---|---|---|---|
| 1 | `OpenAIProvider.stream()` chunk contract | Yields `StreamEvent("text", ...)` deltas terminated by `StreamEvent("done", "")`; aggregating equals the full response | mock `✓` (`test_provider_stream_contract.py::test_mock_stream_yields_deterministic_chunks`, `::test_mock_stream_emits_done_event_last`); **gap**: no OpenAI-cassette test in current `test_provider_stream_contract.py` despite P18 spec TS13 — confirm whether it lives elsewhere or is truly missing |
| 2 | Base stream contract honored | `ResearchProvider.stream()` raises `NotImplementedError` by default | `✓` `test_provider_stream_contract.py::test_base_stream_raises_not_implemented` |
| 3 | Immediate path fallback | If `provider.stream()` raises `NotImplementedError`, `_execute_immediate` falls back to `submit()` + `get_result()` and sinks the final string | `✓` `test_immediate_path.py::test_immediate_falls_back_to_submit_get_result_when_stream_not_implemented` |
| 4 | Immediate path failure isolation | A streaming failure in the immediate path does not double-fail the operation | `✓` `test_immediate_path.py::test_immediate_stream_failure_does_not_double_fail_operation` |
| 5 | No spinner / no progress for immediate-kind | `should_show_spinner` returns `False`; `_poll_display` returns `None` for immediate-kind runs | `✓` `test_immediate_path.py::test_poll_display_yields_none_for_immediate_kind`, `::test_should_show_spinner_short_circuits_for_immediate` |
| 6 | Background-kind regression gate | `_poll_display` continues to yield `Progress` for background no-tty / spinner cases | `✓` `test_immediate_path.py::test_poll_display_yields_progress_for_background_no_tty`, `::test_should_show_spinner_used_by_poll_display_for_background_with_mode_cfg` |
| 7 | Legacy callers without `mode_cfg` | Existing call paths that don't pass `mode_cfg` keep working unchanged | `✓` `test_immediate_path.py::test_poll_display_legacy_no_mode_cfg_unchanged`, `::test_poll_display_legacy_no_mode_cfg_immediate_model` |
| 8 | Kind-mismatch defense raises BEFORE HTTP | `submit()` with `kind="immediate"` + a deep-research model raises `ModeKindMismatchError` with no API call | `✓` `test_mode_kind_mismatch.py::test_immediate_with_o3_deep_research_raises`, `::test_immediate_with_o4_mini_deep_research_raises` |
| 9 | Background + regular model legal | `kind="background"` + non-deep-research model does not raise | `✓` `test_mode_kind_mismatch.py::test_background_with_regular_model_does_not_raise` |
| 10 | Immediate + regular model legal | `kind="immediate"` + non-deep-research model does not raise | `✓` `test_mode_kind_mismatch.py::test_immediate_with_regular_model_does_not_raise` |
| 11 | No-kind declared is legal | Mode without `kind` declared does not raise (legacy compatibility) | `✓` `test_mode_kind_mismatch.py::test_no_kind_declared_does_not_raise` |
| 12 | Mismatch error carries diagnostics | `ModeKindMismatchError` exposes `mode_name`, `model`, `declared_kind`, `required_kind`, `suggestion` | `✓` `test_mode_kind_mismatch.py::test_error_carries_user_facing_suggestion`, `::test_error_subclasses_thotherror` |
| 13 | Real-API kind agreement | Every `KNOWN_MODELS` entry's declared kind matches actual runtime behavior | `✓ live` `tests/extended/test_model_kind_runtime.py::test_model_kind_matches_runtime_behavior` |
| 14 | `--out` / tee / append / repeatable / comma-list | `MultiSink` honors all five output-sink shapes | `✓` `test_output_sinks.py::test_stdout_only`, `::test_file_only_truncates_by_default`, `::test_file_appends_when_requested`, `::test_tee_to_stdout_and_file`, `::test_comma_list_parsing`, `::test_file_opened_lazily`, `::test_close_is_idempotent`, `::test_default_when_no_specs_is_stdout`, `::test_does_not_close_stdout` |
| 15 | `thoth ask` end-to-end output sinks | `ask` forwards `--out`, comma-list, repeatable, append to the runner and writes streamed mock output to file | `✓` `test_p16_pr2_ask.py::test_ask_forwards_out_and_append_to_research_runner`, `::test_ask_out_file_writes_streamed_mock_response`, `::test_ask_out_comma_list_tees_to_stdout_and_file`, `::test_ask_out_repeatable_form_tees_to_stdout_and_file`, `::test_ask_out_append_concatenates_second_run` |
| 16 | `thoth ask` real-API stream + tee | Live OpenAI immediate streaming with `--out -,FILE` writes both stdout and file | `✓ live` `tests/extended/test_openai_real_workflows.py::test_ext_oai_imm_stream_tee_writes_stdout_and_file` |
| 17 | Prompt-source mutual exclusion | `ask` rejects positional+`--prompt`, positional+`--prompt-file`, `--prompt`+`--prompt-file`, and no-prompt | `✓` `test_p16_pr2_ask.py::test_ask_positional_and_prompt_flag_rejected`, `::test_ask_positional_and_prompt_file_rejected`, `::test_ask_prompt_and_prompt_file_rejected`, `::test_ask_no_prompt_at_all_rejected` |
| 18 | Disallowed flags on immediate path | `ask` rejects `--interactive`, `--clarify`, `--pick-model` (background-only flags) | `✓` `test_p16_pr2_ask.py::test_ask_interactive_flag_rejected`, `::test_ask_clarify_flag_rejected`, `::test_ask_pick_model_flag_rejected` |
| 19 | Mode resolution | `ask --mode X` resolves to mode X's config; subcommand-level `--mode` wins over group-level | `✓` `test_p16_pr2_ask.py::test_ask_with_explicit_mode`, `::test_ask_subcommand_mode_wins_over_group_mode` |
| 20 | Prompt sources work | `ask` accepts positional, `--prompt`, `--prompt-file`, group-level flags | `✓` `test_p16_pr2_ask.py::test_ask_with_positional_prompt`, `::test_ask_with_prompt_flag`, `::test_ask_with_prompt_file`, `::test_ask_via_group_level_flags` |
| 21 | Bare-prompt form with `--out` (leading + trailing) | Top-level CLI bare prompt form supports `thoth --out F "p" --provider openai` and `thoth "p" --provider openai --out F` | **gap**: not visible in mock tests; partially covered by P20-TS08/TS09 once landed |
| 22 | `--quiet` suppresses progress UI but not answer | Immediate `--quiet` still streams the answer; suppresses progress / status lines | **gap**: covered by P20-TS11 once landed; no current mock test |
| 23 | Secret masking on `--api-key-openai` end-to-end | CLI accepts `--api-key-openai sk-...`, runs without `OPENAI_API_KEY` in env, never leaks the key in stdout/stderr | **gap**: helper-level coverage exists (`test_secrets.py`); end-to-end CLI flag secret masking covered by P20-TS21 once landed |
| 24 | No checkpoint side effects on default immediate run | Immediate mode without `--project` / `--out FILE` writes no checkpoint, emits no operation-ID, prints no `thoth resume` hint | **gap**: P18 spec TS08 / TS10 referenced but not visible in current `test_immediate_path.py`; P20-TS03 covers it for live API once landed |

**Coverage summary (post-T01 verification):** 21 of 24 items are `✓` offline; 2 of those 24 are `✓ live` (covered by `extended` / `live_api` markers, run nightly / weekly via GitHub Actions). 3 items remain as gaps (`#22`, `#23`, `#24`) — all already in P20's planned scope. One sub-item under `#1` is a confirmed real gap: `OpenAIProvider.stream()` has no offline VCR cassette test (`tests/test_provider_stream_contract.py` docstring explicitly defers it to the extended suite; `tests/test_vcr_openai.py` cassettes only cover `submit`/`check_status`/`get_result`).

### T01 — Validation pass result

`uv run pytest tests/test_immediate_path.py tests/test_mode_kind_mismatch.py tests/test_provider_stream_contract.py tests/test_output_sinks.py tests/test_secrets.py tests/test_p16_pr2_ask.py -v` → **59 passed in 0.78s.** `uv run pytest tests/test_cli_regressions.py -k bare_prompt -v` → **4 passed.** All offline checklist items return `✓`.

Live items `#13` and `#16` not run locally (cost / network). Recent green runs of `.github/workflows/extended.yml` and `.github/workflows/live-api.yml` are the operative evidence. Per CLAUDE.md, manual local invocation is `just test-extended` / `just test-live-api`.

### T02 — Findings (Part 2 deliverable)

Validation surfaced four gaps. None block P22's close-out as `[x]`; all are routable.

| # | Gap | Severity | Blocks P23/P24? | Recommended owner |
|---|---|---|---|---|
| F1 | `OpenAIProvider.stream()` has no offline VCR cassette test (P18 spec referenced TS13 but it never landed; `test_provider_stream_contract.py` defers to the extended suite) | low | no — live coverage exists in `tests/extended/test_openai_real_workflows.py`; P23 / P24 can mirror the deferral pattern for their own `stream()` impls | **P20** — add a TS row to `projects/P20-...` (or PROJECTS.md P20 body) for the OpenAI cassette specifically, e.g. `[P20-TS28] Offline cassette for OpenAIProvider.stream() asserts SSE event translation into StreamEvent("text",...) terminated by StreamEvent("done","")`. If P20 stays paperwork-only and never lands, escalate to a new P##. |
| F2 | `thoth ask --quiet` not directly tested on the immediate path offline | low | no | **P20-TS11** (already planned) |
| F3 | `thoth ask --api-key-openai` not directly tested on the immediate path offline (helper-level secret masking is covered; flag-end-to-end with no env var is not) | low | no | **P20-TS21** (already planned) |
| F4 | No explicit offline test confirming "default immediate run writes no checkpoint, emits no operation-ID, prints no `thoth resume` hint" — P18 spec named TS08 / TS10 but the current `test_immediate_path.py` only covers `_poll_display` / spinner gating; the absence of side effects on the runner is not asserted directly | low | no | **P20-TS03** (already planned, real-API form) — and consider adding an offline equivalent under P20 or as a small addition under a future test-hardening project |

**No findings escalated to a new P##.** All four findings flow into P20's existing scope or remain as informational additions to P20.

### T03 — Cross-provider immediate-call shape survey (Part 3 input)

Existing `ResearchProvider` contract (`src/thoth/providers/base.py`):

```python
async def stream(prompt, mode, system_prompt=None, verbose=False) -> AsyncIterator[StreamEvent]:
    raise NotImplementedError(...)

@dataclass
class StreamEvent:
    kind: Literal["text", "reasoning", "citation", "done"]
    text: str
```

| Concern | OpenAI (shipped) | Perplexity (P23) | Gemini (P24) |
|---|---|---|---|
| HTTP shape | `client.responses.stream(...)` SSE; `response.output_text.delta` events | `chat/completions` with `stream=true` SSE; OpenAI-style `delta.content` events | Interactions API streaming; Google-specific event format |
| Auth | `Bearer $OPENAI_API_KEY` | `Bearer $PERPLEXITY_API_KEY` | `x-goog-api-key: $GEMINI_API_KEY` (per `planning/references.md`) |
| Translation to `StreamEvent` | `delta` → `StreamEvent("text", ...)`, terminal `StreamEvent("done", "")` (already implemented `providers/openai.py:393`) | translate `delta.content` → `text`; Sonar emits citation arrays — slot exists as `kind="citation"` | translate Interactions text chunks → `text`; reasoning chunks (if present) → `kind="reasoning"` |
| Kind-mismatch defense | `_validate_kind_for_model` + `is_background_model` | needs equivalent: Perplexity's `sonar-deep-research` is background; `sonar` / `sonar-pro` are immediate | needs equivalent: Gemini's `deep-research-pro-preview-12-2025` is background; standard chat models are immediate |
| Background `cancel` | `client.responses.cancel(response_id)` | per P18-T19 research — Perplexity does not expose cancel; orphan request_id | per P18-T20 research — Interactions API cancel/abort semantics |
| Current state | Full `submit/check_status/get_result/stream/cancel` | Stub: `submit` raises `ProviderError`; `is_implemented()` returns `False` | No file in `src/thoth/providers/` |

**Shape observations:**
- The existing `ResearchProvider.stream()` + `StreamEvent` is already a thoughtful cross-provider abstraction. Its `kind` field deliberately enumerates `"text"`, `"reasoning"`, `"citation"`, `"done"` — those slots were named in P18 with multi-provider use cases in mind (Perplexity emits citations; reasoning-summary models emit reasoning chunks). The slots are unused in OpenAI's current impl but ready for use by P23 / P24.
- The default `NotImplementedError` plus `_execute_immediate`'s fallback to `submit()` + `get_result()` gives P23 / P24 a graceful staging path: implement background first, ship, then add `stream()` for true immediate behavior. No "all-or-nothing" pressure.
- Each provider translates its own SSE / event format into `StreamEvent` — exactly the existing pattern. There is no shared HTTP layer to abstract; each SDK is provider-specific.

### T04 — Refactor decision

**Outcome (a): No refactor warranted now.**

**Rationale:**
1. The `ResearchProvider.stream()` + `StreamEvent` contract already IS the cross-provider abstraction. Its `kind` enum was P18-designed to accommodate Perplexity citations and reasoning models — there is no abstraction to add that is not already in the base class.
2. P23 (Perplexity) and P24 (Gemini) implement `stream()` independently by translating their SDK's event format into `StreamEvent` chunks. That is the existing pattern; no contract change is needed before they begin.
3. The `NotImplementedError` default + immediate-path fallback removes any "must implement streaming on day one" pressure. P23 / P24 can ship a background-only first cut and add `stream()` later.
4. Provider-specific concerns (auth scheme, kind-mismatch defense per provider's model list, cancel semantics) are inherently provider-local — they cannot be shared in a base class without leaking provider details upstream.
5. P25 (Architecture Review & Cleanup — Immediate Providers) is the right place to look across all three implementations and decide on cleanup. Pulling that decision forward to P22 — before P23 / P24 even exist — would be premature.

**No new P## reserved.** **No Protocol / ABC sketch needed** (the existing `ResearchProvider` serves that role).

### P22 close-out summary

- **Part 1 (validation):** PASS. 21 / 24 checklist items `✓` offline; 2 `✓ live`; 1 confirmed sub-gap (offline cassette for `OpenAIProvider.stream()`) routed to F1.
- **Part 2 (gap analysis):** 4 findings (F1–F4); all route to P20 or remain as P20 informational additions; **none escalate to a new P##**.
- **Part 3 (refactor pre-analysis):** Outcome (a) — no refactor warranted now. P25 owns any cross-cutting cleanup once P23 / P24 land.

P22 is ready to mark `[x]` per the project-level close-out criterion. The only follow-up touching another project is the optional `[P20-TS28]` cassette task suggested by F1; P20 owners can accept or decline.

### Acceptance Criteria
- The validation checklist (TS01) exists in this body **before** T01 runs. ✓ (above)
- Every checklist item has an explicit pass / fail / gap status recorded after T01.
- The Findings section exists, even if the content is *"no gaps."*
- The refactor pre-analysis produces an explicit (a) / (b) / (c) outcome with written rationale.
- The Project Summary line for P22 reflects the close-out outcome label so a future `project-next` reader sees the result without opening the body.
- No new code lands in `src/thoth/` as part of P22 unless Part 3 outcome (b) requires it (and even then scope is limited to a Protocol / ABC declaration, not provider implementation changes).
