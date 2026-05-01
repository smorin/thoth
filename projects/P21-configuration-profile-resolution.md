# P21 — Configuration Profile Resolution & Overlay

**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)
- **Spec:** `docs/superpowers/specs/2026-04-28-p21-configuration-profiles-design.md`
- **Plan:** `docs/superpowers/plans/2026-04-28-p21-configuration-profiles.md`
- **Research:** `research/configuration_profile_pattern.v1.md`

**Status:** `[x]` Completed.

**Goal**: Add CPP-style named configuration profile *resolution* — Thoth honors `--profile NAME`, `THOTH_PROFILE`, and `general.default_profile`, applies the selected `[profiles.<name>]` overlay between project config and env/CLI overrides, and hard-errors on missing profiles. Adds a `prompt_prefix` field with full hierarchy resolution (`profile.modes.X` > `profile` > `modes.X` > `general`; more specific replaces less specific), and ships example profiles via `thoth init` so users get a useful starter config out of the box.

**Status**: Complete — resolver/overlay/root-`--profile` plumbing, `prompt_prefix` 4-level hierarchy, runtime wiring through `run_research`, shipped example profiles in `thoth init`, and the permutation test matrix all landed on `feat/p21-config-profiles`.

**Scope**
- Add profile sections under `[profiles.<name>]`, where nested profile keys mirror normal config paths.
- Resolve profile selection as `--profile NAME` → `THOTH_PROFILE` → `general.default_profile` → no profile.
- Apply the active profile as a `profile` config layer after project config and before environment/CLI per-setting overrides.
- Use per-key replace semantics only; no deep merge inside profile values.
- Hard-error when a selected profile is missing, with the error naming whether the source was flag, env, or config (load-time per REQ-CPP-103).
- Thread the new root `--profile` option through every existing config-loading call site so commands like `thoth config get` honor it.

**Out of Scope**
- `thoth config profiles ...` CRUD commands (deferred to P21b).
- Profile inheritance or `source_profile`-style chains.
- Multiple active profiles.
- Deep-merge behavior inside a profile key.
- Interactive profile selection prompts.
- Runtime profile switching after config is loaded.
- A new top-level `thoth profiles` command group.
- Provider-specific credential chains beyond normal config values.

### Tests & Tasks
- [x] [P21-TS01] Specify the resolver/overlay test suite (resolver, `ConfigManager` overlay, root-flag plumbing) before implementation.
- [x] [P21-T01] Flesh out requirements for configuration profile resolution using `research/configuration_profile_pattern.v1.md`.
- [x] [P21-TS02] `tests/test_config_profiles.py`: `resolve_profile_selection` uses `--profile` before `THOTH_PROFILE`, `THOTH_PROFILE` before `general.default_profile`, and no profile when all are absent.
- [x] [P21-TS03] `tests/test_config_profiles.py`: project profile shadows user profile of the same name wholesale; same-named profile tables are not merged.
- [x] [P21-TS04] `tests/test_config_profiles.py`: missing selected profile raises `ConfigProfileError` and names the selection source for each of `--profile` flag, `THOTH_PROFILE`, and `general.default_profile` pointer (load-time error per REQ-CPP-103).
- [x] [P21-T02] Add `src/thoth/config_profiles.py` with `ProfileSelection`, `ProfileLayer`, profile catalog collection, selection resolution, profile layer resolution, and profile stripping helpers.
- [x] [P21-T03] Add `ConfigProfileError` to `src/thoth/errors.py`.
- [x] [P21-TS05] `tests/test_config_profiles.py`: `ConfigManager` leaves behavior unchanged when no profile is active, applies active profile values, lets env/CLI per-setting values beat profile values, records the actual project config path (`./thoth.toml` or `./.thoth/config.toml`) used by `_load_project_config`, preserves `general.default_profile` after profile splitting, and `THOTH_PROFILE` is NOT in `_get_env_overrides` (regression guard).
- [x] [P21-T04] Update `ConfigManager.load_all_layers` to record the actual project config path used by `_load_project_config`, load raw user/project profiles, resolve the active profile, expose `profile_selection`/`active_profile`/`profile_catalog`, and merge a `profile` layer between project and env.
- [x] [P21-TS06] `tests/test_config_profiles.py`: root `--profile` reaches `thoth config get` and `thoth config list` (via `config_cmd._load_manager`); unknown root profile errors before command output; runtime `--profile`/`THOTH_PROFILE` does NOT mutate the persisted `general.default_profile` (B20: persisted `fast` + `--profile bar` → `config get` returns `fast`, and `cm.profile_selection.name == "bar"` from source `flag`).
- [x] [P21-T05] Add root `--profile` to `_RESEARCH_OPTIONS`, inherited-option policy (`DEFAULT_HONOR` includes `"profile"`), root fallback parsing in `_extract_fallback_options`, and **every** existing config-loading call site, including `src/thoth/config_cmd.py` (`_load_manager` and each `get_config_*_data` entry that reads merged config) and `src/thoth/cli_subcommands/config.py` leaves that forward inherited profile.
- [x] [P21-T06] Update `README.md`, `manual_testing_instructions.md`, and `src/thoth/help.py` with hand-edit profile examples (TOML structure, selection precedence, worked invocations). Documentation examples must show profiles that change the default mode/project, run all available deep-research providers (`["openai", "perplexity"]` today, with a "future-ready" callout pointing at gemini), force one deep-research provider, default to an immediate mode, and store a future-ready interactive default profile. README explains that `--profile`/`THOTH_PROFILE` are read-only runtime inputs and never mutate `general.default_profile`.
- [x] [P21-T07] Update `PROJECTS.md` as implementation tasks land.
- [x] [P21-TS07] `tests/test_config_prompt_prefix.py`: hierarchy resolver — resolves `[profiles.X.modes.M]` > `[profiles.X]` > `[modes.M]` > `[general]` > `None`. More-specific REPLACES less-specific (no concat). Covers each tier, missing-key fallthrough, and empty-string handling.
- [x] [P21-TS08] `tests/test_config_profiles_permutations.py`: permutation matrix — `{flag, env, config-pointer, none}` × `{user-tier, project-tier, both}` × `{prefix-set, prefix-unset}` × `{deep_research, thinking, default}`. Each permutation gets a real TOML config fixture; assertions cover `cm.profile_selection`, the resolved `prompt_prefix`, and the final mode_config. Includes the shipped `init` examples.
- [x] [P21-TS09] `tests/test_run_prompt_prefix.py`: integration — when a profile is active and a `prompt_prefix` resolves, the assembled prompt that reaches the provider is `f"{prefix}\n\n{user_prompt}"`. The mode's `system_prompt` is unchanged. When no prefix resolves, the prompt is unchanged.
- [x] [P21-T08] Add `resolve_prompt_prefix(config, mode)` helper to `src/thoth/config_profiles.py` implementing the 4-level hierarchy.
- [x] [P21-T09] Wire `resolve_prompt_prefix` into `src/thoth/run.py:run_research` so the resolved prefix is prepended to the user prompt once at run entry; `operation.prompt` records the assembled prompt for resume parity.
- [x] [P21-T10] Update `src/thoth/commands.py:init_command` to ship example profiles in the generated `~/.config/thoth/config.toml`: `daily` (thinking + default project), `quick` (thinking), `openai_deep` (single-provider deep_research), `all_deep` (parallel openai+perplexity), `interactive` (interactive mode), and `deep_research` (deep_research with a worked `prompt_prefix` example demonstrating Q3a hierarchy).
- [x] [P21-T11] Document the `prompt_prefix` field and its hierarchy in `README.md` and `manual_testing_instructions.md`. Worked example: `[general] prompt_prefix`, `[modes.deep_research] prompt_prefix`, `[profiles.X] prompt_prefix`, `[profiles.X.modes.M] prompt_prefix` — show resolution outcome for each combination.

### Automated Verification
- `uv run pytest tests/test_config_profiles.py tests/test_config_cmd.py -v` passes.
- `just check` passes.
- `./thoth_test -r --skip-interactive -q` passes.
- `just test-lint` passes.
- `just test-typecheck` passes.
- `git diff --check` passes.
