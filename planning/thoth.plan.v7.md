# P07: Fix Async Submission, Perplexity Readiness, Interactive Status, and Doc/Workflow Alignment

**Goal:** Fix the four confirmed defects in `thoth`:
1. `--async` reports success without submitting work.
2. Perplexity is presented as usable while the provider is not implemented.
3. Interactive `/status` cannot report the last operation status (and does not accept an explicit ID).
4. The documented verification workflow and `make`-based references drift from repo reality (quality work lives in `just`; `make` is bootstrap-only).

**Strategy:** Apply test-driven development for each defect. For every task, add or update tests first, make the implementation pass, then run the full verification workflow. Prioritize user-facing correctness before documentation cleanup.

**Scope:** `src/thoth/__main__.py`, `thoth_test`, documentation (plan, PRD, README, CONTRIBUTING, RELEASE, CHANGELOG), and minimal supporting test files under `tests/`.

**Non-goals:** Implementing the full Perplexity provider. This plan only makes the current product behavior honest and consistent. This plan does **not** add new `make` targets — quality work is `just`-only; `make` keeps `env-check`/`check-uv` only.

---

## Milestone 1: Async Mode Actually Submits Work

### Test Design
- **[P07-TS01]** — Regression proving `--async` persists a checkpoint with at least one provider entry and a real provider job ID.
  PRD refs: F-10 / T-ASYNC-04, F-67 / T-ASYNC-06, F-177 / T-ASYNC-08 (see PRD updates).
- **[P07-TS02]** — Regression proving `thoth status <ID>` after async submission reports provider state, not a permanently empty queued shell.
  PRD refs: F-13 / T-CMD-02.
- **[P07-TS03]** — Regression proving the exact async success output contract from F-177 / T-ASYNC-08 (`Research submitted` + `Operation ID: <id>` + `Check later with: thoth status <id>`) appears **only** after a provider job exists.
- Keep all async tests on the `mock` provider to avoid external API dependence.

### Implementation Tasks
- [ ] **[P07-T01]** Update `run_research()` so the async branch performs provider submission before returning.
- [ ] **[P07-T02]** Persist provider job metadata into the operation checkpoint before exit.
- [ ] **[P07-T03]** Codify the async lifecycle state: `operation.status` moves from `queued` to `running` once submission succeeds (PRD F-67).
- [ ] **[P07-T04]** Ensure partial submission failures surface clearly and do not print the F-177 success output.
- [ ] **[P07-T05]** Keep sync execution behavior unchanged.

### Acceptance Criteria
- `thoth "prompt" --provider mock --api-key-mock dummy --async` prints the F-177 success block only after a provider job exists.
- `thoth status <ID>` shows provider details for the async operation.
- No false-positive "Research submitted" output on submission failure.
- New PRD contract F-177 / T-ASYNC-08 is covered by [P07-TS03].

---

## Milestone 2: Perplexity Availability Is Honest

### Test Design
- **[P07-TS04]** — Regression covering `thoth providers -- --list` so a not-implemented provider is not shown as `✓ Ready`.
  PRD refs: F-113 / T-PROV-13 (status column update), F-93–F-99 (demoted to "Planned").
- **[P07-TS05]** — Regression covering direct execution with `--provider perplexity`: the user must receive a clear unsupported/`ProviderError` message rather than an unexpected exception.
  PRD refs: F-15 (dual-provider default – temporary OpenAI-only note), F-22 / T-ERR-01.
- Decide expected UX: `providers --list` shows Perplexity as unavailable/not implemented; the provider is removed from the default-providers set until it ships.

### Implementation Tasks
- [ ] **[P07-T06]** Introduce a consistent capability/readiness check for providers instead of treating constructor success as operational readiness.
- [ ] **[P07-T07]** Update `providers_command()` to report Perplexity as not implemented.
- [ ] **[P07-T08]** Convert the current `NotImplementedError` path into a user-facing `ThothError` / `ProviderError` with a clear message and suggestion.
- [ ] **[P07-T09]** Review provider help text and descriptions so they do not imply Perplexity is currently usable.
- [ ] **[P07-T10]** Document the temporary single-provider default: update `README.md`, `--help` text, and the inline PRD note under F-15 stating "while Perplexity is pending, default behavior is OpenAI-only."

### Acceptance Criteria
- `thoth providers -- --list` no longer reports Perplexity as `✓ Ready`.
- `thoth "prompt" --provider perplexity ...` fails cleanly with an intentional message.
- No raw `Unexpected error during submission: Perplexity provider not yet implemented` output remains.
- Help text and README reflect OpenAI-only default until Perplexity ships.

---

## Milestone 3: Interactive `/status` Works, With Optional ID

### Test Design
- **[P07-TS06]** — Regression proving `last_operation_id` is stored after a prompt is submitted from interactive mode.
  PRD refs: F-141 (updated for optional ID) / T-INT-13.
- **[P07-TS07]** — Regression proving `/status` (no argument) delegates to the existing status display path for the most recent interactive operation.
  PRD refs: F-141 / T-INT-13.
- **[P07-TS08]** — Regression proving `/status <operation-id>` delegates to the same code path as the top-level `thoth status <ID>` command.
  PRD refs: F-141 / T-INT-13, F-13 / T-CMD-02.
- If full terminal interaction is too expensive, cover this with a focused fixture test around `SlashCommandRegistry` and the interactive submission handoff.

### Implementation Tasks
- [ ] **[P07-T11]** Set `slash_registry.last_operation_id` when a prompt is submitted from interactive mode.
- [ ] **[P07-T12]** Implement `/status` with optional ID argument:
  - No argument → use `last_operation_id` (error if none yet in session).
  - With argument → delegate to the same path as top-level `status <ID>`.
- [ ] **[P07-T13]** Handle async and sync interactive cases consistently.
- [ ] **[P07-T14]** Keep the "No operations run in this session" behavior when `/status` is called with no argument and no prior submission.

### Acceptance Criteria
- After an interactive submission, `/status` (no argument) reports the last operation.
- `/status <id>` works for any existing operation, matching `thoth status <id>`.
- The command uses real checkpoint-backed status output.
- No duplicate status implementation is introduced.

---

## Milestone 4: Documentation and Verification Workflow Match Repo Reality

### Test Design
- **[P07-TS09]** — Doc-level regression checking that no PRD/plan/README/CONTRIBUTING/RELEASE document references the removed `make check`/`make fix`/`make test-check`/`make test-fix`/`make *-all` quality targets. (Simple `grep` assertion in a doc test.)
- **[P07-TS10]** — Doc-level regression checking the PRD's infra requirements (F-152..F-165) reference only `just` targets that exist in `justfile`.

### Implementation Tasks
- [ ] **[P07-T15]** Update `planning/thoth.prd.v24.md`:
  - Rewrite F-152..F-154 to describe the existing `just` quality targets (`just lint`, `just format`, `just typecheck`, `just check`, `just fix`, `just test-lint`, `just test-format`, `just test-typecheck`, `just test-check` if present, `just test-fix`, `just lint-all`, `just format-all`, `just check-all`, `just fix-all`).
  - For F-160–F-165 (venv / UV export): either point to the corresponding `just venv*` recipe or delete the requirement if no equivalent exists in `justfile`.
  - Add Status column to §11.5 Providers table; mark Perplexity as `✗ Not implemented`.
  - Demote F-93..F-99 to "Planned" with a Status column.
  - Add note under F-15 documenting temporary OpenAI-only default.
  - Add F-177 (async success contract) with Test ID `T-ASYNC-08`.
  - Update F-141 to support optional operation ID on `/status`; update §10.1 Interactive Mode Commands accordingly.
- [ ] **[P07-T16]** Update `CONTRIBUTING.md` and `RELEASE.md` to use `make env-check` for bootstrap and `just` for all quality commands (no `make check`).
- [ ] **[P07-T17]** Strip plan `make *` quality references (this file) and keep `make env-check` only.
- [ ] **[P07-T18]** Do **not** add new Makefile quality targets. `Makefile` stays scoped to `env-check`/`check-uv`.

### Acceptance Criteria
- No repo doc (plan, PRD, README, CONTRIBUTING, RELEASE, CHANGELOG) references `make check`, `make fix`, `make test-check`, `make test-fix`, or `make *-all` quality targets.
- PRD F-152..F-165 describe only `just` targets that exist in the current `justfile`.
- `make` targets remain: `env-check`, `check-uv`, `help`.

---

## Recommended Order

1. Milestone 1: fix false async success first because it is a core correctness bug.
2. Milestone 2: fix Perplexity readiness next because the CLI currently lies about supported capability.
3. Milestone 3: fix interactive `/status` after async is trustworthy, so the status view reflects real operation state.
4. Milestone 4: clean documentation and verification references once product behavior is corrected.

This ordering reduces rework because Milestone 3 depends on correct operation persistence from Milestone 1.

---

## Test ↔ PRD ID Map

| Plan ID | Description | PRD ID(s) |
|---------|-------------|-----------|
| [P07-TS01] | Async persists checkpoint + provider job | F-10 / T-ASYNC-04, F-67 / T-ASYNC-06, F-177 / T-ASYNC-08 |
| [P07-TS02] | `status <ID>` after async shows provider state | F-13 / T-CMD-02 |
| [P07-TS03] | Async success output contract | F-177 / T-ASYNC-08 |
| [P07-TS04] | `providers -- --list` honest re Perplexity | F-113 / T-PROV-13 |
| [P07-TS05] | `--provider perplexity` fails cleanly | F-22 / T-ERR-01, F-15 |
| [P07-TS06] | `last_operation_id` stored after interactive submission | F-141 / T-INT-13 |
| [P07-TS07] | `/status` default reports last op | F-141 / T-INT-13 |
| [P07-TS08] | `/status <id>` delegates to top-level status | F-141 / T-INT-13, F-13 / T-CMD-02 |
| [P07-TS09] | No legacy `make` quality references in docs | F-152..F-154 |
| [P07-TS10] | PRD infra requirements match existing `just` targets | F-152..F-165 |

---

## Verification Plan

### Targeted During Development
- Run only the new or affected `thoth_test` cases for each task first.
- For OpenAI-specific paths, keep using cassette-backed pytest tests when relevant and avoid live-network dependencies.

### Full Verification Before Completion (matches CLAUDE.md)
1. `make env-check`
2. `just fix`
3. `just check`
4. `./thoth_test -r`
5. `just test-fix`
6. `just test-lint`
7. `just test-typecheck`
8. Re-run `just check`
9. Re-run `./thoth_test -r`

### Additional Spot Checks
- `./thoth "async smoke" --provider mock --api-key-mock dummy --async`
- `./thoth status <operation-id>`
- `./thoth providers -- --list`
- Interactive smoke path for `/status` (no arg and with `<id>`)

---

## Risks and Design Notes

- Async submission must not duplicate submission logic between sync and async paths; factor common submission setup if needed.
- Interactive `/status` should reuse existing checkpoint-backed code, not invent a parallel status implementation.
- The Perplexity fix should avoid creating a future migration burden; prefer a small readiness abstraction over scattered special cases.
- `Makefile` stays bootstrap-only (`env-check`, `check-uv`). Do not reintroduce quality targets on `make`.

---

## Definition of Done

- All four defects are covered by regression tests using the `[P07-TS##]` convention with PRD `T-*` cross-references.
- The new tests fail before implementation and pass afterward.
- The CLI no longer reports false success for async mode, and the F-177 success message contract is tested.
- Provider listing accurately reflects actual capability; default-providers copy updated to OpenAI-only while Perplexity is pending.
- Interactive `/status` works for the last submitted operation and accepts an optional ID.
- PRD, plan, README, CONTRIBUTING, and RELEASE reference only `just` for quality work; `make` keeps `env-check`/`check-uv` only.
- Full repository verification passes using the CLAUDE.md-documented workflow above.
