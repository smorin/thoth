# Gemini Deep Research API Spike — Findings

**STATUS: live-run completed 2026-05-12.** All 5 spike scripts executed against the live
Gemini API (paid Tier 1+). Evidence files written to `research/_dr_spike_*.txt` / `*.json`.
Estimated spend: ~$2-4.

---

## §1 Confirmed agent IDs

`spike_dr_models.py` called `client.models.list()` (50 models total) and checked for the 3
candidate agent IDs:

| Agent ID | Present |
|---|---|
| `deep-research-preview-04-2026` | **YES** |
| `deep-research-max-preview-04-2026` | **YES** |
| `deep-research-pro-preview-12-2025` | **YES** (legacy, still listed) |

**Gate: PASSED.** `deep-research-preview-04-2026` is live and usable as the P28 v1 default.

> Note: P28 Open Question #6 skeleton claimed the legacy model "no longer appears" — the live
> API contradicts this. The legacy model `deep-research-pro-preview-12-2025` is **still listed**
> as of 2026-05-12. See §8.

---

## §2 Submit response shape

`spike_dr_submit.py` called `client.aio.interactions.create(agent=AGENT, message=PROMPT)`.

- **Return type**: `google.genai._interactions.types.interaction.Interaction` (Pydantic model)
- **`interaction.id`** format: `"v1_<base64-url-safe-blob>"` — NOT prefixed with `"interactions/"`.
  Example: `"v1_Chc1V1lEYXJyVUM0R3IxTWtQcm9qcDhBZxIXNVdZRGFyclVDNEdyMU1rUHJvanA4QWc"`
- **Initial `status`**: `"in_progress"`
- **`steps`**: `None` (not populated until completion)
- **`agent`**: string agent name echoed back (e.g., `"deep-research-preview-04-2026"`)
- **`created` / `updated`**: `datetime.datetime` with UTC tzinfo
- **All top-level attrs** on the Interaction object:
  `agent`, `agent_config`, `created`, `id`, `input`, `model`, `previous_interaction_id`,
  `response_format`, `response_mime_type`, `response_modalities`, `role`, `service_tier`,
  `status`, `steps`, `system_instruction`, `tools`, `updated`, `usage`, `webhook_config`
  (plus Pydantic model methods: `model_dump`, `model_validate`, etc.)
- Most optional fields (`model`, `input`, `previous_interaction_id`, `tools`, etc.) are `None`
  at submit time.

Full object repr and JSON dump in `research/_dr_spike_submit.json`.

---

## §3 Final response shape

`spike_dr_poll.py` polled by interaction ID every 10s and captured the completed interaction.
The research task completed in **~8.8 minutes** (submit at 17:44:05 UTC, completed ~17:52:55 UTC).

### `steps[]` structure (6 steps total)

| Index | `step.type` | `content[]` count | Notes |
|---|---|---|---|
| 0 | `user_input` | 1 | TextContent: the original prompt (102 chars) |
| 1 | `thought` | 0 | ThoughtStep with `signature` + `summary` list (24 TextContent items); no `content[]` field |
| 2 | `model_output` | 1 | TextContent: first research narrative section (2197 chars); **85 URLCitation annotations** |
| 3 | `model_output` | 1 | Image content item (`type='image'`) — inline chart/figure |
| 4 | `model_output` | 1 | TextContent: second narrative section (15123 chars); no annotations |
| 5 | `model_output` | 1 | TextContent: rendered "**Sources:**" list (7188 chars); no annotations |

### ThoughtStep shape

`step[1]` is a `ThoughtStep` object:
- `type`: `"thought"`
- `signature`: `""` (empty string)
- `summary`: list of `TextContent` items (24 items in this run), each with `{type, text, annotations}`

### Top-level final attrs

```
id:      'v1_Chc1V1lEYXJyVUM0R3IxTWtQcm9qcDhBZxIXNVdZRGFyclVDNEdyMU1rUHJvanA4QWc'
status:  'completed'
agent:   'deep-research-preview-04-2026'
created: datetime.datetime(2026, 5, 12, 17, 44, 5, tzinfo=datetime.timezone.utc)
updated: datetime.datetime(2026, 5, 12, 17, 44, 5, tzinfo=datetime.timezone.utc)
usage:
  total_input_tokens:    887,872
  total_output_tokens:    13,205
  total_thought_tokens:   38,879
  total_tool_use_tokens: 942,505
  total_tokens:        1,882,461
  total_cached_tokens:    90,112
```

> **Note**: `outputs` field does not exist. The spec assumption was wrong — the correct field
> is `steps`. See §4 for the citation path correction.

Full dump in `research/_dr_spike_poll.json`.

---

## §4 Citation extraction strategy (the v1 gate)

**RESOLVED — citations found.**

### Where annotations live

- **Path**: `interaction.steps[2].content[0].annotations[]`
- **NOT** `interaction.outputs[-1].annotations[]` (that field does not exist)
- Only `step[2]` (the first `model_output`) carries annotations; `step[4]` and `step[5]` do not.

### URLCitation shape

Each annotation is a `URLCitation` object with these fields:

```python
{
    'type':        'url_citation',    # discriminator string
    '__type__':    'URLCitation',     # SDK internal type tag
    'start_index': int,               # byte offset in content[0].text
    'end_index':   int,               # byte offset in content[0].text
    'title':       None,              # always None in observed response
    'url':         'https://vertexaisearch.cloud.google.com/grounding-api-redirect/...'
}
```

- **85 URLCitation objects** on `step[2].content[0]`
- URLs are Vertex AI grounding redirect URLs (opaque), not the original source URLs
- `title` was `None` on all 85 citations in this run

### Spec delta: correct the `outputs[-1]` assumption

The spec scope §8 path `interaction.outputs[-1].annotations[]` is **wrong**.

Correct extraction pseudocode:
```python
citations = []
for step in interaction.steps:
    if step.type == 'model_output':
        for item in (step.content or []):
            if item.type == 'text' and item.annotations:
                citations.extend(item.annotations)
```

### Alternative: rendered "Sources" block

`step[5].content[0].text` contains a markdown-rendered sources list with domain labels
(e.g., `[usenix.org](https://vertexaisearch.cloud.google.com/grounding-api-redirect/...)`).
This is human-readable but harder to parse programmatically. The structured `annotations[]`
approach is preferred for v1.

### Open Question #3 resolution

The annotations attribute **is** reliably present (85 citations found). The prompt-prepend
workaround (Open Question #3) is **not needed** for citation URLs. However, since `title=None`
and URLs are redirect links, the v1 implementation may want to use the rendered Sources block
to recover domain labels for display. See §8 for OQ #3 update.

---

## §5 Status enum values observed

**Observed transitions during `spike_dr_poll.py` run:**

```
status -> 'in_progress'   (at submit time)
status -> 'completed'     (after ~8.8 minutes)
```

No intermediate states (`'requires_action'`, `'failed'`, `'cancelled'`, `'incomplete'`)
were observed in this poll run.

**Full SDK status type hint** (from `interaction.model_fields['status']`):
```
Literal['in_progress', 'requires_action', 'completed', 'failed', 'cancelled', 'incomplete']
```

- `'incomplete'` is **not** in the official Gemini Interactions API docs but is present in
  the SDK type hint. Likely signals a truncated/quota-interrupted run.
- `'requires_action'` suggests a human-in-the-loop or tool-approval step.

**Implication for `OperationStatus` mapping:**

| Gemini status | Thoth `OperationStatus` |
|---|---|
| `in_progress` | `RUNNING` |
| `requires_action` | `RUNNING` (treat as still running) |
| `completed` | `SUCCEEDED` |
| `failed` | `FAILED` |
| `cancelled` | `CANCELLED` |
| `incomplete` | `FAILED` (conservative) |

---

## §6 Cancel behavior

**VERIFICATION INCONCLUSIVE — cancel() exists but server returned 500.**

`spike_dr_cancel.py` results:

1. **`client.aio.interactions.cancel` exists**: `True` (confirmed via `hasattr` check)
2. **Calling `cancel()` on a running interaction**: raised
   `InternalServerError: Error code: 500 — 'There was a problem processing your request. You will not be charged.'`
3. **Subsequent `interactions.get()` on the same interaction**: also returned 500
4. The interaction entered a **permanently broken server state** — all subsequent GETs on
   that interaction ID also returned 500.

The overscoped task submission may have triggered a server-side error condition before
`cancel()` was called, making the behavior ambiguous — it's unknown whether:
- The `cancel()` call caused the 500, or
- The server had already encountered an error on the overscoped task

**Implications for Task 9 (SIGINT cooperative cancel):**

- `cancel()` API surface exists — can be called
- Whether it cleanly transitions to `'cancelled'` status is **unverified**
- Whether a cancelled interaction preserves partial `steps[]` is **unverified**
- Recommendation: implement `cancel()` call in the SIGINT handler with a try/except around
  the 500, and do NOT attempt to retrieve partial output (assume empty on cancel)

---

## §6a `requires_action` trigger conditions (Task 6a spike — 2026-05-13)

**Probes run** (from `spike_dr_requires_action.py`, 5s poll interval, 10-min budget per probe):

1. `tool_code_execution` — submitted with `tools=[{"type":"code_execution"}]`.
   Final observed status: `in_progress` (10-min budget exhausted before any
   terminal transition); `requires_action` triggered: **NO**.
2. `collaborative_planning` — submitted with
   `agent_config={"type":"deep-research","collaborative_planning": True}`.
   Final status: `completed` (~16s wall after submit); `requires_action`
   triggered: **NO**. The collaborative-planning flag did NOT cause the
   server to pause for plan approval — the agent ran to completion.
3. `tool_file_search` — submitted with `tools=[{"type":"file_search"}]`.
   Final status: `completed` (~489s wall after submit); `requires_action`
   triggered: **NO**.

All three `interactions.create(...)` calls succeeded — neither the `tools`
parameter nor `agent_config.collaborative_planning` was rejected with a 400.
This confirms the SDK accepts these knobs, but the server did NOT respond
with a `requires_action` pause in any of them.

### Captured payload

Not triggered in any probe; the explored configuration space did not elicit
`requires_action`. No payload was captured. The status remains documented
only via the SDK's `Literal[...]` type hint (see §5).

### Implication for v1 mapping

**Keep the v1 baseline.** Without an observed `requires_action` payload,
there is no actionable recovery path to implement. The v1 mapping should
treat `requires_action` as a permanent terminal failure with
`failure_type=requires_action` so that:

- Operations halt cleanly when this status appears (no infinite poll).
- The `failure_type` tag makes the case grep-able in logs and easy to revisit
  if Gemini documents the recovery path later.
- A future probe (Task 9 follow-up or a separate spike) can re-investigate
  if real production traffic ever hits this status — at which point we will
  have a concrete interaction ID to dump and a clear failure surface.

This matches the §5 mapping table's conservative direction (treat as
terminal failure rather than continue-polling), preventing indefinite
polling on an undocumented state.

> **Spend & wall-time note.** 3 probes / 10-min budget per probe. Two
> probes completed (paid DR runs); one timed out at the poll-budget
> boundary (the interaction itself kept running server-side after the
> script stopped polling — Gemini bills for server work, not for our
> polling). Estimated spend: ~$2-3.

---

## §7 Interactions-specific error classes

### Public `google.genai.errors` hierarchy

```
google.genai.errors.APIError        <- Exception
  ClientError                       <- APIError
  ServerError                       <- APIError
```

### Private `google.genai._interactions` hierarchy

The interactions API raises a **completely separate** exception hierarchy that does NOT inherit
from `google.genai.errors`:

```
google.genai._interactions.GeminiNextGenAPIClientError  <- Exception
  BadRequestError    (HTTP 400)
  NotFoundError      (HTTP 404)
  InternalServerError (HTTP 500)
  ... (likely: UnauthorizedError 401, ForbiddenError 403, TooManyRequestsError 429)
```

### Observed failure paths

| Failure | Exception class | `exc.status_code` | `exc.code` |
|---|---|---|---|
| Invalid API key → `interactions.create` | `google.genai._interactions.BadRequestError` | `400` | `None` |
| Unknown agent → `interactions.create` | `google.genai._interactions.BadRequestError` | `400` | `None` |
| Unknown interaction ID → `interactions.get` | `google.genai._interactions.NotFoundError` | `404` | `None` |

**Critical implementation note:**
- Use `exc.status_code` (int) — NOT `exc.code` (always `None`)
- Must import from `google.genai._interactions` (private module) OR catch broad `Exception`
  and discriminate by `exc.status_code`
- The existing `_map_gemini_error` function in thoth uses `google.genai.errors` — interaction
  errors will NOT be caught by those handlers and will propagate as unhandled exceptions

### `_map_gemini_error` extension strategy

```python
# Catch _interactions errors separately:
from google.genai._interactions import (
    GeminiNextGenAPIClientError,
    BadRequestError,
    NotFoundError,
)

try:
    ...
except GeminiNextGenAPIClientError as exc:
    if exc.status_code == 404:
        raise OperationNotFoundError(...)
    elif exc.status_code == 429:
        raise RateLimitError(...)
    elif exc.status_code == 401 or exc.status_code == 403:
        raise AuthenticationError(...)
    else:
        raise ProviderError(...)
```

---

## §8 Updated Open Questions resolutions

Resolution status for each open question from `projects/P28-gemini-background-deep-research.md §Open questions`:

| # | Question | Status | Evidence |
|---|---|---|---|
| 1 | VCR-vs-`google-genai` transport compatibility | OPEN | Not probed by spike scripts; resolved during Task 3 cassette-recording step |
| 2 | `google-genai` version pinning strategy (`>=1.55,<2` vs loose) | OPEN | Architectural decision; not resolvable by live-API spike |
| 3 | Citation prompt-prepend workaround (auto-prepend vs rely on annotations) | **RESOLVED — not needed for citation URLs** | `annotations[]` reliably present (85 citations). `title=None` on all; consider using rendered "Sources" block from `step[-1]` to recover domain labels for display. |
| 4 | Resume after retention expiry (404 shape) | **RESOLVED** | `interactions.get` on unknown ID raises `google.genai._interactions.NotFoundError` with `status_code=404`. The existing `404` branch in `_map_gemini_error` needs to catch `_interactions.NotFoundError` specifically. |
| 5 | `extended` marker scope — `GEMINI_API_KEY` secret in Extended workflow | OPEN | Workflow YAML decision; not resolvable by API spike |
| 6 | ~~Single-agent assumption~~ | **STILL OPEN (corrected)** | Pre-spike skeleton claimed legacy model "no longer appears" — this is wrong. `deep-research-pro-preview-12-2025` IS still listed (2026-05-12). Two-tier agents (`preview` + `max-preview`) documented; `max-preview` also live. P28 v1 uses `preview`; max-tier upgrade path available. |
| 7 | Cancel-on-Ctrl-C default | **PARTIALLY RESOLVED — still-open** | `cancel()` exists on SDK. Status transition to `'cancelled'` and partial output preservation both unverified due to 500 errors on overscoped task. Implement with try/except; assume no partial output on cancel. |
| 8 | Free-tier error message URL stability (`https://ai.google.dev/pricing`) | OPEN | URL audit at implementation time |
