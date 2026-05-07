# P37 — Review starter-profile selection

Review the set of starter profiles shipped by `thoth init`. P33 froze the existing 6 profiles (`daily`, `quick`, `openai_deep`, `all_deep`, `interactive`, `deep_research`) verbatim as seed data so that P33 could stay scoped to typing infrastructure. This project picks up the deferred UX question: are these the right profiles, in the right shape, for first-run users?

### Open questions
- Q: Does `quick` add value distinct from `daily`? Both set `default_mode = "thinking"`; `daily` adds a project name. Is `quick` redundant?
- Q: `openai_deep` vs `all_deep` vs `deep_research` overlap heavily — three profiles for three subtly different deep-research configurations. Is one canonical "deep research" profile + documentation enough?
- Q: Should the starter set bias toward fewer, well-named profiles (one per common workflow) or many, finely-grained ones?
- Q: Does the `interactive` profile need to ship as a starter, or is it discoverable enough through `--mode interactive`?
- Q: Are there workflows we *don't* ship a profile for that we should (e.g. a "research with citations only" profile)?

### Notes
Predecessor: [P33 — Schema-Driven Config Defaults](P33-schema-driven-config-defaults.md). P33 made changing the *content* of starter profiles a one-line edit in `src/thoth/_starter_data.py::STARTER_PROFILES`, so this project is purely a UX/content review — not a refactor.

This is not a typing or infrastructure change. The deliverable is a *decision* on the profile set (potentially: dropping some, renaming some, adding some, changing the example values inside some), backed by user-visible justification.

<!-- Idea state. Minimal by convention.
     Promote with `project-refine P37` when ready. -->
