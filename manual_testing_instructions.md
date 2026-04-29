# Manual Testing Guide

> Updated for P14 (Thoth CLI Ergonomics v1) — the most recent batch of CLI changes. Earlier sections covering response-storage and per-config timeouts have been archived.

## Prerequisites

```bash
# 1. Bootstrap environment (one-time)
make env-check                  # Confirms uv, python3, just, bun present

# 2. Install dependencies
just install                    # Or: just install-dev (also installs git hooks)

# 3. Ensure API keys (env-vars are recommended)
export OPENAI_API_KEY=sk-...
# Optional: source openai.env if you keep it in a file
```

---

## Smoke Tests (run first)

```bash
# 1. Help text renders the new structure
uv run thoth --help | head -60
# Expected: top "Commands:" section, "Research Modes:" with the workflow chain
#           line "clarification → exploration → deep_dive → tutorial → solution → prd → tdd"
#           and Examples: a quick prompt, a chained --auto run, --resume, and a -v debug example.

# 2. Version
uv run thoth --version
# Expected: v2.5.0 (or current)

# 3. Authentication help (P14 feature)
uv run thoth --help auth
# Expected: 3-section block: Environment variables → Config file (with [providers.openai] visible) → CLI flags.

# 4. The other in-CLI help topic still works
uv run thoth help modes
# Expected: per-mode listing with provider/model/kind columns.

# 5. End-to-end mock run (no real API calls)
uv run thoth "smoke test prompt" --provider mock
# Expected: writes a file like 2026-04-25_HHMMSS_default_mock_*.md in the cwd.
```

---

## P14 Feature Tests

### A. `thoth providers` subcommand group

```bash
# A1. New `list` subcommand
uv run thoth providers list
# Expected: "Configured providers:" then "openai", "perplexity" with "key set" or "no key"
#           depending on whether $OPENAI_API_KEY / $PERPLEXITY_API_KEY are exported.

# A2. New `models` subcommand
uv run thoth providers models
# Expected: per-provider sections listing the models referenced in BUILTIN_MODES.

# A3. New `check` subcommand
uv run thoth providers check
# Expected: exit 0 + "All providers have keys set" if both env vars are set,
#           OR exit 2 + "Missing keys for: <names>" if any are missing.
echo "exit=$?"

# A4. Deprecation shim — old form still works with a warning
uv run thoth providers -- --list 2>&1 | head -5
# Expected: first line on stderr is
#   warning: 'thoth providers -- ...' is deprecated; use 'thoth providers list|models|check'
# followed by the legacy provider table.
```

### B. Workflow chain + worked examples in `--help`

```bash
# B1. Verify the workflow chain line appears
uv run thoth --help | grep -F "clarification → exploration → deep_dive"

# B2. Verify the chained-with-async example appears
uv run thoth --help | grep -F 'thoth deep_research --auto --project k8s --async'

# B3. Verify the resume example appears
uv run thoth --help | grep -F 'thoth --resume op_abc123'

# B4. Verify the -v debug example appears
uv run thoth --help | grep -F 'Debug API issues'
```

### C. `--input-file` / `--auto` clearer help

```bash
# C1. --auto mentions "happy path"
uv run thoth --help | grep -F "happy path for chaining modes"

# C2. --input-file mentions "non-thoth document"
uv run thoth --help | grep -F "non-thoth document"
```

### D. API-key documentation pass

```bash
# D1. CLI-flag help is softened (now says "not recommended")
uv run thoth --help | grep -F "not recommended"
# Expected: at least three matches (--api-key-openai, --api-key-perplexity, --api-key-mock).

# D2. README authentication section
sed -n '/^## Authentication/,/^## /p' README.md | head -25
# Expected: 3-step ranked list (env vars > config file > CLI flags last) plus a
#           pointer to `thoth help auth`.

# D3. `thoth help auth` matches `thoth --help auth`
diff <(uv run thoth help auth) <(uv run thoth --help auth)
# Expected: no diff — both routes produce the same output.
```

### E. `APIKeyError` surfaces config path

```bash
# E1. Trigger a missing-key error (unset OPENAI_API_KEY for this test)
unset OPENAI_API_KEY
uv run thoth "test" --provider openai 2>&1 | head -10
# Expected: error message mentions
#   - "openai API key not found"
#   - "Set OPENAI_API_KEY (or edit /Users/<you>/.config/thoth/thoth.config.toml)"
#   - "Config file: /Users/<you>/.config/thoth/thoth.config.toml  (does not exist|exists)"
#   - "Env checked: OPENAI_API_KEY (unset)"
echo "exit=$?"
# Expected exit: 2

# Restore for later tests
export OPENAI_API_KEY=sk-...
```

### F. Progress spinner (sync background-mode runs)

> Requires a real OpenAI key. The spinner is gated to TTY + sync + non-verbose + background model.

```bash
# F1. Spinner shows during sync deep-research (interactive terminal)
uv run thoth deep_research "explain DNS in 50 words" --provider openai
# Expected: live spinner reading
#   "<label> · ~20 min expected · Ctrl-C to background"
# completes when the result is written, then "Deep research running complete".

# F2. Spinner suppressed in --async mode
uv run thoth deep_research "explain TLS in 50 words" --provider openai --async
# Expected: prints an operation ID immediately, no spinner.

# F3. Spinner suppressed in -v verbose mode
uv run thoth deep_research "explain HTTPS" --provider openai -v 2>&1 | head -5
# Expected: raw [thoth] log lines, no spinner.

# F4. Spinner suppressed for non-TTY (piped output)
uv run thoth deep_research "x" --provider openai | head -5
# Expected: completes without ANSI cursor noise; just plain output.

# F5. Spinner suppressed for quick (non-background) modes
uv run thoth "quick test" --provider openai
# Expected: default mode is o3 (immediate); no spinner appears.
```

### G. SIGINT "Resume later" hint

```bash
# G1. Start a slow run and Ctrl-C it
uv run thoth deep_research "long topic" --provider openai
# Press Ctrl-C after a few seconds.
# Expected output lines:
#   - "Checkpoint saved. Resume with: thoth --resume op_<id>"   (existing, Rich green ✓)
#   - "Resume later: thoth --resume op_<id>"                    (new in P14)

# G2. Resume the cancelled job
uv run thoth --resume op_<id>
# Expected: picks up where it left off and finishes.
```

### H. `--pick-model` / `-M` flag

> Picker is gated to immediate (non-background) modes only.

```bash
# H1. Rejected on background-mode modes
uv run thoth --pick-model deep_research "test" 2>&1 | head -6
echo "exit=$?"
# Expected: 5-line error mentioning "only supported for quick (non-deep-research)",
#           the offending model name, and the config-file remediation hint.
# Expected exit: 2

# H2. Rejected on exploration mode (also background)
uv run thoth -M exploration "test" 2>&1 | head -3
echo "exit=$?"
# Expected exit: 2

# H3. Picker shown for default (immediate) mode
uv run thoth --pick-model default "smoke test"
# Expected: numbered list of OpenAI immediate models (o3, gpt-4o, gpt-4o-mini, …),
#           prompt "Pick a model", and after you type a number, the run proceeds
#           with that model overriding the mode default.

# H4. Auto-pick via stdin (non-interactive)
echo 1 | uv run thoth --pick-model default "noninteractive smoke" --provider mock
# Expected: picks the first listed model and runs against mock provider.
```

---

## Recent Changes — Targeted Tests

Files changed in the last 14 commits and the P14 feature each one covers. Use the matching feature section above to exercise them.

| Changed file | P14 feature | Test section |
|---|---|---|
| `src/thoth/errors.py` | `format_config_context` + APIKeyError enrichment | E |
| `src/thoth/cli.py` | `--input-file`/`--auto` help, `--api-key-*` softening, `--pick-model`, `providers` subgroup, `auth` help routing | A, C, D, H |
| `src/thoth/help.py` | epilog, workflow chain, `render_auth_help`, deprecation banner | B, D |
| `src/thoth/commands.py` | `providers_list`/`_models`/`_check` | A |
| `src/thoth/run.py` | spinner gate around poll loop, `model_override` plumbing | F, H |
| `src/thoth/progress.py` (new) | `should_show_spinner`, `run_with_spinner` | F |
| `src/thoth/interactive_picker.py` (new) | `pick_model`, `immediate_models_for_provider` | H |
| `src/thoth/signals.py` | resume-later hint on SIGINT | G |
| `pyproject.toml` / `uv.lock` | `thothspinner` dependency | F |
| `README.md` | Authentication section | D |
| `CHANGELOG.md` / `PROJECTS.md` | release tracking | (docs only) |

---

## Automated Verification

Run before considering manual testing complete:

```bash
just all              # format + lint + typecheck + tests (full gate)
./thoth_test -r       # full thoth_test integration suite (~50s with mock provider)
```

Expected:
- `just all` → all green
- `./thoth_test -r` → 63 passed, 1 skipped, 0 failed (the 1 skipped is pre-existing, not P14)

---

## Known Behaviors / Caveats

- Two resume hints print on Ctrl-C (the older Rich-formatted line + the new "Resume later:"). Functional but redundant; tracked as a follow-up nit.
- `thoth providers help` (without subcommand) currently shows the legacy provider help — examples there still mention `--list` / `--models` flags rather than the new subcommands. Will be cleaned up when the deprecation shim is removed in N+1.
- `--pick-model` over a non-TTY input (e.g. CI without `echo N |`) will hang on the prompt. Pipe a number in or skip the flag.

---

## Configuration Profiles (P21)

Hand-edit `~/.config/thoth/thoth.config.toml` first to add:

```toml
[profiles.fast.general]
default_mode = "thinking"

[general]
default_profile = "fast"
```

Then run:

```bash
thoth config get general.default_mode                      # expect "thinking" (from profile)
THOTH_PROFILE=fast thoth config get general.default_mode   # expect "thinking"
thoth --profile missing config get general.default_mode    # expect ConfigProfileError naming '--profile flag'
thoth config get general.default_profile                   # expect "fast" (persisted)
thoth --profile bar config get general.default_profile     # expect "fast" (NOT mutated by --profile)
```

### Shipped profile examples

`thoth init` writes these example profiles into your config so you can try them immediately:

```bash
thoth --profile daily "what should I focus on today?"      # default_mode=thinking, default_project=daily-notes
thoth --profile openai_deep "compare vector databases"     # deep_research, providers=["openai"]
thoth --profile all_deep "compare vector databases"        # deep_research, parallel openai+perplexity
thoth --profile deep_research "literature review of X"     # deep_research + a worked prompt_prefix
```

### Verifying `prompt_prefix` is applied

```bash
# With the shipped `deep_research` profile, the prompt that reaches the LLM is
# prepended with: "Be thorough. Cite primary sources. Include counter-arguments."
thoth --profile deep_research --verbose "research vector dbs"
# Look for the assembled prompt in the verbose output.
```
