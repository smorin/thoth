# Project Tracker Conventions

This file tracks planned, active, and completed Thoth work. New projects are added near the top in descending project-number order unless the user gives a specific ordering. Each project should keep test/design tasks (`TS`) ahead of implementation tasks (`T`) so work stays test-driven.

## Quick reference: status glyphs

| Glyph | Meaning                | Reach for…                    |
|-------|------------------------|-------------------------------|
| `[?]` | Idea                   | `project-refine` to scope     |
| `[ ]` | Scoped, not started    | start work; flip to `[~]`     |
| `[~]` | In progress            | continue; check next task     |
| `[x]` | Completed              | leave alone                   |
| `[-]` | Decided not to do      | leave alone                   |
| `[>]` | Proceeded to successor | follow the redirect           |

## Project Summary

Keep this summary list updated whenever a project is added, renamed, completed, dropped, or proceeded to a successor. The detailed project entry remains the source of truth; this summary is a quick navigation index.

- [x] **P21** — [Configuration Profile Resolution & Overlay](projects/P21-configuration-profile-resolution.md)
- [x] **P21b** — [Configuration Profile CRUD Commands (depends on P21)](projects/P21b-configuration-profile-crud.md)
- [x] **P21c** — [Config Filename Standardization (`thoth.config.toml` everywhere)](projects/P21c-config-filename-standardization.md)
- [x] **P22** — [OpenAI — Immediate (Synchronous) Calls — closed: validation passed, 4 minor findings routed to P20, refactor outcome (a) (no refactor)](projects/P22-openai-immediate-sync.md)
- [ ] **P23** — [Perplexity — Immediate (Synchronous) Calls](projects/P23-perplexity-immediate-sync.md)
- [ ] **P24** — [Gemini — Immediate (Synchronous) Calls](projects/P24-gemini-immediate-sync.md)
- [ ] **P25** — [Architecture Review & Cleanup — Immediate Providers](projects/P25-arch-review-immediate-providers.md)
- [ ] **P26** — [OpenAI — Background Deep Research](projects/P26-openai-background-deep-research.md)
- [ ] **P27** — [Perplexity — Background Deep Research](projects/P27-perplexity-background-deep-research.md)
- [ ] **P28** — [Gemini — Background Deep Research](projects/P28-gemini-background-deep-research.md)
- [ ] **P29** — [Architecture Review & Cleanup — Background Deep Research Providers](projects/P29-arch-review-background-deep-research.md)
- [ ] **P30** — [Claude Code Skills Support](projects/P30-claude-code-skills-support.md)
- [ ] **P31** — [Interactive Init Command](projects/P31-interactive-init-command.md)
- [ ] **P32** — [Interactive Prompt Refiner](projects/P32-interactive-prompt-refiner.md)
- [ ] **P33** — [Schema-Driven Config Defaults (typed source for `thoth init` and `ConfigSchema`)](projects/P33-schema-driven-config-defaults.md)
- [ ] **P20** — [Extended Real-API Workflow Coverage — Mirror Mock Contracts](projects/P20-live-api-workflow.md)
- [x] **P18** — [Immediate vs Background — Explicit `kind`, Runtime Mismatch, Path Split, Streaming, Cancel](projects/P18-immediate-vs-background-kind.md)
- [x] **P17** — [thoth-ergonomics-v1 Spec Round-Trip — Annotate Implementation Status](projects/P17-ergonomics-spec-round-trip.md)
- [x] **P16 PR2** — [Remove Legacy Shims, Add resume + ask Subcommands](projects/P16-PR2-remove-legacy-shims.md)
- [x] **P16 PR3** — [Automation Polish — `completion` subcommand + universal `--json`](projects/P16-PR3-automation-polish.md)
- [x] **P16 PR1** — [Click-Native CLI Refactor — Subcommand Migration & Parity Gate](projects/P16-PR1-click-native-cli-refactor.md)
- [x] **P15** — [P14 Bug Fixes — pick-model gating, spinner-progress conflict, prompt-file caps](projects/P15-p14-bug-fixes.md)
- [x] **P14** — [Thoth CLI Ergonomics v1](projects/P14-thoth-cli-ergonomics-v1.md)
- [x] **P13** — [P11 Follow-up — is_background_model overload + shared secrets + regression tests](projects/P13-p11-followup-is-background-model.md)
- [ ] **P12** — [CLI Mode Editing — `thoth modes` mutations](projects/P12-cli-mode-editing.md)
- [x] **P11** — [`thoth modes` Discovery Command](projects/P11-thoth-modes-discovery.md)
- [x] **P10** — [Config Subcommand + XDG Layout](projects/P10-config-subcommand-xdg.md)
- [x] **P09** — [Decompose __main__.py + AppContext DI + Provider Registry](projects/P09-decompose-main-appcontext-di.md)
- [x] **P08** — [Typed Exceptions, Unified API Key Resolution, Drop Legacy Config Shim](projects/P08-typed-exceptions-api-key-resolution.md)
- [x] **P06** — [Hybrid Transient/Permanent Error Handling with Resumable Recovery](projects/P06-hybrid-error-handling-resumable.md)
- [x] **P05** — [VCR Cassette Replay Tests](projects/P05-vcr-cassette-replay-tests.md)
- [x] **P03** — [Fix BUG-03 OpenAI Poll Interval Scheduling](projects/P03-bug-03-openai-poll-interval.md)
- [x] **P02** — [Fix BUG-01 OpenAI Background Status Handling](projects/P02-bug-01-openai-background-status.md)
- [x] **P04** — [GAP-01 — max_tool_calls safeguard and tool-selection config](projects/P04-gap-01-max-tool-calls.md)
- [x] **P01** — [Developer Tooling & Automation](projects/P01-developer-tooling.md)

## Project References

Every project that has supporting material must list those references near the beginning of its project entry, before scope and tasks. References can include Superpowers specs/plans, planning docs, research docs, audits, external documentation, or any other source document used to define the work.

Use this shape:

```markdown
**References**
- **Spec:** `docs/superpowers/specs/...`
- **Plan:** `docs/superpowers/plans/...`
- **Research:** `research/...`
- **Audit:** `planning/...`
- **External:** https://...
```

Existing projects may use older labels such as `**Primary spec**`, `**Plan**`, or `**Research basis**`; when editing those entries, prefer normalizing them to the `**References**` block.

## Task ID Key

- `P##` — Project number, for example `P21`
- `P##-TS##` — Test/design task for that project
- `P##-T##` — Implementation, documentation, or verification task for that project
- Suffix letters such as `P21-T09a` — inserted follow-up task that preserves existing numbering

## Usage Rules

- Keep each project entry self-contained: goal, references, scope, tasks, and verification.
- Planning tasks may be checked when the plan/spec exists; implementation tasks stay unchecked until the code or docs they describe have actually landed.
- Mark checkboxes as work lands.
- When adding a new project, preserve the order requested by the user, then adapt numbering to the current file.

---

