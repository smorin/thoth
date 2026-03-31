# Gemini Deep Research Agent API: Complete Technical Reference

**The Gemini Deep Research Agent is an autonomous research agent accessible exclusively through the Interactions API (v1beta), powered by Gemini 3.1 Pro.** It accepts a research query, autonomously plans a multi-step investigation using Google Search and URL context tools, reads dozens of web pages, iterates on knowledge gaps, and returns a comprehensive research report — all in a single API call. This reference covers every endpoint, parameter, schema, pricing detail, known bug, and production pattern needed to build a complete integration from scratch. The API is in public beta as of March 2026, and breaking changes remain possible.

---

## 1. Authentication and client setup

### SDK packages and minimum versions

| Language | Package | Install command | Minimum version |
|----------|---------|-----------------|-----------------|
| Python | `google-genai` | `pip install "google-genai>=1.55.0"` | **1.55.0** |
| JavaScript/TypeScript | `@google/genai` | `npm install @google/genai` | **1.33.0** |
| Go | `google.golang.org/genai` | `go get google.golang.org/genai` | Latest |
| Java | `com.google.genai:google-genai` | Maven 1.0.0 | Latest |

**Legacy packages that do NOT support the Interactions API:** `google-generativeai` (Python), `@google/generative-ai` (JS), `@google-cloud/vertexai` (JS). These are deprecated — do not use them.

### Authentication methods

**API Key (Gemini Developer API)** is the primary method for the Interactions API. The SDK auto-discovers keys from environment variables: `GEMINI_API_KEY` or `GOOGLE_API_KEY` (the latter takes precedence if both are set). For REST calls, pass the header `x-goog-api-key: $GEMINI_API_KEY`.

```python
# Python — explicit API key
from google import genai
client = genai.Client(api_key='YOUR_API_KEY')
```

```javascript
// JavaScript — explicit API key
import { GoogleGenAI } from '@google/genai';
const ai = new GoogleGenAI({ apiKey: 'YOUR_API_KEY' });
```

**Vertex AI authentication** uses Application Default Credentials (ADC) or service accounts. Set `GOOGLE_GENAI_USE_VERTEXAI=true`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, and optionally `GOOGLE_APPLICATION_CREDENTIALS` for service account JSON. However, **the Interactions API is not yet available on Vertex AI** — it is announced as "coming soon." Vertex AI Express Mode allows using an API key with Vertex AI: `client = genai.Client(vertexai=True, api_key='YOUR_VERTEX_EXPRESS_KEY')`.

**OAuth/Service Account** authentication works through Google Cloud ADC (`gcloud auth application-default login` for user credentials, or a service account with the "Vertex AI User" IAM role for CI/CD pipelines).

### Client constructor signatures

```python
# Python full signature
genai.Client(
    api_key: str = None,
    vertexai: bool = False,
    project: str = None,
    location: str = None,
    http_options: HttpOptions = None  # e.g., HttpOptions(api_version='v1beta')
)
# Key properties: client.interactions, client.files, client.file_search_stores
# Async variant: client.aio.interactions.create(), .get(), .cancel()
```

```javascript
// JavaScript full signature
new GoogleGenAI({
    apiKey?: string,
    vertexai?: boolean,
    project?: string,
    location?: string,
    httpOptions?: { apiVersion?: string }
})
// Key properties: ai.interactions, ai.files, ai.models
```

### API version and base URL

The Interactions API exists **only in `v1beta`** — it is not available in the stable `v1` release. The base URL is `https://generativelanguage.googleapis.com/v1beta/`. SDKs default to `v1beta` automatically; override with `http_options={'api_version': 'v1beta'}` if needed. There are no regional endpoint differences for the Gemini Developer API — all traffic goes through the global endpoint. The Vertex AI surface uses `https://{location}-aiplatform.googleapis.com/v1/` but does not yet support the Interactions API.

---

## 2. Complete API surface

### REST endpoints

All paths are relative to `https://generativelanguage.googleapis.com/v1beta/`.

| Operation | Method | Path | Description |
|-----------|--------|------|-------------|
| **Create** | `POST` | `/interactions` | Start a new interaction |
| **Create (streaming)** | `POST` | `/interactions?alt=sse` | Start with SSE streaming |
| **Get** | `GET` | `/interactions/{id}` | Retrieve interaction status and outputs |
| **Get (streaming)** | `GET` | `/interactions/{id}?stream=true&alt=sse` | Stream or resume streaming |
| **Cancel** | `POST` | `/interactions/{id}/cancel` | Cancel a running background interaction |
| **Delete** | `DELETE` | `/interactions/{id}` | Delete a stored interaction |

There is **no `list` endpoint** — you cannot enumerate all interactions. You must track interaction IDs yourself.

Required headers for REST: `Content-Type: application/json` and `x-goog-api-key: $GEMINI_API_KEY`.

### SDK method signatures

```python
# Python SDK — interactions resource
client.interactions.create(
    agent: str = None,                    # e.g., 'deep-research-pro-preview-12-2025'
    model: str = None,                    # Mutually exclusive with agent
    input: str | list[Content] | list[Turn],  # Required
    background: bool = None,              # Required True for agents
    stream: bool = None,                  # Default: False
    store: bool = None,                   # Default: True
    system_instruction: str = None,
    tools: list[Tool] = None,
    agent_config: dict = None,            # For agents; mutually exclusive with generation_config
    generation_config: GenerationConfig = None,  # For models
    previous_interaction_id: str = None,
    response_format: dict = None,
    response_mime_type: str = None,
    response_modalities: list[str] = None,
) -> Interaction | Stream[InteractionSseEvent]

client.interactions.get(
    id: str,                              # Required
    stream: bool = None,
    last_event_id: str = None,            # For stream resumption
    include_input: bool = None,           # Include original input in response
) -> Interaction | Stream[InteractionSseEvent]

client.interactions.cancel(id: str) -> Interaction
# Delete: use REST directly
```

The JavaScript SDK mirrors this structure with `ai.interactions.create({...})`, `.get(id, options)`, and `.cancel(id)`. Async Python variants are available via `client.aio.interactions.*`.

### The Interaction object schema

```json
{
  "id": "string",
  "object": "interaction",
  "status": "in_progress | requires_action | completed | failed | cancelled",
  "agent": "deep-research-pro-preview-12-2025",
  "model": null,
  "role": "agent",
  "created": "2026-03-15T12:22:47Z",
  "updated": "2026-03-15T12:35:12Z",
  "outputs": [Content],
  "usage": Usage,
  "previous_interaction_id": "string | null",
  "input": [Content],
  "system_instruction": "string | null",
  "tools": [Tool],
  "agent_config": { "type": "deep-research", "thinking_summaries": "auto" },
  "generation_config": null,
  "response_format": null,
  "response_modalities": null,
  "store": true,
  "background": true,
  "stream": false
}
```

The **`status` enum** has exactly five values:

| Status | Meaning |
|--------|---------|
| `in_progress` | Agent is actively executing |
| `requires_action` | Model needs function call results (not used by Deep Research) |
| `completed` | Terminal — outputs available |
| `failed` | Terminal — error occurred |
| `cancelled` | Terminal — user or system cancelled |

The **`role` field** is `"agent"` for Deep Research interactions, `"model"` for standard model interactions.

### The Usage object schema

Every field in the Usage object:

```json
{
  "total_input_tokens": 250000,
  "input_tokens_by_modality": [{"modality": "text", "tokens": 250000}],
  "total_cached_tokens": 150000,
  "cached_tokens_by_modality": [{"modality": "text", "tokens": 150000}],
  "total_output_tokens": 60000,
  "output_tokens_by_modality": [{"modality": "text", "tokens": 60000}],
  "total_tool_use_tokens": 0,
  "tool_use_tokens_by_modality": [],
  "total_thought_tokens": 45000,
  "total_tokens": 355000
}
```

The `ModalityTokens` sub-object has `modality` (enum: `"text"`, `"image"`, `"audio"`) and `tokens` (integer). The **`total_thought_tokens` field** tracks reasoning/thinking tokens separately — these are billed as output tokens. Usage metadata was initially missing from API responses but was fixed on December 31, 2025 (confirmed by Google PM Ali Cevik on the developer forum).

### All 16 Content output types

Content objects are polymorphic, discriminated by the `type` field:

| Type | Key fields | Notes |
|------|-----------|-------|
| `text` | `text`, `annotations[]` | Primary output; annotations contain source URLs |
| `image` | `data` (base64), `uri`, `mime_type`, `resolution` | PNG, JPEG, WebP, HEIC, HEIF |
| `audio` | `data`, `uri`, `mime_type` | WAV, MP3, AIFF, AAC, OGG, FLAC |
| `document` | `data`, `uri`, `mime_type` | PDF only |
| `video` | `data`, `uri`, `mime_type`, `resolution` | MP4, MPEG, MOV, AVI, WebM, WMV, 3GPP |
| `thought` | `signature`, `summary` | Agent reasoning steps |
| `function_call` | `name`, `arguments`, `id` | Not used by Deep Research |
| `function_result` | `name`, `is_error`, `result`, `call_id` | Not used by Deep Research |
| `code_execution_call` | `arguments` (language, code), `id` | Not used by Deep Research |
| `code_execution_result` | `result`, `is_error`, `signature`, `call_id` | Not used by Deep Research |
| `google_search_call` | `arguments` (queries[]), `id` | Internal tool call |
| `google_search_result` | `signature`, `result` (url, title, rendered_content) | Search results |
| `url_context_call` | `arguments` (urls[]), `id` | URL fetch call |
| `url_context_result` | `signature`, `result` (url, status), `is_error` | URL fetch result |
| `file_search_call` | `id` | File search initiation |
| `file_search_result` | `result` (title, text, file_search_store) | File search results |

The `TextContent.annotations` array contains source citations: `{ "url": "string", "start_index": int, "end_index": int }`. The `MediaResolution` enum accepts: `low`, `medium`, `high`, `ultra_high`.

---

## 3. Request construction for Deep Research

### The exact agent identifier

```
agent: "deep-research-pro-preview-12-2025"
```

This is the **only built-in agent** currently available. It is powered by **Gemini 3.1 Pro** and is in Preview status. The identifier includes a date suffix (`12-2025`) suggesting versioning, but no other versions are documented.

### Every parameter for Deep Research requests

| Parameter | Type | Required? | Default | Deep Research behavior |
|-----------|------|-----------|---------|----------------------|
| `agent` | string | **Yes** | — | Must be `"deep-research-pro-preview-12-2025"` |
| `input` | string \| Content[] \| Turn[] | **Yes** | — | The research query |
| `background` | boolean | **Yes** | — | **Must be `true`** for all agent interactions |
| `stream` | boolean | No | `false` | Set `true` for SSE streaming; append `?alt=sse` for REST |
| `store` | boolean | No | `true` | **Cannot be `false`** when `background=true` |
| `agent_config` | object | No | — | Only field: `thinking_summaries` ("auto" \| "none") |
| `tools` | Tool[] | No | — | Only `file_search` can be added; google_search and url_context are built-in |
| `system_instruction` | string | No | — | Accepted but not documented as influencing Deep Research behavior |
| `previous_interaction_id` | string | No | — | Chain to a completed interaction for follow-up |
| `response_modalities` | string[] | No | — | Requested output modalities |
| `response_format` | object | No | — | **Not supported** with Deep Research |
| `response_mime_type` | string | No | — | **Not supported** with Deep Research |
| `generation_config` | object | No | — | **Cannot be used** with agents (use `agent_config` instead) |
| `model` | string | No | — | **Mutually exclusive** with `agent` |

### The agent_config object

```python
agent_config = {
    "type": "deep-research",        # Required discriminator
    "thinking_summaries": "auto"    # Optional: "auto" (default) | "none"
}
```

The **only configurable field** is `thinking_summaries`. Set to `"auto"` to receive intermediate reasoning steps during streaming — without this, you get only the final report. The `generation_config` fields (`temperature`, `top_p`, `thinking_level`, `max_output_tokens`) are **not applicable** to Deep Research — the agent manages its own reasoning parameters.

### Input types with examples

**String (simplest):**
```python
input="Research the current state of quantum computing hardware."
```

**Content array (multimodal):**
```python
input=[
    {"type": "text", "text": "Analyze the wildlife in this image and research their conservation status."},
    {"type": "image", "uri": "https://example.com/photo.jpg", "mime_type": "image/jpeg"}
]
```

**Turn array (stateless multi-turn):**
```python
input=[
    {"role": "user", "content": "What are the three largest cities in Spain?"},
    {"role": "model", "content": "Madrid, Barcelona, Valencia."},
    {"role": "user", "content": "Research the economic outlook for the second one."}
]
```

### Multimodal input support

Deep Research supports **images, PDFs, and video** as inputs. The agent analyzes the provided content and then conducts web research contextualized by it. **Audio inputs are explicitly not supported.** Each content type accepts either inline `data` (base64) or a `uri` (public URL or Files API URI).

```json
{
  "input": [
    {"type": "text", "text": "Compare this fiscal report against current public data."},
    {"type": "document", "uri": "files/abc123", "mime_type": "application/pdf"}
  ],
  "agent": "deep-research-pro-preview-12-2025",
  "background": true
}
```

The official docs warn: "Use cautiously, as this increases costs and risks context window overflow."

### system_instruction behavior

The `system_instruction` parameter is accepted on the endpoint and is **interaction-scoped** — it must be re-specified in each new interaction (not inherited via `previous_interaction_id`). However, for Deep Research specifically, **no official examples demonstrate its use**, and steerability is documented as being achieved through the input prompt itself. The recommended approach is to embed formatting and behavioral instructions directly in the `input` text (e.g., "Format as a strategic briefing with tables comparing top 3 companies").

### The store=false constraint

**`background=true` requires `store=true`.** Since Deep Research mandates `background=true`, you **cannot opt out of server-side storage**. Setting `store=false` with `background=true` returns a `400 INVALID_ARGUMENT` error. Data retention is **55 days** on paid tier, **1 day** on free tier.

---

## 4. Tool integrations

### Default tools: google_search and url_context

Deep Research has `google_search` and `url_context` **enabled by default** — you do not specify them in the `tools` array. The agent autonomously formulates search queries, reads results, identifies knowledge gaps, and iterates. These tools are **not independently configurable** — you cannot disable them, pass parameters to them, or control their behavior. The `GoogleSearch` tool type does support an optional `search_types` array (`["web_search", "image_search"]`) in the general API, but this is not documented as configurable for Deep Research.

### file_search: complete setup flow

File search with Deep Research is labeled **experimental**.

**Step 1 — Create a FileSearchStore:**
```python
store = client.file_search_stores.create(
    config={'display_name': 'my-research-data'}
)
# Returns: fileSearchStores/my-research-data-abc123def456
```

Store names are globally scoped, auto-generated from `display_name` plus a 12-character random suffix. Maximum **40 characters**, lowercase alphanumeric or dashes only.

**Step 2 — Upload files:**
```python
# Option A: Direct upload
operation = client.file_search_stores.upload_to_file_search_store(
    file='report.pdf',
    file_search_store_name=store.name,
    config={
        'display_name': 'Q4 Report',
        'custom_metadata': [],      # Optional
        'chunking_config': {},      # Optional
        'mime_type': 'application/pdf'
    }
)
while not operation.done:
    time.sleep(5)
    operation = client.operations.get(operation)

# Option B: Upload via Files API then import
file = client.files.upload(file="report.pdf")
operation = client.file_search_stores.import_file(
    file_search_store_name=store.name,
    config={'file_name': file.name}
)
```

Supported file formats include **PDF, TXT, CSV, DOC, DOCX, XLS, XLSX**, and more. Per-file size limit is **100MB**. Files uploaded via the raw Files API are deleted after 48 hours, but data imported into a FileSearchStore persists until manually deleted. The store uses `gemini-embedding-001` for automatic chunking and vector indexing.

**Step 3 — Use with Deep Research:**
```python
interaction = client.interactions.create(
    input="Compare our 2025 fiscal report against current public web news.",
    agent="deep-research-pro-preview-12-2025",
    background=True,
    tools=[{
        "type": "file_search",
        "file_search_store_names": ["fileSearchStores/my-research-data-abc123def456"]
    }]
)
```

**Known issue:** Multiple forum reports cite 503 errors for files larger than ~10KB during upload, and some API key permission issues with file search stores.

### Function calling, code execution, and MCP with Deep Research

All three are **explicitly not supported.** The official documentation states: "You cannot currently provide custom Function Calling tools or remote MCP (Model Context Protocol) servers to the Deep Research agent." Code execution tools are also excluded.

These tools work with `model`-based interactions (e.g., `gemini-3-flash-preview`) but not with `agent`-based interactions. MCP specifically requires Streamable HTTP servers and does not yet work with Gemini 3 models. The exact error when attempting to pass unsupported tools to Deep Research is not documented; the tools are silently rejected or return a `400 INVALID_ARGUMENT`.

---

## 5. Execution model and lifecycle

### What happens between create() and completion

1. `POST /v1beta/interactions` with `agent` and `background: true` → server returns immediately with a partial Interaction object (`id`, `status: "in_progress"`)
2. The agent executes autonomously: **Plan → Search → Read → Iterate → Output**
3. It formulates search queries, reads web pages via `url_context`, identifies knowledge gaps, and repeats
4. A standard task performs **~80 search queries**; complex tasks up to **~160 queries**
5. The interaction transitions to a terminal state: `completed`, `failed`, or `cancelled`

### Status state machine

```
in_progress → completed    (normal success)
in_progress → failed       (error or timeout)
in_progress → cancelled    (user-initiated or system-initiated cancel)
```

The `requires_action` status is used for standard model interactions with function calling — Deep Research handles all tool calls internally and never enters this state.

### Timeout behavior

The **hard server-side timeout is 60 minutes**. Most tasks complete within **20 minutes**. When the timeout is reached, the interaction should transition to `failed`. However, there are well-documented bugs where interactions get **stuck in `in_progress` indefinitely** and never transition to any terminal state (see Section 10).

### Concurrent interaction limits

**No explicit concurrency limit is published.** The official rate limits page does not list specific limits for `deep-research-pro-preview-12-2025`. A Google PM confirmed that "you can run multiple `background=True` research tasks simultaneously," but the practical limit is governed by per-project RPM/RPD/TPM quotas visible in AI Studio at `aistudio.google.com/rate-limit`.

### Interaction retention

| Tier | Retention |
|------|-----------|
| Paid | **55 days** |
| Free | **1 day** |

After the retention period, interactions are automatically deleted. You can manually delete earlier via `DELETE /v1beta/interactions/{id}`.

### Cancel endpoint behavior

`POST /v1beta/interactions/{id}/cancel` works only on running background interactions. The docs do not specify whether cancellation is immediate or waits for the current step. Community reports show cases where the agent completes with `cancelled` status and zero output near-instantly, suggesting **cancellation is near-immediate**. The endpoint returns the Interaction object with `status: "cancelled"`.

---

## 6. Every method to retrieve results

### Polling via GET

```bash
GET /v1beta/interactions/{id}
Header: x-goog-api-key: $GEMINI_API_KEY
```

**Response when `in_progress`:** Returns the Interaction object with `status: "in_progress"`, `outputs` absent or empty, `usage` null. Poll at **10-second intervals** (recommended by community guides).

**Response when `completed`:** Returns the **full Interaction object including the complete research report** in `outputs[-1].text`, plus the complete `usage` object with all token counts. Annotations (source citations) are in `outputs[-1].annotations[]`.

**Response when `failed` or `cancelled`:** Returns the Interaction with the terminal status, no outputs, and potentially an error field.

```python
# Complete polling pattern
import time
from google import genai

client = genai.Client()
interaction = client.interactions.create(
    agent='deep-research-pro-preview-12-2025',
    input="Research the current state of quantum computing hardware.",
    background=True
)

while True:
    interaction = client.interactions.get(interaction.id)
    if interaction.status == "completed":
        print(interaction.outputs[-1].text)
        break
    elif interaction.status in ("failed", "cancelled"):
        print(f"Terminal status: {interaction.status}")
        break
    time.sleep(10)
```

### Streaming via SSE

Initiate with `stream=True` and `background=True`. For REST, append `?alt=sse`. To receive real-time thinking progress, set `agent_config.thinking_summaries` to `"auto"`.

**Every SSE event type:**

| Event type | Class | Key fields |
|-----------|-------|------------|
| `interaction.start` | InteractionStartEvent | `interaction` (partial, with `id`), `event_id` |
| `interaction.status_update` | InteractionStatusUpdate | `interaction_id`, `status`, `event_id` |
| `content.start` | ContentStart | `index`, `content` (with `type`), `event_id` |
| `content.delta` | ContentDelta | `index`, `delta` (polymorphic), `event_id` |
| `content.stop` | ContentStop | `index`, `event_id` |
| `interaction.complete` | InteractionCompleteEvent | `interaction` (usage metadata only), `event_id` |
| `error` | ErrorEvent | `error` (code, message), `event_id` |

**Every delta type** (discriminated by `delta.type`): `text`, `image`, `audio`, `document`, `video`, `thought_summary`, `thought_signature`, `function_call`, `function_result`, `code_execution_call`, `code_execution_result`, `url_context_call`, `url_context_result`, `google_search_call`, `google_search_result`, `mcp_server_tool_call`, `mcp_server_tool_result`, `file_search_call`, `file_search_result`.

For Deep Research, the relevant delta types are primarily `text` (report chunks) and `thought_summary` (intermediate reasoning updates).

**Critical: `interaction.complete` does NOT contain `outputs`.** During streaming, the final event contains only usage metadata and status. You **must reconstruct the full output by accumulating `content.delta` events** client-side.

```python
# Complete streaming pattern
stream = client.interactions.create(
    agent="deep-research-pro-preview-12-2025",
    input="Research quantum computing hardware in 2026.",
    background=True,
    stream=True,
    agent_config={"type": "deep-research", "thinking_summaries": "auto"}
)

interaction_id = None
last_event_id = None
report = ""

for chunk in stream:
    if chunk.event_type == "interaction.start":
        interaction_id = chunk.interaction.id
    if chunk.event_id:
        last_event_id = chunk.event_id
    if chunk.event_type == "content.delta":
        if chunk.delta.type == "text":
            report += chunk.delta.text
        elif chunk.delta.type == "thought_summary":
            print(f"[Thinking] {chunk.delta.content.text}", flush=True)
    elif chunk.event_type == "interaction.complete":
        print(f"\nComplete. Usage: {chunk.interaction.usage}")
```

### Stream reconnection

If the connection drops, resume using `interactions.get()` with `stream=True` and `last_event_id`:

```python
# Resume from last known event
resume_stream = client.interactions.get(
    id=interaction_id,
    stream=True,
    last_event_id=last_event_id
)
for chunk in resume_stream:
    # Process events as above
```

For REST: `GET /v1beta/interactions/{id}?stream=true&last_event_id={LAST_EVENT_ID}&alt=sse`. The server resumes sending events **after** the specified `last_event_id`. If `last_event_id` is omitted, the stream replays from the beginning. Track both `interaction_id` (from `interaction.start`) and `last_event_id` (from any event's `event_id` field) for reliable reconnection.

### No webhook or callback mechanism

There is **no push-based notification system**. The only retrieval methods are polling (GET) and streaming (SSE). Production patterns from Karl Weinmeister's guide use Cloud Pub/Sub worker pools or Cloud Scheduler for asynchronous result checking.

---

## 7. Multi-turn and conversation state

### How previous_interaction_id works

Pass `previous_interaction_id` with the ID of a completed interaction to continue the conversation. The server retrieves the full conversation history from that ID — you only send the new `input`. This enables asking follow-up questions, requesting clarification, or elaborating on specific sections without restarting.

```python
follow_up = client.interactions.create(
    input="Elaborate on the quantum error correction section.",
    agent="deep-research-pro-preview-12-2025",
    previous_interaction_id=completed_interaction.id,
    background=True
)
```

### Mixing agents and models in chains

**Yes — you can freely chain Deep Research → standard model → Deep Research.** The official docs explicitly state: "You have the flexibility to mix and match Agent and Model interactions within a conversation."

```python
# Step 1: Deep Research generates report
research = client.interactions.create(
    agent="deep-research-pro-preview-12-2025",
    input="Research quantum computing hardware in 2026.",
    background=True
)
# ... poll until completed ...

# Step 2: Standard model translates the report
translation = client.interactions.create(
    model="gemini-3-flash-preview",
    input="Translate the report into German.",
    previous_interaction_id=research.id
)

# Step 3: Image model visualizes findings
visual = client.interactions.create(
    model="gemini-3-pro-image-preview",
    input="Create a timeline infographic from the report.",
    previous_interaction_id=research.id
)
```

Conversations can also be **"forked"** by referencing an older interaction ID with a completely different prompt.

### Inherited vs reset parameters

**Only conversation history (inputs and outputs) is inherited.** Everything else is **interaction-scoped and must be re-specified:**

- `tools` — reset per interaction
- `system_instruction` — reset per interaction
- `generation_config` / `agent_config` — reset per interaction

### Chain depth limits and token economics

No explicit chain depth limit is documented. The practical limit is the context window of the underlying model. Each chained interaction increases `total_input_tokens` as conversation history grows, but **implicit caching** offsets much of the cost — the `total_cached_tokens` field tracks this. The docs confirm: "Using `previous_interaction_id` allows the system to more easily utilize implicit caching for the conversation history, which improves performance and reduces costs."

---

## 8. Rate limits, quotas, and throttling

### Tier system

| Tier | Qualification |
|------|--------------|
| Free | Users in eligible countries (**Deep Research NOT available**) |
| Tier 1 | Billing account linked to project |
| Tier 2 | Total spend > $250 AND ≥30 days since first payment |
| Tier 3 | Total spend > $1,000 AND ≥30 days since first payment |

**Deep Research is not available on the free tier.** Gemini 3.1 Pro shows "Not available" for free-tier access.

### Rate limit specifics

Rate limits are measured across **RPM** (requests per minute), **TPM** (tokens per minute), and **RPD** (requests per day), applied **per project, not per API key**. RPD resets at midnight Pacific Time.

**The official rate limits page does not publish specific numbers for `deep-research-pro-preview-12-2025`.** Limits are dynamically managed and viewable only in AI Studio at `aistudio.google.com/rate-limit`. Preview models have "more restrictive" limits than stable models.

For reference, general Gemini 3 Pro batch enqueued token limits by tier:

| Tier | Batch enqueued tokens |
|------|--------------------|
| Tier 1 | 5,000,000 |
| Tier 2 | 500,000,000 |
| Tier 3 | 1,000,000,000 |

### 429 error response

When rate-limited, the API returns:

```json
{
  "error": {
    "code": 429,
    "message": "Resource exhausted. Please try again later...",
    "errors": [{
      "message": "Resource exhausted...",
      "domain": "global",
      "reason": "rateLimitExceeded"
    }],
    "status": "RESOURCE_EXHAUSTED"
  }
}
```

Response headers may include `x-ratelimit-limit`, `x-ratelimit-remaining`, and `x-ratelimit-reset`, though these are not consistently present. Requests returning 400 or 500 errors are not charged for tokens but **still count against quota**.

### Checking remaining quota

There is **no dedicated quota API endpoint**. Available methods: the AI Studio dashboard (`aistudio.google.com/rate-limit` for real-time per-project limits), `x-ratelimit-remaining` response headers when present, and the Cloud Billing Console filtered to the Gemini API SKU.

### Free search prompts and Deep Research

The **5,000 free search prompts per month** on the paid tier are shared across all Gemini 3 models. Each Deep Research task can execute **80–160 individual search queries** — and Google charges per individual query, not per interaction. A single complex Deep Research task could consume 3% of the monthly free search allowance.

---

## 9. Pricing and token economics

### Gemini 3.1 Pro per-token pricing

| Metric | ≤200K context tokens | >200K context tokens |
|--------|---------------------|---------------------|
| **Input** | $2.00 / 1M tokens | $4.00 / 1M tokens |
| **Output (including thinking)** | $12.00 / 1M tokens | $18.00 / 1M tokens |
| **Context caching (input)** | $0.20 / 1M tokens | $0.40 / 1M tokens |
| **Cache storage** | $4.50 / 1M tokens / hour | $4.50 / 1M tokens / hour |
| **Batch input** | $1.00 / 1M tokens | $2.00 / 1M tokens |
| **Batch output** | $6.00 / 1M tokens | $9.00 / 1M tokens |

### Thinking tokens are billed as output

**Yes.** The pricing page explicitly states "Output price (including thinking tokens)" for all Gemini 3.x models. The `total_thought_tokens` field in the Usage object tracks these separately, but they are billed at the output token rate.

### Google Search pricing

After the free 5,000 prompts/month: **$14 per 1,000 search queries**. Each Deep Research interaction triggers multiple individual queries, and you are charged per query. Retrieved context from Google Search is **not** charged as input tokens (explicitly stated on the pricing page). Google Search grounding was free until January 5, 2026.

### Official cost estimates for Deep Research

| Task complexity | Search queries | Input tokens | Cache rate | Output tokens |
|----------------|---------------|-------------|-----------|--------------|
| **Standard** | ~80 | ~250K | 50–70% | ~60K |
| **Complex** | ~160 | ~900K | 50–70% | ~80K |

**Estimated cost breakdown for a standard task:**
- Google Search: ~$1.12 ($14/1000 × 80 queries)
- Input tokens: ~$0.35–0.50 (factoring in ~60% caching at $0.20/1M)
- Output tokens: ~$0.72 ($12/1M × 60K)
- **Total: approximately $2–3 per research task**

**Complex task estimate: $4–6+** per interaction.

### Real-world developer cost reports

One developer on the Google AI Developer Forum reported running **80 Deep Research calls per day** at approximately **$2.50 per call**, totaling ~$200/day. Token consumption per run ranged from **120K to 500K tokens**, described as "very inconsistent even with the exact same prompt." Another developer spent approximately **$2K just testing** model capabilities.

### No per-interaction cost cap

There is **no way to set a cost cap or token budget on a single Deep Research interaction**. The agent autonomously determines search depth. Project-level monthly spend caps can be set in AI Studio (Settings → Spend page → Monthly spend cap), but this is a blunt instrument that affects all API usage.

---

## 10. Every known bug, edge case, and gotcha

### Interactions stuck in_progress indefinitely

**Severity: Critical. Status: Active as of March 2026.** Deep Research interactions get created with `in_progress` status but never transition to any terminal state. The interaction permanently shows `usage: None` and `outputs: None`. Conditions that trigger this include complex multi-step research prompts, domain-specific queries (same template works for Domain A but fails for Domain B), and content filter triggers on intermediate search results. The problem **worsened significantly around March 4–5, 2026**, going from ~5% failure to near-100% for some users. With streaming enabled, the agent produces 4–5 thinking steps then the stream dies silently with no error. **Workaround:** Implement a hard timeout in your polling loop (15–20 minutes) and treat timeout as failure. Always persist results to your own storage immediately upon completion.

### 403 permission_denied on GET after successful POST

**Severity: Critical. Status: Intermittent.** `POST /v1beta/interactions` returns 200 with a valid interaction ID, but `GET /v1beta/interactions/{id}` immediately returns `403 permission_denied` with body: `{"error": {"message": "There was a problem processing your request. You will not be charged.", "code": "permission_denied"}}`. This reproduces with both raw REST and the Python SDK. The same API key works for `generateContent` — only the interactions GET endpoint fails. **Workaround:** Wait and retry. The issue appears transient.

### Instant cancel with no output

Interactions sometimes transition from `in_progress` to `cancelled` instantly with zero output and zero usage. This appears to be a server-side capacity or internal rate-limiting issue, not a user-initiated cancellation. The `InteractionCompleteEvent` arrives with `status='cancelled'`, `outputs=None`, `usage=None`.

### Lost or reverted interaction results

Previously completed interactions have been observed reverting to `in_progress` status with `None` outputs when re-fetched days later — within the documented 55-day retention period. The API returns HTTP 200 but with stale/incorrect data. **Workaround:** Always persist `interaction.outputs[-1].text` to your own durable storage (Cloud Storage, database) immediately upon completion. Never rely on the Interactions API as a long-term data store.

### Sources and citations not returned

Completed research reports sometimes contain full text but with **no source annotations** — the `annotations` array is empty or absent. The Gemini App consumer version provides a Sources Panel with clickable citations, but the API does not consistently return equivalent structured data. **Workaround:** Embed explicit instructions in the prompt asking the agent to include inline URLs in the report text.

### 503 transient errors

Deep Research returns 503 errors during high-load periods with messages like "experiencing unusually high traffic." These are retryable with **exponential backoff** (start at 1 second, double up to 60 seconds max). Free-tier rate limits were reduced 50–80% in December 2025.

### Streaming output batching

Thinking update events may be **batched in ~15-second groups** of 2–3 rather than arriving individually. The `outputs` array is empty in the `interaction.complete` streaming event — you must accumulate `content.delta` events. The stream can die silently mid-execution (related to the stuck-in-progress bug).

### SDK vs REST behavior differences

Bug #2 (403 on GET) reproduces identically with both SDK and REST. The SDK emits `UserWarning: Interactions usage is experimental and may change in future versions`. The `include_input=True` parameter on `get()` is primarily useful in the SDK for debugging. SDK version matters significantly — `google-genai >= 1.55.0` is the minimum.

### Polling a deleted interaction

After calling `DELETE /v1beta/interactions/{id}`, subsequent GET requests for that ID return an error. The exact error code is not documented but the interaction is no longer accessible.

### Canceling an already-completed interaction

Not explicitly documented. Community reports focus on the reverse problem (system auto-cancellation). Calling cancel on a completed interaction likely returns the interaction in its `completed` state without modification.

### The countTokens API does not work with Deep Research

Confirmed by Google PM Ali Cevik on the developer forum: `countTokens` does not work for agent-based interactions since they use an agent identifier rather than a model identifier.

### Undocumented response quirks

The `object` field always returns `"interaction"` (not prominently documented). The `role` field is `"agent"` for Deep Research vs `"model"` for standard calls. The `agent_config` field may return as `None` in the response even when specified in the request. The `created` and `updated` timestamps are identical for stuck interactions.

---

## 11. Comparison with Vertex AI Enterprise Deep Research

### Vertex AI uses a completely separate API surface

| Aspect | Gemini API (Interactions API) | Vertex AI Enterprise (streamAssist) |
|--------|------------------------------|-------------------------------------|
| **Endpoint** | `generativelanguage.googleapis.com/v1beta/interactions` | `discoveryengine.googleapis.com/v1/.../streamAssist` |
| **Authentication** | API key (`x-goog-api-key`) | OAuth Bearer + `X-Goog-User-Project` header |
| **Agent ID** | `deep-research-pro-preview-12-2025` | `deep_research` |
| **Execution model** | Async background (POST + poll GET) | Single streaming response |
| **Research plan review** | No — agent executes autonomously | Yes — two-step: review plan then "Start Research" |
| **Data sources** | Web (google_search, url_context) + File Search stores | Vertex AI Search data stores + optional web grounding |
| **Stateful follow-ups** | `previous_interaction_id` chaining | Session-based (`session` parameter) |
| **Status** | Public beta (no allowlist) | GA with allowlist |
| **Audio summaries** | Not available | 1–2 minute generated audio summary |
| **Image/video generation** | Not available | Available via `ImageGenerationSpec` / `VideoGenerationSpec` |
| **Enterprise features** | Limited | Full DLP, admin controls, workspace sharing policies |

### The Vertex AI streamAssist endpoint

```
POST https://discoveryengine.googleapis.com/v1/projects/{PROJECT_ID}/locations/global/collections/default_collection/engines/{APP_ID}/assistants/default_assistant:streamAssist
```

The Vertex AI version uses a **two-step flow**: the first request submits the query and returns a research plan; the second request sends "Start Research" with the session ID from step 1 to trigger execution. This allows human review of the research plan before committing resources — a feature the Interactions API does not support.

### Timeline for Interactions API on Vertex AI

**No official timeline exists.** As of March 2026, the two surfaces are on **separate development tracks** — Vertex AI uses Discovery Engine infrastructure while the Interactions API is built on the Generative Language API infrastructure. Google's Interactions API blog post states "This is just the start" but provides no Vertex AI integration date.

---

## Production integration reference code

### Complete Python integration with resilient streaming and reconnection

```python
import time
from google import genai

client = genai.Client()  # Uses GEMINI_API_KEY env var

AGENT = "deep-research-pro-preview-12-2025"
POLL_INTERVAL = 10
MAX_WAIT = 1200  # 20-minute safety timeout

def research_polling(query: str) -> str:
    """Polling-based Deep Research with timeout safety."""
    interaction = client.interactions.create(
        agent=AGENT, input=query, background=True
    )
    start = time.time()
    while time.time() - start < MAX_WAIT:
        result = client.interactions.get(interaction.id)
        if result.status == "completed":
            return result.outputs[-1].text
        elif result.status in ("failed", "cancelled"):
            raise RuntimeError(f"Research {result.status}: {result.id}")
        time.sleep(POLL_INTERVAL)
    raise TimeoutError(f"Research timed out after {MAX_WAIT}s: {interaction.id}")


def research_streaming(query: str) -> str:
    """Streaming Deep Research with reconnection support."""
    interaction_id = None
    last_event_id = None
    report = ""
    is_complete = False

    def process(event_stream):
        nonlocal interaction_id, last_event_id, report, is_complete
        for chunk in event_stream:
            if chunk.event_type == "interaction.start":
                interaction_id = chunk.interaction.id
            if chunk.event_id:
                last_event_id = chunk.event_id
            if chunk.event_type == "content.delta":
                if chunk.delta.type == "text":
                    report += chunk.delta.text
                elif chunk.delta.type == "thought_summary":
                    print(f"[Thinking] {chunk.delta.content.text}")
            if chunk.event_type in ("interaction.complete", "error"):
                is_complete = True

    try:
        stream = client.interactions.create(
            agent=AGENT, input=query, background=True, stream=True,
            agent_config={"type": "deep-research", "thinking_summaries": "auto"}
        )
        process(stream)
    except Exception as e:
        print(f"Connection dropped: {e}")

    while not is_complete and interaction_id:
        time.sleep(2)
        try:
            resume = client.interactions.get(
                id=interaction_id, stream=True, last_event_id=last_event_id
            )
            process(resume)
        except Exception:
            time.sleep(5)  # Exponential backoff in production

    return report
```

### Complete JavaScript integration

```javascript
import { GoogleGenAI } from '@google/genai';

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });
const AGENT = 'deep-research-pro-preview-12-2025';

async function researchPolling(query) {
    const initial = await ai.interactions.create({
        agent: AGENT, input: query, background: true
    });
    const deadline = Date.now() + 20 * 60 * 1000;
    while (Date.now() < deadline) {
        const result = await ai.interactions.get(initial.id);
        if (result.status === 'completed') {
            return result.outputs[result.outputs.length - 1].text;
        }
        if (['failed', 'cancelled'].includes(result.status)) {
            throw new Error(`Research ${result.status}: ${result.id}`);
        }
        await new Promise(r => setTimeout(r, 10000));
    }
    throw new Error(`Research timed out: ${initial.id}`);
}

async function researchStreaming(query) {
    const stream = await ai.interactions.create({
        agent: AGENT, input: query, background: true, stream: true,
        agent_config: { type: 'deep-research', thinking_summaries: 'auto' }
    });
    let report = '';
    for await (const chunk of stream) {
        if (chunk.event_type === 'content.delta') {
            if (chunk.delta.type === 'text') report += chunk.delta.text;
            else if (chunk.delta.type === 'thought_summary')
                console.log(`[Thinking] ${chunk.delta.content.text}`);
        }
    }
    return report;
}
```

### File search integration with Deep Research

```python
# 1. Create store
store = client.file_search_stores.create(config={'display_name': 'research-docs'})

# 2. Upload and index
op = client.file_search_stores.upload_to_file_search_store(
    file='quarterly-report.pdf',
    file_search_store_name=store.name,
    config={'display_name': 'Q4 2025 Report'}
)
while not op.done:
    time.sleep(5)
    op = client.operations.get(op)

# 3. Research combining private data + web
interaction = client.interactions.create(
    agent="deep-research-pro-preview-12-2025",
    input="Compare our Q4 2025 report against current market trends and competitor filings.",
    background=True,
    tools=[{"type": "file_search", "file_search_store_names": [store.name]}]
)
```

### Multi-turn follow-up chain

```python
# Research → Translate → Visualize
research = research_polling("Analyze the 2026 semiconductor supply chain outlook.")

# Follow up with a different model for translation
translation = client.interactions.create(
    model="gemini-3-flash-preview",
    input="Translate the research report into Japanese.",
    previous_interaction_id=research_interaction_id
)

# Fork the conversation for image generation
image = client.interactions.create(
    model="gemini-3-pro-image-preview",
    input="Create an infographic timeline from the report.",
    previous_interaction_id=research_interaction_id
)
```

---

## Conclusion: what this means for production integrations

The Gemini Deep Research Agent API is a **powerful but immature** capability. It can autonomously produce research reports that achieve state-of-the-art scores on benchmarks like Humanity's Last Exam (**46.4%**) and DeepSearchQA (**66.1%**), at a cost of roughly **$2–6 per research task**. The API surface is clean — four endpoints, one agent identifier, one configurable parameter (`thinking_summaries`).

The three most critical production concerns are **reliability** (interactions stuck indefinitely with no error signal), **cost unpredictability** (the agent autonomously determines search depth with no budget cap), and **citation inconsistency** (source annotations sometimes missing entirely). Any production integration must implement hard polling timeouts, immediate result persistence to durable storage, and exponential backoff retry logic. The `countTokens` API does not work with agents, so cost estimation must rely on the official ~80–160 query benchmarks.

The Vertex AI Enterprise surface offers research plan review, audio summaries, and enterprise controls through a completely separate `discoveryengine.googleapis.com` endpoint — but there is no timeline for unifying the two surfaces. For most developer use cases, the Interactions API at `generativelanguage.googleapis.com/v1beta/` with API key authentication remains the primary integration path.