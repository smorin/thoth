# P35 — Uniform `--help` + Useful API-Key Errors

**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)
- **Plan:** [docs/superpowers/plans/2026-05-01-help-uniform-errors.md](../docs/superpowers/plans/2026-05-01-help-uniform-errors.md) — implementation plan (TDD task-by-task)
- **Depends on:** P08 (typed `APIKeyError`, unified key resolution), P09 (provider registry), P11/P12 (modes surface — affects unknown-command suggestions), P14/P16 (CLI dispatch shape)
- **Code:**
  - `src/thoth/help.py:109-137` — `ThothGroup.invoke` (dispatch fix)
  - `src/thoth/help.py:139-160` — `format_commands` (reused by error formatter)
  - `src/thoth/cli.py:250-266` — `_extract_fallback_options` flag table
  - `src/thoth/errors.py:45-64` — `APIKeyError` class
  - `src/thoth/providers/__init__.py:25-65` — `PROVIDERS`, `PROVIDER_ENV_VARS`, `resolve_api_key`
  - `src/thoth/run.py:272-294` — provider-selection fallback

**Status:** `[~]` In progress.

**Goal**: Make `--help` work uniformly across the CLI (any invocation containing `--help` / `-h` shows help, never falls through to the research runner). Replace the misleading "openai API key not found" error that surfaces for unknown subcommands like `thoth profiles --help` with a clear "unknown command" error + fuzzy did-you-mean suggestion + full top-level command listing. Where a key is genuinely required, enumerate all three input channels (env var, `--api-key-*` flag, config file) and show every provider's key status, not just the failing one. Default the runner's provider selection to "any provider that has a resolvable key" instead of hardcoding `openai`, honoring `general.default_provider` when set.

**Out of Scope**
- New `--provider`-flag semantics (existing `--provider` still wins).
- Reorganizing the bare-prompt fallback path itself — multi-token strings still route to research-by-default.
- Provider-key validation against the live API (existing resolver behavior preserved — only `*-not-set` / placeholder rejection).
- Click help-text content rewrites (this project changes routing, not the help body that Click already produces for registered commands).
- Adding new providers (Gemini lands under P24/P28).

### Design Notes — three orthogonal layers

The fix is a single user-visible behavior change but cleanly decomposes into three layers, each with its own subagent-driven implementation cycle:

- **Layer 1 — Dispatch fix.** `ThothGroup.invoke` short-circuits `--help` / `-h` ahead of the existing 3-path dispatch (registered subcommand → builtin mode → bare-prompt fallback). Single-token unrecognized first-args (matching `^[a-z][a-z0-9_-]*$`, no leading `-`) are treated as command typos rather than research prompts and emit a structured "unknown command" error (exit 2) including a fuzzy/curated did-you-mean suggestion and the full top-level command listing. Multi-token / quoted strings preserve the existing bare-prompt behavior. `cli.py`'s `_extract_fallback_options` adds `--help` / `-h` to the flag table as belt-and-suspenders for any path that bypasses `invoke`.
- **Layer 2 — Enhanced `APIKeyError` message.** Title-line `"{provider} API key not found"` is preserved verbatim (existing tests assert on this substring). The suggestion expands from "Set $ENV (or edit $config)" to a numbered list of all three input channels — env var, `--api-key-<provider>` CLI flag, and config-file `[providers.<name>] api_key = "..."` syntax — plus a one-line "switch providers with `--provider <other>`" hint. Status block shows every entry in `PROVIDER_ENV_VARS`, not just the failing one. New `PROVIDER_CLI_FLAGS` sibling registry maps provider → CLI flag name.
- **Layer 3 — Multi-provider default fallback.** `run.py` replaces hardcoded `providers_to_use = ["openai"]` with `available_providers(config, cli_api_keys=...)` — a new helper in `providers/__init__.py` that returns providers whose keys resolve without raising. Selection priority: explicit `--provider` → mode's `provider`/`providers` → `general.default_provider` (if resolvable) → first available in `PROVIDERS` dict order → fall back to `["openai"]` so Layer 2's enhanced error fires when zero providers have keys.

### Design Notes — single-token-vs-prompt heuristic (Layer 1)

Bare prompts in research are typically multi-token natural-language ("what is X", "explain Y"). A single token that matches the command-name regex `^[a-z][a-z0-9_-]*$` is overwhelmingly a command typo. Heuristic preserves the bare-prompt fallback for:

- Multi-token strings (`thoth quantum gravity`)
- Quoted strings with spaces (`thoth "what is X"`)
- Option-only invocations (`thoth --json --provider mock <prompt>`)
- Tokens with uppercase or punctuation outside the command-name shape

Heuristic rejects (treats as typo) only:
- Single bare token, lowercase + digits/hyphens/underscores, no leading `-`, not in registered commands or `BUILTIN_MODES`.

### Design Notes — fuzzy/curated suggestion seed (Layer 1)

Two-tier suggestion lookup in `_suggest_command(typed, registered)`:

1. **Curated `_KNOWN_SUBPATHS` dict** — common typed-token → full-invocation mappings (e.g. `"profiles" → "thoth config profiles"`, `"add" → "thoth modes add"`). Captures cases where the user typed a leaf name from a multi-level command path.
2. **Fuzzy match** via `difflib.get_close_matches(typed, registered, n=1, cutoff=0.7)` against registered top-level command names.

Returns `None` if neither tier produces a hit; the error message then omits the "Did you mean..." line and just shows the full command listing.

### Design Notes — provider selection precedence (Layer 3)

Updated precedence in `run.py`:

| Source                                  | Wins when                                   |
|-----------------------------------------|---------------------------------------------|
| `--provider` flag                       | always, if set                              |
| `mode_config["provider"]` (string)      | mode pins a single provider                 |
| `mode_config["providers"]` (list)       | mode pins multiple providers (mux flow)     |
| `general.default_provider` config key   | set AND has a resolvable key                |
| First entry in `available_providers(…)` | otherwise, if any provider has a key        |
| `["openai"]` (legacy fallback)          | nothing has a key — fires Layer 2 error     |

`available_providers()` is a non-raising sibling of `resolve_api_key()` — it iterates `PROVIDERS` in declared order, swallows `APIKeyError` per provider, and returns the resolvable set.

### Design Notes — error-message format (Layer 1 unknown-command)

```text
Error: unknown command 'profiles'

Did you mean 'thoth config profiles'?

Available top-level commands:
  Run research:  ask, default, clarification, mini_research, deep_research, ...
  Manage thoth:  config, init, list, modes, providers, status, ...

Run `thoth --help` for the full command list and options.
```

Reuses `RUN_COMMANDS` / `ADMIN_COMMANDS` lists and the existing `format_commands` rendering machinery in `help.py:139-160` so the listing format matches `thoth --help` exactly.

### Design Notes — error-message format (Layer 2 APIKeyError)

```text
Error: openai API key not found

Provide an OpenAI API key via one of:
  1. Environment variable: export OPENAI_API_KEY=sk-...
  2. CLI flag:              thoth --api-key-openai sk-... <command>
  3. Config file:           Add the following to /Users/.../thoth.config.toml:
                              [providers.openai]
                              api_key = "sk-..."

Alternatively, switch providers with --provider perplexity (or another) and
supply that provider's key via the same channels.

Status of currently-checked sources:
  Config file: /Users/.../thoth.config.toml  (exists)
  Env vars:    OPENAI_API_KEY (unset)  PERPLEXITY_API_KEY (unset)  MOCK_API_KEY (set)
```

Title-line `"openai API key not found"` is preserved verbatim — `tests/test_api_key_resolver.py` and `thoth_test` cases assert on this substring.

### Tests & Tasks

The plan's task IDs follow the project-harness `P##-T##` / `P##-TS##` convention. Each layer is its own subagent-driven cycle (implementer → spec reviewer → quality reviewer → fix) per the `superpowers:subagent-driven-development` skill.

#### Pre-flight

- [x] [P35-T00] Worktree at `/Users/stevemorin/c/thoth-worktrees/help-uniform-errors`, branch `help-uniform-errors` from `origin/main`.
- [x] [P35-T01] Baseline gate green (980 pytest + 76 thoth_test).
- [~] [P35-T02] Project file + plan + trunk row committed (this commit).

#### Layer 1 — Dispatch fix

- [ ] [P35-TS03] Tests for unknown-command + uniform `--help`. Cases: `thoth profiles --help` (exit 2, "unknown command 'profiles'", "Did you mean 'thoth config profiles'", "Available top-level commands"), `thoth modes --help` (exit 0 click help — regression), `thoth default --help` (mode help — regression), `thoth profiles` (exit 2 same error), `thoth quantum gravity` (bare-prompt fallback preserved), `thoth "what is X"` (bare-prompt preserved), `thoth profiles -h` (same as `--help`).
- [ ] [P35-T04] Implement `_KNOWN_SUBPATHS`, `_suggest_command`, `_format_unknown_command_error` helpers + update `ThothGroup.invoke` short-circuit. Add `--help` / `-h` to `_extract_fallback_options` flag table. Update `tests/baselines/unknown_command.json` to the new "unknown command" output (currently pins the broken behavior).
- [ ] [P35-T05] Spec-reviewer pass on Layer 1 (verify dispatch matrix matches design notes; confirm bare-prompt regression cases preserved).
- [ ] [P35-T06] Quality-reviewer pass on Layer 1 (lint/type/format; assertion-message audit; baseline regen scope).

#### Layer 2 — Enhanced `APIKeyError`

- [ ] [P35-TS07] Tests asserting (a) title-line substring `"openai API key not found"` preserved (regression), (b) suggestion lists env var + CLI flag + config syntax all three, (c) status block enumerates ALL providers' env vars not just the failing one, (d) legacy-config-file guidance still appended when present (regression).
- [ ] [P35-T08] Add `PROVIDER_CLI_FLAGS` registry sibling to `PROVIDER_ENV_VARS`. Rewrite `APIKeyError.__init__` suggestion. Extend / branch `format_config_context` if needed for multi-provider status.
- [ ] [P35-T09] Spec-reviewer pass on Layer 2 (every channel enumerated; status block iterates registry).
- [ ] [P35-T10] Quality-reviewer pass on Layer 2.

#### Layer 3 — Multi-provider default fallback

- [ ] [P35-TS11] Tests: openai-only-set → openai used; perplexity-only-set → perplexity used; `general.default_provider="perplexity"` + key set → perplexity used even when openai also has a key; zero keys → enhanced `APIKeyError`; `--provider mock` always wins.
- [ ] [P35-T12] Implement `available_providers(config, cli_api_keys=None) -> list[str]` in `providers/__init__.py`. Update `run.py:272-294` fallback chain.
- [ ] [P35-T13] Spec-reviewer pass on Layer 3 (precedence matrix matches design notes).
- [ ] [P35-T14] Quality-reviewer pass on Layer 3.

#### Close

- [ ] [P35-T15] Full lefthook gate (`just check` + `uv run pytest -q` + `./thoth_test -r --skip-interactive -q` + `uv run ruff format --check src/ tests/`).
- [ ] [P35-T16] Flip P35 trunk glyph `[~]` → `[x]`. Update each `[ ]` task above to `[x]` as completed.
- [ ] [P35-T17] Push branch, open PR, squash-merge to `main`.

### Verification

After all three layers land:

```bash
unset OPENAI_API_KEY

# Layer 1
uv run thoth profiles --help              # → exit 2, "unknown command 'profiles'", did-you-mean, full list
uv run thoth profiles                     # → exit 2, same error (no longer falls into research)
uv run thoth modes --help                 # → exit 0, standard click help (regression)
uv run thoth quantum gravity              # → bare-prompt fallback (existing behavior)

# Layer 2
uv run thoth ask "test"                   # → multi-line error with env/flag/config + multi-provider status

# Layer 3
export PERPLEXITY_API_KEY=pplx-...
uv run thoth ask "test"                   # → uses perplexity automatically (was: openai-not-found error)

# Full gate
just check && uv run pytest -q && ./thoth_test -r --skip-interactive -q
```

### Acceptance criteria

- [ ] All `--help` invocations work without API keys.
- [ ] Unknown single-token commands emit "unknown command" + did-you-mean + command list (exit 2).
- [ ] Multi-token strings still route to bare-prompt research.
- [ ] `APIKeyError` suggestion lists env var + CLI flag + config syntax.
- [ ] `APIKeyError` shows status of ALL provider env vars.
- [ ] Runner picks any-provider-with-key when no `--provider` given.
- [ ] `general.default_provider` config key honored when its provider has a key.
- [ ] No regressions in registered-subcommand or builtin-mode dispatch.
- [ ] Existing `tests/test_api_key_resolver.py` substring assertions still pass.
- [ ] Full pytest + thoth_test + lefthook gate green.
