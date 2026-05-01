# P12 — CLI Mode Editing — `thoth modes` mutations (v2.12.0)

**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)
- **Plan:** [docs/superpowers/plans/2026-04-30-p12-cli-mode-editing-v2.md](../docs/superpowers/plans/2026-04-30-p12-cli-mode-editing-v2.md) — implementation plan (TDD task-by-task)
- **Superseded plan:** [docs/superpowers/plans/2026-04-30-p12-cli-mode-editing.md](../docs/superpowers/plans/2026-04-30-p12-cli-mode-editing.md) — earlier draft, banner-marked superseded
- **Depends on:** P11 (read paths), P13 (secret helpers), P18 (kind field), P21b (config profiles precedent)
- **Related:** P21* (profile-overlay tier)
- **Code:** `src/thoth/config_profiles.py:107` (overlay-modes semantics)

**Status:** `[~]` In progress.

**Goal**: Let users create, edit, rename, copy, and remove mode definitions from the CLI instead of hand-editing TOML. Adds the mutation half of the `thoth modes` surface (P11 shipped read-only `list`), mirroring the `thoth config profiles` precedent (P21b) where applicable and diverging deliberately where mode semantics require it (builtins, `--model`-on-create, empty-table pruning). Integrates with P18's canonical `kind` field and P21*'s profile-overlay tier.

**Out of Scope**
- GUI / TUI editor — CLI only.
- Validating `system_prompt` content (any string accepted).
- New mode-level fields beyond what `ModeInfo` already surfaces and `BUILTIN_MODES` actually uses today (provider, providers, model, kind, system_prompt, description, auto_input, previous, next). `temperature` and `parallel` are accepted as freeform keys but not in any builtin. The legacy `async` key is deprecated by P18's `kind` field — `kind` is canonical.
- `set-default` / `unset-default` for modes — deferred to a follow-up project. Users edit `general.default_mode` via `thoth config set` until the follow-up lands.
- Schema migration for `[modes.*]` (no on-disk shape change beyond what P18 already established).

### Design Notes — command surface

Argument shape mirrors `thoth config profiles` (P21b) where applicable, with mode-specific deviations:

- `thoth modes add NAME --model M [--provider P] [--description D] [--kind immediate|background] [--override]` — required `--model`; default `provider=openai`, default `kind=immediate`. `--override` opts in to creating a same-named user override for a builtin in the selected tier: base `[modes.NAME]` by default, or `[profiles.X.modes.NAME]` with `--profile X`.
- `thoth modes set NAME KEY VALUE [--string]` — single-leaf write. `--string` forces string parsing for keys like `sk-...`.
- `thoth modes unset NAME KEY` — single-leaf remove. **Never overloaded** — the no-key form is `remove`, not `unset`.
- `thoth modes remove NAME` — whole-table delete (parallel to `config profiles remove`). Idempotent.
- `thoth modes rename OLD NEW` — user-mode only.
- `thoth modes copy SRC DST [--from-profile X] [--override]` — copies effective config (builtin layered with override) into a new user mode. `--from-profile X` reads SRC from `[profiles.X.modes.SRC]` (default reads from base `[modes.SRC]`); composes with `--profile Y` (DST) to enable all four directions: base→base, base→overlay, overlay→base, overlay→overlay. `--override` opts in when DST is a builtin name, writing a same-named override in the selected destination tier.

### Design Notes — targeting model (file × tier)

Targeting is two orthogonal axes: **file on disk** × **tier within file**. Every mutator accepts the same matrix.

- **File axis** (mutually exclusive):
  - default → `~/.thoth/thoth.config.toml`
  - `--project` → `./thoth.config.toml` (or `./.thoth.config.toml`)
  - `--config PATH` → arbitrary TOML at PATH
  - `--project` + `--config PATH` together → `USAGE_ERROR` exit 2 (same rule as `config_cmd._reject_config_project_conflict`)
- **Tier axis** (composes with file axis):
  - default → `[modes.<NAME>]`
  - `--profile X` → `[profiles.X.modes.<NAME>]` (overlay tier; grounded in `config_profiles.py:107` semantics — overlay modes are hidden from `thoth modes` unless `--profile X` / `THOTH_PROFILE=X` is active)

Examples:
- `thoth modes add cheap --model gpt-4o-mini` → `~/.thoth/thoth.config.toml [modes.cheap]`
- `thoth modes add cheap --model gpt-4o-mini --profile dev` → `~/.thoth/thoth.config.toml [profiles.dev.modes.cheap]`
- `thoth modes add cheap --model gpt-4o-mini --project --profile ci` → `./thoth.config.toml [profiles.ci.modes.cheap]`

### Design Notes — semantics shared by every mutator

- **JSON envelope**: every mutator accepts `--json` through the Click wrapper and follows the existing Thoth JSON contract: `{"status": "ok", "data": {schema_version: "1", op, mode, target: {file, tier}, …op-specific keys}}` or `{"status": "error", "error": ...}`. Default human output is a one-line confirmation (e.g. `Set my_brief.temperature = 0.2 → ~/.thoth/thoth.config.toml [modes.my_brief]`). Users who want the full effective view run `thoth modes list --name NAME` afterward.
- **Type coercion**: VALUE parsed via shared `_parse_value` (bool / int / float / string). `--string` forces string. Same rule as `config set`. Reuses helper from `config_cmd.py`.
- **Secret masking**: never echo secret values. The default human confirmation masks; JSON receipts keep the `value` field but mask it for secret-like keys. `--show-secrets` is read-only and not honored on mutators (nothing to reveal — the user just typed the value).
- **Empty-table pruning** (divergence from B17 / `config profiles unset`): when `unset KEY` empties `[modes.NAME]` (or `[profiles.X.modes.NAME]`), the table is pruned. An empty mode table is meaningless. To delete a whole mode in one shot, use `remove`.
- **Idempotency**:
  - `add` compares **`--model` only** for idempotency. Same NAME + same model → no-op exit 0 (other flags like `--description`, `--provider`, `--kind` are ignored on re-add; users update them via `set`). Different model on existing name → `MODE_EXISTS_DIFFERENT_MODEL` exit 1. Rationale: `add` reserves the name + locks the identity-bearing model; metadata adjustments are `set`'s job.
  - `remove` is no-op exit 0 if absent.
  - `unset KEY` is no-op exit 0 if KEY absent on a present mode.
- **Writes go through `ConfigDocument`**: P12 adds `set_mode_value`, `unset_mode_value`, `ensure_mode`, `remove_mode`, `rename_mode`, `copy_mode` primitives, each accepting an optional `profile` argument that switches the target sub-tree to `profiles.<X>.modes.<NAME>`. No direct tomlkit in command code.
- **Effective view after writes**: not auto-printed. The write receipt is intentionally minimal; users run `thoth modes list --name NAME [--profile X]` for the full ModeInfo. Diverges from the original P12 design (which echoed `_render_detail` after every write) — chosen for parity with `config profiles` and to avoid double-rendering.
- **Shared secret helpers**: `src/thoth/_secrets.py` already exists (extracted under P13); P12 simply consumes it. The original P12-T05 / P12-TS05 "extract helpers" tasks no longer apply.

### Design Notes — builtin interaction matrix

The `BUILTIN_MODES` constant defines built-in modes that ship in code (P11). They cannot be mutated *as such*, but a user can create a same-named override in any tier (`[modes.<builtin>]` or `[profiles.X.modes.<builtin>]`) that overrides selected keys. The matrix below applies regardless of tier: `--profile` selects the tier, but only `--override` loosens builtin-name guards for `add` and destination builtin-name guards for `copy`.

| Op             | Builtin only                       | User only                       | Overridden                              | Absent                |
|----------------|------------------------------------|---------------------------------|-----------------------------------------|-----------------------|
| `add NAME`     | refuse `BUILTIN_NAME_RESERVED` unless `--override` | no-op / `MODE_EXISTS_DIFFERENT_MODEL` | no-op / `MODE_EXISTS_DIFFERENT_MODEL` | creates table in chosen tier |
| `set NAME K V` | implicitly creates override in chosen tier; sets K=V | sets K=V                  | sets K=V on override                    | `MODE_NOT_FOUND`      |
| `unset NAME K` | `MODE_NOT_FOUND` (no user-side K)  | drops K; prunes empty           | drops K; prunes empty (override fully reverts to builtin) | `MODE_NOT_FOUND` |
| `remove NAME`  | refuse `BUILTIN_NAME_RESERVED`     | drops user table                | drops override; mode reverts to builtin | no-op exit 0          |
| `rename O→N`   | refuse `BUILTIN_NAME_RESERVED` on O| renames user table              | refuse (drop override first)            | `MODE_NOT_FOUND` on O |
| `copy S→D`     | reads `BUILTIN_MODES`; writes user/overlay at D | reads source table; writes at D | reads effective (builtin+override); writes at D | `MODE_NOT_FOUND` on S |

`rename` additionally refuses if the destination name is a builtin or already exists in the destination tier (`DST_NAME_TAKEN`). `copy` refuses if the destination already exists in the destination tier, and refuses builtin destination names unless `--override` is present.

"Source"/"name-state" axis above refers to the *base* (`[modes.*]`) catalog. Per-profile overlay state is independent: `add cheap --profile dev` is allowed even if `cheap` exists in `[modes.*]` — the two tiers are separate namespaces.

**`--override` exception:** `add NAME --override` and `copy SRC NAME --override` are the explicit opt-in paths for creating a user override whose NAME is a builtin. They write to the selected tier: `[modes.NAME]` by default, or `[profiles.X.modes.NAME]` with `--profile X`. Without `--override`, builtin-name guards are absolute regardless of `--profile`. `--override` does not bypass normal destination conflicts: an existing override in the selected tier still triggers the op's idempotency or `DST_NAME_TAKEN` rules.

**`--override` is strict on non-builtins:** `--override` exists *only* to bypass the builtin-name guard. Passing it when there is no guard to bypass is a `USAGE_ERROR` exit 2. This applies symmetrically to `add NAME --override` (where NAME is not in `BUILTIN_MODES`) and `copy SRC DST --override` (where DST is not in `BUILTIN_MODES`). Rationale: the flag is an explicit shadow opt-in, not a no-op permission modifier — surfacing typos (e.g. the user meant `--provider`) early is worth the strictness.

### Tests & Tasks

Per-command TS rows enumerate functional cases at single-case granularity. Per-command targeting cross-product (file × tier × `--json`) is consolidated into one "targeting matrix" TS row per mutator (the matrix is identical across mutators, so the test family is parameterized; this avoids a 6× explosion in trunk row count while preserving per-command coverage in the suite).

#### `thoth modes add NAME --model M [--provider P] [--description D] [--kind K] [--override] [--project] [--config PATH] [--profile X] [--string] [--json]`
- [x] [P12-TS01a] Happy path: creates `[modes.NAME]` with `model = M`, default `provider = "openai"`, default `kind = "immediate"`; appears in `thoth modes list --source user`
- [x] [P12-TS01b] `--provider P` writes the given provider key
- [x] [P12-TS01c] `--description D` writes the description key
- [x] [P12-TS01d] `--kind background` sets `kind = "background"`; default is `"immediate"`; invalid `--kind` value → `USAGE_ERROR` exit 2
- [x] [P12-TS01e] Idempotency is **model-only**: same NAME + same model → no-op exit 0 even if `--description` / `--provider` / `--kind` differ from existing entry (those flags are ignored on re-add; users update via `set`)
- [x] [P12-TS01f] Same NAME + different model → `MODE_EXISTS_DIFFERENT_MODEL` exit 1
- [x] [P12-TS01g] NAME is a builtin (no `--override`) → `BUILTIN_NAME_RESERVED` exit 1; suggests `copy <name> <new>`
- [x] [P12-TS01h] Targeting matrix: `--project` → `./thoth.config.toml`; `--config PATH` → PATH; `--profile X` → `[profiles.X.modes.NAME]`; `--profile + --project` and `--profile + --config PATH` compose; `--project + --config PATH` rejected with `USAGE_ERROR` exit 2
- [x] [P12-TS01i] `--json` envelope follows the existing wrapper contract: `{"status":"ok","data":{schema_version: "1", op: "add", mode, target: {file, tier}, created, model, provider, kind}}`
- [x] [P12-TS01j] `--override` flag: `add deep_research --model gpt-4o-mini --override` writes `[modes.deep_research]`; `--profile dev --override` writes `[profiles.dev.modes.deep_research]`; without `--override`, builtin names are rejected with `BUILTIN_NAME_RESERVED`; existing overrides still use normal model-only idempotency / different-model checks; `--override` on a non-builtin name (e.g. `add my_brief --model M --override`) is rejected with `USAGE_ERROR` exit 2 — the flag is the explicit builtin-shadow opt-in, not a no-op modifier
- [x] [P12-T01] Implement `thoth modes add` — click command in `cli_subcommands/modes.py`, `get_modes_add_data` + `_op_add` in `modes_cmd.py`, `ConfigDocument.ensure_mode(profile=...)` primitive

#### `thoth modes set NAME KEY VALUE [--project] [--config PATH] [--profile X] [--string] [--json]`
- [x] [P12-TS02a] Updates existing user mode: KEY=VALUE round-trips through tomlkit
- [x] [P12-TS02b] `--string` keeps `sk-...` as a string (no integer coercion)
- [x] [P12-TS02c] Type coercion: `true`/`false` → bool; `42` → int; `0.2` → float
- [x] [P12-TS02d] Setting on a builtin-only name implicitly creates override in the chosen tier (post: `thoth modes list --name NAME [--profile X]` → `source=overridden`)
- [x] [P12-TS02e] Absent NAME in the chosen tier → `MODE_NOT_FOUND` exit 1
- [x] [P12-TS02f] Targeting matrix (same shape as TS01h)
- [x] [P12-TS02g] `--json` envelope follows the existing wrapper contract: `{"status":"ok","data":{schema_version, op: "set", mode, target, key, value, wrote}}`; secret-like `value` receipts are masked
- [x] [P12-T02] Implement `thoth modes set` — click command, `get_modes_set_data` + `_op_set`, `ConfigDocument.set_mode_value(profile=...)`

#### `thoth modes unset NAME KEY [--project] [--config PATH] [--profile X] [--json]`
- [ ] [P12-TS03a] Drops a single user-table key in the chosen tier
- [ ] [P12-TS03b] Empty `[modes.NAME]` (or `[profiles.X.modes.NAME]`) is pruned after the last key is removed (divergence from B17)
- [ ] [P12-TS03c] On overridden mode: pruning fully reverts the override; post `thoth modes list --name NAME` → `source=builtin`
- [ ] [P12-TS03d] Idempotent: KEY absent on present mode → no-op exit 0
- [ ] [P12-TS03e] Pure-builtin NAME (no user-side override in chosen tier) → `MODE_NOT_FOUND` exit 1
- [ ] [P12-TS03f] Targeting matrix (same shape as TS01h)
- [ ] [P12-TS03g] `--json` envelope follows the existing wrapper contract with data `{schema_version, op: "unset", mode, target, key, removed, table_pruned}`
- [ ] [P12-T03] Implement `thoth modes unset` — click command, `get_modes_unset_data` + `_op_unset`, `ConfigDocument.unset_mode_value(profile=..., prune_empty=True)`

#### `thoth modes remove NAME [--project] [--config PATH] [--profile X] [--json]`
- [ ] [P12-TS04a] Drops a user-only mode in the chosen tier; gone from `thoth modes list [--profile X]`
- [ ] [P12-TS04b] On overridden mode: drops override; post → `source=builtin`
- [ ] [P12-TS04c] Builtin-only NAME → `BUILTIN_NAME_RESERVED` exit 1
- [ ] [P12-TS04d] Idempotent: absent NAME in chosen tier → no-op exit 0
- [ ] [P12-TS04e] Targeting matrix (same shape as TS01h)
- [ ] [P12-TS04f] `--json` envelope follows the existing wrapper contract with data `{schema_version, op: "remove", mode, target, removed, reverted_to_builtin}`
- [ ] [P12-T04] Implement `thoth modes remove` — click command, `get_modes_remove_data` + `_op_remove`, `ConfigDocument.remove_mode(profile=...)`

#### `thoth modes rename OLD NEW [--project] [--config PATH] [--profile X] [--json]`
- [ ] [P12-TS05a] Renames a user-only mode in the chosen tier; OLD gone, NEW present with same keys
- [ ] [P12-TS05b] OLD is builtin → `BUILTIN_NAME_RESERVED` exit 1
- [ ] [P12-TS05c] OLD is overridden → refuses (must drop override first)
- [ ] [P12-TS05d] NEW is a builtin name → `DST_NAME_TAKEN` exit 1
- [ ] [P12-TS05e] NEW already exists in the destination tier → `DST_NAME_TAKEN` exit 1
- [ ] [P12-TS05f] Absent OLD in chosen tier → `MODE_NOT_FOUND` exit 1
- [ ] [P12-TS05g] Targeting matrix (same shape as TS01h); rename targets the SAME tier (no cross-tier rename)
- [ ] [P12-TS05h] `--json` envelope follows the existing wrapper contract with data `{schema_version, op: "rename", from, to, target, renamed}`
- [ ] [P12-T05] Implement `thoth modes rename` — click command, `get_modes_rename_data` + `_op_rename`, `ConfigDocument.rename_mode(profile=...)`

#### `thoth modes copy SRC DST [--from-profile X] [--override] [--project] [--config PATH] [--profile Y] [--json]`
- [ ] [P12-TS06a] Builtin-only SRC: writes the destination mode with the builtin's effective keys
- [ ] [P12-TS06b] User SRC: writes destination with SRC's keys; SRC unchanged
- [ ] [P12-TS06c] Overridden SRC: writes the *effective* config (builtin layered with override) to DST
- [ ] [P12-TS06d] DST is a builtin name without `--override` → `DST_NAME_TAKEN` exit 1; with `--override`, writes the same-named override in the selected destination tier; `--override` on a non-builtin DST (e.g. `copy src new_dst --override`) is rejected with `USAGE_ERROR` exit 2 (symmetric with `add`'s strict-on-non-builtin rule)
- [ ] [P12-TS06e] DST already exists in destination tier → `DST_NAME_TAKEN` exit 1
- [ ] [P12-TS06f] Absent SRC in selected source tier → `MODE_NOT_FOUND` exit 1
- [ ] [P12-TS06g1] Direction: **base → base** (no `--from-profile`, no `--profile`): reads `[modes.SRC]`, writes `[modes.DST]`
- [ ] [P12-TS06g2] Direction: **base → overlay** (no `--from-profile`, `--profile dev`): reads `[modes.SRC]`, writes `[profiles.dev.modes.DST]`
- [ ] [P12-TS06g3] Direction: **overlay → base** (`--from-profile dev`, no `--profile`): reads `[profiles.dev.modes.SRC]`, writes `[modes.DST]`
- [ ] [P12-TS06g4] Direction: **overlay → overlay** cross-profile (`--from-profile dev --profile ci`): reads `[profiles.dev.modes.SRC]`, writes `[profiles.ci.modes.DST]`; same-profile overlay→overlay (`--from-profile dev --profile dev`) is also valid
- [ ] [P12-TS06g5] Targeting matrix for the file axis (same shape as TS01h): `--project` and `--config PATH` apply to the DST file; `--from-profile` does not have a file-axis counterpart (SRC is always read from the same file as DST or, for cross-file reads, the user does it in two steps)
- [ ] [P12-TS06h] `--json` envelope follows the existing wrapper contract with data `{schema_version, op: "copy", from, to, source_tier, target, copied}` — `source_tier` is `"modes"` or `"profiles.<X>.modes"`; `target.tier` likewise reflects DST
- [ ] [P12-T06] Implement `thoth modes copy` — click command, `get_modes_copy_data` + `_op_copy`, `ConfigDocument.copy_mode(from_profile=..., profile=...)`

#### Cross-cutting
- [ ] [P12-TS07a] tomlkit round-trip preserves comments and trailing whitespace through every mutation across all targeting combinations (parameterized: 6 ops × 6 targeting combos)
- [ ] [P12-TS07b] All `--json` data payloads share a single `SCHEMA_VERSION` constant inside the existing `status`/`data` wrapper; `target` sub-object shape is uniform across ops
- [ ] [P12-TS07c] Subprocess tests through the click CLI (relies on `ignore_unknown_options=True` from P11) for every op, including `--profile X` flag passing
- [ ] [P12-TS07d] `thoth help modes` epilog and `show_modes_help()` list every new op with examples covering `--project`, `--config PATH`, `--profile`, `--override`, and `--from-profile`
- [ ] [P12-TS07e] Layering: when both `[modes.X]` and `[profiles.dev.modes.X]` exist, `thoth modes list --name X --profile dev` reflects overlay value and `thoth modes list --name X` reflects base value. Validates that P12 mutators land in the right tier and P21*'s overlay reader still resolves correctly across the full set of P12-introduced primitives.
- [ ] [P12-T07] Help integration — extend `show_modes_help()` and the click group epilog; keep `thoth help modes` in sync

#### Removed-from-scope (already shipped under P13)

The original P12 design included two pre-work tasks that already shipped
under P13 — see P13-TS03 (shared-secrets tests) and P13-T04 (secrets
helper extraction).

#### Regression
- [ ] [P12-TS08] Full `uv run pytest tests/` + `./thoth_test -r` green; existing P11 read paths (`thoth modes list`, `--json`, `--name`, `--source`, `--full`, `--profile`) unchanged
- [ ] Regression Test Status

### Deliverable
```bash
$ thoth modes add my_brief --model gpt-4o-mini --description "terse daily brief"
Added mode 'my_brief' (model=gpt-4o-mini, kind=immediate)
# → ~/.thoth/thoth.config.toml [modes.my_brief]

$ thoth modes set my_brief temperature 0.2
Set my_brief.temperature = 0.2

$ thoth modes add team_review --model o1-preview --kind background --project
Added mode 'team_review' (model=o1-preview, kind=background)
# → ./thoth.config.toml [modes.team_review]

$ thoth modes add cheap_test --model gpt-4o-mini --profile dev
Added mode 'cheap_test' under profile 'dev' (kind=immediate)
# → ~/.thoth/thoth.config.toml [profiles.dev.modes.cheap_test]

$ thoth modes copy deep_research custom_research
Copied 'deep_research' (overridden) → 'custom_research' (user)

$ thoth modes rename my_brief brief
Renamed 'my_brief' → 'brief'

$ thoth modes unset brief temperature
Unset brief.temperature

$ thoth modes remove brief
Removed mode 'brief'

$ thoth modes set deep_research parallel false --json | jq .
{ "status": "ok",
  "data": { "schema_version": "1", "op": "set", "mode": "deep_research",
    "target": {"file": "~/.thoth/thoth.config.toml", "tier": "modes"},
    "key": "parallel", "value": false, "wrote": true } }
```

### Automated Verification
- `just check` passes
- `uv run pytest tests/` passes
- `./thoth_test -r` passes
- Every mutator round-trips through tomlkit without losing comments across all targeting combinations
- `--json` envelopes use the existing `status`/`data` wrapper; data payloads share `schema_version: "1"` and a uniform `target` shape
- Builtin-name guard blocks `add` without `--override`, blocks `copy` to builtin destinations without `--override`, and blocks `remove` / `rename` of builtins regardless of `--profile`
- `--project + --config PATH` rejected with `USAGE_ERROR` exit 2 on every mutator

### Manual Verification
- After `thoth modes add my_brief --model gpt-4o-mini`, `thoth modes list` shows it with `source=user`
- After `thoth modes set deep_research parallel false`, `thoth modes list --name deep_research` shows `source=overridden` with `parallel: true → false`
- `thoth modes remove deep_research` reverts the override; `thoth modes list --name deep_research` shows `source=builtin`
- `--project` flag writes to `./thoth.config.toml`, not `~/.thoth/thoth.config.toml`
- `--config PATH` writes to PATH
- `--profile dev` writes to `[profiles.dev.modes.<name>]`; the mode is invisible without `--profile dev` / `THOTH_PROFILE=dev`
- `--profile dev --project` writes to `./thoth.config.toml [profiles.dev.modes.<name>]`
