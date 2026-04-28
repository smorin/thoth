# P18 Phase F — Cancel API research per provider

**Generated:** 2026-04-28 during Phase F of P18 implementation.
**Tracked:** `PROJECTS.md` § P18 tasks T18 / T19 / T20.
**Spec reference:** `docs/superpowers/specs/2026-04-26-p18-immediate-vs-background-design.md` §1 + §4 Q9.

## Purpose

P18 introduces an optional `provider.cancel(job_id)` capability on
`ResearchProvider`. Each upstream provider has its own cancellation
semantics (or lack thereof). Before implementing per-provider, we need to
know what each API actually exposes so we can map it to a uniform thoth
contract. Providers without upstream cancel support raise
`NotImplementedError` from the base — the `thoth cancel` CLI catches it and
reports "upstream cancel not supported, local checkpoint marked cancelled".

## Uniform contract (re: how thoth callers see cancel)

```python
# providers/base.py
async def cancel(self, job_id: str) -> dict[str, Any]:
    """Best-effort cancel of an in-flight job. Returns final status dict.

    Status keys mirror `check_status`:
      {"status": "cancelled", "error": <str>}      — upstream confirmed cancelled
      {"status": "completed", "progress": 1.0}     — finished before cancel landed
      {"status": "permanent_error", "error": ...}  — cancel itself failed
    """
```

`thoth cancel <op-id>` invokes this for each non-completed provider on the
operation, swallowing `NotImplementedError` (to mark only local checkpoint),
and updates the operation's checkpoint to `cancelled` regardless.

---

## OpenAI — confirmed supported

**Endpoint:** `POST /v1/responses/{response_id}/cancel`
**SDK signature:** `client.responses.cancel(response_id) -> Response`
(both sync and async clients)

**When valid:** Only background-mode responses (created with
`background=True`). Immediate/synchronous responses have already returned
content by the time the SDK call resolves; there is nothing to cancel.

**Accepted source states:**
- `queued` — cancel succeeds; final state `cancelled`
- `in_progress` — cancel succeeds; final state `cancelled`
- `completed` — cancel call is a no-op; final state stays `completed`
  (no error)
- `failed`, `incomplete`, `cancelled` — cancel call is a no-op

**Returned status string:** the response's `.status` field becomes
`"cancelled"`. The full Response object is returned so we can read it.

**Billing:** OpenAI bills for tokens generated up to the cancel point.
Cancellation does NOT refund billing. This is fine for our use case
(user wants to stop, not erase) but worth documenting in user-facing help.

**Implementation plan for `OpenAIProvider.cancel`:**

```python
async def cancel(self, job_id: str) -> dict[str, Any]:
    if job_id not in self.jobs:
        # Reattach lazily — cancel may be invoked from `thoth cancel` after
        # a fresh process start where self.jobs is empty.
        try:
            await self.reconnect(job_id)
        except Exception as e:
            return {"status": "permanent_error", "error": f"reconnect failed: {e}"}
    try:
        response = await self.client.responses.cancel(job_id)
        if hasattr(response, "status") and response.status == "completed":
            return {"status": "completed", "progress": 1.0}
        return {"status": "cancelled", "error": "Response was cancelled"}
    except (openai.APIError, Exception) as e:
        return {
            "status": "permanent_error",
            "error": str(e),
            "error_class": type(e).__name__,
        }
```

**Doc URLs (verified during research):**
- `https://platform.openai.com/docs/api-reference/responses` (cancel
  endpoint section)
- `https://cookbook.openai.com/examples/deep_research_api/introduction_to_deep_research_api`
  (operational guide for background submissions)

---

## Perplexity Sonar — needs verification, likely orphan-only

**Status:** **Not yet implemented in thoth** (`PerplexityProvider.submit`
raises NotImplementedError; the provider exists only for `thoth providers
models` listing). Cancel research is forward-compat for when the provider
lands.

**API:** Perplexity exposes `sonar-deep-research` via their async-friendly
chat-completions endpoint. The async submission flow returns a
`request_id` you poll. Documentation as of 2026-04 describes:
- `POST /async/chat/completions` — submit
- `GET /async/chat/completions/{request_id}` — poll

**Cancel endpoint:** **Not documented** at the time of this research.
There is no `DELETE` or `POST .../cancel` endpoint listed in the public
docs.

**Mapping to thoth contract:**

If verification confirms there is no upstream cancel:

```python
async def cancel(self, job_id: str) -> dict[str, Any]:
    # Perplexity does not expose upstream cancel. Drop our local job-id
    # tracking (so we stop polling) and return cancelled. The upstream
    # request will run to completion and bill normally; the user has
    # accepted that by issuing `thoth cancel`.
    self.jobs.pop(job_id, None)
    return {
        "status": "cancelled",
        "error": "Perplexity does not support upstream cancel; "
                 "request will complete and bill normally.",
    }
```

**Alternative (recommended):** Leave `PerplexityProvider.cancel` as the
inherited `NotImplementedError` and let the `thoth cancel` CLI display the
"upstream cancel not supported" message. That communicates the limitation
honestly rather than papering over it with a half-truth.

**Recommendation for v3.1.0:** Leave inherited NotImplementedError. When
the provider's `submit()` lands, revisit cancel based on then-current
docs.

**Doc URLs to re-verify before any implementation:**
- `https://docs.perplexity.ai/getting-started/models/models/sonar-deep-research`
- `https://docs.perplexity.ai/guides/chat-completions-guide`
- `https://docs.perplexity.ai/api-reference/` (if exists at that path)

---

## Gemini Deep Research — needs verification

**Status:** **Not yet implemented in thoth.** The provider scaffold is
referenced in `planning/references.md` but does not exist as a module.

**API:** Gemini exposes deep-research via an "Interactions API" at
`/v1beta/interactions`. The pattern is session-based: create an
interaction, query it, the model emits intermediate research artifacts
asynchronously, you poll for completion.

**Cancel endpoint:** Not explicitly documented as of 2026-04. Session
abandonment (closing the client / not polling) is the implicit cancel.

**Mapping to thoth contract:**

Likely the same recommendation as Perplexity: leave inherited
NotImplementedError until the provider's `submit()` lands. Then
reassess based on the docs at that time.

**Doc URLs to re-verify before any implementation:**
- `https://ai.google.dev/gemini-api/docs/deep-research`
- `https://ai.google.dev/gemini-api/docs/interactions`
- `https://ai.google.dev/gemini-api/docs/gemini-for-research`

---

## Mock — trivial

`MockProvider.cancel(job_id)` was added alongside the contract in
`providers/mock.py`. It pops the job from the in-memory `self.jobs` dict
and returns `{"status": "cancelled", "error": "cancelled by user"}`.
Used by the `test_provider_cancel.py` hermetic suite and by the
`test_cancel_subcommand.py` integration cases.

---

## Phase G implementation matrix

| Provider | `cancel()` impl in v3.1.0 | Rationale |
|---|---|---|
| `OpenAIProvider` | **Implemented** via `client.responses.cancel` | Only provider with `submit()` currently working; cancel API is well-documented |
| `MockProvider` | **Implemented** (pop + return cancelled) | Required for hermetic test coverage |
| `PerplexityProvider` | Inherits `NotImplementedError` | Provider not yet operational; revisit when `submit()` lands |
| `GeminiProvider` | Not present | Provider doesn't exist yet |

The `thoth cancel` CLI catches `NotImplementedError` and reports
"upstream cancel not supported" — preserving the user-visible behavior
contract regardless of which providers eventually grow real cancel
support.

## Verification deferred

The OpenAI section was confirmed against the SDK source and the public
API docs in scope of this research. The Perplexity and Gemini sections
are based on docs as of 2026-04 and may have been augmented since;
re-verify before ANY non-OpenAI cancel implementation lands.
