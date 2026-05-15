# Contributing to Doxa Research

## Setup

```bash
# Clone and enter the project
git clone https://github.com/smorin/doxa-research.git
cd doxa-research

# Check bootstrap environment (uv, python3, just)
make env-check

# Install git hooks
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
