# P21b — Configuration Profile CRUD Commands

**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)
- **Spec:** `docs/superpowers/specs/2026-04-28-p21b-configuration-profiles-crud-design.md`
- **Plan:** `docs/superpowers/plans/2026-04-28-p21b-configuration-profiles-crud.md`
- **Depends on:** P21 (Configuration Profile Resolution & Overlay)
- **Research:** `research/configuration_profile_pattern.v1.md`

**Status:** `[x]` Completed.

**Goal**: Add `thoth config profiles list/show/current/set-default/unset-default/add/set/unset/remove` so users can manage profiles from the CLI without hand-editing TOML. Depends on P21 (uses `cm.profile_catalog`, `cm.profile_selection`, and the threaded `--profile` plumbing).

**Status**: Complete — data functions, Click subgroup, JSON envelopes, and docs all landed across commits `8f9f229` (Task 0 docs rename), `53237e3` (Task 1 data functions), `6126486` (Task 2 Click leaves + JSON envelopes), and the Task 3 docs commit (this one).

**Scope**
- Add nine `get_config_profile_*_data` functions in `config_cmd.py` using `tomlkit`: `list`, `show`, `current`, `set_default`, `unset_default`, `add`, `set`, `unset`, `remove`. Singular naming throughout.
- Add a `config profiles` Click subgroup with corresponding leaves; preserve TOML comments through `tomlkit`.
- Active-state readers (`list`, `current`) honor inherited `--profile`; raw lookup `show NAME` and mutator leaves (`add`/`set`/`unset`/`remove`/`set-default`/`unset-default`) reject it.
- `list` hides same-name lower-precedence user profiles by default and supports `--show-shadowed` to include those rows with explicit `shadowed` / `shadowed_by` metadata.
- `set-default NAME` validates `NAME` against the resolved catalog for the target config view (user/custom + project tiers) before persisting `general.default_profile`; inherited `--config PATH` profiles are valid targets.
- `unset KEY` removes only the named leaf; empty parent tables are left in place. `remove NAME` deletes the whole `[profiles.<name>]` block.
- `--config PATH` and `--project` remain mutually exclusive.

**Out of Scope**
- Anything in P21's out-of-scope list (still applies).
- Top-level `thoth profiles` command group (commands live under `thoth config profiles`).
- Profile-name validation beyond what TOML's bare-key syntax enforces.

### Tests & Tasks
- [x] [P21b-TS01] Specify CRUD test suite (data functions, Click leaves, JSON envelopes, comment preservation, depth-4 paths) before implementation. (Commit `53237e3`.)
- [x] [P21b-TS02] `tests/test_config_profiles_cmd.py`: profile data functions add, set, show, unset, remove, set_default, unset_default, current, list — round-trip and metadata. `list` default output shows only the winning row per profile name; `list(show_shadowed=True)` includes the shadowed user row with `shadowed=true`, `shadowed_by`, and `active=false`. (Commit `53237e3`.)
- [x] [P21b-TS03] `tests/test_config_profiles_cmd.py`: no-prune unset coverage — deep path (`profiles.fast.general.default_mode`) set/unset writes/removes only the leaf and leaves the now-empty `[profiles.fast.general]` parent in place; `unset-default` removes `general.default_profile` while leaving `[general]` in place. (Commit `53237e3`.)
- [x] [P21b-TS04] `tests/test_config_profiles_cmd.py`: tomlkit comment preservation — comments around `[profiles.fast]` and on individual lines survive `set` then `unset`. (Commit `53237e3`.)
- [x] [P21b-TS05] `tests/test_config_profiles_cmd.py`: `set-default NAME` rejects names absent from the resolved catalog with `ConfigProfileError`; cross-tier resolution allows `set-default NAME` when `NAME` lives only in the project tier; inherited `--config PATH` succeeds when `NAME` lives only in that custom config file. (Commit `53237e3`.)
- [x] [P21b-TS06] `tests/test_config_profiles_cmd.py`: mutator leaves (`add`/`set`/`unset`/`remove`/`set-default`/`unset-default`) and raw lookup `show NAME` reject root `--profile`; active-state readers (`list`/`current`) honor it. End-to-end: persisted `fast` + `--profile bar` → `current` returns `bar` from `flag`, `config get general.default_profile` still returns `fast`. (Commit `6126486`.)
- [x] [P21b-T01] Add the nine `get_config_profile_*_data` functions to `config_cmd.py` using existing helpers (`_target_path`, `_reject_config_project_conflict`, `_load_toml_doc`, `_parse_value`, `_mask_in_tree`, `_to_plain`) plus a no-prune leaf-removal helper for profile `unset` and `unset-default`. Do not call `_unset_in_doc` for P21b profile unsets because it prunes empty parent tables. `unset` removes only the named leaf; `set-default NAME` validates against the resolved catalog for the target config view, including inherited `--config PATH`. (Commit `53237e3`.)
- [x] [P21b-T02] Add `config profiles` Click subgroup to `src/thoth/cli_subcommands/config.py` with leaves for `list`, `show`, `current`, `set-default`, `unset-default`, `add`, `set`, `unset`, `remove`. Mutator leaves and `show NAME` omit `"profile"` from `honored_options`; `list` and `current` include it. Add typed `--show-shadowed` on `list`. JSON output via existing envelope helpers. (Commit `6126486`.)
- [x] [P21b-T03] Update `tests/test_json_envelopes.py` and `tests/test_ci_lint_rules.py` for every JSON-capable profile leaf: `list`, `show`, `current`, `set-default`, `unset-default`, `add`, `set`, `unset`, and `remove`. Include mutator smoke rows with fixture/setup state where needed, plus a `list --show-shadowed --json` row. (Commit `6126486`.)
- [x] [P21b-T04] Update `README.md`, `manual_testing_instructions.md`, and `src/thoth/help.py` with command examples (`thoth config profiles ...` invocations) and the `config get general.default_profile` vs `config profiles current` distinction. (Task 3 commit.)
- [x] [P21b-T05] Update `PROJECTS.md` as implementation tasks land. (Task 3 commit.)

### Automated Verification
- `uv run pytest tests/test_config_profiles_cmd.py tests/test_json_envelopes.py tests/test_ci_lint_rules.py -v` passes.
- `just check` passes.
- `./thoth_test -r --skip-interactive -q` passes.
- `just test-lint` passes.
- `just test-typecheck` passes.
- `git diff --check` passes.
