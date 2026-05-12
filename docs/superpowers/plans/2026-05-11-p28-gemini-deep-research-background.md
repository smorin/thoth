# P28 — Gemini Deep Research Background Implementation Plan (v2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Gemini Deep Research background operations on top of the existing P24 `GeminiProvider`. Wire `client.aio.interactions.create(agent="deep-research-preview-04-2026", background=True, store=True)` through the provider-agnostic runtime (`_run_polling_loop`, `OperationStatus`, SIGINT cancel, `OutputManager`), enabling `thoth ask --mode gemini_*_research "..."`, `thoth resume <op-id>`, `thoth cancel <op-id>`.

**Architecture:** **Hybrid `GeminiProvider`, one class, internal routing.** P24 shipped the immediate path (`client.aio.models.generate_content_*` against chat models). P28 adds the Deep Research background path (`client.aio.interactions.*` against the deep-research agents). The public methods `submit/check_status/get_result/cancel/reconnect` become 5-line routers that branch on `is_background_model(self.model)` and delegate to `_immediate_*` (P24's existing methods, renamed) or `_deep_research_*` (new). Shared at the class level: `__init__`, `_map_gemini_error` (extended), `_invalid_key_thotherror`, `_validate_kind_for_model`, retry helpers.

**Architectural delta vs P26/P27:** P26 and P27 each route immediate vs background within a single SDK method (`responses.create` for OpenAI, `chat/completions` for Perplexity) — the branch flips params. **P28's branch uses two completely different SDK surfaces** (`models.generate_content` vs `interactions.create`). This is intentional, not an oversight to consolidate; the P29 cross-provider refactor needs to know this is a real Gemini API constraint, not a style inconsistency.

**Tech Stack:** Python 3.11+, `google-genai>=1.74.0` (already pinned by P24), `httpx`, `tenacity`, `pytest`, existing Thoth runtime. Tests use `unittest.mock.patch` + `AsyncMock` per P24 convention (`tests/test_provider_gemini.py`); VCR is not used for Gemini and is not required for P28.

**Spec:** `projects/P28-gemini-background-deep-research.md`. The "Conventions to carry forward from P26 + P27" section in the spec is the source of truth for cross-provider conventions. Open Question #6 (single vs bifurcated agents) is resolved — v1 ships the speed-efficiency tier only.

**History:** This is v2. The original plan `archive/2026-05-01-p28-gemini-background-deep-research.md` was scoped before P24 merged on 2026-05-10; it assumed P28 was building from scratch. P24 shipped most of `GeminiProvider`'s scaffolding (module, class, registry, error mapper, retry, immediate path). v2 only plans the net-new Deep Research bits.

---

## What P24 already shipped (DO NOT REDO)

| Component | Location | Notes |
|---|---|---|
| `GeminiProvider` class shell + `__init__` | `src/thoth/providers/gemini.py:227-251` | Lazy-imports `google.genai`; takes timeout via `HttpOptions(timeout=ms)`. |
| `_PROVIDER_NAME_GEMINI = "gemini"` constant | `src/thoth/providers/gemini.py:42` | P27 convention (suffix-naming variant). |
| `_map_gemini_error` | `src/thoth/providers/gemini.py:103-192` | Covers 401/403/404/429/400/5xx + httpx errors. P28 extends for interactions-specific cases (Task 2). |
| `_invalid_key_thotherror` usage | imported from `providers/_helpers.py` | Already used in the 401 branch. |
| `_is_retryable_gemini_exception` + `_gemini_stream_retry_delay` | `src/thoth/providers/gemini.py:209-224` | Reuse unchanged for DR retry. |
| `_validate_kind_for_model` | `src/thoth/providers/gemini.py:259-274` | Substring-matches `deep-research`; covers P28's `deep-research-preview-04-2026` automatically. |
| Provider registry | `src/thoth/providers/__init__.py:17,31,38,45` | `GeminiProvider`, `gemini`→class, `GEMINI_API_KEY`, `--api-key-gemini`. |
| CLI flag `--api-key-gemini` | `src/thoth/cli_subcommands/_options.py:75` | Already wired. |
| `GeminiConfig` placeholder | `src/thoth/config_schema.py:240-269` | Has `api_key="${GEMINI_API_KEY}"`. P28 extends for DR tunables (Task 12). |
| Immediate `submit/check_status/get_result/stream` | `src/thoth/providers/gemini.py:352-559` | Chat-completion path. P28 renames to `_immediate_*` and adds router. |
| `tests/test_provider_gemini.py` | 1157 lines | Monkeypatch pattern (`unittest.mock`). Run after every P28 refactor to catch regressions. |
| `is_background_model("deep-research-...")` | `src/thoth/config.py:254-261` | Substring-matches "deep-research". |

## What P28 v1 ships

| Component | Status |
|---|---|
| `cancel()` / `reconnect()` methods | New |
| `_deep_research_submit/check_status/get_result` internal helpers | New |
| `submit/check_status/get_result` router refactor | Modify |
| `_map_gemini_error` interactions-specific branches | Extend |
| `self.jobs` schema with immediate-vs-DR discriminator | Modify |
| 9 `gemini_*_research` modes in KNOWN_MODELS | New |
| `[providers.gemini]` DR-specific tunables (`poll_interval`, `max_wait_minutes`) | Extend |
| Live-API gated tests for DR workflows | New |
| README cost callout + mode listing | Modify |

Total estimated lines: ~400 new code in `gemini.py`, ~300 new unit tests, ~150 live-API tests, ~50 config/CLI/README modifications.

---

## File structure

| Action | Path | Responsibility |
|---|---|---|
| Modify | `src/thoth/providers/gemini.py` | Add DR internal helpers; refactor existing methods to routers; extend error mapper. |
| Modify | `src/thoth/config.py` | Add 9 `gemini_*_research` mode entries to `KNOWN_MODELS`. |
| Modify | `src/thoth/config_schema.py` | Add DR-specific fields to `GeminiConfig` (`poll_interval`, `max_wait_minutes`). |
| Create | `scripts/spike/p28/spike_gemini_dr_*.py` | Five spike scripts for live-API validation. |
| Create | `research/gemini-dr-api-spike-2026-05-11.md` | Spike findings, drives Task 8 citation strategy. |
| Modify | `tests/test_provider_gemini.py` | Add DR-path test classes. Existing immediate-path tests should still pass after Task 3 refactor. |
| Create | `tests/extended/test_gemini_dr_real_workflows.py` | Live-API CLI workflow tests (`@pytest.mark.live_api`). |
| Modify | `.github/workflows/live-api.yml` | Ensure `GEMINI_API_KEY` secret is wired. |
| Modify | `README.md` | Add DR cost callout + 9 new modes in the mode-list section. |

---

## Tasks

### Task 1: Pre-implementation Deep Research API spike

**Why this task exists:** the upstream Interactions API docs are in public beta and do not document several details P28 depends on — specifically (a) where citations live in DR responses, (b) which `google.genai.errors.*` classes interactions-specific failures raise, (c) the exact `steps[].content[]` shape for `step.type="model_output"`. Validating against the live API resolves these before Task 8 writes failing tests.

**Files:**
- Create: `scripts/spike/p28/spike_dr_models.py`
- Create: `scripts/spike/p28/spike_dr_submit.py`
- Create: `scripts/spike/p28/spike_dr_poll.py`
- Create: `scripts/spike/p28/spike_dr_cancel.py`
- Create: `scripts/spike/p28/spike_dr_errors.py`
- Create: `research/gemini-dr-api-spike-2026-05-11.md`

**Pre-conditions:** `GEMINI_API_KEY` env var set to a Tier-1+ Google AI Studio key (Deep Research requires paid tier). Each script is a UV-shebang per project convention.

- [ ] **Step 1: Write `scripts/spike/p28/spike_dr_models.py` — confirm DR agent IDs are listed live**

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["google-genai>=1.74.0"]
# ///
"""P28 spike: confirm deep-research-preview-04-2026 and -max- are live."""

from __future__ import annotations

import os
import sys

from google import genai

CANDIDATES = (
    "deep-research-preview-04-2026",
    "deep-research-max-preview-04-2026",
    "deep-research-pro-preview-12-2025",  # legacy — must NOT appear
)


def main() -> int:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not set", file=sys.stderr)
        return 2
    client = genai.Client(api_key=api_key)
    listed = list(client.models.list())
    names = {getattr(m, "name", "") for m in listed}
    print(f"Models listed: {len(names)}")
    for cand in CANDIDATES:
        present = cand in names or any(cand in n for n in names)
        flag = "YES" if present else "NO "
        print(f"  {flag} {cand}")
    fast_ok = any("deep-research-preview-04-2026" in n for n in names)
    return 0 if fast_ok else 1


if __name__ == "__main__":
    sys.exit(main())
```

Run: `uv run scripts/spike/p28/spike_dr_models.py | tee research/_dr_spike_models.txt`
Expected: prints YES for `deep-research-preview-04-2026`, exit code 0. **Block-if-failed:** if the v1 default agent ID is not listed, stop and reconvene on which agent to ship.

- [ ] **Step 2: Write `scripts/spike/p28/spike_dr_submit.py` — submit a real DR task and capture response shape**

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["google-genai>=1.74.0"]
# ///
"""P28 spike: submit a Deep Research interaction; capture top-level response shape.

Captures: returned object type, top-level attrs, interaction id format, initial status.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from google import genai

AGENT = "deep-research-preview-04-2026"
PROMPT = (
    "What were the three most-cited papers in distributed systems in 2024? "
    "One sentence each. Cite sources."
)
OUT = Path(__file__).parent.parent.parent.parent / "research" / "_dr_spike_submit.json"


async def main_async() -> int:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not set", file=sys.stderr)
        return 2
    client = genai.Client(api_key=api_key)
    resp = await client.aio.interactions.create(
        agent=AGENT,
        input=PROMPT,
        background=True,
        store=True,
    )
    interaction_id = getattr(resp, "id", None)
    print(f"interaction_id = {interaction_id!r}")
    print(f"type = {type(resp).__name__}")
    print(f"attrs = {[a for a in dir(resp) if not a.startswith('_')]}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {
                "captured_at": datetime.now(tz=timezone.utc).isoformat(),
                "interaction_id": interaction_id,
                "type": type(resp).__name__,
                "attrs": [a for a in dir(resp) if not a.startswith("_")],
                "repr": repr(resp)[:2000],
            },
            indent=2,
        )
    )
    print(f"saved {OUT}")
    return 0 if interaction_id else 1


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main())
```

Run: `uv run scripts/spike/p28/spike_dr_submit.py`
Expected: prints an interaction id like `interactions/...`; saves the response shape. **Note the printed interaction id for Step 3.**

- [ ] **Step 3: Write `scripts/spike/p28/spike_dr_poll.py` — poll to completion, capture full `steps[]` + citation shape**

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["google-genai>=1.74.0"]
# ///
"""P28 spike: poll a Deep Research interaction; capture the complete steps[] shape.

PRIMARY DELIVERABLE: locate where citations / URLs / sources live within the
response. The upstream Interactions API docs do not document annotations or
grounding_metadata for Deep Research; this spike resolves the citation
extraction strategy (citation option A from the v2 plan).

Pass INTERACTION_ID env var.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

from google import genai

POLL_S = 10
MAX_WAIT_MIN = 65  # upstream max research time is 60min; add small buffer
OUT = Path(__file__).parent.parent.parent.parent / "research" / "_dr_spike_poll.json"


def _dump_serializable(obj: object) -> object:
    """Best-effort recursive serialization for JSON dump."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_dump_serializable(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): _dump_serializable(v) for k, v in obj.items()}
    if hasattr(obj, "__dict__"):
        return {
            "__type__": type(obj).__name__,
            **{k: _dump_serializable(v) for k, v in vars(obj).items()},
        }
    return repr(obj)[:500]


async def main_async() -> int:
    api_key = os.environ.get("GEMINI_API_KEY")
    interaction_id = os.environ.get("INTERACTION_ID")
    if not (api_key and interaction_id):
        print("GEMINI_API_KEY and INTERACTION_ID required", file=sys.stderr)
        return 2
    client = genai.Client(api_key=api_key)
    deadline = time.monotonic() + MAX_WAIT_MIN * 60
    transitions: list[dict] = []
    last_status: str | None = None
    final = None
    while time.monotonic() < deadline:
        try:
            interaction = await client.aio.interactions.get(id=interaction_id)
        except Exception as exc:
            print(f"GET error: {type(exc).__name__}: {exc}")
            await asyncio.sleep(POLL_S)
            continue
        status = str(getattr(interaction, "status", "?"))
        if status != last_status:
            print(f"  status -> {status!r}")
            transitions.append({"t": time.monotonic(), "status": status})
            last_status = status
        if status in {"completed", "failed", "cancelled"}:
            final = interaction
            break
        await asyncio.sleep(POLL_S)
    if final is None:
        print("Timed out without terminal status")
        return 1
    steps = getattr(final, "steps", None)
    print(f"\n=== FINAL INTERACTION ===")
    print(f"  attrs: {[a for a in dir(final) if not a.startswith('_')]}")
    print(f"  steps type: {type(steps).__name__}; len: {len(steps) if steps else 0}")
    if steps:
        for i, step in enumerate(steps):
            step_type = getattr(step, "type", None)
            print(f"  step[{i}].type = {step_type!r}")
            step_content = getattr(step, "content", None)
            if step_content is None:
                continue
            for j, item in enumerate(step_content):
                item_type = getattr(item, "type", None)
                item_text = getattr(item, "text", None)
                print(
                    f"    step[{i}].content[{j}].type = {item_type!r}; "
                    f"text_preview = {(item_text or '')[:80]!r}"
                )
                # Probe for citation-shaped sub-attrs on this content item.
                for attr in (
                    "citations",
                    "references",
                    "sources",
                    "links",
                    "annotations",
                    "grounding",
                    "url",
                ):
                    val = getattr(item, attr, None)
                    if val is not None:
                        print(f"      ! found attr {attr!r} on content item: {val!r}"[:200])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {
                "interaction_id": interaction_id,
                "transitions": transitions,
                "final_attrs": [a for a in dir(final) if not a.startswith("_")],
                "final_dump": _dump_serializable(final),
            },
            indent=2,
            default=str,
        )
    )
    print(f"\nsaved {OUT}")
    return 0


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main())
```

Run: `INTERACTION_ID=interactions/abc123 uv run scripts/spike/p28/spike_dr_poll.py`
Expected: prints status transitions; on completion, dumps the full step tree and PROBES each content item for citation-shaped attributes (`citations`, `references`, `sources`, `links`, `annotations`, `grounding`, `url`). The JSON dump in `_dr_spike_poll.json` is the canonical record.

**Block-if-failed (the critical gate):** if NO citation-shaped attribute is found ANYWHERE in the response, **stop and reconvene** — Task 8 cannot proceed with citation extraction. Re-check the v1 scope decision on citations (per user 2026-05-11: "A" — structured-only, no fallback).

- [ ] **Step 4: Write `scripts/spike/p28/spike_dr_cancel.py` — verify cancel() + behavior**

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["google-genai>=1.74.0"]
# ///
"""P28 spike: submit an overscoped DR task, cancel immediately, observe behavior."""

from __future__ import annotations

import asyncio
import os
import sys
import time

from google import genai

AGENT = "deep-research-preview-04-2026"
PROMPT = (
    "Exhaustively survey every programming language from 1950 to 2025. "
    "Be maximally comprehensive."
)


async def main_async() -> int:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not set", file=sys.stderr)
        return 2
    client = genai.Client(api_key=api_key)
    print("Checking cancel() exists...")
    has_cancel_async = hasattr(client.aio.interactions, "cancel")
    print(f"  client.aio.interactions.cancel exists: {has_cancel_async}")
    if not has_cancel_async:
        print("CANCEL MISSING — P28 cancel() task cannot be implemented as planned")
        return 1
    print("Submitting overscoped task...")
    resp = await client.aio.interactions.create(
        agent=AGENT, input=PROMPT, background=True, store=True
    )
    interaction_id = getattr(resp, "id", None)
    print(f"  id = {interaction_id}")
    await asyncio.sleep(3)
    print("Calling cancel()...")
    t0 = time.monotonic()
    try:
        await client.aio.interactions.cancel(id=interaction_id)
        print(f"  cancel returned in {time.monotonic()-t0:.2f}s")
    except Exception as exc:
        print(f"  cancel raised: {type(exc).__name__}: {exc}")
        return 1
    for _ in range(12):
        await asyncio.sleep(5)
        interaction = await client.aio.interactions.get(id=interaction_id)
        status = str(getattr(interaction, "status", "?"))
        print(f"  status: {status}")
        if status in {"cancelled", "failed", "completed"}:
            print(f"  outputs/steps present: {bool(getattr(interaction, 'steps', None))}")
            return 0
    print("  did not reach terminal status within 60s post-cancel")
    return 1


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main())
```

Run: `uv run scripts/spike/p28/spike_dr_cancel.py`
Expected: prints `cancel exists: True`, submits, cancels, observes transition to `cancelled` within ~60s post-cancel. **Block-if-failed** if cancel() raises NotImplementedError or doesn't exist — Task 9 needs alternative strategy.

- [ ] **Step 5: Write `scripts/spike/p28/spike_dr_errors.py` — enumerate interactions error classes**

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["google-genai>=1.74.0"]
# ///
"""P28 spike: capture google.genai.errors classes from interactions-specific failures.

Probes: interaction-id-not-found (GET with garbage id), agent-not-found
(CREATE with fake agent), invalid-api-key (CREATE with bad key).
"""

from __future__ import annotations

import asyncio
import inspect
import os
import sys

from google import genai
from google.genai import errors


async def main_async() -> int:
    print("=== google.genai.errors module surface ===")
    for name, cls in inspect.getmembers(errors):
        if name.startswith("_") or not inspect.isclass(cls):
            continue
        bases = ", ".join(b.__name__ for b in cls.__mro__[1:] if b is not object)
        print(f"  {name}  <-  {bases}")
    print("\n=== Probing interaction-specific failure paths ===")
    api_key = os.environ.get("GEMINI_API_KEY")

    print("  [1] invalid api key — interactions.create")
    try:
        bad = genai.Client(api_key="totally-invalid-key-spike")
        await bad.aio.interactions.create(
            agent="deep-research-preview-04-2026", input="x", background=True, store=True
        )
    except Exception as exc:
        print(f"      -> {type(exc).__module__}.{type(exc).__name__}: code="
              f"{getattr(exc, 'code', None)} msg={str(exc)[:160]}")

    if not api_key:
        print("  [2,3] skipped — GEMINI_API_KEY not set")
        return 0
    client = genai.Client(api_key=api_key)

    print("  [2] unknown agent — interactions.create")
    try:
        await client.aio.interactions.create(
            agent="totally-fake-agent-spike", input="x", background=True, store=True
        )
    except Exception as exc:
        print(f"      -> {type(exc).__module__}.{type(exc).__name__}: code="
              f"{getattr(exc, 'code', None)} msg={str(exc)[:160]}")

    print("  [3] unknown interaction id — interactions.get")
    try:
        await client.aio.interactions.get(id="interactions/does-not-exist-spike")
    except Exception as exc:
        print(f"      -> {type(exc).__module__}.{type(exc).__name__}: code="
              f"{getattr(exc, 'code', None)} msg={str(exc)[:160]}")
    return 0


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main())
```

Run: `uv run scripts/spike/p28/spike_dr_errors.py`
Expected: prints the error class hierarchy + the actual exception classes raised by interactions-specific failures. These exact classes feed into Task 2's `_map_gemini_error` extension fixtures.

- [ ] **Step 6: Write `research/gemini-dr-api-spike-2026-05-11.md`**

Required sections (each must cite concrete spike output):

1. **Confirmed agent IDs** — which were YES from Step 1; Block-if-failed status.
2. **Submit response shape** — exact `id` format, top-level attrs, initial status. From Step 2.
3. **Final response shape** — steps[] structure, step.type values, step.content[] item shape. From Step 3.
4. **Citation extraction strategy (the v1 gate)** — which attribute(s) on content items hold citations, exact shape. If NO citation attribute found, this section says "BLOCKED — escalate to user" and Task 8 does not proceed.
5. **Status enum values observed** — every distinct `status` string. From Step 3.
6. **Cancel behavior** — does cancel() exist? does the interaction transition to `cancelled`? does it preserve partial output? From Step 4.
7. **Interactions-specific error classes** — exception class + HTTP code for each probed failure. From Step 5. Feeds Task 2.
8. **Updated Open Questions resolutions** — for each of the spec's Open Questions, mark resolved/still-open with evidence.

- [ ] **Step 7: Commit spike scripts + findings**

```bash
cd /Users/stevemorin/c/thoth-worktrees/p28-gemini-background-deep-research
git add scripts/spike/p28/ research/gemini-dr-api-spike-2026-05-11.md
git commit -m "spike(p28): validate Gemini Deep Research API surface

Five UV scripts probe the live Interactions API: list models, submit
DR task, poll to completion (with citation-shape probe), cancel,
enumerate error classes. Findings in research/gemini-dr-api-spike-2026-05-11.md.

Resolves the citation-extraction strategy (Plan v2 Task 8) and the
interactions-specific error classes (Task 2). Confirms or refutes the
two-tier DR agent ID listing (Task 11 gate)."
```

---

### Task 2: Extend `_map_gemini_error` for Interactions-API-specific failures

**Convention reference (P26+P27):** the error mapper stays a single function — no sync/async split since the Interactions API surface is async-only and reuses the same `genai_errors.ClientError`/`ServerError` exception types. Existing branches (401/403/404/429/400/5xx) remain. P28 adds discriminators where the same HTTP code now has two meanings.

**Files:**
- Modify: `src/thoth/providers/gemini.py:_map_gemini_error`
- Modify: `tests/test_provider_gemini.py` (add test class)

- [ ] **Step 1: Write failing test for interaction-not-found discrimination**

Existing `_map_gemini_error` maps 404 to `"Model {model!r} not found"`. After P28, the same 404 might come from `interactions.get(bad_id)` and should produce a different message.

Append to `tests/test_provider_gemini.py`:

```python
class TestMapGeminiErrorInteractionsSpecific:
    """Task 2: _map_gemini_error discriminates interactions vs models 404."""

    def test_interaction_not_found_404_when_resource_is_interaction(self):
        from google.genai import errors as genai_errors

        from thoth.providers.gemini import _map_gemini_error

        # Construct a ClientError that looks like an interactions.get(bad-id) 404
        exc = genai_errors.ClientError(
            code=404,
            response={
                "error": {
                    "code": 404,
                    "status": "NOT_FOUND",
                    "message": "Interaction not found: interactions/does-not-exist",
                }
            },
        )
        result = _map_gemini_error(exc, model="deep-research-preview-04-2026")
        assert "Interaction" in str(result) or "interaction" in str(result)
        # Must NOT say "Model ... not found" for an interactions 404
        assert "Model 'deep-research-preview-04-2026' not found" not in str(result)

    def test_free_tier_403_for_deep_research_gives_useful_message(self):
        from google.genai import errors as genai_errors

        from thoth.providers.gemini import _map_gemini_error

        exc = genai_errors.ClientError(
            code=403,
            response={
                "error": {
                    "code": 403,
                    "status": "PERMISSION_DENIED",
                    "message": "Deep Research requires a paid tier",
                }
            },
        )
        result = _map_gemini_error(exc, model="deep-research-preview-04-2026")
        msg = str(result)
        assert "paid" in msg.lower() or "tier" in msg.lower()
        # The message should point users at pricing/upgrade docs
        assert "google" in msg.lower() or "pricing" in msg.lower() or "ai.google.dev" in msg
```

- [ ] **Step 2: Run failing tests**

```bash
uv run pytest tests/test_provider_gemini.py::TestMapGeminiErrorInteractionsSpecific -v
```

Expected: 2 FAIL — current `_map_gemini_error` 404 branch returns "Model ... not found" regardless of whether the resource is an interaction.

- [ ] **Step 3: Extend `_map_gemini_error` to discriminate**

In `src/thoth/providers/gemini.py:_map_gemini_error` modify the 404 branch:

```python
if code == 404 or status == "NOT_FOUND":
    msg_lower = message.lower()
    if "interaction" in msg_lower:
        return ProviderError(
            _PROVIDER_NAME_GEMINI,
            f"Gemini interaction not found or expired: {message}. "
            f"Paid-tier retention is 55 days; free-tier 1 day. Start a new "
            f"operation if the interaction has aged out.",
        )
    model_str = repr(model) if model else "(unknown)"
    return ProviderError(
        _PROVIDER_NAME_GEMINI,
        f"Model {model_str} not found or unavailable. "
        f"Run `thoth providers --models --provider gemini` to list valid models.",
    )
```

And modify the 403 branch (PERMISSION_DENIED) to recognize the free-tier-blocked-from-DR case:

```python
if code == 403 or status == "PERMISSION_DENIED":
    msg_lower = message.lower()
    is_dr_model = model and "deep-research" in str(model).lower()
    if is_dr_model and ("tier" in msg_lower or "paid" in msg_lower or "billing" in msg_lower):
        return ProviderError(
            _PROVIDER_NAME_GEMINI,
            f"Gemini Deep Research requires a paid tier (Tier 1+). "
            f"See https://ai.google.dev/pricing. Original error: {message}",
        )
    return ProviderError(
        _PROVIDER_NAME_GEMINI,
        f"Permission denied: {message}",
    )
```

- [ ] **Step 4: Run tests until green**

```bash
uv run pytest tests/test_provider_gemini.py::TestMapGeminiErrorInteractionsSpecific -v
```

Expected: 2 PASS. Then run the full provider test file to confirm no regressions:

```bash
uv run pytest tests/test_provider_gemini.py -v
```

Expected: all existing tests still pass.

- [ ] **Step 5: Commit**

```bash
git add src/thoth/providers/gemini.py tests/test_provider_gemini.py
git commit -m "feat(p28): extend _map_gemini_error for interactions-namespace errors

404 on interactions.get(id) now produces a useful 'interaction expired'
message instead of the 'Model ... not found' message used for chat-model
404s. 403 on Deep Research models with tier/paid/billing phrasing now
surfaces the upgrade-required hint with a pricing URL. Existing chat-model
404/403 paths are unchanged."
```

---

### Task 3: Refactor `submit/check_status/get_result` into routers + `_immediate_*` helpers

**Convention reference (P26+P27):** the public class methods become 5-line routers that delegate based on `is_background_model(self.model)`. P24's existing method bodies are renamed to `_immediate_*` with no behavioral change — this is a pure refactor.

**Files:**
- Modify: `src/thoth/providers/gemini.py:GeminiProvider`
- Modify: `tests/test_provider_gemini.py` (add router tests)

- [ ] **Step 1: Write router tests (will pass trivially after refactor)**

Append to `tests/test_provider_gemini.py`:

```python
class TestGeminiProviderRouting:
    """Task 3: submit/check_status/get_result route on is_background_model."""

    @pytest.mark.asyncio
    async def test_submit_routes_to_immediate_for_chat_model(self, monkeypatch):
        from thoth.providers.gemini import GeminiProvider

        provider = GeminiProvider(api_key="dummy", config={"model": "gemini-2.5-flash-lite"})
        called = {"immediate": False, "deep_research": False}

        async def fake_immediate(prompt, mode, system_prompt, verbose):
            called["immediate"] = True
            return "immediate-job-id"

        async def fake_dr(prompt, mode, system_prompt, verbose):
            called["deep_research"] = True
            return "dr-job-id"

        monkeypatch.setattr(provider, "_immediate_submit", fake_immediate)
        monkeypatch.setattr(provider, "_deep_research_submit", fake_dr)
        result = await provider.submit("x", "gemini_quick", None, False)
        assert result == "immediate-job-id"
        assert called == {"immediate": True, "deep_research": False}

    @pytest.mark.asyncio
    async def test_submit_routes_to_dr_for_deep_research_model(self, monkeypatch):
        from thoth.providers.gemini import GeminiProvider

        provider = GeminiProvider(
            api_key="dummy", config={"model": "deep-research-preview-04-2026"}
        )
        called = {"immediate": False, "deep_research": False}

        async def fake_immediate(prompt, mode, system_prompt, verbose):
            called["immediate"] = True
            return "immediate-job-id"

        async def fake_dr(prompt, mode, system_prompt, verbose):
            called["deep_research"] = True
            return "dr-job-id"

        monkeypatch.setattr(provider, "_immediate_submit", fake_immediate)
        monkeypatch.setattr(provider, "_deep_research_submit", fake_dr)
        result = await provider.submit("x", "gemini_deep_research", None, False)
        assert result == "dr-job-id"
        assert called == {"immediate": False, "deep_research": True}
```

- [ ] **Step 2: Run failing test**

```bash
uv run pytest tests/test_provider_gemini.py::TestGeminiProviderRouting -v
```

Expected: FAIL — `_immediate_submit` and `_deep_research_submit` don't exist yet.

- [ ] **Step 3: Rename existing methods to `_immediate_*` and add routers**

In `src/thoth/providers/gemini.py:GeminiProvider`:

1. Rename `async def submit(...)` → `async def _immediate_submit(...)` (body unchanged)
2. Rename `async def check_status(...)` → `async def _immediate_check_status(...)`
3. Rename `async def get_result(...)` → `async def _immediate_get_result(...)`
4. Add three new public methods:

```python
async def submit(
    self,
    prompt: str,
    mode: str,
    system_prompt: str | None = None,
    verbose: bool = False,
) -> str:
    """Route to immediate (chat-completion) or deep-research (interactions) path."""
    if is_background_model(self.model):
        return await self._deep_research_submit(prompt, mode, system_prompt, verbose)
    return await self._immediate_submit(prompt, mode, system_prompt, verbose)

async def check_status(self, job_id: str) -> dict[str, Any]:
    if self._is_dr_job(job_id):
        return await self._deep_research_check_status(job_id)
    return await self._immediate_check_status(job_id)

async def get_result(self, job_id: str, verbose: bool = False) -> str:
    if self._is_dr_job(job_id):
        return await self._deep_research_get_result(job_id, verbose)
    return await self._immediate_get_result(job_id, verbose)

def _is_dr_job(self, job_id: str) -> bool:
    """Job-id discriminator. DR jobs are stored with kind='deep_research' in self.jobs."""
    job = self.jobs.get(job_id)
    return bool(job and job.get("kind") == "deep_research")
```

5. Add stubs for the `_deep_research_*` methods that `raise NotImplementedError("Implemented in Task 5/7/8")` — these will be filled in by subsequent tasks. The stubs let Task 3's commit be self-contained.

- [ ] **Step 4: Run all gemini tests to confirm no regressions**

```bash
uv run pytest tests/test_provider_gemini.py -v
```

Expected: all existing tests still pass + the two new routing tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/thoth/providers/gemini.py tests/test_provider_gemini.py
git commit -m "refactor(p28): split GeminiProvider into immediate/DR routers

submit/check_status/get_result are now 5-line routers that branch on
is_background_model(self.model) and delegate to _immediate_* (P24's
chat-completion code, renamed verbatim) or _deep_research_* (NEW,
stubbed as NotImplementedError, implemented in Tasks 5/7/8).

_is_dr_job uses a self.jobs[kind] discriminator (added in Task 4).
Pure refactor — no behavioral change for chat-completion paths."
```

---

### Task 4: `self.jobs` schema migration with discriminator

**Files:**
- Modify: `src/thoth/providers/gemini.py:GeminiProvider`
- Modify: `tests/test_provider_gemini.py`

- [ ] **Step 1: Failing test**

```python
class TestGeminiJobsSchema:
    """Task 4: self.jobs entries have a 'kind' discriminator."""

    @pytest.mark.asyncio
    async def test_immediate_submit_stashes_kind_immediate(self, monkeypatch):
        from thoth.providers.gemini import GeminiProvider

        provider = GeminiProvider(api_key="dummy", config={"model": "gemini-2.5-flash-lite"})
        fake_response = MagicMock(id="fake-resp-id")
        with patch.object(provider, "_submit_with_retry", new_callable=AsyncMock) as m:
            m.return_value = fake_response
            job_id = await provider._immediate_submit("x", "gemini_quick", None, False)
        assert provider.jobs[job_id]["kind"] == "immediate"
        assert "response" in provider.jobs[job_id]
```

Run, expect FAIL.

- [ ] **Step 2: Modify `_immediate_submit` to write the discriminator**

In the existing renamed method (was `submit`, now `_immediate_submit`), change:

```python
self.jobs[job_id] = {"response": response, "created_at": time.time()}
```

to:

```python
self.jobs[job_id] = {
    "kind": "immediate",
    "response": response,
    "created_at": time.time(),
}
```

- [ ] **Step 3: Run tests, commit**

```bash
uv run pytest tests/test_provider_gemini.py::TestGeminiJobsSchema -v
uv run pytest tests/test_provider_gemini.py -v  # full sanity
git add -A && git commit -m "refactor(p28): add 'kind' discriminator to self.jobs entries"
```

---

### Task 5: `_deep_research_submit` — failing tests + implementation

**Pre-condition:** Task 1 spike step 2 has completed and the response-shape evidence is in `research/gemini-dr-api-spike-2026-05-11.md` §2. If not, do that first.

**Files:**
- Modify: `src/thoth/providers/gemini.py:GeminiProvider`
- Modify: `tests/test_provider_gemini.py`

- [ ] **Step 1: Write failing tests**

```python
class TestGeminiDeepResearchSubmit:
    """Task 5: _deep_research_submit calls client.aio.interactions.create correctly."""

    @pytest.mark.asyncio
    async def test_submit_calls_interactions_create_with_agent_background_store(self):
        from thoth.providers.gemini import GeminiProvider

        provider = GeminiProvider(
            api_key="dummy", config={"model": "deep-research-preview-04-2026"}
        )
        fake_create = AsyncMock(return_value=MagicMock(id="interactions/xyz-123"))
        provider.client.aio.interactions = MagicMock()
        provider.client.aio.interactions.create = fake_create
        job_id = await provider._deep_research_submit("Research X", "gemini_deep_research", None, False)
        fake_create.assert_awaited_once()
        call_kwargs = fake_create.call_args.kwargs
        assert call_kwargs["agent"] == "deep-research-preview-04-2026"
        assert call_kwargs["input"] == "Research X"
        assert call_kwargs["background"] is True
        assert call_kwargs["store"] is True
        assert job_id == "interactions/xyz-123"
        assert provider.jobs[job_id]["kind"] == "deep_research"
        assert provider.jobs[job_id]["interaction_id"] == "interactions/xyz-123"

    @pytest.mark.asyncio
    async def test_submit_does_not_cache_response_body(self):
        """DR submit returns immediately; the response body is not yet available.
        self.jobs entry must NOT contain a 'response' key (only metadata)."""
        from thoth.providers.gemini import GeminiProvider

        provider = GeminiProvider(
            api_key="dummy", config={"model": "deep-research-preview-04-2026"}
        )
        provider.client.aio.interactions = MagicMock()
        provider.client.aio.interactions.create = AsyncMock(
            return_value=MagicMock(id="interactions/abc")
        )
        job_id = await provider._deep_research_submit("x", "gemini_deep_research", None, False)
        assert "response" not in provider.jobs[job_id]
```

Run, expect FAIL.

- [ ] **Step 2: Implement `_deep_research_submit`**

```python
async def _deep_research_submit(
    self,
    prompt: str,
    mode: str,
    system_prompt: str | None = None,
    verbose: bool = False,
) -> str:
    """Submit a Deep Research interaction; return the interaction id.

    Unlike the immediate path, the response body is NOT yet available — the
    actual research runs asynchronously and is polled via check_status. The
    self.jobs entry stores only metadata (kind, interaction_id, submitted_at,
    mode, model). The response is fetched lazily by _deep_research_get_result.
    """
    self._validate_kind_for_model(mode)
    try:
        response = await self._deep_research_submit_with_retry(prompt)
    except ModeKindMismatchError:
        raise
    except Exception as e:
        raise _map_gemini_error(e, self.model, verbose=verbose) from e

    interaction_id = getattr(response, "id", None)
    if not interaction_id:
        raise ProviderError(
            _PROVIDER_NAME_GEMINI,
            "interactions.create returned a response without an id",
        )
    self.jobs[interaction_id] = {
        "kind": "deep_research",
        "interaction_id": interaction_id,
        "mode": mode,
        "model": self.model,
        "submitted_at": time.time(),
    }
    return interaction_id

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception(_is_retryable_gemini_exception),
    reraise=True,
)
async def _deep_research_submit_with_retry(self, prompt: str) -> Any:
    return await self.client.aio.interactions.create(
        agent=self.model,
        input=prompt,
        background=True,
        store=True,
    )
```

Note: `system_prompt` is ignored on the Deep Research path because the upstream Interactions API for DR does not document a system-instruction parameter. The mode's `system_prompt` is implicitly part of the agent's behavior. Document this in a docstring line.

- [ ] **Step 3: Run tests + commit**

```bash
uv run pytest tests/test_provider_gemini.py::TestGeminiDeepResearchSubmit -v
git add -A && git commit -m "feat(p28): implement _deep_research_submit using interactions.create

Submits with agent=, background=True, store=True (all required by DR API).
Stashes self.jobs[id] = {kind: deep_research, interaction_id, mode, model,
submitted_at} — NO cached response body since DR is async. Retries on
transient errors using the existing _is_retryable_gemini_exception filter
and same tenacity policy as P24's _submit_with_retry."
```

---

### Task 6: `_deep_research_check_status` — failing tests + implementation

**Files:**
- Modify: `src/thoth/providers/gemini.py:GeminiProvider`
- Modify: `tests/test_provider_gemini.py`

- [ ] **Step 1: Failing tests**

```python
class TestGeminiDeepResearchCheckStatus:
    """Task 6: _deep_research_check_status polls interactions.get and maps status."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "live_status,expected_thoth_status",
        [
            ("in_progress", "in_progress"),
            ("completed", "completed"),
            ("failed", "permanent_error"),
            ("cancelled", "cancelled"),
        ],
    )
    async def test_status_mapping(self, live_status, expected_thoth_status):
        from thoth.providers.gemini import GeminiProvider

        provider = GeminiProvider(
            api_key="dummy", config={"model": "deep-research-preview-04-2026"}
        )
        provider.jobs["interactions/abc"] = {"kind": "deep_research", "interaction_id": "interactions/abc"}
        fake_get = AsyncMock(return_value=MagicMock(status=live_status))
        provider.client.aio.interactions = MagicMock()
        provider.client.aio.interactions.get = fake_get
        result = await provider._deep_research_check_status("interactions/abc")
        assert result["status"] == expected_thoth_status

    @pytest.mark.asyncio
    async def test_unknown_job_id(self):
        from thoth.providers.gemini import GeminiProvider

        provider = GeminiProvider(
            api_key="dummy", config={"model": "deep-research-preview-04-2026"}
        )
        result = await provider._deep_research_check_status("interactions/unknown")
        assert result["status"] == "not_found"
```

Run, expect FAIL.

- [ ] **Step 2: Implement**

```python
async def _deep_research_check_status(self, job_id: str) -> dict[str, Any]:
    """Poll interactions.get; map Gemini status to Thoth status enum."""
    if job_id not in self.jobs:
        return {"status": "not_found", "error": f"Unknown job_id: {job_id}"}
    try:
        interaction = await self.client.aio.interactions.get(id=job_id)
    except Exception as e:
        mapped = _map_gemini_error(e, self.model)
        if _is_retryable_gemini_exception(e):
            return {"status": "transient_error", "error": str(mapped)}
        return {"status": "permanent_error", "error": str(mapped)}

    live = str(getattr(interaction, "status", "in_progress"))
    self.jobs[job_id]["last_status"] = live
    self.jobs[job_id]["last_interaction"] = interaction
    mapping = {
        "in_progress": "in_progress",
        "completed": "completed",
        "failed": "permanent_error",
        "cancelled": "cancelled",
    }
    return {
        "status": mapping.get(live, "in_progress"),
        "raw_status": live,
    }
```

- [ ] **Step 3: Run + commit**

```bash
uv run pytest tests/test_provider_gemini.py::TestGeminiDeepResearchCheckStatus -v
git add -A && git commit -m "feat(p28): implement _deep_research_check_status

interactions.get → translate Gemini status enum (in_progress/completed/
failed/cancelled) to Thoth status enum. Errors classified as transient
vs permanent via the existing _is_retryable_gemini_exception filter,
so the runtime polling loop's transient retry budget kicks in for
network blips without surfacing them as user errors."
```

---

### Task 7: `_deep_research_get_result` — failing tests + implementation

**Pre-condition:** Task 1 spike step 3 has resolved the citation extraction strategy and `research/gemini-dr-api-spike-2026-05-11.md` §4 documents the exact attribute path (e.g. `step.content[i].citations`). If §4 says "BLOCKED", **stop and reconvene** before writing the failing test — do not invent a citation shape.

**Files:**
- Modify: `src/thoth/providers/gemini.py:GeminiProvider`
- Modify: `tests/test_provider_gemini.py`

- [ ] **Step 1: Write failing tests using the spike-validated citation shape**

The test fixtures **MUST** use the exact attribute names documented in `research/gemini-dr-api-spike-2026-05-11.md` §4. Example assuming the spike found `step.content[i].citations: list[{title, uri}]` (replace if spike found a different shape):

```python
class TestGeminiDeepResearchGetResult:
    """Task 7: _deep_research_get_result renders steps[] + extracts citations.

    Citation shape per spike findings: see
    research/gemini-dr-api-spike-2026-05-11.md §4 for the authoritative
    attribute path. This test class encodes whatever the spike documented.
    """

    @pytest.mark.asyncio
    async def test_get_result_renders_model_output_text(self):
        from thoth.providers.gemini import GeminiProvider

        provider = GeminiProvider(
            api_key="dummy", config={"model": "deep-research-preview-04-2026"}
        )
        # Build a fake interaction matching the spike-documented shape
        text_item = MagicMock(type="text", text="The three papers are...")
        model_output_step = MagicMock(type="model_output", content=[text_item])
        fake_interaction = MagicMock(status="completed", steps=[model_output_step])
        provider.jobs["interactions/abc"] = {
            "kind": "deep_research",
            "interaction_id": "interactions/abc",
            "last_interaction": fake_interaction,
        }
        result = await provider._deep_research_get_result("interactions/abc", False)
        assert "The three papers are..." in result

    @pytest.mark.asyncio
    async def test_get_result_renders_sources_block_when_citations_present(self):
        from thoth.providers.gemini import GeminiProvider

        provider = GeminiProvider(
            api_key="dummy", config={"model": "deep-research-preview-04-2026"}
        )
        # Citation shape per spike §4 — REPLACE if spike documented different attrs.
        citation_item = MagicMock(
            title="Paxos Made Simple",
            uri="https://example.org/paxos.pdf",
        )
        text_item = MagicMock(type="text", text="Body", citations=[citation_item])
        model_output_step = MagicMock(type="model_output", content=[text_item])
        fake_interaction = MagicMock(status="completed", steps=[model_output_step])
        provider.jobs["interactions/abc"] = {
            "kind": "deep_research",
            "interaction_id": "interactions/abc",
            "last_interaction": fake_interaction,
        }
        result = await provider._deep_research_get_result("interactions/abc", False)
        assert "## Sources" in result
        assert "Paxos Made Simple" in result
        assert "https://example.org/paxos.pdf" in result

    @pytest.mark.asyncio
    async def test_get_result_no_sources_when_citations_absent(self):
        from thoth.providers.gemini import GeminiProvider

        provider = GeminiProvider(
            api_key="dummy", config={"model": "deep-research-preview-04-2026"}
        )
        text_item = MagicMock(type="text", text="Body without sources", citations=[])
        model_output_step = MagicMock(type="model_output", content=[text_item])
        fake_interaction = MagicMock(status="completed", steps=[model_output_step])
        provider.jobs["interactions/abc"] = {
            "kind": "deep_research",
            "interaction_id": "interactions/abc",
            "last_interaction": fake_interaction,
        }
        result = await provider._deep_research_get_result("interactions/abc", False)
        assert "## Sources" not in result
```

- [ ] **Step 2: Implement**

```python
async def _deep_research_get_result(self, job_id: str, verbose: bool = False) -> str:
    """Render the completed interaction as markdown text + ## Sources.

    Reads the cached interaction stashed by _deep_research_check_status. If
    no cache exists (resume flow), re-fetches via interactions.get first.

    Citation extraction follows the structured shape documented in
    research/gemini-dr-api-spike-2026-05-11.md §4 (v1 strategy: structured
    citations only, no regex fallback per user 2026-05-11 decision).
    """
    if job_id not in self.jobs:
        raise ProviderError(_PROVIDER_NAME_GEMINI, f"Unknown job_id: {job_id}")
    job = self.jobs[job_id]
    interaction = job.get("last_interaction")
    if interaction is None:
        try:
            interaction = await self.client.aio.interactions.get(id=job_id)
            job["last_interaction"] = interaction
        except Exception as e:
            raise _map_gemini_error(e, self.model, verbose=verbose) from e

    steps = getattr(interaction, "steps", None) or []
    text_parts: list[str] = []
    citations: list[Citation] = []
    seen_urls: set[str] = set()
    for step in steps:
        if str(getattr(step, "type", "")) != "model_output":
            continue
        content = getattr(step, "content", None) or []
        for item in content:
            text = getattr(item, "text", None) or ""
            if text:
                text_parts.append(text)
            # Citation extraction per spike-documented attribute path.
            # If spike found a different shape, update this block.
            item_citations = getattr(item, "citations", None) or []
            for c in item_citations:
                url = getattr(c, "uri", None) or getattr(c, "url", None)
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                title = getattr(c, "title", "") or urlparse(url).netloc
                citations.append(Citation(title=str(title), url=str(url)))

    answer = "".join(text_parts).strip()
    if not answer and verbose:
        debug_print_empty_response(interaction, provider_label="Gemini DR")

    sections: list[str] = []
    if answer:
        sections.append(answer)
    if citations:
        sections.append(render_sources_block(citations))
    return "\n\n".join(sections)
```

- [ ] **Step 3: Run + commit**

```bash
uv run pytest tests/test_provider_gemini.py::TestGeminiDeepResearchGetResult -v
git add -A && git commit -m "feat(p28): implement _deep_research_get_result with structured citations

Renders interaction.steps[] where step.type='model_output' as markdown.
Extracts citations from item.citations[] (shape per spike §4); dedupes
by URL across steps; renders ## Sources block via the shared
render_sources_block helper. Empty citations omit the Sources section;
empty text returns empty string."
```

---

### Task 8: `cancel()` — failing tests + implementation

**Pre-condition:** Task 1 spike step 4 confirmed `client.aio.interactions.cancel()` exists.

**Files:**
- Modify: `src/thoth/providers/gemini.py:GeminiProvider` (add `cancel` method)
- Modify: `tests/test_provider_gemini.py`

- [ ] **Step 1: Failing tests**

```python
class TestGeminiCancel:
    """Task 8: cancel() invokes interactions.cancel for DR jobs."""

    @pytest.mark.asyncio
    async def test_cancel_calls_interactions_cancel(self):
        from thoth.providers.gemini import GeminiProvider

        provider = GeminiProvider(
            api_key="dummy", config={"model": "deep-research-preview-04-2026"}
        )
        provider.jobs["interactions/abc"] = {
            "kind": "deep_research", "interaction_id": "interactions/abc"
        }
        fake_cancel = AsyncMock(return_value=None)
        provider.client.aio.interactions = MagicMock()
        provider.client.aio.interactions.cancel = fake_cancel
        result = await provider.cancel("interactions/abc")
        fake_cancel.assert_awaited_once_with(id="interactions/abc")
        assert result == {"status": "cancelled"}
        assert provider.jobs["interactions/abc"]["cancel_requested"] is True

    @pytest.mark.asyncio
    async def test_cancel_noop_for_immediate_jobs(self):
        """Immediate jobs (chat completion) don't support upstream cancel."""
        from thoth.providers.gemini import GeminiProvider

        provider = GeminiProvider(api_key="dummy", config={"model": "gemini-2.5-flash-lite"})
        provider.jobs["job-imm"] = {"kind": "immediate", "response": MagicMock()}
        result = await provider.cancel("job-imm")
        assert result["status"] == "cancelled"
        # No upstream call — immediate jobs are already complete
```

- [ ] **Step 2: Implement**

```python
async def cancel(self, job_id: str) -> dict[str, Any]:
    """Cancel a job. For DR, calls interactions.cancel; for immediate, no-op.

    Immediate (chat-completion) jobs are already complete by the time submit
    returns, so cancel is a no-op there. DR jobs run server-side and must
    be explicitly cancelled via the Interactions API.
    """
    if job_id not in self.jobs:
        return {"status": "not_found", "error": f"Unknown job_id: {job_id}"}
    job = self.jobs[job_id]
    if job.get("kind") != "deep_research":
        # Immediate-path: nothing to cancel upstream
        return {"status": "cancelled"}
    try:
        job["cancel_requested"] = True
        await self.client.aio.interactions.cancel(id=job_id)
    except Exception as e:
        raise _map_gemini_error(e, self.model) from e
    return {"status": "cancelled"}
```

- [ ] **Step 3: Run + commit**

```bash
uv run pytest tests/test_provider_gemini.py::TestGeminiCancel -v
git add -A && git commit -m "feat(p28): implement GeminiProvider.cancel()

DR jobs: invoke client.aio.interactions.cancel(id) and set
cancel_requested flag (used by check_status to disambiguate
user-initiated vs server-initiated cancels per research doc §10).
Immediate jobs: no-op (chat completion is already complete by the
time submit returns)."
```

---

### Task 9: `reconnect()` — failing tests + implementation

**Files:**
- Modify: `src/thoth/providers/gemini.py:GeminiProvider`
- Modify: `tests/test_provider_gemini.py`

- [ ] **Step 1: Failing tests**

```python
class TestGeminiReconnect:
    """Task 9: reconnect() re-attaches DR state after process restart."""

    @pytest.mark.asyncio
    async def test_reconnect_repopulates_jobs_entry(self):
        from thoth.providers.gemini import GeminiProvider

        provider = GeminiProvider(
            api_key="dummy", config={"model": "deep-research-preview-04-2026"}
        )
        # Cold start: jobs dict empty
        assert "interactions/abc" not in provider.jobs
        fake_get = AsyncMock(return_value=MagicMock(status="in_progress", id="interactions/abc"))
        provider.client.aio.interactions = MagicMock()
        provider.client.aio.interactions.get = fake_get
        await provider.reconnect("interactions/abc")
        assert "interactions/abc" in provider.jobs
        assert provider.jobs["interactions/abc"]["kind"] == "deep_research"
        assert provider.jobs["interactions/abc"]["interaction_id"] == "interactions/abc"
```

- [ ] **Step 2: Implement**

```python
async def reconnect(self, job_id: str) -> None:
    """Re-attach to an existing DR interaction after process restart.

    Called by the runtime's resume_operation flow. Verifies the interaction
    still exists upstream and seeds self.jobs[job_id] so subsequent
    check_status / get_result calls work. Immediate jobs cannot be reconnected
    (their response was lost with the process); they would have been
    completed before the process ended.
    """
    try:
        interaction = await self.client.aio.interactions.get(id=job_id)
    except Exception as e:
        raise _map_gemini_error(e, self.model) from e
    self.jobs[job_id] = {
        "kind": "deep_research",
        "interaction_id": job_id,
        "model": self.model,
        "reconnected_at": time.time(),
        "last_interaction": interaction,
        "last_status": str(getattr(interaction, "status", "in_progress")),
    }
```

- [ ] **Step 3: Run + commit**

```bash
uv run pytest tests/test_provider_gemini.py::TestGeminiReconnect -v
git add -A && git commit -m "feat(p28): implement GeminiProvider.reconnect()

Re-attaches to an existing DR interaction by id and seeds self.jobs.
Called by runtime resume_operation after process restart. Immediate
jobs cannot reconnect (responses were process-local)."
```

---

### Task 10: Add 9 `gemini_*_research` modes to `KNOWN_MODELS`

**Pre-condition:** Task 1 spike step 1 confirmed `deep-research-preview-04-2026` is listed by the live API.

**Files:**
- Modify: `src/thoth/config.py`
- Modify: `tests/test_provider_gemini.py` (mode-presence assertion)

- [ ] **Step 1: Add the 9 entries**

In `src/thoth/config.py:KNOWN_MODELS`, after the existing `gemini_reasoning` entry, append (preserving the OpenAI mode-name parallels):

```python
"gemini_quick_research": {
    "provider": "gemini",
    "model": "deep-research-preview-04-2026",
    "kind": "background",
    "system_prompt": "Provide a brief, focused research summary in under 500 words.",
    "description": "Quick Gemini Deep Research — short summary.",
    "previous": "exploration",
    "next": "gemini_deep_dive",
},
"gemini_exploration": {
    "provider": "gemini",
    "model": "deep-research-preview-04-2026",
    "kind": "background",
    "system_prompt": "Explore the topic broadly. Identify key dimensions, controversies, and open questions.",
    "description": "Open-ended exploratory Gemini Deep Research.",
    "previous": None,
    "next": "gemini_deep_dive",
},
"gemini_deep_dive": {
    "provider": "gemini",
    "model": "deep-research-preview-04-2026",
    "kind": "background",
    "system_prompt": "Conduct an in-depth, comprehensive analysis. Cite sources.",
    "description": "In-depth Gemini Deep Research dive.",
    "previous": "exploration",
    "next": "gemini_tutorial",
},
"gemini_tutorial": {
    "provider": "gemini",
    "model": "deep-research-preview-04-2026",
    "kind": "background",
    "system_prompt": "Produce a step-by-step tutorial. Include code examples where applicable.",
    "description": "Tutorial-format Gemini Deep Research.",
    "previous": "gemini_deep_dive",
    "next": "gemini_solution",
},
"gemini_solution": {
    "provider": "gemini",
    "model": "deep-research-preview-04-2026",
    "kind": "background",
    "system_prompt": "Recommend a concrete solution. Justify trade-offs.",
    "description": "Solution-recommendation Gemini Deep Research.",
    "previous": "gemini_tutorial",
    "next": "gemini_prd",
},
"gemini_prd": {
    "provider": "gemini",
    "model": "deep-research-preview-04-2026",
    "kind": "background",
    "system_prompt": "Draft a product-requirements document. Include scope, acceptance criteria, and risks.",
    "description": "PRD-format Gemini Deep Research.",
    "previous": "gemini_solution",
    "next": "gemini_tdd",
},
"gemini_tdd": {
    "provider": "gemini",
    "model": "deep-research-preview-04-2026",
    "kind": "background",
    "system_prompt": "Produce a test-driven-development plan. Tests first, then implementation outline.",
    "description": "TDD-plan Gemini Deep Research.",
    "previous": "gemini_prd",
    "next": "gemini_deep_research",
},
"gemini_deep_research": {
    "provider": "gemini",
    "model": "deep-research-preview-04-2026",
    "kind": "background",
    "system_prompt": "Conduct exhaustive Deep Research. Cover every relevant angle. Cite sources rigorously.",
    "description": "Exhaustive Gemini Deep Research.",
    "previous": None,
    "next": None,
},
"gemini_comparison": {
    "provider": "gemini",
    "model": "deep-research-preview-04-2026",
    "kind": "background",
    "system_prompt": "Compare alternatives across explicit criteria. Produce a comparison matrix.",
    "description": "Comparison-table Gemini Deep Research.",
    "previous": None,
    "next": None,
},
```

- [ ] **Step 2: Add a test that asserts all 9 modes are present and well-formed**

```python
class TestGeminiDeepResearchModes:
    """Task 10: 9 gemini_*_research modes are in KNOWN_MODELS."""

    EXPECTED = (
        "gemini_quick_research", "gemini_exploration", "gemini_deep_dive",
        "gemini_tutorial", "gemini_solution", "gemini_prd", "gemini_tdd",
        "gemini_deep_research", "gemini_comparison",
    )

    def test_all_modes_present(self):
        from thoth.config import KNOWN_MODELS

        for mode in self.EXPECTED:
            assert mode in KNOWN_MODELS, f"Missing mode {mode!r}"

    def test_all_modes_use_dr_agent_and_background_kind(self):
        from thoth.config import KNOWN_MODELS

        for mode in self.EXPECTED:
            entry = KNOWN_MODELS[mode]
            assert entry["provider"] == "gemini"
            assert entry["kind"] == "background"
            assert entry["model"] == "deep-research-preview-04-2026"
```

- [ ] **Step 3: Run + commit**

```bash
uv run pytest tests/test_provider_gemini.py::TestGeminiDeepResearchModes -v
git add -A && git commit -m "feat(p28): add 9 gemini_*_research modes for Deep Research

All declare provider=gemini, kind=background, model=deep-research-
preview-04-2026 (v1 ships speed-efficiency tier only; max tier deferred
per resolved Open Question #6). Mode names parallel OpenAI's set for
cross-provider chain compatibility (e.g. 'exploration' -> 'gemini_deep_dive')."
```

---

### Task 11: Extend `[providers.gemini]` schema with DR tunables

**Files:**
- Modify: `src/thoth/config_schema.py:GeminiConfig`
- Modify: `tests/test_config_schema.py` (or wherever GeminiConfig is tested)

- [ ] **Step 1: Failing test**

```python
def test_gemini_config_has_dr_tunables():
    from thoth.config_schema import GeminiConfig

    cfg = GeminiConfig()
    assert hasattr(cfg, "poll_interval")
    assert cfg.poll_interval == 10  # default 10s
    assert hasattr(cfg, "max_wait_minutes")
    assert cfg.max_wait_minutes == 60  # upstream max research time
```

- [ ] **Step 2: Implement — add fields to `GeminiConfig`**

In `src/thoth/config_schema.py:GeminiConfig`, add:

```python
poll_interval: int = Field(
    default=10,
    description="Seconds between Deep Research interaction.get polls.",
)
max_wait_minutes: int = Field(
    default=60,
    description="Max research time before timing out the polling loop. "
                "Upstream Gemini Deep Research hard-limit is 60 minutes; "
                "exceeding indicates a server-side stall.",
)
```

- [ ] **Step 3: Run + commit**

```bash
uv run pytest tests/test_config_schema.py -v -k gemini
git add -A && git commit -m "feat(p28): add DR-specific tunables to GeminiConfig

poll_interval (default 10s) and max_wait_minutes (default 60 — upstream
hard limit). Reused by the runtime polling loop for any kind=background
gemini mode."
```

---

### Task 12: Runtime polling-tunable wiring

**Pre-condition:** verify how `_run_polling_loop` currently picks up provider-specific tunables for OpenAI and Perplexity. Mirror that wiring; do not invent a new mechanism.

**Files:**
- Modify: `src/thoth/run.py` (if needed — possibly already provider-agnostic via config lookup)
- Modify: tests as appropriate

- [ ] **Step 1: Inspect runtime tunable resolution**

```bash
grep -n "poll_interval\|max_wait_minutes" src/thoth/run.py src/thoth/config.py src/thoth/config_schema.py
```

Verify whether the polling loop reads tunables from `providers.<name>.poll_interval` automatically (likely yes — P26/P27 use the same mechanism). If yes, this task is config-validation only.

- [ ] **Step 2: Add an integration test that asserts gemini DR uses the 10s default**

(Test pattern depends on how OpenAI/Perplexity tunables are tested — mirror that.)

- [ ] **Step 3: Run + commit**

```bash
uv run pytest -k "polling or run_polling" -v
git add -A && git commit -m "test(p28): verify _run_polling_loop reads gemini DR tunables"
```

---

### Task 13: Full default test suite green gate

- [ ] **Step 1: Run everything**

```bash
just check                        # ruff + ty
uv run ruff format --check src/ tests/
uv run pytest -q                  # all default tests
./thoth_test -r --skip-interactive -q  # integration tests
```

Expected: all green. Fix any regression introduced by the refactor in Tasks 3-9.

- [ ] **Step 2: Commit if any fixes were needed**

---

### Task 14: README cost callout + mode listing

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add a Deep Research cost section**

Below the existing OpenAI/Perplexity cost notes (locate via `grep -n "deep.research\|cost\|tier" README.md`), add:

```markdown
### Gemini Deep Research costs (P28)

Gemini Deep Research is a paid-tier feature (Tier 1+ on Google AI Studio).
Estimated cost per task:
- `deep-research-preview-04-2026` (default for the 9 `gemini_*_research` modes): **$1–$3 per task**
- `deep-research-max-preview-04-2026` (deferred to a successor project): **$3–$7 per task**

Both agents are currently in **preview**; pricing and behavior may change.
The 60-minute hard research-time limit is enforced upstream.
```

- [ ] **Step 2: Update the modes table to include the 9 new entries**

(Locate the existing modes-listing section; append the 9 `gemini_*_research` modes with their `description` strings.)

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs(p28): README cost callout + 9 gemini_*_research modes"
```

---

### Task 15: Live-API gated tests for DR workflows

**Files:**
- Create: `tests/extended/test_gemini_dr_real_workflows.py`
- Modify: `.github/workflows/live-api.yml` (verify GEMINI_API_KEY present)

- [ ] **Step 1: Write the live-API test file**

```python
"""P28 Task 15: live-API CLI workflow tests for Gemini Deep Research.

Gated by @pytest.mark.live_api; runs weekly via .github/workflows/live-api.yml.
Requires the GEMINI_API_KEY repo secret (paid Tier 1+ account).
"""

from __future__ import annotations

import os
import subprocess

import pytest

requires_key = pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set",
)


@pytest.mark.live_api
@requires_key
def test_thoth_ask_gemini_quick_research_end_to_end(tmp_path):
    """thoth ask --mode gemini_quick_research submits, polls, returns text."""
    out_file = tmp_path / "out.md"
    result = subprocess.run(
        [
            "thoth", "ask",
            "--mode", "gemini_quick_research",
            "--out", str(out_file),
            "What is the difference between Paxos and Raft? Brief.",
        ],
        capture_output=True,
        text=True,
        timeout=20 * 60,  # 20 min — fast tier should finish well under
    )
    assert result.returncode == 0, result.stderr
    assert out_file.exists()
    content = out_file.read_text()
    assert len(content) > 100
    # citation section is optional but expected for DR
    # (don't assert hard — citations may be empty per spike §4 findings)


@pytest.mark.live_api
@requires_key
def test_thoth_resume_gemini_dr(tmp_path):
    """thoth ask then thoth resume re-attaches and completes."""
    # Submit then immediately Ctrl-C-equivalent stop, get the op_id from output,
    # then resume. Test marshalling depends on existing live-test patterns.
    pytest.skip("Wire up via existing live-test resume helper")


@pytest.mark.live_api
@requires_key
def test_thoth_cancel_gemini_dr():
    """thoth cancel transitions a running DR interaction to cancelled."""
    pytest.skip("Wire up via existing live-test cancel helper")


@pytest.mark.live_api
@requires_key
def test_invalid_gemini_key_useful_error():
    """Invalid GEMINI_API_KEY produces the upgrade-URL message, not raw 401."""
    env = os.environ.copy()
    env["GEMINI_API_KEY"] = "invalid-key-live-test"
    result = subprocess.run(
        ["thoth", "ask", "--mode", "gemini_quick_research", "hi"],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    assert result.returncode != 0
    assert "aistudio.google.com" in result.stderr or "api key" in result.stderr.lower()
```

- [ ] **Step 2: Verify workflow YAML wires the secret**

```bash
grep -n "GEMINI_API_KEY" .github/workflows/live-api.yml
```

If missing, add it to the env block. P24 likely already wired this — verify, don't duplicate.

- [ ] **Step 3: Commit**

```bash
git add tests/extended/test_gemini_dr_real_workflows.py .github/workflows/live-api.yml
git commit -m "test(p28): live-API gated tests for Gemini Deep Research workflows"
```

---

### Task 16: Verify extended-marker model-kind drift covers new modes

The existing `tests/extended/test_model_kind_runtime.py` iterates `KNOWN_MODELS` and asserts each declared kind matches runtime behavior. The 9 new `gemini_*_research` modes are auto-included.

- [ ] **Step 1: Confirm auto-coverage**

```bash
uv run pytest tests/extended/test_model_kind_runtime.py -v -m extended -k gemini
```

Expected: 9 new test parameterizations (one per `gemini_*_research` mode) pass.

- [ ] **Step 2: If GEMINI_API_KEY is set locally and you want a live check, run nightly workflow manually**

```bash
gh workflow run "Extended Contract Tests (nightly)"
```

---

### Task 17: PROJECTS.md + project file finalization

**Files:**
- Modify: `projects/P28-gemini-background-deep-research.md` (status update; mark TS01-T04 task list)
- Modify: `PROJECTS.md` (flip P28 row from `[ ]` to `[~]` when Task 1 lands, to `[x]` when Task 17 lands)

- [ ] **Step 1: When starting Task 1, flip the trunk row to `[~]`**

In `PROJECTS.md`, change `- [ ] **P28**` → `- [~] **P28**`. Commit.

- [ ] **Step 2: When Task 16 verifies green, flip to `[x]`**

In `PROJECTS.md` and in the project file's `**Status:**` line. Commit.

- [ ] **Step 3: Update the project file's `### Tests & Tasks` section to mark P28-TS01 / T02 / T03 / T04 done**

The original 4 placeholder tasks in the project file are subsumed by this plan. Mark them `[x]` with a note pointing at the plan tasks that covered each.

---

### Task 18: Final integration verification

- [ ] **Step 1: Run full gate one last time**

```bash
make env-check
just fix
just check
uv run ruff format --check src/ tests/
uv run pytest -q
./thoth_test -r --skip-interactive -q
```

All green.

- [ ] **Step 2: Spot-check the spec acceptance criteria**

Walk the acceptance-criteria list in `projects/P28-gemini-background-deep-research.md` and check each manually or via a targeted test. Anything not covered → file as follow-up, do not retrofit silently.

- [ ] **Step 3: Open the PR**

```bash
gh pr create --title "P28: Gemini Deep Research background path" --body "$(cat <<'EOF'
## Summary
Adds Gemini Deep Research background operations on top of P24's GeminiProvider.

- New: cancel(), reconnect(), _deep_research_submit/check_status/get_result internal helpers
- 9 gemini_*_research modes using deep-research-preview-04-2026 (fast tier; max tier deferred)
- Routing: submit/check_status/get_result branch on is_background_model(self.model)
- _map_gemini_error extended for interactions-namespace 404 + DR-specific 403
- Live-API gated tests via @pytest.mark.live_api

## Plan
docs/superpowers/plans/2026-05-11-p28-gemini-deep-research-background.md

## Test plan
- [x] uv run pytest -q
- [x] ./thoth_test -r --skip-interactive -q
- [x] just check
- [ ] Manual: thoth ask --mode gemini_quick_research "test" — completes end-to-end
- [ ] Manual: thoth cancel during a running DR operation transitions cleanly
EOF
)"
```

---

## Acceptance criteria (mirror of P28 spec, v2)

- `thoth ask --mode gemini_quick_research "test query"` submits, polls, writes the result to the project directory.
- `thoth resume <op-id>` re-attaches to a Gemini DR interaction after process restart.
- `thoth cancel <op-id>` transitions the interaction to `cancelled` via `client.aio.interactions.cancel(id)`.
- All 9 `gemini_*_research` modes appear in `thoth modes` and pass `tests/extended/test_model_kind_runtime.py`.
- `_map_gemini_error` discriminates interactions-namespace 404 (gives "interaction expired" hint) from chat-model 404.
- Default test suite green; gated `live_api` workflow green when run manually with `GEMINI_API_KEY`.
- README documents the DR cost callout + 9 new modes.
- All existing tests (P22/P23/P24/P26/P27 paths) continue to pass — no regressions in chat / OpenAI / Perplexity paths.
