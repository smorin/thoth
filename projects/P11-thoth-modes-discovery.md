# P11 — `thoth modes` Discovery Command (v2.11.0)

**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)

**Status:** `[x]` Completed (v2.11.0).

**Goal**: Give users one authoritative place to see all research modes — built-in and user-defined — with provider, model, kind (immediate vs background), and origin source, so they don't need to read `config.py` or guess from descriptions. Also consolidates mode enumeration through a single helper, removing drift across `cli.py`, `help.py`, and `interactive.py`.

**Out of Scope**
- Editing/adding modes from the CLI (use `thoth config set` / `edit` as today)
- Changing how modes actually execute at runtime (other than the `is_background_mode` helper refactor)
- Reworking the existing `thoth --help` mode listing beyond a one-line pointer + teaser

### Design Notes
- Single derivation point `is_background_mode(mode_config) -> bool` in `src/thoth/config.py`: `bool(mode_config.get("async"))` if set, else `"deep-research" in mode_config.get("model", "")`. Replace ad-hoc check at `src/thoth/providers/openai.py:175,182`.
- Source classification: `builtin` (in `BUILTIN_MODES`, not in TOML), `user` (TOML only), `overridden` (both).
- Normalize `providers` (plural) vs `provider` (singular) into a single `providers: list[str]` on `ModeInfo`.
- Default sort order: `source` → `kind` → `provider` → `model` → `name` (stable/deterministic).
- Secret masking + TTY auto-detect parity with `thoth config` (reuse `_mask_in_tree` / `_is_secret_key`). No `--no-color` flag — auto-detect instead.
- JSON output includes `schema_version: "1"`.
- Tolerate broken user modes: show row with `kind=unknown` + yellow warning, don't crash.
- `thinking` mode: change `model` from `o3-deep-research` to `o3` to match its "quick analysis" description and make it actually immediate.

### Tests & Tasks
- [x] [P11-TS00] Tests for `is_background_mode` helper: explicit `async: true`, explicit `async: false` overrides deep-research model, model contains `deep-research`, model without it, missing model key
- [x] [P11-T00] Implement `is_background_mode` in `src/thoth/config.py`; refactor `providers/openai.py:175,182` + `providers/__init__.py:111` to call it; change `BUILTIN_MODES["thinking"]["model"]` to `"o3"`
- [x] [P11-TS01] Tests for `list_all_modes(cm) -> list[ModeInfo]` returning `{name, source, provider(s), model, kind, description, overrides, schema_version}`. Cover: pure builtin, user-only mode, overridden mode, per-field override detection, `providers` (list) normalization, malformed mode → `kind=unknown` + warning collected
- [x] [P11-T01] Implement `list_all_modes` + `ModeInfo` in `src/thoth/modes_cmd.py`
- [x] [P11-TS02] CLI tests for `thoth modes`: default table + sort order, `--json` shape with `schema_version`, `--source builtin|user|overridden|all` filter, `--show-secrets` unmasks, default masks api_key inside a mode. Use test-isolation fixture (`isolated_thoth_home` + autouse `COLUMNS=200`) — does NOT read the real `~/.thoth/config.toml`
- [x] [P11-T02] Implement `modes_cmd.py` dispatch + Rich table renderer + JSON serializer + secret masking + per-call Console for dynamic width
- [x] [P11-TS05] Tests for `thoth modes --name <mode>` detail view: override diff, `--full` dumps entire `system_prompt`, unknown name returns exit 1
- [x] [P11-T03] Implement `--name` detail view with per-field override diff and `--full` flag
- [x] [P11-T04] Wire `modes` into `src/thoth/cli.py` dispatch (parallel to `config`); add `show_modes_help()` in `src/thoth/help.py`; replace per-mode epilog loop with names-only teaser + pointer; include JSON schema snippet in help
- [x] [P11-TS03] Test that `thoth help modes` prints the new help block and that help epilog still lists mode names
- [x] [P11-TS04] Regression test asserting `BUILTIN_MODES.items()` is no longer iterated in `interactive.py` / `help.py`
- [x] [P11-T05] Route `interactive.py` (`set_mode`, `_show_mode_selection`) mode listing through `list_all_modes()`; validation branches still use `BUILTIN_MODES` (intentional — interactive user-mode support out of scope)
- [x] [P11-T06] Added `ignore_unknown_options=True` in root click context so `--json` / `--name` / `--source` flags pass through to subcommands; updated thoth_test EXIT-02 to assert exit 2 via `thoth modes bogus_op` (the `thoth --invalid-flag` case became "prompt" per new click behavior)
- [x] Regression Test Status — full suite 169/169 pytest + 63/64 thoth_test (1 skipped, 0 failed) green

### Deliverable
```bash
$ thoth modes
 Mode            Source       Provider   Model                   Kind        Description
 default         builtin      openai     o3                      immediate   Default mode — passes prompt directly…
 clarification   builtin      openai     o3                      immediate   Clarifying takes the prompt…
 thinking        builtin      openai     o3                      immediate   Quick thinking and analysis mode…
 mini_research   builtin      openai     o4-mini-deep-research   background  Fast, lightweight research mode…
 exploration     builtin      openai     o3-deep-research        background  Exploration looks at the topic…
 my_brief        user         openai     gpt-4o-mini             immediate   (user-defined)
 deep_research   overridden   openai     o3-deep-research        background  Deep research mode using OpenAI…

$ thoth modes --name deep_research
Mode: deep_research           Source: overridden
Providers: openai             Model: o3-deep-research        Kind: background
Overrides (builtin → effective):
  parallel:       true  →  false
  system_prompt:  (312 chars)  →  (198 chars)   [use --full to see]

$ thoth modes --json | jq '.[] | select(.kind == "background") | .name'
```

### Automated Verification
- `make env-check` passes
- `just check` passes (ruff + ty)
- `./thoth_test -r` passes
- `just test-lint` and `just test-typecheck` pass
- `thoth modes --json` validates against documented schema (`schema_version: "1"`)
- API key values inside a `[modes.*]` table are masked by default

### Manual Verification
- `thoth modes` prints table sorted by source, kind, provider, model
- `thoth modes --name thinking` reflects the `o3` fix and shows `Kind: immediate`
- Running a background mode still routes to OpenAI background responses (sanity check: `thoth deep_research "hello" --async`)
- `thoth --help` still shows mode names (teaser) and points at `thoth modes` for details
