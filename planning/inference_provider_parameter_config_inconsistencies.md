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
| GAP-001 | gap | Root provider request defaults are not normalized | L2/L3 request defaults are copied but not normalized into a provider-consistent request structure. | open | matrix section Configuration Layers L2-L3; matrix section Resolution Rules |
| GAP-002 | gap | Fixed L4 common parameter set is missing | Mode-level flat keys are arbitrary passthrough rather than a documented common parameter set. | open | matrix section Configuration Layers L4/L6; DEC-001 |
| GAP-003 | gap | Shared normalized provider parameter object is missing | `create_provider()` mutates provider config but leaves each adapter to interpret shapes independently. | open | matrix section Resolution Rules; code `src/thoth/providers/__init__.py` |
| GAP-004 | gap | Gemini missing from config defaults provider table | The defaults provider table declares OpenAI and Perplexity API keys but omits Gemini. | open | matrix section Configuration Layers L2; code `src/thoth/config.py` |
| GAP-005 | gap | Gemini timeout override is not applied to the SDK client | Runtime timeout is copied into Gemini config but Gemini client construction does not consume it. | open | matrix row `timeout`; code `src/thoth/providers/gemini.py` |
| GAP-006 | gap | Full parameter matrix is not wired through adapters | Several desired matrix parameters have no adapter translation path. | open | matrix section Parameter Matrix |
| GAP-007 | gap | L9 clarification bypasses shared provider normalization | Interactive clarification reads OpenAI config directly and constructs `AsyncOpenAI` directly. | open | matrix section Configuration Layers L9; DEC-003 |
| INC-001 | inconsistency | L4 flat mode params are copied but consumed unevenly | OpenAI reads flat mode params with a warning, while Perplexity and Gemini ignore flat direct SDK keys. | open | matrix section Configuration Layers L4/L6; DEC-001 |
| INC-002 | inconsistency | Root provider defaults behave differently by provider | OpenAI can half-read root flat values, while Perplexity/Gemini generally require provider namespaces for request params. | open | matrix section Configuration Layers L2/L3; GAP-001 |
| INC-003 | inconsistency | Provider namespace unknown-key policy diverges | Perplexity forwards unknown namespace keys, Gemini allowlists, and OpenAI reads only explicit keys. | open | matrix section Resolution Rules; DEC-004 |
| INC-004 | inconsistency | Built-in mode overrides are shallow | User mode overlays replace nested built-in provider namespaces instead of deep-merging them. | open | matrix section Resolution Rules |
| INC-005 | inconsistency | Runtime timeout has provider-specific effects | OpenAI and Perplexity use timeout in client construction; Gemini currently does not. | open | matrix row `timeout`; GAP-005 |
| INC-006 | inconsistency | Runtime provider override can mismatch mode model and namespace | `--provider` can select a provider while retaining the selected mode's model and unrelated provider namespace. | open | matrix section Resolution Rules; DEC-005 |
| INC-007 | inconsistency | L9 is OpenAI-only while main providers are multi-provider | Clarification has its own OpenAI Chat Completions path instead of the shared OpenAI/Perplexity/Gemini stack. | open | matrix section Configuration Layers L9; DEC-003 |
| INC-008 | inconsistency | Documentation and tests disagree on root provider defaults | Auth help documents provider tables as API-key-only while skipped tests describe desired request defaults. | open | matrix section Configuration Layers L2-L3; GAP-001 |
| INC-009 | inconsistency | Perplexity `search_context_size` needs upstream validation | Local built-ins and adapter defaults use `web_search_options.search_context_size`, but the current Sonar API reference does not clearly list it as a request-body field. | open | matrix row `search_context_size`; DEC-004 |
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
| GAP-001 | Root provider request defaults are not normalized | L2/L3 request defaults are copied but not normalized into a provider-consistent request structure. | open | matrix section Configuration Layers L2-L3 |
| GAP-002 | Fixed L4 common parameter set is missing | Mode-level flat keys are arbitrary passthrough rather than a documented common parameter set. | open | matrix section Configuration Layers L4/L6 |
| GAP-003 | Shared normalized provider parameter object is missing | `create_provider()` mutates provider config but leaves each adapter to interpret shapes independently. | open | matrix section Resolution Rules |
| GAP-004 | Gemini missing from config defaults provider table | The defaults provider table declares OpenAI and Perplexity API keys but omits Gemini. | open | matrix section Configuration Layers L2 |
| GAP-005 | Gemini timeout override is not applied to the SDK client | Runtime timeout is copied into Gemini config but Gemini client construction does not consume it. | open | matrix row `timeout` |
| GAP-006 | Full parameter matrix is not wired through adapters | Several desired matrix parameters have no adapter translation path. | open | matrix section Parameter Matrix |
| GAP-007 | L9 clarification bypasses shared provider normalization | Interactive clarification reads OpenAI config directly and constructs `AsyncOpenAI` directly. | open | matrix section Configuration Layers L9 |

<a id="gap-001"></a>

### GAP-001 - Root Provider Request Defaults Are Not Normalized

- **Description:** L2/L3 request defaults are copied but not normalized into a provider-consistent request structure.
- **Kind:** gap
- **Status:** open
- **Layers affected:** L2, L3, L5, L7
- **Providers affected:** OpenAI, Perplexity, Gemini
- **Source:** `src/thoth/providers/__init__.py:174-202`; `tests/test_provider_config.py:541-672`; `planning/p24-providers-root-namespace-investigation.v1.md:7-69`
- **Detail:** `create_provider()` starts from `[providers.NAME]` and copies the whole table. That makes root request defaults appear to exist, but they are not normalized into the provider namespace before adapter consumption. The P24 investigation explicitly punted the design, and the root-namespace tests are skipped with desired assertions.
- **References:** matrix section Configuration Layers L2-L3; matrix section Resolution Rules; `planning/p24-providers-root-namespace-investigation.v1.md`; `tests/test_provider_config.py::test_root_providers_namespace_*`
- **Related:** INC-002, INC-008, DEC-004

<a id="gap-002"></a>

### GAP-002 - Fixed L4 Common Parameter Set Is Missing

- **Description:** Mode-level flat keys are arbitrary passthrough rather than a documented common parameter set.
- **Kind:** gap
- **Status:** open
- **Layers affected:** L4, L6
- **Providers affected:** all
- **Source:** `src/thoth/providers/__init__.py:48-95`; `tests/extended/test_provider_config_passthrough.py:19-50`
- **Detail:** The factory copies every non-metadata, non-provider-name key from a mode into provider config. That is a passthrough mechanism, not a fixed common parameter contract. The desired matrix narrows L4/L6 to explicit common parameters such as `temperature`, `top_p`, `max_output_tokens`, and `stop_sequences`.
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
- **Detail:** Current allowlists and explicit read sites cover a small subset: OpenAI handles fields such as `temperature` and `max_tool_calls`; Perplexity handles `max_tokens`, `temperature`, `top_p`, `stop`, and `response_format` plus extra-body pass-through; Gemini handles a larger generation config allowlist. Desired rows such as `frequency_penalty`, `presence_penalty`, `seed`, `n`, `logprobs`, `top_logprobs`, `user`, `service_tier`, and unified `max_output_tokens` need explicit adapter decisions.
- **References:** matrix section Parameter Matrix; matrix section Per-Parameter Detail
- **Related:** DEC-002, DEC-004

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

## Inconsistencies (`INC-`)

An inconsistency means a behavior exists, but the semantics differ across layers or providers. Triage by deciding the canonical behavior and then making every provider/layer obey that one contract. Each `INC-*` entry includes context, detailed impact, a recommended direction, and concrete resolution choices so it can be converted directly into a plan.

| ID | Title | Description | Status | Recommendation | Choices | References |
|---|---|---|---|---|---|---|
| INC-001 | L4 flat mode params are copied but consumed unevenly | OpenAI reads flat mode params with a warning, while Perplexity and Gemini ignore flat direct SDK keys. | open | Define L4 as a small common set and route it through the normalizer. | A fixed common set; B namespace-only; C compatibility passthrough | matrix L4/L6; DEC-001 |
| INC-002 | Root provider defaults behave differently by provider | OpenAI can half-read root flat values, while Perplexity/Gemini generally require provider namespaces for request params. | open | Treat L2/L3 as provider defaults normalized into provider namespaces. | A namespaced defaults; B auth/client-only; C flat passthrough | GAP-001; DEC-004 |
| INC-003 | Provider namespace unknown-key policy diverges | Perplexity forwards unknown namespace keys, Gemini allowlists, and OpenAI reads only explicit keys. | open | Validate known keys and require explicit extension bags for arbitrary passthrough. | A extension bags; B strict allowlists; C provider-specific policy | DEC-004 |
| INC-004 | Built-in mode overrides are shallow | User mode overlays replace nested built-in provider namespaces instead of deep-merging them. | open | Deep-merge mode dictionaries consistently with global config layers. | A deep merge; B replacement with docs; C copy built-ins before edits | DEC-006 |
| INC-005 | Runtime timeout has provider-specific effects | OpenAI and Perplexity use timeout in client construction; Gemini currently does not. | open | Make `timeout` a required provider client/runtime control. | A wire all providers; B document unsupported; C split per-provider timeout | GAP-005 |
| INC-006 | Runtime provider override can mismatch mode model and namespace | `--provider` can select a provider while retaining the selected mode's model and unrelated provider namespace. | open | Validate provider/model/namespace compatibility before construction. | A validate and error; B require `--model`; C allow expert override | DEC-005 |
| INC-007 | L9 is OpenAI-only while main providers are multi-provider | Clarification has its own OpenAI Chat Completions path instead of the shared OpenAI/Perplexity/Gemini stack. | open | Keep L9 UX config separate but reuse provider normalization for model calls. | A reuse normalizer; B separate OpenAI path; C fold into modes | GAP-007; DEC-003 |
| INC-008 | Documentation and tests disagree on root provider defaults | Auth help documents provider tables as API-key-only while skipped tests describe desired request defaults. | open | Make docs, skipped tests, and matrix state the same chosen contract. | A docs say deferred; B implement and document; C remove aspirational tests | GAP-001 |
| INC-009 | Perplexity `search_context_size` needs upstream validation | Local built-ins and adapter defaults use `web_search_options.search_context_size`, but the current Sonar API reference does not clearly list it as a request-body field. | open | Verify against current docs/live behavior before keeping it in the desired matrix. | A verify and keep; B remove; C unstable extension | DEC-004 |

<a id="inc-001"></a>

### INC-001 - L4 Flat Mode Params Are Copied But Consumed Unevenly

- **Description:** OpenAI reads flat mode params with a warning, while Perplexity and Gemini ignore flat direct SDK keys.
- **Kind:** inconsistency
- **Status:** open
- **Layers affected:** L4, L6
- **Providers affected:** OpenAI, Perplexity, Gemini
- **Source:** `src/thoth/providers/__init__.py:85-95`; `src/thoth/providers/openai.py:246-281`; `tests/test_provider_perplexity.py:221-253`; `src/thoth/providers/gemini.py:292-320`
- **Context:** L4/L6 are the only provider-neutral places in the proposed stack where a user can say "for this mode, use this common inference parameter" without repeating provider namespaces. The current implementation also uses this flat location as a broad passthrough bucket.
- **Detail:** The factory copies flat mode keys into provider config after skipping metadata and provider names. OpenAI still reads those copied flat keys through `_resolve_provider_config_value()`, but warns that the user should migrate to `[modes.X.openai]`. Perplexity tests assert flat direct SDK kwargs are ignored and only `[modes.X.perplexity]` direct SDK kwargs are consumed. Gemini only reads `config["gemini"]`. The practical result is that `[modes.brief] temperature = 0.2` can affect OpenAI, be ignored by Perplexity, and be ignored by Gemini even though the config shape looks provider-neutral.
- **Recommendation:** Define L4/L6 as a small fixed common parameter set and route those keys through a shared normalizer before adapter translation. Keep provider-specific fields in L5/L7 namespaces. Add deprecation handling for any historical flat keys that are not in the common set.
- **Resolution choices:** Option A (recommended): fixed common set for L4/L6, provider namespaces for everything else. Option B: remove flat common params entirely and require provider namespaces for all request controls. Option C: keep broad flat passthrough temporarily but require warnings and compatibility tests for each provider.
- **References:** matrix section Configuration Layers L4/L6; matrix row `temperature`; DEC-001
- **Related:** GAP-002, GAP-003

<a id="inc-002"></a>

### INC-002 - Root Provider Defaults Behave Differently By Provider

- **Description:** OpenAI can half-read root flat values, while Perplexity/Gemini generally require provider namespaces for request params.
- **Kind:** inconsistency
- **Status:** open
- **Layers affected:** L2, L3
- **Providers affected:** OpenAI, Perplexity, Gemini
- **Source:** `planning/p24-providers-root-namespace-investigation.v1.md:43-57`; `src/thoth/providers/openai.py:246-281`; `src/thoth/providers/perplexity.py:495-523`; `src/thoth/providers/gemini.py:292-320`
- **Context:** L2/L3 are meant to hold provider-scoped defaults that apply before mode overrides. This is the layer users naturally reach for when they want "all OpenAI calls use this default unless a mode overrides it."
- **Detail:** Root provider tables are copied into `provider.config`, so `[providers.openai].temperature = 0.3` is physically present on the OpenAI provider. OpenAI can resolve that flat key, but it cannot distinguish a root provider default from deprecated mode-flat passthrough, so it emits misleading migration guidance. Perplexity and Gemini request construction generally reads `config["perplexity"]` and `config["gemini"]`, so root flat defaults are not equivalent across providers.
- **Recommendation:** Treat L2/L3 as provider defaults that are normalized into the same provider namespace shape used by L5/L7, with lower precedence than mode values. Keep auth/client controls such as `api_key` and `timeout` framework-owned, not request passthrough.
- **Resolution choices:** Option A (recommended): `[providers.NAME]` request defaults normalize into the provider namespace and are overridden by modes. Option B: `[providers.NAME]` remains auth/client-only, and request defaults must live in modes. Option C: preserve flat root passthrough, but tag source layers so root defaults do not trigger mode-flat deprecation warnings.
- **References:** matrix section Configuration Layers L2-L3; GAP-001; DEC-004
- **Related:** GAP-001, INC-008

<a id="inc-003"></a>

### INC-003 - Provider Namespace Unknown-Key Policy Diverges

- **Description:** Perplexity forwards unknown namespace keys, Gemini allowlists, and OpenAI reads only explicit keys.
- **Kind:** inconsistency
- **Status:** open
- **Layers affected:** L5, L7
- **Providers affected:** OpenAI, Perplexity, Gemini
- **Source:** `src/thoth/providers/openai.py:246-281`; `src/thoth/providers/perplexity.py:484-508`; `src/thoth/providers/gemini.py:58-76`; `src/thoth/providers/gemini.py:313-320`
- **Context:** L5/L7 are provider-native escape hatches. They need to support fast vendor evolution without allowing silent typos to become invisible no-ops.
- **Detail:** Perplexity treats remaining namespace keys as `extra_body`, which is useful for provider extension fields. Gemini only passes keys in `_DIRECT_SDK_KEYS_GEMINI`, and `_build_tools()` silently skips unknown tool names. OpenAI has explicit read sites rather than a general namespace-to-SDK mapper. The same typo or newly released vendor key therefore has three outcomes: forwarded, ignored, or unavailable unless code is updated.
- **Recommendation:** Split provider namespace handling into known-key validation plus explicit extension bags. Common and known provider keys should be validated. Arbitrary pass-through should be confined to documented shapes such as `[modes.X.perplexity.extra_body]` or `[modes.X.openai.extra]`.
- **Resolution choices:** Option A (recommended): validate known keys and allow explicit extension bags for arbitrary provider-native fields. Option B: strict allowlist everywhere and require code changes for every new provider key. Option C: provider-specific policies, documented per adapter, with tests showing each behavior.
- **References:** matrix section Resolution Rules; matrix section Parameter Matrix; DEC-004
- **Related:** GAP-003, GAP-006

<a id="inc-004"></a>

### INC-004 - Built-In Mode Overrides Are Shallow

- **Description:** User mode overlays replace nested built-in provider namespaces instead of deep-merging them.
- **Kind:** inconsistency
- **Status:** open
- **Layers affected:** L1, L4, L5, L6, L7
- **Providers affected:** Perplexity, Gemini, OpenAI built-ins with provider namespaces
- **Source:** `src/thoth/config.py:659-688`; `src/thoth/config.py:174-228`
- **Context:** Built-in modes define provider namespaces for provider-specific defaults, such as Gemini tools/thinking budget and Perplexity search settings. Users should be able to override one nested value without accidentally deleting the rest of the built-in provider defaults.
- **Detail:** Global config layers deep-merge dictionaries, but `get_mode_config()` uses `mode_config.update(user_mode)` when overlaying user mode config onto a built-in mode. If a user adds `[modes.gemini_quick.gemini] temperature = 0.2`, that nested table can replace the built-in Gemini namespace instead of merging with `tools = ["google_search"]` and `thinking_budget = 0`. This makes mode overrides less predictable than normal config layer overrides.
- **Recommendation:** Deep-merge built-in mode dictionaries and user/profile mode overrides using the same semantics as the main config layer merge. Arrays should still follow the separately documented array replacement policy.
- **Resolution choices:** Option A (recommended): deep-merge mode dictionaries consistently with global config layers. Option B: preserve full-table replacement but document it prominently and require examples. Option C: require users to copy built-in modes before editing, so overrides are explicit full replacements.
- **References:** matrix section Resolution Rules; matrix section Worked Examples
- **Related:** DEC-006

<a id="inc-005"></a>

### INC-005 - Runtime Timeout Has Provider-Specific Effects

- **Description:** OpenAI and Perplexity use timeout in client construction; Gemini currently does not.
- **Kind:** inconsistency
- **Status:** open
- **Layers affected:** L3, L8
- **Providers affected:** Gemini compared with OpenAI and Perplexity
- **Source:** `src/thoth/providers/__init__.py:188-190`; `src/thoth/providers/openai.py:242-244`; `src/thoth/providers/perplexity.py:406-422`; `src/thoth/providers/gemini.py:213-221`
- **Context:** `timeout` is a framework/client control, not a model payload parameter. Users expect it to work uniformly because it is surfaced as a runtime override and copied for all production providers.
- **Detail:** Timeout is routed through the factory for OpenAI, Perplexity, and Gemini. OpenAI and Perplexity consume it while constructing their clients. Gemini stores the value in config but constructs `genai.Client(api_key=api_key)` without applying timeout to the SDK client or request options. This makes `--timeout` look provider-neutral while having no Gemini effect.
- **Recommendation:** Make `timeout` part of the provider client contract and require every provider adapter to either apply it or explicitly declare it unsupported with a clear warning/error.
- **Resolution choices:** Option A (recommended): wire timeout for every provider and cover it with constructor/request tests. Option B: document Gemini timeout as unsupported and do not pretend L8 applies. Option C: split timeout into provider-specific controls if SDKs require different semantics.
- **References:** matrix row `timeout`; GAP-005
- **Related:** GAP-005

<a id="inc-006"></a>

### INC-006 - Runtime Provider Override Can Mismatch Mode Model And Namespace

- **Description:** `--provider` can select a provider while retaining the selected mode's model and unrelated provider namespace.
- **Kind:** inconsistency
- **Status:** open
- **Layers affected:** L5, L7, L8
- **Providers affected:** all
- **Source:** `src/thoth/run.py:188-220`; `src/thoth/run.py:319-344`; `src/thoth/providers/__init__.py:192-202`
- **Context:** `--provider` is useful for testing and quick provider switching, but modes are often provider-specific because they pin a native model and provider namespace. The override boundary must prevent accidental cross-provider request shapes.
- **Detail:** Provider selection can be forced by `--provider`, and the selected mode's `model` is still copied into provider config before construction. A forced provider can therefore receive a model intended for another provider, while the forced provider namespace may be absent and the original namespace remains irrelevant. Example risk: forcing `--provider gemini` on a Perplexity mode can send Gemini a `sonar` model unless another override intervenes.
- **Recommendation:** Validate the provider/model/namespace combination after provider selection and before provider construction. If a mode is provider-specific, require an explicit compatible `--model` or a provider-native mode when switching provider families.
- **Resolution choices:** Option A (recommended): validate and error on provider/model/namespace mismatch with a repair hint. Option B: allow `--provider` only when paired with `--model` if the mode pins a different provider. Option C: keep permissive expert override behavior, but mark it unsafe and add diagnostics in verbose mode.
- **References:** matrix section Resolution Rules; DEC-005
- **Related:** DEC-005

<a id="inc-007"></a>

### INC-007 - L9 Is OpenAI-Only While Main Providers Are Multi-Provider

- **Description:** Clarification has its own OpenAI Chat Completions path instead of the shared OpenAI/Perplexity/Gemini stack.
- **Kind:** inconsistency
- **Status:** open
- **Layers affected:** L9
- **Providers affected:** OpenAI only today; all if generalized
- **Source:** `src/thoth/config.py:345-365`; `src/thoth/interactive.py:857-909`
- **Context:** L9 is a real level because clarification has its own config subtree with model parameters, retry policy, prompt text, and UI controls. It is not part of the main provider/mode stack, but it still makes LLM requests.
- **Detail:** L9 has model, temperature, max-token, prompt, retry, and UI fields. Its provider field currently does not route through `create_provider()` or the provider registry, so it is a separate parameter subsystem. That means clarification uses OpenAI-specific auth and Chat Completions request construction even though the rest of the app is moving toward OpenAI, Perplexity, and Gemini parity.
- **Recommendation:** Keep L9 as a separate UX subsystem, but route the LLM call through the same provider normalizer and adapter dispatch used by main requests. UI-only fields should stay outside provider normalization.
- **Resolution choices:** Option A (recommended): preserve L9 as a separate config area but reuse shared provider normalization for the model call. Option B: keep the OpenAI-only path and document clarification as intentionally separate. Option C: fold clarification into normal modes and represent interactive clarification as a mode/provider config.
- **References:** matrix section Configuration Layers L9; DEC-003
- **Related:** GAP-007

<a id="inc-008"></a>

### INC-008 - Documentation And Tests Disagree On Root Provider Defaults

- **Description:** Auth help documents provider tables as API-key-only while skipped tests describe desired request defaults.
- **Kind:** inconsistency
- **Status:** open
- **Layers affected:** L2, L3
- **Providers affected:** OpenAI, Perplexity, Gemini
- **Source:** `planning/p24-providers-root-namespace-investigation.v1.md:35-41`; `tests/test_provider_config.py:541-672`
- **Context:** Root provider defaults were investigated and punted. The codebase now has aspirational skipped tests, a planning note, and user-facing docs that do not all describe the same contract.
- **Detail:** The root provider default question is visible in skipped tests and planning docs, but the user-facing auth docs still describe provider tables primarily as auth configuration. This is expected while the feature is punted, but it means documentation cannot yet be used as a complete config contract. A future implementer could reasonably follow either the docs or the skipped tests and make a different choice.
- **Recommendation:** Pick the intended L2/L3 contract first, then make README/help text, skipped tests, and the matrix all cite the same decision ID. Until then, explicitly label root provider request defaults as deferred rather than implied.
- **Resolution choices:** Option A (recommended now): docs say root provider request defaults are deferred and point to GAP-001/DEC-004. Option B: implement root provider defaults and update docs/tests as part of the same change. Option C: remove aspirational skipped tests if the project chooses auth/client-only root provider tables.
- **References:** matrix section Configuration Layers L2-L3; GAP-001
- **Related:** GAP-001, INC-002

<a id="inc-009"></a>

### INC-009 - Perplexity `search_context_size` Needs Upstream Validation

- **Description:** Local built-ins and adapter defaults use `web_search_options.search_context_size`, but the current Sonar API reference does not clearly list it as a request-body field.
- **Kind:** inconsistency
- **Status:** open
- **Layers affected:** L1, L5, L7
- **Providers affected:** Perplexity
- **Source:** `src/thoth/config.py:181-205`; `src/thoth/providers/perplexity.py:491-507`
- **Context:** This is a documentation/API-contract inconsistency rather than a cross-provider behavior issue. Local code uses a Perplexity key path that may have come from an earlier doc/version or empirical behavior, while the current reference surface is not clear enough to treat it as canonical without validation.
- **Detail:** Thoth built-in Perplexity modes and the Perplexity adapter both set `web_search_options.search_context_size`. The current Perplexity Sonar API reference lists `web_search_options` and `web_search_options.search_mode`, plus top-level search filters, but does not clearly list `search_context_size` as a request-body field. This should be verified with current docs and, if necessary, a live request-construction or live API test before keeping it in the desired matrix as a stable key.
- **Recommendation:** Treat `search_context_size` as unconfirmed until it is verified against current Perplexity documentation or a live API contract test. Do not present it as stable desired-state behavior without that evidence.
- **Resolution choices:** Option A (recommended): verify current upstream behavior, then keep the row if supported. Option B: remove `search_context_size` from built-ins and the matrix if unsupported. Option C: move it into a documented unstable Perplexity extension bag until confirmed.
- **References:** matrix row `search_context_size`; Perplexity Sonar chat completion reference; `src/thoth/config.py`; `src/thoth/providers/perplexity.py`
- **Related:** GAP-006, DEC-004

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
- **Related:** GAP-006
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
