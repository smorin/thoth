# Default recipe - show help
default:
    @just --list --unsorted

# ─── Setup ────────────────────────────────────────────────────────────

# Install all dependencies
[group: 'setup']
install:
    uv sync

# Install thoth to /usr/local/bin
[group: 'setup']
install-bin:
    cp thoth /usr/local/bin/
    chmod +x /usr/local/bin/thoth

# Check environment dependencies
[group: 'setup']
check:
    uv run ruff check src/thoth/ --fix
    uv run ty check src/thoth/

# Clean build artifacts
[group: 'setup']
clean:
    rm -rf build/ dist/ *.egg-info
    rm -rf .pytest_cache/ .ruff_cache/
    rm -rf htmlcov/ .coverage
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find . -type f -name ".DS_Store" -delete 2>/dev/null || true

# ─── Quality ──────────────────────────────────────────────────────────

# Run all checks (format, lint, typecheck, security, test)
[group: 'quality']
all: format lint typecheck security test test-vcr

# Format src/thoth/ package
[group: 'quality']
format:
    uv run ruff format src/thoth/

# Lint src/thoth/ package
[group: 'quality']
lint:
    uv run ruff check src/thoth/ --fix

# Type check src/thoth/ package
[group: 'quality']
typecheck:
    uv run ty check src/thoth/

# Run bandit security linter
[group: 'quality']
security:
    uvx bandit -r src/ -ll

# Auto-fix and format src/thoth/
[group: 'quality']
fix:
    uv run ruff check --fix src/thoth/
    uv run ruff format src/thoth/

# Format test suite
[group: 'quality']
test-format:
    uv tool run ruff format thoth_test

# Lint test suite
[group: 'quality']
test-lint:
    uv tool run ruff check thoth_test

# Type check test suite
[group: 'quality']
test-typecheck:
    uv tool run ty check thoth_test

# Auto-fix and format test suite
[group: 'quality']
test-fix:
    uv tool run ruff check --fix thoth_test
    uv tool run ruff format thoth_test

# Format both package and test suite
[group: 'quality']
format-all: format test-format

# Lint both package and test suite
[group: 'quality']
lint-all: lint test-lint

# Run all checks on entire codebase
[group: 'quality']
check-all: lint typecheck test-lint test-typecheck

# Auto-fix and format entire codebase
[group: 'quality']
fix-all: fix test-fix

# ─── Testing ──────────────────────────────────────────────────────────

# Run test suite
[group: 'testing']
test:
    ./thoth_test -r

# Run tests skipping interactive mode (fast, CI-safe)
[group: 'testing']
test-skip-interactive:
    ./thoth_test -r --provider mock --skip-interactive

# Run VCR cassette replay tests
[group: 'testing']
test-vcr:
    uv run pytest tests/test_vcr_openai.py -v

# Regenerate pytest snapshot files
[group: 'testing']
update-snapshots:
    uv run pytest --snapshot-update

# ─── Versioning ───────────────────────────────────────────────────────

# Show current version from pyproject.toml
[group: 'versioning']
current-version:
    @grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/'

# Bump patch version (2.5.0 → 2.5.1)
[group: 'versioning']
bump-patch:
    #!/usr/bin/env bash
    set -euo pipefail
    uvx bump-my-version bump patch
    uv lock
    NEW_V=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
    git add pyproject.toml src/thoth/__init__.py uv.lock
    git commit -m "chore: bump version to $NEW_V"
    echo "Bumped to $NEW_V"
    echo "  Next: git push origin main"

# Bump minor version (2.5.0 → 2.6.0)
[group: 'versioning']
bump-minor:
    #!/usr/bin/env bash
    set -euo pipefail
    uvx bump-my-version bump minor
    uv lock
    NEW_V=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
    git add pyproject.toml src/thoth/__init__.py uv.lock
    git commit -m "chore: bump version to $NEW_V"
    echo "Bumped to $NEW_V"
    echo "  Next: git push origin main"

# Bump major version (2.5.0 → 3.0.0)
[group: 'versioning']
bump-major:
    #!/usr/bin/env bash
    set -euo pipefail
    uvx bump-my-version bump major
    uv lock
    NEW_V=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
    git add pyproject.toml src/thoth/__init__.py uv.lock
    git commit -m "chore: bump version to $NEW_V"
    echo "Bumped to $NEW_V"
    echo "  Next: git push origin main"

# ─── Release ──────────────────────────────────────────────────────────

# Generate CHANGELOG.md from git history (requires git-cliff)
[group: 'release']
changelog version="":
    #!/usr/bin/env bash
    if [ -n "{{version}}" ]; then
        uvx git-cliff --tag "v{{version}}" -o CHANGELOG.md
    else
        uvx git-cliff -o CHANGELOG.md
    fi

# Build distribution (wheel + sdist)
[group: 'release']
build:
    uv build

# Publish to TestPyPI (requires OIDC or UV_PUBLISH_TOKEN)
[group: 'release']
publish-test:
    uv publish --publish-url https://test.pypi.org/legacy/

# Publish to PyPI (requires OIDC or UV_PUBLISH_TOKEN)
[group: 'release']
publish:
    uv publish

# Tag and push a release (triggers CI publish workflow)
[group: 'release']
release version="":
    ./scripts/release.sh {{version}}

# ─── Dev ──────────────────────────────────────────────────────────────

# Show thoth help
[group: 'dev']
dev:
    ./thoth --help

# Run example research prompt
[group: 'dev']
run:
    ./thoth "What is quantum computing?" --provider mock

# Initialize thoth configuration
[group: 'dev']
init:
    ./thoth init

# Quick smoke test of basic functionality
[group: 'dev']
smoke-test:
    ./thoth --version
    ./thoth --help

# ─── Virtual Environment ─────────────────────────────────────────────

# Create virtual environment
[group: 'venv']
venv:
    #!/usr/bin/env bash
    if [ ! -d ".venv" ]; then
        uv venv --python 3.11
        echo "Virtual environment created. Activate with: source .venv/bin/activate"
    else
        echo "Virtual environment already exists. Activate with: source .venv/bin/activate"
    fi

# Install package and dependencies into virtual environment
[group: 'venv']
venv-install: venv
    uv pip install -e ".[dev]"

# Sync exact dependencies
[group: 'venv']
venv-sync: venv
    uv sync

# Remove virtual environment
[group: 'venv']
venv-clean:
    rm -rf .venv

# ─── Git Hooks (lefthook) ────────────────────────────────────────────

# Install lefthook and git hooks
[group: 'git-hooks']
install-lefthook:
    @if command -v lefthook > /dev/null 2>&1; then \
        echo "lefthook is already installed"; \
    else \
        brew install lefthook; \
    fi
    lefthook install
