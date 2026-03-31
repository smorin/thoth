# OpenAI Provider Bugs and Research-Driven Gaps

This document tracks defects and near-term OpenAI provider improvements discovered by reviewing the current implementation against the deep-research research packet and the official OpenAI documentation. It is intentionally limited to the OpenAI provider so the issues, checklists, and fix plans stay actionable.

## Sources

- Code under review: [`src/thoth/__main__.py`](src/thoth/__main__.py)
- Research packet: [`research/openai-deep-research-api.v1.md`](research/openai-deep-research-api.v1.md)
- Repo references: [`planning/references.md`](planning/references.md)
- Current test coverage: [`thoth_test`](thoth_test)
- Official OpenAI deep research guide: <https://developers.openai.com/api/docs/guides/deep-research>
- Official OpenAI cookbook example: <https://cookbook.openai.com/examples/deep_research_api/introduction_to_deep_research_api>
- Official OpenAI models list reference: <https://platform.openai.com/docs/api-reference/models/list>

## Legend

- `Phase 1`: Confirmed bugs
- `Phase 2`: High-confidence gaps and follow-up improvements
- `Impact`: `High`, `Medium`, `Low`
- `Type`: `Reliability`, `Bug Fix`, `Research Update`, `Testing`, `Documentation`, `Cost Control`, `Versioning`

## Phase 1: Confirmed Bugs

### BUG-01 Background status handling is incorrect

- `Status`: Open
- `Impact`: High
- `Type`: Reliability, Bug Fix, Research Update
- `Summary`: The provider does not map the documented background response lifecycle exactly. `failed`, `incomplete`, and `cancelled` are not handled explicitly, and unexpected retrieve behavior can be treated as success instead of a terminal non-success state.

**Evidence**

- Code evidence:
  - [`src/thoth/__main__.py#L2046-L2084`](src/thoth/__main__.py#L2046-L2084)
  - [`src/thoth/__main__.py#L2810-L2843`](src/thoth/__main__.py#L2810-L2843)
- Research evidence:
  - [`research/openai-deep-research-api.v1.md#L281-L288`](research/openai-deep-research-api.v1.md#L281-L288)
  - [`research/openai-deep-research-api.v1.md#L298-L339`](research/openai-deep-research-api.v1.md#L298-L339)
- Official docs:
  - <https://developers.openai.com/api/docs/guides/deep-research>

**Pros**

- Fixing this makes long-running deep-research jobs behave according to the documented API lifecycle.
- It prevents silent success when the API actually returned a non-success terminal state.
- It makes checkpoint state and CLI output more trustworthy during failures.

**Cons**

- The execution loop will need a small state-machine refactor instead of only recognizing `running` and `completed`.
- Existing tests are mostly black-box and will need more fixture-based coverage to keep this stable.

**Final verdict**

This should be fixed first. It is a correctness issue, not just a polish issue, because it affects whether the CLI reports background jobs accurately.

**Checklist**

- [ ] Reproduce `queued`, `failed`, `incomplete`, and `cancelled` response states with mocked responses
- [ ] Stop mapping unknown retrieve states to successful completion
- [ ] Stop treating retrieve exceptions as successful completion unless a completed cached response already exists
- [ ] Propagate terminal failure details into operation state and CLI output
- [ ] Add regression coverage for every documented terminal state

**Fix plan**

Update `OpenAIProvider.check_status()` to map the documented status values exactly. Then update the research execution loop so `failed`, `incomplete`, and `cancelled` are treated as terminal non-success states with explicit error handling instead of being ignored or effectively treated as success.

### BUG-02 Final output parser drops citations and is schema-fragile

- `Status`: Open
- `Impact`: High
- `Type`: Reliability, Bug Fix, Research Update
- `Summary`: The current result parser extracts text loosely from `response.output`, but it does not preserve citations from `output_text.annotations`. It also stringifies reasoning summary objects and can fall back to debug dumps in user-facing output.

**Evidence**

- Code evidence:
  - [`src/thoth/__main__.py#L2086-L2188`](src/thoth/__main__.py#L2086-L2188)
  - [`src/thoth/__main__.py#L1541-L1591`](src/thoth/__main__.py#L1541-L1591)
- Research evidence:
  - [`research/openai-deep-research-api.v1.md#L185-L192`](research/openai-deep-research-api.v1.md#L185-L192)
  - [`research/openai-deep-research-api.v1.md#L201-L279`](research/openai-deep-research-api.v1.md#L201-L279)
- Official docs:
  - <https://developers.openai.com/api/docs/guides/deep-research>

**Pros**

- Preserves the main source attribution feature users expect from deep research.
- Makes the saved Markdown output align with the system prompt that asks for citations.
- Reduces brittle parsing behavior if the response object shape shifts slightly inside the documented schema.

**Cons**

- Requires choosing and documenting a stable Markdown representation for sources.
- Adds a bit more structured parsing code instead of relying on permissive fallback extraction.

**Final verdict**

This should also be fixed in the first pass. Losing citations materially reduces the value of deep-research output and makes the provider less faithful to the documented response format.

**Checklist**

- [ ] Parse the final `message` item using the documented `output_text` plus `annotations` shape
- [ ] Preserve citation URLs and titles in saved output
- [ ] Normalize reasoning summaries by extracting `.text` instead of stringifying whole objects
- [ ] Remove or sharply limit debug-dump fallbacks in normal output paths
- [ ] Add fixture-based tests for citations and reasoning summary extraction

**Fix plan**

Refactor `get_result()` so it reads the final assistant report from the documented `message` content shape, captures `annotations`, and returns a structured result or a normalized content string plus citations. Then update the Markdown writer so citations are preserved in a stable `Sources` section and reasoning summaries render as plain text instead of object dumps.

### BUG-03 Polling loop ignores configured poll interval and over-polls

- `Status`: Open
- `Impact`: Medium
- `Type`: Reliability, Bug Fix
- `Summary`: The progress UI shows a configurable poll interval, but the loop sleeps in one-second increments and calls `check_status()` every pass. That means the CLI effectively polls once per second regardless of the configured interval.

**Evidence**

- Code evidence:
  - [`src/thoth/__main__.py#L2801-L2805`](src/thoth/__main__.py#L2801-L2805)
  - [`src/thoth/__main__.py#L2813-L2820`](src/thoth/__main__.py#L2813-L2820)
  - [`src/thoth/__main__.py#L2856-L2859`](src/thoth/__main__.py#L2856-L2859)
- Research evidence:
  - [`research/openai-deep-research-api.v1.md#L298-L339`](research/openai-deep-research-api.v1.md#L298-L339)
- Official docs:
  - <https://developers.openai.com/api/docs/guides/deep-research>

**Pros**

- Reduces unnecessary polling traffic against long-running background jobs.
- Makes the progress display honest about actual poll cadence.
- Lowers the chance of self-inflicted rate pressure around retrieve calls.

**Cons**

- Users will see fewer progress refreshes unless the UI distinguishes between display refresh and network poll cadence.
- A tighter poll schedule may feel more responsive during short jobs, so this changes perceived behavior.

**Final verdict**

This should be fixed with the Phase 1 bugs. It is less severe than the lifecycle bug, but it is still incorrect behavior and makes the current configuration misleading.

**Checklist**

- [ ] Reproduce current one-second polling behavior
- [ ] Make sleep behavior match configured poll cadence
- [ ] Add lightweight backoff or bounded jitter to reduce burstiness
- [ ] Keep progress text in sync with actual poll timing
- [ ] Add a non-live test for poll scheduling logic

**Fix plan**

Change the polling loop to issue network status checks on the configured interval instead of every second. If the UI still needs frequent redraws, separate display refresh cadence from network polling cadence so only the latter controls `responses.retrieve()`.

## Phase 2: High-Confidence Gaps and Follow-Up Improvements

### GAP-01 No `max_tool_calls` safeguard or tool-selection config

- `Status`: Open
- `Impact`: High
- `Type`: Cost Control, Reliability, Research Update
- `Summary`: The provider hardcodes tool selection for deep-research models and does not pass through `max_tool_calls`, even though the research packet identifies it as the primary control for bounding cost and latency.

**Evidence**

- Code evidence:
  - [`src/thoth/__main__.py#L1910-L1932`](src/thoth/__main__.py#L1910-L1932)
- Research evidence:
  - [`research/openai-deep-research-api.v1.md#L50-L61`](research/openai-deep-research-api.v1.md#L50-L61)
  - [`research/openai-deep-research-api.v1.md#L127-L147`](research/openai-deep-research-api.v1.md#L127-L147)
  - [`research/openai-deep-research-api.v1.md#L404-L410`](research/openai-deep-research-api.v1.md#L404-L410)
  - [`research/openai-deep-research-api.v1.md#L435-L441`](research/openai-deep-research-api.v1.md#L435-L441)
- Official docs:
  - <https://developers.openai.com/api/docs/guides/deep-research>

**Pros**

- Adds the main documented safeguard against runaway tool use, latency, and cost.
- Allows disabling `code_interpreter` for prompt types that do not need it.
- Makes provider behavior easier to tune per mode.

**Cons**

- Introduces more configuration surface and more user-facing documentation burden.
- Poor defaults could make some runs less capable if set too aggressively.

**Final verdict**

This is not a confirmed bug, but it is a strong production gap and should be addressed soon after Phase 1. The research packet treats `max_tool_calls` as a primary operational control.

**Checklist**

- [ ] Add provider config support for `max_tool_calls`
- [ ] Add config support for enabling or disabling `code_interpreter`
- [ ] Document the default cost and latency tradeoff
- [ ] Add tests proving config values reach the request payload

**Fix plan**

Extend the provider configuration schema to support explicit tool configuration and `max_tool_calls`, then pass those values through when constructing the Responses API request. Use safe defaults for deep-research modes and document when to raise or lower the limit.

### GAP-02 No support for file search or MCP tool configuration

- `Status`: Open
- `Impact`: Medium
- `Type`: Research Update, Feature Gap
- `Summary`: The provider only hardcodes web search and code interpreter for deep-research models. It does not expose configuration for `file_search` or `mcp`, even though those are first-class documented deep-research data sources.

**Evidence**

- Code evidence:
  - [`src/thoth/__main__.py#L1910-L1915`](src/thoth/__main__.py#L1910-L1915)
- Research evidence:
  - [`research/openai-deep-research-api.v1.md#L102-L125`](research/openai-deep-research-api.v1.md#L102-L125)
  - [`research/openai-deep-research-api.v1.md#L1293-L1319`](research/openai-deep-research-api.v1.md#L1293-L1319)
- Official docs:
  - <https://developers.openai.com/api/docs/guides/deep-research>

**Pros**

- Unlocks deep research over private or internal data, which is a core documented capability.
- Makes the provider more future-proof than a web-search-only implementation.
- Creates a path to staged workflows where public and private data can be separated deliberately.

**Cons**

- Requires a careful config shape for vector store IDs and MCP servers.
- MCP support needs validation rules, especially `require_approval=never`.

**Final verdict**

This is a feature gap rather than a defect, but it is a meaningful mismatch against the documented deep-research tool surface and should be tracked explicitly.

**Checklist**

- [ ] Define config shape for `file_search` vector store IDs
- [ ] Define config shape for `mcp` tool entries
- [ ] Validate MCP `require_approval=never`
- [ ] Add request-construction tests for both tool types

**Fix plan**

Add provider-level configuration for optional `file_search` and `mcp` tools, validate their inputs, and merge them into the request tool array alongside any optional `code_interpreter` configuration.

### GAP-03 Deep-research modes use rolling aliases instead of pinned snapshots

- `Status`: Open
- `Impact`: Medium
- `Type`: Versioning, Reliability, Research Update
- `Summary`: Built-in modes use alias model names such as `o3-deep-research` and `o4-mini-deep-research`. The research packet recommends pinned dated snapshots for reproducibility in production-oriented integrations.

**Evidence**

- Code evidence:
  - [`src/thoth/__main__.py#L102-L181`](src/thoth/__main__.py#L102-L181)
- Research evidence:
  - [`research/openai-deep-research-api.v1.md#L13-L22`](research/openai-deep-research-api.v1.md#L13-L22)
  - [`research/openai-deep-research-api.v1.md#L563-L576`](research/openai-deep-research-api.v1.md#L563-L576)
- Official docs:
  - <https://developers.openai.com/api/docs/guides/deep-research>

**Pros**

- Improves reproducibility across runs and releases.
- Makes regressions easier to attribute to code changes rather than silent model alias rollovers.
- Creates a clearer operational upgrade story.

**Cons**

- Pinned models require deliberate maintenance when new snapshots ship.
- Aliases are more convenient for always-latest behavior, so this adds a tradeoff the project must document.

**Final verdict**

This should be documented and likely adopted for production-focused modes, but it is a deliberate policy choice rather than an outright bug.

**Checklist**

- [ ] Decide whether defaults should pin to dated snapshots
- [ ] Document alias versus pinned behavior
- [ ] Add a regression note for future model upgrades

**Fix plan**

Pick a default policy for built-in modes. If production reproducibility matters most, change the mode defaults to pinned snapshots and leave aliases available as explicit overrides in config.

### GAP-04 Declared OpenAI SDK minimum is too loose for modern async Responses behavior

- `Status`: Open
- `Impact`: Medium
- `Type`: Reliability, Documentation, Dependency
- `Summary`: The project currently declares `openai>=1.14.0`, while the research packet recommends using a recent SDK because older versions had async Responses issues. The lockfile is current, but published dependency metadata remains permissive.

**Evidence**

- Code evidence:
  - [`pyproject.toml#L27-L36`](pyproject.toml#L27-L36)
  - [`requirements.txt#L25-L40`](requirements.txt#L25-L40)
- Research evidence:
  - [`research/openai-deep-research-api.v1.md#L24-L26`](research/openai-deep-research-api.v1.md#L24-L26)
  - [`research/openai-deep-research-api.v1.md#L451-L476`](research/openai-deep-research-api.v1.md#L451-L476)
- Official docs:
  - <https://developers.openai.com/api/docs/guides/deep-research>

**Pros**

- Reduces the chance that users install an SDK version that technically satisfies the package requirement but behaves poorly with async deep research.
- Aligns published metadata with actual operational expectations.

**Cons**

- Tightening the minimum version can slightly reduce compatibility for older environments.
- Choosing the exact floor requires one clear compatibility decision instead of relying on "latest" alone.

**Final verdict**

This is a dependency and reliability gap that should be fixed, even if the repo itself currently resolves a modern SDK through the lockfile.

**Checklist**

- [ ] Raise the declared package floor or add a runtime version guard
- [ ] Explain why the floor differs from the lockfile version
- [ ] Add a test or startup check for unsupported versions

**Fix plan**

Choose a minimum OpenAI SDK version that is known to support stable async Responses behavior and either enforce it in `pyproject.toml` or fail fast at runtime with a clear message when an older version is installed.

### GAP-05 OpenAI coverage lacks fixture-based parser and lifecycle tests

- `Status`: Open
- `Impact`: Medium
- `Type`: Testing, Reliability
- `Summary`: Existing OpenAI tests are primarily live black-box CLI tests. They do not deterministically cover documented response states, citation parsing, or response-shape handling without the live API.

**Evidence**

- Code evidence:
  - [`thoth_test#L2182-L2314`](thoth_test#L2182-L2314)
- Research evidence:
  - [`research/openai-deep-research-api.v1.md#L197-L279`](research/openai-deep-research-api.v1.md#L197-L279)
  - [`research/openai-deep-research-api.v1.md#L281-L339`](research/openai-deep-research-api.v1.md#L281-L339)
- Official docs:
  - <https://developers.openai.com/api/docs/guides/deep-research>

**Pros**

- Makes lifecycle and parser bugs reproducible without depending on network access or real API behavior.
- Protects the provider against subtle schema regressions.
- Shortens iteration time compared with live deep-research runs.

**Cons**

- Requires introducing fixture or fake-response coverage in addition to the existing black-box suite.
- Adds some maintenance overhead when the SDK shape evolves.

**Final verdict**

This is an important testing gap and should be addressed alongside the Phase 1 fixes so the provider is protected against regressions in the exact areas already identified as weak.

**Checklist**

- [ ] Add non-live fixtures for successful deep-research responses
- [ ] Add non-live fixtures for `failed`, `incomplete`, and `cancelled`
- [ ] Add citation extraction assertions
- [ ] Add polling and lifecycle assertions

**Fix plan**

Keep the existing black-box tests for end-to-end confidence, but add deterministic provider-level fixtures or mocks that exercise the documented response structure and lifecycle without making live API calls.
