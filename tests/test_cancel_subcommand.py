"""P18 Phase G: `thoth cancel <op-id>` subcommand.

Verifies the user-facing flow: load operation, call provider.cancel(),
update checkpoint to cancelled status, exit 0.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests._fixture_helpers import run_thoth
from thoth.cli import cli


def test_cancel_subcommand_registered() -> None:
    """`thoth cancel --help` returns 0 with usage text — the command is wired."""
    from click.testing import CliRunner

    r = CliRunner().invoke(cli, ["cancel", "--help"])
    assert r.exit_code == 0
    assert "cancel" in r.output.lower()


def test_cancel_missing_operation_exits_6() -> None:
    from click.testing import CliRunner

    r = CliRunner().invoke(cli, ["cancel", "DOES-NOT-EXIST-123"])
    assert r.exit_code == 6, r.output


def test_cancel_existing_operation_marks_cancelled(
    isolated_thoth_home: Path,
    checkpoint_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End-to-end: submit + async (background-kind) → cancel → checkpoint cancelled."""
    monkeypatch.chdir(tmp_path)

    # Submit a deep_research run async so it stays in the running state.
    exit_code, stdout, stderr = run_thoth(
        ["--mode", "deep_research", "cancel-test prompt", "--provider", "mock", "--async"],
    )
    assert exit_code == 0, f"submit failed: {stdout=!r} {stderr=!r}"
    # Extract operation id from stdout (mock submit prints "Operation ID: <id>")
    op_id = None
    for line in (stdout + stderr).splitlines():
        if "Operation ID:" in line:
            op_id = line.split("Operation ID:", 1)[1].strip()
            break
    assert op_id, f"could not parse op id: {stdout!r}"

    # Cancel
    cancel_code, cancel_stdout, cancel_stderr = run_thoth(["cancel", op_id])
    assert cancel_code == 0, f"cancel exit={cancel_code} {cancel_stdout=!r} {cancel_stderr=!r}"

    # Checkpoint reflects cancelled status
    checkpoint_file = checkpoint_dir / f"{op_id}.json"
    assert checkpoint_file.exists()
    data = json.loads(checkpoint_file.read_text())
    assert data["status"] == "cancelled", f"checkpoint not cancelled: {data!r}"


def test_cancel_already_completed_operation_is_idempotent(
    isolated_thoth_home: Path,
    checkpoint_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cancelling a completed operation should be a no-op success."""
    monkeypatch.chdir(tmp_path)

    # Run a default mock op to completion (immediate kind, sync).
    # THOTH_POLL_INTERVAL keeps the default polling loop fast under mock.
    exit_code, stdout, stderr = run_thoth(
        ["completed-test", "--provider", "mock"],
        env_overrides={"THOTH_POLL_INTERVAL": "0.1"},
    )
    assert exit_code == 0

    # Find the most recent checkpoint
    checkpoints = sorted(checkpoint_dir.glob("*.json"))
    assert checkpoints, f"no checkpoint created: {list(checkpoint_dir.iterdir())}"
    op_id = checkpoints[-1].stem

    cancel_code, _, _ = run_thoth(["cancel", op_id])
    assert cancel_code == 0
