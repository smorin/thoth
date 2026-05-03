# P35 — `thoth modes set-default` / `unset-default`

## Summary

Add CLI commands to manage the default research mode, parallel to the
existing `thoth config profiles set-default` / `unset-default`. Two
scopes: a base default written to `general.default_mode`, and an active
profile override written to `profiles.<X>.default_mode`. Extend the
runtime resolution path so a per-profile `default_mode` actually takes
effect when its profile is active.

## Motivation

Setting the default mode today requires the generic
`thoth config set general.default_mode NAME`, which:

- Exposes a TOML key path users shouldn't need to know.
- Performs no validation — typos silently create dangling defaults.
- Has no per-profile equivalent.

The existing `thoth config profiles set-default NAME` proved out the
"set-the-pointer" UX for profiles. P35 ports that pattern to modes and
adds the per-profile dimension that's natural for modes but absent for
profile selection.

## Surface

```
thoth [--config PATH] [--profile X] modes set-default NAME [--project] [--config PATH] [--profile X] [--json]
thoth [--config PATH] [--profile X] modes unset-default      [--project] [--config PATH] [--profile X] [--json]
```

`--config PATH` and `--profile X` are accepted both as root-level
inherited options before `modes` and as inline target flags after the
leaf, matching the shared `thoth modes` mutator parser. Inline target
flags override inherited root values. `--project` and `--json` are
leaf-local flags on `set-default` / `unset-default`. JSON envelope
mirrors `config profiles set-default` shape.

## Tier matrix

`--project` / `--config PATH` are **tier selectors** (which file).
`--profile X` is a **key-path selector** (which TOML key). They are
orthogonal.

| Flags                          | File          | Key                          |
|--------------------------------|---------------|------------------------------|
| (none)                         | user config   | `general.default_mode`       |
| `--project`                    | project config| `general.default_mode`       |
| `--config PATH`                | `PATH`        | `general.default_mode`       |
| `--profile X`                  | user config   | `profiles.X.default_mode`    |
| `--profile X --project`        | project config| `profiles.X.default_mode`    |
| `--profile X --config PATH`    | `PATH`        | `profiles.X.default_mode`    |
| `--project --config PATH`      | **error**     | `PROJECT_CONFIG_CONFLICT` (exit 2) |

**Same-tier rule for `--profile X`.** When `--profile X` is passed,
profile X must already be defined in the **target tier** (the file
selected by `--project` / `--config PATH` / default user). The
command refuses if X exists in a different tier or is missing
entirely. The error message tells the user how to fix it: either
adjust the tier flag or create profile X in the desired tier first.

Rationale: the namespace `[profiles.X]` and the keys inside it should
live in the same file. Allowing partial cross-tier entries (e.g.,
`[profiles.X]` defined in project but `profiles.X.default_mode` in
user) creates confusing merge behavior at runtime. Forcing same-tier
co-location surfaces tier-mismatch as an explicit error rather than
a silent footgun.

**Same-tier rule applies only to the profile namespace, not the mode
NAME.** The mode NAME the default points at can be (a) a builtin,
(b) defined in any base `[modes.NAME]` (user or project), or
(c) defined in `[profiles.X.modes.NAME]` (user or project) when
`--profile X` is in play. Modes are resolved at runtime through the
merged config; cross-tier mode resolution is normal. Only the
profile namespace itself requires same-tier co-location.

**Same-tier rule applies only to `set-default`, not `unset-default`.**
Unset is idempotent and harmless when the target file or table is
absent. See `unset-default` rules below.

## Validation

`set-default NAME`:

1. `--project` and `--config PATH` both set → emit
   `PROJECT_CONFIG_CONFLICT`, exit 2 (same shape as
   `profiles set-default`).
2. If `--profile X` is set, X must exist **in the target tier**
   (the same file the write would land in). The check inspects only
   that file's `[profiles.X]` table — not the merged catalog. On
   miss, raise `ConfigProfileError` with `available_profiles`
   scoped to the target tier and a suggestion message telling the
   user either to switch the tier flag or to create profile X in
   the target tier first. Exit 1 (matches existing
   `ConfigProfileError` convention).
3. NAME must be resolvable when the configured default fires (uses
   the merged catalog — cross-tier mode resolution is normal):
   - General scope (no `--profile`): NAME ∈ builtins ∪ base
     `[modes.*]` (across user + project).
   - Profile scope (`--profile X`): NAME ∈ builtins ∪ base
     `[modes.*]` ∪ `[profiles.X.modes.*]`.
   - On miss → "mode not found" `ThothError` including the
     available list. Exit 1 (matches `ThothError` default).

Exit-code summary:

| Failure | Exit code |
|---|---|
| Success | 0 |
| `--project --config PATH` conflict | 2 |
| Profile X not in target tier | 1 |
| Mode NAME not in resolvable set | 1 |

`unset-default`:

- `--project` and `--config PATH` mutual exclusion still applies →
  exit 2 on conflict.
- **No** profile-existence check. Unsetting a key that already isn't
  there is harmless; reaching into a non-existent profile to remove
  a non-existent key is just `NOT_FOUND` (exit 0). Symmetric with
  `config profiles unset-default`, which also doesn't validate.
- NAME validation is N/A (no NAME argument).
- Idempotent: target file missing → `removed=False, reason="NO_FILE"`,
  exit 0. Key absent → `removed=False, reason="NOT_FOUND"`, exit 0.
- Removes only the leaf `default_mode` key. Leaves the surrounding
  `[general]` or `[profiles.X]` table intact even if it goes empty
  (B17 precedent shared with `unset_default_profile`).

## Worked examples

Given:

```
~/.config/thoth/config.toml          (user)
  [profiles.work]
  api_key = "..."

./.thoth/config.toml                 (project)
  [modes.deep-with-stats]
  model = "..."
```

| Command | Outcome |
|---|---|
| `thoth modes set-default deep-with-stats` | ✓ writes `general.default_mode = "deep-with-stats"` to user. NAME resolvable cross-tier (defined in project base modes). |
| `thoth --profile work modes set-default deep-with-stats` | ✓ writes `profiles.work.default_mode = "deep-with-stats"` to user. Profile `work` exists in user (target tier). |
| `thoth --profile work modes set-default deep-with-stats --project` | ✗ exit 1. Profile `work` not in project config. Error: "Profile 'work' not found in project config; pass `--project` only if work is defined there, or run `thoth config profiles add work --project` first." |
| `thoth --profile demo modes set-default deep-with-stats` | ✗ exit 1. Profile `demo` not in user config. Error lists profiles found in user config. |
| `thoth --profile work modes set-default deep_research` | ✓ writes `profiles.work.default_mode = "deep_research"` to user. NAME `deep_research` is a builtin. |
| `thoth modes set-default not-a-mode` | ✗ exit 1. Mode `not-a-mode` not found. Error lists resolvable modes. |
| `thoth --profile work modes unset-default --project` | ✓ no-op. Returns `removed=False, reason="NOT_FOUND"` (or `NO_FILE`). No same-tier check on unset. |
| `thoth --profile demo modes unset-default` | ✓ no-op. Returns `removed=False, reason="NOT_FOUND"`. Profile `demo` doesn't exist anywhere; unset is idempotent. |

## Resolution change

Today (`src/thoth/cli.py:159-161`):

```python
def _config_default_mode(config: ConfigManager) -> str:
    raw = config.get("general.default_mode", "default")
    return str(raw) if raw else "default"
```

After P35, the precedence chain (highest → lowest):

1. CLI positional builtin name (handled in `_resolve_mode_and_prompt`)
2. `--mode` / `-m` flag (handled in `_resolve_mode_and_prompt`)
3. `THOTH_DEFAULT_MODE` env var
4. `profiles.<active>.default_mode` (when a profile is active)
5. `general.default_mode`
6. Hardcoded `"default"`

Slots 3-6 live inside `_config_default_mode`:

```python
def _config_default_mode(config: ConfigManager) -> str:
    env = os.getenv("THOTH_DEFAULT_MODE")
    if env:
        return env

    profile_layer = getattr(config, "active_profile", None)
    if profile_layer is not None:
        data = profile_layer.data if isinstance(profile_layer.data, dict) else {}
        v = data.get("default_mode")
        if isinstance(v, str) and v:
            return v

    raw = config.get("general.default_mode", "default")
    return str(raw) if raw else "default"
```

The existing `THOTH_DEFAULT_MODE → general.default_mode` mapping in
`_env_overrides` (`src/thoth/config.py:425`) is left in place so other
read paths (`thoth config show`, `--debug` dumps) keep seeing the
env-promoted value. Reading the env explicitly here ensures the
precedence holds even when other code paths short-circuit
`general.default_mode`.

## Components touched

| File | Change |
|---|---|
| `src/thoth/config_document.py` | New methods `set_default_mode(name, *, profile=None)`, `unset_default_mode(*, profile=None)`, `default_mode_name(*, profile=None)`. Symmetric with `set_default_profile` / `unset_default_profile` / `default_profile_name`. |
| `src/thoth/config_cmd.py` | New pure-data functions `get_modes_set_default_data(name, *, project, profile, config_path)` and `get_modes_unset_default_data(*, project, profile, config_path)`. Envelope shape mirrors `get_config_profile_set_default_data`. Exported in `__all__`. |
| `src/thoth/cli_subcommands/modes.py` / `src/thoth/modes_cmd.py` | Register `set-default` and `unset-default` in the shared modes mutator dispatch, generate leaves via `_make_modes_leaf`, and update `_MODES_EPILOG` to mention them. |
| `src/thoth/cli.py` | Update `_config_default_mode()` per resolution change above. Add `import os` if not already present (it is). |
| `tests/test_modes_set_default.py` | TDD test file (new) covering validation + matrix + idempotency + JSON envelope. |
| `tests/test_default_mode_resolution.py` | TDD test file (new) covering the precedence chain. |
| `thoth_test/specs/...` | One integration test per command (mock provider) for end-to-end verification. |
| `projects/P35-modes-set-default.md` | New per-project file with task list. Trunk row added to `PROJECTS.md`. |

## TDD test plan

Tests land **before** implementation, per repo policy.

### Set-default validation (`tests/test_modes_set_default.py`)

- NAME not in catalog → exit 1; stderr lists available modes.
- `--project --config PATH` → exit 2, `PROJECT_CONFIG_CONFLICT`.
- NAME = a builtin (e.g. `"deep_research"` or `"default"`) → accepted, write succeeds.
- NAME exists only as `[modes.NAME]` in user → accepted (general scope).
- NAME exists only as `[profiles.Y.modes.NAME]`, writing `--profile X`
  (X ≠ Y) → rejected (mode not resolvable when X is active).
- NAME exists only as `[profiles.X.modes.NAME]`, writing
  `--profile X` → accepted.
- NAME exists in user `[modes.*]`, writing
  `set-default NAME --profile X --project` (and X exists in project)
  → accepted (β: cross-tier mode resolution allowed).

**Same-tier profile-existence rule:**

- Profile X defined only in user; `set-default NAME --profile X`
  (default user target) → accepted.
- Profile X defined only in user; `set-default NAME --profile X --project`
  → exit 1, error names target tier (`project`) and lists profiles
  found there.
- Profile X defined only in project; `set-default NAME --profile X`
  (default user target) → exit 1, error lists user profiles and
  suggests `--project`.
- Profile X defined only in project; `set-default NAME --profile X --project`
  → accepted.
- Profile X defined in both; either tier flag → accepted.
- Profile X nowhere; any tier flag → exit 1 with empty/limited
  available list for the target tier.
- `--config PATH` where PATH has no `[profiles.X]` → exit 1.

### Tier matrix (parametrized)

Cover all 7 rows of the matrix above:

- For each (flags) row, drive the data function with a clean tmp
  user/project pair and assert (a) the right file got the write,
  (b) the right key path was written, (c) other files are untouched,
  (d) the JSON envelope has the documented keys.

### Unset-default idempotency

- Key present → removed, table preserved, exit 0.
- Key absent → `removed=False, reason="NOT_FOUND"`, exit 0.
- Target file missing → `removed=False, reason="NO_FILE"`, exit 0.
- Removing from `[profiles.X]` leaves `[profiles.X]` table even if
  empty.
- Removing from `[general]` leaves `[general]` table even if empty.

### Resolution chain (`tests/test_default_mode_resolution.py`)

Each case uses an isolated `ConfigManager` fixture:

- No env, no profile, no `general.default_mode` → `"default"`.
- `general.default_mode = "deep_research"`, no profile, no env →
  `"deep_research"`.
- `general.default_mode = "deep_research"`, active profile with no
  `default_mode` → `"deep_research"`.
- `general.default_mode = "deep_research"`, active profile with
  `default_mode = "quick_research"` → `"quick_research"`.
- `THOTH_DEFAULT_MODE = "thinking"` + active profile with
  `default_mode = "quick_research"` + `general.default_mode =
  "deep_research"` → `"thinking"`.
- Active profile not loaded (selection.source = `"none"`) but
  `[profiles.X]` table exists in TOML → still `"deep_research"` (only
  the resolved/loaded active profile counts).

### JSON envelope shape

`set-default` success:

```json
{"default_mode": "deep_research", "wrote": true, "path": "/path/to/config.toml"}
```

With `--profile`:

```json
{"default_mode": "deep_research", "profile": "work", "wrote": true, "path": "..."}
```

Errors emit `{"error": "<CODE>", "message": "..."}` via
`emit_error`, matching existing modes/profiles error shapes.

## Out of scope

- New `thoth modes default` / `thoth modes show-default` inspector. The
  resolved value already surfaces via `--debug` config dumps and
  `thoth config show`; per-profile entries surface via
  `thoth config profiles list`.
- Deprecating `THOTH_DEFAULT_MODE`. Env retains its current
  highest-non-CLI slot.
- Changing the schema default `"default"` for `general.default_mode`.
- Auto-routing `--profile X` (without `--project`) to whichever tier
  defines profile X. Orthogonal flags only; users opt into project
  tier explicitly with `--project`.
- A `thoth profiles set-default` shorthand alias (the `config profiles`
  surface stays as-is).

## Risks and mitigations

- **Behavior change for users with `[profiles.X.default_mode]` already
  set.** None: today nothing reads that key, so users haven't been
  setting it. New behavior is purely additive on first set.
- **Env precedence change.** `THOTH_DEFAULT_MODE` keeps its current
  effective rank (highest non-CLI). The resolution refactor preserves
  that by reading env first inside `_config_default_mode`.
- **Validation false negatives** if a mode is added in one tier and
  set as default in another. Mitigated by validating against the
  union catalog scoped to the target tier (general vs profile X).
- **Same-tier rule causes friction for users** who expect partial
  cross-tier writes to "just work". Mitigated by error messages
  that include both fix paths (switch tier flag, or
  `thoth config profiles add X --project` first). The friction is
  intentional: it surfaces an ambiguous intent rather than silently
  picking one tier.
- **`unset-default` on a profile that doesn't exist.** Same as
  `unset-default` on a key that doesn't exist: `removed=False,
  reason="NOT_FOUND"`, exit 0. No profile-existence check on unset
  (writing nothing is harmless).

## Decisions log

| Question | Choice | Rationale |
|---|---|---|
| Write-only or also resolve? | Resolve (scope A) | Don't ship a key nothing reads. |
| Env vs profile precedence | Env beats profile | Mirrors `THOTH_PROFILE` beating `general.default_profile`. Scripts setting env keep working regardless of active profile. |
| Validation strictness | Validate against the resolvable set for the target tier | Prevents dangling defaults. Matches `profiles set-default`. |
| Profile-existence check on `set-default --profile X` | Yes | Symmetric with `profiles set-default` validating profile names. |
| Flag orthogonality (tier vs key path) | Orthogonal | Consistent with existing modes mutators (`add`/`set`/...). User opts into project tier explicitly. |
| Profile-existence check scope (set-default) | **Same-tier** — X must exist in the target file | Prevents partial cross-tier `[profiles.X]` entries that cause confusing merge behavior. Forces user to choose the right tier explicitly. |
| Same-tier rule on mode NAME? | No (β) | Modes are values resolved through the merged config; cross-tier mode resolution is normal. Builtins also count. |
| Same-tier rule on `unset-default`? | No (δ) | Unset is idempotent; missing file/table → silent `NOT_FOUND`/`NO_FILE`. Same-tier rule prevents creating dangling state, which delete cannot do. |

## Acceptance

- `thoth modes set-default NAME` writes `general.default_mode` to user
  config and is reflected in subsequent `thoth ask` invocations
  (resolution test).
- `thoth modes set-default NAME --profile X` writes
  `profiles.X.default_mode` and overrides the base when X is the
  active profile.
- `thoth modes unset-default` removes the key and leaves the
  surrounding table intact.
- All new commands appear in `thoth modes --help` and the
  `_MODES_EPILOG`.
- `make env-check`, `just check`, `just test-lint`,
  `just test-typecheck`, `pytest`, and `./thoth_test -r` all pass.
