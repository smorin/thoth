# Design — Immediate vs Background: Explicit `kind`, Runtime Mismatch, Path Split, Streaming, Cancel (P18)

**Status:** Draft (drafted from session brainstorm 2026-04-25 → 2026-04-26)
**Created:** 2026-04-26
**Project ID:** P18
**Target version:** v2.16.0 (MINOR — fully additive; warn-only for the user-mode `kind`-required transition)
**Tracking:** `PROJECTS.md` § "Project P18" — canonical task list lives there
**Predecessors:**
- **P11** (`thoth modes` Discovery, v2.11.0) — established `Kind = Literal["immediate", "background"]` at the rendering layer (`modes_cmd.py:22`). P18 promotes that vocabulary to a *declared* data field on every mode.
- **P13** (P11 follow-up, v2.11.1) — introduced `is_background_model` / `is_background_mode` substring rules (`config.py:136-155`). P18 deprecates these as the *resolution* path; they survive only inside the runtime mismatch check as the source of truth for "what does this provider require for this model?"
- **P17** (Spec Round-Trip, in flight) — annotates `is_background_mode` as a shipped §4 helper. P17 itself is doc-only and unchanged by this spec; an additive note ("further evolved by P18") may be added once P18 lands.

**Related (concurrent or downstream):**
- **P16 PR2** (`v3.0.0`, `docs/superpowers/specs/2026-04-25-promote-admin-commands-design.md`) — introduces `thoth ask PROMPT` as a Click subcommand. P18's path split happens *inside* the existing dispatch and applies regardless of how the run was invoked: `thoth ask "..." --mode <immediate-mode>` post-PR2 will automatically stream once P18 lands. **No merge-order coupling**; either project can land first.
- **P12** (CLI Mode Editing — `thoth modes set/add`) — once P18 ships, mode-editing commands must surface `kind` as a required field for new user modes. P12 should be drafted with awareness of the P18 contract.
- **Future P19 (v3.0.0 follow-up)** — converts the user-mode `kind` warning to a hard error; drops `mini_research` deprecation alias; drops the `async: bool` legacy override. Lands alongside P16 PR2's other v3.0.0 breakages.

---

## 1. Goal

Make immediate-vs-background a first-class declared property of every research mode. Surface mode/model mismatches at the moment of `submit()` (not config-load) via a typed `ModeKindMismatchError` raised by the provider. Split `_execute_research` into a streaming `_execute_immediate` path and a renamed `_execute_background` path. Add `provider.stream()` and `provider.cancel()` contracts to the base. Ship `thoth cancel <op-id>` and `--out` / `--append` flags. Land an extended-only test suite that exercises every known model against the real API to detect kind drift.

## 2. Motivation

1. **The kind/model relationship is undeclared.** `is_background_model(model)` (`config.py:143`) substring-matches `"deep-research"` to decide whether a job submits as a background async response. There is no audit trail when a builtin's model and intended kind disagree, no contract for user-defined modes, and no way to detect "you've configured `o3-deep-research` for synchronous use" until OpenAI returns a confusing error mid-run.
2. **Immediate UX is noisy.** Synchronous calls (`default`, `thinking`, `clarification` on `o3`) flow through the same `Progress(...)` bar, polling loop, and operation-ID echo as background ops. The polling loop runs exactly one tick before exiting (`providers/openai.py:232-233` shortcut returns `completed` immediately). Failure on an immediate run prints `Resume with: thoth resume <op-id>` — a dead end, since immediate runs have no upstream job to reattach to.
3. **There is no streaming.** Even though OpenAI's Responses API supports `stream=True` for non-deep-research models, immediate runs block on a full `responses.create(...)` round-trip and emit the entire result at the end. The "fast" feel promised by mode descriptions is undermined.
4. **Cancellation is not first-class.** Ctrl-C out of a deep-research run leaves the upstream job running (and billing). The polling loop has a `cancelled` status branch (`run.py:445-456`) but no provider-level `cancel()` to invoke.
5. **Naming overloads invite confusion.** `mini_research` is described as "Fast, lightweight" but uses `o4-mini-deep-research` (background-only). `thinking` is the truly synchronous one. The mismatch is invisible from `thoth modes list` until you correlate `Kind` against the description text by eye.

## 3. Out of scope

- Renaming the `thinking` mode. The session brainstorm initially proposed `thinking → ask`, but P16 PR2 takes `ask` as a subcommand. Rationale: once `kind` is the declared data field, the mode name no longer has to communicate execution model — `thinking` survives unchanged.
- `--out` flag for **background** mode runs. Background already has `--project` and combined-report mechanics; bolting `--out` on is a separate conversation.
- Removing the `is_background_model` substring rule entirely. It survives as the source of truth for "what does *this provider* require for *this model*?" — used inside the runtime mismatch check. Only its role as a *resolution* path is replaced.
- Erroring on user-defined modes missing `kind`. P18 emits a one-time **warning** at config load. The error form is deferred to **P19 / v3.0.0**.
- Reasoning-summary streaming UX. Currently prepended as `## Reasoning Summary` at the end. A future `--show-reasoning` flag is the right home; not P18.
- Implementing Perplexity / Gemini providers. They remain `NotImplementedError`; their `cancel()` and `stream()` impls land when the providers do. P18 only adds the **research items** documenting whether each upstream API supports cancellation.
- A new `thoth ask` subcommand. That is P16 PR2's responsibility; P18's `_execute_immediate` is a behavior layer that PR2's `ask` will benefit from automatically.

## 4. Decisions locked during brainstorming

| # | Question | Decision |
|---|---|---|
| Q1 | Where does mismatch validation live — config-load or runtime? | **Runtime, in `provider.submit()`.** The provider is the only layer that knows its model taxonomy. Config-load doesn't hold provider knowledge and shouldn't grow it. |
| Q2 | How is the model registry maintained — separate `KNOWN_MODELS` constant, or derived? | **Derived from `BUILTIN_MODES`** at module import time. Single source of truth; cross-mode kind conflicts (same `(provider, model)` declared with two different kinds across modes) raise at import. |
| Q3 | Are user-defined modes required to declare `kind`? | **Required**, but enforced as **warn-once in v2.16.0**, **error in v3.0.0** (deferred to P19 alongside P16 PR2 breakages). Substring fallback survives in the warning path only. |
| Q4 | Rename `thinking` mode? | **No.** `ask` is taken by P16 PR2; once `kind` is explicit, the mode name no longer carries execution-model semantics. Keeping `thinking` avoids a needless deprecation. |
| Q5 | Rename `mini_research`? | **Yes — `quick_research`**, with deprecation alias kept in `BUILTIN_MODES`. The `mini` prefix conflated "small model" with "fast UX"; `quick_research` describes the depth tier without overpromising synchronicity. |
| Q6 | `kind` vocabulary — `immediate/background`, `fast/slow`, `sync/async`? | **`immediate` ↔ `background`.** Already used in `modes_cmd.py:22` as the rendered "Kind" column header. "Fast" overpromises (a deep-research run can be fast on a small prompt). "Sync/async" collides with Python's `asyncio` vocabulary. |
| Q7 | Streaming protocol shape | **`async def stream(...) -> AsyncIterator[StreamEvent]`** on `ResearchProvider`. `StreamEvent` is a small dataclass with `kind: Literal["text","reasoning","citation","done"]` + `text: str`. Allows future inline reasoning / citation rendering without recontracting. |
| Q8 | Output sink composition | **`MultiSink`** that fans `write(chunk)` to a list of `IO[str]`. CLI surface: `--out` (repeatable, accepts `-` for stdout, comma-separated values also accepted) + `--append` for non-truncating writes. |
| Q9 | Cancel: implement uniformly, or research first? | **Research first per provider.** Three explicit research tasks (T18/T19/T20 in PROJECTS.md). OpenAI almost certainly supports `responses.cancel`; Perplexity/Gemini TBD. Providers without upstream cancel raise `NotImplementedError`; the `thoth cancel` CLI catches and reports "upstream cancel not supported, local checkpoint marked cancelled". |
| Q10 | Extended test gating | **`pytest -m extended`** + `addopts = "-m 'not extended'"` in default config. Mirror in `./thoth_test --extended` and `just test-extended`. Nightly CI gate (new workflow, gated on repo secret). Never on PR CI. |
| Q11 | What does "extended" assert per model? | **First-poll behavior.** Immediate models must return `completed` on first `check_status`; background models must return `running`/`queued`/`completed` (allow `completed` for fast jobs). Cancel after confirming background submission to limit cost. |
| Q12 | Where does the `kind` field on builtins come from at v2.16.0 boundary? | **All 12 builtins gain explicit `kind`** (`default`, `clarification`, `mini_research`, `exploration`, `deep_dive`, `tutorial`, `solution`, `prd`, `tdd`, `thinking`, `deep_research`, `comparison`). No silent inference for any builtin. |

**Follow-up clarifications (logged for traceability):**
- The runtime mismatch check uses `is_background_model(model)` substring matching to determine *required* kind. Substring sniffing is preserved here intentionally — it's the only place the heuristic correctly maps to "OpenAI's API enforcement boundary." If OpenAI ever ships a non-deep-research model that requires background submission, this is where the rule needs updating.
- The reverse mismatch (declared `background`, model is non-deep-research) is **legal**: OpenAI lets you force-background any model via the `background=True` request param. P18 does not error on this combination.
- Mock provider gets `stream()` and `cancel()` implementations alongside the contracts; without them, the test suite cannot exercise the new paths hermetically.

## 5. Architecture

### 5.1 The shape

The execution dispatch becomes:

```python
# src/thoth/run.py
async def execute(operation, mode_config, ...):
    match mode_kind(mode_config):
        case "immediate":
            return await _execute_immediate(...)
        case "background":
            return await _execute_background(...)  # renamed from _execute_research
```

`mode_kind(cfg)` is the new canonical resolver in `config.py`. Precedence: explicit `kind` → legacy `async: bool` (deprecation warning) → substring sniff on model name (warn-once for user modes, internal error for builtins missing `kind`).

The provider contract grows two optional methods:

```python
# src/thoth/providers/base.py
class ResearchProvider:
    # existing ...
    async def stream(self, prompt, mode, system_prompt, verbose) -> AsyncIterator[StreamEvent]:
        raise NotImplementedError(f"{type(self).__name__} does not support streaming")
    async def cancel(self, job_id: str) -> dict[str, Any]:
        raise NotImplementedError(f"{type(self).__name__} does not support cancel")
```

### 5.2 File layout

| File | State | Responsibility |
|---|---|---|
| `src/thoth/config.py` | Modified | Add `kind` to all 12 `BUILTIN_MODES` entries; add `mode_kind(cfg)`; thin `is_background_mode` wrapper kept; warn-once on user modes missing `kind` in `_validate_config` |
| `src/thoth/models.py` | Modified | Add `ModelSpec` NamedTuple + `derive_known_models()` + `KNOWN_MODELS` module constant. Cross-mode kind conflict raises at import. |
| `src/thoth/errors.py` | Modified | Add `ModeKindMismatchError(ThothError)` carrying `mode_name`/`model`/`declared_kind`/`required_kind` |
| `src/thoth/providers/base.py` | Modified | Add `StreamEvent` dataclass; add `stream()` and `cancel()` raising `NotImplementedError` |
| `src/thoth/providers/__init__.py` | Modified | Thread `mode_config["kind"]` into `provider_config["kind"]` in `create_provider` (`__init__.py:107`) |
| `src/thoth/providers/openai.py` | Modified | Add `_validate_kind_for_model(mode)` (called first in `submit()`); implement `stream()` via `client.responses.stream`; implement `cancel()` via `client.responses.cancel`; remove the `if not background: return completed` shortcut in `check_status` (Phase J cleanup) |
| `src/thoth/providers/mock.py` | Modified | Implement `stream()` (deterministic chunks) and `cancel()` (pop from internal jobs dict, mark cancelled) |
| `src/thoth/providers/perplexity.py` | Modified | Optional: implement `cancel()` *only if* Phase F research confirms upstream support; otherwise leave base `NotImplementedError` |
| `src/thoth/run.py` | Modified | Rename `_execute_research` → `_execute_background`; add top-level `execute()` dispatcher; add `_execute_immediate` (no `Progress`, no polling, streams to `MultiSink`); gate every `thoth resume {id}` / `thoth status {id}` hint on `mode_kind == "background"` |
| `src/thoth/sinks.py` | NEW | `MultiSink` class — fans `write(chunk)` to a list of `IO[str]` handles, lazy file open, ordered close in `finally` |
| `src/thoth/cli_subcommands/cancel.py` | NEW | `@click.command("cancel")` + `OP_ID` positional, delegates to `cancel_operation()` |
| `src/thoth/commands.py` | Modified | Add `cancel_operation(op_id, ctx)`; gate `thoth resume` hints on background kind |
| `src/thoth/signals.py` | Modified | Ctrl-C path calls `cancel_operation` best-effort with 5s timeout before exit |
| `src/thoth/cli.py` | Modified | Add `--out PATH` (repeatable, accepts `-`, comma-list accepted) and `--append` flags to research-running paths; `cli.add_command(cancel)` registration |
| `tests/test_*.py` | NEW | 11 new test files covering builtin schema, registry, mismatch, immediate path, background regression, mode aliases, streaming, sinks, cancel, cancel subcommand, user-mode kind warning |
| `tests/extended/test_model_kind_runtime.py` | NEW | Parametrized over `KNOWN_MODELS`, gated on `@pytest.mark.extended`; hits real API |
| `pyproject.toml` | Modified | Register `extended` marker; `addopts = "-m 'not extended'"`; new `[tool.pytest.ini_options].markers` entry |
| `justfile` | Modified | Add `test-extended` recipe |
| `thoth_test` | Modified | Add `--extended` flag and category column |
| `.github/workflows/extended.yml` | NEW | Nightly cron, gated on `OPENAI_API_KEY` repo secret; informational, not gating |
| `planning/p18-cancel-research.md` | NEW | Findings from Phase F research items (one section per provider) |
| `README.md` | Modified | Document `--out` flag; document `kind` field for user-defined modes; document `thoth cancel`; document the immediate-vs-background contract briefly |
| `manual_testing_instructions.md` | Modified | Streaming, cancel, mismatch, alias scenarios |

### 5.3 What gets added

- **Data model**: `kind` field on every builtin mode; `KNOWN_MODELS` derived registry; `ModelSpec` NamedTuple; `StreamEvent` dataclass.
- **Resolver**: `mode_kind(cfg)` (replaces `is_background_mode` as the canonical resolution path; `is_background_mode` survives as a thin wrapper, and `is_background_model` survives inside the runtime mismatch check only).
- **Errors**: `ModeKindMismatchError` (typed, carries enough metadata for a config-edit suggestion).
- **Provider contracts**: `stream()`, `cancel()` (both with `NotImplementedError` defaults).
- **Execution paths**: `_execute_immediate` (streaming, no progress bar, no resume hints, sinks to `MultiSink`); top-level `execute()` dispatcher.
- **CLI surface**: `--out PATH` (repeatable, `-` for stdout, comma-list); `--append`; `thoth cancel <op-id>` subcommand.
- **Mode aliases**: `mini_research → quick_research` (alias kept).
- **Test infrastructure**: `extended` pytest marker; `tests/extended/` directory; `just test-extended`; `./thoth_test --extended`; nightly CI workflow.

### 5.4 What gets renamed / deprecated

- `_execute_research` → `_execute_background` (internal symbol; no public API).
- `mini_research` → `quick_research` (mode name; alias retained as `{"_deprecated_alias_for": "quick_research"}` stub; `get_mode_config` resolves through it with a one-time `DeprecationWarning`).
- `is_background_mode` → wrapper around `mode_kind(cfg)`. Keep for compat. Deprecation comment, not warning. Removal targets v3.0.0.
- `async: bool` field in mode configs → still honored, but emits a `DeprecationWarning` at resolve time. Removal targets v3.0.0.

### 5.5 What gets removed (Phase J cleanup)

- `if not job_info.get("background", False): return {"status": "completed", "progress": 1.0}` shortcut in `OpenAIProvider.check_status` (`providers/openai.py:232-233`). Becomes unreachable once immediate runs no longer flow through the polling loop. Verify no tests depend on the shortcut path; delete.

### 5.6 The runtime mismatch check

```python
# src/thoth/providers/openai.py
def _validate_kind_for_model(self, mode: str) -> None:
    declared = self.config.get("kind")          # threaded from mode_config
    requires_background = is_background_model(self.model)
    if declared == "immediate" and requires_background:
        raise ModeKindMismatchError(
            mode_name=mode,
            model=self.model,
            declared_kind="immediate",
            required_kind="background",
        )
```

Called as the first line of `OpenAIProvider.submit()` — **before** any HTTP work. The reverse case (declared `background`, model regular) is legal (force-background) and not checked.

### 5.7 Dispatch flow for an immediate run (post-P18)

```
thoth ask "what is X" --mode thinking --out -
  → cli dispatch
  → operation created, mode_config resolved (kind="immediate")
  → execute(...) matches "immediate"
  → _execute_immediate:
       provider = create_provider(...)  # threads kind into provider config
       sink = MultiSink([sys.stdout])
       async for event in provider.stream(prompt, mode, system_prompt):
           if event.kind == "text":
               sink.write(event.text)
       sink.close()
  → no Progress, no checkpoint write (unless --project), no operation ID printed
  → exit 0
```

For a misconfigured immediate run (`thinking` overridden to `o3-deep-research` via `--model`):

```
  → execute(...) matches "immediate"
  → _execute_immediate:
       provider.stream(...) → first calls _validate_kind_for_model("thinking")
       → raises ModeKindMismatchError before any HTTP traffic
  → CLI formats: "Mode 'thinking' is declared as kind='immediate', but model
     'o3-deep-research' requires kind='background'. Update [modes.thinking] in
     your config..."
  → exit 1
```

## 6. Rollout

Phases A–J (10 phases). Authoritative task list in `PROJECTS.md` § "Project P18". High-level shape:

| Phase | What ships | Breaking? |
|---|---|---|
| A | `kind` field on builtins, `KNOWN_MODELS` derivation, cheap consistency tests | No |
| B | `ModeKindMismatchError` + provider runtime check | No (additive — pre-existing valid configs unaffected) |
| C | Path split + hint suppression | No (output changes, but no behavior contract change) |
| D | `mini_research → quick_research` rename + deprecation alias | No |
| E | Streaming + `MultiSink` + `--out` / `--append` | No |
| F | Cancel research per provider (OpenAI, Perplexity, Gemini) | No (research only) |
| G | Cancel impls + `thoth cancel <op-id>` | No |
| H | User-mode `kind` warn-once | No |
| I | Extended test infra (marker, nightly workflow) | No |
| J | Cleanup (`check_status` shortcut removal) + docs + CHANGELOG | No |

Each phase is independently shippable. Phase A is the cheapest first PR.

## 7. Testing strategy

### 7.1 Default suite (hermetic)

| Test file | Phase | What it covers |
|---|---|---|
| `tests/test_builtin_modes_have_kind.py` | A | Every builtin declares `kind ∈ {immediate, background}` |
| `tests/test_known_models_registry.py` | A | `derive_known_models()` returns one entry per unique `(provider, model)`; cross-mode kind conflicts raise; every builtin's triple appears |
| `tests/test_mode_kind_mismatch.py` | B | `OpenAIProvider.submit(...)` with mismatched kind raises `ModeKindMismatchError` *before* any HTTP call (asserted via `respx`/cassette absence) |
| `tests/test_immediate_path.py` | C | Immediate run produces no `Progress`, no operation-ID echo (unless `--project` set), no resume hint |
| `tests/test_background_path.py` | C | Existing behavior unchanged (regression gate) |
| `tests/test_mode_aliases.py` | D | `--mode mini_research` resolves through alias with `DeprecationWarning` |
| `tests/test_provider_stream_contract.py` | E | Mock + OpenAI (cassette) `stream()` yields chunks; aggregated equals non-streaming result |
| `tests/test_output_sinks.py` | E | `--out -`, `--out FILE`, `--out -,FILE`, `--append`; lazy file open |
| `tests/test_provider_cancel.py` | G | Mock cancel; OpenAI cancel (cassette); `NotImplementedError` for unsupported providers |
| `tests/test_cancel_subcommand.py` | G | `thoth cancel <op-id>` updates checkpoint, calls `provider.cancel`, exits 0; missing op exits 6 |
| `tests/test_user_mode_kind_warning.py` | H | User TOML missing `kind` triggers one-time warning at config load |

### 7.2 Extended suite (real API)

`tests/extended/test_model_kind_runtime.py` — parametrized over `KNOWN_MODELS`, asserts:

- `kind == "immediate"` → `check_status(submit())` returns `{"status": "completed", ...}` on first poll (no API delay between submit and result)
- `kind == "background"` → `check_status(submit())` returns `{"status": ∈ {"running", "queued", "completed"}, ...}` on first poll; if not completed, call `provider.cancel()` to abort

Gated: `addopts = "-m 'not extended'"` in default config; run via `pytest -m extended` / `just test-extended` / `./thoth_test --extended`. Nightly CI workflow.

### 7.3 Integration (`thoth_test`)

The existing `thoth_test` integration runner is already exhaustive for background-mode flows. P18 adds:

- A `category` column distinguishing `default` from `extended` cases
- A handful of new test cases covering: streaming output to stdout, streaming to file, tee, mismatch error message format, cancel subcommand happy path, alias deprecation warning

## 8. Cross-project coordination

### 8.1 P16 PR2 — `thoth ask` subcommand (v3.0.0)

PR2 introduces `thoth ask PROMPT` as the canonical scripted research entrypoint, inheriting the full research flag set (`--mode`, `--async`, `--auto`, `--input-file`, `--pick-model`, etc.). P18's path split happens at the dispatch layer below `ask`:

- `thoth ask "..."` (default mode → immediate kind) post-P18 → `_execute_immediate` → streams to stdout
- `thoth ask "..." --mode deep_research` → `_execute_background` → today's polling loop
- `thoth ask "..." --mode thinking --out answer.md` → `_execute_immediate` → streams to file

**Merge-order independence:** P18 can land before, after, or alongside PR2. If P18 lands first, the streaming benefit is realized through the existing `--mode` / `-q` paths until PR2's `ask` subcommand goes live, at which point users get the same streaming through the new verb at no extra cost. If PR2 lands first, `thoth ask` initially emits with today's progress-bar UX; P18 then upgrades it to streaming. **Recommended action**: add a one-line cross-reference to the P16 PR2 spec noting that immediate-mode streaming arrives via P18.

### 8.2 P12 — `thoth modes set/add/unset`

P12 adds CLI surface for editing user modes. After P18, the editing UX must:

- Surface `kind` as a required field for new modes (interactive prompt or `--kind` flag)
- Validate `kind ∈ {"immediate", "background"}` at write time
- Warn if `kind` and model name appear inconsistent (forwards-compat with the v3.0.0 hard-error transition)

P12 can absorb these requirements into its existing scope; no separate cross-project task needed.

### 8.3 P17 — Spec round-trip annotation

P17 is doc-only and unchanged by P18. After P18 lands, P17's spec annotation may add a forward-pointing note to the §4 row covering `is_background_mode`: *"P18 deprecated this helper as a resolution path; survives as a thin wrapper over `mode_kind`."* Optional, not load-bearing.

### 8.4 P19 (future) — v3.0.0 breakages

A separate PROJECTS.md entry will be drafted to land alongside P16 PR2 in v3.0.0. P19 closes out the deprecations P18 starts:

- User modes missing `kind` → **error** at config load (was: warn-once)
- `mini_research` alias → **removed** (was: alias-with-warning)
- `async: bool` field in modes → **removed** (was: warning)
- `is_background_mode` thin wrapper → **removed** (was: kept for compat)

P19 is referenced from P18's PROJECTS.md goal block but not drafted yet. Trigger: P18 lands and stabilizes for one minor.

## 9. Risks and open items

### 9.1 Risks

- **OpenAI streaming compatibility surface** — `client.responses.stream(...)` works for the models we care about, but the event types may have edge cases (reasoning summaries mid-stream, citations as annotations on output_text deltas) that we discover during Phase E. Mitigation: cassette-based tests for the known happy path; fallback to non-streaming `responses.create` if `stream()` raises an unexpected event type. Track as a Phase E follow-up if found.
- **Cassette drift on streaming responses** — VCR cassettes may not faithfully replay streaming events, depending on how the recorder handles SSE/chunked transfer. Mitigation: investigate cassette format support during Phase E test scaffolding; if streaming cassettes are unreliable, test OpenAI streaming via the **extended** suite only and rely on Mock for hermetic coverage.
- **Cancel race conditions** — `thoth cancel` issued just as a background job transitions to `completed` upstream may produce inconsistent local state. Mitigation: re-poll status immediately after `cancel()` returns; treat post-cancel `completed` as success (job finished before the cancel landed).
- **Substring rule fragility surfacing in mismatch check** — the runtime mismatch check still uses `is_background_model(model)`. If OpenAI ships a non-deep-research model that requires background submission, the check goes silent on it. Mitigation: extended test suite catches this — it would observe the kind contract violation against the real API and fail. Documented in Q12 follow-up.

### 9.2 Open items

None blocking. The session brainstorm closed all design questions; remaining items are research tasks (T18/T19/T20) intentionally scoped into Phase F so findings can shape Phase G impl.

## 10. Acceptance criteria for v2.16.0

- Every builtin mode has a `kind` field; `KNOWN_MODELS` is derived (no separate registry)
- A misconfigured mode (immediate kind + deep-research model) fails at provider `submit()` with `ModeKindMismatchError` *before* any API call
- Immediate runs do not emit polling progress, operation IDs (unless persisted), or resume hints
- `--out` supports stdout, file, tee, and append for immediate runs
- `provider.cancel()` exists on the base; OpenAI + Mock implement it; Perplexity/Gemini status reflects research findings
- `thoth cancel <op-id>` cancels in-flight background ops upstream and updates the checkpoint
- Extended test suite parametrizes over `KNOWN_MODELS` and runs only under the `extended` marker
- All deprecation warnings surface (`mini_research`, `async: bool`, missing user-mode `kind`) without erroring; default test suite green
- Documentation updated (`README.md`, `manual_testing_instructions.md`) to reflect immediate vs background, streaming, and cancel surfaces
