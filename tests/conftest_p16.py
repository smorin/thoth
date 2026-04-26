"""Test fixtures for P16 PR1 parity testing."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import TypedDict

import pytest

BASELINES_DIR = Path(__file__).parent / "baselines"


def _scrub_home(s: str) -> str:
    """Replace user's home directory with <HOME> placeholder for portable baselines."""
    home = os.path.expanduser("~")
    if home and home != "/":
        return s.replace(home, "<HOME>")
    return s


class BaselineRecord(TypedDict):
    label: str
    argv: list[str]
    exit_code: int
    stdout: str
    stderr: str


@pytest.fixture
def baseline() -> Callable[[str], BaselineRecord]:
    def _load(label: str) -> BaselineRecord:
        path = BASELINES_DIR / f"{label}.json"
        return json.loads(path.read_text())

    return _load


@pytest.fixture
def run_thoth() -> Callable[[list[str]], tuple[int, str, str]]:
    def _run(argv: list[str]) -> tuple[int, str, str]:
        result = subprocess.run(
            [sys.executable, "-m", "thoth", *argv],
            capture_output=True,
            text=True,
            timeout=30,
            env={"THOTH_TEST_MODE": "1", "PATH": "/usr/bin:/bin"},
        )
        return result.returncode, _scrub_home(result.stdout), _scrub_home(result.stderr)

    return _run
