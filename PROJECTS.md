# Project Tracker Conventions

This file tracks planned, active, and completed Thoth work. New projects are added near the top in descending project-number order unless the user gives a specific ordering. Each project should keep test/design tasks (`TS`) ahead of implementation tasks (`T`) so work stays test-driven.

## Quick reference: status glyphs

| Glyph | Meaning                | Reach for…                    |
|-------|------------------------|-------------------------------|
| `[?]` | Idea                   | `project-refine` to scope     |
| `[ ]` | Scoped, not started    | start work; flip to `[~]`     |
| `[~]` | In progress            | continue; check next task     |
| `[x]` | Completed              | leave alone                   |
| `[-]` | Decided not to do      | leave alone                   |
| `[>]` | Proceeded to successor | follow the redirect           |

## Project Summary

Keep this summary list updated whenever a project is added, renamed, completed, dropped, or proceeded to a successor. The detailed project entry remains the source of truth; this summary is a quick navigation index.

- [x] **P21** — [Configuration Profile Resolution & Overlay](projects/P21-configuration-profile-resolution.md)
- [x] **P21b** — [Configuration Profile CRUD Commands (depends on P21)](projects/P21b-configuration-profile-crud.md)
- [x] **P21c** — [Config Filename Standardization (`thoth.config.toml` everywhere)](projects/P21c-config-filename-standardization.md)
- [x] **P22** — [OpenAI — Immediate (Synchronous) Calls — closed: validation passed, 4 minor findings routed to P20, refactor outcome (a) (no refactor)](projects/P22-openai-immediate-sync.md)
- [ ] **P23** — [Perplexity — Immediate (Synchronous) Calls](projects/P23-perplexity-immediate-sync.md)
- [ ] **P24** — [Gemini — Immediate (Synchronous) Calls](projects/P24-gemini-immediate-sync.md)
- [ ] **P25** — [Architecture Review & Cleanup — Immediate Providers](projects/P25-arch-review-immediate-providers.md)
- [ ] **P26** — [OpenAI — Background Deep Research](projects/P26-openai-background-deep-research.md)
- [ ] **P27** — [Perplexity — Background Deep Research](projects/P27-perplexity-background-deep-research.md)
- [ ] **P28** — [Gemini — Background Deep Research](projects/P28-gemini-background-deep-research.md)
- [ ] **P29** — [Architecture Review & Cleanup — Background Deep Research Providers](projects/P29-arch-review-background-deep-research.md)
- [ ] **P30** — [Claude Code Skills Support](projects/P30-claude-code-skills-support.md)
- [ ] **P31** — [Interactive Init Command](projects/P31-interactive-init-command.md)
- [ ] **P32** — [Interactive Prompt Refiner](projects/P32-interactive-prompt-refiner.md)
- [ ] **P33** — [Schema-Driven Config Defaults (typed source for `thoth init` and `ConfigSchema`)](projects/P33-schema-driven-config-defaults.md)
- [ ] P20 — Extended Real-API Workflow Coverage — Mirror Mock Contracts
- [x] P18 — Immediate vs Background — Explicit `kind`, Runtime Mismatch, Path Split, Streaming, Cancel
- [x] **P17** — [thoth-ergonomics-v1 Spec Round-Trip — Annotate Implementation Status](projects/P17-ergonomics-spec-round-trip.md)
- [x] **P16 PR2** — [Remove Legacy Shims, Add resume + ask Subcommands](projects/P16-PR2-remove-legacy-shims.md)
- [x] P16 PR3 — Automation Polish — `completion` subcommand + universal `--json`
- [x] **P16 PR1** — [Click-Native CLI Refactor — Subcommand Migration & Parity Gate](projects/P16-PR1-click-native-cli-refactor.md)
- [x] **P15** — [P14 Bug Fixes — pick-model gating, spinner-progress conflict, prompt-file caps](projects/P15-p14-bug-fixes.md)
- [x] **P14** — [Thoth CLI Ergonomics v1](projects/P14-thoth-cli-ergonomics-v1.md)
- [x] **P13** — [P11 Follow-up — is_background_model overload + shared secrets + regression tests](projects/P13-p11-followup-is-background-model.md)
- [ ] **P12** — [CLI Mode Editing — `thoth modes` mutations](projects/P12-cli-mode-editing.md)
- [x] **P11** — [`thoth modes` Discovery Command](projects/P11-thoth-modes-discovery.md)
- [x] **P10** — [Config Subcommand + XDG Layout](projects/P10-config-subcommand-xdg.md)
- [x] **P09** — [Decompose __main__.py + AppContext DI + Provider Registry](projects/P09-decompose-main-appcontext-di.md)
- [x] **P08** — [Typed Exceptions, Unified API Key Resolution, Drop Legacy Config Shim](projects/P08-typed-exceptions-api-key-resolution.md)
- [x] **P06** — [Hybrid Transient/Permanent Error Handling with Resumable Recovery](projects/P06-hybrid-error-handling-resumable.md)
- [x] **P05** — [VCR Cassette Replay Tests](projects/P05-vcr-cassette-replay-tests.md)
- [x] **P03** — [Fix BUG-03 OpenAI Poll Interval Scheduling](projects/P03-bug-03-openai-poll-interval.md)
- [x] **P02** — [Fix BUG-01 OpenAI Background Status Handling](projects/P02-bug-01-openai-background-status.md)
- [x] **P04** — [GAP-01 — max_tool_calls safeguard and tool-selection config](projects/P04-gap-01-max-tool-calls.md)
- [x] **P01** — [Developer Tooling & Automation](projects/P01-developer-tooling.md)

## Project References

Every project that has supporting material must list those references near the beginning of its project entry, before scope and tasks. References can include Superpowers specs/plans, planning docs, research docs, audits, external documentation, or any other source document used to define the work.

Use this shape:

```markdown
**References**
- **Spec:** `docs/superpowers/specs/...`
- **Plan:** `docs/superpowers/plans/...`
- **Research:** `research/...`
- **Audit:** `planning/...`
- **External:** https://...
```

Existing projects may use older labels such as `**Primary spec**`, `**Plan**`, or `**Research basis**`; when editing those entries, prefer normalizing them to the `**References**` block.

## Task ID Key

- `P##` — Project number, for example `P21`
- `P##-TS##` — Test/design task for that project
- `P##-T##` — Implementation, documentation, or verification task for that project
- Suffix letters such as `P21-T09a` — inserted follow-up task that preserves existing numbering

## Usage Rules

- Keep each project entry self-contained: goal, references, scope, tasks, and verification.
- Planning tasks may be checked when the plan/spec exists; implementation tasks stay unchecked until the code or docs they describe have actually landed.
- Mark checkboxes as work lands.
- When adding a new project, preserve the order requested by the user, then adapt numbering to the current file.

---

## [~] Project P20: Live-API Workflow Regression Suite (weekly)

**References**
- **Trunk:** [PROJECTS.md](#) (this file)
- **Plan:** [projects/P20-live-api-workflow.md](projects/P20-live-api-workflow.md) — implementation plan (TDD task-by-task)
- **Depends on:** P18 (immediate-vs-background path split, `--out`/`--append`, `provider.stream()`, `provider.cancel()`)
- **Related:** `tests/extended/test_model_kind_runtime.py` (sibling drift watch), `.github/workflows/extended.yml` (sibling cron)
- **Code:** `tests/extended/`, `pyproject.toml` (markers section), `.github/workflows/`, `justfile`

**Goal**: Catch upstream OpenAI API drift in user-visible CLI workflows by running 8 real-API tests every Saturday night via a new `live_api` pytest marker. Sibling to today's `extended` marker (model-kind drift, nightly). Trimmed from a 27-test mock-mirror down to 8 high-leverage tests covering streaming, file output, append, no-metadata, secret leak, and mismatch defense.

**Out of Scope**
- Multi-provider tests (`--combined`, `--auto` chain) — defer until P22+ ship real Perplexity/Gemini providers.
- Mock-mirror parity for low-value flags (`--quiet`, repeatable `--out`, stdin/`--prompt-file`, `--input-file`, bare-prompt leading/trailing, `--output-dir` for immediate, `--project`, tee `-,FILE`).
- `extended_slow` gate for completion-required deep_research jobs — defer until cost data justifies.
- Updates to existing tests (e.g. extending `test_model_kind_runtime.py`) — slim scope adds files only.
- Notification/issue-creation on red badge — manual badge-watching matches the existing `extended.yml` posture.
- Status/cancel real-API tests (`thoth status <op-id>`, `thoth cancel <op-id>`) — already covered by `tests/extended/test_openai_cli_lifecycle.py` (P18-T38).

### Tests & Tasks
- [ ] [P20-TS01] `live_cli_env` fixture: skip-unless `OPENAI_API_KEY`; isolated `HOME` / `XDG_CONFIG_HOME` / `XDG_STATE_HOME` / `XDG_CACHE_HOME`; bounded subprocess timeout; secret-scrub on captured failure output.
- [ ] [P20-TS02] Assertion helpers: `assert_nonempty_file`, `assert_metadata_present`, `assert_metadata_absent`, `assert_secret_not_leaked`.
- [ ] [P20-TS03] `thoth ask "live api streaming smoke" --mode thinking --provider openai` streams non-empty stdout, exits 0, creates no default result file, emits no background completion/status/resume hints.
- [ ] [P20-TS04] `thoth ask "live api file" --mode thinking --provider openai --out answer.md` writes a non-empty `answer.md`, suppresses streamed stdout, creates no default result file.
- [ ] [P20-TS05] `--append`: run the file-output command twice to the same path; assert file size grew and the first run's content prefix is preserved.
- [ ] [P20-TS06] `--no-metadata`: written file is non-empty but has no YAML front-matter, no `operation_id:`, no `### Prompt` section.
- [ ] [P20-TS07] `--api-key-openai sk-...` succeeds with `OPENAI_API_KEY` unset in the test env; assert exit 0 AND key not echoed in stdout/stderr.
- [ ] [P20-TS08] Mismatch defense (no HTTP): real provider construction with an immediate-declared deep-research model raises `ModeKindMismatchError` before any network call.
- [x] [P20-T01] Register `live_api` marker in `pyproject.toml`; extend `addopts` to `-m 'not extended and not live_api'`; add `just test-live-api` recipe.
- [x] [P20-T02] Create `.github/workflows/live-api.yml` with cron `0 2 * * 0` (Sat 7pm PDT, Sun 02:00 UTC), `OPENAI_API_KEY` from secrets, `continue-on-error: true`, mirroring `extended.yml` shape.
- [x] [P20-T03] Update `CLAUDE.md` "Code Quality Assurance Workflow" section and `README.md` test-categories block (if present) to mention the new `live_api` marker, weekly cadence, and trigger command.

### Acceptance Criteria
- `uv run pytest -q` deselects both `extended` and `live_api` (default + PR CI unchanged).
- `uv run pytest -m live_api -v` runs all 8 tests when `OPENAI_API_KEY` is present.
- `.github/workflows/live-api.yml` triggers on the scheduled cron and `workflow_dispatch`.
- Cost target: <$0.20 per weekly run (no `extended_slow` work; immediate streams + no-HTTP mismatch defense).
- All 8 tests assert structural properties only (non-empty, exit code, file presence, secret absence) — no deterministic prose.
- First weekly run after merge produces a documented green or red badge in the merging PR.

## [x] Project P18: Immediate vs Background — Explicit `kind`, Runtime Mismatch, Path Split, Streaming, Cancel (v3.1.0)

**References**
- **Spec:** `docs/superpowers/specs/2026-04-26-p18-immediate-vs-background-design.md` (decisions Q1–Q12 §4, architecture §5, rollout §6, testing strategy §7, cross-project coordination §8, risks §9, **§11 reevaluation log 2026-04-27**)
- **Plan:** `docs/superpowers/plans/2026-04-26-p18-immediate-vs-background.md` (TDD discipline, phase dependency graph, file map, Phase A starter steps, commit cadence, end-of-project checklist, **call-site migration matrix**, **reevaluation 2026-04-27**)

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
- [x] [P18-TS01] `tests/test_builtin_modes_have_kind.py`: every entry in `BUILTIN_MODES` declares `kind ∈ {"immediate","background"}`
- [x] [P18-TS02] `tests/test_known_models_registry.py`: `derive_known_models()` returns one entry per unique `(provider, model)` across builtins; cross-mode kind conflicts raise `ThothError` at module import
- [x] [P18-TS03] `tests/test_known_models_registry.py`: every builtin's `(provider, model, kind)` triple appears in `KNOWN_MODELS`
- [x] [P18-T01] Add `kind` field to all 12 entries in `BUILTIN_MODES` (`config.py:42-133`)
- [x] [P18-T02] Add `ModelSpec` NamedTuple + `derive_known_models()` + module-level `KNOWN_MODELS` constant (in `models.py`)
- [x] [P18-T03] Add `mode_kind(cfg) -> Literal["immediate","background"]` resolver in `config.py`; thin `is_background_mode` wrapper kept for compat with deprecation comment
- [x] [P18-T03b] **(Reeval 2026-04-27)** Update `modes_cmd.py:_derive_kind` (`modes_cmd.py:46-50`) to read `cfg["kind"]` first; fall back to substring heuristic only with a warning. Pre-existing CLI surface (`thoth modes` table "Kind" column) keeps working unchanged.
- [x] [P18-T03c] **(Reeval 2026-04-27)** Audit summary deliverable: write `planning/p18-call-site-audit.md` enumerating the 9 `is_background_*` call sites (per spec §10 acceptance gate); annotate each with disposition (migrate to `mode_kind` / keep as model-level helper / no-op).

**Phase B — Runtime mismatch error (additive, user-visible)**
- [x] [P18-TS04] `tests/test_mode_kind_mismatch.py`: `OpenAIProvider.submit(...)` with `kind="immediate"` + `model="o3-deep-research"` raises `ModeKindMismatchError` *before* any HTTP call (use `respx`/cassette to assert no API hit)
- [x] [P18-TS05] Same with `kind="immediate"` + `model="o4-mini-deep-research"`
- [x] [P18-TS06] `kind="background"` + `model="o3"` does NOT raise (legal force-background)
- [x] [P18-TS07] `tests/test_mode_kind_mismatch.py`: `ModeKindMismatchError` carries `mode_name`, `model`, `declared_kind`, `required_kind` attrs and renders a user-facing `suggestion` referencing `[modes.{mode_name}]`
- [x] [P18-T04] Add `ModeKindMismatchError` class to `errors.py` (subclass of `ThothError`)
- [x] [P18-T05] Thread `mode_config["kind"]` through `create_provider` (`providers/__init__.py:107-112`) into `provider_config["kind"]`; replace the `is_background_mode(provider_config)` call at `providers/__init__.py:111` with `mode_kind(provider_config) == "background"`
- [x] [P18-T06] Add `OpenAIProvider._validate_kind_for_model(mode)` and call it as the first line of `submit()`. The check uses `is_background_model(self.model)` (model-level helper, kept) to determine *required* kind.

**Phase C — Path split + hint suppression**
- [x] [P18-TS08] `tests/test_immediate_path.py`: an immediate-mode run produces no `Progress` rendering, no spinner, no operation-ID echo (unless `--project` or `--out FILE` set), no `thoth resume` hint on failure
- [x] [P18-TS09] `tests/test_background_path.py`: existing background-mode behavior unchanged (regression gate — uses existing fixtures including spinner-engaged TTY case)
- [x] [P18-TS10] `tests/test_immediate_path.py`: an immediate-mode run with `--project foo` DOES write a checkpoint and emit operation ID
- [x] [P18-TS10b] **(Reeval 2026-04-27)** `tests/test_progress_gating.py`: `should_show_spinner` returns `False` for immediate-kind runs (extends existing `progress.py:16-36` test coverage); `_poll_display` falls through to a no-display branch (neither spinner nor Progress) for immediate-kind in TTY
- [x] [P18-T07] Rename `_execute_research` (`run.py:550`) → `_execute_background` in `run.py`; extract a top-level `execute(...)` dispatcher that matches `mode_kind(mode_config)`
- [x] [P18-T08] Add `_execute_immediate` (initially non-streaming — single `submit()` call, direct `get_result()` call, sink to stdout); skips progress bar, spinner, polling loop, resume hints
- [x] [P18-T08b] **(Reeval 2026-04-27)** Extend `_poll_display` (`run.py:57-90`) and `should_show_spinner` (`progress.py:16-36`) to also suppress the `Progress` bar branch for immediate-kind runs (today: spinner is gated, Progress fires unconditionally). Add a `mode_cfg` or `mode_kind` parameter so the gate is mode-aware, not just model-aware.
- [x] [P18-T09] Audit `run.py:629,654,691,692` and `run.py:199,311,313` and `signals.py:93,99` and `commands.py:227,238` — gate every `thoth resume {id}` / `thoth status {id}` / `Operation ID:` emission on `mode_kind(mode_config) == "background"` (or persistence flag set)
- [x] [P18-T09b] **(Reeval 2026-04-27)** Migrate `cli.py:284` (`_thoth_config.is_background_model(model_name)` call) to `mode_kind(mode_config) == "background"` once a mode_cfg is in scope. If `mode_cfg` not available at that call site, leave as `is_background_model(model_name)` (model-level helper) and document.
- [x] [P18-T09c] **(Reeval 2026-04-27)** Migrate `interactive_picker.py:35,44` (`is_background_model(model)` filter on `--pick-model` candidates) to `mode_kind(mode_cfg) == "immediate"`. UX unchanged.
- [x] [P18-T09d] **(Reeval 2026-04-27)** Migrate `cli_subcommands/ask.py:171,176` (`is_background_mode(mode_config)` for Option E `--json` envelope) to `mode_kind(mode_config) == "background"`. Behavior unchanged.

**Phase D — Mode rename + `thoth modes --kind` filter**
- [x] [P18-TS11] `tests/test_mode_aliases.py`: `--mode mini_research` resolves to `quick_research`'s config, prints a one-time deprecation warning per process
- [x] [P18-TS11b] **(Reeval 2026-04-27)** `tests/test_modes_kind_filter.py`: `thoth modes --kind immediate` shows only immediate modes; `thoth modes --kind background` shows only background; invalid value rejected with `BadParameter`; tab-completion uses `completion/sources.py:79 mode_kind` (returns `["immediate","background"]`)
- [x] [P18-T10] Add `quick_research` builtin (copy of current `mini_research` with renamed key + `kind="background"`); keep `mini_research` as `{"_deprecated_alias_for": "quick_research"}` stub
- [x] [P18-T11] `get_mode_config` resolves alias and emits deprecation warning via stdlib `warnings`
- [x] [P18-T11b] **(Reeval 2026-04-27)** Wire `--kind <immediate|background>` flag into `cli_subcommands/modes.py` (the existing `modes` subgroup from P11); use `shell_complete=mode_kind` from `completion/sources.py:79` (currently committed as P18 forward-compat dead code per its own docstring). Filter applies to `modes list/json` operations.
- [x] [P18-T11c] **(Reeval 2026-04-27)** Update `cli_subcommands/_options.py:91` `--pick-model` help string from "(immediate modes only)" to "Interactively pick a model (only for modes with `kind = immediate`)" — language now reflects declared kind, not the substring heuristic.

**Phase E — Streaming + output sinks**
- [x] [P18-TS12] `tests/test_provider_stream_contract.py`: `MockProvider.stream()` yields deterministic chunks; aggregating them equals the full mock result
- [x] [P18-TS13] `tests/test_provider_stream_contract.py`: `OpenAIProvider.stream()` (cassette-replay) yields text deltas; final aggregated string matches non-streaming `get_result` output for the same prompt
- [x] [P18-TS14] `tests/test_provider_stream_contract.py`: streaming a background-only model raises (defense in depth — should be unreachable post-mismatch-check)
- [x] [P18-TS15] `tests/test_output_sinks.py`: `--out -` writes to stdout only; `--out FILE` writes to file only and creates it; `--out -,FILE` tees; `--append` opens with `"a"`, default opens with `"w"`; file is opened lazily (no empty file on aborted submit)
- [x] [P18-T12] Add `StreamEvent` dataclass (`kind`, `text`) and `async def stream(...)` to `ResearchProvider` base raising `NotImplementedError`
- [x] [P18-T13] Implement `MockProvider.stream()` — fixed chunk list with small `await asyncio.sleep(0)` between yields
- [x] [P18-T14] Implement `OpenAIProvider.stream()` using `client.responses.stream(...)` for non-deep-research models; translate `response.output_text.delta` into `StreamEvent("text", delta)`
- [x] [P18-T15] Add `MultiSink` class (in new `src/thoth/sinks.py`) — fans `write(chunk)` to a list of `IO[str]` handles, lazy file open, ordered close in `finally`
- [x] [P18-T16] **(Reeval 2026-04-27)** Add `--out PATH` (repeatable, accepts `-`, comma-list also accepted) and `--append` flags to **`cli_subcommands/_options.py:_RESEARCH_OPTIONS`** so they are inherited by both top-level CLI and `thoth ask` (the existing `_research_options` decorator stack). Add corresponding entries to `cli_subcommands/_option_policy.py` for inheritance + validation. Wire to `MultiSink` inside `_execute_immediate` via `_run_research_default`.
- [x] [P18-T17] Update `_execute_immediate` to call `provider.stream()` and feed chunks into the configured `MultiSink`. If `provider.stream()` raises `NotImplementedError`, fall back to `submit()` + `get_result()` and sink the final string in one chunk.

**Phase F — Cancel: research per provider**
- [x] [P18-T18] **Research item: OpenAI cancel.** WebFetch `https://platform.openai.com/docs/api-reference/responses` (cancel endpoint section) and `https://cookbook.openai.com/examples/deep_research_api/introduction_to_deep_research_api`. Confirm: signature of `client.responses.cancel(response_id)`, accepted source states, returned status string. Document findings in `planning/p18-cancel-research.md`.
- [x] [P18-T19] **Research item: Perplexity cancel.** WebFetch `https://docs.perplexity.ai/getting-started/models/models/sonar-deep-research` and `https://docs.perplexity.ai/guides/chat-completions-guide`. Confirm: does the async submission flow expose a cancel endpoint, or must we orphan the request_id? Document in `planning/p18-cancel-research.md`.
- [x] [P18-T20] **Research item: Gemini cancel.** WebFetch `https://ai.google.dev/gemini-api/docs/deep-research` and `https://ai.google.dev/gemini-api/docs/interactions`. Confirm: Interactions API cancel/abort semantics. Document in `planning/p18-cancel-research.md`.

**Phase G — Cancel: implementation**
- [x] [P18-TS16] `tests/test_provider_cancel.py`: `MockProvider.cancel(job_id)` removes the job and returns `{"status":"cancelled","error":"cancelled by user"}`
- [x] [P18-TS17] `tests/test_provider_cancel.py` (cassette): `OpenAIProvider.cancel(job_id)` calls `responses.cancel`, returns cancelled-shaped status
- [x] [P18-TS18] `tests/test_provider_cancel.py`: providers that don't implement cancel raise `NotImplementedError`; the `thoth cancel` CLI catches it and reports "upstream cancel not supported, local checkpoint marked cancelled"
- [x] [P18-TS19] `tests/test_cancel_subcommand.py`: `thoth cancel <op-id>` updates the checkpoint to `cancelled`, calls `provider.cancel()` for each non-completed provider, exits 0
- [x] [P18-TS20] `tests/test_cancel_subcommand.py`: `thoth cancel MISSING_ID` exits 6 (matching `thoth resume` missing-op behavior)
- [x] [P18-T21] Add `async def cancel(self, job_id: str) -> dict[str, Any]` to `ResearchProvider` base raising `NotImplementedError`
- [x] [P18-T22] Implement `MockProvider.cancel()`
- [x] [P18-T23] Implement `OpenAIProvider.cancel()` per Phase F findings
- [-] [P18-T24] (Perplexity/Gemini cancel impls — only if Phase F research confirms upstream support; otherwise leave as the base `NotImplementedError`)
- [x] [P18-T25] Add `src/thoth/cli_subcommands/cancel.py` — `@click.command("cancel")`, `OP_ID` required positional, `--json` flag, delegates to a new `cancel_operation(op_id, ctx)` in `commands.py`. Mirror the `cli_subcommands/resume.py` pattern (already shipped).
- [x] [P18-T25b] **(Reeval 2026-04-27)** Register `cancel` in `cli.py` via `cli.add_command(cancel)` and add to "Run research" help section in `ThothGroup.format_commands`. Add `shell_complete=operation_ids` to the `OP_ID` positional (using the existing completer from `completion/sources.py:26`).
- [x] [P18-T26] Add `cancel_operation()` to `commands.py` — load operation, iterate non-completed providers, call `provider.cancel()` (catch `NotImplementedError` → emit "upstream cancel not supported, local checkpoint marked cancelled"), update checkpoint, emit user-facing summary. Returns enough data for `--json` envelope.
- [x] [P18-T27] Wire Ctrl-C upstream cancel into the **shared polling loop** (`run.py:_run_polling_loop`, used by both `_execute_background` and `resume_operation`). At the existing `_raise_if_interrupted()` site (`run.py:584`), when the interrupt event is set: resolve toggle (CLI `--cancel-on-interrupt`/`--no-cancel-on-interrupt` overrides config `[execution].cancel_upstream_on_interrupt`, default `true`); if on, call `provider.cancel(job_id)` for every non-completed provider in `jobs` via `asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=5)` (parallel, single 5s envelope); per-provider `NotImplementedError` / `asyncio.TimeoutError` are swallowed; on success print "Cancelled upstream: {provider}". When toggle is off and `--json` is **not** set, print one-line hint "Upstream job still running; run `thoth cancel <op-id>` to stop billing". Then raise `KeyboardInterrupt`. **Out of scope:** `--async` submissions (process already exited), immediate-mode runs (no upstream job). `signals.py` unchanged — the handler keeps owning the local-checkpoint write.

**Phase H — User-mode `kind` warning (warn-once now; v4.0.0 follow-up errors)**
- [x] [P18-TS21] `tests/test_user_mode_kind_warning.py`: a user TOML with a `[modes.X]` table missing `kind` triggers a one-time warning at config load referencing the offending key
- [x] [P18-T28] Add the warning emission in `_validate_config` (`config.py:367`) / mode-merge path; do not error
- [x] [P18-T29] Add a `# TODO(v4.0.0): error on missing kind in user modes` comment at the warning site, cross-referencing future P19

**Phase I — Extended test infrastructure**
- [x] [P18-TS22] `tests/extended/test_model_kind_runtime.py`: parametrized over `KNOWN_MODELS`, hits real API, asserts immediate-kind models return `completed` on first `check_status` and background-kind models return `running`/`queued`/`completed`; cancels background submissions to limit cost (depends on Phase G `provider.cancel()`)
- [x] [P18-T30] **(Reeval 2026-04-27)** Add a NEW `[tool.pytest.ini_options]` section to `pyproject.toml` (none present today): register `extended` marker; add `addopts = "-m 'not extended'"` to default invocation. Verify pre-commit `./thoth_test` integration suite is unaffected (it uses its own runner, not pytest markers).
- [x] [P18-T31] Add `just test-extended` recipe → `uv run pytest -m extended -v`
- [-] [P18-T32] Add `--extended` flag to `thoth_test` runner (parses to a category column); wire to category filter — *superseded by `just test-extended` (P18-T31) + `.github/workflows/extended.yml` (P18-T33), which already provide pytest-level gating; runner-flag is duplicative*
- [x] [P18-T33] Add `.github/workflows/extended.yml` (nightly cron, gated on `OPENAI_API_KEY` repo secret); failures notify but don't block PRs

**Phase J — Documentation + cleanup**
- [x] [P18-T34] Update `README.md` with `--out` flag examples; document the `kind` field for user-defined modes; document `thoth cancel`; document `thoth modes --kind <immediate|background>` filter
- [x] [P18-T35] Update `manual_testing_instructions.md` with immediate-vs-background streaming/cancel/modes-filter scenarios
- [-] [P18-T36] Remove the `if not job_info.get("background", False): return {"status": "completed"}` shortcut in `OpenAIProvider.check_status` (`providers/openai.py:269-270`). **Decided not to do** — commit `41455a3` deliberately deferred removal to v4.0.0/P19 and added an in-source TODO (`providers/openai.py:264-270`); leaving the shortcut as defense-in-depth for `--async` on non-deep-research models.
- [x] [P18-T36b] **(Reeval 2026-04-27)** Update spec `docs/superpowers/specs/2026-04-26-p18-immediate-vs-background-design.md` Status field from "Draft" → "Shipped (v3.1.0, commit `<HASH>`)". Update plan with the same status note.
- [x] [P18-T37] CHANGELOG entries (non-breaking — additive only) — release-please will pick these up for **v3.1.0**: `feat: explicit "kind" field on built-in modes`, `feat: streaming output for immediate modes (--out)`, `feat: thoth cancel <op-id>`, `feat: thoth modes --kind <immediate|background> filter`, `feat: rename mini_research mode to quick_research (alias kept)`, `chore: deprecate "async" mode-config key`
- [x] [P18-T38] Add `--async` flag to `thoth resume` for non-blocking status check + ready-file download. Behavior: do **one** `provider.check_status()` per non-completed provider, save results for any newly-completed ones via `OutputManager.save_result`, update the checkpoint, print a status summary (or JSON envelope when combined with `--json`), and exit without entering the polling loop. Distinct from `thoth resume --json` (pure read-only snapshot, no side effects) and from default `thoth resume` (blocks on full polling loop). Use case: drive-by progress check that also pulls down whatever's ready.

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

