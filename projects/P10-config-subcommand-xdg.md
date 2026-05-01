# P10 — Config Subcommand + XDG Layout (v2.10.0)

**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)

**Status:** `[x]` Completed (v2.10.0).

**Goal**: Add `thoth config` subcommand (get/set/unset/list/path/edit/help) and migrate all user-writable paths to XDG Base Directory Spec. No legacy-path migration.

> **Note:** P10 predates the TS/T split convention; tests landed inline with each T task (see P10-T02 "with TDD" and P10-T11 verification step).

### Tests & Tasks
- [x] [P10-T01] Add tomlkit dependency
- [x] [P10-T02] XDG path helpers in src/thoth/paths.py with TDD
- [x] [P10-T03] Migrate all platformdirs callsites to paths.py
- [x] [P10-T04] config_cmd.py scaffold + get op
- [x] [P10-T05] set op with tomlkit round-trip (comment-preserving)
- [x] [P10-T06] unset op with empty-table pruning
- [x] [P10-T07] list + path ops
- [x] [P10-T08] Secrets masking on get and list (api_key, --show-secrets opt-in)
- [x] [P10-T09] edit + help ops
- [x] [P10-T10] Wire config into CLI dispatch and help system
- [x] [P10-T11] Final verification (lint, typecheck, full pytest suite, thoth_test -r)

### Automated Verification
- `just check` passes
- `uv run pytest tests/` passes
- `./thoth_test -r` passes
- API key values masked by default in `thoth config get/list` output
