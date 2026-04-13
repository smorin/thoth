# Release Guide

This document covers the full release process for Thoth — from toolchain architecture through the step-by-step workflow, CI/CD pipeline internals, OIDC trusted publishing setup, and troubleshooting.

## Table of Contents

- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Versioning](#versioning)
- [Release Checklist](#release-checklist)
- [Step-by-Step Release Process](#step-by-step-release-process)
- [CI/CD Pipeline](#cicd-pipeline)
- [OIDC Trusted Publishing Setup](#oidc-trusted-publishing-setup)
- [Local Build & Publish](#local-build--publish)
- [Troubleshooting](#troubleshooting)

---

## Architecture

The release stack is built entirely on [uv](https://docs.astral.sh/uv/) — no hatch, no twine, no separate publish action.

```
┌─────────────────────────────────────────────────────────┐
│                    Release Pipeline                      │
│                                                          │
│  git tag v*                                              │
│      │                                                   │
│      ▼                                                   │
│  GitHub Actions: publish.yml                            │
│      │                                                   │
│      ├── [build job]                                     │
│      │       uv build  ──►  dist/*.whl + dist/*.tar.gz  │
│      │                                                   │
│      ├── [publish-testpypi job]                          │
│      │       uv publish --trusted-publishing always      │
│      │       --publish-url https://test.pypi.org/legacy/ │
│      │                                                   │
│      └── [publish-pypi job]                              │
│              uv publish --trusted-publishing always      │
└─────────────────────────────────────────────────────────┘
```

### Toolchain

| Concern | Tool | Details |
|---------|------|---------|
| Build backend | `uv_build` | PEP 517 backend, bundled with uv |
| Package manager | `uv` | Dependency resolution, venv, lock file |
| Build | `uv build` | Produces wheel (`.whl`) and source dist (`.tar.gz`) |
| Publish | `uv publish` | Uploads to PyPI/TestPyPI via OIDC or token |
| Task runner | `make` | Wraps uv commands for local convenience |
| CI/CD | GitHub Actions | Automated test, lint, typecheck, publish |
| Auth | OIDC trusted publishing | No stored API tokens — GitHub mints short-lived tokens |

### Key Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Project metadata, version, build-system config |
| `src/thoth/__init__.py` | Package version (`__version__`) |
| `uv.lock` | Locked dependency graph (committed to repo) |
| `.github/workflows/ci.yml` | Runs tests, lint, typecheck on push/PR |
| `.github/workflows/publish.yml` | Builds and publishes on `v*` tag push |
| `Makefile` | Local task automation (`make build`, `make publish`) |
| `CHANGELOG.md` | Release notes, one section per version |

---

## Prerequisites

**Required:**
- [uv](https://docs.astral.sh/uv/) — install with `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Git with push access to `main` and tag push rights on the repo

**For manual publishing (bypassing CI):**
- A PyPI API token, or OIDC trusted publishing configured for your local environment

**Verify your environment:**
```bash
make check   # checks for uv and python3
```

---

## Versioning

Thoth uses [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`.

| Increment | When |
|-----------|------|
| `PATCH` | Bug fixes, dependency bumps, documentation changes |
| `MINOR` | New backward-compatible features, new commands or providers |
| `MAJOR` | Breaking CLI changes or incompatible config format changes |

The version is declared in two places — keep them in sync:

```toml
# pyproject.toml
[project]
version = "2.5.0"
```

```python
# src/thoth/__init__.py
__version__ = "2.5.0"
```

Git tags follow the `v{version}` format (e.g., `v2.5.0`). The tag is the release trigger — pushing a `v*` tag kicks off the full publish workflow.

---

## Release Checklist

Before creating a release, verify all of the following:

- [ ] All CI checks pass on `main` (`push` triggers `ci.yml`)
- [ ] `./thoth_test -r --provider mock` passes with no new failures
- [ ] `pyproject.toml` version is updated to the new version
- [ ] `src/thoth/__init__.py` `__version__` matches `pyproject.toml`
- [ ] `CHANGELOG.md` has an entry for the new version with release date
- [ ] No uncommitted changes (`git status` is clean)
- [ ] You are on the `main` branch

---

## Step-by-Step Release Process

### 1. Update the version

Edit both version declarations to match:

```toml
# pyproject.toml
[project]
version = "2.6.0"   # new version
```

```python
# src/thoth/__init__.py
__version__ = "2.6.0"
```

### 2. Update CHANGELOG.md

Add a section at the top (below the `# Changelog` header):

```markdown
## [2.6.0] — 2026-04-15

### Added
- ...

### Fixed
- ...

### Changed
- ...
```

### 3. Run all checks locally

```bash
make check-all          # lint both src/thoth/ and thoth_test
./thoth_test -r --provider mock   # run full test suite
```

All must pass before proceeding.

### 4. Commit the release

```bash
git add pyproject.toml src/thoth/__init__.py CHANGELOG.md
git commit -m "chore: release v2.6.0"
git push origin main
```

Wait for the CI pipeline (`ci.yml`) to go green on `main`.

### 5. Tag and push

```bash
git tag v2.6.0
git push origin v2.6.0
```

Pushing the `v*` tag triggers `publish.yml` automatically.

### 6. Monitor the publish workflow

Go to the **Actions** tab on GitHub and watch the `Publish` workflow:

1. **Build** — builds `dist/*.whl` and `dist/*.tar.gz`
2. **Publish to TestPyPI** — validates the package on [test.pypi.org](https://test.pypi.org/project/thoth/)
3. **Publish to PyPI** — publishes to [pypi.org/project/thoth/](https://pypi.org/project/thoth/)

Each publish job requires manual approval via its GitHub environment (`testpypi` → `pypi`) if environment protection rules are configured.

### 7. Verify the release

```bash
# Install and run from PyPI
uvx thoth==2.6.0 --version

# Or with pip
pip install thoth==2.6.0
thoth --version
```

---

## CI/CD Pipeline

### `ci.yml` — Continuous Integration

Triggered on every push to `main` and every pull request targeting `main`.

```
push/PR to main
    │
    ├── lint (ubuntu-latest)
    │       uv run ruff format --check src/thoth/
    │       uv run ruff check src/thoth/
    │
    ├── typecheck (ubuntu-latest, continue-on-error)
    │       uv run ty check src/thoth/
    │
    ├── yamllint (ubuntu-latest)
    │       uvx yamllint -c .yamllint .
    │
    ├── actionlint (ubuntu-latest)
    │       actionlint
    │
    └── test (matrix: macOS + Ubuntu × Python 3.11, 3.12, 3.13)
            chmod +x thoth thoth_test
            ./thoth_test -r --provider mock
```

Jobs run in parallel. The `test` matrix runs 6 combinations (2 OS × 3 Python versions). Typecheck is informational (`continue-on-error: true`) due to pre-existing type annotations in the codebase.

### `publish.yml` — Release Publishing

Triggered only on tag pushes matching `v*` (e.g., `v2.5.0`, `v2.6.0`).

```
push tag v*
    │
    └── build (ubuntu-latest)
            astral-sh/setup-uv@v5
            uv build
            upload artifact: dist/
                │
                └── publish-testpypi (environment: testpypi)
                        permissions: id-token: write
                        uv publish --trusted-publishing always
                        --publish-url https://test.pypi.org/legacy/
                            │
                            └── publish-pypi (environment: pypi)
                                    permissions: id-token: write
                                    uv publish --trusted-publishing always
```

Jobs are sequential: `build → publish-testpypi → publish-pypi`. A failure at any stage stops the pipeline.

---

## OIDC Trusted Publishing Setup

Thoth uses [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/) via OpenID Connect (OIDC). No API tokens are stored as GitHub secrets — GitHub Actions mints a short-lived OIDC token that PyPI accepts directly.

### How It Works

1. The workflow requests an OIDC token from GitHub (`id-token: write` permission)
2. `uv publish --trusted-publishing always` presents the token to PyPI
3. PyPI validates the token against the registered trusted publisher configuration
4. If valid, the upload is accepted

### Initial Setup (one-time, per maintainer)

You must register the GitHub Actions workflow as a trusted publisher on both PyPI and TestPyPI before the first release.

**On TestPyPI** ([test.pypi.org/manage/account/publishing/](https://test.pypi.org/manage/account/publishing/)):

| Field | Value |
|-------|-------|
| PyPI Project Name | `thoth` |
| Owner | `smorin` |
| Repository name | `thoth` |
| Workflow filename | `publish.yml` |
| Environment name | `testpypi` |

**On PyPI** ([pypi.org/manage/account/publishing/](https://pypi.org/manage/account/publishing/)):

| Field | Value |
|-------|-------|
| PyPI Project Name | `thoth` |
| Owner | `smorin` |
| Repository name | `thoth` |
| Workflow filename | `publish.yml` |
| Environment name | `pypi` |

### GitHub Environments

Two GitHub environments must exist in the repository settings ([Settings → Environments](https://github.com/smorin/thoth/settings/environments)):

- **`testpypi`** — used by the `publish-testpypi` job
- **`pypi`** — used by the `publish-pypi` job

Optionally add required reviewers to the `pypi` environment for an approval gate before production publishing.

---

## Local Build & Publish

These commands are available for testing builds or publishing manually (e.g., from a maintainer's machine with a token).

```bash
# Build wheel + source distribution
make build
# Output: dist/thoth-2.6.0-py3-none-any.whl
#         dist/thoth-2.6.0.tar.gz

# Publish to TestPyPI (for validation)
UV_PUBLISH_TOKEN=<your-testpypi-token> make publish-test

# Publish to PyPI
UV_PUBLISH_TOKEN=<your-pypi-token> make publish
```

To inspect a built distribution before publishing:

```bash
uvx twine check dist/*
```

---

## Troubleshooting

### Build fails: `uv_build` not found

Ensure uv is up to date. `uv_build` is distributed as part of uv's bundled backend — it does not need to be installed separately.

```bash
uv self update
uv build
```

### Publish fails: `403 Forbidden` on PyPI

The OIDC trusted publisher is not configured, or the environment name / workflow filename does not match exactly what was registered on PyPI. Verify:

1. The workflow file is named `publish.yml` (not `publish.yaml`)
2. The environment in the workflow job matches the environment registered on PyPI (`pypi` / `testpypi`)
3. The repository owner (`smorin`) and name (`thoth`) match exactly

### Publish fails: `400 File already exists`

A distribution with this version already exists on PyPI. PyPI does not allow overwriting. You must bump the version and release again.

### Tag was pushed but workflow did not trigger

Confirm the tag matches the `v*` pattern (e.g., `v2.6.0` not `2.6.0`). Check the Actions tab — filter by the `Publish` workflow.

### TestPyPI publish succeeds but PyPI job is blocked

If the `pypi` GitHub environment has required reviewers configured, you must approve the deployment from the Actions UI before the job runs.

### Version on PyPI doesn't match `pyproject.toml`

The build is stamped with whatever version is in `pyproject.toml` at the time `uv build` runs. Ensure both `pyproject.toml` and `src/thoth/__init__.py` were committed before the tag was pushed.
