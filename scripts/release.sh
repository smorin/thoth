#!/usr/bin/env bash
set -euo pipefail

# Release helper — called by `just release [version]`
# Validates environment, runs quality checks, tags, and pushes.

VERSION="${1:-}"
PYPROJECT_V=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')

err() { echo ""; echo "ERROR: $1"; shift; for line in "$@"; do echo "  $line"; done; echo ""; exit 1; }

# Default to pyproject.toml version if not specified
if [ -z "$VERSION" ]; then
    VERSION="$PYPROJECT_V"
    echo "Using version from pyproject.toml: $VERSION"
fi

# Validate semver format
if ! echo "$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'; then
    err "'$VERSION' is not a valid semver version" \
        "Expected format: X.Y.Z (e.g. 2.5.0)" \
        "Usage: just release $PYPROJECT_V"
fi

# Check version matches pyproject.toml
if [ "$VERSION" != "$PYPROJECT_V" ]; then
    err "Version mismatch: '$VERSION' does not match pyproject.toml '$PYPROJECT_V'" \
        "Either release the checked-in version:" \
        "  just release $PYPROJECT_V" \
        "Or bump pyproject.toml first:" \
        "  just bump-patch   (${PYPROJECT_V} → next patch)" \
        "  just bump-minor   (${PYPROJECT_V} → next minor)" \
        "  just bump-major   (${PYPROJECT_V} → next major)"
fi

# Check tag doesn't already exist
if git rev-parse "v$VERSION" >/dev/null 2>&1; then
    err "Tag v$VERSION already exists — this version has already been released" \
        "Latest tags: $(git tag --sort=-v:refname | head -5 | tr '\n' ' ')" \
        "To release a new version, bump first:" \
        "  just bump-patch" \
        "  just release"
fi

# Ensure uv.lock is in sync with pyproject.toml and committed
echo "==> Checking uv.lock is up-to-date..."
if ! uv lock --check 2>/dev/null; then
    echo "    uv.lock is out of sync — updating..."
    uv lock
fi
if [ -n "$(git status --porcelain uv.lock)" ]; then
    git add uv.lock
    git commit -- uv.lock -m "chore: update uv.lock for v$VERSION"
    echo "    Committed updated uv.lock"
fi

# Check for clean working tree
if [ -n "$(git status --porcelain)" ]; then
    echo ""
    echo "ERROR: Working tree has uncommitted changes"
    echo ""
    git status --short
    echo ""
    echo "  Commit your changes first:"
    echo "    git add -A && git commit -m 'your message'"
    echo "  Or stash them temporarily:"
    echo "    git stash"
    echo ""
    exit 1
fi

# Check on main branch
BRANCH=$(git branch --show-current)
if [ "$BRANCH" != "main" ]; then
    err "Releases must be from the 'main' branch (currently on '$BRANCH')" \
        "Switch to main and merge your changes:" \
        "  git checkout main" \
        "  git merge $BRANCH"
fi

echo "==> Running quality checks (format, lint, typecheck, security, test)..."
if ! uv run ruff format --check src/thoth/; then
    err "Format check failed — files need formatting" \
        "Run 'just format' to auto-fix, then commit before releasing"
fi
if ! uv run ruff check src/thoth/; then
    err "Lint check failed — lint issues found" \
        "Run 'just lint' to auto-fix, then commit before releasing"
fi
if ! just typecheck; then
    err "Typecheck failed — fix type errors before releasing"
fi
if ! just security; then
    err "Security check failed — fix security issues before releasing"
fi
if ! just test; then
    err "Tests failed — fix failing tests before releasing"
fi

echo "==> Generating changelog..."
if ! just changelog "$VERSION"; then
    err "Changelog generation failed" \
        "Make sure git-cliff is available:" \
        "  uvx git-cliff --version" \
        "You can also skip and generate it manually later"
fi

# Auto-commit changelog if it changed
if [ -n "$(git status --porcelain CHANGELOG.md)" ]; then
    git add CHANGELOG.md
    git commit -- CHANGELOG.md -m "chore(release): update CHANGELOG.md for v$VERSION"
    echo "    Committed updated CHANGELOG.md"
fi

echo "==> Building distribution..."
just clean
if ! just build; then
    err "Build failed — fix the build errors above" \
        "Try building manually to debug:" \
        "  uv build"
fi

# Check local is up-to-date with remote (after all local release commits)
git fetch origin main --quiet
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)
if [ "$LOCAL" != "$REMOTE" ]; then
    AHEAD=$(git rev-list origin/main..HEAD --count)
    BEHIND=$(git rev-list HEAD..origin/main --count)
    if [ "$BEHIND" -gt 0 ]; then
        err "Local main is behind origin/main (${AHEAD} ahead, ${BEHIND} behind)" \
            "Local:  ${LOCAL:0:12}" \
            "Remote: ${REMOTE:0:12}" \
            "Pull the latest changes:" \
            "  git pull --rebase origin main"
    fi
fi

echo "==> Tagging v$VERSION and pushing..."
git tag "v$VERSION"
if ! git push origin main; then
    echo ""
    echo "ERROR: Failed to push main to origin"
    echo ""
    echo "  The changelog commit is local. To retry:"
    echo "    git push origin main"
    echo ""
    exit 1
fi
if ! git push origin "v$VERSION"; then
    echo ""
    echo "ERROR: Failed to push tag v$VERSION to origin"
    echo ""
    echo "  The tag was created locally. To retry:"
    echo "    git push origin v$VERSION"
    echo "  To undo the local tag and start over:"
    echo "    git tag -d v$VERSION"
    echo ""
    exit 1
fi

echo ""
echo "Release v$VERSION tagged and pushed!"
echo "CI will publish to TestPyPI → PyPI."
echo ""
echo "  Monitor: https://github.com/$(git remote get-url origin | sed -E 's|.*github\.com[:/]||; s|\.git$||')/actions"
