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
    "Exhaustively survey every programming language from 1950 to 2025. Be maximally comprehensive."
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
    interaction_id: str | None = getattr(resp, "id", None)
    print(f"  id = {interaction_id}")
    if not interaction_id:
        print("  no interaction_id returned from create()")
        return 1
    await asyncio.sleep(3)
    print("Calling cancel()...")
    t0 = time.monotonic()
    try:
        await client.aio.interactions.cancel(id=interaction_id)
        print(f"  cancel returned in {time.monotonic() - t0:.2f}s")
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
