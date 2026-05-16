## Development Principles
- When planning features, look at using design patterns that make it easy to keep code consistent. And then put in place best practices.
- Shared Codex-style agent instructions live in `AGENTS.md`; keep this file and `AGENTS.md` aligned when changing repo guidance.

## Fast Iteration Loop

The pre-commit hook runs ruff + ty + bandit + gitleaks + codespell + the full
`./doxa_test` integration suite (~60s) on every staged `.py` change. During
rapid iteration, **do not commit between edits just to trigger checks** —
run targeted tools directly and commit once when it's actually done.

### Shortest loop first

Pick the narrowest feedback that can detect your change's problem, then widen:

1. **Inner (1-5s)** — rerun the ONE test you're iterating on:
   - Pytest single test: `uv run pytest tests/test_foo.py::test_bar -x -v`
   - Pytest keyword: `uv run pytest tests/ -k "cancelled" -x`
   - doxa_test by ID: `./doxa_test -r -t M8T-03 -v`
     (`-t` does substring match on test_id and description)
2. **Module (5-20s)** — rerun the file: `uv run pytest tests/test_foo.py -v`
3. **Lint/type only (~5s)** — `just check` (skips tests entirely)
4. **Full gate (~60s)** — run once, right before commit: the pre-commit hook
   runs it anyway.

### Finding test IDs to rerun

Both runners print IDs on failure:

- **pytest** prints `tests/test_foo.py::test_bar FAILED` — copy the `::`-path.
- **doxa_test** prints a "Failed Test Details" block with `Test M8T-03:` headers
  and a "To rerun failed tests:" hint at the end of the run.

When a pre-commit hook fails on `./doxa_test`, use quiet mode to get just
the fenced failure blocks (no 64-row noise table):

```bash
./doxa_test -r --provider mock --skip-interactive -q
```

To rerun only what just failed:

```bash
./doxa_test -r --last-failed -q
```

To pick a specific test by exact ID:

```bash
./doxa_test -r --id M8T-03 -v
```

### Discovering tests without running them

- TSV list: `./doxa_test --list`
- JSON list: `./doxa_test --list-json`
- Preview a filter: `./doxa_test --list --provider mock`
- Machine-readable run report is always at `.doxa_test_cache/last_run.json`
  (schema_version 1). Use `--report-json PATH` to also write a copy elsewhere.

### Flaky-test retry policy

Network-dependent doxa_test cases (invalid/missing API-key variants) can
time out at 10s on slow connections and report `exit code -1`. If a single
such test fails on first run, rerun JUST that one:

```bash
./doxa_test -r -t M8T-03
```

For flaky network tests, prefer `./doxa_test -r --last-failed -q` over
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
./doxa_test -r --skip-interactive -q
```

…or equivalently, do a normal `git commit` (no `LEFTHOOK=0`) which
runs all of the above via lefthook.

## Code Quality Assurance Workflow (final pre-commit gate)

This is the one-shot gate to run right before committing — NOT between edits.
For iteration, see "Fast Iteration Loop" above.

1. **Main Executable Verification** (doxa-research):
   ```bash
   make env-check  # Verify bootstrap dependencies are installed
   just fix        # Auto-fix any issues found
   just check      # Run lint and typecheck on main executable
   ```

2. **Run Tests**:
   ```bash
   ./doxa_test -r  # Run the test suite to ensure functionality
   ```

3. **Test Suite Verification** (doxa_test):
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

1. **Copy the test ID** from the failure output (both pytest and doxa_test
   print them).
2. **Rerun ONLY that test** via the inner-loop command above. Do NOT rerun
   the full suite.
3. Add `-v` / `--verbose` if the error message is truncated.
4. Fix and rerun the single test until green.
5. **Widen one step** — rerun the file or the pytest module it lives in.
6. **Only then** run the full gate once before committing.

Do not re-run the 8-step verification (`make env-check` → `just fix` →
`just check` → `./doxa_test` → `just test-fix` → `just test-lint` →
`just test-typecheck`) between edits. That's ~90s per cycle. Run it once
at the end.

### Real-API test suites (gated, NOT in the pre-commit gate)

Two pytest markers gate tests that hit live provider APIs. Both are
deselected by default (`addopts = "-m 'not extended and not live_api'"`)
so `git commit` and PR CI never trigger real network calls or spend.

| Marker | Trigger | Schedule | Purpose |
|---|---|---|---|
| `extended` | `just test-extended` / `pytest -m "extended and not extended_slow"` | nightly via `.github/workflows/extended.yml` (09:00 UTC) | model-kind drift watch — every entry in `KNOWN_MODELS` matches upstream API behavior |
| `live_api` | `just test-live-api` / `pytest -m "live_api and not extended_slow"` | weekly via `.github/workflows/live-api.yml` (Sun 02:00 UTC = Sat 7pm PDT) | CLI workflow regression — streaming, file output, append, secret masking, mismatch defense |

Both workflows run with `continue-on-error: true` (informational, not
blocking) and require the `OPENAI_API_KEY`, `PERPLEXITY_API_KEY`, and
`GEMINI_API_KEY` repo secrets for full provider coverage. Provider-scoped
manual targets are available as `just test-extended-openai`,
`just test-extended-perplexity`, `just test-extended-gemini`,
`just test-live-api-openai`, `just test-live-api-perplexity`, and
`just test-live-api-gemini`. To trigger manually: `gh workflow run
"Extended Contract Tests (nightly)"` or `gh workflow run "Live-API Workflow
Tests (weekly)"`.

## Planning Documents Management

### Location and Structure
- **Primary Planning Directory**: `planning/`
  - This is where all active planning documents should be stored
  - Always check this directory for the latest versions of planning documents
  - Key documents include PRDs (Product Requirements Documents) and implementation plans

### Versioning Format
Planning documents follow this versioning format:
- **PRD Documents**: `doxa-research.prd.vXX.md` (e.g., `doxa-research.prd.v22.md`)
- **Plan Documents**: `doxa-research.plan.vX.md` (e.g., `doxa-research.plan.v5.md`)
- **Other Documents**: `[name].vX.md` (e.g., `temp.v5.md`)

### Version Detection and Incrementing
1. **Finding Latest Version**:
   - List files in `planning/` directory
   - Use regex pattern: `doxa-research\.(prd\.)?v([0-9]+)\.md`
   - Extract version numbers and find the highest

2. **Creating New Version**:
   - Increment the highest version number by 1
   - For PRDs: `doxa-research.prd.v[N+1].md`
   - For Plans: `doxa-research.plan.v[N+1].md`

### Archiving Process
When creating a new version:
1. Create the new version in `planning/` directory
2. After completing updates to the new version:
   - Move the old version to `archive/` directory using git commands:
   ```bash
   git mv planning/doxa-research.prd.v22.md archive/
   git mv planning/doxa-research.plan.v5.md archive/
   ```
3. Commit both the move and the new file:
   ```bash
   git add planning/doxa-research.prd.v23.md
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
`pyproject.toml`, `src/doxa_research/__init__.py`, `CHANGELOG.md`, or
`.release-please-manifest.json` versions. Land conventional commits on
`main`; `release-please.yml` opens a Release PR; merging it tags `vX.Y.Z`
and triggers `publish.yml` (TestPyPI → PyPI). See `RELEASE.md`.

Never say in commits:

 🤖 Generated with [Claude Code](https://claude.ai/code)

 or

   Co-Authored-By: Claude <noreply@anthropic.com>

## Release Coordination & Drift Prevention

This repo uses release-please for version management. Releases publish to
PyPI via `publish.yml` when a `vX.Y.Z` tag is pushed. The chain is:
Release PR merge → release-please tags → tag push → publish.yml runs →
PyPI gate awaits approval → upload.

**Direct commits to main never publish.** Only the chain above ships.

### Always sync with origin/main before substantive work

You are NOT the only actor pushing. release-please opens Release PRs
that the maintainer may merge at any time, landing new commits on
origin/main while you're working locally. Stale-base commits cause
push rejections, painful rebases, and `uv.lock` drift.

Mandatory at the top of any session that may produce commits:

```bash
git fetch origin
git status -sb     # check ahead/behind status
# if behind: rebase before doing anything else
git pull --rebase origin main
```

If `git status -sb` shows `[ahead N, behind M]` with `M > 0`, **STOP**
and rebase before committing or pushing. Pushing a stale branch will
fail with "fetch first" — and any local commits may need re-doing if
release-please bumped versions in the meantime.

### After ANY release-please tag, refresh uv.lock

release-please bumps `pyproject.toml`, `src/<pkg>/__init__.py`, and
`.release-please-manifest.json` when it tags — but it does NOT touch
`uv.lock`. Every release leaves the lock's self-version one patch
behind reality, making `git diff uv.lock` noisy on the next `uv` call.

After every merged Release PR:

```bash
git pull --rebase origin main
uv sync                # regenerates uv.lock to match new pyproject version
git add uv.lock
git commit -m "chore(release): sync uv.lock to match pyproject X.Y.Z"
git push
```

This commit is `chore(release):` which is HIDDEN from release-please
(`chore` is `"hidden": true` in `release-please-config.json`) — so it
does NOT trigger another Release PR. Safe to commit standalone.

**Open follow-up**: wire `uv.lock` into release-please's `extra-files`
config so its self-version is bumped automatically. The generic regex
updater is fiddly because of TOML quoting; deferred.

### Don't batch chore-only commits alone with substantive work

Each chore commit pushes a new origin/main commit, which may race
against release-please's PR updates or against the maintainer merging.
If you need to make multiple chore-style fixes (uv.lock sync, config
tweaks), squash them into a single commit at the end of the session.

### Releases happen on Release-PR merge, not on regular push

Full sequence:

1. Land a `feat:`, `fix:`, `perf:`, `refactor:`, `docs:`, `ci:`, or
   `test:` commit on main. NOT `chore:` — that's hidden.
2. release-please.yml fires; opens (or updates) a Release PR titled
   `chore(release): publish vX.Y.Z — review and merge to ship to PyPI`.
3. Review the Release PR's diff. The CHANGELOG entry should honestly
   reflect what will ship. (release-please can occasionally propose
   stale content if the manifest drifted from reality — see CHANGELOG
   entry for v3.0.6 for one such recovery.)
4. Merge the Release PR. release-please tags `vX.Y.Z` via the GitHub
   App token (the App token can retrigger downstream workflows; the
   default `GITHUB_TOKEN` cannot).
5. `publish.yml` fires on the tag push. Build → TestPyPI (auto OIDC)
   → PyPI (required-reviewer gate).
6. Maintainer approves the `pypi` deployment in the Actions UI. PyPI
   uploads the wheel + sdist.
7. After publish succeeds, locally `git pull --rebase origin main` to
   absorb the release commit, then `uv sync` + chore commit if uv.lock
   drifted (see above).

The `pypi` GitHub environment is reviewer-gated (maintainer = smorin)
on purpose; the `testpypi` environment is auto-approve.

### Never use `--no-verify` or `LEFTHOOK=0`

The `core.hooksPath` post-rename bug silently bypassed hooks for days
in this repo — combined with `--no-verify` use, problems land on main
undetected. If a hook fails, fix the underlying issue. The only
acceptable bypass is a documented short-lived WIP commit that will be
squashed before push, AND only after you've run the equivalent checks
manually.

If hooks appear to stop firing across all commits, suspect the
`core.hooksPath` setting first (see CONTRIBUTING.md → "If Hooks Stop
Firing (post-rename gotcha)").

### Tag protection

`publish.yml` verifies the tagged commit is reachable from
`origin/main` before building. This is defense in depth — release-please
always tags from main so the check is invisible in normal flow, but
prevents attacker- or accident-tagged non-main commits from triggering
a release.

## Worktree Discipline & Main-Sync Patterns

### Default to worktrees for feature work

When making any change beyond a 1-2 line fix, work from a feature
branch in a separate worktree, NOT on main directly. Worktrees give
you:

- A separate working directory immune to release-please activity on
  main while you're working
- Your own remote-tracking branch with `[ahead/behind]` counters
  against your feature branch, not against main
- The main worktree (this repo) stays at HEAD-of-main, ready for
  quick sanity checks, lefthook-hook testing, etc.

Setup:

```bash
# From the main repo (/Users/stevemorin/c/doxa-research):
git worktree add ../doxa-research-worktrees/feat-my-thing -b feat/my-thing
cd ../doxa-research-worktrees/feat-my-thing
# Work, commit, push -u origin feat/my-thing
# Open PR via gh pr create
```

Cleanup after merge:

```bash
cd /Users/stevemorin/c/doxa-research            # back to main
git worktree remove ../doxa-research-worktrees/feat-my-thing
git branch -D feat/my-thing                     # if locally still around
git fetch --prune                               # clear gone remote branches
```

### Main is for releases only

Direct commits to main are reserved for:

- Hot-fix releases sized for a single commit
- Dependabot merges (when CI is green)
- release-please's own bump commits (via Release PR merge)
- Documentation-only changes too small to justify a PR

Everything else: branch → PR → merge. The `pypi` GitHub environment's
reviewer gate is the LAST defense; the first is your own discipline.

### The "fetch + status -sb" prelude

ALWAYS at the top of any work session in the main repo:

```bash
git fetch origin
git status -sb     # check [ahead N, behind M]
```

If `[behind M]` for any `M > 0`, STOP and rebase before doing anything
else:

```bash
git pull --rebase origin main
```

If uv.lock conflicts (common when release-please tagged a release
that your local missed):

```bash
git checkout --theirs uv.lock      # take origin's lock as canonical
uv sync                            # absorb new pyproject version
git add uv.lock
git rebase --continue              # if mid-rebase
```

### After every release-please tag, `uv sync` locally

release-please bumps pyproject.toml + __init__.py + manifest when it
tags. The CI `sync-uv-lock` job in `release-please.yml` ALSO commits
the new uv.lock — but only on the CI side. Your local clone won't
have those commits until you pull.

After every Release PR merge:

```bash
git pull --rebase origin main      # pulls both the release bump AND the sync-uv-lock commit
uv sync                            # idempotent; should be a no-op if CI already synced
```

If `git diff uv.lock` shows changes after `uv sync`, something's out
of sync; investigate before committing.

### "Fetch first" push rejection — the recovery dance

When you push and see:

```
! [rejected]        main -> main (fetch first)
```

Origin moved while you were working. Don't force-push. Run:

```bash
git fetch origin
git pull --rebase origin main
git push
```

Repeat if origin moves AGAIN during your rebase (rare but happens
when multiple Release PRs cascade or dependabot is also merging).

### uv.lock conflict resolution recipe (memorize)

This happened five times in one session. The recipe:

```bash
# During a rebase, uv.lock shows as conflict (UU in `git status`):
git checkout --theirs uv.lock      # accept origin's resolution
uv sync                            # apply local pyproject changes on top
git add uv.lock
git rebase --continue              # OR: git commit, if not in rebase
```

Why `--theirs` instead of `--ours`: origin's `uv.lock` incorporates
the latest dependabot / release-please bumps already merged on main.
Yours is from your local edit session. Origin's is canonical for the
DEPENDENCIES; we re-apply OUR pyproject change on top of it via
`uv sync`.

### When NOT to use a worktree

- Single-line typo fixes that don't need their own PR
- Touching files outside the Python module (README, CHANGELOG entries)
  where conflict probability is near zero
- Emergency hot-fixes where the overhead of branch/PR/merge is too much
- Active session where the main worktree is clean AND main hasn't moved
  since you fetched

Trust your judgment — but when in doubt, branch.

### Hook discipline under main-sync

See also CONTRIBUTING.md → "If Hooks Stop Firing (post-rename gotcha)".

After a `git worktree remove` + parent-dir rename, the hooks path can
silently break. Verify with:

```bash
git config --get core.hooksPath
ls -d "$(git config --get core.hooksPath)" 2>&1
```

If the path is set but missing, `git config --unset core.hooksPath`
to fall back to in-tree hooks.

## API and UV References
Please check @planning/references.md URLs to look up detail about the openai, perplexity, and UV documentation.

## OpenAI API Key
get the openai api key from @openai.env

# Test-driven development.

- Always when creating an implementation plan, make the first thing to design the tests for each task and the milestone. The testing design should be the first step. Then, in the implementation, either a test should be created and then the code updated to pass, or a series of tests should be created and then implementation should pass them all. But it should be test-driven development.
