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
- [ ] [P26-TS01] Design the validation checklist for "OpenAI background deep research works" and write it to this project body **before** running it. One row per item: name, expected behavior, expected evidence (test name(s), cassette name, or live-API observation). TDD discipline: the checklist is the test plan; running it without the plan is not allowed.
- [ ] [P26-T01] Execute the validation pass. Run `uv run pytest tests/test_vcr_openai.py tests/test_immediate_path.py tests/test_mode_kind_mismatch.py -v` for the offline coverage, plus any additional pytest files surfaced by TS01 inventory. For items not covered offline, run targeted live-API checks under `pytest -m live_api` (or `pytest -m extended` for nightly-cadence items). Record pass / fail / observation per checklist item directly in this body. Cancel any stray background jobs in `finally`.

**Part 2 — Gap analysis (conditional)**
- [ ] [P26-T02] Write the Findings section of this project body. If Part 1 had zero failures, this is the single line *"No gaps surfaced; no follow-ups required."* Otherwise, list each gap with severity, blocking-ness for P27 / P28, and recommended owner project (P20 / P34 / P29 / new P## reserved via `project-add`, or won't-fix with rationale).

**Part 3 — Refactor pre-analysis**
- [ ] [P26-T03] Cross-provider background-call shape survey. Compare OpenAI Responses-API background submission (already implemented in `src/thoth/providers/openai.py`), Perplexity Sonar Deep Research async pattern, and Gemini Interactions API. Identify shared shape vs. provider-divergence points: submit body, polling cadence, status enum, cancel semantics, auth header, kind-mismatch defense, secret handling. Output: a comparison table in this body.
- [ ] [P26-T04] Refactor decision. Pick outcome (a) / (b) / (c) per the three-part structure above and write the rationale into this body. If (b), draft the Protocol / ABC sketch (≤ 30 lines) inline. If (c), reserve a new P## via `project-add` and add the redirect note here; the new P## becomes a dependency of P27, P28, and P29.

**Project close-out**
- [ ] [P26-T05] Update the close-out summary at the top of this body with the outcome label (e.g. *"closed: validation passed, no gaps, no refactor"* or *"closed: 2 gaps → P##, refactor outcome (b)"*) and flip P26's trunk glyph to `[x]`.

### Acceptance Criteria
- The validation checklist (TS01) exists in this body **before** T01 runs.
- Every checklist item has an explicit pass / fail / gap status recorded after T01.
- The Findings section exists, even if the content is *"no gaps."*
- The refactor pre-analysis produces an explicit (a) / (b) / (c) outcome with written rationale.
- No new code lands in `src/thoth/` as part of P26 unless Part 3 outcome (b) requires it (and even then scope is limited to a Protocol / ABC declaration, not provider implementation changes).
