# Migration from `thoth` to `doxa-research`

This project was previously released as `thoth` (versions ≤ 2.5.0 on PyPI)
and was renamed to `doxa-research` in version 3.0.0. The rename touched
several user-facing names. **Existing users must migrate manually** — there
is no automatic config migration.

## What changed

| Aspect | Before (≤ 2.5.0) | After (≥ 3.0.0) |
|---|---|---|
| PyPI distribution | `thoth` | `doxa-research` |
| CLI command | `thoth` | `doxa` (and `doxa-research` alias) |
| Python module | `thoth` | `doxa_research` |
| Environment variables (project) | `THOTH_*` | `DOXA_*` |
| User config directory | `~/.config/thoth/` | `~/.config/doxa/` |
| Test runner script | `./thoth_test` | `./doxa_test` |

Provider-namespaced API key variables (`OPENAI_API_KEY`,
`PERPLEXITY_API_KEY`, `GEMINI_API_KEY`) are unchanged.

## How to migrate

1. **Uninstall the old package**:
   ```bash
   uv tool uninstall thoth          # if installed via uv tool install
   # or
   pip uninstall thoth              # if installed via pip
   ```

2. **Install the new package**:
   ```bash
   uvx doxa-research                # try without installing
   uv tool install doxa-research    # permanent install via uv
   # or
   pip install doxa-research
   ```

3. **Move your config directory** (if you had one):
   ```bash
   mv ~/.config/thoth ~/.config/doxa
   doxa providers list              # verify the new config loads cleanly
   ```

4. **Rename project environment variables** in your shell config
   (`~/.zshrc`, `~/.bashrc`, etc.):
   ```bash
   # Before:
   export THOTH_PROFILE="default"
   # After:
   export DOXA_PROFILE="default"
   ```

5. **Update scripts and aliases** referencing `thoth` to use `doxa`.

6. **(Optional) Smoke-test in verbose mode** to confirm everything works:
   ```bash
   doxa providers list --verbose
   doxa ask "test prompt" --verbose --provider mock
   ```

## Why the rename?

*Doxa* (Greek: δόξα) means "opinion", "belief", or "received wisdom" —
fitting for a tool that synthesizes multiple AI perspectives to surface
consensus and divergence across views. See the
[About the name](README.md#about-the-name) section of the README for the
etymology and design rationale.

## Compatibility window

There is no compatibility shim. Old `thoth` versions on PyPI (≤ 2.5.0)
continue to work but receive no further updates. To get bug fixes,
security updates, new providers (e.g. Gemini Deep Research), and new
modes, migrate to `doxa-research`.

For a full changelog of what's new since the rename, see
[CHANGELOG.md](CHANGELOG.md).
