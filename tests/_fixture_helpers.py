"""Shared builders for the migrated fixture tests.

Ported (not imported) from `thoth_test`, to avoid pulling in the custom runner's
module-level `_ensure_test_config_home()` + `atexit.register(shutil.rmtree, ...)`
side effects.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import types
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

THOTH_BIN = str(Path(__file__).resolve().parent.parent / "thoth")


def run_thoth(
    args: list[str],
    env_overrides: dict[str, str] | None = None,
    timeout: int = 30,
    cwd: str | Path | None = None,
) -> tuple[int, str, str]:
    """Run the thoth CLI in a subprocess and return (exit_code, stdout, stderr).

    Inherits `os.environ` so `monkeypatch.setenv("XDG_CONFIG_HOME", ...)` from
    the `isolated_thoth_home` fixture propagates into the subprocess.
    """
    cmd_env = os.environ.copy()
    if env_overrides:
        cmd_env.update(env_overrides)
    cmd_env.setdefault("MOCK_API_KEY", f"mock-key-{uuid4().hex[:16]}")
    cmd_env["COLUMNS"] = "200"

    result = subprocess.run(
        [THOTH_BIN, *args],
        env=cmd_env,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(cwd) if cwd is not None else None,
    )
    return result.returncode, result.stdout, result.stderr


def extract_operation_id(output: str) -> str:
    """Extract an operation ID from 'Operation ID: ...' CLI output."""
    match = re.search(r"Operation ID:\s*(research-\d{8}-\d{6}-[a-f0-9]{16})", output)
    if not match:
        raise AssertionError(f"operation ID not found in output: {output!r}")
    return match.group(1)


def extract_resume_id(output: str) -> str:
    """Extract an operation ID from a 'thoth --resume <id>' hint."""
    match = re.search(r"thoth --resume\s+(research-\d{8}-\d{6}-[a-f0-9]{16})", output)
    if not match:
        raise AssertionError(f"resume hint not found in output: {output!r}")
    return match.group(1)


def load_checkpoint(checkpoint_dir: Path, operation_id: str) -> dict[str, Any]:
    """Load a checkpoint file as JSON for assertions."""
    checkpoint_file = checkpoint_dir / f"{operation_id}.json"
    if not checkpoint_file.exists():
        raise AssertionError(f"checkpoint not found: {checkpoint_file}")
    with open(checkpoint_file) as f:
        return json.load(f)


class FakeLoop:
    """Advancing-clock event loop stub for deterministic poll-interval tests."""

    def __init__(self) -> None:
        self.now = 0.0

    def time(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class MockSeqProvider:
    """Provider stub that records poll times and completes on the second check."""

    model = "mock"

    def __init__(self, fake_loop: FakeLoop) -> None:
        self._fake_loop = fake_loop
        self.poll_times: list[float] = []

    async def submit(
        self, prompt: str, mode: str, system_prompt: str, verbose: bool = False
    ) -> str:
        return "job-1"

    async def check_status(self, job_id: str) -> dict[str, Any]:
        self.poll_times.append(self._fake_loop.time())
        if len(self.poll_times) == 1:
            return {"status": "running", "progress": 0.5}
        return {"status": "completed", "progress": 1.0}

    async def get_result(self, job_id: str, verbose: bool = False) -> str:
        return "mock result content"


def make_mock_openai_response(
    status: str,
    error: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> types.SimpleNamespace:
    """Build a fake OpenAI Response-like object for status-check tests."""
    obj = types.SimpleNamespace(status=status)
    if error is not None:
        obj.error = error
    if metadata is not None:
        obj.metadata = metadata
    return obj


def make_mock_openai_client(response_obj: object) -> types.SimpleNamespace:
    """Build a fake AsyncOpenAI client whose `responses.retrieve()` returns `response_obj`."""

    async def fake_retrieve(*args: object, **kwargs: object) -> object:
        return response_obj

    client = types.SimpleNamespace()
    client.responses = types.SimpleNamespace(retrieve=fake_retrieve)
    return client


def make_mock_openai_result_response(
    text: str,
    annotations: list[dict[str, Any]] | None = None,
    reasoning_summary: list[str] | None = None,
) -> types.SimpleNamespace:
    """Build a fake completed OpenAI Responses API result object for parser tests."""
    ann_objs = [types.SimpleNamespace(**{"type": "url_citation", **a}) for a in (annotations or [])]
    content_item = types.SimpleNamespace(type="output_text", text=text, annotations=ann_objs)
    message_item = types.SimpleNamespace(type="message", content=[content_item])
    items: list[object] = []
    if reasoning_summary is not None:
        summary_objs = [types.SimpleNamespace(text=s) for s in reasoning_summary]
        items.append(types.SimpleNamespace(type="reasoning", summary=summary_objs))
    items.append(message_item)
    return types.SimpleNamespace(output=items)


def write_test_checkpoint(
    checkpoint_dir: Path,
    operation_id: str,
    status: str = "completed",
    **overrides: Any,
) -> Path:
    """Create a valid checkpoint JSON file under the given directory."""
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    data: dict[str, Any] = {
        "id": operation_id,
        "prompt": "test checkpoint prompt",
        "mode": "default",
        "status": status,
        "created_at": (now - timedelta(minutes=5)).isoformat(),
        "updated_at": now.isoformat(),
        "providers": {"mock": {"status": "completed"}},
        "output_paths": {},
        "error": None,
        "progress": 1.0 if status == "completed" else 0.0,
        "project": None,
        "input_files": [],
        "failure_type": None,
    }
    data.update(overrides)
    checkpoint_file = checkpoint_dir / f"{operation_id}.json"
    with open(checkpoint_file, "w") as f:
        json.dump(data, f, indent=2)
    return checkpoint_file


def write_corrupted_checkpoint(checkpoint_dir: Path, operation_id: str) -> Path:
    """Create an intentionally-malformed checkpoint JSON file."""
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_file = checkpoint_dir / f"{operation_id}.json"
    checkpoint_file.write_text("{not valid json")
    return checkpoint_file
