# P04 — GAP-01 — max_tool_calls safeguard and tool-selection config (v2.6.0)

**References**
- **Trunk:** [PROJECTS.md](../PROJECTS.md)

**Status:** `[x]` Completed (v2.6.0).

**Goal**: Expose `max_tool_calls` and `code_interpreter` as optional OpenAI provider config knobs so users can bound cost/latency and disable the code interpreter for prompt types that don't need it. Values must reach the Responses API request payload.

**Out of Scope**
- GAP-02 (file_search / MCP tools), GAP-03 (model aliases), GAP-04 (SDK floor), GAP-05 (fixture gaps)

### Tests & Tasks
- [x] [P04-TS01] Fixture test: `max_tool_calls` set in provider config → value present in request payload
- [x] [P04-TS02] Fixture test: `code_interpreter = false` in provider config → `code_interpreter` absent from tools array
- [x] [P04-TS03] Fixture test: no config keys → request has no `max_tool_calls` key and `code_interpreter` is included by default
- [x] [P04-T01] Read `max_tool_calls` from `self.config` in `OpenAIProvider.submit()` and conditionally add to `request_params`
- [x] [P04-T02] Read `code_interpreter` bool (default `True`) from `self.config` and conditionally include the tool in `tools` list
- [x] [P04-T03] Update OPENAI-BUGS.md (GAP-01 status → Fixed) and PROJECTS.md

### Automated Verification
- `make check` passes
- `./thoth_test -r -t GAP01 --skip-interactive` → 3/3 pass
- `./thoth_test -r --provider mock --skip-interactive` → no regressions

### Regression Test Status
- [x] GAP01-01 verifies max_tool_calls reaches the request payload
- [x] GAP01-02 verifies code_interpreter=False removes the tool
- [x] GAP01-03 verifies default behavior (no max_tool_calls key, code_interpreter included)
