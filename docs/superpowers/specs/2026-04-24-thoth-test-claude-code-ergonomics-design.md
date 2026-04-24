# Design: thoth_test Claude-Code Ergonomics Bundle

**Date:** 2026-04-24
**Owner:** Steve Morin
**Status:** Draft — awaiting user review
**Scope:** `thoth_test` only (the uv-shebang integration runner at repo root). No changes to `./thoth` executable or pytest suite under `tests/`.

## Motivation

`thoth_test` is driven both by humans and by Claude Code (and CI hooks that invoke it on Claude Code's behalf). The human ergonomics are good; the automation ergonomics force shell-scraping workarounds that are already documented in `CLAUDE.md`:

- Grep `Failed Test Details` to skip a 64-row Rich table.
- "Two consecutive failures = real bug" as a manual flaky-retry policy.
- `-t M8T-03` substring-matches on `test_id` and `description` — fine for humans, ambiguous for automation.
- Per-failure rerun hint emits one line per ID — impossible to run multiple failures in one invocation.

Each workaround is a bug that lives in prose. This spec promotes them into features.

## Goals

1. Give automation (Claude Code, hooks, CI) **stable, machine-readable output** that does not require colour-stripping or table-parsing.
2. Give automation **precise selectors** that don't depend on substring ambiguity.
3. Collapse the "rerun what just failed" loop from a multi-step shell pipeline into one flag.
4. Keep the human UX unchanged unless a new flag is passed.

## Non-Goals

- No parallel execution (`-n auto`-style). Out of scope; revisit after this bundle lands.
- No JUnit XML. The JSON report subsumes most consumers; JUnit can be layered on later without re-designing the core.
- No tagging system (`--tag fast`, `--tag network`). Deferred; depends on touching every `TestCase` and is a separate refactor.
- No behaviour change to existing `TestCase` definitions in `all_tests`.
- No change to the `./thoth` CLI, to pytest tests, or to lefthook pre-commit configuration.

## Out-of-Scope Items (explicitly dropped from earlier brainstorm)

From the original 9-item brainstorm, the following are **not** in this spec:
- #6 flaky-retry policy in runner
- #7 tag-based slicing
- #9 items except where they fall out naturally (`--no-progress` appears because `-q` implies it)

Land this bundle first, then revisit.

---

## User-Facing Surface

### New flags

| Flag | Shape | Default | Purpose |
|------|-------|---------|---------|
| `--report-json PATH` | option | (off) | Write an additional JSON report to `PATH`. The cache file at `.thoth_test_cache/last_run.json` is always written regardless. |
| `--list` | flag | off | Print TSV list of tests without running them; `-r` not required. |
| `--list-json` | flag | off | Same as `--list` but JSON array on stdout. |
| `--id ID` | option, repeatable | (empty) | Exact-match test IDs to run. Overrides `-t`, `--provider`, `--interactive`, `--skip-interactive` for selection. |
| `--last-failed` | flag | off | Rerun only tests that failed in the most recent run (reads `.thoth_test_cache/last_run.json`). Implies `-r`. |
| `-q` / `--quiet` | flag | off | Suppress progress bar, table, and passing-test noise. On failure, emit fenced diagnostic blocks. |

### Flag interaction rules

- `--id` **overrides** other selectors. If `--id M8T-03 --provider openai` is given and `M8T-03` is not an openai test, `M8T-03` still runs; a warning is printed (stderr) and `requested_but_filtered` is set in the JSON report.
- `--id` against an unknown ID: warn on stderr (`Warning: --id X not found, ignoring`), do not abort.
- `--last-failed` with no cache file or empty prior failures: exit `2` with stderr message `No prior failures to rerun (.thoth_test_cache/last_run.json missing or empty)`. This distinguishes it from exit `1` (real failures) and exit `0` (success).
- `--last-failed` composes with `--id` by **union**: "these specific IDs plus whatever failed last time." Rare but useful during debugging.
- `-q` suppresses the Rich progress bar and the final results table but does not suppress the fenced failure blocks or the final summary line.
- `--list` and `--list-json` are mutually exclusive; if both set, exit `2` with message.
- `--list` / `--list-json` **do** respect `-t`, `--provider`, `--id`, `--interactive`, `--skip-interactive` so a user can preview what a filter would select. They **do not** respect `--last-failed` (previewing rerun candidates is a separate concern; not in scope).
- `--list` / `--list-json` preempt `-r`. If both are given, listing happens and the runner does not execute.

### Unchanged flags

All existing flags keep current semantics: `-r`, `-a`, `-v`, `-t`, `-p`/`--provider`, `--all-providers`, `--interactive`, `--skip-interactive`, `--no-cleanup`, `--save-output`.

---

## Data Contract: `.thoth_test_cache/last_run.json`

```json
{
  "schema_version": 1,
  "started_at": "2026-04-24T14:32:10Z",
  "finished_at": "2026-04-24T14:33:07Z",
  "duration_total_seconds": 57.3,
  "thoth_test_version": "git:sha",
  "invocation": ["./thoth_test", "-r", "--provider", "mock"],
  "requested_providers": ["mock"],
  "counts": {
    "total": 64,
    "passed": 60,
    "failed": 2,
    "skipped": 2,
    "api_key_failures": 0
  },
  "tests": [
    {
      "test_id": "M1T-01",
      "description": "Verify --version displays version",
      "provider": null,
      "test_type": "subprocess",
      "passed": true,
      "skipped": false,
      "duration_seconds": 0.12,
      "exit_code": 0,
      "error_message": null,
      "is_api_key_failure": false,
      "requested_but_filtered": false,
      "stdout": null,
      "stderr": null
    },
    {
      "test_id": "M8T-03",
      "description": "Interactive mode cancels on Ctrl+C",
      "provider": "mock",
      "test_type": "interactive",
      "passed": false,
      "skipped": false,
      "duration_seconds": 3.41,
      "exit_code": 1,
      "error_message": "Pattern not found: Cancelled",
      "is_api_key_failure": false,
      "requested_but_filtered": false,
      "stdout": "... full stdout ...",
      "stderr": "... full stderr ..."
    }
  ]
}
```

### Schema rules

- `schema_version: 1` is the current contract. Future changes bump this and downstream consumers can branch.
- `stdout` and `stderr` are `null` for passing and skipped tests, **full untruncated strings** for failed tests.
- `provider: null` means provider-agnostic (matches today's `tc.provider or "none"` but uses real `null`).
- `invocation` records `sys.argv` for debugging — especially helpful for reproducing a CI failure locally.
- `requested_but_filtered: true` means the test was explicitly requested via `--id` despite not matching other filters. Lets downstream tooling surface the mismatch.
- Timestamps are UTC ISO-8601 with `Z` suffix.
- The file is written **atomically** (write to `.thoth_test_cache/last_run.json.tmp`, then `os.replace`). Partial writes from an interrupted run must not corrupt the next `--last-failed`.

### Cache directory

- `.thoth_test_cache/` at repo root.
- Must be added to `.gitignore` as part of this change.
- Directory created lazily on first run.
- No automatic pruning — one file, overwritten each run.

---

## Console Output Changes

### Default mode (no new flags)

Unchanged from today. The Rich progress bar, table, failure details, and rerun hint behave identically. A cache file is written silently at the end; no log line announces it (users don't need to know unless they ask).

### `-q` / `--quiet` mode

- **During run:** no progress bar, no per-test prints, no table.
- **On failure:** each failed test emits a fenced block to stdout:

  ```
  ===BEGIN FAILURE M8T-03===
  Test: M8T-03 — Interactive mode cancels on Ctrl+C
  Duration: 3.41s
  Exit code: 1
  Error: Pattern not found: Cancelled
  --- STDOUT ---
  <full untruncated stdout>
  --- STDERR ---
  <full untruncated stderr>
  ===END FAILURE M8T-03===
  ```

- **At end:** one summary line:

  ```
  thoth_test: 60 passed, 2 failed, 2 skipped in 57.3s (cache: .thoth_test_cache/last_run.json)
  ```

- Exit code: `0` on all-pass, `1` on any failure, `2` on infrastructure/usage errors.

### Fenced sentinel format

- Start: `===BEGIN FAILURE <test_id>===`
- End: `===END FAILURE <test_id>===`
- Both are their own lines, with no leading/trailing whitespace, no Rich markup.
- Rationale: trivially greppable; `awk '/===BEGIN FAILURE M8T-03===/,/===END FAILURE M8T-03===/'` extracts exactly one test's failure block without arbitrary line windows.

### `--list` output

TSV (tab-separated), one test per line, no header:

```
M1T-01	none	subprocess	Verify --version displays version
M1T-02	mock	subprocess	Quick mode with mock provider creates output file
M8T-03	mock	interactive	Interactive mode cancels on Ctrl+C
```

Columns: `test_id`, `provider` (or `none`), `test_type`, `description`.

### `--list-json` output

```json
[
  {"test_id": "M1T-01", "provider": null, "test_type": "subprocess", "description": "Verify --version displays version", "is_interactive": false},
  {"test_id": "M1T-02", "provider": "mock", "test_type": "subprocess", "description": "Quick mode with mock provider creates output file", "is_interactive": false}
]
```

---

## Implementation Architecture

### Code organization within `thoth_test`

Keep the single-file uv-shebang structure. Add these sections (near existing ones):

1. **New serializer**: `fn serialize_run_report(runner: TestRunner) -> dict` near `generate_report`.
2. **New cache writer**: `fn write_cache(report: dict, path: Path = CACHE_PATH)` — atomic write.
3. **New cache reader**: `fn read_last_failed(path: Path = CACHE_PATH) -> list[str]` — returns list of failed test_ids or raises `FileNotFoundError` / `ValueError`.
4. **New list printers**: `fn print_list_tsv(tests: list[TestCase])` and `fn print_list_json(tests: list[TestCase])`.
5. **New fenced-block printer**: `fn print_fenced_failure(result: TestResult, test_case: TestCase)`.
6. **New selection resolver**: `fn resolve_selection(flags) -> list[TestCase]` encapsulates all filter composition logic (today this is inline in `main()`).

### Where each flag plugs in

| Flag | Hook point |
|------|------------|
| `--list` / `--list-json` | Early in `main()`: after selection resolver, before `TestRunner` instantiation; print and exit `0`. |
| `--id` | Inside selection resolver; overrides other filters as per rules. |
| `--last-failed` | Inside selection resolver; reads cache, returns list of IDs, delegates to same path as `--id`. |
| `--report-json PATH` | After `generate_report`, serialize report and write to `PATH` (on top of the always-on cache write). |
| `-q` / `--quiet` | A runner mode flag; `TestRunner.__init__` takes `quiet: bool`. `run_all_tests` skips `Progress`; `generate_report` branches to quiet emission. |

### Minimal changes to existing code

- `TestResult`: no new fields. Everything needed for the JSON is already there or derivable from the matching `TestCase`.
- `TestCase`: no new fields. `provider or "none"` becomes `provider` (kept as `None` in serialization).
- `main()`: refactored to delegate filter composition to the new resolver. Keeps backwards compatibility.

---

## Testing Strategy (TDD-First)

Per `CLAUDE.md`, tests come first. Because `thoth_test` is both the runner and (historically) not self-tested in pytest, we add pytest coverage under `tests/test_thoth_test_cli.py` that imports helpers from the shebang script via the existing `sys.path.insert(src)` pattern, or — if easier — factors the pure-Python helpers into a small `src/thoth_test_support.py` module that the shebang imports. **Preferred: keep everything in the shebang, add pytest tests that subprocess-invoke `./thoth_test`** to match the existing black-box convention.

### Test matrix

1. **`--list` output shape**
   - `./thoth_test --list` exits 0, emits ≥1 TSV line, each line has exactly 3 tabs.
   - `./thoth_test --list-json` exits 0, emits valid JSON array, each element has the required keys.
   - Both are silent (no spinner, no table), regardless of whether `-r` is passed.

2. **`--id` exact match**
   - `./thoth_test -r --id M1T-01` runs exactly one test; JSON cache has one entry.
   - `./thoth_test -r --id M1T-01 --id M1T-04` runs exactly two tests.
   - `./thoth_test -r --id NONEXISTENT` warns on stderr, exits 0 with no tests run.
   - `./thoth_test -r --id M1T-01 --provider openai` runs M1T-01 (no openai key needed since test is provider-agnostic) with `requested_but_filtered: false` (it actually matches the filter trivially). Use an id+provider combination that genuinely mismatches to exercise `requested_but_filtered: true`.

3. **`--last-failed`**
   - No cache exists: exit `2` with matching stderr.
   - Cache with one failure: reruns exactly that test.
   - Cache with zero failures: exit `2` (nothing to rerun, same as no-cache case semantically).

4. **`-q` / `--quiet`**
   - Passing run: stdout matches a single summary line, no table, no progress bar characters.
   - Failing run (use a deliberately-failing injected `TestCase`, or a pytest fixture that monkeypatches `all_tests`): stdout contains `===BEGIN FAILURE <id>===` and `===END FAILURE <id>===` with full stdout/stderr between them.

5. **`--report-json`**
   - Writes to given path, file parses as JSON, schema fields present, matches cache content.
   - Atomicity: simulate KeyboardInterrupt mid-write and confirm no `.tmp` leftover corrupts the next read.

6. **Cache always written**
   - Even without `--report-json`, `.thoth_test_cache/last_run.json` is written after every run.
   - Atomic write: no partial files on interrupt.

7. **Backwards compatibility**
   - Every existing invocation in `CLAUDE.md` (e.g., `./thoth_test -r --provider mock --skip-interactive`) produces the **same exit code** and **same human-visible table** as before (byte-for-byte comparison not required; structural: "contains final table, contains `Passed: N`").

### Pre-existing test suite

- `./thoth_test -r` must still pass end-to-end after the change. Lefthook already enforces this. No new test cases added to `all_tests` unless an existing behaviour needs coverage we lacked.

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Cache write on every run breaks CI with read-only filesystem | Catch `PermissionError` / `OSError` during cache write, log to stderr, continue (don't fail the run). `--report-json` still works when writable. |
| JSON with full failure stdout blows up on enormous output | In practice failures are bounded by `TEST_TIMEOUT`; stdout is already materialized in memory today. Document the implicit cap (RAM). If it ever becomes a problem, add `--max-output-bytes` with 1 MB default. |
| `--id` overriding `--skip-interactive` runs pexpect tests in CI non-TTY | pexpect already handles non-TTY gracefully; worst case is a clean failure. Document the precedence in `--help`. |
| Selection-resolver refactor introduces a regression in existing filter composition | The refactor is behaviour-preserving; every pre-existing `main()` test path is preserved. Pytest coverage (test matrix #7) catches drift. |
| `.thoth_test_cache/` accidentally committed | Add to `.gitignore` in the same PR as the feature. |

---

## Rollout

Single PR, since the parts reinforce each other and each is individually small. Commit boundaries within the PR (conventional commits):

1. `feat(thoth_test): add --list and --list-json for test discovery`
2. `feat(thoth_test): add --id for exact-match test selection`
3. `feat(thoth_test): write last-run cache and add --last-failed`
4. `feat(thoth_test): add --report-json for on-demand JSON export`
5. `feat(thoth_test): add -q/--quiet mode with fenced failure blocks`
6. `test(thoth_test): pytest coverage for new CLI flags`
7. `docs(claude): update CLAUDE.md to use new flags instead of grep workarounds`

Each commit keeps the suite green (`./thoth_test -r` passes; pytest passes).

---

## Open Questions Resolved During Brainstorm

| # | Question | Decision |
|---|---|---|
| 1 | Scope | C — four core flags + `--last-failed` + fenced sentinels |
| 2 | Default persistence | B — always write to `.thoth_test_cache/last_run.json` |
| 3 | `--id` composition | B — `--id` overrides other filters, warns on mismatch |
| 4 | `-q` output shape | B — silent on pass, fenced blocks on fail |
| 5 | JSON output content | C — full stdout/stderr for failures, nothing for passes |

## Open Questions Still TBD

None blocking. If any surface during implementation (e.g., concrete wording of warning messages, whether to print a "cache written to ..." debug line under `-v`), defer to writing-plans skill and author discretion.
