# Project: Promote Admin Commands to Click Subcommands

**Status:** `[ ]` Not started — deferred from doxa-research-ergonomics-v1
**Created:** 2026-04-24
**Related spec:** `docs/superpowers/specs/2026-04-24-doxa-research-ergonomics-design.md` (§5)

## Goal

Promote the five administrative commands (`init`, `status`, `list`,
`providers`, `config`) from positional-argument pseudo-commands into real
Click subcommands. Today these live in the same positional slot as
research modes (`deep_research`, `clarification`, etc.), which makes the
CLI surface ambiguous and forces awkward separators like
`doxa-research providers -- --list`.

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
- Deprecating `doxa-research "prompt"` bare invocation — the default-mode
  shortcut continues to work

## Why defer

The current `doxa-research-ergonomics-v1` project targets documentation and
small code additions. A Click subgroup refactor touches `src/doxa_research/cli.py`,
`src/doxa_research/help.py`, `src/doxa_research/interactive.py`, every integration test
that shells out `doxa-research …`, the `doxa_test` fixture set, and all external
docs. It deserves its own TDD-first project with a staged rollout and a
deprecation window.

## Tests & Tasks (draft — finalize at project kickoff)

- [ ] [P##-TS01] Snapshot test of `doxa-research --help` after refactor: admin
      commands listed in a dedicated section, research modes in another
- [ ] [P##-TS02] Click `CliRunner` tests: each of `init`, `status`,
      `list`, `providers`, `config` invoked as a subcommand returns
      exit 0 and expected output
- [ ] [P##-TS03] Backwards-compat: old positional form
      `doxa-research init` / `doxa-research status OP_ID` / etc. continues to work and
      emits a one-line deprecation notice to stderr for exactly one
      release
- [ ] [P##-TS04] `./doxa_test -r` full suite green
- [ ] [P##-TS05] `doxa-research providers -- --list` compatibility shim from
      ergonomics-v1 is still honored (or superseded gracefully)
- [ ] [P##-T01] Add `@click.group()` to top-level `doxa-research` command in
      `src/doxa_research/cli.py`; keep positional-prompt fallback for research modes
- [ ] [P##-T02] Move `init`/`status`/`list`/`providers`/`config` into
      `@cli.command()` definitions; route through existing handlers in
      `src/doxa_research/commands.py`
- [ ] [P##-T03] Update `src/doxa_research/help.py` renderers for the new structure
- [ ] [P##-T04] Update `src/doxa_research/interactive.py` slash-commands if any
      reference the old positional dispatch
- [ ] [P##-T05] Update `./doxa_test` cases and fixtures for new
      invocations
- [ ] [P##-T06] Update `README.md`, `manual_testing_instructions.md`,
      `planning/doxa-research.prd.v24.md` (or its successor), and `CHANGELOG.md`
- [ ] [P##-T07] Deprecation notice infrastructure: one-release warning
      when users invoke the old positional form
- [ ] [P##-T08] Remove deprecation shim (scheduled for N+1 release)

## Open design questions

1. Does `doxa-research --resume OP_ID` stay as a global flag, become
   `doxa-research resume OP_ID`, or both?
2. ~~Do we want nested subcommand groups (e.g., `doxa-research config get/set/edit`,
   `doxa-research providers list/models/check`) or flat subcommands?~~
   **Resolved 2026-04-25:** Flat subcommands, matching the existing
   `config`/`modes` positional-op precedent in `config_cmd.py` and
   `modes_cmd.py`. No nested groups.
3. Shell-completion story for the new surface — does Click's built-in
   `_DOXA_COMPLETE` work once we have a group?

## Acceptance criteria

- Every admin command is dispatched via a Click subcommand
- `doxa-research --help` clearly separates admin commands from research modes
- All prior invocation forms work for one release with a deprecation notice
- Test suite and doxa_test fully green
- CHANGELOG documents the new surface and the deprecation timeline
