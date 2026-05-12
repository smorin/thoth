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
    print("\n=== FINAL INTERACTION ===")
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
