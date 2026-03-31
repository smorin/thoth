# Contributing to Thoth

## Setup

```bash
# Clone and enter the project
git clone https://github.com/smorin/thoth.git
cd thoth

# Check environment dependencies
make check

# Install git hooks
lefthook install

# Install the package in editable mode (creates the thoth command)
uv sync
```

## Running Tests

```bash
# Run tests with mock provider (no API keys needed)
./thoth_test -r

# Run specific test pattern
./thoth_test -r -t "async" -v

# Run with a real provider (requires API key)
./thoth_test -r --provider openai -t M8T
```

## Code Quality

```bash
# Check linting and types
make check

# Auto-fix issues
make fix

# Check the test suite too
make check-all
```

## Submitting a PR

1. Create a branch: `git checkout -b feat/your-feature`
2. Make your changes (tests first per TDD practice)
3. Run `make check-all` and `./thoth_test -r` — both must pass
4. Push and open a PR against `main`

## API Keys

Tests use the mock provider by default — no API keys are required for `./thoth_test -r`.

For live provider tests set:
```bash
export OPENAI_API_KEY="sk-..."
export PERPLEXITY_API_KEY="pplx-..."
```
