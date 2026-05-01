# P16 PR2 — Remove Legacy Shims, Add resume + ask Subcommands (v3.0.0)

**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)

**Status:** `[x]` Completed.

**Goal**: Remove every flag-style shim cataloged in the legacy-form audit; migrate each to a canonical Click subcommand or sub-subcommand; ensure no functionality silently disappears (every removed form must either map to a new form OR be explicitly dropped with documented justification). Triggers v3.0.0 MAJOR.

**Completed:** 2026-04-26
**Pytest count:** 389 passed
**thoth_test count:** 63 passed, 10 skipped (mock-only run: 63 passed, 1 skipped)
**Commits landed on main:** 12 (Tasks 1–12 per the implementation plan)
**FU01–FU05** remain unchecked (deferred to PR3 / P12 / Click 9.0 per scope).

**Specs**:
- `docs/superpowers/specs/2026-04-26-p16-pr2-design.md` — PR2-specific design (decisions Q1-Q7-PR2, components, testing strategy, rollout)
- `docs/superpowers/specs/2026-04-25-promote-admin-commands-design.md` — original P16 design (decisions Q2-Q7 from PR1 brainstorming)
- `docs/superpowers/specs/2026-04-26-p16-pr2-legacy-form-audit.md` — comprehensive shim inventory (the parity checklist)

**Plan**: `docs/superpowers/plans/2026-04-26-p16-pr2-implementation.md` — 12 TDD tasks mapping 1:1 to spec §10's commit sequence (~2,505 lines with bite-sized steps + concrete code blocks)

**Out of scope (PR3)**
- `--json` for every data/action admin command (already partially shipped; full coverage in PR3)
- `completion` subcommand and dynamic completers
- Per-handler `get_*_data()` extraction
- Mode-editing operations (`thoth modes set/add/unset` — P12)
- New 3/4 exit codes — keep today's 0/1/2 scheme (spec §8.3)
- Behavior changes in handlers below the dispatch (handlers in `commands.py`/`config_cmd.py`/`modes_cmd.py` stay byte-identical)

### Architectural decisions locked from brainstorming
- [Q1-PR2] resume option-set: TIGHT + HONOR — accepts `--verbose`, `--config`, `--quiet`, `--no-metadata`, `--timeout`, `--api-key-{openai,perplexity,mock}`; rejects `--auto`, `--input-file`, `--prompt-file`, `--combined`, `--project`, `--output-dir`, `--prompt`, `--async`, `--pick-model`, `--version`, `--interactive`, `--clarify` with clear `BadParameter` errors
- [Q2-PR2] modes hidden-subcommand shim: REMOVE in PR2 (decision A — full consistency with providers shim removal)
- [Q3-PR2] `ask` is a NEW canonical subcommand (positional-arg equivalent of `-q/--prompt`); bare-prompt and `-q` continue to work alongside
- [Q4-PR2] `-R` short alias for `--resume`: REMOVED with `--resume` (audit line 8)
- [Q5-PR2] `ignore_unknown_options=True` on top-level group: REMOVED (typos like `--verbsoe` exit 2 instead of being silently swallowed)
- [More decisions captured during brainstorming will be added as they're locked]

### Migration tasks (one per legacy form — every section-10 row)

**`--resume` family (audit lines 411-416)**
- [x] [P16PR2-T01] Migrate `thoth --resume OP_ID` → `thoth resume OP_ID`. Implement `resume` subcommand at `src/thoth/cli_subcommands/resume.py` accepting honored options per [Q1-PR2]. Update emitters at `run.py:629/654/827/854`, `signals.py:93/99`, `commands.py:227/238`, `help.py:134`. Update fixture regex at `tests/_fixture_helpers.py:63-65`.
- [x] [P16PR2-T02] Remove top-level `--resume`/`-R` global flag from `src/thoth/cli.py:477`. Remove `_dispatch_click_fallback` resume branch at `cli.py:347-358`. Add gating: `thoth --resume OP_ID` exits 2 with stderr suggestion `"Use 'thoth resume OP_ID'"`.
- [x] [P16PR2-T03] Remove `-R OP_ID` short alias (same removal — both `--resume` and `-R` reach same handler per audit line 8). Confirm exit-2 hint applies.
- [x] [P16PR2-T04] Reject combo `thoth resume <op> --pick-model` at the new `resume` subcommand level (currently rejected at cli.py:621-622 — preserve `BadParameter` semantics, exit 2). Migrate `tests/test_pick_model.py:48,109`.
- [x] [P16PR2-T05] Reject combo `thoth resume <op> --async` at the new subcommand (currently rejected at cli.py:609-610). Audit line 414 — currently untested in pytest.
- [x] [P16PR2-T06] Reject combo `thoth resume <op> --interactive` / `--clarify` (DESIGN: per [Q1-PR2] TIGHT, both rejected with `BadParameter`). Currently silently lets resume win (audit line 60) — make explicit error.
- [x] [P16PR2-T07] Honor `thoth --config <path> resume <op>` group inheritance via `_apply_config_path` BEFORE resume call (preserve cli.py:345 production behavior currently untested per audit line 43, line 416).

**`providers --` family (audit lines 417-430)**
- [x] [P16PR2-T08] Remove `providers -- --list` legacy shim implementation at `src/thoth/cli_subcommands/providers.py:34-99`. Add gating: exits 2 with stderr suggestion `"Use 'thoth providers list'"`.
- [x] [P16PR2-T09] Remove `providers -- --models` legacy shim. Add gating exit-2 suggestion `"Use 'thoth providers models'"`.
- [x] [P16PR2-T10] Remove `providers -- --keys` legacy shim (currently UNTESTED in pytest, audit line 114). Add gating exit-2 suggestion `"Use 'thoth providers check'"`.
- [x] [P16PR2-T11] DESIGN-DECISION: `providers -- --refresh-cache` ALONE today is silent no-op (audit line 115, line 420). Decide: gate to exit 2 with suggestion to use `providers models --refresh-cache`, OR drop silently. Recommend exit 2.
- [x] [P16PR2-T12] DESIGN-DECISION: `providers -- --no-cache` ALONE today is silent no-op (audit line 116, line 421). Same decision as T11.
- [x] [P16PR2-T13] Add `--refresh-cache` flag to `providers models` leaf in `cli_subcommands/providers.py`; forward to `commands.providers_command(refresh_cache=True)` (audit line 422 — UNTESTED but in production via legacy `-- --models --refresh-cache`).
- [x] [P16PR2-T14] Add `--no-cache` flag to `providers models` leaf; forward to `commands.providers_command(no_cache=True)` (audit line 423 — UNTESTED but in production).
- [x] [P16PR2-T15] Verify `providers models --provider X --refresh-cache` works after T13 (PRD v24 documents this; audit line 424).
- [x] [P16PR2-T16] Reject combo `providers models --refresh-cache --no-cache` with `BadParameter` (audit line 425, line 129 — currently silent ambiguity). Add explicit mutex.
- [x] [P16PR2-T17] Document removal of `--list --keys` silent-drop combo (audit line 426 — resolved structurally by separate leaves; no action needed beyond confirmation).
- [x] [P16PR2-T18] Remove in-group hidden shim `providers --list` at `providers.py:140-149`. Add gating exit-2 suggestion (audit line 427).
- [x] [P16PR2-T19] Remove in-group hidden shim `providers --models` at `providers.py:152-161`. Add gating exit-2 suggestion (audit line 428).
- [x] [P16PR2-T20] Remove in-group hidden shim `providers --keys` at `providers.py:164-173`. Add gating exit-2 suggestion (audit line 429).
- [x] [P16PR2-T21] Remove undocumented `--check` alias for `--keys` at `providers.py:53` (audit line 120, line 430). No test, no docs — drop silently or with exit-2 hint.
- [x] [P16PR2-T22] DESIGN-DECISION: `thoth providers` (no leaf) — currently exits 0 with help (providers.py:60); `tests/test_p16_dispatch_parity.py:89` accepts 0 OR 2. Pick canonical exit (audit line 250, line 431). Recommend Click default exit 2 for required-subcommand consistency.
- [x] [P16PR2-T23] Update `commands.py` self-references in help text (commands.py:321,333,335,337,339,341,343,409,410) from `thoth providers -- [OPTIONS]` to flat forms (audit line 211).
- [x] [P16PR2-T24] Update `src/thoth/providers/openai.py:69` reference `'thoth providers -- --models --provider openai'` to new flat form (audit line 212).

**`modes --` hidden-shim family (audit lines 432-440)**
- [x] [P16PR2-T25] DESIGN-DECISION: `thoth modes` (no leaf) — currently behaves as `modes list`; `tests/test_p16_thothgroup.py:223` asserts bare form lists modes (audit line 432). Decide: keep shortcut OR require explicit leaf. Per [Q2-PR2] FULL-CONSISTENCY: require explicit leaf; bare form exits 2 with suggestion `"Use 'thoth modes list'"`.
- [x] [P16PR2-T26] Remove `thoth modes --json` hidden subcommand at `cli_subcommands/modes.py:72-75`. Add gating exit-2 suggestion `"Use 'thoth modes list --json'"` (audit line 433 — UNTESTED directly).
- [x] [P16PR2-T27] Remove `thoth modes --show-secrets` hidden subcommand at `modes.py:78-81`. Add gating exit-2 suggestion. **Security-relevant** per audit line 287: callers depending on secret-reveal would silently get masked output. Migration hint must be loud.
- [x] [P16PR2-T28] Remove `thoth modes --full` hidden subcommand at `modes.py:84-87`. Add gating exit-2 suggestion (audit line 435).
- [x] [P16PR2-T29] Remove `thoth modes --name <NAME>` hidden subcommand at `modes.py:90-98`. Add gating exit-2 suggestion (audit line 436).
- [x] [P16PR2-T30] Remove `thoth modes --source <SRC>` hidden subcommand at `modes.py:101-109`. Add gating exit-2 suggestion (audit line 437).
- [x] [P16PR2-T31] DESIGN-DECISION: `thoth modes <UNKNOWN_OP>` — currently `ModesGroup.invoke` routes to `modes_command(arg0, …)` which returns 2 with `"unknown modes op: ..."` wording (audit line 438; thoth_test:2128). Decide: keep custom wording OR accept Click default `"No such command 'bogus_op'"`. Either way, exit code stays 2.
- [x] [P16PR2-T32] Promote `--json`, `--show-secrets`, `--full`, `--name`, `--source` to typed Click options on `modes list` leaf (audit line 440 KEEP-but-promote). Currently passthrough via `_PASSTHROUGH_CONTEXT`.

**`config` subgroup promote-to-typed (audit lines 441-462)**
- [x] [P16PR2-T33] Promote `--raw` on `config get` to typed Click option (audit line 443). **Security-adjacent**: `config_cmd.py:104` shows `--raw` BYPASSES secret masking even without `--show-secrets`. Verbatim line: `if _is_secret_key(key) and not show_secrets and not raw:`. Must be loud-documented.
- [x] [P16PR2-T34] DESIGN-DECISION: `config get KEY --raw` masking-bypass behavior (audit line 302, line 398, line 443). Options: (a) keep as masking bypass (loud-document in `--help`), (b) require explicit `--show-secrets` even with `--raw`. Recommend (b) — explicit security posture.
- [x] [P16PR2-T35] Promote `--json` on `config get` to typed Click option (audit line 444 — UNTESTED).
- [x] [P16PR2-T36] Promote `--show-secrets` on `config get` to typed Click option (audit line 445 — UNTESTED, security-adjacent).
- [x] [P16PR2-T37] Promote `--layer` on `config get` to typed Click option (audit line 446 — UNTESTED; returns wrong-layer data silently if dropped).
- [x] [P16PR2-T38] Promote `--project` on `config set` to typed Click option (audit line 448 — silent drop = wrong target file: `./thoth.toml` vs `~/.thoth/config.toml`).
- [x] [P16PR2-T39] Promote `--string` on `config set` to typed Click option (audit line 449). Without it, `_parse_value` (config_cmd.py:111-124) silently coerces `"true"/"false"/numbers` to bool/int/float — losing string intent.
- [x] [P16PR2-T40] Promote `--project` on `config unset` to typed Click option (audit line 451 — wrong-target risk).
- [x] [P16PR2-T41] Promote `--keys` on `config list` to typed Click option (audit line 453). DESIGN: reject combo `--keys --json` / `--keys --show-secrets` OR document precedence (currently `--keys` wins silently per `config_cmd.py:330-333`).
- [x] [P16PR2-T42] Promote `--json` on `config list` to typed Click option (audit line 454).
- [x] [P16PR2-T43] Promote `--show-secrets` on `config list` to typed Click option (audit line 455 — security-adjacent).
- [x] [P16PR2-T44] Promote `--layer` on `config list` to typed Click option (audit line 456).
- [x] [P16PR2-T45] Promote `--project` on `config path` to typed Click option (audit line 459). Currently `config_cmd.py:347-358` uses `"--project" in args` truthiness — typo `--projects` is silently NOT honored.
- [x] [P16PR2-T46] Promote `--project` on `config edit` to typed Click option (audit line 461).
- [x] [P16PR2-T47] DESIGN-DECISION: `thoth config help` (audit line 462) — currently two divergent paths render different output: `config help` leaf at `config_cmd._op_help` calls `help.show_config_help()` (rich-formatted), while `thoth help config` at `help_cmd.py:31-42` forwards to `config --help` (Click format). Pick one path; converge or document.

**Top-level / cross-cutting (audit lines 463-486)**
- [x] [P16PR2-T48] Add `thoth ask PROMPT` as NEW canonical subcommand at `src/thoth/cli_subcommands/ask.py` (audit line 474 — currently in `RUN_COMMANDS` at help.py:14 but NOT a registered subcommand). Inherit full research flag set per [Q3-PR2]. Register in `cli.add_command(...)` and `ThothGroup.format_commands` "Run research" section.
- [x] [P16PR2-T49] DESIGN-DECISION: `thoth deep_research "topic"` (mode-positional via `ThothGroup.invoke` at help.py:64-89) — KEEP? row at audit line 473. Removing would force mass test migration. Recommend KEEP (currently covered widely, low ROI to remove).
- [x] [P16PR2-T50] DESIGN-DECISION: `thoth "bare prompt"` (whole-argv-as-prompt via `ThothGroup.invoke`) — KEEP? row at audit line 476. Same scope-risk as T49. Recommend KEEP (`tests/test_cli_regressions.py:55` and many others).
- [x] [P16PR2-T51] Remove `thoth -h auth` / `thoth --help auth` parse-time hijack at `help.py:51-55` per Q5-PR2 row 13.ii; Click now rejects the extra topic argument.
- [x] [P16PR2-T52] Remove `thoth help auth` virtual topic at `help_cmd.py:25-28`; retain `render_auth_help()` for docs/future real command reuse.
- [x] [P16PR2-T53] DESIGN-DECISION: `thoth --clarify` (alone, without `--interactive`) — currently silent no-op (audit line 481, line 391). Decide: exit 2 if alone, OR keep silent. Recommend exit 2.
- [x] [P16PR2-T54] Remove dead `completion` listing from `ADMIN_COMMANDS` at `help.py:20` (audit line 472). Currently a phantom in help renderer with no Click command registered. Removal happens here; real `completion` subcommand lands in PR3.
- [x] [P16PR2-T55] DESIGN-DECISION: `thoth status` (no arg) currently exits 1 with `"status command requires an operation ID"` (status.py:16-18). Click's natural default for missing required argument is exit 2. Audit line 331, line 465. Decide: recapture baseline at exit 1 (preserve divergence) OR change to exit 2 (Click natural). Recommend exit 2.
- [x] [P16PR2-T56] Remove `ignore_unknown_options=True` from top-level `@click.group()` decorator per [Q5-PR2]. Audit hidden behavior change: typos like `thoth --verbsoe deep_research` will exit 2 instead of being silently absorbed. Add CHANGELOG callout.
- [x] [P16PR2-T57] Audit and remove `ctx.args` plumbing in `cli.py` if no longer reachable after T56 (spec §5.3).
- [x] [P16PR2-T58] DESIGN-DECISION: `--pick-model` precedence predicate at `cli.py:621-624` mixes `resume_id`, `interactive`, AND `first in ctx.command.commands` into a triple-OR (audit line 392, line 484-485). Decompose into separate explicit mutex checks. Cases for `interactive` and `first-in-commands` are UNTESTED.
- [x] [P16PR2-T59] Add test for `--pick-model --interactive` mutex (audit line 484 — UNTESTED).
- [x] [P16PR2-T60] Add test for `--pick-model <subcommand>` mutex e.g. `--pick-model providers` (audit line 485 — UNTESTED).

**README / docs / migration housekeeping**
- [x] [P16PR2-T61] Update `README.md:218` example `thoth --resume research-…` to new `thoth resume …` form.
- [x] [P16PR2-T62] Update `manual_testing_instructions.md` to use new forms (post-PR2 manual flow).
- [x] [P16PR2-T63] Update help epilog at `src/thoth/help.py:134` from `thoth --resume op_abc123` example to `thoth resume op_abc123`.
- [x] [P16PR2-T64] Update `planning/thoth.prd.v24.md` references to old forms.
- [x] [P16PR2-T65] CHANGELOG entries: `feat!: replace --resume flag with 'thoth resume' subcommand`, `feat!: remove 'thoth providers -- --…' legacy shim`, `feat!: remove 'thoth modes --…' hidden-subcommand shim`, `feat!: add 'thoth ask PROMPT' subcommand`, `feat!: remove ignore_unknown_options (typos now exit 2)` — release-please picks up the `!` for v3.0.0.
- [x] [P16PR2-T66] Archive `planning/project_promote_commands.md` to `archive/` per CLAUDE.md versioning policy (now superseded by spec).

### Silent-drop resolution tasks (one per untested-but-in-production behavior, audit lines 504-516)

- [x] [P16PR2-T67] SILENT-DROP: `thoth --resume <op>` exit code 6 (op not found) at `run.py:719-720`. Preserve in new `resume` subcommand. Add explicit test (P16PR2-TS04).
- [x] [P16PR2-T68] SILENT-DROP: `thoth --resume <op> --config <path>` config inheritance at `cli.py:345`. Preserve in new `resume` subcommand per [Q1-PR2] HONOR. Add explicit test (P16PR2-TS05).
- [x] [P16PR2-T69] SILENT-DROP: `thoth --resume <op> --verbose` verbose flow-through at `cli.py:354`. Preserve in new `resume` subcommand per [Q1-PR2]. Add explicit test (P16PR2-TS06).
- [x] [P16PR2-T70] SILENT-DROP: `thoth --resume <op> -i / --clarify` resume-silently-wins behavior at `cli.py:347,360`. Per [Q1-PR2] TIGHT, REJECT with `BadParameter` (covered by P16PR2-T06).
- [x] [P16PR2-T71] SILENT-DROP: `thoth providers -- --keys` (no test, audit line 508). Resolved by P16PR2-T10 gating; add new-form test for `providers check` at P16PR2-TS11.
- [x] [P16PR2-T72] SILENT-DROP: `thoth providers -- --refresh-cache` alone (silent no-op, audit line 509). Resolved by P16PR2-T11 gating decision.
- [x] [P16PR2-T73] SILENT-DROP: `thoth providers -- --no-cache` alone (silent no-op, audit line 510). Resolved by P16PR2-T12 gating decision.
- [x] [P16PR2-T74] SILENT-DROP: `thoth providers -- --models --refresh-cache` combo (audit line 511). Resolved structurally by P16PR2-T13.
- [x] [P16PR2-T75] SILENT-DROP: `thoth providers -- --models --no-cache` combo (audit line 512). Resolved structurally by P16PR2-T14.
- [x] [P16PR2-T76] SILENT-DROP: `thoth providers -- --models --provider X --refresh-cache` per-provider refresh (audit line 513, documented in PRD v24). Resolved structurally; add test at P16PR2-TS15.
- [x] [P16PR2-T77] SILENT-DROP: `thoth providers -- --refresh-cache --no-cache` silent ambiguity at `commands.py:454-455` (audit line 514, line 129). Resolved by P16PR2-T16 explicit mutex rejection. Add test asserting `BadParameter`.
- [x] [P16PR2-T78] SILENT-DROP: `thoth providers -- --list --keys` (silent drop of second flag at `commands.py:363,413,442` per audit line 515, line 130). Resolved structurally by separate leaves.
- [x] [P16PR2-T79] SILENT-DROP: `providers --check` alias for `--keys` (in-group shim, no test, no docs, audit line 516). Resolved by P16PR2-T21 removal.

### Test-coverage tasks (one per row of section 10 needing a test)

**resume subcommand tests**
- [x] [P16PR2-TS01] Test: `thoth resume <valid_op>` exits 0 + emits `"Research completed"`. Migrates `tests/test_resume.py:48`.
- [x] [P16PR2-TS02] Test: `thoth resume <op>` (permanent fail fixture) exits 7 + emits `"failed permanently"`. Migrates `tests/test_resume.py:90`.
- [x] [P16PR2-TS03] Test: `thoth resume <op>` (already completed) exits 0 + emits `"already completed"`. Migrates `tests/test_resume.py:131`.
- [x] [P16PR2-TS04] Test: `thoth resume MISSING_OP` exits 6 (audit line 70 — NEW, fills silent-drop gap T67).
- [x] [P16PR2-TS05] Test: `thoth --config <path> resume <op>` honors config inheritance (NEW, fills silent-drop gap T68).
- [x] [P16PR2-TS06] Test: `thoth resume <op> --verbose` verbose flow-through (NEW, fills silent-drop gap T69).
- [x] [P16PR2-TS07] Mutex tests: `thoth resume <op> --async`, `... --pick-model`, `... -q "prompt"`, `... -i`, `... --clarify`, `... --version` — each exits 2 with `BadParameter` (audit lines 414-415, line 60). NEW.
- [x] [P16PR2-TS08] Migrate `tests/test_pick_model.py:48,109` (`--pick-model --resume`) to new `resume` subcommand form.
- [x] [P16PR2-TS09] Migrate `tests/test_cli_regressions.py:76` (BUG-CLI-002 regression) to `thoth resume op_regression`.
- [x] [P16PR2-TS10] Verify `tests/test_cli_regressions.py:164` (BUG-CLI-010 — `--version` mutex) still triggers under new shape.

**resume gating tests**
- [x] [P16PR2-TS11] Category-F gate: `thoth --resume OP_ID` exits 2 with stderr hint `"Use 'thoth resume OP_ID'"` (covers T02).
- [x] [P16PR2-TS12] Category-F gate: `thoth -R OP_ID` exits 2 with same hint (covers T03).

**resume emitter / consumer tests**
- [x] [P16PR2-TS13] Update `tests/test_progress_spinner.py:152` to assert emitter prints `"Resume later: thoth resume op_abc123"`.
- [x] [P16PR2-TS14] Update `tests/test_cli_help.py:26` to assert `"thoth resume"` substring (was `"thoth --resume"`).
- [x] [P16PR2-TS15] Update `tests/_fixture_helpers.py:63-65` `extract_resume_id` regex from `r"thoth --resume\s+…"` to new form. Verify all RES-tests still extract op_id.
- [x] [P16PR2-TS16] Update thoth_test patterns at `thoth_test:2170` (TS-09 signal/Ctrl-C `r"Checkpoint saved\. Resume with: thoth --resume"`).
- [x] [P16PR2-TS17] Update thoth_test pattern at `thoth_test:2216` (TR-02 `r"Resume with: .*thoth --resume"`).
- [x] [P16PR2-TS18] Update thoth_test pattern at `thoth_test:2238` (TR-03 negative-assertion variant).

**providers subcommand tests**
- [x] [P16PR2-TS19] Test: `thoth providers list` exits 0 with all provider names (audit line 199).
- [x] [P16PR2-TS20] Test: `thoth providers list --provider X` filters to one provider (currently works in new form — confirm coverage).
- [x] [P16PR2-TS21] Test: `thoth providers models` exits 0 (audit line 201).
- [x] [P16PR2-TS22] Test: `thoth providers models --provider X` (no models) exits 1 (audit line 202).
- [x] [P16PR2-TS23] Test: `thoth providers models --provider invalid` exits 1, stderr contains verbatim `"Unknown provider: invalid"` AND `"Available providers: openai, perplexity, mock"` (audit line 154, line 207). Migrates `thoth_test:2290-2297` T-PROV-10.
- [x] [P16PR2-TS24] Test: `thoth providers check` exits 0 (all keys) or 2 (any missing) per audit line 203.
- [x] [P16PR2-TS25] Test: `thoth providers list` preserves verbatim `"Perplexity search AI (not.*implemented)"` row text (audit line 155, line 208). Migrates `thoth_test:2307` P07-M2-01.
- [x] [P16PR2-TS26] Test: `thoth help providers` preserves epilog patterns `--models.*List available models`, `--provider.*Filter by specific provider` (audit line 110, line 209). Migrates thoth_test T-PROV-09.
- [x] [P16PR2-TS27] Test: `thoth providers models --refresh-cache` triggers `"Fetching available models (refreshing cache)..."` from commands.py:445 (NEW, covers T13/T74).
- [x] [P16PR2-TS28] Test: `thoth providers models --no-cache` forwards `no_cache=True` (NEW, covers T14/T75).
- [x] [P16PR2-TS29] Test: `thoth providers models --refresh-cache --no-cache` rejected with `BadParameter` exit 2 (NEW, covers T16/T77).
- [x] [P16PR2-TS30] Test: `thoth providers models --provider openai --refresh-cache` works (NEW, covers T15/T76).
- [x] [P16PR2-TS31] Migrate `thoth_test:2260` T-PROV-07 `providers -- --models --provider mock` to `providers models --provider mock`.
- [x] [P16PR2-TS32] Migrate `thoth_test:2269` T-PROV-08 `providers -- --models` to `providers models`.

**providers gating tests**
- [x] [P16PR2-TS33] Category-F gate: `thoth providers -- --list` exits 2 with hint `"Use 'thoth providers list'"` (covers T08).
- [x] [P16PR2-TS34] Category-F gate: `thoth providers -- --models` exits 2 with hint (covers T09).
- [x] [P16PR2-TS35] Category-F gate: `thoth providers -- --keys` exits 2 with hint `"Use 'thoth providers check'"` (covers T10).
- [x] [P16PR2-TS36] Category-F gate: `thoth providers --list` (in-group hidden) exits 2 with hint (covers T18).
- [x] [P16PR2-TS37] Category-F gate: `thoth providers --models` (in-group hidden) exits 2 (covers T19).
- [x] [P16PR2-TS38] Category-F gate: `thoth providers --keys` (in-group hidden) exits 2 (covers T20).
- [x] [P16PR2-TS39] Update `tests/test_providers_subcommand.py:23-27` (`test_old_form_deprecated_but_works`) to assert exit-2-with-hint, OR delete if redundant with new TS33.
- [x] [P16PR2-TS40] Test: `thoth providers` (no leaf) exits per T22 decision (likely Click default exit 2). Verify `tests/test_p16_dispatch_parity.py:89` baseline.

**modes subcommand tests**
- [x] [P16PR2-TS41] Category-F gate: `thoth modes --json` exits 2 with hint `"Use 'thoth modes list --json'"` (covers T26).
- [x] [P16PR2-TS42] Category-F gate: `thoth modes --show-secrets` exits 2 with hint (covers T27).
- [x] [P16PR2-TS43] Category-F gate: `thoth modes --full` exits 2 with hint (covers T28).
- [x] [P16PR2-TS44] Category-F gate: `thoth modes --name X` exits 2 with hint (covers T29).
- [x] [P16PR2-TS45] Category-F gate: `thoth modes --source X` exits 2 with hint (covers T30).
- [x] [P16PR2-TS46] Test: `thoth modes` (no leaf) per T25 decision (exit 2 with `"Use 'thoth modes list'"` if removing default-to-list shortcut).
- [x] [P16PR2-TS47] Test: `thoth modes <UNKNOWN_OP>` per T31 decision (exit 2; wording either custom or Click-default).
- [x] [P16PR2-TS48] Test: `thoth modes list --json` (typed flag, NEW per T32).
- [x] [P16PR2-TS49] Test: `thoth modes list --show-secrets` (typed flag, NEW per T32).
- [x] [P16PR2-TS50] Test: `thoth modes list --full` (typed flag, NEW per T32).
- [x] [P16PR2-TS51] Test: `thoth modes list --name NAME` (typed flag, NEW per T32).
- [x] [P16PR2-TS52] Test: `thoth modes list --source SRC` (typed flag, NEW per T32).

**config subcommand tests**
- [x] [P16PR2-TS53] Test: `thoth config get KEY --raw` per T34 decision (masking-bypass behavior). Audit verbatim: `config_cmd.py:104` `if _is_secret_key(key) and not show_secrets and not raw:`. **Security-critical test.**
- [x] [P16PR2-TS54] Test: `thoth config get KEY --json` (typed flag, NEW per T35).
- [x] [P16PR2-TS55] Test: `thoth config get KEY --show-secrets` (typed flag, NEW per T36).
- [x] [P16PR2-TS56] Test: `thoth config get KEY --layer L` (typed flag, NEW per T37).
- [x] [P16PR2-TS57] Test: `thoth config set KEY VALUE` (NEW canonical).
- [x] [P16PR2-TS58] Test: `thoth config set KEY VALUE --project` (typed flag, NEW per T38).
- [x] [P16PR2-TS59] Test: `thoth config set KEY VALUE --string` (typed flag, NEW per T39 — verify `"true"` stays string not bool).
- [x] [P16PR2-TS60] Test: `thoth config unset KEY` (NEW canonical).
- [x] [P16PR2-TS61] Test: `thoth config unset KEY --project` (typed flag, NEW per T40).
- [x] [P16PR2-TS62] Test: `thoth config list --keys` per T41 decision (typed flag + combo policy).
- [x] [P16PR2-TS63] Test: `thoth config list --json` (typed flag, NEW per T42).
- [x] [P16PR2-TS64] Test: `thoth config list --show-secrets` (typed flag, NEW per T43).
- [x] [P16PR2-TS65] Test: `thoth config list --layer L` (typed flag, NEW per T44).
- [x] [P16PR2-TS66] Test: `thoth config list --keys --json` per T41 decision (reject combo OR document precedence).
- [x] [P16PR2-TS67] Test: `thoth config path` (NEW per audit line 458).
- [x] [P16PR2-TS68] Test: `thoth config path --project` (typed flag, NEW per T45).
- [x] [P16PR2-TS69] Test: `thoth config edit` (NEW per audit line 460).
- [x] [P16PR2-TS70] Test: `thoth config edit --project` (typed flag, NEW per T46).
- [x] [P16PR2-TS71] Test: `thoth config help` convergence per T47 decision (collapse to `thoth help config` OR keep leaf).

**ask subcommand tests**
- [x] [P16PR2-TS72] Test: `thoth ask "hello"` (mock provider) routes to default-mode research; equivalent to `thoth -q "hello"` and `thoth "hello"`.
- [x] [P16PR2-TS73] Test: `thoth ask "x" --mode deep_research --async` honors flags identically to bare-prompt path.
- [x] [P16PR2-TS74] Surprising-parse test: `thoth init` (subcommand) vs `thoth "init the database"` (bare-prompt) disambiguated correctly; `thoth ask` (no arg) exits 2.

**Top-level / cross-cutting tests**
- [x] [P16PR2-TS75] Test: `thoth list --all` (audit line 467 — UNTESTED in pytest).
- [x] [P16PR2-TS76] Test: `thoth help auth` virtual topic is removed and exits 2 (audit line 470 — covers T52).
- [x] [P16PR2-TS77] Test: `thoth -h auth` / `thoth --help auth` parse-time hijack is removed and no longer renders auth help (audit line 471 — covers T51).
- [x] [P16PR2-TS78] Test: `thoth --clarify` alone per T53 decision (audit line 481 — UNTESTED).
- [x] [P16PR2-TS79] Test: `thoth --pick-model --interactive` mutex (audit line 484 — UNTESTED, covers T59).
- [x] [P16PR2-TS80] Test: `thoth --pick-model providers` mutex (audit line 485 — UNTESTED, covers T60).
- [x] [P16PR2-TS81] Strict-options test: `thoth --verbsoe deep_research "x"` (typo) exits 2 with Click "no such option" error (covers T56 removal of `ignore_unknown_options`).
- [x] [P16PR2-TS82] Recapture `tests/baselines/status_no_args.json` per T55 decision (exit 1 vs exit 2).
- [x] [P16PR2-TS83] Recapture `tests/baselines/providers_list.json` if T18-T21 change wording (audit line 238).

### Out-of-PR2 follow-ups (deferred to PR3 or later)

- [ ] [P16PR2-FU01] (Deferred to PR3) Add `--json` to `resume`, `ask`, and every data/action admin command per spec §6.5 B-deferred extraction pattern.
- [ ] [P16PR2-FU02] (Deferred to PR3) Implement real `completion` Click subcommand (currently a phantom listing in `help.py:20` removed by P16PR2-T54).
- [ ] [P16PR2-FU03] (Deferred to PR3) `thoth resume <TAB>` op-id dynamic completer in `completion/sources.py`.
- [ ] [P16PR2-FU04] (Deferred to P12) Mode-editing operations: `thoth modes set/add/unset`.
- [ ] [P16PR2-FU05] (Deferred — Click 9.0) Re-evaluate `ctx.protected_args` deprecation warning suppression at `help.py:60-65`.

### Automated verification (PR2 acceptance criteria)
- [ ] `uv run pytest tests/` — green, count >= current baseline (312)
- [ ] `./thoth_test -r --skip-interactive` — green, count >= current baseline (63)
- [ ] `just check` — green
- [ ] `git grep "thoth --resume"` returns ZERO results in `src/`, `tests/`, `README.md`, `manual_testing_instructions.md` (except CHANGELOG and the spec/audit/plan docs themselves)
- [ ] `git grep "thoth providers --"` returns ZERO results in `src/`, `tests/`, README, docs (same exception)
- [ ] `git grep "thoth modes --"` returns ZERO results in `src/`, `tests/`, README, docs (same exception)
- [ ] Every row of audit section 10's master parity checklist has a checked-off "Test required" entry (cross-reference TS01-TS83 against audit lines 411-486)
- [ ] `grep -rn "ignore_unknown_options=True" src/thoth/cli.py` returns ZERO results (T56)

### Manual Verification
- `thoth ask "hello"` → runs default-mode research (mock provider works without API key)
- `thoth resume <op_id>` → resumes recoverable failure end-to-end
- `thoth --resume <op_id>` → exits 2 with hint pointing to `thoth resume`
- `thoth providers -- --list` → exits 2 with hint pointing to `thoth providers list`
- `thoth modes --json` → exits 2 with hint pointing to `thoth modes list --json`
- `thoth --verbsoe deep_research "x"` → exits 2 with Click "no such option" error (was silently absorbed pre-PR2)
- `thoth config get OPENAI_API_KEY --raw` → behavior matches T34 decision (masking-bypass either documented loud OR rejected without `--show-secrets`)
