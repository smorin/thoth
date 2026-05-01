# P17 — thoth-ergonomics-v1 Spec Round-Trip — Annotate Implementation Status (no code change)

**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)
- **Primary spec:** `docs/superpowers/specs/2026-04-24-thoth-ergonomics-design.md`
- **Implementation plan that records the dropped scope:** `planning/thoth.plan.v9.md:18` — *"❌ Drop v8 Task 6 — `thoth workflow` command. User direction; `thoth modes` already shows kind."*

**Status:** `[x]` Completed (documentation only; no version bump).

**Goal**: Close the documentation round-trip on the `thoth-ergonomics-v1` spec. The spec was never back-linked from `PROJECTS.md`, which silently allowed §3.4 (decided dropped) and §3.7 (already shipped) to look "open" from a `PROJECTS.md`-only audit. After this project, the spec itself carries an `## Implementation status` block citing the project/task IDs (P11, P14, dropped) for each §3 item, so future audits can grep the spec to know it's fully accounted for. **Zero code change** — this is purely a documentation correctness project.

### Spec § → outcome map (the actual deliverable, recorded inline so this project entry is self-contained)

| Spec § | Item | Outcome | Where |
|---|---|---|---|
| 3.1 | `providers` subcommand group | ✅ Shipped | P14-T06 (`v2.13.0`) |
| 3.2 | thothspinner sync-poll progress | ✅ Shipped | P14-T07/T08/T09 (`v2.13.0`) |
| 3.3 | Mode-ladder help reorganization | ✅ Shipped (simplified per v9 plan) | P14-T04 (`v2.13.0`) — `help.py:127` workflow chain string |
| **3.4** | **`thoth workflow` / `thoth guide` command** | **`[~]` Won't fix** — superseded by `thoth modes` (P11) | Decision: `planning/thoth.plan.v9.md:18`. Rationale: `thoth modes` already lists every mode with provider/model/`kind=immediate\|background`/source/description in one table, making a separate workflow-ladder command redundant. Adding `thoth workflow` would duplicate discovery surface. |
| 3.5 | API-key documentation pass + `thoth help auth` | ✅ Shipped | P14-T05 (`v2.13.0`) |
| 3.6 | `--input-file` vs `--auto` clearer help | ✅ Shipped | P14-T03 (`v2.13.0`) — verified in current `--help` |
| 3.7 | `-v` / `--verbose` worked example in help | ✅ Shipped (one-liner form) | P14-T04 (`v2.13.0`) — `help.py:135` (`Debug API issues: thoth deep_research "topic" -v`); test at `tests/test_cli_help.py:29` (`test_help_has_verbose_example`). Per spec line 230 ("documentation follows behavior"), the realized form is a single example line, not the multi-line block originally drafted in spec §3.7. |
| 3.8 | Surface config path on errors | ✅ Shipped | P14-T01/T02 (`v2.13.0`) — `format_config_context()` in `errors.py`; verified live (error message includes "Config file:" and "Env checked:") |
| 3.9 | `--pick-model` interactive flag | ✅ Shipped | P14-T11/T12 (`v2.13.0`); P15 follow-up bug fixes |
| §4 | `is_deep_research_model` shared helper | ✅ Shipped (renamed) | P11 / P13 — became `is_background_mode` / `is_background_model` |
| §4 | `format_config_context` helper | ✅ Shipped | P14-T01 |
| §4 | Help rendering helpers | ✅ Shipped | P14-T04, P14-T05 |

**Net:** 8 of 9 §3 items shipped + 3 of 3 §4 helpers shipped; 1 item (§3.4) explicitly retired with rationale.

**Out of Scope**
- Reviving `thoth workflow` — explicitly retired, do not re-implement without a fresh design decision overriding `planning/thoth.plan.v9.md:18`
- Adding the multi-line `-v` example block from spec §3.7 lines 219–226 — the realized one-line form is sufficient per "doc follows behavior" (spec line 230) and a future verbose-output redesign would invalidate the multi-line example anyway
- Any code change at all — this is a documentation-only project

### Tests & Tasks
- [x] [P17-T01..06] **DROPPED** — `thoth workflow` / `thoth guide` command tasks. Decision: `planning/thoth.plan.v9.md:18` (`thoth modes` already provides discovery). Tasks intentionally numbered to preserve audit trail; do not re-allocate these IDs.
- [x] [P17-T07..08] **SHIPPED in P14-T04** — `-v` example tasks. `help.py:135`, tested at `tests/test_cli_help.py:29`. No follow-up work required.
- [x] [P17-T09] Add an `## Implementation status` block at the top of `docs/superpowers/specs/2026-04-24-thoth-ergonomics-design.md` reproducing the §-outcome map above. Pin each ✅ row to its `Pxx-T##` shipping task; pin §3.4 to its drop decision in `planning/thoth.plan.v9.md:18` and the supersession by P11.
- [x] [P17-T10] Annotate `docs/superpowers/specs/2026-04-24-thoth-ergonomics-design.md:135` (the §3.4 `thoth workflow` heading) with a one-line callout: `> **Status:** Dropped per planning/thoth.plan.v9.md:18 — superseded by 'thoth modes' (P11).` so a reader landing in §3.4 directly sees the decision without scrolling to the top.
- [x] [P17-T11] Verify `planning/project_promote_commands.md:5` and `planning/thoth.plan.v9.md:6` (the only other files that reference this spec) don't need updates — they're plan-side, the spec is the source of truth getting annotated. *Verified: `thoth.plan.v9.md:6` is just a "Spec:" link and v9's own line 18 records the §3.4 drop; `project_promote_commands.md:5` references spec §5 (deferred admin-promote work), not §3.4. No edits required.*

### Automated Verification
- `grep -n "Implementation status" docs/superpowers/specs/2026-04-24-thoth-ergonomics-design.md` → returns line 1-region match
- `grep -n "Dropped per" docs/superpowers/specs/2026-04-24-thoth-ergonomics-design.md` → returns the §3.4 callout line
- No code, no tests, no `just check` impact — `git diff --stat` shows only the spec file changed

### Manual Verification
- Open the spec — top of file lists every §3 item with shipping commit/project, §3.4 explicitly marked dropped with link to v9 plan
- A new contributor grepping `PROJECTS.md` for `2026-04-24-thoth-ergonomics-design.md` lands on this entry and immediately sees §3.4 was dropped (no temptation to start implementing)
- Future spec audits (`grep -L "Implementation status" docs/superpowers/specs/*.md`) reveal which other specs still lack a round-trip annotation
