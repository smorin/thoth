# Code Review Report Schema

Use this reference when preparing review reports, trackers, validation plans, and final bug-to-commit summaries.

## Status Lifecycle

Use the most precise status that applies:

- `candidate`: suspected by a review pass, not yet validated.
- `validated-looking`: evidence suggests a real issue, but no second-level validation yet.
- `validation-thesis-written`: validation plan exists.
- `reproduced`: runtime command, test, or manual path confirmed the behavior.
- `source-proven`: source inspection proves the issue without a practical runtime repro.
- `not-reproduced`: validation did not confirm it.
- `needs-clarification`: code, docs, tests, plans, or expected behavior conflict.
- `approved-to-fix`: user approved fixing this issue.
- `test-added`: regression test or guard was added/updated.
- `fixed`: implementation change is complete.
- `verified`: targeted and full repo verification passed or approved substitute passed.
- `committed`: fix is committed and hash is recorded.
- `deferred`: user chose not to fix now.
- `rejected`: user or validation determined this is not a bug.
- `saved-as-project`: larger architecture or cleanup work was captured for later.

## Finding Template

Use this structure for each true bug, code quality risk, or naturally discovered security finding:

```markdown
### [ ] BUG-001: Short title

- Status: candidate
- Severity: critical | high | medium | low
- Type: regression | incorrect behavior | missing validation | state/race | API/CLI contract mismatch | docs-contract conflict | test-code conflict | code quality | maintainability | security
- Confidence: high | medium | low
- Related files: `path/file.ext`
- Line numbers: `path/file.ext:123`
- Code snapshot: short excerpt if useful
- Scope statement: base case broken | happy path works and edge case fails | output-format-specific | environment-specific | unknown pending validation
- Exact failing scenario: command/API path plus inputs, files, config, env, cwd, and output mode
- Known-working scenarios: nearby cases validated as working, or `not checked`
- Found result: what currently happens
- Expected result: what should happen
- Current behavior test: command, test, or manual trigger and observed result
- Validation form: direct shell | test runner | Python wrapper | subshell | harness | manual flow
- Wrapper cross-check: simpler alternate command and result, or why not practical
- Validation thesis: how to prove or disprove this finding
- Validation result: reproduced | source-proven | not-reproduced | needs-clarification
- Why this is a bug: evidence-based argument
- Why this might not be a bug: counterargument or missing context
- Ambiguity to clarify: user/product decision needed, if any
- Recommended regression test: file/test name or test shape
- Test status: proposed | added | updated | not practical | deferred
- Fix group: group name or none
- Recommended order: integer or deferred
- Blocked by: finding IDs or none
- Recommended fix: concrete fix approach
- Verification: targeted and full commands to run
- Commit: hash or none
```

Use `CQ-001` for code quality risks and `SEC-001` for security findings discovered incidentally.

## Precision Rules

Use precise, context-preserving titles and descriptions:

- Do not say a whole feature is broken when only one scenario failed.
- Include the boundary that makes the scenario fail, such as input shape, config file content, output mode, environment, or state transition.
- Name the behavior that still works when it matters to severity or scope.
- Distinguish "base case broken" from "happy path works, edge case fails" from "wrapper-specific failure".
- Do not replace evidence with a summary. Keep the exact command/API path, fixture shape, observed output, and expected output available in the finding.

Example title pattern:

```markdown
BUG-001: JSON error envelope is malformed for invalid config files with `--json`; successful JSON output still works
```

## Validation Thesis Template

Before any fix, write this:

```markdown
Validation thesis for BUG-001:

- Claim: concise statement of the suspected bug.
- Scope hypothesis: base case broken | happy path works and edge case fails | output-format-specific | environment-specific | unknown.
- Known-working baseline to check: nearby success path, non-JSON path, default input, or other control scenario.
- Failing variant to check: exact edge case, input files, config, env, command/API path, and output mode.
- Evidence to check: code paths, docs, tests, commands, logs, or examples.
- Confirmation method: exact command, test, manual path, or source proof. Prefer a direct user-facing shell command when practical.
- Wrapper check: whether validation uses Python, a subshell, a harness, or a script, and the simpler alternate form to run if practical.
- Confirms if: expected failing/current result.
- Disproves or downgrades if: result that would show no bug or only ambiguity.
- Relevant contract sources: implementation, tests, docs, plans, commit history.
```

Only move to fixing when the result is `reproduced` or `source-proven`, or after the user resolves `needs-clarification`.

## Report Sections

Use these sections in order:

1. Review scope and bundle.
2. Validation method and commands used.
3. True bugs.
4. Code quality and maintainability risks.
5. Incidental security findings, if any.
6. Contract conflicts requiring clarification.
7. Common root causes and architecture opportunities.
8. Recommended fix order.
9. One-by-one decision queue.

## Commonality Pass

After findings are validated, look for:

- Same root cause across multiple IDs.
- Repeated code or missing shared abstraction.
- Repeated docs/test/code contract drift.
- Shared validation or parsing pattern.
- Multiple findings that one architecture change would fix.
- A test gap that allowed several issues.

For each group, propose:

- Fix individually.
- Fix as one shared change now.
- Save architecture work as a project for later.
- Clarify intended contract first.

## Fix Ordering

Preserve IDs and add an independent order. Sort by:

1. Clarifications that block other work.
2. Root-cause or architecture fixes that resolve multiple findings.
3. Dependency order.
4. Severity and user impact.
5. Testability and confidence.
6. Blast radius and regression risk.
7. User priority.

Example:

```markdown
Recommended order:

1. BUG-008: shared parser fix; resolves BUG-002 and BUG-005 too.
2. BUG-001: high-severity behavior bug independent of parser group.
3. CQ-003: defer or save as project; broad architecture cleanup.
```

## Final Table

End with a table like:

| ID | Status | Fix group | Regression test | Verification | Commit |
|---|---|---|---|---|---|
| BUG-008 | committed | CLI parsing | `tests/test_cli.py::test_parser_contract` | targeted + full suite passed | `abc1234` |
| BUG-002 | committed | CLI parsing | `tests/test_cli.py::test_parser_contract` | targeted + full suite passed | `abc1234` |
| CQ-003 | saved-as-project | parser cleanup | recommended | not run | none |

For every `fixed`, `verified`, or `committed` item, include the test or explain why a direct test was not practical.
