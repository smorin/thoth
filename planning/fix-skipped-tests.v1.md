# Plan: Delete M1T-09, fix T-SIG-01 and QFILE-02

## Context

Three tests currently skip in `just test`:

- **M1T-09** (thoth_test:2280–2287) is redundant with T-SIG-01 (same F-81 feature; PRD maps F-81 → T-SIG-01 at `planning/thoth.prd.v24.md:340`) and mechanically unreachable:
  - No `signal_after` field, so `run_command` (thoth_test:200) never sends SIGINT.
  - Asserts `expected_exit_code=130`, but `handle_sigint` (src/thoth/__main__.py:4542) ends with `sys.exit(1)`. 130 = 128 + SIGINT, produced only when a process is killed *without* a handler — thoth installs one at src/thoth/__main__.py:4554, so 130 is unreachable.
  - No stdout assertions — the "checkpoint save" half of the description is never verified.
- **T-SIG-01** (thoth_test:2862–2876) is well-designed but `signal_after=0.05` fires SIGINT before thoth's handler is installed and `_current_operation` is populated.
- **QFILE-02** (thoth_test:2727–2748) tries to test `--prompt-file -` stdin piping but has `"|"` as a literal argv element and `run_command` hardcodes `stdin=subprocess.DEVNULL` (thoth_test:190).

### Intended outcome

- Remove the dead test (M1T-09).
- Un-skip T-SIG-01 by giving thoth enough time to install its SIGINT handler before the signal fires.
- Un-skip QFILE-02 by adding minimal stdin plumbing to the test runner and rewriting the command to not rely on shell piping.

## Recommended Approach

Three surgical edits plus one ~6-line infrastructure addition — all in `thoth_test`. No production code changes.

### Files to modify

- `thoth_test` (the top-level test runner script). No changes to `src/thoth/__main__.py`.

### Change 1 — Delete M1T-09

Remove `thoth_test:2279–2287` (the `# Graceful Shutdown Test (F-81)` comment and the TestCase). PRD mapping already names T-SIG-01 as the F-81 test, so no PRD update is needed.

### Change 2 — Fix T-SIG-01

In `thoth_test:2862–2876`:

| Line | From | To |
|---|---|---|
| 2872 | `signal_after=0.05,  # Send SIGINT after 0.05 seconds` | `signal_after=2.0,  # Send SIGINT after thoth's handler is installed` |
| 2874 | `skip=True,` | *(remove)* |
| 2875 | `skip_reason="Timing issues make this test unreliable",` | *(remove)* |

**Why 2.0 s:** thoth cold-starts in ~0.5–1.0 s (uv + Python imports + config load); the mock provider's poll `delay=0.1` (src/thoth/__main__.py:1760) means the polling loop is active well before 2.0 s. At 2.0 s, `handle_sigint` reaches its checkpoint-save branch and prints both asserted patterns. `communicate()` returns as soon as the child exits, so a conservative delay has no downside beyond walltime. If 2.0 s proves flaky in CI, bump to 3.0 s.

### Change 3 — Fix QFILE-02 (infrastructure + test rewrite)

**3a. Add one field to `TestCase`** (thoth_test:107–133):

```python
stdin_input: str | None = None  # Data piped to subprocess stdin
```

**3b. Update `run_command`** (thoth_test:168–214):

Add parameter, flip stdin handle when input is provided, pass `input=` to `communicate`:

```python
def run_command(
    command: list[str],
    env: dict[str, str] | None = None,
    timeout: int = TEST_TIMEOUT,
    cwd: str | None = None,
    signal_after: float | None = None,
    stdin_input: str | None = None,
) -> tuple[int, str, str]:
    ...
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE if stdin_input is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=cmd_env,
        cwd=cwd,
        bufsize=-1,
    )
    ...
    stdout, stderr = process.communicate(input=stdin_input, timeout=timeout)
```

**3c. Wire through at the single call site** (thoth_test:881–886):

```python
exit_code, stdout, stderr = run_command(
    test_command,
    env=test_env,
    timeout=test_case.timeout,
    signal_after=test_case.signal_after,
    stdin_input=test_case.stdin_input,
)
```

**3d. Rewrite QFILE-02** (thoth_test:2727–2748):

```python
TestCase(
    test_id="QFILE-02",
    description="Read prompt from stdin",
    command=[THOTH_EXECUTABLE, "--prompt-file", "-", "--provider", "mock"],
    stdin_input="test prompt from stdin\n",
    expected_stdout_patterns=[r"Research completed"],
    expected_files=["*_mock_*.md"],
    cleanup_files=["*_mock_*.md"],
    expected_exit_code=0,
    provider="mock",
    api_key_method="env",
),
```

Thoth already supports `--prompt-file -` via `sys.stdin.read()` at src/thoth/__main__.py:870–875 — no production code change.

## Out of scope

- **COMB-01** — blocked on Perplexity provider implementation (REAL-02 failure). Stays skipped.
- **REAL-02** — pre-existing "Perplexity provider not yet implemented" gap. Separate project.
- **PRD update for F-81 mapping** — already points to T-SIG-01; no change needed.
- **`thoth_test:is_api_key_error` overmatch** — no longer causes miscategorization now that thoth reads env vars correctly.

## Verification

1. **Targeted replay** of the two fixed tests (if the runner supports filtering):
   ```bash
   ./thoth_test -v --test T-SIG-01
   ./thoth_test -v --test QFILE-02
   ```

2. **Full suite** — confirm M1T-09 gone, T-SIG-01 and QFILE-02 pass:
   ```bash
   ./thoth_test -r
   ```
   Expected: **Total 111, Passed 110, Skipped 2 (COMB-01 + M1T-05 signal-dup if any), Failed 1 (REAL-02 pre-existing).**

3. **Quality gate** per CLAUDE.md:
   ```bash
   make env-check
   just lint typecheck
   just test
   ```

4. **Regression guard**: confirm previously-passing tests remain green — in particular the other mock-provider tests that share `run_command` (should be unaffected since `stdin_input` defaults to `None` → same `DEVNULL` behavior as today).
