#!/usr/bin/env python
"""One-shot script: capture current `thoth` output for every parity-tested invocation.

Run BEFORE any refactor code lands. Writes JSON baseline files into
tests/baselines/. Each baseline records exit code, stdout, stderr.

Usage:
    THOTH_TEST_MODE=1 python tests/baselines/capture_baselines.py

After baselines are committed, this script is deleted in Task 15.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

BASELINES_DIR = Path(__file__).parent

# (label, argv) pairs. Label is the baseline filename stem.
INVOCATIONS: list[tuple[str, list[str]]] = [
    ("help", ["--help"]),
    ("version_short", ["-V"]),
    ("version_long", ["--version"]),
    ("init_help", ["init", "--help"]),
    ("status_no_args", ["status"]),
    ("list_help", ["list", "--help"]),
    ("providers_no_args", ["providers"]),
    ("providers_list", ["providers", "list"]),
    ("config_no_args", ["config"]),
    ("config_list", ["config", "list"]),
    ("modes_no_args", ["modes"]),
    ("help_init", ["help", "init"]),
    ("help_auth", ["help", "auth"]),
    ("help_unknown_topic", ["help", "nosuchtopic"]),
    ("unknown_command", ["nonexistentword"]),
]


def capture(label: str, argv: list[str]) -> dict:
    result = subprocess.run(
        [sys.executable, "-m", "thoth", *argv],
        capture_output=True,
        text=True,
        timeout=30,
        env={"THOTH_TEST_MODE": "1", "PATH": "/usr/bin:/bin"},
    )
    return {
        "label": label,
        "argv": argv,
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def main() -> int:
    BASELINES_DIR.mkdir(exist_ok=True)
    for label, argv in INVOCATIONS:
        baseline = capture(label, argv)
        out_path = BASELINES_DIR / f"{label}.json"
        out_path.write_text(json.dumps(baseline, indent=2, sort_keys=True))
        print(f"captured: {label} (exit={baseline['exit_code']})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
