# Contributing to Doxa Research

## Setup

```bash
# Clone and enter the project
git clone https://github.com/smorin/doxa-research.git
cd doxa-research

# Check bootstrap environment (uv, python3, just)
make env-check

# Install git hooks (see "If hooks stop firing" below)
lefthook install

# Install the package in editable mode (creates the doxa-research command)
uv sync
```

## Running Tests

```bash
# Run tests with mock provider (no API keys needed)
./doxa_test -r

# Run specific test pattern
./doxa_test -r -t "async" -v

# Run with a real provider (requires API key)
./doxa_test -r --provider openai -t M8T
```

## Code Quality

```bash
# Check linting and types (src/doxa_research/)
just check

# Auto-fix issues (src/doxa_research/)
just fix

# Check both src/doxa_research/ and doxa_test
just check-all
```

## Submitting a PR

1. Create a branch: `git checkout -b feat/your-feature`
2. Make your changes (tests first per TDD practice)
3. Run `just check-all` and `./doxa_test -r` — both must pass
4. Push and open a PR against `main`

## API Keys

Tests use the mock provider by default — no API keys are required for `./doxa_test -r`.

For live provider tests set:
```bash
export OPENAI_API_KEY="sk-..."
export PERPLEXITY_API_KEY="pplx-..."
```

## If Hooks Stop Firing (post-rename gotcha)

If your local git appears to bypass all hooks on commit / push — no
ruff, no commitlint, no yamllint, no tests — check whether
`core.hooksPath` is pointing at a path that no longer exists:

```bash
git config --get core.hooksPath
ls -d "$(git config --get core.hooksPath)" 2>&1   # path must exist
```

When lefthook installs hooks, it sets `core.hooksPath` to an absolute
path (e.g. `/Users/you/c/<project>/.git/hooks`). If you ever rename the
directory containing the repo, that absolute path becomes stale; git
silently looks for hooks at the missing path and finds none — every
commit and push bypasses all hooks.

Fix:

```bash
# Option 1: unset the override so git falls back to the default in-tree
# .git/hooks/ (works if lefthook's wrappers are already there)
git config --unset core.hooksPath

# Option 2: reset the hooksPath to match the current repo location
lefthook install --force
```

Verify hooks fire again:

```bash
git commit --allow-empty -m "test: verify hooks"   # should show lefthook output
```

This trap is silent — there's no warning when a stale hooksPath
deactivates everything. After renaming the repo directory, always
run `lefthook install --force` or sanity-check with the steps above.
