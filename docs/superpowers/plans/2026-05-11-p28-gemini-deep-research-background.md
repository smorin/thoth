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

**Spike-driven correction (2026-05-12):** DR exceptions are **NOT** subclasses of `google.genai.errors.APIError` as the original plan assumed. They live in a **separate private hierarchy** at `google.genai._interactions.GeminiNextGenAPIClientError` (with `BadRequestError`, `NotFoundError`, `InternalServerError` subclasses). The existing `_map_gemini_error` will NOT catch them — they will propagate unhandled unless we explicitly add a branch. Use `exc.status_code` (int) — NOT `exc.code` (always `None` for these). See `research/gemini-dr-api-spike-2026-05-11.md` §7 for evidence.

**Catching strategy:** try-import the private module at module load; fall back to duck-type discrimination if the SDK has renamed it (locked by user 2026-05-12).

**Convention reference (P26+P27):** the error mapper stays a single function — no sync/async split since the Interactions API surface is async-only.

**Files:**
- Modify: `src/thoth/providers/gemini.py` (top-of-module imports + `_map_gemini_error`)
- Modify: `tests/test_provider_gemini.py` (add test class)

- [ ] **Step 1: Add try-import + helper at module top**

In `src/thoth/providers/gemini.py`, just below the existing `from google.genai import errors as genai_errors` line, add:

```python
# DR-specific exceptions live in a PRIVATE module (google.genai._interactions)
# that does NOT inherit from google.genai.errors.APIError. Try-import so we
# fail loudly today and degrade gracefully if the SDK ever renames the module.
try:
    from google.genai._interactions import (  # type: ignore[import-not-found]
        GeminiNextGenAPIClientError as _InteractionsAPIError,
    )

    _HAS_INTERACTIONS_ERRORS = True
except ImportError:  # pragma: no cover
    _HAS_INTERACTIONS_ERRORS = False
    _InteractionsAPIError = None  # type: ignore[assignment]


def _is_interactions_error(exc: BaseException) -> bool:
    """True for DR (Interactions API) exceptions, regardless of SDK module path.

    Primary: isinstance check against the imported _InteractionsAPIError. If the
    SDK has renamed the private module since pin-time, fall back to a duck-type
    check (module name + status_code attribute). See spike §7.
    """
    if _HAS_INTERACTIONS_ERRORS and _InteractionsAPIError is not None:
        if isinstance(exc, _InteractionsAPIError):
            return True
    module = type(exc).__module__ or ""
    return module.startswith("google.genai._") and hasattr(exc, "status_code")
```

- [ ] **Step 2: Write failing tests using the actual exception classes from the spike**

Append to `tests/test_provider_gemini.py`:

```python
class TestMapGeminiErrorInteractionsSpecific:
    """Task 2: _map_gemini_error catches google.genai._interactions exceptions."""

    def test_interactions_404_produces_interaction_expired_message(self):
        """interactions.get(bad-id) raises NotFoundError with status_code=404."""
        from google.genai._interactions import NotFoundError  # type: ignore[import-not-found]

        from thoth.providers.gemini import _map_gemini_error

        # Construct a real NotFoundError as the spike observed it.
        # The exact constructor signature is documented in
        # research/gemini-dr-api-spike-2026-05-11.md §7. Use the spike-derived
        # shape — do not invent.
        exc = NotFoundError(
            status_code=404,
            message="Interaction not found: interactions/does-not-exist-spike",
        )
        result = _map_gemini_error(exc, model="deep-research-preview-04-2026")
        msg = str(result)
        assert "interaction" in msg.lower()
        # Must NOT collapse onto the chat-completion 404 message
        assert "Model 'deep-research-preview-04-2026' not found" not in msg

    def test_interactions_400_invalid_key_produces_api_key_error(self):
        """interactions.create with bad key raises BadRequestError with status_code=400."""
        from google.genai._interactions import BadRequestError  # type: ignore[import-not-found]

        from thoth.errors import APIKeyError, ThothError
        from thoth.providers.gemini import _map_gemini_error

        exc = BadRequestError(status_code=400, message="API key not valid")
        result = _map_gemini_error(exc, model="deep-research-preview-04-2026")
        # Either APIKeyError or a ThothError mentioning the AI Studio URL
        assert isinstance(result, (APIKeyError, ThothError))
        if not isinstance(result, APIKeyError):
            assert "aistudio.google.com" in str(result)

    def test_interactions_500_produces_provider_error(self):
        """interactions.{create,get,cancel} 5xx raises InternalServerError."""
        from google.genai._interactions import InternalServerError  # type: ignore[import-not-found]

        from thoth.errors import ProviderError
        from thoth.providers.gemini import _map_gemini_error

        exc = InternalServerError(
            status_code=500, message="Internal server error processing interaction"
        )
        result = _map_gemini_error(exc, model="deep-research-preview-04-2026")
        assert isinstance(result, ProviderError)
        assert "server" in str(result).lower() or "5xx" in str(result).lower()

    def test_duck_type_fallback_when_isinstance_misses(self, monkeypatch):
        """If _InteractionsAPIError isinstance check fails, duck-type still catches.

        Simulates an SDK rename: forge an exception whose module is
        google.genai._interactions but doesn't inherit from our captured class.
        """
        from thoth.errors import ProviderError
        from thoth.providers.gemini import _map_gemini_error

        class _FakeInteractionsError(Exception):
            pass

        # Patch the module path to make duck-type catch it
        _FakeInteractionsError.__module__ = "google.genai._interactions_renamed"
        exc = _FakeInteractionsError("transient outage")
        exc.status_code = 503  # type: ignore[attr-defined]
        result = _map_gemini_error(exc, model="deep-research-preview-04-2026")
        # Falls through to the generic provider error
        assert isinstance(result, ProviderError)
```

- [ ] **Step 3: Run failing tests**

```bash
uv run pytest tests/test_provider_gemini.py::TestMapGeminiErrorInteractionsSpecific -v
```

Expected: 4 FAIL — `_map_gemini_error` doesn't catch `_interactions` exceptions yet.

- [ ] **Step 4: Add the `_is_interactions_error` branch to `_map_gemini_error`**

In `src/thoth/providers/gemini.py:_map_gemini_error`, add a NEW first conditional BEFORE the existing `isinstance(exc, genai_errors.ClientError)` block:

```python
def _map_gemini_error(exc: Exception, model: str | None, verbose: bool = False) -> ThothError:
    # NEW: DR (Interactions API) exceptions are a separate hierarchy.
    if _is_interactions_error(exc):
        status_code = getattr(exc, "status_code", None)
        message = getattr(exc, "message", None) or str(exc) or ""
        msg_lower = message.lower()

        if status_code == 400:
            # Invalid-key paths come through as 400 BadRequest from the
            # interactions endpoint (the chat-completion endpoint returns 401).
            if any(p in msg_lower for p in _INVALID_KEY_PHRASES_GEMINI):
                return _invalid_key_thotherror(
                    "Gemini",
                    "https://aistudio.google.com/app/apikey",
                )
            return ProviderError(_PROVIDER_NAME_GEMINI, f"Bad request: {message}")

        if status_code == 404:
            return ProviderError(
                _PROVIDER_NAME_GEMINI,
                f"Gemini interaction not found or expired: {message}. "
                f"Paid-tier retention is 55 days; free-tier 1 day. Start a new "
                f"operation if the interaction has aged out.",
            )

        if status_code == 429:
            return APIRateLimitError(_PROVIDER_NAME_GEMINI)

        if status_code == 403:
            is_dr_model = model and "deep-research" in str(model).lower()
            if is_dr_model and ("tier" in msg_lower or "paid" in msg_lower or "billing" in msg_lower):
                return ProviderError(
                    _PROVIDER_NAME_GEMINI,
                    f"Gemini Deep Research requires a paid tier (Tier 1+). "
                    f"See https://ai.google.dev/pricing. Original error: {message}",
                )
            return ProviderError(_PROVIDER_NAME_GEMINI, f"Permission denied: {message}")

        if status_code is not None and status_code >= 500:
            return ProviderError(
                _PROVIDER_NAME_GEMINI,
                f"Gemini interactions server error ({status_code}): {message}. "
                f"Retry shortly.",
            )

        # Unknown status_code on a recognised _interactions exception.
        return ProviderError(
            _PROVIDER_NAME_GEMINI,
            f"Gemini interactions API error ({status_code}): {message}",
        )

    # Existing branches follow unchanged: ClientError, ServerError, httpx.*, APIError
    if isinstance(exc, genai_errors.ClientError):
        ...  # P24 code stays
```

- [ ] **Step 5: Run tests until green**

```bash
uv run pytest tests/test_provider_gemini.py::TestMapGeminiErrorInteractionsSpecific -v
```

Expected: 4 PASS. Then run the full provider test file to confirm no regressions:

```bash
uv run pytest tests/test_provider_gemini.py -v
```

Expected: all existing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add src/thoth/providers/gemini.py tests/test_provider_gemini.py
git commit -m "feat(p28): map google.genai._interactions exceptions to ThothError types

Per spike findings (research/gemini-dr-api-spike-2026-05-11.md §7), DR
exceptions raise from google.genai._interactions, a private module that
does NOT inherit from google.genai.errors.APIError. The existing
_map_gemini_error did not catch them.

Adds try-import + duck-type fallback (_is_interactions_error helper)
and a new branch in _map_gemini_error that uses exc.status_code (int)
rather than exc.code (None for this hierarchy). Covers 400 (incl
invalid-key), 403 (incl free-tier-blocked-from-DR), 404 (interaction
expired/not-found), 429 (rate limit), and 5xx. Existing chat-mode
ClientError/ServerError/httpx branches remain unchanged.
"
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

### Task 6: `_deep_research_check_status` — failing tests + baseline mapping

**Spike-driven correction (2026-05-12):** the SDK declares **6** status values, not 4: the type hint on `interaction.status` is `Literal['in_progress', 'requires_action', 'completed', 'failed', 'cancelled', 'incomplete']`. Per spike §5. The mapping decision for `requires_action` and `incomplete` is locked at the v1-conservative defaults below; **Tasks 6a + 6b run follow-up spikes to investigate**, **Task 6c revises the mapping if those spikes find better answers.**

**Failure-type discriminator strategy (locked 2026-05-12):** rather than adding new top-level OperationStatus values (invasive — touches state machine + 7 consumer modules), the provider returns a new failure-type discriminator in the status dict. The runtime translates this into `OperationStatus.failure_type` (existing field at `src/thoth/models.py:125` with `"recoverable" | "permanent" | None`). v1 adds `"requires_action"` as a third failure_type value.

**Baseline mapping table:**

| Gemini status | Provider returns | `OperationStatus.status` (runtime) | `OperationStatus.failure_type` (runtime) | Revisit? |
|---|---|---|---|---|
| `in_progress` | `{"status": "in_progress"}` | `running` | None | — |
| `requires_action` | `{"status": "permanent_error", "failure_type": "requires_action"}` | `failed` | `requires_action` (NEW) | Task 6a |
| `completed` | `{"status": "completed"}` | `completed` | None | — |
| `failed` | `{"status": "permanent_error", "failure_type": "permanent"}` | `failed` | `permanent` | — |
| `cancelled` | `{"status": "cancelled"}` | `cancelled` | None | — |
| `incomplete` | `{"status": "permanent_error", "failure_type": "permanent"}` | `failed` | `permanent` (v1 conservative) | Task 6b |

**Files:**
- Modify: `src/thoth/providers/gemini.py:GeminiProvider`
- Modify: `tests/test_provider_gemini.py`

- [ ] **Step 1: Failing tests (6 status values)**

```python
class TestGeminiDeepResearchCheckStatus:
    """Task 6: _deep_research_check_status polls interactions.get and maps status."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "live_status,expected_thoth_status,expected_failure_type",
        [
            ("in_progress",     "in_progress",     None),
            ("requires_action", "permanent_error", "requires_action"),
            ("completed",       "completed",       None),
            ("failed",          "permanent_error", "permanent"),
            ("cancelled",       "cancelled",       None),
            ("incomplete",      "permanent_error", "permanent"),
        ],
    )
    async def test_status_mapping(self, live_status, expected_thoth_status, expected_failure_type):
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
        if expected_failure_type is None:
            assert "failure_type" not in result or result["failure_type"] is None
        else:
            assert result["failure_type"] == expected_failure_type
        # raw_status always preserved for diagnostics
        assert result["raw_status"] == live_status

    @pytest.mark.asyncio
    async def test_requires_action_error_message_explains_v1_unsupported(self):
        """requires_action is rare for the 9 gemini_*_research modes; if it fires,
        the user needs a clear message about what happened."""
        from thoth.providers.gemini import GeminiProvider

        provider = GeminiProvider(
            api_key="dummy", config={"model": "deep-research-preview-04-2026"}
        )
        provider.jobs["interactions/abc"] = {"kind": "deep_research", "interaction_id": "interactions/abc"}
        fake_get = AsyncMock(return_value=MagicMock(status="requires_action"))
        provider.client.aio.interactions = MagicMock()
        provider.client.aio.interactions.get = fake_get
        result = await provider._deep_research_check_status("interactions/abc")
        assert "requires_action" in result["failure_type"]
        assert "approval" in result["error"].lower() or "action" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_incomplete_error_message_documents_v1_limitation(self):
        """incomplete may be refetchable (Task 6b spike investigates).
        v1 treats as permanent failure; document this in the error message."""
        from thoth.providers.gemini import GeminiProvider

        provider = GeminiProvider(
            api_key="dummy", config={"model": "deep-research-preview-04-2026"}
        )
        provider.jobs["interactions/abc"] = {"kind": "deep_research", "interaction_id": "interactions/abc"}
        fake_get = AsyncMock(return_value=MagicMock(status="incomplete"))
        provider.client.aio.interactions = MagicMock()
        provider.client.aio.interactions.get = fake_get
        result = await provider._deep_research_check_status("interactions/abc")
        assert "incomplete" in result["error"].lower() or "truncated" in result["error"].lower()

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

- [ ] **Step 2: Implement with 6-value mapping**

```python
# Status mapping table at module top (just below the constants block):
_DR_STATUS_MAPPING: dict[str, dict[str, Any]] = {
    "in_progress":     {"status": "in_progress"},
    "completed":       {"status": "completed"},
    "cancelled":       {"status": "cancelled"},
    "failed":          {"status": "permanent_error", "failure_type": "permanent"},
    "requires_action": {
        "status": "permanent_error",
        "failure_type": "requires_action",
        "error": (
            "Gemini interaction is waiting on tool or human approval "
            "(status='requires_action'). This flow is not supported in "
            "P28 v1; the 9 gemini_*_research modes do not request tool "
            "approval. If you see this, please file a bug. See plan v2 "
            "Task 6a for the follow-up spike investigating trigger conditions."
        ),
    },
    "incomplete": {
        "status": "permanent_error",
        "failure_type": "permanent",
        "error": (
            "Gemini Deep Research returned status='incomplete' — the run "
            "finished but output may be truncated. P28 v1 treats this as "
            "a permanent failure conservatively. Re-run the prompt if the "
            "report is needed. Plan v2 Task 6b investigates whether refetch "
            "is possible (may flip this to recoverable in v1.1)."
        ),
    },
}


async def _deep_research_check_status(self, job_id: str) -> dict[str, Any]:
    """Poll interactions.get; map Gemini status to Thoth status + failure_type.

    SDK declares 6 statuses (spike §5). v1 mapping is conservative for
    requires_action and incomplete; Tasks 6a/6b spike + 6c revise.
    """
    if job_id not in self.jobs:
        return {"status": "not_found", "error": f"Unknown job_id: {job_id}"}
    try:
        interaction = await self.client.aio.interactions.get(id=job_id)
    except Exception as e:
        mapped = _map_gemini_error(e, self.model)
        if _is_retryable_gemini_exception(e):
            return {"status": "transient_error", "error": str(mapped)}
        return {"status": "permanent_error", "failure_type": "permanent", "error": str(mapped)}

    live = str(getattr(interaction, "status", "in_progress"))
    self.jobs[job_id]["last_status"] = live
    self.jobs[job_id]["last_interaction"] = interaction

    # Default fallthrough for unknown future SDK status values.
    mapped = _DR_STATUS_MAPPING.get(
        live, {"status": "in_progress"}  # treat unknown as still running
    )
    return {**mapped, "raw_status": live}
```

- [ ] **Step 3: Run + commit**

```bash
uv run pytest tests/test_provider_gemini.py::TestGeminiDeepResearchCheckStatus -v
git add -A && git commit -m "feat(p28): implement _deep_research_check_status with 6-value mapping

Maps the SDK's 6 status values (in_progress, requires_action, completed,
failed, cancelled, incomplete) to Thoth provider-status + failure_type
discriminator. v1 conservatively treats requires_action and incomplete
as permanent_error; Tasks 6a/6b spike further to determine if better
handling is warranted (Task 6c may revise the mapping)."
```

---

### Task 6a: SPIKE — investigate `requires_action` trigger conditions

**Why this task exists:** `requires_action` is in the SDK type hint but absent from public Interactions API docs. We need to know when it appears (tool-approval flows, content-filter trips, quota interruptions, other) so v1.1 can implement proper recovery if warranted. Live-API spend authorized.

**Files:**
- Create: `scripts/spike/p28/spike_dr_requires_action.py`
- Modify: `research/gemini-dr-api-spike-2026-05-11.md` (add §6a section)

- [ ] **Step 1: Write the spike script**

The script attempts to deliberately trigger `requires_action` by:
1. Submitting a DR with `tools=[{"type": "code_execution"}]` (a tool that arguably could need approval)
2. Submitting with `agent_config={"collaborative_planning": True}` (the docs mention collaborative planning)
3. Submitting with content that might trigger filter/safety review (e.g., a prompt about a controversial topic, carefully chosen not to violate policy)
4. Polling each interaction; logging every transition. Capture full response shape if `requires_action` appears.

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["google-genai>=1.74.0"]
# ///
"""P28 Task 6a spike: trigger requires_action and capture payload shape.

Outputs to research/_dr_spike_requires_action.json + _dr_spike_requires_action.txt.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

from google import genai

AGENT = "deep-research-preview-04-2026"
OUT_DIR = Path(__file__).parent.parent.parent.parent / "research"

PROBES = [
    # Probe 1: tool that may require approval
    {
        "label": "tool_code_execution",
        "input": "Run a quick Python computation to estimate pi via Monte Carlo with 10k samples.",
        "extra": {"tools": [{"type": "code_execution"}]},
    },
    # Probe 2: collaborative_planning enabled
    {
        "label": "collaborative_planning",
        "input": "Plan a 3-paper literature review on consensus algorithms.",
        "extra": {"agent_config": {"type": "deep-research", "collaborative_planning": True}},
    },
    # Probe 3: file_search tool (experimental per docs)
    {
        "label": "tool_file_search",
        "input": "Search any uploaded files for distributed-systems content.",
        "extra": {"tools": [{"type": "file_search"}]},
    },
]


async def submit_and_poll(client, label, input_str, extra):
    print(f"\n--- Probe: {label} ---")
    try:
        kwargs = {"agent": AGENT, "input": input_str, "background": True, "store": True, **extra}
        resp = await client.aio.interactions.create(**kwargs)
    except Exception as exc:
        print(f"  CREATE FAILED: {type(exc).__name__}({getattr(exc, 'status_code', '?')}): {exc}")
        return {"label": label, "create_error": f"{type(exc).__name__}: {exc}"}
    interaction_id = getattr(resp, "id", None)
    print(f"  submitted; id={interaction_id}")
    deadline = time.monotonic() + 10 * 60  # 10 min cap per probe
    transitions = []
    last = None
    captured_payload = None
    while time.monotonic() < deadline:
        await asyncio.sleep(5)
        try:
            interaction = await client.aio.interactions.get(id=interaction_id)
        except Exception as exc:
            transitions.append({"t": time.monotonic(), "error": f"{type(exc).__name__}: {exc}"})
            continue
        status = str(getattr(interaction, "status", "?"))
        if status != last:
            print(f"    status -> {status!r}")
            transitions.append({"t": time.monotonic(), "status": status})
            last = status
        if status == "requires_action":
            captured_payload = repr(interaction)[:5000]
            print(f"    !!! captured requires_action payload (5000 char preview)")
            break
        if status in {"completed", "failed", "cancelled", "incomplete"}:
            break
    return {
        "label": label,
        "interaction_id": interaction_id,
        "transitions": transitions,
        "final_status": last,
        "captured_payload": captured_payload,
    }


async def main_async() -> int:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not set", file=sys.stderr)
        return 2
    client = genai.Client(api_key=api_key)
    results = []
    for probe in PROBES:
        results.append(await submit_and_poll(client, **probe))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "_dr_spike_requires_action.json").write_text(json.dumps(results, indent=2))
    triggered = [r for r in results if "requires_action" in (r.get("captured_payload") or "")]
    print(f"\n=== SUMMARY ===")
    print(f"Probes run: {len(results)}; requires_action triggered: {len(triggered)}")
    return 0


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run the spike (live API, user-authorized)**

```bash
uv run scripts/spike/p28/spike_dr_requires_action.py 2>&1 | tee research/_dr_spike_requires_action.txt
```

Expected: 3 probes run; one or zero trigger requires_action. ~$2-5 wall spend.

- [ ] **Step 3: Update findings doc §6a**

Add a §6a section to `research/gemini-dr-api-spike-2026-05-11.md`:

```markdown
## §6a `requires_action` trigger conditions (Task 6a)

**Probes run:** 3 — tool=code_execution, collaborative_planning=True, tool=file_search.
**`requires_action` observed:** [yes for probe N | no in any probe].

If observed: document the captured payload shape (top-level attrs, what
field tells the caller what action is needed). If not observed: document
that requires_action is rare in the explored configuration space and may
require manual triggers we couldn't construct. Either way, the v1 mapping
(permanent_error + failure_type=requires_action with clear error message)
remains correct; Task 6c may upgrade based on findings.
```

- [ ] **Step 4: Commit**

```bash
git add scripts/spike/p28/spike_dr_requires_action.py research/_dr_spike_requires_action.* research/gemini-dr-api-spike-2026-05-11.md
git commit -m "spike(p28): investigate requires_action trigger conditions"
```

(commitlint allows `chore` not `spike`; use `chore(p28):` if commitlint complains.)

---

### Task 6b: SPIKE — investigate `incomplete` recoverability

**Why this task exists:** the SDK type hint exposes `incomplete` but the docs don't describe what it means. We need to know whether the work is genuinely lost (treat as permanent) or whether `interactions.get()` after `incomplete` can continue/refetch the rest (treat as recoverable, plug into the existing resume flow). Live-API spend authorized.

**Files:**
- Create: `scripts/spike/p28/spike_dr_incomplete.py`
- Modify: `research/gemini-dr-api-spike-2026-05-11.md` (add §6b)

- [ ] **Step 1: Write the spike script**

Trigger `incomplete` deliberately by exhausting the 60-min hard cap or by submitting near-quota-exhaustion. A reliable trigger is hard — alternative: probe `interactions.get()` and `interactions.<other_method>` to see if there's a `continue`/`resume` method even before observing `incomplete` in the wild.

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["google-genai>=1.74.0"]
# ///
"""P28 Task 6b spike: investigate incomplete recoverability.

Two probes:
1. Surface probe — does the SDK have a continue() or resume() method on
   interactions? If yes, recovery is likely possible.
2. Trigger probe — submit a deliberately near-budget DR prompt to try to
   trigger 'incomplete' (60-min hard cap from spike §3). May not actually
   trigger; that's fine — surface probe alone is informative.

Outputs to research/_dr_spike_incomplete.json + _dr_spike_incomplete.txt.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import os
import sys
import time
from pathlib import Path

from google import genai

AGENT = "deep-research-preview-04-2026"
OUT_DIR = Path(__file__).parent.parent.parent.parent / "research"


async def surface_probe(client) -> dict:
    print("=== Surface probe: methods available on client.aio.interactions ===")
    methods = [m for m in dir(client.aio.interactions) if not m.startswith("_")]
    print(f"  methods: {methods}")
    # Look for continue/resume/refetch-shaped methods
    candidates = [m for m in methods if any(s in m.lower() for s in ("continue", "resume", "refetch", "retry"))]
    print(f"  candidates for recovery: {candidates or 'NONE'}")
    # Inspect signatures of all methods
    sigs = {}
    for m in methods:
        attr = getattr(client.aio.interactions, m)
        try:
            sigs[m] = str(inspect.signature(attr))
        except (TypeError, ValueError):
            sigs[m] = "<no signature>"
    return {"methods": methods, "recovery_candidates": candidates, "signatures": sigs}


async def trigger_probe(client) -> dict:
    print("\n=== Trigger probe: attempt to elicit 'incomplete' ===")
    # Very-broad prompt to consume the 60-min cap and possibly truncate.
    prompt = (
        "Provide an exhaustive analysis of every published consensus algorithm "
        "from 1980 to 2025, including formal correctness proofs, network "
        "assumptions, performance benchmarks across at least 10 deployments "
        "each, and a comparative matrix with citations. Be maximally thorough."
    )
    try:
        resp = await client.aio.interactions.create(
            agent=AGENT, input=prompt, background=True, store=True
        )
    except Exception as exc:
        return {"create_error": f"{type(exc).__name__}: {exc}"}
    interaction_id = getattr(resp, "id", None)
    print(f"  submitted overscoped prompt; id={interaction_id}")
    deadline = time.monotonic() + 65 * 60  # 65 min (just past hard cap)
    transitions: list[dict] = []
    last = None
    final_interaction = None
    while time.monotonic() < deadline:
        await asyncio.sleep(15)
        try:
            interaction = await client.aio.interactions.get(id=interaction_id)
        except Exception as exc:
            transitions.append({"t": time.monotonic(), "error": f"{type(exc).__name__}: {exc}"})
            continue
        status = str(getattr(interaction, "status", "?"))
        if status != last:
            print(f"    status -> {status!r}")
            transitions.append({"t": time.monotonic(), "status": status})
            last = status
        if status in {"completed", "failed", "cancelled", "incomplete"}:
            final_interaction = interaction
            break
    payload = repr(final_interaction)[:5000] if final_interaction is not None else None
    return {
        "interaction_id": interaction_id,
        "transitions": transitions,
        "final_status": last,
        "final_payload_preview": payload,
    }


async def main_async() -> int:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not set", file=sys.stderr)
        return 2
    client = genai.Client(api_key=api_key)
    results = {
        "surface": await surface_probe(client),
        "trigger": await trigger_probe(client),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "_dr_spike_incomplete.json").write_text(json.dumps(results, indent=2, default=str))
    print(f"\n=== SUMMARY ===")
    print(f"recovery_candidates: {results['surface']['recovery_candidates']}")
    print(f"trigger final_status: {results['trigger'].get('final_status')}")
    return 0


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run the spike (live API, user-authorized)**

```bash
uv run scripts/spike/p28/spike_dr_incomplete.py 2>&1 | tee research/_dr_spike_incomplete.txt
```

Wall time: up to 65 min for the trigger probe. ~$3-7 wall spend.

- [ ] **Step 3: Update findings doc §6b**

Add a §6b section with concrete findings: methods available, whether recovery candidates exist, whether `incomplete` was observed and its payload shape.

- [ ] **Step 4: Commit**

```bash
git add scripts/spike/p28/spike_dr_incomplete.py research/_dr_spike_incomplete.* research/gemini-dr-api-spike-2026-05-11.md
git commit -m "spike(p28): investigate incomplete recoverability"
```

---

### Task 6c: Revise `_deep_research_check_status` mapping per 6a/6b findings

**Pre-condition:** Tasks 6a and 6b have committed their findings to `research/gemini-dr-api-spike-2026-05-11.md` §6a and §6b.

**Decision tree:**

- If §6b found a recovery method (e.g., `interactions.continue(id)` or similar): flip `incomplete` mapping to `failure_type="recoverable"` and verify the resume flow auto-retriggers via the existing `failure_type=recoverable` state-machine transition (`failed → running`).
- If §6b found no recovery method: keep `failure_type="permanent"` and update the error message to be definitive ("output is lost, re-run from scratch").
- If §6a captured a `requires_action` payload with a `respond()` or similar method: add a clear "this can be auto-handled in v1.1" note to the error message. v1 still treats as permanent.
- If §6a did NOT trigger `requires_action`: tighten the error message to explicitly say "this state is rare and unexpected for gemini_*_research modes — please file a bug if encountered."

- [ ] **Step 1: Apply mapping revisions per findings**

Update `_DR_STATUS_MAPPING` in `src/thoth/providers/gemini.py` and the corresponding test parametrize values in `tests/test_provider_gemini.py`. Diff size depends on findings.

- [ ] **Step 2: Run tests until green**

```bash
uv run pytest tests/test_provider_gemini.py::TestGeminiDeepResearchCheckStatus -v
```

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "feat(p28): revise DR status mapping per 6a/6b spike findings

[describe the actual changes based on what 6a/6b found]"
```

---

### Task 7: `_deep_research_get_result` — failing tests + implementation

**Spike-driven correction (2026-05-12):** the citation extraction path the original plan assumed was wrong. Per spike §4:

- **Path is `interaction.steps[N].content[0].annotations[]`** (where `N` is the index of the first `model_output` step), NOT `interaction.outputs[-1].annotations[]`. The `outputs` field does not exist on DR responses.
- **Attribute name is `annotations`**, not `citations`.
- **Only the first `model_output` step's `content[0]` carries them.** Subsequent `model_output` steps don't.
- Each annotation is a `URLCitation` with shape: `{type: 'url_citation', __type__: 'URLCitation', start_index: int, end_index: int, title: None, url: <Vertex AI redirect URL>}`.
- **`title` is always `None`** in observed responses.
- **`url` is a Vertex AI grounding redirect**, not the original source URL.
- The **last step** (`step[-1].content[0].text`) contains a **rendered "Sources" block** with `[domain](redirect-url)` markdown — the SDK's own attempt at human-readable display, with domains parsed from the redirect targets.

**Citation rendering strategy (locked by user 2026-05-12 — "layered"):**

1. **Parse the SDK's rendered Sources block** from `step[-1].content[0].text` into a `url → domain` map.
2. **Follow each redirect URL** (HEAD request, bounded concurrency, 2s per-request timeout) to extract the real source URL.
3. **Title derivation chain:** parsed_sources.get(redirect_url) → urlparse(source_url).netloc → URL string itself.
4. **Link target:** source URL (post-redirect) if redirect-follow succeeded; otherwise the redirect URL.
5. **Failure modes:** if SDK Sources block parse fails, fall through to `urlparse(source).netloc`; if all redirects time out, citations still render with the redirect URLs as both title and link target.

**Files:**
- Modify: `src/thoth/providers/gemini.py:GeminiProvider` (add helpers + method)
- Modify: `tests/test_provider_gemini.py` (add test class)

- [ ] **Step 1: Add helper functions at module bottom (below GeminiProvider class)**

Following P27 convention (helpers below the class — see `perplexity.py:873-979`):

```python
# --- DR citation rendering helpers (P28) ---

import re
import asyncio as _asyncio_for_helpers  # already imported at top; alias avoids confusion

_DR_SOURCES_BLOCK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_DR_REDIRECT_PREFIXES: tuple[str, ...] = (
    "https://vertexaisearch.cloud.google.com/grounding-api-redirect/",
)


def _parse_sdk_sources_block(text: str | None) -> dict[str, str]:
    """Parse the SDK's rendered Sources block into {url: domain_title}.

    The SDK's last step typically contains markdown like:
        [usenix.org](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZ...)
        [arxiv.org](https://vertexaisearch.cloud.google.com/grounding-api-redirect/BXK...)
    Returns a dict mapping each redirect URL to the SDK-extracted domain label.
    Empty dict on parse failure or no matches.
    """
    if not text:
        return {}
    return {url: title for title, url in _DR_SOURCES_BLOCK_RE.findall(text)}


def _is_dr_redirect(url: str) -> bool:
    return any(url.startswith(p) for p in _DR_REDIRECT_PREFIXES)


async def _follow_dr_redirect(
    url: str, *, timeout_s: float = 2.0, client: httpx.AsyncClient | None = None
) -> str | None:
    """Follow a Vertex AI grounding redirect to extract the source URL.

    Returns the final URL on success, None on any failure (timeout, error,
    non-redirect response). The caller is responsible for falling back to
    the redirect URL when None is returned.
    """
    if not _is_dr_redirect(url):
        return url
    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=timeout_s, follow_redirects=False)
    try:
        resp = await client.head(url, follow_redirects=False)
        location = resp.headers.get("Location") or resp.headers.get("location")
        return location if location else None
    except (httpx.RequestError, httpx.HTTPStatusError):
        return None
    finally:
        if owns_client:
            await client.aclose()


async def _resolve_dr_redirects(
    urls: list[str], *, concurrency: int = 10, timeout_s: float = 2.0
) -> dict[str, str | None]:
    """Bounded-concurrency redirect resolution for a list of URLs.

    Returns {original_url: resolved_url_or_None}. Designed for the ~85 citations
    per DR result observed in the spike; ~17s worst-case at 10 concurrent + 2s
    timeout. Caller can ignore None entries and fall back to original_url.
    """
    sem = _asyncio_for_helpers.Semaphore(concurrency)

    async def _one(client: httpx.AsyncClient, u: str) -> tuple[str, str | None]:
        async with sem:
            return u, await _follow_dr_redirect(u, timeout_s=timeout_s, client=client)

    async with httpx.AsyncClient(timeout=timeout_s, follow_redirects=False) as client:
        results = await _asyncio_for_helpers.gather(
            *(_one(client, u) for u in urls), return_exceptions=False
        )
    return dict(results)
```

- [ ] **Step 2: Write failing tests using the spike-correct shape**

Append to `tests/test_provider_gemini.py`:

```python
class TestGeminiDeepResearchGetResult:
    """Task 7: _deep_research_get_result with layered citation rendering.

    Citation shape per spike §4:
      - Path: interaction.steps[N].content[0].annotations[]
      - URLCitation has {type, start_index, end_index, title=None, url=<redirect>}
      - Only the first model_output step carries annotations
      - Last step's content[0].text has the rendered [domain](url) Sources block
    """

    @pytest.mark.asyncio
    async def test_renders_model_output_text(self):
        from thoth.providers.gemini import GeminiProvider

        provider = GeminiProvider(
            api_key="dummy", config={"model": "deep-research-preview-04-2026"}
        )
        text_item = MagicMock(type="text", text="The three papers are...", annotations=[])
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
    async def test_extracts_annotations_from_first_model_output_step(self, monkeypatch):
        """Citation extraction follows the spike-validated path."""
        from thoth.providers.gemini import GeminiProvider

        provider = GeminiProvider(
            api_key="dummy", config={"model": "deep-research-preview-04-2026"}
        )
        # Real shape: URLCitation has title=None, url=<redirect>
        ann = MagicMock(
            type="url_citation",
            title=None,
            url="https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZ123",
            start_index=0,
            end_index=10,
        )
        text_item = MagicMock(type="text", text="Body", annotations=[ann])
        model_output_step = MagicMock(type="model_output", content=[text_item])
        # Last step has the SDK-rendered Sources block we parse for domains
        sources_text = (
            "**Sources:**\n\n"
            "- [usenix.org](https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZ123)\n"
        )
        sources_item = MagicMock(type="text", text=sources_text, annotations=[])
        sources_step = MagicMock(type="model_output", content=[sources_item])
        fake_interaction = MagicMock(status="completed", steps=[model_output_step, sources_step])
        provider.jobs["interactions/abc"] = {
            "kind": "deep_research",
            "interaction_id": "interactions/abc",
            "last_interaction": fake_interaction,
        }
        # Patch redirect follow to return a fake source URL (no real network)
        async def fake_resolve(urls, **kwargs):
            return {u: "https://www.usenix.org/paper.pdf" for u in urls}

        monkeypatch.setattr("thoth.providers.gemini._resolve_dr_redirects", fake_resolve)

        result = await provider._deep_research_get_result("interactions/abc", False)
        assert "## Sources" in result
        assert "usenix.org" in result  # title from parsed SDK Sources block
        # Link target should be the resolved source URL (per layered strategy)
        assert "https://www.usenix.org/paper.pdf" in result

    @pytest.mark.asyncio
    async def test_falls_back_to_redirect_url_when_follow_fails(self, monkeypatch):
        """If redirect-follow returns None, render the redirect URL as link target."""
        from thoth.providers.gemini import GeminiProvider

        provider = GeminiProvider(
            api_key="dummy", config={"model": "deep-research-preview-04-2026"}
        )
        redirect_url = "https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZ123"
        ann = MagicMock(type="url_citation", title=None, url=redirect_url, start_index=0, end_index=10)
        text_item = MagicMock(type="text", text="Body", annotations=[ann])
        model_output_step = MagicMock(type="model_output", content=[text_item])
        fake_interaction = MagicMock(status="completed", steps=[model_output_step])
        provider.jobs["interactions/abc"] = {
            "kind": "deep_research",
            "interaction_id": "interactions/abc",
            "last_interaction": fake_interaction,
        }
        async def fake_resolve(urls, **kwargs):
            return {u: None for u in urls}  # simulate redirect-follow failures

        monkeypatch.setattr("thoth.providers.gemini._resolve_dr_redirects", fake_resolve)

        result = await provider._deep_research_get_result("interactions/abc", False)
        assert "## Sources" in result
        # Should contain the redirect URL since follow failed
        assert redirect_url in result

    @pytest.mark.asyncio
    async def test_no_sources_block_when_no_annotations(self):
        from thoth.providers.gemini import GeminiProvider

        provider = GeminiProvider(
            api_key="dummy", config={"model": "deep-research-preview-04-2026"}
        )
        text_item = MagicMock(type="text", text="Body without sources", annotations=[])
        model_output_step = MagicMock(type="model_output", content=[text_item])
        fake_interaction = MagicMock(status="completed", steps=[model_output_step])
        provider.jobs["interactions/abc"] = {
            "kind": "deep_research",
            "interaction_id": "interactions/abc",
            "last_interaction": fake_interaction,
        }
        result = await provider._deep_research_get_result("interactions/abc", False)
        assert "## Sources" not in result

    @pytest.mark.asyncio
    async def test_dedupes_by_resolved_url(self, monkeypatch):
        """Two redirects pointing to the same source dedupe to one entry."""
        from thoth.providers.gemini import GeminiProvider

        provider = GeminiProvider(
            api_key="dummy", config={"model": "deep-research-preview-04-2026"}
        )
        ann1 = MagicMock(
            type="url_citation", title=None,
            url="https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZ123",
            start_index=0, end_index=10,
        )
        ann2 = MagicMock(
            type="url_citation", title=None,
            url="https://vertexaisearch.cloud.google.com/grounding-api-redirect/BXK456",
            start_index=20, end_index=30,
        )
        text_item = MagicMock(type="text", text="Body", annotations=[ann1, ann2])
        model_output_step = MagicMock(type="model_output", content=[text_item])
        fake_interaction = MagicMock(status="completed", steps=[model_output_step])
        provider.jobs["interactions/abc"] = {
            "kind": "deep_research",
            "interaction_id": "interactions/abc",
            "last_interaction": fake_interaction,
        }
        async def fake_resolve(urls, **kwargs):
            # Both redirects resolve to the SAME source — should dedupe
            return {u: "https://www.usenix.org/paper.pdf" for u in urls}

        monkeypatch.setattr("thoth.providers.gemini._resolve_dr_redirects", fake_resolve)

        result = await provider._deep_research_get_result("interactions/abc", False)
        # The single deduplicated source appears exactly once in the Sources block
        assert result.count("https://www.usenix.org/paper.pdf") == 1
```

Run, expect FAIL.

- [ ] **Step 3: Implement `_deep_research_get_result`**

```python
async def _deep_research_get_result(self, job_id: str, verbose: bool = False) -> str:
    """Render the completed interaction as markdown text + ## Sources.

    Citation extraction per spike §4 (locked 2026-05-12, "layered" strategy):
      1. Walk interaction.steps[] looking for step.type='model_output'.
      2. For each, walk content[].annotations[] to collect URLCitation entries.
      3. Parse the LAST step's text for the SDK-rendered Sources block (gives
         domain titles for the Vertex AI redirect URLs).
      4. Bounded-concurrency HEAD-follow each redirect URL to extract source URL.
      5. Render via render_sources_block; link target = source URL when resolved,
         redirect URL otherwise.
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

    # Pass 1: collect text from all model_output steps + annotations from each.
    text_parts: list[str] = []
    raw_annotations: list[Any] = []
    last_step_text: str | None = None
    for step in steps:
        if str(getattr(step, "type", "")) != "model_output":
            continue
        content = getattr(step, "content", None) or []
        for item in content:
            text = getattr(item, "text", None) or ""
            if text:
                text_parts.append(text)
                last_step_text = text  # tracks the most recent rendered text
            anns = getattr(item, "annotations", None) or []
            raw_annotations.extend(anns)

    # Pass 2: derive title-lookup map from the SDK-rendered Sources block.
    parsed_sources = _parse_sdk_sources_block(last_step_text)

    # Pass 3: resolve redirect URLs in bounded-concurrency parallel.
    redirect_urls = [
        getattr(a, "url", None) for a in raw_annotations if getattr(a, "url", None)
    ]
    resolved = await _resolve_dr_redirects(redirect_urls) if redirect_urls else {}

    # Pass 4: assemble Citation list with title derivation + final URL choice + dedupe.
    citations: list[Citation] = []
    seen_final_urls: set[str] = set()
    for ann in raw_annotations:
        redirect_url = getattr(ann, "url", None)
        if not redirect_url:
            continue
        resolved_url = resolved.get(redirect_url)
        final_url = resolved_url or redirect_url
        if final_url in seen_final_urls:
            continue
        seen_final_urls.add(final_url)
        # Title derivation chain
        title = parsed_sources.get(redirect_url)
        if not title and resolved_url:
            title = urlparse(resolved_url).netloc or None
        if not title:
            title = urlparse(redirect_url).netloc or redirect_url
        citations.append(Citation(title=str(title), url=str(final_url)))

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

- [ ] **Step 4: Run + commit**

```bash
uv run pytest tests/test_provider_gemini.py::TestGeminiDeepResearchGetResult -v
git add -A && git commit -m "feat(p28): _deep_research_get_result with layered citation rendering

Per spike §4 + user-locked strategy (2026-05-12):
- Reads interaction.steps[].content[].annotations[] (not outputs[-1])
- Parses SDK's rendered Sources block from last step for domain titles
- Bounded-concurrency HEAD-follow on Vertex AI redirect URLs (10 concurrent,
  2s timeout each) to extract real source URLs
- Title-derivation chain: parsed_sources -> urlparse(source).netloc -> URL
- Dedupes by final resolved URL
- Falls back to redirect URL if follow fails — citations still render"
```

---

### Task 8a: SPIKE — re-verify cancel against a properly-sized DR task

**Why this task exists:** Task 1 spike step 4 confirmed `client.aio.interactions.cancel()` exists on the SDK, but the cancel test returned HTTP 500 — and subsequent `interactions.get()` on the same interaction also returned 500. The cause is ambiguous: the spike used a deliberately overscoped prompt that may have triggered server-side capacity rejection *before* cancel was called. Per user clarification (2026-05-12): "make sure the prompt is big enough because calling cancel on a prompt that already ran might cause the 500."

This task re-runs the cancel test with a **Goldilocks prompt** (substantial enough to keep DR running for 3-10 minutes, NOT so overscoped it triggers server rejection), uses a **wait-then-poll-then-cancel** pattern to confirm `in_progress` before cancelling, and verifies the cancel return path + terminal state transition + partial-output preservation.

**Files:**
- Create: `scripts/spike/p28/spike_dr_cancel_v2.py`
- Modify: `research/gemini-dr-api-spike-2026-05-11.md` (add §6 update — replace v1 finding with v2 verification)

- [ ] **Step 1: Write the v2 cancel spike**

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["google-genai>=1.74.0"]
# ///
"""P28 Task 8a spike: re-verify cancel() with a properly-sized DR task.

v1 (Task 1 step 4) used an overscoped prompt and got HTTP 500 — ambiguous
whether cancel itself broke or whether the server rejected the request
before cancel was called. v2 uses a Goldilocks prompt and a
wait-then-poll-then-cancel pattern.

Outputs to research/_dr_spike_cancel_v2.json + _dr_spike_cancel_v2.txt.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

from google import genai

AGENT = "deep-research-preview-04-2026"
# Goldilocks prompt: substantial enough for ~3-10 min runtime, not so
# overscoped it triggers server rejection.
PROMPT = (
    "Provide a comprehensive technical comparison of Paxos, Raft, and "
    "Viewstamped Replication consensus algorithms. Cover protocol mechanics, "
    "failure handling, leader election, log replication, and 3+ real-world "
    "deployments of each. Cite sources."
)
OUT = Path(__file__).parent.parent.parent.parent / "research" / "_dr_spike_cancel_v2.json"


async def main_async() -> int:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not set", file=sys.stderr)
        return 2
    client = genai.Client(api_key=api_key)

    print("Submitting Goldilocks DR task...")
    try:
        resp = await client.aio.interactions.create(
            agent=AGENT, input=PROMPT, background=True, store=True
        )
    except Exception as exc:
        print(f"  CREATE FAILED: {type(exc).__name__}: {exc}")
        return 1
    interaction_id = getattr(resp, "id", None)
    print(f"  id={interaction_id}")

    # Wait-then-poll: confirm the interaction is actually IN_PROGRESS before
    # cancelling. Cancelling an already-completed/failed interaction may be
    # what caused the v1 500.
    print("Waiting + polling for in_progress confirmation (5 attempts, 3s apart)...")
    pre_cancel_status = None
    for attempt in range(5):
        await asyncio.sleep(3)
        try:
            interaction = await client.aio.interactions.get(id=interaction_id)
            pre_cancel_status = str(getattr(interaction, "status", "?"))
            print(f"  attempt {attempt + 1}: status={pre_cancel_status!r}")
            if pre_cancel_status == "in_progress":
                break
        except Exception as exc:
            print(f"  attempt {attempt + 1}: GET error {type(exc).__name__}: {exc}")
    if pre_cancel_status != "in_progress":
        print(f"  Interaction never reached in_progress (saw: {pre_cancel_status!r}); aborting")
        return 1

    print("\nCalling cancel() on confirmed-in_progress interaction...")
    cancel_t0 = time.monotonic()
    cancel_outcome: dict = {}
    try:
        cancel_result = await client.aio.interactions.cancel(id=interaction_id)
        cancel_outcome = {
            "succeeded": True,
            "duration_s": time.monotonic() - cancel_t0,
            "result_type": type(cancel_result).__name__,
            "result_repr": repr(cancel_result)[:500],
        }
        print(f"  cancel returned in {cancel_outcome['duration_s']:.2f}s")
    except Exception as exc:
        cancel_outcome = {
            "succeeded": False,
            "duration_s": time.monotonic() - cancel_t0,
            "exception_type": type(exc).__name__,
            "exception_module": type(exc).__module__,
            "status_code": getattr(exc, "status_code", None),
            "message": str(exc)[:500],
        }
        print(f"  cancel FAILED: {type(exc).__name__}({getattr(exc, 'status_code', '?')}): {exc}")

    # Post-cancel: poll for terminal state, check if partial output preserved.
    print("\nPolling for post-cancel terminal state (up to 90s)...")
    transitions = [{"t": 0.0, "status": pre_cancel_status}]
    final_interaction = None
    deadline = time.monotonic() + 90
    last_observed = pre_cancel_status
    while time.monotonic() < deadline:
        await asyncio.sleep(5)
        try:
            interaction = await client.aio.interactions.get(id=interaction_id)
            status = str(getattr(interaction, "status", "?"))
            if status != last_observed:
                print(f"  status -> {status!r}")
                transitions.append({"t": time.monotonic(), "status": status})
                last_observed = status
            if status in {"cancelled", "completed", "failed", "incomplete"}:
                final_interaction = interaction
                break
        except Exception as exc:
            print(f"  post-cancel GET error: {type(exc).__name__}({getattr(exc, 'status_code', '?')}): {exc}")
            transitions.append({"t": time.monotonic(), "error": f"{type(exc).__name__}: {exc}"})
            break

    partial_output_present = False
    if final_interaction is not None:
        steps = getattr(final_interaction, "steps", None) or []
        partial_output_present = any(
            getattr(s, "content", None) for s in steps if str(getattr(s, "type", "")) == "model_output"
        )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "interaction_id": interaction_id,
        "pre_cancel_status": pre_cancel_status,
        "cancel_outcome": cancel_outcome,
        "post_cancel_transitions": transitions,
        "final_status": last_observed,
        "partial_output_present": partial_output_present,
    }, indent=2, default=str))
    print(f"\n=== SUMMARY ===")
    print(f"Pre-cancel status: {pre_cancel_status}")
    print(f"Cancel succeeded: {cancel_outcome.get('succeeded')}")
    print(f"Final status: {last_observed}")
    print(f"Partial output preserved: {partial_output_present}")
    return 0


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run the spike (live API, user-authorized)**

```bash
uv run scripts/spike/p28/spike_dr_cancel_v2.py 2>&1 | tee research/_dr_spike_cancel_v2.txt
```

Wall time: ~2-3 min (Goldilocks prompt; cancel called early). Spend: ~$0.10-0.30.

- [ ] **Step 3: Update findings doc §6**

Update `research/gemini-dr-api-spike-2026-05-11.md` §6 to REPLACE the v1 inconclusive finding with the v2 evidence:

```markdown
## §6 Cancel behavior (v2 — re-verified 2026-05-12)

v1 inconclusive finding (overscoped prompt → 500) superseded.

v2 setup: Goldilocks prompt, wait-then-poll-then-cancel pattern.

Results (from research/_dr_spike_cancel_v2.json):
- Pre-cancel status confirmed: <yes/no>
- cancel() outcome: <success/exception details>
- Final terminal state: <cancelled/failed/completed/incomplete>
- Partial output preserved: <yes/no>
- Conclusion for Task 8 implementation: <implement defensively per the
  guarded pattern OR cancel works cleanly OR defer to v1.1>
```

- [ ] **Step 4: Commit**

```bash
git add scripts/spike/p28/spike_dr_cancel_v2.py research/_dr_spike_cancel_v2.* research/gemini-dr-api-spike-2026-05-11.md
git commit -m "spike(p28): re-verify cancel() with Goldilocks prompt + wait-poll-cancel pattern"
```

(If commitlint rejects `spike`, use `chore(p28):`.)

---

### Task 8: `cancel()` — failing tests + implementation

**Pre-condition:** Task 8a has populated §6 in `research/gemini-dr-api-spike-2026-05-11.md` with the verified cancel behavior. The implementation below is the **defensive baseline** — adjust if Task 8a reveals different behavior.

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
    async def test_cancel_5xx_returns_best_effort_cancelled(self):
        """Per spike §6: cancel may return 5xx in edge cases; treat as best-effort."""
        from google.genai._interactions import InternalServerError  # type: ignore[import-not-found]

        from thoth.providers.gemini import GeminiProvider

        provider = GeminiProvider(
            api_key="dummy", config={"model": "deep-research-preview-04-2026"}
        )
        provider.jobs["interactions/abc"] = {
            "kind": "deep_research", "interaction_id": "interactions/abc"
        }
        fake_cancel = AsyncMock(
            side_effect=InternalServerError(status_code=500, message="cancel failed server-side")
        )
        provider.client.aio.interactions = MagicMock()
        provider.client.aio.interactions.cancel = fake_cancel
        result = await provider.cancel("interactions/abc")
        # Cancel still reports cancelled (best-effort); the runtime treats SIGINT
        # as satisfied. check_status will surface the actual state on next poll.
        assert result["status"] == "cancelled"
        assert result.get("best_effort") is True
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

- [ ] **Step 2: Implement defensively**

```python
async def cancel(self, job_id: str) -> dict[str, Any]:
    """Cancel a job. For DR, calls interactions.cancel; for immediate, no-op.

    Immediate (chat-completion) jobs are already complete by the time submit
    returns, so cancel is a no-op there. DR jobs run server-side and must
    be explicitly cancelled via the Interactions API.

    Defensive 5xx handling per spike §6: if cancel itself returns a server
    error, mark cancel_requested locally and report cancelled best-effort.
    The runtime treats SIGINT as satisfied; check_status will surface the
    actual server-side state on the next poll.
    """
    if job_id not in self.jobs:
        return {"status": "not_found", "error": f"Unknown job_id: {job_id}"}
    job = self.jobs[job_id]
    if job.get("kind") != "deep_research":
        return {"status": "cancelled"}  # immediate path — already complete

    job["cancel_requested"] = True
    try:
        await self.client.aio.interactions.cancel(id=job_id)
        return {"status": "cancelled"}
    except Exception as e:
        # 5xx / network / unknown — treat as best-effort. Map for the error
        # field but still report cancelled so the runtime's SIGINT path
        # completes cleanly.
        if _is_interactions_error(e) and (getattr(e, "status_code", None) or 0) >= 500:
            return {
                "status": "cancelled",
                "best_effort": True,
                "error": f"cancel returned server error ({getattr(e, 'status_code', '?')}); "
                f"interaction may still be running. Next check_status will reflect.",
            }
        raise _map_gemini_error(e, self.model) from e
```

- [ ] **Step 3: Run + commit**

```bash
uv run pytest tests/test_provider_gemini.py::TestGeminiCancel -v
git add -A && git commit -m "feat(p28): implement GeminiProvider.cancel() with defensive 5xx handling

DR jobs: invoke client.aio.interactions.cancel(id) and set
cancel_requested flag. 5xx errors from cancel are treated as best-effort
(returns status=cancelled + best_effort=True) per spike §6 v2 finding;
the runtime's SIGINT path completes cleanly and check_status will surface
actual state on next poll. Immediate jobs: no-op (already complete)."
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
