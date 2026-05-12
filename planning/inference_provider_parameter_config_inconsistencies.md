# Inference Provider Parameter Config Inconsistencies

Sidecar to [inference_provider_parameter_config_matrix.md](inference_provider_parameter_config_matrix.md). The matrix is the desired state; this document tracks current gaps, current inconsistencies, and open design decisions that block a clean implementation.

## ID Scheme

- `GAP-NNN` - desired state requires behavior that is not implemented.
- `INC-NNN` - behavior exists, but differs across providers or layers.
- `DEC-NNN` - a standardization decision entry; the `Status` field records whether it is still proposed, accepted, resolved, or rejected.

IDs are stable and never reused.

## Top-Level Index

| ID | Kind | Title | Description | Status | References |
|---|---|---|---|---|---|
| GAP-001 | gap | Provider request defaults are not normalized | L2/L4 all-provider defaults and L3/L5 per-provider defaults now flow through the shared normalizer. | resolved | matrix section Configuration Layers L2-L5; matrix section Resolution Rules |
| GAP-002 | gap | Mode-generic migration policy is incomplete | A fixed common set now exists, but non-common flat mode keys are silently ignored except for the legacy `max_tool_calls` compatibility path. | accepted | matrix section Configuration Layers L6/L8; DEC-001 |
| GAP-003 | gap | Shared normalized provider parameter object is missing | `ProviderRuntimeConfig` now classifies auth, client, routing, common request, provider request, and extension-bag fields before adapter construction. | resolved | matrix section Resolution Rules; code `src/thoth/providers/parameter_config.py` |
| GAP-004 | gap | Gemini missing from config defaults provider table | The typed defaults provider table now includes Gemini; this stale gap is resolved. | resolved | matrix section Configuration Layers L3; code `src/thoth/config_schema.py` |
| GAP-005 | gap | Gemini timeout override is not applied to the SDK client | Gemini client construction now maps timeout seconds to Google Gen AI `HttpOptions(timeout=...)` milliseconds. | resolved | matrix row `timeout`; code `src/thoth/providers/gemini.py` |
| GAP-006 | gap | Full parameter matrix is not wired through adapters | Several desired matrix parameters have no adapter translation path. | accepted | matrix section Parameter Matrix |
| GAP-007 | gap | L11 clarification bypasses shared provider normalization | Interactive clarification reads OpenAI config directly and constructs `AsyncOpenAI` directly. | accepted | matrix section Configuration Layers L11; DEC-003 |
| GAP-008 | gap | `max_output_tokens` is not normalized across providers | The desired internal token-budget field is not translated to OpenAI, Perplexity, and Gemini consistently. | accepted | matrix row `max_output_tokens`; DEC-002 |
| GAP-009 | gap | `stop_sequences` is not normalized across providers | The desired internal stop-sequence field is not translated to supported provider-native fields consistently. | accepted | matrix row `stop_sequences`; DEC-001 |
| GAP-010 | gap | Gemini `frequency_penalty` is not wired | Gemini supports `frequencyPenalty`, but the Gemini adapter allowlist omits `frequency_penalty`. | accepted | matrix row `frequency_penalty`; code `src/thoth/providers/gemini.py` |
| GAP-011 | gap | Gemini `presence_penalty` is not wired | Gemini supports `presencePenalty`, but the Gemini adapter allowlist omits `presence_penalty`. | accepted | matrix row `presence_penalty`; code `src/thoth/providers/gemini.py` |
| GAP-012 | gap | Gemini `seed` is not wired | Gemini supports `seed`, but the Gemini adapter allowlist omits `seed`. | accepted | matrix row `seed`; code `src/thoth/providers/gemini.py` |
| GAP-013 | gap | Gemini `n` / `candidate_count` is not wired | Gemini supports `candidateCount`, but the adapter does not map internal `n` or provider-native `candidate_count`. | accepted | matrix row `n`; code `src/thoth/providers/gemini.py` |
| GAP-014 | gap | OpenAI `response_format` is not wired | OpenAI Responses supports `text.format`, but the OpenAI adapter does not translate internal `response_format`. | accepted | matrix row `response_format`; code `src/thoth/providers/openai.py` |
| GAP-015 | gap | Gemini `response_format` is not normalized | Gemini supports split structured-output fields, but internal `response_format` is not translated to them. | accepted | matrix row `response_format`; code `src/thoth/providers/gemini.py` |
| GAP-016 | gap | OpenAI `reasoning_effort` is not wired | OpenAI Responses supports `reasoning.effort`, but the OpenAI adapter does not translate internal `reasoning_effort`. | accepted | matrix row `reasoning_effort`; code `src/thoth/providers/openai.py` |
| GAP-017 | gap | Gemini `reasoning_effort` / `thinking_level` is not wired | Gemini supports `thinkingConfig.thinkingLevel`, but the adapter does not map internal `reasoning_effort` or provider-native `thinking_level`. | accepted | matrix row `reasoning_effort`; code `src/thoth/providers/gemini.py` |
| INC-001 | inconsistency | L6/L8 flat mode params are copied but consumed unevenly | Fixed common mode params now route through the shared normalizer and are mirrored into provider namespaces for adapter compatibility. | resolved | matrix section Configuration Layers L6/L8; DEC-001 |
| INC-002 | inconsistency | Root provider defaults behave differently by provider | Root all-provider and per-provider defaults now normalize into equivalent provider request shapes across OpenAI, Perplexity, and Gemini. | resolved | matrix section Configuration Layers L2-L5; matrix section Recognized Field Registry; GAP-001 |
| INC-003 | inconsistency | Provider namespace unknown-key policy diverges | Provider namespace handling now validates recognized keys and requires explicit extension bags for arbitrary passthrough in the normalized path. | resolved | matrix section Resolution Rules; DEC-004 |
| INC-004 | inconsistency | Built-in mode overrides are shallow | Built-in/user/profile mode overlays now deep-merge nested provider namespaces. | resolved | matrix section Resolution Rules |
| INC-005 | inconsistency | Runtime timeout has provider-specific effects | OpenAI, Perplexity, and Gemini now consume normalized timeout during client construction. | resolved | matrix row `timeout`; GAP-005 |
| INC-006 | inconsistency | Runtime provider override can mismatch mode model and namespace | `--provider` can select a provider while retaining the selected mode's model and unrelated provider namespace. | accepted | matrix section Resolution Rules; DEC-005 |
| INC-007 | inconsistency | L11 is OpenAI-only while main providers are multi-provider | Clarification has its own OpenAI Chat Completions path instead of the shared OpenAI/Perplexity/Gemini stack. | accepted | matrix section Configuration Layers L11; DEC-003 |
| INC-008 | inconsistency | Documentation and tests disagree on root provider defaults | Root provider default docs and tests now describe the recognized-field normalizer contract. | resolved | matrix section Configuration Layers L2-L5; matrix section Recognized Field Registry; GAP-001 |
| INC-009 | inconsistency | Perplexity `search_context_size` needs upstream validation | Local built-ins and adapter defaults use `web_search_options.search_context_size`, and current Perplexity Sonar docs validate it as a request option. | accepted | matrix row `search_context_size`; DEC-004 |
| INC-010 | inconsistency | OpenAI `system_prompt` uses developer-role input instead of `instructions` | Desired state names OpenAI `instructions`, while current code sends an equivalent developer-role input message. | accepted | matrix row `system_prompt`; code `src/thoth/providers/openai.py` |
| INC-011 | inconsistency | Perplexity `response_format` differs between sync and async layers | Perplexity sync and async request builders now receive normalized namespaced `response_format`. | resolved | matrix row `response_format`; INC-001 |
| DEC-001 | decision | Define mode flat common params or deprecate flat passthrough | Decide whether flat mode keys are a fixed common set or arbitrary provider passthrough. | accepted | matrix section Configuration Layers L6/L8 |
| DEC-002 | decision | Normalize max token split forms | Decide whether users configure one internal token budget or expose every provider spelling. | accepted | matrix row `max_output_tokens` |
| DEC-003 | decision | L11 clarification integration boundary | Decide whether clarification folds into the provider stack or remains separate while reusing normalization. | accepted | matrix section Configuration Layers L11 |
| DEC-004 | decision | Unknown-key and extension policy | Decide which unknown provider namespace keys pass through, fail validation, or are ignored. | accepted | matrix section Resolution Rules |
| DEC-005 | decision | Provider override mismatch policy | Decide how `--provider` interacts with a mode's provider-specific model and namespace. | accepted | matrix section Resolution Rules |
| DEC-006 | decision | Array merge and unset semantics | Decide array replacement vs append and absence vs explicit-disable semantics. | accepted | matrix section Resolution Rules |
| DEC-007 | decision | Add `[providers.defaults]` all-provider defaults | Decide whether to add `[providers.defaults]` and profile-scoped provider defaults as inherited all-provider layers. | accepted | matrix section Overview; matrix section Recognized Field Registry |
| DEC-008 | decision | Matrix cell target type | Decide whether the matrix should mix request payload keys with client/runtime controls. | accepted | matrix section Parameter Matrix |
| DEC-009 | decision | Canonical provider endpoint scope | Decide which endpoint surface each provider column represents when a provider has multiple APIs. | accepted | matrix section Parameter Matrix |
| DEC-010 | decision | SDK key casing vs REST key casing | Decide whether provider cells use Python SDK key names, REST JSON names, or both. | accepted | matrix section Parameter Matrix |

## Gaps (`GAP-`)

A gap means the desired-state contract requires behavior that the current implementation does not provide. Triage by deciding whether to implement the missing behavior, narrow the desired contract, or split the work into provider-specific follow-ups.

| ID | Title | Description | Status | References |
|---|---|---|---|---|
| GAP-001 | Provider request defaults are not normalized | L2/L4 all-provider defaults and L3/L5 per-provider defaults now flow through the shared normalizer. | resolved | matrix section Configuration Layers L2-L5 |
| GAP-002 | Mode-generic migration policy is incomplete | A fixed common set now exists, but non-common flat mode keys are silently ignored except for the legacy `max_tool_calls` compatibility path. | accepted | matrix section Configuration Layers L6/L8 |
| GAP-003 | Shared normalized provider parameter object is missing | `ProviderRuntimeConfig` now classifies provider parameters before adapter construction. | resolved | matrix section Resolution Rules |
| GAP-004 | Gemini missing from config defaults provider table | The typed defaults provider table now includes Gemini; this stale gap is resolved. | resolved | matrix section Configuration Layers L3 |
| GAP-005 | Gemini timeout override is not applied to the SDK client | Gemini now maps timeout seconds to Google Gen AI `HttpOptions(timeout=...)` milliseconds. | resolved | matrix row `timeout` |
| GAP-006 | Full parameter matrix is not wired through adapters | Several desired matrix parameters have no adapter translation path. | accepted | matrix section Parameter Matrix |
| GAP-007 | L11 clarification bypasses shared provider normalization | Interactive clarification reads OpenAI config directly and constructs `AsyncOpenAI` directly. | accepted | matrix section Configuration Layers L11 |
| GAP-008 | `max_output_tokens` is not normalized across providers | The desired internal token-budget field is not translated to OpenAI, Perplexity, and Gemini consistently. | accepted | matrix row `max_output_tokens` |
| GAP-009 | `stop_sequences` is not normalized across providers | The desired internal stop-sequence field is not translated to supported provider-native fields consistently. | accepted | matrix row `stop_sequences` |
| GAP-010 | Gemini `frequency_penalty` is not wired | Gemini supports `frequencyPenalty`, but the Gemini adapter allowlist omits `frequency_penalty`. | accepted | matrix row `frequency_penalty` |
| GAP-011 | Gemini `presence_penalty` is not wired | Gemini supports `presencePenalty`, but the Gemini adapter allowlist omits `presence_penalty`. | accepted | matrix row `presence_penalty` |
| GAP-012 | Gemini `seed` is not wired | Gemini supports `seed`, but the Gemini adapter allowlist omits `seed`. | accepted | matrix row `seed` |
| GAP-013 | Gemini `n` / `candidate_count` is not wired | Gemini supports `candidateCount`, but the adapter does not map internal `n` or provider-native `candidate_count`. | accepted | matrix row `n` |
| GAP-014 | OpenAI `response_format` is not wired | OpenAI Responses supports `text.format`, but the OpenAI adapter does not translate internal `response_format`. | accepted | matrix row `response_format` |
| GAP-015 | Gemini `response_format` is not normalized | Gemini supports split structured-output fields, but internal `response_format` is not translated to them. | accepted | matrix row `response_format` |
| GAP-016 | OpenAI `reasoning_effort` is not wired | OpenAI Responses supports `reasoning.effort`, but the OpenAI adapter does not translate internal `reasoning_effort`. | accepted | matrix row `reasoning_effort` |
| GAP-017 | Gemini `reasoning_effort` / `thinking_level` is not wired | Gemini supports `thinkingConfig.thinkingLevel`, but the adapter does not map internal `reasoning_effort` or provider-native `thinking_level`. | accepted | matrix row `reasoning_effort` |

<a id="gap-001"></a>

### GAP-001 - Provider Request Defaults Are Not Normalized

- **Description:** L2/L4 all-provider defaults and L3/L5 per-provider defaults now flow through the shared normalizer.
- **Kind:** gap
- **Status:** resolved
- **Layers affected:** L2, L3, L4, L5, L7, L9
- **Providers affected:** OpenAI, Perplexity, Gemini
- **Source:** `src/thoth/providers/parameter_config.py:297-339`; `src/thoth/providers/__init__.py:195-204`; `tests/test_provider_parameter_normalization.py:14-53`; `tests/test_provider_config.py:606-789`
- **Context:** This was the implementation follow-through for accepted `INC-002`, `INC-008`, and `DEC-007`: root all-provider defaults and per-provider defaults are accepted config layers, and runtime request-default normalization now exists.
- **Detail:** `create_provider()` now builds a `ProviderRuntimeConfig` before API-key resolution. The normalizer applies `[providers.defaults]`, `[providers.NAME]`, `[profiles.NAME.providers.defaults]`, and `[profiles.NAME.providers.PROVIDER]` in precedence order, classifies recognized fields into auth/client/routing/common/provider-native sections, and then emits a compatibility config shape for the current adapters.
- **Recommendation:** Keep future changes on the shared normalizer path rather than adding provider-specific default routing in adapters.
- **Resolution choices:** Option B accepted and implemented: resolve `GAP-001` through shared `[providers.defaults]` plus `[providers.NAME]` request-default normalization. Rejected: Option A, split the gap into separate provider-specific entries; Option C, narrow desired state to auth/client-only root provider tables.
- **References:** matrix section Configuration Layers L2-L5; matrix section Resolution Rules; `planning/p24-providers-root-namespace-investigation.v1.md`; `tests/test_provider_config.py::test_root_providers_namespace_*`
- **Related:** INC-002, INC-008, DEC-004

<a id="gap-002"></a>

### GAP-002 - Mode-Generic Migration Policy Is Incomplete

- **Description:** A fixed common set now exists, but non-common flat mode keys are silently ignored except for the legacy `max_tool_calls` compatibility path.
- **Kind:** gap
- **Status:** accepted
- **Layers affected:** L6, L8
- **Providers affected:** all
- **Source:** `src/thoth/providers/parameter_config.py:19-30`; `src/thoth/providers/parameter_config.py:208-227`; `tests/test_provider_parameter_normalization.py:230-287`
- **Context:** This is the remaining implementation follow-through after `INC-001` resolution: L6/L8 now route recognized provider-neutral common inference fields through the normalizer, but the user-facing migration behavior for old arbitrary flat keys is not complete.
- **Detail:** The normalizer no longer treats every non-metadata flat mode key as arbitrary provider passthrough. Recognized common fields are routed; auth/client/unknown flat mode keys are ignored; the legacy flat OpenAI `max_tool_calls` path is preserved explicitly. The missing piece is a deliberate migration surface, such as warnings or config validation errors, for flat non-common provider-native fields that users may still have in existing mode config.
- **Recommendation:** Add a migration diagnostic for non-common flat mode keys. Prefer warning before hard failure for previously accepted configs, and move provider-native values into L7/L9 namespaces or explicit extension bags.
- **Resolution choices:** Option A accepted: keep `GAP-002` as the implementation backlog for migration diagnostics after replacing broad arbitrary L6/L8 passthrough with a fixed common set. Rejected: Option B, silently ignore old arbitrary keys permanently; Option C, hard-fail every non-common flat key immediately.
- **References:** matrix section Configuration Layers L6/L8; matrix section Parameter Matrix; DEC-001
- **Related:** INC-001, DEC-001

<a id="gap-003"></a>

### GAP-003 - Shared Normalized Provider Parameter Object Is Missing

- **Description:** `ProviderRuntimeConfig` now classifies auth, client, routing, common request, provider request, and extension-bag fields before adapter construction.
- **Kind:** gap
- **Status:** resolved
- **Layers affected:** L0-L10
- **Providers affected:** OpenAI, Perplexity, Gemini
- **Source:** `src/thoth/providers/parameter_config.py:93-136`; `src/thoth/providers/parameter_config.py:280-369`; `src/thoth/providers/__init__.py:195-204`; `tests/test_provider_parameter_normalization.py:14-555`
- **Context:** This was the central implementation gap behind accepted `GAP-001`, `GAP-002`, and `INC-003`: the desired layer model needed one shared normalization result rather than three adapter-specific interpretations of a mutable dict.
- **Detail:** `ProviderRuntimeConfig` now carries explicit sections for auth, client controls, routing, framework-owned values, common request fields, provider-native request fields, extension bags, and source metadata. `create_provider()` invokes the normalizer once and passes its compatibility output into the existing adapters.
- **Recommendation:** The remaining adapter work should translate `ProviderRuntimeConfig` directly into SDK payloads over time; the compatibility wrapper keeps the current adapter contracts stable.
- **Resolution choices:** Option A accepted and implemented: build one shared normalized provider parameter object. Rejected: Option B, split into adapter-specific cleanup tasks; Option C, keep plain dict mutation and add helper functions around the existing shape.
- **References:** matrix section Resolution Rules; matrix section Worked Examples; `src/thoth/providers/__init__.py`
- **Related:** GAP-001, INC-001, INC-003

<a id="gap-004"></a>

### GAP-004 - Gemini Missing From Config Defaults Provider Table

- **Description:** The typed defaults provider table now includes Gemini; this stale gap is resolved.
- **Kind:** gap
- **Status:** resolved
- **Layers affected:** L3
- **Providers affected:** Gemini
- **Source:** `src/thoth/config_schema.py:256-269`; `src/thoth/config_schema.py:513-514`; `src/thoth/config.py:313-324`
- **Context:** This gap was valid against an older defaults implementation, but the current worktree derives defaults from the typed schema.
- **Detail:** `ProvidersConfig` now declares `gemini: GeminiConfig = StarterField(default_factory=lambda: GeminiConfig(api_key="${GEMINI_API_KEY}"))`, and `ConfigSchema.get_defaults()` delegates to `default_config_dict()`. Desired state still requires every supported provider to appear in root provider defaults; current code now satisfies that requirement for Gemini.
- **Resolution choices:** Option A accepted: mark `GAP-004` resolved as stale/currently implemented, with source references updated to the typed schema. Rejected: Option B, keep it open pending a new regression test; Option C, replace it with a narrower docs-only gap.
- **References:** matrix section Configuration Layers L3; matrix section Worked Examples A-B; `src/thoth/config.py`
- **Related:** INC-008

<a id="gap-005"></a>

### GAP-005 - Gemini Timeout Override Is Not Applied To The SDK Client

- **Description:** Gemini client construction now maps timeout seconds to Google Gen AI `HttpOptions(timeout=...)` milliseconds.
- **Kind:** gap
- **Status:** resolved
- **Layers affected:** L2, L3, L4, L5, L10
- **Providers affected:** Gemini
- **Source:** `src/thoth/providers/parameter_config.py:365-367`; `src/thoth/providers/gemini.py:222-226`; `tests/test_provider_gemini.py`; `tests/test_provider_parameter_normalization.py:136-155`
- **Context:** Accepted `INC-005` makes `timeout` a provider client/runtime control for every supported provider, including root provider config and runtime overrides.
- **Detail:** `build_provider_runtime_config()` applies runtime timeout overrides into `client.timeout`, and `GeminiProvider.__init__()` now constructs `genai.Client(api_key=..., http_options=types.HttpOptions(timeout=int(seconds * 1000)))`.
- **Recommendation:** Keep `timeout` as a client-control field, not a request payload parameter. Retain constructor-level tests so SDK mock coverage catches regressions without live Gemini calls.
- **Resolution choices:** Option B accepted and implemented: validate the Google SDK timeout hook, then wire Gemini timeout through that hook. Rejected: Option A, treat it as a single direct wiring task without validation; Option C, mark Gemini timeout unsupported and narrow the matrix/runtime contract.
- **References:** matrix row `timeout`; matrix section Resolution Rules
- **Related:** INC-005

<a id="gap-006"></a>

### GAP-006 - Full Parameter Matrix Is Not Wired Through Adapters

- **Description:** Several desired matrix parameters have no adapter translation path.
- **Kind:** gap
- **Status:** accepted
- **Layers affected:** L2-L10
- **Providers affected:** OpenAI, Perplexity, Gemini
- **Source:** `src/thoth/providers/openai.py:55-64`; `src/thoth/providers/perplexity.py:388-394`; `src/thoth/providers/gemini.py:58-76`
- **Context:** This is an umbrella gap for matrix-to-adapter parity. It is intentionally broader than a single implementation task because each parameter family has different provider support, validation rules, and test shape.
- **Detail:** Current allowlists and explicit read sites cover a small subset: OpenAI handles fields such as `temperature` and `max_tool_calls` but does not yet wire Responses-supported `top_p`; Perplexity handles `max_tokens`, `temperature`, `top_p`, `stop`, and `response_format` plus extra-body pass-through; Gemini handles a larger generation config allowlist. Desired rows such as `frequency_penalty`, `presence_penalty`, `seed`, `n`, `logprobs`, `top_logprobs`, `user`, `service_tier`, and unified `max_output_tokens` need explicit adapter decisions.
- **Recommendation:** Keep this as the umbrella tracking item, but split actionable implementation into parameter-family gaps. Each child gap should define provider support, unsupported-provider behavior, normalized key mapping, and tests.
- **Resolution choices:** Option B accepted: split `GAP-006` into parameter-family gaps and keep this entry as an umbrella. Rejected: Option A, keep one broad implementation task for every matrix row; Option C, narrow the matrix to only fields already wired today.
- **References:** matrix section Parameter Matrix; matrix section Per-Parameter Detail
- **Related:** GAP-008, GAP-009, GAP-010, GAP-011, GAP-012, GAP-013, GAP-014, GAP-015, GAP-016, GAP-017, DEC-002, DEC-004

<a id="gap-007"></a>

### GAP-007 - L11 Clarification Bypasses Shared Provider Normalization

- **Description:** Interactive clarification reads OpenAI config directly and constructs `AsyncOpenAI` directly.
- **Kind:** gap
- **Status:** accepted
- **Layers affected:** L11
- **Providers affected:** OpenAI now; all if L11 becomes provider-selectable
- **Source:** `src/thoth/config.py:345-365`; `src/thoth/interactive.py:857-909`
- **Context:** This is the implementation follow-through for accepted `INC-007`: L11 stays a separate clarification UX layer, but its model call should use shared provider normalization.
- **Detail:** The clarification subsystem has its own config subtree and direct OpenAI Chat Completions call. It does not use `create_provider()`, provider namespace normalization, provider API key resolution, or the multi-provider adapter surface.
- **Recommendation:** Keep this as the accepted backlog item for routing L11 clarification model calls through shared provider normalization while leaving UI-only clarification controls outside provider normalization.
- **Resolution choices:** Option A accepted: keep `GAP-007` as the implementation backlog for routing L11 clarification model calls through shared provider normalization. Rejected: Option B, split interactive and CLI clarification into separate gaps now; Option C, keep clarification OpenAI-only and narrow the desired-state contract.
- **References:** matrix section Configuration Layers L11; matrix section Resolution Rules; DEC-003
- **Related:** INC-007, DEC-003

<a id="gap-008"></a>

### GAP-008 - `max_output_tokens` Is Not Normalized Across Providers

- **Description:** The desired internal token-budget field is not translated to OpenAI, Perplexity, and Gemini consistently.
- **Kind:** gap
- **Status:** accepted
- **Layers affected:** L2, L3, L4, L5, L6, L7, L8, L9
- **Providers affected:** OpenAI, Perplexity, Gemini
- **Source:** `src/thoth/providers/openai.py:55-64`; `src/thoth/providers/perplexity.py:388-394`; `src/thoth/providers/perplexity.py:520-528`; `src/thoth/providers/perplexity.py:591-596`; `src/thoth/providers/gemini.py:58-76`
- **Context:** `max_output_tokens` is the desired internal name for output-token budget, but provider APIs use split forms. OpenAI Responses and Gemini use `max_output_tokens`; Perplexity uses `max_tokens`.
- **Detail:** The shared normalizer now carries common/default `max_output_tokens` into the selected provider namespace for adapter compatibility. OpenAI still does not wire `max_output_tokens` into Responses request params, and Perplexity still requires native `max_tokens` because there is no provider translation from internal `max_output_tokens` to `max_tokens`. Gemini already consumes namespaced `max_output_tokens` through `GenerateContentConfig`.
- **Recommendation:** Resolve DEC-002 by using `max_output_tokens` everywhere outside provider namespaces. Adapter normalization should emit OpenAI `max_output_tokens`, Perplexity `max_tokens` / `request.max_tokens`, and Gemini `config.max_output_tokens`. Provider-native aliases may remain in provider namespaces as compatibility inputs.
- **Resolution choices:** Option A accepted: keep `GAP-008` as the parameter-family backlog for normalizing `max_output_tokens` across providers. Rejected: Option B, fold this back into umbrella `GAP-006`; Option C, expose only provider-native names and remove `max_output_tokens` as a common internal field.
- **References:** matrix row `max_output_tokens`; DEC-002; matrix section Configuration Layers L2-L9; `src/thoth/providers/__init__.py`
- **Related:** GAP-003, GAP-006, DEC-002, INC-001

<a id="gap-009"></a>

### GAP-009 - `stop_sequences` Is Not Normalized Across Providers

- **Description:** The desired internal stop-sequence field is not translated to supported provider-native fields consistently.
- **Kind:** gap
- **Status:** accepted
- **Layers affected:** L6, L7, L8, L9
- **Providers affected:** Perplexity, Gemini
- **Source:** `src/thoth/providers/openai.py:55-64`; `src/thoth/providers/perplexity.py:388-394`; `src/thoth/providers/perplexity.py:520-528`; `src/thoth/providers/perplexity.py:591-596`; `src/thoth/providers/gemini.py:58-76`
- **Context:** OpenAI Responses does not expose `stop`/`stop_sequences` on the canonical surface, but Perplexity and Gemini both support stop sequences using different native names.
- **Detail:** The shared normalizer now carries common/default `stop_sequences` into the selected provider namespace for adapter compatibility. Perplexity still requires native `stop` because there is no provider translation from internal `stop_sequences` to `stop`. Gemini already consumes namespaced `stop_sequences` through `GenerateContentConfig`. OpenAI should continue to report unsupported for the Responses surface.
- **Recommendation:** Keep `stop_sequences` in the fixed L6/L8 common set only for providers that support it. Adapter normalization should emit Perplexity `stop` / `request.stop`, Gemini `config.stop_sequences`, and omit or reject the field for OpenAI Responses with a clear compatibility rule.
- **Resolution choices:** Option A accepted: keep `GAP-009` as the parameter-family backlog for `stop_sequences` normalization, including explicit unsupported behavior for OpenAI Responses. Rejected: Option B, remove `stop_sequences` from the fixed L6/L8 set; Option C, keep only provider-native stop fields.
- **References:** matrix row `stop_sequences`; DEC-001; matrix section Configuration Layers L6/L8; `src/thoth/providers/__init__.py`
- **Related:** GAP-003, GAP-006, INC-001

<a id="gap-010"></a>

### GAP-010 - Gemini `frequency_penalty` Is Not Wired

- **Description:** Gemini supports `frequencyPenalty`, but the Gemini adapter allowlist omits `frequency_penalty`.
- **Kind:** gap
- **Status:** accepted
- **Layers affected:** L7, L9
- **Providers affected:** Gemini
- **Source:** `src/thoth/providers/gemini.py:58-76`; `src/thoth/providers/gemini.py:313-320`
- **Context:** The desired matrix exposes Gemini `config.frequency_penalty` because the Google GenerateContent surface documents `frequencyPenalty`.
- **Detail:** `_DIRECT_SDK_KEYS_GEMINI` does not include `frequency_penalty`, so `[modes.X.gemini].frequency_penalty` is silently ignored by `_build_generate_content_config()`. OpenAI Responses and Perplexity Sonar do not expose this key on the canonical surfaces, so this is Gemini-specific adapter work rather than a cross-provider normalization issue.
- **Recommendation:** Add `frequency_penalty` to the Gemini direct SDK key allowlist, with tests that prove it reaches `GenerateContentConfig`. Keep matrix notes that model support may vary and rely on provider errors for unsupported model/config combinations.
- **Resolution choices:** Option A accepted: keep `GAP-010` as the Gemini-specific backlog to wire `frequency_penalty`. Rejected: Option B, merge it with `GAP-011`; Option C, remove `frequency_penalty` from the desired matrix until live model support is proven.
- **References:** matrix row `frequency_penalty`; Gemini GenerateContent reference; `src/thoth/providers/gemini.py`
- **Related:** GAP-006, DEC-004

<a id="gap-011"></a>

### GAP-011 - Gemini `presence_penalty` Is Not Wired

- **Description:** Gemini supports `presencePenalty`, but the Gemini adapter allowlist omits `presence_penalty`.
- **Kind:** gap
- **Status:** accepted
- **Layers affected:** L7, L9
- **Providers affected:** Gemini
- **Source:** `src/thoth/providers/gemini.py:58-76`; `src/thoth/providers/gemini.py:313-320`
- **Context:** The desired matrix exposes Gemini `config.presence_penalty` because the Google GenerateContent surface documents `presencePenalty`.
- **Detail:** `_DIRECT_SDK_KEYS_GEMINI` does not include `presence_penalty`, so `[modes.X.gemini].presence_penalty` is silently ignored by `_build_generate_content_config()`. OpenAI Responses and Perplexity Sonar do not expose this key on the canonical surfaces, so this is Gemini-specific adapter work rather than a cross-provider normalization issue.
- **Recommendation:** Add `presence_penalty` to the Gemini direct SDK key allowlist, with tests that prove it reaches `GenerateContentConfig`. Keep matrix notes that model support may vary and rely on provider errors for unsupported model/config combinations.
- **Resolution choices:** Accepted: keep `GAP-011` as the Gemini-specific backlog to wire `presence_penalty`, mirroring the accepted `GAP-010` penalty-field direction.
- **References:** matrix row `presence_penalty`; Gemini GenerateContent reference; `src/thoth/providers/gemini.py`
- **Related:** GAP-006, DEC-004

<a id="gap-012"></a>

### GAP-012 - Gemini `seed` Is Not Wired

- **Description:** Gemini supports `seed`, but the Gemini adapter allowlist omits `seed`.
- **Kind:** gap
- **Status:** accepted
- **Layers affected:** L7, L9
- **Providers affected:** Gemini
- **Source:** `src/thoth/providers/gemini.py:58-76`; `src/thoth/providers/gemini.py:313-320`
- **Context:** The desired matrix exposes Gemini `config.seed` because the Google GenerateContent surface documents `seed`.
- **Detail:** `_DIRECT_SDK_KEYS_GEMINI` does not include `seed`, so `[modes.X.gemini].seed` is silently ignored by `_build_generate_content_config()`. OpenAI Responses and Perplexity Sonar do not expose this key on the canonical surfaces, so this is Gemini-specific adapter work.
- **Recommendation:** Add `seed` to the Gemini direct SDK key allowlist, with tests that prove it reaches `GenerateContentConfig`. Keep matrix notes that determinism is best-effort and provider/model behavior may vary.
- **Resolution choices:** Accepted: keep `GAP-012` as the Gemini-specific backlog to wire `seed` through `GenerateContentConfig`, with best-effort determinism documented.
- **References:** matrix row `seed`; Gemini GenerateContent reference; `src/thoth/providers/gemini.py`
- **Related:** GAP-006, DEC-004

<a id="gap-013"></a>

### GAP-013 - Gemini `n` / `candidate_count` Is Not Wired

- **Description:** Gemini supports `candidateCount`, but the adapter does not map internal `n` or provider-native `candidate_count`.
- **Kind:** gap
- **Status:** accepted
- **Layers affected:** L6, L7, L8, L9
- **Providers affected:** Gemini
- **Source:** `src/thoth/providers/gemini.py:58-76`; `src/thoth/providers/gemini.py:313-320`
- **Context:** The desired matrix exposes internal `n` as Gemini `config.candidate_count` because the Google GenerateContent surface documents `candidateCount`.
- **Detail:** `_DIRECT_SDK_KEYS_GEMINI` does not include `candidate_count`, and no shared normalizer maps internal `n` to Gemini's SDK field. As a result, common `[modes.X] n = 2`, profile-scoped common `n`, and provider-native `[modes.X.gemini] candidate_count = 2` are not routed to `GenerateContentConfig`.
- **Recommendation:** Normalize internal `n` to Gemini SDK `candidate_count` and also accept provider-native `candidate_count` inside Gemini namespaces, with tests that prove both paths reach `GenerateContentConfig`.
- **Resolution choices:** Accepted: keep `GAP-013` as the backlog to normalize internal `n` to Gemini `candidate_count` and accept provider-native `candidate_count` in Gemini namespaces.
- **References:** matrix row `n`; Gemini GenerateContent reference; matrix section Configuration Layers L6-L9; `src/thoth/providers/gemini.py`
- **Related:** GAP-003, GAP-006, DEC-001, DEC-004

<a id="gap-014"></a>

### GAP-014 - OpenAI `response_format` Is Not Wired

- **Description:** OpenAI Responses supports `text.format`, but the OpenAI adapter does not translate internal `response_format`.
- **Kind:** gap
- **Status:** accepted
- **Layers affected:** L6, L7, L8, L9
- **Providers affected:** OpenAI
- **Source:** `src/thoth/providers/openai.py:55-64`; `src/thoth/providers/openai.py:359-375`; `src/thoth/providers/openai.py:579-589`
- **Context:** The desired matrix exposes internal `response_format` as OpenAI Responses `text.format`, including JSON mode and JSON-schema structured outputs.
- **Detail:** `_DIRECT_SDK_KEYS_OPENAI` does not include `response_format`, and the request builders never set `text.format`. As a result, common or namespaced `response_format` values do not reach `responses.create()` or `responses.stream()`.
- **Recommendation:** Normalize internal `response_format` to OpenAI `text.format`, with tests for at least text/default, JSON object, and JSON schema shapes.
- **Resolution choices:** Accepted: keep `GAP-014` as the OpenAI-specific backlog to normalize internal `response_format` to Responses `text.format`.
- **References:** matrix row `response_format`; OpenAI Structured Outputs guide; `src/thoth/providers/openai.py`
- **Related:** GAP-003, GAP-006, DEC-004

<a id="gap-015"></a>

### GAP-015 - Gemini `response_format` Is Not Normalized

- **Description:** Gemini supports split structured-output fields, but internal `response_format` is not translated to them.
- **Kind:** gap
- **Status:** accepted
- **Layers affected:** L6, L8
- **Providers affected:** Gemini
- **Source:** `src/thoth/providers/gemini.py:58-76`; `src/thoth/providers/gemini.py:313-320`
- **Context:** The desired matrix exposes internal `response_format` as Gemini `response_mime_type`, `response_schema`, and `response_json_schema`.
- **Detail:** Gemini provider-native fields are allowlisted and pass through when placed directly under `[modes.X.gemini]`, but no shared normalizer maps an internal `response_format` object from common mode/profile layers into Gemini's split SDK fields.
- **Recommendation:** Define the canonical internal `response_format` shapes and translate them to Gemini split fields while continuing to accept provider-native Gemini fields in Gemini namespaces.
- **Resolution choices:** Accepted: keep `GAP-015` as the Gemini-specific backlog to translate internal `response_format` into Gemini split structured-output fields while retaining provider-native namespace inputs.
- **References:** matrix row `response_format`; Gemini GenerateContent reference; matrix section Parameter Matrix; `src/thoth/providers/gemini.py`
- **Related:** GAP-003, GAP-006, DEC-001, DEC-004

<a id="gap-016"></a>

### GAP-016 - OpenAI `reasoning_effort` Is Not Wired

- **Description:** OpenAI Responses supports `reasoning.effort`, but the OpenAI adapter does not translate internal `reasoning_effort`.
- **Kind:** gap
- **Status:** accepted
- **Layers affected:** L6, L7, L8, L9
- **Providers affected:** OpenAI
- **Source:** `src/thoth/providers/openai.py:55-64`; `src/thoth/providers/openai.py:359-375`; `src/thoth/providers/openai.py:579-589`
- **Context:** The desired matrix exposes internal `reasoning_effort` as OpenAI Responses `reasoning.effort`.
- **Detail:** `_DIRECT_SDK_KEYS_OPENAI` includes the raw `reasoning` object, but the adapter does not normalize internal `reasoning_effort` into `reasoning.effort`. Current submit hard-codes `reasoning.summary = "auto"`, and current stream only reads `reasoning_summary`.
- **Recommendation:** Normalize internal `reasoning_effort` to OpenAI `reasoning.effort` and merge it with any separately configured `reasoning_summary` / `reasoning.summary` values instead of overwriting one with the other. Value mapping is identity for OpenAI-supported internal values: `none -> none`, `minimal -> minimal`, `low -> low`, `medium -> medium`, `high -> high`, `xhigh -> xhigh`; model-specific support remains validated by provider/model compatibility rules.
- **Resolution choices:** Accepted: keep `GAP-016` as the OpenAI-specific backlog to normalize internal `reasoning_effort` to Responses `reasoning.effort` and merge it with reasoning summary config.
- **References:** matrix row `reasoning_effort`; matrix per-parameter detail `reasoning_effort`; OpenAI Responses create reference; `src/thoth/providers/openai.py`
- **Related:** GAP-003, GAP-006, DEC-001, DEC-004

<a id="gap-017"></a>

### GAP-017 - Gemini `reasoning_effort` / `thinking_level` Is Not Wired

- **Description:** Gemini supports `thinkingConfig.thinkingLevel`, but the adapter does not map internal `reasoning_effort` or provider-native `thinking_level`.
- **Kind:** gap
- **Status:** accepted
- **Layers affected:** L6, L7, L8, L9
- **Providers affected:** Gemini
- **Source:** `src/thoth/providers/gemini.py:58-76`; `src/thoth/providers/gemini.py:301-320`
- **Context:** The desired matrix exposes internal `reasoning_effort` as Gemini `config.thinking_config.thinking_level` for Gemini 3 models.
- **Detail:** `_build_generate_content_config()` only builds `thinking_config` from `thinking_budget` and `include_thoughts`; it does not accept provider-native `thinking_level`, and no shared normalizer maps internal `reasoning_effort` into Gemini's enum field.
- **Recommendation:** Normalize supported internal reasoning effort values to Gemini `thinking_level` while keeping Gemini 2.5 token-budget control in the separate `thinking_budget` row. Accepted value mapping: `minimal -> MINIMAL`, `low -> LOW`, `medium -> MEDIUM`, `high -> HIGH`; `none` and `xhigh` have no Gemini `thinkingLevel` equivalent and should fail validation for Gemini unless a separate provider-specific policy is explicitly chosen.
- **Resolution choices:** Accepted: keep `GAP-017` as the Gemini-specific backlog to normalize supported internal `reasoning_effort` values to Gemini `thinking_level` while keeping `thinking_budget` separate.
- **References:** matrix row `reasoning_effort`; matrix per-parameter detail `reasoning_effort`; Gemini GenerateContent reference; `src/thoth/providers/gemini.py`
- **Related:** GAP-003, GAP-006, DEC-001, DEC-004

## Inconsistencies (`INC-`)

An inconsistency means a behavior exists, but the semantics differ across layers or providers. Triage by deciding the canonical behavior and then making every provider/layer obey that one contract. Each `INC-*` entry includes context, detailed impact, a recommended direction, and concrete resolution choices so it can be converted directly into a plan.

| ID | Title | Description | Status | Recommendation | Choices | References |
|---|---|---|---|---|---|---|
| INC-001 | L6/L8 flat mode params are copied but consumed unevenly | Fixed common mode params now route through the shared normalizer and are mirrored into provider namespaces for adapter compatibility. | resolved | Define L6/L8 as a small common set and route it through the normalizer. | A fixed common set accepted | matrix L6/L8; DEC-001 |
| INC-002 | Root provider defaults behave differently by provider | Root all-provider and per-provider defaults now normalize into equivalent provider request shapes across OpenAI, Perplexity, and Gemini. | resolved | Treat `[providers.NAME]` as the root provider namespace with recognized auth/client fields and recognized request-default fields. | A mixed recognized fields accepted | GAP-001; DEC-004 |
| INC-003 | Provider namespace unknown-key policy diverges | Provider namespace handling now validates recognized keys and requires explicit extension bags for arbitrary passthrough in the normalized path. | resolved | Validate known keys and require explicit extension bags for arbitrary passthrough. | A extension bags accepted | DEC-004 |
| INC-004 | Built-in mode overrides are shallow | Built-in/user/profile mode overlays now deep-merge nested provider namespaces. | resolved | Deep-merge mode dictionaries consistently with global config layers. | A deep merge accepted | DEC-006 |
| INC-005 | Runtime timeout has provider-specific effects | OpenAI, Perplexity, and Gemini now consume normalized timeout during client construction. | resolved | Make `timeout` a required provider client/runtime control. | A wire all providers accepted | GAP-005 |
| INC-006 | Runtime provider override can mismatch mode model and namespace | `--provider` can select a provider while retaining the selected mode's model and unrelated provider namespace. | accepted | Treat `--provider` as an expert override and document that model/namespace may also need explicit overrides. | C expert override accepted | DEC-005 |
| INC-007 | L11 is OpenAI-only while main providers are multi-provider | Clarification has its own OpenAI Chat Completions path instead of the shared OpenAI/Perplexity/Gemini stack. | accepted | Keep L11 UX config separate but reuse provider normalization for model calls. | A reuse normalizer accepted | GAP-007; DEC-003 |
| INC-008 | Documentation and tests disagree on root provider defaults | Root provider default docs and tests now describe the recognized-field normalizer contract. | resolved | Keep docs, tests, and matrix tied to the recognized-field registry. | A align to INC-002 accepted | GAP-001; INC-002 |
| INC-009 | Perplexity `search_context_size` needs upstream validation | Local built-ins and adapter defaults use `web_search_options.search_context_size`, and current Perplexity Sonar docs validate it as a request option. | accepted | Keep `search_context_size` as a first-class Perplexity row with current-doc citations. | A validate and keep accepted | DEC-004 |
| INC-010 | OpenAI `system_prompt` uses developer-role input instead of `instructions` | Desired state names OpenAI `instructions`, while current code sends an equivalent developer-role input message. | accepted | Use top-level `instructions` for OpenAI `system_prompt` during adapter normalization. | A switch to `instructions` accepted | matrix row `system_prompt` |
| INC-011 | Perplexity `response_format` differs between sync and async layers | Perplexity sync and async request builders now receive normalized namespaced `response_format`. | resolved | Route common/root `response_format` through shared normalization before sync/async request construction. | A shared normalization accepted | matrix row `response_format`; INC-001 |

<a id="inc-001"></a>

### INC-001 - L6/L8 Flat Mode Params Are Copied But Consumed Unevenly

- **Description:** Fixed common mode params now route through the shared normalizer and are mirrored into provider namespaces for adapter compatibility.
- **Kind:** inconsistency
- **Status:** resolved
- **Layers affected:** L6, L8
- **Providers affected:** OpenAI, Perplexity, Gemini
- **Source:** `src/thoth/providers/parameter_config.py:19-30`; `src/thoth/providers/parameter_config.py:208-227`; `src/thoth/providers/parameter_config.py:341-363`; `tests/test_provider_parameter_normalization.py:55-106`; `tests/extended/test_provider_config_passthrough.py:19-144`
- **Context:** L6/L8 are provider-neutral mode places where a user can say "for this mode, use this common inference parameter" without repeating provider namespaces. `[providers.defaults]` and profile-scoped provider defaults now cover cross-provider defaults outside a selected mode.
- **Detail:** `_apply_mode_generic_layer()` now recognizes a fixed common set, ignores auth/client/unknown generic fields for compatibility, and mirrors recognized common fields into the selected provider namespace through `to_legacy_config()`. That gives OpenAI, Perplexity sync/async, and Gemini one normalized source for common mode params while preserving the existing adapter config shape.
- **Recommendation:** Keep new provider-specific mode parameters in L7/L9 namespaces or explicit extension bags. Historical flat `max_tool_calls` is preserved as a compatibility exception and should be migrated separately if/when the flat provider-native allowance is removed.
- **Resolution choices:** Option A accepted and implemented for recognized common params: fixed common set for L6/L8, provider namespaces for everything else. Rejected for now: Option B, remove flat common params entirely; Option C, keep broad flat passthrough temporarily.
- **References:** matrix section Configuration Layers L6/L8; matrix rows `temperature`, `top_p`; DEC-001
- **Related:** GAP-002, GAP-003

<a id="inc-002"></a>

### INC-002 - Root Provider Defaults Behave Differently By Provider

- **Description:** Root all-provider and per-provider defaults now normalize into equivalent provider request shapes across OpenAI, Perplexity, and Gemini.
- **Kind:** inconsistency
- **Status:** resolved
- **Layers affected:** L2, L3, L4, L5
- **Providers affected:** OpenAI, Perplexity, Gemini
- **Source:** `src/thoth/providers/parameter_config.py:297-339`; `src/thoth/providers/__init__.py:195-204`; `tests/test_provider_parameter_normalization.py:14-53`; `tests/test_provider_config.py:606-789`
- **Context:** L2-L5 hold provider defaults that apply before mode overrides. This is the layer users naturally reach for when they want "all providers use this default" or "all OpenAI calls use this default unless a mode overrides it."
- **Detail:** Root all-provider defaults and per-provider defaults are now applied through the same `ProviderRuntimeConfig` path and then mirrored into adapter-compatible provider namespaces. Tests cover `[providers.defaults]`, `[providers.NAME]`, profile provider defaults, OpenAI deprecation-warning suppression, and Perplexity/Gemini equivalence.
- **Recommendation:** Treat `[providers.defaults]` as the root all-provider defaults namespace and `[providers.NAME]` as the root per-provider namespace. Add future root-default fields to the recognized-field registry before forwarding them.
- **Resolution choices:** Option B accepted and implemented: root `[providers.defaults]` and `[providers.NAME]` both support recognized defaults, and the normalizer separates auth/client controls from request defaults by a known-field registry before provider adapters build SDK payloads. Rejected: Option A, make `[providers.NAME]` auth/client-only; Option C, add `[providers.NAME.defaults]` tables that modes do not mirror.
- **References:** matrix section Configuration Layers L2-L5; matrix section Recognized Field Registry; GAP-001; DEC-004; DEC-007
- **Related:** GAP-001, INC-008

<a id="inc-003"></a>

### INC-003 - Provider Namespace Unknown-Key Policy Diverges

- **Description:** Provider namespace handling now validates recognized keys and requires explicit extension bags for arbitrary passthrough in the normalized path.
- **Kind:** inconsistency
- **Status:** resolved
- **Layers affected:** L7, L9
- **Providers affected:** OpenAI, Perplexity, Gemini
- **Source:** `src/thoth/providers/parameter_config.py:230-260`; `tests/test_provider_parameter_normalization.py:335-440`; `tests/test_provider_config.py:723-741`
- **Context:** L7/L9 are provider-native escape hatches. They need to support fast vendor evolution without allowing silent typos to become invisible no-ops.
- **Detail:** The shared normalizer rejects unknown root provider keys and unknown L7/L9 provider namespace keys. Arbitrary provider pass-through now requires an explicit extension bag such as `[modes.X.perplexity.extra_body]`. Legacy Perplexity nested root config remains schema-compatible for existing configs, but it is not the canonical normalized extension path.
- **Recommendation:** Keep common and known provider keys validated in the normalizer. Document new vendor options as recognized provider-native keys or route them through explicit extension bags.
- **Resolution choices:** Option A accepted and implemented for normalized provider namespaces: validate known keys and allow explicit extension bags for arbitrary provider-native fields. Rejected: Option B, strict allowlist everywhere; Option C, keep provider-specific policies as permanent behavior.
- **References:** matrix section Resolution Rules; matrix section Parameter Matrix; DEC-004
- **Related:** GAP-003, GAP-006

<a id="inc-004"></a>

### INC-004 - Built-In Mode Overrides Are Shallow

- **Description:** Built-in/user/profile mode overlays now deep-merge nested provider namespaces.
- **Kind:** inconsistency
- **Status:** resolved
- **Layers affected:** L1, L6, L7, L8, L9
- **Providers affected:** Perplexity, Gemini, OpenAI built-ins with provider namespaces
- **Source:** `src/thoth/config.py:650-652`; `tests/test_provider_parameter_normalization.py:521-555`
- **Context:** Built-in modes define provider namespaces for provider-specific defaults, such as Gemini tools/thinking budget and Perplexity search settings. Users should be able to override one nested value without accidentally deleting the rest of the built-in provider defaults.
- **Detail:** `get_mode_config()` now deep-merges user mode overrides into built-in modes, so a user can override one nested provider value without dropping built-in provider defaults such as Gemini tools or thinking budget. Arrays still follow the documented replacement policy.
- **Recommendation:** Keep mode overlay semantics aligned with the main config layer merge.
- **Resolution choices:** Option A accepted and implemented: deep-merge mode dictionaries consistently with global config layers. Rejected: Option B, preserve full-table replacement with documentation; Option C, require users to copy built-in modes before editing.
- **References:** matrix section Resolution Rules; matrix section Worked Examples
- **Related:** DEC-006

<a id="inc-005"></a>

### INC-005 - Runtime Timeout Has Provider-Specific Effects

- **Description:** OpenAI, Perplexity, and Gemini now consume normalized timeout during client construction.
- **Kind:** inconsistency
- **Status:** resolved
- **Layers affected:** L2, L3, L4, L5, L10
- **Providers affected:** Gemini compared with OpenAI and Perplexity
- **Source:** `src/thoth/providers/parameter_config.py:365-367`; `src/thoth/providers/openai.py:242-244`; `src/thoth/providers/perplexity.py:406-422`; `src/thoth/providers/gemini.py:222-226`
- **Context:** `timeout` is a framework/client control, not a model payload parameter. Users expect it to work uniformly because it is surfaced as a runtime override and copied for all production providers.
- **Detail:** Timeout is routed through the shared normalizer as a client control. OpenAI and Perplexity continue to apply it during client construction, and Gemini now applies it via Google Gen AI `HttpOptions(timeout=...)`.
- **Recommendation:** Keep `timeout` out of request payload normalization and treat it as a provider client control.
- **Resolution choices:** Option A accepted and implemented: wire timeout for every provider and cover it with constructor/request tests. Rejected: Option B, document Gemini timeout as unsupported; Option C, split timeout into provider-specific controls.
- **References:** matrix row `timeout`; GAP-005
- **Related:** GAP-005

<a id="inc-006"></a>

### INC-006 - Runtime Provider Override Can Mismatch Mode Model And Namespace

- **Description:** `--provider` can select a provider while retaining the selected mode's model and unrelated provider namespace.
- **Kind:** inconsistency
- **Status:** accepted
- **Layers affected:** L7, L9, L10
- **Providers affected:** all
- **Source:** `src/thoth/run.py:188-220`; `src/thoth/run.py:319-344`; `src/thoth/providers/__init__.py:192-202`
- **Context:** `--provider` is useful for testing and quick provider switching, but modes are often provider-specific because they pin a native model and provider namespace. The override boundary must prevent accidental cross-provider request shapes.
- **Detail:** Provider selection can be forced by `--provider`, and the selected mode's `model` is still copied into provider config before construction. A forced provider can therefore receive a model intended for another provider, while the forced provider namespace may be absent and the original namespace remains irrelevant. Example risk: forcing `--provider gemini` on a Perplexity mode can send Gemini a `sonar` model unless another override intervenes.
- **Recommendation:** Treat `--provider` as an expert override that changes provider selection only. Documentation and diagnostics should make clear that the mode's `model` and provider namespace do not become provider-neutral automatically; users must also pass `--model` or choose a compatible mode when needed.
- **Resolution choices:** Option C accepted: keep permissive expert override behavior, document that provider/model/namespace may mismatch, and add diagnostics in verbose mode. Rejected: Option A, validate and error on provider/model/namespace mismatch; Option B, allow `--provider` only when paired with `--model` if the mode pins a different provider.
- **References:** matrix section Resolution Rules; DEC-005
- **Related:** DEC-005

<a id="inc-007"></a>

### INC-007 - L11 Is OpenAI-Only While Main Providers Are Multi-Provider

- **Description:** Clarification has its own OpenAI Chat Completions path instead of the shared OpenAI/Perplexity/Gemini stack.
- **Kind:** inconsistency
- **Status:** accepted
- **Layers affected:** L11
- **Providers affected:** OpenAI only today; all if generalized
- **Source:** `src/thoth/config.py:345-365`; `src/thoth/interactive.py:857-909`
- **Context:** L11 is a real level because clarification has its own config subtree with model parameters, retry policy, prompt text, and UI controls. It is not part of the main provider/mode stack, but it still makes LLM requests.
- **Detail:** L11 has model, temperature, max-token, prompt, retry, and UI fields. Its provider field currently does not route through `create_provider()` or the provider registry, so it is a separate parameter subsystem. That means clarification uses OpenAI-specific auth and Chat Completions request construction even though the rest of the app is moving toward OpenAI, Perplexity, and Gemini parity.
- **Recommendation:** Keep L11 as a separate UX subsystem, but route the LLM call through the same provider normalizer and adapter dispatch used by main requests. UI-only fields should stay outside provider normalization.
- **Resolution choices:** Option A accepted: preserve L11 as a separate config area but reuse shared provider normalization for the model call. Rejected: Option B, keep the OpenAI-only path; Option C, fold clarification into normal modes.
- **References:** matrix section Configuration Layers L11; DEC-003
- **Related:** GAP-007

<a id="inc-008"></a>

### INC-008 - Documentation And Tests Disagree On Root Provider Defaults

- **Description:** Root provider default docs and tests now describe the recognized-field normalizer contract.
- **Kind:** inconsistency
- **Status:** resolved
- **Layers affected:** L2, L3, L4, L5
- **Providers affected:** OpenAI, Perplexity, Gemini
- **Source:** `planning/inference_provider_parameter_config_matrix.md`; `tests/test_provider_config.py:606-789`; `projects/P24-gemini-immediate-sync.md:233-237`
- **Context:** Root provider defaults were investigated and initially punted. The active docs and tests now align on the implemented recognized-field normalizer contract.
- **Detail:** The skipped root-provider tests have been converted to active tests, the matrix documents `[providers.defaults]` and `[providers.NAME]` as recognized-field default layers, and the project tracker points to the implemented normalizer rather than treating the behavior as merely aspirational.
- **Recommendation:** Keep provider table docs tied to the recognized-field registry so auth/client controls and request defaults do not drift apart again.
- **Resolution choices:** Option A accepted and implemented: align docs, tests, and matrix to `INC-002` and the recognized-field registry. Rejected: Option B, leave implementation tracked elsewhere after docs only; Option C, remove aspirational tests and document root provider tables as auth/client-only.
- **References:** matrix section Configuration Layers L2-L5; matrix section Recognized Field Registry; GAP-001; INC-002; DEC-007; `projects/P24-gemini-immediate-sync.md` P24-T26
- **Related:** GAP-001, INC-002

<a id="inc-009"></a>

### INC-009 - Perplexity `search_context_size` Needs Upstream Validation

- **Description:** Local built-ins and adapter defaults use `web_search_options.search_context_size`, and current Perplexity Sonar docs validate it as a request option.
- **Kind:** inconsistency
- **Status:** accepted
- **Layers affected:** L1, L7, L9
- **Providers affected:** Perplexity
- **Source:** `src/thoth/config.py:181-205`; `src/thoth/providers/perplexity.py:491-507`
- **Context:** This started as a documentation/API-contract inconsistency rather than a cross-provider behavior issue. Local code uses a Perplexity key path that was not obvious in the endpoint reference table, so it needed current upstream validation before the matrix could present it as a stable desired-state key.
- **Detail:** Thoth built-in Perplexity modes and the Perplexity adapter both set `web_search_options.search_context_size`. Current Perplexity docs validate the request shape through the Sonar filters guide, which shows `web_search_options={"search_context_size": "low"}` and identifies accepted values as `low`, `medium`, and `high`. The Sonar API reference also lists `web_search_options` as a request object and returns `usage.search_context_size`; pricing docs price Sonar requests by search context size. The matrix should keep the field and cite the filter/pricing docs rather than relying only on the endpoint schema table.
- **Recommendation:** Keep `search_context_size` as a first-class Perplexity matrix row under `web_search_options.search_context_size`, with accepted values `low`, `medium`, and `high`, and cite current Perplexity Sonar docs.
- **Resolution choices:** Option A accepted: current upstream docs validate `search_context_size`, so keep the row as supported Perplexity desired state. Rejected: Option B, remove it until the endpoint schema table is clearer; Option C, demote it to an unstable extension-bag field.
- **References:** matrix row `search_context_size`; Perplexity Sonar filters guide `https://docs.perplexity.ai/docs/sonar/filters`; Perplexity Sonar chat completion reference `https://docs.perplexity.ai/api-reference/sonar-post`; Perplexity pricing `https://docs.perplexity.ai/docs/getting-started/pricing`; `src/thoth/config.py`; `src/thoth/providers/perplexity.py`
- **Related:** GAP-006, DEC-004

<a id="inc-010"></a>

### INC-010 - OpenAI `system_prompt` Uses Developer-Role Input Instead Of `instructions`

- **Description:** Desired state names OpenAI `instructions`, while current code sends an equivalent developer-role input message.
- **Kind:** inconsistency
- **Status:** accepted
- **Layers affected:** L1, L6, L8
- **Providers affected:** OpenAI
- **Source:** `src/thoth/providers/openai.py:334-342`; `src/thoth/providers/openai.py:567-579`
- **Context:** OpenAI Responses accepts both top-level `instructions` and input messages with `developer`/`system` roles for system-level guidance. The matrix should document one canonical adapter output path rather than listing multiple encodings ambiguously.
- **Detail:** Current OpenAI submit and stream paths prepend `system_prompt` to `input` as a developer-role message. The desired matrix now names `instructions` as the canonical OpenAI key because it is the dedicated Responses API field for system/developer instructions and avoids overloading `input` with two internal concepts (`prompt` and `system_prompt`). This is not a behavior bug today, but it is a normalization mismatch to resolve when provider adapters are centralized.
- **Recommendation:** During adapter normalization, map internal `system_prompt` to OpenAI `instructions` and reserve `input` for user/content messages. Keep a compatibility test proving the semantic output is unchanged.
- **Resolution choices:** Option A accepted: switch OpenAI adapter output to top-level `instructions`. Rejected: Option B, define developer-role input as OpenAI's canonical encoding; Option C, allow both encodings in docs while emitting one path per request.
- **References:** matrix row `system_prompt`; OpenAI Responses create reference `https://platform.openai.com/docs/api-reference/responses`; `src/thoth/providers/openai.py`
- **Related:** GAP-003, DEC-009, DEC-010

<a id="inc-011"></a>

### INC-011 - Perplexity `response_format` Differs Between Sync And Async Layers

- **Description:** Perplexity sync and async request builders now receive normalized namespaced `response_format`.
- **Kind:** inconsistency
- **Status:** resolved
- **Layers affected:** L2, L3, L4, L5, L6, L7, L8, L9
- **Providers affected:** Perplexity
- **Source:** `src/thoth/providers/parameter_config.py:31-40`; `src/thoth/providers/perplexity.py:516-533`; `src/thoth/providers/perplexity.py:596-601`; `tests/test_provider_perplexity.py`; `tests/test_provider_parameter_normalization.py:443-518`
- **Context:** Perplexity Sonar supports `response_format` for structured output on the synchronous chat-completion endpoint, and Thoth's async wrapper constructs a nested `request` object from provider config.
- **Detail:** `ProviderRuntimeConfig.to_legacy_config()` mirrors common `response_format` into the Perplexity namespace. The sync request builder reads that namespace first, and the async wrapper copies namespace values into `request.*`, so root/default/mode-common values now reach both paths consistently.
- **Recommendation:** Keep Perplexity structured-output fields in the shared normalizer and test both sync and async request shapes whenever new common fields are added.
- **Resolution choices:** Option A accepted and implemented: route common/root `response_format` through shared normalization before sync and async request construction so both paths emit the same provider-native `response_format` / `request.response_format` payload. Rejected: Option B, support only `[modes.X.perplexity].response_format`; Option C, document sync and async as intentionally different.
- **References:** matrix row `response_format`; Perplexity Sonar chat completion reference `https://docs.perplexity.ai/api-reference/sonar-post`; `src/thoth/providers/perplexity.py`
- **Related:** INC-001, GAP-003, GAP-006

## Decisions (`DEC-`)

Decision entries are design choices whose resolution can spawn specific `GAP-` or `INC-` remediation work. `proposed` entries still need agreement; `accepted` entries record a contract already reflected in the matrix so downstream work can cite the decision.

| ID | Title | Description | Status | Recommendation | References |
|---|---|---|---|---|---|
| DEC-001 | Define mode flat common params or deprecate flat passthrough | Decide whether flat mode keys are a fixed common set or arbitrary provider passthrough. | accepted | Fixed common set plus provider namespaces for everything else. | matrix section Configuration Layers L6/L8 |
| DEC-002 | Normalize max token split forms | Decide whether users configure one internal token budget or expose every provider spelling. | accepted | Use internal `max_output_tokens`; adapters map native spellings. | matrix row `max_output_tokens` |
| DEC-003 | L11 clarification integration boundary | Decide whether clarification folds into the provider stack or remains separate while reusing normalization. | accepted | Keep L11 separate as UX config, but invoke shared provider normalization for model calls. | matrix section Configuration Layers L11 |
| DEC-004 | Unknown-key and extension policy | Decide which unknown provider namespace keys pass through, fail validation, or are ignored. | accepted | Validate known common keys; allow explicit provider extension bags. | matrix section Resolution Rules |
| DEC-005 | Provider override mismatch policy | Decide how `--provider` interacts with a mode's provider-specific model and namespace. | accepted | Treat `--provider` as a permissive expert override that changes provider selection only. | matrix section Resolution Rules |
| DEC-006 | Array merge and unset semantics | Decide array replacement vs append and absence vs explicit-disable semantics. | accepted | Arrays replace; absence inherits; explicit disable only through named booleans, valid empty arrays, or internal `None`. | matrix section Resolution Rules |
| DEC-007 | Add `[providers.defaults]` all-provider defaults | Decide whether to add `[providers.defaults]` and profile-scoped provider defaults as inherited all-provider layers. | accepted | Add `[providers.defaults]` as a root all-provider defaults layer with lower precedence than `[providers.NAME]`, plus profile-scoped overrides. | matrix section Overview; matrix section Recognized Field Registry |
| DEC-008 | Matrix cell target type | Decide whether the matrix should mix request payload keys with client/runtime controls. | accepted | Split request payload keys from framework/client controls. | matrix section Parameter Matrix |
| DEC-009 | Canonical provider endpoint scope | Decide which endpoint surface each provider column represents when a provider has multiple APIs. | accepted | Name the canonical provider surfaces before the table. | matrix section Parameter Matrix |
| DEC-010 | SDK key casing vs REST key casing | Decide whether provider cells use Python SDK key names, REST JSON names, or both. | accepted | Use Thoth's SDK request shape, with REST casing noted where different. | matrix section Parameter Matrix |

<a id="dec-001"></a>

### DEC-001 - Define Mode Flat Common Params Or Deprecate Flat Passthrough

- **Description:** Decide whether flat mode keys are a fixed common set or arbitrary provider passthrough.
- **Kind:** decision
- **Status:** accepted
- **Layers affected:** L6, L8
- **Providers affected:** all
- **Source:** `src/thoth/providers/__init__.py:48-95`; `tests/test_provider_perplexity.py:221-253`; `src/thoth/providers/gemini.py:292-320`
- **Detail:** Current flat passthrough creates provider-specific behavior from a provider-neutral mode location. The desired matrix treats L6/L8 as a fixed common set.
- **References:** matrix section Configuration Layers L6/L8; matrix section Parameter Matrix
- **Related:** GAP-002, INC-001
- **Recommendation:** Define a fixed common set (`temperature`, `top_p`, `max_output_tokens`, `stop_sequences`, plus any later explicitly accepted common params). Deprecate arbitrary flat passthrough and require provider namespaces for provider-specific fields.
- **Resolution choices:** Option A accepted: define a fixed L6/L8 common set and deprecate arbitrary flat passthrough. Rejected: Option B, remove L6/L8 flat common params entirely; Option C, keep arbitrary flat passthrough as supported behavior.

<a id="dec-002"></a>

### DEC-002 - Normalize Max Token Split Forms

- **Description:** Decide whether users configure one internal token budget or expose every provider spelling.
- **Kind:** decision
- **Status:** accepted
- **Layers affected:** L2-L10
- **Providers affected:** OpenAI, Perplexity, Gemini
- **Source:** `src/thoth/providers/perplexity.py:388-394`; `src/thoth/providers/gemini.py:58-76`; `src/thoth/providers/openai.py:55-64`
- **Detail:** Providers use different names: OpenAI Responses uses `max_output_tokens`, Perplexity uses `max_tokens`, and Gemini uses `max_output_tokens`. OpenAI Chat Completions variants may use other names. Exposing every spelling makes config provider-specific even in shared defaults and mode-generic layers.
- **References:** matrix row `max_output_tokens`; matrix section Per-Parameter Detail
- **Related:** GAP-006, GAP-008
- **Recommendation:** Use internal `max_output_tokens` everywhere outside provider namespaces. Adapters translate to the native field, and provider-specific aliases are accepted only as migration aliases or under namespaces.
- **Resolution choices:** Option A accepted: use internal `max_output_tokens` outside provider namespaces and map native spellings in adapters. Rejected: Option B, expose every provider spelling; Option C, support all aliases everywhere including all-provider defaults and flat L6/L8.

<a id="dec-003"></a>

### DEC-003 - L11 Clarification Integration Boundary

- **Description:** Decide whether clarification folds into the provider stack or remains separate while reusing normalization.
- **Kind:** decision
- **Status:** accepted
- **Layers affected:** L11
- **Providers affected:** OpenAI today; all if generalized
- **Source:** `src/thoth/config.py:345-365`; `src/thoth/interactive.py:857-909`
- **Detail:** Clarification has UI and retry fields that do not belong in normal provider request config. But its model call should not need a separate auth, provider, and parameter path forever.
- **References:** matrix section Configuration Layers L11; GAP-007; INC-007
- **Related:** GAP-007, INC-007
- **Recommendation:** Keep L11 as a separate UX subsystem for fields like `input_height`, `max_input_height`, retry policy, and prompt text. For the LLM call inside L11, reuse the shared provider normalizer and adapter dispatch.
- **Resolution choices:** Option A accepted: keep L11 separate as clarification UX config, but use shared provider normalization for its model call. Rejected: Option B, keep L11 entirely separate and OpenAI-only; Option C, fold clarification into normal modes.

<a id="dec-004"></a>

### DEC-004 - Unknown-Key And Extension Policy

- **Description:** Decide which unknown provider namespace keys pass through, fail validation, or are ignored.
- **Kind:** decision
- **Status:** accepted
- **Layers affected:** L2, L3, L4, L5, L7, L9
- **Providers affected:** OpenAI, Perplexity, Gemini
- **Source:** `src/thoth/providers/openai.py:246-281`; `src/thoth/providers/perplexity.py:484-508`; `src/thoth/providers/gemini.py:58-76`; `tests/test_provider_config.py:615-638`
- **Detail:** Perplexity's API has a broad extension surface that benefits from pass-through. Gemini's typed SDK path benefits from validation/allowlisting. OpenAI currently has explicit read sites. A single policy must still allow provider-specific escape hatches.
- **References:** matrix section Resolution Rules; matrix section Parameter Matrix; GAP-006; INC-003
- **Related:** GAP-001, INC-003
- **Recommendation:** Validate common parameters through the shared matrix. For provider-native extension fields, define explicit extension bags such as `[modes.X.perplexity.extra_body]` or a documented provider allowlist. Do not silently ignore unknown keys unless a provider marks a nested namespace as forward-compatible.
- **Resolution choices:** Option A accepted: validate known/common keys and allow explicit provider extension bags. Rejected: Option B, strict allowlist everywhere; Option C, keep provider-specific unknown-key behavior as permanent policy.

<a id="dec-005"></a>

### DEC-005 - Provider Override Mismatch Policy

- **Description:** Decide how `--provider` interacts with a mode's provider-specific model and namespace.
- **Kind:** decision
- **Status:** accepted
- **Layers affected:** L7, L9, L10
- **Providers affected:** all
- **Source:** `src/thoth/run.py:188-220`; `src/thoth/run.py:319-344`; `src/thoth/providers/__init__.py:192-202`
- **Detail:** Runtime provider override is useful, but retaining a mode's model and provider namespace can create invalid cross-provider payloads.
- **References:** matrix section Resolution Rules; INC-006
- **Related:** INC-006
- **Recommendation:** Treat `--provider` as a permissive expert override that changes provider selection only. It does not make the selected mode's model or provider namespace provider-neutral; users must also pass `--model` or choose a compatible mode when needed. Documentation and verbose diagnostics should call out mismatch risk.
- **Resolution choices:** Option C accepted: keep `--provider` as a permissive expert override and document/diagnose mismatch risk. Rejected: Option A, validate and error on incompatible provider/mode/model combinations; Option B, require `--model` whenever `--provider` overrides a provider-pinned mode.

<a id="dec-006"></a>

### DEC-006 - Array Merge And Unset Semantics

- **Description:** Decide array replacement vs append and absence vs explicit-disable semantics.
- **Kind:** decision
- **Status:** accepted
- **Layers affected:** L1-L10
- **Providers affected:** all
- **Source:** `src/thoth/config.py:544-565`; `src/thoth/config.py:650-652`; `src/thoth/providers/parameter_config.py:139-147`
- **Detail:** Global config layers and mode overlays now deep-merge dictionaries and replace non-dicts. Arrays such as `tools`, `stop_sequences`, and domain filters still need predictable replacement behavior.
- **References:** matrix section Resolution Rules
- **Related:** INC-004
- **Recommendation:** Arrays replace by default. Absence means inherit. Explicit disable uses named booleans like `web_search = false`, empty arrays where an empty array is semantically valid, or internal `None` for APIs that distinguish null from unset.
- **Resolution choices:** Option A accepted: arrays replace; absence inherits; explicit disable uses named booleans, empty arrays where valid, or internal `None` where provider APIs distinguish null. Rejected: Option B, arrays append/merge by default; Option C, treat empty arrays as unset/inherit.

<a id="dec-007"></a>

### DEC-007 - Add `[providers.defaults]` All-Provider Defaults

- **Description:** Decide whether to add `[providers.defaults]` and profile-scoped provider defaults as inherited all-provider layers.
- **Kind:** decision
- **Status:** accepted
- **Layers affected:** L2 and L4
- **Providers affected:** all
- **Source:** `src/thoth/providers/parameter_config.py:297-339`; `tests/test_provider_parameter_normalization.py:14-53`; `planning/p24-providers-root-namespace-investigation.v1.md:62-69`
- **Detail:** The accepted and now implemented contract adds `[providers.defaults]` as L2 and profile-scoped `[profiles.NAME.providers.defaults]` as L4 for recognized shared client controls and common request defaults whose semantics are defined for every supported provider in this contract. L2 has lower precedence than `[providers.NAME]`; L4 has lower precedence than `[profiles.NAME.providers.PROVIDER]`; both are lower precedence than mode layers. They use the same recognized-field registry as root provider config for shared/common fields while excluding provider-specific auth secrets such as `api_key` and provider-native extension bags.
- **References:** matrix section Overview; matrix section Configuration Layers; matrix section Recognized Field Registry
- **Related:** DEC-001, GAP-001, GAP-003
- **Recommendation:** Add `[providers.defaults]` and `[profiles.NAME.providers.defaults]` as all-provider defaults layers for recognized shared client controls and common request defaults. Per-provider defaults override all-provider defaults at the same scope, mode layers override provider defaults, and provider namespaces/extension bags remain the place for provider-native fields.
- **Resolution choices:** Option B accepted: add `[providers.defaults]` plus profile-scoped `[profiles.NAME.providers.defaults]` as all-provider defaults layers. Rejected: Option A, do not add the layer; Option C, add it only for auth/client controls.

<a id="dec-008"></a>

### DEC-008 - Matrix Cell Target Type

- **Description:** Decide whether the matrix should mix request payload keys with client/runtime controls.
- **Kind:** decision
- **Status:** accepted
- **Layers affected:** L2-L11
- **Providers affected:** all
- **Source:** `planning/inference_provider_parameter_config_matrix.md`
- **Detail:** A single table that mixes SDK request keys, client constructor fields, route selection, and streaming methods makes provider cells ambiguous. The matrix should keep request payload keys separate from framework/client controls.
- **References:** matrix section Parameter Matrix
- **Related:** GAP-003
- **Recommendation:** Split `Request Payload Keys` from `Framework And Client Controls`, and make provider cells literal key paths.

<a id="dec-009"></a>

### DEC-009 - Canonical Provider Endpoint Scope

- **Description:** Decide which endpoint surface each provider column represents when a provider has multiple APIs.
- **Kind:** decision
- **Status:** accepted
- **Layers affected:** L0-L10
- **Providers affected:** OpenAI, Perplexity, Gemini
- **Source:** `src/thoth/providers/openai.py`; `src/thoth/providers/perplexity.py`; `src/thoth/providers/gemini.py`
- **Detail:** OpenAI has Responses and Chat Completions surfaces, Perplexity has sync Sonar and async Sonar, and Gemini has GenerateContent plus separate background/interactions planning. A provider column is ambiguous unless the matrix declares its canonical endpoint surface.
- **References:** matrix section Parameter Matrix
- **Related:** DEC-002, DEC-004
- **Recommendation:** Name the canonical provider surfaces immediately before the matrix and keep endpoint-specific exceptions in notes or separate rows.

<a id="dec-010"></a>

### DEC-010 - SDK Key Casing Vs REST Key Casing

- **Description:** Decide whether provider cells use Python SDK key names, REST JSON names, or both.
- **Kind:** decision
- **Status:** accepted
- **Layers affected:** L7, L9, L10
- **Providers affected:** OpenAI, Perplexity, Gemini
- **Source:** `src/thoth/providers/gemini.py`; `planning/inference_provider_parameter_config_matrix.md`
- **Detail:** Gemini in particular differs between Python SDK snake_case and REST camelCase. Since Thoth's adapters use Python SDKs for OpenAI and Gemini and the OpenAI-compatible SDK for Perplexity sync, the matrix should not switch casing silently between rows.
- **References:** matrix section Parameter Matrix
- **Related:** DEC-009
- **Recommendation:** Use Thoth's SDK request shape in provider cells and note REST casing where it differs.

## Migration Notes

Accepted entries are design contracts awaiting implementation unless marked resolved. `GAP-004` is resolved as stale/currently implemented and has no migration. When an accepted or resolved entry changes runtime config behavior, add a migration note here with:

- the resolving ID,
- the old config shape,
- the new config shape,
- whether behavior changes silently or emits a deprecation warning first,
- the code/docs/tests that were updated.

Implemented migrations:

- `GAP-001` / `INC-002` / `INC-008`: `[providers.defaults]`, `[providers.NAME]`, `[profiles.NAME.providers.defaults]`, and `[profiles.NAME.providers.PROVIDER]` now feed the shared provider normalizer. Recognized root defaults such as `timeout`, `temperature`, and `response_format` become adapter-visible defaults for OpenAI, Perplexity, and Gemini. Unknown root provider keys now raise `ValueError` instead of being silently ignored or provider-specific passthrough.
- `INC-001`: L6/L8 mode-generic keys are treated as a fixed common set. Recognized common keys are normalized and mirrored into the selected provider namespace; auth/client/unknown generic mode keys are not promoted. The legacy flat OpenAI `max_tool_calls` path remains as an explicit compatibility exception.
- `INC-003` / `DEC-004`: unknown L7/L9 provider namespace keys now raise `ValueError`. Arbitrary Perplexity pass-through should move to an explicit extension bag, for example `[modes.fast.perplexity.extra_body] vendor_flag = true`. Legacy Perplexity nested root config remains schema-compatible for existing configs, but new documented passthrough should use `extra_body`.
- `GAP-005` / `INC-005`: Gemini timeout now maps from seconds in Thoth config to milliseconds in Google Gen AI `HttpOptions(timeout=...)`.
- `INC-004`: user/profile mode overlays now deep-merge nested provider namespaces into built-in modes. Arrays still replace by default.
- `INC-011`: Perplexity `response_format` is normalized into the provider namespace so sync and async request paths receive the same field.

Expected future migrations:

- `DEC-002` / `GAP-006`: normalize token limit keys to `max_output_tokens`.
- `DEC-005` / `INC-006`: document and diagnose `--provider` mismatch risk while keeping it a permissive expert override.

## Driving Downstream Documents

Every accepted or resolved entry should update each reference target and cite the resolving ID in the target document, test, code comment, or ticket. The top-level index is the punch list for matrix updates, ADRs, implementation tasks, and docs changes.
