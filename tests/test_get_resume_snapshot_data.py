"""Category F — get_resume_snapshot_data unit tests (spec §6.8)."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

from tests.conftest import make_operation


def _write_checkpoint(checkpoint_dir: Path, op, **overrides) -> None:
    payload = {
        "id": op.id,
        "prompt": op.prompt,
        "mode": op.mode,
        "status": op.status,
        "created_at": op.created_at.isoformat(),
        "updated_at": op.updated_at.isoformat(),
        "output_paths": {},
        "input_files": [],
        "providers": {},
        "project": None,
        "output_dir": None,
        "error": None,
        "failure_type": None,
        **overrides,
    }
    (checkpoint_dir / f"{op.id}.json").write_text(json.dumps(payload))


def test_get_resume_snapshot_data_returns_none_for_missing_op(isolated_thoth_home, checkpoint_dir):
    from thoth.run import get_resume_snapshot_data

    assert get_resume_snapshot_data("not-real") is None


def test_snapshot_running_op_returns_status_running(checkpoint_dir):
    from thoth.run import get_resume_snapshot_data

    op = make_operation("research-20260427-000000-aaaaaaaaaaaaaaaa", status="running")
    _write_checkpoint(checkpoint_dir, op)

    data = get_resume_snapshot_data(op.id)
    assert data is not None
    assert data["operation_id"] == op.id
    assert data["status"] == "running"


def test_snapshot_recoverable_failure_maps_failed_with_transient(checkpoint_dir):
    """spec §8.5 mapping: status=failed + failure_type!=permanent → recoverable_failure."""
    from thoth.run import get_resume_snapshot_data

    op = make_operation(
        "research-20260427-000000-aaaaaaaaaaaaaaaa",
        status="failed",
    )
    _write_checkpoint(
        checkpoint_dir,
        op,
        status="failed",
        failure_type="transient",
        error="rate limit exceeded",
    )

    data = get_resume_snapshot_data(op.id)
    assert data is not None
    assert data["status"] == "recoverable_failure"
    assert data["last_error"] == "rate limit exceeded"


def test_snapshot_failed_permanent_keeps_failed_status(checkpoint_dir):
    from thoth.run import get_resume_snapshot_data

    op = make_operation("research-20260427-000000-aaaaaaaaaaaaaaaa", status="failed")
    _write_checkpoint(
        checkpoint_dir,
        op,
        status="failed",
        failure_type="permanent",
        error="auth failed",
    )

    data = get_resume_snapshot_data(op.id)
    assert data is not None
    assert data["status"] == "failed_permanent"


def test_signature_excludes_as_json():
    from thoth.run import get_resume_snapshot_data

    assert "as_json" not in inspect.signature(get_resume_snapshot_data).parameters
