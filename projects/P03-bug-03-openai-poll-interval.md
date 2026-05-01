# P03 — Fix BUG-03 OpenAI Poll Interval Scheduling (v2.5.1)

**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)

**Status:** `[x]` Completed (v2.5.1).

**Goal**: Make the background polling loop respect the configured poll cadence, including bounded jitter and sub-second intervals, while keeping the progress countdown aligned with the next real network poll.

**Out of Scope**
- BUG-02 (citation parsing), GAP-01 through GAP-05

### Tests & Tasks
- [x] [P03-TS01] Add virtual-time fixture tests for jittered and sub-second poll intervals
- [x] [P03-T01] Normalize poll interval math so jitter never truncates a 2s cadence into a 1s poll
- [x] [P03-T02] Schedule polling with absolute deadlines instead of a fixed 1s sleep cap
- [x] [P03-T03] Keep the progress countdown aligned with the next scheduled poll
- [x] [P03-TS02] Keep a mock-provider CLI regression for the end-to-end fixed polling loop
- [x] [P03-T04] Update OPENAI-BUGS.md and PROJECTS.md

### Automated Verification
- `make check` passes
- `./thoth_test -r -t BUG03 --skip-interactive` → 3/3 pass
- `./thoth_test -r -t OAI-BG --skip-interactive` → 14/14 pass

### Regression Test Status
- [x] BUG03-01 verifies -10% jitter still polls at 1.8s, not 1.0s
- [x] BUG03-02 verifies a 0.25s poll interval is honored exactly
- [x] BUG03-03 verifies the CLI still completes a mock-provider research run end to end
