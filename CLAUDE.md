## Development Principles
- When planning features, look at using design patterns that make it easy to keep code consistent. And then put in place best practices.
- Shared Codex-style agent instructions live in `AGENTS.md`; keep this file and `AGENTS.md` aligned when changing repo guidance.

## Fast Iteration Loop

The pre-commit hook runs ruff + ty + bandit + gitleaks + codespell + the full
`./thoth_test` integration suite (~60s) on every staged `.py` change. During
rapid iteration, **do not commit between edits just to trigger checks** —
run targeted tools directly and commit once when it's actually done.

### Shortest loop first

Pick the narrowest feedback that can detect your change's problem, then widen:

1. **Inner (1-5s)** — rerun the ONE test you're iterating on:
   - Pytest single test: `uv run pytest tests/test_foo.py::test_bar -x -v`
   - Pytest keyword: `uv run pytest tests/ -k "cancelled" -x`
   - thoth_test by ID: `./thoth_test -r -t M8T-03 -v`
     (`-t` does substring match on test_id and description)
2. **Module (5-20s)** — rerun the file: `uv run pytest tests/test_foo.py -v`
3. **Lint/type only (~5s)** — `just check` (skips tests entirely)
4. **Full gate (~60s)** — run once, right before commit: the pre-commit hook
   runs it anyway.

### Finding test IDs to rerun

Both runners print IDs on failure:

- **pytest** prints `tests/test_foo.py::test_bar FAILED` — copy the `::`-path.
- **thoth_test** prints a "Failed Test Details" block with `Test M8T-03:` headers
  and a "To rerun failed tests:" hint at the end of the run.

When a pre-commit hook fails on `./thoth_test`, use quiet mode to get just
the fenced failure blocks (no 64-row noise table):

```bash
./thoth_test -r --provider mock --skip-interactive -q
```

To rerun only what just failed:

```bash
./thoth_test -r --last-failed -q
```

To pick a specific test by exact ID:

```bash
./thoth_test -r --id M8T-03 -v
```

### Discovering tests without running them

- TSV list: `./thoth_test --list`
- JSON list: `./thoth_test --list-json`
- Preview a filter: `./thoth_test --list --provider mock`
- Machine-readable run report is always at `.thoth_test_cache/last_run.json`
  (schema_version 1). Use `--report-json PATH` to also write a copy elsewhere.

### Flaky-test retry policy

Network-dependent thoth_test cases (invalid/missing API-key variants) can
time out at 10s on slow connections and report `exit code -1`. If a single
such test fails on first run, rerun JUST that one:

```bash
./thoth_test -r -t M8T-03
```

For flaky network tests, prefer `./thoth_test -r --last-failed -q` over
re-running the full suite.

Two consecutive failures of the same test = real bug. One failure = noise.

### Hook discipline (do not skip routinely)

- **Do NOT** `git commit --no-verify` or `LEFTHOOK=0 git commit` to bypass
  hooks during normal iteration. The pain is a signal you're committing too
  often; keep changes uncommitted and run targeted tools until green.
- **Exception**: for a short-lived intermediate WIP commit you plan to
  squash, `LEFTHOOK=0` is acceptable IF you have already run the equivalent
  checks manually (`just check` + `uv run ruff format --check src/ tests/`
  + the targeted tests you care about). The **last commit before
  `git push`** MUST go through the full hook set.
- ⚠️ `just check` does NOT run `ruff format --check`. If you bypass
  lefthook, you must also run `ruff format --check` (or `ruff format`)
  yourself, otherwise CI's format gate will catch it.

### Periodic full-gate runs (don't save it all for the end)

When working through a multi-commit task, do **not** save the full
lefthook-equivalent gate for the very last commit. Run it periodically
as you go, scaled to commit complexity:

- **Complex / wide-blast-radius commit** (touches many files, refactors
  core modules, changes runtime behavior, modifies CLI surface): run
  the full gate **immediately** after that commit, before starting
  the next one.
- **Simple commits** (test additions, doc tweaks, small bug fixes):
  batch at most **2–3 commits** between full-gate runs. Never more
  than "a few."
- **Always**: the last commit before `git push` goes through the
  full hook set (see above).

The goal is to catch latent format / lint / type / test errors while
the working set is still small enough to fix cheaply, instead of
letting them compound until CI fails after push. Concretely, run:

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run ty check src/
uv run pytest -q
./thoth_test -r --skip-interactive -q
```

…or equivalently, do a normal `git commit` (no `LEFTHOOK=0`) which
runs all of the above via lefthook.

## Code Quality Assurance Workflow (final pre-commit gate)

This is the one-shot gate to run right before committing — NOT between edits.
For iteration, see "Fast Iteration Loop" above.

1. **Main Executable Verification** (thoth):
   ```bash
   make env-check  # Verify bootstrap dependencies are installed
   just fix        # Auto-fix any issues found
   just check      # Run lint and typecheck on main executable
   ```

2. **Run Tests**:
   ```bash
   ./thoth_test -r  # Run the test suite to ensure functionality
   ```

3. **Test Suite Verification** (thoth_test):
   ```bash
   just test-fix        # Auto-fix any issues in test suite
   just test-lint       # Run lint on test suite
   just test-typecheck  # Run typecheck on test suite
   ```

4. **Final Verification**:
   - Only consider the change complete when:
     - `make env-check` passes without errors
     - `just check` passes without errors
     - All tests pass
     - `just test-lint` passes without errors
     - `just test-typecheck` passes without errors

### Test Debugging Workflow

When a test fails:

1. **Copy the test ID** from the failure output (both pytest and thoth_test
   print them).
2. **Rerun ONLY that test** via the inner-loop command above. Do NOT rerun
   the full suite.
3. Add `-v` / `--verbose` if the error message is truncated.
4. Fix and rerun the single test until green.
5. **Widen one step** — rerun the file or the pytest module it lives in.
6. **Only then** run the full gate once before committing.

Do not re-run the 8-step verification (`make env-check` → `just fix` →
`just check` → `./thoth_test` → `just test-fix` → `just test-lint` →
`just test-typecheck`) between edits. That's ~90s per cycle. Run it once
at the end.

### Real-API test suites (gated, NOT in the pre-commit gate)

Two pytest markers gate tests that hit live provider APIs. Both are
deselected by default (`addopts = "-m 'not extended and not live_api'"`)
so `git commit` and PR CI never trigger real network calls or spend.

| Marker | Trigger | Schedule | Purpose |
|---|---|---|---|
| `extended` | `just test-extended` / `pytest -m extended` | nightly via `.github/workflows/extended.yml` (09:00 UTC) | model-kind drift watch — every entry in `KNOWN_MODELS` matches upstream API behavior |
| `live_api` | `just test-live-api` / `pytest -m live_api` | weekly via `.github/workflows/live-api.yml` (Sun 02:00 UTC = Sat 7pm PDT) | CLI workflow regression — streaming, file output, append, secret masking, mismatch defense |

Both workflows run with `continue-on-error: true` (informational, not
blocking) and require the `OPENAI_API_KEY` repo secret. To trigger
manually: `gh workflow run "Extended Contract Tests (nightly)"` or
`gh workflow run "Live-API Workflow Tests (weekly)"`.

## Planning Documents Management

### Location and Structure
- **Primary Planning Directory**: `planning/`
  - This is where all active planning documents should be stored
  - Always check this directory for the latest versions of planning documents
  - Key documents include PRDs (Product Requirements Documents) and implementation plans

### Versioning Format
Planning documents follow this versioning format:
- **PRD Documents**: `thoth.prd.vXX.md` (e.g., `thoth.prd.v22.md`)
- **Plan Documents**: `thoth.plan.vX.md` (e.g., `thoth.plan.v5.md`)
- **Other Documents**: `[name].vX.md` (e.g., `temp.v5.md`)

### Version Detection and Incrementing
1. **Finding Latest Version**:
   - List files in `planning/` directory
   - Use regex pattern: `thoth\.(prd\.)?v([0-9]+)\.md`
   - Extract version numbers and find the highest

2. **Creating New Version**:
   - Increment the highest version number by 1
   - For PRDs: `thoth.prd.v[N+1].md`
   - For Plans: `thoth.plan.v[N+1].md`

### Archiving Process
When creating a new version:
1. Create the new version in `planning/` directory
2. After completing updates to the new version:
   - Move the old version to `archive/` directory using git commands:
   ```bash
   git mv planning/thoth.prd.v22.md archive/
   git mv planning/thoth.plan.v5.md archive/
   ```
3. Commit both the move and the new file:
   ```bash
   git add planning/thoth.prd.v23.md
   git commit -m "Archive v22 PRD and create v23 PRD"
   ```

### References Location
- **References Document**: `planning/references.md`
  - Contains API documentation links and external references
  - Should be checked for OpenAI, Perplexity, and UV documentation

## Git Best Practices

**Conventional Commits are enforced.** Every commit message must match
`<type>[optional scope]: <subject>`. The local `commit-msg` lefthook and the
`commitlint` CI workflow both reject malformed messages. Allowed types:
`feat`, `fix`, `perf`, `refactor`, `docs`, `test`, `ci`, `chore`, `build`,
`style`, `revert`. Use `feat!:` or a `BREAKING CHANGE:` footer for breaking
changes — release-please treats those as `MAJOR` bumps.

**Releases are automated by release-please.** Do not hand-edit
`pyproject.toml`, `src/thoth/__init__.py`, `CHANGELOG.md`, or
`.release-please-manifest.json` versions. Land conventional commits on
`main`; `release-please.yml` opens a Release PR; merging it tags `vX.Y.Z`
and triggers `publish.yml` (TestPyPI → PyPI). See `RELEASE.md`.

Never say in commits:

 🤖 Generated with [Claude Code](https://claude.ai/code)

 or

   Co-Authored-By: Claude <noreply@anthropic.com>

## API and UV References
Please check @planning/references.md URLs to look up detail about the openai, perplexity, and UV documentation.

## OpenAI API Key
get the openai api key from @openai.env

# Test-driven development.

- Always when creating an implementation plan, make the first thing to design the tests for each task and the milestone. The testing design should be the first step. Then, in the implementation, either a test should be created and then the code updated to pass, or a series of tests should be created and then implementation should pass them all. But it should be test-driven development.
