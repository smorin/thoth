# Publishing Thoth to PyPI

This guide walks through the one-time setup and recurring release process for publishing thoth to PyPI using OIDC trusted publishing (no API tokens required).

---

## Prerequisites

- PyPI account at https://pypi.org
- TestPyPI account at https://test.pypi.org
- Admin access to the GitHub repository

---

## One-Time Setup

### Step 1: Configure GitHub Environments

Go to **Settings → Environments** in the GitHub repo and create two environments:

| Environment | Required reviewers |
|-------------|-------------------|
| `testpypi`  | None (auto-approve) |
| `pypi`      | Optional: add yourself as required reviewer for extra safety |

### Step 2: Register Trusted Publishing on TestPyPI

1. Log in to https://test.pypi.org
2. Go to **Account Settings → Publishing → Add a new pending publisher**
3. Fill in:
   - **PyPI Project Name**: `thoth`
   - **Owner**: `smorin` (your GitHub username/org)
   - **Repository name**: `thoth`
   - **Workflow filename**: `publish.yml`
   - **Environment name**: `testpypi`

### Step 3: Register Trusted Publishing on PyPI

1. Log in to https://pypi.org
2. Go to **Account Settings → Publishing → Add a new pending publisher**
3. Fill in the same details as TestPyPI but:
   - **Environment name**: `pypi`

> On your first publish, PyPI creates the project automatically.

### Step 4: Verify `pyproject.toml` metadata

Confirm these fields are correct before first publish:

```toml
[project]
name = "thoth"
version = "2.5.0"          # Must match git tag: v2.5.0
authors = [{ name = "Steve Morin", email = "steve.morin@gmail.com" }]

[project.urls]
Homepage = "https://github.com/smorin/thoth"
```

---

## Release Process

Releases are automated by **release-please**. You write conventional-commit messages; release-please opens a Release PR with the version bump and `CHANGELOG.md` update. Merging the Release PR creates the `vX.Y.Z` tag, which triggers `publish.yml`.

### Step 1: Land conventional commits on main

```bash
git commit -m "feat: add new provider"
git commit -m "fix: handle timeout on stream close"
git push origin main
```

The local `commit-msg` lefthook and the `commitlint` CI job enforce the format.

### Step 2: Wait for / review the Release PR

After each push to `main`, `release-please.yml` opens (or updates) a single PR titled `chore(main): release X.Y.Z`. Its diff bumps `pyproject.toml`, `src/thoth/__init__.py`, `.release-please-manifest.json`, and appends to `CHANGELOG.md`.

Verify:
- The proposed version matches the semantic weight of the commits since the last tag.
- The changelog section lists the expected features/fixes.

### Step 3: Merge the Release PR

Merge via the GitHub UI. release-please then:
1. Creates the tag `vX.Y.Z` on the merge commit.
2. Creates a GitHub Release with the changelog section as the body.

### Step 4: Monitor the publish workflow

The tag push triggers **Actions → Publish**:
1. **build** — wheel + sdist in `dist/`
2. **publish-testpypi** — https://test.pypi.org/project/thoth/
3. **publish-pypi** — https://pypi.org/project/thoth/

### Step 5: Verify the release

```bash
# Verify on TestPyPI
pip install --index-url https://test.pypi.org/simple/ thoth==2.6.0
thoth --version

# Verify on PyPI
uvx thoth==2.6.0 --version
# or
pip install thoth==2.6.0
thoth --version
```

---

## Quick Reference

| Value | What to use |
|-------|------------|
| PyPI project name | `thoth` |
| GitHub owner | `smorin` |
| GitHub repo | `thoth` |
| Workflow file | `publish.yml` |
| TestPyPI environment | `testpypi` |
| PyPI environment | `pypi` |
| Tag format | `v2.6.0` |

---

## Local Build (Optional)

To build locally without publishing:
```bash
make build
ls dist/
# thoth-2.6.0-py3-none-any.whl
# thoth-2.6.0.tar.gz
```

To publish manually (requires API token):
```bash
uv publish --token pypi-...
```
