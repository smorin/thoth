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

### Step 1: Update the version

Edit `pyproject.toml`:
```toml
[project]
version = "2.6.0"
```

Edit `src/thoth/__init__.py`:
```python
__version__ = "2.6.0"
```

### Step 2: Update CHANGELOG.md

Move items from `[Unreleased]` to a new versioned section:
```markdown
## [2.6.0] — 2026-04-15

### Added
- ...
```

### Step 3: Commit and tag

```bash
git add pyproject.toml src/thoth/__init__.py CHANGELOG.md
git commit -m "chore: release v2.6.0"
git tag v2.6.0
git push origin main
git push origin v2.6.0
```

Pushing the `v*` tag triggers `publish.yml` automatically.

### Step 4: Monitor the workflow

Go to **Actions → Publish** in GitHub:
1. **build** job creates wheel + sdist in `dist/`
2. **publish-testpypi** job publishes to https://test.pypi.org/project/thoth/
3. **publish-pypi** job publishes to https://pypi.org/project/thoth/

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
