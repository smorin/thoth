# P33 — Schema-Driven Config Defaults

**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)
- **Motivation:** [P21 Configuration Profile Resolution & Overlay](P21-configuration-profile-resolution.md) — option 2 retrospective
- **Successor (deferred review):** [P37 — Review starter-profile selection](P37-starter-profile-review-.md)
- **Related (provider config surface):** [P23](P23-perplexity-immediate-sync.md), [P28](P28-gemini-background-deep-research.md)
- **Code (current sources of "default truth"):**
  - `src/thoth/config.py:221` — `ConfigSchema.get_defaults()` (runtime defaults)
  - `src/thoth/commands.py:70` — `_build_starter_profiles()` (init starter profiles)
  - `src/thoth/commands.py:111` — `_build_starter_document()` (init full document)

**Status:** `[ ]` Scoped, not started.

**Goal**: Drive every default config value — `thoth init`'s starter document, `ConfigSchema.get_defaults()`, and the per-provider configuration surface — from a single typed source built on Pydantic v2. Eliminate the duplication between runtime defaults and the init template, and gain typechecker + diagnostics coverage for every key the project ships.

**Motivation (P21 follow-up)**: P21's tomlkit refactor made the init writer structurally sound but didn't unify the two sources of "default config truth": `ConfigSchema.get_defaults()` (used by `ConfigManager.load_all_layers`) and `_build_starter_document()` (used by `thoth init`). The init writer is intentionally a *subset* of runtime defaults (it omits `max_transient_errors`, `prompt_max_bytes`, `cancel_upstream_on_interrupt`, and the entire `clarification` section), but the subset is hand-curated rather than declared, so a typo like `prompy_prefix` in the init template still slips past lint/typecheck today. Schema-driven generation closes that gap and prepares the provider config surface for P23/P24/P28 fields that the schema will need to model.

## Architecture (locked)

The schema is **one of three cooperating layers**, not a monolith:

| Layer | Responsibility | Lives in |
|---|---|---|
| 1. **Schema** | Pydantic v2 models — types, defaults, per-field metadata, validation rules. | `src/thoth/config_schema.py` (new) |
| 2. **Seed data** | Example data with no validation rules of its own — the 6 starter profiles (`daily`, `quick`, `openai_deep`, `all_deep`, `interactive`, `deep_research`); the schema validates their *shape*, not their *values*. | `src/thoth/_starter_data.py` (new) — content frozen verbatim from today's `_build_starter_profiles()` |
| 3. **Writer** | tomlkit emitter; reads schema metadata to attach inline comments and pick the `in_starter` field set; reads writer-owned table for structural prose (e.g. `# Configuration profiles (P21)…`). | `src/thoth/commands.py` (rewritten thin wrapper around the schema) |

### Locked decisions

1. **Schema library**: Pydantic v2.12.5 (already a transitive dep — promoted to direct).
2. **In-starter mechanism**: per-field flag via a typed `StarterField(...)` wrapper that returns `Field(json_schema_extra={"in_starter": True})`. Adding a new field forces an explicit decision: `StarterField(...)` ships in init, `Field(...)` does not.
3. **Schema topology**: separate runtime defaults from overlay/user-file shape —
   - `ThothConfig` — runtime default config only, all required-with-defaults. `ConfigSchema.get_defaults()` is derived from this model and must stay byte-identical to today's default dict.
   - `ConfigOverlay` — every runtime-default field optional; **auto-derived** from `ThothConfig` via a `make_partial(Model)` helper, then extended with valid user-only overlay fields that are intentionally not emitted by `get_defaults()` (`general.default_profile`, `general.prompt_prefix`, mode-level prompt/config fields, etc.).
   - `ModeConfig` — schema for `[modes.<name>]` and `[profiles.<name>.modes.<name>]`. It must include the prompt-bearing and mode-control fields the runtime already supports or plans around: `provider`, `model`, `kind`, `system_prompt`, `prompt_prefix`, `temperature`, `max_tokens`, `providers`, `parallel`, `previous`, `next`, `auto_input`, and open-ended mode values accepted by existing mode-editing flows only when deliberately allowed.
   - `ProfileConfig` — profile overlay schema. It mirrors `ConfigOverlay`, also permits profile-root `prompt_prefix` per P21, and validates nested `modes.<mode>` through `ModeConfig`.
   - `PartialThothConfig` remains available as the mechanically-derived runtime partial used by CLI/profile overlay internals; a regression test (`TS03`) asserts field-for-field alignment with `ThothConfig` so manual drift is impossible.
   - `UserConfigFile` — what `thoth.config.toml` actually looks like on disk: `ConfigOverlay` fields plus `profiles: dict[str, ProfileConfig]` plus an optional `experimental: dict[str, Any]` carve-out.
4. **Validation philosophy**: schema is **advisory, not enforced** at runtime.
   - `extra="forbid"` on schema, but violations log warnings via the existing logger — **never raise**. Type-coercion failures fall back to schema default for the field, with a warning.
   - `[experimental]` super-table is exempt (`extra="allow"` carve-out for plugin/experimental keys).
   - `--no-validate` CLI flag suppresses validation entirely (debug/triage tool — not a config option). It is threaded as loader metadata (`ConfigManager.load_all_layers(..., validate=False)` or equivalent), never as a config root inside `cli_args`.
   - Validation reports are collected in a testable place, e.g. `ConfigManager.validation_reports: dict[str, ValidationReport]`, keyed by layer (`user`, `project`, `profile`, `cli`). Human-facing emission may still use the existing config-warning console/log channel, but tests assert against the stored reports.
   - Tests opt into **strict mode** (warnings become errors) so init output and codebase outputs are held to a higher standard than user configs.
5. **Round-trip semantics for TS04**: hybrid —
   - **L2 (parsed dict equality)**: parse init output to dict. Compare the non-`profiles` root tables against `get_defaults()` projected to `starter_keys()`. Compare the parsed `profiles` table separately against `STARTER_PROFILES`, because starter profiles are seed data and are not part of runtime defaults.
   - **L3 (strict schema validation)**: parsed root tables validate through `ThothConfig` projection and the full parsed document validates through `UserConfigFile` with zero warnings in strict mode.
   - **L1 (substring assertions)**: rendered TOML contains `# Thoth Configuration File`, `[profiles]`, and `[profiles.daily]` — catches dropped-comment regressions without a brittle golden file.
6. **Starter-profile content**: the 6 profiles are **frozen verbatim** as `STARTER_PROFILES` seed data. Reviewing the *selection* of profiles is deferred to [P37](P37-starter-profile-review-.md) so P33 stays scoped to typing infrastructure.
7. **Provider config surface (forward-looking)**: each provider gets its own Pydantic model with `api_key`, `model`, `temperature`, `max_tokens`, `timeout`, `base_url` on a shared `ProviderConfigBase`, plus provider-specific fields (e.g. Perplexity's `search_context_size`, OpenAI's `organization`) on subclasses. For future providers, P33 only ensures the schema *shape* is forward-compatible with P23/P24/P28; runtime pickup tests belong to those provider projects. For OpenAI fields that the code already claims to consume, P33 adds regression tests proving those values reach `OpenAIProvider` or the OpenAI request builder.
8. **Comment source for the writer**: hybrid —
   - **Inline help-comments** (e.g. `# Empty string = ad-hoc mode`) live as field metadata on the schema.
   - **Structural prose** (e.g. the multi-line "Configuration profiles (P21)…" header before `[profiles]`) lives in a small writer-owned `WRITER_COMMENTS` table keyed by section path.
9. **Public API stability**:
   - `ConfigSchema.get_defaults() -> dict[str, Any]` — **unchanged signature**, body becomes `_ROOT_SCHEMA.model_dump(mode="python")`.
   - **New** `ConfigSchema.validate(data, *, strict=False) -> ValidationReport` — used by both runtime (`strict=False`) and tests (`strict=True`).
   - **New** `ConfigSchema.starter_keys() -> set[tuple[str, ...]]` — returns `in_starter=True` field paths; consumed by both writer and round-trip test.
   - **New** `ConfigSchema.model() -> type[ThothConfig]` — escape hatch for typed callers; low priority.
10. **Implementation order**: schema module → writer rewrite → runtime hookup. Tests precede each implementation step per CLAUDE.md TDD policy.

## Scope

### In scope
- New `src/thoth/config_schema.py` defining `ThothConfig`, `ConfigOverlay`, `ProfileConfig`, `UserConfigFile`, `PartialThothConfig` (auto-derived), `make_partial()`, per-section sub-models (`GeneralConfig`, `PathsConfig`, `ExecutionConfig`, `OutputConfig`, `ProvidersConfig`, `ClarificationConfig`, `ModesConfig`, `ModeConfig`), and `ProviderConfigBase` + `OpenAIConfig` / `PerplexityConfig` (and a placeholder for `GeminiConfig`).
- `StarterField()` typed wrapper.
- `ConfigSchema.validate()` with warn-only / strict modes; `--no-validate` CLI flag wired through.
- New `src/thoth/_starter_data.py` holding `STARTER_PROFILES` (6 profiles, content byte-identical to today's `_build_starter_profiles()`).
- Refactor `_build_starter_document()` and `_build_starter_profiles()` to thin wrappers over the schema + writer-owned `WRITER_COMMENTS` table.
- Refactor `ConfigSchema.get_defaults()` body to derive from the schema; signature unchanged.
- Hook the validator into `ConfigManager.load_all_layers` (per-layer, warn-only).
- Tests TS00–TS09 below.
- `README.md` update **only if** any user-visible behavior changes (e.g. new warnings appearing).

### Out of scope
- Changing on-disk TOML schema or any default values (the schema must accept exactly what runtime defaults produce today).
- Replacing `tomlkit` with another serializer.
- Touching `BUILTIN_MODES` (mode-specific data, not config defaults — see `src/thoth/config.py:53`).
- Reviewing *which* starter profiles ship — deferred to [P37](P37-starter-profile-review-.md).
- Refactoring runtime call sites to consume new typed provider fields for future/non-OpenAI providers — that work belongs to whichever provider project picks them up (P23/P24/P28, etc.). P33 only adds OpenAI runtime-consumption regression tests for fields it explicitly claims OpenAI already consumes.
- Promoting validation from warn-only to hard-fail. **Never hard-fail.** Warnings are diagnostic; raising on validation failures would be a breaking change to user configs and is explicitly excluded.

## Open questions

All previously open questions have been resolved during this refinement pass and are recorded in **Locked decisions** above. Re-opens (if any) should be added here with a `Q:` prefix and a date.

## Review remediation spec

**Goal:** Harden the P33 implementation plan so schema-driven defaults do not reject valid P21 profile/mode configs, do not confuse schema acceptance with runtime consumption, and remain testable through concrete warnings and dependency checks.

### Findings to address

1. **[Important]** Profile schema must accept P21-valid fields that are not runtime defaults: `general.default_profile`, `general.prompt_prefix`, profile-root `prompt_prefix`, and nested `profiles.<name>.modes.<mode>` prompt/config fields. Recommended action: add `ConfigOverlay`, `ProfileConfig`, and `ModeConfig` instead of using a raw `PartialThothConfig` for every user/profile shape.
2. **[Important]** Starter round-trip equality must separate runtime default projection from starter profile seed data. Recommended action: compare non-`profiles` roots to `starter_keys()` projection and compare `profiles` to `STARTER_PROFILES` separately.
3. **[Important]** Pydantic must be a direct dependency. Recommended action: add `pydantic>=2.12.5,<3` to `pyproject.toml` and lock verification.
4. **[Important]** Provider schema tests must distinguish schema acceptance from runtime consumption. Recommended action: schema-only tests for future provider fields, plus OpenAI-specific consumption tests for fields P33 claims OpenAI already uses.
5. **[Important]** `--no-validate` must be loader metadata, not config data. Recommended action: add explicit loader/API threading and CLI tests.
6. **[Minor]** Validation warnings need a defined collection point. Recommended action: store per-layer `ValidationReport`s and assert on them.
7. **[Minor]** Rename schema-layer `ProviderBase` to `ProviderConfigBase` to avoid confusion with runtime `ResearchProvider`.

### Suggested sequencing

Do P33 as dependency + schema shape first, then starter writer, then validation/runtime hookup. Keep the OpenAI runtime-consumption test near the provider-schema task so any modeled OpenAI field is either proven consumed or explicitly documented as schema-only before implementation proceeds.

### Tests & Tasks

- [ ] [P33-TS00] Dependency metadata test: assert `pyproject.toml` declares `pydantic>=2.12.5,<3` directly (not only through OpenAI's transitive dependency), and `uv.lock` still resolves Pydantic 2.x.
- [ ] [P33-TS01] Schema construction smoke test: instantiating `ThothConfig()` with no overrides succeeds and every default value type-checks. Asserts `ConfigSchema.get_defaults()` equals `_ROOT_SCHEMA.model_dump(mode="python")` byte-identical.
- [ ] [P33-TS02] Schema-coverage test: walk every leaf path in the historical `get_defaults()` (snapshot) and assert each one resolves to a `ThothConfig` field. Separately assert valid user-only overlay paths (`general.default_profile`, `general.prompt_prefix`, `modes.<name>.system_prompt`, `modes.<name>.prompt_prefix`, and `profiles.<name>.prompt_prefix`) resolve through `ConfigOverlay` / `ProfileConfig`. **This is the test family that catches the `prompy_prefix` typo class without rejecting valid P21 fields.**
- [ ] [P33-TS03] `make_partial(ThothConfig)` regression: produced model has the same field set as `ThothConfig`, all marked optional with `None` defaults. Field-for-field alignment makes manual drift impossible.
- [ ] [P33-TS04] Round-trip test (Position C): `_build_starter_document()` output → parsed root tables excluding `profiles` equal `get_defaults()` projected to `ConfigSchema.starter_keys()`; parsed `profiles` equals `STARTER_PROFILES`; full parsed document validates strict-mode through `UserConfigFile` with zero warnings; rendered TOML contains the substring assertions for `# Thoth Configuration File`, `[profiles]`, `[profiles.daily]`.
- [ ] [P33-TS05] Warn-only behavior: a config containing `[general] prompy_prefix = "x"` produces exactly one warning (with field path `general.prompy_prefix`) and does **not** raise. With `--no-validate`, the same config produces zero warnings.
- [ ] [P33-TS06] `[experimental]` carve-out: arbitrary keys under `[experimental]` produce zero warnings even with `extra="forbid"` elsewhere.
- [ ] [P33-TS07] Provider-specific schema fields: `providers.openai.temperature = 0.7` validates through provider schema; `providers.perplexity.search_context_size = "high"` validates; an unknown OpenAI field (`providers.openai.bogus = 1`) warns with the right field path; the Perplexity model rejects (warns on) OpenAI-specific fields. This test is schema acceptance only except where TS09 proves OpenAI runtime consumption.
- [ ] [P33-TS08] Mode/profile prompt surface: configs containing `[modes.thinking] system_prompt = "..."`, `[modes.thinking] prompt_prefix = "..."`, `[profiles.fast] prompt_prefix = "..."`, and `[profiles.fast.modes.thinking] system_prompt = "..."` validate with zero warnings. Typos at the same levels (`system_prompy`, `prompy_prefix`) produce precise warnings.
- [ ] [P33-TS09] OpenAI consumption regression: when `[providers.openai] temperature = 0.2` is set for an OpenAI model that accepts temperature, the value reaches the OpenAI request builder; when an active profile overlays `[profiles.fast.modes.thinking] system_prompt = "Profile prompt"`, the prompt passed to `OpenAIProvider.submit()` uses `"Profile prompt"` as the mode system prompt. If a modeled OpenAI field is not consumed today, either wire it in P33 or explicitly downgrade it to schema-only and remove the runtime claim.
- [ ] [P33-T00] Promote Pydantic to a direct dependency in `pyproject.toml` as `pydantic>=2.12.5,<3` and refresh `uv.lock` without changing the resolved major version. (TS00 must pass.)
- [ ] [P33-T01] Define `ThothConfig` and per-section sub-models in `src/thoth/config_schema.py` with values byte-identical to today's `get_defaults()`. Include the `StarterField()` wrapper. (TS01, TS02 default-path assertions must pass.)
- [ ] [P33-T02] Implement `make_partial()` helper, derive `PartialThothConfig`, define `ConfigOverlay`, `ProfileConfig`, and `UserConfigFile` (top-level overlay + `profiles` + `experimental`). (TS02 overlay assertions, TS03, TS08 must pass.)
- [ ] [P33-T03] Implement `ConfigSchema.validate(data, *, strict=False) -> ValidationReport`. Define `ValidationReport` (a dataclass with `warnings: list[ValidationWarning]`) and `ValidationWarning` (`layer`, `path`, `message`, `value_preview`). Wire `--no-validate` into the CLI as a global flag that passes loader metadata (`validate=False`) rather than adding any key to the config override layer. Add a guard that `_no_validate` / `no_validate` is rejected if someone tries to pass it as user config. (TS05, TS06 must pass.)
- [ ] [P33-T04] Refactor `ConfigSchema.get_defaults()` body to `_ROOT_SCHEMA.model_dump(mode="python")`. Verify byte-identical output against the historical snapshot. (TS01 still passes; full test suite still passes.)
- [ ] [P33-T05] Extract starter profile content to `STARTER_PROFILES` in `src/thoth/_starter_data.py` (content frozen verbatim). Refactor `_build_starter_profiles()` and `_build_starter_document()` to: (a) iterate the schema for in-starter fields, (b) read inline comments from field metadata, (c) read structural comments from a writer-owned `WRITER_COMMENTS` table. (TS04 must pass.)
- [ ] [P33-T06] Define `ProviderConfigBase`, `OpenAIConfig`, `PerplexityConfig`, and a placeholder `GeminiConfig` with the agreed forward-looking field set (`api_key`, `model`, `temperature`, `max_tokens`, `timeout`, `base_url` on the base; provider-specific fields on subclasses). Mark non-OpenAI future fields as schema-only unless their owning provider project adds runtime pickup tests. (TS07 must pass.)
- [ ] [P33-T07] Hook `ConfigSchema.validate()` into `ConfigManager.load_all_layers` per-layer (defaults trivially passes; user file → `UserConfigFile`; CLI overrides → `ConfigOverlay`; profile overlay → `ProfileConfig`). All warn-only. Store the results in `ConfigManager.validation_reports` and emit human-facing warnings through the existing config-warning channel. Full test suite must pass with `validation_reports` empty for existing fixtures.
- [ ] [P33-T08] If any user-visible behavior changed (e.g. new warnings on existing valid configs in test fixtures), document the change in `README.md` and the changelog. If nothing user-visible changed, note that in the project doc and skip the README edit.
- [ ] [P33-T09] Add OpenAI runtime-consumption regression tests and minimal wiring only for OpenAI fields P33 models as runtime-consumed. Profile-overlaid `system_prompt` must be covered because P21 profile work depends on mode prompts. (TS09 must pass.)
- [ ] Regression test status: full `./thoth_test -r` and `uv run pytest` green; `just check` clean; `just test-lint` and `just test-typecheck` clean.

### Deliverable
After P33 lands:
- `ConfigSchema.get_defaults()` returns the same dict it does today, derived from `_ROOT_SCHEMA`.
- `thoth init` produces a TOML document semantically identical to today, generated from the same schema.
- A typo in any default-value source (runtime or init) is caught at test time by TS02 and at user runtime by warn-only validation.
- The provider config surface is forward-compatible with P23/P24/P28 fields.

### Automated verification
- `uv run pytest tests/test_config_schema.py tests/test_provider_config.py tests/test_run_prompt_prefix.py -v` — TS00–TS09 green.
- `./thoth_test -r --skip-interactive -q` — no regressions in integration suite.
- `just check` — lint + typecheck clean (Pydantic models type-check under `ty`).

### Manual verification
- Run `thoth init --hidden` in a scratch dir; diff output against a pre-P33 capture — should be byte-identical (modulo the `version` line and any tomlkit-version-driven formatting).
- Add `[general] prompy_prefix = "x"` to a config; run `thoth status`; observe one warning with field path `general.prompy_prefix`. Add `--no-validate`; observe no warnings.
- Add `[experimental] anything = true` to a config; observe no warnings.
