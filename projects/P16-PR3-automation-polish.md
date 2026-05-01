# P16 PR3 — Automation Polish — `completion` subcommand + universal `--json` (v3.0.0)

**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)

**Status:** `[x]` Completed.

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
