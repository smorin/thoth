# Plan ↔ PRD Inconsistency Audit

**Plan audited:** `planning/thoth.plan.v7.md` (P07 – Fix Async Submission, Perplexity Readiness, Interactive Status, Verification Workflow)
**PRD audited:** `planning/thoth.prd.v24.md` (Thoth v2.5 / target v2.6, Document Version 26.0)
**Audit date:** 2026-04-16

Each inconsistency lists:
- **Plan ref** (lines) and **PRD ref** (lines)
- **Reason** it is inconsistent
- **Options** to resolve
- **Recommendation**, **Rationale**, and **Final Decision**

---

## INC-001: Perplexity Availability – "Ready" vs "Not Implemented"

**Plan ref** – `thoth.plan.v7.md` lines 13, 39–57:
- Non-goal: "Implementing the full Perplexity provider."
- M2 explicitly treats Perplexity as **not implemented**; requires `providers -- --list` to stop showing Perplexity as `✓ Ready`, and a direct `--provider perplexity` call to raise a clear unsupported error.

**PRD ref** – `thoth.prd.v24.md`:
- Line 108 (Core Value Propositions): "Multi-provider intelligence: Automatic parallel execution of OpenAI and Perplexity"
- Line 133–134, 1388: Default multi-provider execution uses OpenAI + Perplexity
- Lines 362–368 (F-93–F-99): seven "Must" Perplexity functional requirements
- Lines 902–905 (§11.5): `providers -- --list` shows Perplexity with `✗ No key` (implies working provider w/o key), not "not implemented"
- Lines 1513–1514: States Perplexity hardcoded model list and provider behavior are delivered features

**Reason:** Plan says Perplexity is unimplemented and must be surfaced as such. PRD repeatedly states Perplexity works, has 7 Must-priority features, ships in the default multi-provider path, and surfaces a "✗ No key" status (not "not implemented") in the providers list.

**Resolution options:**
1. Update PRD to mark Perplexity as *pending / not implemented* (add status column, demote F-93–F-99 to "Planned", change §11.5 table state to `✗ Not implemented`, remove Perplexity from default-providers copy until M11–M13 ships).
2. Expand plan scope to actually implement Perplexity so PRD claims stay honest.

**Recommendation:** Option 1. The plan's stated purpose is to make current behavior honest, not to add a provider. Aligning the PRD with real capability is a documentation fix; implementing Perplexity is a multi-milestone engineering effort already sketched in PRD as "pending implementation in M11–M13" (line 225). Keep PRD authoritative about *intent*, but add an explicit "Status" column and mark unshipped features accordingly.

---

## INC-002: Default Providers Copy vs. Single-Provider Reality

**Plan ref** – `thoth.plan.v7.md` line 13 (non-goal) and M2 acceptance (lines 53–56):
- After the fix, Perplexity is not usable; by implication, the default `thoth "prompt"` path cannot dual-run OpenAI + Perplexity.

**PRD ref** – `thoth.prd.v24.md`:
- Line 103: "just give it a prompt and get comprehensive research results"
- Line 108: "Automatic parallel execution of OpenAI and Perplexity"
- Line 225 (F-15): "Dual-provider execution for deep_research mode by default"
- Line 552–555 (§10.2 example): shows two files created, one per provider
- Line 792 (§11.1): progress display shows "Providers: OpenAI + Perplexity" running in parallel

**Reason:** PRD's core value proposition and multiple examples assume default dual-provider execution. Plan's M2 outcome leaves Perplexity unavailable, breaking the documented default experience. Plan does not specify what the default provider set should look like while Perplexity is absent.

**Resolution options:**
1. Change PRD default-provider behavior to "OpenAI only unless Perplexity is available"; update §11.1 example, Core Value Propositions, and F-15 to reflect single-provider default.
2. Add a task to the plan that documents the temporary single-provider default (update help text, README, and F-15 rationale) until Perplexity lands.

**Recommendation:** Option 2. Keep PRD's long-term "dual-provider" intent, but add an explicit plan task (and a PRD note under F-15) stating "while Perplexity is pending, default behavior is OpenAI-only." This avoids rewriting the PRD's vision while closing the honesty gap the plan is trying to fix.

---

## INC-003: `make check` Semantics – Env Check vs. Lint/Typecheck

**Plan ref** – `thoth.plan.v7.md` lines 88–92, 94–98:
- Adds/redefines `make check` so it runs the documented main-executable lint/typecheck.
- Line 92: suggests moving current dependency check to `make env-check`.

**PRD ref** – `thoth.prd.v24.md` line 451 (F-152):
- "Separate Makefile targets for main executable (lint, format, typecheck, check, fix)" – marked ✓ Implemented.

**Project CLAUDE.md** (external, project-level instructions shown in system context):
- "`make env-check` # Verify bootstrap dependencies are installed"
- "`just check` # Run lint and typecheck on main executable"

**Reason:** Three sources disagree on what `make check` should do. PRD F-152 claims it is already implemented as lint/format/typecheck. Project CLAUDE.md treats `make check` as an env/bootstrap check and routes quality checks through `just check`. Plan proposes repointing `make check` at lint/typecheck while preserving env-check under `make env-check`.

**Resolution options:**
1. Remove all references to `make check` (and other `make` quality targets) from plan and PRD; route every quality action through `just check` / `just fix` / `just test-check` / `just test-fix`. `make` retains only `env-check` (bootstrap dependency verification).
2. Keep `make check` as the env/bootstrap check (per CLAUDE.md) and remove/rename F-152's claim; developers use `just check` directly for lint/typecheck.

**Recommendation:** Option 1.

**Final Decision:** Option 1 – remove every reference to `make check` in plan, PRD, README, and CLAUDE.md; replace with `just check`. `env-check` is the only quality-adjacent target on `make`. PRD F-152 must be rewritten to describe the `just` targets (not Makefile targets).

---

## INC-004: Verification Workflow Commands – Plan vs. CLAUDE.md

**Plan ref** – `thoth.plan.v7.md` lines 144–151 (Verification Plan):
- `make check` → `make fix` → `./thoth_test -r` → `make test-check` → `make test-fix` → re-run.

**Project CLAUDE.md** (Code Quality Assurance Workflow):
- `make env-check` → `just fix` → `just check` → `./thoth_test` → `just test-fix` → `just test-lint` → `just test-typecheck`.

**PRD ref** – `thoth.prd.v24.md` F-152–F-154 (lines 451–453) only list required targets, no workflow ordering.

**Reason:** Plan's verification recipe calls `make`-wrapped quality commands; CLAUDE.md uses `just` directly. Using `make` as a thin wrapper around `just` adds an indirection that hides the real tooling and invites drift.

**Resolution options:**
1. Remove every documented use of `make` as a thin wrapper. Rewrite plan §"Verification Plan" to call `just` directly, mirroring CLAUDE.md: `make env-check` → `just fix` → `just check` → `./thoth_test -r` → `just test-fix` → `just test-lint` → `just test-typecheck`. Delete plan M4 Makefile-target work except for confirming `env-check` behavior.
2. Keep `make` wrappers and update CLAUDE.md to use them.

**Recommendation:** Option 1.

**Final Decision:** Option 1 – do not use `make` as a thin wrapper. Strip plan §"Verification Plan" of `make check/fix/test-check/test-fix` references and replace with the `just` sequence from CLAUDE.md. Update M4 Implementation Tasks to drop "add missing `make` targets" and instead ensure docs (plan, PRD, README) reference `just` for quality work.

---

## INC-005: Plan Missing Venv & `-all` Makefile Targets Promised in PRD

**Plan ref** – `thoth.plan.v7.md` lines 88–89:
- Lists only `check`, `fix`, `test-check`, `test-fix` for M4.

**PRD ref** – `thoth.prd.v24.md`:
- Line 453 (F-154): "Combined Makefile targets for full codebase (lint-all, format-all, check-all, fix-all)" – Must, ✓ Implemented
- Lines 459–463 (F-160–F-163): `venv`, `venv-install`, `venv-sync`, `venv-clean` – Must, ✓ Implemented
- Lines 464–465 (F-164–F-165): UV export integration, process substitution – Must, ✓ Implemented

**Reason:** PRD claims F-154 and F-160–F-165 as implemented Makefile targets. Per INC-003 and INC-004 decisions, new Makefile quality targets are not to be added; the PRD's reliance on `-all` and venv-oriented `make` targets is inconsistent with the "quality lives in `just`" direction.

**Resolution options:**
1. Do not create new Makefile targets. Update the PRD so F-154 / F-160–F-165 reference the existing `just` targets (`just lint-all`, `just format-all`, `just check-all`, `just fix-all`, and whatever `just` targets cover venv lifecycle). If no equivalent `just` target exists for a PRD-listed capability, remove that requirement from the PRD rather than adding a Makefile.
2. Keep PRD as-is and add/preserve Makefile targets.

**Recommendation:** Option 1.

**Final Decision:** Option 1 – no new `make` targets. Rewrite PRD F-152, F-153, F-154 to describe `just` targets. For F-160–F-165 (venv/UV), either point to the corresponding `just` recipe or delete the requirement if the project doesn't have one. Add a plan task to inventory the existing `just` targets and align the PRD list exactly to what exists.

---

## INC-006: Plan Uses No Test IDs; PRD Demands Formal Test IDs

**Plan ref** – `thoth.plan.v7.md`:
- Test Design sections (lines 19–22, 41–45, 62–66, 82–85) describe regression tests in prose only.
- Task Breakdown (lines 115–133) uses Task A/B/C/D, not PRD-style IDs.

**PRD ref** – `thoth.prd.v24.md`:
- Every functional requirement line carries a Test ID (e.g., lines 211–236: T-MODE-01, T-CLI-01, …, T-ASYNC-04, T-PROV-13, T-INT-13).
- Relevant defect-adjacent IDs: F-10/T-ASYNC-04 (async), F-15/T-PROV-01 (Perplexity dual-provider), F-67/T-ASYNC-06 (lifecycle), F-113/T-PROV-13 (providers --list), F-141/T-INT-13 (`/status`), F-152..F-154 (Makefile – currently no Test IDs).

**Reason:** Plan regressions cannot be traced back to PRD requirements because the plan never references T-* IDs. CLAUDE.md requires plan tasks/tests to use `[P##-T##]` / `[P##-TS##]` IDs.

**Resolution options:**
1. Adopt the simplest convention: use the project's `[P##-T##]` / `[P##-TS##]` ID format in the plan, and reference the related PRD `T-*` IDs inline in each test description. Backfill PRD Test IDs where they are missing (F-152..F-165) using the existing `T-*` convention.
2. Introduce a parallel mapping table.

**Recommendation:** Option 1.

**Final Decision:** Option 1 – apply the existing project convention. Rename plan test items to `[P07-TS01]`, `[P07-TS02]`, …; rename tasks to `[P07-T01]`, `[P07-T02]`, …; include the relevant PRD `T-*` reference inline in each test description. File a follow-up edit to add missing PRD Test IDs (e.g., `T-ASYNC-08` for submission persistence, `T-MAKE-01` is dropped per INC-005 – use `T-JUST-01..04` for the `just` workflow instead).

---

## INC-007: Async Success Output Wording Not Defined in Either Doc

**Plan ref** – `thoth.plan.v7.md` line 35:
- "No false-positive 'Research submitted' output on submission failure."
- Acceptance (line 33): "prints an operation ID only after a provider job exists."

**PRD ref** – `thoth.prd.v24.md` lines 622–625 (§10.2 Advanced Mode Examples):
```
Research submitted
Operation ID: research-20240803-143022-a1b2c3d4e5f6g7h8
Check later with: thoth status ...
```

**Reason:** The PRD shows "Research submitted" as success output but does not *require* that exact string as a contract; the plan relies on "Research submitted" semantics without elevating it to an F-ID. A future reworded message could silently re-introduce the very regression the plan is trying to prevent.

**Resolution options:**
1. Add a PRD functional requirement (e.g., F-176) specifying the exact async success message contract and assign it a Test ID (T-ASYNC-08).
2. Leave the PRD example as-is and only assert in plan tests that a provider job exists (no string assertion).

**Recommendation:** Option 1.

**Final Decision:** Option 1 – add PRD F-176 ("Async submission prints `Research submitted` + `Operation ID: <id>` + `Check later with: thoth status <id>` only after a provider job has been successfully created") and test ID `T-ASYNC-08`. Reference `T-ASYNC-08` from plan M1 / `[P07-TS01]`.

---

## INC-008: Interactive `/status` Scope – "Last Operation" vs. Arbitrary Operation

**Plan ref** – `thoth.plan.v7.md` lines 60–76:
- M3 scopes `/status` to the **last** submitted interactive operation (`slash_registry.last_operation_id`).
- Acceptance (line 74): "After an interactive submission, `/status` reports the last operation instead of always saying none exists."

**PRD ref** – `thoth.prd.v24.md`:
- Line 430 (F-141): "Implement `/status` command to check operation status"
- Line 534 (§10.1): `/status     Check operation status`

**Reason:** PRD wording is ambiguous – "operation status" could mean any operation or just the session's last one. Plan narrows to last-in-session without the PRD saying so.

**Resolution options:**
1. Update F-141 to explicitly specify last-operation-in-session behavior only.
2. Expand plan M3 to accept an optional `<ID>` argument in `/status`: with no argument it reports the last interactive operation; with an ID it reports that operation. Update PRD F-141 and §10.1 help text to document both forms.

**Recommendation:** Option 2.

**Final Decision:** Option 2 – `/status` takes an optional operation ID. Default behavior (no argument) shows the last operation submitted in the current interactive session; with an ID it delegates to the same code path as the top-level `thoth status <ID>` command. Update PRD F-141, §10.1 Interactive Mode Commands list, and plan M3 Acceptance Criteria. Add test cases `[P07-TS05]` (default) and `[P07-TS06]` (with ID).

---

## INC-009: PRD Document Version Drift vs. Filename

**Plan ref** – n/a.

**PRD ref** – `thoth.prd.v24.md` lines 1, 12, 15.

**Reason:** File name (v24), product version (v2.5), target release (v2.6), Document Version (26.0) are four different numbers.

**Final Decision:** Ignored per user instruction. No action.

---

## INC-010: Test Command Examples (reference case from prompt)

**Plan ref** – `thoth.plan.v7.md` Task A–D and Test Design sections (lines 19–22, 41–45, 62–66, 82–85):
- Uses prose test names only.

**PRD ref** – `thoth.prd.v24.md` lines 211–236, 262–288, etc.:
- Uses formal `T-*` IDs; examples use natural language like `thoth "test query" --provider mock`.

**Reason:** Plan uses prose descriptions; PRD uses formal test IDs. Matches the example supplied in the audit prompt.

**Resolution options:**
1. Add natural-language example snippets to plan Test Design sections.
2. Keep formal test IDs but add user-friendly descriptions.

**Recommendation:** Per supplied final decision – Add IDs to the PRD where missing and reference them in the plan's formal tests.

**Final Decision:** Accepted. See INC-006 for the concrete ID-assignment plan; PRD gets missing `T-*` IDs (e.g., `T-ASYNC-08`, `T-JUST-01..04`, `T-INT-13` already exists), and the plan references them inline alongside the project's `[P07-TS##]` convention.

---

## Summary Table

| ID | Area | Severity | Final Decision |
|----|------|----------|----------------|
| INC-001 | Perplexity availability | High | Option 1 – mark PRD Perplexity features as "Planned"; keep plan scope narrow |
| INC-002 | Default multi-provider copy | High | Option 2 – add plan task to update PRD/help text while Perplexity pending |
| INC-003 | `make check` semantics | Medium | Remove all `make check` references; use `just check`; `env-check` stays only on `make` |
| INC-004 | Verification workflow drift | Medium | No `make` wrappers; rewrite plan verification to call `just` directly |
| INC-005 | Plan/PRD misaligned on Makefile targets | Medium | No new `make` targets; PRD references existing `just` targets |
| INC-006 | Test ID convention | Medium | Use `[P07-T##]` / `[P07-TS##]` in plan with inline `T-*` PRD refs |
| INC-007 | Async success string contract | Low | Add PRD F-176 + `T-ASYNC-08` |
| INC-008 | `/status` scope | Low | Option 2 – `/status` accepts optional ID, defaults to last-in-session |
| INC-009 | PRD version/filename drift | — | Ignored per user |
| INC-010 | Test IDs in plan | Low | Add missing IDs to PRD; plan references them |
