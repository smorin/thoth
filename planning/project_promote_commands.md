# Project: Promote Admin Commands to Click Subcommands

**Status:** `[ ]` Not started — deferred from thoth-ergonomics-v1
**Created:** 2026-04-24
**Related spec:** `docs/superpowers/specs/2026-04-24-thoth-ergonomics-design.md` (§5)

## Goal

Promote the five administrative commands (`init`, `status`, `list`,
`providers`, `config`) from positional-argument pseudo-commands into real
Click subcommands. Today these live in the same positional slot as
research modes (`deep_research`, `clarification`, etc.), which makes the
CLI surface ambiguous and forces awkward separators like
`thoth providers -- --list`.

After this project, the split is unambiguous:

- **Administrative subcommands** (dispatched by Click group): `init`,
  `status`, `list`, `providers`, `config`, `modes`, `help`
- **Research modes** (positional first argument): `default`, `clarification`,
  `exploration`, `deep_dive`, `tutorial`, `solution`, `prd`, `tdd`,
  `thinking`, `deep_research`, `mini_research`, `comparison`

## Out of scope

- Renaming any mode
- Changing behavior of any existing command
- Breaking the `--resume`, `--async`, `--project`, `--auto`, `--input-file`
  global flags (those stay on the top-level group)
- Deprecating `thoth "prompt"` bare invocation — the default-mode
  shortcut continues to work

## Why defer

The current `thoth-ergonomics-v1` project targets documentation and
small code additions. A Click subgroup refactor touches `src/thoth/cli.py`,
`src/thoth/help.py`, `src/thoth/interactive.py`, every integration test
that shells out `thoth …`, the `thoth_test` fixture set, and all external
docs. It deserves its own TDD-first project with a staged rollout and a
deprecation window.

## Tests & Tasks (draft — finalize at project kickoff)

- [ ] [P##-TS01] Snapshot test of `thoth --help` after refactor: admin
      commands listed in a dedicated section, research modes in another
- [ ] [P##-TS02] Click `CliRunner` tests: each of `init`, `status`,
      `list`, `providers`, `config` invoked as a subcommand returns
      exit 0 and expected output
- [ ] [P##-TS03] Backwards-compat: old positional form
      `thoth init` / `thoth status OP_ID` / etc. continues to work and
      emits a one-line deprecation notice to stderr for exactly one
      release
- [ ] [P##-TS04] `./thoth_test -r` full suite green
- [ ] [P##-TS05] `thoth providers -- --list` compatibility shim from
      ergonomics-v1 is still honored (or superseded gracefully)
- [ ] [P##-T01] Add `@click.group()` to top-level `thoth` command in
      `src/thoth/cli.py`; keep positional-prompt fallback for research modes
- [ ] [P##-T02] Move `init`/`status`/`list`/`providers`/`config` into
      `@cli.command()` definitions; route through existing handlers in
      `src/thoth/commands.py`
- [ ] [P##-T03] Update `src/thoth/help.py` renderers for the new structure
- [ ] [P##-T04] Update `src/thoth/interactive.py` slash-commands if any
      reference the old positional dispatch
- [ ] [P##-T05] Update `./thoth_test` cases and fixtures for new
      invocations
- [ ] [P##-T06] Update `README.md`, `manual_testing_instructions.md`,
      `planning/thoth.prd.v24.md` (or its successor), and `CHANGELOG.md`
- [ ] [P##-T07] Deprecation notice infrastructure: one-release warning
      when users invoke the old positional form
- [ ] [P##-T08] Remove deprecation shim (scheduled for N+1 release)

## Open design questions

1. Does `thoth --resume OP_ID` stay as a global flag, become
   `thoth resume OP_ID`, or both?
2. ~~Do we want nested subcommand groups (e.g., `thoth config get/set/edit`,
   `thoth providers list/models/check`) or flat subcommands?~~
   **Resolved 2026-04-25:** Flat subcommands, matching the existing
   `config`/`modes` positional-op precedent in `config_cmd.py` and
   `modes_cmd.py`. No nested groups.
3. Shell-completion story for the new surface — does Click's built-in
   `_THOTH_COMPLETE` work once we have a group?

## Acceptance criteria

- Every admin command is dispatched via a Click subcommand
- `thoth --help` clearly separates admin commands from research modes
- All prior invocation forms work for one release with a deprecation notice
- Test suite and thoth_test fully green
- CHANGELOG documents the new surface and the deprecation timeline
