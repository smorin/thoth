"""Extended OpenAI CLI lifecycle tests.

These tests hit the real OpenAI API and are therefore gated behind
``pytest -m extended`` plus ``OPENAI_API_KEY``. They exercise command-level
flows that unit tests cannot cover: ``resume --async`` against a real
background response and Ctrl-C cancellation through the actual CLI process.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest

from tests.extended.conftest import (
    REPO_ROOT,
    cancel_background_operation,
    cancel_openai_job_direct,
    load_checkpoint,
    payload,
    read_until_operation_id,
    run_thoth,
    wait_for_provider_job_id,
)

pytestmark = pytest.mark.extended


def test_openai_resume_async_cli_one_tick_after_explicit_async_submit(
    live_cli_env: tuple[dict[str, str], Path],
) -> None:
    """Live OpenAI background op can be checked with one non-blocking resume tick."""
    env, state_root = live_cli_env
    operation_id: str | None = None
    try:
        submit, submit_elapsed = run_thoth(
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
        submit_payload = payload(submit)
        assert submit_payload["status"] == "ok"
        assert submit_payload["data"]["status"] == "submitted"
        operation_id = submit_payload["data"]["operation_id"]
        assert operation_id
        assert submit_elapsed < 30

        resume_json, resume_elapsed = run_thoth(
            ["resume", operation_id, "--async", "--json"],
            env,
        )
        assert resume_json.returncode == 0, resume_json.stderr + resume_json.stdout
        assert resume_json.stdout.lstrip().startswith("{")
        assert resume_json.stdout.rstrip().endswith("}")
        assert resume_elapsed < 20
        resume_payload = payload(resume_json)
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

        resume_text, text_elapsed = run_thoth(["resume", operation_id, "--async"], env)
        assert resume_text.returncode == 0, resume_text.stderr + resume_text.stdout
        assert text_elapsed < 20
        assert (
            "No providers completed since last check." in resume_text.stdout
            or "Saved results from:" in resume_text.stdout
            or "already completed" in resume_text.stdout
        )

        status, _ = run_thoth(["status", operation_id, "--json"], env)
        assert status.returncode == 0, status.stderr + status.stdout
        status_data = payload(status)["data"]
        assert status_data["providers"]["openai"]["status"] in {
            "queued",
            "running",
            "completed",
        }
    finally:
        cancel_background_operation(operation_id, env, state_root)


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
        cwd=REPO_ROOT,
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
        operation_id, prefix_output = read_until_operation_id(proc)
        job_id = wait_for_provider_job_id(state_root, operation_id)

        os.killpg(proc.pid, signal.SIGINT)
        stdout, stderr = proc.communicate(timeout=45)
        combined = "".join(prefix_output) + stdout + stderr

        assert proc.returncode == 1, combined[-2000:]
        assert "Checkpoint saved. Resume with: thoth resume" in combined
        assert "Cancelled upstream: openai" in combined
        assert "Aborted!" in combined

        checkpoint = load_checkpoint(state_root, operation_id)
        assert checkpoint["status"] == "cancelled"
        assert checkpoint["providers"]["openai"]["job_id"] == job_id
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait(timeout=5)
        cancel_openai_job_direct(job_id)
