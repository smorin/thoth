"""Resume-after-failure tests — migrated from thoth_test RES-01..03.

Each test uses `isolated_thoth_home` for XDG_CONFIG_HOME isolation and
`monkeypatch.chdir(tmp_path)` so the `*_mock_*.md` output files land in a
per-test tmp dir and never cross xdist workers.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests._fixture_helpers import (
    extract_resume_id,
    load_checkpoint,
    run_thoth,
)


def test_recoverable_failure_resume_reconnects_and_completes(
    isolated_thoth_home: Path,
    checkpoint_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RES-01: Recoverable failure (background-kind) → resume reconnects and completes.

    P18: the recoverable-failure resume hint only fires for background-kind
    runs (immediate-kind has no upstream job to reattach to). This test uses
    `--mode deep_research` to exercise the resumable path that the hint
    targets.
    """
    monkeypatch.chdir(tmp_path)

    exit_code, stdout, stderr = run_thoth(
        ["--mode", "deep_research", "res01 first", "--provider", "mock"],
        env_overrides={"THOTH_MOCK_BEHAVIOR": "flake:10", "THOTH_POLL_INTERVAL": "0.1"},
    )
    combined = stdout + stderr
    assert exit_code != 0, f"expected non-zero on flake exhaustion, got {exit_code}"
    assert "This failure is recoverable" in combined, f"recoverable hint missing: {combined!r}"
    op_id = extract_resume_id(combined)

    checkpoint = load_checkpoint(checkpoint_dir, op_id)
    assert checkpoint.get("failure_type") == "recoverable", (
        f"expected failure_type=recoverable in checkpoint, got {checkpoint!r}"
    )
    assert checkpoint["providers"]["mock"].get("job_id"), (
        f"expected job_id persisted in checkpoint, got {checkpoint!r}"
    )

    exit_code2, stdout2, stderr2 = run_thoth(
        ["resume", op_id],
        env_overrides={"THOTH_MOCK_BEHAVIOR": "default", "THOTH_POLL_INTERVAL": "0.1"},
    )
    combined2 = stdout2 + stderr2
    assert exit_code2 == 0, (
        f"expected successful resume, got exit={exit_code2}\nstdout={stdout2!r}\nstderr={stderr2!r}"
    )
    assert "Research completed" in combined2, f"expected completion on resume: {combined2!r}"


def test_permanent_failure_resume_refused_with_exit_code_7(
    isolated_thoth_home: Path,
    checkpoint_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RES-02: Permanent failure → resume refused with exit code 7."""
    monkeypatch.chdir(tmp_path)

    before = {p.stem for p in checkpoint_dir.glob("research-*.json")}
    exit_code, stdout, stderr = run_thoth(
        ["res02 first", "--provider", "mock"],
        env_overrides={"THOTH_MOCK_BEHAVIOR": "permanent", "THOTH_POLL_INTERVAL": "0.1"},
    )
    combined = stdout + stderr
    assert exit_code != 0, f"expected non-zero on permanent failure, got {exit_code}"
    assert "This failure is recoverable" not in combined, (
        f"permanent failure must not print recoverable hint: {combined!r}"
    )

    after = {p.stem for p in checkpoint_dir.glob("research-*.json")}
    new_ops = after - before
    assert len(new_ops) == 1, (
        f"expected exactly one new checkpoint, got {new_ops} (combined={combined!r})"
    )
    op_id = next(iter(new_ops))
    checkpoint = load_checkpoint(checkpoint_dir, op_id)
    assert checkpoint.get("failure_type") == "permanent", (
        f"expected failure_type=permanent, got {checkpoint!r}"
    )

    exit_code2, stdout2, stderr2 = run_thoth(
        ["resume", op_id],
        env_overrides={"THOTH_MOCK_BEHAVIOR": "default", "THOTH_POLL_INTERVAL": "0.1"},
    )
    combined2 = stdout2 + stderr2
    assert exit_code2 == 7, (
        f"expected exit code 7 for permanent-failed resume, got {exit_code2}\n"
        f"stdout={stdout2!r}\nstderr={stderr2!r}"
    )
    assert "failed permanently" in combined2, (
        f"expected 'failed permanently' message, got: {combined2!r}"
    )


def test_resume_of_already_completed_operation_is_noop(
    isolated_thoth_home: Path,
    checkpoint_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RES-03: Resume of an already-completed operation is a no-op."""
    monkeypatch.chdir(tmp_path)

    before = {p.stem for p in checkpoint_dir.glob("research-*.json")}
    exit_code, stdout, stderr = run_thoth(
        ["res03 first", "--provider", "mock"],
        env_overrides={"THOTH_MOCK_BEHAVIOR": "default", "THOTH_POLL_INTERVAL": "0.1"},
    )
    combined = stdout + stderr
    assert exit_code == 0, f"expected successful first run, got exit={exit_code}\n{combined!r}"
    after = {p.stem for p in checkpoint_dir.glob("research-*.json")}
    new_ops = after - before
    assert len(new_ops) == 1, (
        f"expected exactly one new checkpoint, got {new_ops} (combined={combined!r})"
    )
    op_id = next(iter(new_ops))
    checkpoint = load_checkpoint(checkpoint_dir, op_id)
    assert checkpoint.get("status") == "completed", (
        f"expected status=completed before resume, got {checkpoint!r}"
    )

    exit_code2, stdout2, stderr2 = run_thoth(
        ["resume", op_id],
        env_overrides={"THOTH_MOCK_BEHAVIOR": "default", "THOTH_POLL_INTERVAL": "0.1"},
    )
    combined2 = stdout2 + stderr2
    assert exit_code2 == 0, (
        f"expected exit 0 for already-completed resume, got {exit_code2}\n{combined2!r}"
    )
    assert "already completed" in combined2, (
        f"expected 'already completed' message, got {combined2!r}"
    )
