# Default recipe - show help
default:
    @just --list --unsorted

# ─── Setup ────────────────────────────────────────────────────────────

# Install all dependencies
[group: 'setup']
install:
    uv sync

# Install full local dev toolchain: uv deps + commitlint (bun) + git hooks
[group: 'setup']
install-dev: install
    bun install
    just install-lefthook

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
all: format lint typecheck security test

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

# Run full test suite (pytest in parallel + thoth_test integration suite)
[group: 'testing']
test:
    uv run pytest tests/ -n auto -v
    ./thoth_test -r

# Run pytest suite serially (for debugging xdist flakiness)
[group: 'testing']
test-serial:
    uv run pytest tests/ -v

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

# ─── Release ──────────────────────────────────────────────────────────
# Releases are automated via release-please. Land conventional commits on
# main; release-please opens a Release PR with the bumped version +
# CHANGELOG.md. Merging that PR tags `vX.Y.Z`, which triggers publish.yml
# to push to TestPyPI and PyPI via OIDC trusted publishing.

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

# Install lefthook, gitleaks, and git hooks
[group: 'git-hooks']
install-lefthook: install-gitleaks
    @if command -v lefthook > /dev/null 2>&1; then \
        echo "lefthook is already installed"; \
    else \
        brew install lefthook; \
    fi
    lefthook install

# Install gitleaks (used by the pre-commit secret scan)
[group: 'git-hooks']
install-gitleaks:
    ./scripts/install-gitleaks.sh
