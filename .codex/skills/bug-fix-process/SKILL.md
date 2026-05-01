---
name: bug-fix-process
description: Process a known bug ID from a structured bug review into a revalidated fix plan and implementation path, including fix-worthiness, multiple-choice user decisions, architectural/common-pattern analysis, consistency and naming review, TDD regression tests, maintainability improvements, verification, tracker updates, and commit reporting. Use when Codex is given a specific bug ID and asked whether or how to fix it, or asked to proceed from a reviewed bug into a fix.
---

# Bug Fix Process

## Overview

Use this skill after a bug has already been identified or assigned an ID. The goal is to revalidate the specific bug, decide whether it should be fixed now, choose the right fix shape, then implement with tests and verification.

This complements `code-review-process`: that skill finds and validates bugs; this skill processes one reviewed bug ID into a fix decision and, when approved, a verified change.

## Intake

Start from a concrete bug identifier. Accept or infer:

- `bug_id`: e.g. `BUG-001`, `CQ-003`, `SEC-001`, or a project-specific ID.
- `source`: review report, tracker, PR comment, issue, branch notes, or user-provided bug text.
- `fix_mode`: `recommend-only`, `ask-before-fix`, or `fix-approved`.
- `scope`: paths, commits, project entry, PR, issue, or exact files.
- `verification`: `targeted`, `repo-standard`, or `full-gate`.

If the bug ID or source is missing, inspect nearby review artifacts first. If still unclear, ask for the bug ID or paste of the finding before proceeding.

## Workflow

1. Read repo instructions first. Follow local guidance such as `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING`, Makefiles, justfiles, package scripts, and CI configs.
2. Locate the bug record. Preserve the original ID, severity, failing scenario, expected behavior, evidence, proposed regression test, and any prior user decision.
3. Revalidate before planning. Reproduce or source-prove the bug against the current code. Prefer the exact original command or scenario, then a simple direct shell/user-facing form when practical.
4. Restate the bug precisely: what fails, what works, which inputs/files/config/output mode matter, and whether this is a base-case failure, edge-case failure, output-format failure, environment-specific failure, or unclear contract.
5. Run the fix-worthiness assessment.
6. Run the architecture and common-pattern assessment.
7. Present a decision package. Use a multiple-choice user-input tool when available; otherwise show concise numbered options and ask for a choice.
8. If approved, write the regression test first and run it to see the expected failure where practical.
9. Implement the chosen fix shape.
10. Run the targeted regression test, then widen to the repo-standard verification requested or documented.
11. Update the relevant tracker, project file, or review report when the repo convention or bug source requires it.
12. Commit only when authorized. Use a conventional commit message if the repo requires it and include the bug ID when useful.
13. Finish with the bug ID, selected strategy, files changed, regression test, verification results, tracker status, commit hash or reason no commit was made, and residual risk.

## Fix-Worthiness Assessment

Decide whether the bug is worth fixing now before designing the patch. Evaluate:

- User impact: severity, frequency, affected workflow, data loss, broken output contract, or blocked release.
- Confidence: reproduced, source-proven, flaky, environment-specific, or still ambiguous.
- Workaround: available, documented, acceptable, or unsafe.
- Fix cost: small localized patch, moderate cross-module change, broad refactor, or unclear.
- Regression risk: public API/CLI change, data migration, format change, concurrency risk, or low-risk internal fix.
- Timing: urgent, should batch with related fixes, should save as a project, or not worth fixing.

Recommended outcomes:

- Fix now when impact is real, evidence is strong, and the patch is reasonably bounded.
- Defer when impact is low, workaround is acceptable, or risk exceeds near-term value.
- Reject when revalidation disproves the bug or the expected behavior is not intended.
- Clarify first when product/docs/tests disagree about the intended contract.
- Save as a project when the right fix is architectural and too broad for the current bug.

## Architecture and Pattern Assessment

Before choosing the implementation, check whether the bug is a symptom of a broader pattern.

Look for:

- Duplicated logic across multiple files or commands.
- Existing helpers, abstractions, validators, serializers, adapters, or command patterns that this code failed to use.
- Naming convention drift, inconsistent option names, mismatched method names, or ambiguous terminology.
- Inconsistent error handling, output envelopes, state transitions, config resolution, parsing, or persistence behavior.
- Similar tests that should be mirrored or generalized.
- Code that could become simpler by using the repo's established pattern.

Choose the smallest fix that also improves maintainability when the evidence supports it:

- Minimal targeted fix: use when the bug is isolated and there is no repeated pattern.
- Pattern-aligned fix: use when a local site drifted from an existing convention.
- Shared abstraction: use when the same behavior is duplicated enough that fixing one site leaves likely future bugs.
- Architecture project: use when a better design is real but too broad for the current bug's risk or timeline.

Do not refactor for aesthetics alone. Tie architecture work to bug prevention, consistency, reduced duplication, clearer naming, or simpler future maintenance.

## Decision Package

Before changing code, present the user with a concise decision package unless `fix_mode` is clearly `fix-approved`.

Include:

- Bug ID and current validation status.
- Precise bug scope and known-working scenarios.
- Fix-worthiness recommendation.
- Architecture/common-pattern finding.
- Recommended regression test.
- Recommended fix option.
- Verification plan.

Offer choices such as:

1. Fix now with the minimal targeted patch.
2. Fix now with a pattern-aligned patch using the existing convention.
3. Fix now with a shared abstraction/refactor because the duplicated pattern is the root cause.
4. Clarify expected behavior before fixing.
5. Defer or reject this bug.
6. Save the architectural work as a separate project and only apply the narrow fix, or no fix now.

If multiple-choice tooling is available, use it for these options. Otherwise, ask the user to choose by number.

## TDD Fix Flow

After approval:

1. State the regression test that should fail before the fix.
2. Add or update that test first where practical.
3. Run the test and record the red result. If the bug cannot be captured directly, explain why and use the closest practical guard.
4. Implement the selected fix shape without unrelated cleanup.
5. Run the regression test and record the green result.
6. Run nearby affected tests.
7. Run the repo-standard verification gate or the user-approved substitute.
8. If a wider architectural fix was selected, verify every touched path that now uses the shared pattern.

## Completion Report

Finish with:

- Bug ID and final status.
- Fix decision: minimal, pattern-aligned, shared abstraction, deferred, rejected, clarified, or saved as project.
- Why the selected approach was worth it.
- Regression test and verification commands with results.
- Architecture/pattern changes made or intentionally not made.
- Tracker/report updates.
- Commit hash, or explicit reason no commit was created.
- Residual risk and follow-up project, if any.

Do not claim the bug is fixed unless the regression test or documented substitute exists, verification has run, and the report preserves the exact bug ID and selected fix strategy.
