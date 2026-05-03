# P35 — Modes Set-Default / Unset-Default Commands

**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)
- **Spec:** [docs/superpowers/specs/2026-05-01-p35-modes-set-default-design.md](../docs/superpowers/specs/2026-05-01-p35-modes-set-default-design.md)
- **Branch / worktree:** `p35-modes-set-default` at `/Users/stevemorin/c/thoth-worktrees/p35-modes-set-default`

**Status:** `[~] In progress — implementation complete; review fix batch in progress.

**Goal**: Add `thoth modes set-default NAME` and `thoth modes unset-default` parallel to the existing `thoth config profiles set-default` / `unset-default`. Two scopes — base `general.default_mode` and per-profile `profiles.<X>.default_mode` — plus a runtime resolution change so the per-profile key actually overrides the base when its profile is active. Replaces the awkward `thoth config set general.default_mode NAME` UX with a validated, mode-aware command.

**Motivation**: Today, setting the default mode requires the generic `thoth config set` command, which exposes a TOML key path and performs no validation. There is also no per-profile equivalent — every profile shares the same default mode. The `config profiles set-default` command proved the "set-the-pointer" UX; P35 ports that pattern to modes and adds the per-profile dimension.

**Scope**
- New CLI surface: `thoth modes set-default NAME [--project | --config PATH] [--profile X] [--json]` and `thoth modes unset-default [...same flags...]`.
- New `ConfigDocument` mutation primitives: `set_default_mode`, `unset_default_mode`, `default_mode_name` (each accepting an optional `profile` kwarg).
- New pure-data functions in `config_cmd.py`: `get_modes_set_default_data`, `get_modes_unset_default_data`. JSON envelope mirrors `config profiles set-default`.
- Shared `modes_cmd.py` mutator registry entries and generated `cli_subcommands/modes.py` leaves, matching the target-flag behavior of add/set/unset/remove/rename/copy.
- Update `_config_default_mode()` in `cli.py` so the precedence chain is: positional builtin → `--mode` flag → `THOTH_DEFAULT_MODE` env → `profiles.<active>.default_mode` → `general.default_mode` → `"default"`.
- Same-tier validation rule for `--profile X` on `set-default`: profile X must already be defined in the target tier file; otherwise exit 1 with a remediation hint. Mode NAME validation stays cross-tier (β). `unset-default` is exempt from the same-tier rule (δ).
- Unset-default is fully idempotent: target file missing → `NO_FILE`, key absent → `NOT_FOUND`, both exit 0.

**Out of Scope**
- New inspector command (e.g. `thoth modes default`). The resolved value already surfaces via `--debug` config dumps and `thoth config show`.
- Deprecating `THOTH_DEFAULT_MODE`. Env retains its current highest-non-CLI slot.
- Changing the schema default `"default"` for `general.default_mode`.
- Auto-routing `--profile X` (without `--project`) to whichever tier defines X. Orthogonal flags only.
- A `thoth profiles set-default` shorthand alias.

### Tests & Tasks

- [x] [P35-TS01] Author validation tests for `set-default`: NAME-not-in-catalog → exit 1 with available list; `--project --config PATH` conflict → exit 2; builtin NAME accepted; cross-tier NAME accepted under `--profile`. Live in `tests/test_modes_set_default.py`.
- [x] [P35-TS02] Author tier-matrix regression rows covering default user writes, inline `--project`, inline `--config PATH`, inline `--profile X`, `--profile X --project`, `--profile X --config PATH`, and `--project --config PATH` conflict. Rows assert the target file/key and CLI exit behavior; JSON envelope coverage is explicit in TS06.
- [x] [P35-TS03] Author **same-tier profile-existence rule** tests for `set-default`: missing target-tier profile under `--project` exits 1 with specific remediation; project-profile and custom-config profile targets are accepted; missing/unknown profile data-layer checks reject cleanly.
- [x] [P35-TS04] Author `unset-default` idempotency tests: key present → removed + table preserved; key absent → `NOT_FOUND` exit 0; file missing → `NO_FILE` exit 0; profile/file existence NOT required (δ).
- [x] [P35-TS05] Author resolution-chain tests in `tests/test_default_mode_resolution.py` covering all 6 cases: empty config → `"default"`; only `general.default_mode`; profile without `default_mode` → falls through; profile with `default_mode` overrides general; `THOTH_DEFAULT_MODE` env beats profile; profile defined in TOML but not the active selection → ignored.
- [x] [P35-TS06] Author JSON envelope tests asserting `modes set-default` / `unset-default` success rows, `MODE_NOT_FOUND` error shape, and docs coverage in `docs/json-output.md`.
- [x] [P35-T01] Implement `ConfigDocument.set_default_mode(name, *, profile=None)`, `unset_default_mode(*, profile=None)`, and `default_mode_name(*, profile=None)` in `src/thoth/config_document.py`. Mirror the existing `set_default_profile` / `unset_default_profile` / `default_profile_name` shape and B17 prune-empty semantics.
- [x] [P35-T02] Implement `get_modes_set_default_data(name, *, project, profile, config_path)` and `get_modes_unset_default_data(*, project, profile, config_path)` in `src/thoth/config_cmd.py`. Wire same-tier profile validation, NAME catalog validation, and `PROJECT_CONFIG_CONFLICT` handling. Export in `__all__`.
- [x] [P35-T03] Register `set-default` / `unset-default` in the shared modes mutator dispatch and generate matching Click leaves from `_make_modes_leaf`. Update `_MODES_EPILOG` to mention them. Verify `thoth modes --help` lists both.
- [x] [P35-T04] Update `_config_default_mode()` in `src/thoth/cli.py` to read `THOTH_DEFAULT_MODE` directly, then check `config.active_profile.data.default_mode`, then `general.default_mode`, then `"default"`. Leave the existing `_env_overrides` mapping in place for non-mode-resolution read paths.
- [x] [P35-T05] Run all tests from TS01-TS06 against the implementation; fix until green.
- [x] [P35-T06] Add at least one integration test under `thoth_test/` driving the new commands end-to-end against the mock provider, verifying the resolved default actually flows through to `thoth ask` mode selection.
      Added `P35-INT-01` to `thoth_test`: setup persists `general.default_mode = "deep_research"` via `thoth modes set-default`, the main command runs `thoth ask` (no `--mode`) and asserts `*_deep_research_mock_*.md` is created with `mode: deep_research` content, teardown runs `thoth modes unset-default` and verifies the key is removed. Suite goes 76 → 77 passing.
- [x] [P35-T07] Manual verification: run the seven worked examples from the spec by hand against tmp configs; confirm error messages are clear and actionable.
      Verified the worked examples against real builtin names. Review follow-up restored inline `--profile` / `--config` parity with sibling `modes` mutators and added regression coverage for the same-tier remediation text.
- [x] [P35-T08] Final pre-commit gate: `make env-check`, `just check`, `just test-lint`, `just test-typecheck`, `pytest`, `./thoth_test -r`. Address any drift; commit when green.
      Review fix batch gate passed: `make env-check`; `just fix`; `just check`; `uv run pytest -q` (`1030 passed, 16 deselected`); `./thoth_test -r` (`93 passed, 11 skipped`); `just test-fix`; `just test-lint`; `just test-typecheck`; `uv run ruff format --check src/ tests/`.
- [ ] [P35-T09] Update CHANGELOG via release-please-friendly conventional commit messages (`feat(modes): add set-default / unset-default commands`). No hand edits to versioning files.
- [ ] [P35-T10] Open PR; verify CI passes; merge.

### Deliverable

```bash
$ uv run thoth modes set-default deep_research
Set default mode to 'deep_research'

$ uv run thoth modes set-default deep_research --profile work
Set default mode to 'deep_research' for profile 'work'

$ uv run thoth modes unset-default --profile work
Unset default mode for profile 'work'

$ uv run thoth modes set-default not-a-mode
Error: Mode 'not-a-mode' not found
Available modes: clarification, comparison, deep_research, default, ...
```

### Automated Verification

- `tests/test_modes_set_default.py` and `tests/test_default_mode_resolution.py` pass.
- `./thoth_test -r --skip-interactive -q` passes (existing suite + new integration cases).
- `just check` passes (lint + typecheck).
- `just test-lint` and `just test-typecheck` pass.

### Manual Verification

- Run the 8 worked examples from the spec; confirm exit codes and messages.
- With a profile-with-default-mode active, `thoth ask "test"` (no positional / no `--mode`) actually uses the profile's default.
- `thoth modes --help` shows `set-default` and `unset-default` and the epilog updates.
- Running `thoth config show` after `set-default --profile X` reflects the new key in the merged config.
