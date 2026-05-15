# P39 — Pluggy-Based Plugin System for Providers & Commands

Pluggy-based plugin discovery so external packages extend providers and commands.

### Open questions
- Q: What hook specs should we expose? (register provider, register command, configuration hooks?)
- Q: Where does plugin discovery happen — at startup or lazily on first use?
- Q: How do plugin-contributed config keys merge with P33's schema-driven defaults?
- Q: Trust model — how do we handle untrusted third-party plugins?

### Notes
- Design inspiration: Simon Willison's [`llm`](https://github.com/simonw/llm) — Pluggy-based plugin architecture, setuptools entry points, plugin hook groups. Study its hook specs and plugin-discovery patterns when scoping.
- Plugins should be able to hook into doxa-research's configuration (extend schema, add defaults, override resolution) — study how `llm` exposes config to its plugins for inspiration.
- Reuses doxa-research's existing provider registry from [P09](P09-decompose-main-appcontext-di.md) and schema-driven config defaults from [P33](P33-schema-driven-config-defaults.md).

<!-- Idea state. Minimal by convention.
     Promote with `project-refine P39` when ready. -->
