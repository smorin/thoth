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
