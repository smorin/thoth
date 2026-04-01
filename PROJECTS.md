## [x] Project P02: Fix BUG-01 OpenAI Background Status Handling (v2.5.0)
**Goal**: Correctly handle all documented OpenAI Responses API background lifecycle states (`incomplete`, `cancelled`, `queued`, no-status-attr, stale-cache) so the CLI never silently misreports terminal failure states as success.

**Out of Scope**
- BUG-02 (citation parsing), BUG-03 (poll interval), GAP-01 through GAP-05

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

---

## [ ] Project P01: Developer Tooling & Automation (v2.6.0)
**Goal**: Add automated dependency updates, changelog generation, version bumping, GitHub contribution templates, snapshot test tooling, security linting, and devcontainer support.

### Tests & Tasks
- [ ] [P01-TS01] Verify `snapshot_report.html` does not appear in `git status` after test run
- [x] [P01-T01] Add `snapshot_report.html` to `.gitignore`
- [ ] [P01-TS02] Verify `make update-snapshots` runs without error
- [x] [P01-T02] Add `update-snapshots` Makefile target
- [ ] [P01-TS03] Validate `.github/dependabot.yml` with `uvx yamllint`
- [x] [P01-T03] Create `.github/dependabot.yml`
- [ ] [P01-TS04] Verify `uvx bandit -r src/thoth/ -ll -q` exits 0
- [x] [P01-T04] Add bandit hook to `lefthook.yml`
- [x] [P01-T05] Create `.github/PULL_REQUEST_TEMPLATE.md`
- [x] [P01-T06] Create `.github/ISSUE_TEMPLATE/bug_report.yml`
- [x] [P01-T07] Create `.github/ISSUE_TEMPLATE/feature_request.yml`
- [ ] [P01-TS05] Verify `make bump TYPE=patch` updates version in `pyproject.toml`
- [x] [P01-T08] Add `[tool.bumpversion]` to `pyproject.toml`
- [x] [P01-T09] Add `bump` Makefile target
- [ ] [P01-TS06] Verify `make changelog` produces valid CHANGELOG.md output
- [x] [P01-T10] Create `cliff.toml`
- [x] [P01-T11] Add `changelog` and `release` Makefile targets
- [x] [P01-T12] Create `.devcontainer/devcontainer.json`

### Deliverable
```bash
make bump TYPE=patch       # bumps version in pyproject.toml, commits, tags
make changelog             # regenerates CHANGELOG.md from git history
make release TYPE=minor    # bump + changelog in one step
make update-snapshots      # regenerate pytest snapshots
```

### Automated Verification
- `make check` passes
- `uvx yamllint .github/dependabot.yml` exits 0
- `uvx bandit -r src/thoth/ -ll -q` exits 0
- `make bump TYPE=patch` increments version in pyproject.toml

### Manual Verification
- Open repo in GitHub Codespaces — devcontainer auto-configures environment
- Create a PR — GitHub shows the PR template checklist
- Open a new issue — GitHub shows structured bug/feature forms
