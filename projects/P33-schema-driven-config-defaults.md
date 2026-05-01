# P33 — Schema-Driven Config Defaults

**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)

**Status:** `[ ]` Scoped, not started.

**Goal**: Drive every default config value — including `thoth init`'s starter document, `ConfigSchema.get_defaults()`, and `BUILTIN_MODES` — from a single typed source (Pydantic model or `@dataclass`-based schema). Eliminate the duplication between the runtime defaults and the init-template, and gain typechecker coverage for every key/value the project ships.

**Status**: Placeholder — requirements still need to be fleshed out before this can be worked on.

**Motivation (P21 follow-up)**: P21's tomlkit refactor (option 2 in the P21 retrospective) made the init writer structurally sound but didn't unify the two sources of "default config truth": `ConfigSchema.get_defaults()` (used by `ConfigManager.load_all_layers`) and `_build_starter_document()` (used by `thoth init`). A typo like `prompy_prefix` in the init template still slips past lint/typecheck today. Schema-driven generation closes that gap.

**Scope (rough)**
- Define a typed `StarterConfig` schema (Pydantic v2 or dataclasses) covering general/paths/execution/output/providers/profiles.
- Refactor `ConfigSchema.get_defaults()` to derive its dict from the schema.
- Refactor `_build_starter_document()` (and `_build_starter_profiles`) to serialize the schema via tomlkit instead of constructing tables by hand.
- Add a regression test asserting `init`'s generated config round-trips through the schema with no validation errors.
- Document migration in `README.md` if any default values change as a side-effect.

**Out of Scope**
- Changing the on-disk TOML schema or any default values.
- Replacing `tomlkit` with another serializer.
- Touching `BUILTIN_MODES` (it's mode-specific data, not config defaults).

### Tests & Tasks
- [ ] [P33-TS01] Design tests for schema-driven config generation before implementation.
- [ ] [P33-T01] Flesh out requirements: pick the schema library (Pydantic v2 vs typed dataclasses), enumerate every key currently in `ConfigSchema.get_defaults()` and `_build_starter_document()`, and document the migration plan.
- [ ] [P33-T02] Implement the typed `StarterConfig` schema and a serializer that emits tomlkit documents.
- [ ] [P33-T03] Replace `ConfigSchema.get_defaults()` and `_build_starter_document()` to derive from the schema. Keep public API stable.
- [ ] [P33-T04] Round-trip test: `init` output parses back to the schema with zero validation errors and matches `ConfigSchema.get_defaults()` byte-for-byte (after profile-stripping).
