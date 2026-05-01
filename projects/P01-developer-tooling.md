# P01 — Developer Tooling & Automation (v2.6.0)

**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)

**Status:** `[x]` Completed (v2.6.0).

**Goal**: Add automated dependency updates, changelog generation, version bumping, GitHub contribution templates, snapshot test tooling, security linting, and devcontainer support.

**Closeout (2026-04-30)**: Implementation tasks shipped in v2.6.0. The remaining one-shot verification checklist (TS01–TS06 + the T13 wrap-up) is closed as `[-]` won't-fix — the same checks now run continuously via lefthook (bandit, yamllint, ruff/ty), CI, and release-please (`make bump`/`make changelog` superseded). A discrete project-level pass adds no signal beyond the daily gate.

### Tests & Tasks
- [-] [P01-TS01] Verify `snapshot_report.html` does not appear in `git status` after test run — won't fix; superseded by `.gitignore` entry
- [x] [P01-T01] Add `snapshot_report.html` to `.gitignore`
- [-] [P01-TS02] Verify `make update-snapshots` runs without error — won't fix; covered by snapshot test runs
- [x] [P01-T02] Add `update-snapshots` Makefile target
- [-] [P01-TS03] Validate `.github/dependabot.yml` with `uvx yamllint` — won't fix; yamllint runs in lefthook + CI
- [x] [P01-T03] Create `.github/dependabot.yml`
- [-] [P01-TS04] Verify `uvx bandit -r src/thoth/ -ll -q` exits 0 — won't fix; bandit runs in lefthook on every commit
- [x] [P01-T04] Add bandit hook to `lefthook.yml`
- [x] [P01-T05] Create `.github/PULL_REQUEST_TEMPLATE.md`
- [x] [P01-T06] Create `.github/ISSUE_TEMPLATE/bug_report.yml`
- [x] [P01-T07] Create `.github/ISSUE_TEMPLATE/feature_request.yml`
- [-] [P01-TS05] Verify `make bump TYPE=patch` updates version in `pyproject.toml` — won't fix; superseded by release-please automation
- [x] [P01-T08] Add `[tool.bumpversion]` to `pyproject.toml`
- [x] [P01-T09] Add `bump` Makefile target
- [-] [P01-TS06] Verify `make changelog` produces valid CHANGELOG.md output — won't fix; superseded by release-please automation
- [x] [P01-T10] Create `cliff.toml`
- [x] [P01-T11] Add `changelog` and `release` Makefile targets
- [x] [P01-T12] Create `.devcontainer/devcontainer.json`
- [-] [P01-T13] Run all P01-TS01..06 verifications and check off each TS row as it passes — won't fix; verification rolled into lefthook + CI

### Deliverable & Automated Verification
Superseded — see **Closeout** above. The original `make bump` / `make changelog` /
`make release` / `make update-snapshots` / `make check` targets and `cliff.toml`
were removed when the project switched to `just`, lefthook, and release-please.
Their continuous-verification equivalents (yamllint, bandit, ruff/ty, release-please
version bumps) now run on every commit via lefthook + CI.

### Manual Verification
- Open repo in GitHub Codespaces — devcontainer auto-configures environment
- Create a PR — GitHub shows the PR template checklist
- Open a new issue — GitHub shows structured bug/feature forms
