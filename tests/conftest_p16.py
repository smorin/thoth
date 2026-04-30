"""Test fixtures for P16 PR1 parity testing."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import TypedDict

import pytest

BASELINES_DIR = Path(__file__).parent / "baselines"


def _scrub_home(s: str, home: str | None = None) -> str:
    """Replace user's home directory with <HOME> placeholder for portable baselines."""
    home_path = home or os.path.expanduser("~")
    if home_path and home_path != "/":
        return s.replace(home_path, "<HOME>")
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
def run_thoth() -> Iterator[Callable[[list[str]], tuple[int, str, str]]]:
    home = Path(tempfile.mkdtemp(prefix="tp16", dir="/tmp"))

    def _run(argv: list[str]) -> tuple[int, str, str]:
        # cwd=str(home): immune to leaked ./thoth.config.toml in the parent's
        # working directory (the repo root). Without this, ConfigManager's
        # relative project_config_paths would load the leaked file.
        result = subprocess.run(
            [sys.executable, "-m", "thoth", *argv],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(home),
            env={"THOTH_TEST_MODE": "1", "PATH": "/usr/bin:/bin", "HOME": str(home)},
        )
        return (
            result.returncode,
            _scrub_home(result.stdout, str(home)),
            _scrub_home(result.stderr, str(home)),
        )

    try:
        yield _run
    finally:
        shutil.rmtree(home, ignore_errors=True)
