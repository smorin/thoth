# Inference Provider Parameter Config Inconsistencies

Sidecar to [inference_provider_parameter_config_matrix.md](inference_provider_parameter_config_matrix.md). The matrix is the desired state; this document tracks current gaps, current inconsistencies, and open design decisions that block a clean implementation.

## ID Scheme

- `GAP-NNN` - desired state requires behavior that is not implemented.
- `INC-NNN` - behavior exists, but differs across providers or layers.
- `DEC-NNN` - an unresolved standardization decision.

IDs are stable and never reused.

## Top-Level Index

| ID | Kind | Title | Description | Status | References |
|---|---|---|---|---|---|
| GAP-001 | gap | Root provider request defaults are not normalized | L2/L3 request defaults are copied but not normalized into a provider-consistent request structure. | accepted | matrix section Configuration Layers L2-L3; matrix section Resolution Rules |
| GAP-002 | gap | Fixed L4 common parameter set is missing | Mode-level flat keys are arbitrary passthrough rather than a documented common parameter set. | accepted | matrix section Configuration Layers L4/L6; DEC-001 |
| GAP-003 | gap | Shared normalized provider parameter object is missing | `create_provider()` mutates provider config but leaves each adapter to interpret shapes independently. | open | matrix section Resolution Rules; code `src/thoth/providers/__init__.py` |
| GAP-004 | gap | Gemini missing from config defaults provider table | The defaults provider table declares OpenAI and Perplexity API keys but omits Gemini. | open | matrix section Configuration Layers L2; code `src/thoth/config.py` |
| GAP-005 | gap | Gemini timeout override is not applied to the SDK client | Runtime timeout is copied into Gemini config but Gemini client construction does not consume it. | open | matrix row `timeout`; code `src/thoth/providers/gemini.py` |
| GAP-006 | gap | Full parameter matrix is not wired through adapters | Several desired matrix parameters have no adapter translation path. | open | matrix section Parameter Matrix |
| GAP-007 | gap | L9 clarification bypasses shared provider normalization | Interactive clarification reads OpenAI config directly and constructs `AsyncOpenAI` directly. | open | matrix section Configuration Layers L9; DEC-003 |
| GAP-008 | gap | `max_output_tokens` is not normalized across providers | The desired internal token-budget field is not translated to OpenAI, Perplexity, and Gemini consistently. | open | matrix row `max_output_tokens`; DEC-002 |
| GAP-009 | gap | `stop_sequences` is not normalized across providers | The desired internal stop-sequence field is not translated to supported provider-native fields consistently. | open | matrix row `stop_sequences`; DEC-001 |
| GAP-010 | gap | Gemini `frequency_penalty` is not wired | Gemini supports `frequencyPenalty`, but the Gemini adapter allowlist omits `frequency_penalty`. | open | matrix row `frequency_penalty`; code `src/thoth/providers/gemini.py` |
| GAP-011 | gap | Gemini `presence_penalty` is not wired | Gemini supports `presencePenalty`, but the Gemini adapter allowlist omits `presence_penalty`. | open | matrix row `presence_penalty`; code `src/thoth/providers/gemini.py` |
| INC-001 | inconsistency | L4 flat mode params are copied but consumed unevenly | Common flat params such as `temperature` are copied, but OpenAI, Perplexity sync/async, and Gemini consume them through different paths. | accepted | matrix section Configuration Layers L4/L6; DEC-001 |
| INC-002 | inconsistency | Root provider defaults behave differently by provider | OpenAI can half-read root flat values, while Perplexity/Gemini generally require provider namespaces for request params. | accepted | matrix section Configuration Layers L2/L3; GAP-001 |
| INC-003 | inconsistency | Provider namespace unknown-key policy diverges | Perplexity forwards unknown namespace keys, Gemini allowlists, and OpenAI reads only explicit keys. | accepted | matrix section Resolution Rules; DEC-004 |
| INC-004 | inconsistency | Built-in mode overrides are shallow | User mode overlays replace nested built-in provider namespaces instead of deep-merging them. | accepted | matrix section Resolution Rules |
| INC-005 | inconsistency | Runtime timeout has provider-specific effects | OpenAI and Perplexity use timeout in client construction; Gemini currently does not. | accepted | matrix row `timeout`; GAP-005 |
| INC-006 | inconsistency | Runtime provider override can mismatch mode model and namespace | `--provider` can select a provider while retaining the selected mode's model and unrelated provider namespace. | accepted | matrix section Resolution Rules; DEC-005 |
| INC-007 | inconsistency | L9 is OpenAI-only while main providers are multi-provider | Clarification has its own OpenAI Chat Completions path instead of the shared OpenAI/Perplexity/Gemini stack. | accepted | matrix section Configuration Layers L9; DEC-003 |
| INC-008 | inconsistency | Documentation and tests disagree on root provider defaults | Auth help documents provider tables as API-key-only while skipped tests describe desired request defaults. | accepted | matrix section Configuration Layers L2-L3; GAP-001 |
| INC-009 | inconsistency | Perplexity `search_context_size` needs upstream validation | Local built-ins and adapter defaults use `web_search_options.search_context_size`, and current Perplexity Sonar docs validate it as a request option. | accepted | matrix row `search_context_size`; DEC-004 |
| INC-010 | inconsistency | OpenAI `system_prompt` uses developer-role input instead of `instructions` | Desired state names OpenAI `instructions`, while current code sends an equivalent developer-role input message. | accepted | matrix row `system_prompt`; code `src/thoth/providers/openai.py` |
| DEC-001 | decision | Define L4 flat common params or deprecate flat passthrough | Decide whether flat mode keys are a fixed common set or arbitrary provider passthrough. | proposed | matrix section Configuration Layers L4/L6 |
| DEC-002 | decision | Normalize max token split forms | Decide whether users configure one internal token budget or expose every provider spelling. | proposed | matrix row `max_output_tokens` |
| DEC-003 | decision | L9 clarification integration boundary | Decide whether clarification folds into the provider stack or remains separate while reusing normalization. | proposed | matrix section Configuration Layers L9 |
| DEC-004 | decision | Unknown-key and extension policy | Decide which unknown provider namespace keys pass through, fail validation, or are ignored. | proposed | matrix section Resolution Rules |
| DEC-005 | decision | Provider override mismatch policy | Decide how `--provider` interacts with a mode's provider-specific model and namespace. | proposed | matrix section Resolution Rules |
| DEC-006 | decision | Array merge and unset semantics | Decide array replacement vs append and absence vs explicit-disable semantics. | proposed | matrix section Resolution Rules |
| DEC-007 | decision | No global all-provider root defaults | Decide whether to keep excluding a generic inherited provider defaults layer. | proposed | matrix section Overview |
| DEC-008 | decision | Matrix cell target type | Decide whether the matrix should mix request payload keys with client/runtime controls. | accepted | matrix section Parameter Matrix |
| DEC-009 | decision | Canonical provider endpoint scope | Decide which endpoint surface each provider column represents when a provider has multiple APIs. | accepted | matrix section Parameter Matrix |
| DEC-010 | decision | SDK key casing vs REST key casing | Decide whether provider cells use Python SDK key names, REST JSON names, or both. | accepted | matrix section Parameter Matrix |

## Gaps (`GAP-`)

A gap means the desired-state contract requires behavior that the current implementation does not provide. Triage by deciding whether to implement the missing behavior, narrow the desired contract, or split the work into provider-specific follow-ups.

| ID | Title | Description | Status | References |
|---|---|---|---|---|
| GAP-001 | Root provider request defaults are not normalized | L2/L3 request defaults are copied but not normalized into a provider-consistent request structure. | accepted | matrix section Configuration Layers L2-L3 |
| GAP-002 | Fixed L4 common parameter set is missing | Mode-level flat keys are arbitrary passthrough rather than a documented common parameter set. | accepted | matrix section Configuration Layers L4/L6 |
| GAP-003 | Shared normalized provider parameter object is missing | `create_provider()` mutates provider config but leaves each adapter to interpret shapes independently. | open | matrix section Resolution Rules |
| GAP-004 | Gemini missing from config defaults provider table | The defaults provider table declares OpenAI and Perplexity API keys but omits Gemini. | open | matrix section Configuration Layers L2 |
| GAP-005 | Gemini timeout override is not applied to the SDK client | Runtime timeout is copied into Gemini config but Gemini client construction does not consume it. | open | matrix row `timeout` |
| GAP-006 | Full parameter matrix is not wired through adapters | Several desired matrix parameters have no adapter translation path. | open | matrix section Parameter Matrix |
| GAP-007 | L9 clarification bypasses shared provider normalization | Interactive clarification reads OpenAI config directly and constructs `AsyncOpenAI` directly. | open | matrix section Configuration Layers L9 |
| GAP-008 | `max_output_tokens` is not normalized across providers | The desired internal token-budget field is not translated to OpenAI, Perplexity, and Gemini consistently. | open | matrix row `max_output_tokens` |
| GAP-009 | `stop_sequences` is not normalized across providers | The desired internal stop-sequence field is not translated to supported provider-native fields consistently. | open | matrix row `stop_sequences` |
| GAP-010 | Gemini `frequency_penalty` is not wired | Gemini supports `frequencyPenalty`, but the Gemini adapter allowlist omits `frequency_penalty`. | open | matrix row `frequency_penalty` |
| GAP-011 | Gemini `presence_penalty` is not wired | Gemini supports `presencePenalty`, but the Gemini adapter allowlist omits `presence_penalty`. | open | matrix row `presence_penalty` |

<a id="gap-001"></a>

### GAP-001 - Root Provider Request Defaults Are Not Normalized

- **Description:** L2/L3 request defaults are copied but not normalized into a provider-consistent request structure.
- **Kind:** gap
- **Status:** accepted
- **Layers affected:** L2, L3, L5, L7
- **Providers affected:** OpenAI, Perplexity, Gemini
- **Source:** `src/thoth/providers/__init__.py:174-202`; `tests/test_provider_config.py:541-672`; `planning/p24-providers-root-namespace-investigation.v1.md:7-69`
- **Context:** This is the implementation follow-through for accepted `INC-002` and `INC-008`: root `[providers.NAME]` is a mixed recognized-field namespace, but runtime request-default normalization is still missing.
- **Detail:** `create_provider()` starts from `[providers.NAME]` and copies the whole table. That makes root request defaults appear to exist, but they are not normalized into the provider namespace before adapter consumption. The P24 investigation explicitly punted the design, and the root-namespace tests are skipped with desired assertions.
- **Recommendation:** Keep this as one shared cross-provider implementation gap rather than splitting it by adapter. The fix should build the common recognized-field registry and normalizer once, then prove OpenAI, Perplexity, and Gemini all receive root provider request defaults with identical precedence semantics.
- **Resolution choices:** Option A accepted: keep `GAP-001` as the accepted implementation backlog for root `[providers.NAME]` request-default normalization. Rejected: Option B, split the gap into separate provider-specific entries; Option C, narrow desired state to auth/client-only root provider tables.
- **References:** matrix section Configuration Layers L2-L3; matrix section Resolution Rules; `planning/p24-providers-root-namespace-investigation.v1.md`; `tests/test_provider_config.py::test_root_providers_namespace_*`
- **Related:** INC-002, INC-008, DEC-004

<a id="gap-002"></a>

### GAP-002 - Fixed L4 Common Parameter Set Is Missing

- **Description:** Mode-level flat keys are arbitrary passthrough rather than a documented common parameter set.
- **Kind:** gap
- **Status:** accepted
- **Layers affected:** L4, L6
- **Providers affected:** all
- **Source:** `src/thoth/providers/__init__.py:48-95`; `tests/extended/test_provider_config_passthrough.py:19-50`
- **Context:** This is the implementation follow-through for accepted `INC-001`: L4/L6 should be provider-neutral common inference fields, not an unbounded provider passthrough bucket.
- **Detail:** The factory copies every non-metadata, non-provider-name key from a mode into provider config. That is a passthrough mechanism, not a fixed common parameter contract. The desired matrix narrows L4/L6 to explicit common parameters such as `temperature`, `top_p`, `max_output_tokens`, and `stop_sequences`; provider-native and experimental fields should live under provider namespaces or explicit extension bags.
- **Recommendation:** Keep this as the backlog item for replacing arbitrary L4/L6 passthrough with a fixed common parameter set and routing those common fields through shared normalization.
- **Resolution choices:** Option A accepted: keep `GAP-002` as the implementation backlog for replacing arbitrary L4/L6 passthrough with a fixed common parameter set. Rejected: Option B, split this into separate schema/routing/migration-warning gaps now; Option C, keep arbitrary flat passthrough as supported behavior.
- **References:** matrix section Configuration Layers L4/L6; matrix section Parameter Matrix; DEC-001
- **Related:** INC-001, DEC-001

<a id="gap-003"></a>

### GAP-003 - Shared Normalized Provider Parameter Object Is Missing

- **Description:** `create_provider()` mutates provider config but leaves each adapter to interpret shapes independently.
- **Kind:** gap
- **Status:** open
- **Layers affected:** L0-L8
- **Providers affected:** OpenAI, Perplexity, Gemini
- **Source:** `src/thoth/providers/__init__.py:154-215`; `src/thoth/providers/openai.py:246-281`; `src/thoth/providers/perplexity.py:484-523`; `src/thoth/providers/gemini.py:276-320`
- **Detail:** The factory is the shared routing point, but it does not produce a typed or tagged normalized structure. OpenAI has a resolver with a flat fallback, Perplexity reads `config["perplexity"]`, and Gemini reads an allowlisted `config["gemini"]`. A common normalizer would make layer precedence and source semantics testable once.
- **References:** matrix section Resolution Rules; matrix section Worked Examples; `src/thoth/providers/__init__.py`
- **Related:** GAP-001, INC-001, INC-003

<a id="gap-004"></a>

### GAP-004 - Gemini Missing From Config Defaults Provider Table

- **Description:** The defaults provider table declares OpenAI and Perplexity API keys but omits Gemini.
- **Kind:** gap
- **Status:** open
- **Layers affected:** L2
- **Providers affected:** Gemini
- **Source:** `src/thoth/config.py:341-344`; `src/thoth/providers/__init__.py:35-38`
- **Detail:** The provider registry and environment variable table include Gemini, but `ConfigSchema.get_defaults()["providers"]` does not include `[providers.gemini]`. Desired state has every supported provider represented in root provider config defaults.
- **References:** matrix section Configuration Layers L2; matrix section Worked Examples A-B; `src/thoth/config.py`
- **Related:** INC-008

<a id="gap-005"></a>

### GAP-005 - Gemini Timeout Override Is Not Applied To The SDK Client

- **Description:** Runtime timeout is copied into Gemini config but Gemini client construction does not consume it.
- **Kind:** gap
- **Status:** open
- **Layers affected:** L3, L8
- **Providers affected:** Gemini
- **Source:** `src/thoth/providers/__init__.py:188-190`; `src/thoth/providers/gemini.py:213-221`
- **Detail:** `create_provider()` stores `timeout` for Gemini when a runtime override is supplied, but `GeminiProvider.__init__()` constructs `genai.Client(api_key=api_key)` without threading timeout into the client or request options. Desired state says timeout is a client/runtime control for every supported provider.
- **References:** matrix row `timeout`; matrix section Resolution Rules
- **Related:** INC-005

<a id="gap-006"></a>

### GAP-006 - Full Parameter Matrix Is Not Wired Through Adapters

- **Description:** Several desired matrix parameters have no adapter translation path.
- **Kind:** gap
- **Status:** open
- **Layers affected:** L2-L8
- **Providers affected:** OpenAI, Perplexity, Gemini
- **Source:** `src/thoth/providers/openai.py:55-64`; `src/thoth/providers/perplexity.py:388-394`; `src/thoth/providers/gemini.py:58-76`
- **Detail:** Current allowlists and explicit read sites cover a small subset: OpenAI handles fields such as `temperature` and `max_tool_calls` but does not yet wire Responses-supported `top_p`; Perplexity handles `max_tokens`, `temperature`, `top_p`, `stop`, and `response_format` plus extra-body pass-through; Gemini handles a larger generation config allowlist. Desired rows such as `frequency_penalty`, `presence_penalty`, `seed`, `n`, `logprobs`, `top_logprobs`, `user`, `service_tier`, and unified `max_output_tokens` need explicit adapter decisions.
- **References:** matrix section Parameter Matrix; matrix section Per-Parameter Detail
- **Related:** GAP-008, DEC-002, DEC-004

<a id="gap-007"></a>

### GAP-007 - L9 Clarification Bypasses Shared Provider Normalization

- **Description:** Interactive clarification reads OpenAI config directly and constructs `AsyncOpenAI` directly.
- **Kind:** gap
- **Status:** open
- **Layers affected:** L9
- **Providers affected:** OpenAI now; all if L9 becomes provider-selectable
- **Source:** `src/thoth/config.py:345-365`; `src/thoth/interactive.py:857-909`
- **Detail:** The clarification subsystem has its own config subtree and direct OpenAI Chat Completions call. It does not use `create_provider()`, provider namespace normalization, provider API key resolution, or the multi-provider adapter surface.
- **References:** matrix section Configuration Layers L9; matrix section Resolution Rules; DEC-003
- **Related:** INC-007, DEC-003

<a id="gap-008"></a>

### GAP-008 - `max_output_tokens` Is Not Normalized Across Providers

- **Description:** The desired internal token-budget field is not translated to OpenAI, Perplexity, and Gemini consistently.
- **Kind:** gap
- **Status:** open
- **Layers affected:** L2, L3, L4, L5, L6, L7
- **Providers affected:** OpenAI, Perplexity, Gemini
- **Source:** `src/thoth/providers/openai.py:55-64`; `src/thoth/providers/perplexity.py:388-394`; `src/thoth/providers/perplexity.py:520-528`; `src/thoth/providers/perplexity.py:591-596`; `src/thoth/providers/gemini.py:58-76`
- **Context:** `max_output_tokens` is the desired internal name for output-token budget, but provider APIs use split forms. OpenAI Responses and Gemini use `max_output_tokens`; Perplexity uses `max_tokens`.
- **Detail:** OpenAI currently does not wire `max_output_tokens` into Responses request params. Perplexity wires native `max_tokens` for sync and async namespace paths, but there is no normalization from internal `max_output_tokens` to `max_tokens`. Gemini wires `gemini.max_output_tokens` through `GenerateContentConfig`, but common L4/L6 `max_output_tokens` is not routed into the Gemini namespace until shared normalization exists.
- **Recommendation:** Resolve DEC-002 by using `max_output_tokens` everywhere outside provider namespaces. Adapter normalization should emit OpenAI `max_output_tokens`, Perplexity `max_tokens` / `request.max_tokens`, and Gemini `config.max_output_tokens`. Provider-native aliases may remain in provider namespaces as compatibility inputs.
- **References:** matrix row `max_output_tokens`; DEC-002; matrix section Configuration Layers L4/L6; `src/thoth/providers/__init__.py`
- **Related:** GAP-003, GAP-006, DEC-002, INC-001

<a id="gap-009"></a>

### GAP-009 - `stop_sequences` Is Not Normalized Across Providers

- **Description:** The desired internal stop-sequence field is not translated to supported provider-native fields consistently.
- **Kind:** gap
- **Status:** open
- **Layers affected:** L4, L5, L6, L7
- **Providers affected:** Perplexity, Gemini
- **Source:** `src/thoth/providers/openai.py:55-64`; `src/thoth/providers/perplexity.py:388-394`; `src/thoth/providers/perplexity.py:520-528`; `src/thoth/providers/perplexity.py:591-596`; `src/thoth/providers/gemini.py:58-76`
- **Context:** OpenAI Responses does not expose `stop`/`stop_sequences` on the canonical surface, but Perplexity and Gemini both support stop sequences using different native names.
- **Detail:** Perplexity wires native `stop` for sync and async namespace paths, but the internal desired name `stop_sequences` is not normalized to `stop`. Gemini wires `gemini.stop_sequences` through `GenerateContentConfig`, but common L4/L6 `stop_sequences` is not routed into the Gemini namespace until shared normalization exists. OpenAI should continue to report unsupported for the Responses surface.
- **Recommendation:** Keep `stop_sequences` in the fixed L4/L6 common set only for providers that support it. Adapter normalization should emit Perplexity `stop` / `request.stop`, Gemini `config.stop_sequences`, and omit or reject the field for OpenAI Responses with a clear compatibility rule.
- **References:** matrix row `stop_sequences`; DEC-001; matrix section Configuration Layers L4/L6; `src/thoth/providers/__init__.py`
- **Related:** GAP-003, GAP-006, INC-001

<a id="gap-010"></a>

### GAP-010 - Gemini `frequency_penalty` Is Not Wired

- **Description:** Gemini supports `frequencyPenalty`, but the Gemini adapter allowlist omits `frequency_penalty`.
- **Kind:** gap
- **Status:** open
- **Layers affected:** L5, L7
- **Providers affected:** Gemini
- **Source:** `src/thoth/providers/gemini.py:58-76`; `src/thoth/providers/gemini.py:313-320`
- **Context:** The desired matrix exposes Gemini `config.frequency_penalty` because the Google GenerateContent surface documents `frequencyPenalty`.
- **Detail:** `_DIRECT_SDK_KEYS_GEMINI` does not include `frequency_penalty`, so `[modes.X.gemini].frequency_penalty` is silently ignored by `_build_generate_content_config()`. OpenAI Responses and Perplexity Sonar do not expose this key on the canonical surfaces, so this is Gemini-specific adapter work rather than a cross-provider normalization issue.
- **Recommendation:** Add `frequency_penalty` to the Gemini direct SDK key allowlist, with tests that prove it reaches `GenerateContentConfig`. Keep matrix notes that model support may vary and rely on provider errors for unsupported model/config combinations.
- **References:** matrix row `frequency_penalty`; Gemini GenerateContent reference; `src/thoth/providers/gemini.py`
- **Related:** GAP-006, DEC-004

<a id="gap-011"></a>

### GAP-011 - Gemini `presence_penalty` Is Not Wired

- **Description:** Gemini supports `presencePenalty`, but the Gemini adapter allowlist omits `presence_penalty`.
- **Kind:** gap
- **Status:** open
- **Layers affected:** L5, L7
- **Providers affected:** Gemini
- **Source:** `src/thoth/providers/gemini.py:58-76`; `src/thoth/providers/gemini.py:313-320`
- **Context:** The desired matrix exposes Gemini `config.presence_penalty` because the Google GenerateContent surface documents `presencePenalty`.
- **Detail:** `_DIRECT_SDK_KEYS_GEMINI` does not include `presence_penalty`, so `[modes.X.gemini].presence_penalty` is silently ignored by `_build_generate_content_config()`. OpenAI Responses and Perplexity Sonar do not expose this key on the canonical surfaces, so this is Gemini-specific adapter work rather than a cross-provider normalization issue.
- **Recommendation:** Add `presence_penalty` to the Gemini direct SDK key allowlist, with tests that prove it reaches `GenerateContentConfig`. Keep matrix notes that model support may vary and rely on provider errors for unsupported model/config combinations.
- **References:** matrix row `presence_penalty`; Gemini GenerateContent reference; `src/thoth/providers/gemini.py`
- **Related:** GAP-006, DEC-004

## Inconsistencies (`INC-`)

An inconsistency means a behavior exists, but the semantics differ across layers or providers. Triage by deciding the canonical behavior and then making every provider/layer obey that one contract. Each `INC-*` entry includes context, detailed impact, a recommended direction, and concrete resolution choices so it can be converted directly into a plan.

| ID | Title | Description | Status | Recommendation | Choices | References |
|---|---|---|---|---|---|---|
| INC-001 | L4 flat mode params are copied but consumed unevenly | Common flat params such as `temperature` are copied, but OpenAI, Perplexity sync/async, and Gemini consume them through different paths. | accepted | Define L4 as a small common set and route it through the normalizer. | A fixed common set accepted | matrix L4/L6; DEC-001 |
| INC-002 | Root provider defaults behave differently by provider | OpenAI can half-read root flat values, while Perplexity/Gemini generally require provider namespaces for request params. | accepted | Treat `[providers.NAME]` as the root provider namespace with recognized auth/client fields and recognized request-default fields. | A mixed recognized fields accepted | GAP-001; DEC-004 |
| INC-003 | Provider namespace unknown-key policy diverges | Perplexity forwards unknown namespace keys, Gemini allowlists, and OpenAI reads only explicit keys. | accepted | Validate known keys and require explicit extension bags for arbitrary passthrough. | A extension bags accepted | DEC-004 |
| INC-004 | Built-in mode overrides are shallow | User mode overlays replace nested built-in provider namespaces instead of deep-merging them. | accepted | Deep-merge mode dictionaries consistently with global config layers. | A deep merge accepted | DEC-006 |
| INC-005 | Runtime timeout has provider-specific effects | OpenAI and Perplexity use timeout in client construction; Gemini currently does not. | accepted | Make `timeout` a required provider client/runtime control. | A wire all providers accepted | GAP-005 |
| INC-006 | Runtime provider override can mismatch mode model and namespace | `--provider` can select a provider while retaining the selected mode's model and unrelated provider namespace. | accepted | Treat `--provider` as an expert override and document that model/namespace may also need explicit overrides. | C expert override accepted | DEC-005 |
| INC-007 | L9 is OpenAI-only while main providers are multi-provider | Clarification has its own OpenAI Chat Completions path instead of the shared OpenAI/Perplexity/Gemini stack. | accepted | Keep L9 UX config separate but reuse provider normalization for model calls. | A reuse normalizer accepted | GAP-007; DEC-003 |
| INC-008 | Documentation and tests disagree on root provider defaults | Auth help documents provider tables as API-key-only while skipped tests describe desired request defaults. | accepted | Align docs, skipped tests, and matrix to `INC-002`; keep runtime work tracked by `GAP-001`. | A align to INC-002 accepted | GAP-001; INC-002 |
| INC-009 | Perplexity `search_context_size` needs upstream validation | Local built-ins and adapter defaults use `web_search_options.search_context_size`, and current Perplexity Sonar docs validate it as a request option. | accepted | Keep `search_context_size` as a first-class Perplexity row with current-doc citations. | A validate and keep accepted | DEC-004 |
| INC-010 | OpenAI `system_prompt` uses developer-role input instead of `instructions` | Desired state names OpenAI `instructions`, while current code sends an equivalent developer-role input message. | accepted | Use top-level `instructions` for OpenAI `system_prompt` during adapter normalization. | A switch to `instructions` accepted | matrix row `system_prompt` |

<a id="inc-001"></a>

### INC-001 - L4 Flat Mode Params Are Copied But Consumed Unevenly

- **Description:** Common flat params such as `temperature` are copied, but OpenAI, Perplexity sync/async, and Gemini consume them through different paths.
- **Kind:** inconsistency
- **Status:** accepted
- **Layers affected:** L4, L6
- **Providers affected:** OpenAI, Perplexity, Gemini
- **Source:** `src/thoth/providers/__init__.py:85-95`; `src/thoth/providers/openai.py:246-281`; `tests/test_provider_perplexity.py:221-253`; `src/thoth/providers/gemini.py:292-320`
- **Context:** L4/L6 are the only provider-neutral places in the proposed stack where a user can say "for this mode, use this common inference parameter" without repeating provider namespaces. The current implementation also uses this flat location as a broad passthrough bucket.
- **Detail:** The factory copies flat mode keys into provider config after skipping metadata and provider names. OpenAI reads namespace values first, then copied flat keys through `_resolve_provider_config_value()` with a `DeprecationWarning`. Perplexity sync reads namespace values first, then root/flat provider config for direct SDK keys, while Perplexity async forwards only the `perplexity` namespace into `request.*`. Gemini only reads `config["gemini"]`. The practical result is that `[modes.brief] temperature = 0.2` can affect OpenAI, affect Perplexity sync through a different fallback path, be ignored by Perplexity async, and be ignored by Gemini even though the config shape looks provider-neutral.
- **Recommendation:** Define L4/L6 as a small fixed common parameter set and route those keys through a shared normalizer before adapter translation. Keep provider-specific fields in L5/L7 namespaces. Add deprecation handling for any historical flat keys that are not in the common set.
- **Resolution choices:** Option A accepted: fixed common set for L4/L6, provider namespaces for everything else. Rejected for now: Option B, remove flat common params entirely; Option C, keep broad flat passthrough temporarily.
- **References:** matrix section Configuration Layers L4/L6; matrix rows `temperature`, `top_p`; DEC-001
- **Related:** GAP-002, GAP-003

<a id="inc-002"></a>

### INC-002 - Root Provider Defaults Behave Differently By Provider

- **Description:** OpenAI can half-read root flat values, while Perplexity/Gemini generally require provider namespaces for request params.
- **Kind:** inconsistency
- **Status:** accepted
- **Layers affected:** L2, L3
- **Providers affected:** OpenAI, Perplexity, Gemini
- **Source:** `planning/p24-providers-root-namespace-investigation.v1.md:43-57`; `src/thoth/providers/openai.py:246-281`; `src/thoth/providers/perplexity.py:495-523`; `src/thoth/providers/gemini.py:292-320`
- **Context:** L2/L3 are meant to hold provider-scoped defaults that apply before mode overrides. This is the layer users naturally reach for when they want "all OpenAI calls use this default unless a mode overrides it."
- **Detail:** Root provider tables are copied into `provider.config`, so `[providers.openai].temperature = 0.3` is physically present on the OpenAI provider. OpenAI can resolve that flat key, but it cannot distinguish a root provider default from deprecated mode-flat passthrough, so it emits misleading migration guidance. Perplexity and Gemini request construction generally reads `config["perplexity"]` and `config["gemini"]`, so root flat defaults are not equivalent across providers.
- **Recommendation:** Treat `[providers.NAME]` as the root provider namespace, not as a separate `.defaults` table. It may contain recognized auth/client fields such as `api_key` and `timeout` plus recognized request-default fields such as `temperature`, provider token-budget keys, or provider-native request fields. The desired-state docs should classify every recognized root key by category, provider key path, precedence, and whether it participates in request normalization.
- **Resolution choices:** Option A accepted: root `[providers.NAME]` supports mixed recognized fields, and the normalizer separates auth/client controls from request defaults by a known-field registry before provider adapters build SDK payloads. Rejected: Option B, make `[providers.NAME]` auth/client-only; Option C, add a `[providers.NAME.defaults]` table that modes do not mirror.
- **References:** matrix section Configuration Layers L2-L3; GAP-001; DEC-004
- **Related:** GAP-001, INC-008

<a id="inc-003"></a>

### INC-003 - Provider Namespace Unknown-Key Policy Diverges

- **Description:** Perplexity forwards unknown namespace keys, Gemini allowlists, and OpenAI reads only explicit keys.
- **Kind:** inconsistency
- **Status:** accepted
- **Layers affected:** L5, L7
- **Providers affected:** OpenAI, Perplexity, Gemini
- **Source:** `src/thoth/providers/openai.py:246-281`; `src/thoth/providers/perplexity.py:484-508`; `src/thoth/providers/gemini.py:58-76`; `src/thoth/providers/gemini.py:313-320`
- **Context:** L5/L7 are provider-native escape hatches. They need to support fast vendor evolution without allowing silent typos to become invisible no-ops.
- **Detail:** Perplexity treats remaining namespace keys as `extra_body`, which is useful for provider extension fields. Gemini only passes keys in `_DIRECT_SDK_KEYS_GEMINI`, and `_build_tools()` silently skips unknown tool names. OpenAI has explicit read sites rather than a general namespace-to-SDK mapper. The same typo or newly released vendor key therefore has three outcomes: forwarded, ignored, or unavailable unless code is updated.
- **Recommendation:** Split provider namespace handling into known-key validation plus explicit extension bags. Common and known provider keys should be validated. Arbitrary pass-through should be confined to documented shapes such as `[modes.X.perplexity.extra_body]` or `[modes.X.openai.extra]`.
- **Resolution choices:** Option A accepted: validate known keys and allow explicit extension bags for arbitrary provider-native fields. Rejected: Option B, strict allowlist everywhere; Option C, keep provider-specific policies as permanent behavior.
- **References:** matrix section Resolution Rules; matrix section Parameter Matrix; DEC-004
- **Related:** GAP-003, GAP-006

<a id="inc-004"></a>

### INC-004 - Built-In Mode Overrides Are Shallow

- **Description:** User mode overlays replace nested built-in provider namespaces instead of deep-merging them.
- **Kind:** inconsistency
- **Status:** accepted
- **Layers affected:** L1, L4, L5, L6, L7
- **Providers affected:** Perplexity, Gemini, OpenAI built-ins with provider namespaces
- **Source:** `src/thoth/config.py:659-688`; `src/thoth/config.py:174-228`
- **Context:** Built-in modes define provider namespaces for provider-specific defaults, such as Gemini tools/thinking budget and Perplexity search settings. Users should be able to override one nested value without accidentally deleting the rest of the built-in provider defaults.
- **Detail:** Global config layers deep-merge dictionaries, but `get_mode_config()` uses `mode_config.update(user_mode)` when overlaying user mode config onto a built-in mode. If a user adds `[modes.gemini_quick.gemini] temperature = 0.2`, that nested table can replace the built-in Gemini namespace instead of merging with `tools = ["google_search"]` and `thinking_budget = 0`. This makes mode overrides less predictable than normal config layer overrides.
- **Recommendation:** Deep-merge built-in mode dictionaries and user/profile mode overrides using the same semantics as the main config layer merge. Arrays should still follow the separately documented array replacement policy.
- **Resolution choices:** Option A accepted: deep-merge mode dictionaries consistently with global config layers. Rejected: Option B, preserve full-table replacement with documentation; Option C, require users to copy built-in modes before editing.
- **References:** matrix section Resolution Rules; matrix section Worked Examples
- **Related:** DEC-006

<a id="inc-005"></a>

### INC-005 - Runtime Timeout Has Provider-Specific Effects

- **Description:** OpenAI and Perplexity use timeout in client construction; Gemini currently does not.
- **Kind:** inconsistency
- **Status:** accepted
- **Layers affected:** L2, L3, L8
- **Providers affected:** Gemini compared with OpenAI and Perplexity
- **Source:** `src/thoth/providers/__init__.py:188-190`; `src/thoth/providers/openai.py:242-244`; `src/thoth/providers/perplexity.py:406-422`; `src/thoth/providers/gemini.py:213-221`
- **Context:** `timeout` is a framework/client control, not a model payload parameter. Users expect it to work uniformly because it is surfaced as a runtime override and copied for all production providers.
- **Detail:** Timeout is routed through the factory for OpenAI, Perplexity, and Gemini. OpenAI and Perplexity consume it while constructing their clients. Gemini stores the value in config but constructs `genai.Client(api_key=api_key)` without applying timeout to the SDK client or request options. This makes `--timeout` look provider-neutral while having no Gemini effect.
- **Recommendation:** Make `timeout` part of the provider client contract and require every provider adapter to either apply it or explicitly declare it unsupported with a clear warning/error.
- **Resolution choices:** Option A accepted: wire timeout for every provider and cover it with constructor/request tests. Rejected: Option B, document Gemini timeout as unsupported; Option C, split timeout into provider-specific controls.
- **References:** matrix row `timeout`; GAP-005
- **Related:** GAP-005

<a id="inc-006"></a>

### INC-006 - Runtime Provider Override Can Mismatch Mode Model And Namespace

- **Description:** `--provider` can select a provider while retaining the selected mode's model and unrelated provider namespace.
- **Kind:** inconsistency
- **Status:** accepted
- **Layers affected:** L5, L7, L8
- **Providers affected:** all
- **Source:** `src/thoth/run.py:188-220`; `src/thoth/run.py:319-344`; `src/thoth/providers/__init__.py:192-202`
- **Context:** `--provider` is useful for testing and quick provider switching, but modes are often provider-specific because they pin a native model and provider namespace. The override boundary must prevent accidental cross-provider request shapes.
- **Detail:** Provider selection can be forced by `--provider`, and the selected mode's `model` is still copied into provider config before construction. A forced provider can therefore receive a model intended for another provider, while the forced provider namespace may be absent and the original namespace remains irrelevant. Example risk: forcing `--provider gemini` on a Perplexity mode can send Gemini a `sonar` model unless another override intervenes.
- **Recommendation:** Treat `--provider` as an expert override that changes provider selection only. Documentation and diagnostics should make clear that the mode's `model` and provider namespace do not become provider-neutral automatically; users must also pass `--model` or choose a compatible mode when needed.
- **Resolution choices:** Option C accepted: keep permissive expert override behavior, document that provider/model/namespace may mismatch, and add diagnostics in verbose mode. Rejected: Option A, validate and error on provider/model/namespace mismatch; Option B, allow `--provider` only when paired with `--model` if the mode pins a different provider.
- **References:** matrix section Resolution Rules; DEC-005
- **Related:** DEC-005

<a id="inc-007"></a>

### INC-007 - L9 Is OpenAI-Only While Main Providers Are Multi-Provider

- **Description:** Clarification has its own OpenAI Chat Completions path instead of the shared OpenAI/Perplexity/Gemini stack.
- **Kind:** inconsistency
- **Status:** accepted
- **Layers affected:** L9
- **Providers affected:** OpenAI only today; all if generalized
- **Source:** `src/thoth/config.py:345-365`; `src/thoth/interactive.py:857-909`
- **Context:** L9 is a real level because clarification has its own config subtree with model parameters, retry policy, prompt text, and UI controls. It is not part of the main provider/mode stack, but it still makes LLM requests.
- **Detail:** L9 has model, temperature, max-token, prompt, retry, and UI fields. Its provider field currently does not route through `create_provider()` or the provider registry, so it is a separate parameter subsystem. That means clarification uses OpenAI-specific auth and Chat Completions request construction even though the rest of the app is moving toward OpenAI, Perplexity, and Gemini parity.
- **Recommendation:** Keep L9 as a separate UX subsystem, but route the LLM call through the same provider normalizer and adapter dispatch used by main requests. UI-only fields should stay outside provider normalization.
- **Resolution choices:** Option A accepted: preserve L9 as a separate config area but reuse shared provider normalization for the model call. Rejected: Option B, keep the OpenAI-only path; Option C, fold clarification into normal modes.
- **References:** matrix section Configuration Layers L9; DEC-003
- **Related:** GAP-007

<a id="inc-008"></a>

### INC-008 - Documentation And Tests Disagree On Root Provider Defaults

- **Description:** Auth help documents provider tables as API-key-only while skipped tests describe desired request defaults.
- **Kind:** inconsistency
- **Status:** accepted
- **Layers affected:** L2, L3
- **Providers affected:** OpenAI, Perplexity, Gemini
- **Source:** `planning/p24-providers-root-namespace-investigation.v1.md:35-41`; `tests/test_provider_config.py:541-672`
- **Context:** Root provider defaults were investigated and punted. The codebase now has aspirational skipped tests, a planning note, and user-facing docs that do not all describe the same contract.
- **Detail:** The root provider default question is visible in skipped tests and planning docs, but the user-facing auth docs still describe provider tables primarily as auth configuration. This is expected while the feature is punted, but it means documentation cannot yet be used as a complete config contract. A future implementer could reasonably follow either the docs or the skipped tests and make a different choice.
- **Recommendation:** Align README/help text, skipped tests, and the matrix to `INC-002`: root `[providers.NAME]` is a mixed recognized-field namespace that can contain auth/client controls and request-default fields. Clearly mark the runtime implementation as incomplete until `GAP-001` is resolved.
- **Resolution choices:** Option A accepted: align docs, skipped tests, and matrix to `INC-002` while keeping runtime implementation work tracked by `GAP-001`. Rejected: Option B, implement root provider defaults in the docs pass; Option C, remove aspirational skipped tests and document root provider tables as auth/client-only.
- **References:** matrix section Configuration Layers L2-L3; GAP-001; INC-002; `projects/P24-gemini-immediate-sync.md` P24-T26
- **Related:** GAP-001, INC-002

<a id="inc-009"></a>

### INC-009 - Perplexity `search_context_size` Needs Upstream Validation

- **Description:** Local built-ins and adapter defaults use `web_search_options.search_context_size`, and current Perplexity Sonar docs validate it as a request option.
- **Kind:** inconsistency
- **Status:** accepted
- **Layers affected:** L1, L5, L7
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
- **Layers affected:** L1, L4, L6
- **Providers affected:** OpenAI
- **Source:** `src/thoth/providers/openai.py:334-342`; `src/thoth/providers/openai.py:567-579`
- **Context:** OpenAI Responses accepts both top-level `instructions` and input messages with `developer`/`system` roles for system-level guidance. The matrix should document one canonical adapter output path rather than listing multiple encodings ambiguously.
- **Detail:** Current OpenAI submit and stream paths prepend `system_prompt` to `input` as a developer-role message. The desired matrix now names `instructions` as the canonical OpenAI key because it is the dedicated Responses API field for system/developer instructions and avoids overloading `input` with two internal concepts (`prompt` and `system_prompt`). This is not a behavior bug today, but it is a normalization mismatch to resolve when provider adapters are centralized.
- **Recommendation:** During adapter normalization, map internal `system_prompt` to OpenAI `instructions` and reserve `input` for user/content messages. Keep a compatibility test proving the semantic output is unchanged.
- **Resolution choices:** Option A accepted: switch OpenAI adapter output to top-level `instructions`. Rejected: Option B, define developer-role input as OpenAI's canonical encoding; Option C, allow both encodings in docs while emitting one path per request.
- **References:** matrix row `system_prompt`; OpenAI Responses create reference `https://platform.openai.com/docs/api-reference/responses`; `src/thoth/providers/openai.py`
- **Related:** GAP-003, DEC-009, DEC-010

## Decisions (`DEC-`)

Decision entries are design choices whose resolution can spawn specific `GAP-` or `INC-` remediation work. `proposed` entries still need agreement; `accepted` entries record a contract already reflected in the matrix so downstream work can cite the decision.

| ID | Title | Description | Status | Recommendation | References |
|---|---|---|---|---|---|
| DEC-001 | Define L4 flat common params or deprecate flat passthrough | Decide whether flat mode keys are a fixed common set or arbitrary provider passthrough. | proposed | Fixed common set plus provider namespaces for everything else. | matrix section Configuration Layers L4/L6 |
| DEC-002 | Normalize max token split forms | Decide whether users configure one internal token budget or expose every provider spelling. | proposed | Use internal `max_output_tokens`; adapters map native spellings. | matrix row `max_output_tokens` |
| DEC-003 | L9 clarification integration boundary | Decide whether clarification folds into the provider stack or remains separate while reusing normalization. | proposed | Keep L9 separate as UX config, but invoke shared provider normalization for model calls. | matrix section Configuration Layers L9 |
| DEC-004 | Unknown-key and extension policy | Decide which unknown provider namespace keys pass through, fail validation, or are ignored. | proposed | Validate known common keys; allow explicit provider extension bags. | matrix section Resolution Rules |
| DEC-005 | Provider override mismatch policy | Decide how `--provider` interacts with a mode's provider-specific model and namespace. | proposed | Validate compatibility and require explicit `--model` or provider-native mode when switching provider families. | matrix section Resolution Rules |
| DEC-006 | Array merge and unset semantics | Decide array replacement vs append and absence vs explicit-disable semantics. | proposed | Arrays replace; absence inherits; explicit disable only through named booleans or internal `None`. | matrix section Resolution Rules |
| DEC-007 | No global all-provider root defaults | Decide whether to keep excluding a generic inherited provider defaults layer. | proposed | Do not add `[providers.defaults]`; use L4/L6 common mode params instead. | matrix section Overview |
| DEC-008 | Matrix cell target type | Decide whether the matrix should mix request payload keys with client/runtime controls. | accepted | Split request payload keys from framework/client controls. | matrix section Parameter Matrix |
| DEC-009 | Canonical provider endpoint scope | Decide which endpoint surface each provider column represents when a provider has multiple APIs. | accepted | Name the canonical provider surfaces before the table. | matrix section Parameter Matrix |
| DEC-010 | SDK key casing vs REST key casing | Decide whether provider cells use Python SDK key names, REST JSON names, or both. | accepted | Use Thoth's SDK request shape, with REST casing noted where different. | matrix section Parameter Matrix |

<a id="dec-001"></a>

### DEC-001 - Define L4 Flat Common Params Or Deprecate Flat Passthrough

- **Description:** Decide whether flat mode keys are a fixed common set or arbitrary provider passthrough.
- **Kind:** decision
- **Status:** proposed
- **Layers affected:** L4, L6
- **Providers affected:** all
- **Source:** `src/thoth/providers/__init__.py:48-95`; `tests/test_provider_perplexity.py:221-253`; `src/thoth/providers/gemini.py:292-320`
- **Detail:** Current flat passthrough creates provider-specific behavior from a provider-neutral location. The desired matrix treats L4/L6 as a fixed common set.
- **References:** matrix section Configuration Layers L4/L6; matrix section Parameter Matrix
- **Related:** GAP-002, INC-001
- **Recommendation:** Define a fixed common set (`temperature`, `top_p`, `max_output_tokens`, `stop_sequences`, plus any later explicitly accepted common params). Deprecate arbitrary flat passthrough and require provider namespaces for provider-specific fields.

<a id="dec-002"></a>

### DEC-002 - Normalize Max Token Split Forms

- **Description:** Decide whether users configure one internal token budget or expose every provider spelling.
- **Kind:** decision
- **Status:** proposed
- **Layers affected:** L2-L8
- **Providers affected:** OpenAI, Perplexity, Gemini
- **Source:** `src/thoth/providers/perplexity.py:388-394`; `src/thoth/providers/gemini.py:58-76`; `src/thoth/providers/openai.py:55-64`
- **Detail:** Providers use different names: OpenAI Responses uses `max_output_tokens`, Perplexity uses `max_tokens`, and Gemini uses `max_output_tokens`. OpenAI Chat Completions variants may use other names. Exposing every spelling makes config provider-specific even at L4.
- **References:** matrix row `max_output_tokens`; matrix section Per-Parameter Detail
- **Related:** GAP-006, GAP-008
- **Recommendation:** Use internal `max_output_tokens` everywhere outside provider namespaces. Adapters translate to the native field, and provider-specific aliases are accepted only as migration aliases or under namespaces.

<a id="dec-003"></a>

### DEC-003 - L9 Clarification Integration Boundary

- **Description:** Decide whether clarification folds into the provider stack or remains separate while reusing normalization.
- **Kind:** decision
- **Status:** proposed
- **Layers affected:** L9
- **Providers affected:** OpenAI today; all if generalized
- **Source:** `src/thoth/config.py:345-365`; `src/thoth/interactive.py:857-909`
- **Detail:** Clarification has UI and retry fields that do not belong in normal provider request config. But its model call should not need a separate auth, provider, and parameter path forever.
- **References:** matrix section Configuration Layers L9; GAP-007; INC-007
- **Related:** GAP-007, INC-007
- **Recommendation:** Keep L9 as a separate UX subsystem for fields like `input_height`, `max_input_height`, retry policy, and prompt text. For the LLM call inside L9, reuse the shared provider normalizer and adapter dispatch.

<a id="dec-004"></a>

### DEC-004 - Unknown-Key And Extension Policy

- **Description:** Decide which unknown provider namespace keys pass through, fail validation, or are ignored.
- **Kind:** decision
- **Status:** proposed
- **Layers affected:** L2, L3, L5, L7
- **Providers affected:** OpenAI, Perplexity, Gemini
- **Source:** `src/thoth/providers/openai.py:246-281`; `src/thoth/providers/perplexity.py:484-508`; `src/thoth/providers/gemini.py:58-76`; `tests/test_provider_config.py:615-638`
- **Detail:** Perplexity's API has a broad extension surface that benefits from pass-through. Gemini's typed SDK path benefits from validation/allowlisting. OpenAI currently has explicit read sites. A single policy must still allow provider-specific escape hatches.
- **References:** matrix section Resolution Rules; matrix section Parameter Matrix; GAP-006; INC-003
- **Related:** GAP-001, INC-003
- **Recommendation:** Validate common parameters through the shared matrix. For provider-native extension fields, define explicit extension bags such as `[modes.X.perplexity.extra_body]` or a documented provider allowlist. Do not silently ignore unknown keys unless a provider marks a nested namespace as forward-compatible.

<a id="dec-005"></a>

### DEC-005 - Provider Override Mismatch Policy

- **Description:** Decide how `--provider` interacts with a mode's provider-specific model and namespace.
- **Kind:** decision
- **Status:** proposed
- **Layers affected:** L5, L7, L8
- **Providers affected:** all
- **Source:** `src/thoth/run.py:188-220`; `src/thoth/run.py:319-344`; `src/thoth/providers/__init__.py:192-202`
- **Detail:** Runtime provider override is useful, but retaining a mode's model and provider namespace can create invalid cross-provider payloads.
- **References:** matrix section Resolution Rules; INC-006
- **Related:** INC-006
- **Recommendation:** Treat `--provider` as selecting a provider only when the selected mode is provider-neutral. If the mode pins a provider-specific model or namespace, require `--model` with a compatible provider model or error with a clear mode/provider mismatch message.

<a id="dec-006"></a>

### DEC-006 - Array Merge And Unset Semantics

- **Description:** Decide array replacement vs append and absence vs explicit-disable semantics.
- **Kind:** decision
- **Status:** proposed
- **Layers affected:** L1-L8
- **Providers affected:** all
- **Source:** `src/thoth/config.py:544-565`; `src/thoth/config.py:659-688`
- **Detail:** Global config layers deep-merge dictionaries and replace non-dicts, but mode overlay is shallow. Arrays such as `tools`, `stop_sequences`, and domain filters need predictable replacement behavior.
- **References:** matrix section Resolution Rules
- **Related:** INC-004
- **Recommendation:** Arrays replace by default. Absence means inherit. Explicit disable uses named booleans like `web_search = false`, empty arrays where an empty array is semantically valid, or internal `None` for APIs that distinguish null from unset.

<a id="dec-007"></a>

### DEC-007 - No Global All-Provider Root Defaults

- **Description:** Decide whether to keep excluding a generic inherited provider defaults layer.
- **Kind:** decision
- **Status:** proposed
- **Layers affected:** potential new layer between L1 and L2
- **Providers affected:** all
- **Source:** `src/thoth/config.py:341-344`; `planning/p24-providers-root-namespace-investigation.v1.md:62-69`
- **Detail:** The current stack has root per-provider tables, but no `[providers.defaults]` table inherited by all providers. Adding one would create another cross-provider precedence layer and overlap with L4/L6 common mode params.
- **References:** matrix section Overview; matrix section Configuration Layers
- **Related:** DEC-001
- **Recommendation:** Do not add a global all-provider root default layer. Keep cross-provider request defaults mode-scoped through L4/L6 so model/provider selection remains explicit.

<a id="dec-008"></a>

### DEC-008 - Matrix Cell Target Type

- **Description:** Decide whether the matrix should mix request payload keys with client/runtime controls.
- **Kind:** decision
- **Status:** accepted
- **Layers affected:** L2-L9
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
- **Layers affected:** L0-L8
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
- **Layers affected:** L5, L7, L8
- **Providers affected:** OpenAI, Perplexity, Gemini
- **Source:** `src/thoth/providers/gemini.py`; `planning/inference_provider_parameter_config_matrix.md`
- **Detail:** Gemini in particular differs between Python SDK snake_case and REST camelCase. Since Thoth's adapters use Python SDKs for OpenAI and Gemini and the OpenAI-compatible SDK for Perplexity sync, the matrix should not switch casing silently between rows.
- **References:** matrix section Parameter Matrix
- **Related:** DEC-009
- **Recommendation:** Use Thoth's SDK request shape in provider cells and note REST casing where it differs.

## Migration Notes

No entries are resolved yet. When an entry is accepted or resolved, add a migration note here with:

- the resolving ID,
- the old config shape,
- the new config shape,
- whether behavior changes silently or emits a deprecation warning first,
- the code/docs/tests that were updated.

Expected future migrations:

- `DEC-001` / `INC-001`: move arbitrary flat mode request keys into provider namespaces or the fixed L4 common set.
- `DEC-002` / `GAP-006`: normalize token limit keys to `max_output_tokens`.
- `GAP-001` / `INC-002`: define whether `[providers.NAME]` request defaults feed provider namespaces or only auth/client settings.
- `DEC-005` / `INC-006`: tighten `--provider` mismatch behavior.

## Driving Downstream Documents

Every accepted or resolved entry should update each reference target and cite the resolving ID in the target document, test, code comment, or ticket. The top-level index is the punch list for matrix updates, ADRs, implementation tasks, and docs changes.
