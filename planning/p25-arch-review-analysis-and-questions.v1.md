# P25 Arch Review — Pre-execution Analysis, Questions, and (Pending) Proposed Plan

**Scope:** Architectural review (factor-architect lens) of the Variant C plan at
`docs/superpowers/plans/2026-05-12-p25-arch-review-immediate-providers.md`,
checked against actual codebase evidence as of 2026-05-12.

**Posture:** Analysis only. No code, no plan, no PROJECTS.md changes have been made.
A proposed plan will be drafted in the "§5 Proposed Plan" section *after* the
questions in §4 are answered one by one with your context and decisions.

---

## §1 Executive Summary

The earlier Variant C plan was built on a partially-stale mental model. Concretely:

- Roughly **50–60 % of the duplication the plan called out as "warranted extraction
  targets" has already shipped**, via P24 post-ship follow-ups (TS20/T21), P27
  factor-dedup work (`_status.py`), and the P33 parameter-config refactor
  (`parameter_config.py`, 319 LOC).
- A cross-provider contract test (`tests/test_provider_stream_contract.py`)
  **already exists**. The plan's "consider creating one" framing is obsolete.
- P28 (Gemini Background DR) is **actively in-flight on a branch** with spike
  commits. The plan ignored this; in practice it creates merge contention if
  P25 touches any provider files concurrently.
- The plan treated P24 as "blocking P25." Reality: 14 of 16 P24 follow-ups are
  `[x]`; the remaining two (`TS22`/`T25`) are a `--input-file` alias rename with
  **zero overlap** with provider architecture. The blocker is technically real but
  functionally null.

Net: Variant C as written would mostly **re-do work that's already done**. The
review still has value, but its center of gravity has shifted from "extract
duplicates" to **"audit what's been extracted, canonicalize the result, and
decide explicitly what stays divergent."**

---

## §2 Evidence — What Is Already Shared

### 2.1 `src/thoth/providers/_helpers.py` (current)

| Symbol | Role | Used by |
|--------|------|---------|
| `_extract_unsupported_param` | Parse offending param name from BadRequestError body | OpenAI, Perplexity (Gemini opts out — different SDK body shape) |
| `_invalid_key_thotherror` | Brand-correct `ThothError` for upstream-rejected key | All three providers |
| `render_sources_block` | Deduped Markdown sources block from `Citation` iterable | All three providers |
| `debug_print_empty_response` | Verbose empty-response debug ladder | All three providers |

Reference-count in providers: OpenAI=8, Perplexity=11, Gemini=10 call sites
into `_helpers`.

### 2.2 `src/thoth/providers/_status.py`

- `_translate_provider_status(provider_status, status_table, *, unknown_template)`
- Per its own docstring: "the pure-data part of that translation. It does NOT
  touch self.jobs caching, exception handling, or any provider-specific I/O."
- Born from the **P27 factor-dedup spec**. The pattern of "one shared pure
  helper module per behavior family" is repo precedent.

### 2.3 `src/thoth/providers/parameter_config.py` (319 LOC)

- Centralizes parameter-namespace resolution across `[modes.X.openai]`,
  `[modes.X.perplexity]`, `[modes.X.gemini]`, `[providers.NAME]`,
  `[profiles.NAME.providers.NAME]`, etc.
- Shipped via P33 and the P24 follow-up T17 ("Originally punted... successor
  implementation now routes... through `parameter_config.py`").
- This module is the de-facto **shared parameter spine** for all three
  immediate providers.

### 2.4 `src/thoth/providers/base.py` (144 LOC)

- `Citation`, `StreamEvent` dataclasses (shared).
- `ResearchProvider` ABC with default `NotImplementedError` overrides for
  `submit`, `check_status`, `get_result`, `list_models`, `stream`, `cancel`,
  `reconnect`. Concrete default for `list_models_cached`, `is_implemented`,
  `implementation_status`, `supports_progress`.
- **Deliberately thin.** P27 spec explicitly chose "separate `_status.py`
  module rather than appended to `base.py` so the ABC doesn't grow
  lifecycle-specific helpers."

### 2.5 Cross-provider tests already in place

| File | Coverage |
|------|----------|
| `tests/test_provider_stream_contract.py` | Stream event shape across base + Mock |
| `tests/test_provider_helpers.py` | `_helpers.py` symbol contracts |
| `tests/test_provider_parameter_normalization.py` | `parameter_config.py` shared normalizer |
| `tests/test_provider_registry.py` | All three providers register properly |
| `tests/test_immediate_path.py` | `_execute_immediate` driver |
| `tests/test_provider_stream_contract.py` + extended suite | Provider streams (OpenAI in `extended`, real-API in `live_api`) |

### 2.6 What is *still* duplicated

Concrete remaining surface, measured from current files:

| Pattern | OpenAI | Perplexity | Gemini | Verdict |
|---------|--------|------------|--------|---------|
| `async def stream()` body | 91 LOC | 90 LOC | 60 LOC | High structural overlap, divergent inner SDK calls |
| Error mapper (`_map_*_error`) | 1 fn | 2 fns (sync + async) | 1 fn | Different SDK exception hierarchies — true divergence |
| `_map_*_error_async` (Perplexity-only duplication) | — | yes | — | **Intra-provider** duplication; could be DRY'd within Perplexity |
| `Citation(...)` constructor calls | 1 site | 3 sites | 3 sites | Already settled: extraction stays per-provider (P24-T21 verdict) |
| `## Reasoning` side-channel render | ad hoc | — | ad hoc | Not yet canonicalized into helpers |
| Empty-content debug ladder | uses `_helpers` | uses `_helpers` | uses `_helpers` | Done |
| Sources block | uses `_helpers` | uses `_helpers` | uses `_helpers` | Done |
| Background-status translation | uses `_status.py` | uses `_status.py` | n/a (background path in P28) | Done for currently-live background providers |

---

## §3 Findings — Benefits, Risks, Lossy Areas

### 3.1 Benefits of running P25 (more comprehensive than the plan's framing)

1. **Audit + canonicalize, not just extract.** The plan framed P25 as
   "find new duplicates"; reality is "verify what's extracted is structured
   correctly + write down the intentional divergence decisions."
2. **De-risk P29.** If immediate-provider shared surface is named and tested
   clearly, P29 (background DR review) has a template to follow.
3. **Documents intentional divergence.** Without an ADR, the Citation extraction
   decision (per-provider) is a tribal-knowledge fact embedded in P24-T21's
   commit. P25 surfaces it as a first-class architectural claim.
4. **Onboarding cost ↓.** A canonical "shared vs. divergent" map makes adding
   a 4th immediate provider (e.g., Anthropic, xAI) substantially easier.
5. **Test surface consolidation.** Today, contract tests are spread across
   four files. Pulling them under one umbrella (without renaming, just a
   docs index + cross-references) makes coverage gaps visible.
6. **Spec round-trip closure.** P17 round-tripped specs against
   implementation. P25 outputs would similarly close the loop on
   `2026-04-26-p18-immediate-vs-background-design.md` and friends.
7. **Cleans up planning debt.** `planning/p24-providers-root-namespace-investigation.v1.md`
   and `planning/p24-openai-stream-audit.v1.md` are pre-decision notes that
   should now graduate to a single ADR.
8. **Tighten "blast radius" of future PRs.** A clearly-named shared module
   means future provider-feature PRs touch fewer files.

### 3.2 Risks (beyond the plan's risk table)

1. **Premature consolidation across kind boundary.** P25 covers immediate
   only. P29 covers background. Some patterns (status translation, polling)
   already live in `_status.py` — but `_helpers.py` is silently being used
   by both kinds. If P25 tightens the "immediate-only" boundary, P29 may
   need to split helpers further. **Better outcome:** declare an explicit
   "kind-agnostic vs kind-specific" boundary as part of P25's deliverable.
2. **Branch contention with P28.** `p28-gemini-background-deep-research`
   branch has live spike commits. P25 work that touches `gemini.py` or
   `_helpers.py` will conflict-merge with P28. Sequence must address this.
3. **`MockProvider` parity.** Any base/helpers refactor must preserve
   `MockProvider` as a drop-in. The current plan doesn't call this out
   explicitly. Risk: silent mock regressions surface only at test time.
4. **`parameter_config.py` is recent (P33).** Building deduplication
   on top of a module that's still settling adds churn risk. Mitigation:
   defer any change *to* `parameter_config.py` to a separate project.
5. **SDK exception hierarchies diverge.** OpenAI SDK exceptions ≠
   google-genai exceptions. A unified `_map_error` is a **leaky
   abstraction trap** — would need a strategy pattern with provider
   tables. Probably not worth it. The plan implicitly assumed it was.
6. **Perplexity has intra-provider duplication** (`_map_perplexity_error`
   vs `_map_perplexity_error_async`). This is *inside* one file, not
   cross-provider — P25's scope ambiguity. Decide whether intra-provider
   DRY is in scope.
7. **`live_api` test cost.** Cross-provider contract tests that exercise
   all three providers live will multiply API spend during P25. Need an
   explicit budget + per-provider skip semantics.
8. **Async/sync split in Perplexity.** The Perplexity provider's stream
   path uses the OpenAI SDK in async mode, and the submit/check path uses
   it sync. Any consolidation must respect this split — not all "Perplexity
   error mapping" is symmetric.
9. **Code-review burden of a multi-commit migration.** Variant C plans
   for one-commit-per-row migration. With ~3 remaining real extraction
   candidates × 3 providers, that's up to ~9 commits. Reviewer fatigue
   risk. Decide PR shape now.
10. **"Done" criteria are subjective.** The plan's Definition of Done
    is "all checkboxes flipped." Doesn't include a measurable target like
    "no helper called from more than one place via inline duplication."
    Risk: project drifts into perfectionism or closes too early.
11. **Future provider addition pressure.** If Anthropic provider lands
    during P25, it has to choose between "use the new shared shape"
    (forces P25 to converge fast) or "delay until P25 closes" (blocks the
    new provider). Decide upfront.

### 3.3 Where the plan is *lossy* (under-specified, missing, or wrong)

| # | Plan section | What it says | What's lossy / wrong |
|---|--------------|--------------|---------------------|
| L1 | "Items requiring review" | Lists `stream()`, citations, error mapping, side-channels, model-listing as targets | Citations and side-channel **already extracted** for `## Sources` + empty-debug. The list isn't current. |
| L2 | "Define shared abstractions" (T02 in Var B) | "Most likely targets: `_helpers.py` expansion, a new `providers/_immediate.py` mixin" | `_immediate.py` doesn't exist; would have to be created. Plan also doesn't acknowledge `_status.py` precedent that says "separate file per behavior family." |
| L3 | Testing strategy | "Should ship a contract test suite" | Already exists at `tests/test_provider_stream_contract.py`. Plan needs to say *extend*, name the specific assertions to add. |
| L4 | Pre-conditions | "P24 is `[x]`" as blocker | Functionally false — remaining P24 tasks are CLI alias work, not provider arch. The real blocker is **P28 branch state**, not mentioned. |
| L5 | Variant C task list | TS01 → T01 → T02 → ... | Skips an explicit "audit what's already extracted" step before the inventory. Without it, T01 over-counts duplication. |
| L6 | Risk table | 5 rows | Misses: MockProvider parity, parameter_config churn, live-API spend, Perplexity intra-provider duplication, branch contention with P28. |
| L7 | "Out of scope" | "Mock.py — already minimal" | Wrong framing. MockProvider isn't a duplication target, but it **is** a refactor constraint — any base-class change must keep Mock working. |
| L8 | Definition of Done | "All checkboxes flipped" | Not measurable. Need a quantitative target: "no behavior duplicated across ≥2 providers without an ADR justification." |
| L9 | Variant C: P25b sibling | Mentioned, not specified | Doesn't enumerate the deferral criteria. When does a row land in P25 vs P25b? |
| L10 | "Recommended Approach: Variant C" | Borrows P21/P21b/P21c pattern | Pattern was for *feature extensions*, not arch review. The analogy is incomplete — P25 is closer to P17 (spec round-trip) than P21. |
| L11 | "Provider-specific deltas" | Absent | The plan doesn't surface the deltas P24 explicitly documented. `projects/P24-gemini-immediate-sync.md` §"Cross-provider parity matrix" and §"Provider-specific deltas vs unified target surface" exist; P25 should read those first. |
| L12 | ADR location | "Commit `docs/architecture/...`" | `docs/architecture/` doesn't yet exist in the repo. Either create the directory convention as part of P25, or use existing `docs/superpowers/specs/` (which already houses design docs). |
| L13 | Spec round-trip | Not mentioned | P17 set the precedent that arch decisions get annotated back into existing specs. P25 should explicitly own the round-trip. |
| L14 | Reasoning side-channel | Not mentioned beyond "P23 introduced" | P24-T18 wired reasoning-summary kwargs through `OpenAIProvider.stream()`. Cross-provider reasoning rendering is a real lossy gap in the plan. |
| L15 | `_map_*_error` SDK divergence | Implicit | OpenAI/Perplexity share OpenAI SDK exceptions; Gemini uses google-genai. The plan doesn't acknowledge the SDK split, which is the single biggest reason error mapping can't be cleanly unified. |
| L16 | Variant C task numbering | TS01 / T01–T07 | Mixes test/non-test tasks freely. Repo convention (PROJECTS.md): every project has at least one `TS##` before its first `T##`, and TDD applies. The plan's audit/inventory tasks (T01, T02) are analysis — should they have TS pairs, or be marked `**TDD: not applicable**`? |

---

## §4 Questions

Each question states context, lists options, and gives my recommendation.
**Answer one at a time, in order.** I'll fold each answer into the proposed
plan section below before asking the next.

### Q1. Reframe the project's purpose

**Context:** The current Variant C plan treats P25 as "find and extract new
duplicates." Evidence shows ~50–60 % of duplication is already extracted
through opportunistic per-provider follow-ups. The work that remains is
*architectural*, not extraction-driven.

**Options:**
- **(a)** Keep the framing as "find and extract" (matches plan as written).
- **(b)** Reframe as "audit what's extracted + canonicalize divergence
  decisions + close planning debt + write the ADR" — extraction becomes a
  secondary outcome of the audit, not the primary deliverable.
- **(c)** Split: P25 = audit + ADR only; create P25b = "extract anything
  the audit surfaced" as a follow-up project.

**Recommendation:** **(b)**. The codebase has already done the extraction
incrementally; what's missing is the architectural decision record and
the explicit "which divergence is intentional" list. (c) is also fine if
you want guaranteed-small scope, but I think the audit naturally surfaces
1–3 small extractions worth doing in the same project.

---

### Q2. Real blocker — P28 branch contention

**Context:** P28 has an active branch (`p28-gemini-background-deep-research`)
with live spike commits touching Gemini-adjacent code. Any P25 work that
edits `gemini.py` or `_helpers.py` will need to be merge-ordered against
P28.

**Options:**
- **(a)** Run P25 first; merge P28 work onto its result.
- **(b)** Wait until P28 merges to `main`; then run P25.
- **(c)** Run P25 in scope-bounded mode (touch *only* helpers and tests,
  never `gemini.py` itself) so P28 can land in parallel.

**Recommendation:** **(c)** — minimizes merge cost and matches the
"audit + canonicalize" framing. If extraction does need to touch a
provider file, do it after P28 merges.

---

### Q3. Treatment of P24 post-ship `TS22`/`T25` blocker

**Context:** The earlier plan said "P25 doesn't start until P24 is `[x]`."
Remaining P24 tasks are `--input-file` alias work — zero overlap with
provider architecture.

**Options:**
- **(a)** Keep the strict "P24 must be `[x]`" rule.
- **(b)** Relax: P25 may start while P24's last two CLI-alias tasks are
  pending, since they don't intersect provider files.
- **(c)** Promote P24-TS22/T25 to its own micro-project (P24d) so P24
  can close cleanly, and P25 has no nominal blocker.

**Recommendation:** **(b)**. Bureaucratic blocker, no real risk.
(c) is overkill; (a) wastes calendar time.

---

### Q4. Audit step (the missing T0)

**Context:** Plan jumps straight to T01 = "duplication inventory." Without
first auditing what's *already* shared, T01 will over-count and produce a
misleading "still duplicated" list.

**Options:**
- **(a)** Add explicit `P25-T00` (or `P25-T01a`): "Inventory existing
  shared surface (`_helpers.py`, `_status.py`, `parameter_config.py`,
  `base.py`)."
- **(b)** Fold the existing-surface inventory into T01.
- **(c)** Skip it — trust the engineer doing the review to read those
  files first.

**Recommendation:** **(a)**. Makes the audit explicit, produces a
durable artifact (the existing-surface table from §2 of this analysis
becomes the T00 output), and prevents over-counting.

---

### Q5. Treatment of `_map_*_error` cross-SDK divergence

**Context:** OpenAI and Perplexity share OpenAI SDK exception types;
Gemini uses google-genai. Unifying all three is a known
leaky-abstraction trap.

**Options:**
- **(a)** Try to unify — strategy pattern with provider-keyed exception
  tables.
- **(b)** Leave fully divergent; document the SDK split in the ADR.
- **(c)** Half-extract: unify only the OpenAI/Perplexity pair (since
  they share an SDK) into a shared helper; leave Gemini alone.

**Recommendation:** **(b)**. The SDK divergence is real architectural
truth, not a duplication smell. Trying to unify creates a worse
abstraction than three honest mappers. (c) is tempting but the
OpenAI/Perplexity overlap is mostly already factored through
`_extract_unsupported_param` and `_invalid_key_thotherror` — the
remaining divergence is intentional (404 vs 422 status handling,
different rate-limit headers).

---

### Q6. Perplexity intra-provider duplication

**Context:** Perplexity has `_map_perplexity_error` and
`_map_perplexity_error_async` — two functions in one file with high
overlap. This is duplication *within* a provider, not across.

**Options:**
- **(a)** In scope for P25 — fold into the audit.
- **(b)** Out of scope; it's a Perplexity-internal cleanup; spin a
  separate `[?]` idea.
- **(c)** In scope only if it falls out cleanly from the audit; otherwise
  defer.

**Recommendation:** **(c)**. P25's name is "cross-provider"; intra-provider
DRY is a different shape of cleanup. If the audit shows an easy unification
(e.g., shared core + sync/async adapter), include it; otherwise defer to
its own `[?]` ticket.

---

### Q7. Reasoning side-channel rendering

**Context:** P24-T18 wired `reasoning_summary` through
`OpenAIProvider.stream()` and added a built-in `openai_reasoning` mode.
Perplexity may render reasoning differently (its `<think>...</think>`
parser is at `perplexity.py:58`). Gemini wires `Part.thought` events
in stream().

**Options:**
- **(a)** Audit "reasoning rendering" as a first-class row in the
  inventory; potentially extract a `render_reasoning_block()` helper.
- **(b)** Leave each provider's reasoning rendering divergent; document
  why in the ADR.
- **(c)** Include only the *consumer side* (CLI rendering) in scope;
  leave provider-side extraction divergent.

**Recommendation:** **(a)**. If `## Sources` was worth extracting
(via `render_sources_block`), `## Reasoning` likely is too. The three
providers already converged on a single output shape; the renderer
should follow. This is one of the few likely-real new extractions
the audit will surface.

---

### Q8. Deliverable shape — ADR location

**Context:** Plan says "commit `docs/architecture/...`" but that
directory doesn't yet exist. Repo uses `docs/superpowers/specs/` for
design docs and `planning/` for analysis notes.

**Options:**
- **(a)** Create `docs/architecture/` convention; P25 is its inaugural
  document.
- **(b)** Use `docs/superpowers/specs/` and name the ADR like other
  specs (`YYYY-MM-DD-immediate-providers-architecture.md`).
- **(c)** Use `planning/` and version it (`immediate-providers-arch.v1.md`).

**Recommendation:** **(b)**. Matches existing convention, gets
indexed alongside the immediate-vs-background design spec
(`2026-04-26-p18-immediate-vs-background-design.md`), and avoids
introducing a new directory mid-project.

---

### Q9. PR shape and review burden

**Context:** Variant C plans one-commit-per-row migration. If audit
surfaces 1–3 extractions × 3 providers, that's up to 9 commits in one PR.

**Options:**
- **(a)** Single PR with all commits; rely on per-commit review.
- **(b)** Audit + ADR in PR #1; each extraction (if any) in its own PR.
- **(c)** Audit + ADR + small obvious extractions in PR #1; defer larger
  extractions to PR #2/#3 via P25b.

**Recommendation:** **(c)**. Lands the architectural decisions fast
(reviewer can focus on the ADR); subsequent extraction PRs are
mechanically small and reviewable in isolation. Matches the repo's
preferred small-PR cadence.

---

### Q10. Measurable Definition of Done

**Context:** Plan's DoD is "all checkboxes flipped." Not measurable.

**Options:**
- **(a)** Add a quantitative target: "no behavior present in ≥2
  providers via inline duplication, unless the divergence is
  recorded in the ADR with a written rationale."
- **(b)** Add a behavioral target: "the ADR is referenced from each
  provider's module docstring and from `base.py`."
- **(c)** Both (a) and (b).

**Recommendation:** **(c)**. (a) drives the technical decision;
(b) makes the decision discoverable from the code without external
docs. Together they prevent the ADR from rotting.

---

### Q11. Scope of contract test extension

**Context:** `tests/test_provider_stream_contract.py` exists but is
mock-focused. P25 might want to extend it to assert cross-provider
contract claims (event sequencing, citation extraction shapes, etc.).

**Options:**
- **(a)** Extend the existing contract file; add new assertions covering
  every shared helper used by ≥2 providers.
- **(b)** Create a new `tests/test_immediate_providers_contract.py`
  alongside; the existing file stays focused on `StreamEvent` invariants.
- **(c)** No contract-test changes in scope. Audit only.

**Recommendation:** **(a)**. Extend in place. Adding a new file
fractures the contract surface. If the existing file's scope name
("P18 Phase E provider.stream() contract") becomes too narrow, rename
its docstring header — but keep one home for contract tests.

---

### Q12. Treatment of planning-doc debt

**Context:** `planning/p24-providers-root-namespace-investigation.v1.md`
and `planning/p24-openai-stream-audit.v1.md` are pre-decision notes
that P24 superseded but didn't archive.

**Options:**
- **(a)** Out of scope. Leave the planning docs alone.
- **(b)** In scope. Move superseded notes to `archive/` as part of
  P25's ADR landing.
- **(c)** In scope only if the audit references them; archive whatever
  becomes obsolete by the ADR.

**Recommendation:** **(c)**. Minimal-touch but principled. The ADR
becomes the canonical reference; whatever the ADR supersedes gets
archived in the same commit.

---

### Q13. Real-API test budget

**Context:** Cross-provider contract tests that hit real APIs (per
`live_api` marker) multiply spend by 3 every run. P25 doesn't yet
have a budget statement.

**Options:**
- **(a)** Keep all new contract tests mock-only; no `live_api`
  additions.
- **(b)** Add `live_api`-marked tests but gate them behind specific
  per-provider opt-outs and document the per-run spend ceiling
  (~$? per provider per full run).
- **(c)** Add `extended`-marked tests (cassette-backed where possible,
  otherwise mock); no `live_api` additions.

**Recommendation:** **(c)**. The repo's existing pattern: `extended`
runs nightly and is informational; `live_api` runs weekly. P25
shouldn't be the reason `live_api` costs grow. Cassette-backed
extended coverage is enough.

---

### Q14. Successor project shape

**Context:** Variant C creates P25b for deferred items.

**Options:**
- **(a)** Pre-register P25b as `[?]` even if the audit surfaces nothing
  worth deferring.
- **(b)** Only create P25b *if* the audit surfaces ≥1 deferred item.
- **(c)** Don't create a sibling; instead, append a "Deferred" section
  to the ADR and capture each as a separate `[?]` idea later.

**Recommendation:** **(b)**. Don't reserve trunk IDs that may not be
used. If items emerge, register them via `project-add` after the audit.

---

## §5 Proposed Plan (pending answers)

This section is intentionally empty. After Q1–Q14 are answered, this
section will be filled with:

1. Restated project goal (driven by Q1)
2. Pre-conditions & sequencing (driven by Q2, Q3)
3. Task list with TS pairs (driven by Q4, Q5, Q6, Q7, Q11)
4. Deliverable map — ADR location, planning doc archival, contract test
   touchpoints (driven by Q8, Q12)
5. PR sequencing & review plan (driven by Q9)
6. Measurable Definition of Done (driven by Q10)
7. Out of scope statement and explicit deferral mechanism (driven by Q6, Q14)
8. Test/CI budget (driven by Q13)
9. Risk register update (incorporating §3.2 above)
10. Update plan for `docs/superpowers/plans/2026-05-12-p25-arch-review-immediate-providers.md`
    and `projects/P25-arch-review-immediate-providers.md` — *no edits in
    this analysis pass*.

---

## §6 Process Note

This document was produced without modifying:

- `docs/superpowers/plans/2026-05-12-p25-arch-review-immediate-providers.md`
- `projects/P25-arch-review-immediate-providers.md`
- `PROJECTS.md`
- any provider, helper, or test code

The only filesystem change is the creation of *this* file under
`planning/`. That choice matches the repo convention for
pre-decision analysis notes (e.g.,
`planning/p24-providers-root-namespace-investigation.v1.md`,
`planning/p24-openai-stream-audit.v1.md`).
