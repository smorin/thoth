# P18-T38: `thoth resume --async` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `--async / -A` flag to `thoth resume <op-id>` for non-blocking status check + ready-file download. The async variant performs **exactly one** `provider.check_status()` per non-completed provider, saves results for any that have flipped to `completed`, updates the checkpoint, prints a summary (or JSON envelope when `--json` is also set), and exits — without entering the polling loop. Use case: drive-by progress check that also pulls down whatever's ready, e.g. checking on a multi-day deep-research without committing the terminal to it.

**Architecture:** Reuse the existing reconnect machinery in `resume_operation` (run.py:1004-1030) — extract it into a `_resume_one_tick(...)` helper so both the polling-loop path and the new async path share the same provider-instantiation surface. The async branch returns early *before* `_run_polling_loop` is called, so it never enters the polling loop and inherits none of its progress UI / interrupt handling. Output side-effects use the same `OutputManager.save_result(...)` call path the polling loop uses at run.py:608-621 — no new save abstraction.

**Tech Stack:** Python 3.11+, Click (`is_flag=True` local option on `resume`), pytest with monkey-patched provider stubs, the existing `_fixture_helpers.MockProvider` patterns from `tests/test_provider_cancel.py` and `tests/test_sigint_upstream_cancel.py`.

**Source of truth:** The P18 row `[P18-T38]` in `/Users/stevemorin/c/thoth/PROJECTS.md` (line ~647). If this plan and PROJECTS.md disagree, PROJECTS.md wins. The plan implements the row; the row defines the contract.

**Locked design decisions (from upstream conversation):**

1. **Operation status on partial:** stay as-is; only per-provider statuses move. Aggregate `operation.status` flips to `"completed"` only when *every* provider reports completed.
2. **JSON envelope shape:** same fields as `get_resume_snapshot_data(...)` PLUS a new `newly_completed: list[str]` field listing provider names whose status flipped to `completed` during this tick.
3. **Already-completed op:** print `"Operation X already completed"` and exit 0. No API calls, no file writes.
4. **Failed providers:** treat as partial success. Save successes, record the failure on the affected provider, exit 0. The user can re-run `thoth resume` (without `--async`) to retry recoverable failures.

**Out of scope:**

- Multi-tick polling — that's plain `thoth resume`. `--async` is intentionally one-shot.
- Resume with `--async` on a checkpoint whose providers don't support `reconnect()` — we keep the existing run.py:1027 error path verbatim.
- Provider-side retry logic — the async tick is "what's the status RIGHT NOW," not "retry until success."

---

## File Structure

| Action | Path | Responsibility |
|---|---|---|
| Create | `tests/test_resume_async.py` | New file. 7 tests covering path isolation, all-running, one-completed partial, all-completed terminal, JSON envelope shape, missing op-id (exit 6), already-completed no-op. Tests written FIRST per CLAUDE.md TDD discipline. |
| Modify | `src/thoth/cli_subcommands/resume.py` | Add local `--async / -A` flag (`is_flag=True`, default `False`). Do NOT add to `_RESUME_HONOR` — the cli-group's own `--async/-A` flag (`async_mode`) is for *initial* submissions and remains rejected on `resume` by `validate_inherited_options`. Thread the local flag to `resume_operation(async_check=...)`. When `as_json and async_check`, branch to a dedicated envelope path that returns the snapshot dict + `newly_completed`. |
| Modify | `src/thoth/run.py` | (a) Add `async_check: bool = False` parameter to `resume_operation`. (b) Extract a `_resume_one_tick(operation, provider_instances, output_manager, checkpoint_manager, mode_config, ctx, verbose) -> dict` helper that runs one `check_status` per provider, saves any newly-completed results, updates and saves checkpoint, returns `{"newly_completed": [...], "operation": operation}`. (c) Branch in `resume_operation`: when `async_check=True`, after the existing reconnect block, call `_resume_one_tick(...)` and return its result instead of entering `_run_polling_loop`. |
| Modify | `src/thoth/run.py` | (d) Update the existing polling-loop branch to ALSO call `_resume_one_tick(...)` once before entering the loop (cosmetic — see Task 3 design note); OR leave it untouched (see decision in Task 3). Default: leave untouched, no shared call. |
| Modify | `manual_testing_instructions.md` | New section *P. `thoth resume --async`* with: P1 still-running drive-by, P2 partial-completion download, P3 already-completed no-op, P4 JSON envelope shape with `newly_completed`. Mirrors the K1–K6 pattern that section K already uses. |
| Modify | `PROJECTS.md` | Flip `[P18-T38] [ ]` → `[x]` at the end. No row-text change; the captured description remains the contract. |

**Decomposition rationale:** Adding `_resume_one_tick(...)` as a dedicated helper (rather than inlining the per-provider loop in two places) avoids duplication and makes the async path independently testable. Tests live in one new file because all 7 cases share the same fixture shape (a checkpoint on disk + `MockProvider` instances reconnected to it); splitting into two files would just duplicate the fixture.

---

## Pre-flight (do this before Task 1)

- [ ] **P0.1: Create a worktree for the work**

```bash
cd /Users/stevemorin/c/thoth
git worktree add /Users/stevemorin/c/thoth-worktrees/p18-t38-resume-async -b p18-t38-resume-async main
cd /Users/stevemorin/c/thoth-worktrees/p18-t38-resume-async
```

Per the user-memory note `feedback_worktrees.md`, thoth worktrees go in `/Users/stevemorin/c/thoth-worktrees/<branch>` (sibling to the repo, NOT `.worktrees/`).

- [ ] **P0.2: Verify the gate is green before starting**

```bash
just check && uv run pytest -q --ignore=tests/extended && ./thoth_test -r --skip-interactive -q
```

Expected: all green. T27 just landed at `9d01b9a`; baseline should be clean.

- [ ] **P0.3: No PROJECTS.md status flip needed**

P18 is already `[~]` in the trunk; T38 is a single `[ ]` row inside it. No top-level state change at start.

---

## Task 1: Test design — write the failing tests first

**Files:**
- Create: `tests/test_resume_async.py`

This task encodes the contract. All 7 tests must FAIL before any production code is written. Per CLAUDE.md test-driven discipline, the design of the tests defines what "done" looks like.

- [ ] **Step 1.1: Write `test_resume_async_path_isolation`**

Verify `--async` does NOT enter `_run_polling_loop`. Monkey-patch `_run_polling_loop` to raise on call; expect the test to pass without that exception.

- [ ] **Step 1.2: Write `test_resume_async_all_running`**

Construct a checkpoint with two providers both returning `running` from `check_status`. Run `resume_operation(..., async_check=True)`. Assert: no `save_result` calls, both per-provider statuses unchanged, operation.status unchanged, exit 0 (no exception).

- [ ] **Step 1.3: Write `test_resume_async_one_completed_one_running`**

One provider returns `completed`, the other `running`. Assert: exactly one `save_result` call (for the completed one), that provider's status is now `completed`, the other's status unchanged, operation.status NOT flipped to `completed` (the locked decision: aggregate stays as-is on partial).

- [ ] **Step 1.4: Write `test_resume_async_all_completed`**

Both providers return `completed`. Assert: two `save_result` calls, both per-provider statuses are `completed`, operation.status is now `completed`.

- [ ] **Step 1.5: Write `test_resume_async_json_envelope`**

Run `thoth resume <op-id> --async --json` via `CliRunner`. Assert JSON output contains `operation_id`, `status`, `mode`, `providers`, AND a `newly_completed` field listing provider names that flipped this tick. No prose on stdout.

- [ ] **Step 1.6: Write `test_resume_async_missing_op_id_exits_6`**

`thoth resume MISSING_ID --async` exits 6 (matches the existing default `resume` behavior at `cli_subcommands/resume.py:96`).

- [ ] **Step 1.7: Write `test_resume_async_already_completed_is_noop`**

Operation checkpoint has `status="completed"`. Run with `--async`. Assert: zero `check_status` calls (no API hit), zero `save_result` calls, "already completed" message printed, exit 0.

- [ ] **Step 1.8: Confirm all 7 tests fail**

```bash
uv run pytest tests/test_resume_async.py -v
```

Expected: 7 failures, all from missing `--async` flag / missing `async_check` parameter / no early-return path. If any test PASSES at this stage, the test isn't actually exercising new behavior — fix the test before moving on.

---

## Task 2: Wire the `--async` flag

**Files:**
- Modify: `src/thoth/cli_subcommands/resume.py`

This task is mechanical: add the Click option, add the parameter to the callback, thread it through to `resume_operation`. No business logic changes. After this task, `thoth resume <op-id> --async` should be a no-op that runs the existing polling loop (because `resume_operation` ignores the new kwarg until Task 3).

- [ ] **Step 2.1: Add the flag declaration**

In `cli_subcommands/resume.py`, after the existing `--cancel-on-interrupt/--no-cancel-on-interrupt` option block, add:

```python
@click.option(
    "--async",
    "-A",
    "async_check",
    is_flag=True,
    help=(
        "Do one status check per provider, save any newly-completed results, "
        "and exit without entering the polling loop. Combine with --json to "
        "emit a snapshot envelope including a `newly_completed` field."
    ),
)
```

The dest name `async_check` avoids shadowing the cli-group's `async_mode` parameter.

- [ ] **Step 2.2: Add the parameter to the callback signature**

Add `async_check: bool` to the `resume(...)` callback parameters, just before `as_json: bool`.

- [ ] **Step 2.3: Pass through to `resume_operation`**

In the bottom call to `_thoth_run.resume_operation(...)`, add `async_check=async_check` as a kwarg.

- [ ] **Step 2.4: Confirm Task 1 tests still all FAIL**

The flag now exists, but `resume_operation` ignores it. The path-isolation test and the no-side-effects-on-completed test should still fail (the polling loop will still execute). Tests 1.5 (JSON envelope) and 1.6 (missing-id) may now pass partially — that's fine; we'll lock them at Task 3 / Task 4.

---

## Task 3: Implement the early-return async branch

**Files:**
- Modify: `src/thoth/run.py`

This is the core behavior change. Extract a helper, branch in `resume_operation`, return early without polling.

- [ ] **Step 3.1: Add `async_check` to `resume_operation` signature**

After `cli_api_keys` in the keyword-only block:

```python
async_check: bool = False,
```

Default `False` to preserve the existing call-site contract (the polling-loop path is unchanged for callers that don't opt in).

- [ ] **Step 3.2: Handle the already-completed short-circuit**

The existing block at run.py:983-986 already handles `operation.status == "completed"` by printing and returning. Verify this branch fires BEFORE any provider reconnection — if not, restructure so it does. The async path must short-circuit cleanly without an API call.

- [ ] **Step 3.3: Extract `_resume_one_tick(...)` helper**

Add a new top-level async function in run.py:

```python
async def _resume_one_tick(
    operation: OperationStatus,
    provider_instances: dict[str, ResearchProvider],
    output_manager: OutputManager,
    checkpoint_manager: CheckpointManager,
    mode_config: dict,
    ctx: AppContext,
    verbose: bool,
) -> dict[str, Any]:
    """Single status-check tick for `thoth resume --async`.

    For each provider currently in provider_instances (already reconnected),
    call check_status once. If a provider returns "completed", fetch and
    save its result, update operation.providers[name].status, and append
    its name to newly_completed. Save the checkpoint exactly once at the
    end. Never enters the polling loop.

    Returns:
        {"newly_completed": [...], "all_done": bool}
    """
    newly_completed: list[str] = []
    for provider_name, provider in provider_instances.items():
        job_id = operation.providers[provider_name]["job_id"]
        status = await provider.check_status(job_id)
        provider_status = status.get("status")

        if provider_status == "completed":
            result_content = await provider.get_result(job_id, verbose=verbose)
            provider_model = getattr(provider, "model", None)
            system_prompt = mode_config.get("system_prompt", "")
            output_path = await output_manager.save_result(
                operation,
                provider_name,
                result_content,
                None,  # output_dir — operation already carries paths
                model=provider_model,
                system_prompt=system_prompt,
            )
            operation.output_paths[provider_name] = output_path
            operation.providers[provider_name]["status"] = "completed"
            operation.providers[provider_name].pop("failure_type", None)
            operation.providers[provider_name].pop("error", None)
            newly_completed.append(provider_name)
        elif provider_status in ("permanent_error", "failed"):
            # Locked decision: partial success — record + continue
            operation.providers[provider_name]["status"] = "failed"
            operation.providers[provider_name]["error"] = status.get("error", "unknown")
        # `running` / `queued` / anything else: leave checkpoint state untouched.

    all_done = all(
        operation.providers[name].get("status") == "completed"
        for name in operation.providers
    )
    if all_done:
        operation.transition_to("completed")

    await checkpoint_manager.save(operation)
    return {"newly_completed": newly_completed, "all_done": all_done}
```

- [ ] **Step 3.4: Branch in `resume_operation`**

After the existing reconnect block (run.py:1031-1035 today, where `provider_instances` is finalized) and before the `_run_polling_loop` call, add:

```python
if async_check:
    tick = await _resume_one_tick(
        operation, provider_instances, output_manager,
        checkpoint_manager, mode_config, ctx, verbose,
    )
    if not quiet and not ctx.as_json:
        # Plain-text summary path. JSON envelope is rendered upstream in
        # resume.py — see Task 4.
        if tick["newly_completed"]:
            console.print(
                "[green]Saved results from:[/green] "
                + ", ".join(tick["newly_completed"])
            )
        else:
            console.print("[dim]No providers completed since last check.[/dim]")
        if tick["all_done"]:
            console.print(f"[green]Operation {operation.id} fully completed.[/green]")
    return tick
```

The polling-loop branch is unchanged.

- [ ] **Step 3.5: Confirm Tests 1.1 / 1.2 / 1.3 / 1.4 / 1.7 pass**

```bash
uv run pytest tests/test_resume_async.py -v -k "path_isolation or all_running or one_completed_one_running or all_completed or already_completed"
```

Test 1.5 (JSON envelope) still fails — that's Task 4. Test 1.6 (missing-id) should already pass if `resume_operation`'s `if not operation: sys.exit(6)` path runs before any `--async` branching.

---

## Task 4: JSON envelope + `newly_completed` field

**Files:**
- Modify: `src/thoth/cli_subcommands/resume.py`

This task wires the third combinator: `--async --json`. The existing `--json`-only path is a snapshot (no upstream calls). The new combination is "do one upstream tick, then emit the snapshot plus what just changed."

- [ ] **Step 4.1: Branch on `async_check` inside the `if as_json:` block**

The current structure at `cli_subcommands/resume.py:81-106` does:
- `as_json` → call `get_resume_snapshot_data` (read-only) → `emit_json(data)` → return
- non-json → flow through to `resume_operation` polling-loop call

Refactor to a three-way:
- `as_json and not async_check` → existing snapshot path, unchanged
- `as_json and async_check` → call `resume_operation(async_check=True)` synchronously via `_run_maybe_async`, then read the latest checkpoint via `get_resume_snapshot_data` and merge in `newly_completed` from the returned dict, then `emit_json(...)`
- `not as_json` → flow through to existing or new resume_operation call (Task 3 already handles `async_check` here)

- [ ] **Step 4.2: Suppress prose output when `as_json and async_check`**

Wrap the `_run_maybe_async(_thoth_run.resume_operation(...))` call in a `contextlib.redirect_stdout(io.StringIO())` block, mirroring the pattern at `cli_subcommands/ask.py:208-211`. The Rich console writes from `_resume_one_tick` must not pollute the JSON envelope on stdout.

Set `app_ctx.as_json = True` before the call so `_resume_one_tick`'s plain-text summary branch is skipped (the existing `not ctx.as_json` guard in Task 3 Step 3.4 already does this once we set the flag).

- [ ] **Step 4.3: Build the merged envelope**

```python
data = get_resume_snapshot_data(operation_id) or {}
data["newly_completed"] = tick["newly_completed"] if tick else []
emit_json(data)
```

`tick` is the return value from the captured `resume_operation(...)` call. If `_run_maybe_async` doesn't propagate the return value today, capture it via a small wrapper or use a closure.

- [ ] **Step 4.4: Confirm Test 1.5 passes**

```bash
uv run pytest tests/test_resume_async.py::test_resume_async_json_envelope -v
```

Expected: green. Stdout must be exactly the JSON envelope; no Rich prose, no log lines.

- [ ] **Step 4.5: Confirm all 7 tests pass**

```bash
uv run pytest tests/test_resume_async.py -v
```

Expected: 7/7 green.

---

## Task 5: Manual testing scenarios + glyph flip

**Files:**
- Modify: `manual_testing_instructions.md`
- Modify: `PROJECTS.md`

- [ ] **Step 5.1: Add section P to `manual_testing_instructions.md`**

After section O (the existing "User-mode missing-`kind` warn-once" section that we shipped earlier in P18), add:

```markdown
### P. `thoth resume --async`

> Drive-by progress check: one status tick per provider, downloads any
> newly-completed results, exits without polling.

```bash
# P1. Drive-by check on a still-running op
OPID=$(uv run thoth ask "long topic" --mode deep_research --async --provider mock --json | jq -r .operation_id)
uv run thoth resume "$OPID" --async
# Expected: prints "No providers completed since last check." and exits 0.
# NO new files written; checkpoint statuses unchanged.

# P2. Partial-completion download (one provider done, one still running)
# (use --combined openai,perplexity if you have keys; or simulate with mock)
uv run thoth resume "$OPID" --async
# Expected: prints "Saved results from: openai" (or whichever flipped).
# That provider's result file is now on disk; the other is still pending.

# P3. Already-completed op is a no-op
uv run thoth resume "$COMPLETED_OPID" --async
# Expected: "Operation X already completed." Exits 0. Zero API calls.

# P4. JSON envelope shape
uv run thoth resume "$OPID" --async --json | jq
# Expected: {operation_id, status, mode, providers, newly_completed: [...]}
# `newly_completed` is the list of provider names that flipped THIS tick.
```
```

- [ ] **Step 5.2: Flip `[P18-T38]` to `[x]` in PROJECTS.md**

Edit the row text minimally — just `[ ]` → `[x]`. Description stays as captured.

- [ ] **Step 5.3: Final commit through full lefthook gate**

```bash
git add tests/test_resume_async.py src/thoth/cli_subcommands/resume.py src/thoth/run.py manual_testing_instructions.md PROJECTS.md
git commit -m "$(cat <<'EOF'
feat(run): add `thoth resume --async` for non-blocking status check + ready-file download (P18-T38)

Adds a third resume mode alongside default-resume (full polling loop)
and resume --json (pure snapshot). The new --async flag does exactly
one provider.check_status() per non-completed provider, saves any
newly-completed results via OutputManager.save_result, updates and
saves the checkpoint, and exits without entering the polling loop.

Use case: drive-by progress check that also pulls down whatever's ready.

Combine with --json to get the snapshot envelope plus a `newly_completed`
field listing providers whose status flipped this tick.

Locked design decisions:
- Operation status stays as-is on partial completion (only flips to
  "completed" when every provider reports completed).
- Failed providers are recorded but treated as partial success (exit 0;
  re-run plain `thoth resume` to retry recoverable failures).
- Already-completed ops are no-ops with a message and exit 0.

Refactor: extracts a `_resume_one_tick(...)` helper in run.py that the
async branch calls; the polling-loop path is untouched.

Tests: tests/test_resume_async.py (7 tests covering path isolation, all
running, partial completion, full completion, JSON envelope shape,
missing op-id, and already-completed no-op).
EOF
)"
```

The lefthook pre-commit gate runs: ruff (format+lint), ty, codespell, gitleaks, and the full `./thoth_test` integration suite. Expect ~45s.

---

## Acceptance criteria

- [ ] All 7 tests in `tests/test_resume_async.py` pass.
- [ ] `thoth resume <op-id> --async` against a running mock-provider op exits in <2s, prints a one-line summary, makes exactly one `check_status` call per non-completed provider, and does NOT call `_run_polling_loop`.
- [ ] `thoth resume <op-id> --async --json` emits a single JSON envelope with the `newly_completed` field; nothing else on stdout.
- [ ] `thoth resume <completed-op> --async` is a no-op with the existing "already completed" message; zero API calls.
- [ ] Default `thoth resume <op-id>` (without `--async`) is byte-identical to today's behavior — full polling loop, same UX.
- [ ] `[P18-T38]` flipped to `[x]` in PROJECTS.md.
- [ ] Manual section P added to `manual_testing_instructions.md`.

---

## Notes

- **No CLI inheritance for `--async`.** The cli-group's `--async / -A` flag (parameter `async_mode`) controls *initial* submissions. We deliberately do NOT add `async_mode` to `_RESUME_HONOR`; if a user types `thoth --async resume <op-id>`, validation rejects it cleanly with the standard "no such option for 'thoth resume'" message. The new local `--async` flag on `resume` is a different parameter (dest `async_check`) and means a different thing.
- **No `signals.py` changes.** SIGINT during `--async` is uninteresting — the flag is a one-shot, by definition fast (single `check_status` round-trip per provider). If interrupted mid-tick, the user gets the existing local-checkpoint-cancelled UX from `handle_sigint`; no upstream cancel is plumbed because the tick is short.
- **Reusing `OutputManager.save_result(operation, provider_name, result_content, output_dir=None, ...)`.** Passing `output_dir=None` mirrors the polling-loop call site (run.py:613) which uses the operation's own `output_paths` resolution. Verify this signature still accepts `None` before relying on it; if not, plumb the `output_dir` through `resume_operation` and forward.
