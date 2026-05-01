---
name: code-review-process
description: Structured multi-method process for reviewing code changes for bugs and maintainability risks, including test-suite evaluation, feature-specific probes, design-doc scope review, precise bug scope language, wrapper-aware validation, candidate validation with evidence, contract conflict handling, one-by-one user approval, regression tests, verified fixes, and bug-to-commit reporting. Use when Codex is asked to check for bugs, review recent work, review a component or project scope, validate suspected defects, or proceed from a bug review into fixes.
---

# Code Review Process

## Overview

Use this skill to run a disciplined code review that favors evidence, explicit scope, user decisions, regression tests, and traceable fixes over broad bug checklists.

Keep `SKILL.md` as the workflow. For the detailed report fields, statuses, and templates, read `references/review-schema.md` when preparing the report or fix tracker.

## Intake

Start by defining scope. If a multiple-choice user-input tool is available, use it. Otherwise, present concise numbered options and ask for a choice.

Offer scope options such as:

1. Recent work: inspect the most likely recent change set.
2. Uncommitted work: inspect staged and unstaged changes.
3. Component/path: inspect specified files, directories, packages, or modules.
4. Project/tracker scope: inspect a project file, issue, PR description, plan, or tracker.
5. Branch/PR scope: compare the current branch to a base branch or PR target.
6. Custom scope: use exact commits, paths, time window, or instructions from the user.

Accept or infer arguments when provided:

- `scope`: `recent`, `uncommitted`, `component`, `project-file`, `branch`, `pr`, or `custom`
- `paths`: files or directories
- `project_file`: e.g. `PROJECTS.md`, `planning/*.md`, issue text, or PR description
- `design_docs`: relevant specs, plans, research notes, trackers, issue text, or PR docs
- `test_commands`: user-provided or repo-standard commands for baseline and targeted tests
- `base`: branch, commit, tag, or merge-base target
- `since`: e.g. `24h`, `36h`, `last 3 commits`
- `focus`: `bugs`, `code-quality`, `regressions`, `behavior`, `tests`, `architecture`, or `docs-contract`
- `fix_mode`: `report-only`, `ask-before-fix`, or `fix-approved`
- `verification`: `targeted`, `full-gate`, or `repo-standard`
- `agent_budget`: requested parallel review passes when subagents are allowed

If scope is underspecified, inspect local context before asking: git status, recent commits, branch base, changed files, repo docs, test commands, and relevant project/tracker files. Recommend a scope with rationale, but do not silently narrow a user-requested scope.

## Bug Discovery Strategy

Use a mixed review strategy. Do not only wait for the existing test suite to fail, and do not report direct feature probes without also checking the repo's test surface when practical.

At minimum, cover these discovery paths unless the user narrows scope or a path is impossible:

- Test-suite baseline: identify the repo's canonical test commands from local instructions, CI, package scripts, Makefiles, justfiles, or existing docs. Run the appropriate baseline early enough to reveal current failures. Record commands, failures, and whether failures look related, pre-existing, or unclear.
- Feature-specific probes: map the changed files and commits to functional features fixed, added, or affected. Exercise those features directly with realistic user-facing commands, API calls, unit tests, integration tests, fixtures, or manual flows.
- Scenario variation: probe happy paths, boundary values, invalid inputs, missing config, conflicting options, repeated runs, persistence or restart behavior, output formats, and compatibility paths that the change could affect.
- Design-doc scope: for project, PR, branch, or time-window reviews, identify the design docs in scope for that period. Check project tracker references, specs, plans, research notes, issue or PR descriptions, docs changed in the same commits, and docs linked from the touched project entry.
- Static and semantic review: inspect control flow, state transitions, data conversion, validation, error handling, resource cleanup, concurrency or ordering assumptions, and migration or backward-compatibility paths.
- Contract cross-checks: compare implementation, tests, docs, examples, CLI help, schemas, public APIs, and commit history for drift or contradictory expected behavior.
- Regression-gap review: look for important changed behavior with no test coverage, tests that assert only implementation details, skipped or weakened assertions, stale fixtures, or mocks that no longer match production request shape.

Choose additional techniques based on the code under review, such as property or fuzz inputs for parsers, matrix tests for configuration layers, replay tests for provider integrations, accessibility or UI checks for frontends, or performance and resource checks for hot paths.

## Precision and Validation Hygiene

Describe bugs with their exact scope. Do not compress a narrow failure into a broad claim.

- State the failing scenario, the inputs/files/configuration, the command or API path, the observed state, and the expected state.
- State known-working nearby scenarios when they matter. Use explicit qualifiers such as "base case works, edge case fails", "happy path works, JSON error envelope fails", "only this input/file combination failed", or "base case is broken".
- Avoid titles like "JSON does not work" unless the base JSON behavior is actually broken. Prefer titles like "JSON error envelope is malformed for invalid config files with `--json`; successful JSON paths still pass".
- Preserve context in the report. Do not omit the setup, files, command shape, output mode, or exact boundary that makes the issue reproducible.
- Separate product behavior from harness behavior. If a failure appears only when wrapped in Python, a subshell, a test harness, or an automation script, validate the same behavior with a simple direct shell command where practical before calling it a product bug.
- Prefer standard shell probes for validation when possible: direct executable invocations, simple environment assignments, here-docs or temp files, `printf` pipes, and ordinary file operations. Record when a wrapper was used and whether an alternate simpler probe agrees.
- Watch for environment-sensitive differences: `cwd`, inherited env vars, shell quoting, glob expansion, stdin/stdout/stderr capture, TTY detection, permissions, temp directories, subprocess isolation, and cleanup behavior.

## Review Workflow

1. Read repo instructions first. Follow local guidance such as `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING`, Makefiles, justfiles, package scripts, and CI configs.
2. Establish the review bundle. Prefer exact diffs, merge-base comparisons, uncommitted changes, recent commits, or user-provided files over a broad repo scan.
3. Identify review surfaces: canonical test suites, affected functional features, user-facing scenarios, relevant design docs, runtime contracts, and likely regression gaps.
4. Run or schedule the test-suite baseline. If the full suite is expensive, start with documented targeted commands and state what full command remains to be run.
5. Split review passes by area. If the current instructions and user request allow subagents, assign disjoint review passes. Otherwise, run the same passes locally and keep notes separated.
6. Test affected features directly with scenario variation. Prefer exact commands, tests, fixtures, or manual flows that exercise the behavior users will hit.
7. Collect candidate findings from all discovery paths. Separate true behavior bugs from code quality or maintainability risks.
8. Deduplicate and validate candidates. Do not report speculative findings as confirmed.
9. Detect contract conflicts. Compare implementation, tests, docs, examples, plans, and commit history. If evidence conflicts, stop before fixing and ask the user to choose the intended contract.
10. Write a validation thesis for each surviving finding before fixing. State how to prove or disprove the bug, including the expected working baseline, failing variant, and simplest practical execution form.
11. Cross-check wrapper-sensitive repros. If validation used Python, a subshell, a harness, or a script, rerun a simpler direct shell or user-facing form when practical and record whether results match.
12. Produce the structured report and tracker using `references/review-schema.md`.
13. Run a commonality pass. Look for shared root causes, duplicated logic, architecture issues, or repeated test gaps.
14. Recommend a fix order. Preserve original IDs; add an explicit recommended order and rationale.
15. Go one by one. Show one finding at a time in recommended order and ask the user what to do.
16. For approved fixes, design the regression test first, then implement the fix, then verify.
17. After each fixed bug or approved fix group, run targeted tests and the repo's documented full test suite. If full verification is expensive or unclear, ask before substituting a narrower command.
18. Commit each verified bug or approved fix group when commits are authorized. Record the commit hash for every fixed finding.
19. End with a bug-to-commit table and verification summary.

## Finding Rules

Assign every finding a stable ID and status:

- True bugs: `BUG-001`, `BUG-002`, ...
- Code quality risks: `CQ-001`, `CQ-002`, ...
- Optional security findings discovered naturally: `SEC-001`, `SEC-002`, ...

Use statuses from the schema reference. At minimum, distinguish: `candidate`, `validation-thesis-written`, `reproduced`, `source-proven`, `not-reproduced`, `needs-clarification`, `approved-to-fix`, `test-added`, `fixed`, `verified`, `committed`, `deferred`, `rejected`, and `saved-as-project`.

Each finding needs evidence:

- Related files and line numbers where appropriate.
- Short code snapshot only when it clarifies the issue.
- Scope statement that distinguishes base-case, happy-path, edge-case, and unknown coverage.
- Exact trigger: command/API call, inputs, files, configuration, environment, and output mode.
- Found result and expected result.
- Known-working scenarios that were tested or source-proven.
- Why it is believed to be a bug.
- Arguments against it being a bug.
- Ambiguity that needs clarification.
- Tested current behavior when reproducible, including trigger and observed result.
- Validation form, including whether the repro used direct shell, a test runner, Python, a subshell, or another wrapper.
- Recommended regression test.

Security findings may be included if discovered, but do not perform a security-focused review unless the user asks for one.

## Contract Conflicts

Treat conflicting evidence as a first-class review result. Examples:

- Docs say one behavior, implementation does another.
- Tests encode a different contract than docs or code comments.
- Multiple docs pages disagree.
- Commit history suggests a behavior was intentionally changed but current docs were not updated.
- A project plan or tracker conflicts with the implemented surface.

When this happens:

1. Create a finding with status `needs-clarification`.
2. Present the conflicting evidence with file and line references.
3. Provide options for the intended contract.
4. Make a recommendation based only on evidence such as commit history, tests, docs recency, issue text, and runtime behavior.
5. Ask the user to choose before fixing.

Do not decide the intended contract on your own when material evidence conflicts.

## Fix Flow

After the report, say "Go one by one" and present findings in the recommended fix order. Show only the current finding plus relevant related IDs.

For each finding, offer choices such as:

- Fix now.
- Defer.
- Reject as not a bug.
- Clarify expected behavior first.
- Apply the same resolution as a related prior finding.
- Save as a larger project.
- Step back and design an architectural fix for the group.

Before fixing:

1. Confirm the finding is `reproduced` or `source-proven`, or get clarification for `needs-clarification`.
2. State the regression test that should fail before the fix.
3. Add or update that test first where practical.
4. Run the test to confirm it captures the issue, unless impossible; record why if skipped.
5. Implement the smallest appropriate fix or the approved shared/architectural fix.
6. Run the targeted regression test.
7. Run the repo's documented full verification after that bug or fix group.
8. Update the tracker checkbox and status.
9. Commit if authorized, using a message that references the finding ID.

If multiple findings share one resolution, fix them as an approved group and mark each finding with the same commit. If a larger architecture change is better but not approved for now, offer to save it as a project and proceed with smaller approved fixes.

## Completion Report

Finish with:

- A table mapping each finding ID to status, fix group, regression test, verification, and commit hash.
- A list of deferred, rejected, or clarification-needed findings.
- Any skipped or substituted verification with rationale.
- Residual risk.

Do not claim a finding is fixed unless the report records the regression test or why no test was practical, the verification commands and results, and the commit or explicit reason no commit was created.
