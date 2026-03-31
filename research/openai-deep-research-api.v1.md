# OpenAI Deep Research API: Complete Technical Reference

**OpenAI's deep research API went live on June 26, 2025**, exposing the deep research capability — previously exclusive to ChatGPT Pro — as a programmatic endpoint on the Responses API. Two models are available: `o3-deep-research` (highest quality, slowest) and `o4-mini-deep-research` (faster, cheaper). The API is fundamentally asynchronous, typically taking minutes to tens of minutes per query, and requires at least one data-source tool (web search, file search, or MCP) to be explicitly configured. A typical query costs **~$1–3 with o4-mini-deep-research** and **~$5–30 with o3-deep-research**, depending on complexity. Unlike the ChatGPT UI, the API skips the clarification and prompt-rewriting steps — developers must supply fully-formed prompts. This document covers everything a senior engineer needs to build a production integration.

---

## 1. Endpoint, model strings, and API surface

### Endpoint URL

The exact endpoint is `POST https://api.openai.com/v1/responses` — the **Responses API**. Deep research is not available via the Assistants API. The model pages list Chat Completions (`/v1/chat/completions`) as a technically supported endpoint, but the official deep research guide exclusively documents and recommends the Responses API, and key features like `background` mode, `max_tool_calls`, and the structured `output` array with tool-call items are Responses API constructs.

### Model identifiers

| Model string | Type | Description |
|---|---|---|
| `o3-deep-research` | Alias (latest) | Highest quality, slowest. Points to the latest dated snapshot |
| `o3-deep-research-2025-06-26` | Pinned snapshot | Stable version for production use |
| `o4-mini-deep-research` | Alias (latest) | Faster and ~5× cheaper than o3. Points to the latest dated snapshot |
| `o4-mini-deep-research-2025-06-26` | Pinned snapshot | Stable version for production use |

Both snapshots were released on **June 26–27, 2025**. These are the only available snapshots as of March 2026. To pin a version for reproducibility, use the dated string (e.g., `o3-deep-research-2025-06-26`).

### SDK requirements

Install the latest OpenAI Python SDK: `pip install --upgrade openai`. The `client.responses.create()` method must be available — earlier SDK versions (before ~v1.78) had issues with async responses. No specific minimum version is documented, but "latest" is explicitly recommended. For Node.js, use `openai` from npm (also latest).

---

## 2. Authentication and access requirements

**Organization verification is required.** Deep research models are available to verified organizations on **Tier 1 through Tier 5** of OpenAI's usage tier system. The free tier is explicitly **not supported** — the rate limit tables show "Not supported" for both models at the free tier.

The tier requirements are:

- **Tier 1:** $5+ paid to OpenAI
- **Tier 2:** $50+ paid, 7+ days since first payment
- **Tier 3:** $100+ paid, 7+ days
- **Tier 4:** $250+ paid, 14+ days
- **Tier 5:** $1,000+ paid, 30+ days

No waitlist, beta flag, or special headers are required beyond the standard `Authorization: Bearer $OPENAI_API_KEY` and `Content-Type: application/json`. The models are generally available (GA). For the ChatGPT product (not the API), free users get 5 queries/month, Plus/Team get 25/month, and Pro gets 250/month — but these quotas do not apply to API usage.

---

## 3. Request format — complete specification

### Full parameter reference

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `model` | string | **Yes** | — | One of the four model strings above |
| `input` | string or array | **Yes** | — | Plain text string or structured messages array |
| `tools` | array | **Yes** | — | At least one data source: `web_search_preview`, `file_search`, or `mcp`. Optionally add `code_interpreter` |
| `background` | boolean | Strongly recommended | `false` | Async execution. Allows polling/webhooks. **Required for production use** |
| `instructions` | string | Optional | — | System-level instructions (alternative to `developer` role in messages) |
| `reasoning` | object | Optional | — | `{"summary": "auto"}` or `{"summary": "detailed"}` for reasoning step summaries |
| `max_tool_calls` | integer | Optional | Unlimited | Caps total tool calls. **Primary lever for controlling cost and latency** |
| `store` | boolean | Optional | `true` | Whether to store the response. Must be `true` when `background=true` |
| `previous_response_id` | string | Optional | — | Chains multi-turn conversations via the Responses API |
| `stream` | boolean | Optional | `false` | Enable SSE streaming. Can combine with `background=true` |

### Input format

The `input` parameter accepts either a plain string or a structured messages array. Supported roles in the messages array are `developer` (system-level), `user`, and `assistant`. Content within messages uses the `input_text` content type.

```json
{
  "input": [
    {
      "role": "developer",
      "content": [{"type": "input_text", "text": "You are a research analyst. Cite all sources."}]
    },
    {
      "role": "user",
      "content": [{"type": "input_text", "text": "Research the economic impact of semaglutide on global healthcare systems."}]
    }
  ]
}
```

System messages are supported via the `developer` role or the `instructions` parameter. Multi-turn conversations are supported via `previous_response_id`. **Image input** is listed as a supported modality on the model pages (text + image in, text out), though the documentation focuses on text-based research workflows. **Function calling and structured outputs are not supported.**

### Tool configuration schemas

**Web search** (required or one of the data sources):
```json
{"type": "web_search_preview"}
```

**Web search with domain filtering** (use `web_search` instead of `web_search_preview`):
```json
{
  "type": "web_search",
  "filters": {
    "allowed_domains": ["pubmed.ncbi.nlm.nih.gov", "clinicaltrials.gov"]
  }
}
```
Up to **100 domains** can be specified. Omit the protocol prefix. Subdomains are automatically included. Note: `user_location` is **not supported** for deep research models. **Important caveat:** community reports indicate `web_search` (vs. `web_search_preview`) can cause timeouts with o3-deep-research — test carefully.

**File search** (max 2 vector stores):
```json
{
  "type": "file_search",
  "vector_store_ids": ["vs_abc123", "vs_def456"]
}
```
Only the `type` and `vector_store_ids` parameters are supported for deep research models.

**Code interpreter** (optional, for data analysis):
```json
{"type": "code_interpreter", "container": {"type": "auto"}}
```

**Remote MCP server:**
```json
{
  "type": "mcp",
  "server_label": "mycompany_mcp_server",
  "server_url": "https://mycompany.com/mcp",
  "require_approval": "never"
}
```
MCP servers **must** implement `search` and `fetch` tools with specific schemas. The `require_approval` field **must** be `"never"` for deep research.

### Complete curl example

```bash
curl https://api.openai.com/v1/responses \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "o3-deep-research",
    "input": "Research the economic impact of semaglutide on global healthcare systems. Include specific figures, trends, and statistics. Prioritize reliable, up-to-date sources. Include inline citations.",
    "background": true,
    "tools": [
      {"type": "web_search_preview"},
      {
        "type": "file_search",
        "vector_store_ids": ["vs_68870b8868b88191894165101435eef6"]
      },
      {"type": "code_interpreter", "container": {"type": "auto"}}
    ],
    "reasoning": {"summary": "auto"},
    "max_tool_calls": 80
  }'
```

### Complete Python SDK example

```python
from openai import OpenAI
from time import sleep

client = OpenAI(timeout=3600)

response = client.responses.create(
    model="o3-deep-research",
    input=[
        {
            "role": "developer",
            "content": [{"type": "input_text", "text": "You are a research analyst. Cite all sources with URLs."}],
        },
        {
            "role": "user",
            "content": [{"type": "input_text", "text": "Research the economic impact of semaglutide on global healthcare systems."}],
        },
    ],
    background=True,
    tools=[
        {"type": "web_search_preview"},
        {"type": "code_interpreter", "container": {"type": "auto"}},
    ],
    reasoning={"summary": "auto"},
    max_tool_calls=80,
)

# Poll until complete
while response.status in {"queued", "in_progress"}:
    print(f"Status: {response.status}")
    sleep(5)
    response = client.responses.retrieve(response.id)

# Access the final report
print(response.output_text)

# Access citations
for item in response.output:
    if item.type == "message":
        for annotation in item.content[0].annotations:
            print(f"  [{annotation.title}]({annotation.url})")
```

---

## 4. Response format — complete specification

### Response JSON structure

The response follows the standard Responses API schema. The `output` array contains a chronological sequence of intermediate tool calls and the final message:

```json
{
  "id": "resp_xxxx",
  "object": "response",
  "created_at": 1756315696,
  "model": "o3-deep-research-2025-06-26",
  "status": "completed",
  "output": [
    {
      "type": "reasoning",
      "id": "rs_xxxx",
      "content": [],
      "summary": [{"text": "Planning research approach..."}]
    },
    {
      "type": "web_search_call",
      "id": "ws_xxxx",
      "status": "completed",
      "action": {"type": "search", "query": "semaglutide economic impact healthcare"}
    },
    {
      "type": "web_search_call",
      "id": "ws_yyyy",
      "status": "completed",
      "action": {"type": "open_page", "url": "https://example.com/study"}
    },
    {
      "type": "code_interpreter_call",
      "id": "ci_xxxx",
      "input": "import pandas as pd\n...",
      "output": "Analysis results..."
    },
    {
      "type": "message",
      "id": "msg_xxxx",
      "status": "completed",
      "role": "assistant",
      "content": [
        {
          "type": "output_text",
          "text": "# Economic Impact of Semaglutide\n\nSemaglutide has transformed...",
          "annotations": [
            {
              "url": "https://example.com/source",
              "title": "Source Title",
              "start_index": 123,
              "end_index": 145
            }
          ]
        }
      ]
    }
  ],
  "usage": {
    "input_tokens": 60506,
    "input_tokens_details": {"cached_tokens": 0},
    "output_tokens": 22883,
    "output_tokens_details": {"reasoning_tokens": 20416},
    "total_tokens": 83389
  }
}
```

### Output item types

| Type | Description |
|---|---|
| `reasoning` | Internal reasoning steps. `content` is typically empty (reasoning tokens are hidden). `summary` contains text when `reasoning.summary` is `"auto"` or `"detailed"` |
| `web_search_call` | Web search action. `action.type` is `"search"`, `"open_page"`, or `"find_in_page"` |
| `code_interpreter_call` | Code execution. Contains `input` (code) and `output` (result) |
| `mcp_call` | MCP server tool call. Contains `name`, `server_label`, and `arguments` |
| `file_search_call` | Vector store search. Contains `queries` and results |
| `message` | The final research report with inline `annotations` (citations) |

### Citations structure

Each annotation on the final message contains `url` (source URL), `title` (source title), `start_index` and `end_index` (character positions in the output text). Access them via `response.output[-1].content[0].annotations`.

### Status values

- **`queued`** — accepted, waiting to start
- **`in_progress`** — actively researching
- **`completed`** — final answer ready
- **`failed`** — error occurred
- **`incomplete`** — partial completion (e.g., output truncated)
- **`cancelled`** — explicitly cancelled by the user

### Reasoning tokens

Reasoning tokens are internal chain-of-thought tokens, reported in `usage.output_tokens_details.reasoning_tokens`. They are **not** returned as visible content — the `content` field of `reasoning` output items is typically empty. Only reasoning *summaries* are visible when configured. In practice, reasoning tokens constitute **~89% of total output tokens** — a critical cost consideration.

---

## 5. Async execution, streaming, and polling

### Background mode is essential

Deep research tasks routinely take **minutes to tens of minutes**. The API supports three consumption patterns, all built on `background=true`:

**Pattern 1 — Polling:**
```python
response = client.responses.create(model="o3-deep-research", input="...", background=True, tools=[...])
while response.status in {"queued", "in_progress"}:
    sleep(5)
    response = client.responses.retrieve(response.id)
```

**Pattern 2 — Webhooks:**
Configure webhooks per-project in the OpenAI dashboard. Supported events: `response.completed`, `response.cancelled`, `response.incomplete`. Webhooks follow the Standard Webhooks specification with retries up to 72 hours on failure. Webhook payloads contain the response ID, which you then retrieve via `client.responses.retrieve()`.

**Pattern 3 — SSE streaming with background mode:**
```python
stream = client.responses.create(
    model="o3-deep-research", input="...",
    background=True, stream=True, tools=[...]
)
cursor = None
for event in stream:
    print(event)
    cursor = event.sequence_number
```

Streaming events include `response.created`, `response.output_item.added`, `response.content_part.added`, `response.output_text.delta`, `response.output_text.done`, `response.completed`, and error variants. Each event carries a `sequence_number` that serves as a cursor — if the connection drops, resume via `GET /v1/responses/{id}?stream=true&starting_after={cursor}`.

### Cancellation

```bash
curl -X POST https://api.openai.com/v1/responses/resp_123/cancel \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json"
```

Python: `client.responses.cancel("resp_123")`. Node.js: `await client.responses.cancel("resp_123")`. Cancellation is idempotent.

### Timeout and retention

Background mode retains response data for **~10 minutes** for polling. Without background mode, set the SDK timeout to at least **3600 seconds** (`OpenAI(timeout=3600)` in Python, `new OpenAI({ timeout: 3600 * 1000 })` in Node.js). Background mode is **incompatible with Zero Data Retention (ZDR)** but compatible with Modified Abuse Monitoring (MAM).

---

## 6. Rate limits and quotas

### o3-deep-research rate limits by tier

| Tier | RPM | TPM | Batch queue |
|---|---|---|---|
| Free | Not supported | — | — |
| Tier 1 | 500 | 200,000 | 200,000 |
| Tier 2 | 5,000 | 450,000 | 300,000 |
| Tier 3 | 5,000 | 800,000 | 500,000 |
| Tier 4 | 10,000 | 2,000,000 | 2,000,000 |
| Tier 5 | 10,000 | 30,000,000 | 10,000,000 |

### o4-mini-deep-research rate limits by tier

| Tier | RPM | TPM | Batch queue |
|---|---|---|---|
| Free | Not supported | — | — |
| Tier 1 | 1,000 | 200,000 | 200,000 |
| Tier 2 | 2,000 | 2,000,000 | 300,000 |
| Tier 3 | 5,000 | 4,000,000 | 500,000 |
| Tier 4 | 10,000 | 10,000,000 | 2,000,000 |
| Tier 5 | 30,000 | 150,000,000 | 10,000,000 |

**The 200K TPM limit at Tier 1 is the single biggest operational pain point.** A single deep research request can consume the entire 200K budget, immediately triggering `429 Too Many Requests` errors for subsequent requests. All tokens — input, output, and reasoning — count against TPM. Rate limits are enforced at the **organization level**, not per-user. Rate-limited responses return HTTP `429` with a `RateLimitError` body including the limit, amount used, and amount requested.

---

## 7. Pricing and real-world cost analysis

### Per-token pricing

| Model | Input | Cached input | Output (includes reasoning) |
|---|---|---|---|
| o3-deep-research | **$10.00**/1M | $2.50/1M | **$40.00**/1M |
| o4-mini-deep-research | **$2.00**/1M | $0.50/1M | **$8.00**/1M |

For comparison, standard o3 is $2/$8 and standard o4-mini is $1.10/$4.40, making deep research variants **2–5× more expensive** per token than their non-research counterparts.

### Additional tool costs

- **Web search:** $10.00 per 1,000 calls ($0.01 per call) for reasoning models
- **Code interpreter:** $0.03 per session
- Search content tokens ingested from the web are billed at the model's **input token rate**

### Real-world cost examples

**o4-mini-deep-research typical query (~$1.10):**
- Input tokens: ~60,500 → ~$0.12
- Output tokens: ~22,900 (including ~20,400 reasoning) → ~$0.18
- Web search: ~77 calls → ~$0.77
- Code interpreter: ~$0.03

**o3-deep-research typical query (~$5–30):**
- Across benchmarks, average cost was **~$10 per query**, with complex queries reaching **~$30**
- The model tends to make 40–80+ web search calls per query

There is **no free tier** for API usage. OpenAI's Researcher Access Program offers up to $1,000 in API credits for qualifying academic researchers.

---

## 8. Tool use and web search configuration

The deep research model does **not** automatically perform web searches — you **must** explicitly include at least one data-source tool in the `tools` array. Without a data source, the request will fail.

### Constraining search behavior

The `max_tool_calls` parameter is the primary control for bounding cost and latency. Setting it to, say, 50 caps the total number of web searches, file searches, and MCP calls the model can make. The `web_search` tool variant (vs. `web_search_preview`) supports domain filtering via `filters.allowed_domains` with up to 100 domains.

### Custom tools and function calling

**Function calling is not supported.** The deep research models only support the four built-in tools: `web_search_preview`/`web_search`, `file_search`, `code_interpreter`, and `mcp`. If you need function calling alongside research, use the standard `o3` or `o4-mini` models with web search tools instead.

---

## 9. Context window and limits

| Specification | o3-deep-research | o4-mini-deep-research |
|---|---|---|
| Input context window | **200,000 tokens** | **200,000 tokens** |
| Maximum output | **100,000 tokens** | **100,000 tokens** |
| Knowledge cutoff | June 1, 2024 | June 1, 2024 |
| Max vector stores | 2 | 2 |
| Input modalities | Text, image | Text, image |
| Output modalities | Text only | Text only |

There is no documented hard limit on the number of sources the model will consult — this is governed dynamically by the model's reasoning, constrained only by `max_tool_calls`. File upload sizes follow standard OpenAI vector store limits. OpenAI recommends keeping input prompts under **~15,000 characters** for optimal results.

---

## 10. Gotchas, limitations, and known issues

**Rate limit exhaustion at Tier 1** is the most common failure. A single deep research call can consume the entire 200K TPM budget, blocking subsequent requests. The only fix is upgrading to Tier 2+ or serializing requests carefully.

**Runaway token consumption with no output** has been reported with o3-deep-research — the model performs dozens of web searches, consumes 1M+ tokens, but never produces a final response. Setting `max_tool_calls` helps mitigate this. Similarly, **truncated reports** are a known issue where only the last ~30% of a report is delivered, and continuation does not reliably recover missing sections.

**The `web_search` vs. `web_search_preview` tool choice matters.** Community reports indicate that using `web_search` (instead of `web_search_preview`) with o3-deep-research causes consistent timeouts and server errors. Use `web_search_preview` unless you specifically need domain filtering.

**MCP tool calls returning `None`** has been reported — MCP calls that work with other models sometimes return empty results with deep research models. The `temperature` parameter is **not supported** (deep research models are reasoning models) and will cause errors if set. Setting `max_tokens` too high can push usage over TPM limits, while setting it too low leads to empty output.

**Citation accuracy** is imperfect. OpenAI acknowledges deep research "can sometimes hallucinate facts" and "may struggle with distinguishing authoritative information from rumors." It shows "weakness in confidence calibration, often failing to convey uncertainty accurately." Community users have reported hallucinated API documentation when using deep research to research OpenAI's own docs.

**Security risks** are elevated when combining web search with MCP/file search. Malicious web pages can embed hidden prompt injections that attempt to exfiltrate private data from MCP sources via search query parameters. OpenAI recommends staged workflows: run web search first, then run private data access without web search.

**Background mode and ZDR are incompatible** — background mode retains data for ~10 minutes, violating zero data retention requirements. There are **no deep-research-specific regional restrictions** for the API beyond standard OpenAI API country availability (160+ countries). Some ChatGPT connectors (Dropbox, SharePoint) are unavailable in the EEA, Switzerland, and UK, but this applies to the ChatGPT product, not the API.

---

## 11. SDK and library support

### Python async example

```python
import asyncio
from openai import AsyncOpenAI

client = AsyncOpenAI(timeout=3600)

async def deep_research(query: str) -> str:
    response = await client.responses.create(
        model="o4-mini-deep-research",
        input=query,
        background=True,
        tools=[{"type": "web_search_preview"}],
        reasoning={"summary": "auto"},
    )
    while response.status in {"queued", "in_progress"}:
        await asyncio.sleep(5)
        response = await client.responses.retrieve(response.id)
    return response.output_text

result = asyncio.run(deep_research("What are the latest breakthroughs in fusion energy?"))
print(result)
```

### Node.js / TypeScript example

```typescript
import OpenAI from "openai";
const client = new OpenAI({ timeout: 3600 * 1000 });

let resp = await client.responses.create({
  model: "o3-deep-research",
  input: "Research the economic impact of semaglutide...",
  background: true,
  tools: [
    { type: "web_search_preview" },
    { type: "code_interpreter", container: { type: "auto" } },
  ],
});

while (resp.status === "queued" || resp.status === "in_progress") {
  await new Promise(resolve => setTimeout(resolve, 5000));
  resp = await client.responses.retrieve(resp.id);
}

console.log(resp.output_text);
```

### curl — all major operations

**Start:**
```bash
curl -X POST https://api.openai.com/v1/responses \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"o3-deep-research","input":"Research topic...","background":true,"tools":[{"type":"web_search_preview"}]}'
```

**Poll:**
```bash
curl https://api.openai.com/v1/responses/resp_xxxx \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

**Cancel:**
```bash
curl -X POST https://api.openai.com/v1/responses/resp_xxxx/cancel \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json"
```

**Resume streaming:**
```bash
curl "https://api.openai.com/v1/responses/resp_xxxx?stream=true&starting_after=42" \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Notable community libraries and tools

- **OpenAI Agents SDK (Python):** `openai-agents-python` — supports deep research as an agent tool
- **OpenAI Agents SDK (JS):** `openai-agents-js` — Node.js agents framework
- **Azure OpenAI:** Full support via Azure Foundry with identical SDK interface
- **Open Deep Research (LangGraph):** Open-source reimplementation by LangChain
- **LangChain.Tools.DeepResearch:** Elixir library with deep research support

---

## 12. How the API differs from ChatGPT deep research

The ChatGPT UI implements a three-step pipeline: (1) **clarification** via gpt-4.1, which asks follow-up questions, (2) **prompt rewriting** via gpt-4.1, which expands the query into a detailed research brief, and (3) **deep research execution**. The API **skips steps 1 and 2 entirely** — it expects a fully-formed prompt and immediately begins researching.

| Capability | ChatGPT UI | API |
|---|---|---|
| Automatic clarifying questions | ✅ | ❌ |
| Automatic prompt rewriting | ✅ | ❌ |
| Real-time visual progress sidebar | ✅ | ❌ (poll or stream) |
| Interrupt mid-research | ✅ | Via cancel endpoint |
| PDF export | ✅ | ❌ |
| Custom system/developer instructions | ❌ | ✅ |
| `max_tool_calls` cost control | ❌ | ✅ |
| Custom MCP server integration | Limited connectors | ✅ (full MCP) |
| Programmatic webhooks | ❌ | ✅ |
| Inspect every intermediate tool call | Partial summary | ✅ (full output array) |
| Batch processing | ❌ | ✅ |

OpenAI recommends implementing your own two-step pre-processing pipeline using gpt-4.1 (clarify → rewrite → research) to match ChatGPT's behavior. The ChatGPT UI has also been updated to a **GPT-5.2-based model** as of February 2026, while the API still uses the o3/o4-mini-based deep research models — potentially a behavioral divergence.

---

## 13. Changelog, versioning, and the road ahead

| Date | Event |
|---|---|
| **Feb 2, 2025** | Deep research launched in ChatGPT for Pro users |
| **Feb 25, 2025** | Expanded to ChatGPT Plus users |
| **Apr 24, 2025** | Increased quotas; introduced o4-mini lightweight variant in ChatGPT |
| **Jun 25, 2025** | OpenAI Cookbook deep research examples published |
| **Jun 26–27, 2025** | **API launch** — `o3-deep-research-2025-06-26` and `o4-mini-deep-research-2025-06-26` released |
| **Jul 17, 2025** | Visual browser mode added to ChatGPT deep research |
| **Feb 10, 2026** | Major ChatGPT update: MCP connectors, site restrictions, GPT-5.2-based model |
| **Mar 26, 2026** | Legacy deep research mode removed from ChatGPT |

**No deprecations** have been announced for the API deep research models. The broader pattern suggests new dated snapshots will be released as the models are updated (similar to how o3 has multiple snapshots). No specific upcoming API changes have been announced. The aliases (`o3-deep-research`, `o4-mini-deep-research`) will automatically roll forward to new snapshots when released — use dated strings for stability.

### Key documentation URLs

| Resource | URL |
|---|---|
| Deep research guide | `https://developers.openai.com/api/docs/guides/deep-research` |
| o3-deep-research model page | `https://developers.openai.com/api/docs/models/o3-deep-research` |
| o4-mini-deep-research model page | `https://developers.openai.com/api/docs/models/o4-mini-deep-research` |
| API pricing | `https://openai.com/api/pricing/` |
| Background mode guide | `https://platform.openai.com/docs/guides/background` |
| Web search tools guide | `https://developers.openai.com/api/docs/guides/tools-web-search` |
| MCP guide | `https://developers.openai.com/api/docs/mcp` |
| Cookbook: Introduction | `https://cookbook.openai.com/examples/deep_research_api/introduction_to_deep_research_api` |
| Cookbook: Agents SDK | `https://developers.openai.com/cookbook/examples/deep_research_api/introduction_to_deep_research_api_agents` |
| Cookbook: MCP server | `https://developers.openai.com/cookbook/examples/deep_research_api/how_to_build_a_deep_research_mcp_server/readme` |
| Tier/access requirements | `https://help.openai.com/en/articles/10362446-api-model-availability-by-usage-tier-and-verification-status` |

## Conclusion

The deep research API is a production-ready but expensive and slow endpoint best suited for high-value, complex research tasks where quality matters more than latency. **Three architectural decisions dominate production integration design:** always use `background=true` with polling or webhooks (never synchronous), always set `max_tool_calls` to bound costs (a single unbound query can reach $30+), and implement pre-processing prompt enrichment via gpt-4.1 to compensate for the missing clarification step. The Tier 1 TPM bottleneck of 200K tokens is the most common operational surprise — teams should plan for Tier 2+ from day one. The lack of function calling means deep research cannot participate in broader agentic tool-use chains directly; instead, treat it as a standalone research step whose output feeds into downstream processing.