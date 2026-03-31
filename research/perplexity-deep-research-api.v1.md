# Perplexity Sonar Deep Research API: Complete Technical Reference

The Perplexity Sonar Deep Research API (`sonar-deep-research`) is an autonomous, multi-search research model accessible via a REST endpoint fully compatible with OpenAI's Chat Completions format. **It is the only Sonar model supporting asynchronous execution and the `reasoning_effort` parameter**, and it carries a unique five-component billing structure spanning input tokens, output tokens, citation tokens, reasoning tokens, and per-search-query fees. This document covers every detail a senior engineer needs to build and operate a production integration against it, accurate as of early 2026.

---

## 1. Endpoint and authentication

### Base URLs

| Purpose | URL | Method |
|---------|-----|--------|
| Synchronous completions | `https://api.perplexity.ai/chat/completions` | POST |
| Async submit | `https://api.perplexity.ai/v1/async/sonar` | POST |
| Async list all jobs | `https://api.perplexity.ai/v1/async/sonar` | GET |
| Async get job by ID | `https://api.perplexity.ai/v1/async/sonar/{request_id}` | GET |

The synchronous path `/chat/completions` also accepts the alias `/v1/sonar`. The OpenAI SDK auto-appends `/chat/completions` to the base URL, so configure `base_url="https://api.perplexity.ai"`. **No regional endpoints or mirrors are published.** The MCP server allows an override via the `PERPLEXITY_BASE_URL` environment variable but no alternate domains exist.

### Authentication

Every request requires a standard Bearer token header:

```
Authorization: Bearer <PERPLEXITY_API_KEY>
Content-Type: application/json
```

Keys are generated in the [API Portal](https://perplexity.ai/account/api) under the API Keys tab. Key rotation was introduced in September 2025: generate a new key, update applications, then deactivate the old key. The official SDKs auto-read the `PERPLEXITY_API_KEY` environment variable.

---

## 2. Request schema — `POST /chat/completions`

### Required fields

| Field | Type | Description |
|-------|------|-------------|
| `model` | `string` | `"sonar-deep-research"` (also accepts `"sonar"`, `"sonar-pro"`, `"sonar-reasoning-pro"`) |
| `messages` | `ChatMessage[]` | Array of message objects |

Each message object contains:

- **`role`** (`string`): `"system"`, `"user"`, `"assistant"`, or `"tool"`
- **`content`** (`string`): The message text. Multimodal content (image URLs via `image_url`, file URLs for PDF/DOC/DOCX/TXT/RTF via `file_url`) is supported on sonar and sonar-pro but **not documented as functional for sonar-deep-research**.

### Complete optional parameter reference

| Field | Type | Default | Valid values | Behavioral effect |
|-------|------|---------|--------------|-------------------|
| `max_tokens` | `integer \| null` | Model-dependent | `0 < x <= 128000` | Caps completion output length. Controls cost |
| `stream` | `boolean \| null` | `false` | `true`, `false` | Enables SSE streaming |
| `stream_mode` | `enum<string>` | `"full"` | `"full"`, `"concise"` | Controls streaming verbosity |
| `stop` | `string \| string[]` | None | Any string(s) | Stop sequence(s) for generation |
| `response_format` | `object` | None | See below | Structured output: text, JSON schema, or regex |
| `reasoning_effort` | `enum<string> \| null` | `"medium"` | `"low"`, `"medium"`, `"high"` | **Deep-research only.** Controls research depth, search count, and reasoning token consumption. `"low"` ≈ $0.41/query, `"high"` ≈ $1.32/query |
| `web_search_options` | `object` | None | `{"search_context_size": "low"\|"medium"\|"high"}` | Controls volume of web content retrieved |
| `search_mode` | `enum<string> \| null` | None | `"web"`, `"academic"`, `"sec"` | `"academic"` prioritizes scholarly sources; `"sec"` focuses on SEC filings |
| `search_domain_filter` | `string[] \| null` | None | Up to 20 domain strings | Allowlist (plain) or denylist (`-` prefix). Mutually exclusive per request |
| `search_recency_filter` | `enum<string> \| null` | None (all time) | `"hour"`, `"day"`, `"week"`, `"month"`, `"year"` | Restricts search results to the specified recency window |
| `search_after_date_filter` | `string \| null` | None | Date string | Results published after this date only |
| `search_before_date_filter` | `string \| null` | None | Date string | Results published before this date only |
| `search_language_filter` | `string[] \| null` | None | Language codes | Filters search results by language |
| `return_images` | `boolean \| null` | `false` | `true`, `false` | Includes image objects in response |
| `return_related_questions` | `boolean \| null` | `false` | `true`, `false` | Includes suggested follow-up questions |
| `enable_search_classifier` | `boolean \| null` | None | `true`, `false` | Lets the model decide whether to search |
| `disable_search` | `boolean \| null` | None | `true`, `false` | Disables web search entirely |
| `safe_search` | `boolean \| null` | `true` | `true`, `false` | SafeSearch content filtering |
| `language_preference` | `string \| null` | None | Language string | Preferred language for search results (sonar/sonar-pro) |

### Legacy parameters not in current schema

**`temperature`, `top_p`, `top_k`, `frequency_penalty`, `presence_penalty`** are **not listed** in the current official API reference. Perplexity's help center states the API "doesn't offer manual control over modeling parameters like temperature or top-p." The API may silently accept them for backward compatibility, but their effect is unspecified for Sonar models. Third-party wrappers (LiteLLM, AIML API) may still pass them through.

### `response_format` variants

1. `{"type": "text"}` — Default plain text
2. `{"type": "json_schema", "json_schema": {"name": "...", "schema": {...}}}` — Structured JSON output
3. Regex-based format — Pattern-constrained output

**Gotcha:** The first request using a new JSON schema incurs a **10–30 second** compilation delay. For `sonar-reasoning-pro`, the `<think>` section is **not stripped** from JSON mode responses — you must parse it out yourself.

---

## 3. Response schema

### Top-level response object

```json
{
  "id": "pplx-abc123",
  "model": "sonar-deep-research",
  "created": 1711900000,
  "object": "chat.completion",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Research findings with inline citations [1][2]...",
        "reasoning_steps": []
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 33,
    "completion_tokens": 7163,
    "total_tokens": 7196,
    "citation_tokens": 20016,
    "num_search_queries": 18,
    "reasoning_tokens": 73997,
    "search_context_size": "low",
    "cost": {
      "input_tokens_cost": 0.000066,
      "output_tokens_cost": 0.057304,
      "citation_tokens_cost": 0.040032,
      "reasoning_tokens_cost": 0.221991,
      "search_queries_cost": 0.09,
      "request_cost": 0.0,
      "total_cost": 0.41
    }
  },
  "search_results": [
    {
      "title": "Source Page Title",
      "url": "https://example.com/article",
      "date": "2025-11-15",
      "last_updated": "2025-11-20",
      "snippet": "",
      "source": "web"
    }
  ],
  "images": [],
  "related_questions": []
}
```

### Key field details

**`usage` object** — Contains **seven fields** plus a nested `cost` breakdown (added July 2025). The `total_tokens` field equals `prompt_tokens + completion_tokens` and **does not include `citation_tokens` or `reasoning_tokens`**, making it misleading for cost estimation on deep research.

**`search_results` array** — Replaces the deprecated `citations` field (deprecated May 2025). Each object contains `title` (string), `url` (string), `date` (string), `last_updated` (string), `snippet` (string, often empty), and `source` (string, currently always `"web"`).

**`images` array** — Populated when `return_images: true`. Each object: `image_url`, `origin_url`, `title`, `width`, `height`.

**`finish_reason`** — Known value: `"stop"`. **Critical gotcha for deep research:** `finish_reason: "stop"` does not reliably indicate the response is complete. Truncation frequently occurs mid-sentence with `"stop"` returned.

---

## 4. Streaming implementation

Enable streaming by setting `"stream": true`. Optionally set `"stream_mode": "full"` (default) or `"concise"`.

### SSE event format

The response uses standard Server-Sent Events with `Content-Type: text/event-stream`. Each event is a `data:` prefixed JSON line:

```
data: {"id":"pplx-abc","model":"sonar-deep-research","choices":[{"index":0,"delta":{"role":"assistant","content":"The "},"finish_reason":null}],"usage":null}

data: {"id":"pplx-abc","model":"sonar-deep-research","choices":[{"index":0,"delta":{"content":"latest "},"finish_reason":null}],"usage":null}

data: [DONE]
```

### Delta chunking behavior

Each chunk's `choices[0].delta` object contains incremental content fragments. **Important caveat:** Unlike OpenAI's API which uses `object: "chat.completion.chunk"`, Perplexity uses `object: "chat.completion"` for streaming responses. Some implementations (notably LiteLLM, per GitHub issue #8455) have observed **cumulative content** rather than true incremental deltas — meaning each chunk's `content` contains all text so far. The official Perplexity SDK handles this correctly.

### Citations and search results arrive in the final chunk

**Search results and metadata are delivered in the final chunk(s) of a streaming response, not progressively during the stream.** The `search_results`, `usage`, and `cost` fields only appear in later/final events. If your UI needs source attribution immediately, consider non-streaming requests.

### Stream completion detection

Three signals, use any combination:
1. The `data: [DONE]` event
2. `finish_reason: "stop"` in the final chunk's choices
3. The `type` field set to `"end_of_stream"`

### Timeout considerations for deep research streaming

Deep research requests can run **2–40+ minutes**. Long pauses between stream chunks (minutes of silence) are normal. Increase client read timeouts accordingly. The official SDK defaults to **15-minute** timeouts. For long queries, the async API is strongly recommended over synchronous streaming.

---

## 5. Async API — the polling workflow for deep research

The async API is **only available for `sonar-deep-research`**. It eliminates timeout risk for long-running research queries.

### Workflow: submit → poll → retrieve

**Step 1 — Submit:**

```bash
curl -X POST https://api.perplexity.ai/v1/async/sonar \
  -H "Authorization: Bearer $PERPLEXITY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "request": {
      "model": "sonar-deep-research",
      "messages": [{"role": "user", "content": "Comprehensive analysis of quantum computing in 2025"}]
    },
    "idempotency_key": "unique-key-12345"
  }'
```

The `request` wrapper is required. The optional `idempotency_key` prevents duplicate submissions.

**Response (200 OK):**

```json
{
  "id": "req_abc123",
  "model": "sonar-deep-research",
  "created_at": 1711900000,
  "status": "CREATED",
  "started_at": null,
  "completed_at": null,
  "failed_at": null,
  "error_message": null,
  "response": null
}
```

**Step 2 — Poll:**

```bash
curl https://api.perplexity.ai/v1/async/sonar/req_abc123 \
  -H "Authorization: Bearer $PERPLEXITY_API_KEY"
```

### Status progression

| Status | Meaning |
|--------|---------|
| `CREATED` | Job queued |
| `IN_PROGRESS` | Research underway |
| `COMPLETED` | Results available in `response` |
| `FAILED` | Error; check `error_message` |

**Results have a 7-day TTL** — after that, the job and its output are deleted.

**Known bug:** Community reports indicate the polling status can show `IN_PROGRESS` for 30–40 minutes even when the actual processing completed in ~2 minutes. The `completed_at` timestamp may reveal the discrepancy.

### Rate limits for async endpoints

| Endpoint | Tier 0 | Tier 1 | Tier 2 | Tier 3 | Tier 4 | Tier 5 |
|----------|--------|--------|--------|--------|--------|--------|
| POST `/v1/async/sonar` | 5 RPM | 10 | 20 | 40 | 60 | 100 |
| GET `/v1/async/sonar` (list) | 3,000 RPM | 3,000 | 3,000 | 3,000 | 3,000 | 3,000 |
| GET `/v1/async/sonar/{id}` | 6,000 RPM | 6,000 | 6,000 | 6,000 | 6,000 | 6,000 |

**No webhook or callback mechanism exists.** Polling is the only option. A recommended approach: poll every 10–15 seconds for typical queries, with exponential backoff up to 30 seconds for long-running jobs.

### Python async polling example

```python
import time
import requests

API_KEY = "your_api_key"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

# Submit
resp = requests.post(
    "https://api.perplexity.ai/v1/async/sonar",
    headers=HEADERS,
    json={
        "request": {
            "model": "sonar-deep-research",
            "messages": [{"role": "user", "content": "Deep analysis of CRISPR therapy trials in 2025"}],
            "reasoning_effort": "high"
        }
    }
)
request_id = resp.json()["id"]
print(f"Submitted: {request_id}")

# Poll with backoff
delay = 10
while True:
    status_resp = requests.get(
        f"https://api.perplexity.ai/v1/async/sonar/{request_id}",
        headers=HEADERS
    )
    data = status_resp.json()
    print(f"Status: {data['status']}")

    if data["status"] == "COMPLETED":
        result = data["response"]
        print(result["choices"][0]["message"]["content"])
        print(f"Searches: {result['usage']['num_search_queries']}")
        print(f"Total cost: ${result['usage']['cost']['total_cost']:.4f}")
        break
    elif data["status"] == "FAILED":
        print(f"Failed: {data.get('error_message')}")
        break

    time.sleep(delay)
    delay = min(delay * 1.5, 30)  # Cap at 30s
```

---

## 6. Pricing model

Sonar Deep Research has a **unique five-component billing structure**, unlike other Sonar models which use flat per-request fees.

### Per-unit costs

| Component | Rate | What it measures |
|-----------|------|-----------------|
| Input tokens | **$2 / 1M tokens** | Your prompt tokens |
| Output tokens | **$8 / 1M tokens** | Generated response tokens |
| Citation tokens | **$2 / 1M tokens** | Tokens from processing retrieved web content |
| Reasoning tokens | **$3 / 1M tokens** | Internal reasoning tokens (hidden from response) |
| Search queries | **$5 / 1,000 queries** | Autonomous web searches executed |

**Citation tokens are only billed for deep research.** As of April 2025, sonar, sonar-pro, and sonar-reasoning-pro no longer charge for citation tokens.

### Cost by reasoning effort — official examples from Perplexity documentation

| Component | Low | Medium | High |
|-----------|-----|--------|------|
| Input tokens | 33 ($0.00) | 7 ($0.00) | 8 ($0.00) |
| Output tokens | 7,163 ($0.06) | 3,847 ($0.03) | 4,435 ($0.04) |
| Citation tokens | 20,016 ($0.04) | 47,293 ($0.09) | 58,196 ($0.12) |
| Reasoning tokens | 73,997 ($0.22) | 308,156 ($0.92) | 339,594 ($1.02) |
| Search queries | 18 ($0.09) | 28 ($0.14) | 30 ($0.15) |
| **Total** | **$0.41** | **$1.19** | **$1.32** |

**Reasoning tokens dominate cost**, accounting for 54–77% of the total. Going from `"low"` to `"high"` roughly triples the total cost, driven primarily by reasoning tokens growing from ~74K to ~340K.

### Comparison with other Sonar models

| Model | Input ($/1M) | Output ($/1M) | Per-request fee (per 1K, low/med/high) |
|-------|-------------|---------------|---------------------------------------|
| sonar | $1 | $1 | $5 / $8 / $12 |
| sonar-pro | $3 | $15 | $6 / $10 / $14 |
| sonar-reasoning-pro | $2 | $8 | $6 / $10 / $14 |
| sonar-deep-research | $2 | $8 | No request fee; per-search + token billing |

---

## 7. Rate limits and usage tiers

### Tier progression (lifetime cumulative credit purchases)

| Tier | Threshold | sonar-deep-research RPM | Other Sonar RPM |
|------|-----------|------------------------|-----------------|
| Tier 0 | $0 | **5** | 50 |
| Tier 1 | $50+ | **10** | 150 |
| Tier 2 | $250+ | **20** | 500 |
| Tier 3 | $500+ | **40** | 1,000 |
| Tier 4 | $1,000+ | **60** | 4,000 |
| Tier 5 | $5,000+ | **100** | 4,000 |

Tiers are permanent — once reached, no downgrade. Beyond Tier 5, custom limits can be requested via Perplexity's enterprise form.

### Rate limiting algorithm

Perplexity uses a **leaky bucket algorithm**. The bucket capacity equals the burst limit, and tokens refill continuously at the sustained rate. For example, at 50 RPM: 1 token refills every 1.2 seconds. This allows short bursts up to the bucket capacity, then enforces the sustained rate.

### Rate limit headers and 429 behavior

Standard `X-RateLimit-*` headers are **not explicitly documented**. The primary signal is:

- **HTTP 429** — `"Request rate limit exceeded, please try again later."`
- Responses include an `X-Request-ID` header for debugging

No `Retry-After` header is documented. Recovery is immediate as bucket tokens refill continuously.

### Recommended backoff strategy

```python
import random
import time

def retry_with_backoff(func, max_retries=5):
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            delay = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(delay)
```

The official SDK auto-retries **2 times** with exponential backoff for 408, 409, 429, and ≥500 errors.

---

## 8. Error handling

### HTTP status codes

| Code | Meaning | SDK Exception | Transient? | Auto-retried? |
|------|---------|--------------|------------|---------------|
| 400 | Bad request / invalid params | `BadRequestError` | No | No |
| 401 | Invalid or missing API key | `AuthenticationError` | No | No |
| 402 | Insufficient credits | `APIStatusError` | No | No |
| 403 | Forbidden resource | `PermissionDeniedError` | No | No |
| 404 | Invalid endpoint | `NotFoundError` | No | No |
| 408 | Request timeout | `APIStatusError` | **Yes** | **Yes** |
| 409 | Conflict | `APIStatusError` | **Yes** | **Yes** |
| 422 | Unprocessable entity | `UnprocessableEntityError` | No | No |
| 429 | Rate limit exceeded | `RateLimitError` | **Yes** | **Yes** |
| 500+ | Internal server error | `InternalServerError` | **Yes** | **Yes** |
| 503 | Service unavailable | `APIStatusError` | **Yes** | **Yes** |

### Error response structure

```python
try:
    client.chat.completions.create(...)
except perplexity.APIStatusError as e:
    print(e.status_code)    # int: HTTP status code
    print(e.type)           # str: error type identifier
    print(e.message)        # str: human-readable message
    print(e.response)       # httpx.Response: raw response
    print(e.response.headers.get('X-Request-ID'))  # debugging ID
except perplexity.APIConnectionError as e:
    print(e.__cause__)      # underlying network error
```

### Idempotency

No formal idempotency guarantee exists for the synchronous endpoint. The async API supports an `idempotency_key` field to prevent duplicate submissions. The SDK's auto-retry behavior for transient errors implies safe-to-retry semantics for those status codes.

### Deep-research-specific error: credits charged on timeout

**Credits are deducted even when a synchronous deep research request times out with no output.** This is a known billing concern reported by the community. The async API avoids this because work completes server-side regardless of client connection state.

---

## 9. OpenAI compatibility layer

### Drop-in SDK configuration

The Perplexity API is designed as a **drop-in replacement** for OpenAI's Chat Completions endpoint. Only two changes are needed:

```python
from openai import OpenAI

client = OpenAI(
    api_key="pplx-...",                    # Perplexity API key
    base_url="https://api.perplexity.ai"   # Override base URL
)

# Use exactly like OpenAI
response = client.chat.completions.create(
    model="sonar-deep-research",
    messages=[{"role": "user", "content": "Research query here"}]
)
print(response.choices[0].message.content)
```

### What works identically

Standard OpenAI fields — `model`, `messages`, `max_tokens`, `stream`, `response_format` — work as expected. Streaming uses the same SSE protocol and the same iteration pattern.

### Perplexity-specific parameters require `extra_body`

When using the OpenAI Python SDK, Perplexity-specific parameters **must** be passed via `extra_body`:

```python
response = client.chat.completions.create(
    model="sonar-deep-research",
    messages=[{"role": "user", "content": "Latest fusion energy breakthroughs"}],
    extra_body={
        "search_domain_filter": ["nature.com", "science.org"],
        "search_recency_filter": "month",
        "reasoning_effort": "high",
        "return_related_questions": True,
        "web_search_options": {"search_context_size": "high"}
    }
)
```

Passing them as direct keyword arguments causes `TypeError: create() got an unexpected keyword argument`. In TypeScript, cast with `as any` to pass them directly.

### Response format differences

Perplexity responses include the standard OpenAI fields **plus** additional fields: `search_results`, `citations` (deprecated), `images`, `related_questions`, and `usage.cost`. The OpenAI SDK's typed response object will not have type definitions for these — access them via dictionary syntax or `getattr`.

### Fields silently ignored

OpenAI-specific parameters like `logprobs`, `n`, `tools`, `tool_choice`, and `logit_bias` are silently ignored or may cause errors depending on the model. Deep research does not support function/tool calling.

---

## 10. Search behavior and control

### `search_domain_filter` — how it works

- **Type:** Array of up to **20** domain strings
- **Allowlist mode:** Plain domain names — `["nature.com", "arxiv.org"]` — restricts search to only these domains
- **Denylist mode:** Prefix with `-` — `["-reddit.com", "-pinterest.com"]` — excludes these domains
- **Modes are mutually exclusive per request** — you cannot mix allow and deny entries
- **Format:** Domain names without protocol (`nature.com`, not `https://nature.com`). Root domain matching is implicit (e.g., `"wikipedia.org"` matches all subdomains). TLD filtering works (e.g., `".gov"`, `".edu"`)
- **Specific URLs** can also be passed for granular blocking (e.g., `"-https://en.wikipedia.org/wiki/Chess"`)

### `search_recency_filter` — temporal scoping

Options: `"hour"`, `"day"`, `"week"`, `"month"`, `"year"`. Default is no filter (all time). For more precise control, use `search_after_date_filter` and `search_before_date_filter` with date strings.

### How many searches does deep research execute?

The model autonomously determines the number of searches. **This cannot be directly controlled or capped by the caller.** Typical ranges from official examples:

- `reasoning_effort: "low"` → ~18 searches
- `reasoning_effort: "medium"` → ~28 searches
- `reasoning_effort: "high"` → ~30 searches

Third-party reports indicate deep research can examine **150+ sources** in a single run. The `num_search_queries` field in the `usage` response reports the exact count for billing.

### Citation-to-search_results index mapping

Inline citations in the response text use **1-indexed** bracket notation: `[1]`, `[2]`, `[3]`. The `search_results` array is standard **0-indexed**. Therefore **inline `[1]` maps to `search_results[0]`**. Multiple citations per claim appear as separate brackets: `[1][2][3]`, never `[1, 2]` or `[1-3]`.

---

## 11. Citations and grounding

### The `citations` field is deprecated

As of **May 2025**, the `citations` field (a simple array of URL strings) has been fully deprecated and removed. Applications must use the `search_results` field, which provides richer metadata: `title`, `url`, `date`, `last_updated`, `snippet`, and `source`.

### Programmatic citation extraction

Parse `[N]` patterns from the response content with a regex, then map to `search_results[N-1]`:

```python
import re

content = response.choices[0].message.content
search_results = response.search_results

# Extract all citation indices
indices = set(int(m) for m in re.findall(r'\[(\d+)\]', content))

# Map to sources
for idx in sorted(indices):
    source = search_results[idx - 1]  # 1-indexed to 0-indexed
    print(f"[{idx}] {source['title']} — {source['url']}")
```

### What are `citation_tokens`?

**Citation tokens are the tokens consumed processing retrieved web content** — the raw text from search results that the model reads and reasons over. Input tokens = prompt tokens (your query) + citation tokens (web content). For deep research, citation tokens are billed at **$2/1M tokens**. For all other Sonar models, citation tokens are no longer charged (as of April 2025).

---

## 12. Reasoning tokens and chain of thought

### `reasoning_tokens` vs `completion_tokens`

These are fundamentally different processing stages:

- **`reasoning_tokens`**: Tokens consumed during the **internal research reasoning phase** — the model's process of analyzing, synthesizing, and planning across all gathered material before writing the final answer. These are **hidden** and never appear in the response.
- **`completion_tokens`**: Tokens in the **visible output** — the final research report delivered to the user.

### Chain-of-thought exposure

**Deep research does NOT expose chain-of-thought.** Per the official FAQ: "We expose the CoTs for Sonar Reasoning Pro. We don't currently expose the CoTs for Deep Research." For `sonar-reasoning-pro`, responses include `<think>...</think>` sections containing visible reasoning. For `sonar-deep-research`, reasoning is entirely internal and billed at $3/1M tokens without any visibility.

### `reasoning_effort` parameter

| Setting | Behavior | Typical reasoning tokens | Typical cost |
|---------|----------|------------------------|--------------|
| `"low"` | Faster, shallower analysis | ~74K | ~$0.41 |
| `"medium"` | Balanced (default) | ~308K | ~$1.19 |
| `"high"` | Deepest analysis, most searches | ~340K | ~$1.32 |

The parameter directly controls the number of searches performed, the depth of internal reasoning, and consequently cost. It is **exclusive to `sonar-deep-research`** (introduced May 2025).

---

## 13. Context window and limits

| Parameter | sonar-deep-research | sonar | sonar-pro | sonar-reasoning-pro |
|-----------|-------------------|-------|-----------|-------------------|
| Input context window | **128,000 tokens** | 128,000 | 200,000 | 128,000 |
| Max output (documented) | 128,000 (max_tokens ceiling) | ~8K | ~8K | Not specified |
| Max output (practical) | **~5,000–10,000 tokens** | ~8K | ~8K | Varies |

**Critical limitation:** While `max_tokens` can be set up to 128,000, **practical output rarely exceeds 5,000–10,000 tokens** before truncation occurs. Community reports document the model cutting off at ~7,000 words even with `max_tokens: 150000`. This is a known, persistent issue.

No documented hard limit exists on the number of messages in a conversation or request payload size beyond the context window constraint.

---

## 14. Multi-turn conversation

### Stateless API — client-managed history

The Perplexity API is **fully stateless**. It does not maintain server-side conversation state. Multi-turn context must be managed client-side by including all previous messages in the `messages` array:

```python
messages = [
    {"role": "system", "content": "You are a thorough research assistant."},
    {"role": "user", "content": "What are the main causes of antibiotic resistance?"},
    {"role": "assistant", "content": "Previous response..."},
    {"role": "user", "content": "Which countries are most affected?"}
]

response = client.chat.completions.create(
    model="sonar-deep-research",
    messages=messages
)
```

### Practical guidance for deep research

Deep research is **optimally used as single-turn** (one comprehensive query → one report) because:

1. Each request may take **2–40+ minutes**, making rapid multi-turn conversation impractical
2. The model performs a full research cycle per request regardless of history
3. As conversation grows, older turns approaching the 128K window are compressed or lost

For persistent memory across turns, Perplexity's cookbook recommends `ChatSummaryMemoryBuffer` (via LlamaIndex) with a ~3,000-token summary limit or vector store retrieval (e.g., LanceDB) for semantic history.

---

## 15. System messages

### Supported but with critical limitation

Deep research **accepts and respects system messages** for controlling the style, tone, format, and language of the generated response:

```json
{"role": "system", "content": "Write in formal academic style. Structure as an annotated bibliography."}
```

**However, the search component does NOT attend to the system prompt.** Only the user prompt drives the actual web search. API parameters (`search_domain_filter`, `search_recency_filter`, etc.) are the correct mechanism for controlling search behavior.

### Prompting best practices

- **Never ask for URLs in prompts** — they are returned in `search_results`
- **Avoid few-shot examples** — they confuse the web search by triggering searches for the example content
- Use system messages for **output formatting only**; use API parameters for search control
- Formatting instruction adherence is inconsistent (~50% success rate per community reports for complex formatting)

---

## 16. SDK and client libraries

### Official Perplexity Python SDK

```bash
pip install perplexityai
```

- **Package:** `perplexityai` on PyPI (latest: v0.30.1, Feb 2026)
- **Import:** `from perplexity import Perplexity`
- **Python:** ≥3.9, powered by httpx
- **Features:** Sync (`Perplexity()`) and async (`AsyncPerplexity()`) clients, built-in streaming, auto-retries (2 default), configurable timeouts (15-min default), full type definitions via Pydantic

```python
from perplexity import Perplexity

client = Perplexity()  # reads PERPLEXITY_API_KEY env var

# Synchronous
response = client.chat.completions.create(
    model="sonar-deep-research",
    messages=[{"role": "user", "content": "Research query"}],
    reasoning_effort="high"
)

# Streaming
stream = client.chat.completions.create(
    model="sonar-deep-research",
    messages=[{"role": "user", "content": "Research query"}],
    stream=True
)
for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")

# Async deep research
async_req = client.async_.chat.completions.create(
    model="sonar-deep-research",
    messages=[{"role": "user", "content": "Research query"}]
)
print(f"Job ID: {async_req.request_id}, Status: {async_req.status}")
```

### Official TypeScript/Node SDK

```bash
npm install @perplexity-ai/perplexity_ai
```

- **Runtimes:** Node.js 20+, Deno 1.28+, Bun 1.0+, Cloudflare Workers, Vercel Edge
- **TypeScript:** ≥4.9

```typescript
import Perplexity from '@perplexity-ai/perplexity_ai';
const client = new Perplexity();
const response = await client.chat.completions.create({
    model: 'sonar-deep-research',
    messages: [{ role: 'user', content: 'Research query' }]
});
```

### OpenAI SDK as drop-in client

Works for both Python and TypeScript by overriding `base_url`. See Section 9 for details. Perplexity-specific params go through `extra_body` (Python) or `as any` cast (TypeScript).

### Third-party options

| Library | Language | Notes |
|---------|----------|-------|
| LiteLLM | Python | Universal proxy; use `model="perplexity/sonar-deep-research"` |
| PerplexiPy | Python | High-level convenience wrapper (BSD-3) |
| `@ai-sdk/perplexity` | TypeScript | Vercel AI SDK integration |
| Spring AI | Java | Reuses OpenAI client with base URL override |

---

## 17. Known limitations, gotchas, and edge cases

### Response truncation — the most critical issue

**Responses are frequently cut off mid-sentence even with generous `max_tokens` settings.** Community reports indicate this affects **25–50% of deep research requests**. The `finish_reason` misleadingly returns `"stop"` even for truncated outputs. This is a known, partially-acknowledged bug as of early 2026.

**Workaround:** Break complex queries into smaller sub-queries. Verify output completeness programmatically (e.g., check for expected section endings). Use the async API for more reliable long-form output.

### Timeout and billing risks

Synchronous deep research requests can take **2–40+ minutes** and frequently exceed HTTP client default timeouts (~60s). **Credits are charged even on timeout with no output returned.** Strongly prefer the async API for production workloads.

### Async polling delay bug

Polling may show `IN_PROGRESS` for 30–40 minutes while the `completed_at` timestamp reveals only 2 minutes of actual processing. Poll based on time elapsed rather than relying solely on status transitions.

### `total_tokens` is misleading for cost

The `usage.total_tokens` field equals `prompt_tokens + completion_tokens` only. It **excludes** `citation_tokens` and `reasoning_tokens`, which often represent 80%+ of the actual cost. Always use `usage.cost.total_cost` for accurate billing.

### Streaming issues

Some third-party integrations (LiteLLM, Discourse) report 502 errors or broken streams with deep research. Long pauses between chunks (minutes) are normal. Pro Search on `sonar-pro` **requires** `stream: true`.

### Formatting inconsistency

Complex formatting instructions in system prompts have approximately **50% adherence** based on community reports.

### API vs consumer Deep Research product

The API and consumer product at perplexity.ai use the same search infrastructure but may differ in model versions, routing, and configuration. SafeSearch defaults to **on** in the API. The consumer product offers generous free quotas (5/day free, 500/day for Pro subscribers), while the API has no free tier.

### Features non-functional or undocumented for deep research

- **Image/file uploads** — Not documented as supported for deep research
- **Tool/function calling** — Not supported
- **`<think>` block exposure** — Not available (reasoning is hidden)
- **JSON structured output** — Undocumented compatibility; may work but untested at scale

---

## 18. Comparison with other Sonar models

### When to use which model

| Model | Best for | Latency | Cost per query |
|-------|----------|---------|----------------|
| **sonar** | Quick factual lookups, current events, simple Q&A | Sub-second (~1200 tok/s on Cerebras) | $0.01–0.02 |
| **sonar-pro** | Complex multi-step queries, follow-ups, detailed answers | Seconds | $0.03–0.10 |
| **sonar-reasoning-pro** | Step-by-step analysis, logical reasoning, math, synthesis | Several seconds | $0.02–0.08 |
| **sonar-deep-research** | Exhaustive reports, literature reviews, market analysis | **2–40+ minutes** | **$0.41–$1.32** |

### Feature support matrix

| Feature | sonar | sonar-pro | sonar-reasoning-pro | sonar-deep-research |
|---------|-------|-----------|-------------------|-------------------|
| Streaming | ✅ | ✅ | ✅ | ✅ |
| Async API | ❌ | ❌ | ❌ | ✅ |
| `reasoning_effort` | ❌ | ❌ | ❌ | ✅ |
| `<think>` CoT exposure | ❌ | ❌ | ✅ | ❌ |
| Citation token billing | ❌ | ❌ | ❌ | ✅ |
| Pro Search mode | ❌ | ✅ | ❌ | ❌ |
| Context window | 128K | 200K | 128K | 128K |
| Structured output (JSON) | ✅ | ✅ | ✅ | Undocumented |

### Deprecated models to avoid

- `sonar-reasoning` — Deprecated December 15, 2025; migrate to `sonar-reasoning-pro`
- `r1-1776` — Deprecated August 1, 2025
- All `llama-3.1-sonar-*` and `pplx-*` names — Deprecated February 2025

---

## Complete code examples

### Basic synchronous request (curl)

```bash
curl -X POST https://api.perplexity.ai/chat/completions \
  -H "Authorization: Bearer $PERPLEXITY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "sonar-deep-research",
    "messages": [
      {"role": "system", "content": "Write a structured research report with sections and citations."},
      {"role": "user", "content": "Comprehensive analysis of mRNA vaccine platform developments in 2025"}
    ],
    "reasoning_effort": "medium",
    "web_search_options": {"search_context_size": "high"},
    "search_recency_filter": "year"
  }'
```

### Streaming request (Python, native SDK)

```python
from perplexity import Perplexity

client = Perplexity()
stream = client.chat.completions.create(
    model="sonar-deep-research",
    messages=[{"role": "user", "content": "State of quantum error correction in 2025"}],
    stream=True,
    reasoning_effort="low"
)

full_content = ""
for chunk in stream:
    delta = chunk.choices[0].delta.content
    if delta:
        full_content += delta
        print(delta, end="", flush=True)

# Final chunk contains search_results and usage
print(f"\n\nSearches: {chunk.usage.num_search_queries}")
```

### Error handling with retries (Python, native SDK)

```python
import perplexity
from perplexity import Perplexity
import httpx

client = Perplexity(
    max_retries=3,
    timeout=httpx.Timeout(connect=10.0, read=900.0, write=10.0, pool=30.0)
)

try:
    response = client.chat.completions.create(
        model="sonar-deep-research",
        messages=[{"role": "user", "content": "Deep research query"}],
        reasoning_effort="high"
    )
    content = response.choices[0].message.content
    cost = response.usage.cost.total_cost
    print(f"Response ({len(content)} chars), cost: ${cost:.4f}")

except perplexity.RateLimitError as e:
    print(f"Rate limited. Request ID: {e.response.headers.get('X-Request-ID')}")

except perplexity.AuthenticationError:
    print("Invalid API key")

except perplexity.APIConnectionError as e:
    print(f"Network error: {e.__cause__}")

except perplexity.APIStatusError as e:
    print(f"API error {e.status_code}: {e.message}")
```

### OpenAI SDK compatibility (Python)

```python
from openai import OpenAI
import os

client = OpenAI(
    api_key=os.environ["PERPLEXITY_API_KEY"],
    base_url="https://api.perplexity.ai"
)

response = client.chat.completions.create(
    model="sonar-deep-research",
    messages=[{"role": "user", "content": "Compare RISC-V adoption across industries in 2025"}],
    max_tokens=8000,
    extra_body={
        "reasoning_effort": "high",
        "search_domain_filter": ["ieee.org", "arxiv.org", "acm.org"],
        "return_related_questions": True,
        "web_search_options": {"search_context_size": "high"}
    }
)

print(response.choices[0].message.content)

# Access Perplexity-specific fields
if hasattr(response, 'search_results'):
    for i, sr in enumerate(response.search_results):
        print(f"[{i+1}] {sr['title']} — {sr['url']}")
```

### Async submit and poll (curl)

```bash
# Submit
curl -X POST https://api.perplexity.ai/v1/async/sonar \
  -H "Authorization: Bearer $PERPLEXITY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "request": {
      "model": "sonar-deep-research",
      "messages": [{"role": "user", "content": "Full analysis of global semiconductor supply chains in 2025"}],
      "reasoning_effort": "high"
    },
    "idempotency_key": "semi-report-2025-v1"
  }'

# Poll (replace REQUEST_ID with the id from submit response)
curl https://api.perplexity.ai/v1/async/sonar/REQUEST_ID \
  -H "Authorization: Bearer $PERPLEXITY_API_KEY"

# List all jobs
curl https://api.perplexity.ai/v1/async/sonar \
  -H "Authorization: Bearer $PERPLEXITY_API_KEY"
```

---

## Conclusion

Three engineering decisions dominate a production integration against `sonar-deep-research`. First, **always use the async API** for production workloads — the synchronous endpoint's multi-minute latency creates timeout and billing risks that the polling workflow cleanly eliminates. Second, **budget for reasoning tokens, not output tokens** — reasoning accounts for 54–77% of total cost and is entirely invisible in the response, making `usage.cost.total_cost` the only reliable cost metric. Third, **validate output completeness** programmatically, because response truncation at `finish_reason: "stop"` remains the most impactful open bug affecting roughly a quarter to half of requests.

The API's OpenAI-compatible surface makes initial integration trivial (two-line SDK configuration change), but its unique billing model, async workflow, and deep-research-specific behaviors (`reasoning_effort`, hidden reasoning tokens, autonomous search counts, minute-scale latency) require purpose-built operational tooling that goes well beyond a standard LLM integration.