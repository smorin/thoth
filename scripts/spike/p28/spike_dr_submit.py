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
from datetime import UTC, datetime
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
                "captured_at": datetime.now(tz=UTC).isoformat(),
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
