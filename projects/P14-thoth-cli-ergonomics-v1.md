# P14 — Thoth CLI Ergonomics v1 (v2.13.0)

**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)

**Status:** `[x]` Completed (v2.13.0).

**Goal**: Reduce first-time-user friction in the thoth CLI.

> **Note:** P14 predates the TS/T split convention; tests landed inline with each T task — see `tests/test_cli_help.py`, `tests/test_pick_model.py`, etc.

### Tests & Tasks
- [x] [P14-T01] format_config_context helper + tests
- [x] [P14-T02] APIKeyError surfaces config file path
- [x] [P14-T03] --input-file/--auto clearer help
- [x] [P14-T04] Workflow chain + worked examples in --help epilog
- [x] [P14-T05] thoth help auth + README authentication ordering pass
- [x] [P14-T06] providers list/models/check subcommands + deprecation shim
- [x] [P14-T07] thothspinner dependency
- [x] [P14-T08] Progress spinner module + gate
- [x] [P14-T09] Wire spinner into run.py polling
- [x] [P14-T10] SIGINT Resume-later hint
- [x] [P14-T11] --pick-model rejection on background modes
- [x] [P14-T12] --pick-model interactive picker for immediate modes
