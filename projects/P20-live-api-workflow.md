# P20 — Live-API Workflow Regression Suite (weekly)

**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)
- **Trunk:** [PROJECTS.md](#) (this file)
- **Plan:** [projects/P20-live-api-workflow.md](projects/P20-live-api-workflow.md) — implementation plan (TDD task-by-task)
- **Depends on:** P18 (immediate-vs-background path split, `--out`/`--append`, `provider.stream()`, `provider.cancel()`)
- **Related:** `tests/extended/test_model_kind_runtime.py` (sibling drift watch), `.github/workflows/extended.yml` (sibling cron)
- **Code:** `tests/extended/`, `pyproject.toml` (markers section), `.github/workflows/`, `justfile`

**Status:** `[~]` In progress.

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
