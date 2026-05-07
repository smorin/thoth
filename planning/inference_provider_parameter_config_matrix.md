# Inference Provider Parameter Config Matrix

Sidecar: [inference_provider_parameter_config_inconsistencies.md](inference_provider_parameter_config_inconsistencies.md)

## Overview

This document is the desired-state contract for Thoth's inference provider parameter configuration. It defines the canonical layers, merge behavior, provider-neutral parameter names, provider-specific translations, and final SDK request shapes. It is not a status report; current gaps, partial behavior, migration work, and undecided policy questions live in the sidecar.

Mental model:

```text
provider defaults -> root provider defaults -> mode generic common params -> mode provider namespace -> CLI/run overrides
```

Profiles are not a separate provider mechanism. The active profile is a normal config layer that may override any supported shape before provider parameters are normalized. There is also no generic inherited `[providers]` or `[providers.defaults]` layer in this contract; cross-provider request defaults belong in the mode generic common-param layers.

## Configuration Layers

Precedence runs from lowest to highest inside this provider-parameter stack.

| ID | Level | Example |
|---|---|---|
| L0 | Provider implementation defaults | `OpenAIProvider` uses `model = "o3"`; `PerplexityProvider` uses `model = "sonar"`; `GeminiProvider` uses `model = "gemini-2.5-flash-lite"`. |
| L1 | Built-in mode defaults | `BUILTIN_MODES["gemini_quick"]["gemini"] = {tools = ["google_search"], thinking_budget = 0}`. |
| L2 | Root per-provider config | `[providers.openai] api_key = "${OPENAI_API_KEY}"; temperature = 0.2`. |
| L3 | Profile-scoped root per-provider config | `[profiles.work.providers.gemini] api_key = "${GEMINI_WORK_API_KEY}"; timeout = 45`. |
| L4 | Mode generic common params | `[modes.fast] temperature = 0.2; max_output_tokens = 800`. |
| L5 | Mode provider namespace | `[modes.fast.gemini] thinking_budget = 0; tools = ["google_search"]`. |
| L6 | Profile-scoped mode generic | `[profiles.work.modes.fast] top_p = 0.8`. |
| L7 | Profile-scoped mode provider namespace | `[profiles.work.modes.fast.perplexity] search_domain_filter = ["docs.perplexity.ai"]`. |
| L8 | Runtime overrides | `--provider perplexity --model sonar-pro --timeout 60 --api-key-perplexity "$PERPLEXITY_API_KEY"`. |
| L9 | Separate clarification config | `[clarification.interactive] model = "gpt-4o-mini"; temperature = 0.3; max_output_tokens = 800`. |

## Resolution Rules

The repository-level config merge order is:

```text
defaults -> user -> project -> profile -> env -> cli
```

Active profile selection is:

```text
--profile -> THOTH_PROFILE -> general.default_profile
```

Provider construction follows one shared path:

1. Start with provider implementation defaults (L0).
2. Add built-in mode defaults when the selected mode is built in (L1).
3. Add root provider config for the chosen provider (L2).
4. Add profile-scoped root provider config if a profile is active (L3).
5. Add mode generic common parameters from the selected mode (L4).
6. Add the selected provider namespace from the selected mode (L5).
7. Add profile-scoped mode generic parameters (L6).
8. Add profile-scoped provider namespace parameters (L7).
9. Add runtime overrides from CLI/run state (L8).
10. Keep clarification config separate unless a clarification flow explicitly invokes the same normalizer (L9).

`create_provider()` should normalize once into a shared provider-runtime structure, then each provider adapter should translate that structure into the native SDK shape. Framework-owned values such as `api_key`, `timeout`, `provider`, `providers`, `kind`, `model`, `system_prompt`, `prompt_prefix`, and `stream` are not blindly forwarded as arbitrary SDK kwargs.

Scalar values replace lower-precedence values. Object values deep-merge when they are parameter objects, including provider namespaces and nested SDK objects such as `web_search_options` or `thinking_config`. Arrays replace by default; they do not append unless a parameter explicitly defines append semantics. Absence means inherit. TOML has no native `null`, so users unset/remove config keys to inherit. Internal `None` means "explicitly disable" only for parameters whose provider semantics support that distinction.

Provider-specific exceptions are allowed only when named in the parameter matrix or a per-parameter detail section. For example, OpenAI reasoning models may reject `temperature`; the adapter should omit unsupported parameters or surface a targeted provider error according to the provider contract.

## Worked Examples

### Example A - Minimal Provider Defaults

Layers involved: L0 and L2. No mode parameter layer participates. This is a provider-normalization example, not a runnable `thoth ask` example; runnable CLI execution also performs mode resolution and provider selection.

User config, `~/.config/thoth/thoth.config.toml`:

```toml
version = "2.0"

[providers.gemini]
api_key = "${GEMINI_API_KEY}"
```

No profile config:

```toml
# No active profile.
```

No mode config:

```toml
# No [modes.*] block participates in this example.
```

Normalizer input:

```json
{
  "provider": "gemini",
  "prompt": "Explain database indexes in two paragraphs.",
  "mode_config": null,
  "runtime_overrides": {}
}
```

Trace:

| Layer | Contribution |
|---|---|
| L0 | `GeminiProvider` default model is `gemini-2.5-flash-lite`. |
| L1 | No built-in mode parameter block participates. |
| L2 | `[providers.gemini]` supplies the API key only. |
| L3 | No active profile. |
| L4-L7 | No mode/provider parameter overrides. |
| L8 | No runtime parameter overrides. |
| L9 | Not a clarification request. |

Final normalized provider request:

```json
{
  "provider": "gemini",
  "sdk_call": "client.models.generate_content",
  "auth": {
    "api_key": "${GEMINI_API_KEY}"
  },
  "kwargs": {
    "model": "gemini-2.5-flash-lite",
    "contents": [
      {
        "role": "user",
        "parts": [
          {"text": "Explain database indexes in two paragraphs."}
        ]
      }
    ]
  }
}
```

### Example B - Mode Provider Namespace

Layers involved: L0, L2, L4, and L5. The common `temperature` can be translated for any provider that supports it; Gemini-specific thinking and tools live under the Gemini namespace.

User config, `~/.config/thoth/thoth.config.toml`:

```toml
version = "2.0"

[providers.gemini]
api_key = "${GEMINI_API_KEY}"
```

Project config, `./thoth.config.toml`:

```toml
version = "2.0"

[modes.fast_gemini]
provider = "gemini"
model = "gemini-2.5-flash-lite"
kind = "immediate"
temperature = 0.2

[modes.fast_gemini.gemini]
tools = ["google_search"]
thinking_budget = 0
```

No profile config:

```toml
# No active profile.
```

Command line:

```bash
thoth ask --mode fast_gemini "Summarize the Python packaging changes."
```

Trace:

| Layer | Contribution |
|---|---|
| L0 | Gemini default model is `gemini-2.5-flash-lite`. |
| L1 | No built-in mode with this name; no built-in provider namespace. |
| L2 | `[providers.gemini]` supplies the API key. |
| L3 | No active profile. |
| L4 | `[modes.fast_gemini] temperature = 0.2` sets the common temperature. |
| L5 | `[modes.fast_gemini.gemini]` sets Google Search and disables 2.5 Flash thinking with budget `0`. |
| L6-L7 | No profile mode overrides. |
| L8 | `--mode` selects the mode; it does not override request parameters. |
| L9 | Not a clarification request. |

Final normalized provider request:

```json
{
  "provider": "gemini",
  "sdk_call": "client.models.generate_content",
  "auth": {
    "api_key": "${GEMINI_API_KEY}"
  },
  "kwargs": {
    "model": "gemini-2.5-flash-lite",
    "contents": [
      {
        "role": "user",
        "parts": [
          {"text": "Summarize the Python packaging changes."}
        ]
      }
    ],
    "config": {
      "temperature": 0.2,
      "tools": [{"google_search": {}}],
      "thinking_config": {
        "thinking_budget": 0
      }
    }
  }
}
```

### Example C - Profile, Mode, Provider Namespace, And CLI

Layers involved: L0, L2, L3, L4, L5, L6, L7, and L8. The active profile overrides the root Perplexity API key, adjusts common mode params, adds provider-specific search controls, and the CLI overrides the model.

User config, `~/.config/thoth/thoth.config.toml`:

```toml
version = "2.0"

[providers.perplexity]
api_key = "${PERPLEXITY_API_KEY}"

[profiles.work.providers.perplexity]
api_key = "${PERPLEXITY_WORK_API_KEY}"
timeout = 45

[profiles.work.modes.focused_research]
top_p = 0.8
max_output_tokens = 1200

[profiles.work.modes.focused_research.perplexity]
search_domain_filter = ["docs.perplexity.ai", "platform.openai.com"]

[profiles.work.modes.focused_research.perplexity.web_search_options]
search_context_size = "high"
```

Project config, `./thoth.config.toml`:

```toml
version = "2.0"

[modes.focused_research]
provider = "perplexity"
model = "sonar"
kind = "immediate"
temperature = 0.4

[modes.focused_research.perplexity]
stream_mode = "concise"

[modes.focused_research.perplexity.web_search_options]
search_context_size = "low"
```

Profile config is the profile block in the user file above:

```toml
[profiles.work.providers.perplexity]
api_key = "${PERPLEXITY_WORK_API_KEY}"
timeout = 45

[profiles.work.modes.focused_research]
top_p = 0.8
max_output_tokens = 1200

[profiles.work.modes.focused_research.perplexity]
search_domain_filter = ["docs.perplexity.ai", "platform.openai.com"]

[profiles.work.modes.focused_research.perplexity.web_search_options]
search_context_size = "high"
```

Command line:

```bash
thoth --profile work ask --mode focused_research --provider perplexity --model sonar-pro "Compare current SDK parameter names."
```

Trace:

| Layer | Contribution |
|---|---|
| L0 | Perplexity default model is `sonar`. |
| L1 | No built-in mode with this name. |
| L2 | Root `[providers.perplexity]` supplies the base API key. |
| L3 | Profile root provider block replaces the API key with `${PERPLEXITY_WORK_API_KEY}` and sets `timeout = 45`. |
| L4 | Project mode generic block sets `temperature = 0.4`. |
| L5 | Project Perplexity namespace sets `stream_mode = "concise"` and `web_search_options.search_context_size = "low"`. |
| L6 | Profile mode generic block sets `top_p = 0.8` and `max_output_tokens = 1200`. |
| L7 | Profile Perplexity namespace sets `search_domain_filter` and overrides `web_search_options.search_context_size` to `"high"`. |
| L8 | `--provider perplexity` selects Perplexity; `--model sonar-pro` overrides the mode model. |
| L9 | Not a clarification request. |

Final normalized provider request:

```json
{
  "provider": "perplexity",
  "sdk_call": "client.chat.completions.create",
  "auth": {
    "api_key": "${PERPLEXITY_WORK_API_KEY}"
  },
  "client": {
    "base_url": "https://api.perplexity.ai",
    "timeout": 45
  },
  "kwargs": {
    "model": "sonar-pro",
    "messages": [
      {
        "role": "user",
        "content": "Compare current SDK parameter names."
      }
    ],
    "temperature": 0.4,
    "top_p": 0.8,
    "max_tokens": 1200,
    "extra_body": {
      "stream_mode": "concise",
      "web_search_options": {
        "search_context_size": "high"
      },
      "search_domain_filter": ["docs.perplexity.ai", "platform.openai.com"]
    }
  }
}
```

## Parameter Matrix

This table is Thoth's desired internal parameter surface. It is not a raw dump of every vendor option. Provider columns contain the native request key path the adapter should emit. `-` means unsupported by that provider surface. Key paths use the Python SDK shape when Thoth uses an SDK; REST-only names are called out in notes.

Canonical provider surfaces for this matrix:

- OpenAI: Responses API `responses.create()` / `responses.stream()`.
- Perplexity: Sonar Chat Completions `/v1/sonar` plus async wrapper `/v1/async/sonar` where noted.
- Gemini: Google GenAI `models.generate_content()` / `models.generate_content_stream()` with `GenerateContentConfig`.

### Request Payload Keys

| Internal parameter | OpenAI key path | Perplexity key path | Gemini key path | Notes |
|---|---|---|---|---|
| `model` | `model` | `model`; `request.model` | `model` | Gemini `model` is a Python SDK kwarg and REST path parameter (`models/{model}`), not `GenerateContentConfig`. Perplexity `request.model` is the async wrapper path. Runtime `--model` overrides before adapter translation. |
| `prompt` | `input` | `messages` | `contents` | Thoth builds this from user prompt plus file/context inputs. |
| `system_prompt` | `instructions` | `messages[].role`; `request.messages[].role` | `config.system_instruction` | OpenAI `instructions` is the desired canonical encoding; current code emits an equivalent developer-role input message. Perplexity `request.*` paths are async wrapper paths. Gemini REST spelling is `systemInstruction` / `system_instruction` depending client surface. |
| `temperature` | `temperature` | `temperature`; `request.temperature` | `config.temperature` | Perplexity `request.*` paths are async wrapper paths. Adapter omits for OpenAI models that reject it. |
| `top_p` | `top_p` | `top_p`; `request.top_p` | `config.top_p` | Perplexity `request.*` paths are async wrapper paths. Common L4 candidate. |
| `top_k` | - | - | `config.top_k` | Gemini-only. |
| `max_output_tokens` | `max_output_tokens` | `max_tokens`; `request.max_tokens` | `config.max_output_tokens` | Perplexity `request.*` paths are async wrapper paths. Canonical internal name; provider aliases normalize here. |
| `stop_sequences` | - | `stop`; `request.stop` | `config.stop_sequences` | Perplexity `request.*` paths are async wrapper paths. OpenAI Responses does not expose a `stop` request key in the canonical surface. |
| `frequency_penalty` | - | - | `config.frequency_penalty` | OpenAI Responses does not expose this key; Gemini model support may vary. |
| `presence_penalty` | - | - | `config.presence_penalty` | Gemini model support may vary. |
| `seed` | - | - | `config.seed` | Best-effort determinism where the model supports it. |
| `n` | - | - | `config.candidate_count` | OpenAI Responses and Perplexity Sonar do not use `n` in the canonical surface. |
| `response_format` | `text.format` | `response_format`; `request.response_format` | `config.response_mime_type`; `config.response_schema`; `config.response_json_schema` | Perplexity `request.*` paths are async wrapper paths. Structured output maps to provider-specific schema fields. |
| `reasoning_effort` | `reasoning.effort` | `reasoning_effort`; `request.reasoning_effort` | `config.thinking_config.thinking_level` | Perplexity `request.*` paths are async wrapper paths. Gemini 3 uses thinking levels. |
| `thinking_budget` | - | - | `config.thinking_config.thinking_budget` | Gemini 2.5 uses thinking budgets. |
| `include_thoughts` | - | - | `config.thinking_config.include_thoughts` | OpenAI uses summary config instead of this name. |
| `reasoning_summary` | `reasoning.summary` | `stream_mode` | `config.thinking_config.include_thoughts` | Perplexity `stream_mode = "concise"` controls separate reasoning events. |
| `tools` | `tools` | - | `config.tools` | Perplexity Sonar search controls are separate request keys, not a generic `tools` array. |
| `tool_choice` | `tool_choice` | - | `config.tool_config.function_calling_config.mode` | Provider-specific function-calling policy. |
| `parallel_tool_calls` | `parallel_tool_calls` | - | - | OpenAI-only. |
| `code_interpreter` | `tools[].type` | - | `config.tools[].code_execution` | OpenAI value is a tool object with `type = "code_interpreter"`. |
| `web_search` | `tools[].type` | `disable_search` | `config.tools[].google_search` | Perplexity search is native; `disable_search` is inverse semantics. |
| `search_context_size` | - | `web_search_options.search_context_size` | - | Needs validation against current Perplexity docs; see sidecar. |
| `search_mode` | - | `web_search_options.search_mode` | - | Perplexity values include `web`, `academic`, and `sec`. |
| `search_domain_filter` | - | `search_domain_filter` | - | Perplexity-only. |
| `search_language_filter` | - | `search_language_filter` | - | Perplexity-only. |
| `search_recency_filter` | - | `search_recency_filter` | - | Perplexity-only. |
| `search_after_date_filter` | - | `search_after_date_filter` | - | Perplexity date filter. |
| `search_before_date_filter` | - | `search_before_date_filter` | - | Perplexity date filter. |
| `last_updated_after_filter` | - | `last_updated_after_filter` | - | Perplexity date filter. |
| `last_updated_before_filter` | - | `last_updated_before_filter` | - | Perplexity date filter. |
| `image_format_filter` | - | `image_format_filter` | - | Perplexity image-result filter. |
| `image_domain_filter` | - | `image_domain_filter` | - | Perplexity image-result filter. |
| `return_images` | - | `return_images` | - | Perplexity-only. |
| `return_related_questions` | - | `return_related_questions` | - | Perplexity-only. |
| `enable_search_classifier` | - | `enable_search_classifier` | - | Perplexity-only. |
| `disable_search` | - | `disable_search` | - | Perplexity-only; inverse of Thoth `web_search`. |
| `safety_settings` | - | - | `config.safety_settings`; `safetySettings` | Gemini Python SDK sets this through config; second spelling is REST JSON. |
| `logprobs` | `include`; output `logprobs` | - | `config.response_logprobs` | OpenAI uses include/output fields; Gemini also needs `config.logprobs` for top count. |
| `top_logprobs` | `top_logprobs` | - | `config.logprobs` | OpenAI and Gemini range is provider-defined. |
| `safety_identifier` | `safety_identifier` | - | - | OpenAI abuse/safety identifier. |
| `prompt_cache_key` | `prompt_cache_key` | - | - | OpenAI replacement path for cache bucketing. |
| `prompt_cache_retention` | `prompt_cache_retention` | - | - | OpenAI cache retention policy. |
| `user` | `user` | - | - | Deprecated in OpenAI Responses; prefer `safety_identifier` plus `prompt_cache_key`. |
| `service_tier` | `service_tier` | - | `service_tier` | Gemini REST spelling is `serviceTier`. |
| `metadata` | `metadata` | - | - | OpenAI object metadata. |
| `store` | `store` | - | `store` | Provider retention/storage flag where supported. |
| `truncation` | `truncation` | - | - | OpenAI Responses input truncation strategy. |
| `language_preference` | - | `language_preference` | - | Perplexity-only. |
| `idempotency_key` | - | `idempotency_key` | - | Perplexity async wrapper key, outside `request`. |

### Framework And Client Controls

These are not generic inference payload keys. They are included here because they participate in the same config layers and are often confused with request parameters.

| Internal control | OpenAI key path | Perplexity key path | Gemini key path | Notes |
|---|---|---|---|---|
| `api_key` | `api_key`; `Authorization` | `api_key`; `Authorization` | `api_key`; `x-goog-api-key` | Resolved by CLI, env, then config. |
| `timeout` | `timeout` | `timeout` | `timeout` | Client/runtime control, not model payload. |
| `provider` | - | - | - | Thoth routing control. |
| `providers` | - | - | - | Thoth multi-provider routing control. |
| `kind` | `background` | - | - | Thoth routing control; OpenAI also has a `background` request key. Perplexity/Gemini use endpoint or mode selection rather than a `kind` key. |
| `background` | `background` | `/v1/async/sonar` endpoint | background endpoint/agent when supported | OpenAI has a request key; Perplexity uses a different endpoint. |
| `stream` | `responses.stream()` | `stream` | `models.generate_content_stream()` | Runtime execution control. Only Perplexity Sonar exposes it as a request key. |
| `system_prompt` | see request table | see request table | see request table | Listed here because it is assembled by Thoth, not blindly forwarded. |

## Per-Parameter Detail

### `model`

Provider-native model ID. Runtime `--model` has the highest precedence and overrides the selected mode's model for the selected provider. Provider adapters validate model/kind compatibility before network calls where possible.

### `system_prompt`

Framework message-building input, not arbitrary provider passthrough. It maps to OpenAI developer instructions/input, Perplexity system messages, and Gemini `system_instruction`.

### `temperature`

Common sampling parameter. Higher layers replace lower values. Adapters omit it for models that reject temperature rather than sending a known-invalid request.

### `top_p`

Common nucleus sampling parameter. Preferred over provider-specific spellings. Provider adapters map it to native request keys when supported.

### `top_k`

Gemini-specific sampling parameter. It should live in a Gemini namespace unless a future provider supports the same semantic.

### `max_output_tokens`

Canonical internal output-token budget. Adapters translate to OpenAI `max_output_tokens`, Perplexity `max_tokens`, and Gemini `max_output_tokens`. Provider-specific aliases should normalize into this internal name before adapter translation.

### `stop_sequences`

Canonical stop sequence list or string. Adapters translate to Perplexity `stop` and Gemini `stop_sequences`. OpenAI Responses has no canonical `stop` key in this matrix; an OpenAI Chat Completions compatibility path would need its own endpoint-specific row or adapter rule.

### `frequency_penalty` And `presence_penalty`

Gemini-model-specific sampling controls in this matrix. OpenAI Chat Completions compatibility may expose similarly named fields, but the canonical OpenAI Responses surface does not.

### `seed`

Best-effort deterministic generation seed where the provider/model exposes it. Absence inherits provider behavior.

### `n`

Number of candidate responses. Gemini maps this to `candidate_count`. Other provider endpoint variants may expose a similar field, but they are outside the canonical surfaces above unless explicitly added.

### `stream`

Thoth run-control parameter. It chooses streaming vs one-shot execution and may map to a provider SDK streaming call or `stream=true` depending provider path.

### `response_format`

Canonical structured output request. OpenAI maps to Responses text format / structured output config, Perplexity maps to `response_format`, and Gemini maps to response MIME/schema fields.

### `reasoning_effort`

Reasoning intensity for providers that expose an effort enum. OpenAI maps to `reasoning.effort`; Perplexity maps to `reasoning_effort`; Gemini 3 maps to `thinking_level`.

### `thinking_budget`

Gemini 2.5 thinking token budget. `0` disables thinking on models that allow it, and `-1` requests dynamic thinking.

### `include_thoughts` And `reasoning_summary`

Controls whether summarized reasoning is requested or surfaced. OpenAI uses reasoning summary fields, Perplexity exposes reasoning through reasoning models and stream mode, and Gemini uses `include_thoughts`.

### `tools`, `tool_choice`, `parallel_tool_calls`, `code_interpreter`, And `web_search`

Tool semantics are provider-native. The shared config name should normalize common intent, while provider namespaces carry native tool declarations and provider-only controls.

### Perplexity Search Controls

`search_mode`, domain/language/recency/date filters, image filters, `return_images`, `return_related_questions`, `enable_search_classifier`, and `disable_search` map to Perplexity Sonar request fields. `search_context_size` is retained because local built-ins and code use it, but it needs explicit validation against the current upstream request schema before being treated as a stable desired-state key.

### `safety_settings`

Gemini-native safety configuration. It should remain provider-namespaced unless a cross-provider safety abstraction is explicitly designed.

### `logprobs` And `top_logprobs`

Output-probability controls. They are endpoint/model-specific and should be omitted unless supported by the chosen provider/model.

### `user`, `safety_identifier`, `service_tier`, And `metadata`

Provider platform controls. They do not change prompt semantics directly but affect attribution, safety, routing, priority, caching, retention, or dashboard metadata. OpenAI `user` is deprecated in favor of `safety_identifier` and `prompt_cache_key`.

### `timeout`

Client/runtime timeout, not an inference payload parameter. It can be set at root provider or runtime layers and must affect all provider clients consistently.

### `language_preference` And `idempotency_key`

Perplexity-specific controls. `language_preference` is a request preference; `idempotency_key` belongs to the async wrapper.

## References

- OpenAI Responses API create reference: https://platform.openai.com/docs/api-reference/responses/create
- Perplexity Sonar chat completion reference: https://docs.perplexity.ai/api-reference/sonar-post
- Perplexity async Sonar reference: https://docs.perplexity.ai/api-reference/async-sonar-post
- Gemini generate content API reference: https://ai.google.dev/api/generate-content
- Gemini thinking guide: https://ai.google.dev/gemini-api/docs/thinking
- Local references index: [references.md](references.md)
