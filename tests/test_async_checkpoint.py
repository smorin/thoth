"""Async submission + status tests — migrated from thoth_test P07-M1-01/02.

Each test uses `isolated_thoth_home` so its checkpoints land in a per-test
XDG_CONFIG_HOME and never collide with other xdist workers.
"""

from __future__ import annotations

import re
from pathlib import Path

from tests._fixture_helpers import (
    extract_operation_id,
    load_checkpoint,
    run_thoth,
)


def test_async_submission_persists_provider_job_metadata(
    isolated_thoth_home: Path, checkpoint_dir: Path
) -> None:
    """P07-M1-01: async submission persists provider job metadata in the checkpoint."""
    env = {"THOTH_POLL_INTERVAL": "1"}
    exit_code, stdout, stderr = run_thoth(
        ["test async persistence", "--async", "--provider", "mock"],
        env_overrides=env,
        timeout=5,
    )
    assert exit_code == 0, f"unexpected exit code {exit_code}\nstdout={stdout}\nstderr={stderr}"

    operation_id = extract_operation_id(stdout)
    data = load_checkpoint(checkpoint_dir, operation_id)
    providers = data.get("providers", {})
    assert data.get("status") == "running", f"expected running checkpoint, got: {data}"
    assert "mock" in providers, f"mock provider missing from checkpoint: {data}"
    assert providers["mock"].get("status") == "running", f"expected running provider: {data}"
    job_id = providers["mock"].get("job_id")
    assert isinstance(job_id, str) and job_id.startswith("mock-"), (
        f"expected mock job id in checkpoint, got: {job_id!r}"
    )


def test_status_shows_running_provider_for_async_operation(
    isolated_thoth_home: Path, checkpoint_dir: Path
) -> None:
    """P07-M1-02: status shows provider state for an async-submitted operation."""
    env = {"THOTH_POLL_INTERVAL": "1"}
    exit_code, stdout, stderr = run_thoth(
        ["test async status", "--async", "--provider", "mock"],
        env_overrides=env,
        timeout=5,
    )
    assert exit_code == 0, f"unexpected exit code {exit_code}\nstdout={stdout}\nstderr={stderr}"

    operation_id = extract_operation_id(stdout)
    status_exit, status_stdout, status_stderr = run_thoth(
        ["status", operation_id],
        timeout=5,
    )
    assert status_exit == 0, (
        f"unexpected status exit {status_exit}\nstdout={status_stdout}\nstderr={status_stderr}"
    )
    assert "Provider Status:" in status_stdout, f"provider status missing: {status_stdout!r}"
    assert re.search(r"Mock:\s+▶\s+Running", status_stdout), (
        f"running mock status missing: {status_stdout!r}"
    )
