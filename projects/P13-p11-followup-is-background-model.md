# P13 — P11 Follow-up — is_background_model overload + shared secrets + regression tests (v2.11.1)

**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)

**Status:** `[x]` Completed (v2.11.1).

**Goal**: Close the six non-blocking items carried over from P11 review before new feature work (P12) builds on them. Purely follow-up: one clarifying helper, two test-coverage gaps, one prose fix, one shared-module extraction, one regression test that would have caught a silent pre-P11 bug.

**Out of Scope**
- New user-facing features (that's P12)
- Refactoring `is_background_mode` itself — we add an adjunct, not a replacement
- Extending masking rules (same `api_key` suffix contract)

### Design Notes
- **Helper shape**: keep `is_background_mode(mode_config)` as the dict-shaped contract. Add `is_background_model(model: str | None) -> bool` as the string-shaped primitive. `is_background_mode` delegates to `is_background_model` after the `async` short-circuit — one derivation rule, two ergonomic entry points.
- **Call-site updates**: the two `openai.py` callsites (which synthesize `{"model": self.model}` today) switch to `is_background_model(self.model)`. The `providers/__init__.py` callsite keeps `is_background_mode(provider_config)` because it passes a real config dict that could carry `async`.
- **Shared secrets module**: extract `_mask_secret`, `_is_secret_key`, `_mask_tree` to `src/thoth/_secrets.py` (leading underscore — internal). Both `config_cmd.py` and `modes_cmd.py` import from there. If P12 ships first and does the extraction, this task becomes a no-op; if P13 ships first, P12-T05 drops.
- **Regression test**: `thoth config list --json` was broken before P11 (click ate `--json`). P11's `ignore_unknown_options=True` fix repaired it incidentally but there's no subprocess test guarding it. Add one.
- **Docstring prose**: `src/thoth/providers/__init__.py` lines 6 and 79 still say "deep-research background mode" as if it were a code mechanism — update to name `is_background_mode` so a reader scanning the header finds the actual implementation.

### Tests & Tasks
- [x] [P13-TS01] Tests for `is_background_model(model)`: `None`, empty string, `"o3"`, `"o3-deep-research"`, `"o4-mini-deep-research"`, case-sensitivity (`"o3-Deep-Research"` → False), non-bool `async` values via `is_background_mode` (`{"async": 1}` → True, `{"async": "yes"}` → True) — closes P11 review Minor gaps M2/M3
- [x] [P13-T01] Added `is_background_model(model: str | None) -> bool` in `src/thoth/config.py`; `is_background_mode` now delegates (commit `89498ef`)
- [x] [P13-T02] Switched `providers/openai.py:175,182` from `is_background_mode({"model": self.model})` to `is_background_model(self.model)` — synthetic-dict abstraction leak gone (commit `dfb86b9`)
- [x] [P13-TS02] Unit tests for `create_provider("openai", ...)` asserting `provider_config["background"]=True` on deep-research and `False` on plain `o3` (commit `12a43e9`)
- [x] [P13-T03] Docstrings in `src/thoth/providers/__init__.py` (lines 6, 79) now reference `is_background_mode` by name (commit `01b9d11`)
- [x] [P13-TS03] 13 tests in `tests/test_secrets.py` verify `_mask_secret`, `_is_secret_key`, `_mask_tree` semantics (last-4 retention, `${VAR}` passthrough, dotted-path suffix, list + dict recursion)
- [x] [P13-T04] Created `src/thoth/_secrets.py`; `config_cmd.py` and `modes_cmd.py` now import shared helpers. Duplicates deleted. `config_cmd.py` uses `from thoth._secrets import _mask_tree as _mask_in_tree` alias to preserve call-site names (commit `5d2cee2`)
- [x] [P13-TS04] Subprocess regression test `test_thoth_config_list_json_subprocess` in `tests/test_config_cmd.py` (commit `9813a59`); also repaired the `thoth` uv-script metadata (`tomlkit>=0.13`) that was blocking the test
- [x] [P13-TS05] Regression: `just check` clean, 200 pytest passed / 1 skipped, `./thoth_test -r --skip-interactive` 63 passed / 1 skipped / 0 failed
- [x] [P13-T05] See note in P12 below — P12-T05 is obsoleted by P13-T04
- [x] Regression Test Status — all green

### Automated Verification
- `just check` passes (ruff + ty)
- `uv run pytest tests/` passes (169 → ~175 with new tests)
- `./thoth_test -r` passes
- `grep -rn '"deep-research"' src/thoth/providers/` returns zero code-logic matches (same as post-P11 baseline)
- `grep -n "_mask_secret\|_is_secret_key\|_mask_tree" src/thoth/config_cmd.py src/thoth/modes_cmd.py` shows only imports from `_secrets`, no duplicate definitions

### Manual Verification
- `./thoth config list --json | jq keys` produces valid JSON (was broken before P11, not currently test-guarded)
- `./thoth modes --json` still masks `api_key` in any `[modes.*]` table after the secrets extraction
