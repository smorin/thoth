# Design — Config Filename Standardization (P21c)

**Status:** Draft for review (decisions locked 2026-04-28; ready for plan)
**Created:** 2026-04-28
**Project ID:** P21c
**Target version:** v3.2.0 (land before P21 implementation if possible — see §7)
**Tracking:** `PROJECTS.md` § "Project P21c: Config Filename Standardization"
**Related:** P21 (`docs/superpowers/specs/2026-04-28-p21-configuration-profiles-design.md`), P21b (`docs/superpowers/specs/2026-04-28-p21b-configuration-profiles-crud-design.md`)

---

## 1. Goal

Standardize the Thoth config filename to **`thoth.config.toml`**. There is **one** user-tier location and **two** project-tier locations (mutually exclusive). The filename alone uniquely identifies a Thoth config file regardless of where it lives.

| Tier | Today | After P21c |
|---|---|---|
| User (XDG) | `$XDG_CONFIG_HOME/thoth/config.toml` | `$XDG_CONFIG_HOME/thoth/thoth.config.toml` |
| Project — visible | `./thoth.toml` | `./thoth.config.toml` |
| Project — hidden | `./.thoth/config.toml` (dir form) | `./.thoth.config.toml` (dotfile form) |

**No legacy fallback.** The old filenames stop being read entirely. Users with existing config files must rename them.

**Both project-tier files present → hard error.** Thoth refuses to choose; the user must delete one. There is no precedence rule between `./thoth.config.toml` and `./.thoth.config.toml`.

## 2. Motivation

Thoth currently uses three different filenames depending on where the file lives:

- `config.toml` (user XDG dir) — generic, only meaningful because of the surrounding `thoth/` directory.
- `thoth.toml` (project root) — specific, but a different name from the user file.
- `config.toml` again (project `.thoth/` dir) — same as the user file, but ambiguous when seen out of context.

This creates friction:

- **Identification.** A user opening `~/.config/thoth/config.toml` in an editor sees a tab labeled `config.toml` with no provenance. A `thoth.config.toml` tab is unambiguous.
- **Search.** `grep -r thoth.config.toml .` locates every Thoth config; today there is no single filename that works.
- **Documentation.** README, help text, manual-testing notes, and error messages all have to qualify which config file they mean. One filename collapses that.
- **Mental model.** Users have to remember three names and which goes where. One name removes the rule.

The trade-off is a mildly redundant XDG path (`thoth/thoth.config.toml`). That redundancy is the *intended* cost of "filename identifies it" — it is not accidental.

## 3. Decisions

### Q1. What is the canonical filename? *(locked)*

`thoth.config.toml`. Rationale:

- `thoth.` prefix → unambiguous tool identification regardless of directory.
- `.config.` infix → matches the existing convention shared by tools like `vite.config.ts`, `prettier.config.js`, where `<tool>.config.<ext>` reads as "the config for this tool."
- `.toml` suffix → unchanged file format.

### Q2. Backwards compatibility? *(locked — none)*

No legacy fallback. The loader does **not** read `~/.config/thoth/config.toml`, `./thoth.toml`, or `./.thoth/config.toml`. After P21c lands, those files are inert.

When no canonical config is found, Thoth raises a clear "config not found" error. **As a UX courtesy** (not a fallback), the error message *checks for* legacy filenames at the same paths and, if any are present, names them in the suggestion text:

```text
No Thoth config found.
  Looked for: ~/.config/thoth/thoth.config.toml
              ./thoth.config.toml
              ./.thoth.config.toml

  Detected legacy file: ./thoth.toml
  This filename is no longer read. Rename it to ./thoth.config.toml or ./.thoth.config.toml.
```

The detection is purely informational. It runs only on the "config not found" path; it does not load the legacy file or fire on the happy path.

### Q3. How are the two project-tier filenames resolved? *(locked — error on ambiguity)*

`./thoth.config.toml` and `./.thoth.config.toml` are equally acceptable. There is **no precedence**. If both exist in the same project root, Thoth raises `ConfigAmbiguousError` and asks the user to delete one:

```text
Two Thoth config files found in the project root:
  ./thoth.config.toml
  ./.thoth.config.toml

Delete one before continuing. They are not merged and Thoth will not pick between them.
```

Rationale: precedence in this case is arbitrary (no semantic difference between visible and dotfile forms), and silently picking one is worse than refusing — a user who edits the "wrong" one would never see their changes apply.

The check fires whenever Thoth resolves a project config path: at config load and at any CLI command that resolves the project file (e.g. mutator `config` leaves and `init`).

### Q4. Does this change `init`? *(locked — yes, both forms)*

Yes:

- `thoth init` (project) writes `./thoth.config.toml` by default. A flag to write the dotfile form (`./.thoth.config.toml`) instead is included — see §4.3 for the exact spelling.
- `thoth init --user` writes `$XDG_CONFIG_HOME/thoth/thoth.config.toml`. This is in scope (P21c-T04).
- `init` refuses to overwrite an existing canonical file unless `--force` is passed (existing `init` behavior; documented here only for completeness).
- `init` does **not** auto-rename legacy files. If the user has `./thoth.toml` and runs `thoth init`, the new file is written alongside; the next `thoth` invocation hits the §3 Q3 ambiguity case (legacy file ignored, canonical loaded — see §3 Q2: legacy detection is informational only and does not block load when canonical is present). The "Detected legacy file" notice still appears in any error path.

### Q5. Does this affect the `[profiles.<name>]` overlay? *(locked — no)*

P21 lives entirely *inside* whichever config file is loaded. The filename change is orthogonal to P21's selection/overlay logic. The only intersection is that P21 spec strings, error messages, and tests refer to the legacy filenames; those references are updated in P21c as part of the docs sweep.

## 4. Architecture

### 4.1 `src/thoth/paths.py`

```python
def user_config_file() -> Path:
    return user_config_dir() / "thoth.config.toml"
```

The legacy `legacy_user_config_file()` helper proposed in the earlier draft is **not** added. Legacy detection lives in the error-path helper (§4.4), not in `paths.py`.

### 4.2 `src/thoth/config.py`

`ConfigManager.__init__`:

```python
self.project_config_paths = [
    "./thoth.config.toml",
    "./.thoth.config.toml",
]
```

`_load_project_config_with_path()`:

1. Find which of the two canonical paths exist.
2. If both → raise `ConfigAmbiguousError` (see §4.5).
3. If exactly one → load it and return `(data, path)`.
4. If neither → return `({}, None)` (project config is optional, same as today).

User-tier loading: load `user_config_file()` if it exists; if not, treat as missing (no fallback). The "config not found" error handler runs the legacy detector and embellishes the message.

### 4.3 `thoth init`

- `thoth init` → writes `./thoth.config.toml`.
- `thoth init --hidden` (or `--dotfile` — final spelling decided in plan) → writes `./.thoth.config.toml` instead.
- `thoth init --user` → writes `$XDG_CONFIG_HOME/thoth/thoth.config.toml`.
- `--user` and `--hidden` are mutually exclusive.
- All three respect existing `--force` overwrite semantics.

The exact flag name (`--hidden` vs `--dotfile` vs `--dot`) is a small open question for the plan; the *capability* is locked.

### 4.4 Legacy detection helper (informational only)

A small helper centralizes legacy-file detection so the error path is the *only* place that knows about legacy names:

```python
LEGACY_USER_PATH = user_config_dir() / "config.toml"
LEGACY_PROJECT_PATHS = ("./thoth.toml", "./.thoth/config.toml")

def detect_legacy_paths() -> list[Path]:
    """Return any legacy Thoth config files that exist on disk.
    Used to enrich 'config not found' error messages — never to load.
    """
    ...
```

Called only from the "no config found" error formatter. Never invoked on the happy path. Tests assert that successful loads do not call it.

### 4.5 Errors

`src/thoth/errors.py` adds two error classes:

- `ConfigNotFoundError(ThothError)` — raised when config is required but no canonical file exists. Message includes the canonical paths Thoth looked at and any detected legacy files (§3 Q2 wording).
- `ConfigAmbiguousError(ThothError)` — raised when both `./thoth.config.toml` and `./.thoth.config.toml` exist (§3 Q3 wording).

`ConfigProfileError` from P21 is unchanged.

### 4.6 Help text and CLI strings audit

Every literal string in code that names a config path is audited and updated:

- `src/thoth/help.py` — `thoth help config`, init help, etc.
- `src/thoth/cli_subcommands/config.py` — leaf help text.
- `src/thoth/errors.py` — error formatting.
- Any other `*.py` file containing `config.toml`, `thoth.toml`, or `.thoth/`.

## 5. Documentation

P21c updates:

- `README.md` — config section, install/setup walkthrough, migration note for users on legacy filenames.
- `manual_testing_instructions.md` — every smoke test that references a config path.
- `CLAUDE.md` and `AGENTS.md` — audited and updated if either names a config file.
- P21 spec/plan (`docs/superpowers/specs/2026-04-28-p21-configuration-profiles-design.md`, `docs/superpowers/plans/2026-04-28-p21-configuration-profiles.md`) — updated to canonical names *or* annotated with a "see P21c" pointer; choice depends on §7 sequencing.
- P21b spec/plan — same treatment.
- Any `planning/` doc that names config paths.

The migration note in README is short:

> **Migrating from earlier Thoth versions.** Rename `~/.config/thoth/config.toml` → `~/.config/thoth/thoth.config.toml`, `./thoth.toml` → `./thoth.config.toml` (or `./.thoth.config.toml`), and `./.thoth/config.toml` → `./.thoth.config.toml`. Thoth no longer reads the old filenames.

## 6. Out of Scope

- A `thoth config migrate` CLI command that renames files in place. (Could be a future project if the rename instruction proves insufficient.)
- A "deprecation window" or fallback read of legacy filenames. Decided against; clean break.
- Changing the file format (still TOML).
- Changing the *structure* inside the file.
- Changing the project marker semantics (presence of either canonical project path still means "this is a Thoth project").
- Adding a `THOTH_CONFIG_FILENAME` env var to override the filename.
- Picking precedence between `./thoth.config.toml` and `./.thoth.config.toml`. There is no precedence; both present → error.
- A directory-form project config (e.g. `./.thoth/thoth.config.toml`). The `.thoth/` directory pattern is retired for config purposes.

## 7. Sequencing

P21c interacts with P21 and P21b because both reference the legacy filenames in specs, plans, tests, and error messages. Three viable orderings:

1. **P21c → P21 → P21b** *(preferred)*. P21c lands first while P21 is still in planning; P21's spec/plan/tests are written against the new names from the start.
2. **P21 → P21c → P21b**. P21 ships with legacy names; P21c follows and sweeps P21's tests/strings; P21b is then written against the new names. Cost: extra churn.
3. **P21 → P21b → P21c**. Both ship on legacy names; P21c does one big rename sweep. Cost: largest sweep.

Option 1 is recommended unless P21 is already mid-implementation when P21c is approved.

## 8. Acceptance Criteria

- `thoth.config.toml` is read from all three canonical locations: user XDG, project root, and project dotfile form.
- Legacy filenames (`config.toml` in user dir, `thoth.toml`, `.thoth/config.toml`) are **not** read.
- When no canonical config is found and a legacy file exists at one of the legacy paths, the "config not found" error names the detected legacy file(s) and the rename target.
- When both `./thoth.config.toml` and `./.thoth.config.toml` exist in the project root, Thoth raises `ConfigAmbiguousError` and asks the user to delete one. No precedence is applied.
- `thoth init` writes `./thoth.config.toml`. The dotfile-form flag writes `./.thoth.config.toml`. `thoth init --user` writes `$XDG_CONFIG_HOME/thoth/thoth.config.toml`. `--user` and the dotfile-form flag are mutually exclusive.
- README, manual_testing_instructions, help text, error messages, and P21/P21b spec/plan docs all reference `thoth.config.toml`.
- Successful config loads do **not** call the legacy detection helper (regression guard for inadvertent fallback).
- `git diff --check`, `just check`, `./thoth_test -r --skip-interactive -q`, `just test-lint`, `just test-typecheck` all pass.

## 9. Open Questions

Small items for the plan, not blockers for approval:

1. **Dotfile-form `init` flag spelling** — `--hidden`, `--dotfile`, or `--dot`? Recommendation: `--hidden` (most discoverable in `--help`).
2. **`init --user --force`** semantics — confirm `--force` overwrite applies to the user-tier file too, not just the project file.
3. **Test fixture file layout** — existing tests use `tmp_path` heavily; confirm the new ambiguity test can reuse those fixtures without restructuring.
