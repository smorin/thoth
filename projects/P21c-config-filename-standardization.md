# P21c — Config Filename Standardization

**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)
- **Spec:** `docs/superpowers/specs/2026-04-28-p21c-config-filename-standardization-design.md`
- **Plan:** `docs/superpowers/plans/2026-04-28-p21c-config-filename-standardization.md`
- **Related:** P21 (`docs/superpowers/specs/2026-04-28-p21-configuration-profiles-design.md`), P21b (`docs/superpowers/specs/2026-04-28-p21b-configuration-profiles-crud-design.md`) — both reference legacy filenames in their specs/plans/tests; P21c either lands first or sweeps through them.

**Status:** `[x]` Completed.

**Goal**: Standardize Thoth's config filename to `thoth.config.toml` so the filename alone uniquely identifies a Thoth config file. Three canonical locations: one user-tier (`$XDG_CONFIG_HOME/thoth/thoth.config.toml`) and two project-tier (`./thoth.config.toml` or `./.thoth.config.toml`, mutually exclusive). Clean break — legacy filenames (`config.toml` in user dir, `thoth.toml`, `.thoth/config.toml`) are no longer read; their presence is detected only to enrich "config not found" error messages with rename guidance.

**Status**: Complete — canonical filename, ambiguity error, legacy-detection helper, `init --user/--hidden/--force`, full source/test/docs sweep all landed across commits `0ce248a` (failing tests), `ac84b00` (paths + errors), `0b5b5b1` (loader), `6ca8ac0` (init flags), `88978c7` (source string sweep), `2590928` (tests + docs sweep).

**Scope**
- Canonical filename is `thoth.config.toml`. Three accepted locations:
  - User: `$XDG_CONFIG_HOME/thoth/thoth.config.toml`
  - Project root, visible: `./thoth.config.toml`
  - Project root, dotfile: `./.thoth.config.toml`
- The two project-tier filenames are mutually exclusive. Both present → `ConfigAmbiguousError` with a "delete one before continuing" message. No precedence is applied.
- Legacy filenames (`config.toml` in user XDG dir, `./thoth.toml`, `./.thoth/config.toml`) are **not loaded**. The `.thoth/` directory form is retired for config purposes.
- A "config not found" error path (and only that path) checks for legacy files at the legacy paths and, if any are present, names them in the suggestion text with the rename target. The legacy-detection helper is never called on the happy path.
- `thoth init` writes `./thoth.config.toml` by default. A flag (`--hidden` or similar — final spelling decided in plan) writes `./.thoth.config.toml` instead. `thoth init --user` writes `$XDG_CONFIG_HOME/thoth/thoth.config.toml` without pre-loading project config, so project-tier ambiguity does not block user-tier repair. `--user` and the dotfile flag are mutually exclusive. `--force` semantics unchanged.
- Sweep README, `manual_testing_instructions.md`, help text, error messages, and the P21/P21b spec/plan docs to use the canonical filename.

**Out of Scope**
- A `thoth config migrate` CLI command that renames files in place.
- Any deprecation-window or fallback read of legacy filenames. Legacy reads are gone, full stop.
- Changes to file format, file structure, or the `[profiles.<name>]` overlay semantics.
- A `THOTH_CONFIG_FILENAME` env var to override the filename.
- Project marker semantics — presence of either canonical project path still means "this is a Thoth project."
- Picking precedence between `./thoth.config.toml` and `./.thoth.config.toml`. There is none; both present → error.
- A directory-form project config (e.g. `./.thoth/thoth.config.toml`).

**Sequencing preference**: P21c → P21 → P21b. Landing P21c before P21 implementation lets P21's spec/plan/tests be written against the canonical names from the start. If P21 is mid-implementation when P21c is approved, fall back to a P21 → P21c → P21b ordering and accept the small sweep through P21's just-landed strings.

**Open questions for the plan** (small items, do not block plan write-up)
- Final spelling for the dotfile-form `init` flag: `--hidden` (recommended), `--dotfile`, or `--dot`.
- Confirm `--force` overwrite semantics extend to `init --user` too.

### Tests & Tasks
- [x] [P21c-TS01] Specify the test suite — canonical resolution at all three locations, ambiguity error on both project-root files, "config not found" error message includes any detected legacy paths, `init` flag combinations — before implementation.
      Landed in `0ce248a` as 30 failing tests in `tests/test_config_filename.py`.
- [x] [P21c-T01] Write the implementation plan at `docs/superpowers/plans/2026-04-28-p21c-config-filename-standardization.md`, resolving the small open questions from the spec.
- [x] [P21c-TS02] `tests/test_config_filename.py`: user-tier loads `$XDG_CONFIG_HOME/thoth/thoth.config.toml` when present; raises `ConfigNotFoundError` when only the legacy `config.toml` exists, and the error message names the legacy file with the rename target. (Tests A1–A5.)
- [x] [P21c-TS03] Project tier: `./thoth.config.toml` only → loads. `./.thoth.config.toml` only → loads. Both present → `ConfigAmbiguousError`. Neither present → returns empty/no-project-config. (Tests B1–B8.)
- [x] [P21c-TS04] Legacy detection helper invoked only on the "config not found" error path; regression guard asserts the legacy detector was not called on a successful canonical load. (Tests C1–C3.)
- [x] [P21c-TS05] `thoth init` writes `./thoth.config.toml` by default. `--hidden` writes `./.thoth.config.toml`. `--user` writes the user-tier canonical path without loading project config. `--user` and `--hidden` are mutually exclusive. None overwrite without `--force`; JSON init emits envelopes for both refusal and `--force` overwrite paths. (Tests D1–D14.)
- [x] [P21c-T02] Update `src/thoth/paths.py`: `user_config_file()` returns the canonical user path. (Commit `ac84b00`.)
- [x] [P21c-T03] Update `src/thoth/config.py`: canonical `project_config_paths`; `ConfigAmbiguousError` if both exist; user-tier load skips legacy; `detect_legacy_paths()` helper. (Commit `0b5b5b1`.)
- [x] [P21c-T04] Update `thoth init`: add `--user`, `--hidden`, `--force`; enforce mutual exclusion. (Commit `6ca8ac0`.)
- [x] [P21c-T05] Add `ConfigNotFoundError` and `ConfigAmbiguousError` to `src/thoth/errors.py`. (Commit `ac84b00`.)
- [x] [P21c-T06] Sweep error messages, help text, and CLI strings to canonical filename. (Commit `88978c7`.)
- [x] [P21c-T07] Update `README.md` with migration note and `manual_testing_instructions.md`. (Commit `2590928`.)
- [x] [P21c-T08] Update P21 and P21b spec/plan docs to canonical filename. (Commit `2590928`.)
- [x] [P21c-T09] Update `PROJECTS.md` as implementation tasks land.

### Automated Verification
- `uv run pytest tests/test_config_filename.py tests/test_config.py -v` passes (test file name finalized in plan).
- `just check` passes.
- `./thoth_test -r --skip-interactive -q` passes.
- `just test-lint` passes.
- `just test-typecheck` passes.
- `git diff --check` passes.
