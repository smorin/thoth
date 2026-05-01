# P16 PR1 — Click-Native CLI Refactor — Subcommand Migration & Parity Gate (v2.15.0)

**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)

**Status:** `[x]` Completed.

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
