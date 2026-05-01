# P06 — Hybrid Transient/Permanent Error Handling with Resumable Recovery (v2.7.0)

**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)

**Status:** `[x]` Completed (v2.7.0).

**Goal**: Classify provider errors as transient vs permanent, retry transient ones in-place with bounded backoff, and make recoverable failures (and Ctrl-C) resumable via `thoth --resume <id>` by reconnecting to persisted job IDs.

**Out of Scope**
- Checkpoint schema migration (backward-compat handled via `setdefault("failure_type", None)`)
- Perplexity / Gemini providers (still not implemented)
- Decorrelated-jitter backoff (simple exponential backoff is sufficient)

### Tests & Tasks
- [x] [P06-T01] Extend MockProvider with THOTH_MOCK_BEHAVIOR env (flake:N, permanent)
- [x] [P06-T02] Add `OperationStatus.failure_type` + checkpoint serialization
- [x] [P06-T03] Allow failed → running state transition so resume can re-enter
- [x] [P06-T04] Classify errors in `OpenAIProvider.check_status` (transient vs permanent)
- [x] [P06-T05] Add `max_transient_errors` config default
- [x] [P06-T06] Extract `_run_polling_loop` helper shared by run and resume
- [x] [P06-T07] Add retry loop + exponential backoff for transient errors
- [x] [P06-T08] Add `OpenAIProvider.reconnect` + `MockProvider.reconnect`
- [x] [P06-T09] Implement `resume_operation` to rebuild providers and re-enter poll loop
- [x] [P06-T10] Surface "Resume with: thoth --resume <id>" hint on recoverable failure and SIGINT
- [x] [P06-TS01] TR-01: transient errors below threshold retried and job completes
- [x] [P06-TS02] TR-02: transient errors above threshold fail recoverable with resume hint
- [x] [P06-TS03] TR-03: permanent error fails immediately with no resume hint
- [x] [P06-TS04] RES-01: resume recoverable failure reattaches and completes
- [x] [P06-TS05] RES-02: resume refuses permanent failure with exit code 7
- [x] [P06-TS06] RES-03: resume of already-completed operation is a no-op

### Automated Verification
- `make env-check` passes
- `just lint` / `just typecheck` pass
- `just test-lint` / `just test-typecheck` pass
- `./thoth_test -r` → 124 passed, 1 skipped, 0 failed

### Regression Test Status
- [x] OAI-BG-01..08 updated for new `permanent_error` / `transient_error` return values
- [x] Existing BUG-03 jitter/poll-interval fixture tests still pass (share module globals)
- [x] P07 async-mode tests still pass (async path now actually submits to providers)
