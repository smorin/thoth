# P15 — P14 Bug Fixes — pick-model gating, spinner-progress conflict, prompt-file caps (v2.14.0)

**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)

**Status:** `[x]` Completed (v2.14.0).

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
