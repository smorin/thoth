"""Extended OpenAI CLI lifecycle tests.

These tests hit the real OpenAI API and are therefore gated behind
``pytest -m extended`` plus ``OPENAI_API_KEY``. They exercise command-level
flows that unit tests cannot cover: ``resume --async`` against a real
background response and Ctrl-C cancellation through the actual CLI process.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import select
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.extended

_REPO_ROOT = Path(__file__).resolve().parents[2]
_OP_ID_RE = re.compile(r"Operation ID:\s*(research-\d{8}-\d{6}-[a-f0-9]{16})")
_OPENAI_BACKGROUND_MODE = {
    "provider": "openai",
    "model": "o4-mini-deep-research",
    "kind": "background",
}


def _require_openai_key() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY is required for OpenAI extended CLI lifecycle tests")


@pytest.fixture
def live_cli_env(tmp_path: Path) -> tuple[dict[str, str], Path]:
    """Return an isolated environment for live CLI subprocesses."""
    _require_openai_key()
    env = os.environ.copy()
    env.update(
        {
            "XDG_CONFIG_HOME": str(tmp_path / "config"),
            "XDG_STATE_HOME": str(tmp_path / "state"),
            "XDG_CACHE_HOME": str(tmp_path / "cache"),
            "PYTHONUNBUFFERED": "1",
            "COLUMNS": "200",
        }
    )
    env.setdefault("UV_CACHE_DIR", str(_REPO_ROOT / ".uv-cache"))
    return env, tmp_path


def _run_thoth(
    args: list[str],
    env: dict[str, str],
    *,
    timeout: float = 90.0,
) -> tuple[subprocess.CompletedProcess[str], float]:
    start = time.monotonic()
    result = subprocess.run(
        [sys.executable, "-m", "thoth", *args],
        cwd=_REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result, time.monotonic() - start


def _checkpoint_path(state_root: Path, operation_id: str) -> Path:
    return state_root / "state" / "thoth" / "checkpoints" / f"{operation_id}.json"


def _load_checkpoint(state_root: Path, operation_id: str) -> dict[str, Any]:
    return json.loads(_checkpoint_path(state_root, operation_id).read_text())


def _payload(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return json.loads(result.stdout)


def _cancel_operation(operation_id: str | None, env: dict[str, str]) -> None:
    if not operation_id:
        return
    _run_thoth(["cancel", operation_id, "--json"], env, timeout=45)


def _cancel_openai_job_direct(job_id: str | None) -> None:
    """Best-effort cleanup for jobs whose checkpoint was already terminal."""
    if not job_id:
        return

    from thoth.config import ConfigManager
    from thoth.providers import create_provider

    config = ConfigManager()
    config.load_all_layers({})
    provider = create_provider("openai", config, mode_config=_OPENAI_BACKGROUND_MODE)
    try:
        asyncio.run(provider.cancel(job_id))
    except Exception:
        # Cleanup must not obscure the assertion that already failed.
        pass


def _read_until_operation_id(
    proc: subprocess.Popen[str],
    *,
    timeout: float = 45.0,
) -> tuple[str, list[str]]:
    assert proc.stdout is not None
    assert proc.stderr is not None
    streams = [proc.stdout, proc.stderr]
    seen: list[str] = []
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        if proc.poll() is not None:
            remaining_out, remaining_err = proc.communicate(timeout=1)
            seen.extend([remaining_out, remaining_err])
            pytest.fail("thoth exited before printing an operation id:\n" + "".join(seen)[-2000:])

        readable, _, _ = select.select(streams, [], [], 0.2)
        for stream in readable:
            line = stream.readline()
            if not line:
                continue
            seen.append(line)
            match = _OP_ID_RE.search(line)
            if match:
                return match.group(1), seen

    proc.kill()
    pytest.fail("timed out waiting for operation id:\n" + "".join(seen)[-2000:])


def _wait_for_provider_job_id(
    state_root: Path,
    operation_id: str,
    *,
    timeout: float = 45.0,
) -> str:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        path = _checkpoint_path(state_root, operation_id)
        if path.exists():
            try:
                checkpoint = json.loads(path.read_text())
            except json.JSONDecodeError:
                time.sleep(0.1)
                continue
            job_id = checkpoint.get("providers", {}).get("openai", {}).get("job_id")
            if job_id:
                return str(job_id)
        time.sleep(0.2)
    pytest.fail(f"timed out waiting for provider job id in checkpoint for {operation_id}")


def test_openai_resume_async_cli_one_tick(live_cli_env: tuple[dict[str, str], Path]) -> None:
    """Live OpenAI background op can be checked with one non-blocking resume tick."""
    env, state_root = live_cli_env
    operation_id: str | None = None
    try:
        submit, submit_elapsed = _run_thoth(
            [
                "ask",
                "Return exactly these three words: async resume probe",
                "--mode",
                "quick_research",
                "--provider",
                "openai",
                "--async",
                "--json",
            ],
            env,
        )
        assert submit.returncode == 0, submit.stderr + submit.stdout
        submit_payload = _payload(submit)
        assert submit_payload["status"] == "ok"
        assert submit_payload["data"]["status"] == "submitted"
        operation_id = submit_payload["data"]["operation_id"]
        assert operation_id
        assert submit_elapsed < 30

        resume_json, resume_elapsed = _run_thoth(
            ["resume", operation_id, "--async", "--json"],
            env,
        )
        assert resume_json.returncode == 0, resume_json.stderr + resume_json.stdout
        assert resume_json.stdout.lstrip().startswith("{")
        assert resume_json.stdout.rstrip().endswith("}")
        assert resume_elapsed < 20
        resume_payload = _payload(resume_json)
        resume_data = resume_payload["data"]
        assert resume_payload["status"] == "ok"
        assert resume_data["operation_id"] == operation_id
        assert isinstance(resume_data["newly_completed"], list)
        assert set(resume_data["providers"]) == {"openai"}
        assert resume_data["providers"]["openai"]["status"] in {
            "queued",
            "running",
            "completed",
        }

        resume_text, text_elapsed = _run_thoth(["resume", operation_id, "--async"], env)
        assert resume_text.returncode == 0, resume_text.stderr + resume_text.stdout
        assert text_elapsed < 20
        assert (
            "No providers completed since last check." in resume_text.stdout
            or "Saved results from:" in resume_text.stdout
            or "already completed" in resume_text.stdout
        )

        status, _ = _run_thoth(["status", operation_id, "--json"], env)
        assert status.returncode == 0, status.stderr + status.stdout
        status_data = _payload(status)["data"]
        assert status_data["providers"]["openai"]["status"] in {
            "queued",
            "running",
            "completed",
        }
    finally:
        _cancel_operation(operation_id, env)


def test_openai_ctrl_c_sync_background_cancels_upstream(
    live_cli_env: tuple[dict[str, str], Path],
) -> None:
    """Ctrl-C during a live OpenAI background run cancels upstream and checkpoints."""
    env, state_root = live_cli_env
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "thoth",
            "ask",
            "Start a short live cancellation probe. Keep the response concise.",
            "--mode",
            "quick_research",
            "--provider",
            "openai",
            "--verbose",
            "--cancel-on-interrupt",
        ],
        cwd=_REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    operation_id: str | None = None
    job_id: str | None = None
    prefix_output: list[str] = []
    try:
        operation_id, prefix_output = _read_until_operation_id(proc)
        job_id = _wait_for_provider_job_id(state_root, operation_id)

        os.killpg(proc.pid, signal.SIGINT)
        stdout, stderr = proc.communicate(timeout=45)
        combined = "".join(prefix_output) + stdout + stderr

        assert proc.returncode == 1, combined[-2000:]
        assert "Checkpoint saved. Resume with: thoth resume" in combined
        assert "Cancelled upstream: openai" in combined
        assert "Aborted!" in combined

        checkpoint = _load_checkpoint(state_root, operation_id)
        assert checkpoint["status"] == "cancelled"
        assert checkpoint["providers"]["openai"]["job_id"] == job_id
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait(timeout=5)
        _cancel_openai_job_direct(job_id)
