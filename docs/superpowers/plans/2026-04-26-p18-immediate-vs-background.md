# P18 — Immediate vs Background: Execution Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** Promote the immediate-vs-background distinction to a first-class, declared `kind` field on every mode; raise a typed runtime error on mismatches; split execution into a streaming immediate path and a renamed background path; add provider streaming + cancel; rename `mini_research → quick_research`; ship `thoth cancel`; add an extended-only real-API test suite.

**Spec:** `docs/superpowers/specs/2026-04-26-p18-immediate-vs-background-design.md` (architecture, decisions, rollout, testing strategy, risks)

**Authoritative task list:** `PROJECTS.md` § "Project P18: Immediate vs Background — Explicit `kind`, Runtime Mismatch, Path Split, Streaming, Cancel (v2.16.0)" — phases A–J, 37 tasks + 22 test specs, each with a `[Pxx-Tnn]` / `[Pxx-TSnn]` ID. **Update task checkboxes there as work lands; do not duplicate the list in this plan.**

**Tech stack:** Python 3.11+, Click 8.x, pytest, `respx`/`vcr` cassettes, existing `isolated_thoth_home` test fixture, `./thoth_test` integration runner.

**Target version:** v2.16.0 (additive minor; the `kind`-required-on-user-modes hard error is deferred to a future P19 / v3.0.0).

**Predecessor projects:** P11 (`thoth modes` discovery — established the rendering vocabulary), P13 (`is_background_model` substring rule — P18 replaces it as a resolution path).
**Related concurrent project:** P16 PR2 (`thoth ask` subcommand — no merge-order coupling; see spec §8.1).

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

## File creation/modification map

See spec §5.2 for the full table. Quick index by phase:

| Phase | Creates | Modifies |
|---|---|---|
| A | `tests/test_builtin_modes_have_kind.py`, `tests/test_known_models_registry.py` | `config.py`, `models.py` |
| B | `tests/test_mode_kind_mismatch.py` | `errors.py`, `providers/__init__.py`, `providers/openai.py` |
| C | `tests/test_immediate_path.py`, `tests/test_background_path.py` | `run.py`, `commands.py`, `signals.py`, `help.py` |
| D | `tests/test_mode_aliases.py` | `config.py` |
| E | `src/thoth/sinks.py`, `tests/test_provider_stream_contract.py`, `tests/test_output_sinks.py` | `providers/base.py`, `providers/openai.py`, `providers/mock.py`, `cli.py`, `run.py` |
| F | `planning/p18-cancel-research.md` | (none — research only) |
| G | `src/thoth/cli_subcommands/cancel.py`, `tests/test_provider_cancel.py`, `tests/test_cancel_subcommand.py` | `providers/base.py`, `providers/openai.py`, `providers/mock.py`, `commands.py`, `signals.py`, `cli.py` |
| H | `tests/test_user_mode_kind_warning.py` | `config.py` |
| I | `tests/extended/test_model_kind_runtime.py`, `.github/workflows/extended.yml` | `pyproject.toml`, `justfile`, `thoth_test` |
| J | (none) | `providers/openai.py` (delete shortcut), `README.md`, `manual_testing_instructions.md`, `CHANGELOG.md` (auto via release-please) |

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

- [ ] All 22 `[P18-TSnn]` tests in `PROJECTS.md` pass on default suite
- [ ] All 37 `[P18-Tnn]` tasks in `PROJECTS.md` are checked off
- [ ] `make env-check` passes
- [ ] `just check` passes (ruff + ty)
- [ ] `./thoth_test -r --skip-interactive -q` passes (integration)
- [ ] `uv run pytest -m extended` passes when `OPENAI_API_KEY` is set (extended)
- [ ] `README.md` and `manual_testing_instructions.md` reflect the new surface
- [ ] CHANGELOG entries land with `feat:` / `chore:` prefixes (release-please picks up MINOR bump)
- [ ] `planning/p18-cancel-research.md` exists with one section per provider
- [ ] Spec `docs/superpowers/specs/2026-04-26-p18-immediate-vs-background-design.md` Status field updated from "Draft" → "Shipped" with the v2.16.0 release commit linked
- [ ] PROJECTS.md P18 status flipped from `[ ]` to `[x]`
- [ ] Cross-reference note added to P16 PR2 spec (see spec §8.1) noting that streaming arrives via P18
