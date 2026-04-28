# P18 — Immediate vs Background: Execution Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task.
>
> **Reevaluated 2026-04-27** — see end of doc for codebase delta + revised file map.

**Goal:** Promote the immediate-vs-background distinction to a first-class, declared `kind` field on every mode; raise a typed runtime error on mismatches; split execution into a streaming immediate path and a renamed background path; add provider streaming + cancel; rename `mini_research → quick_research`; ship `thoth cancel`; add an extended-only real-API test suite; wire the dead-code `--kind` filter on `thoth modes`.

**Spec:** `docs/superpowers/specs/2026-04-26-p18-immediate-vs-background-design.md` (architecture, decisions, rollout, testing strategy, risks, reevaluation log §11)

**Authoritative task list:** `PROJECTS.md` § "Project P18: Immediate vs Background — Explicit `kind`, Runtime Mismatch, Path Split, Streaming, Cancel (v3.1.0)" — phases A–J, each task carries a `[P18-Tnn]` / `[P18-TSnn]` ID. **Update task checkboxes there as work lands; do not duplicate the list in this plan.**

**Tech stack:** Python 3.11+, Click 8.x, pytest, `respx`/`vcr` cassettes, existing `isolated_thoth_home` test fixture, `./thoth_test` integration runner.

**Target version:** **v3.1.0** (additive minor on the v3 line; release-please will tag v3.0.0 from the queued `feat!` in #24 first; P18 lands after that). The `kind`-required-on-user-modes **hard error** is deferred to a future **P19 / v4.0.0**.

**Predecessor projects:**
- P11 (`thoth modes` discovery — established the rendering vocabulary; v2.11.0)
- P13 (`is_background_model` substring rule — P18 replaces it as a resolution path; v2.11.1)
- P14 (`should_show_spinner` shipped — gates spinner on `is_background_model`; v2.13.0)
- P16 PR1+PR2+PR3 (Click-native CLI + `thoth ask`/`resume` + `--json` everywhere + `completion/sources.py:79 mode_kind` dead code; landed in `f8b62f2`, awaiting v3.0.0 release tag)

---

## TDD discipline (per `CLAUDE.md`)

For every phase below: **write the test first, watch it fail, then make it pass.** Use the inner-loop commands documented in `CLAUDE.md` § "Fast Iteration Loop" — do **not** run the full pre-commit gate between edits. Run the gate once at end-of-phase.

Inner-loop pattern for this project:
- New unit test: `uv run pytest tests/test_<file>.py::<test> -x -v`
- Whole new test file: `uv run pytest tests/test_<file>.py -v`
- Lint/type only: `just check`
- Full gate before commit: pre-commit hook handles it; do not pre-run unless debugging

---

## Phase ordering and dependencies

```
A (schema)  ────────────────►  B (mismatch error)  ──┐
   │                                                  │
   └──►  C (path split)  ──►  D (rename)  ──►  E (stream + sinks)
                                                      │
                                                      ▼
F (cancel research)  ──►  G (cancel impl + subcommand)
                                                      │
H (warn-once user modes)  ◄─────────────────── independent
                                                      │
I (extended test infra)  ◄──── needs A's KNOWN_MODELS
                                                      │
J (cleanup + docs)  ◄────────── runs after C lands and stabilizes
```

**Cheapest first PR:** Phase A only — adds `kind` to builtins, derives `KNOWN_MODELS`, ships consistency tests. Zero behavior change. ~6 files touched. **Recommended starting point.**

**Critical-path PRs (in order):**
1. Phase A
2. Phase B (depends on A's `kind` field)
3. Phase C (depends on A's `mode_kind` resolver)
4. Phases D, H, I (independent; can interleave with C/E/G)
5. Phase E (depends on C's `_execute_immediate`)
6. Phase F (research only; no code)
7. Phase G (depends on F's findings)
8. Phase J (cleanup; runs last)

**Backstop tests on every PR:**
- Existing `tests/test_*.py` continues to pass unchanged
- `./thoth_test -r` continues to pass (integration suite)
- `just check` green (ruff + ty)

---

## File creation/modification map (verified against `main` 2026-04-27)

See spec §5.2 for the full table with line references. Quick index by phase:

| Phase | Creates | Modifies |
|---|---|---|
| A | `tests/test_builtin_modes_have_kind.py`, `tests/test_known_models_registry.py` | `config.py` (add `kind` to all 12 builtins, add `mode_kind()`), `models.py` (`KNOWN_MODELS`, `derive_known_models()`, `ModelSpec`) |
| B | `tests/test_mode_kind_mismatch.py` | `errors.py` (`ModeKindMismatchError`), `providers/__init__.py:107-112` (thread `kind` through), `providers/openai.py` (add `_validate_kind_for_model`) |
| C | `tests/test_immediate_path.py`, `tests/test_background_path.py` | `run.py:550` (rename `_execute_research` → `_execute_background`, add `execute()` + `_execute_immediate`), `run.py:629,654,691,692` (gate `thoth resume`/`thoth status` hints on background kind), `run.py:199,311` (gate `Operation ID` echo on background or persist), `progress.py:16-36` (extend `should_show_spinner` to suppress Progress bar too for immediate runs), `interactive_picker.py:35,44` (migrate to `mode_kind`), `commands.py`, `signals.py`, `help.py` |
| D | `tests/test_mode_aliases.py`, `tests/test_modes_kind_filter.py` | `config.py` (alias resolution + `DeprecationWarning`), `cli_subcommands/modes.py` (add `--kind` option, wire `completion/sources.py:79 mode_kind` completer), `cli_subcommands/_options.py:91` (update `--pick-model` help) |
| E | `src/thoth/sinks.py` (`MultiSink`), `tests/test_provider_stream_contract.py`, `tests/test_output_sinks.py` | `providers/base.py` (`StreamEvent`, `stream()`), `providers/openai.py` (impl `stream` via `responses.stream`), `providers/mock.py` (impl deterministic chunks), `cli_subcommands/_options.py:_RESEARCH_OPTIONS` (add `--out`, `--append`), `cli_subcommands/_option_policy.py` (register options), `cli_subcommands/ask.py` (thread `--out`/`--append` into `_run_research_default`), `run.py:_execute_immediate` (call `stream()`, sink chunks) |
| F | `planning/p18-cancel-research.md` | (none — research only) |
| G | `src/thoth/cli_subcommands/cancel.py`, `tests/test_provider_cancel.py`, `tests/test_cancel_subcommand.py` | `providers/base.py` (`cancel()`), `providers/openai.py` (impl `responses.cancel`), `providers/mock.py`, `commands.py` (`cancel_operation()`), `signals.py` (Ctrl-C → cancel best-effort), `cli.py` (`cli.add_command(cancel)`) |
| H | `tests/test_user_mode_kind_warning.py` | `config.py:367 _validate_config` (warn-once on user-mode missing `kind`) |
| I | `tests/extended/test_model_kind_runtime.py`, `.github/workflows/extended.yml` | `pyproject.toml` (NEW `[tool.pytest.ini_options]` section: `markers`, `addopts`), `justfile` (`test-extended` recipe), `thoth_test` (`--extended` flag, category column) |
| J | (none) | `providers/openai.py:232-233` (delete non-background shortcut in `check_status`), `README.md`, `manual_testing_instructions.md`, CHANGELOG via release-please |

**Call-site migration matrix for `is_background_*` (Phase A end + scattered):**

| File:line | Current | Post-P18 | Phase |
|---|---|---|---|
| `config.py:146` (`is_background_mode`) | def | thin wrapper over `mode_kind`, kept for compat | A |
| `config.py:136` (`is_background_model`) | def | unchanged — model-level helper for `_validate_kind_for_model` and `should_show_spinner` | A (no change) |
| `interactive_picker.py:35,44` | `is_background_model(model)` filter | `mode_kind(mode_cfg) == "immediate"` | C |
| `cli.py:284` | `_thoth_config.is_background_model(model_name)` | `mode_kind(mode_cfg) == "background"` | C |
| `progress.py:33` (`should_show_spinner`) | `is_background_model(model)` | unchanged — model-level helper | C (extend gate, don't migrate) |
| `modes_cmd.py:51` (`_derive_kind`) | `is_background_mode(cfg)` | read `cfg["kind"]`; fall back to `mode_kind` | A |
| `providers/openai.py:176,183` | `is_background_model(self.model)` | unchanged — model-level helper inside provider | A (no change) |
| `providers/__init__.py:111` (`create_provider`) | `is_background_mode(provider_config)` | `mode_kind(provider_config) == "background"` | B |
| `cli_subcommands/ask.py:176` | `is_background_mode(mode_config)` | `mode_kind(mode_config) == "background"` | C |

---

## Phase A starter — first concrete tasks

Worker can begin with these three steps; the rest of Phase A is enumerated as `[P18-T01..T03]` + `[P18-TS01..TS03]` in `PROJECTS.md`.

### Step A.1 — write `tests/test_builtin_modes_have_kind.py`

```python
"""Every builtin mode must declare an explicit `kind`. Substring sniffing is
deprecated; this test prevents regressions where a new builtin lands without
the field."""
from __future__ import annotations
import pytest
from thoth.config import BUILTIN_MODES

VALID_KINDS = {"immediate", "background"}

@pytest.mark.parametrize("name,cfg", sorted(BUILTIN_MODES.items()))
def test_builtin_declares_kind(name: str, cfg: dict) -> None:
    assert "kind" in cfg, f"Builtin mode '{name}' missing required 'kind' field"
    assert cfg["kind"] in VALID_KINDS, (
        f"Builtin mode '{name}' has kind={cfg['kind']!r}; "
        f"must be one of {sorted(VALID_KINDS)}"
    )
```

Run: `uv run pytest tests/test_builtin_modes_have_kind.py -v` → all 12 fail (expected).

### Step A.2 — add `kind` to all 12 entries in `BUILTIN_MODES`

`config.py:42-133`. Mapping (derived from current model assignments + brainstorm decisions):

| Mode | Model | `kind` |
|---|---|---|
| `default` | `o3` | `immediate` |
| `clarification` | `o3` | `immediate` |
| `thinking` | `o3` | `immediate` |
| `mini_research` | `o4-mini-deep-research` | `background` |
| `quick_research` *(new alias target — see Step D.1)* | `o4-mini-deep-research` | `background` |
| `exploration` | `o3-deep-research` | `background` |
| `deep_dive` | `o3-deep-research` | `background` |
| `tutorial` | `o3-deep-research` | `background` |
| `solution` | `o3-deep-research` | `background` |
| `prd` | `o3-deep-research` | `background` |
| `tdd` | `o3-deep-research` | `background` |
| `deep_research` | `o3-deep-research` | `background` |
| `comparison` | `o3-deep-research` | `background` |

Run: `uv run pytest tests/test_builtin_modes_have_kind.py -v` → all 13 pass.

### Step A.3 — write `tests/test_known_models_registry.py` and `derive_known_models()`

```python
# tests/test_known_models_registry.py
def test_derive_known_models_returns_unique_specs():
    specs = derive_known_models()
    keys = {(s.provider, s.id) for s in specs}
    assert len(keys) == len(specs), "duplicate (provider, model) pairs"

def test_every_builtin_appears():
    specs = derive_known_models()
    triples = {(s.provider, s.id, s.kind) for s in specs}
    for name, cfg in BUILTIN_MODES.items():
        assert (cfg["provider"], cfg["model"], cfg["kind"]) in triples

def test_cross_mode_kind_conflict_raises():
    """Simulate by injecting a conflicting BUILTIN_MODES entry; restore after."""
    ...
```

Implement `derive_known_models()` per spec §5.2 / §4 Q2.

---

## Per-phase commit cadence

One commit per phase letter is reasonable for review. Commit message format per CLAUDE.md "Conventional Commits enforced":

| Phase | Suggested message |
|---|---|
| A | `feat(modes): add explicit kind field on every builtin and derive KNOWN_MODELS` |
| B | `feat(providers): raise ModeKindMismatchError when declared kind contradicts model` |
| C | `feat(run): split execution into immediate and background paths; suppress resume hints for immediate` |
| D | `feat(modes): rename mini_research to quick_research with deprecation alias` |
| E | `feat(stream): add provider.stream() and --out/--append output sinks for immediate mode` |
| F | `docs: research cancel support across openai, perplexity, gemini` |
| G | `feat(providers): add provider.cancel() and 'thoth cancel' subcommand` |
| H | `feat(config): warn when user-defined mode is missing kind` |
| I | `test(extended): add real-API model kind contract suite gated by pytest -m extended` |
| J | `chore: remove non-background shortcut in OpenAIProvider.check_status; document immediate vs background` |

Each commit is independently revertable.

---

## End-of-project checklist

Before declaring P18 complete:

- [ ] All `[P18-TSnn]` tests in `PROJECTS.md` pass on default suite
- [ ] All `[P18-Tnn]` tasks in `PROJECTS.md` are checked off
- [ ] `make env-check` passes
- [ ] `just check` passes (ruff + ty)
- [ ] `./thoth_test -r --skip-interactive -q` passes (integration)
- [ ] `uv run pytest -m extended` passes when `OPENAI_API_KEY` is set (extended)
- [ ] `README.md` and `manual_testing_instructions.md` reflect the new surface
- [ ] CHANGELOG entries land with `feat:` / `chore:` prefixes (release-please picks up MINOR bump → v3.1.0)
- [ ] `planning/p18-cancel-research.md` exists with one section per provider
- [ ] Spec `docs/superpowers/specs/2026-04-26-p18-immediate-vs-background-design.md` Status field updated from "Draft" → "Shipped" with the v3.1.0 release commit linked
- [ ] PROJECTS.md P18 status flipped from `[ ]` to `[x]`
- [ ] All 9 `is_background_*` call sites audited per spec §10 acceptance gate; resolution-path callers migrated to `mode_kind`
- [ ] Dead-code `mode_kind` completer in `completion/sources.py:79` is **wired** (not still dead)
- [ ] `should_show_spinner` extended so immediate runs see neither spinner nor Progress bar
- [ ] Cross-reference note in P16 spec already exists (`docs/superpowers/specs/2026-04-25-promote-admin-commands-design.md` `**Related:**` section); confirm still accurate post-P18

---

## Reevaluation log

### 2026-04-27 — Plan reevaluation against post-P16-PR3 codebase

**What changed in the codebase since plan was drafted (2026-04-26):**

- Commit `f8b62f2` shipped P16 PR2 + PR3 to `main`: `cli_subcommands/` directory, `_research_options` shared decorator, `thoth ask`/`thoth resume` subcommands, `--json` everywhere, `completion/sources.py`, `progress.py:should_show_spinner`. `feat!` queues v3.0.0 from release-please.
- `completion/sources.py:79 mode_kind` was added as **dead code with the explicit comment** *"Per spec §6.4: `mode_kind` is committed as dead code (~5 LOC) for P18 forward-compat — P18 will wire `--kind` later."* — PR3 author left a hook for us.
- `interactive_picker.py:44` and `_research_options:91` already use the "immediate models only" concept informally via `is_background_model`. The migration is straightforward.
- `thoth ask --json` already implements **Option E** (background → submit envelope; immediate → snapshot from checkpoint) at `ask.py:158-231`. The kind-aware split exists for the JSON path; P18 brings the same split to the human-readable path *and* adds streaming.

**What this means for the plan:**

1. **Target version**: v2.16.0 → **v3.1.0**. release-please tags v3.0.0 first from the queued `feat!`.
2. **Phase A grows slightly**: also migrate `interactive_picker.py:44` and `modes_cmd.py:_derive_kind` to use the new resolver.
3. **Phase C grows slightly**: also extend `should_show_spinner` to suppress Progress bar for immediate runs (it already suppresses spinner; Progress is the remaining noise).
4. **Phase D grows slightly**: wire `--kind` filter on `thoth modes` using the dead-code `mode_kind` completer in `completion/sources.py:79`.
5. **Phase E placement**: `--out`/`--append` flags go in **`cli_subcommands/_options.py:_RESEARCH_OPTIONS`**, not `cli.py`. Both top-level CLI and `thoth ask` inherit them via the existing decorator stack.
6. **Phase G placement**: `cli_subcommands/cancel.py` mirrors the `cli_subcommands/resume.py` pattern that's already shipped.

**What did NOT change:** Phase ordering, TDD discipline, Phase A starter (still the cheapest first PR), commit cadence, every test scaffold. The architecture from spec §5 is unchanged.

**Recommended worker action on resumption**: re-run the inner-loop sanity (`uv run pytest tests/test_builtin_modes_have_kind.py -v` if it exists) to confirm baseline; if the file doesn't exist yet, start with **Phase A Step A.1** as written in the original plan. That step is unchanged and independent of the codebase delta.
