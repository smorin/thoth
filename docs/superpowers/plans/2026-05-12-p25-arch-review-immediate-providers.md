# P25 — Architecture Review & Cleanup (Immediate Providers) — Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan. Steps use `- [ ]` checkbox syntax for tracking.

**Goal:** Conduct a cross-provider architecture review across the three immediate-call providers (`openai.py`, `perplexity.py`, `gemini.py`) once all three are in place, and act on the findings — either by extracting shared abstractions or by documenting why divergence should stay.

**Status when planned:** P25 is `[ ]` Scoped; **blocked on P24** (`[~]` In progress — main contract shipped, 7 follow-up tasks tracked).

**Tech stack:** Python 3.11+, existing `ResearchProvider` ABC in `src/thoth/providers/base.py`, pytest, `ty`, `ruff`.

**References**
- Trunk: [PROJECTS.md](../../../PROJECTS.md)
- Project file: [`projects/P25-arch-review-immediate-providers.md`](../../../projects/P25-arch-review-immediate-providers.md)
- Immediate providers (subject of review):
  - `src/thoth/providers/openai.py` (~829 lines)
  - `src/thoth/providers/perplexity.py` (~1015 lines)
  - `src/thoth/providers/gemini.py` (~576 lines)
- Base contract: `src/thoth/providers/base.py` (~144 lines)
- Predecessor projects: P22 (OpenAI sync), P23 (Perplexity sync), P24 (Gemini sync — in progress)
- Successor: P29 (background DR arch review)

---

## Pre-conditions (must be true before starting)

- [ ] P24 is `[x]`, including the 7 reviewer-flagged follow-ups (TS17–TS21 + T18–T24).
- [ ] All three immediate providers pass `live_api` and `extended` markers.
- [ ] `is_implemented() → True` for OpenAI, Perplexity, Gemini.

If P24 isn't done, **do not start P25**. Surface the blocker and pick a different project.

---

## Plan Variants

### Variant A — Quick MVP (decision-only, 1–2 days)

**Shape:** Land a single Markdown ADR documenting findings + the *decision to do nothing*, or to schedule a follow-up project (P25b).

**Tasks**

| ID | Task | Depends on | Description |
|----|------|-----------|-------------|
| P25-TS01 | Define review criteria | — | Decide what counts as "duplication worth removing": ≥40 lines of near-identical logic across ≥2 providers, or a base-class shaped hook present in 2/3 with one diverging. Codify as a one-page rubric in the ADR draft. |
| P25-T01 | Duplication inventory | TS01 | Diff the three `stream()` bodies, error mappers, citation extractors, side-channel renderers. Produce a Markdown table: each row = a behavior, columns = OpenAI / Perplexity / Gemini, cells = "same" / "varies on X" / "absent". No code changes. |
| P25-T02 | Feasibility verdict | T01 | For each row in the inventory, classify: (a) shared abstraction warranted, (b) leave divergent (intentional), (c) borderline. Write the verdict and rationale in the ADR. |
| P25-T03 | Ship ADR | T02 | Commit `docs/architecture/2026-MM-DD-immediate-providers-review.md`. If (a) rows exist, file successor project P25b; if not, document why. |

**Trade-offs:** Fastest path to closing P25. Defers any actual cleanup. Risk: ADR rots if no successor project is created.

---

### Variant B — Comprehensive (decision + full extraction, 1–2 weeks)

**Shape:** Decision + ship an extraction PR that consolidates everything classified as "warranted".

**Tasks**

| ID | Task | Depends on | Description |
|----|------|-----------|-------------|
| P25-TS01 | Define review criteria | — | Same rubric as Variant A. |
| P25-TS02 | Regression-test snapshot | TS01 | Capture current behavior with a frozen test set: full `live_api` + `extended` + `pytest` runs, save reports as `.thoth_test_cache/p25-baseline.json` and a tagged git ref. Any post-extraction divergence vs. this baseline is a regression. |
| P25-T01 | Duplication inventory | TS01 | Same as Variant A. |
| P25-T02 | Design shared abstractions | T01 | For every "warranted" row: design the extraction. Most likely targets: `_helpers.py` expansion, a new `providers/_immediate.py` mixin or strategy module, error-mapper consolidation in `errors.py`. Document the API in the ADR. |
| P25-T03 | TDD: write tests against new shared API | T02 | Add `tests/test_immediate_providers_shared.py` exercising the proposed shared module(s) — these must fail until extraction lands. |
| P25-T04 | Extract & migrate OpenAI | T03 | First migration. Pick OpenAI as the canonical reference because it shipped first and is the most-exercised path. Keep its observable behavior identical (regression baseline holds). |
| P25-T05 | Migrate Perplexity | T04 | Apply the shared module. Resolve any drift surfaced during migration with an explicit decision (extend the abstraction or carve out a provider-specific override). |
| P25-T06 | Migrate Gemini | T05 | Final migration. Confirm all three providers now use the shared surface. |
| P25-T07 | ADR + project files | T06 | Document outcome. Update each provider file's `**References**` block to point at the shared module. |
| P25-T08 | Full-gate verification | T07 | `make env-check` → `just check` → `./thoth_test -r` → `just test-lint` → `just test-typecheck` → `just test-extended` → `just test-live-api` against the P25-TS02 baseline. |

**Trade-offs:** Highest payoff (lasting maintainability win), but biggest blast radius. Risk: extraction surfaces hidden behavioral differences mid-migration, expanding scope.

---

### Variant C — Balanced (decision + targeted extraction, 3–5 days) ★ recommended

**Shape:** Decision document plus *targeted* extraction of only the unambiguous duplicates. Anything borderline → P25b.

**Tasks**

| ID | Task | Depends on | Description |
|----|------|-----------|-------------|
| P25-TS01 | Define review criteria | — | Same rubric. |
| P25-TS02 | Baseline test snapshot | TS01 | Run `./thoth_test -r --skip-interactive -q` + `pytest -q` + (if API keys available) `just test-extended-{openai,perplexity,gemini}` and store reports. Acts as regression oracle. |
| P25-T01 | Duplication inventory | TS01 | Markdown table; same as A/B. |
| P25-T02 | Triage: extract-now vs. defer | T01 | For each "warranted" row, score effort × risk. Move only **low-effort, low-risk** items into this project; borderline / high-risk items go to a new `[?]` P25b. |
| P25-T03 | TDD: tests for in-scope extractions | T02 | Failing tests against the new shared surface. |
| P25-T04 | Extract in-scope items | T03 | One commit per extraction (per row). Each commit must keep `./thoth_test -r` green vs. the TS02 baseline. |
| P25-T05 | Migrate all three providers row-by-row | T04 | One commit per `(row × provider)`, smallest reversible units. |
| P25-T06 | ADR + create P25b if needed | T05 | Document extracted vs. deferred, rationale for each, and seed `projects/P25b-...-.md` as `[?]` for deferred items. |
| P25-T07 | Full-gate verification | T06 | `make env-check` → `just check` → `./thoth_test -r` → `just test-lint` → `just test-typecheck`. Periodic full-gate per `CLAUDE.md` (every 2–3 commits during T04/T05). |

**Trade-offs:** Real cleanup without committing to a possibly-painful all-or-nothing migration. Borderline calls deferred rather than litigated under deadline pressure.

---

## Recommended Approach: Variant C

**Why:** Architecture reviews fail in two modes — *paper tigers* (Variant A: write doc, change nothing, rot) and *yak-shaves* (Variant B: try to consolidate everything, surface every legacy decision, blow out scope). Variant C ships the unambiguous wins, captures the rest as a follow-up project where the next round of evidence (P29 background DR review) might change the answer, and keeps each commit small enough to bisect.

It also matches this repo's prior practice: P21 / P21b / P21c was the same "extract what's clear, defer what's not, sequence as separate projects" pattern.

---

## Architecture & Design

### Items Requiring Review (likely candidates surfaced by T01)

- **`stream()` event normalization** — currently each provider builds `StreamEvent` instances inline. Likely a shared event-builder helper.
- **Citation extraction** — `Citation` dataclass is shared but population logic is per-provider. Candidate for `_helpers.py` functions or a strategy method on the base class.
- **Error mapping** — OpenAI/Perplexity each map SDK exceptions to `APIRateLimitError` / `APIQuotaError` / `APIAuthenticationError`. Gemini (P24) likely added its own. Consolidation target.
- **Side-channel rendering** — `## Reasoning` / `## Sources` blocks. P23 introduced; P24 reuses; OpenAI may diverge.
- **Model-listing + caching** — base already exposes `list_models_cached()`; check if providers duplicate any of that pattern.

### Clean code patterns

- **Strategy / Template Method on `ResearchProvider`** — push more concrete behavior into the base if 2/3 providers can share it without sacrificing readability.
- **Pure helper module (`providers/_helpers.py`)** — already exists; expand it for stateless logic (event builders, citation munging) rather than growing the ABC surface.
- **No premature abstraction** — per repo CLAUDE.md ("three similar lines is better than a premature abstraction"). Anything < ~40 lines stays duplicated.

### Items needing explicit decision (call out in ADR)

- Should the immediate-providers review hold to a contract test suite (`tests/test_immediate_providers_contract.py`) that runs against all three? Strong "yes" if Variant B; optional under Variant C.
- Should the shared module also constrain the (separate) background DR providers, or stay scoped to immediate? Strong "no" — wait for P29 to give that decision its own evidence.

---

## Testing Strategy

### Regression oracle

- **P25-TS02 baseline** — captured before any code changes. `./thoth_test -r --skip-interactive -q`, `pytest -q`, optionally `just test-extended-*` per provider. Any post-extraction divergence is a regression unless explicitly justified in the ADR.

### Unit tests (Variant B & C)

- `tests/test_immediate_providers_shared.py` — exercises the new shared surface (event builder, citation munger, error mapper) directly.
- Each migrated provider keeps its existing unit tests; they must continue to pass *without modification* in C. If they require changes in B, that's a sign the extraction changed observable behavior.

### Integration tests

- `./thoth_test -r --provider openai|perplexity|gemini` per provider (`live_api` marker).
- Cross-provider parity matrix (already exercised by P24's tests under the `extended` marker).

### Verification Checklist (Variant C)

- [ ] Pre-conditions met (P24 `[x]`)
- [ ] `P25-TS01` rubric committed
- [ ] `P25-TS02` baseline stored in `.thoth_test_cache/p25-baseline.json` (or referenced commit SHA)
- [ ] `P25-T01` duplication inventory committed (Markdown table)
- [ ] `P25-T02` triage table committed with extract-now vs. defer columns
- [ ] `P25-T03` failing tests committed
- [ ] `P25-T04` + `T05` each commit green vs. baseline
- [ ] ADR landed under `docs/architecture/`
- [ ] P25b (if needed) added to trunk as `[?]` via `project-add`
- [ ] Final `pre-commit` hook gate passes on the last commit before `git push`

---

## Task Dependencies & Ordering (Variant C)

```
TS01 ──┬─► T01 ──► T02 ──► T03 ──► T04 ──► T05 ──► T06 ──► T07
       │
       └─► TS02
```

`TS01` and `TS02` can run in parallel after the rubric draft starts.
`T04` → `T05` is a serial chain by design — one extraction per commit, one provider migration per commit, to keep blast radius small.

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Extraction surfaces *hidden* behavioral differences | TS02 baseline + one-commit-per-migration → bisect to the offending commit cheaply. |
| Scope creep into background DR providers | Out of scope — explicitly. Background review is P29. |
| ADR rots | Variant C ships *code changes alongside the ADR*; the code itself becomes the durable record. P25b captures anything deferred so it doesn't get lost. |
| Long-lived branch during T04/T05 | Use periodic full-gate runs (per `CLAUDE.md` discipline) — full lefthook gate every 2–3 commits, immediately after any wide-blast-radius commit. |
| Borderline duplication litigated under deadline | Defer to P25b; do not negotiate borderline calls inside this project. |

---

## Out of Scope

- Background-DR providers (P29 owns that review).
- New provider features.
- Spec / PRD changes (this is a structural refactor, not a behavioral one).
- Touching `mock.py` (already minimal; not part of the duplication surface).
