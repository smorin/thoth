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
3. **Schema topology**: two top-level models —
   - `ThothConfig` — runtime config, all required-with-defaults.
   - `PartialThothConfig` — every field optional; **auto-derived** from `ThothConfig` via a `make_partial(Model)` helper. A regression test (`TS03`) asserts field-for-field alignment so manual drift is impossible.
   - `UserConfigFile` — what `thoth.config.toml` actually looks like on disk: `ThothConfig`'s fields plus `profiles: dict[str, PartialThothConfig]` plus an optional `experimental: dict[str, Any]` carve-out.
4. **Validation philosophy**: schema is **advisory, not enforced** at runtime.
   - `extra="forbid"` on schema, but violations log warnings via the existing logger — **never raise**. Type-coercion failures fall back to schema default for the field, with a warning.
   - `[experimental]` super-table is exempt (`extra="allow"` carve-out for plugin/experimental keys).
   - `--no-validate` CLI flag suppresses validation entirely (debug/triage tool — not a config option).
   - Tests opt into **strict mode** (warnings become errors) so init output and codebase outputs are held to a higher standard than user configs.
5. **Round-trip semantics for TS04**: hybrid —
   - **L2 (parsed dict equality)**: parse init output to dict; compare against `get_defaults()` projected to `starter_keys()`.
   - **L3 (strict schema validation)**: parsed dict validates through `ThothConfig` (or `UserConfigFile` for the version with profiles) with zero warnings in strict mode.
   - **L1 (substring assertions)**: rendered TOML contains `# Thoth Configuration File`, `[profiles]`, and `[profiles.daily]` — catches dropped-comment regressions without a brittle golden file.
6. **Starter-profile content**: the 6 profiles are **frozen verbatim** as `STARTER_PROFILES` seed data. Reviewing the *selection* of profiles is deferred to [P37](P37-starter-profile-review-.md) so P33 stays scoped to typing infrastructure.
7. **Provider config surface (forward-looking)**: each provider gets its own Pydantic model with `api_key`, `model`, `temperature`, `max_tokens`, `timeout`, `base_url` on a shared `ProviderBase`, plus provider-specific fields (e.g. Perplexity's `search_context_size`, OpenAI's `organization`) on subclasses. The runtime call sites picking up the new fields is **out of scope**; P33 only ensures the schema *shape* is forward-compatible with P23/P24/P28.
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
- New `src/thoth/config_schema.py` defining `ThothConfig`, `UserConfigFile`, `PartialThothConfig` (auto-derived), `make_partial()`, per-section sub-models (`GeneralConfig`, `PathsConfig`, `ExecutionConfig`, `OutputConfig`, `ProvidersConfig`, `ClarificationConfig`, `ModesConfig`), and `ProviderBase` + `OpenAIConfig` / `PerplexityConfig` (and a placeholder for `GeminiConfig`).
- `StarterField()` typed wrapper.
- `ConfigSchema.validate()` with warn-only / strict modes; `--no-validate` CLI flag wired through.
- New `src/thoth/_starter_data.py` holding `STARTER_PROFILES` (6 profiles, content byte-identical to today's `_build_starter_profiles()`).
- Refactor `_build_starter_document()` and `_build_starter_profiles()` to thin wrappers over the schema + writer-owned `WRITER_COMMENTS` table.
- Refactor `ConfigSchema.get_defaults()` body to derive from the schema; signature unchanged.
- Hook the validator into `ConfigManager.load_all_layers` (per-layer, warn-only).
- Tests TS01–TS07 below.
- `README.md` update **only if** any user-visible behavior changes (e.g. new warnings appearing).

### Out of scope
- Changing on-disk TOML schema or any default values (the schema must accept exactly what runtime defaults produce today).
- Replacing `tomlkit` with another serializer.
- Touching `BUILTIN_MODES` (mode-specific data, not config defaults — see `src/thoth/modes.py:53`).
- Reviewing *which* starter profiles ship — deferred to [P37](P37-starter-profile-review-.md).
- Refactoring runtime call sites to consume the new typed provider fields (`temperature`, etc.) — that work belongs to whichever future project picks them up (likely P28 Gemini).
- Promoting validation from warn-only to hard-fail. **Never hard-fail.** Warnings are diagnostic; raising on validation failures would be a breaking change to user configs and is explicitly excluded.

## Open questions

All previously open questions have been resolved during this refinement pass and are recorded in **Locked decisions** above. Re-opens (if any) should be added here with a `Q:` prefix and a date.

### Tests & Tasks

- [ ] [P33-TS01] Schema construction smoke test: instantiating `ThothConfig()` with no overrides succeeds and every default value type-checks. Asserts `ConfigSchema.get_defaults()` equals `_ROOT_SCHEMA.model_dump(mode="python")` byte-identical.
- [ ] [P33-TS02] Schema-coverage test: walk every leaf path in the historical `get_defaults()` (snapshot) and assert each one resolves to a `ThothConfig` field. **This is the test that catches the `prompy_prefix` typo class.**
- [ ] [P33-TS03] `make_partial(ThothConfig)` regression: produced model has the same field set as `ThothConfig`, all marked optional with `None` defaults. Field-for-field alignment makes manual drift impossible.
- [ ] [P33-TS04] Round-trip test (Position C): `_build_starter_document()` output → parsed dict equals `get_defaults()` projected to `ConfigSchema.starter_keys()`; validates strict-mode through `UserConfigFile` with zero warnings; rendered TOML contains the substring assertions for `# Thoth Configuration File`, `[profiles]`, `[profiles.daily]`.
- [ ] [P33-TS05] Warn-only behavior: a config containing `[general] prompy_prefix = "x"` produces exactly one warning (with field path `general.prompy_prefix`) and does **not** raise. With `--no-validate`, the same config produces zero warnings.
- [ ] [P33-TS06] `[experimental]` carve-out: arbitrary keys under `[experimental]` produce zero warnings even with `extra="forbid"` elsewhere.
- [ ] [P33-TS07] Provider-specific fields: `providers.openai.temperature = 0.7` round-trips through `ThothConfig` cleanly; `providers.perplexity.search_context_size = "high"` validates; an unknown OpenAI field (`providers.openai.bogus = 1`) warns with the right field path; the Perplexity model rejects (warns on) OpenAI-specific fields.
- [ ] [P33-T01] Define `ThothConfig` and per-section sub-models in `src/thoth/config_schema.py` with values byte-identical to today's `get_defaults()`. Include the `StarterField()` wrapper. (TS01, TS02 must pass.)
- [ ] [P33-T02] Implement `make_partial()` helper, derive `PartialThothConfig`, define `UserConfigFile` (top-level + `profiles` + `experimental`). (TS03 must pass.)
- [ ] [P33-T03] Implement `ConfigSchema.validate(data, *, strict=False) -> ValidationReport`. Define `ValidationReport` (a dataclass with `warnings: list[ValidationWarning]`). Wire `--no-validate` into the CLI as a global flag. (TS05, TS06 must pass.)
- [ ] [P33-T04] Refactor `ConfigSchema.get_defaults()` body to `_ROOT_SCHEMA.model_dump(mode="python")`. Verify byte-identical output against the historical snapshot. (TS01 still passes; full test suite still passes.)
- [ ] [P33-T05] Extract starter profile content to `STARTER_PROFILES` in `src/thoth/_starter_data.py` (content frozen verbatim). Refactor `_build_starter_profiles()` and `_build_starter_document()` to: (a) iterate the schema for in-starter fields, (b) read inline comments from field metadata, (c) read structural comments from a writer-owned `WRITER_COMMENTS` table. (TS04 must pass.)
- [ ] [P33-T06] Define `ProviderBase`, `OpenAIConfig`, `PerplexityConfig`, and a placeholder `GeminiConfig` with the agreed forward-looking field set (`api_key`, `model`, `temperature`, `max_tokens`, `timeout`, `base_url` on the base; provider-specific fields on subclasses). (TS07 must pass.)
- [ ] [P33-T07] Hook `ConfigSchema.validate()` into `ConfigManager.load_all_layers` per-layer (defaults trivially passes; user file → `UserConfigFile`; CLI overrides → `PartialThothConfig`; profile overlay → `PartialThothConfig`). All warn-only. Full test suite must pass with zero new warnings on existing fixtures.
- [ ] [P33-T08] If any user-visible behavior changed (e.g. new warnings on existing valid configs in test fixtures), document the change in `README.md` and the changelog. If nothing user-visible changed, note that in the project doc and skip the README edit.
- [ ] Regression test status: full `./thoth_test -r` and `uv run pytest` green; `just check` clean; `just test-lint` and `just test-typecheck` clean.

### Deliverable
After P33 lands:
- `ConfigSchema.get_defaults()` returns the same dict it does today, derived from `_ROOT_SCHEMA`.
- `thoth init` produces a TOML document semantically identical to today, generated from the same schema.
- A typo in any default-value source (runtime or init) is caught at test time by TS02 and at user runtime by warn-only validation.
- The provider config surface is forward-compatible with P23/P24/P28 fields.

### Automated verification
- `uv run pytest tests/test_config_schema.py -v` — TS01–TS07 green.
- `./thoth_test -r --skip-interactive -q` — no regressions in integration suite.
- `just check` — lint + typecheck clean (Pydantic models type-check under `ty`).

### Manual verification
- Run `thoth init --hidden` in a scratch dir; diff output against a pre-P33 capture — should be byte-identical (modulo the `version` line and any tomlkit-version-driven formatting).
- Add `[general] prompy_prefix = "x"` to a config; run `thoth status`; observe one warning with field path `general.prompy_prefix`. Add `--no-validate`; observe no warnings.
- Add `[experimental] anything = true` to a config; observe no warnings.
