# P18 — `is_background_*` call-site audit

**Generated:** 2026-04-27 during Phase A of P18 implementation.
**Tracked:** `PROJECTS.md` § P18-T03c.
**Spec reference:** `docs/superpowers/specs/2026-04-26-p18-immediate-vs-background-design.md` §10 acceptance gate.

## Purpose

P18 introduces `mode_kind(cfg)` as the canonical resolver for a mode's
execution kind. The two pre-existing helpers split into distinct roles:

| Helper | Role after P18 |
|---|---|
| `mode_kind(mode_config)` | **NEW.** Canonical resolution path. Reads declared `kind`; falls back through `async` (deprecated) and `is_background_model(model)` (substring) for legacy/user modes. |
| `is_background_mode(mode_config)` | Thin wrapper over `mode_kind(...) == "background"`. Kept for compat. **Removed in v4.0.0.** |
| `is_background_model(model)` | **Unchanged.** Model-level helper for "what does this provider require for this model?". Used inside the runtime mismatch check and `should_show_spinner`. **Stays in v4.0.0.** |

This document enumerates every existing call site, classifies each, and
records the disposition for the Phase A → C migration.

## Call-site inventory (post-Phase A)

`grep -rn "is_background_mode\|is_background_model" src/thoth/` on `feat/p18-immediate-vs-background` after Phase A:

| # | Call site | Helper used | Today | Disposition | Phase |
|---|---|---|---|---|---|
| 1 | `config.py:136` | `is_background_model` def | model-level helper | **Unchanged.** Used inside runtime mismatch check + spinner gate. | (no change) |
| 2 | `config.py:189` | `mode_kind` def *(NEW in Phase A)* | n/a | **Added.** Canonical resolver. | A (done) |
| 3 | `config.py:218` | `is_background_mode` def | mode-level wrapper | **Becomes thin wrapper over `mode_kind`.** Done in Phase A. | A (done) |
| 4 | `interactive_picker.py:35,44` | `is_background_model(model)` | filters `--pick-model` candidates ("immediate models only") | **Migrate to `mode_kind(mode_cfg) == "immediate"`** if mode_cfg in scope; else stay as model-level helper if only `model` is available. | C |
| 5 | `cli.py:284` | `is_background_model(model_name)` | gates a CLI behavior on the resolved model | **Migrate to `mode_kind(mode_cfg) == "background"`** if mode_cfg in scope at this call site; else keep as model-level helper. | C |
| 6 | `progress.py:33` | `is_background_model(model)` | spinner gate | **Unchanged at the helper level.** Phase C extends `should_show_spinner` to **also** suppress the Progress bar for immediate runs (gate becomes mode-aware via a new `mode_cfg` parameter). | C |
| 7 | `modes_cmd.py:51` | (was) `is_background_mode(cfg)` | derives display kind for `thoth modes` table | **Migrated to read `cfg["kind"]` first, fall back via `mode_kind`.** Done in Phase A. | A (done) |
| 8 | `providers/openai.py:176` | `is_background_model(self.model)` | branches submission tools (`web_search_preview`, `code_interpreter`) on whether model is deep-research | **Unchanged.** Model-level helper — provider's internal taxonomy. | (no change) |
| 9 | `providers/openai.py:183` | `is_background_model(self.model)` | sets `use_background` request param | **Unchanged.** Same reason as #8. Could optionally read `self.config.get("kind") == "background"` after Phase B threads kind through; not load-bearing for this PR. | (no change) |
| 10 | `providers/__init__.py:111` (`create_provider`) | `is_background_mode(provider_config)` | sets `provider_config["background"] = True` for openai when mode is background | **Migrate to `mode_kind(provider_config) == "background"`** so the resolution is explicit and uses the declared `kind` first. | B |
| 11 | `cli_subcommands/ask.py:171,176` | `is_background_mode(mode_config)` | Option E `--json` envelope decision: background → submit envelope; immediate → snapshot from checkpoint | **Migrate to `mode_kind(mode_config) == "background"`**. Behavior unchanged. | C |

## Migration policy

- **Resolution-path callers** (those holding a `mode_config` and asking "is this mode background?") **migrate to `mode_kind(cfg)`** so they pick up the explicit `kind` field first.
- **Model-level callers** (those holding only a `model` string, not a `mode_config`) **keep `is_background_model(model)`**. The substring rule is correct as the API-enforcement boundary inside the runtime mismatch check (Phase B) and the spinner gate (Phase C).
- **No new substring-only resolution** introduced anywhere. All new code uses `mode_kind(cfg)`.

## Phase B / C migration target

Post-Phases B + C, `grep -rnE 'is_background_(mode|model)' src/thoth/` should return only:
- `config.py` (the two defs + the thin `is_background_mode` wrapper)
- `progress.py:33` (model-level spinner gate; unchanged)
- `providers/openai.py:176, 183` (model-level provider taxonomy; unchanged)
- The new runtime mismatch check inside `OpenAIProvider._validate_kind_for_model` (Phase B)

That's the v3.1.0 acceptance gate per spec §10.

## v4.0.0 (future P19) follow-up

- Drop `is_background_mode(cfg)` thin wrapper. Callers migrate to `mode_kind(cfg) == "background"`.
- Drop `async: bool` legacy field. `mode_kind` removes the deprecation branch.
- Required-kind error for user modes (was: warn-once in Phase H).

The model-level `is_background_model(model)` helper survives — it remains the
correct heuristic for "this OpenAI model requires background submission".
