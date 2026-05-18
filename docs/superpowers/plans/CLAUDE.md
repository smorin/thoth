# Plan-writing conventions

Plans live at `docs/superpowers/plans/YYYY-MM-DD-<feature>.md`. Created
via `superpowers:writing-plans`, executed via `superpowers:executing-plans`
or `superpowers:subagent-driven-development`.

## Required header

Every plan opens with this banner so executor agents pick the right
sub-skill:

```markdown
# <Feature> Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** [one sentence]
**Architecture:** [2-3 sentences]
**Tech Stack:** [...]
**Spec:** projects/P<NN>-<slug>.md
```

## Cross-reference tasks by stable NAME, not by number

When the plan grows by inserting tasks (spike-driven corrections,
quality-review fixes), task numbers shift. References like
`"Implemented in Task 5"` become wrong.

```markdown
# BAD — breaks on renumber
"...as confirmed in Task 5..."

# GOOD — stable across renumbers
"...as confirmed in the `_deep_research_submit` task..."
"...see the cancel-spike task..."
```

If you must use numbers (e.g. in stub `NotImplementedError` messages),
keep them in ONE place (the stub) and update them deliberately during
renumber. Don't sprinkle the number across multiple bullet points
in the plan body.

## Renumbering with care

If a plan needs renumbering (e.g. inserting a new Task 2):

```bash
perl -pi -e 's/\bTask (\d+)\b/$1>=2 && $1<=25 ? "Task " . ($1+1) : "Task $1"/ge' plan.md
```

The `\b` word boundaries and the conditional range prevent collisions
(e.g. "Task 25" → "Task 26" before "Task 2" → "Task 3"). After
renumbering, verify cross-refs in:

- Section headers (`### Task N:`)
- Body prose ("filled in by Task N")
- Code blocks (especially stub NotImplementedError messages)
- Commit-message templates inside the plan
- File-structure tables (e.g. "created in Task N")

## Spike-driven corrections

When a Task-1 spike reveals plan assumptions were wrong, add a
`**Spike-driven correction (DATE):**` callout INSIDE each affected
task — don't rely solely on the refresh-log at the top. Executors
read tasks one at a time and may miss top-of-file context.

```markdown
### Task 5: _deep_research_submit — failing tests + implementation

**Spike-driven correction (2026-05-12):** the assumed `agent=` parameter
was confirmed live. The request shape includes `store=True` (required
when `background=True`). See `research/spike-2026-05-11.md` §2.

**Files:**
- ...
```

## Commit-message embedding (commitlint footer traps)

Plans often include commit-message templates inside `git commit -m "..."`
fences. These messages, when committed, must pass commitlint. Two
parser surprises seen in this repo:

| Pattern | What commitlint does | Fix |
|---|---|---|
| `Open Question #6.` in body | `#6` matches the issue-reference trailer regex; body line ending with the trailer-like token triggers `footer-leading-blank` | Spell out: `Open Question 6` / `OQ6` / `Q.6` |
| Body line ending in `:` followed by a paragraph | Trailing colon is read as a footer-token separator; next paragraph parsed as a malformed footer | Reword so no body line ends with `:` (or end the body before the paragraph break) |

Pre-test commit messages locally with `bunx commitlint` (the lefthook
hook does this on every commit) BEFORE pasting them into a plan
template — otherwise reviewers will hit the failure on PR CI.

## Avoid bypass flags in plan-templated commits

Plan templates should NOT include `--no-verify` or `LEFTHOOK=0`. Per
the root `CLAUDE.md` Hook Discipline section: bypass is reserved for
short-lived intermediate WIP commits the author plans to squash.
Plan-templated commits are not WIP — they're the actual deliverable.

## Allowed commit types

Conventional Commits enforced by commitlint. The allowed `type` values:

```
feat, fix, perf, refactor, docs, test, ci, chore, build, style, revert
```

Not allowed: `spike`, `wip`, `update`, `improve`, etc. Spike commits
use `chore(<scope>):`. Plan-doc commits use `docs(<scope>):`.

## Subject length

100 characters MAX. Header-only — body is unbounded. Plans should
template subjects ≤ 80 chars to leave room for scope-prefix length.

## Plan refresh vs new dated file

| When | What |
|---|---|
| Small edits (< 30% of tasks change) | In-place refresh; add an `**Updated YYYY-MM-DD:**` log line under the header. |
| Large rewrites (>= 30% of tasks change) | Archive the old plan to `archive/`, write a new dated plan. Update the project file's "Plan" reference. |

See the P28 v1 → v2 transition for an example of the large-rewrite path
(`archive/2026-05-01-p28-gemini-background-deep-research.md` →
`docs/superpowers/plans/2026-05-11-p28-gemini-deep-research-background.md`).
