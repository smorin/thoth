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
    {
        "label": "tool_code_execution",
        "input_str": "Run a quick Python computation to estimate pi via Monte Carlo with 10k samples.",
        "extra": {"tools": [{"type": "code_execution"}]},
    },
    {
        "label": "collaborative_planning",
        "input_str": "Plan a 3-paper literature review on consensus algorithms.",
        "extra": {"agent_config": {"type": "deep-research", "collaborative_planning": True}},
    },
    {
        "label": "tool_file_search",
        "input_str": "Search any uploaded files for distributed-systems content.",
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
    deadline = time.monotonic() + 10 * 60
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
            print("    !!! captured requires_action payload (5000 char preview)")
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
    print("\n=== SUMMARY ===")
    print(f"Probes run: {len(results)}; requires_action triggered: {len(triggered)}")
    return 0


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main())
