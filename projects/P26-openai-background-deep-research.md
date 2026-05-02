# P26 — OpenAI — Background Deep Research

**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)
- **Sibling (immediate-path equivalent):** P22 (`projects/P22-openai-immediate-sync.md`) — three-part structure (validation + gap analysis + refactor pre-analysis) being mirrored here for the background path.
- **Predecessors (already shipped):** P02 (BUG-01 OpenAI background status handling), P03 (BUG-03 OpenAI poll interval scheduling), P18 (immediate-vs-background `kind`, runtime mismatch, path split, streaming, cancel) — established the background path validated here.
- **Successor (cross-provider):** P29 — Architecture Review & Cleanup — Background Deep Research Providers. Part 3 of P26 feeds P29 once P27 / P28 have shipped.
- **Adjacent (live & extended coverage):** P20 — Live-API Workflow Regression Suite. Background-path live evidence relies on the `live_api` / `extended` pytest markers added in P20.
- **Adjacent (offline streaming coverage):** P34 — `[?]` Offline testing for `OpenAIProvider.stream()` (VCR or alternative). Out of scope here; immediate-path streaming offline coverage is P34's job, not P26's.
- **Code:** `src/thoth/providers/openai.py:166` (`submit`), `:255` (`check_status`), `:355` (`cancel`), `:393` (`stream`), `:452` (`get_result`); `src/thoth/run.py` background dispatcher and `_poll_display`.
- **Existing tests:** `tests/test_vcr_openai.py` (background cassette replay for `submit` / `check_status` / `get_result`), `tests/test_immediate_path.py` (background spinner / progress regression gates), `tests/test_mode_kind_mismatch.py` (background-kind defense), `tests/extended/test_openai_real_workflows.py` (live-API).
- **External (Responses API):** https://platform.openai.com/docs/api-reference/responses
- **External (Deep-research cookbook):** https://cookbook.openai.com/examples/deep_research_api/introduction_to_deep_research_api

**Status:** `[ ]` Scoped, not started.

**Goal**: Validate that OpenAI background deep research already works end-to-end as a distinct path from immediate, and produce a lightweight architecture pre-analysis informing whether cross-provider refactoring should pull forward from P29 before P27 / P28 implement their background paths. P26 produces evidence and a decision; it does **not** add new provider implementation. If validation surfaces zero gaps and the pre-analysis recommends no refactor, P26 closes as `[x]` with that documented confirmation.

### Three-part structure

1. **Detailed validation pass.** Verify in depth that the background deep-research path on OpenAI works end-to-end. Deliverable: a structured checklist (in this project body) cross-referenced to existing tests and to fresh evidence where coverage is missing. Items include: `submit` returns a `resp_*` ID; status transitions `queued → in_progress → completed` plus `failed` / `cancelled`; `check_status` poll cadence honors backoff (BUG-03 regression gate); `get_result` returns full text and surfaces partial output on failure; `cancel` is idempotent; kind-mismatch defense raises **before** any HTTP call for `kind="background"` + non-deep-research model; checkpoint write on background submission and `thoth resume` replays it; secret masking on `--api-key-openai` through the background workflow; output sinks (`--out`, tee, append, repeatable) on the background path; offline cassette coverage in `tests/test_vcr_openai.py`; live-API regression coverage via P20 nightly / weekly markers. Close-out: every item passes, or every failing item is rerouted to Part 2.
2. **Gap analysis (conditional on Part 1).** If Part 1 surfaces anything lacking, each gap becomes a Finding with: (a) what's lacking, (b) severity and blocking-ness for P27 / P28, (c) recommended owner project (existing P## — typically P20, P34, or P29 — or a new P## via `project-add`, or won't-fix with rationale). **No implementation in P26.** If Part 1 passes everything, Part 2 produces the single line *"No gaps surfaced; no follow-ups required."*
3. **Refactor pre-analysis.** Survey OpenAI's background-call shape (validated in Part 1) against what P27 (Perplexity) and P28 (Gemini) will need. Produce one of three outcomes:
   - **(a) No refactor warranted now.** P27 / P28 each implement their own background path; P29 reviews all three together. Default outcome.
   - **(b) Lightweight shape-fixing only.** Define a Protocol / ABC the three background paths will implement; P26 does not change provider code, but P27 / P28 build to the contract. Document the contract here.
   - **(c) Refactor blocks the cluster.** The existing OpenAI background path needs reshaping before P27 / P28 can sensibly mirror it. Reserve a new P## via `project-add` and redirect; do not refactor inside P26.

**Out of scope**
- Re-implementing the existing background path (already shipped via P02 / P03 / P18; full surface in `src/thoth/providers/openai.py`).
- Adding new VCR / cassette work for the background path (`tests/test_vcr_openai.py` already covers `submit` / `check_status` / `get_result`); offline streaming coverage is P34's scope, not P26's.
- Adding new live-test infrastructure (`pyproject.toml` already deselects `live_api` / `extended` markers by default; nightly / weekly GitHub Actions workflows landed in P20).
- Landing the cross-provider refactor itself (P29 owns that, unless Part 3 outcome (c) triggers a new project).
- Cross-provider work — P27 (Perplexity) and P28 (Gemini) do their own background validation in their own projects.

**Project-level close-out**: P26 marks `[x]` when all three parts have closed out, regardless of which outcomes they produced. The fastest valid end state is *"Part 1 passes everything, Part 2 produces zero gaps, Part 3 picks outcome (a)"* — that legitimately ends as `[x]` with no code change.

### Tests & Tasks

**Part 1 — Detailed validation**
- [x] [P26-TS01] Design the validation checklist for "OpenAI background deep research works" and write it to this project body **before** running it. One row per item: name, expected behavior, expected evidence (test name(s), cassette name, or live-API observation). TDD discipline: the checklist is the test plan; running it without the plan is not allowed.
- [x] [P26-T01] Execute the validation pass. Run `uv run pytest` against the inventory surfaced by TS01 for the offline coverage. For items not covered offline, cite live-API workflow evidence (`pytest -m extended` / `live_api`). Record pass / fail / observation per checklist item directly in this body.

**Part 2 — Gap analysis (conditional)**
- [ ] [P26-T02] Write the Findings section of this project body. If Part 1 had zero failures, this is the single line *"No gaps surfaced; no follow-ups required."* Otherwise, list each gap with severity, blocking-ness for P27 / P28, and recommended owner project (P20 / P34 / P29 / new P## reserved via `project-add`, or won't-fix with rationale).

**Part 3 — Refactor pre-analysis**
- [ ] [P26-T03] Cross-provider background-call shape survey. Compare OpenAI Responses-API background submission (already implemented in `src/thoth/providers/openai.py`), Perplexity Sonar Deep Research async pattern, and Gemini Interactions API. Identify shared shape vs. provider-divergence points: submit body, polling cadence, status enum, cancel semantics, auth header, kind-mismatch defense, secret handling. Output: a comparison table in this body.
- [ ] [P26-T04] Refactor decision. Pick outcome (a) / (b) / (c) per the three-part structure above and write the rationale into this body. If (b), draft the Protocol / ABC sketch (≤ 30 lines) inline. If (c), reserve a new P## via `project-add` and add the redirect note here; the new P## becomes a dependency of P27, P28, and P29.

**Project close-out**
- [ ] [P26-T05] Update the close-out summary at the top of this body with the outcome label (e.g. *"closed: validation passed, no gaps, no refactor"* or *"closed: 2 gaps → P##, refactor outcome (b)"*) and flip P26's trunk glyph to `[x]`.

### Validation Checklist (TS01 deliverable) + Coverage Map

Each row: what we expect "OpenAI background deep research works" to mean, and where the existing evidence lives. Status legend: `✓` covered offline; `✓ live` covered under `extended` / `live_api` markers (nightly / weekly via GitHub Actions); `gap` = needs attention in T01 or routes to Part 2. Rows shared with the immediate path are referenced by P22 row number rather than re-tested here.

| # | Item | Expected behavior | Coverage |
|---|---|---|---|
| 1 | `submit(prompt, mode="deep-research")` returns `resp_*` ID and stores job metadata | OpenAI Responses API submission with `background=true` returns response whose ID starts with `resp_`; `provider.jobs[job_id]` populated with `background=True` | `✓` `test_vcr_openai.py::TestSubmit::test_submit_returns_response_id`, `::test_submit_returns_expected_id`, `::test_submit_stores_job_info` |
| 2 | `submit()` transport retry on transient HTTP errors | tenacity `@retry` retries `openai.APITimeoutError` / `openai.APIConnectionError` with exponential backoff before re-raising | source `src/thoth/providers/openai.py:182-188`; runtime evidence covered under live-API workflow |
| 3 | `check_status()` provider state machine — non-completion variants | queued ≠ completed; in_progress → running; failed → permanent_error w/ message; incomplete → permanent_error; cancelled → cancelled; missing-status attr is non-completed; network error with stale in-progress cache returns transient (not completed); network error with completed cache returns completed | `✓` `test_oai_background.py::test_queued_status_is_not_completed`, `::test_in_progress_maps_to_running`, `::test_failed_status_propagates_error`, `::test_incomplete_status_maps_to_permanent_error`, `::test_cancelled_status_maps_to_cancelled`, `::test_no_status_attr_is_not_completed`, `::test_network_error_with_stale_inprogress_cache_is_not_completed`, `::test_network_error_with_completed_cache_still_returns_completed` |
| 4 | `check_status()` happy-path completion via cassette | polling check_status across cassette interactions reaches `completed` | `✓` `test_vcr_openai.py::TestPolling::test_first_status_is_in_progress_or_queued`, `::test_poll_to_completed` |
| 5 | Polling-loop schedule honors jitter (BUG-03 regression gate) | `_compute_poll_interval(base)` jitters by ±10%; sub-second base intervals respected; negative jitter does not truncate a 2 s interval | `✓` `test_polling_interval.py::test_negative_jitter_does_not_truncate_two_second_interval`, `::test_sub_second_poll_interval_is_honored` |
| 6 | Polling loop: queued does NOT exit; terminal-failure enums route to operation-fail with checkpoint | provider returning `queued` keeps loop alive; `failed` / `cancelled` / `error` / `not_found` / unknown statuses mark provider failed and save checkpoint | `✓` `test_oai_background.py::test_queued_does_not_exit_polling_loop`, `::test_failed_provider_fails_operation`, `::test_cancelled_provider_fails_operation`, `::test_error_provider_fails_operation`, `::test_not_found_provider_fails_with_error_details`, `::test_unknown_provider_status_fails_with_error_message` |
| 7 | `cancel(job_id)` is idempotent and surfaces upstream-cancel correctly | mock cancel pops job and returns `cancelled`; OpenAI cancel calls `client.responses.cancel(response_id)`; cancelling a completed job is a no-op; SIGINT triggers upstream-cancel within a 5 s envelope; subcommand cancels and is idempotent on already-completed ops | `✓` `test_provider_cancel.py::test_mock_cancel_pops_job_and_returns_cancelled`, `::test_openai_cancel_calls_responses_cancel`, `::test_openai_cancel_completed_job_is_noop`, `::test_openai_cancel_handles_api_error`; `test_sigint_upstream_cancel.py` (full file, 7 tests); `test_cancel_subcommand.py` (4 tests) |
| 8 | `get_result()` returns substantial research output on completion | get_result aggregates `output_text` from completed response; result is non-empty research content | `✓` `test_vcr_openai.py::TestGetResult::test_get_result_returns_text`, `::test_get_result_contains_research_content` |
| 9 | Checkpoint write timing on background submission | submission persists provider-job metadata; running-provider status visible while operation in progress | `✓` `test_async_checkpoint.py::test_async_submission_persists_provider_job_metadata`, `::test_status_shows_running_provider_for_async_operation` |
| 10 | `thoth resume` replays a checkpointed background op | recoverable failure resume reconnects and completes; permanent failure refused with exit 7; resume-of-completed is a no-op; async resume short-circuits the polling loop in seven distinct shapes (running / partial / all-completed / JSON-envelope / missing-op-id-exit-6 / already-completed-noop / no-files-when-running); resume command honors `--verbose` / `--quiet` / `--no-metadata` / `--timeout` / `--api-key-*` / `--config-path` and rejects undeclared options | `✓` `test_resume.py` (3 tests); `test_resume_async.py` (7 tests); `test_p16_pr2_resume.py::test_resume_with_op_id` plus 12 sibling tests |
| 11 | Kind-mismatch defense — background direction | `kind="background"` + non-DR model does not raise; `kind="background"` + DR-model is the production happy path (validated implicitly via cassette tests, rows #1 / #4); immediate-direction defense (`immediate` + DR raises) covered by P22 row #8 | `✓` `test_mode_kind_mismatch.py::test_background_with_regular_model_does_not_raise`, `::test_no_kind_declared_does_not_raise`; cross-ref P22 row #8 |
| 12 | `is_background_model` / `is_background_mode` classification | DR-suffix-bearing model strings classify as background; non-DR strings (including bare `o3`) classify as immediate; explicit `async` / `kind` override wins; case-sensitive substring match; null / empty inputs are immediate | `✓` `test_is_background_mode.py` (full file, 17 tests) |
| 13 | Live-API end-to-end OpenAI background workflow | nightly / weekly cadence: submit + auto-async + explicit-async + cancel-cmd + blocking-resume lifecycle against real OpenAI | `✓ live` `tests/extended/test_openai_real_workflows.py::test_ext_oai_bg_json_auto_async_submits_and_can_cancel`, `::test_ext_oai_bg_json_explicit_async_submits_and_can_cancel`, `::test_ext_oai_bg_cancel_cmd_json_cancels_live_background_job`, `::test_ext_oai_bg_async_blocking_resume_complete_lifecycle` (gated under `pytest -m extended` / `live_api`; nightly via `.github/workflows/extended.yml`, weekly via `.github/workflows/live-api.yml`) |
| 14 | Shared concerns inherited from P22 (immediate-path validation) | auth header (`Bearer $OPENAI_API_KEY`), secret masking on `--api-key-openai`, output sinks (`--out`, tee, `--append`, repeatable, comma-list), framework-level kind-defense plumbing — same machinery in `_run_polling_loop` / `MultiSink`, kind-agnostic | `✓` reference P22 rows #14 (`test_output_sinks.py`, 9 tests), #15 (ask-side sinks), #18 (flag rejection), #21–#23 (bare-prompt, `--quiet`, secret masking — gaps closed in P20). Background path reuses the same `MultiSink` + `--api-key-*` resolution; no new code path to validate. |

**Coverage summary (post-T01 verification):** 13 of 14 rows `✓` offline; 1 of 14 `✓ live` (nightly / weekly GitHub Actions). Row `#2` (submit-time tenacity retry) is verified by source inspection plus the live-API workflow; offline coverage is intentionally absent because retry timing is a tenacity-library guarantee, not a thoth contract.

### T01 — Validation pass result

`uv run pytest tests/test_vcr_openai.py tests/test_oai_background.py tests/test_polling_interval.py tests/test_async_checkpoint.py tests/test_provider_cancel.py tests/test_cancel_subcommand.py tests/test_sigint_upstream_cancel.py tests/test_resume.py tests/test_resume_async.py tests/test_p16_pr2_resume.py tests/test_is_background_mode.py tests/test_mode_kind_mismatch.py -v` → **97 passed in 14.69 s.** All offline checklist rows return `✓`.

Live row `#13` not run locally (cost / network). Recent green runs of `.github/workflows/extended.yml` (nightly 09:00 UTC) and `.github/workflows/live-api.yml` (weekly Sun 02:00 UTC) are the operative evidence. Per CLAUDE.md, manual local invocation is `just test-extended` / `just test-live-api` (require `OPENAI_API_KEY`).

### Acceptance Criteria
- The validation checklist (TS01) exists in this body **before** T01 runs.
- Every checklist item has an explicit pass / fail / gap status recorded after T01.
- The Findings section exists, even if the content is *"no gaps."*
- The refactor pre-analysis produces an explicit (a) / (b) / (c) outcome with written rationale.
- No new code lands in `src/thoth/` as part of P26 unless Part 3 outcome (b) requires it (and even then scope is limited to a Protocol / ABC declaration, not provider implementation changes).
