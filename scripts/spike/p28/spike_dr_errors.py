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
        print(
            f"      -> {type(exc).__module__}.{type(exc).__name__}: code="
            f"{getattr(exc, 'code', None)} msg={str(exc)[:160]}"
        )

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
        print(
            f"      -> {type(exc).__module__}.{type(exc).__name__}: code="
            f"{getattr(exc, 'code', None)} msg={str(exc)[:160]}"
        )

    print("  [3] unknown interaction id — interactions.get")
    try:
        await client.aio.interactions.get(id="interactions/does-not-exist-spike")
    except Exception as exc:
        print(
            f"      -> {type(exc).__module__}.{type(exc).__name__}: code="
            f"{getattr(exc, 'code', None)} msg={str(exc)[:160]}"
        )
    return 0


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main())
