## [ ] Project P21: Configuration Profiles
**Goal**: Add named configuration profiles that let users set defaults and switch between them.

**Status**: Placeholder — requirements still need to be fleshed out before this can be worked on.

### Tests & Tasks
- [ ] [P21-TS01] Design tests for profile selection, default application, and config-file persistence before implementation.
- [ ] [P21-T01] Flesh out requirements for configuration profiles.
- [ ] [P21-T02] Implement profiles that set defaults applied to subsequent commands.
- [ ] [P21-T03] Store and load profiles from the configuration file.

---

## [ ] Project P22: OpenAI — Immediate (Synchronous) Calls
**Goal**: Add standard, single-shot synchronous LLM completion calls via OpenAI.

**Status**: Placeholder — requirements still need to be fleshed out before this can be worked on.

### Tests & Tasks
- [ ] [P22-TS01] Design tests for OpenAI immediate-call behavior, cassette replay, and live-test gating before implementation.
- [ ] [P22-T01] Flesh out requirements for OpenAI immediate calls.
- [ ] [P22-T02] Implement normal synchronous LLM completion calls.
- [ ] [P22-T03] Add VCR recording/replay coverage for local testing.
- [ ] [P22-T04] Add live testing capability disabled by default.

---

## [ ] Project P23: Perplexity — Immediate (Synchronous) Calls
**Goal**: Add standard, single-shot synchronous LLM completion calls via Perplexity.

**Status**: Placeholder — requirements still need to be fleshed out before this can be worked on.

### Tests & Tasks
- [ ] [P23-TS01] Design tests for Perplexity immediate-call behavior, cassette replay, and live-test gating before implementation.
- [ ] [P23-T01] Flesh out requirements for Perplexity immediate calls.
- [ ] [P23-T02] Implement normal synchronous LLM completion calls.
- [ ] [P23-T03] Add VCR recording/replay coverage for local testing.
- [ ] [P23-T04] Add live testing capability disabled by default.

---

## [ ] Project P24: Gemini — Immediate (Synchronous) Calls
**Goal**: Add standard, single-shot synchronous LLM completion calls via Gemini.

**Status**: Placeholder — requirements still need to be fleshed out before this can be worked on.

### Tests & Tasks
- [ ] [P24-TS01] Design tests for Gemini immediate-call behavior, cassette replay, and live-test gating before implementation.
- [ ] [P24-T01] Flesh out requirements for Gemini immediate calls.
- [ ] [P24-T02] Implement normal synchronous LLM completion calls.
- [ ] [P24-T03] Add VCR recording/replay coverage for local testing.
- [ ] [P24-T04] Add live testing capability disabled by default.

---

## [ ] Project P25: Architecture Review & Cleanup — Immediate Providers
**Goal**: Conduct a cross-provider architecture review across the three immediate-call providers once all three are in place.

**Status**: Placeholder — requirements still need to be fleshed out before this can be worked on.

### Tests & Tasks
- [ ] [P25-TS01] Define review criteria and any regression tests needed before architecture changes are proposed.
- [ ] [P25-T01] Flesh out requirements for the immediate-provider architecture review.
- [ ] [P25-T02] Analyze whether shared infrastructure is feasible across the three immediate providers.
- [ ] [P25-T03] Document if no shared abstraction is warranted.
- [ ] [P25-T04] If applicable, recommend architecture enhancements that reduce duplication and improve stability, uniformity, and maintainability.

---

## [ ] Project P26: OpenAI — Background Deep Research
**Goal**: Add long-running deep research operations via OpenAI, submitted and polled to completion.

**Status**: Placeholder — requirements still need to be fleshed out before this can be worked on.

### Tests & Tasks
- [ ] [P26-TS01] Design tests for OpenAI background submission, polling, cassette replay, and live-test gating before implementation.
- [ ] [P26-T01] Flesh out requirements for OpenAI background deep research.
- [ ] [P26-T02] Implement async deep research submission and polling.
- [ ] [P26-T03] Add VCR recording/replay coverage for local testing.
- [ ] [P26-T04] Add live testing capability disabled by default.

---

## [ ] Project P27: Perplexity — Background Deep Research
**Goal**: Add long-running deep research operations via Perplexity, submitted and polled to completion.

**Status**: Placeholder — requirements still need to be fleshed out before this can be worked on.

### Tests & Tasks
- [ ] [P27-TS01] Design tests for Perplexity background submission, polling, cassette replay, and live-test gating before implementation.
- [ ] [P27-T01] Flesh out requirements for Perplexity background deep research.
- [ ] [P27-T02] Implement async deep research submission and polling.
- [ ] [P27-T03] Add VCR recording/replay coverage for local testing.
- [ ] [P27-T04] Add live testing capability disabled by default.

---

## [ ] Project P28: Gemini — Background Deep Research
**Goal**: Add long-running deep research operations via Gemini, submitted and polled to completion.

**Status**: Placeholder — requirements still need to be fleshed out before this can be worked on.

### Tests & Tasks
- [ ] [P28-TS01] Design tests for Gemini background submission, polling, cassette replay, and live-test gating before implementation.
- [ ] [P28-T01] Flesh out requirements for Gemini background deep research.
- [ ] [P28-T02] Implement async deep research submission and polling.
- [ ] [P28-T03] Add VCR recording/replay coverage for local testing.
- [ ] [P28-T04] Add live testing capability disabled by default.

---

## [ ] Project P29: Architecture Review & Cleanup — Background Deep Research Providers
**Goal**: Conduct a cross-provider architecture review across the three background deep research providers once all three are in place.

**Status**: Placeholder — requirements still need to be fleshed out before this can be worked on.

### Tests & Tasks
- [ ] [P29-TS01] Define review criteria and any regression tests needed before architecture changes are proposed.
- [ ] [P29-T01] Flesh out requirements for the background-provider architecture review.
- [ ] [P29-T02] Analyze whether shared infrastructure is feasible across the three background deep research providers.
- [ ] [P29-T03] Document if no shared abstraction is warranted.
- [ ] [P29-T04] If applicable, recommend architecture enhancements that reduce duplication and improve stability, uniformity, and maintainability.

---

## [ ] Project P30: Claude Code Skills Support
**Goal**: Add support for Claude Code skills, similar to what Codex provides.

**Reference**: https://github.com/openai/codex-plugin-cc

**Status**: Placeholder — requirements still need to be fleshed out before this can be worked on.

### Tests & Tasks
- [ ] [P30-TS01] Design tests for Claude Code skill discovery, loading, and execution before implementation.
- [ ] [P30-T01] Flesh out requirements for Claude Code skills support.
- [ ] [P30-T02] Implement Claude Code skills support using the reference plugin as input.

---

## [ ] Project P31: Interactive Init Command
**Goal**: Add an interactive `init` command.

**Status**: Placeholder — requirements still need to be fleshed out before this can be worked on.

### Tests & Tasks
- [ ] [P31-TS01] Design tests for the interactive `init` flow before implementation.
- [ ] [P31-T01] Flesh out requirements for the interactive `init` command.
- [ ] [P31-T02] Implement the interactive `init` command.

---

## [ ] Project P32: Interactive Prompt Refiner
**Goal**: Add a fast, interactive prompt-refinement workflow before research submission.

**Status**: Placeholder — requirements still need to be fleshed out before this can be worked on.

### Tests & Tasks
- [ ] [P32-TS01] Design tests for the prompt-refinement workflow before implementation.
- [ ] [P32-T01] Flesh out requirements for the interactive prompt refiner.
- [ ] [P32-T02] Implement an interactive workflow that refines a research prompt before submission.
- [ ] [P32-T03] Keep the refiner fast and avoid full deep research during refinement.

---

## [ ] Project P20: Extended Real-API Workflow Coverage — Mirror Mock Contracts

**Goal**: Expand the `@pytest.mark.extended` real-API suite from model-kind smoke checks into periodic workflow coverage that mirrors the important mock/thoth_test contracts. These tests stay out of default pytest, run manually or nightly, and answer: "Does the real OpenAI runtime still honor the immediate/background split, output sinks, file output semantics, status/cancel behavior, and option forwarding?"

**Primary dependency**: P18 immediate-vs-background path split and `tests/extended/test_model_kind_runtime.py`.
**Primary files**:
- Add: `tests/extended/test_real_api_workflows.py`
- Modify: `tests/extended/conftest.py` if shared real-API helpers are split out
- Modify: `pyproject.toml` only if adding a narrower marker such as `extended_slow`
- Modify: `justfile` only if adding a helper command such as `just test-extended-workflows`

**Scope rule**: mirror the mock contracts at the workflow boundary, but keep assertions stable for real LLM output. Assert non-empty output, file creation/non-creation, metadata presence/absence, CLI status text, operation state, secret masking, and checkpoint/output paths. Do **not** assert deterministic prose.

**Cost and safety gates**
- All tests use `@pytest.mark.extended`; default `uv run pytest` must still deselect them.
- Tests that complete real background deep-research jobs should also use a second marker or env gate, e.g. `@pytest.mark.extended_slow` or `THOTH_EXTENDED_SLOW=1`.
- Use tiny prompts and isolated temp output/config/state directories.
- Prefer `--async` + `cancel` for background state-machine checks where completion is not required.
- Always assert CLI-provided API keys are not printed in stdout/stderr.
- Cancel any still-running background job in `finally`.

### Test Design

**Shared helpers**
- [ ] [P20-TS01] Add an extended-test CLI runner fixture that:
  - skips unless `OPENAI_API_KEY` is set;
  - sets isolated `HOME`, `XDG_CONFIG_HOME`, `XDG_STATE_HOME`, `XDG_CACHE_HOME`;
  - runs `python -m thoth ...` or `uv run thoth ...` with a bounded timeout;
  - returns `exit_code`, `stdout`, `stderr`, and temp output paths;
  - scrubs secrets from captured failure output.
- [ ] [P20-TS02] Add helper assertions for real-output files:
  - `assert_nonempty_file(path)`;
  - `assert_no_default_result_files(tmp_path, provider="openai")`;
  - `assert_metadata_present(path, prompt_fragment, mode, provider)`;
  - `assert_metadata_absent(path)`;
  - `assert_secret_not_leaked(stdout, stderr, secret)`.

**Immediate real-API workflows, mirror mock streaming/output-sink tests**
- [ ] [P20-TS03] `thoth ask "extended immediate stdout" --mode thinking --provider openai` streams non-empty stdout, exits 0, creates no default result file, emits no background completion/status/resume hints.
- [ ] [P20-TS04] `thoth ask "extended immediate file" --mode thinking --provider openai --out answer.md` writes a non-empty `answer.md`, suppresses streamed stdout, and creates no default result file.
- [ ] [P20-TS05] `--out -,answer.md` tees real streamed output to stdout and file; both are non-empty.
- [ ] [P20-TS06] repeatable `--out - --out answer.md` behaves like the comma-list tee form.
- [ ] [P20-TS07] `--append` appends instead of truncating: run twice to the same file and assert file size grows and the first run's content prefix is preserved.
- [ ] [P20-TS08] bare prompt form supports leading `--out`: `thoth --out answer.md --provider openai "extended bare leading"`.
- [ ] [P20-TS09] bare prompt form supports trailing `--out`: `thoth "extended bare trailing" --provider openai --out answer.md`.
- [ ] [P20-TS10] immediate `--output-dir DIR` alone does not create a background-style result file.
- [ ] [P20-TS11] immediate `--quiet` still streams the answer but suppresses progress/background-only UI.

**Background real-API workflows, mirror BG-* and file-output tests**
- [ ] [P20-TS12] `thoth deep_research "extended bg async" --provider openai --async` returns an operation ID, writes a checkpoint, and `thoth status <op-id>` reports a valid queued/running/completed state; cancel if still active.
- [ ] [P20-TS13] `thoth cancel <op-id>` against a running real OpenAI background job marks the checkpoint cancelled and exits 0.
- [ ] [P20-TS14] gated slow test: synchronous `thoth deep_research "extended bg complete" --provider openai --output-dir DIR` eventually exits 0 and writes a non-empty OpenAI result file with metadata.
- [ ] [P20-TS15] `--project extended-project` writes under `base_output_dir/extended-project/` and reports the project output location.
- [ ] [P20-TS16] `--input-file input.md` records `input_files:` metadata in the generated result.
- [ ] [P20-TS17] `--no-metadata` writes a non-empty result file without YAML metadata, `operation_id:`, or the `### Prompt` section.
- [ ] [P20-TS18] `--quiet` still writes the result file while suppressing `Research completed`, `Results saved to:`, progress text, and status/list hints as appropriate for quiet background mode.
- [ ] [P20-TS19] `--prompt-file prompt.txt` uses the prompt file; assert metadata or output path reflects the file prompt enough to prove the prompt source was honored.
- [ ] [P20-TS20] `--prompt-file -` accepts stdin in a subprocess run and completes or submits correctly.
- [ ] [P20-TS21] `--api-key-openai sk-...` works without `OPENAI_API_KEY` in the environment and does not leak the key in stdout/stderr.

**Chained and multi-output workflows**
- [ ] [P20-TS22] gated slow test: `--auto` chain in one project. Run a first background mode that writes an output, then run the next background mode with `--auto --project same-project`; assert the second operation records the previous output under `input_files:`.
- [ ] [P20-TS23] `--auto` with no previous project output prints the warning and does not crash.
- [ ] [P20-TS24] `--combined` real-provider test remains skipped until at least two real providers are operational, or until a mixed real+mock policy is explicitly accepted. When enabled, assert separate provider outputs plus a combined report are written and the combined report contains provider section headers.
- [ ] [P20-TS25] no `--combined` means no combined report is written, even when multiple provider outputs exist.

**Real provider runtime contract expansion**
- [ ] [P20-TS26] Extend `tests/extended/test_model_kind_runtime.py` so every `KNOWN_MODELS` entry also proves the provider path used matches the declared kind:
  - immediate models exercise `provider.stream()` and produce at least one text delta;
  - background models exercise `submit()` + `check_status()` and are cancellable when still running.
- [ ] [P20-TS27] Add a mismatch defense test with real provider construction but no HTTP call: immediate-declared deep-research model raises `ModeKindMismatchError` before any request is made.

### Acceptance Criteria
- `uv run pytest -q` still reports the extended workflow tests as deselected by default.
- `uv run pytest -m extended tests/extended/test_real_api_workflows.py -v` runs the fast real-API workflow tests when `OPENAI_API_KEY` is present.
- Slow/costly background completion and `--auto` chain tests are separately gated and documented in their skip reasons.
- Every immediate mock workflow with `--out`, tee, append, bare prompt, quiet, and no default result file has a corresponding real-API extended test.
- Every background mock workflow for project, input file, no metadata, quiet, prompt-file, stdin, CLI API key, status/cancel, and output-file creation has a corresponding real-API extended test or a documented provider-availability skip.
- `--combined` and `--auto` are explicitly covered by future extended tests, not just by mock/integration tests.

## [ ] Project P18: Immediate vs Background — Explicit `kind`, Runtime Mismatch, Path Split, Streaming, Cancel (v3.1.0)

**Primary spec**: `docs/superpowers/specs/2026-04-26-p18-immediate-vs-background-design.md` (decisions Q1–Q12 §4, architecture §5, rollout §6, testing strategy §7, cross-project coordination §8, risks §9, **§11 reevaluation log 2026-04-27**)
**Plan**: `docs/superpowers/plans/2026-04-26-p18-immediate-vs-background.md` (TDD discipline, phase dependency graph, file map, Phase A starter steps, commit cadence, end-of-project checklist, **call-site migration matrix**, **reevaluation 2026-04-27**)

**Reevaluated 2026-04-27 against post-P16-PR3 codebase.** P16 PR1+PR2+PR3 shipped to `main` in commit `f8b62f2`; v3.0.0 release tag pending release-please. P18 lands as **v3.1.0** (next minor on v3 line). Several P18 hooks are already in the codebase awaiting wiring: `completion/sources.py:79 mode_kind` is dead-code "for P18 forward-compat"; `progress.py:should_show_spinner` already gates spinner on `is_background_model`; `interactive_picker.py:44` filters `--pick-model` candidates "immediate models only"; `cli_subcommands/ask.py:176` uses `is_background_mode(mode_config)` for the `--json` Option E split. Architecture/decisions unchanged; only file references and target version changed. See spec §11 for the full delta.

**Goal**: Make the immediate-vs-background execution distinction a first-class, explicit property of every mode. Promote the existing `Kind = Literal["immediate", "background"]` vocabulary (`modes_cmd.py:22`) to a required `kind` field on every builtin mode, derive a `KNOWN_MODELS` registry from `BUILTIN_MODES` (single source of truth, cross-mode consistency enforced), and surface mode/model mismatches at **runtime** (not config-load) via a typed `ModeKindMismatchError` raised by the provider's `submit()`. Split `_execute_research` (`run.py:550`) into `_execute_immediate` (no progress bar, no spinner, no resume/status hints, streams output) and `_execute_background` (current behavior, renamed). Add a `provider.stream()` contract for the immediate path with `--out FILE` / `--out -,FILE` / `--append` flags wired into `cli_subcommands/_options.py:_RESEARCH_OPTIONS` (so both top-level CLI and `thoth ask` inherit them) and backed by a `MultiSink`. Add a `provider.cancel()` capability per provider, gated on per-provider research, plus a `thoth cancel <op-id>` subcommand mirroring the `cli_subcommands/resume.py` pattern. Wire the dead-code `--kind` filter on `thoth modes` using `completion/sources.py:79 mode_kind`. Rename `mini_research` → `quick_research` (deprecation alias). Add an extended-only test suite, parametrized over `KNOWN_MODELS`, that hits the real API to verify each model's declared kind matches actual API behavior — gated behind `pytest -m extended` / `./thoth_test --extended`, never on default runs.

**Coordination with shipped P16 (v3.0.0 — landed in `f8b62f2`)**: `thoth ask` is the canonical scripted research entrypoint and inherits `_research_options`. P18's path split happens **inside** the existing dispatch — `thoth ask "..." --mode <immediate-mode>` automatically gets streaming behavior. `thoth ask --json` already implements the kind-aware split (Option E in `cli_subcommands/ask.py:158-231`); P18 brings the same split to the human-readable path. No PR2/PR3 changes required.

**Follow-up tracked separately**: requiring `kind` on user-defined modes lands as **warn-once** in P18; the **error** form is deferred to a future P19 / **v4.0.0** breakage window (when the next major opens — v3.0.0 is already locked by P16 breakages).

**Future test-hardening project**: add dedicated background-mode regression coverage for `--combined` and `--auto`. P18 now pins the immediate/background split and the core background options, but `--combined` multi-provider report generation and `--auto` cross-run input chaining still need explicit tests under the new contract.

**Out of Scope**
- Renaming mode `thinking` (kept — `kind` carries the execution-model semantics now; further renaming would collide with PR2's `ask` subcommand)
- `--out` for **background** mode (deferred — background already has `--project` + combined-report mechanics; bolting `--out` on is a separate conversation)
- Reworking reasoning-summary rendering in streaming mode (gated behind a future `--show-reasoning` flag, design TBD)
- Implementing Perplexity/Gemini providers (still `NotImplementedError`; their `cancel()` and `stream()` impls land when the providers do)
- Removing the `is_background_model` substring rule from the runtime mismatch check — it remains the source of truth for "what does *this provider* require for this model?"
- Erroring on user modes missing `kind` (warn-once only in P18; error form deferred to v3.0.0 follow-up)

### Design Notes
- **`KNOWN_MODELS` derivation** (`models.py` or `config.py`): built once at import time from `BUILTIN_MODES`. Same `(provider, model)` pair appearing under two different `kind` values across builtins → `ThothError` at module import (we shipped a broken config). User-only models are intentionally excluded from `KNOWN_MODELS` — user opted in, user owns kind correctness.
- **Mismatch is detected at the provider, not the config layer.** `OpenAIProvider.submit()` calls `self._validate_kind_for_model(mode)` first thing; raises `ModeKindMismatchError` if `declared_kind == "immediate"` but `is_background_model(self.model)`. The reverse (`background` declared, regular model) is legal — OpenAI lets you force-background any model. `create_provider` (`providers/__init__.py:107`) threads `mode_config["kind"]` into `provider_config`.
- **`mode_kind(cfg) -> Literal["immediate","background"]`** replaces `is_background_mode` as the canonical resolver. Precedence: explicit `kind` field → legacy `async: bool` (deprecation warning) → substring sniff on model name (warn-once for user modes, error for builtins missing `kind`).
- **Path split** (`run.py`): `execute(...)` matches on `mode_kind(mode_config)` and dispatches to `_execute_immediate` or `_execute_background`. Immediate path skips: progress bar, polling loop, `transition_to("running")` checkpoint write, resume hint on failure, operation-ID echo (unless `--project` or `--out FILE` set).
- **`provider.stream()`** new contract on `ResearchProvider` base: `async def stream(prompt, mode, system_prompt, verbose) -> AsyncIterator[StreamEvent]`. OpenAI impl uses `client.responses.stream(...)`. Mock yields deterministic chunks for tests. Default base raises `NotImplementedError`. Defense in depth: providers refuse to stream a model whose API requires background — but the runtime mismatch check should already have caught it.
- **`MultiSink`** sinks `write(chunk)` to a list of `IO[str]`. stdout is one entry; file is opened lazily on first chunk (don't truncate on empty output) and closed in `finally`. `--out -` (default), `--out FILE`, `--out -,FILE`, repeatable `--out` flag, `--append` flag for non-truncating writes.
- **`provider.cancel(job_id)`** new optional contract; default raises `NotImplementedError`. OpenAI impl calls `client.responses.cancel(job_id)` for background jobs. Per-provider research items below cover Perplexity + Gemini before any non-OpenAI cancel impl is attempted.
- **Mode rename**: `mini_research` → `quick_research`. The old name remains in `BUILTIN_MODES` carrying a `_deprecated_alias_for: "quick_research"` marker; `get_mode_config` resolves through it with a one-time deprecation warning. Deletion targets v3.0.0 follow-up.
- **`thoth cancel <op-id>`** subcommand: loads operation from checkpoint, instantiates each provider that has a non-completed job, calls `cancel()` (catches `NotImplementedError` and reports "this provider does not support upstream cancellation; the local checkpoint is marked cancelled"), updates checkpoint to `cancelled`, exits 0. Ctrl-C during a running background op should also call `cancel()` best-effort with a short timeout before exiting.
- **Extended test suite**: `tests/extended/` directory; `@pytest.mark.extended` registered in `pyproject.toml`; default `addopts = "-m 'not extended'"` skips it. Parametrized over `KNOWN_MODELS`; submits a tiny ping prompt, asserts kind contract holds (immediate → first `check_status` is `completed`; background → `running`/`queued`/`completed`); calls `cancel()` after confirming a background submission to limit cost. Run via `uv run pytest -m extended` / `just test-extended` / `./thoth_test -r --extended`. Designed for nightly CI, not PR CI.
- **Cleanup last**: once the path split is firm and immediate runs no longer flow through the polling loop, delete the `if not job_info.get("background", False): return {"status": "completed"}` shortcut in `OpenAIProvider.check_status` (`providers/openai.py:232-233`) — it becomes unreachable.

### Tests & Tasks
**Phase A — `kind` schema + `KNOWN_MODELS` derivation (no behavior change)**
- [ ] [P18-TS01] `tests/test_builtin_modes_have_kind.py`: every entry in `BUILTIN_MODES` declares `kind ∈ {"immediate","background"}`
- [ ] [P18-TS02] `tests/test_known_models_registry.py`: `derive_known_models()` returns one entry per unique `(provider, model)` across builtins; cross-mode kind conflicts raise `ThothError` at module import
- [ ] [P18-TS03] `tests/test_known_models_registry.py`: every builtin's `(provider, model, kind)` triple appears in `KNOWN_MODELS`
- [ ] [P18-T01] Add `kind` field to all 12 entries in `BUILTIN_MODES` (`config.py:42-133`)
- [ ] [P18-T02] Add `ModelSpec` NamedTuple + `derive_known_models()` + module-level `KNOWN_MODELS` constant (in `models.py`)
- [ ] [P18-T03] Add `mode_kind(cfg) -> Literal["immediate","background"]` resolver in `config.py`; thin `is_background_mode` wrapper kept for compat with deprecation comment
- [ ] [P18-T03b] **(Reeval 2026-04-27)** Update `modes_cmd.py:_derive_kind` (`modes_cmd.py:46-50`) to read `cfg["kind"]` first; fall back to substring heuristic only with a warning. Pre-existing CLI surface (`thoth modes` table "Kind" column) keeps working unchanged.
- [ ] [P18-T03c] **(Reeval 2026-04-27)** Audit summary deliverable: write `planning/p18-call-site-audit.md` enumerating the 9 `is_background_*` call sites (per spec §10 acceptance gate); annotate each with disposition (migrate to `mode_kind` / keep as model-level helper / no-op).

**Phase B — Runtime mismatch error (additive, user-visible)**
- [ ] [P18-TS04] `tests/test_mode_kind_mismatch.py`: `OpenAIProvider.submit(...)` with `kind="immediate"` + `model="o3-deep-research"` raises `ModeKindMismatchError` *before* any HTTP call (use `respx`/cassette to assert no API hit)
- [ ] [P18-TS05] Same with `kind="immediate"` + `model="o4-mini-deep-research"`
- [ ] [P18-TS06] `kind="background"` + `model="o3"` does NOT raise (legal force-background)
- [ ] [P18-TS07] `tests/test_mode_kind_mismatch.py`: `ModeKindMismatchError` carries `mode_name`, `model`, `declared_kind`, `required_kind` attrs and renders a user-facing `suggestion` referencing `[modes.{mode_name}]`
- [ ] [P18-T04] Add `ModeKindMismatchError` class to `errors.py` (subclass of `ThothError`)
- [ ] [P18-T05] Thread `mode_config["kind"]` through `create_provider` (`providers/__init__.py:107-112`) into `provider_config["kind"]`; replace the `is_background_mode(provider_config)` call at `providers/__init__.py:111` with `mode_kind(provider_config) == "background"`
- [ ] [P18-T06] Add `OpenAIProvider._validate_kind_for_model(mode)` and call it as the first line of `submit()`. The check uses `is_background_model(self.model)` (model-level helper, kept) to determine *required* kind.

**Phase C — Path split + hint suppression**
- [ ] [P18-TS08] `tests/test_immediate_path.py`: an immediate-mode run produces no `Progress` rendering, no spinner, no operation-ID echo (unless `--project` or `--out FILE` set), no `thoth resume` hint on failure
- [ ] [P18-TS09] `tests/test_background_path.py`: existing background-mode behavior unchanged (regression gate — uses existing fixtures including spinner-engaged TTY case)
- [ ] [P18-TS10] `tests/test_immediate_path.py`: an immediate-mode run with `--project foo` DOES write a checkpoint and emit operation ID
- [ ] [P18-TS10b] **(Reeval 2026-04-27)** `tests/test_progress_gating.py`: `should_show_spinner` returns `False` for immediate-kind runs (extends existing `progress.py:16-36` test coverage); `_poll_display` falls through to a no-display branch (neither spinner nor Progress) for immediate-kind in TTY
- [ ] [P18-T07] Rename `_execute_research` (`run.py:550`) → `_execute_background` in `run.py`; extract a top-level `execute(...)` dispatcher that matches `mode_kind(mode_config)`
- [ ] [P18-T08] Add `_execute_immediate` (initially non-streaming — single `submit()` call, direct `get_result()` call, sink to stdout); skips progress bar, spinner, polling loop, resume hints
- [ ] [P18-T08b] **(Reeval 2026-04-27)** Extend `_poll_display` (`run.py:57-90`) and `should_show_spinner` (`progress.py:16-36`) to also suppress the `Progress` bar branch for immediate-kind runs (today: spinner is gated, Progress fires unconditionally). Add a `mode_cfg` or `mode_kind` parameter so the gate is mode-aware, not just model-aware.
- [ ] [P18-T09] Audit `run.py:629,654,691,692` and `run.py:199,311,313` and `signals.py:93,99` and `commands.py:227,238` — gate every `thoth resume {id}` / `thoth status {id}` / `Operation ID:` emission on `mode_kind(mode_config) == "background"` (or persistence flag set)
- [ ] [P18-T09b] **(Reeval 2026-04-27)** Migrate `cli.py:284` (`_thoth_config.is_background_model(model_name)` call) to `mode_kind(mode_config) == "background"` once a mode_cfg is in scope. If `mode_cfg` not available at that call site, leave as `is_background_model(model_name)` (model-level helper) and document.
- [ ] [P18-T09c] **(Reeval 2026-04-27)** Migrate `interactive_picker.py:35,44` (`is_background_model(model)` filter on `--pick-model` candidates) to `mode_kind(mode_cfg) == "immediate"`. UX unchanged.
- [ ] [P18-T09d] **(Reeval 2026-04-27)** Migrate `cli_subcommands/ask.py:171,176` (`is_background_mode(mode_config)` for Option E `--json` envelope) to `mode_kind(mode_config) == "background"`. Behavior unchanged.

**Phase D — Mode rename + `thoth modes --kind` filter**
- [ ] [P18-TS11] `tests/test_mode_aliases.py`: `--mode mini_research` resolves to `quick_research`'s config, prints a one-time deprecation warning per process
- [ ] [P18-TS11b] **(Reeval 2026-04-27)** `tests/test_modes_kind_filter.py`: `thoth modes --kind immediate` shows only immediate modes; `thoth modes --kind background` shows only background; invalid value rejected with `BadParameter`; tab-completion uses `completion/sources.py:79 mode_kind` (returns `["immediate","background"]`)
- [ ] [P18-T10] Add `quick_research` builtin (copy of current `mini_research` with renamed key + `kind="background"`); keep `mini_research` as `{"_deprecated_alias_for": "quick_research"}` stub
- [ ] [P18-T11] `get_mode_config` resolves alias and emits deprecation warning via stdlib `warnings`
- [ ] [P18-T11b] **(Reeval 2026-04-27)** Wire `--kind <immediate|background>` flag into `cli_subcommands/modes.py` (the existing `modes` subgroup from P11); use `shell_complete=mode_kind` from `completion/sources.py:79` (currently committed as P18 forward-compat dead code per its own docstring). Filter applies to `modes list/json` operations.
- [ ] [P18-T11c] **(Reeval 2026-04-27)** Update `cli_subcommands/_options.py:91` `--pick-model` help string from "(immediate modes only)" to "Interactively pick a model (only for modes with `kind = immediate`)" — language now reflects declared kind, not the substring heuristic.

**Phase E — Streaming + output sinks**
- [ ] [P18-TS12] `tests/test_provider_stream_contract.py`: `MockProvider.stream()` yields deterministic chunks; aggregating them equals the full mock result
- [ ] [P18-TS13] `tests/test_provider_stream_contract.py`: `OpenAIProvider.stream()` (cassette-replay) yields text deltas; final aggregated string matches non-streaming `get_result` output for the same prompt
- [ ] [P18-TS14] `tests/test_provider_stream_contract.py`: streaming a background-only model raises (defense in depth — should be unreachable post-mismatch-check)
- [ ] [P18-TS15] `tests/test_output_sinks.py`: `--out -` writes to stdout only; `--out FILE` writes to file only and creates it; `--out -,FILE` tees; `--append` opens with `"a"`, default opens with `"w"`; file is opened lazily (no empty file on aborted submit)
- [ ] [P18-T12] Add `StreamEvent` dataclass (`kind`, `text`) and `async def stream(...)` to `ResearchProvider` base raising `NotImplementedError`
- [ ] [P18-T13] Implement `MockProvider.stream()` — fixed chunk list with small `await asyncio.sleep(0)` between yields
- [ ] [P18-T14] Implement `OpenAIProvider.stream()` using `client.responses.stream(...)` for non-deep-research models; translate `response.output_text.delta` into `StreamEvent("text", delta)`
- [ ] [P18-T15] Add `MultiSink` class (in new `src/thoth/sinks.py`) — fans `write(chunk)` to a list of `IO[str]` handles, lazy file open, ordered close in `finally`
- [ ] [P18-T16] **(Reeval 2026-04-27)** Add `--out PATH` (repeatable, accepts `-`, comma-list also accepted) and `--append` flags to **`cli_subcommands/_options.py:_RESEARCH_OPTIONS`** so they are inherited by both top-level CLI and `thoth ask` (the existing `_research_options` decorator stack). Add corresponding entries to `cli_subcommands/_option_policy.py` for inheritance + validation. Wire to `MultiSink` inside `_execute_immediate` via `_run_research_default`.
- [ ] [P18-T17] Update `_execute_immediate` to call `provider.stream()` and feed chunks into the configured `MultiSink`. If `provider.stream()` raises `NotImplementedError`, fall back to `submit()` + `get_result()` and sink the final string in one chunk.

**Phase F — Cancel: research per provider**
- [ ] [P18-T18] **Research item: OpenAI cancel.** WebFetch `https://platform.openai.com/docs/api-reference/responses` (cancel endpoint section) and `https://cookbook.openai.com/examples/deep_research_api/introduction_to_deep_research_api`. Confirm: signature of `client.responses.cancel(response_id)`, accepted source states, returned status string. Document findings in `planning/p18-cancel-research.md`.
- [ ] [P18-T19] **Research item: Perplexity cancel.** WebFetch `https://docs.perplexity.ai/getting-started/models/models/sonar-deep-research` and `https://docs.perplexity.ai/guides/chat-completions-guide`. Confirm: does the async submission flow expose a cancel endpoint, or must we orphan the request_id? Document in `planning/p18-cancel-research.md`.
- [ ] [P18-T20] **Research item: Gemini cancel.** WebFetch `https://ai.google.dev/gemini-api/docs/deep-research` and `https://ai.google.dev/gemini-api/docs/interactions`. Confirm: Interactions API cancel/abort semantics. Document in `planning/p18-cancel-research.md`.

**Phase G — Cancel: implementation**
- [ ] [P18-TS16] `tests/test_provider_cancel.py`: `MockProvider.cancel(job_id)` removes the job and returns `{"status":"cancelled","error":"cancelled by user"}`
- [ ] [P18-TS17] `tests/test_provider_cancel.py` (cassette): `OpenAIProvider.cancel(job_id)` calls `responses.cancel`, returns cancelled-shaped status
- [ ] [P18-TS18] `tests/test_provider_cancel.py`: providers that don't implement cancel raise `NotImplementedError`; the `thoth cancel` CLI catches it and reports "upstream cancel not supported, local checkpoint marked cancelled"
- [ ] [P18-TS19] `tests/test_cancel_subcommand.py`: `thoth cancel <op-id>` updates the checkpoint to `cancelled`, calls `provider.cancel()` for each non-completed provider, exits 0
- [ ] [P18-TS20] `tests/test_cancel_subcommand.py`: `thoth cancel MISSING_ID` exits 6 (matching `thoth resume` missing-op behavior)
- [ ] [P18-T21] Add `async def cancel(self, job_id: str) -> dict[str, Any]` to `ResearchProvider` base raising `NotImplementedError`
- [ ] [P18-T22] Implement `MockProvider.cancel()`
- [ ] [P18-T23] Implement `OpenAIProvider.cancel()` per Phase F findings
- [ ] [P18-T24] (Perplexity/Gemini cancel impls — only if Phase F research confirms upstream support; otherwise leave as the base `NotImplementedError`)
- [ ] [P18-T25] Add `src/thoth/cli_subcommands/cancel.py` — `@click.command("cancel")`, `OP_ID` required positional, `--json` flag, delegates to a new `cancel_operation(op_id, ctx)` in `commands.py`. Mirror the `cli_subcommands/resume.py` pattern (already shipped).
- [ ] [P18-T25b] **(Reeval 2026-04-27)** Register `cancel` in `cli.py` via `cli.add_command(cancel)` and add to "Run research" help section in `ThothGroup.format_commands`. Add `shell_complete=operation_ids` to the `OP_ID` positional (using the existing completer from `completion/sources.py:26`).
- [ ] [P18-T26] Add `cancel_operation()` to `commands.py` — load operation, iterate non-completed providers, call `provider.cancel()` (catch `NotImplementedError` → emit "upstream cancel not supported, local checkpoint marked cancelled"), update checkpoint, emit user-facing summary. Returns enough data for `--json` envelope.
- [ ] [P18-T27] Wire Ctrl-C signal path (`signals.py`) to call `cancel_operation()` best-effort with a 5s timeout before exiting

**Phase H — User-mode `kind` warning (warn-once now; v4.0.0 follow-up errors)**
- [ ] [P18-TS21] `tests/test_user_mode_kind_warning.py`: a user TOML with a `[modes.X]` table missing `kind` triggers a one-time warning at config load referencing the offending key
- [ ] [P18-T28] Add the warning emission in `_validate_config` (`config.py:367`) / mode-merge path; do not error
- [ ] [P18-T29] Add a `# TODO(v4.0.0): error on missing kind in user modes` comment at the warning site, cross-referencing future P19

**Phase I — Extended test infrastructure**
- [ ] [P18-TS22] `tests/extended/test_model_kind_runtime.py`: parametrized over `KNOWN_MODELS`, hits real API, asserts immediate-kind models return `completed` on first `check_status` and background-kind models return `running`/`queued`/`completed`; cancels background submissions to limit cost (depends on Phase G `provider.cancel()`)
- [ ] [P18-T30] **(Reeval 2026-04-27)** Add a NEW `[tool.pytest.ini_options]` section to `pyproject.toml` (none present today): register `extended` marker; add `addopts = "-m 'not extended'"` to default invocation. Verify pre-commit `./thoth_test` integration suite is unaffected (it uses its own runner, not pytest markers).
- [ ] [P18-T31] Add `just test-extended` recipe → `uv run pytest -m extended -v`
- [ ] [P18-T32] Add `--extended` flag to `thoth_test` runner (parses to a category column); wire to category filter
- [ ] [P18-T33] Add `.github/workflows/extended.yml` (nightly cron, gated on `OPENAI_API_KEY` repo secret); failures notify but don't block PRs

**Phase J — Documentation + cleanup**
- [ ] [P18-T34] Update `README.md` with `--out` flag examples; document the `kind` field for user-defined modes; document `thoth cancel`; document `thoth modes --kind <immediate|background>` filter
- [ ] [P18-T35] Update `manual_testing_instructions.md` with immediate-vs-background streaming/cancel/modes-filter scenarios
- [ ] [P18-T36] Remove the `if not job_info.get("background", False): return {"status": "completed"}` shortcut in `OpenAIProvider.check_status` (`providers/openai.py:232-233`) — unreachable post-Phase C. Run `uv run pytest tests/` first to confirm no test depends on the shortcut implicitly.
- [ ] [P18-T36b] **(Reeval 2026-04-27)** Update spec `docs/superpowers/specs/2026-04-26-p18-immediate-vs-background-design.md` Status field from "Draft" → "Shipped (v3.1.0, commit `<HASH>`)". Update plan with the same status note.
- [ ] [P18-T37] CHANGELOG entries (non-breaking — additive only) — release-please will pick these up for **v3.1.0**: `feat: explicit "kind" field on built-in modes`, `feat: streaming output for immediate modes (--out)`, `feat: thoth cancel <op-id>`, `feat: thoth modes --kind <immediate|background> filter`, `feat: rename mini_research mode to quick_research (alias kept)`, `chore: deprecate "async" mode-config key`

- [ ] Regression Test Status

### Automated Verification
- `uv run pytest tests/test_builtin_modes_have_kind.py tests/test_known_models_registry.py tests/test_mode_kind_mismatch.py tests/test_immediate_path.py tests/test_background_path.py tests/test_progress_gating.py tests/test_mode_aliases.py tests/test_modes_kind_filter.py tests/test_provider_stream_contract.py tests/test_output_sinks.py tests/test_provider_cancel.py tests/test_cancel_subcommand.py tests/test_user_mode_kind_warning.py -v` — all green
- `uv run pytest tests/` — full suite green
- `./thoth_test -r --skip-interactive -q` — full suite green
- `just check` — green (ruff + ty)
- `uv run pytest -m extended -v` — green when `OPENAI_API_KEY` is present (nightly CI; not gating PRs)
- No reachable call to `is_background_model` substring sniffing on a builtin mode (covered by P18-TS01)
- **(Reeval 2026-04-27)** `grep -rn "is_background_mode\|is_background_model" src/thoth/` returns ≤ the documented set in `planning/p18-call-site-audit.md` — no new resolution-path callers introduced

### Manual Verification
- `thoth deep_research "topic"` (or PR2's `thoth ask "topic" --mode deep_research`) behaves identically to today (background regression)
- `thoth thinking "what is X"` (or PR2's `thoth ask "what is X" --mode thinking`) streams to stdout in seconds, prints no operation ID, prints no `thoth resume` hint
- `thoth ask "..." --mode thinking --out answer.md` writes to `answer.md` only; rerun with `--append` appends; `--out -,answer.md` tees to both
- `thoth ask "..." --mode mini_research` prints a deprecation warning pointing at `quick_research`, then runs as background
- Edit user TOML, add `[modes.foo]` with provider/model but no `kind` → next thoth run prints a one-time warning at config load, then proceeds (warn-only in v3.1.0; v4.0.0 will error)
- **(Reeval 2026-04-27)** `thoth modes --kind immediate` filters the table to just immediate modes; `thoth modes --kind background` to just background; tab-completing the value offers `immediate` / `background`
- `thoth ask "..." --mode quick_research --model o3` (manual override forcing immediate kind on a background-only model) → fails fast with `ModeKindMismatchError` carrying `[modes.quick_research]` config-edit suggestion; no API call made
- `thoth cancel <op-id>` for a running background op → checkpoint updated to `cancelled`, OpenAI `responses.cancel` called, exit 0
- `thoth cancel <op-id>` for a completed op → exits with helpful "operation already completed" message
- Ctrl-C during a `deep_research` run → cancellation issued upstream before process exits

### Acceptance criteria
- Every builtin mode has a `kind` field; `KNOWN_MODELS` is derived (no separate registry)
- A misconfigured mode (immediate kind + deep-research model) fails at provider `submit()` with `ModeKindMismatchError` before any API call
- Immediate runs do not emit polling progress, operation IDs (unless persisted), or resume hints
- `--out` supports stdout, file, tee, and append for immediate runs
- `provider.cancel()` exists on the base; OpenAI + Mock implement it; Perplexity/Gemini status reflects research findings
- `thoth cancel <op-id>` cancels in-flight background ops upstream and updates the checkpoint
- Extended test suite parametrizes over `KNOWN_MODELS` and runs only under the `extended` marker

---

## [ ] Project P17: thoth-ergonomics-v1 Spec Round-Trip — Annotate Implementation Status (no code change)
**Goal**: Close the documentation round-trip on the `thoth-ergonomics-v1` spec. The spec was never back-linked from `PROJECTS.md`, which silently allowed §3.4 (decided dropped) and §3.7 (already shipped) to look "open" from a `PROJECTS.md`-only audit. After this project, the spec itself carries an `## Implementation status` block citing the project/task IDs (P11, P14, dropped) for each §3 item, so future audits can grep the spec to know it's fully accounted for. **Zero code change** — this is purely a documentation correctness project.

**Primary spec**: `docs/superpowers/specs/2026-04-24-thoth-ergonomics-design.md`
**Implementation plan that records the dropped scope**: `planning/thoth.plan.v9.md:18` — *"❌ Drop v8 Task 6 — `thoth workflow` command. User direction; `thoth modes` already shows kind."*

### Spec § → outcome map (the actual deliverable, recorded inline so this project entry is self-contained)

| Spec § | Item | Outcome | Where |
|---|---|---|---|
| 3.1 | `providers` subcommand group | ✅ Shipped | P14-T06 (`v2.13.0`) |
| 3.2 | thothspinner sync-poll progress | ✅ Shipped | P14-T07/T08/T09 (`v2.13.0`) |
| 3.3 | Mode-ladder help reorganization | ✅ Shipped (simplified per v9 plan) | P14-T04 (`v2.13.0`) — `help.py:127` workflow chain string |
| **3.4** | **`thoth workflow` / `thoth guide` command** | **`[~]` Won't fix** — superseded by `thoth modes` (P11) | Decision: `planning/thoth.plan.v9.md:18`. Rationale: `thoth modes` already lists every mode with provider/model/`kind=immediate\|background`/source/description in one table, making a separate workflow-ladder command redundant. Adding `thoth workflow` would duplicate discovery surface. |
| 3.5 | API-key documentation pass + `thoth help auth` | ✅ Shipped | P14-T05 (`v2.13.0`) |
| 3.6 | `--input-file` vs `--auto` clearer help | ✅ Shipped | P14-T03 (`v2.13.0`) — verified in current `--help` |
| 3.7 | `-v` / `--verbose` worked example in help | ✅ Shipped (one-liner form) | P14-T04 (`v2.13.0`) — `help.py:135` (`Debug API issues: thoth deep_research "topic" -v`); test at `tests/test_cli_help.py:29` (`test_help_has_verbose_example`). Per spec line 230 ("documentation follows behavior"), the realized form is a single example line, not the multi-line block originally drafted in spec §3.7. |
| 3.8 | Surface config path on errors | ✅ Shipped | P14-T01/T02 (`v2.13.0`) — `format_config_context()` in `errors.py`; verified live (error message includes "Config file:" and "Env checked:") |
| 3.9 | `--pick-model` interactive flag | ✅ Shipped | P14-T11/T12 (`v2.13.0`); P15 follow-up bug fixes |
| §4 | `is_deep_research_model` shared helper | ✅ Shipped (renamed) | P11 / P13 — became `is_background_mode` / `is_background_model` |
| §4 | `format_config_context` helper | ✅ Shipped | P14-T01 |
| §4 | Help rendering helpers | ✅ Shipped | P14-T04, P14-T05 |

**Net:** 8 of 9 §3 items shipped + 3 of 3 §4 helpers shipped; 1 item (§3.4) explicitly retired with rationale.

**Out of Scope**
- Reviving `thoth workflow` — explicitly retired, do not re-implement without a fresh design decision overriding `planning/thoth.plan.v9.md:18`
- Adding the multi-line `-v` example block from spec §3.7 lines 219–226 — the realized one-line form is sufficient per "doc follows behavior" (spec line 230) and a future verbose-output redesign would invalidate the multi-line example anyway
- Any code change at all — this is a documentation-only project

### Tests & Tasks
- [~] [P17-T01..06] **RETIRED** — `thoth workflow` / `thoth guide` command tasks. Decision: `planning/thoth.plan.v9.md:18` (`thoth modes` already provides discovery). Tasks intentionally numbered to preserve audit trail; do not re-allocate these IDs.
- [~] [P17-T07..08] **NOT NEEDED** — `-v` example tasks. Already shipped in P14-T04 (`help.py:135`, tested at `tests/test_cli_help.py:29`). Marking won't-fix because no follow-up work is required, not because the feature is dropped.
- [ ] [P17-T09] Add an `## Implementation status` block at the top of `docs/superpowers/specs/2026-04-24-thoth-ergonomics-design.md` reproducing the §-outcome map above. Pin each ✅ row to its `Pxx-T##` shipping task; pin §3.4 to its drop decision in `planning/thoth.plan.v9.md:18` and the supersession by P11.
- [ ] [P17-T10] Annotate `docs/superpowers/specs/2026-04-24-thoth-ergonomics-design.md:135` (the §3.4 `thoth workflow` heading) with a one-line callout: `> **Status:** Dropped per planning/thoth.plan.v9.md:18 — superseded by 'thoth modes' (P11).` so a reader landing in §3.4 directly sees the decision without scrolling to the top.
- [ ] [P17-T11] Verify `planning/project_promote_commands.md:5` and `planning/thoth.plan.v9.md:6` (the only other files that reference this spec) don't need updates — they're plan-side, the spec is the source of truth getting annotated.

### Automated Verification
- `grep -n "Implementation status" docs/superpowers/specs/2026-04-24-thoth-ergonomics-design.md` → returns line 1-region match
- `grep -n "Dropped per" docs/superpowers/specs/2026-04-24-thoth-ergonomics-design.md` → returns the §3.4 callout line
- No code, no tests, no `just check` impact — `git diff --stat` shows only the spec file changed

### Manual Verification
- Open the spec — top of file lists every §3 item with shipping commit/project, §3.4 explicitly marked dropped with link to v9 plan
- A new contributor grepping `PROJECTS.md` for `2026-04-24-thoth-ergonomics-design.md` lands on this entry and immediately sees §3.4 was dropped (no temptation to start implementing)
- Future spec audits (`grep -L "Implementation status" docs/superpowers/specs/*.md`) reveal which other specs still lack a round-trip annotation

---

## [x] Project P16 PR2: Remove Legacy Shims, Add resume + ask Subcommands (v3.0.0)
**Goal**: Remove every flag-style shim cataloged in the legacy-form audit; migrate each to a canonical Click subcommand or sub-subcommand; ensure no functionality silently disappears (every removed form must either map to a new form OR be explicitly dropped with documented justification). Triggers v3.0.0 MAJOR.

**Completed:** 2026-04-26
**Pytest count:** 389 passed
**thoth_test count:** 63 passed, 10 skipped (mock-only run: 63 passed, 1 skipped)
**Commits landed on main:** 12 (Tasks 1–12 per the implementation plan)
**FU01–FU05** remain unchecked (deferred to PR3 / P12 / Click 9.0 per scope).

**Specs**:
- `docs/superpowers/specs/2026-04-26-p16-pr2-design.md` — PR2-specific design (decisions Q1-Q7-PR2, components, testing strategy, rollout)
- `docs/superpowers/specs/2026-04-25-promote-admin-commands-design.md` — original P16 design (decisions Q2-Q7 from PR1 brainstorming)
- `docs/superpowers/specs/2026-04-26-p16-pr2-legacy-form-audit.md` — comprehensive shim inventory (the parity checklist)

**Plan**: `docs/superpowers/plans/2026-04-26-p16-pr2-implementation.md` — 12 TDD tasks mapping 1:1 to spec §10's commit sequence (~2,505 lines with bite-sized steps + concrete code blocks)

**Out of scope (PR3)**
- `--json` for every data/action admin command (already partially shipped; full coverage in PR3)
- `completion` subcommand and dynamic completers
- Per-handler `get_*_data()` extraction
- Mode-editing operations (`thoth modes set/add/unset` — P12)
- New 3/4 exit codes — keep today's 0/1/2 scheme (spec §8.3)
- Behavior changes in handlers below the dispatch (handlers in `commands.py`/`config_cmd.py`/`modes_cmd.py` stay byte-identical)

### Architectural decisions locked from brainstorming
- [Q1-PR2] resume option-set: TIGHT + HONOR — accepts `--verbose`, `--config`, `--quiet`, `--no-metadata`, `--timeout`, `--api-key-{openai,perplexity,mock}`; rejects `--auto`, `--input-file`, `--prompt-file`, `--combined`, `--project`, `--output-dir`, `--prompt`, `--async`, `--pick-model`, `--version`, `--interactive`, `--clarify` with clear `BadParameter` errors
- [Q2-PR2] modes hidden-subcommand shim: REMOVE in PR2 (decision A — full consistency with providers shim removal)
- [Q3-PR2] `ask` is a NEW canonical subcommand (positional-arg equivalent of `-q/--prompt`); bare-prompt and `-q` continue to work alongside
- [Q4-PR2] `-R` short alias for `--resume`: REMOVED with `--resume` (audit line 8)
- [Q5-PR2] `ignore_unknown_options=True` on top-level group: REMOVED (typos like `--verbsoe` exit 2 instead of being silently swallowed)
- [More decisions captured during brainstorming will be added as they're locked]

### Migration tasks (one per legacy form — every section-10 row)

**`--resume` family (audit lines 411-416)**
- [x] [P16PR2-T01] Migrate `thoth --resume OP_ID` → `thoth resume OP_ID`. Implement `resume` subcommand at `src/thoth/cli_subcommands/resume.py` accepting honored options per [Q1-PR2]. Update emitters at `run.py:629/654/827/854`, `signals.py:93/99`, `commands.py:227/238`, `help.py:134`. Update fixture regex at `tests/_fixture_helpers.py:63-65`.
- [x] [P16PR2-T02] Remove top-level `--resume`/`-R` global flag from `src/thoth/cli.py:477`. Remove `_dispatch_click_fallback` resume branch at `cli.py:347-358`. Add gating: `thoth --resume OP_ID` exits 2 with stderr suggestion `"Use 'thoth resume OP_ID'"`.
- [x] [P16PR2-T03] Remove `-R OP_ID` short alias (same removal — both `--resume` and `-R` reach same handler per audit line 8). Confirm exit-2 hint applies.
- [x] [P16PR2-T04] Reject combo `thoth resume <op> --pick-model` at the new `resume` subcommand level (currently rejected at cli.py:621-622 — preserve `BadParameter` semantics, exit 2). Migrate `tests/test_pick_model.py:48,109`.
- [x] [P16PR2-T05] Reject combo `thoth resume <op> --async` at the new subcommand (currently rejected at cli.py:609-610). Audit line 414 — currently untested in pytest.
- [x] [P16PR2-T06] Reject combo `thoth resume <op> --interactive` / `--clarify` (DESIGN: per [Q1-PR2] TIGHT, both rejected with `BadParameter`). Currently silently lets resume win (audit line 60) — make explicit error.
- [x] [P16PR2-T07] Honor `thoth --config <path> resume <op>` group inheritance via `_apply_config_path` BEFORE resume call (preserve cli.py:345 production behavior currently untested per audit line 43, line 416).

**`providers --` family (audit lines 417-430)**
- [x] [P16PR2-T08] Remove `providers -- --list` legacy shim implementation at `src/thoth/cli_subcommands/providers.py:34-99`. Add gating: exits 2 with stderr suggestion `"Use 'thoth providers list'"`.
- [x] [P16PR2-T09] Remove `providers -- --models` legacy shim. Add gating exit-2 suggestion `"Use 'thoth providers models'"`.
- [x] [P16PR2-T10] Remove `providers -- --keys` legacy shim (currently UNTESTED in pytest, audit line 114). Add gating exit-2 suggestion `"Use 'thoth providers check'"`.
- [x] [P16PR2-T11] DESIGN-DECISION: `providers -- --refresh-cache` ALONE today is silent no-op (audit line 115, line 420). Decide: gate to exit 2 with suggestion to use `providers models --refresh-cache`, OR drop silently. Recommend exit 2.
- [x] [P16PR2-T12] DESIGN-DECISION: `providers -- --no-cache` ALONE today is silent no-op (audit line 116, line 421). Same decision as T11.
- [x] [P16PR2-T13] Add `--refresh-cache` flag to `providers models` leaf in `cli_subcommands/providers.py`; forward to `commands.providers_command(refresh_cache=True)` (audit line 422 — UNTESTED but in production via legacy `-- --models --refresh-cache`).
- [x] [P16PR2-T14] Add `--no-cache` flag to `providers models` leaf; forward to `commands.providers_command(no_cache=True)` (audit line 423 — UNTESTED but in production).
- [x] [P16PR2-T15] Verify `providers models --provider X --refresh-cache` works after T13 (PRD v24 documents this; audit line 424).
- [x] [P16PR2-T16] Reject combo `providers models --refresh-cache --no-cache` with `BadParameter` (audit line 425, line 129 — currently silent ambiguity). Add explicit mutex.
- [x] [P16PR2-T17] Document removal of `--list --keys` silent-drop combo (audit line 426 — resolved structurally by separate leaves; no action needed beyond confirmation).
- [x] [P16PR2-T18] Remove in-group hidden shim `providers --list` at `providers.py:140-149`. Add gating exit-2 suggestion (audit line 427).
- [x] [P16PR2-T19] Remove in-group hidden shim `providers --models` at `providers.py:152-161`. Add gating exit-2 suggestion (audit line 428).
- [x] [P16PR2-T20] Remove in-group hidden shim `providers --keys` at `providers.py:164-173`. Add gating exit-2 suggestion (audit line 429).
- [x] [P16PR2-T21] Remove undocumented `--check` alias for `--keys` at `providers.py:53` (audit line 120, line 430). No test, no docs — drop silently or with exit-2 hint.
- [x] [P16PR2-T22] DESIGN-DECISION: `thoth providers` (no leaf) — currently exits 0 with help (providers.py:60); `tests/test_p16_dispatch_parity.py:89` accepts 0 OR 2. Pick canonical exit (audit line 250, line 431). Recommend Click default exit 2 for required-subcommand consistency.
- [x] [P16PR2-T23] Update `commands.py` self-references in help text (commands.py:321,333,335,337,339,341,343,409,410) from `thoth providers -- [OPTIONS]` to flat forms (audit line 211).
- [x] [P16PR2-T24] Update `src/thoth/providers/openai.py:69` reference `'thoth providers -- --models --provider openai'` to new flat form (audit line 212).

**`modes --` hidden-shim family (audit lines 432-440)**
- [x] [P16PR2-T25] DESIGN-DECISION: `thoth modes` (no leaf) — currently behaves as `modes list`; `tests/test_p16_thothgroup.py:223` asserts bare form lists modes (audit line 432). Decide: keep shortcut OR require explicit leaf. Per [Q2-PR2] FULL-CONSISTENCY: require explicit leaf; bare form exits 2 with suggestion `"Use 'thoth modes list'"`.
- [x] [P16PR2-T26] Remove `thoth modes --json` hidden subcommand at `cli_subcommands/modes.py:72-75`. Add gating exit-2 suggestion `"Use 'thoth modes list --json'"` (audit line 433 — UNTESTED directly).
- [x] [P16PR2-T27] Remove `thoth modes --show-secrets` hidden subcommand at `modes.py:78-81`. Add gating exit-2 suggestion. **Security-relevant** per audit line 287: callers depending on secret-reveal would silently get masked output. Migration hint must be loud.
- [x] [P16PR2-T28] Remove `thoth modes --full` hidden subcommand at `modes.py:84-87`. Add gating exit-2 suggestion (audit line 435).
- [x] [P16PR2-T29] Remove `thoth modes --name <NAME>` hidden subcommand at `modes.py:90-98`. Add gating exit-2 suggestion (audit line 436).
- [x] [P16PR2-T30] Remove `thoth modes --source <SRC>` hidden subcommand at `modes.py:101-109`. Add gating exit-2 suggestion (audit line 437).
- [x] [P16PR2-T31] DESIGN-DECISION: `thoth modes <UNKNOWN_OP>` — currently `ModesGroup.invoke` routes to `modes_command(arg0, …)` which returns 2 with `"unknown modes op: ..."` wording (audit line 438; thoth_test:2128). Decide: keep custom wording OR accept Click default `"No such command 'bogus_op'"`. Either way, exit code stays 2.
- [x] [P16PR2-T32] Promote `--json`, `--show-secrets`, `--full`, `--name`, `--source` to typed Click options on `modes list` leaf (audit line 440 KEEP-but-promote). Currently passthrough via `_PASSTHROUGH_CONTEXT`.

**`config` subgroup promote-to-typed (audit lines 441-462)**
- [x] [P16PR2-T33] Promote `--raw` on `config get` to typed Click option (audit line 443). **Security-adjacent**: `config_cmd.py:104` shows `--raw` BYPASSES secret masking even without `--show-secrets`. Verbatim line: `if _is_secret_key(key) and not show_secrets and not raw:`. Must be loud-documented.
- [x] [P16PR2-T34] DESIGN-DECISION: `config get KEY --raw` masking-bypass behavior (audit line 302, line 398, line 443). Options: (a) keep as masking bypass (loud-document in `--help`), (b) require explicit `--show-secrets` even with `--raw`. Recommend (b) — explicit security posture.
- [x] [P16PR2-T35] Promote `--json` on `config get` to typed Click option (audit line 444 — UNTESTED).
- [x] [P16PR2-T36] Promote `--show-secrets` on `config get` to typed Click option (audit line 445 — UNTESTED, security-adjacent).
- [x] [P16PR2-T37] Promote `--layer` on `config get` to typed Click option (audit line 446 — UNTESTED; returns wrong-layer data silently if dropped).
- [x] [P16PR2-T38] Promote `--project` on `config set` to typed Click option (audit line 448 — silent drop = wrong target file: `./thoth.toml` vs `~/.thoth/config.toml`).
- [x] [P16PR2-T39] Promote `--string` on `config set` to typed Click option (audit line 449). Without it, `_parse_value` (config_cmd.py:111-124) silently coerces `"true"/"false"/numbers` to bool/int/float — losing string intent.
- [x] [P16PR2-T40] Promote `--project` on `config unset` to typed Click option (audit line 451 — wrong-target risk).
- [x] [P16PR2-T41] Promote `--keys` on `config list` to typed Click option (audit line 453). DESIGN: reject combo `--keys --json` / `--keys --show-secrets` OR document precedence (currently `--keys` wins silently per `config_cmd.py:330-333`).
- [x] [P16PR2-T42] Promote `--json` on `config list` to typed Click option (audit line 454).
- [x] [P16PR2-T43] Promote `--show-secrets` on `config list` to typed Click option (audit line 455 — security-adjacent).
- [x] [P16PR2-T44] Promote `--layer` on `config list` to typed Click option (audit line 456).
- [x] [P16PR2-T45] Promote `--project` on `config path` to typed Click option (audit line 459). Currently `config_cmd.py:347-358` uses `"--project" in args` truthiness — typo `--projects` is silently NOT honored.
- [x] [P16PR2-T46] Promote `--project` on `config edit` to typed Click option (audit line 461).
- [x] [P16PR2-T47] DESIGN-DECISION: `thoth config help` (audit line 462) — currently two divergent paths render different output: `config help` leaf at `config_cmd._op_help` calls `help.show_config_help()` (rich-formatted), while `thoth help config` at `help_cmd.py:31-42` forwards to `config --help` (Click format). Pick one path; converge or document.

**Top-level / cross-cutting (audit lines 463-486)**
- [x] [P16PR2-T48] Add `thoth ask PROMPT` as NEW canonical subcommand at `src/thoth/cli_subcommands/ask.py` (audit line 474 — currently in `RUN_COMMANDS` at help.py:14 but NOT a registered subcommand). Inherit full research flag set per [Q3-PR2]. Register in `cli.add_command(...)` and `ThothGroup.format_commands` "Run research" section.
- [x] [P16PR2-T49] DESIGN-DECISION: `thoth deep_research "topic"` (mode-positional via `ThothGroup.invoke` at help.py:64-89) — KEEP? row at audit line 473. Removing would force mass test migration. Recommend KEEP (currently covered widely, low ROI to remove).
- [x] [P16PR2-T50] DESIGN-DECISION: `thoth "bare prompt"` (whole-argv-as-prompt via `ThothGroup.invoke`) — KEEP? row at audit line 476. Same scope-risk as T49. Recommend KEEP (`tests/test_cli_regressions.py:55` and many others).
- [x] [P16PR2-T51] Remove `thoth -h auth` / `thoth --help auth` parse-time hijack at `help.py:51-55` per Q5-PR2 row 13.ii; Click now rejects the extra topic argument.
- [x] [P16PR2-T52] Remove `thoth help auth` virtual topic at `help_cmd.py:25-28`; retain `render_auth_help()` for docs/future real command reuse.
- [x] [P16PR2-T53] DESIGN-DECISION: `thoth --clarify` (alone, without `--interactive`) — currently silent no-op (audit line 481, line 391). Decide: exit 2 if alone, OR keep silent. Recommend exit 2.
- [x] [P16PR2-T54] Remove dead `completion` listing from `ADMIN_COMMANDS` at `help.py:20` (audit line 472). Currently a phantom in help renderer with no Click command registered. Removal happens here; real `completion` subcommand lands in PR3.
- [x] [P16PR2-T55] DESIGN-DECISION: `thoth status` (no arg) currently exits 1 with `"status command requires an operation ID"` (status.py:16-18). Click's natural default for missing required argument is exit 2. Audit line 331, line 465. Decide: recapture baseline at exit 1 (preserve divergence) OR change to exit 2 (Click natural). Recommend exit 2.
- [x] [P16PR2-T56] Remove `ignore_unknown_options=True` from top-level `@click.group()` decorator per [Q5-PR2]. Audit hidden behavior change: typos like `thoth --verbsoe deep_research` will exit 2 instead of being silently absorbed. Add CHANGELOG callout.
- [x] [P16PR2-T57] Audit and remove `ctx.args` plumbing in `cli.py` if no longer reachable after T56 (spec §5.3).
- [x] [P16PR2-T58] DESIGN-DECISION: `--pick-model` precedence predicate at `cli.py:621-624` mixes `resume_id`, `interactive`, AND `first in ctx.command.commands` into a triple-OR (audit line 392, line 484-485). Decompose into separate explicit mutex checks. Cases for `interactive` and `first-in-commands` are UNTESTED.
- [x] [P16PR2-T59] Add test for `--pick-model --interactive` mutex (audit line 484 — UNTESTED).
- [x] [P16PR2-T60] Add test for `--pick-model <subcommand>` mutex e.g. `--pick-model providers` (audit line 485 — UNTESTED).

**README / docs / migration housekeeping**
- [x] [P16PR2-T61] Update `README.md:218` example `thoth --resume research-…` to new `thoth resume …` form.
- [x] [P16PR2-T62] Update `manual_testing_instructions.md` to use new forms (post-PR2 manual flow).
- [x] [P16PR2-T63] Update help epilog at `src/thoth/help.py:134` from `thoth --resume op_abc123` example to `thoth resume op_abc123`.
- [x] [P16PR2-T64] Update `planning/thoth.prd.v24.md` references to old forms.
- [x] [P16PR2-T65] CHANGELOG entries: `feat!: replace --resume flag with 'thoth resume' subcommand`, `feat!: remove 'thoth providers -- --…' legacy shim`, `feat!: remove 'thoth modes --…' hidden-subcommand shim`, `feat!: add 'thoth ask PROMPT' subcommand`, `feat!: remove ignore_unknown_options (typos now exit 2)` — release-please picks up the `!` for v3.0.0.
- [x] [P16PR2-T66] Archive `planning/project_promote_commands.md` to `archive/` per CLAUDE.md versioning policy (now superseded by spec).

### Silent-drop resolution tasks (one per untested-but-in-production behavior, audit lines 504-516)

- [x] [P16PR2-T67] SILENT-DROP: `thoth --resume <op>` exit code 6 (op not found) at `run.py:719-720`. Preserve in new `resume` subcommand. Add explicit test (P16PR2-TS04).
- [x] [P16PR2-T68] SILENT-DROP: `thoth --resume <op> --config <path>` config inheritance at `cli.py:345`. Preserve in new `resume` subcommand per [Q1-PR2] HONOR. Add explicit test (P16PR2-TS05).
- [x] [P16PR2-T69] SILENT-DROP: `thoth --resume <op> --verbose` verbose flow-through at `cli.py:354`. Preserve in new `resume` subcommand per [Q1-PR2]. Add explicit test (P16PR2-TS06).
- [x] [P16PR2-T70] SILENT-DROP: `thoth --resume <op> -i / --clarify` resume-silently-wins behavior at `cli.py:347,360`. Per [Q1-PR2] TIGHT, REJECT with `BadParameter` (covered by P16PR2-T06).
- [x] [P16PR2-T71] SILENT-DROP: `thoth providers -- --keys` (no test, audit line 508). Resolved by P16PR2-T10 gating; add new-form test for `providers check` at P16PR2-TS11.
- [x] [P16PR2-T72] SILENT-DROP: `thoth providers -- --refresh-cache` alone (silent no-op, audit line 509). Resolved by P16PR2-T11 gating decision.
- [x] [P16PR2-T73] SILENT-DROP: `thoth providers -- --no-cache` alone (silent no-op, audit line 510). Resolved by P16PR2-T12 gating decision.
- [x] [P16PR2-T74] SILENT-DROP: `thoth providers -- --models --refresh-cache` combo (audit line 511). Resolved structurally by P16PR2-T13.
- [x] [P16PR2-T75] SILENT-DROP: `thoth providers -- --models --no-cache` combo (audit line 512). Resolved structurally by P16PR2-T14.
- [x] [P16PR2-T76] SILENT-DROP: `thoth providers -- --models --provider X --refresh-cache` per-provider refresh (audit line 513, documented in PRD v24). Resolved structurally; add test at P16PR2-TS15.
- [x] [P16PR2-T77] SILENT-DROP: `thoth providers -- --refresh-cache --no-cache` silent ambiguity at `commands.py:454-455` (audit line 514, line 129). Resolved by P16PR2-T16 explicit mutex rejection. Add test asserting `BadParameter`.
- [x] [P16PR2-T78] SILENT-DROP: `thoth providers -- --list --keys` (silent drop of second flag at `commands.py:363,413,442` per audit line 515, line 130). Resolved structurally by separate leaves.
- [x] [P16PR2-T79] SILENT-DROP: `providers --check` alias for `--keys` (in-group shim, no test, no docs, audit line 516). Resolved by P16PR2-T21 removal.

### Test-coverage tasks (one per row of section 10 needing a test)

**resume subcommand tests**
- [x] [P16PR2-TS01] Test: `thoth resume <valid_op>` exits 0 + emits `"Research completed"`. Migrates `tests/test_resume.py:48`.
- [x] [P16PR2-TS02] Test: `thoth resume <op>` (permanent fail fixture) exits 7 + emits `"failed permanently"`. Migrates `tests/test_resume.py:90`.
- [x] [P16PR2-TS03] Test: `thoth resume <op>` (already completed) exits 0 + emits `"already completed"`. Migrates `tests/test_resume.py:131`.
- [x] [P16PR2-TS04] Test: `thoth resume MISSING_OP` exits 6 (audit line 70 — NEW, fills silent-drop gap T67).
- [x] [P16PR2-TS05] Test: `thoth --config <path> resume <op>` honors config inheritance (NEW, fills silent-drop gap T68).
- [x] [P16PR2-TS06] Test: `thoth resume <op> --verbose` verbose flow-through (NEW, fills silent-drop gap T69).
- [x] [P16PR2-TS07] Mutex tests: `thoth resume <op> --async`, `... --pick-model`, `... -q "prompt"`, `... -i`, `... --clarify`, `... --version` — each exits 2 with `BadParameter` (audit lines 414-415, line 60). NEW.
- [x] [P16PR2-TS08] Migrate `tests/test_pick_model.py:48,109` (`--pick-model --resume`) to new `resume` subcommand form.
- [x] [P16PR2-TS09] Migrate `tests/test_cli_regressions.py:76` (BUG-CLI-002 regression) to `thoth resume op_regression`.
- [x] [P16PR2-TS10] Verify `tests/test_cli_regressions.py:164` (BUG-CLI-010 — `--version` mutex) still triggers under new shape.

**resume gating tests**
- [x] [P16PR2-TS11] Category-F gate: `thoth --resume OP_ID` exits 2 with stderr hint `"Use 'thoth resume OP_ID'"` (covers T02).
- [x] [P16PR2-TS12] Category-F gate: `thoth -R OP_ID` exits 2 with same hint (covers T03).

**resume emitter / consumer tests**
- [x] [P16PR2-TS13] Update `tests/test_progress_spinner.py:152` to assert emitter prints `"Resume later: thoth resume op_abc123"`.
- [x] [P16PR2-TS14] Update `tests/test_cli_help.py:26` to assert `"thoth resume"` substring (was `"thoth --resume"`).
- [x] [P16PR2-TS15] Update `tests/_fixture_helpers.py:63-65` `extract_resume_id` regex from `r"thoth --resume\s+…"` to new form. Verify all RES-tests still extract op_id.
- [x] [P16PR2-TS16] Update thoth_test patterns at `thoth_test:2170` (TS-09 signal/Ctrl-C `r"Checkpoint saved\. Resume with: thoth --resume"`).
- [x] [P16PR2-TS17] Update thoth_test pattern at `thoth_test:2216` (TR-02 `r"Resume with: .*thoth --resume"`).
- [x] [P16PR2-TS18] Update thoth_test pattern at `thoth_test:2238` (TR-03 negative-assertion variant).

**providers subcommand tests**
- [x] [P16PR2-TS19] Test: `thoth providers list` exits 0 with all provider names (audit line 199).
- [x] [P16PR2-TS20] Test: `thoth providers list --provider X` filters to one provider (currently works in new form — confirm coverage).
- [x] [P16PR2-TS21] Test: `thoth providers models` exits 0 (audit line 201).
- [x] [P16PR2-TS22] Test: `thoth providers models --provider X` (no models) exits 1 (audit line 202).
- [x] [P16PR2-TS23] Test: `thoth providers models --provider invalid` exits 1, stderr contains verbatim `"Unknown provider: invalid"` AND `"Available providers: openai, perplexity, mock"` (audit line 154, line 207). Migrates `thoth_test:2290-2297` T-PROV-10.
- [x] [P16PR2-TS24] Test: `thoth providers check` exits 0 (all keys) or 2 (any missing) per audit line 203.
- [x] [P16PR2-TS25] Test: `thoth providers list` preserves verbatim `"Perplexity search AI (not.*implemented)"` row text (audit line 155, line 208). Migrates `thoth_test:2307` P07-M2-01.
- [x] [P16PR2-TS26] Test: `thoth help providers` preserves epilog patterns `--models.*List available models`, `--provider.*Filter by specific provider` (audit line 110, line 209). Migrates thoth_test T-PROV-09.
- [x] [P16PR2-TS27] Test: `thoth providers models --refresh-cache` triggers `"Fetching available models (refreshing cache)..."` from commands.py:445 (NEW, covers T13/T74).
- [x] [P16PR2-TS28] Test: `thoth providers models --no-cache` forwards `no_cache=True` (NEW, covers T14/T75).
- [x] [P16PR2-TS29] Test: `thoth providers models --refresh-cache --no-cache` rejected with `BadParameter` exit 2 (NEW, covers T16/T77).
- [x] [P16PR2-TS30] Test: `thoth providers models --provider openai --refresh-cache` works (NEW, covers T15/T76).
- [x] [P16PR2-TS31] Migrate `thoth_test:2260` T-PROV-07 `providers -- --models --provider mock` to `providers models --provider mock`.
- [x] [P16PR2-TS32] Migrate `thoth_test:2269` T-PROV-08 `providers -- --models` to `providers models`.

**providers gating tests**
- [x] [P16PR2-TS33] Category-F gate: `thoth providers -- --list` exits 2 with hint `"Use 'thoth providers list'"` (covers T08).
- [x] [P16PR2-TS34] Category-F gate: `thoth providers -- --models` exits 2 with hint (covers T09).
- [x] [P16PR2-TS35] Category-F gate: `thoth providers -- --keys` exits 2 with hint `"Use 'thoth providers check'"` (covers T10).
- [x] [P16PR2-TS36] Category-F gate: `thoth providers --list` (in-group hidden) exits 2 with hint (covers T18).
- [x] [P16PR2-TS37] Category-F gate: `thoth providers --models` (in-group hidden) exits 2 (covers T19).
- [x] [P16PR2-TS38] Category-F gate: `thoth providers --keys` (in-group hidden) exits 2 (covers T20).
- [x] [P16PR2-TS39] Update `tests/test_providers_subcommand.py:23-27` (`test_old_form_deprecated_but_works`) to assert exit-2-with-hint, OR delete if redundant with new TS33.
- [x] [P16PR2-TS40] Test: `thoth providers` (no leaf) exits per T22 decision (likely Click default exit 2). Verify `tests/test_p16_dispatch_parity.py:89` baseline.

**modes subcommand tests**
- [x] [P16PR2-TS41] Category-F gate: `thoth modes --json` exits 2 with hint `"Use 'thoth modes list --json'"` (covers T26).
- [x] [P16PR2-TS42] Category-F gate: `thoth modes --show-secrets` exits 2 with hint (covers T27).
- [x] [P16PR2-TS43] Category-F gate: `thoth modes --full` exits 2 with hint (covers T28).
- [x] [P16PR2-TS44] Category-F gate: `thoth modes --name X` exits 2 with hint (covers T29).
- [x] [P16PR2-TS45] Category-F gate: `thoth modes --source X` exits 2 with hint (covers T30).
- [x] [P16PR2-TS46] Test: `thoth modes` (no leaf) per T25 decision (exit 2 with `"Use 'thoth modes list'"` if removing default-to-list shortcut).
- [x] [P16PR2-TS47] Test: `thoth modes <UNKNOWN_OP>` per T31 decision (exit 2; wording either custom or Click-default).
- [x] [P16PR2-TS48] Test: `thoth modes list --json` (typed flag, NEW per T32).
- [x] [P16PR2-TS49] Test: `thoth modes list --show-secrets` (typed flag, NEW per T32).
- [x] [P16PR2-TS50] Test: `thoth modes list --full` (typed flag, NEW per T32).
- [x] [P16PR2-TS51] Test: `thoth modes list --name NAME` (typed flag, NEW per T32).
- [x] [P16PR2-TS52] Test: `thoth modes list --source SRC` (typed flag, NEW per T32).

**config subcommand tests**
- [x] [P16PR2-TS53] Test: `thoth config get KEY --raw` per T34 decision (masking-bypass behavior). Audit verbatim: `config_cmd.py:104` `if _is_secret_key(key) and not show_secrets and not raw:`. **Security-critical test.**
- [x] [P16PR2-TS54] Test: `thoth config get KEY --json` (typed flag, NEW per T35).
- [x] [P16PR2-TS55] Test: `thoth config get KEY --show-secrets` (typed flag, NEW per T36).
- [x] [P16PR2-TS56] Test: `thoth config get KEY --layer L` (typed flag, NEW per T37).
- [x] [P16PR2-TS57] Test: `thoth config set KEY VALUE` (NEW canonical).
- [x] [P16PR2-TS58] Test: `thoth config set KEY VALUE --project` (typed flag, NEW per T38).
- [x] [P16PR2-TS59] Test: `thoth config set KEY VALUE --string` (typed flag, NEW per T39 — verify `"true"` stays string not bool).
- [x] [P16PR2-TS60] Test: `thoth config unset KEY` (NEW canonical).
- [x] [P16PR2-TS61] Test: `thoth config unset KEY --project` (typed flag, NEW per T40).
- [x] [P16PR2-TS62] Test: `thoth config list --keys` per T41 decision (typed flag + combo policy).
- [x] [P16PR2-TS63] Test: `thoth config list --json` (typed flag, NEW per T42).
- [x] [P16PR2-TS64] Test: `thoth config list --show-secrets` (typed flag, NEW per T43).
- [x] [P16PR2-TS65] Test: `thoth config list --layer L` (typed flag, NEW per T44).
- [x] [P16PR2-TS66] Test: `thoth config list --keys --json` per T41 decision (reject combo OR document precedence).
- [x] [P16PR2-TS67] Test: `thoth config path` (NEW per audit line 458).
- [x] [P16PR2-TS68] Test: `thoth config path --project` (typed flag, NEW per T45).
- [x] [P16PR2-TS69] Test: `thoth config edit` (NEW per audit line 460).
- [x] [P16PR2-TS70] Test: `thoth config edit --project` (typed flag, NEW per T46).
- [x] [P16PR2-TS71] Test: `thoth config help` convergence per T47 decision (collapse to `thoth help config` OR keep leaf).

**ask subcommand tests**
- [x] [P16PR2-TS72] Test: `thoth ask "hello"` (mock provider) routes to default-mode research; equivalent to `thoth -q "hello"` and `thoth "hello"`.
- [x] [P16PR2-TS73] Test: `thoth ask "x" --mode deep_research --async` honors flags identically to bare-prompt path.
- [x] [P16PR2-TS74] Surprising-parse test: `thoth init` (subcommand) vs `thoth "init the database"` (bare-prompt) disambiguated correctly; `thoth ask` (no arg) exits 2.

**Top-level / cross-cutting tests**
- [x] [P16PR2-TS75] Test: `thoth list --all` (audit line 467 — UNTESTED in pytest).
- [x] [P16PR2-TS76] Test: `thoth help auth` virtual topic is removed and exits 2 (audit line 470 — covers T52).
- [x] [P16PR2-TS77] Test: `thoth -h auth` / `thoth --help auth` parse-time hijack is removed and no longer renders auth help (audit line 471 — covers T51).
- [x] [P16PR2-TS78] Test: `thoth --clarify` alone per T53 decision (audit line 481 — UNTESTED).
- [x] [P16PR2-TS79] Test: `thoth --pick-model --interactive` mutex (audit line 484 — UNTESTED, covers T59).
- [x] [P16PR2-TS80] Test: `thoth --pick-model providers` mutex (audit line 485 — UNTESTED, covers T60).
- [x] [P16PR2-TS81] Strict-options test: `thoth --verbsoe deep_research "x"` (typo) exits 2 with Click "no such option" error (covers T56 removal of `ignore_unknown_options`).
- [x] [P16PR2-TS82] Recapture `tests/baselines/status_no_args.json` per T55 decision (exit 1 vs exit 2).
- [x] [P16PR2-TS83] Recapture `tests/baselines/providers_list.json` if T18-T21 change wording (audit line 238).

### Out-of-PR2 follow-ups (deferred to PR3 or later)

- [ ] [P16PR2-FU01] (Deferred to PR3) Add `--json` to `resume`, `ask`, and every data/action admin command per spec §6.5 B-deferred extraction pattern.
- [ ] [P16PR2-FU02] (Deferred to PR3) Implement real `completion` Click subcommand (currently a phantom listing in `help.py:20` removed by P16PR2-T54).
- [ ] [P16PR2-FU03] (Deferred to PR3) `thoth resume <TAB>` op-id dynamic completer in `completion/sources.py`.
- [ ] [P16PR2-FU04] (Deferred to P12) Mode-editing operations: `thoth modes set/add/unset`.
- [ ] [P16PR2-FU05] (Deferred — Click 9.0) Re-evaluate `ctx.protected_args` deprecation warning suppression at `help.py:60-65`.

### Automated verification (PR2 acceptance criteria)
- [ ] `uv run pytest tests/` — green, count >= current baseline (312)
- [ ] `./thoth_test -r --skip-interactive` — green, count >= current baseline (63)
- [ ] `just check` — green
- [ ] `git grep "thoth --resume"` returns ZERO results in `src/`, `tests/`, `README.md`, `manual_testing_instructions.md` (except CHANGELOG and the spec/audit/plan docs themselves)
- [ ] `git grep "thoth providers --"` returns ZERO results in `src/`, `tests/`, README, docs (same exception)
- [ ] `git grep "thoth modes --"` returns ZERO results in `src/`, `tests/`, README, docs (same exception)
- [ ] Every row of audit section 10's master parity checklist has a checked-off "Test required" entry (cross-reference TS01-TS83 against audit lines 411-486)
- [ ] `grep -rn "ignore_unknown_options=True" src/thoth/cli.py` returns ZERO results (T56)

### Manual Verification
- `thoth ask "hello"` → runs default-mode research (mock provider works without API key)
- `thoth resume <op_id>` → resumes recoverable failure end-to-end
- `thoth --resume <op_id>` → exits 2 with hint pointing to `thoth resume`
- `thoth providers -- --list` → exits 2 with hint pointing to `thoth providers list`
- `thoth modes --json` → exits 2 with hint pointing to `thoth modes list --json`
- `thoth --verbsoe deep_research "x"` → exits 2 with Click "no such option" error (was silently absorbed pre-PR2)
- `thoth config get OPENAI_API_KEY --raw` → behavior matches T34 decision (masking-bypass either documented loud OR rejected without `--show-secrets`)

---

## [x] Project P16 PR3: Automation Polish — `completion` subcommand + universal `--json` (v3.0.0)
**Goal**: Ship the automation-and-scripting half of v3.0.0. Add `thoth completion {bash,zsh,fish}` (with `--install`) backed by dynamic completers in `completion/sources.py`. Add `--json` to every data/action admin command via the B-deferred per-handler `get_*_data() -> dict` extraction pattern, with envelope contract centralized in `json_output.py`. Completion script success stays raw shell output for `eval "$(thoth completion zsh)"`; `completion --json` is only for structured errors/install metadata. `help` stays human-only. Closes PRD F-70 and Plan M21-07. Lands as the final commit before release-please opens the v3.0.0 PR.

**Specs**:
- `docs/superpowers/specs/2026-04-26-p16-pr3-design.md` — PR3-specific design (decisions Q1-Q3-PR3, components, testing strategy, rollout)
- `docs/superpowers/specs/2026-04-25-promote-admin-commands-design.md` — original P16 design (Q4 completion, Q5 `--json`, §6.3 `completion/`, §6.4 `json_output.py`, §6.5 B-deferred handler pattern, §10 PR3 rollout)

**Plan**: `docs/superpowers/plans/2026-04-26-p16-pr3-implementation.md` — 20 TDD tasks mapping 1:1 to spec §10's commit sequence (~3,983 lines with bite-sized steps + concrete code blocks)

**Out of Scope**
- New subcommands beyond `completion` (PR2 already shipped `ask`/`resume`)
- Removing anything (spec §5.3: "PR3 — Nothing removed; pure addition")
- Reworking exit codes (still 0/1/2; granular `error.code` strings live inside JSON envelopes only — spec §8.3)
- Wrapping completion scripts or help text in success JSON (`completion` and `help` keep their shell/human stdout contracts)
- Migrating `interactive.py::SlashCommandCompleter` to `completion/sources.py` — optional polish, not blocker (spec §3, §6.3)

### Design Notes
- **JSON envelope contract** (spec §6.4): success = `{"status":"ok","data":{...}}`; error = `{"status":"error","error":{"code":"STRING_CODE","message":"...","details":{...}?}}`. Top-level object always. Stdlib only (`json`, `sys`).
- **Critical invariant** (spec §7.2): the subcommand wrapper is the ONLY place that knows about `--json`. Handlers below never branch on the flag. CI lint rule: `! grep -rnE "as_json" src/thoth/commands.py src/thoth/config_cmd.py src/thoth/modes_cmd.py`. If a future PR adds `as_json=True` plumbing, lint fails.
- **B-deferred extraction** (spec §6.5): each handler that needs `--json` gets a `get_*_data() -> dict` sibling extracted; the existing Rich-printing function is refactored to call the data function, then format. No `as_json` flag in handler signatures.
- **Completer data sources** (spec §6.3) live in `completion/sources.py` as pure functions: `operation_ids`, `mode_names`, `config_keys`, `provider_names`. Importable by both Click `shell_complete=` callbacks AND `interactive.py::SlashCommandCompleter` (shared-data-source design constraint from Q4).
- **`completion <shell> --install`** writes to conventional shell rc location (e.g., `~/.zshrc`, `~/.bashrc`, `~/.config/fish/completions/thoth.fish`) with prompt-before-overwrite in tty; refuses with a helpful error in non-tty unless `--force`. Detect existing `_thoth_completion` block; preview + prompt y/n.
- **fish support** (spec §13): `pyproject.toml` already pins `click>=8.0`, and `uv.lock` currently resolves Click 8.3.1, so bash, zsh, and fish are all in PR3 scope.
- **`init --json`** requires `--non-interactive` (spec §8.2). Without it: `emit_error("JSON_REQUIRES_NONINTERACTIVE", ...)` exit 2.
- **`config edit --json`**: success envelope after editor closes; failure → `emit_error("EDITOR_FAILED", ..., {"exit_code": N})`.

### Tests & Tasks
**Phase A — `json_output.py` foundation**
- [x] [P16-PR3-TS01] `tests/test_json_output.py`: `emit_json({"foo":1})` writes `{"status":"ok","data":{"foo":1}}` to stdout and exits 0
- [x] [P16-PR3-TS02] `tests/test_json_output.py`: `emit_error("CODE", "msg", {"detail":1})` writes `{"status":"error","error":{"code":"CODE","message":"msg","details":{"detail":1}}}` and exits 1; `exit_code=2` honored
- [x] [P16-PR3-TS03] Round-trip parse test: every emitted envelope is `json.loads`-able
- [x] [P16-PR3-T01] Create `src/thoth/json_output.py` with `emit_json(data)` and `emit_error(code, message, details=None, exit_code=1)`. Stdlib only.

**Phase B — `completion` subcommand**
- [x] [P16-PR3-TS04] `tests/test_completion.py`: `thoth completion bash` emits a script containing `_THOTH_COMPLETE=bash_source thoth`
- [x] [P16-PR3-TS05] Same for `zsh` and `fish`; `thoth completion zsh-bogus --json` exits 2 with `UNSUPPORTED_SHELL`
- [x] [P16-PR3-TS06] `tests/test_completion_install.py`: `thoth completion bash --install` writes to `~/.bashrc` (tmp-home fixture); rerun detects existing block and prompts before overwrite
- [x] [P16-PR3-TS07] Non-tty + no `--force` → install refuses with helpful error
- [x] [P16-PR3-T02] Confirm existing `click>=8.0` pin and Click 8.x lockfile; keep `fish` in the required shell set
- [x] [P16-PR3-T03] Create `src/thoth/completion/__init__.py`, `script.py` (init script generation), `sources.py` (completer data functions: `operation_ids`, `mode_names`, `config_keys`, `provider_names`)
- [x] [P16-PR3-T04] Add `src/thoth/cli_subcommands/completion.py` with `@click.command("completion")` + string `shell` arg validated in the command body against `{bash,zsh,fish}` + `--install/--force/--json` flags. Do not use a raw `click.Choice`, because invalid-shell errors must be emit-able as `UNSUPPORTED_SHELL` JSON.
- [x] [P16-PR3-T05] Wire `shell_complete=` callbacks into existing subcommands: `resume OP_ID`, `status OP_ID`, `config get KEY`, `config set KEY`, `modes list --name NAME`

**Phase C — `--json` rollout (one task per command, B-deferred extraction each)**
- [x] [P16-PR3-TS08] `tests/test_json_envelopes.py`: parametrized over every data/action `--json` command (`init`, `status`, `list`, `providers list/models/check`, `config get/set/unset/list/path/edit`, `modes list`, `ask`, `resume`) — each emits a top-level object with `status` field, parses cleanly. `completion --json` error/install cases are covered in completion tests; `help` intentionally has no `--json`.
- [x] [P16-PR3-T06] `init --json` (requires `--non-interactive` per spec §8.2; emit `JSON_REQUIRES_NONINTERACTIVE` otherwise)
- [x] [P16-PR3-T07] `status OP_ID --json` (extract `get_status_data()` from `commands.show_status`)
- [x] [P16-PR3-T08] `list --json` (extract `get_list_data()` from `commands.list_operations`)
- [x] [P16-PR3-T09] `providers list/models/check --json` (extract `get_providers_*_data()` siblings)
- [x] [P16-PR3-T10] `config get/set/unset/list/path --json` (extract `get_config_*_data()` siblings)
- [x] [P16-PR3-T11] `config edit --json` (success envelope after editor closes; `EDITOR_FAILED` on non-zero editor exit)
- [x] [P16-PR3-T12] `modes list --json` (legacy `modes --json` was removed in PR2; migrate the P11 schema into the new envelope contract)
- [x] [P16-PR3-T13] `ask --json` and `resume --json` (research-path JSON: minimal envelope with `operation_id`, `status`, `result_path` — full streaming output stays human-readable)

**Phase D — CI lint rules**
- [x] [P16-PR3-T14] Add CI check: `! grep -rnE "as_json" src/thoth/commands.py src/thoth/config_cmd.py src/thoth/modes_cmd.py` (handlers must not branch on JSON flag)
- [x] [P16-PR3-T15] Add CI check: `JSON_COMMANDS` parametrize-list in `test_json_envelopes.py` is complete — every data/action `@click.command` in `cli_subcommands/` with a success-envelope `--json` path appears in the list. Exclude `help` and raw completion-script success; assert `completion --json` error/install paths in completion tests.

**Phase E — Documentation + release**
- [x] [P16-PR3-T16] Update `planning/thoth.prd.v24.md:96` ("Added shell completion support") from aspirational to actually-shipped (spec §13 stale-PRD note)
- [x] [P16-PR3-T17] Document JSON envelope contract in `README.md` and a new `docs/json-output.md`
- [x] [P16-PR3-T18] Mark PRD F-70 and Plan M21-07 complete
- [x] [P16-PR3-T19] CHANGELOG entries (non-breaking — pure additions, but consolidate v3.0.0 narrative): `feat: shell completion (bash, zsh, fish)`, `feat: --json on all data/action admin commands`
- [x] [P16-PR3-T20] Verify release-please opens v3.0.0 PR after PR3 merges; merge → tag → publish

- [x] Regression Test Status

### Automated Verification
- `uv run pytest tests/test_json_output.py tests/test_completion.py tests/test_completion_install.py tests/test_json_envelopes.py -v` — all green
- `uv run pytest tests/` — full suite green
- `./thoth_test -r --skip-interactive -q` — full suite green
- `just check` — green (ruff + ty)
- CI lint rule: `! grep -rnE "as_json" src/thoth/commands.py src/thoth/config_cmd.py src/thoth/modes_cmd.py` exits 0
- `thoth status NONEXISTENT_ID --json | jq .status` returns `"error"`; `.error.code` returns `"OPERATION_NOT_FOUND"`

### Manual Verification
- `eval "$(thoth completion zsh)"` then `thoth resume <TAB>` shows live op-ids from `~/.thoth/operations/`
- `thoth completion bash --install` writes to `~/.bashrc`; rerun prompts before overwrite
- `thoth init --json --non-interactive` emits success envelope; `thoth init --json` (no flag) emits `JSON_REQUIRES_NONINTERACTIVE` exit 2
- `thoth providers list --json | jq '.data[].name'` returns provider names
- `thoth config edit --json` emits success envelope after vim closes

### Acceptance criteria for v3.0.0 release (cumulative across PR1+PR2+PR3, per spec §11)
- `thoth --help` shows two-section layout + epilog
- Every admin command is a real Click subcommand
- `thoth ask` works as canonical scripted form; `thoth resume OP_ID` is the only resume form
- `thoth --resume OP_ID` and `thoth providers -- --list` both exit 2 with migration hints
- `thoth completion bash|zsh|fish` ships working init scripts
- `thoth resume <TAB>`, `thoth status <TAB>`, `thoth config get <TAB>` complete with live data
- Every data/action admin command supports `--json` with valid envelope
- CHANGELOG documents v3.0.0 with breaking changes and migration paths

---

## [x] Project P16 PR1: Click-Native CLI Refactor — Subcommand Migration & Parity Gate (v2.15.0)
**Goal**: Migrate `thoth`'s imperative `cli.py` dispatch into Click subcommands (`init`, `status`, `list`, `providers`, `config`, `modes`, `help`) and lock the user-visible behavior with a parity gate before any further refactors.

**Out of Scope**
- Deep_research / quick / sonar mode dispatch (still imperative — handled in PR2)
- `--pick-model`, `-i`, `--resume` ergonomics (P14/P15 territory)
- Removing the `--mode` positional fallback (PR3)

### Design Notes
- Two-step migration: build Click subcommands alongside the old dispatch; once parity is proven, delete the dead imperative branch.
- Parity policy (T15): 8 byte-stable invocations + 7 structural tests. Byte-stable for outputs we trust to be unchanged; structural for outputs that intentionally changed (two-section --help layout) or where pre-refactor output was a Click bug (parent --help leaking into `init --help` / `list --help`).
- `_scrub_home` in conftest_p16 keeps baselines portable across users.
- `THOTH_TEST_MODE=1` env in `run_thoth` fixture isolates from user config.

### Tests & Tasks
- [x] [P16-TS01..08] Capture pre-refactor baselines (15 invocations) under `tests/baselines/*.json`
- [x] [P16-T01..04] Build subcommand modules under `src/thoth/cli_subcommands/{init,status,list,providers,config,modes,help}.py`
- [x] [P16-T05] Wire Click subgroups into `cli` group; preserve fallback dispatch for modes/research
- [x] [P16-T06] Migrate `thoth status` to Click with `OP_ID` required argument
- [x] [P16-T07] Migrate `thoth list` (with `--all`) to Click
- [x] [P16-T08] Migrate `thoth config` and `thoth providers` as Click subgroups with leaf commands
- [x] [P16-T09] Migrate `thoth modes` to Click
- [x] [P16-T10] Migrate `thoth help` as a thin alias that forwards to `<subcommand> --help`
- [x] [P16-T11] Build two-section `--help` layout (Run research / Manage thoth) + structural tests
- [x] [P16-T12] Type-check + lint cleanup on `help_cmd.py`
- [x] [P16-T13] Remove `ThothCommand`, dead `show_*_help`, `build_epilog`, `COMMAND_NAMES`
- [x] [P16-T14] Remove dead imperative dispatch block from `cli.py`
- [x] [P16-T15] Finalize parity gate: 8 byte-stable + 7 structural; restore exit-2 for `thoth config` no-args; recapture `status_no_args` baseline against Click natural exit-2 behavior; capture new `help_post_pr1.json` baseline

### Automated Verification
- `uv run pytest tests/test_p16_dispatch_parity.py tests/test_p16_thothgroup.py -v` — 40 passing
- `just check` — green (ruff + ty)
- `uv run pytest tests/` — **312 passed / 0 failed**
- `./thoth_test -r --skip-interactive` — **63 passed / 0 failed / 10 skipped** (the 10 skips are OpenAI/Perplexity provider tests that auto-skip when API keys are unset)

### Manual Verification
- `thoth --help` → two-section layout
- `thoth status` → exits 2 with Click's "Missing argument 'OP_ID'"
- `thoth config` → exits 2 with explicit op-required hint (parity restored)
- `thoth providers` → lists subcommands (Click natural; exit 2)
- `thoth help init` → forwards to `init --help` (exit 0)
- `thoth init --help` / `thoth list --help` → show subcommand help (no parent leak)

### Known Follow-ups (out of scope for PR1, picked up by PR2/PR3)
- Deep_research / quick / sonar mode dispatch (currently routed via `ThothGroup.invoke` mode-positional + bare-prompt fallback paths — works, but PR2 may consolidate)
- `--mode` positional fallback still exists (intentional per spec; surrounded by parity tests)
- `ctx.protected_args` Click 9.0 deprecation — currently suppressed via `warnings.catch_warnings` in `help.py:60-65`; revisit when Click 9 lands
- `thoth config help` was already broken pre-refactor (no `help` leaf in config Click subgroup); `show_config_help` retained for the internal `config_command(op="help")` API path

---

## [x] Project P15: P14 Bug Fixes — pick-model gating, spinner-progress conflict, prompt-file caps (v2.14.0)
**Goal**: Fix four post-merge defects found in P14: dual `rich.Live` displays during sync deep_research, `--pick-model` firing in non-research dispatch paths, unbounded `--prompt-file` reads, and asymmetric/hardcoded picker model list.

**Out of Scope**
- Reworking `--pick-model` to accept a model arg (current is_flag stays)
- Replacing thothspinner with another library
- Changing release versioning policy

### Design Notes
- **BUG-02 first** (smallest, no deps); **BUG-03** next (introduces early config-load pattern); **BUG-06** depends on early config-load; **BUG-01** last (biggest restructure).
- **BUG-01**: split `_execute_research` into submit-then-poll phases; the poll phase picks `Progress(...)` xor `run_with_spinner(...)` based on `should_show_spinner`. ThothSpinner kwargs: `spinner_style="npm_dots"`, `message_shimmer=True`, `timer_format="auto"`, `hint_text="Ctrl-C to background"`, hide progress component (no real pct), no auto-clear.
- **BUG-02**: move the `if pick_model:` block to the research dispatch arm; reject combos with `--resume`/`-i`/commands at the top.
- **BUG-03**: add `[execution].prompt_max_bytes = 1048576` default; one helper covers both stdin and file paths; document in `show_config_help()` and README.
- **BUG-06**: `immediate_models_for_provider(provider, config)` walks `config.data["modes"]` (merged), drops the openai-only hardcoded extras.

### Tests & Tasks
- [x] [P15-TS01] `tests/test_pick_model.py`: 4 negative cases — `--pick-model --resume X`, `--pick-model -i`, `--pick-model providers list`, `--pick-model` no args — assert exit != 0 and "only applies to research runs" in stderr
- [x] [P15-T01] BUG-02: move `if pick_model:` block in `cli.py` to before the research dispatch arm; add combo guard (`pick_model and (resume_id or interactive or args[0] in COMMAND_NAMES)` → `BadParameter`)
- [x] [P15-TS02] `tests/test_prompt_file_limit.py`: oversized stdin → BadParameter, oversized file → BadParameter, non-UTF-8 file → BadParameter, custom config limit honored
- [x] [P15-T02] BUG-03: add `prompt_max_bytes` to `ConfigSchema.get_defaults()["execution"]`; add `_read_prompt(path_or_dash, max_bytes)` helper; document in `show_config_help()` + `README.md`
- [x] [P15-TS03] `tests/test_picker_user_modes.py`: a user-defined mode with `model = "X"` appears in picker output; openai/perplexity/mock all use the same code path (no hardcoded extras)
- [x] [P15-T03] BUG-06: change `immediate_models_for_provider(provider, config)` signature; walk `config.data["modes"]`; drop openai hardcoded extras; thread config from `cli.py` callsite
- [x] [P15-TS04] `tests/test_progress_spinner.py`: assert `Progress` and `run_with_spinner` are mutually exclusive (mock both, assert XOR); existing should_show_spinner tests stay green
- [x] [P15-T04] BUG-01: split `_execute_research` submit/poll; poll-phase chooses `Progress` xor `run_with_spinner`; ThothSpinner constructor uses chosen kwargs; hide progress component
- [x] [P15-T05] BUG-07 verification: assert "Mode 'None' uses None" string is unreachable (covered by P15-TS01)
- [x] [P15-T06] CHANGELOG.md entry under Unreleased

### Automated Verification
- `uv run pytest tests/test_pick_model.py tests/test_prompt_file_limit.py tests/test_picker_user_modes.py tests/test_progress_spinner.py -v`
- `just check` (lint + typecheck)
- `./thoth_test -r --provider mock --skip-interactive -q`
- Final: full pre-commit gate before commit

### Manual Verification
- `thoth providers list --pick-model` → rejected with helpful message
- `thoth --pick-model -i` → rejected
- `thoth deep_research "X"` in TTY → spinner shows, no garbled output
- `thoth --prompt-file /dev/null deep_research` (empty) → "Prompt cannot be empty"
- Config knob: set `[execution] prompt_max_bytes = 100` → file >100 bytes rejected

---

## [x] Project P14: Thoth CLI Ergonomics v1 (v2.13.0)
**Goal**: Reduce first-time-user friction in the thoth CLI.

### Tests & Tasks
- [x] [P14-T01] format_config_context helper + tests
- [x] [P14-T02] APIKeyError surfaces config file path
- [x] [P14-T03] --input-file/--auto clearer help
- [x] [P14-T04] Workflow chain + worked examples in --help epilog
- [x] [P14-T05] thoth help auth + README authentication ordering pass
- [x] [P14-T06] providers list/models/check subcommands + deprecation shim
- [x] [P14-T07] thothspinner dependency
- [x] [P14-T08] Progress spinner module + gate
- [x] [P14-T09] Wire spinner into run.py polling
- [x] [P14-T10] SIGINT Resume-later hint
- [x] [P14-T11] --pick-model rejection on background modes
- [x] [P14-T12] --pick-model interactive picker for immediate modes

---

## [x] Project P13: P11 Follow-up — is_background_model overload + shared secrets + regression tests (v2.11.1)
**Goal**: Close the six non-blocking items carried over from P11 review before new feature work (P12) builds on them. Purely follow-up: one clarifying helper, two test-coverage gaps, one prose fix, one shared-module extraction, one regression test that would have caught a silent pre-P11 bug.

**Out of Scope**
- New user-facing features (that's P12)
- Refactoring `is_background_mode` itself — we add an adjunct, not a replacement
- Extending masking rules (same `api_key` suffix contract)

### Design Notes
- **Helper shape**: keep `is_background_mode(mode_config)` as the dict-shaped contract. Add `is_background_model(model: str | None) -> bool` as the string-shaped primitive. `is_background_mode` delegates to `is_background_model` after the `async` short-circuit — one derivation rule, two ergonomic entry points.
- **Call-site updates**: the two `openai.py` callsites (which synthesize `{"model": self.model}` today) switch to `is_background_model(self.model)`. The `providers/__init__.py` callsite keeps `is_background_mode(provider_config)` because it passes a real config dict that could carry `async`.
- **Shared secrets module**: extract `_mask_secret`, `_is_secret_key`, `_mask_tree` to `src/thoth/_secrets.py` (leading underscore — internal). Both `config_cmd.py` and `modes_cmd.py` import from there. If P12 ships first and does the extraction, this task becomes a no-op; if P13 ships first, P12-T05 drops.
- **Regression test**: `thoth config list --json` was broken before P11 (click ate `--json`). P11's `ignore_unknown_options=True` fix repaired it incidentally but there's no subprocess test guarding it. Add one.
- **Docstring prose**: `src/thoth/providers/__init__.py` lines 6 and 79 still say "deep-research background mode" as if it were a code mechanism — update to name `is_background_mode` so a reader scanning the header finds the actual implementation.

### Tests & Tasks
- [x] [P13-TS01] Tests for `is_background_model(model)`: `None`, empty string, `"o3"`, `"o3-deep-research"`, `"o4-mini-deep-research"`, case-sensitivity (`"o3-Deep-Research"` → False), non-bool `async` values via `is_background_mode` (`{"async": 1}` → True, `{"async": "yes"}` → True) — closes P11 review Minor gaps M2/M3
- [x] [P13-T01] Added `is_background_model(model: str | None) -> bool` in `src/thoth/config.py`; `is_background_mode` now delegates (commit `89498ef`)
- [x] [P13-T02] Switched `providers/openai.py:175,182` from `is_background_mode({"model": self.model})` to `is_background_model(self.model)` — synthetic-dict abstraction leak gone (commit `dfb86b9`)
- [x] [P13-TS02] Unit tests for `create_provider("openai", ...)` asserting `provider_config["background"]=True` on deep-research and `False` on plain `o3` (commit `12a43e9`)
- [x] [P13-T03] Docstrings in `src/thoth/providers/__init__.py` (lines 6, 79) now reference `is_background_mode` by name (commit `01b9d11`)
- [x] [P13-TS03] 13 tests in `tests/test_secrets.py` verify `_mask_secret`, `_is_secret_key`, `_mask_tree` semantics (last-4 retention, `${VAR}` passthrough, dotted-path suffix, list + dict recursion)
- [x] [P13-T04] Created `src/thoth/_secrets.py`; `config_cmd.py` and `modes_cmd.py` now import shared helpers. Duplicates deleted. `config_cmd.py` uses `from thoth._secrets import _mask_tree as _mask_in_tree` alias to preserve call-site names (commit `5d2cee2`)
- [x] [P13-TS04] Subprocess regression test `test_thoth_config_list_json_subprocess` in `tests/test_config_cmd.py` (commit `9813a59`); also repaired the `thoth` uv-script metadata (`tomlkit>=0.13`) that was blocking the test
- [x] [P13-TS05] Regression: `just check` clean, 200 pytest passed / 1 skipped, `./thoth_test -r --skip-interactive` 63 passed / 1 skipped / 0 failed
- [x] [P13-T05] See note in P12 below — P12-T05 is obsoleted by P13-T04
- [x] Regression Test Status — all green

### Automated Verification
- `just check` passes (ruff + ty)
- `uv run pytest tests/` passes (169 → ~175 with new tests)
- `./thoth_test -r` passes
- `grep -rn '"deep-research"' src/thoth/providers/` returns zero code-logic matches (same as post-P11 baseline)
- `grep -n "_mask_secret\|_is_secret_key\|_mask_tree" src/thoth/config_cmd.py src/thoth/modes_cmd.py` shows only imports from `_secrets`, no duplicate definitions

### Manual Verification
- `./thoth config list --json | jq keys` produces valid JSON (was broken before P11, not currently test-guarded)
- `./thoth modes --json` still masks `api_key` in any `[modes.*]` table after the secrets extraction

---

## [ ] Project P12: CLI Mode Editing — `thoth modes set` / `thoth modes add` (v2.12.0)
**Goal**: Let users create, edit, and delete mode definitions from the CLI instead of hand-editing TOML. Parallel to `thoth config set/unset` but scoped to `[modes.*]` tables. Uses the tomlkit round-trip already in `config_cmd.py` so comments and formatting survive.

**Out of Scope**
- GUI/TUI editor (keep it CLI-only)
- Validating `system_prompt` content (any string accepted)
- Adding new mode-level fields beyond what `ModeInfo` already surfaces (provider, providers, model, async, system_prompt, description, temperature, parallel, auto_input, previous, next)
- Schema migration for `[modes.*]` (same version as P11)

### Design Notes
- Subcommand shape mirrors `config`: `thoth modes set <name> <key> <value>`, `thoth modes unset <name> [<key>]`, `thoth modes add <name> --model M [--provider P] [--description D]`, `thoth modes rename <old> <new>`, `thoth modes copy <src> <dst>`.
- `--project` flag writes to `./thoth.toml` instead of user config, matching `config set --project`.
- Type coercion reuses `_parse_value` pattern from `config_cmd.py` (bool/int/float/string).
- Protected keys: cannot `unset` a builtin mode's own entry (but CAN override its keys via a user-side `[modes.<builtin>]` table — that's already how overrides work).
- Secrets: same masking rules; `--string` flag forces string parsing so `sk-...` keys aren't coerced to numbers.
- After each write, print the effective `ModeInfo` so the user sees what changed end-to-end (reuses `list_all_modes` + `_render_detail`).
- Extract the shared secret-masking helpers (`_mask_secret`, `_is_secret_key`, `_mask_tree`) from `config_cmd.py` + `modes_cmd.py` into `thoth/_secrets.py` as part of this work — third caller incoming makes the duplication no longer tolerable.

### Tests & Tasks
- [ ] [P12-TS01] Tests for `thoth modes add <name> --model M`: creates `[modes.<name>]` in user TOML with model + provider=openai default; appears in `thoth modes --source user` afterward
- [ ] [P12-T01] Implement `_op_add` in `modes_cmd.py` with tomlkit round-trip
- [ ] [P12-TS02] Tests for `thoth modes set <name> <key> <value>`: updates existing user mode; creating a key on a builtin-only name implicitly creates an overriding `[modes.<name>]` table (source becomes "overridden"); --project writes to project TOML
- [ ] [P12-T02] Implement `_op_set` with type coercion + `--string` + `--project`
- [ ] [P12-TS03] Tests for `thoth modes unset <name> <key>`: removes a single key (prunes empty table); `thoth modes unset <name>` (no key) removes entire user table; refuses to touch `BUILTIN_MODES` (but allows dropping a user override)
- [ ] [P12-T03] Implement `_op_unset` with empty-table pruning (mirrors `config_cmd._unset_in_doc`)
- [ ] [P12-TS04] Tests for `thoth modes rename <old> <new>` (user modes only) and `thoth modes copy <src> <dst>` (copies from any mode — builtin or user — into a new user mode)
- [ ] [P12-T04] Implement `_op_rename` and `_op_copy`
- [~] [P12-TS05] Obsoleted by P13-TS03 — shared-secrets tests already exist in `tests/test_secrets.py`
- [~] [P12-T05] Obsoleted by P13-T04 — `src/thoth/_secrets.py` already extracted; `config_cmd.py` and `modes_cmd.py` already route through it
- [ ] [P12-TS06] Subprocess tests: `thoth modes add / set / unset / rename / copy` through the click CLI (now that `ignore_unknown_options=True` from P11 makes flags work)
- [ ] [P12-T06] Wire new ops into `modes_command` dispatch (`list | add | set | unset | rename | copy`)
- [ ] [P12-T07] Update `show_modes_help()` in `help.py` with the new ops + examples; update `thoth help modes` epilog
- [ ] [P12-TS07] Regression: full `uv run pytest tests/` + `./thoth_test -r` still green; existing `thoth modes list/--json/--name/--source` unchanged
- [ ] Regression Test Status

### Deliverable
```bash
$ thoth modes add my_brief --model gpt-4o-mini --description "terse daily brief"
Added mode 'my_brief' (source=user, kind=immediate, model=gpt-4o-mini)

$ thoth modes set my_brief temperature 0.2
Updated my_brief.temperature = 0.2

$ thoth modes copy deep_research custom_research
Copied builtin 'deep_research' to user mode 'custom_research'

$ thoth modes unset my_brief temperature
Removed my_brief.temperature

$ thoth modes unset my_brief
Removed user mode 'my_brief'
```

### Automated Verification
- `just check` passes
- `uv run pytest tests/` passes
- `./thoth_test -r` passes
- `thoth modes add` / `set` / `unset` round-trip through user TOML without losing comments (tomlkit fidelity)

### Manual Verification
- Adding a mode then running `thoth modes` shows it with `source=user`
- Overriding a builtin then running `thoth modes --name <mode>` shows `source=overridden` with the diff
- `--project` flag writes to `./thoth.toml` not `~/.thoth/config.toml`

---

## [x] Project P11: `thoth modes` Discovery Command (v2.11.0)
**Goal**: Give users one authoritative place to see all research modes — built-in and user-defined — with provider, model, kind (immediate vs background), and origin source, so they don't need to read `config.py` or guess from descriptions. Also consolidates mode enumeration through a single helper, removing drift across `cli.py`, `help.py`, and `interactive.py`.

**Out of Scope**
- Editing/adding modes from the CLI (use `thoth config set` / `edit` as today)
- Changing how modes actually execute at runtime (other than the `is_background_mode` helper refactor)
- Reworking the existing `thoth --help` mode listing beyond a one-line pointer + teaser

### Design Notes
- Single derivation point `is_background_mode(mode_config) -> bool` in `src/thoth/config.py`: `bool(mode_config.get("async"))` if set, else `"deep-research" in mode_config.get("model", "")`. Replace ad-hoc check at `src/thoth/providers/openai.py:175,182`.
- Source classification: `builtin` (in `BUILTIN_MODES`, not in TOML), `user` (TOML only), `overridden` (both).
- Normalize `providers` (plural) vs `provider` (singular) into a single `providers: list[str]` on `ModeInfo`.
- Default sort order: `source` → `kind` → `provider` → `model` → `name` (stable/deterministic).
- Secret masking + TTY auto-detect parity with `thoth config` (reuse `_mask_in_tree` / `_is_secret_key`). No `--no-color` flag — auto-detect instead.
- JSON output includes `schema_version: "1"`.
- Tolerate broken user modes: show row with `kind=unknown` + yellow warning, don't crash.
- `thinking` mode: change `model` from `o3-deep-research` to `o3` to match its "quick analysis" description and make it actually immediate.

### Tests & Tasks
- [x] [P11-TS00] Tests for `is_background_mode` helper: explicit `async: true`, explicit `async: false` overrides deep-research model, model contains `deep-research`, model without it, missing model key
- [x] [P11-T00] Implement `is_background_mode` in `src/thoth/config.py`; refactor `providers/openai.py:175,182` + `providers/__init__.py:111` to call it; change `BUILTIN_MODES["thinking"]["model"]` to `"o3"`
- [x] [P11-TS01] Tests for `list_all_modes(cm) -> list[ModeInfo]` returning `{name, source, provider(s), model, kind, description, overrides, schema_version}`. Cover: pure builtin, user-only mode, overridden mode, per-field override detection, `providers` (list) normalization, malformed mode → `kind=unknown` + warning collected
- [x] [P11-T01] Implement `list_all_modes` + `ModeInfo` in `src/thoth/modes_cmd.py`
- [x] [P11-TS02] CLI tests for `thoth modes`: default table + sort order, `--json` shape with `schema_version`, `--source builtin|user|overridden|all` filter, `--show-secrets` unmasks, default masks api_key inside a mode. Use test-isolation fixture (`isolated_thoth_home` + autouse `COLUMNS=200`) — does NOT read the real `~/.thoth/config.toml`
- [x] [P11-T02] Implement `modes_cmd.py` dispatch + Rich table renderer + JSON serializer + secret masking + per-call Console for dynamic width
- [x] [P11-TS05] Tests for `thoth modes --name <mode>` detail view: override diff, `--full` dumps entire `system_prompt`, unknown name returns exit 1
- [x] [P11-T03] Implement `--name` detail view with per-field override diff and `--full` flag
- [x] [P11-T04] Wire `modes` into `src/thoth/cli.py` dispatch (parallel to `config`); add `show_modes_help()` in `src/thoth/help.py`; replace per-mode epilog loop with names-only teaser + pointer; include JSON schema snippet in help
- [x] [P11-TS03] Test that `thoth help modes` prints the new help block and that help epilog still lists mode names
- [x] [P11-TS04] Regression test asserting `BUILTIN_MODES.items()` is no longer iterated in `interactive.py` / `help.py`
- [x] [P11-T05] Route `interactive.py` (`set_mode`, `_show_mode_selection`) mode listing through `list_all_modes()`; validation branches still use `BUILTIN_MODES` (intentional — interactive user-mode support out of scope)
- [x] [P11-T06] Added `ignore_unknown_options=True` in root click context so `--json` / `--name` / `--source` flags pass through to subcommands; updated thoth_test EXIT-02 to assert exit 2 via `thoth modes bogus_op` (the `thoth --invalid-flag` case became "prompt" per new click behavior)
- [x] Regression Test Status — full suite 169/169 pytest + 63/64 thoth_test (1 skipped, 0 failed) green

### Deliverable
```bash
$ thoth modes
 Mode            Source       Provider   Model                   Kind        Description
 default         builtin      openai     o3                      immediate   Default mode — passes prompt directly…
 clarification   builtin      openai     o3                      immediate   Clarifying takes the prompt…
 thinking        builtin      openai     o3                      immediate   Quick thinking and analysis mode…
 mini_research   builtin      openai     o4-mini-deep-research   background  Fast, lightweight research mode…
 exploration     builtin      openai     o3-deep-research        background  Exploration looks at the topic…
 my_brief        user         openai     gpt-4o-mini             immediate   (user-defined)
 deep_research   overridden   openai     o3-deep-research        background  Deep research mode using OpenAI…

$ thoth modes --name deep_research
Mode: deep_research           Source: overridden
Providers: openai             Model: o3-deep-research        Kind: background
Overrides (builtin → effective):
  parallel:       true  →  false
  system_prompt:  (312 chars)  →  (198 chars)   [use --full to see]

$ thoth modes --json | jq '.[] | select(.kind == "background") | .name'
```

### Automated Verification
- `make env-check` passes
- `just check` passes (ruff + ty)
- `./thoth_test -r` passes
- `just test-lint` and `just test-typecheck` pass
- `thoth modes --json` validates against documented schema (`schema_version: "1"`)
- API key values inside a `[modes.*]` table are masked by default

### Manual Verification
- `thoth modes` prints table sorted by source, kind, provider, model
- `thoth modes --name thinking` reflects the `o3` fix and shows `Kind: immediate`
- Running a background mode still routes to OpenAI background responses (sanity check: `thoth deep_research "hello" --async`)
- `thoth --help` still shows mode names (teaser) and points at `thoth modes` for details

---

## [x] Project P10: Config Subcommand + XDG Layout (v2.10.0)
**Goal**: Add `thoth config` subcommand (get/set/unset/list/path/edit/help) and migrate all user-writable paths to XDG Base Directory Spec. No legacy-path migration.

### Tests & Tasks
- [x] [P10-T01] Add tomlkit dependency
- [x] [P10-T02] XDG path helpers in src/thoth/paths.py with TDD
- [x] [P10-T03] Migrate all platformdirs callsites to paths.py
- [x] [P10-T04] config_cmd.py scaffold + get op
- [x] [P10-T05] set op with tomlkit round-trip (comment-preserving)
- [x] [P10-T06] unset op with empty-table pruning
- [x] [P10-T07] list + path ops
- [x] [P10-T08] Secrets masking on get and list (api_key, --show-secrets opt-in)
- [x] [P10-T09] edit + help ops
- [x] [P10-T10] Wire config into CLI dispatch and help system
- [x] [P10-T11] Final verification (lint, typecheck, full pytest suite, thoth_test -r)

### Automated Verification
- `just check` passes
- `uv run pytest tests/` passes
- `./thoth_test -r` passes
- API key values masked by default in `thoth config get/list` output

---

## [x] Project P09: Decompose __main__.py + AppContext DI + Provider Registry (v2.9.0)
**Goal**: Split the ~5000-line src/thoth/__main__.py into a package of focused modules (errors, config, models, providers/*, checkpoint, output, signals, run, cli, interactive, help, commands), replace module-level singletons with an injected `AppContext` dataclass, and collapse the two provider factories (`ProviderRegistry.create` + `create_provider`) into a single `PROVIDERS` dict lookup. Behavior-preserving physical relocation; no new features.

**Out of Scope**
- Renaming any public symbols (OpenAIProvider, OperationStatus, _execute_research, etc. keep their names)
- Changing the public import path used by tests/thoth_test (both continue to import from `thoth.__main__`)
- Changing click CLI commands/options/help text
- CHANGELOG/docs rewrites (track under P08-T12)
- Further decomposing InteractiveSession (~800 lines) — flagged for follow-up
- Decorator-based provider auto-registration — literal dict only

### Tests & Tasks
Phase 1 — Foundations (pure extraction, no DI yet)
- [x] [P09-TS01] tests/test_imports.py: `from thoth.__main__ import X` still works for all 40+ symbols currently used by tests/thoth_test
- [x] [P09-T01] Extract src/thoth/errors.py (ThothError, APIKeyError, APIQuotaError, ProviderError, DiskSpaceError, handle_error)
- [x] [P09-T02] Extract src/thoth/utils.py (generate_operation_id, sanitize_slug, mask_api_key, check_disk_space, _is_placeholder)
- [x] [P09-T03] Extract src/thoth/models.py (InputMode, OperationStatus, InteractiveInitialSettings, ModelCache)
- [x] [P09-T04] Extract src/thoth/config.py (ConfigSchema, ConfigManager, get_config, _config_path, THOTH_VERSION, CONFIG_VERSION, BUILTIN_MODES)
- [x] [P09-T05] Add re-export shim to src/thoth/__main__.py for extracted symbols; run full test + thoth_test suite GREEN

Phase 2 — Signals + I/O managers
- [x] [P09-TS02] tests/test_sigint_handler.py still green after signals moved to thoth.signals
- [x] [P09-T06] Extract src/thoth/signals.py (_interrupt_event, _last_interrupt_at, _INTERRUPT_FORCE_EXIT_WINDOW_S, _raise_if_interrupted, handle_sigint)
- [x] [P09-T07] Extract src/thoth/checkpoint.py (CheckpointManager)
- [x] [P09-T08] Extract src/thoth/output.py (OutputManager; atomic-write logic preserved verbatim)
- [x] [P09-T09] Update __main__.py shim; full suite GREEN

Phase 3 — Providers package + R02 registry
- [x] [P09-TS03] tests/test_openai_errors.py still green after _map_openai_error moves to thoth.providers.openai
- [x] [P09-TS04] tests/test_api_key_resolver.py still green after resolve_api_key moves to thoth.providers
- [x] [P09-TS05] tests/test_vcr_openai.py still green (VCR cassette replays)
- [x] [P09-TS06] tests/test_provider_registry.py (NEW): create_provider("mock") returns MockProvider; create_provider("bogus") raises ValueError; PROVIDERS dict contains {openai, perplexity, mock}
- [x] [P09-T10] Create src/thoth/providers/base.py (ResearchProvider Protocol)
- [x] [P09-T11] Extract src/thoth/providers/mock.py (MockProvider)
- [x] [P09-T12] Extract src/thoth/providers/openai.py (OpenAIProvider, _map_openai_error)
- [x] [P09-T13] Extract src/thoth/providers/perplexity.py (PerplexityProvider)
- [x] [P09-T14] Create src/thoth/providers/__init__.py with PROVIDERS dict, PROVIDER_ENV_VARS, resolve_api_key, create_provider
- [x] [P09-T15] Delete ProviderRegistry class — only caller was the old create_provider itself
- [x] [P09-T16] Update __main__.py shim; full suite GREEN

Phase 4 — Run loop + commands + help + CLI + interactive
- [x] [P09-TS07] thoth_test (black-box) full run still matches P06 baseline + P08 additions
- [x] [P09-T17] Extract src/thoth/run.py (find_latest_outputs, get_estimated_duration, run_research, _run_polling_loop, _execute_research, resume_operation)
- [x] [P09-T18] Extract src/thoth/commands.py (CommandHandler, status_command, list_command, show_status, list_operations, providers_command)
- [x] [P09-T19] Extract src/thoth/help.py (ThothCommand, build_epilog, show_*_help)
- [x] [P09-T20] Extract src/thoth/interactive.py (SlashCommandRegistry, SlashCommandCompleter, ClarificationSession, InteractiveSession, enter_interactive_mode)
- [x] [P09-T21] Extract src/thoth/cli.py (click cli(), main())
- [x] [P09-T22] Reduce __main__.py to the re-export shim + `if __name__ == "__main__": main()`
- [x] [P09-T23] Verify `thoth = "thoth.__main__:main"` entry point still executes `thoth --help` successfully

Phase 5 — R12 AppContext wiring
- [x] [P09-TS08] tests/test_app_context.py (NEW): AppContext instance constructible; defaults sane; verbose propagates
- [x] [P09-T24] Create src/thoth/context.py with AppContext dataclass
- [x] [P09-T25] Thread `ctx: AppContext` parameter through run_research → _execute_research → _run_polling_loop signatures
- [x] [P09-T26] Replace reads of module-level `console` with `ctx.console` inside run/commands/interactive modules
- [x] [P09-T27] Replace reads of `_current_checkpoint_manager` / `_current_operation` with `ctx.checkpoint_manager` / `ctx.current_operation`
- [x] [P09-T28] In cli.main(), construct AppContext once and pass to all async entry points
- [x] [P09-T29] Keep signals module-globals (`_interrupt_event` etc.) aliased to `ctx.interrupt_event` for test back-compat
- [x] [P09-T30] Full suite GREEN

Phase 6 — Cleanup
- [x] [P09-T31] Remove unused imports from each new module (ruff)
- [x] [P09-T32] Ensure `just check` passes (ruff + ty) on entire src/thoth/ tree
- [x] [P09-T33] Ensure `just test-fix && just test-lint && just test-typecheck` all pass
- [x] [P09-T34] Update PROJECTS.md task states

### Regression Test Status
- [x] tests/ full pytest suite: 55 tests green (new test_imports, test_provider_registry, test_app_context added)
- [x] thoth_test full run: 115 passed / 11 skipped / 0 failed — no regressions
- [x] `thoth --help` exit 0
- [x] Manual smoke: `MOCK_API_KEY=test uv run thoth --provider mock "hello phase5"` completes end-to-end

---

## [-] Project P08: Typed Exceptions, Unified API Key Resolution, Drop Legacy Config Shim (v2.8.0)
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

---

## [x] Project P06: Hybrid Transient/Permanent Error Handling with Resumable Recovery (v2.7.0)
**Goal**: Classify provider errors as transient vs permanent, retry transient ones in-place with bounded backoff, and make recoverable failures (and Ctrl-C) resumable via `thoth --resume <id>` by reconnecting to persisted job IDs.

**Out of Scope**
- Checkpoint schema migration (backward-compat handled via `setdefault("failure_type", None)`)
- Perplexity / Gemini providers (still not implemented)
- Decorrelated-jitter backoff (simple exponential backoff is sufficient)

### Tests & Tasks
- [x] [P06-T01] Extend MockProvider with THOTH_MOCK_BEHAVIOR env (flake:N, permanent)
- [x] [P06-T02] Add `OperationStatus.failure_type` + checkpoint serialization
- [x] [P06-T03] Allow failed → running state transition so resume can re-enter
- [x] [P06-T04] Classify errors in `OpenAIProvider.check_status` (transient vs permanent)
- [x] [P06-T05] Add `max_transient_errors` config default
- [x] [P06-T06] Extract `_run_polling_loop` helper shared by run and resume
- [x] [P06-T07] Add retry loop + exponential backoff for transient errors
- [x] [P06-T08] Add `OpenAIProvider.reconnect` + `MockProvider.reconnect`
- [x] [P06-T09] Implement `resume_operation` to rebuild providers and re-enter poll loop
- [x] [P06-T10] Surface "Resume with: thoth --resume <id>" hint on recoverable failure and SIGINT
- [x] [P06-TS01] TR-01: transient errors below threshold retried and job completes
- [x] [P06-TS02] TR-02: transient errors above threshold fail recoverable with resume hint
- [x] [P06-TS03] TR-03: permanent error fails immediately with no resume hint
- [x] [P06-TS04] RES-01: resume recoverable failure reattaches and completes
- [x] [P06-TS05] RES-02: resume refuses permanent failure with exit code 7
- [x] [P06-TS06] RES-03: resume of already-completed operation is a no-op

### Automated Verification
- `make env-check` passes
- `just lint` / `just typecheck` pass
- `just test-lint` / `just test-typecheck` pass
- `./thoth_test -r` → 124 passed, 1 skipped, 0 failed

### Regression Test Status
- [x] OAI-BG-01..08 updated for new `permanent_error` / `transient_error` return values
- [x] Existing BUG-03 jitter/poll-interval fixture tests still pass (share module globals)
- [x] P07 async-mode tests still pass (async path now actually submits to providers)

---

## [x] Project P05: VCR Cassette Replay Tests (v2.6.0)
**Goal**: Add pytest-based VCR cassette replay tests that exercise OpenAIProvider against recorded API traffic, using Option B (separate pytest test file) from thoth_vcr.md.

**Out of Scope**
- Gemini/Perplexity cassettes (blocked on deepresearch_replay P03/P04)
- Integration into thoth_test runner (Option A rejected)

### Tests & Tasks
- [x] [P05-T01] Add pytest and vcrpy to dev dependencies
- [x] [P05-T02] Create tests/conftest.py with shared VCR configuration
- [x] [P05-TS01] VCR-OAI-SUBMIT: submit() returns response ID from cassette
- [x] [P05-TS02] VCR-OAI-SUBMIT: submit() returns exact cassette ID
- [x] [P05-TS03] VCR-OAI-SUBMIT: submit() stores job info with background=True
- [x] [P05-TS04] VCR-OAI-POLL: first check_status() returns queued/in_progress
- [x] [P05-TS05] VCR-OAI-POLL: polling reaches completed status
- [x] [P05-TS06] VCR-OAI-RESULT: get_result() returns substantial text
- [x] [P05-TS07] VCR-OAI-RESULT: get_result() contains domain-relevant content
- [x] [P05-T03] Add test-vcr justfile recipe and wire into just all
- [x] [P05-T04] Update PROJECTS.md

### Automated Verification
- `make check` passes
- `just test-vcr` → 7/7 pass
- `just all` completes without errors

### Regression Test Status
- [x] All existing thoth_test tests still pass
- [x] VCR tests run in `record_mode="none"` — no live API calls

---

## [x] Project P03: Fix BUG-03 OpenAI Poll Interval Scheduling (v2.5.1)
**Goal**: Make the background polling loop respect the configured poll cadence, including bounded jitter and sub-second intervals, while keeping the progress countdown aligned with the next real network poll.

**Out of Scope**
- BUG-02 (citation parsing), GAP-01 through GAP-05

### Tests & Tasks
- [x] [P03-TS01] Add virtual-time fixture tests for jittered and sub-second poll intervals
- [x] [P03-T01] Normalize poll interval math so jitter never truncates a 2s cadence into a 1s poll
- [x] [P03-T02] Schedule polling with absolute deadlines instead of a fixed 1s sleep cap
- [x] [P03-T03] Keep the progress countdown aligned with the next scheduled poll
- [x] [P03-TS02] Keep a mock-provider CLI regression for the end-to-end fixed polling loop
- [x] [P03-T04] Update OPENAI-BUGS.md and PROJECTS.md

### Automated Verification
- `make check` passes
- `./thoth_test -r -t BUG03 --skip-interactive` → 3/3 pass
- `./thoth_test -r -t OAI-BG --skip-interactive` → 14/14 pass

### Regression Test Status
- [x] BUG03-01 verifies -10% jitter still polls at 1.8s, not 1.0s
- [x] BUG03-02 verifies a 0.25s poll interval is honored exactly
- [x] BUG03-03 verifies the CLI still completes a mock-provider research run end to end

---

## [x] Project P02: Fix BUG-01 OpenAI Background Status Handling (v2.5.0)
**Goal**: Correctly handle all documented OpenAI Responses API background lifecycle states (`incomplete`, `cancelled`, `queued`, no-status-attr, stale-cache) so the CLI never silently misreports terminal failure states as success.

**Out of Scope**
- BUG-02 (citation parsing), GAP-01 through GAP-05

### Tests & Tasks
- [x] [P02-T01] Add `"fixture"` test_type dispatch + helpers to `thoth_test`
- [x] [P02-TS01] Add OAI-BG-01–08 fixture tests for `check_status()` (queued, failed, incomplete, cancelled, no-status-attr, stale-cache, good-cache, in_progress regression)
- [x] [P02-T02] Fix `check_status()` in `OpenAIProvider` — explicit branches for all 6 API statuses, fixed no-status-attr and stale-cache paths
- [x] [P02-TS02] Add OAI-BG-09–14 polling loop fixture tests (queued no premature exit, failed/cancelled/error propagate, not_found/unknown normalize to error)
- [x] [P02-T03] Fix polling loop in `_execute_research()` — queued keeps polling, terminal failures propagate
- [x] [P02-T04] Update OPENAI-BUGS.md (BUG-01 status → Fixed) and PROJECTS.md

### Automated Verification
- `make check` passes
- `./thoth_test -r -t OAI-BG --skip-interactive` → 14/14 pass
- `./thoth_test -r --provider mock --skip-interactive` → 67 passed, 0 failed

### Regression Test Status
- [x] All 14 OAI-BG fixture tests pass

---

## [x] Project P04: GAP-01 — max_tool_calls safeguard and tool-selection config (v2.6.0)
**Goal**: Expose `max_tool_calls` and `code_interpreter` as optional OpenAI provider config knobs so users can bound cost/latency and disable the code interpreter for prompt types that don't need it. Values must reach the Responses API request payload.

**Out of Scope**
- GAP-02 (file_search / MCP tools), GAP-03 (model aliases), GAP-04 (SDK floor), GAP-05 (fixture gaps)

### Tests & Tasks
- [x] [P04-TS01] Fixture test: `max_tool_calls` set in provider config → value present in request payload
- [x] [P04-TS02] Fixture test: `code_interpreter = false` in provider config → `code_interpreter` absent from tools array
- [x] [P04-TS03] Fixture test: no config keys → request has no `max_tool_calls` key and `code_interpreter` is included by default
- [x] [P04-T01] Read `max_tool_calls` from `self.config` in `OpenAIProvider.submit()` and conditionally add to `request_params`
- [x] [P04-T02] Read `code_interpreter` bool (default `True`) from `self.config` and conditionally include the tool in `tools` list
- [x] [P04-T03] Update OPENAI-BUGS.md (GAP-01 status → Fixed) and PROJECTS.md

### Automated Verification
- `make check` passes
- `./thoth_test -r -t GAP01 --skip-interactive` → 3/3 pass
- `./thoth_test -r --provider mock --skip-interactive` → no regressions

### Regression Test Status
- [x] GAP01-01 verifies max_tool_calls reaches the request payload
- [x] GAP01-02 verifies code_interpreter=False removes the tool
- [x] GAP01-03 verifies default behavior (no max_tool_calls key, code_interpreter included)

---

## [ ] Project P01: Developer Tooling & Automation (v2.6.0)
**Goal**: Add automated dependency updates, changelog generation, version bumping, GitHub contribution templates, snapshot test tooling, security linting, and devcontainer support.

### Tests & Tasks
- [ ] [P01-TS01] Verify `snapshot_report.html` does not appear in `git status` after test run
- [x] [P01-T01] Add `snapshot_report.html` to `.gitignore`
- [ ] [P01-TS02] Verify `make update-snapshots` runs without error
- [x] [P01-T02] Add `update-snapshots` Makefile target
- [ ] [P01-TS03] Validate `.github/dependabot.yml` with `uvx yamllint`
- [x] [P01-T03] Create `.github/dependabot.yml`
- [ ] [P01-TS04] Verify `uvx bandit -r src/thoth/ -ll -q` exits 0
- [x] [P01-T04] Add bandit hook to `lefthook.yml`
- [x] [P01-T05] Create `.github/PULL_REQUEST_TEMPLATE.md`
- [x] [P01-T06] Create `.github/ISSUE_TEMPLATE/bug_report.yml`
- [x] [P01-T07] Create `.github/ISSUE_TEMPLATE/feature_request.yml`
- [ ] [P01-TS05] Verify `make bump TYPE=patch` updates version in `pyproject.toml`
- [x] [P01-T08] Add `[tool.bumpversion]` to `pyproject.toml`
- [x] [P01-T09] Add `bump` Makefile target
- [ ] [P01-TS06] Verify `make changelog` produces valid CHANGELOG.md output
- [x] [P01-T10] Create `cliff.toml`
- [x] [P01-T11] Add `changelog` and `release` Makefile targets
- [x] [P01-T12] Create `.devcontainer/devcontainer.json`

### Deliverable
```bash
make bump TYPE=patch       # bumps version in pyproject.toml, commits, tags
make changelog             # regenerates CHANGELOG.md from git history
make release TYPE=minor    # bump + changelog in one step
make update-snapshots      # regenerate pytest snapshots
```

### Automated Verification
- `make check` passes
- `uvx yamllint .github/dependabot.yml` exits 0
- `uvx bandit -r src/thoth/ -ll -q` exits 0
- `make bump TYPE=patch` increments version in pyproject.toml

### Manual Verification
- Open repo in GitHub Codespaces — devcontainer auto-configures environment
- Create a PR — GitHub shows the PR template checklist
- Open a new issue — GitHub shows structured bug/feature forms
