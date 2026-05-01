# P02 — Fix BUG-01 OpenAI Background Status Handling (v2.5.0)

**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)

**Status:** `[x]` Completed (v2.5.0).

**Goal**: Correctly handle all documented OpenAI Responses API background lifecycle states (`incomplete`, `cancelled`, `queued`, no-status-attr, stale-cache) so the CLI never silently misreports terminal failure states as success.

**Out of Scope**
- BUG-02 (citation parsing), GAP-01 through GAP-05

### Tests & Tasks
- [x] [P02-T01] Add `"fixture"` test_type dispatch + helpers to `thoth_test`
- [x] [P02-TS01] Add OAI-BG-01–08 fixture tests for `check_status()` (queued, failed, incomplete, cancelled, no-status-attr, stale-cache, good-cache, in_progress regression)
- [x] [P02-T02] Fix `check_status()` in `OpenAIProvider` — explicit branches for all 6 API statuses, fixed no-status-attr and stale-cache paths
- [x] [P02-TS02] Add OAI-BG-09–14 polling loop fixture tests (queued no premature exit, failed/cancelled/error propagate, not_found/unknown normalize to error)
- [x] [P02-T03] Fix polling loop in `_execute_research()` — queued keeps polling, terminal failures propagate
- [x] [P02-T04] Update OPENAI-BUGS.md (BUG-01 status → Fixed) and PROJECTS.md

### Automated Verification
- `make check` passes
- `./thoth_test -r -t OAI-BG --skip-interactive` → 14/14 pass
- `./thoth_test -r --provider mock --skip-interactive` → 67 passed, 0 failed

### Regression Test Status
- [x] All 14 OAI-BG fixture tests pass
